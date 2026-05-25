# ProcBlock Agent and Collaborator Runbook

This is the primary operating document for both human collaborators and coding agents.
Use this file first, then open `docs/collaborator-agent-setup.md` for copy-paste setup steps.

## 1) Project Map

ProcBlock is a medicine-procurement traceability system:

- Frontend: `client/`
- Backend API and Celery tasks: `server/`
- Solana Anchor workspace: `onchain/`

Core contract file:
- `onchain/programs/vaxchain_trust_layer/src/lib.rs`

## 2) Current Status Snapshot (May 2026)

### Proven

1. Program builds with `cargo-build-sbf` and `anchor build` in the current toolchain lane.
2. CI has a manual runtime lane in `.github/workflows/onchain-safety-gate.yml` (`manual-anchor-dry-run`).
3. Backend task-queue dry-run script exists and validates real Django/Celery task flow through the Solana bridge.

### Still Blocking Production

1. Validator runtime stability is not deterministic on this workstation (privilege/runtime issues).
2. Branch hygiene and release governance are not yet complete.
3. External security review remains pending.

## 3) Ten-Minute Setup (Humans and Agents)

Read and execute:

1. `docs/collaborator-agent-setup.md`
2. `onchain/scripts/run-anchor-dry-run.ps1`
3. `server/scripts/dry_run_task_queue_sync.py`

If you only run one lane, run the on-chain dry-run lane first.

## 4) On-Chain Architecture Snapshot

Main PDAs:

- `config`: seeds `['config']`
- `hub`: seeds `['hub', hub_code]`
- `batch`: seeds `['batch', batch_id_hash]`
- `transfer`: seeds `['transfer', batch_id_hash, transfer_nonce]`

Implemented instructions:

- `initialize_network`
- `set_compression_tree`
- `rotate_network_authority`
- `register_hub`
- `deactivate_hub`
- `reactivate_hub`
- `create_batch`
- `record_intake`
- `initiate_transfer`
- `receive_transfer`
- `record_dispensation`

## 5) Fast Validation Lanes

### Lane A: On-Chain Build + Runtime Dry-Run

From `onchain/`:

```powershell
$env:USERPROFILE='C:\Users\Desktop'
$env:HOME='C:\Users\Desktop'
cargo-build-sbf -v --manifest-path '.\programs\vaxchain_trust_layer\Cargo.toml'
.\scripts\run-anchor-dry-run.ps1 -StartElevatedValidator
```

Expected output includes:

- `ANCHOR_DRY_RUN_OK`

### Lane B: Backend Queue Dry-Run

From `server/`:

```powershell
c:/Users/Desktop/Projects/Procurement/.venv/Scripts/python.exe .\scripts\dry_run_task_queue_sync.py
```

Expected output includes:

- `TASK_QUEUE_DRY_RUN_OK`

Note: this lane intentionally uses SQLite via `config.settings_task_dry_run` to avoid local Postgres driver friction while preserving task-path behavior.

### Lane C: CI Reproducibility

Use GitHub Actions:

- Workflow: `Onchain Safety Gate`
- Trigger: `workflow_dispatch`
- Job: `manual-anchor-dry-run`

## 6) Troubleshooting Playbook

### Error: Windows privilege error (1314) when starting validator

Action:

1. Start an elevated PowerShell terminal.
2. Re-run `onchain/scripts/run-anchor-dry-run.ps1 -StartElevatedValidator`.

### Error: validator reachable but slot not advancing

Symptom:

- Transaction signatures are created but never confirm.
- Dry-run scripts fail with slot progression warnings.

Action:

1. Kill stale validator processes.
2. Start a fresh validator instance with reset ledger.
3. Re-run Lane A before Lane B.

### Error: psycopg2 build failure on Python 3.13

Action:

1. Use `server/config/settings_task_dry_run.py` lane for local validation.
2. Keep production DB settings unchanged.

### Error: Docker compose validator lane unavailable locally

Action:

1. Use native validator lane and script-driven dry-run instead of blocking on Docker.
2. Keep CI runtime lane as source of reproducible evidence.

## 7) Safety Policy for Agents

### Allowed auto-apply scope

Low-risk only:

- diagnostics improvements
- docs and setup clarity
- build and harness stabilization
- non-semantic refactors

### Human approval required

- account constraints and validation logic
- event/error schema changes
- non-trivial backend bridge behavior changes

### Explicit security review required

- authority model changes
- PDA seed changes
- account layout changes
- lifecycle state-machine changes
- deployment or upgrade ceremony updates

## 8) Mandatory Gates Before Merge

For any contract-impacting PR:

1. `cargo-build-sbf` passes.
2. `anchor build` passes and IDL is reviewed.
3. TypeScript compile check passes.
4. Runtime dry-run lane passes in a healthy validator environment.
5. `docs/release-checklist.md` is completed.

## 9) Branch and Collaboration Rules

1. Do not push directly to `main` with unreviewed local state.
2. Keep commits lane-scoped and small.
3. Include exact commands and outputs used for validation in PR notes.
4. If blocked by environment, report exact blocker signature and stop unsafe workarounds.

## 10) Sensitive Surfaces

Treat these paths as high-risk:

- `onchain/programs/vaxchain_trust_layer/src/lib.rs`
- `onchain/target/idl/vaxchain_trust_layer.json`
- `server/blockchain/solana_bridge.py`
- `.github/workflows/onchain-safety-gate.yml`
- `.github/workflows/pr-risk-gates.yml`

## 11) References

- Setup guide: `docs/collaborator-agent-setup.md`
- Release gate checklist: `docs/release-checklist.md`
- On-chain architecture details: `onchain/README.md`
