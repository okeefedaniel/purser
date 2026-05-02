"""Purser views — financial close, submissions, compliance, portal."""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from keel.compliance.models import ComplianceItem, ComplianceObligation
from keel.periods.models import FiscalPeriod, FiscalYear
from keel.reporting.models import ReportLineItem
from keel.signatures.models import ManifestHandoff

from .forms import CloseLocalSignForm, ProgramForm, SubmissionLineValueForm
from .models import (
    BudgetBaseline, ClosePackage, Program, Submission,
    SubmissionAttachment, SubmissionLineValue,
)
from .services import manifest_signing
from .workflows import SUBMISSION_WORKFLOW


# Admin-tier roles that satisfy any operational role gate. ``agency_admin``
# is the customer-side admin (no Django /admin/ access); ``purser_admin``
# / ``system_admin`` are the IT-tier roles. Centralized so adding another
# admin role in future is a one-line change.
_PURSER_ADMIN_ROLES = frozenset({'purser_admin', 'system_admin', 'agency_admin'})


def _check_role(user, allowed_roles):
    """Check if user has one of the allowed Purser roles."""
    role = getattr(user, 'role', '') or ''
    return role in allowed_roles or role in _PURSER_ADMIN_ROLES


def _user_can_edit_program(user, program) -> bool:
    """Agency/team scoping for a program submission.

    A user may touch a Program's submission state only when any of:
      * they are a Purser admin / system admin
      * they are in the Program's ``submitters`` team
      * they are in the Program's ``reviewers`` team (for save/review)

    Combined with ``_check_role`` this prevents any logged-in Keel user
    from mutating another agency's submissions by POSTing to the htmx
    ``save_line_value`` endpoint (IDOR #103) or instantiating arbitrary
    submissions via ``submission_form`` (#104).
    """
    if not user.is_authenticated:
        return False
    role = getattr(user, 'role', '') or ''
    if role in _PURSER_ADMIN_ROLES or getattr(user, 'is_superuser', False):
        return True
    if program.submitters.filter(pk=user.pk).exists():
        return True
    if program.reviewers.filter(pk=user.pk).exists():
        return True
    return False


# ---------------------------------------------------------------------------
# Close Dashboard
# ---------------------------------------------------------------------------
@login_required
def dashboard(request):
    """Close dashboard — grid of programs x recent periods."""
    current_fy = FiscalYear.objects.filter(is_current=True).first()
    # Keep the queryset unsliced so downstream .filter() / .last() still work;
    # materialize the top-4 list separately for grid rendering.
    periods_qs = FiscalPeriod.objects.filter(
        fiscal_year=current_fy,
    ).order_by('month') if current_fy else FiscalPeriod.objects.none()
    periods = list(periods_qs[:4])

    programs = Program.objects.filter(is_active=True).order_by('program_type', 'name')

    # Build grid data: {(program_id, period_id): submission}
    submissions = Submission.objects.filter(
        program__in=programs,
        fiscal_period__in=periods,
    ).select_related('program', 'fiscal_period')

    grid = {}
    for sub in submissions:
        grid.setdefault(sub.program_id, {})[sub.fiscal_period_id] = sub

    # Current period stats
    current_period = periods_qs.filter(
        status__in=['submissions_due', 'under_review'],
    ).first() or (periods_qs.last() if periods_qs.exists() else None)

    stats = {}
    if current_period:
        period_subs = Submission.objects.filter(fiscal_period=current_period)
        stats = {
            'total_programs': programs.count(),
            'submitted': period_subs.exclude(status='draft').count(),
            'approved': period_subs.filter(status__in=['approved', 'closed']).count(),
            'draft': period_subs.filter(status='draft').count(),
        }

    from django.urls import reverse
    dashboard_url = reverse('dashboard_alias')
    review_url = reverse('purser:review_queue')
    program_url = reverse('purser:program_list')
    stat_urls = {
        'programs_url': program_url if stats.get('total_programs') else dashboard_url,
        'submitted_url': review_url if stats.get('submitted') else dashboard_url,
        'approved_url': dashboard_url,
        'draft_url': dashboard_url,
    }
    return render(request, 'purser/dashboard.html', {
        'programs': programs,
        'periods': periods,
        'grid': grid,
        'current_period': current_period,
        'stats': stats,
        'stat_urls': stat_urls,
        'current_fy': current_fy,
    })


