# ProcBlock Collaborator and Agent Setup

This guide is for both human contributors and coding agents.
It is designed to get a new workstation productive quickly with deterministic validation lanes.

## 1) Goals

After this guide, you should be able to:

1. Build the Anchor program.
2. Run local on-chain dry-run validation.
3. Run backend queue-to-chain dry-run validation.
4. Trigger the manual CI dry-run lane.

## 2) Prerequisites

Install these before continuing:

1. Rust and rustup
2. Solana CLI
3. Anchor CLI
4. Node.js and npm
5. Python environment at `C:/Users/Desktop/Projects/Procurement/.venv`

## 3) On-Chain Lane (Required First)

From `ProcBlock/onchain`:

```powershell
$env:USERPROFILE='C:\Users\Desktop'
$env:HOME='C:\Users\Desktop'
cargo-build-sbf -v --manifest-path '.\programs\vaxchain_trust_layer\Cargo.toml'
.\scripts\run-anchor-dry-run.ps1 -StartElevatedValidator
```

Success criteria:

1. Build completes without errors.
2. Dry-run output includes `ANCHOR_DRY_RUN_OK`.

## 4) Backend Task Queue Lane

From `ProcBlock/server`:

```powershell
c:/Users/Desktop/Projects/Procurement/.venv/Scripts/python.exe .\scripts\dry_run_task_queue_sync.py
```

Success criteria:

1. Output includes `TASK_QUEUE_DRY_RUN_OK`.
2. Queue entry status is confirmed.

Notes:

1. This script uses `config.settings_task_dry_run` with SQLite for predictable local setup.
2. Production DB settings are not changed by this lane.

## 5) CI Reproducibility Lane

Trigger workflow manually:

1. Workflow: `Onchain Safety Gate`
2. Event: `workflow_dispatch`
3. Job: `manual-anchor-dry-run`

Treat this job as shared evidence for collaborator and agent reproducibility.

## 6) Common Failures and Fixes

### Validator privilege error (Windows 1314)

1. Open PowerShell as Administrator.
2. Re-run: `onchain/scripts/run-anchor-dry-run.ps1 -StartElevatedValidator`

### Validator reachable but slot not advancing

Symptoms:

1. Signatures are returned but never confirm.
2. Dry-run fails with slot progression warnings.

Fix:

1. Stop stale validator processes.
2. Start a fresh validator with reset ledger.
3. Re-run on-chain lane first, backend lane second.

### psycopg2 build issues on local Python 3.13

1. Continue using the SQLite dry-run lane.
2. Do not change production DB config as a workaround.

## 7) Daily Workflow for Collaborators and Agents

1. Pull latest branch and confirm branch state.
2. Run on-chain dry-run lane.
3. Run backend queue dry-run lane.
4. Make minimal changes.
5. Re-run affected lane(s).
6. Record exact commands and results in PR.

## 8) Before Asking for Review

1. Complete `docs/release-checklist.md` entries relevant to your change.
2. Confirm `main` is up to date before merge.
3. Include blocker details if any lane is environment-limited.