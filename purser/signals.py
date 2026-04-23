"""Manifest roundtrip receiver for ClosePackage.

When a ``ManifestHandoff`` completes — via the inbound Manifest webhook
at ``/keel/signatures/webhook/`` or via
``keel.signatures.client.local_sign`` standalone fallback —
``keel.signatures`` fires ``packet_approved``. This receiver:

  1. Writes the signed PDF to the ClosePackage's ``attachments``
     collection as a ``ClosePackageAttachment(source=MANIFEST_SIGNED)``
     with ``manifest_packet_uuid`` filled in.
  2. Transitions ``ClosePackage.status`` to the handoff's
     ``on_approved_status`` (``'signed'``) — ClosePackage doesn't use
     WorkflowEngine today, so the receiver updates the field directly.

Downstream receivers (e.g. Helm publish) can attach to the same signal
independently.
"""
import logging

from django.apps import apps
from django.core.files.base import ContentFile
from django.dispatch import receiver

from keel.signatures.signals import packet_approved

logger = logging.getLogger(__name__)


@receiver(packet_approved)
def on_packet_approved(sender, handoff, source_obj, signed_pdf, **kwargs):
    """File the signed PDF on the close package + transition status."""
    if not hasattr(source_obj, '_meta'):
        return
    if source_obj._meta.label_lower != 'purser.closepackage':
        return

    try:
        attachment_cls = apps.get_model(*handoff.attachment_model.split('.'))
    except (LookupError, ValueError):
        logger.exception(
            'Unknown attachment model %r on handoff %s',
            handoff.attachment_model, handoff.pk,
        )
        return

    if hasattr(signed_pdf, 'read'):
        raw = signed_pdf.read()
        filename = (
            getattr(signed_pdf, 'name', None)
            or f'{handoff.packet_label or "signed"}.pdf'
        )
    else:
        raw = bytes(signed_pdf)
        filename = f'{handoff.packet_label or "signed"}.pdf'
    filename = filename.rsplit('/', 1)[-1] or 'signed.pdf'

    attachment_cls.objects.create(
        **{handoff.attachment_fk_name: source_obj},
        file=ContentFile(raw, name=filename),
        filename=filename,
        content_type='application/pdf',
        size_bytes=len(raw),
        description=handoff.packet_label or 'Signed close package via Manifest',
        visibility='internal',
        source='manifest_signed',
        manifest_packet_uuid=handoff.manifest_packet_uuid,
        uploaded_by=handoff.created_by,
    )

    target = handoff.on_approved_status or 'signed'
    if source_obj.status != target:
        source_obj.status = target
        try:
            source_obj.save(update_fields=['status', 'updated_at'])
        except Exception:
            logger.exception(
                'Failed to transition ClosePackage %s → %s after handoff %s',
                source_obj.pk, target, handoff.pk,
            )
