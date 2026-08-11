from __future__ import annotations

import threading
import time

from cas_forex.bounded_model_call import bounded_provider_generate


class _FastProvider:
    def __init__(self) -> None:
        self.kwargs = None
        self.calls = 0

    def status(self):
        return {
            "active_provider": "claude",
            "active_provider_label": "Claude (test)",
            "active_is_paid": True,
        }

    def generate(self, prompt, system, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        return {"ok": True, "text": "done", "provider": "claude"}


class _BlockingLocalProvider:
    def __init__(self) -> None:
        self.release = threading.Event()
        self.calls = 0

    def status(self):
        return {
            "active_provider": "local-fallback",
            "active_provider_label": "Local (test)",
            "active_is_paid": False,
        }

    def generate(self, prompt, system, **kwargs):
        self.calls += 1
        self.release.wait(2.0)
        return {"ok": True, "text": "done", "provider": "local-fallback"}


def test_bounded_provider_generate_preserves_structured_generation_arguments():
    provider = _FastProvider()
    result = bounded_provider_generate(
        provider,
        "prompt",
        "system",
        channel="test-fast-provider",
        wall_timeout_seconds=1.0,
        generate_kwargs={
            "request_timeout": 0.75,
            "max_attempts": 1,
            "response_format": {"type": "object"},
        },
    )

    assert result["ok"] is True
    assert result["text"] == "done"
    assert result["wall_timeout_seconds"] == 1.0
    assert provider.kwargs == {
        "request_kind": "test-fast-provider",
        "request_timeout": 0.75,
        "max_attempts": 1,
        "response_format": {"type": "object"},
    }


def test_bounded_provider_generate_times_out_and_rejects_inference_pileup():
    provider = _BlockingLocalProvider()
    channel = "test-blocking-local-provider"

    started = time.monotonic()
    timed_out = bounded_provider_generate(
        provider,
        "prompt-1",
        "system",
        channel=channel,
        wall_timeout_seconds=0.05,
    )
    elapsed = time.monotonic() - started
    in_progress = bounded_provider_generate(
        provider,
        "prompt-2",
        "system",
        channel=channel,
        wall_timeout_seconds=0.05,
    )

    assert timed_out["ok"] is False
    assert timed_out["error_code"] == "MODEL_CALL_TIMEOUT"
    assert elapsed < 0.5
    assert in_progress["ok"] is False
    assert in_progress["error_code"] == "MODEL_CALL_IN_PROGRESS"
    assert in_progress["model_call_id"] == timed_out["model_call_id"]
    assert provider.calls == 1

    provider.release.set()
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        retried = bounded_provider_generate(
            provider,
            "prompt-3",
            "system",
            channel=channel,
            wall_timeout_seconds=0.2,
        )
        if retried.get("completed_after_wall_timeout"):
            break
        time.sleep(0.01)
    else:
        raise AssertionError("completed single-flight channel did not reopen")

    assert retried["ok"] is True
    assert retried["completed_after_wall_timeout"] is True
    assert retried["model_call_id"] == timed_out["model_call_id"]
    assert provider.calls == 1


def test_fast_completion_is_not_replayed_on_the_next_call():
    provider = _FastProvider()
    channel = "test-fast-not-replayed"

    first = bounded_provider_generate(
        provider,
        "prompt-1",
        "system",
        channel=channel,
        wall_timeout_seconds=1.0,
    )
    second = bounded_provider_generate(
        provider,
        "prompt-2",
        "system",
        channel=channel,
        wall_timeout_seconds=1.0,
    )

    assert first["ok"] is True
    assert second["ok"] is True
    assert "completed_after_wall_timeout" not in second
    assert provider.calls == 2


def test_late_result_is_not_delivered_to_a_different_decision_kind():
    provider = _BlockingLocalProvider()
    channel = "test-kind-isolation"
    timed_out = bounded_provider_generate(
        provider,
        "position-prompt",
        "system",
        channel=channel,
        request_kind="position_management",
        wall_timeout_seconds=0.05,
    )
    provider.release.set()
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        trade_result = bounded_provider_generate(
            provider,
            "trade-prompt",
            "system",
            channel=channel,
            request_kind="trade_entry",
            wall_timeout_seconds=0.5,
        )
        if trade_result.get("error_code") != "MODEL_CALL_IN_PROGRESS":
            break
        time.sleep(0.01)
    else:
        raise AssertionError("completed result from the other decision kind did not clear")

    assert timed_out["error_code"] == "MODEL_CALL_TIMEOUT"
    assert trade_result["ok"] is True
    assert "completed_after_wall_timeout" not in trade_result
    assert provider.calls == 2
