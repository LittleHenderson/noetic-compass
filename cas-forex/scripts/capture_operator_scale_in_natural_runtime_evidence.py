"""Bind one natural Operator scale-in to its decision and MT5 demo receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "runtime" / "operator-scale-in-natural-receipt-latest.json"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _json_lines(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _direct_operator_provenance(scale: dict[str, Any]) -> dict[str, Any]:
    dispatch = dict(scale.get("dispatch_result") or {})
    execution_provenance = dict(dispatch.get("execution_provenance") or {})
    direct = dict(scale.get("operator_decision_provenance") or {})
    nested = dict(execution_provenance.get("operator_decision") or {})
    version_trace = dict(execution_provenance.get("version_trace") or {})
    present = all(
        (
            direct.get("operator_provider"),
            direct.get("operator_model_ref"),
            direct.get("operator_model_backend"),
            direct.get("operator_prompt_version"),
            direct.get("operator_action_ref"),
            direct.get("operator_reason"),
            nested.get("provider"),
            nested.get("model_ref"),
            nested.get("model_backend"),
            nested.get("prompt_version"),
            nested.get("action_ref"),
            nested.get("reason"),
            version_trace.get("model_provider"),
            version_trace.get("model_ref"),
            version_trace.get("operator_event_hash"),
        )
    )
    return {
        "present": present,
        "direct": direct,
        "execution_provenance": nested,
        "version_trace": version_trace,
    }


def build_report(*, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    scale_path = repo_root / "runtime" / "ai-operator-scale-in-execution-audit.jsonl"
    operator_path = repo_root / "runtime" / "ai-operator-position-edge-audit.jsonl"
    attempts_path = repo_root / "runtime" / "order-attempts.json"
    source_path = repo_root / "cas_forex" / "ai_operator_scale_in.py"
    operator_audits = _json_lines(operator_path)
    operator_by_hash = {
        str(row.get("event_hash") or ""): row
        for row in operator_audits
        if row.get("event_hash")
    }
    matched = [
        (row, operator_by_hash.get(str(row.get("operator_event_hash") or "")))
        for row in _json_lines(scale_path)
        if row.get("status") == "EXECUTED_RECONCILED"
        and row.get("terminal_receipt_status") == "RECONCILED"
        and operator_by_hash.get(str(row.get("operator_event_hash") or ""))
    ]
    if not matched:
        raise RuntimeError("No natural reconciled Operator scale-in receipt is available.")
    direct_matches = [item for item in matched if _direct_operator_provenance(item[0])["present"]]
    historical_gap_matches = [item for item in matched if not _direct_operator_provenance(item[0])["present"]]
    scale, operator = direct_matches[-1] if direct_matches else matched[-1]
    historical_scale, historical_operator = historical_gap_matches[0] if historical_gap_matches else ({}, {})
    operator_event_hash = str(scale.get("operator_event_hash") or "")
    parent_ticket = str(scale.get("parent_broker_ticket") or "")
    sizing_ref = str(scale.get("sizing_ref") or "")
    decision = next(
        (
            dict(row)
            for row in operator.get("decisions") or []
            if str(row.get("position_key") or "") == f"ticket:{parent_ticket}"
            and str(row.get("sizing_ref") or "") == sizing_ref
            and str(row.get("decision") or "").upper() == "SELECT"
        ),
        {},
    )
    attempt_id = str((scale.get("dispatch_result") or {}).get("audit_attempt_id") or "")
    attempt = dict((_json(attempts_path).get("attempts") or {}).get(attempt_id) or {})
    dispatch = dict(scale.get("dispatch_result") or {})
    provenance = dict(dispatch.get("execution_provenance") or {})
    selected_operator_snapshot = dict(provenance.get("operator_decision") or {})
    selected_version_trace = dict(provenance.get("version_trace") or {})
    direct_provenance = _direct_operator_provenance(scale)
    historical_dispatch = dict(historical_scale.get("dispatch_result") or {})
    historical_provenance = dict(historical_dispatch.get("execution_provenance") or {})
    historical_operator_snapshot = dict(historical_provenance.get("operator_decision") or {})
    historical_version_trace = dict(historical_provenance.get("version_trace") or {})
    source = source_path.read_text(encoding="utf-8")
    correction_present = all(
        marker in source
        for marker in (
            '"operator_provider"',
            '"operator_model_ref"',
            '"operator_action_ref"',
            '"operator_reason"',
            "proposed.update(",
        )
    )
    slot = dict(scale.get("compound_slot_policy") or {})
    authorization = dict(scale.get("authorization") or {})
    terminal = dict(scale.get("terminal_receipt") or {})
    natural_scale_in_complete = all(
        (
            operator_event_hash,
            decision.get("action_ref"),
            decision.get("reason"),
            operator.get("provider"),
            operator.get("model_ref"),
            authorization.get("one_shot") is True,
            authorization.get("status") == "AUTHORIZED",
            slot.get("ordinary_entry_cap_unchanged") is True,
            slot.get("effective_max_positions_per_symbol")
            == slot.get("base_max_positions_per_symbol")
            + slot.get("authorized_compound_slot_allowance"),
            dispatch.get("executed") is True,
            terminal.get("status") == "RECONCILED",
            attempt.get("result_status") == "BROKER_EXECUTED",
        )
    )
    direct_receipt_present = bool(direct_provenance.get("present"))
    report: dict[str, Any] = {
        "report_kind": "cas_forex_operator_scale_in_natural_receipt",
        "status": (
            "PASS_NATURAL_SCALE_IN_WITH_DIRECT_ATTRIBUTION"
            if natural_scale_in_complete and correction_present and direct_receipt_present
            else "PASS_NATURAL_SCALE_IN_WITH_ATTRIBUTION_CORRECTION"
            if natural_scale_in_complete and correction_present
            else "FAIL_INCOMPLETE_NATURAL_SCALE_IN_RECEIPT"
        ),
        "captured_from_existing_receipts": True,
        "natural_operator_decision": {
            "generated_at": operator.get("generated_at"),
            "event_hash": operator_event_hash,
            "status": operator.get("status"),
            "provider": operator.get("provider"),
            "provider_label": operator.get("provider_label"),
            "model_ref": operator.get("model_ref"),
            "model_backend": operator.get("model_backend"),
            "prompt_version": operator.get("prompt_version"),
            "model_prompt_hash": operator.get("model_prompt_hash"),
            "system_prompt_hash": operator.get("system_prompt_hash"),
            "decision_context_hash": operator.get("decision_context_hash"),
            "decision": decision,
        },
        "one_shot_authorization": authorization,
        "compound_slot_policy": slot,
        "execution": {
            "generated_at": scale.get("generated_at"),
            "status": scale.get("status"),
            "audit_id": scale.get("audit_id"),
            "action_id": scale.get("action_id"),
            "parent_broker_ticket": parent_ticket,
            "child_broker_ticket": (dispatch.get("outcome") or {}).get("broker_ticket"),
            "sizing_ref": sizing_ref,
            "sizing_plan_hash": scale.get("sizing_plan_hash"),
            "selected_lots": attempt.get("volume"),
            "attempt_id": attempt_id,
            "attempt_status": attempt.get("result_status"),
            "terminal_receipt": terminal,
        },
        "historical_generic_provenance_gap": {
            "present": bool(historical_scale),
            "generated_at": historical_scale.get("generated_at"),
            "parent_broker_ticket": historical_scale.get("parent_broker_ticket"),
            "operator_event_hash": historical_scale.get("operator_event_hash"),
            "source_operator_provider": historical_operator.get("provider"),
            "source_operator_model_ref": historical_operator.get("model_ref"),
            "operator_snapshot": historical_operator_snapshot,
            "version_trace_model_provider": historical_version_trace.get("model_provider"),
            "version_trace_model_ref": historical_version_trace.get("model_ref"),
            "interpretation": (
                "The immutable historical generic dispatch receipt retained the Operator event hash but omitted "
                "the actual model fields. Its immutable source Operator event retains the actual decision identity."
            ),
        },
        "post_correction_natural_receipt": {
            "present": direct_receipt_present,
            "status": "present" if direct_receipt_present else "OPEN",
            "generated_at": scale.get("generated_at") if direct_receipt_present else None,
            "parent_broker_ticket": parent_ticket if direct_receipt_present else None,
            "child_broker_ticket": (dispatch.get("outcome") or {}).get("broker_ticket") if direct_receipt_present else None,
            "operator_event_hash": operator_event_hash if direct_receipt_present else None,
            "operator_decision_provenance": direct_provenance.get("direct") if direct_receipt_present else {},
            "execution_provenance_operator_decision": (
                direct_provenance.get("execution_provenance") if direct_receipt_present else {}
            ),
            "execution_provenance_version_trace": (
                direct_provenance.get("version_trace") if direct_receipt_present else {}
            ),
        },
        "source_correction": {
            "present": correction_present,
            "path": str(source_path.relative_to(repo_root)),
            "sha256": _sha(source_path),
            "future_receipt_requirement": (
                "Natural post-correction scale-ins must carry the actual provider/model/action/rationale directly "
                "inside execution provenance; the historical generic receipt remains immutable."
            ),
            "post_correction_natural_receipt_status": "present" if direct_receipt_present else "OPEN",
            "selected_execution_operator_snapshot": selected_operator_snapshot,
            "selected_execution_version_trace": selected_version_trace,
        },
        "source_artifacts": {
            str(scale_path.relative_to(repo_root)): _sha(scale_path),
            str(operator_path.relative_to(repo_root)): _sha(operator_path),
            str(attempts_path.relative_to(repo_root)): _sha(attempts_path),
        },
        "broker_touched_by_capture": False,
        "orders_placed_by_capture": False,
        "money_moved_by_capture": False,
        "claim_boundary": (
            "This artifact binds one already-completed natural MT5 demo scale-in to its exact local-model decision, "
            "one-shot authorization, compound-slot policy, broker attempt, and reconciled terminal volume. The "
            "capture performs no broker action. A direct-attribution receipt proves the corrected provenance path "
            "when present. Neither that receipt nor the historical receipt proves durable edge, future profitability, "
            "or live-money readiness."
        ),
    }
    report["event_hash"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if str(report.get("status") or "").startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
