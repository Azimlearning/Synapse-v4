# Research: making Synapse faster, better looking and deployed, compared with ChatGPT's Intelligent UI

> Done 2026-11-01 at the owner's request. Research only: no product code changed and no paid call was made. Each finding says what supports it: **MEASURED** (the local traces in `data/traces.jsonl`, 128 questions, the last on 2026-10-29), **LOOKED AT** (labs from `data/environments.db` rendered here in Chromium), **READ** (the code), **SOURCE** (an outside page, linked at the end), **ESTIMATE** (arithmetic on the above, not yet run).

## 1. The short version

1. **A generated lab takes about 4 minutes, and most of that is avoidable.** The largest causes are Opus left on from the demo, and a first page that is written in full and then thrown away.
2. **Compose is already fast (about 24 seconds).** Free is the slow lane, and Free is the lane that answers "anything".
3. **The labs people see first are the weak ones.** The hand-built Kit labs look good. The Free labs bury the bench under text and are hard to read on a phone.
4. **OpenAI's advantage is that the interface appears while it is written.** Synapse's advantage is that the result is checked and hands-on. The goal is to get the first without giving up the second.
5. **"We are not a catalogue" is a fair claim only if Free is fast.** Today, the answer to an unexpected question takes minutes.

### Correction, same day, after the owner's reply

- **Sonnet is unproven, so section 2's Sonnet rows and A1 overstate it.** The traces hold 6 Sonnet Free pages (about 29 s each), and all 6 were refused: none reached a student as a Free lab. Every Free run after them is Opus, so the traces hold no finished Free run on Sonnet. The owner reports about 4 minutes on both models. A model switch alone is not the fix; the estimates of 90 s and 55 s are withdrawn.
- **The owner's direction: the library answers only a repeated question.** A question with a twist must be generated, reusing the Kit. Today 16 of 60 library hits come from a topic or name match (`api/pipeline/run.py`), which would stop. This changes D-42 and needs an ADR. The priority moves to one writer that combines Free and Kit parts and streams (B1 and B3).

## 2. Where the time goes (MEASURED)

| Path | Typical time | What it costs | Sample |
|---|---|---|---|
| Library hit | 0.15 s median, 0.85 s at p90 | $0 | 17 lookups with a timing |
| Compose | about 24 s (11.5 s of model calls, 12.3 s of browser checks) | about $0.05 | 31 runs |
| Free on Opus (the current demo setting) | about 4 min: 220 s median of model calls (175 to 429 s), plus about 15 to 20 s in the browser | about $0.50 to $1.03 | latest 11 runs |

Timing for one Free page:

| Writer | Median time | p90 | Median tokens out | Tokens per second | Calls |
|---|---|---|---|---|---|
| Opus 5.5 (`heavy`) | 98 s | 174 s | 10,394 | 107 | 22 |
| Sonnet 5.5 (`standard`) | 29 s | 32 s | 4,775 | 164 | 6 |

The Sonnet sample is small and comes from older prompts, so it says nothing yet about quality on `free.v7`.

### The four causes, largest first

**A. Opus writes far more than the page needs.** A stored Free page is 12,621 to 20,211 bytes, roughly 4,000 to 6,000 tokens (ESTIMATE). Opus bills a median of 10,394 tokens and up to about 20,000 per page. Opus always thinks and bills that as output (`api/llm/providers/anthropic.py`), so most of the gap is probably thinking, which the student never sees. This is an inference: the traces do not split thinking from text.

**B. Nearly every run writes the page twice.** 9 of the latest 11 Free runs wrote two or more pages. In the six newest runs, every retry shown was `too long`: a full page is written (up to 174 s), rejected by `wording.unread`, and written again. A check that runs after the writing wastes the entire wait. `api/pipeline/run.py:968` records only `why="too long"`, not which limit was hit (script length, 160 lines, or a 400-character line), so **the exact cause is not yet known**. The first fix is to record it.

**C. The Plan is written even when Free will lead.** On Opus it takes a median of 21 s, up to 50 s with a refusal and retry, before Free starts. It stays useful as the fallback (D-76), and on Sonnet it costs about 5 s.

**D. Ten seconds of every verification is a fixed wait.** `INTERACTION_SECONDS = 10.0` (`api/verify/render.py:36`) accounts for most of the 12.3 s median in Compose.

### What each lever could reach (ESTIMATE)

