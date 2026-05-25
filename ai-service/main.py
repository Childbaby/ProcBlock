"""
ZAMMSA ProcBlock — AI Insight Module
FastAPI microservice for anomaly detection and geospatial mapping.
"""

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from anomaly_detector import SupplyChainAnomalyDetector
from geospatial_mapper import GeospatialMapper
from deidentifier import sanitize_logs, compute_facility_aggregates

app = FastAPI(
    title="ProcBlock AI Insight API",
    description="Anonymized analytics for ZAMMSA medical supply chain",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Load sample data
DATA_PATH = "data/sample_logs.csv"

try:
    raw_logs = pd.read_csv(DATA_PATH)
    clean_logs = sanitize_logs(raw_logs)
    aggregate_data = compute_facility_aggregates(clean_logs)
    print(f"Loaded {len(clean_logs)} anonymized facility records")
except Exception as e:
    print(f"Warning: Could not load sample data: {e}")
    clean_logs = pd.DataFrame()
    aggregate_data = pd.DataFrame()

# Initialize models
detector = SupplyChainAnomalyDetector(contamination=0.1)
mapper = GeospatialMapper()

if not clean_logs.empty:
    detector.fit(clean_logs)


@app.get("/")
def root():
    return {
        "service": "ProcBlock AI Insight Module",
        "status": "operational",
        "records_loaded": len(clean_logs),
        "anonymization": "enabled",
    }


@app.get("/anomalies")
def get_anomalies():
    """Return detected anomalies from supply chain data."""
    if clean_logs.empty:
        return {"anomalies": [], "total_records": 0, "message": "No data available"}

    try:
        anomalies = detector.detect(clean_logs)
        return {
            "anomalies": anomalies,
            "total_records": len(clean_logs),
            "anomaly_count": len(anomalies),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/geospatial")
def get_geospatial():
    """Return hub distribution and supply flow data."""
    if clean_logs.empty:
        return {"hubs": [], "flows": [], "message": "No data available"}

    try:
        hub_stats = mapper.analyze_distribution(clean_logs)
        flow_data = mapper.get_flow_data(clean_logs)
        return {
            "hubs": hub_stats,
            "flows": flow_data,
            "total_hubs": len(hub_stats),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "healthy", "deidentifier": "active"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
