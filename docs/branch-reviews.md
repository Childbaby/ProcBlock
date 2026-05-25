# ProcBlock — Per-Branch Code Review & Forward-Looking Guide

This document covers what each branch contributed, where it excels today, where it needs attention, and how to instruct an AI coding assistant to produce SOTA-quality code for that layer in the future.

---

## Branch: `main` — Django API + Celery + Solana Bridge

### What this branch does well

- **Clean separation of concerns.** The `server/` tree neatly separates models, serialisers, views, tasks, and the Solana bridge into distinct modules with clear single responsibilities.
- **Defence-in-depth on data storage.** The `MedicineRecord` model stores no PII — only logistics hashes and anonymous facility codes. The `DocumentHashView` hashes procurement PDFs without persisting the file itself.
- **Celery architecture.** `CELERY_TASK_ACKS_LATE` and `CELERY_WORKER_PREFETCH_MULTIPLIER = 1` are production-grade settings that prevent message loss on worker restart and avoid hot-worker starvation under poor connectivity.
- **`BlockchainSyncQueue` decoupling.** Writing to the on-chain layer never blocks the HTTP response. The queue-and-worker pattern is the correct design for a system where RPC latency is unpredictable.
- **Privacy middleware.** `middleware/privacy.py` strips identifying fields before logging, which is a rare and commendable design choice at this layer.

### Issues fixed in this review cycle

| # | File | Issue | Fix applied |
|---|------|-------|-------------|
| 1 | `server/create_admin.py` | Default password `"adminpass"` | Fail-fast `EnvironmentError` if `ADMIN_PASSWORD` unset |
| 2 | `server/app/views.py` | `retry_sync` only checked `IsAuthenticated` | Added `permission_classes=[IsAdminUser]` |
| 3 | `server/app/serializers.py` | `fields = '__all__'` exposed internal fields | Explicit field list + `read_only_fields` |
| 4 | `server/config/settings.py` | Missing `CELERY_BEAT_SCHEDULE` | Added 5-minute `flush_pending_syncs` schedule |
| 5 | `server/config/settings.py` | Missing security headers | Added `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS`, HSTS/SSL toggle via `DJANGO_SECURE` env var |

### Forward-looking priorities

1. **Add `flush_pending_syncs` as an actual Celery task in `tasks.py`** — `CELERY_BEAT_SCHEDULE` now references `app.tasks.flush_pending_syncs`; that function needs to exist.
2. **Test `retry_sync` with `IsAdminUser`** — write a DRF test case using `force_authenticate` to confirm non-admin returns 403.
3. **Add rate-limiting** to the medicine creation endpoint (`DEFAULT_THROTTLE_CLASSES` in DRF settings) to prevent bulk-import abuse.
4. **Rotate the Solana bridge keypair path** — `SOLANA_PAYER_KEYPAIR_PATH` should be a secret-manager reference, not a raw file path.
5. **Replace `SESSION_ENGINE` default** — if Django sessions are used, move to Redis-backed sessions to be stateless across containers.

### AI Prompting Guide for `main` (Django layer)

**Why**: Django's security surface is large. AI assistants default to permissive patterns (e.g. `fields = '__all__'`, broad `IsAuthenticated` guards) unless explicitly constrained. The prompts below steer toward production-hardened output.

```
You are a senior Django/DRF security engineer. Apply these constraints to every
response:

SERIALISERS
- Never use fields = '__all__'. Always enumerate fields explicitly.
- Mark auto-populated fields (id, created_at, updated_at, received_date, is_synced,
  on_chain_signature) as read_only_fields.
- Add field-level validation for every CharField with a bounded domain.

VIEWSETS
- Every @action that modifies state must declare permission_classes=[IsAdminUser]
  unless the design spec explicitly says otherwise.
- perform_create / perform_update must create an AuditEvent entry.
- Use @transaction.atomic on writes that touch multiple tables.

SETTINGS
- CELERY_BEAT_SCHEDULE must include all periodic tasks.
- All security headers (SECURE_CONTENT_TYPE_NOSNIFF, X_FRAME_OPTIONS,
  SECURE_HSTS_SECONDS) must be present and controlled by a DJANGO_SECURE env toggle.
- Never add a fallback value for credential env vars. Raise EnvironmentError or
  KeyError on missing values. Fail fast.

MODELS
- Annotate every model field with a help_text that explains why it is non-PII.
- Never store file content. Hash it at the boundary, store the digest.

CELERY
- All tasks must be idempotent. Explain idempotency in the docstring.
- CELERY_TASK_ACKS_LATE = True and CELERY_WORKER_PREFETCH_MULTIPLIER = 1 are
  non-negotiable.

OUTPUT FORMAT
Produce production-ready Django 4.x code. Include type annotations. No TODOs.
```

