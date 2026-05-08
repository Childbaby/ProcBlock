"""
ProcBlock_AI Assistant — Database Seeder
Populates the database with sample facilities, inventory logs, and shipments.

Usage:
    export DATABASE_URL=postgresql://user:pass@localhost:5432/procblock
    export VAULT_MASTER_KEY=<64-char hex>
    python seed.py
"""

import os
import uuid
import json
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app import engine, SessionLocal
from models import Base, Facility, InventoryLog, AnomalyAlert, ActivityEvent, ShipmentVault
from vault_crypto import encrypt_field, compute_payload_hash

Base.metadata.create_all(engine)

HUBS = ["Lusaka", "Ndola", "Livingstone", "Chipata", "Kasama", "Solwezi", "Mongu"]
HUB_PROVINCES = {
    "Lusaka": "Lusaka", "Ndola": "Copperbelt", "Livingstone": "Southern",
    "Chipata": "Eastern", "Kasama": "Northern", "Solwezi": "North-Western", "Mongu": "Western",
}
HUB_COORDS = {
    "Lusaka":      (-15.4166, 28.2833), "Ndola":    (-12.9587, 28.6366),
    "Livingstone": (-17.8419, 25.8546), "Chipata":  (-13.6333, 32.6500),
    "Kasama":      (-10.2167, 31.1833), "Solwezi":  (-12.1833, 26.4000),
    "Mongu":       (-15.2500, 23.1333),
}
FACILITY_TYPES  = ["hospital", "clinic", "pharmacy", "warehouse", "depot"]
MEDICINES = [
    ("AMX500", "Amoxicillin 500mg"),
    ("PCM500", "Paracetamol 500mg"),
    ("ART20",  "Artemether-Lumefantrine 20/120mg"),
    ("CTX960", "Cotrimoxazole 960mg"),
    ("MET500", "Metformin 500mg"),
    ("ORS",    "Oral Rehydration Salts"),
    ("ZINC20", "Zinc Sulphate 20mg"),
    ("FER200", "Ferrous Sulphate 200mg"),
    ("FOL5",   "Folic Acid 5mg"),
    ("ARV30",  "TDF/3TC/DTG 300/300/50mg"),
]
SUPPLIERS = ["MoH Central Stores", "Zambia Medicines Agency", "PharmaCare Ltd", "HealthPro Zambia"]


def seed_facilities(db: Session) -> list[Facility]:
    print("Seeding facilities…")
    facilities = []
    for hub in HUBS:
        for ftype in random.sample(FACILITY_TYPES, k=2):
            lat, lng = HUB_COORDS[hub]
            f = Facility(
                id            = str(uuid.uuid4()),
                name          = f"{hub} {ftype.title()} {random.randint(1, 3)}",
                facility_type = ftype,
                hub           = hub,
                province      = HUB_PROVINCES[hub],
                risk_score    = round(random.uniform(5.0, 85.0), 1),
                status        = random.choice(["active", "active", "active", "flagged"]),
                lat           = lat + random.uniform(-0.5, 0.5),
                lng           = lng + random.uniform(-0.5, 0.5),
            )
            db.add(f)
            facilities.append(f)
    db.commit()
    print(f"  → {len(facilities)} facilities created")
    return facilities


def seed_inventory_logs(db: Session, facilities: list[Facility]):
    print("Seeding inventory logs…")
    count = 0
    now   = datetime.utcnow()

    for facility in facilities:
        for med_code, med_name in random.sample(MEDICINES, k=4):
            for week in range(8):
                intake_date = now - timedelta(weeks=week + 1)
                received    = random.randint(200, 1200)
                dispensed   = random.randint(180, int(received * 1.15))  # occasional over-dispensation
                balance     = max(0, received - dispensed)

                log = InventoryLog(
                    id                 = str(uuid.uuid4()),
                    facility_id        = facility.id,
                    hub                = facility.hub,
                    medicine_code      = med_code,
                    medicine_name      = med_name,
                    quantity_received  = received,
                    quantity_dispensed = dispensed,
                    stock_balance      = balance,
                    unit               = "units",
                    batch_number       = f"BAT-{uuid.uuid4().hex[:8].upper()}",
                    intake_date        = intake_date,
                    dispensation_date  = intake_date + timedelta(days=random.randint(1, 7)),
                    anomaly_flag       = dispensed > received,
                )
                db.add(log)
                count += 1

    db.commit()
    print(f"  → {count} inventory logs created")


