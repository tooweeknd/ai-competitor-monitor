"""AI Competitor Monitor - demo dashboard.

Run:  streamlit run app.py
Reads the pipeline outputs (run `python -m src.pipeline` first, or use the
button below). Demo data is synthetic.
"""
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from data.catalog import FOCUS_OWNER, PLATFORMS

ROOT = Path(__file__).resolve().parent
PROC = ROOT / "data" / "processed"

st.set_page_config(page_title="AI Competitor Monitor", layout="wide")

st.title("AI Competitor Monitor")
st.caption("Personal prototype · consumer-health DCommerce · **demo data: synthetic** · "
           "agent drafts, human reviews")

if st.sidebar.button("▶ Re-run pipeline"):
    from src.pipeline import run
    with st.spinner("collecting → signals → brief…"):
        st.sidebar.success(run())

try:
    df = pd.read_csv(PROC / "snapshots_normalised.csv", parse_dates=["week", "first_seen_week"], dtype={"pincode": str})
    sig = pd.read_csv(PROC / "signals_latest.csv")
    soa = pd.read_csv(PROC / "share_of_assortment.csv", parse_dates=["week"])
except FileNotFoundError:
    st.error("No pipeline output yet. Run `python data/generate_demo_data.py` then `python -m src.pipeline`.")
    st.stop()

latest = df["week"].max()
focus = df["owner"] == FOCUS_OWNER

# ---------------- sidebar filters ----------------
st.sidebar.header("Filters")
cats = st.sidebar.multiselect("Category", sorted(df["category"].unique()), default=sorted(df["category"].unique()))
plats = st.sidebar.multiselect("Platform", sorted(df["platform"].unique()), default=sorted(df["platform"].unique()))
cities = st.sidebar.multiselect("City", sorted(df["city"].unique()), default=sorted(df["city"].unique()))
f = df[df["category"].isin(cats) & df["platform"].isin(plats) & df["city"].isin(cities)]
_all_cities = len(cities) == df["city"].nunique()
_city_mask = sig["city"].isin(cities) | (sig["city"].isin(["(all)", "(multiple)"]) if _all_cities else False)
sig_f = sig[sig["category"].isin(cats) & sig["platform"].isin(plats) & _city_mask]
_scope_str = (f"categories: {', '.join(cats)} ({len(cats)}/{df['category'].nunique()}) | "
              f"platforms: {', '.join(plats)} ({len(plats)}/{df['platform'].nunique()}) | "
              f"cities: {', '.join(cities)} ({len(cities)}/{df['city'].nunique()})")
import hashlib as _hl
def _content_hash(_f, _s):
    h = _hl.sha1()
    h.update(pd.util.hash_pandas_object(_f, index=False).values.tobytes() if len(_f) else b"empty-f")
    h.update(pd.util.hash_pandas_object(_s, index=False).values.tobytes() if len(_s) else b"empty-s")
    return h.hexdigest()[:12]
_fp = f"{_scope_str} | week {latest.date()} | content {_content_hash(f, sig_f)}"
_agent_stale = bool(st.session_state.get("agent_brief")) and st.session_state.get("agent_fp") != _fp

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Price & Promo", f"Signals ({len(sig)})", "Agent run", "Weekly Brief"])

