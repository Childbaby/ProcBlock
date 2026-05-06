-- =============================================================================
-- LOCAL DATA VAULT — PostgreSQL 15+ Schema
-- Project : Zambia Pharmaceutical Supply Chain (Solana + Off-Chain)
-- Compliance: Data Protection Act No. 3 of 2021 (DPA 2021)
-- Encryption : AES-256-GCM applied at application layer (vault_crypto.py)
--              Sensitive columns store base64(nonce || ciphertext+tag)
-- Host       : Ndola (data residency requirement)
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";    -- DB-side hashing utilities

-- =============================================================================
-- CUSTOM TYPES
-- =============================================================================

CREATE TYPE action_type AS ENUM (
    'INSERT',
    'UPDATE',
    'DELETE',
    'VERIFY',        -- reconciliation check against Solana TX
    'EXPORT',        -- data subject access request export
    'ACCESS'         -- read access for audit trail
);

CREATE TYPE shipment_status AS ENUM (
    'PENDING',
    'IN_TRANSIT',
    'DELIVERED',
    'FLAGGED',       -- anomaly detected (quantity mismatch, etc.)
    'RECALLED'
);

-- =============================================================================
-- TABLE 1: facilities
-- Business identifier format: FAC-YYYYMM-XXXX  (e.g. FAC-202506-0042)
-- Encrypted fields: facility_name, gps_coordinates, physical_address
-- Public fields : business_id, license_number, region_code, created_at
-- =============================================================================

