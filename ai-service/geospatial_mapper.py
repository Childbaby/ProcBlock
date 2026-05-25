"""
Geospatial Mapper for ZAMMSA ProcBlock

Visualizes medicine distribution across Zambia's 7 regional hubs.
Processes only aggregate facility data — zero patient information.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any


# Zambia's 7 Regional Medical Hubs
ZAMBIA_HUBS = [
    {"id": "hub-1", "name": "Lusaka Central Hub", "region": "Lusaka"},
    {"id": "hub-2", "name": "Kitwe District Hub", "region": "Copperbelt"},
    {"id": "hub-3", "name": "Livingstone Hub", "region": "Southern"},
    {"id": "hub-4", "name": "Chipata Hub", "region": "Eastern"},
    {"id": "hub-5", "name": "Solwezi Hub", "region": "North-Western"},
    {"id": "hub-6", "name": "Mansa Hub", "region": "Luapula"},
    {"id": "hub-7", "name": "Mongu Hub", "region": "Western"},
]


class GeospatialMapper:
    def __init__(self):
        self.hubs = {hub["id"]: hub for hub in ZAMBIA_HUBS}

    def analyze_distribution(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze medicine distribution across hubs."""
        hub_stats = []

        for hub in ZAMBIA_HUBS:
            hub_data = df[df["hub_region"] == hub["region"]]

            if len(hub_data) > 0:
                stock_level = self._calculate_stock_level(hub_data)
                transaction_count = len(hub_data)
                last_update = hub_data["intake_timestamp"].max()

                # Determine hub status
                if transaction_count == 0:
                    status = "offline"
                elif stock_level < 30:
                    status = "degraded"
                else:
                    status = "online"
            else:
                stock_level = 0
                transaction_count = 0
                last_update = "No data"
                status = "offline"

            hub_stats.append({
                "id": hub["id"],
                "name": hub["name"],
                "region": hub["region"],
                "status": status,
                "stockLevel": round(stock_level, 1),
                "transactionCount": transaction_count,
                "lastUpdate": str(last_update) if last_update != "No data" else last_update,
            })

        return hub_stats

    def _calculate_stock_level(self, hub_data: pd.DataFrame) -> float:
        """Estimate stock level as % of intake not yet dispensed.

        Uses dispensation_timestamp presence as a deterministic proxy:
        records without a dispensation timestamp are still in stock.
        Falls back to full-stock (100%) when the column is absent.
        """
        total = len(hub_data)
        if total == 0:
            return 0.0

        if "dispensation_timestamp" in hub_data.columns:
            dispensed_count = int(hub_data["dispensation_timestamp"].notna().sum())
        else:
            # No dispensation column — conservatively treat as all in-stock
            dispensed_count = 0

        remaining_ratio = (total - dispensed_count) / total
        return round(max(0.0, min(100.0, remaining_ratio * 100)), 1)

    def get_flow_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate supply flow data between hubs."""
        flows = []

        source_hubs = df["hub_region"].unique()

        for source in source_hubs:
            source_data = df[df["hub_region"] == source]
            total_shipments = len(source_data)

            if total_shipments > 0:
                flows.append({
                    "hub": source,
                    "totalShipments": total_shipments,
                    "totalQuantity": int(source_data["quantity"].sum()),
                    "avgTransitHours": round(
                        (
                            pd.to_datetime(source_data["dispensation_timestamp"])
                            - pd.to_datetime(source_data["intake_timestamp"])
                        ).dt.total_seconds().mean() / 3600,
                        2,
                    ),
                })

        return flows
