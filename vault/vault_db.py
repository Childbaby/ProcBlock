"""
vault_db.py
===========
Database operations for the Local Data Vault.

Handles:
  - Inserting & querying facilities, staff, and shipments
    (auto-encrypts sensitive fields via VaultCrypto)
  - Writing to audit_log on every mutating operation
  - Reconciling a Solana TX ID against the expected on-chain hash

Dependencies:
    pip install psycopg[binary] cryptography python-dotenv

Environment variables required:
    VAULT_MASTER_KEY   — 64-char hex AES-256 key
    DB_HOST            — e.g. localhost
    DB_PORT            — e.g. 5432
    DB_NAME            — e.g. vault_db
    DB_USER            — e.g. vault_app
    DB_PASSWORD        — application DB password

Usage example:
    from vault_db import VaultDB
    db = VaultDB()
    fac_id = db.insert_facility(
        license_number="ZAMRA-2025-001",
        facility_name="Ndola Central Hospital",
        physical_address="Buteko Avenue, Ndola, Copperbelt",
        gps_coordinates="-12.9706, 28.6369",
        region_code="CBT",
        facility_type="HOSPITAL",
        performed_by="STF-0001",
    )
"""

import os
import json
from contextlib import contextmanager
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

from vault_crypto import (
    VaultCrypto,
    VaultCryptoError,
    generate_facility_id,
    generate_staff_id,
    generate_shipment_id,
)


# ---------------------------------------------------------------------------
# DB connection helper
# ---------------------------------------------------------------------------

def _get_dsn() -> str:
    return (
        f"host={os.environ['DB_HOST']} "
        f"port={os.environ.get('DB_PORT', '5432')} "
        f"dbname={os.environ['DB_NAME']} "
        f"user={os.environ['DB_USER']} "
        f"password={os.environ['DB_PASSWORD']} "
        f"sslmode=require"          # enforce TLS in transit
    )


