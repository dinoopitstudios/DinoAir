from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from input_processing import InputPipeline, InputPipelineError, IntentType

if TYPE_CHECKING:
    from collections.abc import Callable


def _collector() -> tuple[list[str], Callable[[str], None]]:
    messages: list[str] = []
    return messages, messages.append


class StubWatchdog:
    def __init__(self) -> None:
        self.monitoring = True
        self.thresholds: dict[str, float] = {"vram": 90.0, "ram": 90.0, "cpu": 90.0}

    # Basic API used by handler
    def get_current_metrics(self) -> dict[str, Any]:
        return {
            "vram_percent": 11.0,
            "vram_used": 1.1,
            "vram_total": 10.0,
            "ram_percent": 22.0,
            "ram_used": 3.3,
            "ram_total": 15.0,
            "cpu_percent": 5.0,
        }

    def start_monitoring(self) -> None:
        self.monitoring = True

    def stop_monitoring(self) -> None:
        self.monitoring = False

    def get_metrics_history(self, n: int) -> list[dict[str, Any]]:
        return [
            {
                "timestamp": "2025-01-01T00:00:00",
                "vram_percent": 10.0,
                "ram_percent": 20.0,
                "cpu_percent": 5.0,
            }
        ][:n]

    def clear_metrics_history(self) -> None:
        pass

    def kill_process_by_pid(self, pid: int) -> bool:
        return False

    def kill_process_by_name(self, name: str) -> int:
        return 0


def test_watchdog_status_command_returns_message():
    messages, feedback = _collector()
    wd = StubWatchdog()
    pipeline = InputPipeline(
        gui_feedback_hook=feedback, watchdog_ref=wd, enable_enhanced_security=True
    )

    # Send a command that should be handled by the watchdog handler
    text, intent = pipeline.run("watchdog status")

    if intent != IntentType.COMMAND:
        raise AssertionError
    if not ("Watchdog" in text or "metrics" in text or "Status" in text):
        raise AssertionError
    # Command handling returns early (no final "Intent:" GUI feedback is guaranteed)
    assert isinstance(messages, list)


def test_enhanced_security_rejection_increments_counter(
    monkeypatch: pytest.MonkeyPatch,
):
    messages, feedback = _collector()
    pipeline = InputPipeline(gui_feedback_hook=feedback, enable_enhanced_security=True)

    # Monkeypatch sanitize_input to simulate strict mode rejection by raising ValueError
    def _raise_value_error(_user_input: str, **_kwargs):
        raise ValueError("Rejected by strict policy")

    # Ensure enhanced_sanitizer exists
    assert pipeline.enhanced_sanitizer is not None
    monkeypatch.setattr(
        pipeline.enhanced_sanitizer, "sanitize_input", _raise_value_error, raising=True
    )

    with pytest.raises(InputPipelineError):
        pipeline.run("dangerous payload")

    # Verify the rejection counter incremented and GUI got a security message
    counters = pipeline.get_security_counters()
    if counters.get("rejections", 0) < 1:
        raise AssertionError
    if not any("Security:" in m or "Security" in m for m in messages):
        raise AssertionError


def test_attacks_blocked_counter_and_feedback(monkeypatch: pytest.MonkeyPatch):
    messages, feedback = _collector()
    pipeline = InputPipeline(gui_feedback_hook=feedback, enable_enhanced_security=True)

    # Simulate sanitize_input returning a benign string
    def _sanitize_ok(_user_input: str, **_kwargs) -> str:
        return "sanitized"

    # Simulate security summary reporting blocked attacks
    def _summary_with_attacks() -> dict[str, Any]:
        return {"total_attacks": 3}

    assert pipeline.enhanced_sanitizer is not None
    monkeypatch.setattr(pipeline.enhanced_sanitizer, "sanitize_input", _sanitize_ok, raising=True)
    monkeypatch.setattr(
        pipeline.enhanced_sanitizer,
        "get_security_summary",
        _summary_with_attacks,
        raising=True,
    )

    out, intent = pipeline.run("anything")
    # Validate we received a recognized intent enum member
    assert isinstance(intent, IntentType)

    # Verify we reported attacks and incremented counter
    if not any("Blocked" in m or "Security" in m for m in messages):
        raise AssertionError
    counters = pipeline.get_security_counters()
    if counters.get("attacks_blocked", 0) < 3:
        raise AssertionError
