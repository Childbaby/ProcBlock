"""
MedChain – Data Models
======================
Design constraints
------------------
* NO personally-identifiable information is stored in any field.
* Document content never touches the database; only its SHA-256 hash is persisted.
* The SyncQueue model decouples on-chain writes from API responses (Celery handles them).
"""
import re
from django.db import models
from django.core.exceptions import ValidationError


# ── Validators ────────────────────────────────────────────────────────────────

def validate_sha256(value: str) -> None:
    """Ensure the stored hash is a valid 64-character hex string (SHA-256)."""
    if not re.fullmatch(r"[a-f0-9]{64}", value.lower()):
        raise ValidationError(
            "document_hash must be a 64-character lowercase hex string (SHA-256)."
        )


def validate_positive(value: int) -> None:
    if value <= 0:
        raise ValidationError("Quantity must be a positive integer.")


# ── Core medicine catalogue ───────────────────────────────────────────────────

class MedicineRecord(models.Model):
    """
    Represents a single medicine SKU in the national procurement ledger.
    Stores only logistics-relevant, non-PII attributes.
    """

    class StockStatus(models.TextChoices):
        ADEQUATE = "ADEQUATE", "Adequate"
        LOW = "LOW", "Low"
        CRITICAL = "CRITICAL", "Critical"
        OUT_OF_STOCK = "OUT_OF_STOCK", "Out of Stock"

    # Identity
    drug_name = models.CharField(max_length=255, db_index=True)
    batch_number = models.CharField(max_length=64, unique=True)
    atc_code = models.CharField(
        max_length=10,
        blank=True,
        help_text="WHO Anatomical Therapeutic Chemical classification code",
    )

    # Quantities
    quantity = models.PositiveIntegerField(validators=[validate_positive])
    unit_of_measure = models.CharField(max_length=32, default="units")  # e.g. tablets, ml

    # Supply-chain metadata (non-PII)
    facility_code = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Anonymous facility identifier – not linked to staff names",
    )
    district_code = models.CharField(max_length=16, blank=True)
    expiry_date = models.DateField()
    received_date = models.DateField(auto_now_add=True)

    # Blockchain anchor
    document_hash = models.CharField(
        max_length=64,
        unique=True,
        validators=[validate_sha256],
        help_text="SHA-256 hex digest of the procurement PDF – stored on Solana",
    )
    on_chain_signature = models.CharField(
        max_length=128,
        blank=True,
        help_text="Solana transaction signature once the hash is confirmed on-chain",
    )
    is_synced = models.BooleanField(default=False, db_index=True)

    # Stock health
    stock_status = models.CharField(
        max_length=16,
        choices=StockStatus.choices,
        default=StockStatus.ADEQUATE,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["drug_name", "facility_code"]),
            models.Index(fields=["is_synced"]),
        ]

    def __str__(self) -> str:
        return f"{self.drug_name} | batch {self.batch_number}"

    @property
    def is_expired(self) -> bool:
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()


# ── Blockchain sync queue (NFR-03 Burst Sync) ────────────────────────────────

class BlockchainSyncQueue(models.Model):
    """
    Queues medicine records that have not yet been written to Solana.
    Celery workers drain this table whenever connectivity allows.
    """

    class SyncStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        CONFIRMED = "CONFIRMED", "Confirmed"
        FAILED = "FAILED", "Failed"

    medicine = models.OneToOneField(
        MedicineRecord,
        on_delete=models.CASCADE,
        related_name="sync_entry",
    )
    status = models.CharField(
        max_length=16,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
        db_index=True,
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    queued_at = models.DateTimeField(auto_now_add=True)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["queued_at"]

    def __str__(self) -> str:
        return f"SyncQueue[{self.medicine.batch_number}] – {self.status}"


# ── Audit log (immutable, append-only) ───────────────────────────────────────

class AuditEvent(models.Model):
    """
    Append-only log of significant system events.
    No user names or identifiers – only action codes and references.
    """

    class EventType(models.TextChoices):
        RECORD_CREATED = "RECORD_CREATED", "Record Created"
        RECORD_UPDATED = "RECORD_UPDATED", "Record Updated"
        SYNC_QUEUED = "SYNC_QUEUED", "Sync Queued"
        SYNC_CONFIRMED = "SYNC_CONFIRMED", "Sync Confirmed"
        SYNC_FAILED = "SYNC_FAILED", "Sync Failed"
        PII_STRIPPED = "PII_STRIPPED", "PII Stripped from Request"

    event_type = models.CharField(max_length=32, choices=EventType.choices, db_index=True)
    medicine_batch = models.CharField(max_length=64, blank=True)  # denormalised ref
    detail = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def save(self, *args, **kwargs):
        # Enforce immutability: existing records cannot be modified
        if self.pk:
            raise ValidationError("AuditEvent records are immutable.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.event_type} @ {self.timestamp:%Y-%m-%d %H:%M:%S}"
