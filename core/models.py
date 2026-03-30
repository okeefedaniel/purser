"""Purser-specific concrete subclasses of Keel abstract models."""
from django.db import models
from django.utils.translation import gettext_lazy as _

from keel.core.models import AbstractAuditLog, AbstractNotification
from keel.notifications.models import AbstractNotificationPreference, AbstractNotificationLog


class AuditLog(AbstractAuditLog):
    """Purser audit log with domain-specific actions.

    Python 3.14 disallows extending enums with members, so we widen
    the action field to accept any string rather than subclassing
    Action. The base Action choices are still available for display.
    """

    # Purser-specific action constants (not a TextChoices subclass)
    ACTION_SUBMISSION_SUBMIT = 'submission_submit'
    ACTION_SUBMISSION_APPROVE = 'submission_approve'
    ACTION_SUBMISSION_REJECT = 'submission_reject'
    ACTION_CLOSE_PERIOD = 'close_period'
    ACTION_COMPLIANCE_SUBMIT = 'compliance_submit'
    ACTION_COMPLIANCE_ACCEPT = 'compliance_accept'
    ACTION_COMPLIANCE_REJECT = 'compliance_reject'
    ACTION_HARBOR_PULL = 'harbor_pull'

    # Override action field to allow longer values without enum constraint
    action = models.CharField(max_length=25)

    class Meta(AbstractAuditLog.Meta):
        db_table = 'purser_audit_log'


class Notification(AbstractNotification):

    class Meta(AbstractNotification.Meta):
        db_table = 'purser_notification'


class NotificationPreference(AbstractNotificationPreference):

    class Meta(AbstractNotificationPreference.Meta):
        db_table = 'purser_notification_preference'


class NotificationLog(AbstractNotificationLog):

    class Meta(AbstractNotificationLog.Meta):
        db_table = 'purser_notification_log'
