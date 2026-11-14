# Adapted from Azimlearning/Arcana-v2, api/llm/models.py @ 21c6dcf5. Read in full. Anthropic ids only until a live
# provider exists (P3); OpenRouter ids are not carried over because nothing uses them yet.
"""Model ids per provider and tier (heavy, standard, light).

Ids and prices were checked against the provider's models and pricing pages on 2026-10-16 and again on 2026-10-18 (models overview: the three ids
below are the Claude API ids and aliases, each retiring no sooner than September 2027; see pricing.py). Re-check both before a paid run: they change.
"""

from __future__ import annotations

from api.llm.types import Tier

ANTHROPIC_MODELS: dict[Tier, str] = {
    "heavy": "claude-opus-5-5",
    "standard": "claude-sonnet-5-5",
    "light": "claude-haiku-5-5",
}

DEFAULT_FREE_CHAIN: tuple[str, ...] = (
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "google/gemma-4-31b-it:free",
    "inclusionai/ling-3.2-flash:free",
)
"""The free OpenRouter models tried, in this order, before the paid Anthropic provider (D-83). Checked against openrouter.ai/api/v1/models on 2026-11-14: all
three are listed with a zero price and room for the output we ask for. Free models are withdrawn and renamed without notice: override the list with LLM_FREE_CHAIN
(at most MAX_FREE_CHAIN ids, each ending ':free') and re-check it before a demo."""
MAX_FREE_CHAIN = 3
