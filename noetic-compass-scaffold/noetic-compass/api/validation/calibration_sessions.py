"""Calibration-session queueing and durable reconciliation logs."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from .correlation import OPERATOR_NAMES


def _validation_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "validation"


def _sessions_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path)
    return _validation_dir() / "calibration_sessions.json"


def _clip_text(text: str, limit: int = 180) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else f"{compact[:limit - 3]}..."


def load_calibration_sessions(path: Path | str | None = None) -> list[dict]:
    """Load saved calibration-session entries."""
    target = _sessions_path(path)
    if not target.exists():
        return []
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_calibration_sessions(entries: list[dict], path: Path | str | None = None) -> None:
    """Persist calibration-session entries."""
    target = _sessions_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def append_calibration_session(entry: dict, path: Path | str | None = None) -> list[dict]:
    """Append a calibration-session entry and return the full store."""
    entries = load_calibration_sessions(path)
    timestamped = {
        **entry,
        "timestamp": entry.get("timestamp") or datetime.now(timezone.utc).isoformat(),
    }
    entries.append(timestamped)
    save_calibration_sessions(entries, path)
    return entries


def build_calibration_session_payload(
    labels: list[dict],
    machine_results: list[dict],
    sessions: list[dict] | None = None,
    limit: int = 12,
) -> dict:
    """Build a calibration queue plus recent reconciliation history."""
    sessions = sessions or []
    session_counts: dict[int, int] = defaultdict(int)
    latest_session_by_item: dict[int, dict] = {}
    for session in sessions:
        idx = session.get("item_index")
        if idx is None:
            continue
        item_index = int(idx)
        session_counts[item_index] += 1
        previous = latest_session_by_item.get(item_index)
        if previous is None or str(session.get("timestamp", "")) > str(previous.get("timestamp", "")):
            latest_session_by_item[item_index] = session

    machine_by_idx: dict[int, dict] = {}
    for item in machine_results:
        idx = item.get("index")
        if idx is None:
            continue
        machine_by_idx[int(idx)] = item

    labels_by_item: dict[int, list[dict]] = defaultdict(list)
    for label in labels:
        idx = label.get("item_index")
        if idx is None:
            continue
        labels_by_item[int(idx)].append(label)

    queue: list[dict] = []
    for item_index, item_labels in labels_by_item.items():
        unique_raters = sorted({str(label.get("rater", "unknown")) for label in item_labels})
        if len(unique_raters) < 2:
            continue

        machine_item = machine_by_idx.get(item_index, {})
        machine_operator_scores = [
            round(float(score) * 10.0, 2) for score in machine_item.get("operator_scores", [])[:10]
        ]
        machine_domain_scores = [
            round(float(score) * 40.0, 2) for score in machine_item.get("domain_averages", [])[:4]
        ]
        panel_operator_scores = [
            round(
                mean(float(label.get("operator_scores", [0] * 10)[op_idx]) for label in item_labels),
                2,
            )
            for op_idx in range(10)
        ]
        panel_domain_scores = [
            round(
                mean(float(label.get("domain_scores", [0] * 4)[dom_idx]) for label in item_labels),
                2,
            )
            for dom_idx in range(4)
        ]

        operator_spreads: list[dict] = []
        for op_idx in range(10):
            scores = [
                float(label.get("operator_scores", [0] * 10)[op_idx])
                for label in item_labels
                if len(label.get("operator_scores", [])) > op_idx
            ]
            if len(scores) < 2:
                continue
            operator_spreads.append(
                {
                    "operator_index": op_idx,
                    "operator_name": OPERATOR_NAMES[op_idx],
                    "spread": round(max(scores) - min(scores), 2),
                    "panel_mean": round(mean(scores), 2),
                }
            )
        operator_spreads.sort(key=lambda item: (-item["spread"], item["operator_index"]))

        machine_panel_gap_values = [
            abs(panel_operator_scores[idx] - machine_operator_scores[idx])
            for idx in range(min(len(panel_operator_scores), len(machine_operator_scores)))
        ]
        queue.append(
            {
                "item_index": item_index,
                "prompt": str(machine_item.get("prompt", item_labels[0].get("prompt", ""))),
                "prompt_excerpt": _clip_text(str(machine_item.get("prompt", item_labels[0].get("prompt", "")))),
                "response": str((machine_item.get("llm_response") or {}).get("text", "")),
                "model": str((machine_item.get("llm_response") or {}).get("model", "")),
                "raters": unique_raters,
                "labels": [
                    {
                        "rater": str(label.get("rater", "unknown")),
                        "timestamp": str(label.get("timestamp", "")),
                        "notes": str(label.get("notes", "")),
                        "operator_scores": [int(score) for score in label.get("operator_scores", [])[:10]],
                        "domain_scores": [int(score) for score in label.get("domain_scores", [])[:4]],
                    }
                    for label in item_labels
                ],
                "panel_operator_scores": panel_operator_scores,
                "panel_domain_scores": panel_domain_scores,
                "machine_operator_scores": machine_operator_scores,
                "machine_domain_scores": machine_domain_scores,
                "largest_operator_gap": operator_spreads[0] if operator_spreads else None,
                "mean_spread": round(mean(item["spread"] for item in operator_spreads), 2) if operator_spreads else 0.0,
                "machine_panel_gap": round(mean(machine_panel_gap_values), 2) if machine_panel_gap_values else 0.0,
                "session_count": session_counts.get(item_index, 0),
                "last_session": latest_session_by_item.get(item_index),
            }
        )

    queue.sort(
        key=lambda item: (
            item["session_count"] > 0,
            -float(item["largest_operator_gap"]["spread"]) if item.get("largest_operator_gap") else 0.0,
            -float(item["mean_spread"]),
            item["item_index"],
        )
    )

    recent_sessions = sorted(
        sessions,
        key=lambda entry: str(entry.get("timestamp", "")),
        reverse=True,
    )[:20]
    return {
        "queue": queue[:limit],
        "recent_sessions": recent_sessions,
    }
