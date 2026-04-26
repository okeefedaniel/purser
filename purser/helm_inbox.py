"""Purser's /api/v1/helm-feed/inbox/ endpoint — per-user submission inbox.

Items where the requesting user is the gating reviewer right now in
Purser. Submission has no per-record assignee, so the predicate is:

  - Status in {SUBMITTED, UNDER_REVIEW}
  - The user is a member of program.reviewers (M2M)
  - AND either nobody has claimed the review yet (reviewed_by IS NULL)
    OR the user is the one who claimed it (reviewed_by == user)

This intentionally surfaces unclaimed-but-eligible submissions to all
program reviewers — the "ball" is in any reviewer's court until one
claims it. Once claimed, only the claimant sees it as their own work.

Conforms to the UserInbox shape in helm.dashboard.feed_contract.
Auth + cache + sub resolution all come from keel.feed.helm_inbox_view.
"""
from django.conf import settings
from django.db.models import Q
from keel.feed.views import helm_inbox_view

from .helm_feed import _product_url
from .models import Submission


_AWAITING_ME_STATUSES = (
    Submission.Status.SUBMITTED,
    Submission.Status.UNDER_REVIEW,
)


@helm_inbox_view
def purser_helm_feed_inbox(request, user):
    from core.models import Notification

    base_url = _product_url().rstrip('/')
    items = []

    qs = (
        Submission.objects
        .filter(status__in=_AWAITING_ME_STATUSES, program__reviewers=user)
        .filter(Q(reviewed_by__isnull=True) | Q(reviewed_by=user))
        .select_related('program', 'fiscal_period')
        .order_by('submitted_at')
        .distinct()
    )
    for sub in qs:
        program_name = getattr(sub.program, 'name', '') or sub.program.code
        period = getattr(sub.fiscal_period, 'label', '') or ''
        title = f'Review: {program_name}'
        if period:
            title += f' — {period}'
        # If someone else has claimed it, this user shouldn't see it (the
        # filter above already excludes that case, but keep the guard for
        # the type='approval' label).
        type_label = 'review' if sub.reviewed_by_id is None else 'approval'
        items.append({
            'id': str(sub.id),
            'type': type_label,
            'title': title,
            'deep_link': f'{base_url}/purser/review/{sub.pk}/',
            'waiting_since': (sub.submitted_at or sub.created_at).isoformat(),
            'due_date': None,
            'priority': 'normal',
        })

    unread = (
        Notification.objects
        .filter(recipient=user, is_read=False)
        .order_by('-created_at')[:50]
    )
    notifications = []
    for n in unread:
        link = n.link or ''
        if link and base_url and link.startswith('/'):
            link = f'{base_url}{link}'
        notifications.append({
            'id': str(n.id),
            'title': n.title,
            'body': getattr(n, 'message', '') or '',
            'deep_link': link,
            'created_at': n.created_at.isoformat(),
            'priority': (n.priority or 'normal').lower(),
        })

    return {
        'product': getattr(settings, 'KEEL_PRODUCT_CODE', 'purser'),
        'product_label': getattr(settings, 'KEEL_PRODUCT_NAME', 'Purser'),
        'product_url': base_url,
        'user_sub': '',  # filled by decorator
        'items': items,
        'unread_notifications': notifications,
        'fetched_at': '',  # filled by decorator
    }
