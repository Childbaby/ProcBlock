# VaxChain Zambia On-Chain Trust Layer

This workspace is the Solana and Anchor side of ProcBlock for ZAMMSA medicine procurement.
It replaces memo-only anchoring with first-class program state for batch intake, custody transfer,
and dispensation auditability.

## Contributor and Agent Quick Start

Use this sequence for fastest onboarding:

1. Read `../docs/collaborator-agent-setup.md`.
2. Run the on-chain dry-run lane from this folder:

```powershell
$env:USERPROFILE='C:\Users\Desktop'
$env:HOME='C:\Users\Desktop'
cargo-build-sbf -v --manifest-path '.\programs\vaxchain_trust_layer\Cargo.toml'
.\scripts\run-anchor-dry-run.ps1 -StartElevatedValidator
```

3. Then run backend queue validation from `../server`:

```powershell
c:/Users/Desktop/Projects/Procurement/.venv/Scripts/python.exe .\scripts\dry_run_task_queue_sync.py
```

Expected success markers:

- `ANCHOR_DRY_RUN_OK`
- `TASK_QUEUE_DRY_RUN_OK`

If validator is reachable but slot does not advance, restart validator and rerun this lane first.

## Design Outcome

Use one Anchor program, not several loosely coupled programs.

- `NetworkConfig` PDA stores the network authority and the active Bubblegum compression tree.
- `HubAccount` PDA represents each regional hub or authorized facility custodian.
- `MedicineBatch` PDA is the batch-level source of truth for custody and remaining units.
- `CustodyTransfer` PDA is the append-only handoff receipt for each hub-to-hub transfer.

This keeps the mutable custody path simple and cheap while still leaving room for Metaplex state
compression as the authenticity layer.

## Streamlined Review

The existing repository already has a Django Solana bridge, but it currently anchors hashes through
memo transactions only. That is useful as a fallback, not as the primary trust model.

For this system, the clean split is:

- Anchor program manages state transitions and authorization.
- Bubblegum cNFTs provide provenance and authenticity proofs.
- Django sends only hashes and non-PII identifiers to the chain.

The key streamlining choice is to keep custody truth at the batch PDA level. Do not mutate every
compressed NFT leaf on every transfer. Mint batch-level or unit-level cNFTs at issuance, and let
the Anchor program own custody state changes. That avoids turning a low-cost audit system into a
high-churn leaf-update system.

## Lifecycle

The minimum viable lifecycle is:

1. `Created`: batch registered on-chain by an authorized hub custodian.
2. `Received`: first physical intake acknowledged.
3. `InTransit`: custody handoff initiated to another hub.
4. `Received`: destination hub confirms receipt.
5. `Dispensed`: remaining units reduced to zero.

This scaffold assumes one active transfer per batch and transfers the full remaining balance. If
operations later require split-lot routing, add `split_batch` as a dedicated instruction instead of
overloading the transfer state machine.

## PDA Scheme

- `config`: seeds `['config']`
- `hub`: seeds `['hub', hub_code]`
- `batch`: seeds `['batch', batch_id_hash]`
- `transfer`: seeds `['transfer', batch_id_hash, transfer_nonce]`

`batch_id_hash` should be a SHA-256 digest generated off-chain from a deterministic lot identity,
for example GS1 lot fields plus manufacturer and expiry metadata.

## Instruction Surface

- `initialize_network`: creates the global config PDA.
- `set_compression_tree`: updates the Bubblegum tree used by the trust layer.
- `register_hub`: registers a regional hub authority.
- `create_batch`: creates the batch PDA and anchors document and metadata hashes.
- `record_intake`: acknowledges the first physical receipt.
- `initiate_transfer`: creates an immutable transfer receipt and sets the batch to `InTransit`.
- `receive_transfer`: finalizes a handoff into the destination hub.
- `record_dispensation`: decrements remaining units until the batch is fully dispensed.

## cNFT Strategy

Use Metaplex state compression in two tiers:

- Default path: one cNFT per batch for normal SKUs.
- High-risk path: one cNFT per serialized unit for vaccines, controlled medicines, or high-leakage
  products.

Recommended cNFT metadata fields:

- `batch_id_hash`
- `medicine_code`
- `document_hash`
- `metadata_hash`
- `origin_hub`
- `expiry_epoch`

Do not put names, NRC numbers, patient data, or facility staff data into metadata.

## Security Rules

- Only the network authority can register hubs or rotate the compression tree.
- Only the current hub authority can create a batch, acknowledge intake, initiate transfer, or
  record dispensation for that batch.
- Only the destination hub authority can confirm receipt.
- Hashes are fixed-size 32-byte values so the chain stores proofs, not raw paperwork.
- Every custody handoff emits an event and persists a transfer receipt PDA.

## Devnet and Mainnet Use

- Local development: `docker compose up solana_validator`
- Free team testing: Solana Devnet
- Production: Solana Mainnet with a dedicated compression tree and audited authority controls

Replace the placeholder program ID in `Anchor.toml` and `lib.rs` before deployment.

## Backend Integration Contract

The current Django bridge in `server/blockchain/solana_bridge.py` should be treated as a temporary
memo-based compatibility path. Once the Anchor client is added, Django should submit program
instructions using:

- `batch_id_hash`
- `document_hash`
- `metadata_hash`
- hub authority signer or delegated relayer
- returned transaction signature for the local audit table

## Next On-Chain Work

1. Add Bubblegum CPI calls for batch or unit minting.
2. Add `split_batch` only if regional redistribution requires partial custody movement.
3. Add recall and quarantine instructions after the base custody path is stable.
4. Replace the placeholder program ID and wire Anchor tests.
