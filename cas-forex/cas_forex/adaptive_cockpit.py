"""Read-only adaptive compounding cockpit artifacts for CAS Forex."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from cas_forex.adaptive_compounding import summarize_adaptive_compounding_reviews
from cas_forex.paper_decision import summarize_paper_route_decisions
from cas_forex.paper_proof import PaperProofPlan, summarize_paper_proof
from cas_forex.paper_risk import summarize_paper_risk_reviews
from cas_forex.paper_ui_readiness import evaluate_paper_ui_readiness


ADAPTIVE_COCKPIT_CLAIM_BOUNDARY = (
    "The adaptive cockpit is read-only paper/research UI. Live trading, broker "
    "ACCEPT, auto-deposit, debit/card/bank movement, and payout automation remain NOT LICENSED."
)


def build_adaptive_cockpit_payload(
    plan: PaperProofPlan,
    output_dir: str | Path,
    *,
    imported_history_summary: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    out_dir = Path(output_dir)
    proof = summarize_paper_proof(plan, out_dir)
    decision = summarize_paper_route_decisions(plan, out_dir)
    risk = summarize_paper_risk_reviews(plan, out_dir)
    adaptive = summarize_adaptive_compounding_reviews(plan, out_dir)
    readiness = evaluate_paper_ui_readiness(plan, out_dir)
    latest_adaptive = adaptive.get("latest_review") or {}
    latest_decisions = latest_adaptive.get("decisions", []) if isinstance(latest_adaptive, Mapping) else []
    return {
        "plan_id": plan.plan_id,
        "lead_id": plan.lead_id,
        "strategy_setting": plan.strategy_setting,
        "timeframe": plan.timeframe,
        "cockpit_status": "READ_ONLY_PAPER_RESEARCH",
        "adaptive_action_counts": adaptive.get("action_counts", {}),
        "latest_adaptive_decisions": latest_decisions,
        "paper_proof": proof.model_dump(mode="json"),
        "paper_decision": decision,
        "paper_risk": risk,
        "adaptive_compounding": adaptive,
        "ui_readiness": readiness.__dict__,
        "imported_history": imported_history_summary,
        "claim_boundary": ADAPTIVE_COCKPIT_CLAIM_BOUNDARY,
        "deployment_status": "NOT LICENSED",
        "broker_accept_status": "NOT LICENSED",
        "payment_transfer_status": "NOT LICENSED",
    }


def write_adaptive_cockpit_payload(payload: Mapping[str, Any], output_dir: str | Path) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{payload.get('plan_id', 'cas-forex')}-adaptive-cockpit.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def write_adaptive_cockpit_html(payload: Mapping[str, Any], output_dir: str | Path) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{payload.get('plan_id', 'cas-forex')}-adaptive-cockpit.html"
    path.write_text(_render_html(payload), encoding="utf-8")
    return path


def _render_html(payload: Mapping[str, Any]) -> str:
    decisions = payload.get("latest_adaptive_decisions", [])
    rows = []
    if isinstance(decisions, list):
        for decision in decisions:
            if not isinstance(decision, Mapping):
                continue
            rows.append(
                "<tr>"
                f"<td>{_esc(decision.get('symbol'))}</td>"
                f"<td>{_esc(decision.get('action'))}</td>"
                f"<td>{_esc(decision.get('direction'))}</td>"
                f"<td>{_esc(decision.get('lot_size'))}</td>"
                f"<td>{_esc(decision.get('stop_loss'))}</td>"
                f"<td>{_esc(decision.get('take_profit'))}</td>"
                f"<td>{_esc(decision.get('evidence_score'))}</td>"
                f"<td>{_esc(decision.get('reason'))}</td>"
                "</tr>"
            )
    if not rows:
        rows.append("<tr><td colspan=\"8\">No adaptive review has been recorded yet.</td></tr>")
    actions = payload.get("adaptive_action_counts", {})
    action_chips = ""
    if isinstance(actions, Mapping):
        action_chips = "".join(
            f"<span class=\"chip\">{_esc(key)}: {_esc(value)}</span>"
            for key, value in sorted(actions.items())
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CAS Forex Adaptive Cockpit</title>
  <style>
    :root {{
      color-scheme: dark;
      font-family: Arial, sans-serif;
      background: #101318;
      color: #eef2f5;
    }}
    body {{ margin: 0; background: #101318; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    header {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }}
    h1 {{ margin: 0 0 6px; font-size: 30px; letter-spacing: 0; }}
    h2 {{ margin: 28px 0 12px; font-size: 18px; letter-spacing: 0; }}
    .status {{ color: #8bd4ff; font-weight: 700; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }}
    .card {{ border: 1px solid #2c3542; border-radius: 8px; padding: 14px; background: #171c23; }}
    .label {{ color: #9aa7b5; font-size: 12px; }}
    .value {{ margin-top: 6px; font-size: 20px; font-weight: 700; }}
    .license {{ border: 1px solid #734040; background: #211719; color: #ffb4b4; border-radius: 8px; padding: 12px; margin-top: 18px; }}
    table {{ width: 100%; border-collapse: collapse; background: #151a20; border: 1px solid #2c3542; }}
    th, td {{ text-align: left; border-bottom: 1px solid #2c3542; padding: 10px; font-size: 13px; vertical-align: top; }}
    th {{ color: #9aa7b5; font-weight: 700; }}
    .chip {{ display: inline-block; border: 1px solid #3f4c5c; border-radius: 999px; padding: 6px 10px; margin: 0 8px 8px 0; color: #cdd8e3; }}
    @media (max-width: 900px) {{
      header {{ display: block; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      table {{ display: block; overflow-x: auto; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>CAS Forex Adaptive Cockpit</h1>
      <div class="status">{_esc(payload.get('cockpit_status'))}</div>
    </div>
    <div class="status">{_esc(payload.get('strategy_setting'))} / {_esc(payload.get('timeframe'))}</div>
  </header>
  <div class="license">{_esc(payload.get('claim_boundary'))}</div>
  <section class="grid">
    <div class="card"><div class="label">Plan</div><div class="value">{_esc(payload.get('plan_id'))}</div></div>
    <div class="card"><div class="label">Lead</div><div class="value">{_esc(payload.get('lead_id'))}</div></div>
    <div class="card"><div class="label">Deployment</div><div class="value">{_esc(payload.get('deployment_status'))}</div></div>
    <div class="card"><div class="label">Broker ACCEPT</div><div class="value">{_esc(payload.get('broker_accept_status'))}</div></div>
  </section>
  <h2>Adaptive Actions</h2>
  <div>{action_chips or '<span class="chip">No actions recorded</span>'}</div>
  <h2>Latest Decisions</h2>
  <table>
    <thead>
      <tr><th>Symbol</th><th>Action</th><th>Direction</th><th>Lots</th><th>Stop</th><th>Target</th><th>Evidence</th><th>Reason</th></tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</main>
</body>
</html>
"""


def _esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)

