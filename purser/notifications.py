"""Purser notification type registrations with Keel's notification registry."""
from keel.notifications.registry import register, NotificationType

# ---------------------------------------------------------------------------
# Financial Close Notifications
# ---------------------------------------------------------------------------
register(NotificationType(
    key='purser_submission_due',
    label='Submission Due',
    description='Reminder that a program submission is due',
    category='Financial Close',
    default_channels=['in_app', 'email'],
    default_roles=['purser_submitter'],
    priority='medium',
    email_template='notifications/submission_due.html',
    email_subject='{period_label} close: your {program_name} submission is due by {deadline}',
))

register(NotificationType(
    key='purser_submission_overdue',
    label='Submission Overdue',
    description='A program submission is past its deadline',
    category='Financial Close',
    default_channels=['in_app', 'email'],
    default_roles=['purser_submitter', 'purser_reviewer'],
    priority='high',
    email_template='notifications/submission_due.html',
    email_subject='OVERDUE: {program_name} has not submitted for {period_label}',
    allow_mute=False,
))

register(NotificationType(
    key='purser_submission_ready_for_review',
    label='Submission Ready for Review',
    description='A new submission is ready for review',
    category='Financial Close',
    default_channels=['in_app', 'email'],
    default_roles=['purser_reviewer'],
    priority='medium',
    email_template='notifications/submission_due.html',
    email_subject='New submission from {program_name} ready for review',
))

register(NotificationType(
    key='purser_revision_requested',
    label='Revision Requested',
    description='A submission needs revision',
    category='Financial Close',
    default_channels=['in_app', 'email'],
    default_roles=['purser_submitter'],
    priority='high',
    email_template='notifications/submission_due.html',
    email_subject='Your {program_name} submission needs revision',
))

register(NotificationType(
    key='purser_close_package_ready',
    label='Close Package Ready',
    description='All submissions approved, close package ready',
    category='Financial Close',
    default_channels=['in_app', 'email'],
    default_roles=['purser_admin', 'agency_admin', 'purser_reviewer'],
    priority='medium',
    email_template='notifications/submission_due.html',
    email_subject='All programs submitted for {period_label}. Close package ready.',
))

register(NotificationType(
    key='purser_variance_alert',
    label='Variance Alert',
    description='A line item exceeds budget variance threshold',
    category='Financial Close',
    default_channels=['in_app', 'email'],
    default_roles=['purser_reviewer', 'purser_admin', 'agency_admin'],
    priority='high',
    email_template='notifications/submission_due.html',
    email_subject='{program_name} {line_item} is {pct}% over budget for {period_label}',
))

register(NotificationType(
    key='purser_close_package_signed',
    label='Close Package Signed',
    description='Close package has been signed in Manifest',
    category='Financial Close',
    default_channels=['in_app', 'email'],
    default_roles=['purser_readonly'],
    priority='medium',
    email_template='notifications/submission_due.html',
    email_subject='{period_label} close package signed and available',
))

# ---------------------------------------------------------------------------
# Compliance Notifications
# ---------------------------------------------------------------------------
register(NotificationType(
    key='purser_compliance_reminder',
    label='Compliance Reminder',
    description='Upcoming compliance deadline',
    category='Compliance',
    default_channels=['email'],
    default_roles=['external_submitter'],
    priority='medium',
    email_template='notifications/compliance_reminder.html',
    email_subject='Reminder: {item_label} is due on {due_date}',
))

register(NotificationType(
    key='purser_compliance_overdue',
    label='Compliance Overdue',
    description='A compliance item is past its due date',
    category='Compliance',
    default_channels=['in_app', 'email'],
    default_roles=['external_submitter', 'purser_compliance_officer'],
    priority='high',
    email_template='notifications/compliance_overdue.html',
    email_subject='OVERDUE: {item_label} from {recipient_name}',
    allow_mute=False,
))

register(NotificationType(
    key='purser_compliance_escalation',
    label='Compliance Escalation',
    description='Compliance item escalated past grace period',
    category='Compliance',
    default_channels=['email'],
    default_roles=['purser_admin', 'agency_admin'],
    priority='urgent',
    email_template='notifications/compliance_overdue.html',
    email_subject='ESCALATION: {recipient_name} is {days} days overdue on {item_label}',
    allow_mute=False,
))

register(NotificationType(
    key='purser_compliance_submitted',
    label='Compliance Document Submitted',
    description='A grant recipient submitted a compliance document',
    category='Compliance',
    default_channels=['in_app', 'email'],
    default_roles=['purser_compliance_officer'],
    priority='medium',
    email_template='notifications/compliance_reminder.html',
    email_subject='New compliance submission from {recipient_name} for {item_label}',
))

register(NotificationType(
    key='purser_compliance_accepted',
    label='Compliance Accepted',
    description='A compliance submission was accepted',
    category='Compliance',
    default_channels=['email'],
    default_roles=['external_submitter'],
    priority='low',
    email_template='notifications/compliance_reminder.html',
    email_subject='Your {item_label} has been accepted',
))

register(NotificationType(
    key='purser_compliance_rejected',
    label='Compliance Rejected',
    description='A compliance submission was rejected and needs resubmission',
    category='Compliance',
    default_channels=['email'],
    default_roles=['external_submitter'],
    priority='high',
    email_template='notifications/compliance_reminder.html',
    email_subject='Your {item_label} needs resubmission: {notes}',
))
