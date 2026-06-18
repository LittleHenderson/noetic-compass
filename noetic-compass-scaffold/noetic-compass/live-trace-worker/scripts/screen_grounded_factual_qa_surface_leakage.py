"""Surface-leakage screen for grounded factual-QA hallucination-risk banks.

This is a preflight gate. It does not read model hidden states and it does not
license hallucination detection or prevention. It only checks whether a bank is
worth W0 capture by making sure simple surface baselines do not already solve
SUPPORTED versus UNSUPPORTED labels.
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
    hash_char_ngram_features,
    hash_text_features,
    make_group_folds,
)


SCHEMA_VERSION = "cas_harness_grounded_factual_qa_surface_screen.v1"
SUPPORT_LABELS = ("SUPPORTED", "UNSUPPORTED")


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-bank", required=True, type=Path)
    parser.add_argument("--output-report", "--output", required=True, dest="output_report", type=Path)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--text-dim", type=int, default=4096)
    parser.add_argument("--max-text-ba", type=float, default=0.60)
    parser.add_argument("--max-baseline-ba", type=float, default=0.60)
    parser.add_argument("--min-topic-classes", type=int, default=5)
    parser.add_argument("--min-label-per-topic", type=int, default=40)
    parser.add_argument("--min-mixed-prompt-groups", type=int, default=20)
    parser.add_argument("--probe-C", type=float, default=0.25)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = screen_grounded_factual_qa_surface_leakage(
        prompt_bank_path=args.prompt_bank,
        folds=args.folds,
        seed=args.seed,
        text_dim=args.text_dim,
        max_text_ba=args.max_text_ba,
        max_baseline_ba=args.max_baseline_ba,
        min_topic_classes=args.min_topic_classes,
        min_label_per_topic=args.min_label_per_topic,
        min_mixed_prompt_groups=args.min_mixed_prompt_groups,
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
                "char_text_hash_balanced_accuracy": report["metrics"].get("char_text_hash_balanced_accuracy"),
                "gates": report["gates"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"[grounded-factual-qa-surface-screen] wrote {args.output_report}")
    return 0


def screen_grounded_factual_qa_surface_leakage(
    *,
    prompt_bank_path: Path,
    folds: int = 5,
    seed: int = 42,
    text_dim: int = 4096,
    max_text_ba: float = 0.60,
    max_baseline_ba: float = 0.60,
    min_topic_classes: int = 5,
    min_label_per_topic: int = 40,
    min_mixed_prompt_groups: int = 20,
    probe_C: float = 0.25,
    probe_max_iter: int = 1000,
) -> dict[str, Any]:
    rows = load_bank_rows(prompt_bank_path)
    prepared = prepare_arrays(rows)
    exact_violations = exact_prompt_group_violations(prepared["groups"], prepared["prompts"])
    prompt_contract = summarize_prompt_group_contract(
        prepared["groups"],
        prepared["prompts"],
        prepared["labels"],
    )
    label_counts = Counter(prepared["labels"].tolist())
    topic_label_counts = count_categories_by_label(prepared["topics"], prepared["labels"])
    testable_topics = sorted(
        topic
        for topic, counter in topic_label_counts.items()
        if all(counter.get(label, 0) >= min_label_per_topic for label in SUPPORT_LABELS)
    )

    if len(set(prepared["groups"].tolist())) < folds:
        return blocked_report(
            prompt_bank_path=prompt_bank_path,
            prepared=prepared,
            reason=f"Need at least {folds} prompt groups for grouped folds.",
            exact_violations=exact_violations,
            prompt_contract=prompt_contract,
        )

    fold_indices = make_group_folds(prepared["groups"], n_folds=folds, seed=seed)
    y = prepared["labels"]

    text_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            hash_text_features(prepared["prompts"], dim=text_dim),
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )
    char_text_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            hash_char_ngram_features(prepared["prompts"], dim=text_dim),
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )
    prompt_length_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            np.asarray([[len(prompt)] for prompt in prepared["prompts"]], dtype=np.float32),
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )
    evidence_length_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            prepared["evidence_lengths"].reshape(-1, 1),
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )
    topic_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(prepared["topics"], y, fold_indices),
    )
    domain_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(prepared["domains"], y, fold_indices),
    )
    evidence_source_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(prepared["evidence_sources"], y, fold_indices),
    )
    retrieval_condition_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(prepared["retrieval_conditions"], y, fold_indices),
    )
    retrieval_score_bucket_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(prepared["retrieval_score_buckets"], y, fold_indices),
    )

    gates = {
        "exact_prompt_group_pass": not exact_violations,
        "same_prompt_mixed_group_floor_pass": (
            prompt_contract["mixed_prompt_group_count"] >= min_mixed_prompt_groups
        ),
        "label_row_floor_pass": all(
            label_counts.get(label, 0) >= min_label_per_topic for label in SUPPORT_LABELS
        ),
        "topic_floor_pass": len(testable_topics) >= min_topic_classes,
        "label_per_topic_floor_pass": all(
            all(counter.get(label, 0) >= min_label_per_topic for label in SUPPORT_LABELS)
            for counter in topic_label_counts.values()
        ),
        "text_leakage_pass": text_ba <= max_text_ba,
        "char_text_leakage_pass": char_text_ba <= max_text_ba,
        "prompt_length_leakage_pass": prompt_length_ba <= max_baseline_ba,
        "evidence_length_leakage_pass": evidence_length_ba <= max_baseline_ba,
        "topic_leakage_pass": topic_ba <= max_baseline_ba,
        "domain_leakage_pass": domain_ba <= max_baseline_ba,
        "evidence_source_leakage_pass": evidence_source_ba <= max_baseline_ba,
        "retrieval_condition_leakage_pass": retrieval_condition_ba <= max_baseline_ba,
        "retrieval_score_bucket_leakage_pass": retrieval_score_bucket_ba <= max_baseline_ba,
    }
    ready = all(gates.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "prompt_bank": str(prompt_bank_path),
        "status": "READY_FOR_W0_CAPTURE" if ready else "BLOCKED",
        "claim": "OPEN / NOT LICENSED for internal W0 hallucination-risk detection.",
        "claim_ceiling": (
            "This is a surface-leakage data-readiness screen only. It can authorize "
            "W0 capture, but it does not license hidden-state hallucination detection, "
            "hallucination prevention, live interception, prompt-injection prevention/"
            "removal/reversal, CjtPredictionHead claims, or causal proof."
        ),
        "row_count": int(len(y)),
        "prompt_group_count": int(prompt_contract["prompt_group_count"]),
        "mixed_prompt_group_count": int(prompt_contract["mixed_prompt_group_count"]),
        "fold_count": int(len(fold_indices)),
        "required_topic_classes": int(min_topic_classes),
        "required_label_per_topic": int(min_label_per_topic),
        "required_mixed_prompt_groups": int(min_mixed_prompt_groups),
        "testable_topic_count": int(len(testable_topics)),
        "testable_topics": testable_topics,
        "support_status_distribution": dict(sorted(label_counts.items())),
        "topic_label_distribution": {
            topic: dict(sorted(counter.items())) for topic, counter in sorted(topic_label_counts.items())
        },
        "domain_distribution": dict(sorted(Counter(prepared["domains"].tolist()).items())),
        "evidence_source_distribution": dict(
            sorted(Counter(prepared["evidence_sources"].tolist()).items())
        ),
        "retrieval_condition_distribution": dict(
            sorted(Counter(prepared["retrieval_conditions"].tolist()).items())
        ),
        "retrieval_score_bucket_distribution": dict(
            sorted(Counter(prepared["retrieval_score_buckets"].tolist()).items())
        ),
        "prompt_group_contract": prompt_contract,
        "metrics": {
            "text_hash_balanced_accuracy": round(text_ba, 6),
            "char_text_hash_balanced_accuracy": round(char_text_ba, 6),
            "prompt_length_balanced_accuracy": round(prompt_length_ba, 6),
            "evidence_length_balanced_accuracy": round(evidence_length_ba, 6),
            "topic_majority_balanced_accuracy": round(topic_ba, 6),
            "domain_majority_balanced_accuracy": round(domain_ba, 6),
            "evidence_source_majority_balanced_accuracy": round(evidence_source_ba, 6),
            "retrieval_condition_majority_balanced_accuracy": round(retrieval_condition_ba, 6),
            "retrieval_score_bucket_majority_balanced_accuracy": round(retrieval_score_bucket_ba, 6),
            "max_text_ba": float(max_text_ba),
            "max_baseline_ba": float(max_baseline_ba),
        },
        "gates": gates,
        "exact_prompt_group_violations": exact_violations[:20],
        "next_artifact_when_ready": (
            "Capture W0 activations, preserve support/evidence metadata, then run "
            "evaluate_hallucination_prespeech.py on evidence-grounded labels."
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
    topics: list[str] = []
    domains: list[str] = []
    evidence_sources: list[str] = []
    retrieval_conditions: list[str] = []
    retrieval_score_buckets: list[str] = []
    evidence_lengths: list[int] = []
    for index, row in enumerate(rows):
        prompt = str(row.get("prompt") or "").strip()
        label = normalise_support_status(row.get("support_status") or row.get("target_support_status"))
        topic = str(row.get("topic") or row.get("payload_class") or "").strip()
        if not prompt or label is None or not topic:
            continue
        prompts.append(prompt)
        groups.append(str(row.get("prompt_group_id") or derive_prompt_group_id(row, index)))
        labels.append(label)
        topics.append(topic)
        domains.append(str(row.get("domain") or row.get("expected_cas_axes", {}).get("domain") or "unknown"))
        evidence_sources.append(str(row.get("evidence_source") or "unknown"))
        retrieval_conditions.append(str(row.get("retrieval_condition") or "unknown"))
        retrieval_score_buckets.append(str(row.get("retrieval_score_bucket") or "unknown"))
        evidence_lengths.append(len(str(row.get("evidence_text") or "")))
    if not prompts:
        raise RuntimeError("No rows with prompt, topic, and support_status found.")
    return {
        "prompts": np.asarray(prompts, dtype=object).astype(str),
        "groups": np.asarray(groups, dtype=object).astype(str),
        "labels": np.asarray(labels, dtype=object).astype(str),
        "topics": np.asarray(topics, dtype=object).astype(str),
        "domains": np.asarray(domains, dtype=object).astype(str),
        "evidence_sources": np.asarray(evidence_sources, dtype=object).astype(str),
        "retrieval_conditions": np.asarray(retrieval_conditions, dtype=object).astype(str),
        "retrieval_score_buckets": np.asarray(retrieval_score_buckets, dtype=object).astype(str),
        "evidence_lengths": np.asarray(evidence_lengths, dtype=np.float32),
    }


def normalise_support_status(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    aliases = {
        "SUPPORT": "SUPPORTED",
        "GROUNDED": "SUPPORTED",
        "TRUE_SUPPORTED": "SUPPORTED",
        "UNSUPPORT": "UNSUPPORTED",
        "UNSUPPORTED_CLAIM": "UNSUPPORTED",
        "HALLUCINATED": "UNSUPPORTED",
        "HALLUCINATION": "UNSUPPORTED",
    }
    text = aliases.get(text, text)
    return text if text in SUPPORT_LABELS else None


def derive_prompt_group_id(row: Mapping[str, Any], index: int) -> str:
    scenario_id = str(row.get("id") or row.get("scenario_id") or "").strip()
    if scenario_id and "_seed_" in scenario_id:
        return scenario_id.rsplit("_seed_", 1)[0]
    digest = hashlib.sha256(str(row.get("prompt") or index).encode("utf-8")).hexdigest()[:16]
    return f"prompt:{digest}"


def exact_prompt_group_violations(groups: np.ndarray, prompts: np.ndarray) -> list[str]:
    prompts_by_group: dict[str, set[str]] = defaultdict(set)
    for group, prompt in zip(groups.tolist(), prompts.tolist(), strict=True):
        prompts_by_group[str(group)].add(hashlib.sha256(str(prompt).encode("utf-8")).hexdigest())
    return sorted(group for group, hashes in prompts_by_group.items() if len(hashes) != 1)


def summarize_prompt_group_contract(
    groups: np.ndarray,
    prompts: np.ndarray,
    labels: np.ndarray,
) -> dict[str, Any]:
    prompts_by_group: dict[str, set[str]] = defaultdict(set)
    labels_by_group: dict[str, set[str]] = defaultdict(set)
    rows_by_group: Counter[str] = Counter()
    for group, prompt, label in zip(groups.tolist(), prompts.tolist(), labels.tolist(), strict=True):
        key = str(group)
        prompts_by_group[key].add(str(prompt))
        labels_by_group[key].add(str(label))
        rows_by_group[key] += 1
    non_exact = sorted(group for group, group_prompts in prompts_by_group.items() if len(group_prompts) != 1)
    mixed = sorted(
        group for group, group_labels in labels_by_group.items() if set(SUPPORT_LABELS).issubset(group_labels)
    )
    singleton = sorted(group for group, count in rows_by_group.items() if count < 2)
    return {
        "prompt_group_count": len(prompts_by_group),
        "exact_prompt_group_count": len(prompts_by_group) - len(non_exact),
        "non_exact_prompt_group_count": len(non_exact),
        "mixed_prompt_group_count": len(mixed),
        "singleton_prompt_group_count": len(singleton),
        "non_exact_prompt_group_examples": non_exact[:10],
        "mixed_prompt_group_examples": mixed[:10],
        "singleton_prompt_group_examples": singleton[:10],
        "contract": (
            "Every prompt group must hold one exact prompt/evidence setup, and "
            "enough groups must contain both SUPPORTED and UNSUPPORTED labels."
        ),
    }


def count_categories_by_label(categories: np.ndarray, labels: np.ndarray) -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for category, label in zip(categories.tolist(), labels.tolist(), strict=True):
        counts[str(category)][str(label)] += 1
    return counts


def blocked_report(
    *,
    prompt_bank_path: Path,
    prepared: dict[str, np.ndarray],
    reason: str,
    exact_violations: list[str],
    prompt_contract: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "prompt_bank": str(prompt_bank_path),
        "status": "BLOCKED",
        "claim": "OPEN / NOT LICENSED for internal W0 hallucination-risk detection.",
        "claim_ceiling": "Surface-leakage preflight failed before W0 capture.",
        "blocker": reason,
        "row_count": int(len(prepared.get("labels", []))),
        "prompt_group_count": int(prompt_contract.get("prompt_group_count", 0)),
        "support_status_distribution": dict(
            sorted(Counter(prepared.get("labels", np.asarray([], dtype=object)).tolist()).items())
        ),
        "prompt_group_contract": prompt_contract,
        "metrics": {},
        "gates": {"ready_for_grouped_folds_pass": False},
        "exact_prompt_group_violations": exact_violations[:20],
    }


if __name__ == "__main__":
    raise SystemExit(main())