class VaultDB:
    """
    High-level vault operations.

    Every INSERT / UPDATE automatically:
      1. Encrypts sensitive fields with AES-256-GCM
      2. Hashes the plaintext payload (for audit + on-chain anchoring)
      3. Appends a row to audit_log
    """

    def __init__(self):
        self._crypto = VaultCrypto()
        self._dsn    = _get_dsn()

    @contextmanager
    def _conn(self):
        """Open a connection and auto-commit on clean exit."""
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            yield conn

    # -----------------------------------------------------------------------
    # SEQUENCE helpers — generate next business ID for each entity
    # -----------------------------------------------------------------------

    def _next_facility_seq(self, conn) -> int:
        row = conn.execute(
            "SELECT COUNT(*) + 1 AS n FROM facilities"
        ).fetchone()
        return row["n"]

    def _next_staff_seq(self, conn) -> int:
        row = conn.execute(
            "SELECT COUNT(*) + 1 AS n FROM staff_members"
        ).fetchone()
        return row["n"]

    def _next_shipment_seq(self, conn) -> int:
        row = conn.execute(
            "SELECT COUNT(*) + 1 AS n FROM shipments"
        ).fetchone()
        return row["n"]

    # -----------------------------------------------------------------------
    # AUDIT helper
    # -----------------------------------------------------------------------

    def _write_audit(
        self,
        conn,
        *,
        action: str,
        target_table: str,
        target_record_id: str,
        data_hash: str,
        performed_by: str,
        solana_tx_id: str | None = None,
        client_ip: str | None = None,
        notes: str | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO audit_log
              (solana_tx_id, action, target_table, target_record_id,
               data_hash, performed_by, client_ip, notes)
            VALUES (%s, %s::action_type, %s, %s, %s, %s, %s::inet, %s)
            """,
            (solana_tx_id, action, target_table, target_record_id,
             data_hash, performed_by, client_ip, notes),
        )

    # -----------------------------------------------------------------------
    # FACILITIES
    # -----------------------------------------------------------------------

    def insert_facility(
        self,
        *,
        license_number: str,
        facility_name: str,
        physical_address: str,
        region_code: str,
        facility_type: str,
        gps_coordinates: str | None = None,
        performed_by: str,
        client_ip: str | None = None,
    ) -> str:
        """
        Insert a new facility. Returns the generated business_id.

        Encrypted fields: facility_name, physical_address, gps_coordinates
        """
        plaintext_record = {
            "license_number":   license_number,
            "facility_name":    facility_name,
            "physical_address": physical_address,
            "gps_coordinates":  gps_coordinates,
            "region_code":      region_code,
            "facility_type":    facility_type,
        }
        record_hash = VaultCrypto.hash_record(plaintext_record)

        with self._conn() as conn:
            business_id = generate_facility_id(self._next_facility_seq(conn))

            conn.execute(
                """
                INSERT INTO facilities
                  (business_id, license_number,
                   enc_facility_name, enc_physical_address, enc_gps_coordinates,
                   region_code, facility_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    business_id,
                    license_number,
                    self._crypto.encrypt(facility_name),
                    self._crypto.encrypt(physical_address),
                    self._crypto.encrypt(gps_coordinates) if gps_coordinates else None,
                    region_code,
                    facility_type,
                ),
            )
            self._write_audit(
                conn,
                action="INSERT",
                target_table="facilities",
                target_record_id=business_id,
                data_hash=record_hash,
                performed_by=performed_by,
                client_ip=client_ip,
            )
        return business_id

    def get_facility(self, business_id: str) -> dict[str, Any] | None:
        """
        Fetch and decrypt a facility record.
        Returns a dict with plaintext fields, or None if not found.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM facilities WHERE business_id = %s",
                (business_id,),
            ).fetchone()

        if not row:
            return None

        return {
            "id":                row["id"],
            "business_id":       row["business_id"],
            "license_number":    row["license_number"],
            "facility_name":     self._crypto.decrypt(row["enc_facility_name"]),
            "physical_address":  self._crypto.decrypt(row["enc_physical_address"]),
            "gps_coordinates":   (
                self._crypto.decrypt(row["enc_gps_coordinates"])
                if row["enc_gps_coordinates"] else None
            ),
            "region_code":       row["region_code"],
            "facility_type":     row["facility_type"],
            "is_active":         row["is_active"],
            "created_at":        row["created_at"].isoformat(),
        }

    # -----------------------------------------------------------------------
    # STAFF MEMBERS
    # -----------------------------------------------------------------------

    def insert_staff(
        self,
        *,
        facility_business_id: str,
        full_name: str,
        national_id: str,
        role_code: str,
        phone_number: str | None = None,
        performed_by: str,
        client_ip: str | None = None,
    ) -> str:
        """
        Insert a staff member. Returns the generated business_id (STF-XXXX).
        """
        plaintext_record = {
            "facility":    facility_business_id,
            "full_name":   full_name,
            "national_id": national_id,
            "role_code":   role_code,
        }
        record_hash = VaultCrypto.hash_record(plaintext_record)

        with self._conn() as conn:
            # Resolve facility UUID from business_id
            fac = conn.execute(
                "SELECT id FROM facilities WHERE business_id = %s",
                (facility_business_id,),
            ).fetchone()
            if not fac:
                raise ValueError(f"Facility {facility_business_id!r} not found.")

            business_id = generate_staff_id(self._next_staff_seq(conn))

            conn.execute(
                """
                INSERT INTO staff_members
                  (business_id, facility_id,
                   enc_full_name, enc_national_id, enc_phone_number, role_code)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    business_id,
                    fac["id"],
                    self._crypto.encrypt(full_name),
                    self._crypto.encrypt(national_id),
                    self._crypto.encrypt(phone_number) if phone_number else None,
                    role_code,
                ),
            )
            self._write_audit(
                conn,
                action="INSERT",
                target_table="staff_members",
                target_record_id=business_id,
                data_hash=record_hash,
                performed_by=performed_by,
                client_ip=client_ip,
            )
        return business_id

    # -----------------------------------------------------------------------
    # SHIPMENTS
    # -----------------------------------------------------------------------

    def insert_shipment(
        self,
        *,
        origin_business_id: str,
        destination_business_id: str,
        drug_details: dict[str, Any],
        batch_number: str,
        supplier_name: str,
        dispatch_date: date,
        dispatched_by_staff_id: str | None = None,
        expected_delivery_date: date | None = None,
        performed_by: str,
        client_ip: str | None = None,
    ) -> tuple[str, str]:
        """
        Insert a new shipment.

        Returns (business_id, on_chain_payload_hash).
        The caller must submit on_chain_payload_hash to Solana and then
        call confirm_solana_tx() once the TX is confirmed.

        drug_details example:
          {
            "drug_name":   "Artemether-Lumefantrine",
            "quantity":    500,
            "unit":        "tablets",
            "expiry_date": "2027-06-30",
            "cold_chain":  False,
          }
        """
        # Hash the plaintext payload — this is what goes on-chain
        canonical_payload = {
            "origin":       origin_business_id,
            "destination":  destination_business_id,
            "drug_details": drug_details,
            "batch_number": batch_number,
            "supplier":     supplier_name,
            "dispatch_date": str(dispatch_date),
        }
        payload_hash = VaultCrypto.hash_record(canonical_payload)

        with self._conn() as conn:
            # Resolve UUIDs
            origin = conn.execute(
                "SELECT id FROM facilities WHERE business_id = %s",
                (origin_business_id,),
            ).fetchone()
            dest = conn.execute(
                "SELECT id FROM facilities WHERE business_id = %s",
                (destination_business_id,),
            ).fetchone()
            dispatcher = None
            if dispatched_by_staff_id:
                dispatcher = conn.execute(
                    "SELECT id FROM staff_members WHERE business_id = %s",
                    (dispatched_by_staff_id,),
                ).fetchone()

            if not origin:
                raise ValueError(f"Origin facility {origin_business_id!r} not found.")
            if not dest:
                raise ValueError(f"Destination facility {destination_business_id!r} not found.")

            business_id = generate_shipment_id(self._next_shipment_seq(conn))

            conn.execute(
                """
                INSERT INTO shipments
                  (business_id, origin_facility_id, destination_facility_id,
                   dispatched_by, enc_drug_details, enc_batch_number,
                   enc_supplier_name, on_chain_payload_hash,
                   dispatch_date, expected_delivery_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    business_id,
                    origin["id"],
                    dest["id"],
                    dispatcher["id"] if dispatcher else None,
                    self._crypto.encrypt_json(drug_details),
                    self._crypto.encrypt(batch_number),
                    self._crypto.encrypt(supplier_name),
                    payload_hash,
                    dispatch_date,
                    expected_delivery_date,
                ),
            )
            # Stage reconciliation row (Solana TX not yet known)
            conn.execute(
                """
                INSERT INTO solana_reconciliation (solana_tx_id, expected_hash)
                VALUES (%s, %s)
                """,
                (f"PENDING:{business_id}", payload_hash),
            )
            self._write_audit(
                conn,
                action="INSERT",
                target_table="shipments",
                target_record_id=business_id,
                data_hash=payload_hash,
                performed_by=performed_by,
                client_ip=client_ip,
                notes=f"payload_hash={payload_hash[:16]}…",
            )
        return business_id, payload_hash

    def confirm_solana_tx(
        self,
        *,
        shipment_business_id: str,
        solana_tx_id: str,
        performed_by: str,
    ) -> None:
        """
        Called after the Solana transaction is confirmed on-chain.
        Updates shipments.solana_tx_id and the reconciliation table.
        """
        with self._conn() as conn:
            result = conn.execute(
                """
                UPDATE shipments
                   SET solana_tx_id = %s
                 WHERE business_id = %s
                RETURNING on_chain_payload_hash
                """,
                (solana_tx_id, shipment_business_id),
            ).fetchone()

            if not result:
                raise ValueError(f"Shipment {shipment_business_id!r} not found.")

            # Update reconciliation row
            conn.execute(
                """
                UPDATE solana_reconciliation
                   SET solana_tx_id = %s
                 WHERE solana_tx_id = %s
                """,
                (solana_tx_id, f"PENDING:{shipment_business_id}"),
            )
            self._write_audit(
                conn,
                action="UPDATE",
                target_table="shipments",
                target_record_id=shipment_business_id,
                data_hash=result["on_chain_payload_hash"],
                performed_by=performed_by,
                solana_tx_id=solana_tx_id,
                notes="Solana TX confirmed.",
            )

    # -----------------------------------------------------------------------
    # RECONCILIATION — verify on-chain hash matches local record
    # -----------------------------------------------------------------------

    def verify_shipment(
        self,
        *,
        shipment_business_id: str,
        on_chain_hash: str,      # hash retrieved FROM Solana by the caller
        performed_by: str,
    ) -> bool:
        """
        Compares the hash stored on Solana (supplied by caller after
        querying the chain) against the local on_chain_payload_hash.

        Returns True if they match (integrity verified), False otherwise.
        Also writes the result to solana_reconciliation and audit_log.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT solana_tx_id, on_chain_payload_hash FROM shipments WHERE business_id = %s",
                (shipment_business_id,),
            ).fetchone()

            if not row:
                raise ValueError(f"Shipment {shipment_business_id!r} not found.")

            passed = row["on_chain_payload_hash"] == on_chain_hash

            conn.execute(
                """
                UPDATE solana_reconciliation
                   SET verified_at = NOW(),
                       verification_passed = %s,
                       mismatch_notes = %s
                 WHERE solana_tx_id = %s
                """,
                (
                    passed,
                    None if passed else f"Expected {row['on_chain_payload_hash'][:16]}… got {on_chain_hash[:16]}…",
                    row["solana_tx_id"],
                ),
            )
            self._write_audit(
                conn,
                action="VERIFY",
                target_table="shipments",
                target_record_id=shipment_business_id,
                data_hash=on_chain_hash,
                performed_by=performed_by,
                solana_tx_id=row["solana_tx_id"],
                notes="PASS" if passed else "FAIL — hash mismatch",
            )
        return passed

    # -----------------------------------------------------------------------
    # AUDIT LOG queries
    # -----------------------------------------------------------------------

    def get_audit_trail(self, record_id: str) -> list[dict[str, Any]]:
        """Return the full audit trail for a given business_id."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, solana_tx_id, action, target_table,
                       target_record_id, data_hash, performed_by,
                       client_ip::text, notes, created_at
                  FROM audit_log
                 WHERE target_record_id = %s
                 ORDER BY created_at ASC
                """,
                (record_id,),
            ).fetchall()
        return [
            {**r, "created_at": r["created_at"].isoformat()}
            for r in rows
        ]
