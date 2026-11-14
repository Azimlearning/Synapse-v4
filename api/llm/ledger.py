# Adapted from Azimlearning/Arcana-v2, api/llm/ledger.py @ 21c6dcf5. Read in full. Changes: stdlib logging, this repo's
# SpendCapExceeded, and a ledger that lives at data/ledger.db by default (see Settings.resolved_ledger_path).
"""The spend ledger: every paid call is written here, and the monthly cap is enforced from it.

Callers go through reserve() then settle(): reserve() refuses, before anything is sent, if the month's recorded spend plus
calls already in flight plus this call's worst case would exceed the cap (hard constraint 8).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    Column,
    Engine,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    insert,
    inspect,
    select,
    text,
)
from sqlalchemy.exc import OperationalError

from api.core.errors import SpendCapExceeded

log = logging.getLogger(__name__)

metadata = MetaData()

spend_ledger = Table(
    "spend_ledger",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ts", String, nullable=False),
    Column("month", String, nullable=False, index=True),
    Column("provider", String, nullable=False),
    Column("model", String, nullable=False),
    Column("tokens_in", Integer, nullable=False),
    Column("tokens_out", Integer, nullable=False),
    Column("cost_usd", Float, nullable=False),
    Column("purpose", String, nullable=False),
    Column("status", String, nullable=False),  # "ok" or "failed" (failed attempts cost nothing)
    Column("cache_read_tokens", Integer, nullable=False, server_default="0"),
    Column("cache_write_tokens", Integer, nullable=False, server_default="0"),
)


def engine_for(path: Path) -> Engine:
    """A SQLite engine at `path`, creating the parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")


@dataclass(frozen=True)
class Reservation:
    estimate_usd: float


