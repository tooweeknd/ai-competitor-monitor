"""Generate 12 weeks of synthetic snapshot data with planted events in the
final weeks so the signal engine and brief have something real to find.

Run:  python data/generate_demo_data.py
Out:  data/snapshots/snapshots.csv
"""
import numpy as np
import pandas as pd
from pathlib import Path
from catalog import (SKUS, PLATFORMS, LOCATIONS, BASE_MRP, BRAND_OWNER)

rng = np.random.default_rng(42)
WEEKS = pd.date_range(end="2026-10-26", periods=12, freq="W-MON")
OUT = Path(__file__).parent / "snapshots"
OUT.mkdir(exist_ok=True)

# Which platforms list which categories (assortment logic, not random noise)
CAT_PLATFORM_OK = {
    "Oral Care": {"Blinkit", "Zepto", "Swiggy Instamart", "Amazon", "Flipkart Minutes"},
    "Digestive Health": {"Blinkit", "Zepto", "Swiggy Instamart", "Amazon", "Flipkart Minutes", "1mg", "PharmEasy"},
    "Pain Relief": {"Blinkit", "Zepto", "Swiggy Instamart", "Amazon", "1mg", "PharmEasy"},
    "Vitamins & Supplements": {"Blinkit", "Amazon", "Flipkart Minutes", "1mg", "PharmEasy"},
    "Nasal Care": {"Blinkit", "Zepto", "Amazon", "1mg", "PharmEasy"},
}

rows = []
first_seen = {}
for sku, brand, cat, variant, pack in SKUS:
    mrp = BASE_MRP[sku]
    for platform, _ in PLATFORMS:
        if platform not in CAT_PLATFORM_OK[cat]:
            continue
        # not every platform lists every SKU -> assortment gaps exist by design
        forced = (sku, platform) in {("VIT-CEN-W50", "Amazon"), ("VIT-SUP-D60", "Blinkit")}
        if not forced and rng.random() < 0.18 and not (brand in ("Sensodyne", "Eno", "Crocin") and platform in ("Blinkit", "Amazon")):
            continue
        # NPI (planted): Centrum Women launches on Amazon and Supradyn Daily
        # lands on Blinkit in the final week -> new_launch signals for the demo
        FORCE_LAUNCH = {("VIT-CEN-W50", "Amazon"): 11, ("VIT-SUP-D60", "Blinkit"): 11}
        launch_wk = FORCE_LAUNCH.get((sku, platform), 0)
        first_seen[(sku, platform)] = WEEKS[launch_wk]
        for city, pin in LOCATIONS:
            if rng.random() < 0.25:  # location-level listing gaps
                continue
            base_disc = rng.uniform(0.03, 0.22)
            for wi, wk in enumerate(WEEKS):
                if wk < WEEKS[launch_wk]:
                    continue
                disc = np.clip(base_disc + rng.normal(0, 0.01), 0, 0.45)
                price = mrp
                in_stock = int(rng.random() > 0.015)
                sponsored = int(rng.random() < 0.15)

                # ---- planted events ----
                # 1. Zepto runs a deep promo on Colgate Total in weeks 11-12
                if sku == "ORC-COL-TT200" and platform == "Zepto" and wi == 11:
                    disc = 0.34
                    sponsored = 1
                # 2. Sensodyne Repair & Protect goes OOS on Blinkit Gurgaon in week 12
                if sku == "ORC-SEN-RP100" and platform == "Blinkit" and city == "Gurgaon" and wi == 11:
                    in_stock = 0
                # 3. Dolo-650 cuts price on 1mg in week 12
                if sku == "PAI-DOL-650T15" and platform == "1mg" and wi == 11:
                    price = 30
                # 4. Instamart quietly widens Pepsodent discount in week 12
                if sku == "ORC-PEP-GC150" and platform == "Swiggy Instamart" and wi == 11:
                    disc = min(disc + 0.12, 0.45)
                # 5. Crocin 500 availability dip on PharmEasy Mumbai week 11 (recovers)
                if sku == "PAI-CRO-500T15" and platform == "PharmEasy" and city == "Mumbai" and wi == 10:
                    in_stock = 0
                # 6. Centrum Adults raises MRP on Amazon in week 12
                if sku == "VIT-CEN-A30" and platform == "Amazon" and wi == 11:
                    price = int(mrp * 1.08)

                rows.append({
                    "week": wk.date().isoformat(), "platform": platform,
                    "platform_kind": dict(PLATFORMS)[platform],
                    "city": city, "pincode": pin, "sku_id": sku, "brand": brand,
                    "owner": BRAND_OWNER[brand], "category": cat,
                    "variant": variant, "pack_qty": pack, "mrp": price,
                    "selling_price": round(price * (1 - disc), 2),
                    "discount_pct": round(disc * 100, 1),
                    "in_stock": in_stock, "sponsored": sponsored,
                    "rating": round(np.clip(rng.normal(4.2, 0.25), 3.2, 4.9), 1),
                    "review_count": int(np.exp(rng.normal(6, 1.2))),
                    "first_seen_week": first_seen[(sku, platform)].date().isoformat(),
                })

df = pd.DataFrame(rows)
df.to_csv(OUT / "snapshots.csv", index=False)
print(f"wrote {len(df):,} rows -> {OUT/'snapshots.csv'}  ({df['week'].nunique()} weeks, "
      f"{df['sku_id'].nunique()} SKUs, {df['platform'].nunique()} platforms)")
