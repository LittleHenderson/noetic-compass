"""Stage 4B ingest — OpenAssistant OASST2 user-question-only loader.

Loads the OASST2 dataset from Hugging Face, filters to the first user-side
message (the question prompter wrote) for each English conversation, drops
ALL assistant/prompter reply text, and writes a clean JSONL pilot file.

Per user-ratified Stage 4 mix recommendation (2026-05-14): **external
questions only, foreign answer text NEVER enters training**. License-clean
per `docs/working/dataset_scout_consolidated_2026_05_07.md` (Apache 2.0).

Output schema (one record per line):

    {
      "id": "oasst2_q_NNNNNN",
      "question_text": "<the user-side English prompt>",
      "language": "en",
      "char_len": <int>,
      "source": {
        "dataset": "OpenAssistant/oasst2",
        "license": "Apache-2.0",
        "message_id": "<HF message_id>",
        "tree_id": "<HF message_tree_id>",
        "role": "prompter",
        "retrieved_at": "<UTC iso>"
      }
    }

Hard rules enforced:
- Skip non-English messages.
- Skip messages where `role != "prompter"`.
- Only the FIRST prompter message per conversation tree (no follow-up
  prompts whose context depends on a foreign assistant reply).
- Length sanity: 20 <= char_len <= 800. Skip overly short (low signal) /
  overly long (won't survive max_prompt_len=256 in collator) messages.
- Drop ALL reply_text / assistant_text / role:assistant fields. We never
  store the foreign answer.

Usage:
    pip install datasets   # one-time
    python cas-synthetic/scripts/ingest_oasst2_questions.py \\
        --out cas-synthetic/data/stage4b/oasst2_questions_pilot.jsonl \\
        --target 500 \\
        --seed 4242
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import pathlib
import random
import sys


def _utc_now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=str,
        default="cas-synthetic/data/stage4b/oasst2_questions_pilot.jsonl",
    )
    p.add_argument(
        "--manifest",
        type=str,
        default="",
        help="Manifest path (default: <out>.manifest.json)",
    )
    p.add_argument("--target", type=int, default=500)
    p.add_argument("--seed", type=int, default=4242)
    p.add_argument(
        "--split",
        type=str,
        default="train",
        choices=("train", "validation"),
    )
    p.add_argument("--min-chars", type=int, default=20)
    p.add_argument("--max-chars", type=int, default=800)
    args = p.parse_args(argv)

    try:
        from datasets import load_dataset
    except ImportError:
        print(
            "ERROR: `datasets` not installed. Run `pip install datasets` first.",
            file=sys.stderr,
        )
        return 2

    print(f"loading OpenAssistant/oasst2 split={args.split} (HF dataset)...")
    ds = load_dataset("OpenAssistant/oasst2", split=args.split)
    print(f"loaded: {len(ds)} raw messages")

    rng = random.Random(int(args.seed))

    # Group by message_tree_id; pick the FIRST prompter message per tree.
    by_tree: dict[str, dict] = {}
    n_non_en = 0
    n_non_prompter = 0
    n_no_text = 0
    for rec in ds:
        if rec.get("role") != "prompter":
            n_non_prompter += 1
            continue
        if rec.get("lang") != "en":
            n_non_en += 1
            continue
        text = (rec.get("text") or "").strip()
        if not text:
            n_no_text += 1
            continue
        tree_id = rec.get("message_tree_id") or rec.get("tree_id") or ""
        # Only keep first-turn (parent_id == None or empty) prompter messages.
        parent = rec.get("parent_id")
        if parent:
            continue
        if tree_id and tree_id in by_tree:
            continue
        by_tree[tree_id or rec.get("message_id", "")] = rec

    # Length filter.
    candidates: list[dict] = []
    n_too_short = 0
    n_too_long = 0
    for rec in by_tree.values():
        text = (rec.get("text") or "").strip()
        if len(text) < int(args.min_chars):
            n_too_short += 1
            continue
        if len(text) > int(args.max_chars):
            n_too_long += 1
            continue
        candidates.append(rec)

    print(
        f"filter stats: non_prompter={n_non_prompter} non_en={n_non_en} "
        f"no_text={n_no_text} too_short={n_too_short} too_long={n_too_long}"
    )
    print(f"candidates after filter: {len(candidates)}")

    # Shuffle deterministically and take target.
    rng.shuffle(candidates)
    selected = candidates[: int(args.target)]
    print(f"selected: {len(selected)}")

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    retrieved_at = _utc_now()
    with out_path.open("w", encoding="utf-8") as fh:
        for i, rec in enumerate(selected):
            text = (rec.get("text") or "").strip()
            out_rec = {
                "id": f"oasst2_q_{i:06d}",
                "question_text": text,
                "language": "en",
                "char_len": len(text),
                "source": {
                    "dataset": "OpenAssistant/oasst2",
                    "license": "Apache-2.0",
                    "message_id": rec.get("message_id", ""),
                    "tree_id": rec.get("message_tree_id") or rec.get("tree_id") or "",
                    "role": "prompter",
                    "retrieved_at": retrieved_at,
                },
            }
            fh.write(json.dumps(out_rec, ensure_ascii=False) + "\n")

    # sha256 of output for provenance.
    h = hashlib.sha256()
    with out_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    sha = h.hexdigest()

    manifest_path = pathlib.Path(args.manifest or str(out_path) + ".manifest.json")
    manifest = {
        "schema_version": "stage4b.oasst2.v1",
        "created_at": retrieved_at,
        "output_file": str(out_path),
        "sha256": sha,
        "n_records": len(selected),
        "target_requested": int(args.target),
        "seed": int(args.seed),
        "source": {
            "dataset": "OpenAssistant/oasst2",
            "split": args.split,
            "license": "Apache-2.0",
            "hf_url": "https://huggingface.co/datasets/OpenAssistant/oasst2",
            "scout_audit": "docs/working/dataset_scout_consolidated_2026_05_07.md (primary recommendation)",
        },
        "filters": {
            "lang": "en",
            "role": "prompter",
            "parent_id": "must_be_null (first-turn only)",
            "char_len_min": int(args.min_chars),
            "char_len_max": int(args.max_chars),
        },
        "filter_stats": {
            "n_non_prompter_dropped": n_non_prompter,
            "n_non_en_dropped": n_non_en,
            "n_no_text_dropped": n_no_text,
            "n_too_short_dropped": n_too_short,
            "n_too_long_dropped": n_too_long,
            "n_first_turn_prompter_candidates": len(candidates),
        },
        "rule": "external questions only; foreign answer text never stored",
    }
    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)

    print(f"wrote {len(selected)} records to {out_path}")
    print(f"sha256 {sha}")
    print(f"manifest {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
