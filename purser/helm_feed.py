"""Purser's /api/v1/helm-feed/ endpoint.

Exposes fiscal close and financial metrics for Helm's executive dashboard.
"""
from django.conf import settings

from keel.feed.views import helm_feed_view


def _product_url():
    if getattr(settings, 'DEMO_MODE', False):
        return 'https://demo-purser.docklabs.ai'
    return 'https://purser.docklabs.ai'


@helm_feed_view
def purser_helm_feed(request):
    from purser.models import ClosePackage, Submission

    base_url = _product_url()

    # ── Metrics ──────────────────────────────────────────────────

    # Current close package progress
    latest_close = ClosePackage.objects.order_by('-created_at').first()
    close_progress = 0
    if latest_close:
        # Calculate progress as percentage of submissions approved for this period
        total_subs = Submission.objects.filter(fiscal_period=latest_close.fiscal_period).count()
        approved_subs = Submission.objects.filter(
            fiscal_period=latest_close.fiscal_period,
            status='approved',
        ).count()
        if total_subs > 0:
            close_progress = int((approved_subs / total_subs) * 100)

    # Submissions pending review
    pending_review = Submission.objects.filter(
        status__in=['submitted', 'under_review'],
    ).count()

    # Variance flags (submissions with revision requested)
    variance_flags = Submission.objects.filter(
        status='revision_requested',
    ).count()

    metrics = [
        {
            'key': 'close_progress',
            'label': 'Close Progress',
            'value': close_progress,
            'unit': 'percent',
            'trend': None, 'trend_value': None, 'trend_period': None,
            'severity': 'normal',
            'deep_link': f'{base_url}/purser/close/',
        },
        {
            'key': 'pending_review',
            'label': 'Pending Review',
            'value': pending_review,
            'unit': None,
            'trend': None, 'trend_value': None, 'trend_period': None,
            'severity': 'normal',
            'deep_link': f'{base_url}/purser/review/',
        },
        {
            'key': 'variance_flags',
            'label': 'Variance Flags',
            'value': variance_flags,
            'unit': None,
            'trend': None, 'trend_value': None, 'trend_period': None,
            'severity': 'warning' if variance_flags > 0 else 'normal',
            'deep_link': f'{base_url}/purser/',
        },
    ]

    # ── Action Items ─────────────────────────────────────────────
    action_items = []

    # Submissions awaiting review
    submissions_to_review = (
        Submission.objects
        .filter(status__in=['submitted', 'under_review'])
        .select_related('program')
        .order_by('submitted_at')[:5]
    )
    for sub in submissions_to_review:
        program_name = sub.program.name if hasattr(sub, 'program') and sub.program else 'Unknown'
        action_items.append({
            'id': f'purser-review-{sub.pk}',
            'type': 'approval',
            'title': f'Review: {program_name} submission',
            'description': f'Status: {sub.get_status_display()}',
            'priority': 'medium',
            'due_date': '',
            'assigned_to_role': 'program_director',
            'deep_link': f'{base_url}/purser/review/{sub.pk}/',
            'created_at': sub.submitted_at.isoformat() if hasattr(sub, 'submitted_at') and sub.submitted_at else '',
        })

    # ── Alerts ───────────────────────────────────────────────────
    alerts = []

    if variance_flags > 0:
        alerts.append({
            'id': 'purser-variances',
            'type': 'variance',
            'title': f'{variance_flags} submission{"s" if variance_flags != 1 else ""} flagged for revision',
            'severity': 'warning',
            'since': '',
            'deep_link': f'{base_url}/purser/',
        })

    return {
        'product': 'purser',
        'product_label': 'Purser',
        'product_url': f'{base_url}/dashboard/',
        'metrics': metrics,
        'action_items': action_items,
        'alerts': alerts,
        'sparklines': {},
    }