with tab1:
    cur = f[f["week"] == latest]
    c1, c2, c3, c4, c5 = st.columns(5)
    fa1 = cur.loc[cur["owner"] == FOCUS_OWNER, "in_stock"]
    c1.metric("SKUs tracked", f["sku_id"].nunique())
    c2.metric("Platforms", f["platform"].nunique())
    c3.metric("Pin codes", f["pincode"].nunique())
    c4.metric(FOCUS_OWNER + " availability (demo)", f"{100 * fa1.mean():.1f}%" if len(fa1) else "n/a")
    c5.metric("Signals this week", len(sig), delta=f"{(sig['severity'] == 'high').sum()} high", delta_color="inverse")
    st.caption("All figures on this page are computed from synthetic demo data - not real Haleon or competitor performance.")

    st.subheader("Share of assortment by owner")
    soa_f = soa.merge(df[["brand", "owner"]].drop_duplicates(), on="brand")
    soa_f = soa_f[soa_f["category"].isin(cats) & soa_f["platform"].isin(plats)]
    if soa_f.empty:
        st.info("No assortment data in the current filter scope.")
        d = soa_f
    else:
        cat_pick = st.selectbox("Category", sorted(soa_f["category"].unique()), key="soa_cat")
        d = soa_f[(soa_f["category"] == cat_pick) & (soa_f["week"] == latest)]
    if not d.empty:
        fig = px.bar(d, x="platform", y="share_pct", color="owner", barmode="group",
                     labels={"share_pct": "share of listed SKUs (%)"},
                     title=f"{cat_pick} - latest week")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Availability trend")
    av = (f.groupby(["week", "owner"], as_index=False)["in_stock"].mean())
    av["availability_pct"] = 100 * av["in_stock"]
    fig = px.line(av, x="week", y="availability_pct", color="owner", markers=True,
                  labels={"availability_pct": "in-stock listings (%)"})
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Selling-price trend (median across locations)")
    _brand_opts = sorted(f["brand"].unique())
    _brand_def = [b for b in ["Sensodyne", "Colgate Total", "Pepsodent"] if b in _brand_opts]
    brand_pick = st.multiselect("Brands", _brand_opts, default=_brand_def)
    d = f[f["brand"].isin(brand_pick)]
    plat_pick = st.selectbox("Platform", ["(all)"] + sorted(f["platform"].unique()), key="pp")
    if plat_pick != "(all)":
        d = d[d["platform"] == plat_pick]
    g = d.groupby(["week", "brand"], as_index=False)["selling_price"].median()
    fig = px.line(g, x="week", y="selling_price", color="brand", markers=True,
                  labels={"selling_price": "median selling price (Rs)"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Discount depth - latest week")
    d = f[f["week"] == latest].groupby(["platform", "brand"], as_index=False)["discount_pct"].mean()
    fig = px.density_heatmap(d, x="platform", y="brand", z="discount_pct", histfunc="avg",
                             color_continuous_scale="Reds",
                             labels={"discount_pct": "avg discount (%)"})
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Detected signals - latest week")
    sev = st.multiselect("Severity", ["high", "medium", "low"], default=["high", "medium"])
    typ = st.multiselect("Type", sorted(sig["type"].unique()), default=sorted(sig["type"].unique()))
    only_focus = st.checkbox("Only focus-portfolio flags")
    s = sig[sig["severity"].isin(sev) & sig["type"].isin(typ)]
    if only_focus:
        s = s[s["focus"]]
    st.dataframe(s[["severity", "type", "category", "platform", "city", "brand", "detail"]]
                 .sort_values("severity"), use_container_width=True, height=420,
                 column_config={"detail": st.column_config.TextColumn(width="medium")})
    if s.empty:
        st.info("No signals match the current filters.")
    else:
        pick = st.selectbox("Inspect full signal", range(len(s)),
                        format_func=lambda i: f"[{s.iloc[i]['severity']}] {s.iloc[i]['type']} - {s.iloc[i]['brand']} - {s.iloc[i]['platform']}")
        r = s.iloc[pick]
        st.info(f"**{r['type']}** ({r['severity']}) - {r['category']} / {r['brand']} / {r['platform']} / {r['city']}\n\n{r['detail']}")
    st.caption("Severity is rule-based (size of move; OOS on focus brands ranks high). "
               "OOS flags are debounced: a flip must hold two prior weeks to fire.")

with tab4:
    st.subheader("Agent investigation - live run")
    import os
    have_key = any(os.environ.get(k) for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"])
    if not have_key:
        st.warning("No LLM API key configured. The agent does not fake a run without one - "
                   "set OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY or GEMINI_API_KEY and rerun. "
                   "The Signals and Weekly Brief tabs show the rule-based detectors and template draft, "
                   "which are separate from this agent.")
    else:
        st.caption("The agent chooses what to investigate, calls data tools, then drafts an evidence-linked brief. Every tool call is shown.")
        if f.empty:
            st.info("No data in the current filter scope - widen the sidebar filters to run the agent.")
        elif st.button("Run investigation agent"):
            from src.agent import run_investigation
            trace_box = st.empty()
            lines = []
            def t(line):
                lines.append(line)
                trace_box.code("\n".join(lines), language="text")
            with st.spinner("Agent investigating..."):
                try:
                    brief_md, _ = run_investigation(f, sig_f, trace=t)
                    st.session_state["agent_brief"] = brief_md
                    st.session_state["agent_scope"] = _scope_str
                    st.session_state["agent_fp"] = _fp
                except Exception as e:
                    st.error(str(e))
    if st.session_state.get("agent_brief"):
        st.divider()
        if _agent_stale:
            st.warning("This agent draft was produced for a different scope/data state "
                       f"({st.session_state.get('agent_scope', 'unknown')}). "
                       "It will NOT be used in the report until you rerun the agent on the current filters.")
        st.markdown("### Agent draft brief (unreviewed)")
        st.markdown(st.session_state["agent_brief"])

    st.divider()
    st.subheader("Report output")
    st.caption("Builds a standalone report from the CURRENT filters - what you see is what the report carries.")
    if st.session_state.get("report_fp") and st.session_state["report_fp"] != _fp:
        for k in ("report_draft", "report_label", "report_html", "report_fp"):
            st.session_state.pop(k, None)
        st.caption("Filters or data changed - the previous report draft was discarded. Build a fresh one.")
    if st.button("Build report from current view"):
        from src.report import build_report
        from src.brief import template_brief
        cur_f = f[f["week"] == latest]
        fa = cur_f.loc[cur_f["owner"] == FOCUS_OWNER, "in_stock"]
        kpis_f = {"skus": f["sku_id"].nunique(), "platforms": f["platform"].nunique(),
                  "locations": f["pincode"].nunique(),
                  "focus_avail": round(100 * fa.mean(), 1) if len(fa) else "n/a",
                  "n_signals": len(sig_f), "n_high": int((sig_f["severity"] == "high").sum())}
        if st.session_state.get("agent_brief") and not _agent_stale:
            btext = st.session_state["agent_brief"]
            blabel = "LLM agent draft - investigated scope: " + st.session_state.get("agent_scope", "full dataset")
        else:
            btext = template_brief(sig_f, latest.date().isoformat(), FOCUS_OWNER, kpis_f)
            blabel = "Rule-based template brief, regenerated for the current filter scope (no LLM involved)"
            if _agent_stale:
                blabel += " | a stale agent draft for a different scope was deliberately NOT used"
        st.session_state["report_draft"] = btext
        st.session_state["report_label"] = blabel
        st.session_state["report_fp"] = _fp
    if st.session_state.get("report_draft"):
        st.markdown("**Human review** - edit the scoped draft before export:")
        edited = st.text_area("review", value=st.session_state["report_draft"],
                              height=220, label_visibility="collapsed",
                              key="report_review_" + str(abs(hash(_fp))))
        status = "human-edited before export" if edited != st.session_state["report_draft"] else "unedited draft"
        if st.button("Export report with reviewed brief"):
            from src.report import build_report as _br
            st.session_state["report_html"] = _br(
                f, sig_f, edited, FOCUS_OWNER, _scope_str,
                brief_label=st.session_state["report_label"] + f" | review status: {status}")
    if st.session_state.get("report_html"):
        st.download_button("Download report (.html)", st.session_state["report_html"],
                           file_name="competitor_monitor_report.html", mime="text/html")

with tab5:
    st.subheader("Weekly brief - draft for review")
    st.caption("Brief is generated from the full dataset (all categories, platforms, cities) for the latest week - sidebar filters do not change it.")
    briefs = sorted((ROOT / "briefs").glob("weekly_brief_*.md"))
    if not briefs:
        st.info("Run the pipeline to generate a brief.")
    else:
        pick = st.selectbox("Brief", [b.name for b in briefs], index=len(briefs) - 1)
        text = (ROOT / "briefs" / pick).read_text()
        st.markdown(text)
        st.divider()
        st.markdown("**Human review step** - edit before circulating:")
        edited = st.text_area("Edit draft", value=text, height=300, label_visibility="collapsed")
        st.download_button("Download reviewed brief (.md)", edited,
                           file_name=pick.replace(".md", "_reviewed.md"))
