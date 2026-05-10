"""Audit existing fractal training targets with the strict verifier.

Per user directive 2026-05-10 (post fractal_repair Phase 1 commit
``255b2a7``): inference-side fractal repair would be fake progress
because the v1c model's generated sequence is structurally unbound
from the source Φ<…>, not merely over-long. The next move is to
**clean the teacher signal** — find fractal training rows where
the English target itself doesn't preserve exact k-order/count.

This is a Stage-1 one-off audit. It runs ``verify_fractal_rendering``
over every fractal-shaped row in the v1 mix train/val/test files and
produces:

  - Per-row JSONL with the verifier's full log
  - Markdown summary report with aggregate stats by k-length, by
    notation, and by mismatch shape
  - Quarantine candidate list (rows that fail strict ordered-
    sequence validation)

The audit is read-only — it does not delete or rewrite any corpus
rows. The user's Stage 2 (quarantine or regenerate) is a separate
decision once this report lands.

Usage:
  python cas-synthetic/scripts/audit_fractal_targets.py

Outputs:
  cas-synthetic/data/path_d/fractal_target_audit_<timestamp>.jsonl
  cas-synthetic/data/path_d/fractal_target_audit_<timestamp>.md
"""
from __future__ import annotations

import json
import sys
import types
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD_ROOT = REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass"
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(SCAFFOLD_ROOT / "cas-native")]
sys.modules["cas_native"] = pkg
sys.path.insert(0, str(SCAFFOLD_ROOT))

from cas_native.inference.fractal_repair import (  # noqa: E402
    parse_fractal,
    verify_fractal_rendering,
)


CORPUS_FILES = [
    "cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl",
    "cas-synthetic/data/path_d/v1_mix_nlgen_val.jsonl",
    "cas-synthetic/data/path_d/v1_mix_nlgen_test.jsonl",
]
OUT_DIR = REPO_ROOT / "cas-synthetic/data/path_d"


def audit_one_record(rec: dict) -> dict | None:
    """Run the verifier on one corpus row. Returns audit row when the
    source is a fractal expression; ``None`` for non-fractal rows.

    Filters to cas_to_english only — fractal shapes also appear in
    invalid_to_explanation rows where the target is an error
    explanation, not a rendering of the sequence."""
    task_type = rec.get("v1mix_task_type") or rec.get("task_type") or ""
    if task_type and task_type != "cas_to_english":
        return None
    cas = rec.get("cas_expression", "")
    target = rec.get("reply_text", "")
    if not cas or not target:
        return None
    seq = parse_fractal(cas)
    if seq is None:
        return None
    _unchanged, log = verify_fractal_rendering(
        source_cas=cas, rendered=target,
    )
    return {
        "id": rec.get("id", ""),
        "source_split": rec.get("__source_split", ""),
        "cas_expression": cas,
        "target_text": target,
        "k_count": len(seq.k_values),
        "k_values": list(seq.k_values),
        "notation": seq.notation,
        "fractal_log": log.to_dict(),
        # Convenience fields for the markdown summary.
        "cardinality_matches": log.cardinality_matches,
        "sequence_matches": log.sequence_matches,
        "found_k_count": log.found_k_count,
        "found_k_sequence": list(log.found_k_sequence),
        "n_repeat_runs": len(log.repeat_runs),
    }


def run_audit() -> tuple[Path, Path, dict]:
    """Walk the corpus files, audit every fractal row, write JSONL +
    markdown report. Returns ``(jsonl_path, md_path, summary_dict)``."""
    audit_rows: list[dict] = []
    files_scanned: list[tuple[str, int, int]] = []  # (path, n_rows, n_fractal)

    for rel in CORPUS_FILES:
        path = REPO_ROOT / rel
        if not path.exists():
            files_scanned.append((rel, 0, 0))
            continue
        n_rows = 0
        n_fractal = 0
        split_name = path.stem.replace("v1_mix_nlgen_", "")
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                rec["__source_split"] = split_name
                n_rows += 1
                row = audit_one_record(rec)
                if row is not None:
                    audit_rows.append(row)
                    n_fractal += 1
        files_scanned.append((rel, n_rows, n_fractal))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = OUT_DIR / f"fractal_target_audit_{timestamp}.jsonl"
    md_path = OUT_DIR / f"fractal_target_audit_{timestamp}.md"

    with jsonl_path.open("w", encoding="utf-8") as fh:
        for row in audit_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = build_summary(audit_rows, files_scanned)
    md_path.write_text(render_markdown(summary, audit_rows), encoding="utf-8")
    return jsonl_path, md_path, summary


