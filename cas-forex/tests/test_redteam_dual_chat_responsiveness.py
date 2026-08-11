from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "redteam_dual_chat_responsiveness.py"
)
SPEC = importlib.util.spec_from_file_location(
    "redteam_dual_chat_responsiveness",
    SCRIPT_PATH,
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_dual_chat_report_requires_grounded_and_model_paths(monkeypatch) -> None:
    def fake_post(url, payload, *, timeout):  # noqa: ARG001
        message = str(payload.get("message") or "")
        if "/assistant/" in url and message.startswith("Compare mean reversion"):
            body = {
                "source": "local",
                "reply": (
                    "The snapshot does not contain a validated current regime "
                    "classification, so I cannot truthfully claim one."
                ),
            }
        elif "/assistant/" in url and message.startswith("Explain why regime shifts"):
            body = {
                "source": "ai-provider",
                "model": "deepseek-v4-flash:cloud",
                "reply": "Regime shifts change the assumptions a fixed strategy relies on.",
            }
        elif "/assistant/" in url:
            body = {
                "source": "local",
                "reply": "Current runtime: dispatch running=True, lane=PAPER.",
            }
        elif message.startswith("WHY DONT YOU SCALP"):
            body = {
                "chat_path_status": "LOCAL_TRADE_PATH_TRUTH",
                "reply": "Current PAPER scan has no executable candidate.",
            }
        else:
            body = {
                "chat_path_status": "LOCAL_COMPOUND_AUTHORITY_TRUTH",
                "reply": "The Operator may compound only a qualifying protected winner.",
            }
        return {"http_status": 200, "elapsed_ms": 12, "body": body}

    monkeypatch.setattr(MODULE, "_post_json", fake_post)

    report = MODULE.build_report("http://127.0.0.1:8765/api/forex")

    assert report["status"] == "PASS_GROUNDED_DUAL_CHAT"
    assert all(report["invariant_checks"].values())
    assert report["broker_touched"] is False
    assert report["money_moved"] is False
    assert report["settings_changed"] is False
    assert len(report["event_hash"]) == 64
