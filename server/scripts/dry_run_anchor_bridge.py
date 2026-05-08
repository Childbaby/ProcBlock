from __future__ import annotations

import hashlib
import json
import os
import struct
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from blockchain.solana_bridge import SolanaBridge

RPC_URL = os.getenv("PROCBLOCK_DRY_RUN_RPC_URL", "http://127.0.0.1:8899")
PROGRAM_ID = os.getenv("PROCBLOCK_DRY_RUN_PROGRAM_ID", "8had5koATJfLWrZ5yMrnSsQ5Ssc5aW4EWNtwrHzb4Prz")
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
HUB_CODE = os.getenv("PROCBLOCK_DRY_RUN_HUB_CODE", "ZMHUB001")
KEYPAIR_PATH = Path(
    os.getenv(
        "PROCBLOCK_DRY_RUN_KEYPAIR_PATH",
        str(Path.home() / ".config" / "solana" / "id.json"),
    )
)


def anchor_discriminator(ix_name: str) -> bytes:
    return hashlib.sha256(f"global:{ix_name}".encode("utf-8")).digest()[:8]


def borsh_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return struct.pack("<I", len(encoded)) + encoded


def load_payer(path: Path) -> Keypair:
    with path.open("r", encoding="utf-8") as f:
        secret = json.load(f)
    return Keypair.from_bytes(bytes(secret))


def send_ix(client: Client, payer: Keypair, ix: Instruction) -> Signature:
    tx = Transaction()
    tx.add(ix)
    resp = client.send_transaction(
        tx,
        payer,
        opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed"),
    )
    return resp.value


def ensure_funded(client: Client, payer: Keypair) -> None:
    bal = client.get_balance(payer.pubkey()).value
    if bal >= 2_000_000_000:
        return

    sig = client.request_airdrop(payer.pubkey(), 3_000_000_000).value
    client.confirm_transaction(sig, commitment="confirmed")


def ensure_rpc_is_progressing(client: Client, rpc_url: str) -> None:
    previous_slot = client.get_slot(commitment="processed").value
    for _ in range(5):
        time.sleep(2)
        current_slot = client.get_slot(commitment="processed").value
        if current_slot > previous_slot:
            return
        previous_slot = current_slot

    raise RuntimeError(
        f"Validator at {rpc_url} is reachable but slot is not advancing. "
        "Restart the validator and retry."
    )


def ensure_network_initialized(client: Client, payer: Keypair, program_id: Pubkey) -> Pubkey:
    config_pda, _ = Pubkey.find_program_address([b"config"], program_id)
    existing = client.get_account_info(config_pda).value
    if existing is not None:
        return config_pda

    data = anchor_discriminator("initialize_network") + bytes(payer.pubkey())
    accounts = [
        AccountMeta(config_pda, False, True),
        AccountMeta(payer.pubkey(), True, True),
        AccountMeta(Pubkey.from_string(SYSTEM_PROGRAM_ID), False, False),
    ]
    ix = Instruction(program_id, data, accounts)
    sig = send_ix(client, payer, ix)
    client.confirm_transaction(sig, commitment="confirmed")
    return config_pda


def ensure_hub_registered(
    client: Client,
    payer: Keypair,
    program_id: Pubkey,
    config_pda: Pubkey,
    hub_code: str,
) -> Pubkey:
    hub_pda, _ = Pubkey.find_program_address([b"hub", hub_code.encode("utf-8")], program_id)
    existing = client.get_account_info(hub_pda).value
    if existing is not None:
        return hub_pda

    hub_label_hash = hashlib.sha256(hub_code.encode("utf-8")).digest()
    data = (
        anchor_discriminator("register_hub")
        + borsh_string(hub_code)
        + hub_label_hash
    )
    accounts = [
        AccountMeta(config_pda, False, True),
        AccountMeta(hub_pda, False, True),
        AccountMeta(payer.pubkey(), False, False),
        AccountMeta(payer.pubkey(), True, True),
        AccountMeta(Pubkey.from_string(SYSTEM_PROGRAM_ID), False, False),
    ]
    ix = Instruction(program_id, data, accounts)
    sig = send_ix(client, payer, ix)
    client.confirm_transaction(sig, commitment="confirmed")
    return hub_pda


def main() -> None:
    if not KEYPAIR_PATH.exists():
        raise FileNotFoundError(f"Keypair not found: {KEYPAIR_PATH}")

    payer = load_payer(KEYPAIR_PATH)
    program_id = Pubkey.from_string(PROGRAM_ID)
    client = Client(RPC_URL)

    try:
        client.get_latest_blockhash()
    except Exception as exc:
        raise RuntimeError(f"Validator is unreachable at {RPC_URL}: {exc}") from exc

    ensure_rpc_is_progressing(client, RPC_URL)

    ensure_funded(client, payer)
    config_pda = ensure_network_initialized(client, payer, program_id)
    ensure_hub_registered(client, payer, program_id, config_pda, HUB_CODE)

    unique_batch_number = f"DRYRUN-BATCH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    record = SimpleNamespace(
        document_hash=hashlib.sha256(b"dry-run-document").hexdigest(),
        batch_number=unique_batch_number,
        quantity=120,
        atc_code="J07BX",
        drug_name="Dry Run Vaccine",
        facility_code="FAC-DRYRUN",
        unit_of_measure="units",
        expiry_date=date(2027, 1, 31),
    )

    bridge = SolanaBridge(
        rpc_url=RPC_URL,
        payer=payer,
        program_id=PROGRAM_ID,
        bridge_mode="anchor",
        hub_code=HUB_CODE,
        medicine_code_prefix="MED",
        allow_memo_fallback=False,
        stub=False,
    )

    sig = bridge.submit_record(record)
    if not bridge.confirm(sig, max_retries=5):
        raise RuntimeError(f"Anchor submission not confirmed: {sig}")

    status_resp = client.get_signature_statuses([Signature.from_string(sig)])
    status = status_resp.value[0]
    if status is None:
        raise RuntimeError(f"No signature status available for submitted tx: {sig}")
    if status.err is not None:
        raise RuntimeError(f"Submitted tx failed on chain | sig={sig} err={status.err}")

    batch_id_hash = hashlib.sha256(record.batch_number.encode("utf-8")).digest()
    batch_pda, _ = Pubkey.find_program_address([b"batch", batch_id_hash], program_id)
    exists = client.get_account_info(batch_pda, commitment="confirmed").value is not None
    if not exists:
        raise RuntimeError("Batch PDA was not found after confirmed submission")

    print("ANCHOR_DRY_RUN_OK")
    print(f"signature={sig}")
    print(f"batch_pda={batch_pda}")


if __name__ == "__main__":
    main()
