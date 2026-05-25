# ProcBlock Release Checklist

Use this checklist before any production deployment.

Setup reference for humans and agents: `docs/collaborator-agent-setup.md`

## Build and Artifacts

- [ ] `cargo-build-sbf` succeeded for `onchain/programs/vaxchain_trust_layer`
- [ ] `anchor build` succeeded and regenerated IDL
- [ ] `onchain/target/idl/vaxchain_trust_layer.json` diff reviewed
- [ ] TypeScript tests compile (`npx tsc -p ./tsconfig.json --noEmit`)
- [ ] Integration tests executed in healthy validator environment
- [ ] Local dry-run automation succeeds (`onchain/scripts/run-anchor-dry-run.ps1`)
- [ ] Manual CI dry-run lane passed (`Onchain Safety Gate` workflow_dispatch job `manual-anchor-dry-run`)

## Contract Safety Gates

- [ ] Authorization checks unchanged or intentionally reviewed
- [ ] PDA seeds unchanged or migration/impact analysis documented
- [ ] Account layout changes reviewed for compatibility
- [ ] Error and event schema changes reviewed with downstream consumers

## Backend and Integration

- [ ] Backend bridge mode set explicitly (`SOLANA_BRIDGE_MODE`)
- [ ] Anchor-mode create_batch path validated end-to-end
- [ ] Memo fallback policy confirmed (`SOLANA_ALLOW_MEMO_FALLBACK`)
- [ ] Queue/retry flow validated for sync failures and recoveries

## Governance and Ops

- [ ] Deployment authority verified for target environment
- [ ] Upgrade authority controls reviewed (multisig or equivalent)
- [ ] Monitoring and alerting ready for failed syncs / transaction errors
- [ ] Incident rollback and emergency response steps verified

## Approval Gates

- [ ] Medium-risk changes approved by at least one qualified reviewer
- [ ] High-risk changes approved by security reviewer
- [ ] High-risk PR includes markers:
  - [ ] `HIGH_RISK_APPROVED: YES`
  - [ ] `SECURITY_REVIEW_APPROVED: YES`

## Final Sign-off

- [ ] Release owner sign-off
- [ ] Product/operations sign-off
- [ ] Deployment window approved
