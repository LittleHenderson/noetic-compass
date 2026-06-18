"""Surface-leakage preflight for CJT bias/vibration banks.

Run this before GPU capture. If word/character/length/category baselines can
separate risk perturbations from controls, the bank is not suitable for an
internal hidden-state claim yet.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.build_cjt_bias_vibration_bank import (  # noqa: E402
    BASE_ROLE,
    BENIGN_ROLE,
    INJECTION_ROLE,
    SUPPORTED_ROLE,
    TRUSTED_CORRECTION_ROLE,
    UNSUPPORTED_ROLE,
)
from scripts.evaluate_behavior_v5_prespeech import (  # noqa: E402
    balanced_accuracy,
    cross_val_category_majority_predict,
    cross_val_linear_probe_predict,
    hash_char_ngram_features,
    hash_text_features,
    make_group_folds,
)
from scripts.evaluate_cjt_bias_vibration_diagnostic import length_delta_features  # noqa: E402


SCHEMA_VERSION = "cas_harness_cjt_bias_vibration_surface_screen.v0"
RISK_LABEL = "RISK_PERTURBATION"
CONTROL_LABEL = "CONTROL_PERTURBATION"
RISK_ROLES = {INJECTION_ROLE, UNSUPPORTED_ROLE}
CONTROL_ROLES = {BENIGN_ROLE, TRUSTED_CORRECTION_ROLE, SUPPORTED_ROLE}
DELTA_ROLES = tuple(sorted(RISK_ROLES | CONTROL_ROLES))
DEFAULT_MAX_BASELINE_BA = 0.60


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--text-dim", type=int, default=4096)
    parser.add_argument("--max-baseline-ba", type=float, default=DEFAULT_MAX_BASELINE_BA)
    parser.add_argument("--probe-C", type=float, default=0.25)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = screen_cjt_bias_vibration_surface_leakage(
        bank_path=args.bank,
        folds=args.folds,
        seed=args.seed,
        text_dim=args.text_dim,
        max_baseline_ba=args.max_baseline_ba,
        probe_C=args.probe_C,
        probe_max_iter=args.probe_max_iter,
    )
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "word_text_delta_ba": report["metrics"].get("word_text_delta_balanced_accuracy"),
                "char_text_delta_ba": report["metrics"].get("char_text_delta_balanced_accuracy"),
                "length_delta_ba": report["metrics"].get("length_delta_balanced_accuracy"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"[cjt-bias-vibration-surface] wrote {args.output_report}")
    return 0


def screen_cjt_bias_vibration_surface_leakage(
    *,
    bank_path: Path,
    folds: int,
    seed: int,
    text_dim: int,
    max_baseline_ba: float = DEFAULT_MAX_BASELINE_BA,
    probe_C: float = 0.25,
    probe_max_iter: int = 1000,
) -> dict[str, Any]:
    scenarios = load_scenarios(bank_path)
    delta_rows = build_prompt_delta_rows(scenarios)
    if delta_rows["status"] != "ready":
        return {
            "schema_version": SCHEMA_VERSION,
            "created_at": datetime.now(UTC).isoformat(),
            "bank": str(bank_path),
            "status": "BLOCKED",
            "claim": "OPEN / NOT LICENSED for CJT bias/vibration hidden response detection.",
            "blocker": delta_rows["status"],
            "gates": {"paired_delta_rows_ready_pass": False},
            "metrics": {},
        }

    groups = delta_rows["group_id"]
    y = delta_rows["label"]
    fold_indices = make_group_folds(groups, n_folds=min(folds, len(set(groups.tolist()))), seed=seed)
    base_prompts = delta_rows["base_prompts"]
    variant_prompts = delta_rows["variant_prompts"]

    word_x = delta_hash_features(base_prompts, variant_prompts, dim=text_dim, char=False)
    char_x = delta_hash_features(base_prompts, variant_prompts, dim=text_dim, char=True)
    length_x = length_delta_features(base_prompts, variant_prompts)

    word_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(word_x, y, fold_indices, C=probe_C, max_iter=probe_max_iter),
    )
    char_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(char_x, y, fold_indices, C=probe_C, max_iter=probe_max_iter),
    )
    length_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(length_x, y, fold_indices, C=probe_C, max_iter=probe_max_iter),
    )
    payload_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(delta_rows["payload_class"], y, fold_indices),
    )
    domain_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(delta_rows["domain"], y, fold_indices),
    )
    family_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(delta_rows["family"], y, fold_indices),
    )
    gates = {
        "paired_delta_rows_ready_pass": True,
        "word_text_leakage_pass": word_ba <= max_baseline_ba,
        "char_text_leakage_pass": char_ba <= max_baseline_ba,
        "length_leakage_pass": length_ba <= max_baseline_ba,
        "payload_leakage_pass": payload_ba <= max_baseline_ba,
        "domain_leakage_pass": domain_ba <= max_baseline_ba,
        "family_leakage_pass": family_ba <= max_baseline_ba,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "bank": str(bank_path),
        "status": "READY_FOR_W0_CAPTURE" if all(gates.values()) else "BLOCKED_SURFACE_LEAKAGE",
        "claim": "OPEN / NOT LICENSED for CJT bias/vibration hidden response detection.",
        "claim_ceiling": "Surface preflight only. It does not use hidden states and licenses no internal claim.",
        "gates": gates,
        "metrics": {
            "delta_row_count": int(len(y)),
            "prompt_group_count": int(len(set(groups.tolist()))),
            "delta_label_distribution": dict(sorted(Counter(y.tolist()).items())),
            "word_text_delta_balanced_accuracy": float(word_ba),
            "char_text_delta_balanced_accuracy": float(char_ba),
            "length_delta_balanced_accuracy": float(length_ba),
            "payload_class_balanced_accuracy": float(payload_ba),
            "domain_balanced_accuracy": float(domain_ba),
            "family_balanced_accuracy": float(family_ba),
            "max_baseline_ba": float(max_baseline_ba),
        },
    }


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    scenarios = payload.get("scenarios", payload) if isinstance(payload, dict) else payload
    if not isinstance(scenarios, list):
        raise RuntimeError("Bank must be a list or contain a scenarios list.")
    return [row for row in scenarios if isinstance(row, dict)]


def build_prompt_delta_rows(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in scenarios:
        by_group[str(row.get("prompt_group_id") or row.get("id") or "")].append(row)

    rows: list[dict[str, Any]] = []
    excluded: Counter[str] = Counter()
    for group_id, group_rows in sorted(by_group.items()):
        role_to_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in group_rows:
            role_to_rows[str(row.get("cjt_role") or "")].append(row)
        if BASE_ROLE not in role_to_rows:
            excluded["missing_base_role"] += 1
            continue
        base_prompt = first_prompt(role_to_rows[BASE_ROLE])
        for role in DELTA_ROLES:
            if role not in role_to_rows:
                excluded[f"missing_{role.lower()}"] += 1
                continue
            sample = role_to_rows[role][0]
            rows.append(
                {
                    "group_id": group_id,
                    "role": role,
                    "family": role_family(role, sample),
                    "label": RISK_LABEL if role in RISK_ROLES else CONTROL_LABEL,
                    "payload_class": str(sample.get("payload_class") or "unknown"),
                    "domain": str(sample.get("domain") or "unknown"),
                    "base_prompt": base_prompt,
                    "variant_prompt": str(sample.get("prompt") or ""),
                }
            )
    if not rows:
        return {"status": "blocked_no_paired_delta_rows", "excluded": dict(sorted(excluded.items()))}
    labels = np.asarray([row["label"] for row in rows], dtype=object)
    if not {RISK_LABEL, CONTROL_LABEL}.issubset(set(labels.tolist())):
        return {
            "status": "blocked_missing_risk_or_control_delta_rows",
            "excluded": dict(sorted(excluded.items())),
        }
    return {
        "status": "ready",
        "group_id": np.asarray([row["group_id"] for row in rows], dtype=object),
        "role": np.asarray([row["role"] for row in rows], dtype=object),
        "family": np.asarray([row["family"] for row in rows], dtype=object),
        "label": labels,
        "payload_class": np.asarray([row["payload_class"] for row in rows], dtype=object),
        "domain": np.asarray([row["domain"] for row in rows], dtype=object),
        "base_prompts": np.asarray([row["base_prompt"] for row in rows], dtype=object),
        "variant_prompts": np.asarray([row["variant_prompt"] for row in rows], dtype=object),
    }


def first_prompt(rows: list[dict[str, Any]]) -> str:
    return str(rows[0].get("prompt") or "") if rows else ""


def role_family(role: str, row: dict[str, Any]) -> str:
    if role in {INJECTION_ROLE, BENIGN_ROLE, TRUSTED_CORRECTION_ROLE}:
        return "instruction_integrity"
    if role in {SUPPORTED_ROLE, UNSUPPORTED_ROLE}:
        return "factual_support"
    return str(row.get("cjt_family") or "unknown")


def delta_hash_features(base_prompts: np.ndarray, variant_prompts: np.ndarray, *, dim: int, char: bool) -> np.ndarray:
    base = hash_char_ngram_features(base_prompts, dim=dim) if char else hash_text_features(base_prompts, dim=dim)
    variant = (
        hash_char_ngram_features(variant_prompts, dim=dim)
        if char
        else hash_text_features(variant_prompts, dim=dim)
    )
    return (variant - base).astype(np.float32)


if __name__ == "__main__":
    raise SystemExit(main())