# ---------------------------------------------------------------------------
# Submission Form
# ---------------------------------------------------------------------------
@login_required
def submission_form(request, program_code, period_id):
    """Submission form — chart of accounts as editable form."""
    program = get_object_or_404(Program, code=program_code)
    period = get_object_or_404(FiscalPeriod, pk=period_id)

    if not _check_role(request.user, ['purser_submitter', 'purser_reviewer']):
        raise PermissionDenied('Not authorized for Purser submissions.')
    if not _user_can_edit_program(request.user, program):
        raise PermissionDenied('Not a member of this program.')

    submission, created = Submission.objects.get_or_create(
        program=program, fiscal_period=period,
        defaults={'created_by': request.user},
    )

    # Get line items for this schema
    line_items = program.report_schema.line_items.order_by('group', 'sort_order')

    # Get or create line values
    values = {}
    for li in line_items:
        val, _ = SubmissionLineValue.objects.get_or_create(
            submission=submission, line_item=li,
            defaults={'created_by': request.user},
        )
        values[li.id] = val

    # Prior period values for comparison
    prior_period = FiscalPeriod.objects.filter(
        fiscal_year=period.fiscal_year,
        month=period.month - 1,
    ).first()
    prior_values = {}
    if prior_period:
        prior_sub = Submission.objects.filter(
            program=program, fiscal_period=prior_period,
        ).first()
        if prior_sub:
            for pv in prior_sub.line_values.all():
                prior_values[pv.line_item_id] = pv.numeric_value

    # Budget baselines for comparison
    budgets = {}
    for bb in BudgetBaseline.objects.filter(
        program=program, fiscal_year=period.fiscal_year,
    ):
        budgets[bb.line_item_id] = bb.monthly_spread.get(
            str(period.month), bb.annual_amount / 12
        )

    # Check available transitions
    transitions = SUBMISSION_WORKFLOW.get_available_transitions(
        submission.status, request.user,
    )

    return render(request, 'purser/submission_form.html', {
        'program': program,
        'period': period,
        'submission': submission,
        'line_items': line_items,
        'values': values,
        'prior_values': prior_values,
        'budgets': budgets,
        'transitions': transitions,
    })


@login_required
@require_POST
def save_line_value(request, value_id):
    """htmx endpoint — save a single line value inline."""
    value = get_object_or_404(
        SubmissionLineValue.objects.select_related(
            'submission__program',
        ),
        pk=value_id,
    )
    submission = value.submission

    if not _check_role(request.user, ['purser_submitter', 'purser_reviewer']):
        return JsonResponse({'error': 'forbidden'}, status=403)
    if not _user_can_edit_program(request.user, submission.program):
        return JsonResponse({'error': 'forbidden'}, status=403)

    if submission.status not in ('draft', 'revision_requested'):
        return JsonResponse({'error': 'Submission is not editable'}, status=400)

    form = SubmissionLineValueForm(request.POST, instance=value)
    if form.is_valid():
        form.save()
        return render(request, 'purser/includes/submission_line.html', {
            'line_item': value.line_item,
            'value': value,
        })

    return JsonResponse({'errors': form.errors}, status=400)


@login_required
@require_POST
def transition_submission(request, submission_id, target_status):
    """Execute a workflow transition on a submission."""
    submission = get_object_or_404(
        Submission.objects.select_related('program'),
        pk=submission_id,
    )
    if not _check_role(request.user, ['purser_submitter', 'purser_reviewer']):
        raise PermissionDenied('Not authorized for Purser submissions.')
    if not _user_can_edit_program(request.user, submission.program):
        raise PermissionDenied('Not a member of this program.')
    comment = request.POST.get('comment', '')

    SUBMISSION_WORKFLOW.execute(
        submission, target_status,
        user=request.user, comment=comment,
    )

    # Set timestamps
    if target_status == 'submitted':
        submission.submitted_by = request.user
        submission.submitted_at = timezone.now()
        submission.save(update_fields=['submitted_by', 'submitted_at'])
    elif target_status in ('approved', 'revision_requested'):
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.reviewer_notes = comment
        submission.save(update_fields=['reviewed_by', 'reviewed_at', 'reviewer_notes'])

    return redirect('purser:submission_form',
                    program_code=submission.program.code,
                    period_id=submission.fiscal_period_id)


