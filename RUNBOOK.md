# AI Competitor Monitor - Local Demo Runbook

A working prototype of an AI-assisted competitor intelligence monitor for
consumer-health categories (oral care demo data). Built as a personal
portfolio project.

**What it is**
- A Python + Streamlit dashboard with a tool-using LLM investigator agent.
- Data pipeline turns raw weekly retail snapshots into normalised tables,
  detects price / promotion / assortment / availability signals, and tracks
  share-of-assortment.
- An LLM agent (Gemini free tier by default, OpenAI-compatible interface;
  Claude or other OpenAI-compatible providers also supported) investigates
  the week's signals: it chooses which tool queries to run, forms
  hypotheses (labelled as such), and drafts a weekly brief in which every claim cites the tool output backing it.
- A dynamic report tab exports a standalone HTML report built from the
  current dashboard filters.
- The rule-based signal detectors and the template brief are separate from
  the agent. The agent never fakes a run: without an API key it says so.

**What it is not**
- Not production software. All data is synthetic demo data (labelled as
  such), generated locally. No real retailer or employer data is used.
- A human reviews every brief before it would be shared. That review step
  is deliberate.

## Setup (about 5 minutes)

Requires Python 3.10+.

```bash
unzip ai-competitor-monitor-demo.zip
cd ai-competitor-monitor
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the dashboard

```bash
streamlit run app.py
```

Opens at http://localhost:8501 with five tabs:
1. **Overview** - category KPIs and weekly trends.
2. **Price & Promo** - competitor price moves and promotion intensity.
3. **Signals** - ranked anomaly list with severity.
4. **Agent run** - the LLM investigator (needs an API key, see below),
   plus the **Report output** section: one click builds a standalone HTML
   report from the current dashboard filters, with a human review/edit
   step before download.
5. **Weekly Brief** - the drafted weekly brief with a reviewed-markdown
   download.

The processed demo dataset ships in `data/processed/`. If the raw
snapshots in `data/snapshots/` are missing, the pipeline regenerates them
on first run - no manual step needed.

## Enable the investigator agent (free tier)

1. Get a free Gemini API key at https://aistudio.google.com/app/api-keys
   (no billing required; a key for this project, named
   "ai-competitor-monitor-demo-v3", already exists in this account).
2. Provide it without hardcoding:

```bash
export GEMINI_API_KEY="your-key-here"   # never commit this
streamlit run app.py
```

   Or put `GEMINI_API_KEY = "your-key-here"` in `.streamlit/secrets.toml`
   (gitignored) for local runs, or in the host's secrets UI when deployed.
3. Open the **Agent run** tab and click "Run investigation agent".
   The tool-call trace and the evidence-cited brief appear in ~5 seconds
   on the default `gemini-3.5-flash-lite` model. Set `GEMINI_MODEL` to
   override the model.

## Interview walkthrough (suggested flow)

1. Overview tab: frame the business question (what moved this week?).
2. Signals tab: show the ranked anomaly feed and severity.
3. Agent run tab: run the agent live - point out it *chooses its own
   queries* (tool calls visible in the trace) and that every claim cites
   the tool output backing it (tool-level citations, not unique row IDs).
4. Agent run tab, Report output section: build the HTML report from the current filters, show the review/edit step, download it.
5. Close on the review step: the agent drafts, a person approves.

## Repo layout

- `app.py` - Streamlit dashboard (five tabs).
- `src/pipeline.py` - raw snapshots to processed tables (regenerates
  missing demo data).
- `src/signals.py` - rule-based anomaly detectors.
- `src/agent.py` - tool-using LLM investigator loop.
- `src/brief.py` - template brief fallback (kept distinct from agent).
- `src/report.py` - dynamic HTML report builder.
- `data/generate_demo_data.py` - synthetic data generator.
- `docs/demo_script.md` - longer demo narrative; `docs/screenshots/` -
  dashboard screenshots.

Tested revision: local HEAD `db5fb5c` (matches GitHub `main` content,
private repo tooweeknd/ai-competitor-monitor, plus this runbook).
