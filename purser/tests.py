"""Baseline tests for Purser's state machines and close/compliance logic.

Covers:
  * Submission state machine — happy path, invalid transitions, permissions,
    comment requirements, and status history audit trail.
  * Compliance deadline workflow — overdue handling, rejection/resubmit,
    waive permissions.
  * Close package generation — aggregation gating on approved submissions.
"""
from datetime import date
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from keel.accounts.models import KeelUser
from keel.compliance.models import ComplianceItem
from keel.periods.models import FiscalPeriod, FiscalYear
from keel.reporting.models import ReportLineItem, ReportSchema

from purser.models import (
    BudgetBaseline,
    ClosePackage,
    Program,
    Submission,
    SubmissionLineValue,
    SubmissionStatusHistory,
)
from purser.services.close_package import generate_close_package
from purser.workflows import COMPLIANCE_WORKFLOW, SUBMISSION_WORKFLOW


def make_user(username, role=None, *, is_superuser=False):
    """Create a KeelUser with the given purser product role."""
    user = KeelUser.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='irrelevant-for-tests-123',
        is_superuser=is_superuser,
        is_staff=is_superuser,
    )
    if role is not None:
        user._product_role = role
    return user


class SubmissionWorkflowFixture(TestCase):
    """Shared fixture for submission workflow tests."""

    @classmethod
    def setUpTestData(cls):
        cls.year = FiscalYear.objects.create(
            name='FY2026',
            start_date=date(2025, 7, 1),
            end_date=date(2026, 6, 30),
            is_current=True,
        )
        cls.period = FiscalPeriod.objects.create(
            fiscal_year=cls.year,
            month=9,
            label='March 2026',
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )
        cls.schema = ReportSchema.objects.create(
            name='Monthly Close',
            slug='monthly-close',
            product='purser',
        )
        cls.program = Program.objects.create(
            name='Manufacturing Assistance Act',
            code='MAA',
            program_type=Program.ProgramType.GRANT,
            report_schema=cls.schema,
        )

    def make_submission(self, status=Submission.Status.DRAFT):
        return Submission.objects.create(
            program=self.program,
            fiscal_period=self.period,
            status=status,
        )


class SubmissionHappyPathTests(SubmissionWorkflowFixture):
    """The full draft → submitted → under_review → approved → closed path."""

    def test_full_lifecycle(self):
        submitter = make_user('submitter', role='purser_submitter')
        reviewer = make_user('reviewer', role='purser_reviewer')
        admin = make_user('admin', role='purser_admin')
        submission = self.make_submission()

        SUBMISSION_WORKFLOW.execute(submission, 'submitted', user=submitter)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'submitted')

        SUBMISSION_WORKFLOW.execute(submission, 'under_review', user=reviewer)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'under_review')

        SUBMISSION_WORKFLOW.execute(submission, 'approved', user=reviewer)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'approved')

        SUBMISSION_WORKFLOW.execute(submission, 'closed', user=admin)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'closed')

    def test_revision_cycle(self):
        submitter = make_user('submitter', role='purser_submitter')
        reviewer = make_user('reviewer', role='purser_reviewer')
        submission = self.make_submission()

        SUBMISSION_WORKFLOW.execute(submission, 'submitted', user=submitter)
        SUBMISSION_WORKFLOW.execute(submission, 'under_review', user=reviewer)
        SUBMISSION_WORKFLOW.execute(
            submission, 'revision_requested',
            user=reviewer, comment='Line 4 missing note',
        )
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'revision_requested')

        SUBMISSION_WORKFLOW.execute(submission, 'draft', user=submitter)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'draft')

    def test_status_history_is_recorded(self):
        submitter = make_user('submitter', role='purser_submitter')
        reviewer = make_user('reviewer', role='purser_reviewer')
        submission = self.make_submission()

        SUBMISSION_WORKFLOW.execute(submission, 'submitted', user=submitter)
        SUBMISSION_WORKFLOW.execute(submission, 'under_review', user=reviewer)

        history = list(
            SubmissionStatusHistory.objects
            .filter(submission=submission)
            .order_by('changed_at')
        )
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].old_status, 'draft')
        self.assertEqual(history[0].new_status, 'submitted')
        self.assertEqual(history[0].changed_by, submitter)
        self.assertEqual(history[1].new_status, 'under_review')
        self.assertEqual(history[1].changed_by, reviewer)


