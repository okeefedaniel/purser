from django.contrib import admin

from .models import (
    Program, Submission, SubmissionLineValue,
    SubmissionAttachment, ClosePackage, BudgetBaseline,
)


class SubmissionLineValueInline(admin.TabularInline):
    model = SubmissionLineValue
    extra = 0
    fields = ('line_item', 'numeric_value', 'text_value', 'note')


class SubmissionAttachmentInline(admin.TabularInline):
    model = SubmissionAttachment
    extra = 0
    fields = ('file', 'description')


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'program_type', 'report_schema', 'is_active',
                    'pulls_from_harbor')
    list_filter = ('program_type', 'is_active', 'pulls_from_harbor')
    search_fields = ('name', 'code')
    filter_horizontal = ('submitters', 'reviewers')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('program', 'fiscal_period', 'status', 'source',
                    'submitted_by', 'submitted_at')
    list_filter = ('status', 'source', 'program')
    search_fields = ('program__name', 'program__code')
    raw_id_fields = ('submitted_by', 'reviewed_by')
    inlines = [SubmissionLineValueInline, SubmissionAttachmentInline]


@admin.register(ClosePackage)
class ClosePackageAdmin(admin.ModelAdmin):
    list_display = ('fiscal_period', 'status', 'published_at')
    list_filter = ('status',)
    raw_id_fields = ('published_by',)


@admin.register(BudgetBaseline)
class BudgetBaselineAdmin(admin.ModelAdmin):
    list_display = ('program', 'fiscal_year', 'line_item', 'annual_amount')
    list_filter = ('program', 'fiscal_year')
