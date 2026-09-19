"""Compute the FROZEN removal list the contract's REMOVALS placeholder must carry.

Two classes, and they are different kinds of thing:

  1. SHORTCUT rules -- questions a registered no-learning rule answers, so a gain there is not evidence of
     learning. Ids come from `measurements/leaks_review/lk6_gate_population_out.txt` lines 62, 65 and 68.
  2. ARCHITECTURAL INEXPRESSIBILITY -- the five `correspondence` questions, removed because the drafted head
     CANNOT EXPRESS a bijection (LB12/LB13/LB15: 0 of 20 held correct, and in 81 of 88 records no additive
     per-node score can prefer a correct answer). This is a limit of the head, not a shortcut.

Output is the exact dict to paste into `pointer_contract.REMOVALS`. Pure Python, $0, no torch.
Run from a short working directory.
"""
import ast
import json
import sys
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD "
            r"CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX "
            r"TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research" / "CAS_META_2_COMPOSITION")]

from cas_meta2.typed_teaching import pointer_contract as pc   # noqa: E402

# The ids lk6 printed. Read them from the artifact rather than retyping them, so a transcription slip is impossible.
LK6 = (CNCM / "records" / "typed_pointer_001" / "pre_design" / "measurements" / "leaks_review"
       / "lk6_gate_population_out.txt").read_text(encoding="utf-8")


def ids_on(line_marker):
    """lk6 prints the ids with Python repr (single quotes), so parse with literal_eval, not json."""
    for line in LK6.splitlines():
        if line_marker in line:
            start, end = line.find("["), line.rfind("]")
            if start != -1 and end != -1:
                return ast.literal_eval(line[start:end + 1])
    raise SystemExit("marker not found: " + line_marker)


fp2_parts = ids_on("FP2 parts")
order_dependence = ids_on("order dependence")
present_for_all = ids_on("PRESENT-for-all")
print("from lk6:  FP2 parts %d, order dependence %d, PRESENT-for-all %d"
      % (len(fp2_parts), len(order_dependence), len(present_for_all)))

# The eligible held RELATIONAL questions, through the practice study's OWN derivation.
frozen, tokenizer, dev = pc.load_material(CNCM)
held = pc.held_back_questions(frozen)
trained = set(pc.split(frozen)[1])
gates = pc._practice_gates()
eligible, shortcut_hit, shortcut = gates.eligible_questions(frozen, trained, held)
kind_of = {row["query"]["query_id"]: row["query"]["kind"] for row in frozen["registry"]}

relational = sorted(q for q in eligible if kind_of[q] in pc.RELATIONAL)
by_kind = {}
for q in relational:
    by_kind.setdefault(kind_of[q], []).append(q)
print("eligible RELATIONAL: %d  %s" % (len(relational), {k: len(v) for k, v in sorted(by_kind.items())}))

correspondence = by_kind.get("correspondence", [])
print("correspondence (the inexpressible class): %d" % len(correspondence))

# Sanity: every lk6 id must be one of the eligible relational questions.
for name, ids in (("fp2_parts", fp2_parts), ("order_dependence", order_dependence),
                  ("present_for_all", present_for_all)):
    unknown = [i for i in ids if i not in set(relational)]
    print("  %-18s all present in the eligible relational set: %s" % (name, not unknown))

removals = {
    "flag_rule": {"parts": fp2_parts},
    "order_rule": {"reach": order_dependence},
    "present_rule": {"reach": present_for_all},
    "inexpressible": {"correspondence": correspondence},
}
removed = [i for rule in removals.values() for ids in rule.values() for i in ids]
surviving = sorted(set(relational) - set(removed))
surv_by_kind = {}
for q in surviving:
    surv_by_kind.setdefault(kind_of[q], []).append(q)

print()
print("REMOVALS = %s" % json.dumps(removals, indent=4, sort_keys=True))
print()
print("removed total %d (duplicates %d)" % (len(removed), len(removed) - len(set(removed))))
print("POPULATION = %d  %s" % (len(surviving), {k: len(v) for k, v in sorted(surv_by_kind.items())}))
print("matches the frozen 18: %s" % (len(surviving) == 18))
print("population digest = %s" % pc.digest(surviving))
