# ProcBlock — ProcBase Prototype

This repository contains a Django backend and Next.js frontend for a procurement-to-blockchain prototype.

Quick start (local, development):

1. Copy `.env.example` to `.env` and edit secrets.

2. Build and start containers:

```bash
docker-compose up --build
```

3. The Django API will be available at `http://127.0.0.1:8000/admin/`.

## Local development without Docker

### Backend

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings_task_dry_run
export SECRET_KEY=dev-secret
export DB_PASSWORD=dummy
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

- Admin login: `http://127.0.0.1:8000/admin/`

### Frontend

```bash
cd client
npm install
npm run dev -- --hostname 0.0.0.0
```

- Frontend available at `http://localhost:3000`

## Available services

- Django backend: `http://127.0.0.1:8000/`
- Admin UI: `http://127.0.0.1:8000/admin/`
- API base: `http://127.0.0.1:8000/api/v1/`
- Frontend app: `http://localhost:3000`

Key components:
- `server/` — Django application (DRF, Celery, Redis)
- `client/` — Next.js frontend
- `blockchain/` — Solana bridge

Privacy & compliance:
- `middleware/privacy.py` strips PII from inbound requests before processing.
- Document contents are hashed using SHA-256 via `crypto/hashing.py` and only the digest is written on-chain.

Notes:
- Ensure `DB_PASSWORD` is set in `.env` before starting containers.
- Solana support is optional; the bridge runs in stub mode when `solana` packages or keypair are absent.
