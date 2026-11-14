# Adapted from Azimlearning/Arcana-v2, api/core/settings.py @ 21c6dcf5. Read in full. Changes: the mode variable is
# SYNAPSE_LLM_MODE, embeddings are dropped (A-9), OpenRouter is an optional fallback (it is not required in live mode),
# and PUBLIC_ORIGIN is added because the sandbox CSP names it explicitly (hard constraint 2).
"""Typed settings from the process environment (the `.env` file; never the Environment artifact).

Every variable is documented in refdocs/guides/env_setup.md. Fakes are the default, so with SYNAPSE_LLM_MODE=fake no key
is needed and no network call is made. A live mode without its key or without a spend cap raises ConfigError at startup,
naming each missing variable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from api.llm.models import DEFAULT_FREE_CHAIN, MAX_FREE_CHAIN

ENV_SETUP_DOC = "refdocs/guides/env_setup.md"

Mode = Literal["fake", "live"]


class ConfigError(Exception):
    """Startup configuration is unusable. The message names every missing variable."""

    def __init__(self, missing: list[tuple[str, str]]):
        self.missing = missing
        lines = [f"  {name}: {why}" for name, why in missing]
        super().__init__(
            "Missing required configuration:\n"
            + "\n".join(lines)
            + f"\nSee {ENV_SETUP_DOC} for where to get each value."
        )


class Settings(BaseSettings):
    """Field names are the variable names, case-insensitively."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    synapse_llm_mode: Mode = "fake"
    data_dir: Path = Path("./data")
    ledger_path: Path | None = None
    """Where the spend ledger lives. Unset: `<data_dir>/ledger.db`, ONE file so the monthly cap covers every run."""
    kit_dist_dir: Path = Path("./packages/kit/dist")
    """Where the built Kit lives (`<semver>/core.js` and `manifest.json`). Served at /vendor/kit/ and read by the render harness."""
    public_origin: str = "http://localhost:3000"
    """The origin the web app is served from. The injected CSP names it, because an opaque-origin srcdoc makes 'self' match nothing."""
    log_level: str = "INFO"
    corpus_dir: Path | None = None
    """The local textbook corpus (api/evidence). Never in the repository. Unset: no citation can be verified and `kit-verified` cannot be minted."""
    verify_interaction_seconds: float = 10.0
    """How long the render harness presses controls and inputs while verifying one Environment. Tests use 1; do not go below 5 for real use."""

    rate_limit_per_minute: int = 20
    """Questions one client address may ask per minute (0 turns the limit off). Behind a proxy every client shares the proxy's address: set it at the proxy too."""
    flag_evict_threshold: int = 3
    """How many flags take an Environment out of the library and write a regression record (P5). 0 turns eviction off; a flag is then only counted."""
    daily_limit_per_client: int = 200
    """Questions one client address may ask per UTC day (0 turns the limit off). There are no accounts, so an address stands for a session (deploy gate, D-11)."""
    daily_limit_total: int = 0
    """Questions the whole server answers per UTC day (0 turns the limit off). Set it before any public deploy: it bounds a crowd of addresses before the monthly spend cap does."""
    max_concurrent_asks: int = 3
    """How many questions are worked on at once. Each can launch a browser to verify an Environment, so this bounds memory and CPU (0 turns it off)."""
    prompt_caching: bool = False
    """Ask the provider to cache the system prompt of every call (B6, D-55). Off until one measured run shows a real saving: the ledger already prices cache reads and
    writes, so turning it on cannot under-count, but the saving is not yet measured."""
    lane_preference: Literal["kit", "balanced", "free"] = "balanced"
    """Which lane leads after a Plan passes its checks (W18, D-76, the owner's call: "leaning more towards free"). `balanced`: the Free lane leads when the planner says the
    Kit only partly fits the question or the Plan draws no picture; `free`: it leads for every question; `kit`: only when the Kit cannot take the question. A refused Free page
    falls back to the Kit lab. Each Free page costs a paid generation and a paid second reading."""
    generation_tier: Literal["standard", "heavy"] = "standard"
    """Which model tier plans the Kit lab and writes the Free and simple pages (W20). `heavy` (Opus) for a demo day, the owner's call: a stronger writer with
    larger output limits, at several times the spend per question; the readers keep their own tier. Switch back to `standard` after."""
    free_lane_enabled: bool = True
    """Let a question the Kit cannot express get a whole model-written page (the labelled Free lane, D-07, D-41). On by default since W16 (D-67, the owner's call:
    "u should be able to generate anything related to simulation or experiments"). It also needs the wording check, which the API turns on only in live mode, so it
    does nothing in fake mode. Each Free page costs a paid generation and a paid second reading, inside the spend caps."""
    bm_show_drafts: bool = True
    """Serve Bahasa Melayu Environments whose translation has not been reviewed by a fluent person (W12, D-62). On by default since W16 (D-68, the owner's call: no
    reviewer will be found, "basically just leave on"); the web marks every such lab "draft translation". Turn it off to serve reviewed translations only."""
    store_attestation_key: SecretStr | None = None
    """HMAC key that signs stored Environments (A-19). Keep it OUTSIDE the data directory. Unset: rows are unsigned and the gate trusts the store."""
    anthropic_api_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None
    llm_free_chain: str = ""
    """Free OpenRouter models tried before the paid provider (D-83), comma separated, in order, at most three, each ending ':free'. Empty: the default chain
    (`api.llm.models.DEFAULT_FREE_CHAIN`) whenever OPENROUTER_API_KEY is set. 'off': no free models, Anthropic only (the old behaviour)."""
    llm_monthly_cap_usd: float | None = None
    llm_total_cap_usd: float | None = None
    """An all-time budget for the whole project, enforced beside the monthly cap (which resets on the 1st). Unset: only the monthly cap applies."""

    def free_chain(self) -> tuple[str, ...]:
        """The free models to try before the paid one, in order: empty without an OpenRouter key or when LLM_FREE_CHAIN is 'off'."""
        if not _has(self.openrouter_api_key):
            return ()
        raw = self.llm_free_chain.strip()
        if raw.lower() in ("off", "none"):
            return ()
        if not raw:
            return DEFAULT_FREE_CHAIN
        return tuple(m.strip() for m in raw.split(",") if m.strip())

    def free_chain_problem(self) -> str | None:
        chain = self.free_chain()
        if len(chain) > MAX_FREE_CHAIN:
            return f"at most {MAX_FREE_CHAIN} models, got {len(chain)}"
        bad = [m for m in chain if not (m.endswith(":free") or m == "openrouter/free")]
        if bad:
            return f"only free models are allowed (ids ending ':free'); not free: {', '.join(bad)}"
        return None

    def resolved_ledger_path(self) -> Path:
        return self.ledger_path if self.ledger_path is not None else self.data_dir / "ledger.db"

    def missing_for_mode(self) -> list[tuple[str, str]]:
        """Variables the selected mode requires but the environment did not supply."""
        missing: list[tuple[str, str]] = []
        if self.synapse_llm_mode == "live":
            if not _has(self.anthropic_api_key):
                missing.append(("ANTHROPIC_API_KEY", "required when SYNAPSE_LLM_MODE=live"))
            problem = self.free_chain_problem()
            if problem is not None:
                missing.append(("LLM_FREE_CHAIN", problem))
            if self.llm_monthly_cap_usd is None or self.llm_monthly_cap_usd <= 0:
                missing.append(("LLM_MONTHLY_CAP_USD", "required (a positive number) when SYNAPSE_LLM_MODE=live"))
            if not self.resolved_ledger_path().is_absolute():
                missing.append(
                    (
                        "LEDGER_PATH",
                        "must be an absolute path when SYNAPSE_LLM_MODE=live, so the cap holds whatever directory the API is started from",
                    )
                )
        return missing


def _has(secret: SecretStr | None) -> bool:
    return secret is not None and bool(secret.get_secret_value().strip())


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    """Build settings and fail loudly if live mode lacks its key or cap.

    Tests pass env_file=None so a developer's real .env never leaks into them.
    """
    settings = Settings(_env_file=env_file)  # pyright: ignore[reportCallIssue]
    missing = settings.missing_for_mode()
    if missing:
        raise ConfigError(missing)
    return settings
