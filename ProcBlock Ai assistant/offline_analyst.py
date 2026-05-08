"""
ProcBlock_AI Assistant — Offline Analyst
Rule-based database analysis engine — automatic fallback when OpenAI is unreachable.

Python port of offlineAnalyst.ts
"""

import re
from datetime import datetime
from typing import Generator
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models import (
    ShipmentVault, AnomalyAlert, InventoryLog,
    Facility, Conversation, Message
)
from vault_crypto import decrypt_field


# ── Intent Classification ─────────────────────────────────────────────────────

INTENT_PATTERNS = {
    "shipments":     r"\b(shipment|intake|dispatch|delivery|deliver|transit|received|batch)\b",
    "dispensation":  r"\b(dispens|issue|distribut|given out|hand.?out)\b",
    "leakage":       r"\b(leakage|leak|divert|stolen|theft|missing|diverted|discrepancy)\b",
    "alerts":        r"\b(alert|anomal|flag|suspicious|risk|detect)\b",
    "regional":      r"\b(region|hub|lusaka|ndola|livingstone|chipata|kasama|solwezi|mongu|province)\b",
    "inventory":     r"\b(inventory|stock|supply|balance|level|shortage|surplus)\b",
    "medicines":     r"\b(medicine|drug|medication|amoxicillin|paracetamol|malaria|antibiotic|arv|pharmaceutical)\b",
    "summary":       r"\b(summary|overview|status|report|how.?is|what.?is|tell me|analyse|analyze)\b",
}

def classify_intent(question: str) -> str:
    q = question.lower()
    for intent, pattern in INTENT_PATTERNS.items():
        if re.search(pattern, q):
            return intent
    return "summary"


# ── Response Generators ───────────────────────────────────────────────────────

def _shipments_response(db: Session) -> str:
    total  = db.query(func.count(ShipmentVault.id)).scalar() or 0
    by_status = (
        db.query(ShipmentVault.status, func.count(ShipmentVault.id))
        .group_by(ShipmentVault.status)
        .all()
    )
    flagged = db.query(ShipmentVault).filter(ShipmentVault.status == "FLAGGED").limit(5).all()
    recent  = db.query(ShipmentVault).order_by(desc(ShipmentVault.created_at)).limit(5).all()

    lines = [
        "## Shipment Tracker Overview",
        f"\n**Total Shipments:** {total}\n",
        "### Status Breakdown",
    ]
    for status, count in by_status:
        lines.append(f"- **{status}:** {count}")

    if recent:
        lines.append("\n### 5 Most Recent Shipments")
        for s in recent:
            try:
                drug = decrypt_field(s.enc_drug_details)
            except Exception:
                drug = "[encrypted]"
            lines.append(f"- `{s.shipment_ref}` — {s.shipment_type} | {s.status} | qty: {s.quantity} | {drug[:60]}")

    if flagged:
        lines.append(f"\n### ⚠ Flagged Shipments ({len(flagged)})")
        for s in flagged:
            lines.append(f"- `{s.shipment_ref}` — qty: {s.quantity} — created: {s.created_at.date()}")

    return "\n".join(lines)


def _dispensation_response(db: Session) -> str:
    total_dispensed = db.query(func.sum(InventoryLog.quantity_dispensed)).scalar() or 0
    total_received  = db.query(func.sum(InventoryLog.quantity_received)).scalar() or 0

    by_hub = (
        db.query(InventoryLog.hub,
                 func.sum(InventoryLog.quantity_dispensed).label("dispensed"),
                 func.sum(InventoryLog.quantity_received).label("received"))
        .group_by(InventoryLog.hub)
        .order_by(desc("dispensed"))
        .all()
    )

    lines = [
        "## Dispensation Analysis",
        f"\n**Total Dispensed (all time):** {total_dispensed:,} units",
        f"**Total Received (all time):** {total_received:,} units",
        f"**Coverage Ratio:** {(total_dispensed / total_received * 100):.1f}%" if total_received else "",
        "\n### Dispensation by Regional Hub",
    ]
    for row in by_hub:
        ratio = (row.dispensed / row.received * 100) if row.received else 0
        flag  = " ⚠ OVER-DISPENSED" if ratio > 95 else ""
        lines.append(f"- **{row.hub}:** {row.dispensed:,} dispensed / {row.received:,} received ({ratio:.1f}%){flag}")

    return "\n".join(lines)


