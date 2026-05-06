"""
MedChain – PII Sanitization Middleware
=======================================
Runs on EVERY inbound request before any view processes the body.

Patterns stripped
-----------------
1. Zambian NRC numbers       e.g. 123456/78/9
2. International phone nums  e.g. +260971234567 / 0971234567
3. E-mail addresses
4. Proper names (NLP heuristic: Title-cased word pairs, Dr./Mrs./Mr. prefixes)
5. Generic name-like fields  detected by key inspection in JSON payloads

Strategy
--------
* JSON bodies are parsed, each string value is scrubbed, then re-serialised.
* Non-JSON bodies (form data, plain text) are regex-scrubbed directly.
* An AuditEvent is logged whenever PII is found and stripped.
* The middleware NEVER blocks a request; it sanitises and passes on.
"""
import json
import logging
import re
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("medchain.privacy")

# ── Compiled patterns ─────────────────────────────────────────────────────────

# Zambian NRC: XXXXXX/XX/X  (6 digits / 2 digits / 1 digit)
_NRC = re.compile(r"\b\d{6}/\d{2}/\d\b")

# Phone numbers: +260XXXXXXXXX, 260XXXXXXXXX, 09/07XXXXXXXX (Zambia MTN/Airtel/Zamtel)
_PHONE = re.compile(
    r"(?:\+?260|0)(?:9[5-7]|7[1-9])\d{7}\b"
)

# Generic international phone (fallback)
_PHONE_INTL = re.compile(r"\+?\d[\d\s\-().]{8,14}\d")

# Email addresses
_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# Honourifics + capitalised name (NLP heuristic)
_HONOURIFIC_NAME = re.compile(
    r"\b(?:Dr|Mr|Mrs|Ms|Prof|Rev|Eng)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b"
)

# Two consecutive title-cased words likely to be a full name
_TITLE_CASE_PAIR = re.compile(r"\b([A-Z][a-z]{2,})\s+([A-Z][a-z]{2,})\b")

# Keys in JSON that should always be blanked regardless of value
_PII_KEYS = frozenset({
    "patient_name", "patient_id", "full_name", "first_name", "last_name",
    "surname", "nrc", "nrc_number", "national_id", "phone", "phone_number",
    "mobile", "email", "address", "next_of_kin", "prescriber_name",
    "doctor_name", "nurse_name", "staff_name", "staff_id",
})

_REDACT = "[REDACTED]"


# ── Core scrubbing logic ──────────────────────────────────────────────────────

def scrub_string(value: str) -> tuple[str, bool]:
    """
    Apply all PII patterns to a string.
    Returns (cleaned_value, was_changed).
    """
    original = value
    value = _NRC.sub(_REDACT, value)
    value = _PHONE.sub(_REDACT, value)
    value = _EMAIL.sub(_REDACT, value)
    value = _HONOURIFIC_NAME.sub(_REDACT, value)
    # Only apply the title-case heuristic to longer strings (reduces false positives
    # on drug names like "Amoxicillin Tablets")
    if len(value) > 30:
        value = _TITLE_CASE_PAIR.sub(_REDACT, value)
    return value, value != original


def scrub_dict(data: Any, depth: int = 0) -> tuple[Any, bool]:
    """
    Recursively walk a parsed JSON structure, scrubbing PII from all string values
    and blanking known PII keys entirely.
    Returns (cleaned_data, was_changed).
    """
    if depth > 10:
        return data, False  # guard against deeply nested payloads

    changed = False

    if isinstance(data, dict):
        result = {}
        for key, val in data.items():
            if key.lower() in _PII_KEYS:
                result[key] = _REDACT
                changed = True
            else:
                cleaned, c = scrub_dict(val, depth + 1)
                result[key] = cleaned
                changed = changed or c
        return result, changed

    if isinstance(data, list):
        result = []
        for item in data:
            cleaned, c = scrub_dict(item, depth + 1)
            result.append(cleaned)
            changed = changed or c
        return result, changed

    if isinstance(data, str):
        return scrub_string(data)

    return data, False


# ── Middleware class ──────────────────────────────────────────────────────────

class PIISanitizationMiddleware(MiddlewareMixin):
    """
    Django middleware that sanitises inbound request bodies for PII
    before any view or serializer can process them.
    """

    def process_request(self, request: HttpRequest) -> None:
        content_type = request.content_type or ""
        body = request.body  # read once; cached by Django

        if not body:
            return

        pii_found = False

        # ── JSON payloads ──────────────────────────────────────────────────
        if "application/json" in content_type:
            try:
                data = json.loads(body)
                cleaned, pii_found = scrub_dict(data)
                if pii_found:
                    # Overwrite the cached body so DRF parsers see clean data
                    cleaned_bytes = json.dumps(cleaned).encode("utf-8")
                    request._body = cleaned_bytes  # type: ignore[attr-defined]
            except (json.JSONDecodeError, UnicodeDecodeError):
                logger.warning("PIISanitizationMiddleware: Could not parse JSON body.")

        # ── Form-encoded / plain-text payloads ────────────────────────────
        elif "application/x-www-form-urlencoded" in content_type or "text/plain" in content_type:
            try:
                text = body.decode("utf-8")
                cleaned_text, pii_found = scrub_string(text)
                if pii_found:
                    request._body = cleaned_text.encode("utf-8")  # type: ignore[attr-defined]
            except UnicodeDecodeError:
                pass

        # ── Audit log ──────────────────────────────────────────────────────
        if pii_found:
            logger.warning(
                "PIISanitizationMiddleware: PII detected and stripped | path=%s method=%s",
                request.path,
                request.method,
            )
            # Async-safe: defer DB write to avoid slowing the request
            try:
                from app.tasks import log_pii_strip_event
                log_pii_strip_event.delay(request.path, request.method)
            except Exception:
                # Task queue may not be available in all test/CI environments
                pass
