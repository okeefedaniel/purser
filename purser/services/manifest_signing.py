"""Send close packages to Manifest for formal sign-off.

Thin wrapper over ``keel.signatures.client.send_to_manifest`` so purser
conforms to the suite-wide Project Lifecycle roundtrip contract (see
``keel/CLAUDE.md`` → "Project Lifecycle Standard"):

  1. Outbound: write a ``ManifestHandoff`` row, best-effort POST to
     Manifest, surface failures in the UI without blocking the caller.
  2. Inbound: Manifest POSTs to ``/keel/signatures/webhook/`` on
     completion; ``keel.signatures`` fires ``packet_approved``.
  3. Receiver (``purser.signals``): attaches the signed PDF to the
     ClosePackage as a ``ClosePackageAttachment(source=MANIFEST_SIGNED)``
     and transitions ``ClosePackage.status`` to ``SIGNED``.

A local-sign fallback is available via
``keel.signatures.client.local_sign`` for standalone deployments where
Manifest isn't configured — fires the same signal so the source
object's status and attachment collection end up identical.
"""
from __future__ import annotations

import logging

from django.urls import reverse

from keel.signatures.client import (
    is_available as manifest_is_available,
    local_sign as _local_sign,
    send_to_manifest as _send_to_manifest,
)
from keel.signatures.models import ManifestHandoff

logger = logging.getLogger(__name__)


def is_available() -> bool:
    """True when Manifest is configured for this deployment."""
    return manifest_is_available()


def send_to_manifest(close_package, request=None, signers=None, created_by=None):
    """Create a Manifest signing session for the close package.

    Args:
        close_package: The ``ClosePackage`` to route for signing. Must
            have a ``pdf_export`` file; the PDF's URL is passed to
            Manifest as the document to sign.
        request: Optional Django ``HttpRequest`` used to build the
            absolute callback URL. When omitted, no callback is sent
            and Manifest completion will have to be reconciled via
            polling or admin action.
        signers: Optional list of ``[{'email': ..., 'name': ...}]``
            dicts. Defaults to an empty list — Manifest will require
            signers to be added through its own UI in that case.
        created_by: User initiating the handoff.

    Returns:
        The ``ManifestHandoff`` row (status will be ``SENT`` on success,
        ``FAILED`` on outbound network error).
    """
    if not close_package.pdf_export:
        raise ValueError('Close package must have a PDF export before signing')

    callback_url = None
    if request is not None:
        callback_url = request.build_absolute_uri(
            reverse('keel_signatures:webhook'),
        )

    handoff = _send_to_manifest(
        source_obj=close_package,
        packet_label=f'{close_package.fiscal_period.label} Close Package',
        signers=signers or [],
        attachment_model='purser.ClosePackageAttachment',
        attachment_fk_name='close_package',
        on_approved_status='signed',
        initial_document_url=close_package.pdf_export.url,
        created_by=created_by,
        callback_url=callback_url,
    )

    # Flip the close-package state to SIGNING on successful outbound.
    # On FAILED, leave the prior state alone so the user can retry.
    # The legacy ClosePackage.manifest_signing_id field is not updated
    # here — ManifestHandoff is now the canonical link and querying
    # via that table is the recommended pattern (see signals.py).
    if handoff.status == ManifestHandoff.Status.SENT:
        close_package.status = 'signing'
        close_package.save(update_fields=['status', 'updated_at'])

    logger.info(
        'Close package %s handoff %s → %s',
        close_package.pk, handoff.pk, handoff.get_status_display(),
    )
    return handoff


def local_sign(close_package, signed_pdf, created_by=None):
    """Standalone-mode fallback for signing a close package locally.

    Records a ``ManifestHandoff`` with ``status=LOCAL_SIGNED`` and fires
    the same ``packet_approved`` signal the real Manifest roundtrip
    does, so the close-package status and attachment collection end up
    identical whether or not Manifest is deployed.
    """
    if not close_package.pdf_export:
        raise ValueError('Close package must have a PDF export before signing')

    handoff = _local_sign(
        source_obj=close_package,
        signed_pdf=signed_pdf,
        attachment_model='purser.ClosePackageAttachment',
        attachment_fk_name='close_package',
        on_approved_status='signed',
        packet_label=f'{close_package.fiscal_period.label} Close Package (local)',
        created_by=created_by,
    )
    return handoff
