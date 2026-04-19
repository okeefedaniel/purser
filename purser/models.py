"""Purser domain models — financial close, submissions, close packages."""
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from keel.core.models import KeelBaseModel, AbstractStatusHistory
from keel.security.scanning import FileSecurityValidator


class Program(KeelBaseModel):
    """A DECD program that reports monthly activity."""

    class ProgramType(models.TextChoices):
        GRANT = 'grant', _('Grant')
        LOAN = 'loan', _('Loan')
        TAX_CREDIT = 'tax_credit', _('Tax Credit')
        BOND = 'bond', _('Bond Financing')
        FEDERAL_PASSTHROUGH = 'federal_passthrough', _('Federal Pass-Through')
        OTHER = 'other', _('Other')

    name = models.CharField(max_length=200)             # "Manufacturing Assistance Act"
    code = models.CharField(max_length=20, unique=True) # "MAA"
    program_type = models.CharField(
        max_length=50, choices=ProgramType.choices,
    )
    report_schema = models.ForeignKey(
        'keel_reporting.ReportSchema', on_delete=models.PROTECT,
        related_name='purser_programs',
    )

    # Role assignments via keel.auth
    submitters = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='purser_program_submissions',
        blank=True,
    )
    reviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='purser_program_reviews',
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    # Harbor integration
    pulls_from_harbor = models.BooleanField(default=False)
    harbor_api_endpoint = models.URLField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.code} — {self.name}"


class Submission(KeelBaseModel):
    """A program team's monthly financial report for a fiscal period.

    Uses keel.workflow for state management.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        SUBMITTED = 'submitted', _('Submitted')
        UNDER_REVIEW = 'under_review', _('Under Review')
        REVISION_REQUESTED = 'revision_requested', _('Revision Requested')
        APPROVED = 'approved', _('Approved')
        CLOSED = 'closed', _('Closed')

    class Source(models.TextChoices):
        MANUAL = 'manual', _('Manual Entry')
        HARBOR_PULL = 'harbor_pull', _('Auto-Pull from Harbor')
        CSV_IMPORT = 'csv_import', _('CSV Import')

    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, related_name='submissions',
    )
    fiscal_period = models.ForeignKey(
        'keel_periods.FiscalPeriod', on_delete=models.CASCADE,
        related_name='purser_submissions',
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT,
    )
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.MANUAL,
    )

    # People
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='purser_submitted',
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='purser_reviewed',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['program', 'fiscal_period']
        ordering = ['-fiscal_period__start_date', 'program__name']

    def __str__(self):
        return f"{self.program.code} — {self.fiscal_period.label}"


class SubmissionLineValue(KeelBaseModel):
    """A single value in a submission, tied to a ReportLineItem."""

    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name='line_values',
    )
    line_item = models.ForeignKey(
        'keel_reporting.ReportLineItem', on_delete=models.CASCADE,
        related_name='purser_values',
    )
    numeric_value = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    text_value = models.TextField(blank=True)
    note = models.TextField(blank=True)                 # Per-line explanation

    class Meta:
        unique_together = ['submission', 'line_item']

    def __str__(self):
        return f"{self.line_item.code}: {self.numeric_value or self.text_value}"


class SubmissionAttachment(KeelBaseModel):
    """Supporting document on a submission."""

    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name='attachments',
    )
    file = models.FileField(
        upload_to='submissions/attachments/%Y/%m/',
        validators=[FileSecurityValidator()],
    )
    filename = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=200, blank=True)

    def save(self, *args, **kwargs):
        if self.file and not self.filename:
            self.filename = self.file.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.filename or str(self.file)


class ClosePackage(KeelBaseModel):
    """Consolidated output for a fiscal period.

    Created when all program submissions are approved.
    Flows to Manifest for sign-off, then to Helm.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft — awaiting submissions')
        COMPLETE = 'complete', _('Complete — all approved')
        SIGNING = 'signing', _('Signing — in Manifest')
        SIGNED = 'signed', _('Signed — approved')
        PUBLISHED = 'published', _('Published — distributed')

    fiscal_period = models.OneToOneField(
        'keel_periods.FiscalPeriod', on_delete=models.CASCADE,
        related_name='purser_close_package',
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT,
    )

    # Aggregated snapshots (JSON)
    aggregated_data = models.JSONField(default=dict, blank=True)
    variance_vs_prior = models.JSONField(default=dict, blank=True)
    variance_vs_budget = models.JSONField(default=dict, blank=True)
    compliance_summary = models.JSONField(default=dict, blank=True)

    # Manifest integration
    manifest_signing_id = models.UUIDField(null=True, blank=True)

    # Generated output
    executive_summary = models.TextField(blank=True)
    pdf_export = models.FileField(
        upload_to='close_packages/%Y/%m/', blank=True,
        validators=[FileSecurityValidator()],
    )

    # Distribution
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fiscal_period__start_date']

    def __str__(self):
        return f"Close Package — {self.fiscal_period.label}"


class BudgetBaseline(KeelBaseModel):
    """Annual budget for a program. Used for variance analysis."""

    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, related_name='budgets',
    )
    fiscal_year = models.ForeignKey(
        'keel_periods.FiscalYear', on_delete=models.CASCADE,
        related_name='purser_budgets',
    )
    line_item = models.ForeignKey(
        'keel_reporting.ReportLineItem', on_delete=models.CASCADE,
        related_name='purser_budgets',
    )
    annual_amount = models.DecimalField(max_digits=15, decimal_places=2)
    monthly_spread = models.JSONField(default=dict, blank=True)
    # {"1": 50000, "2": 50000, ...} — month keys match FiscalPeriod.month

    class Meta:
        unique_together = ['program', 'fiscal_year', 'line_item']

    def __str__(self):
        return f"{self.program.code} — {self.line_item.code} — {self.fiscal_year.name}"


class SubmissionStatusHistory(AbstractStatusHistory):
    """Immutable audit trail of submission status transitions."""
    submission = models.ForeignKey(
        'Submission', on_delete=models.CASCADE, related_name='status_history',
    )

    class Meta(AbstractStatusHistory.Meta):
        verbose_name_plural = 'submission status histories'
