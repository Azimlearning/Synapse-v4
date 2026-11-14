"""The OpenRouter free-model provider against a mock transport: no socket is opened and nothing is billed (D-83)."""

from __future__ import annotations

import json

import httpx
import pytest

from api.llm.providers.base import ProviderFailure
from api.llm.providers.openrouter import COOLDOWN_GONE, COOLDOWN_REFUSED, OpenRouterProvider, is_free_model
from api.llm.types import LLMRequest

KEY = "test-key-not-a-real-credential"
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
REQ = LLMRequest(prompt="Why does a spring stretch?", purpose="explain", system="Be brief.", max_tokens=200)


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def provider(handler, clock: Clock | None = None) -> OpenRouterProvider:  # noqa: ANN001
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenRouterProvider(KEY, MODEL, client=client, clock=clock or Clock())


def ok(text: str = "hello", finish: str = "stop", **usage: int) -> httpx.Response:
    body = {
        "id": "gen-1",
        "model": MODEL,
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, **usage},
    }
    return httpx.Response(200, json=body)


def err(status: int, error_type: str = "x", headers: dict | None = None) -> httpx.Response:
    body = {"error": {"code": status, "message": "secret detail", "metadata": {"error_type": error_type}}}
    return httpx.Response(status, json=body, headers=headers or {})


def test_only_free_models_can_be_built() -> None:
    assert is_free_model("google/gemma-4-31b-it:free") and is_free_model("openrouter/free")
    with pytest.raises(ValueError, match="free model"):
        OpenRouterProvider(KEY, "anthropic/claude-opus-5-5")
    with pytest.raises(ValueError):
        OpenRouterProvider("", MODEL)


async def test_a_good_reply_has_the_chat_completions_shape() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["auth"], seen["body"] = str(request.url), request.headers["authorization"], json.loads(request.content)
        seen["headers"] = {k.lower() for k in request.headers}
        return ok("a spring stretches")

    reply = await provider(handler).complete(REQ, MODEL)
    assert reply.text == "a spring stretches" and (reply.tokens_in, reply.tokens_out) == (10, 5)
    assert seen["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert seen["auth"] == f"Bearer {KEY}"
    assert seen["body"]["model"] == MODEL and seen["body"]["max_tokens"] == 200 and "stream" not in seen["body"]
    assert seen["body"]["messages"] == [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Why does a spring stretch?"}]
    assert "http-referer" not in seen["headers"] and "x-title" not in seen["headers"]  # nothing names the project to a third party


@pytest.mark.parametrize("status", [400, 401, 402, 403, 404, 408, 429, 500, 502, 503])
async def test_no_http_error_can_stop_the_run(status: int) -> None:
    """The paid provider sits behind this one: auth, credit and bad-request kinds would stop the run before it got the call."""
    with pytest.raises(ProviderFailure) as caught:
        await provider(lambda r: err(status, "rate_limit_exceeded")).complete(REQ, MODEL)
    assert caught.value.kind in ("transient", "timeout")
    assert "secret detail" not in str(caught.value) and KEY not in str(caught.value)


async def test_a_rate_limited_model_is_skipped_until_its_cool_down_ends() -> None:
    clock, calls = Clock(), []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return err(429, headers={"retry-after": "30"}) if len(calls) == 1 else ok()

    p = provider(handler, clock)
    with pytest.raises(ProviderFailure):
        await p.complete(REQ, MODEL)
    assert 29 <= p.cooling_down() <= 30
    with pytest.raises(ProviderFailure, match="cooling down"):
        await p.complete(REQ, MODEL)
    assert len(calls) == 1  # the second call never reached the network
    clock.now += 31
    assert (await p.complete(REQ, MODEL)).text == "hello"


async def test_refused_and_withdrawn_models_cool_down_longer() -> None:
    p401, p404 = provider(lambda r: err(401)), provider(lambda r: err(404))
    for p in (p401, p404):
        with pytest.raises(ProviderFailure):
            await p.complete(REQ, MODEL)
    assert p401.cooling_down() == COOLDOWN_REFUSED and p404.cooling_down() == COOLDOWN_GONE


async def test_an_error_inside_a_200_body_is_a_failure_not_a_reply() -> None:
    body = {"error": {"code": 429, "message": "x", "metadata": {"error_type": "rate_limit_exceeded"}}}
    p = provider(lambda r: httpx.Response(200, json=body))
    with pytest.raises(ProviderFailure, match="429 rate_limit_exceeded"):
        await p.complete(REQ, MODEL)
    assert p.cooling_down() > 0


async def test_a_reasoning_model_that_spent_its_budget_thinking_is_truncated_and_empty_is_refused() -> None:
    with pytest.raises(ProviderFailure) as cut:
        await provider(lambda r: ok("", finish="length", completion_tokens=200)).complete(REQ, MODEL)
    assert cut.value.kind == "truncated" and cut.value.tokens_out == 200
    with pytest.raises(ProviderFailure, match="no text"):
        await provider(lambda r: ok("   ")).complete(REQ, MODEL)
    with pytest.raises(ProviderFailure):
        await provider(lambda r: ok("partial", finish="error")).complete(REQ, MODEL)


def sse(*events: object) -> httpx.Response:
    lines = [": OPENROUTER PROCESSING", ""]
    for e in events:
        lines += [e if isinstance(e, str) else "data: " + json.dumps(e), ""]
    return httpx.Response(200, content="\n".join(lines).encode(), headers={"content-type": "text/event-stream"})


def chunk(text: str | None = None, finish: str | None = None, **extra: object) -> dict:
    return {"id": "gen-1", "model": MODEL, "choices": [{"delta": {"content": text} if text is not None else {}, "finish_reason": finish}], **extra}


async def test_a_stream_hands_over_text_as_it_arrives_and_reads_usage_from_the_last_chunk() -> None:
    seen: list[str] = []
    seen_body: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_body.update(json.loads(request.content))
        return sse(chunk("The spring "), chunk("stretches."), chunk(None, "stop", usage={"prompt_tokens": 12, "completion_tokens": 7}), "data: [DONE]")

    reply = await provider(handler).complete(REQ, MODEL, on_text=seen.append)
    assert seen_body["stream"] is True
    assert seen == ["The spring ", "stretches."] and reply.text == "The spring stretches."
    assert (reply.tokens_in, reply.tokens_out) == (12, 7)


async def test_a_mid_stream_error_is_a_failure_after_its_partial_text() -> None:
    seen: list[str] = []
    error = {"error": {"code": 502, "message": "x", "metadata": {"error_type": "provider_disconnect"}}}
    p = provider(lambda r: sse(chunk("half a "), error))
    with pytest.raises(ProviderFailure, match="provider_disconnect"):
        await p.complete(REQ, MODEL, on_text=seen.append)
    assert seen == ["half a "]


async def test_a_stream_http_error_is_a_failure_too() -> None:
    with pytest.raises(ProviderFailure) as caught:
        await provider(lambda r: err(429)).complete(REQ, MODEL, on_text=lambda _t: None)
    assert caught.value.kind == "transient"
