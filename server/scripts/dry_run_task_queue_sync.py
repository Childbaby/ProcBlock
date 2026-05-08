from __future__ import annotations

import hashlib
import os
import sys
import time
from datetime import date
from pathlib import Path
from uuid import uuid4

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


def configure_environment() -> None:
    # Use the project settings and provide sensible local defaults for dry-run execution.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_task_dry_run")
    os.environ.setdefault("SECRET_KEY", "dry-run-secret-key")
    os.environ.setdefault("DB_HOST", "127.0.0.1")
    os.environ.setdefault("DB_PORT", "5432")
    os.environ.setdefault("DB_NAME", "medchain")
    os.environ.setdefault("DB_USER", "postgres")
    os.environ.setdefault("DB_PASSWORD", "postgres")

    # Force anchor path for this verification lane.
    os.environ.setdefault("SOLANA_BRIDGE_MODE", "anchor")
    os.environ.setdefault("SOLANA_ALLOW_MEMO_FALLBACK", "False")
    os.environ.setdefault("SOLANA_RPC_URL", "http://127.0.0.1:8899")
    os.environ.setdefault("SOLANA_PROGRAM_ID", "8had5koATJfLWrZ5yMrnSsQ5Ssc5aW4EWNtwrHzb4Prz")
    os.environ.setdefault("SOLANA_HUB_CODE", "ZMHUB001")
    os.environ.setdefault("SOLANA_MEDICINE_CODE_PREFIX", "MED")
    os.environ.setdefault(
        "SOLANA_PAYER_KEYPAIR_PATH",
        os.path.join(os.path.expanduser("~"), ".config", "solana", "id.json"),
    )


def reset_dry_run_database() -> None:
    db_path = SERVER_ROOT / "task-dry-run.sqlite3"
    if db_path.exists():
        db_path.unlink()


def ensure_rpc_is_progressing() -> None:
    from solana.rpc.api import Client

    rpc_url = os.environ["SOLANA_RPC_URL"]
    client = Client(rpc_url)

    previous_slot = client.get_slot(commitment="processed").value
    for _ in range(5):
        time.sleep(2)
        current_slot = client.get_slot(commitment="processed").value
        if current_slot > previous_slot:
            return
        previous_slot = current_slot

    raise RuntimeError(
        f"Validator at {rpc_url} is reachable but slot is not advancing. "
        "Restart the validator and retry."
    )


def ensure_schema() -> None:
    from django.core.management import call_command

    # App has no migration package yet; run_syncdb creates unmanaged app tables.
    call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)


def run_task_queue_sync_dry_run() -> dict:
    from celery import current_app
    from app.models import BlockchainSyncQueue, MedicineRecord
    from app.tasks import flush_pending_syncs

    token = uuid4().hex[:12].upper()
    batch_number = f"TASK-DRYRUN-{token}"
    document_hash = hashlib.sha256(f"task-dry-run-{token}".encode("utf-8")).hexdigest()

    record = MedicineRecord.objects.create(
        drug_name="Task Queue Dry Run Vaccine",
        batch_number=batch_number,
        atc_code="J07BX",
        quantity=240,
        unit_of_measure="units",
        facility_code="FAC-TASK-DRYRUN",
        district_code="DSTRY",
        expiry_date=date(2027, 12, 31),
        document_hash=document_hash,
    )
    BlockchainSyncQueue.objects.create(medicine=record)

    # Make celery delay/apply_async execute inline for deterministic dry-run behavior.
    current_app.conf.task_always_eager = True
    current_app.conf.task_eager_propagates = True

    flush_result = flush_pending_syncs.delay()
    flush_payload = flush_result.get(timeout=180)

    record.refresh_from_db()
    queue_entry = BlockchainSyncQueue.objects.get(medicine_id=record.id)

    if not record.is_synced:
        raise RuntimeError("Record did not reach is_synced=True")
    if not record.on_chain_signature:
        raise RuntimeError("Record is synced but on_chain_signature is empty")
    if queue_entry.status != BlockchainSyncQueue.SyncStatus.CONFIRMED:
        raise RuntimeError(f"Unexpected queue status: {queue_entry.status}")

    return {
        "medicine_id": record.id,
        "batch_number": record.batch_number,
        "signature": record.on_chain_signature,
        "queue_status": queue_entry.status,
        "flush_queued": flush_payload.get("queued", 0),
    }


def main() -> None:
    configure_environment()
    ensure_rpc_is_progressing()
    reset_dry_run_database()

    import django

    django.setup()
    ensure_schema()

    outcome = run_task_queue_sync_dry_run()

    print("TASK_QUEUE_DRY_RUN_OK")
    print(f"medicine_id={outcome['medicine_id']}")
    print(f"batch_number={outcome['batch_number']}")
    print(f"signature={outcome['signature']}")
    print(f"queue_status={outcome['queue_status']}")
    print(f"flush_queued={outcome['flush_queued']}")


if __name__ == "__main__":
    main()
