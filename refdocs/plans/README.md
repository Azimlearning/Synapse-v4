# Plans

> **MANDATORY:** Before implementing any non-trivial feature, a plan document must exist in this folder.
> A plan covers **what** and **why**: goal, scope, constraints, risks, definition of done.
> The **how** and **in what order** belongs in `refdocs/execution/`. When the two merge, both stop being read.

## Naming convention

`YYYY-MM-DD-<slug>.md`: the date the plan was written, then a short kebab-case slug.

**The execution doc uses the identical filename** in `refdocs/execution/`. Same date, same slug: that mirroring is how you find a plan's other half without opening anything. If a plan gets superseded, write a new one and mark the old row Superseded; don't rewrite history in place.

## Required sections in every plan

1. **Why this exists:** the problem, in the user's terms
2. **What's already covered:** what needs no work, so nobody rebuilds it
3. **Scope:** what's in, and what's explicitly out *with reasons*
4. **Approach:** the shape of the solution
5. **Risks & unknowns:** with honest confidence levels. "I read this library's docs" and "I think this library does that" are different rows.
6. **Definition of done:** phrased as observable facts, not intentions

## Index

Add a row when you write a plan. Update the status when it moves: a stale index is how a project ends up with three plans for the same thing.

Status vocabulary: `Draft` · `In progress` · `Done` · `Blocked` · `Superseded` · `On hold`

| File | Description | Status |
|---|---|---|
| [2026-10-16-p0-walking-skeleton-census.md](2026-10-16-p0-walking-skeleton-census.md) | P0: walking skeleton and coverage census | Done (the owner delegated the vertical choice; the census stays an estimate) |
| [2026-10-16-v4-enhancement-audit.md](2026-10-16-v4-enhancement-audit.md) | Audit of every wanted v4 enhancement against the PRD | Done |
| [2026-10-16-p1-kit-core-and-verification.md](2026-10-16-p1-kit-core-and-verification.md) | P1: Kit core, provenance, L1 to L3, L6 baseline, isolation spike | Done (cloud scope) |
| [2026-10-16-p1b-models-track.md](2026-10-16-p1b-models-track.md) | P1b: trained local models (multi-head router) and the misconception matcher | Done (cloud scope) |
| [2026-10-16-p3-mark3-pipeline.md](2026-10-16-p3-mark3-pipeline.md) | P3: the layered, skeleton-first Mark 3 pipeline (plan as data, assembler, slot fills, fail checks, prompt packs) | Done on fakes (cloud scope); the first paid run is waiting on the owner |
| [2026-10-16-p2-p5-p6-evidence-library-pedagogy.md](2026-10-16-p2-p5-p6-evidence-library-pedagogy.md) | P2, P5, P6 cloud scope: evidence engine, library and lifecycle, pedagogy components (written after the build) | Done (cloud scope) |
| [2026-10-16-p4-kit-expansion.md](2026-10-16-p4-kit-expansion.md) | P4: eight new science models and eleven verified Environments across three subjects (written after the build) | Done (cloud scope) |
| [2026-10-18-p2-real-corpus-and-citations.md](2026-10-18-p2-real-corpus-and-citations.md) | P2 on the real corpus: ingestion, citation registry, 16 `kit-verified` Environments (D-36) | In progress (OCR and catalogue matching, tasks 4, 9, 10, remain; see W7) |
| [2026-11-14-free-model-chain.md](2026-11-14-free-model-chain.md) | Up to three free OpenRouter models in front of the paid Anthropic key (D-83) | Built, awaiting the owner's key and a live check |
| [2026-10-28-w16-generation-upgrade.md](2026-10-28-w16-generation-upgrade.md) | The generation upgrade: 26 apparatus parts with motion on 25 benches, planner v6, the Free lane drawing a lab on by default, Malay drafts on (D-66 to D-68) | Done (2026-10-28) |
| [2026-10-28-w15-illustrated-scenes.md](2026-10-28-w15-illustrated-scenes.md) | Illustrated scenes for the graph-only labs: refraction and pressure first (D-65) | Two done (2026-10-28) |
| [2026-10-28-w14-ui-review.md](2026-10-28-w14-ui-review.md) | A UI review of the running app and its fixes: lab layout, phone top bar, dark-mode line art (D-64) | Done (2026-10-28) |
| [2026-10-27-w13-malay-router-and-gpu-job.md](2026-10-27-w13-malay-router-and-gpu-job.md) | Malay questions for the router (a glossary guard) and the trained-model GPU job (D-63) | Guard done; GPU job written, not run (2026-10-27) |
| [2026-10-27-w12-bahasa-melayu.md](2026-10-27-w12-bahasa-melayu.md) | Bahasa Melayu: translated Environments, the EN/BM switch, the review rule (D-62) | Done as drafts; no reviewer yet (2026-10-27) |
| [2026-10-27-w7b-models-and-lab-anatomy.md](2026-10-27-w7b-models-and-lab-anatomy.md) | Five more models and Plans, the lab anatomy and takeover layout, name matching (D-59 to D-61) | Done on fakes (2026-10-27) |
| [2026-10-27-w7-local-content-and-evidence.md](2026-10-27-w7-local-content-and-evidence.md) | Orbit citations, printed pages, offline lab report, cache accounting, five models and four Plans (D-54 to D-58) | Done on fakes (2026-10-27); smoke and reseed open |
| [2026-10-25-p7-cloud-followups.md](2026-10-25-p7-cloud-followups.md) | Known constants (PLAN-020), CI, friendly citations, static gallery (D-47) | Done (2026-10-25); CI not yet run on GitHub |
| [2026-10-25-w5a-misconception-probe.md](2026-10-25-w5a-misconception-probe.md) | W5a: the misconception probe, host text offered above a measured threshold (D-48) | Done (2026-10-25); three of five entries |
| [2026-10-25-w5b-amali-report.md](2026-10-25-w5b-amali-report.md) | W5b: the Amali lab report from recorded rows, through a bridge message (D-49) | Done (2026-10-25); Stage only |
| [2026-10-25-w5c-exam-mirror.md](2026-10-25-w5c-exam-mirror.md) | W5c: the exam mirror, marked by key words in the browser (D-50) | Done (2026-10-25); six items, no teacher review |
| [2026-10-24-w4-interaction-kit-and-benches.md](2026-10-24-w4-interaction-kit-and-benches.md) | W4: the interaction Kit and the V3 benches rebuilt as Kit parts (D-44, D-45, D-46) | Stages 1 (Hooke mass bench), 2 (titration bench) and 3 (fermentation bench) done; stage 4 not started |
| [2026-10-23-w3-v3-ui-port.md](2026-10-23-w3-v3-ui-port.md) | W3: the web UI on Synapse V3's design and style, with honest labels (D-38, D-43) | Done (2026-10-23); no real-phone or screen-reader pass yet |
| [2026-10-23-w2-instant-library.md](2026-10-23-w2-instant-library.md) | W2: the library is consulted first; a covered topic is answered with no model call (D-42) | Done (2026-10-23); flag-evicts-and-regression-eval still open |
| [2026-10-22-w1-l4-and-free-lane.md](2026-10-22-w1-l4-and-free-lane.md) | W1: the L4 wording check and the Free lane (D-41) | Done on fakes (2026-10-23); the paid measurements are W8 |
| [2026-10-22-completion-roadmap.md](2026-10-22-completion-roadmap.md) | The umbrella roadmap W0 to W11: L4 and Free lane, library hits, V3 UI port, interaction Kit, pedagogy, reach, content, paid runs, trust and the deploy gate (D-38 to D-40) | In progress (W0 done; each later workstream gets its own pair) |
