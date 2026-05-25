"""
ProcBlock_AI Assistant — AI Analyst Routes (Flask blueprint)
Supports both SSE streaming (online GPT) and offline fallback.
"""

import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, Response, stream_with_context, abort
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import Conversation, Message, ShipmentVault, AnomalyAlert, InventoryLog
from offline_analyst import stream_offline_response

analyst_bp = Blueprint("analyst", __name__, url_prefix="/api/openai")

AI_SYSTEM_PROMPT = """You are ProcBlock_AI, an expert pharmaceutical supply chain analyst for Zambia's Ministry of Health.
You monitor 7 regional healthcare hubs: Lusaka, Ndola, Livingstone, Chipata, Kasama, Solwezi, and Mongu.

Your role:
- Detect medicine leakage, diversion, and stock anomalies
- Analyse intake vs dispensation discrepancies
- Provide actionable insights to supply chain administrators
- Respond in clear, professional markdown

Always be precise, cite specific numbers from the data provided, and flag high-risk findings prominently."""


def _get_db() -> Session:
    from app import SessionLocal
    return SessionLocal()


def _build_context(db: Session) -> str:
    shipments = db.query(ShipmentVault).order_by(desc(ShipmentVault.created_at)).limit(5).all()
    alerts    = db.query(AnomalyAlert).filter(AnomalyAlert.status == "active").order_by(
        desc(AnomalyAlert.risk_score)).limit(5).all()
    logs      = db.query(InventoryLog).order_by(desc(InventoryLog.created_at)).limit(10).all()

    context_parts = ["## Live Supply Chain Context\n"]

    context_parts.append("### Recent Shipments")
    for s in shipments:
        context_parts.append(f"- {s.shipment_ref}: {s.status} | qty: {s.quantity} | type: {s.shipment_type}")

    context_parts.append("\n### Active Alerts (Top 5 by Risk)")
    for a in alerts:
        context_parts.append(f"- [{a.severity.upper()}] {a.anomaly_type} | {a.hub} | risk: {a.risk_score:.0f}/100")
        if a.description:
            context_parts.append(f"  {a.description[:120]}")

    context_parts.append("\n### Recent Inventory Movements")
    for l in logs:
        context_parts.append(
            f"- {l.medicine_name} | {l.hub} | recv: {l.quantity_received} | disp: {l.quantity_dispensed} | bal: {l.stock_balance}"
        )

    return "\n".join(context_parts)


# ── Conversations ─────────────────────────────────────────────────────────────

@analyst_bp.post("/conversations")
def create_conversation():
    db    = _get_db()
    data  = request.get_json(force=True) or {}
    title = data.get("title", f"Analysis {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")

    conv = Conversation(id=str(uuid.uuid4()), title=title)
    db.add(conv)
    db.commit()
    return jsonify({"id": conv.id, "title": conv.title, "created_at": conv.created_at.isoformat()}), 201


@analyst_bp.get("/conversations")
def list_conversations():
    db   = _get_db()
    convs = db.query(Conversation).order_by(desc(Conversation.created_at)).limit(20).all()
    return jsonify([
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()}
        for c in convs
    ])


@analyst_bp.get("/conversations/<conv_id>/messages")
def get_messages(conv_id: str):
    db   = _get_db()
    msgs = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at).all()
    return jsonify([
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in msgs
    ])


# ── Streaming message endpoint ────────────────────────────────────────────────

@analyst_bp.post("/conversations/<conv_id>/messages")
def send_message(conv_id: str):
    db   = _get_db()
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        abort(404, "Conversation not found")

    data    = request.get_json(force=True) or {}
    content = data.get("content", "").strip()
    if not content:
        abort(400, "Message content is required")

    # Persist user message
    user_msg = Message(
        id              = str(uuid.uuid4()),
        conversation_id = conv_id,
        role            = "user",
        content         = content,
    )
    db.add(user_msg)
    db.commit()

    # Try OpenAI first, fall back to offline analyst
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    api_key  = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY", "replit")

    def generate_openai():
        try:
            from openai import OpenAI
            client  = OpenAI(base_url=base_url, api_key=api_key)
            context = _build_context(db)

            history = db.query(Message).filter(
                Message.conversation_id == conv_id
            ).order_by(Message.created_at).limit(20).all()

            messages = [
                {"role": "system", "content": AI_SYSTEM_PROMPT + "\n\n" + context}
            ]
            for m in history:
                messages.append({"role": m.role, "content": m.content})

            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True,
                temperature=0.3,
                max_tokens=1200,
            )

            full_response = ""
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_response += delta
                    yield f"data: {json.dumps({'delta': delta})}\n\n"

            # Persist assistant message
            assistant_msg = Message(
                id              = str(uuid.uuid4()),
                conversation_id = conv_id,
                role            = "assistant",
                content         = full_response,
            )
            db.add(assistant_msg)
            db.commit()
            yield "data: [DONE]\n\n"

        except Exception:
            # Offline fallback
            yield from generate_offline()

    def generate_offline():
        full_response = ""
        for word in stream_offline_response(content, db):
            full_response += word
            yield f"data: {json.dumps({'delta': word})}\n\n"

        assistant_msg = Message(
            id              = str(uuid.uuid4()),
            conversation_id = conv_id,
            role            = "assistant",
            content         = full_response,
        )
        db.add(assistant_msg)
        db.commit()
        yield "data: [DONE]\n\n"

    generator = generate_openai() if base_url else generate_offline()

    return Response(
        stream_with_context(generator),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":   "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":      "keep-alive",
        },
    )