def _leakage_response(db: Session) -> str:
    leakage_logs = (
        db.query(InventoryLog)
        .filter(InventoryLog.quantity_dispensed > InventoryLog.quantity_received)
        .limit(10)
        .all()
    )
    flagged_shipments = (
        db.query(ShipmentVault)
        .filter(ShipmentVault.status.in_(["FLAGGED", "RECALLED"]))
        .all()
    )
    diversion_alerts = (
        db.query(AnomalyAlert)
        .filter(AnomalyAlert.anomaly_type.in_(["diversion_pattern", "stock_deficit"]))
        .filter(AnomalyAlert.status == "active")
        .all()
    )

    lines = [
        "## Leakage & Diversion Analysis",
        f"\n**Facilities with over-dispensation:** {len(leakage_logs)}",
        f"**Flagged/Recalled Shipments:** {len(flagged_shipments)}",
        f"**Active Diversion Alerts:** {len(diversion_alerts)}",
    ]

    if leakage_logs:
        lines.append("\n### Over-Dispensation Records")
        for log in leakage_logs:
            diff = log.quantity_dispensed - log.quantity_received
            lines.append(f"- **{log.medicine_name}** at hub `{log.hub}` — excess: {diff:+,} units (balance: {log.stock_balance})")

    if diversion_alerts:
        lines.append("\n### Active Diversion Alerts")
        for a in diversion_alerts:
            lines.append(f"- [{a.severity.upper()}] {a.anomaly_type} — {a.hub} — risk score: {a.risk_score:.0f}/100")

    return "\n".join(lines)


def _alerts_response(db: Session) -> str:
    alerts = (
        db.query(AnomalyAlert)
        .filter(AnomalyAlert.status == "active")
        .order_by(desc(AnomalyAlert.risk_score))
        .all()
    )
    high   = [a for a in alerts if a.severity == "high"]
    medium = [a for a in alerts if a.severity == "medium"]
    low    = [a for a in alerts if a.severity == "low"]

    lines = [
        "## Anomaly Alerts Summary",
        f"\n**Total Active Alerts:** {len(alerts)}",
        f"- 🔴 High Risk: {len(high)}",
        f"- 🟡 Medium Risk: {len(medium)}",
        f"- 🟢 Low Risk: {len(low)}",
    ]

    if high:
        lines.append("\n### High Priority — Immediate Action Required")
        for a in high[:5]:
            lines.append(f"- **{a.anomaly_type}** | {a.hub} | Risk: {a.risk_score:.0f}/100")
            if a.description:
                lines.append(f"  > {a.description[:140]}")

    if medium:
        lines.append("\n### Medium Priority")
        for a in medium[:5]:
            lines.append(f"- {a.anomaly_type} | {a.hub} | Risk: {a.risk_score:.0f}/100")

    return "\n".join(lines)


def _regional_response(db: Session) -> str:
    hubs = ["Lusaka", "Ndola", "Livingstone", "Chipata", "Kasama", "Solwezi", "Mongu"]
    lines = ["## Regional Hub Analysis\n"]

    for hub in hubs:
        intake     = db.query(func.sum(InventoryLog.quantity_received)).filter(InventoryLog.hub == hub).scalar() or 0
        dispensed  = db.query(func.sum(InventoryLog.quantity_dispensed)).filter(InventoryLog.hub == hub).scalar() or 0
        alert_cnt  = db.query(func.count(AnomalyAlert.id)).filter(
            AnomalyAlert.hub == hub, AnomalyAlert.status == "active"
        ).scalar() or 0
        risk_icon  = "🔴" if alert_cnt >= 3 else ("🟡" if alert_cnt >= 1 else "🟢")
        lines.append(f"### {risk_icon} {hub}")
        lines.append(f"- Intake: {intake:,} | Dispensed: {dispensed:,} | Active Alerts: {alert_cnt}")

    return "\n".join(lines)


def _inventory_response(db: Session) -> str:
    total_balance = db.query(func.sum(InventoryLog.stock_balance)).scalar() or 0
    low_stock = (
        db.query(InventoryLog)
        .filter(InventoryLog.stock_balance < 50)
        .order_by(InventoryLog.stock_balance)
        .limit(10)
        .all()
    )
    lines = [
        "## Inventory & Stock Status",
        f"\n**System-wide Stock Balance:** {total_balance:,} units",
        f"**Low-Stock Items (< 50 units):** {len(low_stock)}",
    ]
    if low_stock:
        lines.append("\n### Critical Low-Stock Alerts")
        for log in low_stock:
            lines.append(f"- **{log.medicine_name}** | {log.hub} | Balance: {log.stock_balance} units")
    return "\n".join(lines)


