"""Operator inbox commands: parse a JSON dict, never ignore unknown kinds."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from codexloop.domain.approval import ApprovalPolicy, SandboxMode
from codexloop.domain.errors import ConfigurationError
from codexloop.domain.model_profile import Effort


class PromptTiming(StrEnum):
    NOW = "now"
    NEXT_TURN = "next_turn"


@dataclass(frozen=True, slots=True)
class Stop:
    def to_dict(self) -> dict[str, object]:
        return {"kind": "stop"}


@dataclass(frozen=True, slots=True)
class Prompt:
    text: str
    timing: PromptTiming

    def to_dict(self) -> dict[str, object]:
        return {"kind": "prompt", "text": self.text, "timing": self.timing.value}


@dataclass(frozen=True, slots=True)
class SetModel:
    model: str

    def to_dict(self) -> dict[str, object]:
        return {"kind": "set_model", "model": self.model}


@dataclass(frozen=True, slots=True)
class SetEffort:
    effort: Effort

    def to_dict(self) -> dict[str, object]:
        return {"kind": "set_effort", "effort": self.effort.value}


@dataclass(frozen=True, slots=True)
class SetApproval:
    policy: ApprovalPolicy

    def to_dict(self) -> dict[str, object]:
        return {"kind": "set_approval", "policy": self.policy.value}


@dataclass(frozen=True, slots=True)
class SetSandbox:
    sandbox: SandboxMode

    def to_dict(self) -> dict[str, object]:
        return {"kind": "set_sandbox", "sandbox": self.sandbox.value}


@dataclass(frozen=True, slots=True)
class SetCwd:
    cwd: str

    def to_dict(self) -> dict[str, object]:
        return {"kind": "set_cwd", "cwd": self.cwd}


@dataclass(frozen=True, slots=True)
class Snapshot:
    def to_dict(self) -> dict[str, object]:
        return {"kind": "snapshot"}


@dataclass(frozen=True, slots=True)
class ResourceMutate:
    payload: dict[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", dict(self.payload))

    def to_dict(self) -> dict[str, object]:
        return {"kind": "resource_mutate", "payload": dict(self.payload)}


InboxCommand = (
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


def parse_control(data: Mapping[str, object]) -> InboxCommand:
    kind = data.get("kind")
    if not isinstance(kind, str):
        raise ConfigurationError("control command missing kind")
    builder = _BUILDERS.get(kind)
    if builder is None:
        raise ConfigurationError(f"unknown control command kind: {kind!r}")
    return builder(data)


class ControlCommand:
    """Factory for inbox command variants (``Stop | Prompt | …``)."""

    @staticmethod
    def from_dict(data: Mapping[str, object]) -> InboxCommand:
        return parse_control(data)


def _parse_stop(_data: Mapping[str, object]) -> Stop:
    return Stop()


def _parse_prompt(data: Mapping[str, object]) -> Prompt:
    return Prompt(text=str(data["text"]), timing=PromptTiming(str(data["timing"])))


def _parse_set_model(data: Mapping[str, object]) -> SetModel:
    return SetModel(model=str(data["model"]))


def _parse_set_effort(data: Mapping[str, object]) -> SetEffort:
    return SetEffort(effort=Effort(str(data["effort"])))


def _parse_set_approval(data: Mapping[str, object]) -> SetApproval:
    return SetApproval(policy=ApprovalPolicy(str(data["policy"])))


def _parse_set_sandbox(data: Mapping[str, object]) -> SetSandbox:
    return SetSandbox(sandbox=SandboxMode(str(data["sandbox"])))


def _parse_set_cwd(data: Mapping[str, object]) -> SetCwd:
    return SetCwd(cwd=str(data["cwd"]))


def _parse_snapshot(_data: Mapping[str, object]) -> Snapshot:
    return Snapshot()


def _parse_resource_mutate(data: Mapping[str, object]) -> ResourceMutate:
    payload = cast(Mapping[str, object], data["payload"])
    return ResourceMutate(payload=dict(payload))


_BUILDERS: dict[str, Callable[[Mapping[str, object]], InboxCommand]] = {
    "stop": _parse_stop,
    "prompt": _parse_prompt,
    "set_model": _parse_set_model,
    "set_effort": _parse_set_effort,
    "set_approval": _parse_set_approval,
    "set_sandbox": _parse_set_sandbox,
    "set_cwd": _parse_set_cwd,
    "snapshot": _parse_snapshot,
    "resource_mutate": _parse_resource_mutate,
}
