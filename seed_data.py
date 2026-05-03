#!/usr/bin/env python
"""Seed Purser with fiscal years, report schemas, compliance templates, and sample programs."""
import os
from datetime import date

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purser_site.settings')
django.setup()

from keel.compliance.models import ComplianceTemplate
from keel.periods.models import FiscalYear, FiscalPeriod
from keel.reporting.models import ReportSchema, ReportLineItem


def seed_fiscal_years():
    """Create FY2025 and FY2026 with all 12 monthly periods."""
    YEARS = [
        ('FY2025', date(2024, 7, 1), date(2025, 6, 30), False),
        ('FY2026', date(2025, 7, 1), date(2026, 6, 30), True),
    ]

    # Month mapping: fiscal month 1=July, 2=Aug, ..., 12=June
    MONTH_MAP = {
        1: (7, 'July'), 2: (8, 'August'), 3: (9, 'September'),
        4: (10, 'October'), 5: (11, 'November'), 6: (12, 'December'),
        7: (1, 'January'), 8: (2, 'February'), 9: (3, 'March'),
        10: (4, 'April'), 11: (5, 'May'), 12: (6, 'June'),
    }

    for name, start, end, is_current in YEARS:
        fy, created = FiscalYear.objects.get_or_create(
            name=name,
            defaults={'start_date': start, 'end_date': end, 'is_current': is_current},
        )
        if created:
            print(f"  Created {name}")

        for fiscal_month, (cal_month, month_name) in MONTH_MAP.items():
            # Determine the calendar year for this month
            if cal_month >= 7:
                cal_year = start.year
            else:
                cal_year = end.year

            period_start = date(cal_year, cal_month, 1)
            # Calculate end of month
            if cal_month == 12:
                period_end = date(cal_year, 12, 31)
            elif cal_month in (1, 3, 5, 7, 8, 10):
                period_end = date(cal_year, cal_month, 31)
            elif cal_month in (4, 6, 9, 11):
                period_end = date(cal_year, cal_month, 30)
            else:  # February
                if cal_year % 4 == 0 and (cal_year % 100 != 0 or cal_year % 400 == 0):
                    period_end = date(cal_year, 2, 29)
                else:
                    period_end = date(cal_year, 2, 28)

            label = f"{month_name} {cal_year}"
            FiscalPeriod.objects.get_or_create(
                fiscal_year=fy, month=fiscal_month,
                defaults={
                    'label': label,
                    'start_date': period_start,
                    'end_date': period_end,
                },
            )

    print(f"  Fiscal years: {FiscalYear.objects.count()}, Periods: {FiscalPeriod.objects.count()}")


def seed_report_schemas():
    """Create the three starter report schemas with line items."""

    # --- Grant Program Monthly Close ---
    schema, _ = ReportSchema.objects.get_or_create(
        slug='grant-monthly-close',
        defaults={
            'name': 'Grant Program Monthly Close',
            'product': 'purser',
            'description': 'Monthly financial activity report for grant programs.',
        },
    )
    GRANT_ITEMS = [
        ('BEG_BAL', 'Beginning balance', 'currency', 0, True, 'Prior period END_BAL', 'Balances'),
        ('NEW_APPROP', 'New appropriations', 'currency', 1, False, '', 'Activity'),
        ('OBLIG', 'New obligations', 'currency', 2, False, '', 'Activity'),
        ('DISB', 'Disbursements', 'currency', 3, False, '', 'Activity'),
        ('DEOBLIG', 'Deobligations', 'currency', 4, False, '', 'Activity'),
        ('RECAP', 'Recaptured funds', 'currency', 5, False, '', 'Activity'),
        ('END_BAL', 'Ending balance', 'currency', 6, True, 'BEG_BAL + NEW_APPROP + RECAP - DISB - DEOBLIG', 'Balances'),
        ('APPS_RECV', 'Applications received', 'integer', 7, False, '', 'Metrics'),
        ('APPS_APPR', 'Applications approved', 'integer', 8, False, '', 'Metrics'),
        ('JOBS_COMMIT', 'Jobs committed', 'integer', 9, False, '', 'Metrics'),
        ('JOBS_VERIFY', 'Jobs verified', 'integer', 10, False, '', 'Metrics'),
        ('NOTES', 'Program notes', 'text', 11, False, '', ''),
    ]
    for code, label, dtype, order, calc, formula, group in GRANT_ITEMS:
        ReportLineItem.objects.get_or_create(
            schema=schema, code=code,
            defaults={
                'label': label, 'data_type': dtype, 'sort_order': order,
                'is_calculated': calc, 'formula': formula, 'group': group,
                'is_required': dtype != 'text',
            },
        )
    print(f"  Grant schema: {schema.line_items.count()} line items")

    # --- Loan Program Monthly Close ---
    schema, _ = ReportSchema.objects.get_or_create(
        slug='loan-monthly-close',
        defaults={
            'name': 'Loan Program Monthly Close',
            'product': 'purser',
            'description': 'Monthly financial activity report for loan programs.',
        },
    )
    LOAN_ITEMS = [
        ('BEG_BAL', 'Beginning portfolio balance', 'currency', 0, True, 'Prior period END_BAL', 'Balances'),
        ('NEW_LOANS', 'New loans issued', 'currency', 1, False, '', 'Activity'),
        ('REPAY', 'Principal repayments', 'currency', 2, False, '', 'Activity'),
        ('WRITEOFF', 'Write-offs', 'currency', 3, False, '', 'Activity'),
        ('END_BAL', 'Ending portfolio balance', 'currency', 4, True, 'BEG_BAL + NEW_LOANS - REPAY - WRITEOFF', 'Balances'),
        ('APPS_RECV', 'Applications received', 'integer', 5, False, '', 'Metrics'),
        ('APPS_APPR', 'Applications approved', 'integer', 6, False, '', 'Metrics'),
        ('DELINQ_30', 'Delinquent 30+ days', 'integer', 7, False, '', 'Risk'),
        ('DELINQ_90', 'Delinquent 90+ days', 'integer', 8, False, '', 'Risk'),
        ('NOTES', 'Program notes', 'text', 9, False, '', ''),
    ]
    for code, label, dtype, order, calc, formula, group in LOAN_ITEMS:
        ReportLineItem.objects.get_or_create(
            schema=schema, code=code,
            defaults={
                'label': label, 'data_type': dtype, 'sort_order': order,
                'is_calculated': calc, 'formula': formula, 'group': group,
                'is_required': dtype != 'text',
            },
        )
    print(f"  Loan schema: {schema.line_items.count()} line items")

    # --- Tax Credit Monthly Close ---
    schema, _ = ReportSchema.objects.get_or_create(
        slug='tax-credit-monthly-close',
        defaults={
            'name': 'Tax Credit Monthly Close',
            'product': 'purser',
            'description': 'Monthly financial activity report for tax credit programs.',
        },
    )
    TC_ITEMS = [
        ('AUTH_BAL', 'Authorized balance', 'currency', 0, True, 'Prior period END_AUTH', 'Balances'),
        ('NEW_AUTH', 'New authorizations', 'currency', 1, False, '', 'Activity'),
        ('ISSUED', 'Credits issued/claimed', 'currency', 2, False, '', 'Activity'),
        ('EXPIRED', 'Credits expired', 'currency', 3, False, '', 'Activity'),
        ('END_AUTH', 'Ending authorized balance', 'currency', 4, True, 'AUTH_BAL + NEW_AUTH - ISSUED - EXPIRED', 'Balances'),
        ('CERTS', 'Certificates issued', 'integer', 5, False, '', 'Metrics'),
        ('NOTES', 'Program notes', 'text', 6, False, '', ''),
    ]
    for code, label, dtype, order, calc, formula, group in TC_ITEMS:
        ReportLineItem.objects.get_or_create(
            schema=schema, code=code,
            defaults={
                'label': label, 'data_type': dtype, 'sort_order': order,
                'is_calculated': calc, 'formula': formula, 'group': group,
                'is_required': dtype != 'text',
            },
        )
    print(f"  Tax credit schema: {schema.line_items.count()} line items")


