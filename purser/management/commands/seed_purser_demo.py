"""Seed demo fiscal year + programs for Purser dashboard demos.

Creates a current FiscalYear, its 12 FiscalPeriods, a minimal
ReportSchema, and a few Programs so the purser dashboard renders
non-zero numbers. Idempotent.
"""
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand

from keel.periods.models import FiscalYear, FiscalPeriod
from keel.reporting.models import ReportSchema

from purser.models import Program


MONTH_LABELS = [
    'July', 'August', 'September', 'October', 'November', 'December',
    'January', 'February', 'March', 'April', 'May', 'June',
]

PROGRAMS = [
    ('MAA', 'Manufacturing Assistance Act', Program.ProgramType.GRANT),
    ('SBX', 'Small Business Express', Program.ProgramType.LOAN),
    ('FPT', 'Federal Pass-Through', Program.ProgramType.FEDERAL_PASSTHROUGH),
    ('BND', 'Economic Development Bonds', Program.ProgramType.BOND),
]


class Command(BaseCommand):
    help = 'Seed demo fiscal year, periods, report schema, and programs for Purser.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true')

    def handle(self, *args, **options):
        if not getattr(settings, 'DEMO_MODE', False) and not options['force']:
            self.stdout.write(self.style.WARNING(
                'DEMO_MODE is not enabled. Use --force to override.'
            ))
            return

        today = date.today()
        fy_start_year = today.year if today.month >= 7 else today.year - 1
        fy_name = f'FY{fy_start_year + 1}'

        fiscal_year, _ = FiscalYear.objects.update_or_create(
            name=fy_name,
            defaults={
                'start_date': date(fy_start_year, 7, 1),
                'end_date': date(fy_start_year + 1, 6, 30),
                'is_current': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(f'  Fiscal year: {fiscal_year}'))

        for i, label in enumerate(MONTH_LABELS):
            cal_month = 7 + i if i < 6 else i - 5
            cal_year = fy_start_year if i < 6 else fy_start_year + 1
            next_month = cal_month + 1 if cal_month < 12 else 1
            next_year = cal_year if cal_month < 12 else cal_year + 1
            FiscalPeriod.objects.update_or_create(
                fiscal_year=fiscal_year,
                month=i + 1,
                defaults={
                    'label': f'{label} {cal_year}',
                    'start_date': date(cal_year, cal_month, 1),
                    'end_date': date(next_year, next_month, 1),
                    'status': (
                        FiscalPeriod.Status.OPEN if cal_year > today.year or
                        (cal_year == today.year and cal_month >= today.month)
                        else FiscalPeriod.Status.CLOSED
                    ),
                },
            )

        schema, _ = ReportSchema.objects.update_or_create(
            slug='grant-monthly-close',
            defaults={
                'name': 'Grant Program Monthly Close',
                'description': 'Standard monthly close report for grant programs.',
                'product': 'purser',
                'version': 1,
                'is_active': True,
            },
        )

        for code, name, ptype in PROGRAMS:
            Program.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'program_type': ptype,
                    'report_schema': schema,
                    'is_active': True,
                },
            )
            self.stdout.write(self.style.SUCCESS(f'  Program: {code} — {name}'))

        self.stdout.write(self.style.SUCCESS('Purser demo seed complete.'))
