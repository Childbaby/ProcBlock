## Summary

Describe what changed and why.

## Risk Classification

Select exactly one:

- [ ] Low
- [ ] Medium
- [ ] High

## Changed Surfaces

List touched areas:

- [ ] onchain contract logic
- [ ] onchain IDL
- [ ] backend blockchain bridge
- [ ] API/business logic
- [ ] infra/CI
- [ ] docs

## Validation Evidence

- [ ] `cargo-build-sbf` passed
- [ ] `anchor build` passed
- [ ] `tsc --noEmit` passed
- [ ] Runtime integration tests passed (or explicitly not run)
- [ ] IDL diff reviewed (if contract-facing)

## Setup and Repro Lane

- [ ] I followed `docs/collaborator-agent-setup.md`
- [ ] I can reproduce the issue/fix in at least one deterministic lane

Lane used:

- [ ] On-chain dry-run (`onchain/scripts/run-anchor-dry-run.ps1`)
- [ ] Backend queue dry-run (`server/scripts/dry_run_task_queue_sync.py`)
- [ ] Manual CI lane (`Onchain Safety Gate` -> `manual-anchor-dry-run`)

## Release Checklist

Reference and complete: `docs/release-checklist.md`

## High-Risk Gate Markers

Only required when high-risk files are changed.

HIGH_RISK_APPROVED: NO
SECURITY_REVIEW_APPROVED: NO

Change each marker to `YES` only after explicit human approval.
