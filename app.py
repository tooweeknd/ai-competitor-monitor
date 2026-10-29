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

st.set_page_config(page_title="AI Competitor Monitor", page_icon="📡", layout="wide")

st.title("📡 AI Competitor Monitor")
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

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Price & Promo", f"Signals ({len(sig)})", "Weekly Brief"])

with tab1:
    cur = f[f["week"] == latest]
    c1, c2, c3, c4, c5 = st.columns(5)
    n_focus_avail = 100 * cur.loc[cur["owner"] == FOCUS_OWNER, "in_stock"].mean()
    c1.metric("SKUs tracked", df["sku_id"].nunique())
    c2.metric("Platforms", df["platform"].nunique())
    c3.metric("Pin codes", df["pincode"].nunique())
    c4.metric(FOCUS_OWNER + " availability", f"{n_focus_avail:.1f}%")
    c5.metric("Signals this week", len(sig), delta=f"{(sig['severity'] == 'high').sum()} high", delta_color="inverse")

    st.subheader("Share of assortment by owner")
    soa_f = soa.merge(df[["brand", "owner"]].drop_duplicates(), on="brand")
    soa_f = soa_f[soa_f["category"].isin(cats) & soa_f["platform"].isin(plats)]
    cat_pick = st.selectbox("Category", sorted(soa_f["category"].unique()), key="soa_cat")
    d = soa_f[(soa_f["category"] == cat_pick) & (soa_f["week"] == latest)]
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
    brand_pick = st.multiselect("Brands", sorted(f["brand"].unique()),
                                default=["Sensodyne", "Colgate Total", "Pepsodent"])
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
                 .sort_values("severity"), use_container_width=True, height=420)
    st.caption("Severity is rule-based (size of move; OOS on focus brands ranks high). "
               "OOS flags are debounced: a flip must hold two prior weeks to fire.")

with tab4:
    st.subheader("Weekly brief - draft for review")
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
