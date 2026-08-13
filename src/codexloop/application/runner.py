"""AutonomousRunner — executes domain.loop Decisions against application ports."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import assert_never

from codexloop.application.dto import RunResult, TurnOutcome
from codexloop.application.ports import (
    AgentGateway,
    CapacityProbe,
    Clock,
    RunControl,
    RunStateStore,
    SessionLock,
    Sleeper,
    ThreadCatalog,
)
from codexloop.domain.budget import Budget, BudgetLedger
from codexloop.domain.capacity import Available, CapacityState
from codexloop.domain.classify import classify
from codexloop.domain.completion import (
    DEFAULT_DONE_MARKER,
    CompletionEvaluator,
    CompletionVerdict,
    Continue,
)
from codexloop.domain.loop import (
    BackoffUntil,
    Drain,
    Finish,
    LoopOutcome,
    Probe,
    RunLoopStateMachine,
    RunState,
    SendTurn,
    WaitUntil,
)
from codexloop.domain.plan import WorkPlan
from codexloop.domain.session import Explicit, MostRecent, PlanFile, SessionSelector, ThreadRef
from codexloop.domain.waiting import AdaptiveWaitPolicy, WaitConfig

_FAR_FUTURE = timedelta(days=3650)
_ZERO = timedelta(0)


def _discard_artifact(name: str, content: str) -> None:
    del name, content


@dataclass
class RunnerContext:
    """Ports and knobs the runner needs. Unused collaborators may be omitted."""

    clock: Clock
    sleeper: Sleeper
    gateway: AgentGateway
    probe: CapacityProbe
    store: RunStateStore
    control: RunControl
    catalog: ThreadCatalog | None = None
    lock: SessionLock | None = None
    write_artifact: Callable[[str, str], None] | None = None
    budget: Budget = field(
        default_factory=lambda: Budget(max_turns=None, max_dollars=None, max_wall_clock=None)
    )
    wait_policy: AdaptiveWaitPolicy | None = None
    max_wait: timedelta | None = None
    run_id: str = "anonymous"
    cwd: str = "."
    model: str = "unknown"


class AutonomousRunner:
    def __init__(self, ctx: RunnerContext) -> None:
        self._clock = ctx.clock
        self._sleeper = ctx.sleeper
        self._gateway = ctx.gateway
        self._probe = ctx.probe
        self._store = ctx.store
        self._control = ctx.control
        self._catalog = ctx.catalog
        self._lock = ctx.lock
        self._write_artifact = ctx.write_artifact or _discard_artifact
        self._budget = ctx.budget
        self._wait_policy = ctx.wait_policy or AdaptiveWaitPolicy(WaitConfig(), rand=lambda: 0.0)
        self._max_wait = ctx.max_wait
        self._run_id = ctx.run_id
        self._cwd = ctx.cwd
        self._model = ctx.model
        self._machine = RunLoopStateMachine()
        self._evaluator = CompletionEvaluator()
        self._ledger = BudgetLedger(ctx.budget)

    async def run(self, selector: SessionSelector, plan: str) -> RunResult:
        thread_id = self._thread_id_from(selector)
        plan_text, remaining, first_turn = self._restore(thread_id, plan)
        if plan_text:
            parsed = WorkPlan.parse(plan_text)
            if not remaining:
                remaining = list(parsed.remaining_work)

        locked_id: str | None = None
        if self._lock is not None and thread_id is not None:
            if not self._lock.acquire(thread_id):
                await self._gateway.close()
                return RunResult(success=False, reason="lock", turns=0, thread_id=thread_id)
            locked_id = thread_id

        state = RunState.Preflight
        outcome = LoopOutcome(capacity=Available())
        started = self._clock.now()
        last_mark = started
        deadline = started + (self._max_wait if self._max_wait is not None else _FAR_FUTURE)
        wait_attempt = 0

        try:
            while True:
                controls = list(self._control.poll())
                now = self._clock.now()
                last_mark = self._record_elapsed(last_mark, now)

                if state is RunState.Preflight:
                    probed = await self._probe.probe()
                    outcome = LoopOutcome(
                        capacity=probed.outcome,
                        deadline_exceeded=now >= deadline,
                    )
                else:
                    outcome = replace(outcome, deadline_exceeded=now >= deadline)

                state, decision = self._machine.advance(state, outcome, now, self._ledger, controls)

                match decision:
                    case SendTurn():
                        prompt = plan_text if first_turn else _continuation(remaining)
                        first_turn = False
                        turn = await self._gateway.send_turn(prompt)
                        if turn.thread_id:
                            thread_id = turn.thread_id
                            locked_id = self._maybe_lock(thread_id, locked_id)
                        last_mark = self._record_elapsed(last_mark, self._clock.now())
                        self._ledger.record(turns=1, dollars=turn.cost_dollars)
                        capacity, completion = _interpret(turn, self._evaluator)
                        if isinstance(completion, Continue):
                            remaining = list(completion.remaining)
                        self._persist(
                            key=thread_id,
                            remaining=remaining,
                            first_turn_done=True,
                            plan_text=plan_text,
                        )
                        self._record_thread(thread_id, started)
                        wait_attempt = 0
                        outcome = LoopOutcome(capacity=capacity, completion=completion)
                    case Probe():
                        probed = await self._probe.probe()
                        outcome = LoopOutcome(capacity=probed.outcome)
                    case WaitUntil() | BackoffUntil():
                        until = self._wait_policy.next_probe_at(
                            outcome.capacity, self._clock.now(), wait_attempt, deadline
                        )
                        wait_attempt += 1
                        await self._sleeper.sleep_until(until)
                    case Drain():
                        self._write_stop_summary(thread_id, remaining)
                        self._persist(
                            key=thread_id,
                            remaining=remaining,
                            first_turn_done=not first_turn,
                            plan_text=plan_text,
                        )
                    case Finish() as finish:
                        self._persist(
                            key=thread_id,
                            remaining=remaining,
                            first_turn_done=not first_turn,
                            plan_text=plan_text,
                        )
                        return RunResult(
                            success=finish.success,
                            reason=finish.reason,
                            turns=self._ledger.turns,
                            thread_id=thread_id,
                        )
                    case _:  # pragma: no cover — Decision is a closed union
                        assert_never(decision)
        finally:
            if locked_id is not None and self._lock is not None:
                self._lock.release(locked_id)
            await self._gateway.close()

    def _thread_id_from(self, selector: SessionSelector) -> str | None:
        match selector:
            case Explicit(thread_id=thread_id):
                return thread_id
            case MostRecent():
                return self._most_recent()
            case PlanFile():
                return None
            case _:  # pragma: no cover — SessionSelector is a closed union
                assert_never(selector)

    def _most_recent(self) -> str | None:
        if self._catalog is None:
            return None
        threads = list(self._catalog.list_threads())
        if not threads:
            return None
        latest = max(threads, key=lambda ref: ref.started_at)
        return latest.thread_id

    def _restore(self, thread_id: str | None, plan: str) -> tuple[str, list[str], bool]:
        if thread_id is None:
            return plan, [], True
        stored = self._store.load(thread_id)
        if stored is None:
            return plan, [], True
        plan_text = str(stored.get("plan_text") or plan)
        remaining_raw = stored.get("remaining_work") or []
        remaining = [str(item) for item in remaining_raw] if isinstance(remaining_raw, list) else []
        first_turn = not bool(stored.get("first_turn_done"))
        turns = _int_field(stored.get("turns"))
        dollars = _float_field(stored.get("dollars"))
        elapsed_s = _float_field(stored.get("elapsed_seconds"))
        if turns or dollars or elapsed_s:
            self._ledger.record(turns=turns, dollars=dollars, elapsed=timedelta(seconds=elapsed_s))
        return plan_text, remaining, first_turn

    def _maybe_lock(self, thread_id: str, locked_id: str | None) -> str | None:
        if self._lock is None or locked_id is not None:
            return locked_id
        if self._lock.acquire(thread_id):
            return thread_id
        return None

    def _record_elapsed(self, last_mark: datetime, now: datetime) -> datetime:
        delta = now - last_mark
        if delta > _ZERO:
            self._ledger.record(elapsed=delta)
        return now

    def _persist(
        self,
        *,
        key: str | None,
        remaining: Sequence[str],
        first_turn_done: bool,
        plan_text: str,
    ) -> None:
        run_id = key or self._run_id
        self._store.save(
            run_id,
            {
                "thread_id": key,
                "turns": self._ledger.turns,
                "dollars": self._ledger.dollars,
                "elapsed_seconds": self._ledger.elapsed.total_seconds(),
                "remaining_work": list(remaining),
                "first_turn_done": first_turn_done,
                "plan_text": plan_text,
            },
        )

    def _record_thread(self, thread_id: str | None, started: datetime) -> None:
        if self._catalog is None or thread_id is None:
            return
        self._catalog.record(
            ThreadRef(
                thread_id=thread_id,
                cwd=self._cwd,
                started_at=started,
                model=self._model,
            )
        )

    def _write_stop_summary(self, thread_id: str | None, remaining: Sequence[str]) -> None:
        items = "\n".join(f"- {item}" for item in remaining) if remaining else "_none_"
        body = (
            "# Stop summary\n\n"
            "**Reason:** stop\n"
            f"**Thread:** `{thread_id or 'unknown'}`\n"
            f"**Turns:** {self._ledger.turns}\n\n"
            "## Remaining work\n\n"
            f"{items}\n"
        )
        self._write_artifact("stop-summary.md", body)


def _continuation(remaining: Sequence[str]) -> str:
    if remaining:
        items = "\n".join(f"- {name}" for name in remaining)
        body = f"Continue. Remaining work:\n{items}"
    else:
        body = "Continue."
    return (
        f"{body}\n\n"
        "When the entire task is fully complete, output "
        f"{DEFAULT_DONE_MARKER} on its own line."
    )


def _interpret(
    turn: TurnOutcome, evaluator: CompletionEvaluator
) -> tuple[CapacityState, CompletionVerdict]:
    if turn.signals is None:
        return Available(), Continue(remaining=[])
    capacity = classify(turn.signals)
    return capacity, evaluator.evaluate(turn.signals, capacity)


def _int_field(value: object) -> int:
    if isinstance(value, int):
        return value
    return 0


def _float_field(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    return 0.0


__all__ = ["AutonomousRunner", "RunnerContext"]
