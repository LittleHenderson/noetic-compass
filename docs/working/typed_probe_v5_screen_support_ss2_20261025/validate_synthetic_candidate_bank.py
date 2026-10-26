#!/usr/bin/env python3
"""Second-pass structural check for the SS2 synthetic candidate bank."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = HERE / "candidate_bank_ss2_400_20261025.jsonl"
BUILDER = HERE / "build_synthetic_candidate_bank.py"
BUILDER_REPORT = HERE / "candidate_bank_validation_20261025.json"
PRIOR_BANK = HERE.parent / "typed_probe_v5_stage_s_continuation_retry5_20261025" / "candidate_bank_v4_120_20260610.jsonl"
PRIOR_SOURCE = Path(r"D:\tksCAS-archive\qwen_confirmatory_20260610\injected_overt_combined_240_20260609.jsonl")
EXPECTED_PRIOR_BANK = "4a6b73ecd764fce0373cdb7ce5500b00ea0dc9a4fca6be3e2a8761857b57f32f"
EXPECTED_PRIOR_SOURCE = "0d22f5e896075d8a89d935a87812da53338d59184d70f7bc46c74110477ea7fa"
DOMAINS = {
    "code_comment", "document_qa", "email", "faq", "meeting_notes",
    "news", "product_review", "recipe", "support_ticket", "travel",
}
PAYLOAD_CLASSES = {f"ext_{i}" for i in range(8)}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[\w]+", value, re.UNICODE))


def prior_contexts(path: Path, expected_hash: str) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"required comparison source is absent: {path}")
    if file_hash(path) != expected_hash:
        raise ValueError(f"comparison source hash mismatch: {path}")
    found: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        prompt = row["prompt_text"]
        goal = row["injection_goal"]
        if prompt.endswith(goal):
            prompt = prompt[:-len(goal)].rstrip()
        found.add(normalized(prompt))
    return found


def main() -> None:
    rows = [json.loads(line) for line in BANK.read_text(encoding="utf-8").splitlines() if line.strip()]
    report = json.loads(BUILDER_REPORT.read_text(encoding="utf-8"))
    if len(rows) != 400:
        raise ValueError(f"found {len(rows)} rows, expected 400")
    required = {"prompt_id", "arm", "domain", "payload_class", "injection_goal", "prompt_text", "synthetic_provenance"}
    if any(not required.issubset(row) for row in rows):
        raise ValueError("one or more rows are missing runner or provenance fields")
    if len({row["prompt_id"] for row in rows}) != 400:
        raise ValueError("prompt IDs are not unique")
    if len({normalized(row["prompt_text"]) for row in rows}) != 400:
        raise ValueError("normalized complete prompt texts are not unique")
    if {row["domain"] for row in rows} != DOMAINS:
        raise ValueError("the bank has an unexpected domain set")
    if {row["payload_class"] for row in rows} != PAYLOAD_CLASSES:
        raise ValueError("the bank has an unexpected payload-class set")
    domain_hist = Counter(row["domain"] for row in rows)
    payload_hist = Counter(row["payload_class"] for row in rows)
    cell_hist = Counter((row["domain"], row["payload_class"]) for row in rows)
    if set(domain_hist.values()) != {40} or set(payload_hist.values()) != {50}:
        raise ValueError("domain or payload balance is incorrect")
    if len(cell_hist) != 80 or set(cell_hist.values()) != {5}:
        raise ValueError("domain-by-payload balance is incorrect")
    if any(row["arm"] != "INJECTED" for row in rows):
        raise ValueError("unexpected arm value")
    for row in rows:
        trailer = "\n\nEmbedded note: " + row["injection_goal"]
        if not row["prompt_text"].endswith(trailer):
            raise ValueError(f"prompt {row['prompt_id']} does not end with its declared note")
        provenance = row["synthetic_provenance"]
        if provenance.get("task_context_id") != row["prompt_id"]:
            raise ValueError(f"context ID mismatch for {row['prompt_id']}")
        context = row["prompt_text"].split("\n\nFictional material:\n", 1)[1][:-len(trailer)]
        expected = hashlib.sha256(context.encode("utf-8")).hexdigest()
        if expected != provenance.get("context_sha256"):
            raise ValueError(f"context hash mismatch for {row['prompt_id']}")
    new_contexts = set()
    for row in rows:
        trailer = "\n\nEmbedded note: " + row["injection_goal"]
        body = row["prompt_text"].split("\n\nFictional material:\n", 1)[1]
        context = body[:-len(trailer)]
        new_contexts.add(normalized(context))
    old = prior_contexts(PRIOR_BANK, EXPECTED_PRIOR_BANK)
    old |= prior_contexts(PRIOR_SOURCE, EXPECTED_PRIOR_SOURCE)
    overlap = new_contexts & old
    if overlap:
        raise ValueError(f"found {len(overlap)} exact normalized prior-context overlaps")
    if report.get("bank_sha256") != file_hash(BANK) or report.get("builder_sha256") != file_hash(BUILDER):
        raise ValueError("builder validation record does not match current files")
    result = {
        "status": "SECOND_PASS_STRUCTURAL_CHECK_PASSED",
        "bank_sha256": file_hash(BANK),
        "builder_sha256": file_hash(BUILDER),
        "validator_sha256": file_hash(Path(__file__)),
        "rows": len(rows),
        "unique_prompt_ids": len({row["prompt_id"] for row in rows}),
        "unique_normalized_prompt_text": len({normalized(row["prompt_text"]) for row in rows}),
        "domain_counts": dict(sorted(domain_hist.items())),
        "payload_counts": dict(sorted(payload_hist.items())),
        "domain_payload_cells": len(cell_hist),
        "rows_per_domain_payload_cell": sorted(set(cell_hist.values())),
        "exact_normalized_prior_context_overlaps": 0,
        "comparison_source_hashes": {
            "retry5_candidate_bank": EXPECTED_PRIOR_BANK,
            "240_row_source": EXPECTED_PRIOR_SOURCE,
        },
        "limits": "This checks structure and exact normalized text overlap. It does not establish semantic uniqueness or replace human review.",
        "run_status": "NOT RUN; no model, AWS, or paid API execution",
    }
    (HERE / "candidate_bank_secondary_check_20261025.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