# ---------------------------------------------------------------------------
# Review Queue
# ---------------------------------------------------------------------------
@login_required
def review_queue(request):
    """List submissions pending review."""
    submissions = Submission.objects.filter(
        status__in=['submitted', 'under_review'],
    ).select_related('program', 'fiscal_period', 'submitted_by')

    return render(request, 'purser/review_queue.html', {
        'submissions': submissions,
    })


@login_required
def review_detail(request, submission_id):
    """Review a specific submission."""
    submission = get_object_or_404(
        Submission.objects.select_related('program', 'fiscal_period'),
        pk=submission_id,
    )
    line_items = submission.program.report_schema.line_items.order_by('sort_order')
    values = {v.line_item_id: v for v in submission.line_values.all()}

    transitions = SUBMISSION_WORKFLOW.get_available_transitions(
        submission.status, request.user,
    )

    return render(request, 'purser/review_detail.html', {
        'submission': submission,
        'line_items': line_items,
        'values': values,
        'transitions': transitions,
    })


# ---------------------------------------------------------------------------
# Compliance Dashboard
# ---------------------------------------------------------------------------
@login_required
def compliance_dashboard(request):
    """Compliance overview — by program, overdue items."""
    obligations = ComplianceObligation.objects.filter(
        is_active=True,
    ).select_related('template')

    items = ComplianceItem.objects.select_related(
        'obligation', 'obligation__template',
    )

    overdue = items.filter(status='overdue').order_by('due_date')
    upcoming = items.filter(
        status__in=['upcoming', 'pending'],
    ).order_by('due_date')[:20]

    stats = {
        'total_active': obligations.count(),
        'overdue_count': overdue.count(),
        'upcoming_count': upcoming.count(),
        'submitted_pending': items.filter(
            status__in=['submitted', 'under_review'],
        ).count(),
    }

    return render(request, 'purser/compliance_dashboard.html', {
        'overdue': overdue,
        'upcoming': upcoming,
        'stats': stats,
    })


@login_required
def compliance_detail(request, item_id):
    """Detail view of a compliance item."""
    item = get_object_or_404(
        ComplianceItem.objects.select_related(
            'obligation', 'obligation__template', 'fiscal_period',
        ),
        pk=item_id,
    )
    return render(request, 'purser/compliance_detail.html', {
        'item': item,
    })


# ---------------------------------------------------------------------------
# External Portal
# ---------------------------------------------------------------------------
@login_required
def portal_dashboard(request):
    """External submitter portal — their compliance obligations.

    Scopes ``ComplianceItem`` rows to the requesting user's Agency via the
    GenericFK ``recipient`` field. Without this filter, every external
    submitter could see every agency's obligations (finding #112).
    """
    from django.contrib.contenttypes.models import ContentType

    user = request.user
    agency = getattr(user, 'agency', None)
    items = ComplianceItem.objects.none()
    if agency is not None:
        agency_ct = ContentType.objects.get_for_model(agency.__class__)
        items = ComplianceItem.objects.filter(
            recipient_content_type=agency_ct,
            recipient_object_id=agency.pk,
            status__in=['upcoming', 'pending', 'overdue', 'submitted',
                        'under_review', 'accepted', 'rejected'],
        ).select_related(
            'obligation', 'obligation__template',
        ).order_by('due_date')

    return render(request, 'purser/portal_dashboard.html', {
        'items': items,
    })


