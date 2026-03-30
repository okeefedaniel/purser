"""Purser workflow definitions using Keel's WorkflowEngine."""
from keel.core.workflow import Transition, WorkflowEngine


SUBMISSION_WORKFLOW = WorkflowEngine([
    Transition(
        'draft', 'submitted',
        roles=['purser_submitter', 'purser_admin'],
        label='Submit',
        description='Submit monthly report for review',
    ),
    Transition(
        'submitted', 'under_review',
        roles=['purser_reviewer', 'purser_admin'],
        label='Begin Review',
    ),
    Transition(
        'under_review', 'revision_requested',
        roles=['purser_reviewer', 'purser_admin'],
        label='Request Revision',
        require_comment=True,
    ),
    Transition(
        'under_review', 'approved',
        roles=['purser_reviewer', 'purser_admin'],
        label='Approve',
    ),
    Transition(
        'revision_requested', 'draft',
        roles=['purser_submitter', 'purser_admin'],
        label='Revise',
    ),
    Transition(
        'approved', 'closed',
        roles=['purser_admin'],
        label='Close',
    ),
])


COMPLIANCE_WORKFLOW = WorkflowEngine([
    Transition(
        'upcoming', 'pending',
        roles=['any'],
        label='Due Soon',
    ),
    Transition(
        'pending', 'submitted',
        roles=['external_submitter', 'purser_submitter', 'purser_admin'],
        label='Submit',
    ),
    Transition(
        'overdue', 'submitted',
        roles=['external_submitter', 'purser_submitter', 'purser_admin'],
        label='Submit (Late)',
    ),
    Transition(
        'submitted', 'under_review',
        roles=['purser_compliance_officer', 'purser_admin'],
        label='Review',
    ),
    Transition(
        'under_review', 'accepted',
        roles=['purser_compliance_officer', 'purser_admin'],
        label='Accept',
    ),
    Transition(
        'under_review', 'rejected',
        roles=['purser_compliance_officer', 'purser_admin'],
        label='Reject',
        require_comment=True,
    ),
    Transition(
        'rejected', 'pending',
        roles=['external_submitter', 'purser_submitter'],
        label='Resubmit',
    ),
    Transition(
        'pending', 'overdue',
        roles=['any'],
        label='Mark Overdue',
    ),
    Transition(
        'pending', 'waived',
        roles=['purser_admin'],
        label='Waive',
        require_comment=True,
    ),
    Transition(
        'overdue', 'waived',
        roles=['purser_admin'],
        label='Waive',
        require_comment=True,
    ),
])
