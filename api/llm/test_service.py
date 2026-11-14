"""The seam's guarantees: fakes by default and offline, live mode needs a key and a cap, the cap refuses before any
provider call, and every call is written to the ledger."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from api.core.errors import ProviderRejected, ProviderUnavailable, SpendCapExceeded
from api.core.settings import ConfigError, load_settings
from api.llm.factory import build_ledger, build_llm_service
from api.llm.ledger import SpendLedger, engine_for
from api.llm.models import ANTHROPIC_MODELS
from api.llm.pricing import cost_usd, estimate_call_cost, estimate_input_tokens
from api.llm.providers.anthropic import AnthropicProvider
from api.llm.providers.base import ProviderFailure
from api.llm.providers.fake import FakeProvider
from api.llm.service import LLMService
from api.llm.types import LLMRequest


def _ledger(tmp_path: Path, cap: float | None) -> SpendLedger:
    return SpendLedger(engine_for(tmp_path / "ledger.db"), cap, clock=lambda: datetime(2026, 10, 16, tzinfo=UTC))


@pytest.mark.usefixtures("clean_env", "no_network")
async def test_default_mode_is_fake_and_makes_no_network_call(tmp_path: Path) -> None:
    settings = load_settings(env_file=None)
    assert settings.synapse_llm_mode == "fake"
    settings = settings.model_copy(update={"data_dir": tmp_path})
    service = build_llm_service(settings, build_ledger(settings))
    result = await service.complete(LLMRequest(prompt="why does a spring stretch", purpose="explain"))
    assert result.provider == "fake"
    assert result.cost_usd == 0.0
    assert result.text.startswith("[fake:explain:")


@pytest.mark.usefixtures("clean_env")
async def test_fake_reply_is_deterministic(tmp_path: Path) -> None:
    provider = FakeProvider()
    service = LLMService(provider, None, _ledger(tmp_path, None))
    a = await service.complete(LLMRequest(prompt="same", purpose="explain"))
    b = await service.complete(LLMRequest(prompt="same", purpose="explain"))
    c = await service.complete(LLMRequest(prompt="different", purpose="explain"))
    assert a.text == b.text
    assert a.text != c.text


@pytest.mark.usefixtures("clean_env")
def test_live_mode_without_key_names_anthropic_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYNAPSE_LLM_MODE", "live")
    monkeypatch.setenv("LLM_MONTHLY_CAP_USD", "5")
    with pytest.raises(ConfigError) as err:
        load_settings(env_file=None)
    assert "ANTHROPIC_API_KEY" in str(err.value)
    assert "LLM_MONTHLY_CAP_USD" not in str(err.value)


@pytest.mark.usefixtures("clean_env")
def test_live_mode_without_cap_names_llm_monthly_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYNAPSE_LLM_MODE", "live")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    with pytest.raises(ConfigError) as err:
        load_settings(env_file=None)
    assert "LLM_MONTHLY_CAP_USD" in str(err.value)
    assert "ANTHROPIC_API_KEY" not in str(err.value)


@pytest.mark.usefixtures("clean_env")
def test_live_mode_rejects_a_zero_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYNAPSE_LLM_MODE", "live")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("LLM_MONTHLY_CAP_USD", "0")
    with pytest.raises(ConfigError, match="LLM_MONTHLY_CAP_USD"):
        load_settings(env_file=None)


@pytest.mark.usefixtures("clean_env", "no_network")
def test_live_mode_with_a_key_and_a_cap_builds_the_anthropic_provider_and_opens_no_socket(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SYNAPSE_LLM_MODE", "live")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("LLM_MONTHLY_CAP_USD", "5")
    monkeypatch.setenv("LEDGER_PATH", str(tmp_path / "ledger.db"))
    settings = load_settings(env_file=None)
    ledger = build_ledger(settings)
    service = build_llm_service(settings, ledger)
    (provider,) = service._providers  # noqa: SLF001  # live mode has the one provider and no fallback
    assert isinstance(provider, AnthropicProvider) and provider.name == "anthropic"
    assert ledger.remaining_usd() == 5.0  # the cap is on the ledger the service writes to


@pytest.mark.usefixtures("clean_env", "no_network")
def test_live_mode_without_a_key_or_a_cap_builds_no_provider_even_without_load_settings(tmp_path: Path) -> None:
    from api.core.settings import Settings

    ledger = SpendLedger(engine_for(tmp_path / "l.db"), 5.0)
    no_key = Settings.model_validate(
        {"synapse_llm_mode": "live", "llm_monthly_cap_usd": 5, "ledger_path": str(tmp_path / "l.db")}
    )
    with pytest.raises(ConfigError) as err:
        build_llm_service(no_key, ledger)
    assert "ANTHROPIC_API_KEY" in str(err.value)
    no_cap = Settings.model_validate(
        {"synapse_llm_mode": "live", "anthropic_api_key": "sk-x", "ledger_path": str(tmp_path / "l.db")}
    )
    with pytest.raises(ConfigError) as err:
        build_llm_service(no_cap, ledger)
    assert "LLM_MONTHLY_CAP_USD" in str(err.value)


async def test_a_billed_reply_the_service_then_rejects_is_booked_with_its_real_output_tokens(tmp_path: Path) -> None:
    """A reply cut off at max_tokens was billed in full, thinking included. Booking only the input would let the cap be exceeded."""

    class CutOff:
        name = "anthropic"

        def model_for(self, tier):  # noqa: ANN001, ANN201
            return ANTHROPIC_MODELS[tier]

        async def complete(self, request, model):  # noqa: ANN001, ANN201
            raise ProviderFailure("anthropic", "cut off", "truncated", tokens_in=1_000, tokens_out=16_000)

    ledger = _ledger(tmp_path, cap=10.0)
    service = LLMService(CutOff(), None, ledger)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
    with pytest.raises(ProviderUnavailable):
        await service.complete(LLMRequest(prompt="x", purpose="plan", tier="standard", max_tokens=16_000))
    (row,) = ledger.rows()
    # Sonnet 5.5: $2 in, $10 out per million tokens.
    assert row["status"] == "failed" and (row["tokens_in"], row["tokens_out"]) == (1_000, 16_000)
    assert row["cost_usd"] == pytest.approx((1_000 * 2 + 16_000 * 10) / 1_000_000)
    assert ledger.month_total() == pytest.approx(row["cost_usd"])


async def test_request_over_the_cap_is_refused_before_the_provider(tmp_path: Path) -> None:
    # A fake that prices like a real provider: sonnet is $2 in, $10 out per million, so 16k output tokens is $0.16.
    spy = FakeProvider(name="anthropic", models=ANTHROPIC_MODELS)
    service = LLMService(spy, None, _ledger(tmp_path, cap=0.01))
    with pytest.raises(SpendCapExceeded):
        await service.complete(LLMRequest(prompt="x" * 300, purpose="plan", max_tokens=16_000))
    assert spy.calls == []


def test_would_fit_is_true_only_when_the_cap_covers_the_worst_case_of_every_request_together(tmp_path: Path) -> None:
    page = LLMRequest(prompt="x" * 30, purpose="free", tier="standard", max_tokens=6_000)  # about $0.06 reserved
    reading = LLMRequest(prompt="x" * 30, purpose="wording_free", tier="standard", max_tokens=400)  # about $0.004
    spy = FakeProvider(name="anthropic", models=ANTHROPIC_MODELS)
    assert LLMService(spy, None, _ledger(tmp_path / "a", cap=None)).would_fit([page, reading])  # no cap: always
    assert LLMService(spy, None, _ledger(tmp_path / "b", cap=0.10)).would_fit([page, reading])
    assert not LLMService(spy, None, _ledger(tmp_path / "c", cap=0.062)).would_fit([page, reading])  # the page fits, the pair does not
    assert LLMService(spy, None, _ledger(tmp_path / "c2", cap=0.062)).would_fit([page])
    assert spy.calls == []  # asking never sends anything


async def test_spend_accumulates_toward_the_cap(tmp_path: Path) -> None:
    # Each reply is 5000 characters (1250 output tokens), so each settled call really books about $0.0125.
    spy = FakeProvider(lambda _request: "y" * 5000, name="anthropic", models=ANTHROPIC_MODELS)
    ledger = _ledger(tmp_path, cap=0.05)
    service = LLMService(spy, None, ledger)
    request = LLMRequest(prompt="x" * 30, purpose="plan", max_tokens=2_000)  # worst case about $0.02
    await service.complete(request)
    await service.complete(request)
    assert ledger.month_total() == pytest.approx(0.025, abs=0.001)
    # Alone, 3000 output tokens ($0.03) fits under the cap; on top of the $0.025 already spent it does not.
    with pytest.raises(SpendCapExceeded):
        await service.complete(LLMRequest(prompt="x" * 30, purpose="plan", max_tokens=3_000))
    assert len(spy.calls) == 2


async def test_a_ledger_row_records_purpose_tokens_and_cost(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap=10.0)
    service = LLMService(FakeProvider(name="anthropic", models=ANTHROPIC_MODELS), None, ledger)
    result = await service.complete(LLMRequest(prompt="hello there", purpose="explain", max_tokens=200))
    (row,) = ledger.rows()
    assert row["purpose"] == "explain"
    assert row["status"] == "ok"
    assert row["tokens_in"] == result.tokens_in > 0
    assert row["tokens_out"] == result.tokens_out > 0
    assert row["cost_usd"] == pytest.approx(result.cost_usd)
    assert row["cost_usd"] > 0


async def test_failed_attempt_is_recorded_as_failed_and_costs_nothing(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap=10.0)
    broken = FakeProvider(name="anthropic", models=ANTHROPIC_MODELS, fail_with="timeout")
    service = LLMService(broken, None, ledger)
    with pytest.raises(ProviderUnavailable):
        await service.complete(LLMRequest(prompt="hi", purpose="explain"))
    (row,) = ledger.rows()
    assert row["status"] == "failed"
    assert row["cost_usd"] == 0.0


async def test_a_timeout_is_booked_at_the_worst_case_because_the_provider_may_have_generated_the_whole_reply(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap=10.0)
    service = LLMService(
        FakeProvider(name="anthropic", models=ANTHROPIC_MODELS, fail_with="timed out", fail_kind="timeout"),
        None,
        ledger,
    )
    request = LLMRequest(prompt="x" * 3000, purpose="plan")
    with pytest.raises(ProviderUnavailable):
        await service.complete(request)
    (row,) = ledger.rows()
    assert row["status"] == "failed"
    assert row["cost_usd"] == pytest.approx(estimate_call_cost("anthropic", ANTHROPIC_MODELS[request.tier], request))
    assert row["cost_usd"] > cost_usd("anthropic", ANTHROPIC_MODELS[request.tier], estimate_input_tokens(request), 0)  # more than the input alone


@pytest.mark.parametrize("kind", ["credit_exhausted", "auth", "bad_request"])
async def test_a_failure_a_retry_cannot_fix_stops_at_once_and_says_it_is_not_the_cap(tmp_path: Path, kind: str) -> None:
    ledger = _ledger(tmp_path, cap=10.0)
    first = FakeProvider(name="anthropic", models=ANTHROPIC_MODELS, fail_with="rejected", fail_kind=kind)  # type: ignore[arg-type]
    fallback = FakeProvider(name="fallbackco", models=ANTHROPIC_MODELS)
    service = LLMService(first, fallback, ledger)
    with pytest.raises(ProviderRejected) as err:
        await service.complete(LLMRequest(prompt="hi", purpose="plan"))
    assert "not the spend cap" in str(err.value) and err.value.retryable is False
    assert fallback.calls == []  # a balance or key problem is never retried on another provider


async def test_a_cancelled_call_is_booked_for_its_input_and_the_cancellation_propagates(tmp_path: Path) -> None:
    import asyncio

    class Hangs:
        name = "anthropic"

        def model_for(self, tier):  # noqa: ANN001, ANN201
            return ANTHROPIC_MODELS[tier]

        async def complete(self, request, model):  # noqa: ANN001, ANN201
            await asyncio.sleep(10)

    ledger = _ledger(tmp_path, cap=10.0)
    service = LLMService(Hangs(), None, ledger)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
    task = asyncio.create_task(service.complete(LLMRequest(prompt="x" * 3000, purpose="plan")))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    (row,) = ledger.rows()
    assert row["cost_usd"] > 0 and ledger.remaining_usd() == pytest.approx(10.0 - row["cost_usd"])


async def test_a_run_whose_worst_case_does_not_fit_the_cap_is_refused_before_it_starts(tmp_path: Path) -> None:
    service = LLMService(FakeProvider(name="anthropic", models=ANTHROPIC_MODELS), None, _ledger(tmp_path, cap=0.50))
    service.ensure_budget(0.40)
    with pytest.raises(SpendCapExceeded):
        service.ensure_budget(0.80)
    assert (
        LLMService(FakeProvider(), None, _ledger(tmp_path / "u", cap=None)).ensure_budget(99.0) is None
    )  # no cap: nothing to check


@pytest.mark.usefixtures("clean_env")
def test_live_mode_is_never_built_uncapped_or_with_a_relative_ledger_even_without_load_settings(tmp_path: Path) -> None:
    from api.core.settings import Settings

    def settings(**kw: object) -> Settings:
        return Settings.model_validate({"synapse_llm_mode": "live", "anthropic_api_key": "sk-x", **kw})

    with pytest.raises(ConfigError) as err:
        build_ledger(settings(ledger_path=str(tmp_path / "l.db")))
    assert "LLM_MONTHLY_CAP_USD" in str(err.value)
    with pytest.raises(ConfigError) as err:
        build_ledger(settings(llm_monthly_cap_usd=1))
    assert "LEDGER_PATH" in str(err.value)


async def test_the_spend_summary_splits_by_purpose_and_model_and_counts_failed_calls(tmp_path: Path) -> None:
    ledger = SpendLedger(engine_for(tmp_path / "l.db"), 1.0)
    service = LLMService(FakeProvider(name="anthropic", models=ANTHROPIC_MODELS), None, ledger)
    await service.complete(LLMRequest(prompt="a" * 300, purpose="plan", tier="standard", max_tokens=100))
    await service.complete(LLMRequest(prompt="b" * 300, purpose="explain", tier="light", max_tokens=100))
    broken = LLMService(
        FakeProvider(name="anthropic", models=ANTHROPIC_MODELS, fail_with="x", fail_kind="transient"), None, ledger
    )
    with pytest.raises(Exception):  # noqa: B017, PT011
        await broken.complete(LLMRequest(prompt="c", purpose="plan", tier="standard", max_tokens=10))
    s = ledger.summary()
    assert s["cap_usd"] == 1.0 and s["calls"] == 3 and s["failed_calls"] == 1
    assert set(s["by_purpose"]) == {"plan", "explain"} and set(s["by_model"]) == {
        "claude-sonnet-5-5",
        "claude-haiku-5-5",
    }
    assert s["spent_usd"] == pytest.approx(sum(s["by_model"].values())) and s["remaining_usd"] == pytest.approx(
        1.0 - s["spent_usd"]
    )


async def test_the_all_time_budget_holds_across_months_when_the_monthly_cap_has_reset(tmp_path: Path) -> None:
    """The owner's limit is for the whole project. The monthly cap resets on the 1st; the all-time budget must not."""
    now = {"t": datetime(2026, 10, 30, tzinfo=UTC)}
    ledger = SpendLedger(engine_for(tmp_path / "l.db"), 5.0, clock=lambda: now["t"], total_cap_usd=0.05)
    service = LLMService(FakeProvider(lambda _r: "y" * 5000, name="anthropic", models=ANTHROPIC_MODELS), None, ledger)
    request = LLMRequest(prompt="x" * 30, purpose="plan", max_tokens=1_000)  # a worst case of about $0.01
    await service.complete(request)
    await service.complete(request)
    spent = ledger.all_time_total()
    assert spent > 0.02
    now["t"] = datetime(2026, 11, 2, tzinfo=UTC)  # a new month: the monthly cap sees nothing spent
    assert ledger.month_total() == 0.0 and ledger.all_time_total() == pytest.approx(spent)
    with pytest.raises(SpendCapExceeded, match="all-time"):
        await service.complete(LLMRequest(prompt="x" * 30, purpose="plan", max_tokens=4_000))  # $0.04 worst case would pass $0.05 in all
    assert ledger.remaining_usd() == pytest.approx(0.05 - spent)  # the smaller of the two caps


