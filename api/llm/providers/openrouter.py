"""The OpenRouter provider, for FREE models only (D-83). Read against the current OpenRouter docs on 2026-11-14:
https://openrouter.ai/docs/api_reference/errors-and-debugging.md, /api-reference/streaming.md, /api-reference/limits.md and /api_reference/overview.md.
What was confirmed there: `POST /api/v1/chat/completions` in the OpenAI shape (`choices[0].message.content`, `finish_reason` normalised to
stop, length, content_filter, error, `usage.prompt_tokens` and `completion_tokens`); an error before generation starts is an HTTP error with the body
`{"error": {"code", "message", "metadata"}}`, and one after it starts is a `200` with the error in the body or as an SSE data event; a stream carries
`: OPENROUTER PROCESSING` comment lines to skip, ends with `data: [DONE]`, and reports `usage` once, in the final chunk; free models (ids ending `:free`) are
limited to 20 requests a minute and 50 a day, or 1000 a day once 10 credits have ever been bought; 429 and 503 may carry `Retry-After`.

Why this provider never raises a rejecting failure kind: the chain behind it ends in the paid Anthropic provider, and the service stops a whole run on
`auth`, `credit_exhausted` and `bad_request`. A bad OpenRouter key, a removed model or a rate limit must send the call to the next provider, never stop the
run. So every failure here is `transient` (or `timeout` / `truncated`, which the service also treats as "try the next one"), and a failing model is put on a
cool-down so the next calls skip it with no network round trip.

It cannot bill: the constructor refuses any model id that is not a `:free` variant, and `api/llm/pricing.py` prices those at zero. Plain httpx, no SDK, like the
Anthropic provider. No attribution headers are sent (they would name the project to a third party). Free endpoints may log prompts; see D-83.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable

import httpx

from api.llm.providers.base import ProviderFailure, TextSink
from api.llm.types import LLMRequest, ProviderResponse, Tier

BASE_URL = "https://openrouter.ai/api/v1"

COOLDOWN_RATE_LIMIT = 60.0
"""Seconds to skip a model after a 429 or 503 that sent no `Retry-After`. The per-minute free limit is 20 requests."""
COOLDOWN_REFUSED = 300.0
"""After 401, 402 or 403: a key or balance problem does not clear in a minute."""
COOLDOWN_GONE = 900.0
"""After 404 (the free model was withdrawn) or 400 (it does not take our request)."""
COOLDOWN_MAX = 1800.0


def is_free_model(model: str) -> bool:
    return model.endswith(":free") or model == "openrouter/free"


class OpenRouterProvider:
    """One free model on OpenRouter. The chain holds several of these, one per model, each with its own cool-down."""

    name = "openrouter"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = BASE_URL,
        timeout_seconds: float = 120.0,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        if not api_key:
            raise ValueError("an API key is required")
        if not is_free_model(model):
            raise ValueError(f"'{model}' is not a free model (its id must end in ':free'); this provider is for free models only")
        self._key = api_key
        self._model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._clock = clock
        self._cool_until = 0.0

    def model_for(self, tier: Tier) -> str:
        return self._model

    def cooling_down(self) -> float:
        """Seconds this model is still being skipped (0 when it is available)."""
        return max(self._cool_until - self._clock(), 0.0)

    def _cool(self, seconds: float) -> None:
        self._cool_until = self._clock() + min(max(seconds, 1.0), COOLDOWN_MAX)

    def _body(self, request: LLMRequest, model: str, stream: bool) -> dict:
        messages = ([{"role": "system", "content": request.system}] if request.system else []) + [{"role": "user", "content": request.prompt}]
        body: dict = {"model": model, "messages": messages, "max_tokens": request.max_tokens}
        if stream:
            body["stream"] = True
        return body

    async def complete(self, request: LLMRequest, model: str, on_text: TextSink | None = None) -> ProviderResponse:
        wait = self.cooling_down()
        if wait > 0:
            raise ProviderFailure(self.name, f"{model} is cooling down for {wait:.0f} s after a failure", "transient")
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        if on_text is not None:
            return await self._stream(request, model, headers, on_text)
        try:
            reply = await self._client.post(self._url, headers=headers, json=self._body(request, model, False))
        except httpx.TimeoutException as exc:
            self._cool(COOLDOWN_RATE_LIMIT)
            raise ProviderFailure(self.name, f"{model}: the request timed out", "timeout") from exc
        except httpx.HTTPError as exc:
            self._cool(COOLDOWN_RATE_LIMIT)
            raise ProviderFailure(self.name, f"{model}: network error ({type(exc).__name__})", "transient") from exc
        if reply.status_code != 200:
            raise self._failure(reply, model)
        try:
            data = reply.json()
        except ValueError as exc:
            raise ProviderFailure(self.name, f"{model}: the reply was not JSON", "transient") from exc
        if isinstance(data, dict) and data.get("error"):
            raise self._body_error(data["error"], model)  # a 200 whose body is an error: the model failed after the request was accepted
        try:
            choice = data["choices"][0]
            text = choice["message"].get("content") or ""
            finish = choice.get("finish_reason")
            usage = data.get("usage") or {}
            tokens_in, tokens_out = int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            raise ProviderFailure(self.name, f"{model}: the reply was not a chat completion", "transient") from exc
        return self._checked(text, finish, tokens_in, tokens_out, str(data.get("model") or model), model)

    def _checked(self, text: str, finish: str | None, tokens_in: int, tokens_out: int, echoed: str, model: str) -> ProviderResponse:
        if finish == "length":
            # A reasoning model can spend the whole budget thinking and return nothing; retrying the same model does not help.
            raise ProviderFailure(self.name, f"{model}: the reply was cut off at max_tokens", "truncated", tokens_in=tokens_in, tokens_out=tokens_out)
        if finish in ("error", "content_filter"):
            raise ProviderFailure(self.name, f"{model}: the reply ended with {finish}", "transient", tokens_in=tokens_in, tokens_out=tokens_out)
        if not text.strip():
            raise ProviderFailure(self.name, f"{model}: the reply had no text (finish_reason {finish})", "transient", tokens_in=tokens_in, tokens_out=tokens_out)
        return ProviderResponse(text=text, model=echoed, tokens_in=tokens_in, tokens_out=tokens_out)

    async def _stream(self, request: LLMRequest, model: str, headers: dict, on_text: TextSink) -> ProviderResponse:
        """The same call with `stream: true`. Comment lines (`: OPENROUTER PROCESSING`) are skipped, `[DONE]` ends it, a chunk with a top-level `error` is a
        mid-stream failure, and the usage arrives once, in the last chunk."""
        parts: list[str] = []
        usage: dict = {}
        finish: str | None = None
        echoed = model
        try:
            async with self._client.stream("POST", self._url, headers=headers, json=self._body(request, model, True)) as reply:
                if reply.status_code != 200:
                    await reply.aread()
                    raise self._failure(reply, model)
                async for line in reply.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except ValueError:
                        continue
                    if not isinstance(chunk, dict):
                        continue
                    if chunk.get("error"):
                        raise self._body_error(chunk["error"], model)
                    echoed = str(chunk.get("model") or echoed)
                    usage.update({k: v for k, v in (chunk.get("usage") or {}).items() if v is not None})
                    for choice in chunk.get("choices") or []:
                        piece = (choice.get("delta") or {}).get("content")
                        if piece:
                            parts.append(str(piece))
                            on_text(str(piece))
                        finish = choice.get("finish_reason") or finish
        except httpx.TimeoutException as exc:
            self._cool(COOLDOWN_RATE_LIMIT)
            raise ProviderFailure(self.name, f"{model}: the request timed out", "timeout") from exc
        except httpx.HTTPError as exc:
            self._cool(COOLDOWN_RATE_LIMIT)
            raise ProviderFailure(self.name, f"{model}: network error ({type(exc).__name__})", "transient") from exc
        tokens_in, tokens_out = int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)
        return self._checked("".join(parts), finish, tokens_in, tokens_out, echoed, model)

    def _body_error(self, error: object, model: str) -> ProviderFailure:
        """A failure reported inside a 200 body or an SSE event. Only the numeric code and the typed `error_type` are kept, never the message."""
        code, kind = 0, "unknown"
        if isinstance(error, dict):
            try:
                code = int(error.get("code") or 0)
            except (TypeError, ValueError):
                code = 0
            meta = error.get("metadata")
            if isinstance(meta, dict):
                kind = str(meta.get("error_type") or "unknown")[:40]
        if code in (429, 503) or kind == "rate_limit_exceeded":
            self._cool(COOLDOWN_RATE_LIMIT)
        return ProviderFailure(self.name, f"{model}: error {code} {kind}", "transient")

    def _failure(self, reply: httpx.Response, model: str) -> ProviderFailure:
        """An HTTP error. Never `auth`, `credit_exhausted` or `bad_request`: those stop the whole run, and the paid provider behind this one must still get the call."""
        status = reply.status_code
        try:
            error_type = str(reply.json()["error"]["metadata"]["error_type"])[:40]
        except (ValueError, KeyError, TypeError):
            error_type = "unknown"
        retry_after = _seconds(reply.headers.get("retry-after"))
        if status in (429, 503):
            self._cool(retry_after or COOLDOWN_RATE_LIMIT)
        elif status in (401, 402, 403):
            self._cool(retry_after or COOLDOWN_REFUSED)
        elif status in (400, 404):
            self._cool(COOLDOWN_GONE)
        elif status in (408, 502, 504) or status >= 500:
            self._cool(COOLDOWN_RATE_LIMIT / 2)
        kind = "timeout" if status in (408, 504) else "transient"
        return ProviderFailure(self.name, f"{model}: HTTP {status} {error_type}", kind)


def _seconds(value: str | None) -> float | None:
    try:
        seconds = float(value) if value is not None else None
    except ValueError:
        return None
    return seconds if seconds and seconds > 0 else None
