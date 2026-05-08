import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Any


class SupplyChainAnomalyDetector:
    def __init__(self, contamination: float = 0.1):
        self.model = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
        self.scaler = StandardScaler()
        self.is_fitted = False

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame()
        features["transit_hours"] = (
            pd.to_datetime(df["dispensation_timestamp"]) - pd.to_datetime(df["intake_timestamp"])
        ).dt.total_seconds() / 3600
        features["quantity"] = df["quantity"].astype(float)
        features["intake_hour"] = pd.to_datetime(df["intake_timestamp"]).dt.hour.astype(float)
        return features

    def fit(self, df: pd.DataFrame) -> None:
        features = self._engineer_features(df)
        scaled_features = self.scaler.fit_transform(features)
        self.model.fit(scaled_features)
        self.is_fitted = True

    def detect(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if not self.is_fitted:
            raise ValueError("Model must be fitted before detection.")
        features = self._engineer_features(df)
        scaled_features = self.scaler.transform(features)
        predictions = self.model.predict(scaled_features)
        scores = self.model.score_samples(scaled_features)
        anomalies = []
        for idx, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1:
                row = df.iloc[idx]
                anomaly_score = abs(score)
                severity = "high" if anomaly_score > 0.5 else "medium" if anomaly_score > 0.3 else "low"
                anomalies.append({
                    "id": f"anom-{idx}",
                    "type": "stockout" if severity == "high" else "custody",
                    "severity": severity,
                    "message": f"Anomaly: {row.get("commodity", "Unknown")} at {row.get("facility_id", "Unknown")}",
                    "location": row.get("hub_region", "Unknown Hub"),
                    "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                    "status": "active",
                    "score": round(anomaly_score, 4),
                })
        return sorted(anomalies, key=lambda x: x["score"], reverse=True)
