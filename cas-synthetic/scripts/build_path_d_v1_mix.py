"""Path D Wave 4 — corpus aggregator for v1 training mix.

Aggregates promotion-grade Path D slices into a single training-ready
corpus with provenance, stratified splits, and a sanity-check report.

INCLUSION RULES (v1 mix, default):
  - cas_to_english:           Wave 2.5 SFE-certified accepted records
                               (main run + 2 backfills)
  - invalid_to_explanation:   Phase 1 audit-clean slot

EXCLUSION RULES (v1 mix, default):
  - english_to_cas:           Phase 1 100% verbatim-copy — needs SFE rebuild
  - invalid_to_corrected:     Phase 1 ~30% unrelated-correction — needs rebuild

Schema of each v1-mix row (single unified format across tasks):
  {
    "row_id":     "v1mix_<task>_<seq>",
    "task_type":  "cas_to_english" | "invalid_to_explanation",
    "input":      "<task-input string>",
    "target":     "<task-target string>",
    "split":      "train" | "val" | "test",
    "meta": {
      "source_slice":                    "wave2_5" | "phase1",
      "source_id":                       "<seed_id or sample_id>",
      "grammar_category_or_error_class": "<category>",
      "source_path":                     "<file>",
      "sfe_certified":                   true | false,
      "sfe_tries":                       null | int
    }
  }

Splits are stratified by (task_type, grammar_category_or_error_class) with
a deterministic seed. Strata smaller than `--min-stratum-size` go entirely
to train (no val/test split for them) and are listed in the manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for ln, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                sys.stderr.write(f"[warn] {path}:{ln} skipping malformed line: {e}\n")


_INV_EXPLAIN_PAYLOAD_RX = __import__("re").compile(
    r"<<USER>>\s*\n(?P<payload>.*?)(?=\n\nWrite a concise)",
    __import__("re").DOTALL,
)


def _extract_invalid_to_explanation_payload(prompt: str) -> str:
    """Extract just the task payload from a phase 1 invalid_to_explanation prompt.

    Phase 1 prompts are formatted as:
        <<SYSTEM>>
        ... system instructions ...
        <<USER>>
        Invalid CAS expression (error class: <class>):

            <invalid CAS>

        Compiler error message:

            <compiler error>

        Write a concise, plain-English description aimed at a curious adult reader. ...
        STRICT anti-drift rules: ...

    We strip the user-block instructions and keep just the
    "Invalid CAS expression ... Compiler error ..." payload. This makes
    the v1-mix input symmetric with cas_to_english (raw payload only;
    the trainer wraps with a task-specific prompt during training).

    Falls back to the full <<USER>> block if the expected payload boundary
    is not found, so unanticipated formats degrade safely.
    """
    if not isinstance(prompt, str):
        return str(prompt)
    m = _INV_EXPLAIN_PAYLOAD_RX.search(prompt)
    if m:
        return m.group("payload").strip()
    # Fallback: keep everything after <<USER>>
    marker = "<<USER>>"
    idx = prompt.find(marker)
    if idx < 0:
        return prompt.strip()
    return prompt[idx + len(marker):].lstrip("\n").rstrip()


def load_wave2_5_cas_to_english(paths: list[Path]) -> list[dict[str, Any]]:
    """Load Wave 2.5 SFE-certified cas_to_english accepted records.

    One v1-mix row per accepted record. SFE-certified = True.
    """
    out: list[dict[str, Any]] = []
    for p in paths:
        if not p.exists():
            sys.stderr.write(f"[warn] missing wave2.5 file: {p}\n")
            continue
        for r in _read_jsonl(p):
            seed_id = r["seed_id"]
            cas = r["source_cas"]
            english = r["english_description"]
            cat = r.get("grammar_category", "unknown")
            tries = r.get("sfe_tries")
            out.append({
                "task_type": "cas_to_english",
                "input": cas,
                "target": english,
                "meta": {
                    "source_slice": "wave2_5",
                    "source_id": seed_id,
                    "grammar_category_or_error_class": cat,
                    "source_path": str(p.relative_to(_REPO_ROOT)) if p.is_absolute() else str(p),
                    "sfe_certified": True,
                    "sfe_tries": tries,
                },
            })
    return out


def load_phase1_invalid_to_explanation(path: Path) -> list[dict[str, Any]]:
    """Load phase 1 invalid_to_explanation slot from the aggregate file.

    Filters to slot=='invalid_to_explanation'. SFE-certified = False
    (phase 1 didn't use SFE; this slot was clean per phase 1 audit).
    """
    out: list[dict[str, Any]] = []
    if not path.exists():
        sys.stderr.write(f"[warn] missing phase1 aggregate: {path}\n")
        return out
    for r in _read_jsonl(path):
        if r.get("slot") != "invalid_to_explanation":
            continue
        prompt = r.get("prompt_to_model", "")
        payload = _extract_invalid_to_explanation_payload(prompt) if isinstance(prompt, str) else str(prompt)
        target = r.get("raw_response", "")
        cat = r.get("source_grammar_category_or_error_class", "unknown")
        sample_id = r.get("sample_id", r.get("source_id", ""))
        out.append({
            "task_type": "invalid_to_explanation",
            "input": payload,
            "target": target,
            "meta": {
                "source_slice": "phase1",
                "source_id": sample_id,
                "grammar_category_or_error_class": cat,
                "source_path": str(path.relative_to(_REPO_ROOT)) if path.is_absolute() else str(path),
                "sfe_certified": False,
                "sfe_tries": None,
            },
        })
    return out


def dedupe_within_task(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Dedupe within a task by source_id. First occurrence wins.

    Returns (deduped_rows, duplicates_dropped).
    """
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    dups = 0
    for r in rows:
        key = r["meta"]["source_id"]
        if key in seen:
            dups += 1
            continue
        seen.add(key)
        out.append(r)
    return out, dups


def stratified_split(
    rows: list[dict[str, Any]],
    *,
    train_frac: float,
    val_frac: float,
    test_frac: float,
    min_stratum_size: int,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Stratified train/val/test split by (task_type, grammar_category).

    Strata smaller than ``min_stratum_size`` go entirely to train. This
    guarantees val/test only contain strata where we can sample meaningfully.

    Returns (rows_with_split_assigned, split_diagnostics).
    """
    if abs(train_frac + val_frac + test_frac - 1.0) > 1e-6:
        raise ValueError(
            f"split fractions must sum to 1.0, got "
            f"{train_frac}+{val_frac}+{test_frac}={train_frac+val_frac+test_frac}"
        )
    rng = random.Random(seed)
    by_stratum: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        key = (r["task_type"], r["meta"]["grammar_category_or_error_class"])
        by_stratum[key].append(r)

    diag: dict[str, Any] = {
        "min_stratum_size": min_stratum_size,
        "seed": seed,
        "fractions": {"train": train_frac, "val": val_frac, "test": test_frac},
        "strata": [],
        "small_strata_train_only": [],
    }
    for (task, cat), bucket in sorted(by_stratum.items()):
        n = len(bucket)
        rng.shuffle(bucket)
        if n < min_stratum_size:
            for r in bucket:
                r["split"] = "train"
            diag["small_strata_train_only"].append({
                "task_type": task,
                "grammar_category_or_error_class": cat,
                "n": n,
            })
            diag["strata"].append({
                "task_type": task,
                "grammar_category_or_error_class": cat,
                "n": n,
                "train": n, "val": 0, "test": 0,
            })
            continue
        n_test = max(1, int(round(n * test_frac)))
        n_val = max(1, int(round(n * val_frac)))
        n_train = n - n_test - n_val
        if n_train <= 0:
            n_train = 1
            if n_val > 1:
                n_val -= 1
            else:
                n_test -= 1
        # Assign in order: train | val | test
        for i, r in enumerate(bucket):
            if i < n_train:
                r["split"] = "train"
            elif i < n_train + n_val:
                r["split"] = "val"
            else:
                r["split"] = "test"
        diag["strata"].append({
            "task_type": task,
            "grammar_category_or_error_class": cat,
            "n": n,
            "train": n_train, "val": n_val, "test": n_test,
        })
    return rows, diag


def assign_row_ids(rows: list[dict[str, Any]]) -> None:
    counters: dict[str, int] = defaultdict(int)
    for r in rows:
        idx = counters[r["task_type"]]
        r["row_id"] = f"v1mix_{r['task_type']}_{idx:06d}"
        counters[r["task_type"]] += 1


def stable_hash_inclusion_rules(rules: dict[str, Any]) -> str:
    payload = json.dumps(rules, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def sanity_checks(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Light corpus sanity checks for the manifest. Not a quality gate.

    Returns counts and diagnostic flags. Per the project rule: do not
    leave the v1 mix unaudited at the slice level — but heavy quality
    is the SFE pipeline's responsibility upstream, not this aggregator.
    """
    # Slot balance
    by_task = Counter(r["task_type"] for r in rows)

    # Token-length proxies (chars; trainer can tokenize properly)
    def char_stats(values: list[int]) -> dict[str, float]:
        if not values:
            return {"n": 0, "min": 0, "max": 0, "mean": 0.0, "p50": 0, "p95": 0}
        s = sorted(values)
        return {
            "n": len(s),
            "min": s[0],
            "max": s[-1],
            "mean": sum(s) / len(s),
            "p50": s[len(s) // 2],
            "p95": s[max(0, int(len(s) * 0.95) - 1)],
        }

    inputs_by_task: dict[str, list[int]] = defaultdict(list)
    targets_by_task: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        inputs_by_task[r["task_type"]].append(len(r["input"]))
        targets_by_task[r["task_type"]].append(len(r["target"]))

    char_stats_per_task = {
        t: {
            "input_chars": char_stats(inputs_by_task[t]),
            "target_chars": char_stats(targets_by_task[t]),
        }
        for t in by_task
    }

    # CAS-leakage in cas_to_english TARGET (must be 0)
    import re
    HARD_RX = re.compile(r"\^\d|\bF[1-7]\b|StateCluster|RelationCluster|NoeticCluster|[∩∪∖∈⊂⊆⊃⊇]|→")
    JARGON_RX = re.compile(r"\boperator(s|ial|ially)?\b|\bnoetic(s)?\b|\bcognitive operation", re.I)
    cas_to_eng_target_hard_hits = 0
    cas_to_eng_target_jargon_hits = 0
    for r in rows:
        if r["task_type"] != "cas_to_english":
            continue
        if HARD_RX.search(r["target"]):
            cas_to_eng_target_hard_hits += 1
        if JARGON_RX.search(r["target"]):
            cas_to_eng_target_jargon_hits += 1

    # Verbatim input==target (would be a parrot regression)
    verbatim = sum(1 for r in rows if r["input"].strip() == r["target"].strip())

    # source_id collision check across the full mix (post-dedupe should be 0
    # within task; cross-task collisions are fine because seeds and inv_seeds
    # share namespaces by construction — so we report cross-task only)
    by_task_sids: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        by_task_sids[r["task_type"]].add(r["meta"]["source_id"])
    cross_task_overlap_sids = (
        len(by_task_sids.get("cas_to_english", set())
            & by_task_sids.get("invalid_to_explanation", set()))
    )

    return {
        "total_rows": len(rows),
        "task_distribution": dict(by_task),
        "char_stats_per_task": char_stats_per_task,
        "cas_to_english_target_hard_notation_hits": cas_to_eng_target_hard_hits,
        "cas_to_english_target_jargon_hits": cas_to_eng_target_jargon_hits,
        "verbatim_input_equals_target": verbatim,
        "cross_task_source_id_overlap": cross_task_overlap_sids,
    }


def write_split(rows: list[dict[str, Any]], split: str, out_path: Path) -> int:
    n = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for r in rows:
            if r["split"] != split:
                continue
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("--out-dir", type=Path,
                   default=_REPO_ROOT / "cas-synthetic" / "data" / "path_d")
    p.add_argument("--train-frac", type=float, default=0.90)
    p.add_argument("--val-frac", type=float, default=0.05)
    p.add_argument("--test-frac", type=float, default=0.05)
    p.add_argument("--min-stratum-size", type=int, default=20,
                   help="strata with fewer than this many rows go entirely "
                        "to train (no val/test split for them)")
    p.add_argument("--seed", type=int, default=20260509,
                   help="deterministic split seed")
    p.add_argument("--mix-tag", type=str, default="v1",
                   help="output filename tag (e.g., v1 -> v1_mix_train.jsonl)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    inclusion_rules = {
        "version": "v1_path_d_2026_05_08",
        "slices_included": [
            {
                "slice_id": "wave2_5_cas_to_english",
                "task_type": "cas_to_english",
                "files": [
                    "cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_20260508T203848Z.jsonl",
                    "cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_20260509T002355Z.jsonl",
                    "cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_20260509T002541Z.jsonl",
                ],
                "sfe_certified": True,
                "rationale": "Wave 2.5 SFE-gated, all 4 promotion gates passed, human review PASS.",
            },
            {
                "slice_id": "phase1_invalid_to_explanation",
                "task_type": "invalid_to_explanation",
                "files": [
                    "cas-synthetic/data/path_d/wave3_phase1_aggregate_20260508.jsonl",
                ],
                "sfe_certified": False,
                "rationale": "Phase 1 audit (2026-05-08) flagged this slot CLEAN. The other 3 phase 1 slots are NEEDS_REWORK.",
            },
        ],
        "slices_excluded": [
            {
                "slice_id": "phase1_cas_to_english",
                "reason": "Replaced by wave2_5_cas_to_english (SFE-gated, structurally certified).",
            },
            {
                "slice_id": "phase1_english_to_cas",
                "reason": "Phase 1 audit found 100% verbatim-copy. Needs SFE-equivalent rebuild before inclusion.",
            },
            {
                "slice_id": "phase1_invalid_to_corrected",
                "reason": "Phase 1 audit found ~30% unrelated-correction. Needs SFE-equivalent rebuild before inclusion.",
            },
        ],
    }
    rules_hash = stable_hash_inclusion_rules(inclusion_rules)

    # Load slices
    wave2_5_paths = [_REPO_ROOT / Path(p) for p in
                     [s["files"] for s in inclusion_rules["slices_included"]
                      if s["slice_id"] == "wave2_5_cas_to_english"][0]]
    phase1_path = _REPO_ROOT / Path(
        [s["files"] for s in inclusion_rules["slices_included"]
         if s["slice_id"] == "phase1_invalid_to_explanation"][0][0]
    )

    rows_c2e = load_wave2_5_cas_to_english(wave2_5_paths)
    rows_inv = load_phase1_invalid_to_explanation(phase1_path)

    # Per-task dedupe
    rows_c2e, dups_c2e = dedupe_within_task(rows_c2e)
    rows_inv, dups_inv = dedupe_within_task(rows_inv)

    rows = rows_c2e + rows_inv

    # Splits
    rows, split_diag = stratified_split(
        rows,
        train_frac=args.train_frac,
        val_frac=args.val_frac,
        test_frac=args.test_frac,
        min_stratum_size=args.min_stratum_size,
        seed=args.seed,
    )

    # Row IDs (deterministic by current order, which is loaded order)
    assign_row_ids(rows)

    # Sanity
    sanity = sanity_checks(rows)

    # Write splits
    tag = args.mix_tag
    out_train = out_dir / f"{tag}_mix_train.jsonl"
    out_val = out_dir / f"{tag}_mix_val.jsonl"
    out_test = out_dir / f"{tag}_mix_test.jsonl"
    n_train = write_split(rows, "train", out_train)
    n_val = write_split(rows, "val", out_val)
    n_test = write_split(rows, "test", out_test)

    # Manifest
    timestamp = _utc_now_compact()
    manifest_path = out_dir / f"{tag}_mix_manifest_{timestamp}.json"
    manifest = {
        "tag": tag,
        "created_at": _utc_now_iso(),
        "inclusion_rules": inclusion_rules,
        "inclusion_rules_hash": rules_hash,
        "split_seed": args.seed,
        "split_fractions": {
            "train": args.train_frac, "val": args.val_frac, "test": args.test_frac,
        },
        "min_stratum_size": args.min_stratum_size,
        "loaded_counts": {
            "cas_to_english_raw": len(rows_c2e) + dups_c2e,
            "cas_to_english_after_dedupe": len(rows_c2e),
            "cas_to_english_dups_dropped": dups_c2e,
            "invalid_to_explanation_raw": len(rows_inv) + dups_inv,
            "invalid_to_explanation_after_dedupe": len(rows_inv),
            "invalid_to_explanation_dups_dropped": dups_inv,
            "total_after_dedupe": len(rows),
        },
        "split_counts": {
            "train": n_train, "val": n_val, "test": n_test,
        },
        "split_diagnostics": split_diag,
        "sanity": sanity,
        "outputs": {
            "train": str(out_train.relative_to(_REPO_ROOT)),
            "val": str(out_val.relative_to(_REPO_ROOT)),
            "test": str(out_test.relative_to(_REPO_ROOT)),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                             encoding="utf-8")

    # Console summary
    summary = {
        "manifest": str(manifest_path.relative_to(_REPO_ROOT)),
        "total_rows": len(rows),
        "split": {"train": n_train, "val": n_val, "test": n_test},
        "task_distribution": sanity["task_distribution"],
        "rules_hash": rules_hash,
        "sanity_red_flags": {
            "cas_to_english_target_hard_notation_hits": sanity["cas_to_english_target_hard_notation_hits"],
            "cas_to_english_target_jargon_hits": sanity["cas_to_english_target_jargon_hits"],
            "verbatim_input_equals_target": sanity["verbatim_input_equals_target"],
        },
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