# ---------------------------------------------------------------------------
# Close Package
# ---------------------------------------------------------------------------
@login_required
def close_package(request, period_id):
    """View consolidated close package for a period."""
    period = get_object_or_404(FiscalPeriod, pk=period_id)
    package, created = ClosePackage.objects.get_or_create(
        fiscal_period=period,
        defaults={'created_by': request.user},
    )

    submissions = Submission.objects.filter(
        fiscal_period=period,
    ).select_related('program')

    # Signing context — show Send-to-Manifest / Upload-signed buttons and
    # the last handoff's state (if any) on the close-package detail page.
    latest_handoff = ManifestHandoff.objects.filter(
        source_app_label='purser',
        source_model='closepackage',
        source_pk=str(package.pk),
    ).first()

    return render(request, 'purser/close_package.html', {
        'period': period,
        'package': package,
        'submissions': submissions,
        'manifest_available': manifest_signing.is_available(),
        'latest_handoff': latest_handoff,
        'signed_attachments': package.attachments.filter(
            source='manifest_signed',
        ).order_by('-uploaded_at'),
    })


@login_required
@require_POST
def close_package_sign_send(request, period_id):
    """Send the close package through Manifest for signing."""
    period = get_object_or_404(FiscalPeriod, pk=period_id)
    package = get_object_or_404(ClosePackage, fiscal_period=period)

    if not package.pdf_export:
        messages.error(
            request,
            'Generate the close package PDF before sending for signing.',
        )
        return redirect('purser:close_package', period_id=period.pk)

    if not manifest_signing.is_available():
        messages.error(
            request,
            'Manifest is not configured. Use "Upload signed close package" instead.',
        )
        return redirect('purser:close_package', period_id=period.pk)

    display_name = request.user.get_full_name() or request.user.username
    handoff = manifest_signing.send_to_manifest(
        close_package=package,
        request=request,
        signers=[{'email': request.user.email, 'name': display_name}],
        created_by=request.user,
    )

    if handoff.status == ManifestHandoff.Status.SENT:
        messages.success(
            request,
            'Close package sent to Manifest for signing. '
            'The status will advance to Signed on completion.',
        )
    else:
        messages.error(
            request,
            f'Could not reach Manifest: '
            f'{handoff.error_message or handoff.get_status_display()}. '
            'The attempt is logged.',
        )
    return redirect('purser:close_package', period_id=period.pk)


@login_required
def close_package_sign_local(request, period_id):
    """Upload a locally-signed close package when Manifest isn't deployed."""
    period = get_object_or_404(FiscalPeriod, pk=period_id)
    package = get_object_or_404(ClosePackage, fiscal_period=period)

    if not package.pdf_export:
        messages.error(
            request,
            'Generate the close package PDF before uploading a signed version.',
        )
        return redirect('purser:close_package', period_id=period.pk)

    if request.method == 'POST':
        form = CloseLocalSignForm(request.POST, request.FILES)
        if form.is_valid():
            manifest_signing.local_sign(
                close_package=package,
                signed_pdf=form.cleaned_data['signed_pdf'],
                created_by=request.user,
            )
            messages.success(
                request,
                'Signed close package recorded. Status moved to Signed.',
            )
            return redirect('purser:close_package', period_id=period.pk)
    else:
        form = CloseLocalSignForm()

    return render(request, 'purser/close_package_local_sign.html', {
        'period': period,
        'package': package,
        'form': form,
    })


# ---------------------------------------------------------------------------
# Program Admin
# ---------------------------------------------------------------------------
@login_required
def program_list(request):
    """Manage programs."""
    programs = Program.objects.all().select_related('report_schema')
    return render(request, 'purser/program_list.html', {
        'programs': programs,
    })


@login_required
def program_form(request, program_id=None):
    """Create or edit a program."""
    program = get_object_or_404(Program, pk=program_id) if program_id else None
    form = ProgramForm(request.POST or None, instance=program)

    if request.method == 'POST' and form.is_valid():
        prog = form.save(commit=False)
        if not prog.pk:
            prog.created_by = request.user
        prog.save()
        form.save_m2m()
        return redirect('purser:program_list')

    return render(request, 'purser/program_form.html', {
        'form': form,
        'program': program,
    })
