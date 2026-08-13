"""Use case: pre-flight doctor checks before a long unattended run."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class DoctorReport:
    checks: tuple[DoctorCheck, ...]
    auth_mode: str
    probe_strategies: Mapping[str, bool] = field(default_factory=dict)

    @property
    def all_passed(self) -> bool:
        return all(check.passed for check in self.checks)


class DoctorEnvironment(Protocol):
    def diagnose(self, *, cwd: Path) -> DoctorReport: ...


def run_doctor(env: DoctorEnvironment, *, cwd: Path) -> DoctorReport:
    return env.diagnose(cwd=cwd)


__all__ = ["DoctorCheck", "DoctorEnvironment", "DoctorReport", "run_doctor"]
