"""Redaction by key and by credential pattern, including nested payloads."""

from __future__ import annotations

import io
import json
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from codexloop.infrastructure.clock import AnyioSleeper, SystemClock
from codexloop.infrastructure.logging import RedactionProcessor, configure_logging, get_logger
from codexloop.infrastructure.progress import LoggingProgressReporter
from codexloop.infrastructure.redact import REDACTED_VALUE, redact
from tests.application.fakes import FakeLogger

_SK_TOKEN = "sk-abcdefghijklmnopqrstuvwxyz0123"
_SECRET_KEYS = (
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
    "authorization",
    "access_token",
    "refresh_token",
    "client_secret",
    "api_key",
)


def test_secret_keys_are_scrubbed() -> None:
    payload = {key: f"value-for-{key}" for key in _SECRET_KEYS}
    redacted = redact(payload)
    for key in _SECRET_KEYS:
        assert redacted[key] == REDACTED_VALUE
        assert f"value-for-{key}" not in json.dumps(redacted)


def test_sk_pattern_is_scrubbed_under_innocuous_key() -> None:
    redacted = redact({"note": f"token={_SK_TOKEN} ok"})
    assert _SK_TOKEN not in redacted["note"]
    assert REDACTED_VALUE in redacted["note"]


def test_redaction_survives_nested_dicts_and_lists() -> None:
    payload = {
        "outer": {
            "OPENAI_API_KEY": "plain-secret",
            "items": [
                {"access_token": "nested-token"},
                f"prefix {_SK_TOKEN} suffix",
            ],
        }
    }
    redacted = redact(payload)
    dumped = json.dumps(redacted)
    assert redacted["outer"]["OPENAI_API_KEY"] == REDACTED_VALUE
    assert redacted["outer"]["items"][0]["access_token"] == REDACTED_VALUE
    assert _SK_TOKEN not in dumped
    assert "plain-secret" not in dumped
    assert "nested-token" not in dumped
    assert REDACTED_VALUE in redacted["outer"]["items"][1]


def test_redaction_processor_scrubs_event_dict() -> None:
    processor = RedactionProcessor()
    event = processor(None, "info", {"event": "auth", "api_key": "secret", "note": _SK_TOKEN})
    assert event["api_key"] == REDACTED_VALUE
    assert _SK_TOKEN not in event["note"]


def test_configure_logging_puts_redaction_in_the_chain() -> None:
    buf = io.StringIO()
    old = sys.stderr
    sys.stderr = buf
    try:
        configure_logging(level="INFO", json_logs=True)
        get_logger(component="unit").info("sample.event", api_key="secret", note=_SK_TOKEN)
    finally:
        sys.stderr = old
        logging.getLogger().handlers.clear()
    text = buf.getvalue()
    assert "secret" not in text
    assert _SK_TOKEN not in text
    json_lines = [json.loads(line) for line in text.splitlines() if line.startswith("{")]
    assert json_lines
    assert json_lines[0]["api_key"] == REDACTED_VALUE


def test_jsonl_audit_log_redacts_payload(tmp_path: Path) -> None:
    from codexloop.infrastructure.audit import JsonlAuditLog

    path = tmp_path / "audit.jsonl"
    log = JsonlAuditLog(path)
    log.append("auth", {"OPENAI_API_KEY": "secret", "ok": True})
    record = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert record["event_type"] == "auth"
    assert record["OPENAI_API_KEY"] == REDACTED_VALUE
    assert record["ok"] is True


def test_progress_reporter_logs_event() -> None:
    logger = FakeLogger()
    reporter = LoggingProgressReporter(logger)
    reporter.report("turn.sent", attempt=2)
    assert logger.events == [("info", "turn.sent", {"attempt": 2})]


def test_system_clock_now_is_timezone_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)
    assert abs((now - datetime.now(UTC)).total_seconds()) < 2


async def test_sleeper_is_noop_when_target_is_in_the_past() -> None:
    clock = SystemClock()
    sleeper = AnyioSleeper(clock)
    past = clock.now() - timedelta(seconds=30)
    start = clock.now()
    await sleeper.sleep_until(past)
    assert (clock.now() - start).total_seconds() < 0.5
