"""
ProcBase – Celery Tasks
========================
NFR-03 Burst Sync: tasks queue blockchain writes and flush them
when connectivity is restored, with exponential back-off.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("procbase.tasks")


# ── Blockchain sync ───────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=8,
    default_retry_delay=30,      # seconds; doubles on each retry
    acks_late=True,
    name="app.tasks.sync_record_to_blockchain",
)
def sync_record_to_blockchain(self, medicine_id: int) -> dict:
    """
    Submit a MedicineRecord's document_hash to Solana and update the
    local sync queue entry.

    Retry schedule (exponential back-off):
      attempt 1 →  30 s
      attempt 2 →  60 s
      attempt 3 → 120 s  …up to 8 retries (~64 min total)
    """
    from app.models import MedicineRecord, BlockchainSyncQueue, AuditEvent
    from blockchain.solana_bridge import get_bridge

    try:
        record = MedicineRecord.objects.select_related("sync_entry").get(pk=medicine_id)
    except MedicineRecord.DoesNotExist:
        logger.error("sync_record_to_blockchain: MedicineRecord %d not found", medicine_id)
        return {"status": "not_found"}

    # Ensure a queue entry exists
    queue_entry, _ = BlockchainSyncQueue.objects.get_or_create(medicine=record)
    queue_entry.status = BlockchainSyncQueue.SyncStatus.IN_PROGRESS
    queue_entry.attempts += 1
    queue_entry.last_attempted_at = timezone.now()
    queue_entry.save(update_fields=["status", "attempts", "last_attempted_at"])

    bridge = get_bridge()

    try:
        signature = bridge.submit_record(record)
        confirmed = bridge.confirm(signature)

        if confirmed:
            record.on_chain_signature = signature
            record.is_synced = True
            record.save(update_fields=["on_chain_signature", "is_synced"])

            queue_entry.status = BlockchainSyncQueue.SyncStatus.CONFIRMED
            queue_entry.confirmed_at = timezone.now()
            queue_entry.save(update_fields=["status", "confirmed_at"])

            AuditEvent.objects.create(
                event_type=AuditEvent.EventType.SYNC_CONFIRMED,
                medicine_batch=record.batch_number,
                detail={"signature": signature, "attempt": queue_entry.attempts},
            )

            logger.info(
                "Blockchain sync confirmed | batch=%s sig=%s",
                record.batch_number,
                signature,
            )
            return {"status": "confirmed", "signature": signature}

        else:
            raise RuntimeError("Transaction submitted but not confirmed.")

    except Exception as exc:
        queue_entry.status = BlockchainSyncQueue.SyncStatus.FAILED
        queue_entry.last_error = str(exc)
        queue_entry.save(update_fields=["status", "last_error"])

        AuditEvent.objects.create(
            event_type=AuditEvent.EventType.SYNC_FAILED,
            medicine_batch=record.batch_number,
            detail={"error": str(exc), "attempt": queue_entry.attempts},
        )

        logger.warning(
            "Sync failed for batch=%s (attempt %d): %s",
            record.batch_number,
            queue_entry.attempts,
            exc,
        )

        # Retry with exponential back-off
        raise self.retry(
            exc=exc,
            countdown=30 * (2 ** self.request.retries),
        )


@shared_task(name="app.tasks.flush_pending_syncs")
def flush_pending_syncs() -> dict:
    """
    Periodic task: find all PENDING or FAILED queue entries and
    re-dispatch their sync tasks.
    Beat schedule: every 5 minutes via Celery Beat (configure in settings).

    This is the "burst sync" engine for NFR-03.
    """
    from app.models import BlockchainSyncQueue

    pending = BlockchainSyncQueue.objects.filter(
        status__in=[
            BlockchainSyncQueue.SyncStatus.PENDING,
            BlockchainSyncQueue.SyncStatus.FAILED,
        ],
        attempts__lt=8,  # don't retry permanently failed records
    ).select_related("medicine")

    count = 0
    for entry in pending:
        sync_record_to_blockchain.delay(entry.medicine_id)
        count += 1

    logger.info("flush_pending_syncs: queued %d records", count)
    return {"queued": count}


# ── PII audit logging ─────────────────────────────────────────────────────────

@shared_task(name="app.tasks.log_pii_strip_event")
def log_pii_strip_event(path: str, method: str) -> None:
    """
    Write an AuditEvent when the privacy middleware detects and strips PII.
    Runs async so it doesn't slow down the inbound request.
    """
    from app.models import AuditEvent

    AuditEvent.objects.create(
        event_type=AuditEvent.EventType.PII_STRIPPED,
        detail={"path": path, "method": method},
    )
