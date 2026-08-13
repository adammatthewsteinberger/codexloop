"""Pure domain layer — stdlib only."""

from codexloop.domain.error_codes import ErrorClass, classify_code
from codexloop.domain.errors import (
    AuthError,
    BudgetExceeded,
    CapacityError,
    CodexBinaryError,
    CodexloopError,
    CodexProtocolError,
    ConfigurationError,
    WaitDeadlineExceeded,
)

__all__ = [
    "AuthError",
    "BudgetExceeded",
    "CapacityError",
    "CodexBinaryError",
    "CodexloopError",
    "CodexProtocolError",
    "ConfigurationError",
    "ErrorClass",
    "WaitDeadlineExceeded",
    "classify_code",
]
