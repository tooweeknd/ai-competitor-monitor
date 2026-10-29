"""Investigator agent: a tool-using LLM loop that examines the week's data,
forms hypotheses and drafts the brief with evidence citations.

This is the agentic path. It ONLY runs with a configured LLM key - without
one it refuses rather than faking agent behavior with templates.

Supported (OpenAI-compatible chat-completions APIs):
  OPENAI_API_KEY                       (api.openai.com, model gpt-4o-mini)
  GROQ_API_KEY                         (api.groq.com, model llama-3.3-70b-versatile)
  GEMINI_API_KEY / GOOGLE_API_KEY      (generativelanguage.googleapis.com, gemini-3.5-flash-lite; override via GEMINI_MODEL)
  ANTHROPIC_API_KEY                    (native messages API, claude-sonnet-4-5)

Every claim in the draft cites evidence rows returned by the tools, so a
reviewer can check each statement against the underlying data.
"""
from __future__ import annotations
import json, os
import pandas as pd

MAX_STEPS = 10

def _tools(df, sig):
    def get_price_history(brand, platform=None):
        d = df[df["brand"].str.lower() == brand.lower()]
        if platform: d = d[d["platform"].str.lower() == platform.lower()]
        g = d.groupby(["week", "sku_id", "variant"], as_index=False)["selling_price"].median()
        return g.tail(30).to_dict("records")

    def compare_discounts(category=None):
        d = df[df["week"] == df["week"].max()]
        if category: d = d[d["category"] == category]
        g = d.groupby(["platform", "brand"], as_index=False)["discount_pct"].mean()
        return g.round(1).to_dict("records")

    def check_availability(brand=None):
        d = df if brand is None else df[df["brand"].str.lower() == brand.lower()]
        latest = d[d["week"] == d["week"].max()]
        oos = latest[latest["in_stock"] == 0][["platform", "city", "pincode", "brand", "variant"]]
        return {"availability_pct": round(100 * latest["in_stock"].mean(), 1),
                "oos_listings": oos.to_dict("records")}

    def get_signals(type=None, severity=None):
        s = sig
        if type: s = s[s["type"] == type]
        if severity: s = s[s["severity"] == severity]
        return s[["severity", "type", "category", "platform", "city", "brand", "detail"]].head(25).to_dict("records")

    def assortment_share(category, platform=None):
        d = df[(df["week"] == df["week"].max()) & (df["category"] == category)]
        if platform: d = d[d["platform"] == platform]
        g = d.groupby(["platform", "owner"]).size().rename("listings").reset_index()
        tot = g.groupby("platform")["listings"].transform("sum")
        g["share_pct"] = (100 * g["listings"] / tot).round(1)
        return g.to_dict("records")

    fns = {"get_price_history": get_price_history, "compare_discounts": compare_discounts,
           "check_availability": check_availability, "get_signals": get_signals,
           "assortment_share": assortment_share}
    schemas = [
        {"name": "get_price_history", "description": "Weekly median selling price per SKU for a brand (optionally one platform).", "params": {"brand": "str (required)", "platform": "str (optional)"}},
        {"name": "compare_discounts", "description": "Latest-week average discount % by platform and brand (optionally one category).", "params": {"category": "str (optional)"}},
        {"name": "check_availability", "description": "Latest availability % and current out-of-stock listings with pin codes (optionally one brand).", "params": {"brand": "str (optional)"}},
        {"name": "get_signals", "description": "Detected signal rows with evidence details; filter by type or severity.", "params": {"type": "str (optional)", "severity": "str (optional)"}},
        {"name": "assortment_share", "description": "Share of listed SKUs by brand owner for a category (optionally one platform).", "params": {"category": "str (required)", "platform": "str (optional)"}},
    ]
    return fns, schemas

SYSTEM = """You are a competitive-intelligence analyst agent for a consumer-health
company (focus portfolio owner: Haleon). Investigate this week's competitor
data using ONLY the provided tools. Work like an analyst:
1. Pull the week's high-severity signals first.
2. For each material one, gather corroborating evidence with the other tools
   (price history, discount benchmarks, availability, assortment share).
3. Then draft a weekly brief: What happened / Why it might be happening
   (hypotheses, labelled as such) / What next.
Rules: every claim must cite the evidence it came from as [tool: key fields].
Never invent numbers. If evidence is thin, say so. Under 400 words. The data
is a synthetic demo set - say so once at the top."""

