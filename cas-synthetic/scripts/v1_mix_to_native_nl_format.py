"""Adapter: Path D v1 mix -> CAS-Native NL generation training format.

Reads ``v1_mix_train.jsonl`` (and optionally val/test) and emits records in
the schema consumed by ``train_native_nl_gen.py``:

  {
    "id":               "<row_id>",
    "trace_id":         "<source_id>",
    "conversation_id":  "v1mix_<task_type>",
    "turn_index":       0,
    "prompt_text":      "<task instruction + input>",
    "reply_text":       "<target>",
    "cas_expression":   "<canonical CAS payload>",
    "register":         "T"
  }

Prompt templates per task (designed to:
- give the model a clean task signal at training time
- be reusable verbatim at inference time
- avoid jargon contamination — task instructions describe the request in
  plain English):

  cas_to_english:
    "Describe the following CAS expression in plain English:\\n\\n{input}"

  invalid_to_explanation:
    "Explain in plain English why the following CAS expression is invalid:\\n\\n{input}"

cas_expression field:
- For cas_to_english: same as input (the CAS expression).
- For invalid_to_explanation: the invalid CAS expression alone, extracted
  from the input via regex. Falls back to the full input if extraction
  fails (sample_reply telemetry will still log it).

register field: defaulted to "T" (transcendent) since the v1 mix does not
carry per-record register labels. The trainer accepts T/A/f/E uniformly;
"T" is the v7.4-compatible default and matches the v0 corpus convention.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

_REPO_ROOT = Path(__file__).resolve().parents[2]


_INVALID_CAS_RX = re.compile(
    r"Invalid CAS expression \(error class: [^)]+\):\s*\n\s*(?P<cas>.+?)(?=\n\s*Compiler error message:)",
    re.DOTALL,
)


def _extract_invalid_cas(input_text: str) -> str:
    """Extract the invalid CAS expression from an invalid_to_explanation input.

    Falls back to the full input if the boundary regex fails.
    """
    m = _INVALID_CAS_RX.search(input_text)
    if m:
        return m.group("cas").strip()
    return input_text.strip()


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


PROMPT_TEMPLATES = {
    "cas_to_english":
        "Describe the following CAS expression in plain English:\n\n{input}",
    "invalid_to_explanation":
        "Explain in plain English why the following CAS expression is invalid:\n\n{input}",
}


def adapt_record(rec: dict[str, Any]) -> dict[str, Any] | None:
    task = rec["task_type"]
    template = PROMPT_TEMPLATES.get(task)
    if template is None:
        return None
    inp = rec["input"]
    prompt_text = template.format(input=inp)
    reply_text = rec["target"]
    if task == "cas_to_english":
        cas_expression = inp
    elif task == "invalid_to_explanation":
        cas_expression = _extract_invalid_cas(inp)
    else:
        cas_expression = inp

    return {
        "id": rec["row_id"],
        "trace_id": rec["meta"]["source_id"],
        "conversation_id": f"v1mix_{task}",
        "turn_index": 0,
        "prompt_text": prompt_text,
        "reply_text": reply_text,
        "cas_expression": cas_expression,
        "register": "T",
        "v1mix_task_type": task,
        "v1mix_grammar_category_or_error_class":
            rec["meta"]["grammar_category_or_error_class"],
        "v1mix_source_slice": rec["meta"]["source_slice"],
        "v1mix_sfe_certified": rec["meta"]["sfe_certified"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("--in-train", type=Path,
                   default=_REPO_ROOT / "cas-synthetic" / "data" / "path_d" / "v1_mix_train.jsonl")
    p.add_argument("--in-val", type=Path,
                   default=_REPO_ROOT / "cas-synthetic" / "data" / "path_d" / "v1_mix_val.jsonl")
    p.add_argument("--in-test", type=Path,
                   default=_REPO_ROOT / "cas-synthetic" / "data" / "path_d" / "v1_mix_test.jsonl")
    p.add_argument("--out-dir", type=Path,
                   default=_REPO_ROOT / "cas-synthetic" / "data" / "path_d")
    p.add_argument("--out-tag", type=str, default="v1_mix_nlgen")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary = {}
    for split_name, in_path in [
        ("train", args.in_train),
        ("val",   args.in_val),
        ("test",  args.in_test),
    ]:
        if not in_path.exists():
            sys.stderr.write(f"[warn] missing input: {in_path}\n")
            summary[split_name] = {"in": str(in_path), "out": None, "n_in": 0, "n_out": 0, "skipped": 0}
            continue
        out_path = args.out_dir / f"{args.out_tag}_{split_name}.jsonl"
        n_in = 0
        n_out = 0
        skipped = 0
        with out_path.open("w", encoding="utf-8") as fh:
            for rec in _read_jsonl(in_path):
                n_in += 1
                adapted = adapt_record(rec)
                if adapted is None:
                    skipped += 1
                    continue
                fh.write(json.dumps(adapted, ensure_ascii=False) + "\n")
                n_out += 1
        summary[split_name] = {
            "in": str(in_path.relative_to(_REPO_ROOT)),
            "out": str(out_path.relative_to(_REPO_ROOT)),
            "n_in": n_in, "n_out": n_out, "skipped": skipped,
        }

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
