"""v0-rc1 canary — deterministic regression gate for v1c+scaffolds.

Drives ``v1_eval_pack_24records.py`` against the archived v0 checkpoint
with the v0 flag profile (per
``docs/releases/V0_RELEASE_CANDIDATE.md`` §3), then byte-diffs the
resulting JSONL against a frozen baseline.

Per CLAUDE.md ``feedback_aggregate_metrics_never_get_to_be_the_audit``:
the canary catches drift, it does NOT grade quality. Per
``V0_RELEASE_CANDIDATE.md`` §7: re-baseline only on explicit v0.N-rc
bump authorization.

Modes
-----
``--check`` (default):
    Run eval pack with v0 env, diff against ``v0_canary_baseline.jsonl``.
    Exit 0 on pass / 1 on drift / 2 on setup error.

``--freeze``:
    Run eval pack with v0 env, write current outputs as the new frozen
    baseline. Use ONLY when bumping the v0.N-rc tag with explicit user
    authorization.

Drift signals (any one fails the canary)
----------------------------------------
1. ``final_text`` byte-differs per record  → BYTE DRIFT
2. ``task_routed`` routing decision changes per record  → ROUTING DRIFT
3. ``hard_notation_count`` ≠ baseline (any leak when baseline 0)  → HARD NOTATION
4. ``jargon_count`` ≠ baseline (any leak when baseline 0)  → JARGON
5. Repair-log substitution counts or fire patterns drift  → REPAIR-LOG DRIFT
   (``n_omega_subs``, ``n_coef_subs``, ``n_var_subs``,
    ``rpm_seed_fired``, ``seed_decoder_text``, and the five nested log
    dicts: rpm_repair, rpm_retry, meta_logic_repair, generation_cleanup,
    fractal_repair)
6. Routing-tier fields (``compiled``, ``truncated``, ``quality_passed``,
    ``quality_failures``) differ  → ROUTING-TIER DRIFT

Exit codes
----------
0  canary passed
1  drift detected (report printed to stdout)
2  setup error (missing checkpoint / baseline / eval pack script)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "cas-synthetic" / "scripts"
DATA_DIR = REPO_ROOT / "cas-synthetic" / "data" / "path_d"

# Archived v0 checkpoint (per V0_RELEASE_CANDIDATE.md §2)
ARCHIVE_DIR = Path(r"D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep")

# Frozen baseline JSONL — committed to repo alongside this script.
BASELINE_PATH = DATA_DIR / "v0_canary_baseline.jsonl"

# Existing eval-pack driver (unchanged; we drive it via env vars).
EVAL_PACK_SCRIPT = SCRIPTS_DIR / "v1_eval_pack_24records.py"

# v0 flag profile — must match V0_RELEASE_CANDIDATE.md §3.
# USE_FRACTAL_DECODER="0" is explicit defensive pinning: v0 byte-equality
# requires the v1e Phase 1B fractal decoder OFF.
V0_ENV = {
    "USE_V1C_TASK_TOKENS": "1",
    "USE_V1C_RPM_SEED": "1",
    "USE_V1C_RPM_RETRY": "0",
    "USE_FRACTAL_DECODER": "0",
    "CHECKPOINT_DIR": str(ARCHIVE_DIR),
}

# Top-level fields that must match the baseline per-record.
DRIFT_FIELDS = (
    "final_text",
    "task_routed",
    "compiled",
    "truncated",
    "quality_passed",
    "quality_failures",
    "hard_notation_count",
    "jargon_count",
    "n_omega_subs",
    "n_coef_subs",
    "n_var_subs",
    "rpm_seed_fired",
    "seed_decoder_text",
    "omega_recovered_pre",
    "omega_recovered_post",
    "omega_total",
    "coef_recovered_pre",
    "coef_recovered_post",
    "coef_total",
    "n_steps",
)

# Nested log fields — entire dict must match.
REPAIR_LOG_FIELDS = (
    "rpm_repair_log",
    "rpm_retry_log",
    "meta_logic_repair_log",
    "generation_cleanup_log",
    "fractal_repair_log",
)


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def setup_checks() -> int:
    """Verify all required paths exist. Return 0 if OK, 2 on error."""
    if not ARCHIVE_DIR.exists():
        print(f"[error] archive dir not found: {ARCHIVE_DIR}", file=sys.stderr)
        print(
            "  Per V0_RELEASE_CANDIDATE.md §2, pull the checkpoint from "
            "pod into the archive dir.",
            file=sys.stderr,
        )
        return 2
    for name in ("model_final.pt", "tokenizer.json", "english_bpe.json",
                 "checkpoint_manifest.json"):
        p = ARCHIVE_DIR / name
        if not p.exists():
            print(f"[error] archive missing {name}: {p}", file=sys.stderr)
            return 2
    if not EVAL_PACK_SCRIPT.exists():
        print(
            f"[error] eval pack script not found: {EVAL_PACK_SCRIPT}",
            file=sys.stderr,
        )
        return 2
    return 0


def run_eval_pack() -> Path:
    """Invoke the eval-pack subprocess with v0 env. Return path to JSONL output."""
    env = {**os.environ, **V0_ENV}
    print(f"running eval pack with v0 env...")
    for k, v in V0_ENV.items():
        print(f"  {k}={v}")
    print()

    # Record the dir state BEFORE so we can identify the new file.
    before = set(DATA_DIR.glob("v1_eval_pack_24records_*.jsonl"))

    subprocess.run(
        [sys.executable, str(EVAL_PACK_SCRIPT)],
        env=env,
        cwd=str(REPO_ROOT),
        check=True,
    )

    after = set(DATA_DIR.glob("v1_eval_pack_24records_*.jsonl"))
    new = after - before
    if len(new) == 1:
        return new.pop()
    if not new:
        # Could happen if the eval-pack wrote no JSONL; fall back to
        # newest by mtime.
        candidates = sorted(after, key=lambda p: p.stat().st_mtime)
        if not candidates:
            raise RuntimeError("eval pack produced no JSONL output")
        return candidates[-1]
    # Multiple new files (unlikely) — pick the newest.
    return max(new, key=lambda p: p.stat().st_mtime)


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def diff_records(current: list[dict], baseline: list[dict]) -> list[tuple]:
    """Return list of (record_id, field, baseline_value, current_value)."""
    drifts: list[tuple] = []

    if len(current) != len(baseline):
        drifts.append(
            ("__overall__", "record_count", len(baseline), len(current))
        )
        return drifts

    cur_by_id = {r.get("record_id", f"row{i}"): r for i, r in enumerate(current)}
    base_by_id = {r.get("record_id", f"row{i}"): r for i, r in enumerate(baseline)}

    if set(cur_by_id) != set(base_by_id):
        missing = sorted(set(base_by_id) - set(cur_by_id))
        extra = sorted(set(cur_by_id) - set(base_by_id))
        if missing:
            drifts.append(
                ("__overall__", "missing_record_ids", missing, [])
            )
        if extra:
            drifts.append(
                ("__overall__", "extra_record_ids", [], extra)
            )
        return drifts

    for rid in sorted(cur_by_id):
        cur = cur_by_id[rid]
        base = base_by_id[rid]
        for f in DRIFT_FIELDS:
            if cur.get(f) != base.get(f):
                drifts.append((rid, f, base.get(f), cur.get(f)))
        for rf in REPAIR_LOG_FIELDS:
            if cur.get(rf) != base.get(rf):
                drifts.append((rid, rf, base.get(rf), cur.get(rf)))
    return drifts


def report_drifts(drifts: list[tuple], current_jsonl: Path) -> None:
    print()
    print("=" * 72)
    print(f"v0 canary FAILED: {len(drifts)} drift signal(s)")
    print("=" * 72)
    print()
    for rid, field, base_val, cur_val in drifts:
        base_repr = json.dumps(base_val, ensure_ascii=False, default=str)
        cur_repr = json.dumps(cur_val, ensure_ascii=False, default=str)
        # Truncate long values for readability; full diff is in the JSONL.
        if len(base_repr) > 240:
            base_repr = base_repr[:240] + "...[truncated]"
        if len(cur_repr) > 240:
            cur_repr = cur_repr[:240] + "...[truncated]"
        print(f"record={rid}  field={field}")
        print(f"  baseline: {base_repr}")
        print(f"  current:  {cur_repr}")
        print()
    print("=" * 72)
    print(f"current eval output preserved at: {current_jsonl}")
    print(f"frozen baseline at:               {BASELINE_PATH}")
    print()
    print("If this drift is INTENTIONAL (e.g. a v0.N-rc bump approved")
    print("by user), re-run with --freeze to update the baseline.")
    print("Otherwise treat this as a regression and investigate.")


def write_baseline(current: list[dict], current_jsonl: Path) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Strip volatile fields that aren't part of the canary contract.
    # The eval pack JSONL includes target/cas_expression/task_type/etc.
    # from the input record — keep those (they're stable across runs
    # because stratify_sample uses a fixed seed).
    with BASELINE_PATH.open("w", encoding="utf-8") as f:
        for rec in current:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print()
    print("=" * 72)
    print(f"v0 canary FROZEN baseline written")
    print("=" * 72)
    print(f"  baseline path: {BASELINE_PATH}")
    print(f"  record count:  {len(current)}")
    print(f"  source eval:   {current_jsonl}")
    print()
    print("Commit this baseline alongside any v0.N-rc tag bump.")
    print(
        "Per V0_RELEASE_CANDIDATE.md §7: the prior baseline should "
        "remain in git history."
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="v0-rc1 canary harness — deterministic regression gate",
    )
    ap.add_argument(
        "--freeze", action="store_true",
        help="Write current outputs as the new frozen baseline "
             "(use only on explicit v0.N-rc bump).",
    )
    args = ap.parse_args()

    print(f"v0 canary — {_utc_now_compact()}")
    print(f"  archive dir: {ARCHIVE_DIR}")
    print(f"  mode:        {'FREEZE' if args.freeze else 'CHECK'}")
    print()

    rc = setup_checks()
    if rc != 0:
        return rc

    current_jsonl = run_eval_pack()
    print()
    print(f"eval output: {current_jsonl}")
    current = load_jsonl(current_jsonl)
    print(f"  records: {len(current)}")

    if args.freeze:
        write_baseline(current, current_jsonl)
        return 0

    if not BASELINE_PATH.exists():
        print(
            f"[error] baseline not found: {BASELINE_PATH}",
            file=sys.stderr,
        )
        print(
            "  Run with --freeze first to generate the v0 baseline.",
            file=sys.stderr,
        )
        return 2

    baseline = load_jsonl(BASELINE_PATH)
    drifts = diff_records(current, baseline)

    if not drifts:
        print()
        print("=" * 72)
        print(f"v0 canary PASS: all {len(current)} records match baseline")
        print("=" * 72)
        return 0

    report_drifts(drifts, current_jsonl)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
