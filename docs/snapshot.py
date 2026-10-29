"""Export a static HTML snapshot of the monitor (charts + brief) for sharing.
This is a visual snapshot of one run - the functioning app is app.py."""
from pathlib import Path
import pandas as pd
import plotly.express as px

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"

df = pd.read_csv(PROC / "snapshots_normalised.csv", parse_dates=["week"])
sig = pd.read_csv(PROC / "signals_latest.csv")
soa = pd.read_csv(PROC / "share_of_assortment.csv", parse_dates=["week"])
latest = df["week"].max()

def fig_html(fig):
    return fig.to_html(full_html=False, include_plotlyjs="cdn")

# 1. share of assortment, digestive health, latest
soa_f = soa.merge(df[["brand", "owner"]].drop_duplicates(), on="brand")
d = soa_f[(soa_f["category"] == "Oral Care") & (soa_f["week"] == latest)]
f1 = px.bar(d, x="platform", y="share_pct", color="owner", barmode="group",
            title="Share of assortment - Oral Care, latest week",
            labels={"share_pct": "share of listed SKUs (%)"})

# 2. availability trend
av = df.groupby(["week", "owner"], as_index=False)["in_stock"].mean()
av["availability_pct"] = 100 * av["in_stock"]
f2 = px.line(av, x="week", y="availability_pct", color="owner", markers=True,
             title="Availability trend by brand owner",
             labels={"availability_pct": "in-stock listings (%)"})

# 3. price trend oral care brands
d = df[df["brand"].isin(["Sensodyne", "Colgate Total", "Pepsodent"])]
g = d.groupby(["week", "brand"], as_index=False)["selling_price"].median()
f3 = px.line(g, x="week", y="selling_price", color="brand", markers=True,
             title="Selling price trend (median, Rs) - note the Zepto promo week",
             labels={"selling_price": "median selling price (Rs)"})

sev_order = {"high": 0, "medium": 1, "low": 2}
sig = sig.sort_values("severity", key=lambda s: s.map(sev_order))
rows = "".join(
    f"<tr class='{r.severity}'><td>{r.severity}</td><td>{r.type}</td><td>{r.category}</td>"
    f"<td>{r.platform}</td><td>{r.city}</td><td>{r.detail}</td></tr>"
    for r in sig.head(40).itertuples())

brief = (ROOT / "briefs" / f"weekly_brief_{latest.date().isoformat()}.md").read_text()
brief_html = "".join(
    f"<h3>{l[2:]}</h3>" if l.startswith("## ") else
    f"<h2>{l[2:]}</h2>" if l.startswith("# ") else
    f"<li>{l[2:]}</li>" if l.startswith("- ") else
    f"<p>{l}</p>" if l.strip() else ""
    for l in brief.splitlines() if not l.startswith("|"))

html = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Competitor Monitor - run snapshot</title>
<style>
body {{ font-family: -apple-system, 'Segoe UI', sans-serif; margin: 24px auto; max-width: 1100px; color: #1a1a2e; padding: 0 12px; }}
h1 {{ margin-bottom: 0; }} .tag {{ color: #666; margin-top: 4px; }}
.kpis {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 18px 0; }}
.kpi {{ background: #f4f6fb; border-radius: 10px; padding: 12px 18px; min-width: 120px; }}
.kpi b {{ display: block; font-size: 24px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
td, th {{ border-bottom: 1px solid #e4e7ef; padding: 6px 8px; text-align: left; }}
tr.high td:first-child {{ color: #c0392b; font-weight: 700; }}
tr.medium td:first-child {{ color: #d68910; font-weight: 700; }}
.section {{ margin-top: 36px; }}
.brief {{ background: #fafbfd; border: 1px solid #e4e7ef; border-radius: 10px; padding: 8px 20px; }}
</style></head><body>
<h1>AI Competitor Monitor</h1>
<p class="tag">Run snapshot of {latest.date()} &middot; personal prototype &middot; <b>demo data: synthetic</b> &middot; the live app is a Streamlit dashboard; this page is a static export of one run.</p>
<div class="kpis">
<div class="kpi">SKUs tracked<b>{df['sku_id'].nunique()}</b></div>
<div class="kpi">Platforms<b>{df['platform'].nunique()}</b></div>
<div class="kpi">Pin codes<b>{df['pincode'].nunique()}</b></div>
<div class="kpi">Signals this week<b>{len(sig)}</b></div>
<div class="kpi">High severity<b>{(sig['severity']=='high').sum()}</b></div>
</div>
<div class="section">{fig_html(f1)}</div>
<div class="section">{fig_html(f2)}</div>
<div class="section">{fig_html(f3)}</div>
<div class="section"><h2>Detected signals (top 40 of {len(sig)})</h2>
<table><tr><th>severity</th><th>type</th><th>category</th><th>platform</th><th>city</th><th>detail</th></tr>{rows}</table></div>
<div class="section"><h2>Weekly brief (agent draft, human review retained)</h2>
<div class="brief">{brief_html}</div></div>
</body></html>"""

out = ROOT / "docs" / "snapshot.html"
out.write_text(html)
print("wrote", out, len(html), "bytes")
