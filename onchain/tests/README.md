# On-Chain Tests Guide

This folder contains integration tests for the Anchor program in:

- `onchain/programs/vaxchain_trust_layer/src/lib.rs`

Primary suite:

- `onchain/tests/vaxchain_trust_layer.ts`

## Run Tests Locally

From `onchain/`:

```powershell
npx tsc -p .\tsconfig.json --noEmit
npx ts-mocha -p .\tsconfig.json -t 1000000 tests\vaxchain_trust_layer.ts
```

If validator setup is unstable in your local environment, run:

```powershell
.\scripts\run-anchor-dry-run.ps1 -StartElevatedValidator
```

before launching tests.

## CI-Reproducible Runtime Lane

Use the manual workflow dispatch lane:

1. Workflow: `Onchain Safety Gate`
2. Job: `manual-anchor-dry-run`

## Contributor Notes

1. Keep test updates coupled to on-chain logic changes.
2. Record exact commands and outcomes in PR notes.
3. For setup help, start with `docs/collaborator-agent-setup.md`.