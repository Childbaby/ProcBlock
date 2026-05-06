"""
vault_crypto.py
===============
AES-256-GCM encryption layer for the Local Data Vault.

DPA 2021 Compliance Context
----------------------------
- Section 20: Sensitive Personal Data must be processed with appropriate
  technical safeguards — AES-256-GCM satisfies this.
- Section 27: Access controls — key is never stored in the database,
  only in the environment / key management service.
- GCM mode provides both confidentiality AND integrity (authentication tag),
  meaning tampered ciphertext is detected before decryption.

Encryption Format (stored in DB as base64)
------------------------------------------
  base64( nonce[12 bytes] || ciphertext || tag[16 bytes] )

The tag is automatically appended to ciphertext by AESGCM.encrypt().
Total overhead per field: 12 (nonce) + 16 (tag) = 28 bytes + plaintext length.

Usage
-----
  from vault_crypto import VaultCrypto
  vc = VaultCrypto()                      # reads VAULT_MASTER_KEY from env
  token = vc.encrypt("Davison Mapiza")
  plain = vc.decrypt(token)               # → "Davison Mapiza"
"""

import os
import base64
import hashlib
import json
import secrets
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NONCE_SIZE = 12          # 96-bit nonce — GCM recommended size
KEY_SIZE   = 32          # 256-bit key


class VaultCryptoError(Exception):
    """Raised when encryption or decryption fails."""


class VaultCrypto:
    """
    AES-256-GCM symmetric encryption for sensitive database fields.

    The master key is loaded from the environment variable VAULT_MASTER_KEY.
    It must be exactly 64 hex characters (32 bytes = 256 bits).

    Example .env entry:
        VAULT_MASTER_KEY=4a7f3b9e1c2d5f8a0e4b7c3d9f1a2e5b8c4d7f0a3b6e9c2d5f8a1e4b7c0d3f6a

    To generate a secure key (run once, store safely):
        python -c "import secrets; print(secrets.token_hex(32))"
    """

    def __init__(self, key_hex: str | None = None):
        raw = key_hex or os.environ.get("VAULT_MASTER_KEY")
        if not raw:
            raise VaultCryptoError(
                "VAULT_MASTER_KEY environment variable is not set. "
                "Set it before starting the application."
            )
        try:
            key_bytes = bytes.fromhex(raw.strip())
        except ValueError:
            raise VaultCryptoError("VAULT_MASTER_KEY must be a valid hex string.")
        if len(key_bytes) != KEY_SIZE:
            raise VaultCryptoError(
                f"VAULT_MASTER_KEY must be exactly {KEY_SIZE * 2} hex chars "
                f"({KEY_SIZE} bytes). Got {len(key_bytes)} bytes."
            )
        self._aesgcm = AESGCM(key_bytes)

    # -----------------------------------------------------------------------
    # Core encrypt / decrypt
    # -----------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a UTF-8 string.

        Returns a base64-encoded token:  base64(nonce || ciphertext+tag)
        This token is safe to store in a TEXT column.
        """
        if not isinstance(plaintext, str):
            raise VaultCryptoError("plaintext must be a str.")
        nonce = secrets.token_bytes(NONCE_SIZE)          # fresh nonce every call
        ct    = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ct).decode("ascii")

    def decrypt(self, token: str) -> str:
        """
        Decrypt a token produced by encrypt().

        Raises VaultCryptoError if the token is tampered, truncated, or
        was encrypted with a different key (GCM tag mismatch).
        """
        if not isinstance(token, str):
            raise VaultCryptoError("token must be a str.")
        try:
            raw   = base64.b64decode(token)
            nonce = raw[:NONCE_SIZE]
            ct    = raw[NONCE_SIZE:]
            plain = self._aesgcm.decrypt(nonce, ct, None)
            return plain.decode("utf-8")
        except Exception as exc:
            # Do NOT surface raw cryptographic errors to callers/logs
            raise VaultCryptoError("Decryption failed — bad key or corrupted token.") from exc

    # -----------------------------------------------------------------------
    # Convenience helpers for JSON blobs (e.g. enc_drug_details)
    # -----------------------------------------------------------------------

    def encrypt_json(self, data: dict[str, Any]) -> str:
        """Serialize a dict to JSON then encrypt it."""
        return self.encrypt(json.dumps(data, ensure_ascii=False))

    def decrypt_json(self, token: str) -> dict[str, Any]:
        """Decrypt a token and deserialize the JSON payload."""
        return json.loads(self.decrypt(token))

    # -----------------------------------------------------------------------
    # Hashing (for on-chain payload hash & audit_log.data_hash)
    # -----------------------------------------------------------------------

    @staticmethod
    def sha256_hex(data: str | bytes) -> str:
        """
        Return the SHA-256 hex digest of data.
        Used to produce:
          - shipments.on_chain_payload_hash (committed to Solana)
          - audit_log.data_hash (snapshot of record state at action time)
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hash_record(record: dict[str, Any]) -> str:
        """
        Deterministically hash a record dict (sorted keys, no whitespace).
        Encrypted tokens are hashed as-is (the ciphertext changes with each
        encrypt() call, so hash the plaintext dict BEFORE encryption).
        """
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return VaultCrypto.sha256_hex(canonical)


# ---------------------------------------------------------------------------
# Business ID generators
# ---------------------------------------------------------------------------

def generate_facility_id(sequence_num: int) -> str:
    """
    FAC-YYYYMM-XXXX
    Example: FAC-202506-0042
    """
    from datetime import date
    ym = date.today().strftime("%Y%m")
    return f"FAC-{ym}-{sequence_num:04d}"


def generate_staff_id(sequence_num: int) -> str:
    """
    STF-XXXX
    Example: STF-0099
    """
    return f"STF-{sequence_num:04d}"


def generate_shipment_id(sequence_num: int) -> str:
    """
    SHP-YYYYMMDD-XXXXXX
    Example: SHP-20250601-000142
    """
    from datetime import date
    ymd = date.today().strftime("%Y%m%d")
    return f"SHP-{ymd}-{sequence_num:06d}"


# ---------------------------------------------------------------------------
# Quick self-test (run: python vault_crypto.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    test_key = secrets.token_hex(32)
    os.environ["VAULT_MASTER_KEY"] = test_key

    vc = VaultCrypto()
    print("✓ VaultCrypto initialised")

    samples = [
        "Davison Mapiza",
        "123456/78/1",          # NRC format
        "+260977123456",
        "Plot 42, Cairo Road, Lusaka",
    ]
    for s in samples:
        token   = vc.encrypt(s)
        decoded = vc.decrypt(token)
        assert decoded == s, f"Mismatch: {s!r} → {decoded!r}"
        print(f"  encrypt/decrypt OK : {s!r}")

    # JSON blob test
    drug_payload = {
        "drug_name":  "Artemether-Lumefantrine",
        "quantity":   500,
        "unit":       "tablets",
        "batch":      "B2025-0041",
        "expiry_date": "2027-06-30",
        "cold_chain": False,
    }
    token   = vc.encrypt_json(drug_payload)
    decoded = vc.decrypt_json(token)
    assert decoded == drug_payload
    print(f"  encrypt_json/decrypt_json OK")

    # Hash test
    h = VaultCrypto.hash_record(drug_payload)
    assert len(h) == 64
    print(f"  hash_record OK : {h[:16]}…")

    # Tamper detection
    tampered = token[:-4] + "XXXX"
    try:
        vc.decrypt(tampered)
        print("  ✗ Tamper detection FAILED — this should not happen", file=sys.stderr)
    except VaultCryptoError:
        print("  ✓ Tamper detection OK")

    print("\nAll tests passed.")