def test_without_an_all_time_budget_nothing_changes_and_the_summary_shows_both(tmp_path: Path) -> None:
    plain = SpendLedger(engine_for(tmp_path / "a.db"), 1.0)
    assert plain.remaining_usd() == 1.0 and plain.summary()["total_cap_usd"] is None
    both = SpendLedger(engine_for(tmp_path / "b.db"), 1.0, total_cap_usd=0.25)
    assert both.remaining_usd() == 0.25 and both.summary()["total_cap_usd"] == 0.25 and both.summary()["all_time_spent_usd"] == 0.0
    only_total = SpendLedger(engine_for(tmp_path / "c.db"), None, total_cap_usd=0.25)
    assert only_total.remaining_usd() == 0.25


def test_the_all_time_budget_setting_reaches_the_ledger_the_service_writes_to(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SYNAPSE_LLM_MODE", "live")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("LLM_MONTHLY_CAP_USD", "5")
    monkeypatch.setenv("LLM_TOTAL_CAP_USD", "2")
    monkeypatch.setenv("LEDGER_PATH", str(tmp_path / "ledger.db"))
    settings = load_settings(env_file=None)
    ledger = build_ledger(settings)
    assert settings.llm_total_cap_usd == 2.0 and ledger.remaining_usd() == 2.0
    ledger.close()


# ---- D-83: free models first, the paid provider last ----


def _free(name: str, **kw) -> FakeProvider:  # noqa: ANN003
    return FakeProvider(name="openrouter", models={"heavy": name, "standard": name, "light": name}, **kw)


@pytest.mark.usefixtures("clean_env")
async def test_a_chain_tries_each_free_model_in_order_and_ends_on_the_paid_one(tmp_path: Path) -> None:
    free_a, free_b, paid = _free("a:free", fail_with="HTTP 429"), _free("b:free", fail_with="HTTP 503"), FakeProvider(name="anthropic")
    result = await LLMService(free_a, [free_b, paid], _ledger(tmp_path, 5.0)).complete(LLMRequest(prompt="q", purpose="explain"))
    assert (len(free_a.calls), len(free_b.calls), len(paid.calls)) == (1, 1, 1)
    assert result.provider == "anthropic" and result.fell_back


@pytest.mark.usefixtures("clean_env")
async def test_the_first_free_model_that_answers_stops_the_chain_and_costs_nothing(tmp_path: Path) -> None:
    free_a, free_b, paid = _free("a:free", fail_with="HTTP 429"), _free("b:free"), FakeProvider(name="anthropic")
    ledger = _ledger(tmp_path, 5.0)
    result = await LLMService(free_a, [free_b, paid], ledger).complete(LLMRequest(prompt="q", purpose="explain", max_tokens=1000))
    assert result.provider == "openrouter" and result.model == "b:free" and result.cost_usd == 0.0
    assert paid.calls == [] and ledger.month_total() == 0.0


@pytest.mark.usefixtures("clean_env")
async def test_an_exhausted_cap_still_lets_the_free_models_answer_but_never_the_paid_one(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, 0.0001)  # no room for any paid call
    paid = FakeProvider(name="anthropic")
    assert (await LLMService(_free("a:free"), [paid], ledger).complete(LLMRequest(prompt="q", purpose="explain", max_tokens=4000))).provider == "openrouter"
    with pytest.raises(SpendCapExceeded):
        await LLMService(_free("a:free", fail_with="HTTP 429"), [paid], ledger).complete(LLMRequest(prompt="q", purpose="explain", max_tokens=4000))
    assert paid.calls == []


def test_the_free_chain_is_configured_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.llm.models import DEFAULT_FREE_CHAIN

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")
    s = load_settings(env_file=None)
    assert s.free_chain() == DEFAULT_FREE_CHAIN and len(DEFAULT_FREE_CHAIN) <= 3
    assert s.model_copy(update={"llm_free_chain": "off"}).free_chain() == ()
    assert s.model_copy(update={"llm_free_chain": "a/b:free, c/d:free"}).free_chain() == ("a/b:free", "c/d:free")
    assert s.model_copy(update={"llm_free_chain": "a:free,b:free,c:free,d:free"}).free_chain_problem()
    assert "not free" in (s.model_copy(update={"llm_free_chain": "anthropic/claude-opus-5-5"}).free_chain_problem() or "")
    monkeypatch.delenv("OPENROUTER_API_KEY")
    assert load_settings(env_file=None).free_chain() == ()  # no key, no free models


@pytest.mark.usefixtures("clean_env")
def test_live_factory_puts_the_free_models_in_front_of_anthropic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SYNAPSE_LLM_MODE", "live")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-ant-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")
    monkeypatch.setenv("LLM_MONTHLY_CAP_USD", "5")
    monkeypatch.setenv("LEDGER_PATH", str(tmp_path / "ledger.db"))
    settings = load_settings(env_file=None)
    service = build_llm_service(settings, build_ledger(settings))
    assert [p.name for p in service._providers] == ["openrouter", "openrouter", "openrouter", "anthropic"]  # noqa: SLF001
    monkeypatch.setenv("LLM_FREE_CHAIN", "off")
    off = load_settings(env_file=None)
    assert [p.name for p in build_llm_service(off, build_ledger(off))._providers] == ["anthropic"]  # noqa: SLF001