def _medicines_response(db: Session, question: str) -> str:
    q = question.lower()
    med_match = re.search(r"\b(amoxicillin|paracetamol|artemether|cotrimoxazole|metformin|ors|zinc|ferrous|folic|arv)\b", q)

    lines = ["## Medicine Analysis\n"]
    if med_match:
        med = med_match.group(0).capitalize()
        rows = (
            db.query(InventoryLog)
            .filter(InventoryLog.medicine_name.ilike(f"%{med}%"))
            .order_by(desc(InventoryLog.dispensation_date))
            .limit(10)
            .all()
        )
        lines.append(f"### {med} — Distribution Summary")
        total_d = sum(r.quantity_dispensed for r in rows)
        total_r = sum(r.quantity_received for r in rows)
        lines.append(f"- Total Dispensed: {total_d:,} | Total Received: {total_r:,}")
        for row in rows:
            lines.append(f"- {row.hub}: dispensed {row.quantity_dispensed}, balance {row.stock_balance}")
    else:
        top = (
            db.query(InventoryLog.medicine_name,
                     func.sum(InventoryLog.quantity_dispensed).label("total"))
            .group_by(InventoryLog.medicine_name)
            .order_by(desc("total"))
            .limit(10)
            .all()
        )
        lines.append("### Top 10 Dispensed Medicines (All Hubs)")
        for i, row in enumerate(top, 1):
            lines.append(f"{i}. **{row.medicine_name}** — {row.total:,} units dispensed")

    return "\n".join(lines)


def _summary_response(db: Session) -> str:
    total_shipments = db.query(func.count(ShipmentVault.id)).scalar() or 0
    active_alerts   = db.query(func.count(AnomalyAlert.id)).filter(AnomalyAlert.status == "active").scalar() or 0
    high_alerts     = db.query(func.count(AnomalyAlert.id)).filter(
        AnomalyAlert.status == "active", AnomalyAlert.severity == "high"
    ).scalar() or 0
    total_logs      = db.query(func.count(InventoryLog.id)).scalar() or 0
    total_dispensed = db.query(func.sum(InventoryLog.quantity_dispensed)).scalar() or 0
    total_received  = db.query(func.sum(InventoryLog.quantity_received)).scalar() or 0
    flagged         = db.query(func.count(ShipmentVault.id)).filter(ShipmentVault.status == "FLAGGED").scalar() or 0

    lines = [
        "## ProcBlock_AI — Supply Chain Overview",
        f"\n**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "\n### Key Metrics",
        f"- Total Shipments Tracked: {total_shipments} ({flagged} flagged)",
        f"- Active Anomaly Alerts: {active_alerts} ({high_alerts} high-risk)",
        f"- Inventory Logs Processed: {total_logs:,}",
        f"- Total Medicines Dispensed: {total_dispensed:,} units",
        f"- Total Medicines Received: {total_received:,} units",
    ]
    if total_received:
        ratio = total_dispensed / total_received * 100
        risk  = "⚠ HIGH" if ratio > 95 else ("MODERATE" if ratio > 80 else "NORMAL")
        lines.append(f"- Dispensation/Intake Ratio: {ratio:.1f}% [{risk}]")

    return "\n".join(lines)


# ── Public streaming interface ────────────────────────────────────────────────

def stream_offline_response(question: str, db: Session) -> Generator[str, None, None]:
    """
    Classify the question, build a markdown response from the DB,
    then yield it word-by-word to simulate streaming.
    """
    intent = classify_intent(question)

    dispatch = {
        "shipments":    lambda: _shipments_response(db),
        "dispensation": lambda: _dispensation_response(db),
        "leakage":      lambda: _leakage_response(db),
        "alerts":       lambda: _alerts_response(db),
        "regional":     lambda: _regional_response(db),
        "inventory":    lambda: _inventory_response(db),
        "medicines":    lambda: _medicines_response(db, question),
        "summary":      lambda: _summary_response(db),
    }

    header = "⚡ *Offline mode — database-driven analysis*\n\n"
    full_text = header + dispatch.get(intent, dispatch["summary"])()

    for word in full_text.split(" "):
        yield word + " "
