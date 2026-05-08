"""
MedChain – Solana Bridge
=========================
Handles all communication with the Solana blockchain.

Responsibilities
----------------
* Submit medicine records to the Anchor program via `create_batch`.
* Keep memo anchoring as an explicit compatibility fallback.
* Confirm a submitted transaction signature.
* Provide a safe no-op stub when Solana credentials are not configured
    (for local development / CI without a funded keypair).

Dependencies
------------
        pip install solana solders
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import struct
from pathlib import Path
from typing import Optional

logger = logging.getLogger("medchain.solana")

SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
ANCHOR_CREATE_BATCH_IX = "create_batch"

# ── Optional import guard ─────────────────────────────────────────────────────
# solana-py is optional in environments that don't need live blockchain access.
try:
    from solana.rpc.api import Client as SolanaClient
    from solana.rpc.types import TxOpts
    from solana.transaction import Transaction
    from solders.instruction import AccountMeta, Instruction
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.signature import Signature
    from spl.memo.instructions import create_memo, MemoParams

    _SOLANA_AVAILABLE = True
except ImportError:
    _SOLANA_AVAILABLE = False
    logger.warning(
        "solana / solders packages not installed. "
        "SolanaBridge will run in STUB mode (no real transactions)."
    )


# ── Bridge class ──────────────────────────────────────────────────────────────

class SolanaBridge:
    """
    Wraps solana-py to provide a simple submit/confirm interface.

    Example::
        bridge = SolanaBridge.from_env()
        sig = bridge.submit_hash("abc123...64hexchars")
        confirmed = bridge.confirm(sig)
    """

    def __init__(
        self,
        rpc_url: str,
        payer: Optional["Keypair"] = None,
        program_id: Optional[str] = None,
        bridge_mode: str = "anchor",
        hub_code: Optional[str] = None,
        medicine_code_prefix: str = "MED",
        allow_memo_fallback: bool = True,
        stub: bool = False,
    ) -> None:
        self.rpc_url = rpc_url
        self.payer = payer
        self.program_id = program_id
        self.bridge_mode = (bridge_mode or "anchor").strip().lower()
        self.hub_code = (hub_code or "").strip().upper() or None
        self.medicine_code_prefix = (medicine_code_prefix or "MED").strip().upper()
        self.allow_memo_fallback = allow_memo_fallback
        self.stub = stub or not _SOLANA_AVAILABLE or payer is None

        if not self.stub:
            self._client = SolanaClient(rpc_url)
            logger.info(
                "SolanaBridge initialised | rpc=%s mode=%s",
                rpc_url,
                self.bridge_mode,
            )
        else:
            logger.info("SolanaBridge running in STUB mode – no real transactions.")

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_env(cls) -> "SolanaBridge":
        """Build a bridge instance from Django settings / environment variables."""
        from django.conf import settings

        rpc_url = getattr(settings, "SOLANA_RPC_URL", "https://api.devnet.solana.com")
        program_id = getattr(settings, "SOLANA_PROGRAM_ID", "") or None
        bridge_mode = getattr(settings, "SOLANA_BRIDGE_MODE", "anchor")
        hub_code = getattr(settings, "SOLANA_HUB_CODE", "") or None
        medicine_code_prefix = getattr(settings, "SOLANA_MEDICINE_CODE_PREFIX", "MED")
        allow_memo_fallback = getattr(settings, "SOLANA_ALLOW_MEMO_FALLBACK", True)
        keypair_path = getattr(settings, "SOLANA_PAYER_KEYPAIR_PATH", "")

        payer = None
        if keypair_path and Path(keypair_path).exists() and _SOLANA_AVAILABLE:
            try:
                with open(keypair_path) as f:
                    secret = json.load(f)  # Solana CLI JSON format: list of 64 ints
                payer = Keypair.from_bytes(bytes(secret))
                logger.info("Loaded Solana payer: %s", payer.pubkey())
            except Exception as exc:
                logger.error("Failed to load Solana keypair: %s", exc)

        return cls(
            rpc_url=rpc_url,
            payer=payer,
            program_id=program_id,
            bridge_mode=bridge_mode,
            hub_code=hub_code,
            medicine_code_prefix=medicine_code_prefix,
            allow_memo_fallback=allow_memo_fallback,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def submit_hash(self, document_hash: str) -> str:
        """
        Write a 64-character SHA-256 hex digest to Solana as a Memo transaction.

        Returns the transaction signature string.
        Raises RuntimeError on submission failure.
        """
        normalized_hash = self._normalize_hash(document_hash)

        if self.stub:
            stub_sig = f"STUB_{normalized_hash[:16]}_STUBSIG"
            logger.debug("STUB submit_hash → %s", stub_sig)
            return stub_sig

        try:
            memo_ix = create_memo(
                MemoParams(
                    program_id=Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"),
                    signers=[self.payer.pubkey()],
                    message=bytes(normalized_hash, "utf-8"),
                )
            )

            tx = Transaction()
            tx.add(memo_ix)

            resp = self._client.send_transaction(
                tx,
                self.payer,
                opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed"),
            )

            sig = str(resp.value)
            logger.info("Submitted hash to Solana | sig=%s hash=%s", sig, normalized_hash)
            return sig

        except Exception as exc:
            logger.error("Solana submit_hash failed: %s", exc)
            raise RuntimeError(f"Blockchain submission failed: {exc}") from exc

    def submit_record(self, record: object) -> str:
        """
        Submit a medicine record to Solana according to configured bridge mode.

        Modes:
        - anchor: submit `create_batch` instruction to the Anchor program.
        - memo: legacy hash anchoring via Memo transaction.
        """
        document_hash = self._normalize_hash(getattr(record, "document_hash", ""))

        if self.stub:
            return self.submit_hash(document_hash)

        if self.bridge_mode == "memo":
            return self.submit_hash(document_hash)

        if self.bridge_mode != "anchor":
            logger.warning(
                "Unknown SOLANA_BRIDGE_MODE=%s. Falling back to memo path.",
                self.bridge_mode,
            )
            return self.submit_hash(document_hash)

        try:
            batch_code = self._normalize_batch_code(str(getattr(record, "batch_number", "")))
            medicine_code = self._derive_medicine_code(record)
            total_units = int(getattr(record, "quantity", 0))
            if total_units <= 0:
                raise ValueError("quantity must be positive for create_batch")

            batch_id_hash = hashlib.sha256(batch_code.encode("utf-8")).digest()
            document_hash_bytes = bytes.fromhex(document_hash)
            metadata_hash_bytes = self._derive_metadata_hash(record)

            sig = self._submit_create_batch(
                batch_id_hash=batch_id_hash,
                batch_code=batch_code,
                medicine_code=medicine_code,
                total_units=total_units,
                document_hash=document_hash_bytes,
                metadata_hash=metadata_hash_bytes,
            )
            logger.info(
                "Submitted record via Anchor create_batch | sig=%s batch=%s",
                sig,
                batch_code,
            )
            return sig
        except Exception as exc:
            if self.allow_memo_fallback:
                logger.warning(
                    "Anchor submit failed (%s). Falling back to memo path.",
                    exc,
                )
                return self.submit_hash(document_hash)
            raise RuntimeError(f"Anchor submission failed: {exc}") from exc

    def _submit_create_batch(
        self,
        *,
        batch_id_hash: bytes,
        batch_code: str,
        medicine_code: str,
        total_units: int,
        document_hash: bytes,
        metadata_hash: bytes,
    ) -> str:
        if not self.program_id:
            raise ValueError("SOLANA_PROGRAM_ID is required in anchor mode")
        if not self.hub_code:
            raise ValueError("SOLANA_HUB_CODE is required in anchor mode")
        if len(self.hub_code.encode("utf-8")) > 16:
            raise ValueError("SOLANA_HUB_CODE exceeds max on-chain length (16 bytes)")

        program_id = Pubkey.from_string(self.program_id)
        system_program = Pubkey.from_string(SYSTEM_PROGRAM_ID)
        config_pda, _ = Pubkey.find_program_address([b"config"], program_id)
        hub_pda, _ = Pubkey.find_program_address(
            [b"hub", self.hub_code.encode("utf-8")],
            program_id,
        )
        batch_pda, _ = Pubkey.find_program_address([b"batch", batch_id_hash], program_id)

        ix_data = self._encode_create_batch_data(
            batch_id_hash=batch_id_hash,
            batch_code=batch_code,
            medicine_code=medicine_code,
            total_units=total_units,
            document_hash=document_hash,
            metadata_hash=metadata_hash,
        )

        ix_accounts = [
            AccountMeta(config_pda, False, True),
            AccountMeta(hub_pda, False, False),
            AccountMeta(batch_pda, False, True),
            AccountMeta(self.payer.pubkey(), True, True),
            AccountMeta(system_program, False, False),
        ]
        ix = Instruction(program_id, ix_data, ix_accounts)

        tx = Transaction()
        tx.add(ix)

        resp = self._client.send_transaction(
            tx,
            self.payer,
            opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed"),
        )
        return str(resp.value)

    @staticmethod
    def _anchor_discriminator(ix_name: str) -> bytes:
        return hashlib.sha256(f"global:{ix_name}".encode("utf-8")).digest()[:8]

    @staticmethod
    def _borsh_string(value: str) -> bytes:
        encoded = value.encode("utf-8")
        return struct.pack("<I", len(encoded)) + encoded

    def _encode_create_batch_data(
        self,
        *,
        batch_id_hash: bytes,
        batch_code: str,
        medicine_code: str,
        total_units: int,
        document_hash: bytes,
        metadata_hash: bytes,
    ) -> bytes:
        if len(batch_id_hash) != 32:
            raise ValueError("batch_id_hash must be 32 bytes")
        if len(document_hash) != 32:
            raise ValueError("document_hash must be 32 bytes")
        if len(metadata_hash) != 32:
            raise ValueError("metadata_hash must be 32 bytes")

        discriminator = self._anchor_discriminator(ANCHOR_CREATE_BATCH_IX)
        return b"".join(
            [
                discriminator,
                batch_id_hash,
                self._borsh_string(batch_code),
                self._borsh_string(medicine_code),
                struct.pack("<Q", total_units),
                document_hash,
                metadata_hash,
            ]
        )

    @staticmethod
    def _normalize_hash(document_hash: str) -> str:
        normalized = (document_hash or "").strip().lower()
        if len(normalized) != 64:
            raise ValueError(f"Invalid SHA-256 hash length: {document_hash!r}")
        try:
            bytes.fromhex(normalized)
        except ValueError as exc:
            raise ValueError(f"Invalid SHA-256 hash: {document_hash!r}") from exc
        return normalized

    @staticmethod
    def _normalize_batch_code(batch_number: str) -> str:
        batch_code = (batch_number or "").strip()
        if not batch_code:
            raise ValueError("batch_number is required for create_batch")
        if len(batch_code.encode("utf-8")) > 64:
            raise ValueError("batch_number exceeds max on-chain length (64 bytes)")
        return batch_code

    def _derive_medicine_code(self, record: object) -> str:
        atc_code = str(getattr(record, "atc_code", "") or "").strip().upper()
        if atc_code:
            medicine_code = re.sub(r"[^A-Z0-9-]", "", atc_code)
        else:
            drug_name = str(getattr(record, "drug_name", "") or "").strip().upper()
            compact = re.sub(r"[^A-Z0-9]+", "-", drug_name).strip("-")
            if not compact:
                compact = "UNKNOWN"
            medicine_code = f"{self.medicine_code_prefix}-{compact}"

        medicine_code = medicine_code[:32]
        if not medicine_code:
            raise ValueError("medicine_code cannot be empty")
        return medicine_code

    @staticmethod
    def _derive_metadata_hash(record: object) -> bytes:
        batch_number = str(getattr(record, "batch_number", "") or "").strip()
        drug_name = str(getattr(record, "drug_name", "") or "").strip()
        facility_code = str(getattr(record, "facility_code", "") or "").strip()
        quantity = str(getattr(record, "quantity", "") or "").strip()
        unit = str(getattr(record, "unit_of_measure", "") or "").strip()
        expiry = str(getattr(record, "expiry_date", "") or "").strip()

        payload = "|".join([batch_number, drug_name, facility_code, expiry, quantity, unit])
        return hashlib.sha256(payload.encode("utf-8")).digest()

    def confirm(self, signature: str, max_retries: int = 5) -> bool:
        """
        Poll Solana for transaction confirmation.
        Returns True if confirmed, False if still pending after retries.
        """
        if self.stub:
            return True  # stub always confirms

        import time

        try:
            signature_obj = Signature.from_string(signature)
        except Exception as exc:
            logger.error("Invalid signature format | sig=%s err=%s", signature, exc)
            return False

        for attempt in range(1, max_retries + 1):
            try:
                resp = self._client.get_transaction(signature_obj, commitment="confirmed")
                if resp.value is not None:
                    logger.info("Transaction confirmed | sig=%s", signature)
                    return True
            except Exception as exc:
                logger.warning("Confirm attempt %d failed: %s", attempt, exc)
            time.sleep(2 ** attempt)  # exponential back-off

        logger.error("Transaction not confirmed after %d attempts | sig=%s", max_retries, signature)
        return False

    def get_balance(self) -> Optional[int]:
        """Return payer account balance in lamports (useful for health checks)."""
        if self.stub or not self.payer:
            return None
        resp = self._client.get_balance(self.payer.pubkey())
        return resp.value


# ── Module-level singleton ────────────────────────────────────────────────────
# Instantiated lazily so Django settings are fully loaded first.
_bridge: Optional[SolanaBridge] = None


def get_bridge() -> SolanaBridge:
    """Return the module-level SolanaBridge singleton, creating it if necessary."""
    global _bridge
    if _bridge is None:
        _bridge = SolanaBridge.from_env()
    return _bridge
