# ProcBlock — Backend (ProcBase) Overview

This document describes the server backend implemented in `server/` (ProcBase prototype).
It explains the architecture, key modules, data models, how to run the system, and troubleshooting tips.

## Quick summary

- Backend: Django 4.2 + Django REST Framework
- Background jobs: Celery (workers + beat) with Redis broker/result backend
- Database: PostgreSQL (docker service)
- Blockchain: Solana bridge (optional; runs in STUB mode if no keypair)
- Local Data Vault: separate DB helpers + AES-256-GCM encryption for sensitive fields

## Important files

- Server root: `server/` — main Django project and app.
- App (models, views, serializers): [server/app](server/app)
- Config & settings: [server/config](server/config)
- Solana bridge: [server/blockchain/solana_bridge.py](server/blockchain/solana_bridge.py)
- Vault helpers: [vault/vault_db.py](vault/vault_db.py), [vault/vault_crypto.py](vault/vault_crypto.py)
- Middleware PII sanitizer: [server/middleware/privacy.py](server/middleware/privacy.py)
- Docker compose orchestrates services: `docker-compose.yml`

## Architecture & responsibilities

- Django project (`server/`) exposes REST APIs (DRF) and an admin UI.
- `app` contains domain logic: procurement medicine records, blockchain sync queue, and audit events.
- Celery workers process asynchronous tasks (e.g., blockchain writes, logging PII strip events).
- Redis is the broker/result backend for Celery.
- Postgres stores application data; migrations manage schema evolution.
- Vault code handles sensitive data encryption and a separate auditing/reconciliation flow for shipments.
- SolanaBridge wraps the Solana client and will submit the SHA‑256 hash of a payload as a memo transaction.

## Data model highlights

See [server/app/models.py](server/app/models.py) for full definitions. Key models:

- MedicineRecord
  - Stores non-PII logistics fields only (e.g. `drug_name`, `batch_number`, `quantity`, `expiry_date`, `facility_code`).
  - `document_hash`: SHA‑256 hex digest of procurement document (anchor for on‑chain proof).
  - `on_chain_signature`: Solana tx signature once recorded on-chain.
  - `is_synced`: boolean index used by sync workers.

- BlockchainSyncQueue
  - One-to-one with `MedicineRecord`.
  - Tracks sync `status` (PENDING, IN_PROGRESS, CONFIRMED, FAILED), retry `attempts`, and `last_error`.
  - Consumed by a Celery worker that calls the Solana bridge.

- AuditEvent
  - Append-only log of significant events.
  - Immutable: `save()` raises if updating existing record.
  - Stores `event_type`, `medicine_batch` (denormalised ref), `detail` JSON and timestamp.

## Admin

- `server/app/admin.py` registers `MedicineRecord` and `AuditEvent` so they appear as cards in the admin UI.
- Project ships `django-jazzmin` for a nicer admin skin; see `JAZZMIN_SETTINGS` in `server/config/settings.py`.

## Vault (Local Data Vault)

- Files: `vault/vault_crypto.py`, `vault/vault_db.py`.
- `VaultCrypto` uses AES-256-GCM; master key is read from `VAULT_MASTER_KEY` env var.
  - Tokens are stored base64(nonce || ciphertext || tag).
  - `hash_record()` produces canonical SHA‑256 hashes for on-chain anchoring and audit entries.
- `VaultDB` provides high-level helpers to insert facilities, staff, and shipments while:
  1. Encrypting sensitive fields (AES-GCM)
  2. Hashing plaintext payloads for on-chain anchoring
  3. Writing an audit entry per mutating operation

## Solana bridge

- Implemented in `server/blockchain/solana_bridge.py`.
- Submits a SHA‑256 hex digest as a Solana Memo transaction and returns a transaction signature.
- If `solana`/`solders` packages or a payer keypair are missing, the bridge runs in STUB mode (safe for local dev).

## Middleware: PII sanitization

