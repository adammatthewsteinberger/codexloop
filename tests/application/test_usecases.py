"""Thin use-case wrappers around AutonomousRunner and the ports."""

from __future__ import annotations

from datetime import UTC, datetime

from codexloop.application.dto import ProbeResult, RunResult, TurnOutcome
from codexloop.application.runner import RunnerContext
from codexloop.application.usecases.list_threads import list_threads
from codexloop.application.usecases.preflight import preflight
from codexloop.application.usecases.resume_thread import resume_thread
from codexloop.application.usecases.run_plan import run_plan
from codexloop.domain.budget import Budget
from codexloop.domain.capacity import Available, QuotaExhausted
from codexloop.domain.completion import DEFAULT_DONE_MARKER
from codexloop.domain.session import PlanFile, ThreadRef
from codexloop.domain.signals import TurnSignals
from tests.application.fakes import (
    FakeAgentGateway,
    FakeCapacityProbe,
    FakeClock,
    FakeRunControl,
    FakeRunStateStore,
    FakeSleeper,
    FakeThreadCatalog,
)

NOW = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
PLAN = "- [ ] Add login\n"
THREAD_ID = "thr_use"


def _ctx(
    *,
    outcomes: list[TurnOutcome],
    probes: ProbeResult | None = None,
    catalog: FakeThreadCatalog | None = None,
    store: FakeRunStateStore | None = None,
) -> RunnerContext:
    clock = FakeClock(NOW)
    return RunnerContext(
        clock=clock,
        sleeper=FakeSleeper(clock),
        gateway=FakeAgentGateway(outcomes),
        probe=FakeCapacityProbe(probes),
        store=store or FakeRunStateStore(),
        control=FakeRunControl(),
        catalog=catalog,
        budget=Budget(max_turns=None, max_dollars=None, max_wall_clock=None),
    )


def _done() -> TurnOutcome:
    return TurnOutcome(
        thread_id=THREAD_ID,
        signals=TurnSignals(final_message=DEFAULT_DONE_MARKER),
    )


async def test_run_plan_drives_the_runner_to_done() -> None:
    result = await run_plan(_ctx(outcomes=[_done()]), PlanFile("plan.md"), PLAN)
    assert result == RunResult(success=True, reason="done", turns=1, thread_id=THREAD_ID)


async def test_resume_thread_uses_explicit_selector() -> None:
    store = FakeRunStateStore()
    store.save(
        THREAD_ID,
        {
            "thread_id": THREAD_ID,
            "turns": 1,
            "remaining_work": ["Add login"],
            "first_turn_done": True,
            "plan_text": PLAN,
            "dollars": 0.0,
            "elapsed_seconds": 0.0,
        },
    )
    result = await resume_thread(
        _ctx(outcomes=[_done()], store=store),
        THREAD_ID,
        PLAN,
    )
    assert result.success is True
    assert result.thread_id == THREAD_ID
    assert isinstance(result, RunResult)


async def test_preflight_returns_probe_result() -> None:
    exhausted = ProbeResult(outcome=QuotaExhausted(reason="insufficient_quota"))
    result = await preflight(_ctx(outcomes=[_done()], probes=exhausted))
    assert result == exhausted


def test_list_threads_delegates_to_catalog() -> None:
    catalog = FakeThreadCatalog()
    ref = ThreadRef(thread_id="thr_a", cwd="/work", started_at=NOW, model="gpt-5")
    catalog.record(ref)
    assert list(list_threads(_ctx(outcomes=[_done()], catalog=catalog))) == [ref]


def test_list_threads_without_catalog_is_empty() -> None:
    assert list(list_threads(_ctx(outcomes=[_done()], catalog=None))) == []


async def test_preflight_available_by_default() -> None:
    result = await preflight(_ctx(outcomes=[_done()]))
    assert result == ProbeResult(outcome=Available())
