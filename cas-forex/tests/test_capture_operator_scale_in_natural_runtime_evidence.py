from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "capture_operator_scale_in_natural_runtime_evidence.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("capture_operator_scale_in_natural_runtime_evidence", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _operator(event: str, parent: str, sizing_ref: str, action_ref: str) -> dict:
    return {
        "generated_at": "2026-07-14T04:00:00+00:00",
        "event_hash": event,
        "status": "AI_OPERATOR_POSITION_DECIDED",
        "provider": "local-fallback",
        "provider_label": "Local model (deepseek-r1:latest)",
        "model_ref": "deepseek-r1:latest",
        "model_backend": "ollama",
        "prompt_version": "ai_operator_position_edge.v14",
        "model_prompt_hash": "prompt-hash",
        "system_prompt_hash": "system-hash",
        "decision_context_hash": "context-hash",
        "decisions": [
            {
                "position_key": f"ticket:{parent}",
                "decision": "SELECT",
                "intent": "scale_in",
                "action_ref": action_ref,
                "sizing_ref": sizing_ref,
                "reason": "Compound a protected net winner.",
            }
        ],
    }


def _scale(
    *,
    event: str,
    parent: str,
    child: int,
    attempt_id: str,
    sizing_ref: str,
    action_ref: str,
    direct: bool,
) -> dict:
    direct_fields = {
        "operator_provider": "local-fallback",
        "operator_model_ref": "deepseek-r1:latest",
        "operator_model_backend": "ollama",
        "operator_prompt_version": "ai_operator_position_edge.v14",
        "operator_action_ref": action_ref,
        "operator_reason": "Compound a protected net winner.",
    }
    nested = {
        "provider": "local-fallback",
        "model_ref": "deepseek-r1:latest",
        "model_backend": "ollama",
        "prompt_version": "ai_operator_position_edge.v14",
        "action_ref": action_ref,
        "reason": "Compound a protected net winner.",
    }
    trace = {
        "model_provider": "local-fallback",
        "model_ref": "deepseek-r1:latest",
        "operator_event_hash": event,
    }
    return {
        "generated_at": "2026-07-14T04:01:00+00:00",
        "status": "EXECUTED_RECONCILED",
        "terminal_receipt_status": "RECONCILED",
        "operator_event_hash": event,
        "parent_broker_ticket": parent,
        "sizing_ref": sizing_ref,
        "sizing_plan_hash": "sizing-plan",
        "authorization": {
            "status": "AUTHORIZED",
            "one_shot": True,
            "parent_ticket": parent,
        },
        "compound_slot_policy": {
            "base_max_positions_per_symbol": 1,
            "authorized_compound_slot_allowance": 1,
            "effective_max_positions_per_symbol": 2,
            "ordinary_entry_cap_unchanged": True,
        },
        "terminal_receipt": {
            "status": "RECONCILED",
            "before_volume": 0.01,
            "actual_after_volume": 0.02,
        },
        "operator_decision_provenance": direct_fields if direct else {},
        "dispatch_result": {
            "executed": True,
            "audit_attempt_id": attempt_id,
            "outcome": {"broker_ticket": child},
            "execution_provenance": {
                "operator_decision": nested if direct else {},
                "version_trace": trace if direct else {"model_provider": "not_attached"},
            },
        },
    }


def test_report_preserves_historical_gap_and_proves_direct_post_correction_receipt(tmp_path: Path):
    module = _load_module()
    old_event = "old-event"
    new_event = "new-event"
    old_ref = "old-size"
    new_ref = "new-size"
    old_action = "old-action"
    new_action = "new-action"
    operators = [
        _operator(old_event, "100", old_ref, old_action),
        _operator(new_event, "200", new_ref, new_action),
    ]
    scales = [
        _scale(
            event=old_event,
            parent="100",
            child=101,
            attempt_id="attempt-old",
            sizing_ref=old_ref,
            action_ref=old_action,
            direct=False,
        ),
        _scale(
            event=new_event,
            parent="200",
            child=201,
            attempt_id="attempt-new",
            sizing_ref=new_ref,
            action_ref=new_action,
            direct=True,
        ),
    ]
    _write_jsonl(tmp_path / "runtime" / "ai-operator-position-edge-audit.jsonl", operators)
    _write_jsonl(tmp_path / "runtime" / "ai-operator-scale-in-execution-audit.jsonl", scales)
    (tmp_path / "runtime" / "order-attempts.json").write_text(
        json.dumps(
            {
                "attempts": {
                    "attempt-old": {"result_status": "BROKER_EXECUTED", "volume": 0.01},
                    "attempt-new": {"result_status": "BROKER_EXECUTED", "volume": 0.01},
                }
            }
        ),
        encoding="utf-8",
    )
    source = tmp_path / "cas_forex" / "ai_operator_scale_in.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        '\n'.join(
            (
                '"operator_provider"',
                '"operator_model_ref"',
                '"operator_action_ref"',
                '"operator_reason"',
                "proposed.update(",
            )
        ),
        encoding="utf-8",
    )

    report = module.build_report(repo_root=tmp_path)

    assert report["status"] == "PASS_NATURAL_SCALE_IN_WITH_DIRECT_ATTRIBUTION"
    assert report["execution"]["parent_broker_ticket"] == "200"
    assert report["execution"]["child_broker_ticket"] == 201
    assert report["historical_generic_provenance_gap"]["present"] is True
    assert report["historical_generic_provenance_gap"]["parent_broker_ticket"] == "100"
    assert report["post_correction_natural_receipt"]["status"] == "present"
    assert (
        report["post_correction_natural_receipt"]["operator_decision_provenance"]["operator_model_ref"]
        == "deepseek-r1:latest"
    )
    assert report["source_correction"]["post_correction_natural_receipt_status"] == "present"
    assert report["broker_touched_by_capture"] is False
    assert report["orders_placed_by_capture"] is False
    assert len(report["event_hash"]) == 64
