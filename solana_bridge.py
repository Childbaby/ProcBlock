"""
MedChain – Solana Bridge
=========================
Handles all communication with the Solana blockchain.

Responsibilities
----------------
* Submit a SHA-256 document hash as a memo transaction on Solana.
* Confirm a submitted transaction signature.
* Provide a safe no-op stub when Solana credentials are not configured
  (for local development / CI without a funded keypair).

Dependencies
------------
    pip install solana solders
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("medchain.solana")

# ── Optional import guard ─────────────────────────────────────────────────────
# solana-py is optional in environments that don't need live blockchain access.
try:
    from solana.rpc.api import Client as SolanaClient
    from solana.rpc.types import TxOpts
    from solana.transaction import Transaction
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
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
        stub: bool = False,
    ) -> None:
        self.rpc_url = rpc_url
        self.payer = payer
        self.program_id = program_id
        self.stub = stub or not _SOLANA_AVAILABLE or payer is None

        if not self.stub:
            self._client = SolanaClient(rpc_url)
            logger.info("SolanaBridge initialised | rpc=%s", rpc_url)
        else:
            logger.info("SolanaBridge running in STUB mode – no real transactions.")

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_env(cls) -> "SolanaBridge":
        """Build a bridge instance from Django settings / environment variables."""
        from django.conf import settings

        rpc_url = getattr(settings, "SOLANA_RPC_URL", "https://api.devnet.solana.com")
        program_id = getattr(settings, "SOLANA_PROGRAM_ID", "") or None
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

        return cls(rpc_url=rpc_url, payer=payer, program_id=program_id)

    # ── Public API ────────────────────────────────────────────────────────────

    def submit_hash(self, document_hash: str) -> str:
        """
        Write a 64-character SHA-256 hex digest to Solana as a Memo transaction.

        Returns the transaction signature string.
        Raises RuntimeError on submission failure.
        """
        if len(document_hash) != 64 or not all(c in "0123456789abcdef" for c in document_hash):
            raise ValueError(f"Invalid SHA-256 hash: {document_hash!r}")

        if self.stub:
            stub_sig = f"STUB_{document_hash[:16]}_STUBSIG"
            logger.debug("STUB submit_hash → %s", stub_sig)
            return stub_sig

        try:
            memo_ix = create_memo(
                MemoParams(
                    program_id=Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"),
                    signers=[self.payer.pubkey()],
                    message=bytes(document_hash, "utf-8"),
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
            logger.info("Submitted hash to Solana | sig=%s hash=%s", sig, document_hash)
            return sig

        except Exception as exc:
            logger.error("Solana submit_hash failed: %s", exc)
            raise RuntimeError(f"Blockchain submission failed: {exc}") from exc

    def confirm(self, signature: str, max_retries: int = 5) -> bool:
        """
        Poll Solana for transaction confirmation.
        Returns True if confirmed, False if still pending after retries.
        """
        if self.stub:
            return True  # stub always confirms

        import time

        for attempt in range(1, max_retries + 1):
            try:
                resp = self._client.get_transaction(signature, commitment="confirmed")
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
