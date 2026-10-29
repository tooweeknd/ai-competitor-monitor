"""End-to-end run: snapshots -> signals -> weekly brief.

Run:  python -m src.pipeline
Out:  data/processed/signals_latest.csv
      data/processed/share_of_assortment.csv
      data/processed/availability.csv
      briefs/weekly_brief_<week>.md
"""
from pathlib import Path
from data.catalog import FOCUS_OWNER
from src.collectors import load_snapshots
from src.signals import detect_signals, share_of_assortment, availability
from src.brief import make_brief

ROOT = Path(__file__).resolve().parent.parent

def run(snapshot_path: str | Path | None = None) -> dict:
    snapshot_path = snapshot_path or (ROOT / "data" / "snapshots" / "snapshots.csv")
    df = load_snapshots(snapshot_path)
    latest = df["week"].max()

    sig = detect_signals(df, FOCUS_OWNER)
    soa = share_of_assortment(df)
    avail = availability(df)

    focus_cur = df[(df["week"] == latest) & (df["owner"] == FOCUS_OWNER)]
    kpis = {
        "skus": int(df["sku_id"].nunique()),
        "platforms": int(df["platform"].nunique()),
        "locations": int(df[["city", "pincode"]].drop_duplicates().shape[0]),
        "focus_avail": round(100 * focus_cur["in_stock"].mean(), 1) if len(focus_cur) else None,
        "n_signals": int(len(sig)),
        "n_high": int((sig["severity"] == "high").sum()) if len(sig) else 0,
    }

    (ROOT / "data" / "processed").mkdir(parents=True, exist_ok=True)
    sig.to_csv(ROOT / "data" / "processed" / "signals_latest.csv", index=False)
    soa.to_csv(ROOT / "data" / "processed" / "share_of_assortment.csv", index=False)
    avail.to_csv(ROOT / "data" / "processed" / "availability.csv", index=False)
    df.to_csv(ROOT / "data" / "processed" / "snapshots_normalised.csv", index=False)

    brief, engine = make_brief(sig, latest.date().isoformat(), FOCUS_OWNER, kpis)
    (ROOT / "briefs").mkdir(exist_ok=True)
    path = ROOT / "briefs" / f"weekly_brief_{latest.date().isoformat()}.md"
    path.write_text(brief)
    return {"signals": len(sig), "high": kpis["n_high"], "brief": str(path), "engine": engine}

if __name__ == "__main__":
    print(run())