---

## Branch: `ProcBlock-Ai-assistant` — Flask Analytics Vault

### What this branch does well

- **AES-256-GCM field encryption.** `vault_crypto.py` uses authenticated encryption with a random 96-bit nonce and a per-record MAC. This is the correct modern primitive for field-level encryption.
- **Blueprint structure.** The four blueprints (`shipments`, `dashboard`, `analyst`, `anomalies`) are well-scoped and independently testable.
- **Offline analyst fallback.** `offline_analyst.py` provides a rule-based narrative fallback when OpenAI is unavailable — resilient design for low-connectivity deployments.
- **Audit logging.** `AuditLog` records are written on all state-changing shipment operations.
- **Strict status-transition graph.** `STATUS_TRANSITIONS` in `shipments.py` is a data-driven state machine — a clean, testable design.

### Issues fixed in this review cycle

| # | File | Issue | Fix applied |
|---|------|-------|-------------|
| 1 | `procblock_python/vault_crypto.py` | Hardcoded 32-byte AES key in `__main__` block | Replaced with fail-fast `SystemExit` if `VAULT_MASTER_KEY` not set |
| 2 | `procblock_python/app.py` | `Access-Control-Allow-Origin: *` | Replaced with origin-allowlist from `CORS_ALLOWED_ORIGINS` env var |
| 3 | `procblock_python/app.py` | `SessionLocal()` opened but never closed | Added `get_db()` with Flask `g` + `teardown_appcontext` |
| 4 | All 4 blueprints | `_get_db()` created new sessions per call | Updated to delegate to `app.get_db()` |

### Forward-looking priorities

1. **Add authentication middleware.** All Flask blueprints are currently unauthenticated. Add a `@require_api_key` decorator that checks `Authorization: Bearer <token>` against a hashed list of known tokens stored in the database.
2. **Encrypt AuditLog entries at rest.** The vault encrypts shipment PII but audit entries may contain indirect identifiers. Apply `encrypt_field` to `detail` columns.
3. **Add SQLAlchemy schema migrations** (Alembic). `Base.metadata.create_all()` in production is a footgun — schema changes are not tracked or reversible.
4. **Centralise error handling.** Add a `@shipments_bp.errorhandler(Exception)` blueprint-level handler that logs the traceback and returns a sanitised JSON error.
5. **Rate-limit the AI analyst endpoint.** `POST /api/openai/query` proxies to GPT without any rate limit, making it a cost-amplification vector.

### AI Prompting Guide for `ProcBlock-Ai-assistant` (Flask/vault layer)

**Why**: Flask defaults are permissive. Without explicit instruction, AI assistants will omit teardown hooks, leave sessions open, and use `*` in CORS headers. The prompts below encode the patterns needed for a vault-grade Flask service.

```
You are a senior Flask/SQLAlchemy engineer building a pharmaceutical vault API.
Apply these constraints to every response:

DB SESSIONS
- All database access must go through Flask's g object: g.db = SessionLocal().
- Register a teardown_appcontext hook that closes g.db after every request.
- Blueprints must import get_db() from app, never create SessionLocal() directly.

AUTHENTICATION
- Every route blueprint must be protected by an @require_api_key decorator.
- The decorator reads Authorization: Bearer <token>, hashes the token with
  SHA-256, and compares to the stored hash. Never store tokens in plaintext.

ENCRYPTION
- PII fields (names, addresses, contact info) must be encrypted with
  encrypt_field() before being written to the database.
- Encrypted fields must be decrypted only in the response serialisation layer,
  never in database queries.

CORS
- Never use Access-Control-Allow-Origin: *. Read allowed origins from
  CORS_ALLOWED_ORIGINS env var (comma-separated). Check request.headers.Origin
  against the allowlist.

ERROR HANDLING
- All blueprint routes must be wrapped in try/except.
- Log the full traceback with logger.exception() and return a sanitised JSON
  error to the caller. Never expose stack traces.

SECRETS
- If a required secret env var is missing at startup, raise EnvironmentError
  immediately. No fallback values for keys or tokens.

OUTPUT FORMAT
Produce Flask 3.x compatible code. Use type annotations. No print statements.
```

---

## Branch: `ci/manual-anchor-dry-run-evidence` — CI/CD & On-Chain Anchor

### What this branch does well

