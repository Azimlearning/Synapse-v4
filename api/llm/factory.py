# Adapted from Azimlearning/Arcana-v2, api/llm/factory.py @ 21c6dcf5. Read in full. Changes: live mode builds the Anthropic provider only after the key, the
# cap and an absolute ledger path are all present; with an OpenRouter key it puts up to three free models in front of it (D-83).
"""Build the LLM service for the configured mode (SYNAPSE_LLM_MODE)."""

from __future__ import annotations

from collections.abc import Callable

from api.core.errors import ProviderUnavailable
from api.core.settings import ConfigError, Settings
from api.llm.ledger import SpendLedger, engine_for
from api.llm.providers.anthropic import AnthropicProvider
from api.llm.providers.fake import FakeProvider
from api.llm.providers.openrouter import OpenRouterProvider
from api.llm.service import LLMService
from api.llm.types import LLMRequest


def _require_live_prerequisites(settings: Settings) -> None:
    """Live mode never runs uncapped, whatever path built the Settings (load_settings checks too, but Settings can be constructed directly)."""
    missing = settings.missing_for_mode()
    if missing:
        raise ConfigError(missing)


def build_ledger(settings: Settings) -> SpendLedger:
    """The ledger at the configured path, capped by LLM_MONTHLY_CAP_USD (None: uncapped, which only fake mode allows)."""
    _require_live_prerequisites(settings)
    return SpendLedger(
        engine_for(settings.resolved_ledger_path()), settings.llm_monthly_cap_usd, total_cap_usd=settings.llm_total_cap_usd
    )


def build_llm_service(
    settings: Settings,
    ledger: SpendLedger,
    fake_responder: Callable[[LLMRequest], str] | None = None,
) -> LLMService:
    """Fake mode: one free fake provider. Live mode: the Anthropic provider behind the ledger and its cap, never uncapped."""
    if settings.synapse_llm_mode == "fake":
        if fake_responder is None:
            from api.pipeline.fakes import (
                fake_responder as pipeline_fakes,
            )  # purpose-aware fakes for the pipeline (route, plan, fill)

            fake_responder = pipeline_fakes
        provider = FakeProvider(fake_responder)
        return LLMService(provider, None, ledger, prompt_caching=settings.prompt_caching)
    _require_live_prerequisites(settings)
    if settings.anthropic_api_key is None:
        raise ProviderUnavailable("Live mode needs ANTHROPIC_API_KEY; no provider was built.")
    paid = AnthropicProvider(settings.anthropic_api_key.get_secret_value())
    free = free_providers(settings)
    if not free:
        return LLMService(paid, None, ledger, prompt_caching=settings.prompt_caching)
    # D-83: the free models first, in order, and the paid Anthropic provider last. Any ProviderFailure (a rate limit, an outage, a withdrawn model) moves the call on.
    return LLMService(free[0], [*free[1:], paid], ledger, prompt_caching=settings.prompt_caching)


def free_providers(settings: Settings) -> list[OpenRouterProvider]:
    """One provider per free model in the configured chain, in order; empty when no OpenRouter key is set or the chain is turned off."""
    chain = settings.free_chain()
    if not chain or settings.openrouter_api_key is None:
        return []
    key = settings.openrouter_api_key.get_secret_value()
    return [OpenRouterProvider(key, model) for model in chain]
