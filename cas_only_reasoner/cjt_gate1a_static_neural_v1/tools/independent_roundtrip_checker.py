"""independent_roundtrip_checker.py -- the INDEPENDENT preservation checker
(INDEPENDENT_PRESERVATION_CHECKER_SPEC.md).

INDEPENDENCE LAW: this module imports NOTHING from the generator and shares no
template-rendering code. It recovers the formal operations from the surface text
with its OWN grammar, derives the answer from its OWN recovered trace, and fails
any passage whose recovery mismatches the seed record in class, argument, order,
question, or derived answer. Failed round trips are EXCLUDED, never relabeled --
this module has no write access to labels.

Honest limit: same-process code-path independence (two disjoint programs in one
repository), not organizational independence.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# op grammar: (class, family, regex, argument-mapper) -- written against the
# REGISTERED template families, not against generator internals
_G = [
    ("^2", "A", re.compile(r"^(\w+) was drawn to (\w+)\.$"),
     lambda m: ["^2", m[1], m[2]]),
    ("^2", "B", re.compile(r"^(\w+) pulled (\w+) toward it\.$"),
     lambda m: ["^2", m[2], m[1]]),
    ("^2", "C", re.compile(r"^(\w+) felt an unmistakable pull toward (\w+)\.$"),
     lambda m: ["^2", m[1], m[2]]),
    ("^2", "D", re.compile(r"^the appeal of (\w+) captured (\w+) completely\.$"),
     lambda m: ["^2", m[2], m[1]]),
    ("^3", "A", re.compile(r"^(\w+) withdrew from (\w+)\.$"),
     lambda m: ["^3", m[1], m[2]]),
    ("^3", "B", re.compile(r"^(\w+) repelled (\w+) from the start\.$"),
     lambda m: ["^3", m[2], m[1]]),
    ("^3", "C", re.compile(r"^(\w+) recoiled whenever (\w+) came up\.$"),
     lambda m: ["^3", m[1], m[2]]),
    ("^3", "D", re.compile(r"^faced with (\w+), (\w+) backed away\.$"),
     lambda m: ["^3", m[2], m[1]]),
    ("^6", "A", re.compile(r"^(\w+) broke down into (\w+), (\w+), and (\w+)\.$"),
     lambda m: ["^6", m[1], [m[2], m[3], m[4]]]),
    ("^6", "B", re.compile(r"^inside (\w+) lay (\w+), (\w+), and (\w+)\.$"),
     lambda m: ["^6", m[1], [m[2], m[3], m[4]]]),
    ("^6", "C", re.compile(r"^(\w+) could be split into (\w+), (\w+), and (\w+)\.$"),
     lambda m: ["^6", m[1], [m[2], m[3], m[4]]]),
    ("^6", "D", re.compile(r"^three strands made up (\w+): (\w+), (\w+), and (\w+)\.$"),
     lambda m: ["^6", m[1], [m[2], m[3], m[4]]]),
    ("^8", "A", re.compile(r"^(\w+) brought (\w+) to (\w+)'s mind\.$"),
     lambda m: ["^8", m[3], m[1], m[2]]),
    ("^8", "B", re.compile(r"^whenever (\w+) thought of (\w+), (\w+) surfaced\.$"),
     lambda m: ["^8", m[1], m[2], m[3]]),
    ("^8", "C", re.compile(r"^(\w+) reminded (\w+) of (\w+)\.$"),
     lambda m: ["^8", m[2], m[1], m[3]]),
    ("^8", "D", re.compile(r"^for (\w+), (\w+) always summoned (\w+)\.$"),
     lambda m: ["^8", m[1], m[2], m[3]]),
]

_Q = [
    ("Q_ATTRACT", re.compile(r"^which idea was (\w+) drawn to\?$")),
    ("Q_AVERT", re.compile(r"^which idea did (\w+) withdraw from\?$")),
    ("Q_PART", re.compile(r"^what is part ([123]) of (\w+)\?$")),
    ("Q_TRIGGER", re.compile(r"^what did (\w+) bring to (\w+)'s mind\?$")),
]


def _parse_clause(text):
    """Return (op, cls, family) or (None, None, None); ambiguity fails closed."""
    hits = [(mapper(m), cls, fam) for cls, fam, rx, mapper in _G
            if (m := rx.match(text))]
    if len(hits) != 1:
        return None, None, None
    return hits[0]


def _derive_answer(qtype, qm, trace):
    if qtype == "Q_ATTRACT":
        hits = [op for op in trace if op[0] == "^2" and op[1] == qm.group(1)]
        return hits[0][2] if len(hits) == 1 else None
    if qtype == "Q_AVERT":
        hits = [op for op in trace if op[0] == "^3" and op[1] == qm.group(1)]
        return hits[0][2] if len(hits) == 1 else None
    if qtype == "Q_PART":
        k, idea = int(qm.group(1)), qm.group(2)
        hits = [op for op in trace if op[0] == "^6" and op[1] == idea]
        return hits[0][2][k - 1] if len(hits) == 1 else None
    hits = [op for op in trace
            if op[0] == "^8" and op[2] == qm.group(1) and op[1] == qm.group(2)]
    return hits[0][3] if len(hits) == 1 else None


def check_record(rec):
    """(True, 'ROUNDTRIP_PASS') or (False, reason). Pure; no label writes."""
    recovered, families = [], []
    for j, clause in enumerate(rec["clauses"]):
        op, cls, fam = _parse_clause(clause["text"])
        if op is None:
            return False, f"ROUNDTRIP_FAIL(clause {j}: unparseable or ambiguous)"
        recovered.append(op)
        families.append(fam)
    if recovered != [list(op) for op in rec["seed_trace"]]:
        return False, "ROUNDTRIP_FAIL(trace mismatch: class/argument/order)"
    if families != list(rec["template_families"]):
        return False, "ROUNDTRIP_FAIL(template family mismatch)"
    if [op[0] for op in recovered] != list(rec["idea_labels"]):
        return False, "ROUNDTRIP_FAIL(idea label mismatch)"
    qhits = [(qt, m) for qt, rx in _Q if (m := rx.match(rec["question"]))]
    if len(qhits) != 1:
        return False, "ROUNDTRIP_FAIL(question unparseable or ambiguous)"
    qtype, qm = qhits[0]
    if qtype != rec["question_type"]:
        return False, "ROUNDTRIP_FAIL(question type mismatch)"
    answer = _derive_answer(qtype, qm, recovered)
    if answer is None:
        return False, "ROUNDTRIP_FAIL(answer not uniquely derivable)"
    if answer != rec["answer"]:
        return False, "ROUNDTRIP_FAIL(derived answer mismatch)"
    if answer not in rec["candidates"]:
        return False, "ROUNDTRIP_FAIL(answer outside the closed candidate set)"
    return True, "ROUNDTRIP_PASS"


def main():
    fails = 0
    for path in sys.argv[1:]:
        for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines()):
            ok, reason = check_record(json.loads(line))
            if not ok:
                fails += 1
                print(f"{path}:{n + 1}: {reason}")
    print("ALL ROUNDTRIPS PASS" if fails == 0 else f"{fails} ROUNDTRIP FAILURES")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
