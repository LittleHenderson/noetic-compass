"""Probe pre-Operator candidate starvation without changing controls or trading."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterator, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cas_forex.ai_control_authority import get_authority
from cas_forex.config import config
import cas_forex.directional_intelligence as directional_intelligence
from cas_forex.live_candle_route_policy import _scan_candidate_block_reason
from cas_forex.time_utils import utc_now
from cas_forex.waste_market_data import build_waste_market_state_scan


DEFAULT_OUTPUT_PATH = (
    REPO_ROOT / "runtime" / "redteam-entry-opportunity-starvation-latest.json"
)
DEFAULT_EMISSION_PATH = REPO_ROOT / "runtime" / "live-candle-route-emissions.json"
DEFAULT_TIMEFRAMES = ("M1", "M5", "M15", "H1")
DEFAULT_PROBE_FLOORS = (0.30, 0.20, 0.18)


class _ReadOnlyControlView:
    def __init__(self, base: Any, directional_floor: float):
        self._base = base
        self._directional_floor = float(directional_floor)

    def get(self, key: str) -> Any:
        if str(key) == "min_directional_confidence":
            return self._directional_floor
        return self._base.get(key)


class _ReadOnlyAuthorityView:
    def __init__(self, base: Any, directional_floor: float):
        self._base = base
        self.control = _ReadOnlyControlView(base.control, directional_floor)
        self.owner_envelope = base.owner_envelope

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)


@contextmanager
def _temporary_read_only_floor(authority: Any, floor: float) -> Iterator[None]:
    original = directional_intelligence.get_authority
    directional_intelligence.get_authority = lambda: _ReadOnlyAuthorityView(
        authority, floor
    )
    try:
        yield
    finally:
        directional_intelligence.get_authority = original


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def _file_hash(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _normalized_floors(
    *, current: float, owner_min: float, owner_max: float, requested: Sequence[float]
) -> list[float]:
    values = [current, *requested]
    return sorted(
        {
            round(max(owner_min, min(owner_max, float(value))), 6)
            for value in values
        },
        reverse=True,
    )


def _scan_lane(
    *,
    authority: Any,
    floor: float,
    timeframe: str,
    symbols: Sequence[str],
    threshold: float,
) -> dict[str, Any]:
    with _temporary_read_only_floor(authority, floor):
        state = build_waste_market_state_scan(
            authority=authority,
            timeframe=timeframe,
            bars=300,
            max_pairs=200,
            max_scan_candidates=max(12, len(symbols)),
            allowed_symbols=list(symbols),
            threshold=threshold,
            candidate_block_reason=lambda candidate_state, candidate_edge: (
                _scan_candidate_block_reason(
                    candidate_state,
                    candidate_edge,
                    emission_state_path=DEFAULT_EMISSION_PATH,
                    config=config,
                )
            ),
        )
    scan = state.get("waste_market_scan")
    scan = dict(scan) if isinstance(scan, Mapping) else {}
    attempts = [
        dict(row) for row in (scan.get("attempts") or []) if isinstance(row, Mapping)
    ]
    directional_candidates = [
        row
        for row in attempts
        if str(row.get("candidate_direction") or "") in {"LONG", "SHORT"}
    ]
    pass_previews = [
        row
        for row in directional_candidates
        if str(row.get("edge_status") or "") == "PASS"
        and bool(row.get("edge_has_token", False))
    ]
    entry_stage_summary = scan.get("entry_stage_summary")
    entry_stage_summary = (
        dict(entry_stage_summary)
        if isinstance(entry_stage_summary, Mapping)
        else {}
    )
    best_shadow_pass_lane = entry_stage_summary.get("best_shadow_pass_lane")
    best_shadow_pass_lane = (
        dict(best_shadow_pass_lane)
        if isinstance(best_shadow_pass_lane, Mapping)
        else None
    )
    return {
        "timeframe": timeframe,
        "directional_floor": floor,
        "scan_status": scan.get("status"),
        "attempt_count": len(attempts),
        "entry_stage_summary": entry_stage_summary,
        "directional_candidate_count": len(directional_candidates),
        "pass_preview_count": len(pass_previews),
        "shadow_pass_preview_count": int(
            entry_stage_summary.get("shadow_pass_preview_count") or 0
        ),
        "best_shadow_pass_lane": best_shadow_pass_lane,
        "directional_candidates": [
            {
                "symbol": row.get("symbol"),
                "direction": row.get("candidate_direction"),
                "directional_score": row.get("directional_score"),
                "edge_status": row.get("edge_status"),
                "measured_win_prob": row.get("measured_win_prob"),
                "candidate_actionable": row.get("candidate_actionable"),
                "candidate_block_reason": row.get("candidate_block_reason"),
                "shadow_edge_status": row.get("shadow_edge_status"),
                "shadow_measured_win_prob": row.get("shadow_measured_win_prob"),
                "shadow_edge_preview_unregistered": row.get(
                    "shadow_edge_preview_unregistered"
                ),
                "shadow_edge_authorization_minted": row.get(
                    "shadow_edge_authorization_minted"
                ),
                "shadow_has_edge_token": row.get("shadow_has_edge_token"),
            }
            for row in directional_candidates
        ],
        "broker_execution_touched": bool(scan.get("broker_execution_touched", False)),
        "order_send_called": False,
        "money_moved": bool(scan.get("money_moved", False)),
    }


def build_report(
    *,
    timeframes: Sequence[str] = DEFAULT_TIMEFRAMES,
    probe_floors: Sequence[float] = DEFAULT_PROBE_FLOORS,
) -> dict[str, Any]:
    authority = get_authority()
    snapshot_before = authority.snapshot()
    control_before = (snapshot_before.get("control_surface") or {}).get("values") or {}
    bounds = (snapshot_before.get("control_surface") or {}).get("bounds") or {}
    floor_bounds = bounds.get("min_directional_confidence") or {}
    current_floor = float(
        control_before["min_directional_confidence"]
        if "min_directional_confidence" in control_before
        else 0.18
    )
    owner_min = float(floor_bounds["min"] if "min" in floor_bounds else 0.05)
    owner_max = float(floor_bounds["max"] if "max" in floor_bounds else 0.90)
    floors = _normalized_floors(
        current=current_floor,
        owner_min=owner_min,
        owner_max=owner_max,
        requested=probe_floors,
    )
    symbols = list(control_before.get("symbols") or [])
    threshold = float(control_before.get("edge_threshold") or 0.65)
    state_path = Path(authority.state_path)
    control_hash_before = _stable_hash(control_before)
    state_file_hash_before = _file_hash(state_path)

    lanes = [
        _scan_lane(
            authority=authority,
            floor=floor,
            timeframe=str(timeframe).upper(),
            symbols=symbols,
            threshold=threshold,
        )
        for floor in floors
        for timeframe in timeframes
    ]

    snapshot_after = authority.snapshot()
    control_after = (snapshot_after.get("control_surface") or {}).get("values") or {}
    control_hash_after = _stable_hash(control_after)
    state_file_hash_after = _file_hash(state_path)
    controls_unchanged = control_hash_before == control_hash_after
    authority_file_unchanged = state_file_hash_before == state_file_hash_after
    current_lanes = [
        lane for lane in lanes if float(lane["directional_floor"]) == current_floor
    ]
    current_attempts = sum(int(lane["attempt_count"]) for lane in current_lanes)
    current_candidates = sum(
        int(lane["directional_candidate_count"]) for lane in current_lanes
    )
    current_shadow_passes = sum(
        int(lane.get("shadow_pass_preview_count") or 0) for lane in current_lanes
    )
    current_shadow_lanes = [
        dict(lane["best_shadow_pass_lane"])
        for lane in current_lanes
        if isinstance(lane.get("best_shadow_pass_lane"), Mapping)
    ]
    current_best_shadow_pass = max(
        current_shadow_lanes,
        key=lambda lane: (
            float(lane.get("directional_score") or float("-inf")),
            float(lane.get("measured_win_prob") or float("-inf")),
        ),
        default=None,
    )
    broker_touched = any(bool(lane["broker_execution_touched"]) for lane in lanes)
    money_moved = any(bool(lane["money_moved"]) for lane in lanes)
    status = (
        "NO_TOUCH_ENTRY_STARVATION_PROBE_COMPLETE"
        if controls_unchanged
        and authority_file_unchanged
        and not broker_touched
        and not money_moved
        else "NO_TOUCH_INVARIANT_FAILED"
    )
    report: dict[str, Any] = {
        "report_kind": "cas_forex_entry_opportunity_starvation_redteam",
        "generated_at": utc_now().isoformat(),
        "status": status,
        "current_directional_floor": current_floor,
        "owner_directional_floor_bounds": {"min": owner_min, "max": owner_max},
        "probe_floors": floors,
        "timeframes": [str(value).upper() for value in timeframes],
        "symbols": symbols,
        "edge_threshold": threshold,
        "current_floor_summary": {
            "attempt_count": current_attempts,
            "directional_candidate_count": current_candidates,
            "shadow_pass_preview_count": current_shadow_passes,
            "best_shadow_pass_lane": current_best_shadow_pass,
            "all_observed_lanes_below_directional_floor": bool(
                current_attempts > 0 and current_candidates == 0
            ),
        },
        "lanes": lanes,
        "controls_unchanged": controls_unchanged,
        "authority_state_file_unchanged": authority_file_unchanged,
        "control_hash_before": control_hash_before,
        "control_hash_after": control_hash_after,
        "authority_file_hash_before": state_file_hash_before,
        "authority_file_hash_after": state_file_hash_after,
        "broker_execution_touched": broker_touched,
        "order_send_called": False,
        "money_moved": money_moved,
        "claim_boundary": (
            "This probe reads broker candles and evaluates candidate formation at "
            "temporary in-memory directional floors. It does not persist a dial, "
            "register an edge authorization, approve or dispatch an order, call "
            "order_send, move money, or prove that a lower floor is profitable."
        ),
    }
    report["event_hash"] = _stable_hash(report)
    return report


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframes", default=",".join(DEFAULT_TIMEFRAMES))
    parser.add_argument(
        "--floors",
        default=",".join(str(value) for value in DEFAULT_PROBE_FLOORS),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()
    report = build_report(
        timeframes=_parse_csv(args.timeframes),
        probe_floors=[float(value) for value in _parse_csv(args.floors)],
    )
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(f"{target.suffix}.tmp")
    temp.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    temp.replace(target)
    print(
        json.dumps(
            {
                "status": report["status"],
                "current_floor_summary": report["current_floor_summary"],
                "controls_unchanged": report["controls_unchanged"],
                "authority_state_file_unchanged": report[
                    "authority_state_file_unchanged"
                ],
                "broker_execution_touched": report["broker_execution_touched"],
                "order_send_called": report["order_send_called"],
                "money_moved": report["money_moved"],
                "output": str(target),
            },
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "NO_TOUCH_ENTRY_STARVATION_PROBE_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