- **CI safety-gate design.** `.github/workflows/onchain-safety-gate.yml` has a `manual-anchor-dry-run` job that is `workflow_dispatch` only, preventing accidental on-chain program deployments on push.
- **Anchor program structure.** `vaxchain_trust_layer/src/lib.rs` implements the correct PDAs (`config`, `hub`, `batch`, `transfer`) with seed-based derivation, making account addresses deterministic and verifiable.
- **Vendor pinning.** `onchain/vendor/anchor-syn-0.30.1/` pins the Anchor parser version, eliminating build non-determinism from crate registry changes.
- **Dry-run scripts.** `run-anchor-dry-run.ps1` and `safety-gate.ps1` provide a scripted lane that documents the exact commands and expected outputs, making reproducible evidence straightforward.
- **State machine instructions.** Instructions are cleanly separated: `initialize_network`, `register_hub`, `create_batch`, `initiate_transfer`, `receive_transfer`, `record_dispensation` form a complete, well-ordered lifecycle.

### Forward-looking priorities

1. **Add account constraint comments.** Every `#[account(...)]` constraint should have a `// Safety:` comment explaining what attack it prevents. This is a Rust/Anchor convention that makes security review faster.
2. **Add integration test coverage.** `onchain/tests/vaxchain_trust_layer.ts` exists but its current coverage level is unknown. Every instruction should have at least: a happy-path test, a bad-authority test, and an invalid-state-transition test.
3. **Add program log assertions.** Use `anchor_lang::emit!` to emit structured events from each instruction. Tests can then assert on event fields rather than account state alone.
4. **Implement on-chain error codes.** Define an `ErrorCode` enum with `#[error_code]` for every constraint violation so the TypeScript SDK gets typed errors instead of raw codes.
5. **Formalise the upgrade authority rotation.** `rotate_network_authority` exists on-chain but the upgrade-authority of the deployed program itself is a separate governance concern. Add a runbook for BPF upgrade authority multi-sig.

### AI Prompting Guide for the `ci/onchain` layer (Anchor/Rust + CI)

**Why**: Solana/Anchor programs have a unique security model where mistakes in account validation allow draining or spoofing. AI assistants often omit `has_one`, `constraint`, or `seeds` verifications. The prompts below enforce the security baseline.

```
You are a senior Solana Anchor engineer. Apply these rules to every response:

ACCOUNT VALIDATION
- Every instruction must validate all signers with has_one or constraint.
- PDA accounts must always include seeds and bump in their #[account] macro.
- Never write an instruction that accepts an arbitrary account without validating
  its owner, discriminator, or seeds.
- Add a // Safety: <reason> comment on every constraint explaining what attack
  it blocks.

ERROR HANDLING
- All invalid states must return a named ErrorCode variant, never a raw error
  string.
- Every ErrorCode must have a human-readable #[msg()] annotation.

EVENTS
- Every state-changing instruction must emit a structured event with emit!().
- Events must include: instruction name, actor pubkey, affected PDA, and
  a Unix timestamp.

TESTING (TypeScript / Anchor)
- Each instruction needs three tests: happy path, wrong-signer test, and
  invalid-state test.
- Use expect(...).to.be.rejectedWith() with the exact ErrorCode name.

CI
- workflow_dispatch triggers only for any job that touches on-chain programs.
- Every PR must run cargo-build-sbf and anchor build before merge.
- IDL diffs must be reviewed before merge as part of the PR checklist.

OUTPUT FORMAT
Produce idiomatic Anchor 0.30 Rust. Use typed accounts. No unwrap() in
instruction handlers. All arithmetic must use checked_add / checked_sub.
```

---

## Branch: `frontend-complete` — Next.js 14 UI + FastAPI AI Service

### What this branch does well

- **Full offline-first field scanner.** The IndexedDB-backed custody transfer queue means field workers can scan barcodes and record transfers with no network connectivity. This is the right UX model for a resource-constrained healthcare logistics context.
- **GS1 DataMatrix parser.** `gs1-parser.ts` correctly handles Application Identifiers (AI 01 for GTIN, AI 10 for lot, AI 17 for expiry, AI 21 for serial), which is the actual standard used by pharmaceutical manufacturers.
- **AI-service architecture.** The FastAPI microservice with `IsolationForest` anomaly detection is cleanly separated from the Next.js app and is independently deployable.
- **`deidentifier.py` in the AI pipeline.** Sanitising supply-chain logs before feeding them to the model is the correct privacy-preserving design for a government health system.
- **Next.js API proxy routes.** `src/app/api/anomalies/route.ts` and `geospatial/route.ts` proxy to the AI service, keeping the AI service URL server-side only.

### Issues fixed in this review cycle

