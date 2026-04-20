from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'
    label = 'purser_core'
    verbose_name = 'Purser Core'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # Register Purser models for signal-based audit logging
        from keel.core.audit_signals import register_audited_model, connect_audit_signals

        register_audited_model('purser.Program', 'Program')
        register_audited_model('purser.Submission', 'Submission')
        register_audited_model('purser.SubmissionLineValue', 'Submission Line Value')
        register_audited_model('purser.SubmissionAttachment', 'Submission Attachment')
        register_audited_model('purser.ClosePackage', 'Close Package')
        register_audited_model('purser.BudgetBaseline', 'Budget Baseline')

        connect_audit_signals()
