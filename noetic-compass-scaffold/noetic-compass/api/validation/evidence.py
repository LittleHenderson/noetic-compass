"""Validation evidence storage, review, export, and seeding helpers.

Tracks auxiliary evidence beyond human labels:
- scorer agreement cases
- benchmark suite runs
- false positive / false negative cases
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from io import StringIO
from pathlib import Path
from statistics import mean
from typing import Any


EVIDENCE_KINDS = ("scorer_agreement", "benchmark_suites", "error_cases")

_KIND_LABELS = {
    "scorer_agreement": "Scorer Agreement",
    "benchmark_suites": "Benchmark Suite",
    "error_cases": "Error Case",
}

_TIER_RANKS = {
    "Below Prototype Threshold": 0,
    "Bronze Research Tier": 1,
    "Silver Research Tier": 2,
    "Gold Research Tier": 3,
    "Platinum Research Tier": 4,
}


def _validation_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "validation"


def _default_path() -> Path:
    return _validation_dir() / "evidence_log.json"


def _baseline_path() -> Path:
    return _validation_dir() / "baseline_results.json"


def _studies_dir() -> Path:
    return _validation_dir() / "studies"


def _labels_path() -> Path:
    return _validation_dir() / "human_labels.json"


def _empty_store() -> dict:
    return {
        "scorer_agreement": [],
        "benchmark_suites": [],
        "error_cases": [],
    }


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clip_excerpt(text: str, limit: int = 220) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[:limit - 3]}..."


def _tier_from_score(score_100: float) -> str:
    if score_100 >= 90.0:
        return "Platinum Research Tier"
    if score_100 >= 75.0:
        return "Gold Research Tier"
    if score_100 >= 60.0:
        return "Silver Research Tier"
    if score_100 >= 40.0:
        return "Bronze Research Tier"
    return "Below Prototype Threshold"


def _normalize_tier(certification: str | None) -> str:
    if not certification:
        return "Below Prototype Threshold"
    if certification == "Fail":
        return "Below Prototype Threshold"
    return f"{certification} Research Tier"


def _entry_provider(kind: str, entry: dict) -> str | None:
    if kind == "scorer_agreement":
        return entry.get("generator_provider") or entry.get("provider")
    return entry.get("provider")


def _entry_model(kind: str, entry: dict) -> str | None:
    if kind == "scorer_agreement":
        return entry.get("generator_model") or entry.get("model")
    return entry.get("model")


def _entry_timestamp(entry: dict) -> str:
    value = entry.get("timestamp")
    return str(value) if value else ""


def _entry_summary(kind: str, entry: dict) -> str:
    if kind == "scorer_agreement":
        machine_score = _safe_float(entry.get("machine_score"))
        scorer_score = _safe_float(entry.get("scorer_score"))
        generator = entry.get("generator_provider", "unknown")
        scorer = entry.get("scorer_provider", "unknown")
        return (
            f"{generator} generated, {scorer} scored, "
            f"machine {machine_score:.1f} vs scorer {scorer_score:.1f}."
        )
    if kind == "benchmark_suites":
        suite = entry.get("suite_name", "Unnamed suite")
        provider = entry.get("provider", "unknown")
        scoring_mode = str(entry.get("scoring_mode") or "heuristic_fallback")
        scoring_provider = entry.get("scoring_provider")
        cases_run = _safe_int(entry.get("cases_run"))
        mean_score = entry.get("mean_score")
        successes = _safe_int(entry.get("successes"))
        failures = _safe_int(entry.get("failures"))
        status = str(entry.get("status") or "completed")
        mode_bits = scoring_mode
        if scoring_mode == "secondary_llm" and scoring_provider:
            mode_bits = f"{scoring_mode} via {scoring_provider}"
        if mean_score is None:
            mean_bits = "mean unavailable"
        else:
            mean_bits = f"mean {_safe_float(mean_score):.1f}"
        if failures or status == "failed":
            return (
                f"{suite} on {provider} [{mode_bits}], status={status}, "
                f"{successes} succeeded / {failures} failed, {mean_bits}."
            )
        return f"{suite} on {provider} [{mode_bits}], {cases_run} cases, {mean_bits}."
    case_kind = str(entry.get("kind", "error_case")).replace("_", " ")
    expected = entry.get("expected_tier", "unknown expected tier")
    observed = entry.get("observed_tier", "unknown observed tier")
    return f"{case_kind}: expected {expected}, observed {observed}."


def _flatten_store(store: dict) -> list[dict]:
    rows: list[dict] = []
    for kind in EVIDENCE_KINDS:
        for entry in store.get(kind, []):
            row = dict(entry)
            if kind == "error_cases":
                row["case_kind"] = entry.get("kind")
            row["kind"] = kind
            row["kind_label"] = _KIND_LABELS[kind]
            row["provider"] = _entry_provider(kind, entry)
            row["model"] = _entry_model(kind, entry)
            row["summary"] = _entry_summary(kind, entry)
            rows.append(row)
    rows.sort(key=lambda item: _entry_timestamp(item), reverse=True)
    return rows


def _iter_study_bundles(
    *,
    baseline_path: Path | None = None,
) -> list[tuple[Path, dict]]:
    seen: set[Path] = set()
    bundles: list[tuple[Path, dict]] = []

    primary = baseline_path or _baseline_path()
    if primary.exists():
        payload = _read_json(primary)
        if isinstance(payload, dict):
            bundles.append((primary, payload))
            seen.add(primary.resolve())

    for path in sorted(_studies_dir().glob("*.json")):
        resolved = path.resolve()
        if resolved in seen:
            continue
        payload = _read_json(path)
        if isinstance(payload, dict):
            bundles.append((path, payload))
            seen.add(resolved)
    return bundles


def _display_bundle_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_validation_dir().resolve()))
    except ValueError:
        return str(path)


def _matches_filter(
    entry: dict,
    *,
    kind: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    q: str | None = None,
) -> bool:
    if kind and entry.get("kind") != kind:
        return False
    if provider and str(entry.get("provider") or "").lower() != provider.lower():
        return False
    if model and str(entry.get("model") or "").lower() != model.lower():
        return False
    if q:
        haystack = " ".join(
            str(entry.get(field, ""))
            for field in (
                "summary",
                "notes",
                "prompt_excerpt",
                "suite_name",
                "expected_tier",
                "observed_tier",
                "provider",
                "model",
            )
        ).lower()
        if q.lower() not in haystack:
            return False
    return True


def load_evidence(path: Path | str | None = None) -> dict:
    file_path = Path(path) if path else _default_path()
    if not file_path.exists():
        return _empty_store()
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return _empty_store()

    store = _empty_store()
    if isinstance(data, dict):
        for key in store:
            value = data.get(key, [])
            store[key] = value if isinstance(value, list) else []
    return store


def save_evidence(store: dict, path: Path | str | None = None) -> None:
    file_path = Path(path) if path else _default_path()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(store, indent=2), encoding="utf-8")


def append_evidence_entry(kind: str, entry: dict, path: Path | str | None = None) -> dict:
    store = load_evidence(path)
    if kind not in store:
        raise ValueError(f"unknown evidence kind: {kind}")
    store[kind].append(entry)
    save_evidence(store, path)
    return store


def build_evidence_summary(store: dict) -> dict:
    scorer_entries = store.get("scorer_agreement", [])
    benchmark_entries = store.get("benchmark_suites", [])
    error_entries = store.get("error_cases", [])

    scorer_gaps = [
        abs(float(entry.get("machine_score", 0.0)) - float(entry.get("scorer_score", 0.0)))
        for entry in scorer_entries
    ]
    benchmark_case_total = sum(int(entry.get("cases_run", 0)) for entry in benchmark_entries)
    benchmark_failed = sum(1 for entry in benchmark_entries if str(entry.get("status") or "completed") != "completed")
    false_positives = sum(1 for entry in error_entries if entry.get("kind") == "false_positive")
    false_negatives = sum(1 for entry in error_entries if entry.get("kind") == "false_negative")

    return {
        "scorer_agreement": {
            "count": len(scorer_entries),
            "mean_absolute_gap": round(mean(scorer_gaps), 3) if scorer_gaps else 0.0,
            "recent": scorer_entries[-5:],
        },
        "benchmark_suites": {
            "count": len(benchmark_entries),
            "cases_run": benchmark_case_total,
            "failed_runs": benchmark_failed,
            "recent": benchmark_entries[-5:],
        },
        "error_cases": {
            "count": len(error_entries),
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "recent": error_entries[-5:],
        },
    }


def build_evidence_review(
    store: dict,
    *,
    kind: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    all_entries = _flatten_store(store)
    filtered = [
        entry
        for entry in all_entries
        if _matches_filter(entry, kind=kind, provider=provider, model=model, q=q)
    ]

    return {
        "total": len(filtered),
        "returned": len(filtered[offset: offset + limit]),
        "filters": {
            "kind": kind,
            "provider": provider,
            "model": model,
            "q": q,
            "limit": limit,
            "offset": offset,
        },
        "facets": {
            "kinds": [{"value": value, "label": _KIND_LABELS[value]} for value in EVIDENCE_KINDS],
            "providers": sorted({str(entry.get("provider")) for entry in all_entries if entry.get("provider")}),
            "models": sorted({str(entry.get("model")) for entry in all_entries if entry.get("model")}),
        },
        "entries": filtered[offset: offset + limit],
    }


def build_evidence_trends(store: dict) -> dict:
    entries = _flatten_store(store)
    timeline: dict[str, dict[str, Any]] = {}
    provider_totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "provider": "",
            "total_entries": 0,
            "scorer_agreement": 0,
            "benchmark_suites": 0,
            "error_cases": 0,
            "mean_absolute_gap": 0.0,
            "_gaps": [],
            "benchmark_cases": 0,
            "failed_runs": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "latest_timestamp": "",
        }
    )
    model_totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "model": "",
            "total_entries": 0,
            "scorer_agreement": 0,
            "benchmark_suites": 0,
            "error_cases": 0,
            "mean_absolute_gap": 0.0,
            "_gaps": [],
            "benchmark_cases": 0,
            "failed_runs": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "latest_timestamp": "",
        }
    )

    tier_drift: dict[tuple[str, str], int] = defaultdict(int)

    for entry in entries:
        timestamp = _entry_timestamp(entry)
        date_key = timestamp[:10] if len(timestamp) >= 10 else "unknown"
        day = timeline.setdefault(
            date_key,
            {"date": date_key, "total": 0, "scorer_agreement": 0, "benchmark_suites": 0, "error_cases": 0},
        )
        day["total"] += 1
        day[entry["kind"]] += 1

        provider = entry.get("provider")
        if provider:
            row = provider_totals[str(provider)]
            row["provider"] = str(provider)
            row["total_entries"] += 1
            row[entry["kind"]] += 1
            row["latest_timestamp"] = max(row["latest_timestamp"], timestamp)
            if entry["kind"] == "scorer_agreement":
                gap = abs(_safe_float(entry.get("machine_score")) - _safe_float(entry.get("scorer_score")))
                row["_gaps"].append(gap)
            elif entry["kind"] == "benchmark_suites":
                row["benchmark_cases"] += _safe_int(entry.get("cases_run"))
                if str(entry.get("status") or "completed") != "completed":
                    row["failed_runs"] += 1
            elif entry["kind"] == "error_cases":
                case_kind = entry.get("case_kind") or entry.get("kind")
                if case_kind == "false_positive":
                    row["false_positives"] += 1
                elif case_kind == "false_negative":
                    row["false_negatives"] += 1

        model = entry.get("model")
        if model:
            row = model_totals[str(model)]
            row["model"] = str(model)
            row["total_entries"] += 1
            row[entry["kind"]] += 1
            row["latest_timestamp"] = max(row["latest_timestamp"], timestamp)
            if entry["kind"] == "scorer_agreement":
                gap = abs(_safe_float(entry.get("machine_score")) - _safe_float(entry.get("scorer_score")))
                row["_gaps"].append(gap)
            elif entry["kind"] == "benchmark_suites":
                row["benchmark_cases"] += _safe_int(entry.get("cases_run"))
                if str(entry.get("status") or "completed") != "completed":
                    row["failed_runs"] += 1
            elif entry["kind"] == "error_cases":
                case_kind = entry.get("case_kind") or entry.get("kind")
                if case_kind == "false_positive":
                    row["false_positives"] += 1
                elif case_kind == "false_negative":
                    row["false_negatives"] += 1

        if entry["kind"] == "error_cases":
            expected = str(entry.get("expected_tier") or "unknown")
            observed = str(entry.get("observed_tier") or "unknown")
            tier_drift[(expected, observed)] += 1

    def _finalize(rows: dict[str, dict[str, Any]], key: str) -> list[dict]:
        finalized: list[dict] = []
        for row in rows.values():
            gaps = row.pop("_gaps")
            row["mean_absolute_gap"] = round(mean(gaps), 3) if gaps else 0.0
            finalized.append(row)
        finalized.sort(key=lambda item: (-item["total_entries"], str(item.get(key) or "")))
        return finalized

    return {
        "timeline": [timeline[date] for date in sorted(timeline.keys())],
        "by_provider": _finalize(provider_totals, "provider"),
        "by_model": _finalize(model_totals, "model"),
        "tier_drift": [
            {"expected_tier": expected, "observed_tier": observed, "count": count}
            for (expected, observed), count in sorted(tier_drift.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


def export_evidence_csv(
    store: dict,
    *,
    kind: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    q: str | None = None,
) -> str:
    review = build_evidence_review(store, kind=kind, provider=provider, model=model, q=q, limit=100000, offset=0)
    fields = [
        "timestamp",
        "kind",
        "provider",
        "model",
        "scoring_mode",
        "scoring_provider",
        "scoring_model",
        "summary",
        "case_kind",
        "item_index",
        "generator_provider",
        "generator_model",
        "scorer_provider",
        "scorer_model",
        "machine_score",
        "scorer_score",
        "suite_name",
        "status",
        "successes",
        "failures",
        "cases_run",
        "mean_score",
        "variance",
        "expected_tier",
        "observed_tier",
        "prompt_excerpt",
        "notes",
    ]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for entry in review["entries"]:
        writer.writerow({field: entry.get(field, "") for field in fields})
    return buffer.getvalue()


def seed_evidence_from_artifacts(
    *,
    path: Path | str | None = None,
    baseline_path: Path | str | None = None,
    labels_path: Path | str | None = None,
    replace: bool = True,
) -> dict:
    labels = _read_json(Path(labels_path) if labels_path else _labels_path()) or []
    primary_path = Path(baseline_path) if baseline_path else _baseline_path()
    primary_bundle = _read_json(primary_path) or {}
    summary = primary_bundle.get("summary", {}) if isinstance(primary_bundle, dict) else {}
    results = primary_bundle.get("results", []) if isinstance(primary_bundle, dict) else []

    labels_by_item: dict[int, list[dict]] = defaultdict(list)
    for label in labels:
        idx = label.get("item_index")
        if idx is None:
            continue
        labels_by_item[_safe_int(idx)] += [label]

    provider = str(summary.get("provider") or "unknown")
    model_counts: dict[str, int] = defaultdict(int)
    for item in results:
        model = str(item.get("llm_response", {}).get("model") or "")
        if model:
            model_counts[model] += 1
    default_model = max(model_counts, key=model_counts.get) if model_counts else None

    scorer_entries: list[dict] = []
    error_entries: list[dict] = []

    for item in results:
        idx = _safe_int(item.get("index"), -1)
        if idx < 0 or idx not in labels_by_item:
            continue
        item_labels = labels_by_item[idx]
        human_operator_means = [
            mean(float(score) for score in label.get("operator_scores", [])[:10])
            for label in item_labels
            if label.get("operator_scores")
        ]
        if not human_operator_means:
            continue

        machine_operator_scores = item.get("operator_scores", [])[:10]
        if not machine_operator_scores:
            continue

        machine_mean_10 = mean(float(score) for score in machine_operator_scores) * 10.0
        human_panel_mean_10 = mean(human_operator_means)
        latest_timestamp = max(str(label.get("timestamp", "")) for label in item_labels)
        model = str(item.get("llm_response", {}).get("model") or default_model or "")
        prompt_excerpt = _clip_excerpt(str(item.get("prompt", "")))
        scorer_entries.append({
            "generator_provider": provider,
            "generator_model": model or None,
            "scorer_provider": "human_panel",
            "scorer_model": "human_panel_v1",
            "prompt_excerpt": prompt_excerpt,
            "machine_score": round(machine_mean_10, 3),
            "scorer_score": round(human_panel_mean_10, 3),
            "notes": (
                f"Derived from {len(item_labels)} human ratings for baseline item {idx}; "
                f"machine score is mean operator score, scorer score is panel mean."
            ),
            "item_index": idx,
            "timestamp": latest_timestamp,
        })

        expected_tier = _tier_from_score(human_panel_mean_10 * 10.0)
        observed_tier = _normalize_tier(str(item.get("certification") or "Fail"))
        expected_rank = _TIER_RANKS[expected_tier]
        observed_rank = _TIER_RANKS[observed_tier]
        if expected_rank != observed_rank:
            error_entries.append({
                "kind": "false_positive" if observed_rank > expected_rank else "false_negative",
                "prompt_excerpt": prompt_excerpt,
                "expected_tier": expected_tier,
                "observed_tier": observed_tier,
                "notes": (
                    f"Derived from {len(item_labels)} human ratings; "
                    f"machine composite={_safe_float(item.get('composite')):.2f}, "
                    f"human panel mean={human_panel_mean_10:.2f}/10."
                ),
                "item_index": idx,
                "provider": provider,
                "model": model or None,
                "timestamp": latest_timestamp,
            })

    benchmark_entries: list[dict] = []
    for bundle_path, bundle in _iter_study_bundles(baseline_path=primary_path):
        bundle_summary = bundle.get("summary", {}) if isinstance(bundle, dict) else {}
        if not bundle_summary:
            continue
        bundle_provider = str(bundle_summary.get("provider") or "unknown")
        bundle_results = bundle.get("results", []) if isinstance(bundle, dict) else []
        bundle_model_counts: dict[str, int] = defaultdict(int)
        for item in bundle_results:
            model = str(item.get("llm_response", {}).get("model") or "")
            if model:
                bundle_model_counts[model] += 1
        bundle_model = max(bundle_model_counts, key=bundle_model_counts.get) if bundle_model_counts else None
        std = _safe_float(bundle_summary.get("composite_std"))
        display_path = _display_bundle_path(bundle_path)
        notes = (
            f"Derived from {display_path} summary statistics."
            if bundle_summary.get("successes", 0) > 0
            else f"Derived from {display_path}; all prompts failed."
        )
        benchmark_entries.append(
            {
                "suite_name": str(bundle_summary.get("study_label") or f"baseline-study-{bundle_provider}"),
                "provider": bundle_provider,
                "model": str(bundle_summary.get("model") or bundle_model or "") or None,
                "scoring_mode": str(bundle_summary.get("scoring_mode") or "heuristic_fallback"),
                "scoring_provider": (
                    str(bundle_summary.get("scoring_provider"))
                    if bundle_summary.get("scoring_provider")
                    else None
                ),
                "scoring_model": (
                    str(bundle_summary.get("scoring_model"))
                    if bundle_summary.get("scoring_model")
                    else None
                ),
                "status": str(bundle_summary.get("status") or "completed"),
                "successes": _safe_int(bundle_summary.get("successes")),
                "failures": _safe_int(bundle_summary.get("failures")),
                "cases_run": _safe_int(bundle_summary.get("prompt_count"), len(bundle_results)),
                "mean_score": round(_safe_float(bundle_summary.get("composite_mean")), 3)
                if bundle_summary.get("composite_mean") is not None
                else None,
                "variance": round(std * std, 4) if bundle_summary.get("composite_std") is not None else None,
                "prompt_source": str(bundle_summary.get("prompt_source") or ""),
                "archive_path": display_path,
                "notes": notes,
                "timestamp": str(bundle_summary.get("study_date") or ""),
            }
        )

    store = _empty_store() if replace else load_evidence(path)
    store["scorer_agreement"] = scorer_entries if replace else store["scorer_agreement"] + scorer_entries
    store["benchmark_suites"] = benchmark_entries if replace else store["benchmark_suites"] + benchmark_entries
    store["error_cases"] = error_entries if replace else store["error_cases"] + error_entries
    save_evidence(store, path)
    return store
