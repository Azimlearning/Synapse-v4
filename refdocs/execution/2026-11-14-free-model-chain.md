# Execution: a chain of free OpenRouter models in front of the paid Anthropic key

> The how and the order for [the plan](../plans/2026-11-14-free-model-chain.md). Built 2026-11-14.

## Steps, in order, as done

1. Read the current OpenRouter docs (errors, streaming, limits, overview) and the live model list (`GET https://openrouter.ai/api/v1/models`, public, no key): 471 models, 17 free. Chose three for the default chain by size and room for output.
2. `api/llm/providers/openrouter.py`: `OpenRouterProvider(api_key, model)`. Refuses a model id that is not free. `complete()` posts to `/chat/completions`; with `on_text` it streams, skipping `:` comment lines, ending on `[DONE]`, treating a top-level `error` chunk as a failure, reading usage from the last chunk. Every failure is `transient`, `timeout` or `truncated`. A per-instance cool-down skips a failing model with no network call.
3. `api/llm/pricing.py`: an `openrouter` model ending `:free` (or `openrouter/free`) prices at zero.
4. `api/llm/ledger.py`: `reserve(0)` returns an empty reservation without checking a cap. A call that cannot cost anything is never refused, so a used-up cap still lets free models answer. The paid provider is refused as before.
5. `api/llm/service.py`: `fallback` may be a list. `would_fit` still prices the first provider, which is now free, so the pipeline's up-front budget check no longer refuses a run the free models can serve; the paid last resort is still refused at its own reservation.
6. `api/llm/models.py`: `DEFAULT_FREE_CHAIN` (three ids) and `MAX_FREE_CHAIN = 3`. `api/core/settings.py`: `LLM_FREE_CHAIN`, `free_chain()`, `free_chain_problem()`; live mode fails closed on more than three ids or any id that is not free.
7. `api/llm/factory.py`: live mode builds the free providers (when `OPENROUTER_API_KEY` is set) in front of the Anthropic provider. `api/app.py`: `/health` adds `llm_chain`.
8. Tests: `api/llm/providers/test_openrouter.py` (shape, errors never stop a run, cool-down, error in a 200 body, truncation, stream, mid-stream error) and five chain tests in `api/llm/test_service.py`.
9. `refdocs/guides/env_setup.md`, ADR D-83, changelog, plans index.

## Deviations

- The plan's first draft routed purposes separately. Not built: the owner asked for one chain; per-purpose routing waits for a measured verified rate per model.
- No attribution headers (`HTTP-Referer`, `X-Title`) are sent: they would name the project to a third party.

## How to run it

Put `OPENROUTER_API_KEY=...` in `.env` and restart the API. Optional: `LLM_FREE_CHAIN=model-a:free,model-b:free,model-c:free`, or `off` to go back to Anthropic only. Check `GET /health` for `llm_chain`, ask one question that is not in the library, then `GET /spend` for an `openrouter` row at $0.