def seed_shipments(db: Session, facilities: list[Facility]):
    print("Seeding shipments…")
    statuses = ["PENDING", "IN_TRANSIT", "DELIVERED", "DELIVERED", "FLAGGED"]
    count    = 0

    for _ in range(20):
        origin, dest = random.sample(facilities, 2)
        med_code, med_name = random.choice(MEDICINES)
        quantity = random.randint(100, 2000)
        drug_details = {
            "medicine_code": med_code,
            "medicine_name": med_name,
            "quantity":      quantity,
            "unit":          "units",
            "expiry_date":   "2027-06",
            "cold_chain":    False,
        }
        supplier     = random.choice(SUPPLIERS)
        batch_number = f"BAT-{uuid.uuid4().hex[:8].upper()}"
        status       = random.choice(statuses)

        canonical = {
            "drug_details":            drug_details,
            "batch_number":            batch_number,
            "supplier_name":           supplier,
            "quantity":                quantity,
            "unit":                    "units",
            "shipment_type":           "INTAKE",
            "origin_facility_id":      origin.id,
            "destination_facility_id": dest.id,
        }

        s = ShipmentVault(
            id                      = str(uuid.uuid4()),
            shipment_ref            = f"SHP-{uuid.uuid4().hex[:8].upper()}",
            shipment_type           = "INTAKE",
            origin_facility_id      = origin.id,
            destination_facility_id = dest.id,
            enc_drug_details        = encrypt_field(json.dumps(drug_details)),
            enc_batch_number        = encrypt_field(batch_number),
            enc_supplier_name       = encrypt_field(supplier),
            quantity                = quantity,
            unit                    = "units",
            status                  = status,
            on_chain_payload_hash   = compute_payload_hash(canonical),
            dispatched_at           = datetime.utcnow() - timedelta(days=random.randint(1, 30)) if status != "PENDING" else None,
            delivered_at            = datetime.utcnow() - timedelta(days=random.randint(0, 10)) if status == "DELIVERED" else None,
        )
        db.add(s)
        count += 1

    db.commit()
    print(f"  → {count} shipments seeded")


def seed_alerts(db: Session, facilities: list[Facility]):
    print("Seeding anomaly alerts…")
    alert_types = [
        ("stock_deficit",      "high",   75),
        ("threshold_exceeded", "medium", 55),
        ("rapid_dispensation", "high",   80),
        ("regional_imbalance", "medium", 45),
        ("diversion_pattern",  "high",   90),
    ]
    count = 0
    for facility in random.sample(facilities, k=min(10, len(facilities))):
        atype, severity, base_score = random.choice(alert_types)
        a = AnomalyAlert(
            id           = str(uuid.uuid4()),
            facility_id  = facility.id,
            hub          = facility.hub,
            anomaly_type = atype,
            severity     = severity,
            risk_score   = base_score + random.uniform(-10, 10),
            description  = f"Detected {atype.replace('_', ' ')} at {facility.name}.",
            status       = random.choice(["active", "active", "resolved"]),
            medicine_code = random.choice(MEDICINES)[0],
            detected_at  = datetime.utcnow() - timedelta(days=random.randint(0, 14)),
        )
        db.add(a)
        count += 1

    db.commit()
    print(f"  → {count} alerts seeded")


def seed_activity(db: Session):
    print("Seeding activity feed…")
    events = [
        ("anomaly_detected", "Stock deficit detected at Ndola Clinic", "Ndola",    "warning"),
        ("scan_complete",    "AI scan complete — 3 new anomalies",     "Lusaka",   "info"),
        ("shipment_flagged", "Shipment SHP-8A3F2E flagged",            "Chipata",  "error"),
        ("log_upload",       "180 inventory logs uploaded",            "Kasama",   "info"),
        ("alert_resolved",   "Rapid dispensation alert resolved",      "Solwezi",  "success"),
        ("scan_complete",    "Weekly scan — 7 anomalies detected",     "Lusaka",   "warning"),
        ("shipment_created", "New INTAKE shipment created",            "Mongu",    "info"),
        ("diversion_alert",  "Possible diversion pattern detected",    "Livingstone", "error"),
    ]
    for etype, desc, hub, severity in events:
        db.add(ActivityEvent(
            id         = str(uuid.uuid4()),
            event_type = etype,
            description= desc,
            hub        = hub,
            severity   = severity,
            created_at = datetime.utcnow() - timedelta(hours=random.randint(0, 72)),
        ))
    db.commit()
    print(f"  → {len(events)} activity events seeded")


def run():
    db = SessionLocal()
    try:
        print("\n=== ProcBlock_AI — Database Seeder ===\n")
        facilities = seed_facilities(db)
        seed_inventory_logs(db, facilities)
        seed_shipments(db, facilities)
        seed_alerts(db, facilities)
        seed_activity(db)
        print("\nSeeding complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