| Step | Free lab total | Note |
|---|---|---|
| Today (Opus, usually two pages) | about 240 s | MEASURED |
| Sonnet, still two pages | about 90 s | Quality must be tested |
| Sonnet, one page | about 55 s | Route 1 + explain 3 + plan 5 + page 29 + reader 3 + browser 15 |
| Plus a faster browser check | about 45 s | Only if the planted-defect rate holds |
| Free writer reuses Kit parts (section 6, item B3) | about 20 to 30 s | The page shrinks to about 1,500 to 2,500 tokens; not designed yet |

The first written words already reach the student within a few seconds, because the explanation streams before the lab starts.

## 3. Compared with ChatGPT and Gemini

An earlier note, `2026-10-21-chatgpt-intelligent-ui-rea.md`, grades the Intelligent UI sources. Nothing here comes from a live GPT-6 session.

| | ChatGPT Intelligent UI | Gemini generative UI | Synapse |
|---|---|---|---|
| How it is built | Library of native streamable components plus a compiler that runs during generation (SOURCE, attributed to OpenAI) | Model codes a full custom page, with tools (image generation, search), detailed instructions and post-processing (SOURCE) | Compose: JSON Plan over audited Kit. Free: a model-written page in a house frame |
| What the user sees during the wait | The interface appears in pieces. Model can answer while still thinking | Status messages and thinking steps (SOURCE, secondary) | Explanation, stage log, code as text. **No lab until it passes** |
| Speed claims | 44 percent sooner to *start* a web-search answer. No figure for a finished interface (SOURCE) | Paper's quality results are stated as "when ignoring generation speed" (SOURCE) | 24 s Compose, about 4 min Free (MEASURED) |
| Interaction | Sliders and forms run with no model call (SOURCE, competitor's reverse engineering, unverified) | Generated page runs in the browser | Same, plus drag-and-drop apparatus |
| Follow-up changes | Reported: UI actions can start a new turn from the UI's state (same unverified source) | Not checked | **None.** `/ask` takes no history or parent lab (READ) |
| Is it correct? | No public check found. Press advises users to verify figures (SOURCE) | Post-processors address "common issues". No science check described (SOURCE) | Browser run, drags, independent reference recomputation, textbook citation, visible label |
| Consistency | One design system everywhere (SOURCE) | Style configurable (SOURCE) | Two looks at present (section 4) |
| Curriculum | General. Its learning modules cover 70+ set concepts (SOURCE) | General | KSSM citations, Bahasa Melayu, exam mirror, lab report |
| Stated weakness | OpenAI: "work ahead to improve the model's design judgment and expand what it can create" (SOURCE) | Generation latency (SOURCE, secondary) | Speed, visuals on Free |

### What to take from this

- **Stream structure, not code.** Showing the page's source (D-79) is honest but means little to a 16-year-old. ChatGPT shows the *interface* forming. Section 6, item B1 is the closest version that respects the no-unverified rule.
- **Keep one design vocabulary.** OpenAI's catalogue is why its output looks like one product. The Kit can do this too, but the Free lane cannot call it today.
- **Grade design, not just correctness.** OpenAI graded generated interfaces for clarity, usefulness and completeness. Synapse's checks are strong on correctness and have almost nothing for layout or legibility.
- **Do not chase scale or speed parity.** Nobody can check a chatbot's numbers from its demo. Synapse can show its checks passing live. This is the one claim neither competitor makes publicly, though that is an absence in public sources, not proof about their internals.

### "We are not a catalogue"

Google frames generative UI the same way: users get tailored interfaces "rather than having to select from an existing catalog of applications". OpenAI's own March learning modules are, by contrast, a set list of 70+ concepts.

Synapse can claim this honestly with one wording: **"Ask anything. We build the experiment, then we tell you exactly how far it was checked."** Two facts need care:

- A wild question lands in Free, so its label is `model-checked`, never `kit-verified` (hard constraints 3 and 4). Saying so is a strength, because it is the provenance story.
- The library is a *cache of labs already built*, and it only answers when the question's content words are all covered (`library.uncovered`). Describing it that way is accurate. Calling it a catalogue undersells the product.

## 4. What the labs look like (LOOKED AT)

Rendered at 1280 and 360 px with reduced motion, offline, with the CSP removed so the picture could load. **Not reviewed:** motion, dragging, dark mode, the landing page.

| Measure | Free labs | Kit labs |
|---|---|---|
| Top of the drawing at 1280 x 800 | 575 px | 268 to 360 px |
| Top of the drawing at 360 x 740 | 1,162 to 1,242 px (the third screen) | 612 to 860 px |
| Page height at 360 px | 2,615 to 2,914 px | 2,335 to 2,500 px |

1. **The experiment comes after the reading.** Try this, Key idea, Predict and Steps all sit above the bench. On a phone the student scrolls past two screens of text to reach the thing that makes this a lab.
2. **Free drawings are unreadable on a phone.** The SVG scales to about 300 px and its labels become tiny. This falls short of hard constraint 10's intent, and no check catches it.
3. **Labels collide.** Pendulum: the ticks run together as "30°20°10°0°", and a line runs through the "0.10 kg" label. Planets (Kit): "Jupiter" overlaps the "Planet" axis title and Saturn's ring touches Jupiter.
4. **Two products.** Kit labs use a gold serif title and step chips. Free labs use a sans title and stacked cards.
5. **Scenes look flat where they should be striking.** The black hole sits on a near-white bench because `free.v7` rule 5 steers backgrounds to `var(--bench)`. The Kit's dark planets scene shows how much a real backdrop adds.
6. **Sparse benches.** Kit apparatus is clear but small inside a large empty card.
7. **No shared fonts inside the frame.** The app's fonts stop at the frame; the labs fall back to system fonts.

## 5. Deployment

**State (READ).** `Dockerfile`, `render.yaml` and `deploy/entrypoint.sh` exist, and the guide says they have never been run with Docker. The repo records no live URL, and Docker is not installed on this machine. D-75's waiver has ended (STATUS, 2026-10-31), so **hard constraint 12 applies again: a public URL needs the deploy gate met or a new owner waiver.** The last four CI runs on `main` failed or were cancelled: the most recent had a smoke timeout and a Python job cancelled at its 45-minute limit.

| Host for the API | Cost for 2 GB | For | Against |
|---|---|---|---|
| **Render Standard (recommended)** | about $25 a month (secondary sources; its own page gave no figure to the fetch) | Blueprint already written; Singapore; persistent disk | Blueprint unproven; 15-minute first boot |
| Fly.io | $13.39 shared, $33 performance-1x (Virginia prices; Singapore differs, not read) | Per-second billing; can stop when idle | New config; shared CPU may slow Chromium; a cold start at the wrong moment |
| Cloud Run | Pay per use | 60-minute request limit fits streaming | Instance disk does not persist (from general knowledge, not re-read), so the store and **the spend ledger** would be lost: unsafe without a database change |
| The laptop and a tunnel | $0 | Nothing to build | Rejected in D-75; keep only as the venue fallback |

Vercel stays for the web app; it cannot run the API (D-75).

Hardening before any URL:

- Get CI green first: a deploy from a failing `main` proves nothing.
- Build the library at image build, for a fixed origin, so boot takes seconds rather than 15 minutes. Labs are bound to one origin by their CSP, so the origin must be settled first.
- Add a shared access code, so a stranger cannot spend the cap. Today the only guards are per-address limits and the cap.
- Rehearse from a phone on mobile data, and keep a local run and a recording as the fallback.
- Confirm `GENERATION_TIER` on the host. `render.yaml` does not set it, so it defaults to `standard`.

**Open choice A-8.** Without the textbook corpus on the server, no deployed lab can earn `kit-verified`. That removes the strongest visible claim from the demo.

## 6. Recommended work, in dependency order

**A. Before anything else. Small, and everything else is measured against these.**

| # | Work | Why |
|---|---|---|
| A1 | Set `GENERATION_TIER=standard`, then a paid comparison on 10 questions against the stored Opus pages | Largest single saving; quality unknown |
| A2 | Record which limit `unread` hit, then stop a page as soon as the stream shows it cannot pass (over the limit, or a forbidden pattern) | Stops paying for a page already doomed. No check weakened |
| A3 | Bench first in `free_house.py`: title, Try this, then the bench and readouts. Predict stays before the first drag, Steps and Key idea move below or fold | Fixes the largest visual fault in one place, for every generated lab |
| A4 | Free drawing rules: dark or themed backdrops by subject, a minimum label size at 360 px, bigger apparatus | Prompt change, needs an eval delta |
| A5 | Layout checks in the verifier: text overlapping text, text outside the drawing, labels under a minimum rendered size. A failure feeds the existing retry | Catches items 2 and 3 of section 4 mechanically, in Kit and Free labs |
| A6 | CI green, then a Docker build in CI, then one Render deploy with the access code | Needs the owner's waiver decision first |

**B. Once A is green: the visible jump.**

| # | Work | Why |
|---|---|---|
| B1 | **Forming lab.** Show the Free sections in the shell as they stream: title, Predict (answerable while waiting), and the drawing as an inert picture marked "Draft, still being checked". The real lab replaces it after verification | The closest honest match to ChatGPT's streaming. **Needs the owner: see decision 3** |
| B2 | **Change this lab.** Follow-ups like "now do it on Mars" send the existing page and the request; the model returns only the changed sections, and all checks rerun | ChatGPT-style conversation and a great live demo; should be much faster than a new page. Needs a wire change |
| B3 | **Free can call the Kit.** Give the Free writer the drag handlers, 26 apparatus parts, graph and backdrops as library calls | Fewer tokens (faster), and Free labs gain the Kit's looks. The label stays `model-checked`. Needs a plan and a `kit-guardian` review |
| B4 | **Faster verification on a virtual clock.** Playwright's clock can fast-forward timers, so the 10 s wait may shrink to under a second, and could run far longer in virtual time | May also catch the listed `g-timer-60s-forge` miss. Accept only if the L6 rate does not fall (hard constraint 9) |
| B5 | Vendored fonts and a one-style pass across Kit and Free | Removes the two-products look. A Kit change, so it needs a relock |

**C. Later, after the current list.**

- **A design reader:** a cheap vision model scores a screenshot for clarity, usefulness and completeness, feeding the retry only. Reported, never the primary metric (hard constraint 9).
- **Scene language:** a small typed format of primitives (bodies, fluids, particles, forces, formulas) that streams and compiles part by part. This is the long-term answer to "not a catalogue, and fast": a catalogue of atoms, not of labs. It is the largest item here and should not start before B3 shows what the primitives need.
- **Prompt caching:** already built and off (`prompt_caching`). Measure it.

Not recommended: running Free and Compose in parallel (pays twice, already rejected in D-76), dropping the second reader to save 3 s, adopting OpenUI packages (install-time telemetry, see the 2026-10-21 note).

## 7. Decisions for the owner

1. **Paid comparison (A1).** Projected about $2, hard ceiling $3, for 10 questions on Sonnet. Not run. It needs a stated amount, and the current month's spend should be checked against the cap first.
2. **Deploy.** A new time-boxed waiver with an access code (recommended for demos) or the full gate. Also whether the corpus goes on the server (A-8).
3. **Draft view (B1).** This changes an earlier call. On 2026-10-22 the owner ruled out a "Not fully checked" draft view, and D-79 reads hard constraint 1 as "not rendered or run". An inert picture with no controls runs no generated code, but it does show an unverified drawing and words that the second reader has not yet read. Recommended, with a clear draft label, recorded as a new ADR.

## 8. Limits of this research

- The trace sample is one person's testing, across prompt versions, on a home connection. Free on Opus has 22 page calls; Free on Sonnet has 6, on older prompts.
- All times are server side; none measure what a student perceives.
- `ESTIMATE` rows have not been run.
- Render's and Fly's Singapore prices were not confirmed on their own pages.
- Secondary sources on Intelligent UI repeat each other, and the architecture details beyond "components plus compiler" rest on one competitor's reverse engineering.

## Sources (accessed 2026-11-01)

- [OpenAI: new ways to learn math and science in ChatGPT](https://openai.com/index/new-ways-to-learn-math-and-science-in-chatgpt)
- [TechRepublic: GPT-6 Intelligent UI](https://www.techrepublic.com/article/news-gpt-6-intelligent-ui-charts-forms/)
- [TechCrunch: ChatGPT is getting a lot more visual](https://techcrunch.com/2026/10/07/chatgpt-is-getting-a-lot-more-visual-with-the-launch-of-a-new-interface/)
- [Wikidocs: detailed Korean summary of OpenAI's announcement](https://wikidocs.net/blog/@jaehong/32854/)
- [CellCog: GPT-6 in ChatGPT](https://cellcog.ai/blog/gpt-6-intelligent-ui/) (a vendor with a stated interest)
- [OpenUI/Thesys: how ChatGPT Intelligent UI works](https://www.openui.com/blog/how-chatgpt-intelligent-ui-works) (a competitor's reverse engineering, unverified)
- [Google Research: Generative UI](https://research.google/blog/generative-ui-a-rich-custom-visual-interactive-user-experience-for-any-prompt/)
- [PPC Land: Gemini 3 in Search with model-designed interfaces](https://ppc.land/google-deploys-gemini-3-in-search-with-model-designed-interfaces/)
- [Playwright for Python: Clock](https://playwright.dev/python/docs/clock)
- [Fly.io pricing](https://docs.fly.io/about/pricing)
- [Cloud Run request timeout](https://docs.cloud.google.com/run/docs/configuring/request-timeout)
- [Render pricing summary, third party](https://temps.sh/blog/render-pricing-2026)
