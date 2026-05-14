"""Stage 4A v0.2 merged-corpus builder.

Concatenates two already-vetted sources into one train-clean JSONL in the
NativeNLCollator schema used by `train_native_nl_gen.py`:

  1. Wave 2.5 (5,244 records, already inverted from English-description
     → CAS-target by Track 1's build_stage4_track1_corpus.py).
  2. Stage 4B pilot accepted records (Apache 2.0 OASST2 questions with
     Haiku-proposed + compiler-validated + judge-scored CAS), EXCLUDING
     the 9 records flagged by the copyright/long-quote detector. Net
     364 clean-train records.

Output schema is identical to the Wave 2.5 inverted records, so the
trainer can ingest both seamlessly:

    {
      "id": "<stable id>",
      "trace_id": "<seed_id or ext_seed_id>",
      "schema_version": "native_nl.v1",
      "tier": "tier1_sfe" | "tier2_external_q",
      "prompt_text": "<English>",
      "reply_text": "<CAS expression>",
      "cas_expression": "",   # intentionally empty — encoder must not see target
      "v1mix_task_type": "stage4_english_to_cas",
      "grammar_category": "<one of 10 categories>",
      "provenance": { ... }
    }

Per Codex audit `0e97599`: the 9 copyright-flagged accepts are
QUARANTINE, not train-clean. They are excluded from this output.

Per Codex audit `728be8c`: category spread is 4 in Stage 4B (not 5); the
combined corpus inherits Wave 2.5's full 10-category coverage so the
deliberate exception is documented in the v0.2 AUTHORIZED entry.

Mix ratio: NATURAL (~93/7 Wave 2.5 / Stage 4B), NO upsampling, per the
v0.2 AUTHORIZED entry. Stage 4B records appear once per epoch.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import pathlib
from collections import Counter

WAVE_2_5_INVERTED = "cas-synthetic/data/stage4/track1_merged_2026_05_14.jsonl"
STAGE_4B_ACCEPTED = "cas-synthetic/data/stage4b/stage4b_pilot_20260514T185757Z_accepted.jsonl"
DEFAULT_OUT = "cas-synthetic/data/stage4/track1_v02_merged_2026_05_14.jsonl"
DEFAULT_MANIFEST = "cas-synthetic/data/stage4/track1_v02_merged_2026_05_14.manifest.json"


def _utc_now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def invert_stage4b_record(src: dict, idx: int) -> dict | None:
    """Map a Stage 4B accepted record into NativeNLCollator schema.

    Field-mapping (mirrors build_stage4_track1_corpus.py):
        english_description -> prompt_text
        source_cas          -> reply_text (decoder target)
        cas_expression      -> ""  (encoder must not see target)
    """
    src_cas = (src.get("source_cas") or "").strip()
    eng = (src.get("english_description") or "").strip()
    if not src_cas or not eng:
        return None
    return {
        "id": f"stage4b_track2_{idx:06d}",
        "trace_id": src.get("seed_id") or f"stage4b_track2_trace_{idx:06d}",
        "schema_version": "native_nl.v1",
        "tier": "tier2_external_q",
        "prompt_text": eng,
        "reply_text": src_cas,
        "cas_expression": "",
        "v1mix_task_type": "stage4_english_to_cas",
        "grammar_category": src.get("grammar_category", ""),
        "provenance": {
            "source": "oasst2_via_haiku_sdg",
            "stage4b_pilot_id": src.get("stage4b_pilot_id", ""),
            "seed_id": src.get("seed_id", ""),
            "judge_score": (src.get("judge_result") or {}).get("score"),
            "model_used": src.get("model_used", ""),
            "repair_attempts": len(src.get("repair_attempts") or []),
            "copyright_flag": src.get("copyright_flag"),
            "external_question_dataset": (
                (src.get("external_question_provenance") or {}).get("dataset", "")
            ),
            "external_question_license": (
                (src.get("external_question_provenance") or {}).get("license", "")
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wave25-inverted", type=str, default=WAVE_2_5_INVERTED)
    p.add_argument("--stage4b-accepted", type=str, default=STAGE_4B_ACCEPTED)
    p.add_argument("--out", type=str, default=DEFAULT_OUT)
    p.add_argument("--manifest", type=str, default=DEFAULT_MANIFEST)
    args = p.parse_args(argv)

    out_records: list[dict] = []

    # ---- Layer 1: Wave 2.5 inverted (drop-in copy) ----
    wave_path = pathlib.Path(args.wave25_inverted)
    if not wave_path.exists():
        print(f"FATAL: missing Wave 2.5 inverted file: {wave_path}")
        return 2
    n_wave25 = 0
    with wave_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out_records.append(json.loads(line))
            n_wave25 += 1
    print(f"loaded Wave 2.5 inverted: {n_wave25} records from {wave_path}")

    # ---- Layer 2: Stage 4B accepted, drop copyright-quarantined ----
    s4b_path = pathlib.Path(args.stage4b_accepted)
    if not s4b_path.exists():
        print(f"FATAL: missing Stage 4B accepted file: {s4b_path}")
        return 2
    n_s4b_in = 0
    n_s4b_quarantined = 0
    n_s4b_invalid = 0
    n_s4b_kept = 0
    s4b_cat_counts: Counter[str] = Counter()
    with s4b_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            n_s4b_in += 1
            r = json.loads(line)
            if r.get("copyright_flag"):
                n_s4b_quarantined += 1
                continue
            inv = invert_stage4b_record(r, n_s4b_kept)
            if inv is None:
                n_s4b_invalid += 1
                continue
            out_records.append(inv)
            n_s4b_kept += 1
            s4b_cat_counts[inv["grammar_category"]] += 1
    print(f"Stage 4B accepted total: {n_s4b_in}")
    print(f"  quarantined (copyright): {n_s4b_quarantined}")
    print(f"  invalid (empty fields):  {n_s4b_invalid}")
    print(f"  kept (clean-train):       {n_s4b_kept}")

    # ---- Write merged corpus + manifest ----
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for r in out_records:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    h = hashlib.sha256()
    with out_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    sha = h.hexdigest()

    # Aggregate category coverage across both layers
    all_cat_counts: Counter[str] = Counter()
    for r in out_records:
        all_cat_counts[r.get("grammar_category", "?")] += 1

    manifest = {
        "schema_version": "stage4_v02_merged.v1",
        "created_at": _utc_now(),
        "output_file": str(out_path),
        "sha256": sha,
        "total_records": len(out_records),
        "n_wave25": n_wave25,
        "n_stage4b_in": n_s4b_in,
        "n_stage4b_quarantined": n_s4b_quarantined,
        "n_stage4b_invalid": n_s4b_invalid,
        "n_stage4b_kept": n_s4b_kept,
        "mix_ratio_wave25_pct": round(100 * n_wave25 / len(out_records), 2),
        "mix_ratio_stage4b_pct": round(100 * n_s4b_kept / len(out_records), 2),
        "category_spread_total": dict(all_cat_counts.most_common()),
        "category_spread_stage4b_layer": dict(s4b_cat_counts.most_common()),
        "source_wave25": args.wave25_inverted,
        "source_stage4b": args.stage4b_accepted,
        "rule": (
            "Wave 2.5 inverted records + Stage 4B clean-train (excludes "
            "copyright-quarantined). Natural mix ratio, no upsampling. "
            "Foreign answer text NEVER stored — only Haiku-proposed CAS that "
            "passed our compiler + judge."
        ),
        "policy_links": {
            "data_strategy_memory": "feedback_cas_native_data_strategy_2026_05_13.md (2026-05-14 refinement)",
            "stage4_spec": "docs/working/stage4_minimal_nl_training_spec_2026_05_13.md",
            "stage4b_pilot_findings": "docs/working/stage4b_pilot_2026_05_14/FINDINGS.md",
            "stage4_v02_authorized_entry": "docs/working/agent_exchange/decisions.md 2026-05-14T19:45Z",
        },
    }
    with pathlib.Path(args.manifest).open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)

    print()
    print(f"wrote {len(out_records)} merged records to {out_path}")
    print(f"sha256: {sha}")
    print(f"mix: {manifest['mix_ratio_wave25_pct']}% Wave 2.5 / {manifest['mix_ratio_stage4b_pct']}% Stage 4B")
    print()
    print("category spread (combined):")
    for cat, n in all_cat_counts.most_common():
        print(f"  {n:5d}  {cat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
