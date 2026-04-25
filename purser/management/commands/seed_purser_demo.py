"""Seed demo fiscal year + programs for Purser dashboard demos.

Creates a current FiscalYear, its 12 FiscalPeriods, a minimal
ReportSchema, a few Programs, and demo Submission/ClosePackage
rows so the Close Dashboard grid renders varied statuses instead
of all "Not Started". Idempotent.
"""
from datetime import date
from django.utils import timezone

from django.conf import settings
from django.core.management.base import BaseCommand

from keel.periods.models import FiscalYear, FiscalPeriod
from keel.reporting.models import ReportSchema

from purser.models import ClosePackage, Program, Submission


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

        self._seed_closeout_demo(fiscal_year, today)

        self.stdout.write(self.style.SUCCESS('Purser demo seed complete.'))

    def _seed_closeout_demo(self, fiscal_year, today):
        """Populate Submissions + ClosePackages for past periods.

        Cycles statuses across (program × period) so the Close Dashboard
        grid renders varied "Submitted / Approved / Closed / Draft"
        cells instead of an empty "Not Started" wall.
        """
        # Status cycle — mirrors the spread a real agency would have
        # mid-fiscal-year (most months approved, current month in flight).
        STATUS_CYCLE = [
            Submission.Status.APPROVED,
            Submission.Status.APPROVED,
            Submission.Status.SUBMITTED,
            Submission.Status.UNDER_REVIEW,
            Submission.Status.DRAFT,
        ]

        past_periods = list(
            FiscalPeriod.objects
            .filter(fiscal_year=fiscal_year, end_date__lte=today)
            .order_by('start_date')
        )
        if not past_periods:
            self.stdout.write(self.style.WARNING(
                '  No past fiscal periods yet — skipping Submission seed.'
            ))
            return

        programs = list(Program.objects.filter(code__in=[c for c, _, _ in PROGRAMS]))
        now = timezone.now()
        created_subs = 0
        for prog_idx, program in enumerate(programs):
            for per_idx, period in enumerate(past_periods):
                status = STATUS_CYCLE[(prog_idx + per_idx) % len(STATUS_CYCLE)]
                _, was_created = Submission.objects.get_or_create(
                    program=program,
                    fiscal_period=period,
                    defaults={
                        'status': status,
                        'source': Submission.Source.MANUAL,
                        'submitted_at': now if status != Submission.Status.DRAFT else None,
                        'reviewed_at': (
                            now if status in (
                                Submission.Status.APPROVED,
                                Submission.Status.UNDER_REVIEW,
                            ) else None
                        ),
                    },
                )
                if was_created:
                    created_subs += 1

        # ClosePackage for the two earliest past periods (one Signed,
        # one Complete) to demonstrate the close flow downstream of
        # approved submissions.
        package_targets = [
            (past_periods[0], ClosePackage.Status.SIGNED),
        ]
        if len(past_periods) > 1:
            package_targets.append((past_periods[1], ClosePackage.Status.COMPLETE))

        created_pkgs = 0
        for period, pkg_status in package_targets:
            _, was_created = ClosePackage.objects.get_or_create(
                fiscal_period=period,
                defaults={'status': pkg_status},
            )
            if was_created:
                created_pkgs += 1

        self.stdout.write(self.style.SUCCESS(
            f'  Closeout seed: {created_subs} submissions, {created_pkgs} close packages'
        ))
