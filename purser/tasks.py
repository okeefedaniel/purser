"""Background tasks for compliance and submission deadline checking."""
import logging
from datetime import timedelta

from django.utils import timezone

from keel.compliance.models import ComplianceItem

logger = logging.getLogger(__name__)


def check_compliance_deadlines():
    """Nightly check for upcoming and overdue compliance items.

    Run via cron or management command at 6am daily.
    """
    today = timezone.now().date()

    # Mark overdue items
    overdue = ComplianceItem.objects.filter(
        status='pending',
        due_date__lt=today,
    )
    count = overdue.update(status='overdue')
    if count:
        logger.info("Marked %d compliance items as overdue", count)

    # Transition upcoming to pending (within reminder lead days)
    upcoming = ComplianceItem.objects.filter(
        status='upcoming',
    ).select_related('obligation__template')

    for item in upcoming:
        lead_days = item.obligation.template.reminder_lead_days
        if item.due_date - timedelta(days=lead_days) <= today:
            item.status = 'pending'
            item.save(update_fields=['status', 'updated_at'])


def check_submission_deadlines():
    """Nightly check for submission deadlines."""
    from keel.periods.models import FiscalPeriod

    today = timezone.now()

    # Find periods with passed submission deadlines
    overdue_periods = FiscalPeriod.objects.filter(
        status='submissions_due',
        submission_deadline__lt=today,
    )

    for period in overdue_periods:
        from purser.models import Submission
        incomplete = Submission.objects.filter(
            fiscal_period=period,
            status='draft',
        ).select_related('program')

        if incomplete.exists():
            logger.warning(
                "Period %s has %d incomplete submissions past deadline",
                period.label, incomplete.count(),
            )