def build_summary(
    rows: list[dict], files: list[tuple[str, int, int]],
) -> dict:
    total = len(rows)
    if total == 0:
        return {"total": 0, "files": files}
    seq_match = sum(1 for r in rows if r["sequence_matches"])
    card_match_only = sum(
        1 for r in rows
        if r["cardinality_matches"] and not r["sequence_matches"]
    )
    cardinality_drift = sum(
        1 for r in rows if not r["cardinality_matches"]
    )
    by_k = Counter(r["k_count"] for r in rows)
    by_notation = Counter(r["notation"] for r in rows)
    by_split = Counter(r["source_split"] for r in rows)

    # Sequence-match rate by k-length bucket: confirm hypothesis that
    # long fractals are worse-gated.
    rate_by_k: dict[int, dict[str, int]] = {}
    for k in sorted(by_k):
        bucket = [r for r in rows if r["k_count"] == k]
        rate_by_k[k] = {
            "n": len(bucket),
            "sequence_match": sum(1 for r in bucket if r["sequence_matches"]),
            "cardinality_match": sum(
                1 for r in bucket if r["cardinality_matches"]
            ),
        }

    # Mojibake detection: count rows whose source CAS contains
    # known-corrupted bytes ("Î", "Â", or weird mojibake markers).
    mojibake_markers = ("Î¦", "Â", "âŸ¨", "âŸ©")
    mojibake_count = sum(
        1 for r in rows
        if any(m in r["cas_expression"] for m in mojibake_markers)
    )

    return {
        "total": total,
        "files": files,
        "sequence_match": seq_match,
        "cardinality_match_only": card_match_only,
        "cardinality_drift": cardinality_drift,
        "rate_by_k": rate_by_k,
        "by_notation": dict(by_notation),
        "by_split": dict(by_split),
        "mojibake_count": mojibake_count,
    }


def render_markdown(summary: dict, rows: list[dict]) -> str:
    """Build a human-readable audit report from the summary +
    a sample of worst offenders."""
    lines: list[str] = []
    lines.append("# Fractal target audit")
    lines.append("")
    lines.append(
        "Strict ordered-sequence validation of every fractal-shaped "
        "training row in the v1 mix corpus, using "
        "`cas_native.inference.fractal_repair.verify_fractal_rendering`."
    )
    lines.append("")
    lines.append("## Files scanned")
    lines.append("")
    lines.append("| File | Rows | Fractal rows |")
    lines.append("|---|---:|---:|")
    for path, n_rows, n_fractal in summary["files"]:
        lines.append(f"| `{path}` | {n_rows} | {n_fractal} |")
    lines.append("")

    if summary["total"] == 0:
        lines.append("No fractal rows found.")
        return "\n".join(lines)

    total = summary["total"]
    seq_match = summary["sequence_match"]
    card_only = summary["cardinality_match_only"]
    drift = summary["cardinality_drift"]
    pct = lambda n: f"{100*n/total:.1f}%"

    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- Total fractal rows: **{total}**")
    lines.append(
        f"- Strict sequence match (target preserves exact k-order/count): "
        f"**{seq_match} ({pct(seq_match)})**"
    )
    lines.append(
        f"- Cardinality match only (right count, wrong order): "
        f"{card_only} ({pct(card_only)})"
    )
    lines.append(
        f"- Cardinality drift (wrong count): {drift} ({pct(drift)})"
    )
    lines.append(f"- Mojibake-corrupted source CAS: {summary['mojibake_count']}")
    lines.append("")
    lines.append("## By k-length bucket")
    lines.append("")
    lines.append("| k | Rows | Sequence match | Cardinality match |")
    lines.append("|---:|---:|---:|---:|")
    for k, stat in summary["rate_by_k"].items():
        n = stat["n"]
        sm = stat["sequence_match"]
        cm = stat["cardinality_match"]
        sm_pct = f"{100*sm/n:.1f}%" if n else "—"
        cm_pct = f"{100*cm/n:.1f}%" if n else "—"
        lines.append(f"| {k} | {n} | {sm} ({sm_pct}) | {cm} ({cm_pct}) |")
    lines.append("")
    lines.append("## By notation")
    lines.append("")
    for notation, n in summary["by_notation"].items():
        lines.append(f"- `{notation}<…>` : {n} rows")
    lines.append("")
    lines.append("## By split")
    lines.append("")
    for split, n in summary["by_split"].items():
        lines.append(f"- {split}: {n} rows")
    lines.append("")

    # Worst offenders: 8 rows with highest mismatch_position count
    # plus longest k. Useful as a manual-review starting point.
    worst = sorted(
        (r for r in rows if not r["sequence_matches"]),
        key=lambda r: (
            -len(r["fractal_log"]["mismatch_positions"]),
            -r["k_count"],
        ),
    )[:8]
    if worst:
        lines.append("## Sample of worst offenders (manual review)")
        lines.append("")
        for r in worst:
            lines.append(f"**id**: `{r['id']}` ({r['source_split']})")
            lines.append("")
            lines.append(f"- source: `{r['cas_expression'][:120]}`")
            lines.append(f"- expected k: {r['k_values']}")
            lines.append(f"- found k: {r['found_k_sequence']}")
            lines.append(f"- target text: {r['target_text'][:240]}")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    print("Auditing fractal training targets with strict verifier...")
    jsonl_path, md_path, summary = run_audit()
    print()
    print(f"Audit JSONL: {jsonl_path}")
    print(f"Audit report: {md_path}")
    print()
    if summary["total"] == 0:
        print("No fractal rows found — exiting.")
        return 0
    total = summary["total"]
    seq = summary["sequence_match"]
    print(
        f"Headline: {seq}/{total} ({100*seq/total:.1f}%) fractal training "
        f"rows have targets that preserve exact k-order/count."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
