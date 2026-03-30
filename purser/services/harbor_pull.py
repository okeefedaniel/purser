"""Pull fiscal activity data from Harbor to pre-fill Purser submissions."""
import logging

import requests
from django.conf import settings

from keel.reporting.models import ReportLineItem
from purser.models import Program, Submission, SubmissionLineValue

logger = logging.getLogger(__name__)

# Maps Harbor API field names to report line item codes
FIELD_MAP = {
    'beginning_balance': 'BEG_BAL',
    'new_obligations': 'OBLIG',
    'disbursements': 'DISB',
    'deobligations': 'DEOBLIG',
    'recaptured_funds': 'RECAP',
    'applications_received': 'APPS_RECV',
    'applications_approved': 'APPS_APPR',
    'jobs_committed': 'JOBS_COMMIT',
    'jobs_verified': 'JOBS_VERIFY',
}


def pull_from_harbor(program, period):
    """Pre-fill a Purser submission from Harbor's fiscal activity data.

    The submitter reviews the auto-filled data and clicks Submit.
    They don't have to enter anything from scratch — just verify.
    """
    if not program.pulls_from_harbor or not program.harbor_api_endpoint:
        raise ValueError(f"{program.code} is not configured for Harbor pull")

    url = program.harbor_api_endpoint.rstrip('/')
    params = {
        'program_code': program.code,
        'period_start': period.start_date.isoformat(),
        'period_end': period.end_date.isoformat(),
    }
    headers = {
        'Authorization': f'Bearer {settings.KEEL_API_KEY}',
    }

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    activity = response.json()

    submission, created = Submission.objects.get_or_create(
        program=program, fiscal_period=period,
        defaults={'source': 'harbor_pull', 'status': 'draft'},
    )

    for api_field, line_code in FIELD_MAP.items():
        value = activity.get(api_field)
        if value is not None:
            try:
                line_item = program.report_schema.line_items.get(code=line_code)
            except ReportLineItem.DoesNotExist:
                logger.warning(
                    "Line item %s not found in schema %s",
                    line_code, program.report_schema.slug,
                )
                continue

            SubmissionLineValue.objects.update_or_create(
                submission=submission, line_item=line_item,
                defaults={'numeric_value': value},
            )

    logger.info("Pulled Harbor data for %s / %s", program.code, period.label)
    return submission
