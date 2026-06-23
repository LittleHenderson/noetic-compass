"""Evidence-backed data loader for the CAS Forex proof cockpit API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from cas_forex.authority_boundary import build_authority_boundary_report
from cas_forex.runtime_gates import build_runtime_gates_report
from cas_forex.ai_model import model_status
from cas_forex.broker_profiles import broker_candidates


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = REPO_ROOT / "evidence_runs"
PROOF_DIR = EVIDENCE_ROOT / "index_tsmom_126_paper_proof"
PLAN_ID = "index-tsmom-126-d1-paper-proof"


def dashboard_state() -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "uiReadiness": ui_readiness(),
        "dailySchedule": daily_schedule(),
        "dailyBundle": daily_bundle(),
        "ownerControl": owner_control(),
        "strategyLeads": strategy_leads(),
        "backsolve": backsolve_summary(),
        "conditionTally": condition_tally(),
        "walkForward": walk_forward_summary(),
        "mt5Receipt": mt5_receipt(),
        "authorityBoundary": authority_boundary(),
        "runtimeGates": runtime_gates_report(),
        "aiModel": ai_model_status(),
        "brokerCandidates": broker_candidate_profiles(),
    }
    adaptive = adaptive_cockpit()
    if adaptive is not None:
        state["adaptive"] = adaptive
    history = mt_history()
    if history is not None:
        state["mtHistory"] = history
    return state


def ui_readiness() -> Dict[str, Any]:
    return _read_json(PROOF_DIR / f"{PLAN_ID}-ui-readiness-status.json")


def daily_schedule() -> Dict[str, Any]:
    return _read_json(PROOF_DIR / f"{PLAN_ID}-daily-schedule-status.json")


def daily_bundle(date: Optional[str] = None) -> Dict[str, Any]:
    bundle = _read_json(PROOF_DIR / f"{PLAN_ID}-daily-bundle-status.json")
    if date is not None and bundle.get("date") != date:
        raise HTTPException(status_code=404, detail=f"No daily bundle for {date}")
    return bundle


def latest_decision() -> Dict[str, Any]:
    return daily_bundle()["latest_decision"]


def latest_risk() -> Dict[str, Any]:
    return daily_bundle()["latest_risk"]


def strategy_leads() -> List[Dict[str, Any]]:
    payload = _read_json(REPO_ROOT / "strategy_leads.json")
    leads = payload.get("leads", [])
    if not isinstance(leads, list):
        raise HTTPException(status_code=500, detail="strategy_leads.json has invalid leads shape")
    return leads


def backsolve_summary() -> Dict[str, Any]:
    path = _latest_file(EVIDENCE_ROOT / "leverage_income_backsolve", "leverage-income-backsolve-*-report.json")
    report = _read_json(path)
    autonomy = report.get("ai_autonomy") or {}
    math = report.get("required_return_math") or {}
    return {
        "run_id": report.get("run_id"),
        "total_scenarios": report.get("scenario_count", 0),
        "viable_scenarios": report.get("viable_scenario_count", 0),
        "ai_autonomy_mode": autonomy.get("mode"),
        "ai_selection": autonomy.get("status"),
        "required_return_math": {
            "target_5k_on_5k_pct": math.get("$5k_target_on_$5k_seed_pct", 100.0),
            "target_12k_on_5k_pct": math.get("$12k_target_on_$5k_seed_pct", 240.0),
        },
        "verdict_counts": report.get("verdict_counts", {}),
        "capital_label": "SURVIVAL_RISK",
        "claim_boundary": report.get(
            "claim_boundary",
            "Paper-only leverage/income backsolve. Live trading remains NOT LICENSED.",
        ),
        "deployment_status": report.get("deployment_status", "NOT LICENSED"),
    }


def condition_tally() -> List[Dict[str, Any]]:
    path = _latest_file(EVIDENCE_ROOT / "condition_tally", "condition-tally-*-report.json")
    report = _read_json(path)
    tally = report.get("tally") or {}
    buckets = tally.get("buckets", [])
    if not isinstance(buckets, list):
        raise HTTPException(status_code=500, detail="condition tally report has invalid bucket shape")
    return buckets


def walk_forward_summary() -> Dict[str, Any]:
    path = _latest_file(EVIDENCE_ROOT / "walk_forward_condition_lab", "walk-forward-*-report.json")
    report = _read_json(path)
    summary = report.get("combined_summary") or {}
    arguments = report.get("arguments") or {}
    return {
        "run_id": report.get("run_id"),
        "total_windows": summary.get("windows", 0),
        "routed_windows": summary.get("routed_windows", 0),
        "active_routed_windows": summary.get("active_routed_windows", 0),
        "positive_active_routed_windows": summary.get("positive_active_routed_windows", 0),
        "routed_total_return_pct": summary.get("routed_total_return_pct_sum", 0.0),
        "active_routed_mean_return_pct": summary.get("active_routed_mean_return_pct", 0.0),
        "routed_max_drawdown_pct": summary.get("routed_max_drawdown_pct", 0.0),
        "total_routed_trades": summary.get("routed_total_trades", 0),
        "research_grade": summary.get("research_grade", "NOT_PROMOTED"),
        "symbols": arguments.get("symbols", []),
        "claim_boundary": report.get(
            "claim_boundary",
            summary.get("claim_boundary", "Research-only walk-forward result. Live trading remains NOT LICENSED."),
        ),
    }


def adaptive_cockpit() -> Optional[Dict[str, Any]]:
    path = PROOF_DIR / f"{PLAN_ID}-adaptive-cockpit.json"
    if not path.exists():
        return None
    return _read_json(path)


def latest_adaptive_compounding() -> Optional[Dict[str, Any]]:
    payload = adaptive_cockpit()
    if not payload:
        return None
    return (payload.get("adaptive_compounding") or {}).get("latest_review")


def authority_boundary() -> Dict[str, Any]:
    return build_authority_boundary_report(strategy_leads()).to_dict()


def runtime_gates_report() -> Dict[str, Any]:
    return build_runtime_gates_report().to_dict()


def ai_model_status() -> Dict[str, Any]:
    return model_status().to_dict()


def broker_candidate_profiles() -> List[Dict[str, Any]]:
    return broker_candidates()


def owner_control() -> Dict[str, Any]:
    return {
        "mode": "AI_FULL_AUTO_PAPER",
        "max_concurrent_trades": 15,
        "max_loss_cap_pct": 10,
        "ai_autonomy_enabled": True,
        "live_requested": False,
        "live_blocked": True,
        "personal_utilization_only": True,
        "account_scope": "PERSONAL_ONLY",
        "disallowed_scopes": [
            "client_money",
            "pooled_capital",
            "family_or_friend_capital",
            "managed_accounts",
            "public_service",
        ],
        "claim_boundary": (
            "Owner control policy is personal-utilization-only: CAS Forex is for the owner's own account, "
            "own credentials, own evidence, and own decisions. No client, pooled, family/friend, managed-account, "
            "or public-service use. CAS Forex can run research/paper automation now; live trading, broker ACCEPT, "
            "and payment movement require explicit owner enable flags, credentials/provider config, and gate clearance."
        ),
    }


def mt_history() -> Optional[Dict[str, Any]]:
    output_dir = EVIDENCE_ROOT / "mt_history_import"
    if not output_dir.exists():
        return None
    files = sorted(output_dir.glob("*.json"))
    if not files:
        return None
    report = _read_json(files[-1])
    summary = report.get("summary")
    return summary if isinstance(summary, dict) else report


def mt5_receipt() -> Dict[str, Any]:
    payload = _read_json(PROOF_DIR / f"{PLAN_ID}-mt5-demo-probe-20260622153728.json")
    probe = payload.get("probe") or {}
    receipt = probe.get("receipt") or {}
    report = payload.get("report") or {}
    daily_summaries = report.get("daily_summaries") or []
    latest_summary = daily_summaries[-1] if daily_summaries else {}
    return {
        "receipt_id": receipt.get("receipt_id") or latest_summary.get("receipt_id"),
        "receipt_validation_status": receipt.get("receipt_validation_status") or latest_summary.get("receipt_validation_status"),
        "broker_mode": receipt.get("broker_mode") or latest_summary.get("broker_mode"),
        "trading_date": receipt.get("trading_date") or latest_summary.get("date"),
        "symbols": receipt.get("symbols") or latest_summary.get("symbols") or [],
        "orders_attempted": receipt.get("orders_attempted", latest_summary.get("orders_attempted", 0)),
        "open_positions_reconciled": bool(
            receipt.get("open_positions_reconciled", latest_summary.get("open_positions_reconciled", False))
        ),
        "live_mode": bool(receipt.get("live_mode", latest_summary.get("live_mode", False))),
        "broker_api_authenticated": bool(
            receipt.get("broker_api_authenticated", latest_summary.get("broker_api_authenticated", False))
        ),
        "broker_source_verified": bool(
            receipt.get("broker_source_verified", latest_summary.get("broker_source_verified", False))
        ),
        "server": receipt.get("server") or latest_summary.get("server"),
        "terminal_name": receipt.get("terminal_name") or latest_summary.get("terminal_name"),
        "receipt_hash_sha256": receipt.get("receipt_hash_sha256") or latest_summary.get("broker_receipt_hash_sha256"),
        "broker_export_sha256": receipt.get("broker_export_sha256") or latest_summary.get("broker_export_sha256"),
        "packet_hash": "56faa6ac644c30fa6ff86588121aa2f4acc58b95401000e1a0b1227fca0a63cf",
        "record_hash": "a52334295d7251512a04137ff2bc83ade0228c0ec798f67a872d3e0742c1f092",
        "chain_verified": bool(report.get("chain_verified", False)),
        "worm_retained": False,
    }


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing evidence artifact: {path.relative_to(REPO_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_file(directory: Path, pattern: str) -> Path:
    if not directory.exists():
        raise HTTPException(status_code=404, detail=f"Missing evidence directory: {directory.relative_to(REPO_ROOT)}")
    files = sorted(directory.glob(pattern))
    if not files:
        raise HTTPException(status_code=404, detail=f"No evidence files match {pattern}")
    return files[-1]