CREATE TABLE facilities (
    id                  UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id         VARCHAR(20)     UNIQUE NOT NULL,          -- FAC-YYYYMM-XXXX
    license_number      VARCHAR(50)     UNIQUE NOT NULL,          -- ZAMRA / MOH license (pseudonym on-chain)

    -- Encrypted at rest (AES-256-GCM via vault_crypto.py)
    -- Format: base64(12-byte nonce || ciphertext || 16-byte GCM tag)
    enc_facility_name       TEXT        NOT NULL,
    enc_physical_address    TEXT        NOT NULL,
    enc_gps_coordinates     TEXT,                                 -- nullable; rural facilities may lack GPS

    region_code         CHAR(3)         NOT NULL,                 -- e.g. 'CBT' = Copperbelt, 'LUS' = Lusaka
    facility_type       VARCHAR(30)     NOT NULL                  -- HOSPITAL | CLINIC | PHARMACY | DEPOT
                            CHECK (facility_type IN ('HOSPITAL','CLINIC','PHARMACY','DEPOT','WAREHOUSE')),
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE 2: staff_members
-- Business identifier format: STF-XXXX  (e.g. STF-0099)
-- Encrypted fields: full_name, national_id, phone_number
-- Public fields : business_id, facility_id, role_code, created_at
-- =============================================================================

CREATE TABLE staff_members (
    id                  UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id         VARCHAR(10)     UNIQUE NOT NULL,          -- STF-XXXX
    facility_id         UUID            NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,

    -- Encrypted at rest
    enc_full_name       TEXT            NOT NULL,
    enc_national_id     TEXT            NOT NULL,                 -- NRC / passport number
    enc_phone_number    TEXT,

    role_code           VARCHAR(20)     NOT NULL                  -- PHARMACIST | NURSE | DRIVER | ADMIN
                            CHECK (role_code IN ('PHARMACIST','NURSE','DRIVER','ADMIN','INSPECTOR')),
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE 3: shipments
-- Business identifier format: SHP-YYYYMMDD-XXXXXX  (e.g. SHP-20250601-000142)
-- Encrypted fields: drug_details (JSON blob), batch_number, supplier_name
-- Public fields : business_id, origin/destination facility, status, on_chain_hash
-- =============================================================================

CREATE TABLE shipments (
    id                      UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id             VARCHAR(25)     UNIQUE NOT NULL,      -- SHP-YYYYMMDD-XXXXXX

    origin_facility_id      UUID            NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,
    destination_facility_id UUID            NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,
    dispatched_by           UUID            REFERENCES staff_members(id),
    received_by             UUID            REFERENCES staff_members(id),

    -- Encrypted at rest (JSON blob containing drug name, quantity, unit, expiry, etc.)
    enc_drug_details        TEXT            NOT NULL,
    enc_batch_number        TEXT            NOT NULL,
    enc_supplier_name       TEXT            NOT NULL,

    -- On-chain anchor (Solana) — stores SHA-256 hash of shipment payload, NOT the raw data
    on_chain_payload_hash   CHAR(64)        NOT NULL,             -- hex SHA-256
    solana_tx_id            VARCHAR(90),                          -- populated after Solana confirmation

    status                  shipment_status NOT NULL DEFAULT 'PENDING',
    dispatch_date           DATE            NOT NULL,
    expected_delivery_date  DATE,
    actual_delivery_date    DATE,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT dispatch_before_delivery
        CHECK (expected_delivery_date IS NULL OR expected_delivery_date >= dispatch_date)
);

-- =============================================================================
-- TABLE 4: audit_log
-- Central reconciliation table — links every DB action to a Solana TX ID.
-- This is the bridge between off-chain PostgreSQL and on-chain Solana.
-- Never update or delete rows from this table (append-only by design).
-- =============================================================================

CREATE TABLE audit_log (
    id                  BIGSERIAL       PRIMARY KEY,
    solana_tx_id        VARCHAR(90),                              -- NULL until Solana confirms
    action              action_type     NOT NULL,
    target_table        VARCHAR(50)     NOT NULL,
    target_record_id    VARCHAR(30)     NOT NULL,                 -- business_id of affected record
    data_hash           CHAR(64)        NOT NULL,                 -- SHA-256 of record state at action time (hex)
    performed_by        VARCHAR(10)     NOT NULL,                 -- STF-XXXX business ID
    client_ip           INET,                                     -- for access logging (DPA 2021 §31)
    notes               TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Audit log is append-only: revoke UPDATE and DELETE from all roles
REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM PUBLIC;

-- =============================================================================
-- TABLE 5: solana_reconciliation
-- Stores the expected vs actual hash for every Solana TX,
-- allowing periodic integrity verification (DPA 2021 data accuracy principle).
-- =============================================================================

CREATE TABLE solana_reconciliation (
    id                  BIGSERIAL       PRIMARY KEY,
    solana_tx_id        VARCHAR(90)     NOT NULL UNIQUE,
    expected_hash       CHAR(64)        NOT NULL,                 -- hash committed on-chain
    verified_at         TIMESTAMPTZ,                              -- NULL = not yet verified
    verification_passed BOOLEAN,                                  -- TRUE | FALSE | NULL (pending)
    mismatch_notes      TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- INDEXES (performance on common query patterns)
-- =============================================================================

CREATE INDEX idx_facilities_business_id       ON facilities(business_id);
CREATE INDEX idx_facilities_region            ON facilities(region_code);
CREATE INDEX idx_staff_business_id            ON staff_members(business_id);
CREATE INDEX idx_staff_facility               ON staff_members(facility_id);
CREATE INDEX idx_shipments_business_id        ON shipments(business_id);
CREATE INDEX idx_shipments_solana_tx          ON shipments(solana_tx_id);
CREATE INDEX idx_shipments_status             ON shipments(status);
CREATE INDEX idx_shipments_origin             ON shipments(origin_facility_id);
CREATE INDEX idx_shipments_destination        ON shipments(destination_facility_id);
CREATE INDEX idx_audit_target_record          ON audit_log(target_record_id);
CREATE INDEX idx_audit_solana_tx              ON audit_log(solana_tx_id);
CREATE INDEX idx_audit_created_at             ON audit_log(created_at DESC);
CREATE INDEX idx_reconciliation_tx            ON solana_reconciliation(solana_tx_id);

-- =============================================================================
-- TRIGGERS — auto-update updated_at on row change
-- =============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_facilities_updated_at
    BEFORE UPDATE ON facilities
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_staff_updated_at
    BEFORE UPDATE ON staff_members
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_shipments_updated_at
    BEFORE UPDATE ON shipments
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- ROLES & PERMISSIONS (least-privilege — DPA 2021 §27 access control)
-- =============================================================================

-- Application role: read + write (used by vault_db.py)
CREATE ROLE vault_app LOGIN PASSWORD 'CHANGE_BEFORE_DEPLOY';
GRANT SELECT, INSERT, UPDATE ON facilities, staff_members, shipments TO vault_app;
GRANT SELECT, INSERT ON audit_log, solana_reconciliation TO vault_app;
GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq, solana_reconciliation_id_seq TO vault_app;

-- Read-only role: for auditors / compliance officers
CREATE ROLE vault_auditor LOGIN PASSWORD 'CHANGE_BEFORE_DEPLOY';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO vault_auditor;

-- No direct DB access for anonymous or external users
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