class SubmissionInvalidTransitionTests(SubmissionWorkflowFixture):
    """Reject transitions that aren't in the workflow graph."""

    def test_draft_cannot_skip_to_approved(self):
        reviewer = make_user('reviewer', role='purser_reviewer')
        submission = self.make_submission()
        with self.assertRaises(ValidationError):
            SUBMISSION_WORKFLOW.execute(submission, 'approved', user=reviewer)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'draft')

    def test_draft_cannot_skip_to_closed(self):
        admin = make_user('admin', role='purser_admin')
        submission = self.make_submission()
        with self.assertRaises(ValidationError):
            SUBMISSION_WORKFLOW.execute(submission, 'closed', user=admin)

    def test_approved_cannot_go_back_to_draft(self):
        admin = make_user('admin', role='purser_admin')
        submission = self.make_submission(Submission.Status.APPROVED)
        with self.assertRaises(ValidationError):
            SUBMISSION_WORKFLOW.execute(submission, 'draft', user=admin)

    def test_closed_is_terminal(self):
        admin = make_user('admin', role='purser_admin')
        submission = self.make_submission(Submission.Status.CLOSED)
        available = SUBMISSION_WORKFLOW.get_available_transitions(
            submission.status, admin,
        )
        self.assertEqual(available, [])

    def test_revision_requested_requires_comment(self):
        reviewer = make_user('reviewer', role='purser_reviewer')
        submission = self.make_submission(Submission.Status.UNDER_REVIEW)
        with self.assertRaises(ValidationError):
            SUBMISSION_WORKFLOW.execute(
                submission, 'revision_requested', user=reviewer, comment='',
            )
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'under_review')

    def test_failed_transition_leaves_no_history(self):
        reviewer = make_user('reviewer', role='purser_reviewer')
        submission = self.make_submission()
        with self.assertRaises(ValidationError):
            SUBMISSION_WORKFLOW.execute(submission, 'approved', user=reviewer)
        self.assertFalse(
            SubmissionStatusHistory.objects.filter(submission=submission).exists()
        )


