# Evidence

> Measurements and estimates the project's decisions rest on. Each file says plainly which it is. Nothing here is a claim of coverage or correctness unless it names the command that produced it.

| File | What it is | Kind | Status |
|---|---|---|---|
| [2026-10-16-p0-census.md](2026-10-16-p0-census.md) | The P0 coverage census: 53 KSSM topics against the Kit's micro-component kinds, with counts and a first-vertical ranking | **Estimate** (one annotator, from topic names and hints, no textbook opened) | Awaiting the owner's review |
| [2026-10-16-chatgpt-ui-research.md](2026-10-16-chatgpt-ui-research.md) | How ChatGPT's apps UI works (Apps SDK, MCP Apps, A2UI, AG-UI) and what it means for the Mark 3 pipeline | **Research from search summaries**, not primary pages; lists the pages to read locally. Covers the Apps SDK only (scope correction added 2026-10-21) | Done |
| [2026-10-28-w16-paid-measurement.md](2026-10-28-w16-paid-measurement.md) | The planner with the apparatus bench on the 14-question breadth set, and the planner v7 fix | **Paid measurement**, $1.1122 of an approved $1.50; small samples after the fix | Done |
| [2026-11-01-speed-visual-deploy-research.md](2026-11-01-speed-visual-deploy-research.md) | Where generation time goes, what the labs look like, deploy options, and a comparison with ChatGPT and Gemini | **Mixed**: measured from local traces, labs looked at, outside sources; estimates marked. No paid call | Done; decisions open |
| [2026-10-21-chatgpt-intelligent-ui-rea.md](2026-10-21-chatgpt-intelligent-ui-rea.md) | ChatGPT's Intelligent UI (GPT-6) versus the Apps SDK, a findings ledger by evidence type, and a static REA analysis of a public look-alike (OpenUI Lang 1.0.1) | **Mixed**: OpenAI release notes (primary), press, one competitor's reverse engineering (unverified), local static analysis of third-party packages. No live ChatGPT capture | Done; live capture still open |

The census file is generated: edit `eval/census/census.py`, then run `uv run python eval/census/census.py --write-report`. A test fails if the file is stale. The topic list is `data/kssm_topics.json`, ported from Synapse v3 with its provenance recorded in the file.
