# Environment Setup: Synapse v4

> **Security:** never commit a real value from this file. `.env*` is gitignored; `.env.example` carries the *names* with blank values and is committed.
> Never paste a real token into a plan, an execution doc, a changelog entry, or a chat transcript. If one leaks, rotate it: don't just delete the message.
> **Naming:** this file is about process settings (the `.env` file). It has nothing to do with the "Environment" artifact Synapse generates.

Last updated: 2026-10-16

---

## Required variables

| Variable | Required | Where to get it | Read by | Notes |
|---|---|---|---|---|
| `SYNAPSE_LLM_MODE` | Yes (defaults to `fake`) | Set by you: `fake` or `live` | API | `fake` uses a deterministic fake model and makes no network call. `live` is paid and needs the two rows below |
| `LLM_MONTHLY_CAP_USD` | Yes in `live` mode | Set by you, in US dollars | API LLM seam | Calls are refused before sending if they would exceed it. The API refuses to start in `live` mode without it |
| `LLM_TOTAL_CAP_USD` | No (recommended) | Set by you, in US dollars | API LLM seam | An ALL-TIME budget for the whole project, enforced beside the monthly cap: the monthly cap resets on the 1st, this does not. A call that would take the ledger file past it is refused before sending. The paid-run script shows it and counts it in what remains |
| `ANTHROPIC_API_KEY` | Yes in `live` mode | https://console.anthropic.com (API keys) | API | Server side only. Never `NEXT_PUBLIC_` |
| `NEXT_PUBLIC_API_BASE_URL` | Yes for the web app | Your API address, `http://localhost:8000` locally | Web | Public by design: it is a URL, not a secret |
| `PUBLIC_ORIGIN` | Yes | The origin the web app is served from, `http://localhost:3000` locally | API (CSP injection) | The artifact CSP names this origin explicitly (ADR D-06) |

## Optional variables

| Variable | Default if unset | What it changes |
|---|---|---|
| `OPENROUTER_API_KEY` | none | Turns on the free-model chain (D-83): up to three free OpenRouter models are tried before the paid Anthropic key. Free tier: 20 requests a minute and 50 a day (1000 a day once 10 credits have ever been bought). Only `:free` models are ever called |
| `LLM_FREE_CHAIN` | the three defaults in `api/llm/models.py` | Comma separated free model ids in the order to try them, at most three, each ending `:free`; `off` turns the free chain off. Free ids are withdrawn without notice: re-check them at `openrouter.ai/models?max_price=0`. Not a secret |
| `KIT_DIST_DIR` | `./packages/kit/dist` | Where the built Kit lives (`<semver>/core.js`, `manifest.json`). The API serves it at `/vendor/kit/` and the render harness reads it. Build it with `pnpm --filter @synapse/kit build` |
| `VERIFY_INTERACTION_SECONDS` | `10` | How long the render harness presses controls and inputs while verifying one Environment (the longer, the more conditional behaviour it can reach). Tests use `1`. Not a secret |
| `CORPUS_DIR` | none | A local folder of textbook text (one `.jsonl` per document, made by `api/evidence/ingest.py`). Never committed (rule 13). Unset means no citation can be verified, so `kit-verified` cannot be minted. Also holds `citations.json` (the quotations the committed pointer ids resolve to; local only). The API reads the corpus once per process: restart it after re-ingesting. Not a secret, but the contents are copyrighted |
| `FREE_LANE_ENABLED` | `false` | `true` lets a question the Kit cannot express get a whole page written by a model (the labelled Free lane, D-07 and D-41). It is shown as `model-checked` with a plain limits line, never `kit-verified` or `canonical`, and only after a second model has read its words and formulas. It needs live mode (the second reading is turned on only there), and each Free page costs a paid generation (up to 6,000 output tokens) and a paid reading. Every question the Kit cannot take is logged to `<DATA_DIR>/kit_gaps.jsonl` whether or not this is on. Not a secret |
| `STORE_ATTESTATION_KEY` | none | A secret string (32 or more random characters) that signs every stored Environment (HMAC-SHA256, A-19). Keep it OUTSIDE the data directory and out of git. Set: the delivery gate refuses any row without a valid signature, so a row written straight into the SQLite file is never delivered. Unset: rows are unsigned and the gate trusts the store (acceptable only while the API is single-operator and not public, D-11). Required at the deploy gate. Changing it makes every older row `unattested`, so re-verify after a rotation |
| `RATE_LIMIT_PER_MINUTE` | `20` | Questions one client address may ask per minute; above it `/ask` answers HTTP 429 `rate_limited`. `0` turns it off. Behind a proxy every client shares the proxy's address, so set the limit at the proxy as well. Not a secret |
| `DAILY_LIMIT_PER_CLIENT` | `200` | Questions one client address may ask per UTC day; above it `/ask` answers HTTP 429 `rate_limited`. `0` turns it off. There are no accounts, so an address stands for a session (D-11). Not a secret |
| `DAILY_LIMIT_TOTAL` | `0` | Questions the whole server answers per UTC day; `0` turns it off. Set it before any public deploy: it stops a crowd of addresses before the monthly spend cap does. Not a secret |
| `PROMPT_CACHING` | `false` | Ask the provider to cache the system prompt of every call (D-55). The ledger prices cache reads and writes, so turning it on cannot under-count spend, but the saving is not yet measured: leave it off until one measured run (the owner confirms its cost first). Not a secret |
| `MAX_CONCURRENT_ASKS` | `3` | How many questions are worked on at once (each may launch a browser to verify an Environment, so this bounds memory and CPU). Above it `/ask` answers 429. `0` turns it off. Not a secret |
| `DATA_DIR` | `./data` | Where local stores and the default spend ledger live |
| `LEDGER_PATH` | `<DATA_DIR>/ledger.db` | Overrides the spend ledger file. Keep ONE ledger so the monthly cap covers every run |
| `LOG_LEVEL` | `INFO` | API log verbosity |

---

## Setup

```bash
# Not runnable until P0 task 1 creates the workspace.
cp .env.example .env
# Edit .env. For development leave SYNAPSE_LLM_MODE=fake and no key is needed.
```

Surface notes: the API reads everything except `NEXT_PUBLIC_API_BASE_URL`. The web app reads only `NEXT_PUBLIC_*`. The web build must never see `ANTHROPIC_API_KEY`.

---

## Rules

- **Client-side bundles are public.** Anything inlined into a browser build is readable by anyone who opens devtools. A key that must stay secret goes through a server-side route, never into client code.
- **`.env.example` is the documentation.** Add the variable name there the moment you add the variable.
- **A missing required variable should fail loudly at startup**, with a message naming the variable and pointing here.
- **Rotate on exposure, not on suspicion of exposure.** If you can't prove a key never left the machine, treat it as leaked.
- **Paid runs need the owner's go.** Setting `SYNAPSE_LLM_MODE=live` is not permission to run an evaluation or an ingestion. State the projected amount first (CLAUDE.md rule 7).

## When a variable changes

Adding, renaming, or removing one means updating, in the same session: this file, `.env.example`, the deploy target's dashboard (if any), and a changelog entry.