class SubmissionPermissionTests(SubmissionWorkflowFixture):
    """Only the right role can execute each transition."""

    def test_submitter_cannot_review(self):
        submitter = make_user('submitter', role='purser_submitter')
        submission = self.make_submission(Submission.Status.SUBMITTED)
        with self.assertRaises(PermissionDenied):
            SUBMISSION_WORKFLOW.execute(submission, 'under_review', user=submitter)

    def test_submitter_cannot_approve(self):
        submitter = make_user('submitter', role='purser_submitter')
        submission = self.make_submission(Submission.Status.UNDER_REVIEW)
        with self.assertRaises(PermissionDenied):
            SUBMISSION_WORKFLOW.execute(submission, 'approved', user=submitter)

    def test_reviewer_cannot_close(self):
        reviewer = make_user('reviewer', role='purser_reviewer')
        submission = self.make_submission(Submission.Status.APPROVED)
        with self.assertRaises(PermissionDenied):
            SUBMISSION_WORKFLOW.execute(submission, 'closed', user=reviewer)

    def test_readonly_user_has_no_transitions(self):
        readonly = make_user('readonly', role='purser_readonly')
        submission = self.make_submission(Submission.Status.SUBMITTED)
        available = SUBMISSION_WORKFLOW.get_available_transitions(
            submission.status, readonly,
        )
        self.assertEqual(available, [])

    def test_readonly_cannot_submit(self):
        readonly = make_user('readonly', role='purser_readonly')
        submission = self.make_submission()
        with self.assertRaises(PermissionDenied):
            SUBMISSION_WORKFLOW.execute(submission, 'submitted', user=readonly)

    def test_admin_can_do_everything(self):
        admin = make_user('admin', role='purser_admin')
        submission = self.make_submission()
        for target in ('submitted', 'under_review', 'approved', 'closed'):
            SUBMISSION_WORKFLOW.execute(submission, target, user=admin)
            submission.refresh_from_db()
            self.assertEqual(submission.status, target)

    def test_superuser_bypasses_role_check(self):
        root = make_user('root', is_superuser=True)
        submission = self.make_submission(Submission.Status.APPROVED)
        SUBMISSION_WORKFLOW.execute(submission, 'closed', user=root)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'closed')

    def test_available_transitions_filtered_per_role(self):
        submitter = make_user('submitter', role='purser_submitter')
        reviewer = make_user('reviewer', role='purser_reviewer')

        draft_for_submitter = SUBMISSION_WORKFLOW.get_available_transitions(
            'draft', submitter,
        )
        self.assertEqual([t.to_status for t in draft_for_submitter], ['submitted'])

        draft_for_reviewer = SUBMISSION_WORKFLOW.get_available_transitions(
            'draft', reviewer,
        )
        self.assertEqual(draft_for_reviewer, [])

        review_for_reviewer = SUBMISSION_WORKFLOW.get_available_transitions(
            'under_review', reviewer,
        )
        self.assertEqual(
            sorted(t.to_status for t in review_for_reviewer),
            ['approved', 'revision_requested'],
        )


class ComplianceWorkflowTests(TestCase):
    """The compliance deadline workflow used by ComplianceItem."""

    def test_pending_can_go_overdue(self):
        # 'any' role — deadline-passed tick runs without a user
        self.assertTrue(COMPLIANCE_WORKFLOW.can_transition('pending', 'overdue'))

    def test_overdue_can_still_be_submitted_late(self):
        submitter = make_user('sub', role='purser_submitter')
        self.assertTrue(
            COMPLIANCE_WORKFLOW.can_transition('overdue', 'submitted', submitter)
        )

    def test_reject_requires_comment(self):
        officer = make_user('officer', role='purser_compliance_officer')
        item = ComplianceItem(status='under_review', label='Q3', due_date=date(2026, 4, 15))
        with self.assertRaises(ValidationError):
            COMPLIANCE_WORKFLOW.execute(item, 'rejected', user=officer, comment='', save=False)

    def test_waive_requires_admin(self):
        officer = make_user('officer', role='purser_compliance_officer')
        item = ComplianceItem(status='overdue', label='Q3', due_date=date(2026, 4, 15))
        with self.assertRaises(PermissionDenied):
            COMPLIANCE_WORKFLOW.execute(
                item, 'waived', user=officer, comment='unable to comply', save=False,
            )

    def test_waive_allowed_for_admin_with_comment(self):
        admin = make_user('admin', role='purser_admin')
        item = ComplianceItem(status='overdue', label='Q3', due_date=date(2026, 4, 15))
        COMPLIANCE_WORKFLOW.execute(
            item, 'waived', user=admin, comment='hardship waiver approved', save=False,
        )
        self.assertEqual(item.status, 'waived')

    def test_rejected_item_can_be_resubmitted(self):
        submitter = make_user('sub', role='purser_submitter')
        self.assertTrue(
            COMPLIANCE_WORKFLOW.can_transition('rejected', 'pending', submitter)
        )

    def test_officer_can_accept(self):
        officer = make_user('officer', role='purser_compliance_officer')
        item = ComplianceItem(status='under_review', label='Q3', due_date=date(2026, 4, 15))
        COMPLIANCE_WORKFLOW.execute(item, 'accepted', user=officer, save=False)
        self.assertEqual(item.status, 'accepted')

    def test_cannot_accept_from_pending(self):
        officer = make_user('officer', role='purser_compliance_officer')
        item = ComplianceItem(status='pending', label='Q3', due_date=date(2026, 4, 15))
        with self.assertRaises(ValidationError):
            COMPLIANCE_WORKFLOW.execute(item, 'accepted', user=officer, save=False)


