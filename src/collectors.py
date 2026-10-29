"""Collection layer.

This prototype reads local snapshot CSVs. The seam is deliberate: a real
deployment swaps `load_snapshots` for collectors that pull platform pages,
retailer APIs or a data provider, landing rows in the SAME schema. Nothing
downstream (signals, brief, dashboard) changes when the source changes.
"""
from pathlib import Path
import pandas as pd

REQUIRED_COLS = {
    "week", "platform", "city", "pincode", "sku_id", "brand", "owner",
    "category", "variant", "pack_qty", "mrp", "selling_price",
    "discount_pct", "in_stock", "first_seen_week",
}

def load_snapshots(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"pincode": str})
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"snapshot file is missing columns: {sorted(missing)}")
    df["week"] = pd.to_datetime(df["week"])
    df["first_seen_week"] = pd.to_datetime(df["first_seen_week"])
    return df.sort_values(["week", "platform", "sku_id"]).reset_index(drop=True)
