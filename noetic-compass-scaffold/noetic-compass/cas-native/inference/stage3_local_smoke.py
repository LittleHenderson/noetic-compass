"""One-record local smoke test for the Stage 3 trained model.

Step 3 of Codex's post-Stage-3 ordering. Closes the loop from "can load
the checkpoint" (Step 2) to "can actually generate on this machine."

Picks a deterministic record (default index 0) from
`cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.jsonl`, runs greedy
free-decode through the existing `SimplexCollator` + `decode_canary_pack`
path that the pod evaluator uses, and scores the generated text via
`per_record_recovery`. Saves a JSON report to `.tmp/` and prints a tight
human-readable summary.

Usage:
    python -m cas_native.inference.stage3_local_smoke
    python -m cas_native.inference.stage3_local_smoke --record-idx 0

Bounded scope (per `decisions.md` 2026-05-13T09:10Z): single-record CPU
smoke, no CLI surface, no chat REPL touch, no pod work.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import types
from collections import Counter
from pathlib import Path
from typing import Any, Optional

# Package indirection — mirrors inference/cas_cli.py so this module can be
# invoked from anywhere without `cas_native` being pip-installed. Tests
# go through conftest.py which already aliases the package; this block
# matters only for CLI invocation (`python -m cas_native.inference.stage3_local_smoke`).
_SCRIPT_DIR = Path(__file__).resolve()
_NOETIC_COMPASS_ROOT = _SCRIPT_DIR.parents[2]  # noetic-compass/
if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__path__ = [str(_NOETIC_COMPASS_ROOT / "cas-native")]
    sys.modules["cas_native"] = pkg
if str(_NOETIC_COMPASS_ROOT) not in sys.path:
    sys.path.insert(0, str(_NOETIC_COMPASS_ROOT))

import torch  # noqa: E402


# Project paths.
# This file:        tksCAS/noetic-compass-scaffold/noetic-compass/
#                          cas-native/inference/stage3_local_smoke.py
# parents[0] = inference/        parents[1] = cas-native/
# parents[2] = noetic-compass/   parents[3] = noetic-compass-scaffold/
# parents[4] = tksCAS/ (repo root)
_THIS = Path(__file__).resolve()
_CAS_NATIVE_ROOT = _THIS.parents[1]  # cas-native/
_REPO_ROOT = _THIS.parents[4]  # tksCAS/
_DEFAULT_DEV_PATH = (
    _REPO_ROOT / "cas-synthetic" / "data" / "path_d"
    / "rpm_copy_grounding_v2_dev.jsonl"
)
_DEFAULT_REPORT_DIR = _REPO_ROOT / ".tmp"


def _load_record(dev_path: Path, idx: int) -> dict[str, Any]:
    """Read the dev jsonl, return record at `idx`."""
    if not dev_path.exists():
        raise FileNotFoundError(
            f"Dev pack not found at {dev_path!s}. The smoke needs a known "
            f"CAS record to feed the model."
        )
    with dev_path.open("r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    if idx >= len(records):
        raise IndexError(
            f"record_idx={idx} out of range; dev pack has {len(records)} records"
        )
    return records[idx]


def _slot_trace_summary(trace: list[int]) -> dict[str, Any]:
    """Compress a per-position slot_type trace into a counts dict +
    longest STAGE_VAR run. STAGE_VAR id = 2 per simplex_collator constants."""
    if not trace:
        return {"length": 0, "counts": {}, "longest_stage_var_run": 0}
    counts = Counter(trace)
    longest = cur = 0
    STAGE_VAR_ID = 2
    for sid in trace:
        if sid == STAGE_VAR_ID:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    return {
        "length": len(trace),
        "counts": {str(k): int(v) for k, v in sorted(counts.items())},
        "longest_stage_var_run": int(longest),
    }


def run_stage3_local_smoke(
    record_idx: int = 0,
    dev_path: Optional[Path] = None,
    archive_root: Optional[Path] = None,
    max_new_tokens: int = 192,
    save_report: bool = True,
) -> dict[str, Any]:
    """Load the Stage 3 model from local archive and run one record through
    free-decode. Returns a smoke report dict with: archive hashes, target
    identifiers, generated text, recovery score, slot-trace summary,
    timing.

    Args:
        record_idx: which record in dev pack to feed (0 = deterministic,
            same record every smoke run).
        dev_path: override the default dev pack path.
        archive_root: override the default `D:\\tksCAS-archive\\` archive.
        max_new_tokens: matches the post-training eval setting.
        save_report: when True, dumps the report to
            `.tmp/stage3_local_smoke_<ts>.json` (NOT committed).

    Raises:
        RuntimeError from `load_stage3_local` on any hash mismatch.
        FileNotFoundError if the dev pack is missing.
    """
    from cas_native.inference.stage3_local_loader import load_stage3_local
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    from cas_native.evaluation.sample_decoder import decode_canary_pack
    from cas_native.evaluation.evaluate_candidate_e_stage2 import (
        per_record_recovery,
    )

    dev_path = dev_path or _DEFAULT_DEV_PATH

    t0 = time.time()
    bundle = load_stage3_local(archive_root=archive_root, device="cpu")
    load_secs = time.time() - t0

    record = _load_record(dev_path, record_idx)

    # The collator handles cas_prefix construction + lm_decoder_input_ids
    # + typed_slot_positions + typed_slot_source_idx. Same code path the
    # pod evaluator uses; no special-case branches here.
    collator = SimplexCollator(bundle.tokenizer, enable_simplex_aux=True)
    device = torch.device("cpu")

    t1 = time.time()
    decoded = decode_canary_pack(
        bundle.model, [record], collator, bundle.tokenizer,
        device=device, max_new_tokens=max_new_tokens,
        hard_typed_emission=False, copy_confidence_threshold=0.5,
        truncate_traces=False,
    )
    decode_secs = time.time() - t1
    entry = decoded[0]
    generated_text = entry.get("generated_text", "")

    recovery = per_record_recovery(record, generated_text)

    slot_trace = entry.get("slot_type_trace", []) or []
    slot_summary = _slot_trace_summary(slot_trace)

    report: dict[str, Any] = {
        "smoke_version": 1,
        "stage": "stage3_local_smoke",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dev_path": str(dev_path),
        "record_idx": record_idx,
        "record_id": record.get("id"),
        "task": record.get("v1mix_task_type"),
        "grammar_category": record.get("v1mix_grammar_category_or_error_class"),
        "archive_hashes": bundle.hash_report,
        "manifest_ablation_mode": bundle.manifest.get("ablation_mode"),
        "manifest_n_steps": bundle.manifest.get("config", {}).get("n_steps"),
        "prompt_text": record.get("prompt_text"),
        "cas_expression": record.get("cas_expression"),
        "canonical_identifiers": (
            record.get("eval_meta", {}).get("canonical_identifiers", [])
        ),
        "generated_text": generated_text,
        "n_tokens_generated": entry.get("n_tokens_generated"),
        "recovery": {
            "applicable": recovery["applicable"],
            "n_target": recovery["n_target"],
            "n_recovered": recovery["n_recovered"],
            "recovery_rate": recovery["recovery_rate"],
            "generated_identifiers": recovery["generated_identifiers"],
            "per_ident_hits": recovery["per_ident_hits"],
        },
        "slot_type_trace_summary": slot_summary,
        "timing_seconds": {
            "load": round(load_secs, 3),
            "decode": round(decode_secs, 3),
        },
        "gates": {
            "no_crash": True,  # if we got here, no crash
            "generated_non_empty": bool(generated_text),
            "ge_one_canonical_recovered": (
                recovery["applicable"] and recovery["n_recovered"] >= 1
            ),
            "lm_finite": True,  # decode_canary_pack would have raised on NaN
        },
    }
    report["gates"]["overall_pass"] = all(report["gates"].values())

    if save_report:
        _DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        report_path = _DEFAULT_REPORT_DIR / f"stage3_local_smoke_{ts}.json"
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        report["report_path"] = str(report_path)

    return report


def _print_summary(report: dict[str, Any]) -> None:
    """Human-readable single-page summary to stdout."""
    print(f"=== Stage 3 local smoke — {report['timestamp_utc']} ===")
    print(f"record:          {report['record_id']} (idx {report['record_idx']})")
    print(f"task / category: {report['task']} / {report['grammar_category']}")
    print(f"timing:          load={report['timing_seconds']['load']}s  "
          f"decode={report['timing_seconds']['decode']}s")
    print()
    print("--- prompt ---")
    print(report.get("prompt_text") or "(none)")
    print()
    print("--- gold cas_expression ---")
    print(report.get("cas_expression") or "(none)")
    print()
    print(f"--- canonical identifiers ({len(report['canonical_identifiers'])}) ---")
    for i, t in enumerate(report["canonical_identifiers"]):
        hit = report["recovery"]["per_ident_hits"].get(t, False)
        marker = "OK " if hit else "MISS"
        print(f"  [{marker}] {i}: {t}")
    print()
    print("--- generated text ---")
    print(report.get("generated_text") or "(empty)")
    print()
    rec = report["recovery"]
    print(f"recovery:        {rec['n_recovered']}/{rec['n_target']} = "
          f"{rec['recovery_rate']}")
    st = report["slot_type_trace_summary"]
    print(f"slot trace:      length={st['length']}  "
          f"longest_STAGE_VAR_run={st['longest_stage_var_run']}  "
          f"counts={st['counts']}")
    print()
    print("--- gates ---")
    for k, v in report["gates"].items():
        marker = "PASS" if v else "FAIL"
        print(f"  [{marker}] {k}")
    if rp := report.get("report_path"):
        print()
        print(f"full report: {rp}")


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Stage 3 local one-record smoke")
    p.add_argument("--record-idx", type=int, default=0,
                   help="Which dev record to feed (default 0, deterministic).")
    p.add_argument("--dev-path", type=str, default=str(_DEFAULT_DEV_PATH),
                   help=f"Dev jsonl path (default: {_DEFAULT_DEV_PATH}).")
    p.add_argument("--archive-root", type=str, default=None,
                   help="Override archive root (default: D:\\tksCAS-archive\\).")
    p.add_argument("--max-new-tokens", type=int, default=192)
    p.add_argument("--no-save-report", action="store_true",
                   help="Skip writing .tmp/stage3_local_smoke_*.json.")
    args = p.parse_args(argv)

    report = run_stage3_local_smoke(
        record_idx=args.record_idx,
        dev_path=Path(args.dev_path),
        archive_root=(Path(args.archive_root) if args.archive_root else None),
        max_new_tokens=args.max_new_tokens,
        save_report=not args.no_save_report,
    )
    _print_summary(report)
    return 0 if report["gates"]["overall_pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