class ClosePackageAggregationTests(SubmissionWorkflowFixture):
    """generate_close_package aggregates only approved/closed submissions."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.disb = ReportLineItem.objects.create(
            schema=cls.schema, code='DISB', label='Disbursements',
            data_type=ReportLineItem.DataType.CURRENCY,
        )
        cls.second_program = Program.objects.create(
            name='Small Business Express',
            code='SBX',
            program_type=Program.ProgramType.GRANT,
            report_schema=cls.schema,
        )

    def _make_approved_submission(self, program, amount):
        sub = Submission.objects.create(
            program=program,
            fiscal_period=self.period,
            status=Submission.Status.APPROVED,
        )
        SubmissionLineValue.objects.create(
            submission=sub, line_item=self.disb,
            numeric_value=Decimal(amount),
        )
        return sub

    def test_aggregates_approved_submissions_across_programs(self):
        self._make_approved_submission(self.program, '10000.00')
        self._make_approved_submission(self.second_program, '5000.00')

        package = generate_close_package(self.period)
        grant_totals = package.aggregated_data['Grant']['DISB']
        self.assertEqual(grant_totals['total'], 15000.0)
        self.assertEqual(grant_totals['programs'], {'MAA': 10000.0, 'SBX': 5000.0})

    def test_package_complete_when_all_programs_approved(self):
        self._make_approved_submission(self.program, '10000.00')
        self._make_approved_submission(self.second_program, '5000.00')

        package = generate_close_package(self.period)
        self.assertEqual(package.status, ClosePackage.Status.COMPLETE)

    def test_package_stays_draft_if_any_submission_unapproved(self):
        self._make_approved_submission(self.program, '10000.00')
        # Second program only submitted, not approved
        Submission.objects.create(
            program=self.second_program,
            fiscal_period=self.period,
            status=Submission.Status.SUBMITTED,
        )

        package = generate_close_package(self.period)
        self.assertEqual(package.status, ClosePackage.Status.DRAFT)

    def test_draft_submissions_excluded_from_aggregation(self):
        Submission.objects.create(
            program=self.program,
            fiscal_period=self.period,
            status=Submission.Status.DRAFT,
        )
        package = generate_close_package(self.period)
        self.assertEqual(package.aggregated_data, {})

    def test_inactive_programs_ignored_for_completeness(self):
        # Only the first program is active → a single approved submission
        # is enough to mark the package complete.
        self.second_program.is_active = False
        self.second_program.save()
        self._make_approved_submission(self.program, '10000.00')

        package = generate_close_package(self.period)
        self.assertEqual(package.status, ClosePackage.Status.COMPLETE)


class BudgetBaselineTests(SubmissionWorkflowFixture):
    """Monthly spread uniqueness and shape — used for variance analysis."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.line = ReportLineItem.objects.create(
            schema=cls.schema, code='DISB', label='Disbursements',
        )

    def test_baseline_is_unique_per_program_year_line(self):
        BudgetBaseline.objects.create(
            program=self.program,
            fiscal_year=self.year,
            line_item=self.line,
            annual_amount=Decimal('600000.00'),
            monthly_spread={str(m): 50000 for m in range(1, 13)},
        )
        with self.assertRaises(Exception):
            BudgetBaseline.objects.create(
                program=self.program,
                fiscal_year=self.year,
                line_item=self.line,
                annual_amount=Decimal('700000.00'),
            )