| # | File | Issue | Fix applied |
|---|------|-------|-------------|
| 1 | `src/app/login/page.tsx` | Hardcoded `zammsa2024` credentials in JS bundle | Replaced with real `POST /api/auth/token/` call; token stored in `sessionStorage` |
| 2 | `src/app/scanner/page.tsx` | `new FileDataTransfer()` — not a browser API | Removed; replaced with dynamic `import('html5-qrcode')` in async callback |
| 3 | `src/app/scanner/page.tsx` | `require('html5-qrcode')` in ESM component | Replaced with `await import('html5-qrcode')` |
| 4 | `src/app/scanner/page.tsx` | `handleScanError` flooded console every frame | Changed to no-op callback |
| 5 | `ai-service/anomaly_detector.py` | f-string inner double-quotes — `SyntaxError` on Python 3.11 | Replaced with `.format()` |
| 6 | `ai-service/geospatial_mapper.py` | `np.random.uniform` for stock levels | Replaced with deterministic `dispensation_timestamp` presence ratio |
| 7 | `src/lib/indexeddb-cache.ts` | `getPendingTransfers(): Promise<any[]>` | Added `CachedTransfer` interface; typed return value |
| 8 | `src/app/dashboard/page.tsx` | `onResolve/onInvestigate` were `console.log` stubs | Connected to `setAnomalies` state updaters |

### Forward-looking priorities

1. **Add a proper auth context.** `sessionStorage.setItem('procblock_auth_token', token)` is a start, but a React context provider with a `useAuth()` hook should gate all protected routes and attach the token to API requests automatically.
2. **Add a Next.js middleware** (`src/middleware.ts`) that redirects unauthenticated requests to `/login` before they reach any page component. This prevents protected routes from rendering even briefly.
3. **Sync the IndexedDB queue on reconnect.** The scanner writes transfers offline but there is no background sync trigger. Add a `navigator.onLine` / `ServiceWorker` listener that calls `syncPendingTransfers()` when the browser comes back online.
4. **Replace the `ai-service` default URL.** `process.env.AI_SERVICE_URL || 'http://localhost:8000'` conflicts with Django on the same port. Default should be `http://ai-service:8000` (the Docker service name).
5. **Add Zod validation** to all API response shapes. The frontend currently trusts the AI service response structure without validation.
6. **Move the `src/` directory to `client/`** (or update `package.json` root). The current layout has both a `client/` skeleton and a root `src/` directory, which is confusing for new contributors.

### AI Prompting Guide for `frontend-complete` (Next.js 14 + FastAPI)

**Why**: Next.js 14 App Router has different conventions from Pages Router. AI assistants often mix them. The prompts below enforce App Router idioms, type safety, and offline-first patterns.

```
You are a senior Next.js 14 / TypeScript / Tailwind engineer. Apply these
rules to every response:

NEXT.JS APP ROUTER
- All components in app/ are Server Components by default. Add 'use client'
  only when the component uses hooks, browser APIs, or event handlers.
- Dynamic imports with { ssr: false } are required for any library that
  accesses browser APIs (window, navigator, IndexedDB, camera).
- Never use require() in a Next.js component. Use ES module import or
  await import() inside an async function.

AUTHENTICATION
- Token storage: sessionStorage for short-lived sessions, httpOnly cookies
  for persistent sessions. Never localStorage for auth tokens.
- Protect all routes via src/middleware.ts using NextResponse.redirect()
  for unauthenticated requests.
- Create a useAuth() hook that reads the token and provides it to fetch calls
  via an Authorization header.

TYPE SAFETY
- No any type. Define explicit interfaces for all API response shapes.
- Use Zod to parse and validate all external API responses before using them
  in state.
- Mark all useState initial values with explicit type parameters.

OFFLINE / INDEXEDDB
- Every IndexedDB operation must be in a try/catch with a user-visible error
  state.
- Offline-captured records must be synced when navigator.onLine becomes true.
  Register a window.addEventListener('online', syncPendingTransfers) in a
  useEffect cleanup hook.

FASTAPI (PYTHON SIDE)
- All pydantic models must have field_validator for every field that has a
  finite domain.
- Data loaded at startup must handle FileNotFoundError gracefully and continue
  with empty state, logging a warning.
- Return typed response models (response_model=...) on every endpoint. Never
  return dict directly.
- f-strings must use single quotes for inner strings on Python < 3.12, or use
  .format() for maximum compatibility.

OUTPUT FORMAT
Produce Next.js 14 App Router components. Full TypeScript. No implicit any.
No TODOs. Include unit test skeletons using Vitest/React Testing Library.
```

---

## Cross-cutting: Things every branch should adopt

| Concern | Recommendation |
|---------|---------------|
| **Secret scanning** | Add `gitleaks` or `trufflehog` to the pre-commit hook to catch keys before they reach git history |
| **Dependency audit** | Run `npm audit` (frontend), `pip-audit` (Python), and `cargo audit` (Rust) in CI |
| **Structured logging** | All services should emit JSON logs with `request_id`, `service`, and `level` fields |
| **Health endpoints** | Every service should have a `/healthz` that checks DB connectivity and returns HTTP 200/503 |
| **Environment parity** | `docker-compose.yml` should define all required env vars with `# required` comments; no service should start with a missing required var |
