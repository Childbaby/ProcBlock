"""
MedChain – Cryptography Module
================================
Generates SHA-256 hashes of procurement documents.

Design principle: document bytes NEVER leave this module.
Only the hex digest travels through the rest of the system.
"""
import hashlib
import hmac
import os
from pathlib import Path
from typing import BinaryIO


def hash_bytes(data: bytes) -> str:
    """
    Return the lowercase SHA-256 hex digest of raw bytes.

    >>> hash_bytes(b"hello")
    '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
    """
    return hashlib.sha256(data).hexdigest()


def hash_file(file_obj: BinaryIO, chunk_size: int = 65_536) -> str:
    """
    Stream-hash a file-like object in chunks to avoid loading large
    procurement PDFs into memory.

    Usage::
        with open("purchase_order.pdf", "rb") as f:
            digest = hash_file(f)
    """
    h = hashlib.sha256()
    while chunk := file_obj.read(chunk_size):
        h.update(chunk)
    return h.hexdigest()


def hash_file_path(path: str | Path) -> str:
    """Convenience wrapper that opens a path and calls hash_file."""
    with open(path, "rb") as f:
        return hash_file(f)


def verify_hash(data: bytes, expected_hex: str) -> bool:
    """
    Constant-time comparison to verify a document against its stored hash.
    Uses hmac.compare_digest to prevent timing attacks.

    Returns True if the document matches, False otherwise.
    """
    actual = hash_bytes(data)
    return hmac.compare_digest(actual.encode(), expected_hex.lower().encode())


def generate_salt(length: int = 32) -> str:
    """Generate a cryptographically random hex salt (not used in on-chain storage
    but available for future HMAC-based integrity checks)."""
    return os.urandom(length).hex()
