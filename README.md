# ProcBlock — MedChain Prototype

This repository contains a Django backend and Next.js frontend for a procurement-to-blockchain prototype.

Quick start (local, development):

1. Copy `.env.example` to `.env` and edit secrets.

2. Build and start containers:

```bash
docker-compose up --build
```

3. The Django API will be available at `http://localhost:8000`.

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
