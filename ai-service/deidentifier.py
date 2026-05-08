"""
De-identification Logic for ZAMMSA ProcBlock AI Module
"""

import pandas as pd

FORBIDDEN_COLUMNS = [
    "patient_name",
    "patient_id",
    "prescriber_name",
    "prescriber_license",
    "personal_health_info",
]


def validate_schema(df: pd.DataFrame) -> bool:
    columns = [col.lower() for col in df.columns]
    for forbidden in FORBIDDEN_COLUMNS:
        if forbidden in columns:
            raise ValueError(f"FORBIDDEN COLUMN: '{forbidden}'")
    return True


def sanitize_logs(df: pd.DataFrame) -> pd.DataFrame:
    validate_schema(df)
    safe_columns = [col for col in df.columns if col.lower() not in FORBIDDEN_COLUMNS]
    return df[safe_columns]


def compute_facility_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    df_copy = df.copy()
    return df_copy.groupby(["facility_id", "hub_region", "commodity"]).agg(
        total_quantity=("quantity", "sum"),
        transaction_count=("quantity", "count"),
    ).reset_index()
