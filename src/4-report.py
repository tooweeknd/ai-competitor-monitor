"""Dynamic report builder: renders the CURRENT dashboard view (active filters)
as a standalone HTML report. Charts stay interactive (plotly via CDN)."""
import re
import pandas as pd
import plotly.express as px

def _fig(fig): return fig.to_html(full_html=False, include_plotlyjs="cdn")

def build_report(df, sig, brief_text, focus_owner, scope_str, brief_label="") -> str:
    empty = df.empty
    latest = df["week"].max() if not empty else pd.NaT
    cur = df[df["week"] == latest] if not empty else df
    focus_cur = cur[cur["owner"] == focus_owner]

    av = df.groupby(["week", "owner"], as_index=False)["in_stock"].mean()
    av["availability_pct"] = 100 * av["in_stock"]
    f1 = px.line(av, x="week", y="availability_pct", color="owner", markers=True,
                 title="Availability trend", labels={"availability_pct": "in-stock listings (%)"})

    g = df.groupby(["week", "brand"], as_index=False)["selling_price"].median()
    f2 = px.line(g, x="week", y="selling_price", color="brand", markers=True,
                 title="Selling price trend (median, Rs)")

    soa = (cur.groupby(["platform", "owner"]).size().rename("n").reset_index())
    tot = soa.groupby("platform")["n"].transform("sum")
    soa["share_pct"] = (100 * soa["n"] / tot).round(1)
    f3 = px.bar(soa, x="platform", y="share_pct", color="owner", barmode="group",
                title="Share of assortment - latest week", labels={"share_pct": "%"})

    sev_order = {"high": 0, "medium": 1, "low": 2}
    s = sig.sort_values("severity", key=lambda x: x.map(sev_order))
    rows = "".join(f"<tr class='{r.severity}'><td>{r.severity}</td><td>{r.type}</td>"
                   f"<td>{r.category}</td><td>{r.platform}</td><td>{r.city}</td>"
                   f"<td>{r.brand}</td><td>{r.detail}</td></tr>" for r in s.itertuples())

    def _md(l):
        l = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", l)
        return re.sub(r"_([^_]+)_", r"<em>\1</em>", l)
    brief_html = "".join(
        f"<h3>{_md(l[3:])}</h3>" if l.startswith("## ") else
        f"<h2>{_md(l[2:])}</h2>" if l.startswith("# ") else
        f"<li>{_md(l[2:])}</li>" if l.startswith("- ") else
        f"<p>{_md(l)}</p>" if l.strip() else ""
        for l in brief_text.splitlines() if not l.strip().startswith("|"))

    week_label = latest.date() if not empty else "no data in scope"
    if len(focus_cur):
        n_focus_avail = f"{100 * focus_cur['in_stock'].mean():.1f}%"
        focus_note = ""
    else:
        n_focus_avail = "n/a"
        focus_note = f" ({focus_owner} has no listings in the current filter scope)"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Competitor Monitor report - {week_label}</title>
<style>
body {{ font-family: -apple-system, 'Segoe UI', sans-serif; margin: 24px auto; max-width: 1100px; color: #1a1a2e; padding: 0 12px; }}
.kpis {{ display: flex; gap: 14px; flex-wrap: wrap; margin: 16px 0; }}
.kpi {{ background: #f4f6fb; border-radius: 10px; padding: 10px 16px; }}
.kpi b {{ display: block; font-size: 22px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 12.5px; }}
td, th {{ border-bottom: 1px solid #e4e7ef; padding: 5px 7px; text-align: left; vertical-align: top; }}
tr.high td:first-child {{ color: #c0392b; font-weight: 700; }}
tr.medium td:first-child {{ color: #d68910; font-weight: 700; }}
.brief {{ background: #fafbfd; border: 1px solid #e4e7ef; border-radius: 10px; padding: 8px 20px; }}
.tag {{ color: #666; }}
</style></head><body>
<h1>AI Competitor Monitor - report</h1>
<p class="tag">Week of {week_label} &middot; scope: {scope_str} &middot; <b>demo data: synthetic</b> &middot; generated from the live dashboard's current view</p>
<div class="kpis">
<div class="kpi">SKUs<b>{df['sku_id'].nunique()}</b></div>
<div class="kpi">Platforms<b>{df["platform"].nunique()}</b></div>
<div class="kpi">{focus_owner} availability (demo)<b>{n_focus_avail}</b><span class="tag">{focus_note}</span></div>
<div class="kpi">Signals<b>{len(sig)}</b></div>
<div class="kpi">High severity<b>{(sig['severity']=='high').sum()}</b></div>
</div>
{"" if empty else f"<h2>Availability</h2>{_fig(f1)}<h2>Prices</h2>{_fig(f2)}<h2>Assortment</h2>{_fig(f3)}"}
{"<p class='tag'>No listings in the current filter scope - charts omitted.</p>" if empty else ""}
<h2>Signals ({len(s)})</h2>
<table><tr><th>severity</th><th>type</th><th>category</th><th>platform</th><th>city</th><th>brand</th><th>detail</th></tr>{rows}</table>
<h2>Weekly brief (draft for review)</h2><p class="tag">{brief_label}</p><div class="brief">{brief_html}</div>
</body></html>"""
