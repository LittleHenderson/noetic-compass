"""Stage 4 Track 1 corpus inverter.

Reads Wave 2.5 + Wave 3 layer3 records (CAS-to-English direction:
``source_cas`` + ``english_description``) and emits records under the
NativeNLCollator schema for the inverted Stage 4 task (English to CAS):

    prompt_text     <- english_description    (encoder input)
    reply_text      <- source_cas             (decoder target = emit CAS as text)
    cas_expression  <- ""                     (EMPTY on purpose — prevents the
                                               encoder from seeing the target
                                               via cas_prefix_ids, which would
                                               make the task trivially copyable)

Dedupes by ``seed_id`` first, then by exact-match ``english_description``,
then drops any record whose English side appears verbatim as a
``user_prompt`` in the held-out eval set.

Writes one JSONL output + a manifest with sha256 and per-source counts.
NO LLM calls. NO foreign text in any target. Pure local file transform.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import pathlib
from collections import Counter

# Source files audited 2026-05-14 (commit 4c48e11).
WAVE_2_5_FILES: list[str] = [
    "cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_20260508T203848Z.jsonl",
    "cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_20260509T002355Z.jsonl",
    "cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_20260509T002541Z.jsonl",
]
WAVE_3_LAYER3: str = (
    "cas-synthetic/data/path_d/wave3_step2_5_layer3_clean_20260508T110453Z.jsonl"
)
EVAL_FILE: str = (
    "cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl"
)

DEFAULT_OUT = "cas-synthetic/data/stage4/track1_merged_2026_05_14.jsonl"
DEFAULT_MANIFEST = "cas-synthetic/data/stage4/track1_merged_2026_05_14.manifest.json"


def _load_eval_prompts(path: str) -> set[str]:
    p = pathlib.Path(path)
    out: set[str] = set()
    if not p.exists():
        return out
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            v = r.get("user_prompt")
            if isinstance(v, str) and v.strip():
                out.add(v.strip())
    return out


def to_stage4_record(src: dict, idx: int, src_file: str) -> dict | None:
    src_cas = (src.get("source_cas") or "").strip()
    eng = (src.get("english_description") or "").strip()
    if not src_cas or not eng:
        return None
    return {
        "id": f"stage4_track1_{idx:06d}",
        "trace_id": src.get("seed_id") or f"stage4_track1_trace_{idx:06d}",
        "schema_version": "native_nl.v1",
        "tier": "tier1_sfe",
        "prompt_text": eng,
        "reply_text": src_cas,
        "cas_expression": "",
        "v1mix_task_type": "stage4_english_to_cas",
        "grammar_category": src.get("grammar_category", ""),
        "provenance": {
            "source_file": src_file,
            "seed_id": src.get("seed_id", ""),
            "wave2_5_run_id": src.get("wave2_5_run_id", ""),
            "model_used": src.get("model_used", ""),
            "sfe_tries": src.get("sfe_tries", 0),
            "validators_passed": src.get("validators_passed", []),
            "post_filter_validators_passed": src.get("post_filter_validators_passed", []),
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=str, default=DEFAULT_OUT)
    p.add_argument("--manifest", type=str, default=DEFAULT_MANIFEST)
    p.add_argument(
        "--no-eval-dedupe",
        action="store_true",
        help="Skip dedupe against the held-out eval set (NOT recommended).",
    )
    args = p.parse_args(argv)

    eval_prompts: set[str] = set() if args.no_eval_dedupe else _load_eval_prompts(EVAL_FILE)

    seen_seeds: set[str] = set()
    seen_english: set[str] = set()
    file_counts: Counter[str] = Counter()
    cat_counts: Counter[str] = Counter()
    out_records: list[dict] = []
    eval_dedupe_drops = 0
    empty_drops = 0

    sources = [(fp, False) for fp in WAVE_2_5_FILES] + [(WAVE_3_LAYER3, True)]
    for fp, _is_layer3 in sources:
        srcp = pathlib.Path(fp)
        if not srcp.exists():
            print(f"WARN missing source: {fp}")
            continue
        with srcp.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sid = r.get("seed_id")
                if sid and sid in seen_seeds:
                    continue
                eng = (r.get("english_description") or "").strip()
                if not eng or not r.get("source_cas"):
                    empty_drops += 1
                    continue
                if eng in eval_prompts:
                    eval_dedupe_drops += 1
                    continue
                if eng in seen_english:
                    continue
                if sid:
                    seen_seeds.add(sid)
                seen_english.add(eng)
                rec = to_stage4_record(r, len(out_records), srcp.name)
                if rec is None:
                    empty_drops += 1
                    continue
                out_records.append(rec)
                file_counts[srcp.name] += 1
                cat_counts[r.get("grammar_category", "?")] += 1

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for r in out_records:
            fh.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")

    h = hashlib.sha256()
    with out_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    sha = h.hexdigest()

    manifest = {
        "schema_version": "stage4.track1.v1",
        "created_at": _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output_file": str(out_path),
        "sha256": sha,
        "total_records": len(out_records),
        "per_source_file_counts": dict(file_counts),
        "per_grammar_category_counts": dict(cat_counts.most_common()),
        "eval_dedupe_drops": eval_dedupe_drops,
        "empty_or_invalid_drops": empty_drops,
        "task_type": "stage4_english_to_cas",
        "field_inversion": (
            "english_description -> prompt_text (encoder); "
            "source_cas -> reply_text (decoder target); "
            "cas_expression intentionally empty to prevent target leakage"
        ),
        "rule": (
            "no foreign answer text in any target; all targets are own "
            "Path D Wave 2.5 + Wave 3 SFE CAS expressions"
        ),
        "source_files": [str(pathlib.Path(fp)) for fp in WAVE_2_5_FILES + [WAVE_3_LAYER3]],
        "eval_dedupe_against": EVAL_FILE if not args.no_eval_dedupe else None,
    }
    with pathlib.Path(args.manifest).open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)

    print(f"Wrote {len(out_records)} records to {out_path}")
    print(f"SHA256: {sha}")
    print(f"Eval-dedupe drops: {eval_dedupe_drops}")
    print(f"Empty/invalid drops: {empty_drops}")
    print(f"\nPer-source file:")
    for k, v in file_counts.most_common():
        print(f"  {v:5d}  {k}")
    print(f"\nPer-grammar-category:")
    for k, v in cat_counts.most_common():
        print(f"  {v:5d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
