"""Signal engine: turns raw weekly snapshots into reviewable events.

Signal types
------------
price_move       selling-price change beyond PRICE_MOVE_PCT week over week
discount_shift   discount-depth change beyond DISCOUNT_SHIFT_PP percentage points
oos_event        in_stock flipped 1 -> 0 (and recovery 0 -> 1)
new_launch       SKU first seen on a platform in the latest week
assortment_gap   focus-brand category listed on a platform where a competitor
                 SKU exists but no focus-brand SKU does
share_shift      share-of-assortment change beyond SHARE_SHIFT_PP for a brand
"""
import pandas as pd

PRICE_MOVE_PCT = 3.0
DISCOUNT_SHIFT_PP = 5.0
SHARE_SHIFT_PP = 2.0

def _sev(pct_change: float) -> str:
    a = abs(pct_change)
    return "high" if a >= 10 else "medium" if a >= 5 else "low"

def share_of_assortment(df: pd.DataFrame) -> pd.DataFrame:
    """Brand share of listed SKUs per week/platform/category."""
    g = (df.groupby(["week", "platform", "category", "brand"])
           .size().rename("listings").reset_index())
    tot = g.groupby(["week", "platform", "category"])["listings"].transform("sum")
    g["share_pct"] = (100 * g["listings"] / tot).round(1)
    return g

def availability(df: pd.DataFrame) -> pd.DataFrame:
    """Availability % per week/platform/category (focus vs rest handled by caller)."""
    return (df.groupby(["week", "platform", "category"], as_index=False)
              .agg(availability_pct=("in_stock", lambda s: round(100 * s.mean(), 1))))

def detect_signals(df: pd.DataFrame, focus_owner: str) -> pd.DataFrame:
    weeks = sorted(df["week"].unique())
    latest, prev, prev2 = weeks[-1], weeks[-2], weeks[-3]
    cur = df[df["week"] == latest]
    prv = df[df["week"] == prev]
    prv2 = df[df["week"] == prev2]
    key = ["platform", "city", "pincode", "sku_id"]
    m = cur.merge(prv, on=key, suffixes=("", "_prev"))
    m = m.merge(prv2[key + ["in_stock"]].rename(columns={"in_stock": "in_stock_prev2"}), on=key, how="left")
    sig = []

    # price moves & discount shifts (SKU-location level)
    for _, r in m.iterrows():
        if r["mrp_prev"] and r["selling_price_prev"]:
            pct = 100 * (r["selling_price"] - r["selling_price_prev"]) / r["selling_price_prev"]
            if abs(pct) >= PRICE_MOVE_PCT:
                direction = "cut" if pct < 0 else "increase"
                sig.append(dict(type="price_move", severity=_sev(pct),
                    platform=r["platform"], city=r["city"], category=r["category"],
                    brand=r["brand"], owner=r["owner"], sku=r["sku_id"],
                    detail=(f"{r['brand']} {r['variant']}: price {direction} "
                            f"{pct:+.1f}% (Rs {r['selling_price_prev']:.0f} -> Rs {r['selling_price']:.0f}) "
                            f"on {r['platform']}, {r['city']}"),
                    focus=bool(r["owner"] == focus_owner)))
        dshift = r["discount_pct"] - r["discount_pct_prev"]
        if abs(dshift) >= DISCOUNT_SHIFT_PP:
            sig.append(dict(type="discount_shift", severity=_sev(dshift),
                platform=r["platform"], city=r["city"], category=r["category"],
                brand=r["brand"], owner=r["owner"], sku=r["sku_id"],
                detail=(f"{r['brand']} {r['variant']}: discount depth {dshift:+.1f}pp "
                        f"(now {r['discount_pct']:.0f}%) on {r['platform']}, {r['city']}"),
                focus=bool(r["owner"] == focus_owner)))
        prev2_stock = r["in_stock_prev2"] if not pd.isna(r["in_stock_prev2"]) else r["in_stock_prev"]
        # debounce: only flag a flip that held for two prior weeks (kills scanner noise)
        stable_prev = r["in_stock_prev"] == prev2_stock
        if r["in_stock"] != r["in_stock_prev"] and stable_prev:
            kind = "went out of stock" if r["in_stock"] == 0 else "back in stock"
            sig.append(dict(type="oos_event",
                severity="high" if r["in_stock"] == 0 and r["owner"] == focus_owner else "medium",
                platform=r["platform"], city=r["city"], category=r["category"],
                brand=r["brand"], owner=r["owner"], sku=r["sku_id"],
                detail=f"{r['brand']} {r['variant']} {kind} on {r['platform']}, {r['city']}",
                focus=bool(r["owner"] == focus_owner)))

    # new launches (latest week == first seen)
    nl = cur[cur["first_seen_week"] == latest]
    for (_, _), r in nl.groupby(["sku_id", "platform"]):
        r = r.iloc[0]
        sig.append(dict(type="new_launch", severity="high",
            platform=r["platform"], city="(multiple)", category=r["category"],
            brand=r["brand"], owner=r["owner"], sku=r["sku_id"],
            detail=f"New listing: {r['brand']} {r['variant']} appeared on {r['platform']}",
            focus=bool(r["owner"] == focus_owner)))

    # assortment gaps: category/platform where competitor is listed, focus owner is not
    cat_plat = cur.groupby(["category", "platform"])["owner"].apply(set).reset_index()
    for _, r in cat_plat.iterrows():
        if focus_owner not in r["owner"]:
            sig.append(dict(type="assortment_gap", severity="medium",
                platform=r["platform"], city="(all)", category=r["category"],
                brand="(focus portfolio)", owner=focus_owner, sku="-",
                detail=(f"No {focus_owner} listing in {r['category']} on {r['platform']} "
                        f"while competitors are listed"),
                focus=True))

    # share-of-assortment shift (platform/category/brand, latest vs prior)
    soa = share_of_assortment(df)
    a = soa[soa["week"] == latest].set_index(["platform", "category", "brand"])
    b = soa[soa["week"] == prev].set_index(["platform", "category", "brand"])
    joined = a.join(b, lsuffix="", rsuffix="_prev")
    for (plat, cat, brand), r in joined.iterrows():
        if pd.isna(r.get("share_pct_prev")):
            continue
        shift = r["share_pct"] - r["share_pct_prev"]
        if abs(shift) >= SHARE_SHIFT_PP:
            sig.append(dict(type="share_shift", severity=_sev(shift),
                platform=plat, city="(all)", category=cat, brand=brand,
                owner=cur[cur["brand"] == brand]["owner"].iloc[0] if (cur["brand"] == brand).any() else "",
                sku="-",
                detail=(f"{brand}: share of assortment in {cat} on {plat} "
                        f"{shift:+.1f}pp (now {r['share_pct']:.0f}%)"),
                focus=bool(brand and (cur["brand"] == brand).any()
                           and cur.loc[cur["brand"] == brand, "owner"].iloc[0] == focus_owner)))

    out = pd.DataFrame(sig)
    if not out.empty:
        sev_order = {"high": 0, "medium": 1, "low": 2}
        out["week"] = latest.date().isoformat()
        out = out.sort_values(["severity", "focus"], key=lambda s: s.map(sev_order) if s.name == "severity" else ~s)
    return out
