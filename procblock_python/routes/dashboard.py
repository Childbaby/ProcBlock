"""
ProcBlock_AI Assistant — Dashboard Routes (Flask blueprint)
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from models import Facility, InventoryLog, AnomalyAlert, ActivityEvent, ShipmentVault

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


def _get_db() -> Session:
    from app import get_db
    return get_db()


@dashboard_bp.get("/summary")
def summary():
    db = _get_db()

    total_facilities  = db.query(func.count(Facility.id)).scalar() or 0
    flagged_facilities = db.query(func.count(Facility.id)).filter(Facility.status == "flagged").scalar() or 0
    active_alerts     = db.query(func.count(AnomalyAlert.id)).filter(AnomalyAlert.status == "active").scalar() or 0
    high_alerts       = db.query(func.count(AnomalyAlert.id)).filter(
        AnomalyAlert.status == "active", AnomalyAlert.severity == "high"
    ).scalar() or 0
    total_logs        = db.query(func.count(InventoryLog.id)).scalar() or 0

    avg_risk = db.query(func.avg(AnomalyAlert.risk_score)).filter(AnomalyAlert.status == "active").scalar() or 0

    recent_events = (
        db.query(ActivityEvent)
        .order_by(desc(ActivityEvent.created_at))
        .limit(10)
        .all()
    )

    return jsonify({
        "facilities":         {"total": total_facilities, "flagged": flagged_facilities},
        "alerts":             {"total": active_alerts, "high": high_alerts},
        "risk_score":         round(float(avg_risk), 1),
        "logs_processed":     total_logs,
        "recent_activity":    [
            {
                "id":          e.id,
                "event_type":  e.event_type,
                "description": e.description,
                "hub":         e.hub,
                "severity":    e.severity,
                "created_at":  e.created_at.isoformat(),
            }
            for e in recent_events
        ],
    })


@dashboard_bp.get("/trend")
def trend():
    db = _get_db()
    weeks = []
    now = datetime.utcnow()

    for i in range(7, -1, -1):
        week_start = now - timedelta(weeks=i + 1)
        week_end   = now - timedelta(weeks=i)

        dispensed = db.query(func.sum(InventoryLog.quantity_dispensed)).filter(
            InventoryLog.dispensation_date >= week_start,
            InventoryLog.dispensation_date <  week_end,
        ).scalar() or 0

        anomaly_count = db.query(func.count(AnomalyAlert.id)).filter(
            AnomalyAlert.detected_at >= week_start,
            AnomalyAlert.detected_at <  week_end,
        ).scalar() or 0

        weeks.append({
            "week":           f"W{8 - i}",
            "week_start":     week_start.date().isoformat(),
            "dispensation":   int(dispensed),
            "anomaly_count":  int(anomaly_count),
        })

    return jsonify(weeks)


@dashboard_bp.get("/hub-distribution")
def hub_distribution():
    db = _get_db()
    hubs = ["Lusaka", "Ndola", "Livingstone", "Chipata", "Kasama", "Solwezi", "Mongu"]

    HUB_COORDS = {
        "Lusaka":      {"lat": -15.4166, "lng": 28.2833},
        "Ndola":       {"lat": -12.9587, "lng": 28.6366},
        "Livingstone": {"lat": -17.8419, "lng": 25.8546},
        "Chipata":     {"lat": -13.6333, "lng": 32.6500},
        "Kasama":      {"lat": -10.2167, "lng": 31.1833},
        "Solwezi":     {"lat": -12.1833, "lng": 26.4000},
        "Mongu":       {"lat": -15.2500, "lng": 23.1333},
    }

    result = []
    for hub in hubs:
        intake    = db.query(func.sum(InventoryLog.quantity_received)).filter(InventoryLog.hub == hub).scalar() or 0
        dispensed = db.query(func.sum(InventoryLog.quantity_dispensed)).filter(InventoryLog.hub == hub).scalar() or 0
        alert_cnt = db.query(func.count(AnomalyAlert.id)).filter(
            AnomalyAlert.hub == hub, AnomalyAlert.status == "active"
        ).scalar() or 0
        high_cnt  = db.query(func.count(AnomalyAlert.id)).filter(
            AnomalyAlert.hub == hub, AnomalyAlert.status == "active", AnomalyAlert.severity == "high"
        ).scalar() or 0

        risk_level = "high" if high_cnt > 0 else ("medium" if alert_cnt > 0 else "low")

        result.append({
            "hub":         hub,
            "coords":      HUB_COORDS.get(hub, {}),
            "intake":      int(intake),
            "dispensed":   int(dispensed),
            "alert_count": int(alert_cnt),
            "risk_level":  risk_level,
        })

    return jsonify(result)
