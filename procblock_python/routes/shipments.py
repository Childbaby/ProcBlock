"""
ProcBlock_AI Assistant — Shipments Routes (Flask blueprint)
"""

import hashlib
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, abort
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from models import ShipmentVault, AuditLog, get_engine
from vault_crypto import encrypt_field, decrypt_field, compute_payload_hash

shipments_bp = Blueprint("shipments", __name__, url_prefix="/api/shipments")

VALID_STATUSES = {"PENDING", "IN_TRANSIT", "DELIVERED", "FLAGGED", "RECALLED"}

STATUS_TRANSITIONS = {
    "PENDING":    ["IN_TRANSIT", "FLAGGED"],
    "IN_TRANSIT": ["DELIVERED", "FLAGGED"],
    "DELIVERED":  [],
    "FLAGGED":    ["RECALLED", "IN_TRANSIT"],
    "RECALLED":   [],
}


def _get_db() -> Session:
    from app import get_db
    return get_db()


def _decrypt_shipment(s: ShipmentVault) -> dict:
    try:
        drug_details = json.loads(decrypt_field(s.enc_drug_details))
    except Exception:
        drug_details = {}
    try:
        batch_number = decrypt_field(s.enc_batch_number)
    except Exception:
        batch_number = "[encrypted]"
    try:
        supplier_name = decrypt_field(s.enc_supplier_name)
    except Exception:
        supplier_name = "[encrypted]"

    return {
        "id":                      s.id,
        "shipment_ref":            s.shipment_ref,
        "shipment_type":           s.shipment_type,
        "origin_facility_id":      s.origin_facility_id,
        "destination_facility_id": s.destination_facility_id,
        "drug_details":            drug_details,
        "batch_number":            batch_number,
        "supplier_name":           supplier_name,
        "quantity":                s.quantity,
        "unit":                    s.unit,
        "status":                  s.status,
        "on_chain_payload_hash":   s.on_chain_payload_hash,
        "dispatched_at":           s.dispatched_at.isoformat() if s.dispatched_at else None,
        "delivered_at":            s.delivered_at.isoformat() if s.delivered_at else None,
        "created_at":              s.created_at.isoformat() if s.created_at else None,
    }


@shipments_bp.get("/")
def list_shipments():
    db = _get_db()
    status  = request.args.get("status")
    page    = int(request.args.get("page", 1))
    limit   = min(int(request.args.get("limit", 20)), 100)
    offset  = (page - 1) * limit

    q = db.query(ShipmentVault).order_by(desc(ShipmentVault.created_at))
    if status:
        q = q.filter(ShipmentVault.status == status.upper())

    total = q.count()
    rows  = q.offset(offset).limit(limit).all()
    return jsonify({"shipments": [_decrypt_shipment(s) for s in rows], "total": total, "page": page})


@shipments_bp.get("/stats")
def shipment_stats():
    db = _get_db()
    rows = (
        db.query(ShipmentVault.status, func.count(ShipmentVault.id))
        .group_by(ShipmentVault.status)
        .all()
    )
    stats = {r[0]: r[1] for r in rows}
    return jsonify(stats)


@shipments_bp.post("/")
def create_shipment():
    data = request.get_json(force=True) or {}

    required = ["drug_details", "quantity", "shipment_type"]
    for field in required:
        if field not in data:
            abort(400, f"Missing required field: {field}")

    drug_details  = data["drug_details"]
    batch_number  = data.get("batch_number", "N/A")
    supplier_name = data.get("supplier_name", "Unknown")
    quantity      = int(data["quantity"])
    shipment_type = data["shipment_type"].upper()
    unit          = data.get("unit", "units")
    origin        = data.get("origin_facility_id")
    destination   = data.get("destination_facility_id")

    # Compute on-chain hash before encryption
    canonical_payload = {
        "drug_details":            drug_details,
        "batch_number":            batch_number,
        "supplier_name":           supplier_name,
        "quantity":                quantity,
        "unit":                    unit,
        "shipment_type":           shipment_type,
        "origin_facility_id":      origin,
        "destination_facility_id": destination,
    }
    payload_hash = compute_payload_hash(canonical_payload)

    shipment = ShipmentVault(
        id                      = str(uuid.uuid4()),
        shipment_ref            = f"SHP-{uuid.uuid4().hex[:8].upper()}",
        shipment_type           = shipment_type,
        origin_facility_id      = origin,
        destination_facility_id = destination,
        enc_drug_details        = encrypt_field(json.dumps(drug_details)),
        enc_batch_number        = encrypt_field(batch_number),
        enc_supplier_name       = encrypt_field(supplier_name),
        quantity                = quantity,
        unit                    = unit,
        status                  = "PENDING",
        on_chain_payload_hash   = payload_hash,
    )

    db = _get_db()
    db.add(shipment)

    record_hash = hashlib.sha256(json.dumps(canonical_payload, sort_keys=True).encode()).hexdigest()
    audit = AuditLog(
        action       = "INSERT",
        target_table = "shipments_vault",
        business_id  = shipment.id,
        record_hash  = record_hash,
        client_ip    = request.remote_addr,
    )
    db.add(audit)
    db.commit()

    return jsonify(_decrypt_shipment(shipment)), 201


@shipments_bp.patch("/<shipment_id>/status")
def update_status(shipment_id: str):
    db = _get_db()
    shipment = db.query(ShipmentVault).filter(ShipmentVault.id == shipment_id).first()
    if not shipment:
        abort(404, "Shipment not found")

    data       = request.get_json(force=True) or {}
    new_status = data.get("status", "").upper()

    if new_status not in VALID_STATUSES:
        abort(400, f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")

    allowed = STATUS_TRANSITIONS.get(shipment.status, [])
    if new_status not in allowed:
        abort(400, f"Cannot transition from {shipment.status} to {new_status}")

    shipment.status     = new_status
    shipment.updated_at = datetime.utcnow()
    if new_status == "IN_TRANSIT":
        shipment.dispatched_at = datetime.utcnow()
    elif new_status == "DELIVERED":
        shipment.delivered_at = datetime.utcnow()

    record_hash = hashlib.sha256(f"{shipment_id}:{new_status}".encode()).hexdigest()
    db.add(AuditLog(
        action       = "UPDATE",
        target_table = "shipments_vault",
        business_id  = shipment_id,
        record_hash  = record_hash,
        client_ip    = request.remote_addr,
    ))
    db.commit()

    return jsonify(_decrypt_shipment(shipment))


@shipments_bp.get("/audit/<shipment_id>")
def get_audit_trail(shipment_id: str):
    db = _get_db()
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.business_id == shipment_id, AuditLog.target_table == "shipments_vault")
        .order_by(AuditLog.created_at)
        .all()
    )
    return jsonify([
        {
            "id":          l.id,
            "action":      l.action,
            "record_hash": l.record_hash,
            "client_ip":   l.client_ip,
            "solana_tx_id": l.solana_tx_id,
            "created_at":  l.created_at.isoformat(),
        }
        for l in logs
    ])
