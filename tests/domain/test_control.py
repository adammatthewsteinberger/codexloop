"""Operator inbox ControlCommand ADT: JSON round-trip, unknown kinds rejected."""

from __future__ import annotations

import json

import pytest

from codexloop.domain.approval import ApprovalPolicy, SandboxMode
from codexloop.domain.control import (
    ControlCommand,
    Prompt,
    PromptTiming,
    ResourceMutate,
    SetApproval,
    SetCwd,
    SetEffort,
    SetModel,
    SetSandbox,
    Snapshot,
    Stop,
    parse_control,
)
from codexloop.domain.errors import ConfigurationError
from codexloop.domain.model_profile import Effort

COMMANDS: tuple[object, ...] = (
    Stop(),
    Prompt(text="keep going", timing=PromptTiming.NOW),
    Prompt(text="after this turn", timing=PromptTiming.NEXT_TURN),
    SetModel(model="gpt-5"),
    SetEffort(effort=Effort.HIGH),
    SetApproval(policy=ApprovalPolicy.NEVER),
    SetSandbox(sandbox=SandboxMode.WORKSPACE_WRITE),
    SetCwd(cwd="/tmp/proj"),
    Snapshot(),
    ResourceMutate(payload={"cpu": 2, "mem": "4g"}),
)


@pytest.mark.parametrize("command", COMMANDS, ids=lambda c: type(c).__name__ + repr(c))
def test_control_command_round_trips_through_json_dict(command: object) -> None:
    assert hasattr(command, "to_dict")
    data = command.to_dict()  # type: ignore[union-attr]
    encoded = json.loads(json.dumps(data))
    restored = parse_control(encoded)
    assert restored == command
    assert ControlCommand.from_dict(encoded) == command


def test_unknown_command_kind_is_rejected_not_ignored() -> None:
    with pytest.raises(ConfigurationError):
        parse_control({"kind": "launch_missiles"})
    with pytest.raises(ConfigurationError):
        ControlCommand.from_dict({"kind": "STOP"})


def test_missing_kind_is_rejected() -> None:
    with pytest.raises(ConfigurationError):
        parse_control({"text": "no kind here"})


def test_prompt_timing_values() -> None:
    assert PromptTiming.NOW.value == "now"
    assert PromptTiming.NEXT_TURN.value == "next_turn"


def test_stop_inbox_shape() -> None:
    assert Stop().to_dict() == {"kind": "stop"}
    assert parse_control({"kind": "stop"}) == Stop()


def test_control_variants_are_frozen_slots() -> None:
    for command in COMMANDS:
        params = command.__dataclass_params__  # type: ignore[union-attr]
        assert params.frozen is True
        assert params.slots is True
