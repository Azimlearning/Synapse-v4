# Adapted from Azimlearning/Arcana-v2, api/llm/service.py @ 21c6dcf5. Read in full. Changes: the per-turn token budget is
# dropped (P3 re-introduces a budget when there is a planner), stdlib logging, this repo's errors.
"""The LLM seam. Nothing else in the codebase calls a provider (hard constraint 8).

complete() tries the primary, then each fallback in order (D-83: up to three free models, then the paid provider), on any ProviderFailure. Before each attempt it reserves that attempt's
worst-case cost against the monthly cap; a refusal there happens before the provider is invoked. Every attempt, including
failed ones, is written to the spend ledger.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace

from api.core.errors import BadRequest, ProviderRejected, ProviderUnavailable, SpendCapExceeded
from api.llm.ledger import SpendLedger
from api.llm.pricing import cost_usd, estimate_call_cost, estimate_input_tokens
from api.llm.providers.base import Provider, ProviderFailure, TextSink
from api.llm.types import MAX_OUTPUT_TOKENS, LLMRequest, LLMResult

log = logging.getLogger(__name__)


class LLMService:
    def __init__(self, primary: Provider, fallback: Provider | Sequence[Provider] | None, ledger: SpendLedger, *, prompt_caching: bool = False):
        """`fallback` is one provider or an ordered list of them (D-83: free models first, the paid one last): each is tried in turn on a ProviderFailure."""
        rest: list[Provider] = [] if fallback is None else list(fallback) if isinstance(fallback, Sequence) else [fallback]
        self._providers = [primary, *rest]
        self._ledger = ledger
        self._prompt_caching = prompt_caching
        """Ask providers to cache every system prompt (PROMPT_CACHING, off by default). The ledger prices what comes back; see api/llm/pricing.py."""

    def _prepared(self, request: LLMRequest) -> LLMRequest:
        """The request as it will be sent: with caching on, a request that has a system prompt asks for it to be cached."""
        if self._prompt_caching and request.system and not request.cache_system:
            return replace(request, cache_system=True)
        return request

    def remaining_usd(self) -> float | None:
        """What the monthly cap still allows (None: no cap). For up-front checks before a big job."""
        return self._ledger.remaining_usd()

    def ensure_budget(self, projected_usd: float) -> None:
        """Refuse a run up front when the cap cannot cover its projected worst case (a sweep must not start and then hit the cap half way)."""
        remaining = self.remaining_usd()
        if remaining is not None and remaining < projected_usd:
            raise SpendCapExceeded(
                f"The run is projected to cost up to ${projected_usd:.2f} but only ${remaining:.2f} of this month's cap remains. Nothing was sent."
            )

    def would_fit(self, requests: list[LLMRequest]) -> bool:
        """True when the cap leaves room for the worst case of all of `requests` together (each at its estimated input plus a full max_tokens, as the ledger
        will reserve it), priced for the primary provider. For a job that is worthless unless every call can be made: a page that is generated and then cannot
        be read is money spent on nothing."""
        remaining = self.remaining_usd()
        if remaining is None:
            return True
        provider = self._providers[0]
        total = sum(estimate_call_cost(provider.name, provider.model_for(r.tier), self._prepared(r)) for r in requests)
        return remaining >= total

    async def complete(self, request: LLMRequest, on_text: TextSink | None = None) -> LLMResult:
        """One paid call through the cap and the ledger. `on_text` (W19, D-79) watches the reply's text as it is generated; nothing about the reservation,
        the cap, the booking or the fallback changes with it. A fallback provider's text is watched too, after the first provider's partial text."""
        request = self._prepared(request)
        if not 1 <= request.max_tokens <= MAX_OUTPUT_TOKENS:
            raise BadRequest(f"max_tokens must be between 1 and {MAX_OUTPUT_TOKENS}.")

        last_failure: ProviderFailure | None = None
        for index, provider in enumerate(self._providers):
            model = provider.model_for(request.tier)
            reservation = self._ledger.reserve(estimate_call_cost(provider.name, model, request))
            try:
                response = await (provider.complete(request, model) if on_text is None else provider.complete(request, model, on_text=on_text))
            except ProviderFailure as failure:
                # A reply the provider billed and we then rejected (cut off, empty, refused) arrives with its real usage: book that, output
                # included. A timeout (or a cut-off with no usage to read) may have been billed for the whole reply, because the provider can go on
                # generating after our client gives up: with nothing to read, book the worst case the reservation already assumed, not the input alone.
                if failure.tokens_in is not None and failure.tokens_out is not None:
                    tokens_in, tokens_out = failure.tokens_in, failure.tokens_out
                    billed = cost_usd(provider.name, model, tokens_in, tokens_out, assume_cache_writes=request.cache_system)
                else:
                    tokens_in = tokens_out = 0
                    billed = reservation.estimate_usd if failure.kind in ("timeout", "truncated") else 0.0
                self._ledger.settle(
                    reservation,
                    provider=provider.name,
                    model=model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=billed,
                    purpose=request.purpose,
                    status="failed",
                )
                log.warning(
                    "provider_failed provider=%s kind=%s reason=%s", provider.name, failure.kind, failure.reason
                )
                if failure.kind in ("credit_exhausted", "auth", "bad_request"):
                    raise ProviderRejected(
                        f"The provider refused the request ({failure.kind.replace('_', ' ')}). This is the provider's balance, key or our request, "
                        "not the spend cap, and retrying will not help."
                    ) from failure
                last_failure = failure
                continue
            except BaseException:
                # Cancellation (a client closing the stream) or a bug: the provider may already have billed the input, so book that, release the
                # reservation, then let the exception propagate.
                self._ledger.settle(
                    reservation,
                    provider=provider.name,
                    model=model,
                    tokens_in=0,
                    tokens_out=0,
                    cost_usd=cost_usd(provider.name, model, estimate_input_tokens(request), 0, assume_cache_writes=request.cache_system),
                    purpose=request.purpose,
                    status="failed",
                )
                raise

            # Price by the model that was REQUESTED (an id this code chose and the table knows), never by the id echoed
            # back. A provider-reported cost is trusted only as a lower bound: book the larger of the two.
            estimated = cost_usd(
                provider.name, model, response.tokens_in, response.tokens_out, response.cache_read_tokens, response.cache_write_tokens
            )
            cost = estimated if response.cost_usd is None else max(response.cost_usd, estimated)
            self._ledger.settle(
                reservation,
                provider=provider.name,
                model=response.model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                cost_usd=cost,
                purpose=request.purpose,
                cache_read_tokens=response.cache_read_tokens,
                cache_write_tokens=response.cache_write_tokens,
            )
            return LLMResult(
                text=response.text,
                provider=provider.name,
                model=response.model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                cost_usd=cost,
                fell_back=index > 0,
                cache_read_tokens=response.cache_read_tokens,
                cache_write_tokens=response.cache_write_tokens,
            )

        raise ProviderUnavailable("No LLM provider could serve the request.") from last_failure
