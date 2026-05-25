"""
ProcBlock_AI Assistant — Anomaly Alert Routes (Flask blueprint)
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, abort
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from models import AnomalyAlert
from anomaly_detection import run_scan

anomalies_bp = Blueprint("anomalies", __name__, url_prefix="/api/anomalies")


def _get_db() -> Session:
    from app import get_db
    return get_db()


@anomalies_bp.get("/")
def list_alerts():
    db       = _get_db()
    severity = request.args.get("severity")
    status   = request.args.get("status", "active")
    limit    = min(int(request.args.get("limit", 50)), 200)

    q = db.query(AnomalyAlert).order_by(desc(AnomalyAlert.risk_score))
    if status:
        q = q.filter(AnomalyAlert.status == status)
    if severity:
        q = q.filter(AnomalyAlert.severity == severity.lower())

    alerts = q.limit(limit).all()
    return jsonify([
        {
            "id":            a.id,
            "facility_id":   a.facility_id,
            "hub":           a.hub,
            "anomaly_type":  a.anomaly_type,
            "severity":      a.severity,
            "risk_score":    a.risk_score,
            "description":   a.description,
            "status":        a.status,
            "medicine_code": a.medicine_code,
            "detected_at":   a.detected_at.isoformat() if a.detected_at else None,
            "resolved_at":   a.resolved_at.isoformat() if a.resolved_at else None,
        }
        for a in alerts
    ])


@anomalies_bp.post("/scan")
def trigger_scan():
    db     = _get_db()
    result = run_scan(db)
    return jsonify({
        "message":  f"Scan complete — {result['inserted']} new alerts, {result['skipped']} skipped",
        "inserted": result["inserted"],
        "skipped":  result["skipped"],
    }), 200


@anomalies_bp.patch("/<alert_id>")
def update_alert(alert_id: str):
    db    = _get_db()
    alert = db.query(AnomalyAlert).filter(AnomalyAlert.id == alert_id).first()
    if not alert:
        abort(404, "Alert not found")

    data       = request.get_json(force=True) or {}
    new_status = data.get("status", "").lower()

    if new_status not in {"resolved", "dismissed"}:
        abort(400, "Status must be 'resolved' or 'dismissed'")

    alert.status      = new_status
    alert.resolved_at = datetime.utcnow()
    db.commit()

    return jsonify({"id": alert.id, "status": alert.status, "resolved_at": alert.resolved_at.isoformat()})