class SpendLedger:
    def __init__(
        self,
        engine: Engine,
        monthly_cap_usd: float | None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        total_cap_usd: float | None = None,
    ):
        self._engine = engine
        self._cap = monthly_cap_usd
        self._total_cap = total_cap_usd
        """An all-time ceiling on this ledger file, enforced beside the monthly cap: the monthly cap resets on the 1st, a project budget does not."""
        self._clock = clock
        self._lock = threading.Lock()
        self._pending = 0.0
        metadata.create_all(engine)
        self._add_missing_columns()

    def _add_missing_columns(self) -> None:
        """A ledger written before the cache columns existed keeps every row and gains the two columns at zero (SQLAlchemy's create_all never alters a table)."""
        for name in ("cache_read_tokens", "cache_write_tokens"):
            if name in {c["name"] for c in inspect(self._engine).get_columns("spend_ledger")}:
                continue
            try:
                with self._engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE spend_ledger ADD COLUMN {name} INTEGER NOT NULL DEFAULT 0"))
            except OperationalError:
                # Another process (the API and an evaluation script opening the same file at once) added the column between the check and the ALTER.
                # That is fine; anything else that left the column missing is a real fault and is raised.
                if name not in {c["name"] for c in inspect(self._engine).get_columns("spend_ledger")}:
                    raise

    def close(self) -> None:
        """Release the SQLite file. Windows cannot delete a database file that a pooled connection still holds open (Linux can)."""
        self._engine.dispose()

    def month_total(self) -> float:
        month = self._clock().strftime("%Y-%m")
        with self._engine.connect() as conn:
            total = conn.execute(
                select(func.coalesce(func.sum(spend_ledger.c.cost_usd), 0.0)).where(spend_ledger.c.month == month)
            ).scalar_one()
        return float(total)

    def all_time_total(self) -> float:
        with self._engine.connect() as conn:
            return float(conn.execute(select(func.coalesce(func.sum(spend_ledger.c.cost_usd), 0.0))).scalar_one())

    def summary(self) -> dict:
        """This month's spend for the operator: total, cap, what remains, and the split by purpose and by model. No prompt or reply text is ever stored."""
        month = self._clock().strftime("%Y-%m")
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    spend_ledger.c.purpose,
                    spend_ledger.c.model,
                    spend_ledger.c.status,
                    func.count(),
                    func.sum(spend_ledger.c.cost_usd),
                    func.sum(spend_ledger.c.tokens_in),
                    func.sum(spend_ledger.c.tokens_out),
                    func.sum(spend_ledger.c.cache_read_tokens),
                    func.sum(spend_ledger.c.cache_write_tokens),
                )
                .where(spend_ledger.c.month == month)
                .group_by(spend_ledger.c.purpose, spend_ledger.c.model, spend_ledger.c.status)
            ).all()
        by_purpose: dict[str, float] = {}
        by_model: dict[str, float] = {}
        calls = failed = cache_read = cache_write = 0
        for purpose, model, status, n, cost, _tin, _tout, c_read, c_write in rows:
            cache_read += int(c_read or 0)
            cache_write += int(c_write or 0)
            by_purpose[purpose] = by_purpose.get(purpose, 0.0) + float(cost or 0.0)
            by_model[model] = by_model.get(model, 0.0) + float(cost or 0.0)
            calls += int(n)
            failed += int(n) if status == "failed" else 0
        return {
            "month": month,
            "spent_usd": round(self.month_total(), 6),
            "cap_usd": self._cap,
            "remaining_usd": None if self._cap is None else round(self.remaining_usd() or 0.0, 6),
            "total_cap_usd": self._total_cap,
            "all_time_spent_usd": round(self.all_time_total(), 6),
            "calls": calls,
            "failed_calls": failed,
            "cache_read_tokens": cache_read,
            "cache_write_tokens": cache_write,
            "by_purpose": {k: round(v, 6) for k, v in sorted(by_purpose.items())},
            "by_model": {k: round(v, 6) for k, v in sorted(by_model.items())},
        }

    def remaining_usd(self) -> float | None:
        """What may still be spent: the smaller of the monthly cap and the all-time cap, each less what is spent and in flight; None when there is no cap."""
        if self._cap is None and self._total_cap is None:
            return None
        with self._lock:
            room = [
                cap - spent - self._pending
                for cap, spent in ((self._cap, self.month_total() if self._cap is not None else 0.0), (self._total_cap, self.all_time_total() if self._total_cap is not None else 0.0))
                if cap is not None
            ]
            return max(min(room), 0.0)

    def reserve(self, estimate_usd: float) -> Reservation:
        """Claim budget for one call, or raise SpendCapExceeded. Call before the provider. A call that cannot cost anything (a free model, D-83) claims nothing and
        is never refused: a cap that is used up must still let the free providers answer."""
        if estimate_usd <= 0:
            return Reservation(0.0)
        with self._lock:
            if self._cap is not None:
                spent = self.month_total()
                if spent + self._pending + estimate_usd > self._cap:
                    log.warning(
                        "spend_cap_refused cap_usd=%s spent_usd=%.6f in_flight_usd=%.6f estimate_usd=%.6f",
                        self._cap,
                        spent,
                        self._pending,
                        estimate_usd,
                    )
                    raise SpendCapExceeded(
                        f"Monthly LLM cap of ${self._cap:.2f} would be exceeded "
                        f"(${spent:.4f} spent this month, this call may cost up to "
                        f"${estimate_usd:.4f}). The call was not sent."
                    )
            if self._total_cap is not None:
                lifetime = self.all_time_total()
                if lifetime + self._pending + estimate_usd > self._total_cap:
                    log.warning(
                        "total_cap_refused cap_usd=%s spent_usd=%.6f in_flight_usd=%.6f estimate_usd=%.6f",
                        self._total_cap,
                        lifetime,
                        self._pending,
                        estimate_usd,
                    )
                    raise SpendCapExceeded(
                        f"The all-time LLM budget of ${self._total_cap:.2f} would be exceeded "
                        f"(${lifetime:.4f} spent in all, this call may cost up to ${estimate_usd:.4f}). The call was not sent."
                    )
            self._pending += estimate_usd
            return Reservation(estimate_usd)

    def settle(
        self,
        reservation: Reservation,
        *,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        purpose: str,
        status: str = "ok",
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> None:
        """Release the reservation and record what actually happened."""
        now = self._clock()
        with self._lock:
            self._pending = max(self._pending - reservation.estimate_usd, 0.0)
            with self._engine.begin() as conn:
                conn.execute(
                    insert(spend_ledger).values(
                        ts=now.isoformat(),
                        month=now.strftime("%Y-%m"),
                        provider=provider,
                        model=model,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost_usd=cost_usd,
                        purpose=purpose,
                        status=status,
                        cache_read_tokens=cache_read_tokens,
                        cache_write_tokens=cache_write_tokens,
                    )
                )
        log.info(
            "spend_recorded provider=%s model=%s purpose=%s status=%s tokens_in=%d tokens_out=%d cost_usd=%.6f",
            provider,
            model,
            purpose,
            status,
            tokens_in,
            tokens_out,
            cost_usd,
        )

    def rows(self) -> list[dict]:
        with self._engine.connect() as conn:
            result = conn.execute(select(spend_ledger).order_by(spend_ledger.c.id))
            return [dict(r._mapping) for r in result]
