"""Surface-leakage screen for the hidden/encoded prompt-injection bank.

This is a preflight gate. It does not read model hidden states and it does not
license a detector. It only checks whether the bank is worth W0 capture by
making sure simple surface baselines do not already solve PRESENT vs ABSENT.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_behavior_v5_prespeech import (  # noqa: E402
    balanced_accuracy,
    cross_val_category_majority_predict,
    cross_val_linear_probe_predict,
    hash_text_features,
    make_group_folds,
)


SCHEMA_VERSION = "cas_harness_hidden_prompt_injection_surface_screen.v1"
STATUS_LABELS = ("ABSENT", "PRESENT")


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-bank", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--text-dim", type=int, default=4096)
    parser.add_argument("--max-text-ba", type=float, default=0.60)
    parser.add_argument("--max-baseline-ba", type=float, default=0.60)
    parser.add_argument("--min-payload-classes", type=int, default=5)
    parser.add_argument("--min-groups-per-label", type=int, default=20)
    parser.add_argument("--min-rows-per-label", type=int, default=100)
    parser.add_argument("--probe-C", type=float, default=0.25)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = screen_hidden_prompt_injection_surface_leakage(
        prompt_bank_path=args.prompt_bank,
        folds=args.folds,
        seed=args.seed,
        text_dim=args.text_dim,
        max_text_ba=args.max_text_ba,
        max_baseline_ba=args.max_baseline_ba,
        min_payload_classes=args.min_payload_classes,
        min_groups_per_label=args.min_groups_per_label,
        min_rows_per_label=args.min_rows_per_label,
        probe_C=args.probe_C,
        probe_max_iter=args.probe_max_iter,
    )
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "claim": report["claim"],
                "text_hash_balanced_accuracy": report["metrics"].get("text_hash_balanced_accuracy"),
                "length_balanced_accuracy": report["metrics"].get("length_balanced_accuracy"),
                "gates": report["gates"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"[hidden-prompt-injection-surface-screen] wrote {args.output_report}")
    return 0


def screen_hidden_prompt_injection_surface_leakage(
    *,
    prompt_bank_path: Path,
    folds: int = 5,
    seed: int = 42,
    text_dim: int = 4096,
    max_text_ba: float = 0.60,
    max_baseline_ba: float = 0.60,
    min_payload_classes: int = 5,
    min_groups_per_label: int = 20,
    min_rows_per_label: int = 100,
    probe_C: float = 0.25,
    probe_max_iter: int = 1000,
) -> dict[str, Any]:
    rows = load_bank_rows(prompt_bank_path)
    prepared = prepare_arrays(rows)
    exact_violations = exact_prompt_group_violations(prepared["groups"], prepared["prompts"])
    label_counts = Counter(prepared["labels"].tolist())
    group_label_counts = count_groups_by_label(prepared["groups"], prepared["labels"])
    payload_label_counts = count_payloads_by_label(prepared["payloads"], prepared["labels"])
    testable_payloads = sorted(
        payload
        for payload, counter in payload_label_counts.items()
        if all(counter.get(label, 0) > 0 for label in STATUS_LABELS)
    )

    if len(set(prepared["groups"].tolist())) < folds:
        return blocked_report(
            prompt_bank_path=prompt_bank_path,
            prepared=prepared,
            reason=f"Need at least {folds} prompt groups for grouped folds.",
            exact_violations=exact_violations,
        )

    fold_indices = make_group_folds(prepared["groups"], n_folds=folds, seed=seed)
    y = prepared["labels"]

    text_x = hash_text_features(prepared["prompts"], dim=text_dim)
    text_pred = cross_val_linear_probe_predict(
        text_x,
        y,
        fold_indices,
        C=probe_C,
        max_iter=probe_max_iter,
    )
    text_ba = balanced_accuracy(y, text_pred)

    length_x = np.asarray([[len(prompt)] for prompt in prepared["prompts"]], dtype=np.float32)
    length_pred = cross_val_linear_probe_predict(
        length_x,
        y,
        fold_indices,
        C=probe_C,
        max_iter=probe_max_iter,
    )
    length_ba = balanced_accuracy(y, length_pred)

    payload_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(prepared["payloads"], y, fold_indices),
    )
    domain_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(prepared["domains"], y, fold_indices),
    )
    encoding_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(prepared["encodings"], y, fold_indices),
    )

    gates = {
        "exact_prompt_group_pass": not exact_violations,
        "label_row_floor_pass": all(label_counts.get(label, 0) >= min_rows_per_label for label in STATUS_LABELS),
        "label_group_floor_pass": all(
            group_label_counts.get(label, 0) >= min_groups_per_label for label in STATUS_LABELS
        ),
        "payload_balance_pass": len(testable_payloads) >= min_payload_classes,
        "text_leakage_pass": text_ba <= max_text_ba,
        "length_leakage_pass": length_ba <= max_baseline_ba,
        "payload_leakage_pass": payload_ba <= max_baseline_ba,
        "domain_leakage_pass": domain_ba <= max_baseline_ba,
        "encoding_leakage_pass": encoding_ba <= max_baseline_ba,
    }
    ready = all(gates.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "prompt_bank": str(prompt_bank_path),
        "status": "READY_FOR_W0_CAPTURE" if ready else "BLOCKED",
        "claim": "OPEN / NOT LICENSED for internal W0 prompt-injection detection.",
        "claim_ceiling": (
            "This is a surface-leakage data-readiness screen only. It can authorize "
            "W0 capture, but it does not license hidden-state detection, live "
            "interception, prevention/removal/reversal, hallucination prevention, "
            "CjtPredictionHead claims, or causal proof."
        ),
        "row_count": int(len(y)),
        "prompt_group_count": int(len(set(prepared["groups"].tolist()))),
        "fold_count": int(len(fold_indices)),
        "required_payload_classes": int(min_payload_classes),
        "required_groups_per_label": int(min_groups_per_label),
        "required_rows_per_label": int(min_rows_per_label),
        "testable_payload_class_count": int(len(testable_payloads)),
        "testable_payload_classes": testable_payloads,
        "label_distribution": dict(sorted(label_counts.items())),
        "label_prompt_group_distribution": dict(sorted(group_label_counts.items())),
        "payload_label_distribution": {
            payload: dict(sorted(counter.items())) for payload, counter in sorted(payload_label_counts.items())
        },
        "encoding_distribution": dict(sorted(Counter(prepared["encodings"].tolist()).items())),
        "metrics": {
            "text_hash_balanced_accuracy": round(text_ba, 6),
            "length_balanced_accuracy": round(length_ba, 6),
            "payload_majority_balanced_accuracy": round(payload_ba, 6),
            "domain_majority_balanced_accuracy": round(domain_ba, 6),
            "encoding_majority_balanced_accuracy": round(encoding_ba, 6),
            "max_text_ba": float(max_text_ba),
            "max_baseline_ba": float(max_baseline_ba),
        },
        "gates": gates,
        "exact_prompt_group_violations": exact_violations[:20],
        "next_artifact_when_ready": (
            "Capture all-layer W0 activations for this bank, preserving prompt_injection_status "
            "labels, then run evaluate_hidden_prompt_injection_prespeech.py."
        ),
    }


def load_bank_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("scenarios", payload) if isinstance(payload, Mapping) else payload
    if not isinstance(rows, list):
        raise RuntimeError("Prompt bank must be a list or contain a scenarios list.")
    usable = [row for row in rows if isinstance(row, Mapping)]
    if not usable:
        raise RuntimeError("No usable prompt rows found.")
    return [dict(row) for row in usable]


def prepare_arrays(rows: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    prompts: list[str] = []
    groups: list[str] = []
    labels: list[str] = []
    payloads: list[str] = []
    domains: list[str] = []
    encodings: list[str] = []
    for index, row in enumerate(rows):
        prompt = str(row.get("prompt") or "").strip()
        label = normalise_status(row.get("prompt_injection_status") or row.get("target_prompt_injection_status"))
        payload_class = str(row.get("payload_class") or "").strip()
        if not prompt or label is None or not payload_class:
            continue
        prompts.append(prompt)
        groups.append(str(row.get("prompt_group_id") or derive_prompt_group_id(row, index)))
        labels.append(label)
        payloads.append(payload_class)
        domains.append(str(row.get("domain") or row.get("expected_cas_axes", {}).get("domain") or "unknown"))
        encodings.append(str(row.get("encoding") or "unknown"))
    if not prompts:
        raise RuntimeError("No rows with prompt, payload_class, and prompt_injection_status found.")
    return {
        "prompts": np.asarray(prompts, dtype=object).astype(str),
        "groups": np.asarray(groups, dtype=object).astype(str),
        "labels": np.asarray(labels, dtype=object).astype(str),
        "payloads": np.asarray(payloads, dtype=object).astype(str),
        "domains": np.asarray(domains, dtype=object).astype(str),
        "encodings": np.asarray(encodings, dtype=object).astype(str),
    }


def normalise_status(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    aliases = {
        "PROMPT_INJECTION_PRESENT": "PRESENT",
        "INJECTION_PRESENT": "PRESENT",
        "PROMPT_INJECTION_ABSENT": "ABSENT",
        "INJECTION_ABSENT": "ABSENT",
        "CLEAN": "ABSENT",
    }
    text = aliases.get(text, text)
    return text if text in STATUS_LABELS else None


def derive_prompt_group_id(row: Mapping[str, Any], index: int) -> str:
    scenario_id = str(row.get("id") or row.get("scenario_id") or "").strip()
    if scenario_id:
        return scenario_id.rsplit("_seed_", 1)[0]
    digest = hashlib.sha256(str(row.get("prompt") or index).encode("utf-8")).hexdigest()[:16]
    return f"prompt:{digest}"


def exact_prompt_group_violations(groups: np.ndarray, prompts: np.ndarray) -> list[str]:
    prompts_by_group: dict[str, set[str]] = defaultdict(set)
    for group, prompt in zip(groups.tolist(), prompts.tolist(), strict=True):
        prompts_by_group[str(group)].add(hashlib.sha256(str(prompt).encode("utf-8")).hexdigest())
    return sorted(group for group, hashes in prompts_by_group.items() if len(hashes) != 1)


def count_groups_by_label(groups: np.ndarray, labels: np.ndarray) -> dict[str, int]:
    labels_by_group: dict[str, str] = {}
    for group, label in zip(groups.tolist(), labels.tolist(), strict=True):
        labels_by_group.setdefault(str(group), str(label))
    return dict(sorted(Counter(labels_by_group.values()).items()))


def count_payloads_by_label(payloads: np.ndarray, labels: np.ndarray) -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for payload, label in zip(payloads.tolist(), labels.tolist(), strict=True):
        counts[str(payload)][str(label)] += 1
    return counts


def blocked_report(
    *,
    prompt_bank_path: Path,
    prepared: dict[str, np.ndarray],
    reason: str,
    exact_violations: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "prompt_bank": str(prompt_bank_path),
        "status": "BLOCKED",
        "claim": "OPEN / NOT LICENSED for internal W0 prompt-injection detection.",
        "claim_ceiling": "Surface-leakage preflight failed before W0 capture.",
        "blocker": reason,
        "row_count": int(len(prepared.get("labels", []))),
        "prompt_group_count": int(len(set(prepared.get("groups", np.asarray([], dtype=object)).tolist()))),
        "label_distribution": dict(sorted(Counter(prepared.get("labels", np.asarray([], dtype=object)).tolist()).items())),
        "metrics": {},
        "gates": {"ready_for_grouped_folds_pass": False},
        "exact_prompt_group_violations": exact_violations[:20],
    }


if __name__ == "__main__":
    raise SystemExit(main())
