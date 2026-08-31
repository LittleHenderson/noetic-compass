"""audit_candidate_occurrence.py -- the registered corpus occurrence audit.

Owner audit 2026-08-31 section 7: record how many answer candidates occur FIRST
outside their target clause (the clause whose formal operation yields the
answer). Under the old contextual first-occurrence encoding this fraction was an
architecture confound; the encoding is now context-free (amendment A5), so this
is recorded as a dataset characteristic, not a live confound.

Reads the materialized train/val files only (no protected touch). Writes
CANDIDATE_OCCURRENCE_AUDIT.json.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
from exec.fsio import write_utf8_lf  # noqa: E402 -- the ONE canonical writer

QOP = {"Q_ATTRACT": "^2", "Q_AVERT": "^3", "Q_PART": "^6", "Q_TRIGGER": "^8"}


def target_clause_index(rec):
    """The clause whose op answers the question (unique by the passage law)."""
    qt, trace = rec["question_type"], rec["seed_trace"]
    for j, op in enumerate(trace):
        if op[0] != QOP[qt]:
            continue
        if qt == "Q_ATTRACT" and rec["question"] == \
                f"which idea was {op[1]} drawn to?":
            return j
        if qt == "Q_AVERT" and rec["question"] == \
                f"which idea did {op[1]} withdraw from?":
            return j
        if qt == "Q_PART" and rec["answer"] in op[2] \
                and f"of {op[1]}?" in rec["question"]:
            return j
        if qt == "Q_TRIGGER" and op[3] == rec["answer"] \
                and rec["question"].startswith(f"what did {op[2]} "):
            return j
    raise AssertionError(f"no target clause in {rec['passage_id']}")


def audit_split(path):
    n = outside = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        j = target_clause_index(rec)
        starts, pos = [], 0
        for c in rec["clauses"]:
            starts.append(pos)
            pos += len(c["text"]) + 1
        first = re.search(rf"\b{re.escape(rec['answer'])}\b", rec["text"]).start()
        clause_start = starts[j]
        clause_end = clause_start + len(rec["clauses"][j]["text"])
        n += 1
        if not (clause_start <= first < clause_end):
            outside += 1
    return {"passages": n, "answer_first_occurrence_outside_target_clause": outside,
            "fraction": outside / n}


def main():
    out = {"audit_id": "CANDIDATE_OCCURRENCE_AUDIT",
           "law": ("recorded per owner audit 2026-08-31 section 7; candidate "
                   "encoding is CONTEXT-FREE (frozen input embeddings), so no "
                   "arm ever encodes a candidate from a contextual occurrence -- "
                   "this measures the dataset characteristic that motivated the "
                   "encoding change"),
           "splits": {"train": audit_split(PKG / "data" / "candidate" / "train.jsonl"),
                      "val": audit_split(PKG / "data" / "candidate" / "val.jsonl")}}
    write_utf8_lf(PKG / "CANDIDATE_OCCURRENCE_AUDIT.json",
                  json.dumps(out, indent=2) + "\n")
    for split, v in out["splits"].items():
        print(f"{split}: {v['answer_first_occurrence_outside_target_clause']}"
              f"/{v['passages']} = {v['fraction']:.3f} first-occur outside target clause")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
