# Adapted from Azimlearning/Arcana-v2, api/llm/pricing.py @ 21c6dcf5. Read in full. Changes: embeddings dropped (A-9), the
# figures are marked ASSUMED because they come from refdocs/synapse-v4-sources.md and are unchecked against the pricing page.
"""Cost estimates, in USD, used to enforce the monthly cap before a call is sent.

Prices are per million tokens (input, output), read from the provider's pricing page on 2026-10-16 (Opus 5.5 $4 and $20, Sonnet 5.5 $2 and
$10, Haiku 5.5 $0.10 and $0.50 up to 100,000 prompt tokens, Haiku 4.5 $1 and $5), and confirmed unchanged on 2026-10-18 (models overview and pricing
pages). Prompt caching is OFF by default (PROMPT_CACHING). The ledger knows its rates, so turning it on cannot under-count: a cache read is 5 percent of the base
input rate on Opus 5.5 and Sonnet 5.5 and 10 percent on Haiku 5.5, and a cache write costs 1.25 times the base rate (ASSUMED for the 5-minute cache: confirm it on the
pricing page, and the saving by one measured run, before relying on it). A model this table does not know is priced with no read discount. Before a call the cap
reserves the worst case, every input token as a write.
Re-check against the pricing page before a paid run. Estimates are deliberately conservative: input tokens are over-counted and output is assumed to run to
max_tokens. An unknown model is priced as the dearest one, so a typo can only over-reserve.
"""

from __future__ import annotations

import math
import re

from api.llm.types import LLMRequest

PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),  # prompts up to 100,000 tokens; ours are far below
    "claude-haiku-4-5": (1.0, 5.0),
}

_FALLBACK_PRICE = max(PRICES_PER_MTOK.values())

CACHE_READ_FRACTION: dict[str, float] = {
    "claude-opus-5-5": 0.05,
    "claude-sonnet-5-5": 0.05,
    "claude-haiku-5-5": 0.10,
    "claude-haiku-4-5": 0.10,  # ASSUMED: not read from the pricing page
}
CACHE_WRITE_MULTIPLIER = 1.25
"""ASSUMED (D-55): the 5-minute cache write is 1.25 times the base input rate. A higher figure here only makes the ledger more cautious."""

FREE_PROVIDERS = frozenset({"fake"})

_DATE_SUFFIX = re.compile(r"-\d{8}$")


def _normalise(model: str) -> str:
    """An alias for a model id: no provider prefix, dots as dashes, no dated-snapshot suffix."""
    return _DATE_SUFFIX.sub("", model.removeprefix("anthropic/").replace(".", "-"))


def price_for(provider: str, model: str) -> tuple[float, float]:
    if provider in FREE_PROVIDERS:
        return (0.0, 0.0)
    if provider == "openrouter" and (model.endswith(":free") or model == "openrouter/free"):
        return (0.0, 0.0)  # D-83: only free variants are ever built (the provider refuses any other id), so this can never under-count a paid model
    return PRICES_PER_MTOK.get(_normalise(model), _FALLBACK_PRICE)


def estimate_input_tokens(request: LLMRequest) -> int:
    """About one token per 3 characters: higher than the usual ~4, so it errs toward refusing."""
    chars = len(request.prompt) + len(request.system or "")
    return math.ceil(chars / 3)


def cost_usd(
    provider: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    *,
    assume_cache_writes: bool = False,
) -> float:
    """What a call cost. `tokens_in` counts ALL input tokens; `cache_read_tokens` and `cache_write_tokens` are parts of it. With neither this is the plain base-rate price.
    `assume_cache_writes` prices every input token as a cache write: the worst case, for a call whose usage is not known (an estimate, a timeout)."""
    price_in, price_out = price_for(provider, model)
    if assume_cache_writes:
        input_cost = tokens_in * price_in * CACHE_WRITE_MULTIPLIER
    else:
        read = min(max(cache_read_tokens, 0), tokens_in)
        write = min(max(cache_write_tokens, 0), tokens_in - read)
        fraction = CACHE_READ_FRACTION.get(_normalise(model), 1.0)
        input_cost = (tokens_in - read - write) * price_in + read * price_in * fraction + write * price_in * CACHE_WRITE_MULTIPLIER
    return (input_cost + tokens_out * price_out) / 1_000_000


def estimate_call_cost(provider: str, model: str, request: LLMRequest) -> float:
    """Worst case: the estimated input plus an output that fills max_tokens."""
    return cost_usd(provider, model, estimate_input_tokens(request), request.max_tokens, assume_cache_writes=request.cache_system)