def seed_compliance_templates():
    """Create the 9 standard compliance templates."""
    TEMPLATES = [
        ('quarterly-progress-report', 'Quarterly progress report',
         'document', 'quarterly', 14, 7, True, 'pdf,docx'),
        ('annual-audited-financials', 'Annual audited financials',
         'financial_report', 'annual', 30, 14, True, 'pdf'),
        ('job-creation-milestone-y1', 'Job creation milestone — Year 1',
         'milestone', 'one_time', 30, 14, False, ''),
        ('job-creation-milestone-y2', 'Job creation milestone — Year 2',
         'milestone', 'one_time', 30, 14, False, ''),
        ('site-visit-certification', 'Site visit certification',
         'certification', 'annual', 14, 7, True, 'pdf'),
        ('quarterly-financial-report', 'Quarterly financial report',
         'financial_report', 'quarterly', 14, 7, True, 'pdf,xlsx'),
        ('environmental-compliance-cert', 'Environmental compliance certification',
         'certification', 'annual', 30, 14, True, 'pdf'),
        ('insurance-certificate-renewal', 'Insurance certificate renewal',
         'document', 'annual', 30, 14, True, 'pdf'),
        ('semi-annual-progress-report', 'Semi-annual progress report',
         'document', 'semi_annual', 14, 7, True, 'pdf,docx'),
    ]

    for slug, name, req_type, cadence, lead, esc, req_doc, file_types in TEMPLATES:
        ComplianceTemplate.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'requirement_type': req_type,
                'cadence': cadence,
                'reminder_lead_days': lead,
                'escalation_after_days': esc,
                'requires_document': req_doc,
                'accepted_file_types': file_types,
            },
        )

    print(f"  Compliance templates: {ComplianceTemplate.objects.count()}")


def seed_sample_programs():
    """Create sample programs for testing."""
    from purser.models import Program

    grant_schema = ReportSchema.objects.get(slug='grant-monthly-close')
    loan_schema = ReportSchema.objects.get(slug='loan-monthly-close')
    tc_schema = ReportSchema.objects.get(slug='tax-credit-monthly-close')

    PROGRAMS = [
        ('MAA', 'Manufacturing Assistance Act', 'grant', grant_schema),
        ('SAG', 'Small Business Assistance Grant', 'grant', grant_schema),
        ('UDAG', 'Urban Development Action Grant', 'grant', grant_schema),
        ('SLF', 'Small Business Loan Fund', 'loan', loan_schema),
        ('URB', 'Urban Act Loan Program', 'loan', loan_schema),
        ('FILM', 'Film & Digital Media Tax Credit', 'tax_credit', tc_schema),
        ('HTCC', 'Historic Tax Credit', 'tax_credit', tc_schema),
    ]

    for code, name, ptype, schema in PROGRAMS:
        Program.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'program_type': ptype,
                'report_schema': schema,
            },
        )

    print(f"  Programs: {Program.objects.count()}")


if __name__ == '__main__':
    print("Seeding Purser data...")
    seed_fiscal_years()
    seed_report_schemas()
    seed_compliance_templates()
    seed_sample_programs()
    print("Done.")
