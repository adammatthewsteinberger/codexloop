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

COMMANDS: tuple[ControlCommand, ...] = (
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
def test_control_command_round_trips_through_json_dict(command: ControlCommand) -> None:
    data = command.to_dict()
    encoded = json.loads(json.dumps(data))
    restored = parse_control(encoded)
    assert restored == command


def test_control_command_is_the_inbox_union() -> None:
    assert ControlCommand == (
        Stop
        | Prompt
        | SetModel
        | SetEffort
        | SetApproval
        | SetSandbox
        | SetCwd
        | Snapshot
        | ResourceMutate
    )
    for command in COMMANDS:
        assert isinstance(command, ControlCommand)


def test_unknown_command_kind_is_rejected_not_ignored() -> None:
    with pytest.raises(ConfigurationError):
        parse_control({"kind": "launch_missiles"})
    with pytest.raises(ConfigurationError):
        parse_control({"kind": "STOP"})


def test_missing_kind_is_rejected() -> None:
    with pytest.raises(ConfigurationError):
        parse_control({"text": "no kind here"})


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "prompt"},
        {"kind": "prompt", "text": "hi"},
        {"kind": "set_model"},
        {"kind": "set_effort"},
        {"kind": "set_approval"},
        {"kind": "set_sandbox"},
        {"kind": "set_cwd"},
        {"kind": "resource_mutate"},
    ],
    ids=[
        "prompt_missing_fields",
        "prompt_missing_timing",
        "set_model_missing_model",
        "set_effort_missing_effort",
        "set_approval_missing_policy",
        "set_sandbox_missing_sandbox",
        "set_cwd_missing_cwd",
        "resource_mutate_missing_payload",
    ],
)
def test_known_kind_missing_fields_raise_configuration_error(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ConfigurationError):
        parse_control(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "prompt", "text": "hi", "timing": "later"},
        {"kind": "set_effort", "effort": "turbo"},
        {"kind": "set_approval", "policy": "sometimes"},
        {"kind": "set_sandbox", "sandbox": "no-box"},
    ],
    ids=[
        "bad_prompt_timing",
        "bad_effort",
        "bad_approval_policy",
        "bad_sandbox_mode",
    ],
)
def test_known_kind_bad_enum_strings_raise_configuration_error(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ConfigurationError):
        parse_control(payload)


def test_resource_mutate_bad_payload_raises_configuration_error() -> None:
    with pytest.raises(ConfigurationError):
        parse_control({"kind": "resource_mutate", "payload": "not-a-mapping"})
    with pytest.raises(ConfigurationError):
        parse_control({"kind": "resource_mutate", "payload": None})


def test_prompt_timing_values() -> None:
    assert PromptTiming.NOW.value == "now"
    assert PromptTiming.NEXT_TURN.value == "next_turn"


def test_stop_inbox_shape() -> None:
    assert Stop().to_dict() == {"kind": "stop"}
    assert parse_control({"kind": "stop"}) == Stop()


def test_control_variants_are_frozen_slots() -> None:
    for command in COMMANDS:
        params = command.__dataclass_params__
        assert params.frozen is True
        assert params.slots is True