def _openai_client():
    from openai import OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAI(), "gpt-4o-mini"
    if os.environ.get("GROQ_API_KEY"):
        return OpenAI(base_url="https://api.groq.com/openai/v1"), "llama-3.3-70b-versatile"
    gem = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gem:
        # Free-tier keys created after the 2.x retirement no longer serve
        # gemini-2.x; 3.5-flash-lite answers in ~1s so the live loop stays demo-able.
        # Override with GEMINI_MODEL (e.g. gemini-3.8-flash for deeper reasoning).
        model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
        return OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                      api_key=gem), model
    return None, None

def run_investigation(df, sig, focus_owner="Haleon", trace=print):
    """Run the agent loop. `trace` receives each step for the dashboard's live view.
    Returns (brief_markdown, trace_lines). Raises RuntimeError if no key."""
    fns, schemas = _tools(df, sig)
    lines = []
    def log(s): lines.append(s); trace(s)

    client, model = _openai_client()
    if client is None and not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("No LLM key configured. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, "
                           "GROQ_API_KEY or GEMINI_API_KEY. The agent does not fake a run without one.")

    tool_prompt = SYSTEM + "\n\nAvailable tools:\n" + "\n".join(
        f"- {s['name']}({s['params']}): {s['description']}" for s in schemas) + \
        "\n\nTo call a tool, reply with exactly one line: TOOL <name> <json args>. " \
        "When you have enough evidence, reply with the final brief starting with: BRIEF"

    if client is not None:
        log(f"[agent] provider=openai-compatible model={model}")
        msgs = [{"role": "system", "content": tool_prompt},
                {"role": "user", "content": f"Investigate this week for {focus_owner}. Start."}]
        for step in range(MAX_STEPS):
            r = client.chat.completions.create(model=model, messages=msgs, temperature=0.2)
            txt = (r.choices[0].message.content or "").strip()
            if txt.startswith("```"):
                txt = txt.strip("`").lstrip("json").strip()
            if txt.startswith("BRIEF"):
                log("[agent] draft complete")
                return txt[5:].strip().lstrip(":").strip(), lines
            if txt.startswith("TOOL "):
                rest = txt[len("TOOL "):]
                name, _, argstr = rest.partition(" ")
                try:
                    args = json.loads(argstr) if argstr.strip() else {}
                    result = fns[name.strip()](**args)
                except Exception as e:
                    result = {"error": str(e)}
                log(f"[tool {step+1}] {name.strip()}({args}) -> {json.dumps(result, default=str)[:400]}")
                msgs += [{"role": "assistant", "content": txt},
                         {"role": "user", "content": "Tool result:\n" + json.dumps(result, default=str)[:6000]}]
            else:
                msgs += [{"role": "assistant", "content": txt},
                         {"role": "user", "content": "Call a tool (TOOL <name> <json>) or finish with BRIEF."}]
        return "Agent hit step limit before drafting. Trace kept for review.", lines

    # Anthropic native path
    import anthropic
    log("[agent] provider=anthropic model=claude-sonnet-4-5")
    msgs = [{"role": "user", "content": tool_prompt + f"\n\nInvestigate this week for {focus_owner}. Start."}]
    ac = anthropic.Anthropic()
    for step in range(MAX_STEPS):
        r = ac.messages.create(model="claude-sonnet-4-5", max_tokens=2000, messages=msgs)
        txt = "".join(b.text for b in r.content if b.type == "text")
        if txt.startswith("BRIEF"):
            log("[agent] draft complete")
            return txt[5:].strip().lstrip(":").strip(), lines
        if txt.startswith("TOOL "):
            _, name, _, argstr = txt.partition("TOOL ")
            name, _, argstr = name.partition(" ")
            try:
                args = json.loads(argstr) if argstr.strip() else {}
                result = fns[name.strip()](**args)
            except Exception as e:
                result = {"error": str(e)}
            log(f"[tool {step+1}] {name.strip()}({args}) -> {json.dumps(result, default=str)[:400]}")
            msgs += [{"role": "assistant", "content": txt},
                     {"role": "user", "content": "Tool result:\n" + json.dumps(result, default=str)[:6000]}]
        else:
            msgs += [{"role": "assistant", "content": txt},
                     {"role": "user", "content": "Call a tool (TOOL <name> <json>) or finish with BRIEF."}]
    return "Agent hit step limit before drafting. Trace kept for review.", lines
