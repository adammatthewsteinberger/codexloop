"""Wind-down coverage: exercise interrupt pass-through and control-command continue."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from codexloop.application.dto import TurnOutcome
from codexloop.application.runner import AutonomousRunner, RunnerContext
from codexloop.domain.completion import DEFAULT_DONE_MARKER
from codexloop.domain.control import Stop, WindDownCommand
from codexloop.domain.session import PlanFile
from codexloop.domain.signals import TurnSignals
from tests.application.fakes import (
    FakeAgentGateway,
    FakeCapacityProbe,
    FakeClock,
    FakeRunControl,
    FakeRunStateStore,
    FakeSleeper,
)

NOW = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)
PLAN = "- [ ] Test coverage\n"
THREAD_ID = "thr_coverage"


def _continue(remaining: list[str]) -> TurnOutcome:
    return TurnOutcome(
        thread_id=THREAD_ID,
        signals=TurnSignals(
            structured_output={
                "complete": False,
                "remaining_work": remaining,
            }
        ),
    )


def _done() -> TurnOutcome:
    return TurnOutcome(
        thread_id=THREAD_ID,
        signals=TurnSignals(final_message=DEFAULT_DONE_MARKER),
    )


@pytest.mark.asyncio
async def test_stop_interrupt_during_wait_passes_through() -> None:
    """Stop interrupt during wait hits the pass statement in case 'stop'."""
    clock = FakeClock(NOW)
    sleeper = FakeSleeper(clock)
    # First poll empty, second poll returns Stop during sleep
    control = FakeRunControl(script=[[], [Stop()]])

    ctx = RunnerContext(
        clock=clock,
        sleeper=sleeper,
        gateway=FakeAgentGateway([_continue(["work"])]),
        probe=FakeCapacityProbe(),
        store=FakeRunStateStore(),
        control=control,
    )
    runner = AutonomousRunner(ctx)

    # Sleep should return early with "stop"
    target = clock.now() + timedelta(seconds=10)
    result = await runner._sleep_interruptible(target)

    assert result == "stop"
    assert clock.now() < target


@pytest.mark.asyncio
async def test_wind_down_interrupt_during_wait_passes_through() -> None:
    """WindDownCommand interrupt during wait hits the pass statement in case 'wind_down'."""
    clock = FakeClock(NOW)
    sleeper = FakeSleeper(clock)
    # First poll empty, second poll returns WindDownCommand during sleep
    control = FakeRunControl(script=[[], [WindDownCommand(reason="test")]])

    ctx = RunnerContext(
        clock=clock,
        sleeper=sleeper,
        gateway=FakeAgentGateway([_continue(["work"])]),
        probe=FakeCapacityProbe(),
        store=FakeRunStateStore(),
        control=control,
    )
    runner = AutonomousRunner(ctx)

    # Sleep should return early with "wind_down"
    target = clock.now() + timedelta(seconds=10)
    result = await runner._sleep_interruptible(target)

    assert result == "wind_down"
    assert clock.now() < target


@pytest.mark.asyncio
async def test_wind_down_command_in_control_is_skipped_in_apply() -> None:
    """WindDownCommand in control commands hits the continue in _apply_control_commands."""
    clock = FakeClock(NOW)
    # WindDownCommand arrives immediately
    control = FakeRunControl([WindDownCommand(reason="coverage test")])

    ctx = RunnerContext(
        clock=clock,
        sleeper=FakeSleeper(clock),
        gateway=FakeAgentGateway([_done()]),
        probe=FakeCapacityProbe(),
        store=FakeRunStateStore(),
        control=control,
    )

    result = await AutonomousRunner(ctx).run(PlanFile("plan.md"), PLAN)

    # WindDownCommand is handled by state machine, not by _apply_control_commands
    # The command should be safely skipped (continue), and run should complete normally
    assert result.success is True


@pytest.mark.asyncio
async def test_sleep_interruptible_with_non_interrupt_command() -> None:
    """Non-interrupt commands during sleep hit the False branch of
    isinstance(cmd, WindDownCommand)."""
    from codexloop.domain.control import Prompt, PromptTiming

    clock = FakeClock(NOW)
    sleeper = FakeSleeper(clock)
    # First poll empty, second poll returns a Prompt (non-interrupt command)
    # This hits the 547->544 branch (WindDownCommand check False, loop continues)
    control = FakeRunControl(script=[[], [Prompt(text="test", timing=PromptTiming.NEXT_TURN)]])

    ctx = RunnerContext(
        clock=clock,
        sleeper=sleeper,
        gateway=FakeAgentGateway(),
        probe=FakeCapacityProbe(),
        store=FakeRunStateStore(),
        control=control,
    )
    runner = AutonomousRunner(ctx)

    # Sleep should NOT return early for non-interrupt commands
    target = clock.now() + timedelta(seconds=1)
    result = await runner._sleep_interruptible(target)

    # No interrupt, returns None
    assert result is None
    # Should have slept the full duration
    assert clock.now() >= target
