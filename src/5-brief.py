"""Weekly brief generator.

Two paths:
1. LLM path  - if OPENAI_API_KEY or ANTHROPIC_API_KEY is set, signals are
   summarised by the model into a what/why/next brief. Nothing is sent to any
   API unless a key is configured by the user.
2. Template path (default) - a deterministic brief built straight from the
   signal table. Zero cost, fully reproducible, works offline. This is what
   the demo runs on.

Either way the output is a DRAFT for human review - the dashboard keeps an
edit/approve step. The agent proposes; the analyst disposes.
"""
import json, os
import pandas as pd

def _fmt_signals_table(sig: pd.DataFrame, limit: int = 30) -> str:
    if sig.empty:
        return "No signals crossed thresholds this week."
    lines = ["| Severity | Type | Category | Signal |", "|---|---|---|---|"]
    for _, r in sig.head(limit).iterrows():
        lines.append(f"| {r['severity']} | {r['type']} | {r['category']} | {r['detail']} |")
    return "\n".join(lines)

def _collapse(sig: pd.DataFrame) -> pd.DataFrame:
    """One narrative line per (type, sku, platform): highest-severity example,
    with the affected-city count folded into the detail."""
    if sig.empty:
        return sig
    sev_rank = {"high": 0, "medium": 1, "low": 2}
    s = sig.copy()
    s["_r"] = s["severity"].map(sev_rank)
    out = []
    for (typ, sku, plat), grp in s.sort_values("_r").groupby(["type", "sku", "platform"], sort=False):
        r = grp.iloc[0].copy()
        cities = sorted(set(grp["city"]) - {"(all)", "(multiple)"})
        if len(cities) > 1:
            base = r["detail"].split(", " + cities[0])[0] if cities and r["detail"].endswith(cities[0]) else r["detail"]
            # strip the trailing single-city mention then generalise
            for c in cities:
                base = base.replace(", " + c, "")
            r["detail"] = f"{base} ({len(cities)} cities: {', '.join(cities[:4])}{'...' if len(cities) > 4 else ''})"
        out.append(r)
    return pd.DataFrame(out).sort_values("_r").drop(columns="_r")


def template_brief(sig: pd.DataFrame, week: str, focus_owner: str, kpis: dict) -> str:
    sig = _collapse(sig)
    hi = sig[sig["severity"] == "high"] if not sig.empty else sig
    focus_hits = sig[sig["focus"]] if not sig.empty else sig
    comp_moves = sig[(~sig["focus"]) & (sig["type"].isin(["price_move", "discount_shift", "new_launch", "share_shift"]))] if not sig.empty else sig

    what, why, nxt = [], [], []
    if not comp_moves.empty:
        top = comp_moves.head(4)
        what.append("Competitor moves this week:")
        what += [f"- {r['detail']}" for _, r in top.iterrows()]
    if not focus_hits.empty:
        what.append(f"\n{focus_owner} portfolio flags:")
        what += [f"- {r['detail']}" for _, r in focus_hits.head(4).iterrows()]
    if not what:
        what.append("- No material moves crossed the detection thresholds this week.")

    for _, r in hi.head(5).iterrows():
        if r["type"] == "oos_event" and "out of stock" in r["detail"]:
            why.append(f"- {r['detail']} - likely lost visibility and offtake for the affected pin codes; check if a competitor captured the slot (sponsored placements below).")
        elif r["type"] == "discount_shift":
            why.append(f"- {r['detail']} - consistent with a promo push; watch whether it holds next week (sustained = pricing stance, one-off = promo slot).")
        elif r["type"] == "new_launch":
            why.append(f"- {r['detail']} - early NPI signal; track rating/review build and any intro pricing over the next 2-4 weeks.")
        elif r["type"] == "price_move":
            why.append(f"- {r['detail']} - could be an MRP revision or a platform-level pricing test; confirm against other platforms.")
    if not why:
        why.append("- Signals were low severity; treat as watchlist items rather than drivers.")

    for _, r in hi.head(5).iterrows():
        if r["type"] == "oos_event" and r["focus"]:
            nxt.append(f"- Escalate availability issue: {r['detail']}. Confirm supply vs listing takedown before Friday trading review.")
        elif r["type"] == "assortment_gap":
            nxt.append(f"- Assess listing opportunity: {r['detail']}.")
        elif r["type"] in ("discount_shift", "price_move") and not r["focus"]:
            nxt.append(f"- Benchmark response for {r['category']} on {r['platform']}: hold, match, or promote around {r['brand']}.")
    nxt.append("- Keep watching medium/low signals; they auto-flag again if they persist or widen.")

    fa_txt = f"{kpis['focus_avail']}%" if isinstance(kpis.get('focus_avail'), (int, float)) else "n/a (no focus-brand listings in scope)"
    if not kpis.get("skus"):
        return f"""# Weekly Competitor Brief - week of {week}

_Draft generated from detected signals. Review before circulating. Demo data: synthetic._

## Snapshot
- No data available to evaluate under the current filter scope (0 listings, 0 signals).

## What happened
- Nothing to report: the current scope contains no listings, so there is no data to evaluate. This is an empty slice, not a quiet week.

## Why it might be happening (hypotheses to verify)
- Not applicable until the scope contains data.

## What next
- Widen the category/platform/city filters or load a week that has data, then regenerate.
"""
    return f"""# Weekly Competitor Brief - week of {week}

_Draft generated from detected signals. Review before circulating. Demo data: synthetic._

## Snapshot
- SKUs tracked: {kpis['skus']} | Platforms: {kpis['platforms']} | Locations: {kpis['locations']}
- Avg availability ({focus_owner}): {fa_txt} | Signals flagged: {kpis['n_signals']} ({kpis['n_high']} high)

## What happened
{chr(10).join(what)}

## Why it might be happening (hypotheses to verify)
{chr(10).join(why)}

## What next
{chr(10).join(nxt)}

## Full signal log (top 30)
{_fmt_signals_table(sig)}
"""

def llm_brief(sig: pd.DataFrame, week: str, focus_owner: str, kpis: dict) -> str | None:
    """Draft with an LLM if a key is configured; otherwise return None."""
    payload = json.dumps({
        "week": week, "focus_owner": focus_owner, "kpis": kpis,
        "signals": sig.head(40).to_dict("records") if not sig.empty else [],
    }, default=str)
    prompt = (
        "You are a competitive-intelligence analyst for a consumer-health company. "
        "Turn these detected signals into a concise weekly brief with sections "
        "'What happened', 'Why it might be happening (hypotheses to verify)', and "
        "'What next'. Be specific, name brands/platforms/categories, mark hypotheses "
        "as hypotheses, and keep it under 400 words. Data is synthetic demo data.\n\n"
        + payload)
    try:
        if os.environ.get("OPENAI_API_KEY"):
            from openai import OpenAI
            r = OpenAI().chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}], temperature=0.3)
            return r.choices[0].message.content
        if os.environ.get("ANTHROPIC_API_KEY"):
            import anthropic
            r = anthropic.Anthropic().messages.create(
                model="claude-sonnet-4-5", max_tokens=1200,
                messages=[{"role": "user", "content": prompt}])
            return r.content[0].text
    except Exception as e:  # fall back quietly; demo must not die on API issues
        print(f"[brief] LLM path failed ({e}); using template brief")
    return None

def make_brief(sig, week, focus_owner, kpis) -> tuple[str, str]:
    text = llm_brief(sig, week, focus_owner, kpis)
    if text:
        return text, "llm"
    return template_brief(sig, week, focus_owner, kpis), "template"
