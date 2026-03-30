"""Close package generation — aggregation, variance analysis."""
import logging
from decimal import Decimal

from purser.models import ClosePackage, Submission, BudgetBaseline

logger = logging.getLogger(__name__)


def generate_close_package(period):
    """Aggregate all approved submissions into a close package."""
    package, created = ClosePackage.objects.get_or_create(
        fiscal_period=period,
    )

    submissions = Submission.objects.filter(
        fiscal_period=period,
        status__in=['approved', 'closed'],
    ).select_related('program')

    # Aggregate data by program type and line item
    aggregated = {}
    for sub in submissions:
        prog_type = sub.program.get_program_type_display()
        if prog_type not in aggregated:
            aggregated[prog_type] = {}

        for val in sub.line_values.select_related('line_item'):
            code = val.line_item.code
            amount = float(val.numeric_value or 0)
            if code not in aggregated[prog_type]:
                aggregated[prog_type][code] = {
                    'label': val.line_item.label,
                    'total': 0,
                    'programs': {},
                }
            aggregated[prog_type][code]['total'] += amount
            aggregated[prog_type][code]['programs'][sub.program.code] = amount

    package.aggregated_data = aggregated

    # Check if all programs have approved submissions
    from purser.models import Program
    active_programs = Program.objects.filter(is_active=True).count()
    approved_count = submissions.count()

    if approved_count >= active_programs and active_programs > 0:
        package.status = 'complete'
    else:
        package.status = 'draft'

    package.save()
    logger.info("Generated close package for %s", period.label)
    return package
