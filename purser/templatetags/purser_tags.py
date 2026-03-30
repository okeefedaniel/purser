from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key in templates."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def currency(value):
    """Format a number as currency."""
    if value is None:
        return '—'
    try:
        return f'${float(value):,.2f}'
    except (ValueError, TypeError):
        return str(value)


STATUS_COLORS = {
    'draft': 'secondary',
    'submitted': 'info',
    'under_review': 'warning',
    'revision_requested': 'danger',
    'approved': 'success',
    'closed': 'dark',
    'upcoming': 'light',
    'pending': 'info',
    'overdue': 'danger',
    'accepted': 'success',
    'rejected': 'danger',
    'waived': 'secondary',
    'open': 'primary',
    'submissions_due': 'warning',
    'complete': 'success',
    'signing': 'info',
    'signed': 'success',
    'published': 'dark',
}


@register.filter
def status_color(status):
    """Return Bootstrap color class for a status."""
    return STATUS_COLORS.get(status, 'secondary')
