"""
ProcBlock_AI Assistant — Vault Crypto
AES-256-GCM field-level encryption (Python port of vaultCrypto.ts)

Requirements:
    pip install cryptography

Environment:
    VAULT_MASTER_KEY — 64 hex chars (32 bytes)
"""

import os
import base64
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_BYTES = 12   # 96-bit nonce (GCM standard)
TAG_BYTES   = 16   # 128-bit authentication tag


def _get_master_key() -> bytes:
    raw = os.environ.get("VAULT_MASTER_KEY", "")
    if len(raw) != 64:
        raise EnvironmentError(
            "VAULT_MASTER_KEY must be a 64-char hex string (32 bytes). "
            f"Got {len(raw)} chars."
        )
    return bytes.fromhex(raw)


def encrypt_field(plaintext: str) -> str:
    """
    Encrypt a plaintext string and return a base64-encoded ciphertext blob.

    Format (after base64 decode):
        nonce[12 bytes] || ciphertext[n bytes] || tag[16 bytes]
    """
    key = _get_master_key()
    nonce = secrets.token_bytes(NONCE_BYTES)
    aesgcm = AESGCM(key)
    # AESGCM.encrypt() appends the 16-byte tag automatically
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    blob = nonce + ciphertext_with_tag
    return base64.b64encode(blob).decode("ascii")


def decrypt_field(encoded: str) -> str:
    """
    Decrypt a base64-encoded blob previously produced by encrypt_field().
    Raises ValueError if the ciphertext has been tampered with.
    """
    key = _get_master_key()
    blob = base64.b64decode(encoded)
    if len(blob) < NONCE_BYTES + TAG_BYTES:
        raise ValueError("Ciphertext blob is too short — data may be corrupted.")
    nonce = blob[:NONCE_BYTES]
    ciphertext_with_tag = blob[NONCE_BYTES:]
    aesgcm = AESGCM(key)
    plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
    return plaintext_bytes.decode("utf-8")


def compute_payload_hash(payload: dict) -> str:
    """
    Compute a canonical SHA-256 hash of a shipment payload dict for
    on-chain anchoring (Solana TX verification).

    Keys are sorted to ensure deterministic serialisation.
    """
    import hashlib, json
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── Quick smoke test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.environ.setdefault(
        "VAULT_MASTER_KEY",
        "38cb3e9c1daf14f3696cfd327da59b7336ec75533c3218fd7506302c4a706795"
    )
    sample = "Amoxicillin 500mg — 1200 tablets — EXP 2026-12"
    enc = encrypt_field(sample)
    dec = decrypt_field(enc)
    print(f"Original : {sample}")
    print(f"Encrypted: {enc[:60]}…")
    print(f"Decrypted: {dec}")
    assert dec == sample, "Round-trip failed!"
    print("AES-256-GCM round-trip OK")