- See `server/middleware/privacy.py`.
- Runs on every inbound request before views/serializers see the body.
- Uses regex/hueristics to redact NRCs, phone numbers, emails, honourific name patterns, and blank certain JSON keys.
- When PII is stripped, an audit event is scheduled via a Celery task (`log_pii_strip_event`).

## Celery configuration

- Broker/result backend: Redis (`REDIS_URL`, env). Configured via settings: `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`.
- `docker-compose.yml` defines `celery_worker` and `celery_beat` services.
- Tasks are defined in `server/app/tasks.py` (e.g. sync, audit logging helpers).

## How to run (recommended: Docker)

1. Copy `.env.example` to `.env` and set secrets (local dev defaults exist in `.env` file):

```powershell
Copy-Item .env.example -Destination .env
# Edit .env as needed (SECRET_KEY, DB_PASSWORD, VAULT_MASTER_KEY if using vault, etc.)
```

2. Build and start services using Docker Compose (will build the web image, start Postgres and Redis, run migrations via the container entrypoint):

```bash
docker compose up --build
```

3. The web admin will be available at `http://localhost:8000/admin`.

Notes: the `web` container's `entrypoint.sh` runs `python manage.py migrate` and `collectstatic` before starting the server.

## How to run locally without Docker (developer machine)

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate     # macOS / Linux
.\.venv\Scripts\activate    # Windows PowerShell
```

2. Install dependencies (may require system packages for `psycopg2`):

```bash
pip install --upgrade pip
pip install -r server/requirements.txt
```

3. Create `.env` in `server/` or set the required env vars and run migrations:

```bash
cd server
python manage.py makemigrations app
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Troubleshooting: on Windows, `psycopg2-binary` can fail to build if system build tools are missing. Use Docker (recommended) or install the PostgreSQL client libraries / Visual C++ build tools, or use WSL.

## Migrations & DB

- Migrations live under `server/app/migrations/`.
- We created and applied migrations for `app` (e.g. `0001_initial.py`) which creates `MedicineRecord`, `AuditEvent`, and `BlockchainSyncQueue` tables.
- To create migrations locally: `python manage.py makemigrations app` then `python manage.py migrate`.

## Admin and verification helpers

- `server/app/admin.py` — registers `MedicineRecord` and `AuditEvent` for the admin.
- `server/verify_admin.py` — small helper used to statically and dynamically check admin registrations.
- `server/create_admin.py` — helper script used to create or confirm a superuser inside the container.

## What we've done in this session (useful references)

- Registered `MedicineRecord` and `AuditEvent` in admin: see [server/app/admin.py](server/app/admin.py)
- Created `verify_admin.py` and `create_admin.py` under `server/` to help testing/automation.
- Brought up the stack with `docker compose up --build`, created & applied migrations, and verified the admin UI.

## Troubleshooting & common issues

- ProgrammingError: `relation "app_medicinerecord" does not exist`
  - Cause: migrations not applied. Fix: `python manage.py migrate` (or let container entrypoint run migrations).

- `ModuleNotFoundError: No module named 'django'` or `psycopg2` build failures
  - Fix: use the `web` Docker image (bundled with correct system libs), or set up a matching Python environment and install system packages required by `psycopg2`.

- Solana in STUB mode
  - If `solana` / `solders` packages or a payer keypair file are missing, the `SolanaBridge` will operate in stub mode for safe local dev. Provide `SOLANA_PAYER_KEYPAIR_PATH` and install `solana` dependencies to enable live submission.

## Next steps you might want

- Add API documentation (OpenAPI / DRF schema + examples) and a Postman/Insomnia collection.
- Add end-to-end tests for the sync path: create `MedicineRecord` → queue sync → Celery worker submits to Solana (or stub) → confirm reconciliation.
- Add a small management command to re-run reconciliation for historical data.

## Contacts & notes

If you'd like, I can:

- Generate an OpenAPI/Swagger spec for the REST API.
- Add example curl/JS snippets showing how to create a `MedicineRecord` and trigger a sync.
- Create a Postgres fixture or sample data to test the admin UI.

---

File created: `docs/backend.md` — please review and tell me if you want more detail in any section.
