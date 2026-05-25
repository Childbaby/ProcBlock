"""
ProcBlock_AI Assistant — Anomaly Detection Engine

Uses OpenAI GPT to scan inventory logs in batches and detect supply chain
anomalies. Falls back to a statistical engine when the API is unavailable.

Requirements:
    pip install openai sqlalchemy
"""

import os
import json
import hashlib
import statistics
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

from models import InventoryLog, AnomalyAlert, Facility


ANOMALY_TYPES = {
    "stock_deficit":       "Dispensation exceeds received stock without a legitimate explanation",
    "threshold_exceeded":  "Stock movement falls outside statistical thresholds (±2σ)",
    "rapid_dispensation":  "Unusually fast distribution rate — possible bulk diversion",
    "unusual_delay":       "Shipment or stock movement significantly delayed vs expected",
    "regional_imbalance":  "Significant disparity between hubs receiving similar allocation",
    "diversion_pattern":   "Combination of indicators consistent with systematic diversion",
}

SYSTEM_PROMPT = """You are an expert pharmaceutical supply chain analyst for Zambia's Ministry of Health.
Analyse the provided inventory log data and identify anomalies.

Return a JSON array of anomaly objects. Each object must have:
{
  "facility_id": "<string>",
  "hub": "<string>",
  "anomaly_type": "stock_deficit|threshold_exceeded|rapid_dispensation|unusual_delay|regional_imbalance|diversion_pattern",
  "severity": "low|medium|high",
  "risk_score": <number 0-100>,
  "description": "<clear explanation>",
  "medicine_code": "<string or null>"
}

Return ONLY the JSON array, no other text."""


# ── Statistical fallback ──────────────────────────────────────────────────────

def _detect_statistical_anomalies(logs: list[InventoryLog]) -> list[dict]:
    anomalies = []
    by_medicine: dict[str, list[InventoryLog]] = {}
    for log in logs:
        by_medicine.setdefault(log.medicine_code, []).append(log)

    for med_code, med_logs in by_medicine.items():
        dispensed_vals = [l.quantity_dispensed for l in med_logs]
        received_vals  = [l.quantity_received  for l in med_logs]

        if len(dispensed_vals) < 2:
            continue

        mean_d = statistics.mean(dispensed_vals)
        try:
            std_d = statistics.stdev(dispensed_vals)
        except statistics.StatisticsError:
            std_d = 0

        for log in med_logs:
            # Over-dispensation
            if log.quantity_received > 0 and log.quantity_dispensed > log.quantity_received:
                excess   = log.quantity_dispensed - log.quantity_received
                ratio    = log.quantity_dispensed / log.quantity_received
                severity = "high" if ratio > 1.5 else "medium"
                anomalies.append({
                    "facility_id":  log.facility_id,
                    "hub":          log.hub,
                    "anomaly_type": "stock_deficit",
                    "severity":     severity,
                    "risk_score":   min(100, round(ratio * 40)),
                    "description":  (
                        f"{log.medicine_name}: dispensed {log.quantity_dispensed} units "
                        f"but only received {log.quantity_received} — excess of {excess} units."
                    ),
                    "medicine_code": log.medicine_code,
                })

            # Statistical threshold
            if std_d > 0 and abs(log.quantity_dispensed - mean_d) > 2 * std_d:
                z_score = abs(log.quantity_dispensed - mean_d) / std_d
                anomalies.append({
                    "facility_id":  log.facility_id,
                    "hub":          log.hub,
                    "anomaly_type": "threshold_exceeded",
                    "severity":     "medium" if z_score < 3 else "high",
                    "risk_score":   min(100, round(z_score * 15)),
                    "description":  (
                        f"{log.medicine_name}: dispensation of {log.quantity_dispensed} units "
                        f"is {z_score:.1f}σ from the hub mean of {mean_d:.0f}."
                    ),
                    "medicine_code": log.medicine_code,
                })

    return anomalies


# ── GPT-powered detection ─────────────────────────────────────────────────────

def _detect_ai_anomalies(logs: list[InventoryLog]) -> list[dict]:
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    api_key  = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY", "replit")

    if not base_url or not _OPENAI_AVAILABLE:
        return _detect_statistical_anomalies(logs)

    client = OpenAI(base_url=base_url, api_key=api_key)

    log_data = [
        {
            "facility_id":         l.facility_id,
            "hub":                 l.hub,
            "medicine_code":       l.medicine_code,
            "medicine_name":       l.medicine_name,
            "quantity_received":   l.quantity_received,
            "quantity_dispensed":  l.quantity_dispensed,
            "stock_balance":       l.stock_balance,
            "intake_date":         l.intake_date.isoformat() if l.intake_date else None,
            "dispensation_date":   l.dispensation_date.isoformat() if l.dispensation_date else None,
        }
        for l in logs
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": json.dumps(log_data)},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content or "[]"
        return json.loads(raw)
    except Exception as e:
        print(f"[anomaly_detection] GPT failed ({e}), using statistical fallback")
        return _detect_statistical_anomalies(logs)


# ── Public scan function ──────────────────────────────────────────────────────

def run_scan(db: Session, batch_size: int = 100) -> dict:
    """
    Run a full anomaly detection scan.
    Returns a summary dict: { inserted, skipped, alerts }.
    """
    logs = db.query(InventoryLog).order_by(desc(InventoryLog.created_at)).limit(batch_size).all()

    if not logs:
        return {"inserted": 0, "skipped": 0, "alerts": []}

    anomalies = _detect_ai_anomalies(logs)

    inserted = 0
    skipped  = 0
    result_alerts = []

    for a in anomalies:
        # De-duplicate: skip if identical alert already active
        existing = (
            db.query(AnomalyAlert)
            .filter(
                AnomalyAlert.facility_id  == a.get("facility_id"),
                AnomalyAlert.anomaly_type == a.get("anomaly_type"),
                AnomalyAlert.medicine_code == a.get("medicine_code"),
                AnomalyAlert.status       == "active",
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        alert = AnomalyAlert(
            facility_id   = a.get("facility_id"),
            hub           = a.get("hub"),
            anomaly_type  = a.get("anomaly_type", "threshold_exceeded"),
            severity      = a.get("severity", "medium"),
            risk_score    = float(a.get("risk_score", 50)),
            description   = a.get("description", ""),
            medicine_code = a.get("medicine_code"),
            status        = "active",
            detected_at   = datetime.utcnow(),
        )
        db.add(alert)
        inserted += 1
        result_alerts.append(a)

    if inserted:
        db.commit()

    return {"inserted": inserted, "skipped": skipped, "alerts": result_alerts}
