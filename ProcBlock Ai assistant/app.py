"""
ProcBlock_AI Assistant — Flask Application Entry Point

Usage:
    pip install -r requirements.txt
    export DATABASE_URL=postgresql://user:pass@localhost:5432/procblock
    export VAULT_MASTER_KEY=<64-char hex>
    export AI_INTEGRATIONS_OPENAI_BASE_URL=<url>   # optional — enables GPT
    export AI_INTEGRATIONS_OPENAI_API_KEY=<key>    # optional — enables GPT
    python app.py
"""

import os
import logging
from flask import Flask, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models import Base
from routes import shipments_bp, dashboard_bp, analyst_bp, anomalies_bp

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger("procblock")

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL environment variable is required.")

engine       = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Auto-create tables on startup
Base.metadata.create_all(engine)
logger.info("Database tables ready.")

# ── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# ── Blueprints ────────────────────────────────────────────────────────────────
app.register_blueprint(dashboard_bp)
app.register_blueprint(shipments_bp)
app.register_blueprint(analyst_bp)
app.register_blueprint(anomalies_bp)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/healthz")
def healthz():
    return jsonify({"status": "ok", "service": "ProcBlock_AI Python API"})


# ── CORS (dev) ────────────────────────────────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
    return response


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e.description)}), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": str(e.description)}), 404

@app.errorhandler(500)
def server_error(e):
    logger.exception("Unhandled server error")
    return jsonify({"error": "Internal server error"}), 500


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting ProcBlock_AI Python API on port {port}")
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
