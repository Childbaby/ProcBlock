"""
ProcBlock_AI Assistant — Database Models
SQLAlchemy ORM models mirroring the Drizzle schema.

Requirements:
    pip install sqlalchemy psycopg2-binary
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean,
    Text, DateTime, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()


def new_uuid() -> str:
    return str(uuid.uuid4())


# ── Analytics Tables ──────────────────────────────────────────────────────────

class Facility(Base):
    __tablename__ = "facilities"

    id           = Column(String, primary_key=True, default=new_uuid)
    name         = Column(String(255), nullable=False)
    facility_type = Column(String(100), nullable=False)  # hospital | clinic | pharmacy | warehouse | depot
    hub          = Column(String(100), nullable=False)   # Lusaka | Ndola | etc.
    province     = Column(String(100), nullable=False)
    risk_score   = Column(Float, default=0.0)
    status       = Column(String(50), default="active")  # active | flagged | inactive
    lat          = Column(Float)
    lng          = Column(Float)
    created_at   = Column(DateTime, default=datetime.utcnow)

    inventory_logs = relationship("InventoryLog", back_populates="facility")
    anomaly_alerts = relationship("AnomalyAlert", back_populates="facility")


class InventoryLog(Base):
    __tablename__ = "inventory_logs"

    id               = Column(String, primary_key=True, default=new_uuid)
    facility_id      = Column(String, ForeignKey("facilities.id"), nullable=False)
    hub              = Column(String(100), nullable=False)
    medicine_code    = Column(String(100), nullable=False)
    medicine_name    = Column(String(255), nullable=False)
    quantity_received = Column(Integer, default=0)
    quantity_dispensed = Column(Integer, default=0)
    stock_balance    = Column(Integer, default=0)
    unit             = Column(String(50), default="units")
    batch_number     = Column(String(100))
    intake_date      = Column(DateTime)
    dispensation_date = Column(DateTime)
    anomaly_flag     = Column(Boolean, default=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    facility = relationship("Facility", back_populates="inventory_logs")


class AnomalyAlert(Base):
    __tablename__ = "anomaly_alerts"

    id           = Column(String, primary_key=True, default=new_uuid)
    facility_id  = Column(String, ForeignKey("facilities.id"))
    hub          = Column(String(100))
    anomaly_type = Column(String(100), nullable=False)
    # stock_deficit | threshold_exceeded | rapid_dispensation
    # unusual_delay | regional_imbalance | diversion_pattern
    severity     = Column(String(50), nullable=False)   # low | medium | high
    risk_score   = Column(Float, default=0.0)
    description  = Column(Text)
    status       = Column(String(50), default="active")  # active | resolved | dismissed
    medicine_code = Column(String(100))
    detected_at  = Column(DateTime, default=datetime.utcnow)
    resolved_at  = Column(DateTime)

    facility = relationship("Facility", back_populates="anomaly_alerts")


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id          = Column(String, primary_key=True, default=new_uuid)
    event_type  = Column(String(100), nullable=False)
    description = Column(Text)
    hub         = Column(String(100))
    severity    = Column(String(50), default="info")
    created_at  = Column(DateTime, default=datetime.utcnow)


# ── Vault Tables (DPA 2021 — AES-256-GCM encrypted fields) ───────────────────

class StaffMember(Base):
    __tablename__ = "staff_members"

    id                  = Column(String, primary_key=True, default=new_uuid)
    staff_id            = Column(String(100), unique=True, nullable=False)
    role                = Column(String(100), nullable=False)  # pharmacist | driver | admin | auditor
    hub                 = Column(String(100), nullable=False)
    facility_id         = Column(String, ForeignKey("facilities.id"))
    enc_full_name       = Column(Text, nullable=False)    # AES-256-GCM encrypted
    enc_national_id     = Column(Text, nullable=False)    # AES-256-GCM encrypted
    enc_phone_number    = Column(Text, nullable=False)    # AES-256-GCM encrypted
    is_active           = Column(Boolean, default=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ShipmentVault(Base):
    __tablename__ = "shipments_vault"

    id                      = Column(String, primary_key=True, default=new_uuid)
    shipment_ref            = Column(String(100), unique=True, nullable=False)
    shipment_type           = Column(String(50), nullable=False)  # INTAKE | DISPENSATION
    origin_facility_id      = Column(String, ForeignKey("facilities.id"))
    destination_facility_id = Column(String, ForeignKey("facilities.id"))
    enc_drug_details        = Column(Text, nullable=False)   # AES encrypted JSON blob
    enc_batch_number        = Column(Text, nullable=False)   # AES encrypted
    enc_supplier_name       = Column(Text, nullable=False)   # AES encrypted
    quantity                = Column(Integer, nullable=False)
    unit                    = Column(String(50), default="units")
    status                  = Column(String(50), default="PENDING")
    # PENDING | IN_TRANSIT | DELIVERED | FLAGGED | RECALLED
    on_chain_payload_hash   = Column(String(64))  # SHA-256 hex for Solana TX
    dispatched_at           = Column(DateTime)
    delivered_at            = Column(DateTime)
    created_at              = Column(DateTime, default=datetime.utcnow)
    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    origin      = relationship("Facility", foreign_keys=[origin_facility_id])
    destination = relationship("Facility", foreign_keys=[destination_facility_id])


class AuditLog(Base):
    __tablename__ = "audit_log"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    action          = Column(String(50), nullable=False)   # INSERT | UPDATE | DELETE | VERIFY
    target_table    = Column(String(100), nullable=False)
    business_id     = Column(String, nullable=False)
    record_hash     = Column(String(64), nullable=False)   # SHA-256 of record state
    performed_by    = Column(String, ForeignKey("staff_members.id"))
    client_ip       = Column(String(45))
    solana_tx_id    = Column(String(200))
    created_at      = Column(DateTime, default=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    id         = Column(String, primary_key=True, default=new_uuid)
    title      = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id              = Column(String, primary_key=True, default=new_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role            = Column(String(20), nullable=False)   # user | assistant | system
    content         = Column(Text, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_engine(database_url: str | None = None):
    url = database_url or os.environ["DATABASE_URL"]
    return create_engine(url, pool_pre_ping=True)


def create_all_tables(engine):
    Base.metadata.create_all(engine)


import os
