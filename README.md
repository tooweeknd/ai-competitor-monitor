# AI Competitor Monitor (personal prototype)

An end-to-end agent that watches competitor price and assortment signals across
quick commerce, marketplaces and e-pharmacy platforms, flags what moved, and
drafts a weekly brief for human review.

**Status: prototype, not a production system.** The shipped demo runs on
clearly labelled synthetic data. Human review is a deliberate step, not an
afterthought: the agent drafts, the analyst disposes.

## Why this exists

Manual competitor tracking in DCommerce means opening five to seven platform
apps, city by city, and eyeballing prices, discounts, availability and
assortment. The judgment is in the interpretation, not the collection. This
project automates the collection and first-pass reading so an analyst spends
their time on the "so what" and "what next".

## What it does

1. **Collect** (`src/collectors.py`) - loads weekly snapshots in a fixed schema
   (platform, city, pin code, SKU, MRP, selling price, discount, availability,
   sponsored flag, first-seen). The local-CSV seam is deliberate: swap in live
   collectors (platform pages, retailer APIs, a data provider) and nothing
   downstream changes.
2. **Detect signals** (`src/signals.py`) - rule-based detectors:
   - `price_move` - selling-price move beyond 3% week over week
   - `discount_shift` - discount-depth move beyond 5pp
   - `oos_event` - availability flips, debounced (a flip must hold two prior
     weeks to fire, which kills scanner noise)
   - `new_launch` - a SKU's first appearance on a platform (early NPI signal)
   - `assortment_gap` - categories where competitors are listed and the focus
     portfolio is absent
   - `share_shift` - share-of-assortment moves beyond 2pp
   Every signal carries a severity, a plain-English description and a
   focus-portfolio flag. Rules are transparent and tunable - thresholds are
   constants at the top of the file.
3. **Draft the weekly brief** (`src/brief.py`) - turns the signal table into a
   what-happened / why-it-might-be-happening / what-next brief. Two engines:
   - *template* (default): deterministic, offline, zero cost, reproducible
   - *LLM*: set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`
     and the same signals are summarised by a model (Gemini is reached via
     its OpenAI-compatible endpoint, so no extra SDK). Nothing leaves the
     machine unless you configure a key yourself.
4. **Review in the dashboard** (`app.py`) - Streamlit app with five views:
   overview KPIs and share/availability trends, price & promo cuts, the signal
   feed (filterable, severity-ranked), an **agent run** view where a
   tool-using LLM investigates the current signal table through explicit tool
   calls and drafts an evidence-cited brief (each claim cites the tool output
   behind it), and the weekly brief with an edit-and-download review step.
   A **report builder** exports the current filtered view - KPIs, charts,
   signals and the draft brief - as a standalone HTML file, after the same
   human review.

## Demo data

`data/generate_demo_data.py` builds 12 weeks of synthetic snapshots: consumer-
health categories (oral care, digestive health, pain relief, vitamins, nasal
care) across Blinkit, Zepto, Swiggy Instamart, Amazon, Flipkart Minutes, 1mg
and PharmEasy, in Gurgaon, Delhi, Mumbai and Bengaluru. Brand names are public
trademarks of their owners; every price, discount, rating and availability
value is invented for demonstration. Planted events in the final week (a
competitor promo push, an own-brand stockout, an NPI launch, an MRP revision)
give the signal engine something real to find, so the demo tells a story
instead of showing noise.

## Quickstart

```bash
pip install -r requirements.txt
python data/generate_demo_data.py   # synthetic snapshots
python -m src.pipeline              # collect -> signals -> brief
streamlit run app.py                # dashboard on localhost:8501
# optional, for the agent run tab (a free AI Studio key works):
export GEMINI_API_KEY=...
```

## Design choices that matter for real use

- **Consistent KPI definitions.** Prices are compared per pack, and the schema
  carries `pack_qty` so multipacks/virtual combos can be normalised to unit
  price before comparison - the classic source of fake "price drops".
- **Pin-code granularity.** Signals keep platform + city + pin code so an OOS
  flag is actionable ("Sensodyne R&P out on Blinkit, Gurgaon 122001") rather
  than a national average that hides it.
- **Debounce before alarm.** Two-week stability required before an
  availability flip fires. A monitor that cries wolf gets muted.
- **Hypotheses are labelled hypotheses.** The brief separates what moved
  (observed) from why it might have moved (to verify). Price and assortment
  alone do not yield offtake, NSV or market share - this tool watches the
  shelf; commercial impact needs sales data joined in.
- **Human review retained.** The brief is a draft with an edit step. The agent
  proposes; the analyst disposes.

## Roadmap (what production would add)

- Live collectors behind the existing schema seam, with per-platform
  politeness limits and robots/ToS compliance
- Scheduled runs (cron/GitHub Actions) with snapshot history in SQLite/DuckDB
- Alert routing (email/Slack) for high-severity signals
- Joining sell-through data to quantify commercial impact of detected moves
- Evaluation loop: analyst edits to the brief fed back as signal-quality labels
