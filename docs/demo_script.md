# Showing the monitor in an interview (5 minutes)

1. **Frame (30s).** "Manual competitor tracking across q-comm and e-pharmacy
   is hours of app-hopping per week. I built a small agent that collects the
   shelf, detects what moved, and drafts the weekly brief I would otherwise
   assemble by hand. This is a personal prototype on synthetic data."
2. **Overview tab (1m).** Share of assortment by owner, availability trend.
   Point at pin-code granularity: "a stockout is a pin-code event, not a
   national average."
3. **Signals tab (1.5m).** Walk the high-severity feed: competitor promo push
   on Zepto, own-brand OOS in Gurgaon, an NPI first listing, an MRP revision.
   Mention debouncing and transparent thresholds: "rules I can defend, not a
   black box."
4. **Brief tab (1.5m).** Show the generated what/why/next draft. Stress the
   review step: "the agent drafts, the analyst disposes - hypotheses are
   labelled as hypotheses."
5. **Architecture close (30s).** "Collection sits behind one schema seam, so
   the same pipeline runs on live feeds. The LLM is one swappable component;
   the value is in the signal definitions and the review loop."

## If asked "is this live?"
No - it's a prototype on synthetic data. The collection seam, signal engine
and review workflow are the real design; live collectors are the roadmap item.

## If asked "does this give market share?"
No. Price and assortment signals show the shelf. Offtake, NSV and share need
sales data joined in - the roadmap names that explicitly.
