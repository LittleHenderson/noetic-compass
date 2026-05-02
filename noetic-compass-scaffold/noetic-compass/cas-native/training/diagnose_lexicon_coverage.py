#!/usr/bin/env python3
"""Lexicon-coverage diagnostic for canonical and paraphrase eval sets.

Re-tokenizes the held-out 1K canonical eval set and its paraphrase-augmented
3K with the *current* lexicon, then reports per-token provenance breakdown
(LEXICON / CAS_NOTATION / FALLBACK).

This is the no-GPU diagnostic that tests the OOV-bottleneck hypothesis:
if the paraphrase-eval failure (Session 43, 37.2% paraphrase exact vs 85.1%
canonical) is driven by the lexicon missing synonym surfaces, then expanding
the lexicon should reduce the FALLBACK fraction on paraphrase prompts more
than on canonical prompts.

Outputs at ``--out-dir``:

  - ``lexicon_coverage_report.json`` — full numerical breakdown.
  - ``lexicon_coverage_report.md`` — human-readable summary.

Run with the canonical Level 3 eval JSONL plus the lexicon checkpoint of
interest. Default lexicon is the freshly-built seed.
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path
from typing import Any, Iterable

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

_CAS_NATIVE_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _CAS_NATIVE_ROOT.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(_CAS_NATIVE_ROOT / "__init__.py")
    package.__path__ = [str(_CAS_NATIVE_ROOT)]
    sys.modules["cas_native"] = package

from cas_native.tokenizer import (
    CASLexicon,
    SOURCE_LABELS,
    load_seed_lexicon,
    summarize_token_provenance,
    tokenize,
)


# Inlined JSONL loader to keep this diagnostic torch-free; the canonical
# loader in structured_prediction_ingest.py transitively imports torch.nn.
def load_level3_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
            if limit is not None and len(records) >= limit:
                break
    return records


# SOURCE_LABELS imported from cas_native.tokenizer.provenance via the
# tokenizer package re-export.

# Inlined to keep this diagnostic torch-free. Mirror of
# evaluate_paraphrase_invariance.py PARAPHRASE_TEMPLATES /
# extract_recoverable_slots / make_paraphrase_records — keep in sync.
import copy as _copy  # local alias; only used by paraphrase generator below
_PARAPHRASE_TEMPLATES: tuple[str, ...] = (
    "Map this recoverable CAS slot reading into notation, then explain it briefly: {slots}.",
    "Please reconstruct the exact CAS expression from these stated slots: {slots}.",
    "As a CAS notation check, translate this slot list into the formal expression: {slots}.",
    "Given this recoverable structure, return the CAS notation and a concise explanation: {slots}.",
)
_KNOWN_SUFFIXES: tuple[str, ...] = (
    ". What notation should I use?",
    ". What is the precise notation?",
    ".",
)


def _extract_recoverable_slots(prompt: str) -> str:
    marker = "families:"
    start = prompt.find(marker)
    if start < 0:
        return prompt.strip()
    slots = prompt[start:].strip()
    for suffix in _KNOWN_SUFFIXES:
        if slots.endswith(suffix):
            slots = slots[: -len(suffix)].strip()
            break
    return slots


def _paraphrase_record(record: dict[str, Any], paraphrase_index: int) -> dict[str, Any]:
    template = _PARAPHRASE_TEMPLATES[paraphrase_index % len(_PARAPHRASE_TEMPLATES)]
    slots = _extract_recoverable_slots(str(record.get("user_prompt") or ""))
    out = _copy.deepcopy(record)
    out["base_id"] = record.get("id")
    out["paraphrase_index"] = paraphrase_index
    out["id"] = f"{record.get('id')}::para{paraphrase_index}"
    out["user_prompt"] = template.format(slots=slots)
    out["paraphrase_source"] = "deterministic_recoverable_slot_template"
    return out


def make_paraphrase_records(
    records: Iterable[dict[str, Any]], *, variants_per_record: int
) -> list[dict[str, Any]]:
    if variants_per_record <= 0:
        raise ValueError("variants_per_record must be positive")
    return [
        _paraphrase_record(record, paraphrase_index=index)
        for record in records
        for index in range(variants_per_record)
    ]


def diagnose(
    canonical_path: Path,
    *,
    variants_per_record: int = 3,
    lexicon: CASLexicon | None = None,
) -> dict[str, Any]:
    """Tokenize canonical + paraphrase eval prompts and return the report."""

    canonical_records = load_level3_jsonl(canonical_path)
    paraphrase_records = make_paraphrase_records(
        canonical_records, variants_per_record=variants_per_record
    )

    canonical_sequences = [
        tokenize(str(r.get("user_prompt") or ""), lexicon=lexicon)
        for r in canonical_records
    ]
    paraphrase_sequences = [
        tokenize(str(r.get("user_prompt") or ""), lexicon=lexicon)
        for r in paraphrase_records
    ]

    canonical_summary = summarize_token_provenance(
        canonical_sequences, records=canonical_records
    )
    paraphrase_summary = summarize_token_provenance(
        paraphrase_sequences, records=paraphrase_records
    )

    delta = {
        "signal_fraction_canonical": canonical_summary["overall_signal_fraction"],
        "signal_fraction_paraphrase": paraphrase_summary["overall_signal_fraction"],
        "delta_signal_fraction_pp": (
            paraphrase_summary["overall_signal_fraction"]
            - canonical_summary["overall_signal_fraction"]
        )
        * 100.0,
    }

    # Per-bucket delta — flag buckets where paraphrase coverage falls behind.
    bucket_delta: dict[str, dict[str, float]] = {}
    for bucket in sorted(
        set(canonical_summary["by_bucket"]) | set(paraphrase_summary["by_bucket"])
    ):
        c = canonical_summary["by_bucket"].get(bucket, {})
        p = paraphrase_summary["by_bucket"].get(bucket, {})
        c_frac = c.get("signal_fraction", 0.0)
        p_frac = p.get("signal_fraction", 0.0)
        bucket_delta[bucket] = {
            "canonical_signal_fraction": c_frac,
            "paraphrase_signal_fraction": p_frac,
            "delta_pp": (p_frac - c_frac) * 100.0,
        }

    lexicon_size = (lexicon or load_seed_lexicon()).size

    return {
        "lexicon_size": lexicon_size,
        "canonical_path": str(canonical_path),
        "variants_per_record": variants_per_record,
        "canonical": canonical_summary,
        "paraphrase": paraphrase_summary,
        "delta": delta,
        "by_bucket_delta": bucket_delta,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Lexicon Coverage Diagnostic")
    lines.append("")
    lines.append(f"- Lexicon size: **{report['lexicon_size']}**")
    lines.append(f"- Canonical eval: `{report['canonical_path']}`")
    lines.append(f"- Paraphrases per record: {report['variants_per_record']}")
    lines.append("")

    def _src_block(summary: dict[str, Any], title: str) -> None:
        lines.append(f"## {title}")
        lines.append("")
        lines.append(f"- Records: {summary['n_records']:,}")
        lines.append(f"- Total tokens: {summary['total_tokens']:,}")
        lines.append(
            f"- Signal-bearing tokens (LEXICON+CAS_NOTATION): "
            f"{summary['total_signal_bearing']:,} "
            f"({summary['overall_signal_fraction']*100:.1f}%)"
        )
        lines.append("")
        lines.append("| Source | Tokens | Fraction |")
        lines.append("|---|---:|---:|")
        for label in SOURCE_LABELS:
            n = summary["by_source"][label]
            f = summary["by_source_fraction"][label]
            lines.append(f"| {label} | {n:,} | {f*100:.2f}% |")
        lines.append("")

    _src_block(report["canonical"], "Canonical eval")
    _src_block(report["paraphrase"], "Paraphrase eval")

    d = report["delta"]
    lines.append("## Headline delta")
    lines.append("")
    lines.append(
        f"- Canonical signal fraction: **{d['signal_fraction_canonical']*100:.1f}%**"
    )
    lines.append(
        f"- Paraphrase signal fraction: **{d['signal_fraction_paraphrase']*100:.1f}%**"
    )
    sign = "+" if d["delta_signal_fraction_pp"] >= 0 else ""
    lines.append(
        f"- Δ paraphrase − canonical: **{sign}{d['delta_signal_fraction_pp']:.2f} pp**"
    )
    lines.append("")
    lines.append(
        "If the paraphrase signal fraction is meaningfully *below* canonical, "
        "the lexicon is the OOV bottleneck on paraphrase generalization. "
        "If they are close, the encoder — not the lexicon — is the next bottleneck."
    )
    lines.append("")

    lines.append("## By bucket")
    lines.append("")
    lines.append("| Bucket | Canonical signal % | Paraphrase signal % | Δ (pp) |")
    lines.append("|---|---:|---:|---:|")
    for bucket, entry in report["by_bucket_delta"].items():
        c = entry["canonical_signal_fraction"] * 100
        p = entry["paraphrase_signal_fraction"] * 100
        d_pp = entry["delta_pp"]
        sign = "+" if d_pp >= 0 else ""
        lines.append(f"| {bucket} | {c:.1f}% | {p:.1f}% | {sign}{d_pp:.2f} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--canonical",
        type=Path,
        required=True,
        help="Held-out canonical Level 3 eval JSONL (e.g., level3_recoverable_eval_1000.jsonl).",
    )
    parser.add_argument(
        "--variants-per-record",
        type=int,
        default=3,
        help="Paraphrase variants per canonical record (matches Session 43 setup).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Directory for lexicon_coverage_report.json + .md.",
    )
    args = parser.parse_args(argv)

    report = diagnose(
        args.canonical,
        variants_per_record=args.variants_per_record,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "lexicon_coverage_report.json"
    md_path = args.out_dir / "lexicon_coverage_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    delta_pp = report["delta"]["delta_signal_fraction_pp"]
    sign = "+" if delta_pp >= 0 else ""
    print(
        json.dumps(
            {
                "lexicon_size": report["lexicon_size"],
                "canonical_signal_pct": round(
                    report["canonical"]["overall_signal_fraction"] * 100, 2
                ),
                "paraphrase_signal_pct": round(
                    report["paraphrase"]["overall_signal_fraction"] * 100, 2
                ),
                "delta_pp": f"{sign}{delta_pp:.2f}",
                "report_json": str(json_path),
                "report_md": str(md_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
