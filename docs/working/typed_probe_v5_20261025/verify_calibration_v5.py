#!/usr/bin/env python3
# Compare owner labels with the hidden panel answer key only after owner labeling is complete.
import argparse
import json
import sys

VALID = {"C", "R", "I", "U"}


def load_jsonl(path):
    with open(path, encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-labels", required=True)
    parser.add_argument("--answer-key", required=True)
    args = parser.parse_args()
    human_rows = load_jsonl(args.owner_labels)
    key_rows = load_jsonl(args.answer_key)
    if len(human_rows) != 30 or len(key_rows) != 30:
        raise SystemExit("FAIL: expected exactly 30 owner labels and 30 answer-key rows")
    key = {row["trace_id"]: row["panel_label"] for row in key_rows}
    if len(key) != 30:
        raise SystemExit("FAIL: answer-key trace IDs are not unique")
    exact = 0
    seen = set()
    for row in human_rows:
        trace_id = row.get("trace_id")
        label = str(row.get("human_label", "")).strip().upper()
        if trace_id not in key or trace_id in seen or label not in VALID:
            raise SystemExit("FAIL: missing, duplicate, or invalid owner label")
        seen.add(trace_id)
        exact += int(label == key[trace_id])
    if seen != set(key):
        raise SystemExit("FAIL: owner-label trace IDs do not match the answer key")
    print(json.dumps({"n": 30, "exact_matches": exact, "required": 24,
                      "stage_c_gate": exact >= 24}, sort_keys=True))
    return 0 if exact >= 24 else 2


if __name__ == "__main__":
    sys.exit(main())
