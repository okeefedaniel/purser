"""Send close packages to Manifest for formal sign-off."""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_to_manifest(close_package):
    """Create a Manifest signing session for the close package."""
    if not close_package.pdf_export:
        raise ValueError("Close package must have a PDF export before signing")

    manifest_url = getattr(settings, 'MANIFEST_API_URL', 'https://manifest.docklabs.ai')
    headers = {
        'Authorization': f'Bearer {settings.KEEL_API_KEY}',
        'Content-Type': 'application/json',
    }

    payload = {
        'document_url': close_package.pdf_export.url,
        'title': f'{close_package.fiscal_period.label} Close Package',
        'callback_url': f'{settings.KEEL_API_URL}/purser/api/webhooks/manifest/',
        'callback_event': 'signing.completed',
    }

    response = requests.post(
        f'{manifest_url}/api/signing-sessions/',
        json=payload,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    close_package.status = 'signing'
    close_package.manifest_signing_id = data['id']
    close_package.save(update_fields=['status', 'manifest_signing_id', 'updated_at'])

    logger.info("Sent close package %s to Manifest", close_package.pk)
    return data
