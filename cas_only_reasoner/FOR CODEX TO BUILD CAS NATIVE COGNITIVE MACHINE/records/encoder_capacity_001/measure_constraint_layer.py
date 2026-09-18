"""The declared-constraint layer, measured end to end through the real module.

Pure standard library plus the project's pure modules. No torch, no device, no model, no training, no
new run. Reads the recorded score table and the frozen course.

What this measures
------------------
`cncm/answer_constraints.py` corrects a decision table using only what the packet declares. Rounds
32-35 measured its pieces one at a time on the recorded scores; this runs the **actual module** over
**every question of every kind** in **all six runs**, so the pieces are combined in the code rather
than added up on paper.

For each question:

    unconstrained = slots.score_decisions(packet, scores)              the run's own rule
    constrained   = answer_constraints.apply_constraints(...)          the same, corrected
    both -> slots.assemble_answer -> compare against the derived truth

Correctness is membership of the whole admissible set, because `analogy` and `correspondence` admit
6-9 and 1-6 answers per question and comparing to the first element alone undercounts them.
"""

from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa: E402
from cncm import answer_constraints  # noqa: E402

RECEIPTS = HOME / "records/typed_matched_001"
MANY = ("edge_account", "role_set", "parts", "context", "definition")


def main() -> int:
    frozen_course, _tokenizer, _ = worker_contract.load_material(HOME)
    receipts = sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/artifacts/final_predictions.json").is_file()
    )
    print(f"runs: {len(receipts)}", flush=True)
    print()

    grand = {}
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        predictions = json.loads((artifacts / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        per_kind = {}
        for prediction in predictions:
            packet = course.model_packet(frozen_course, prediction["record_id"])
            plan = slots.compile_slots(packet)
            kind = plan["kind"]
            target = checker.derive_target(packet["source"], packet["record"]["query"])
            admissible = {json.dumps(item["value"], sort_keys=True)
                          for item in target["admissible_answers"]}
            scores = prediction["scores"]

            row = per_kind.setdefault(kind, Counter())
            row["questions"] += 1
            try:
                base = slots.score_decisions(packet, scores)
            except Exception:                                         # noqa: BLE001
                continue

            def ok(decisions):
                try:
                    value = slots.assemble_answer(packet, decisions)["value"]
                except Exception:                                     # noqa: BLE001
                    return False
                return json.dumps(value, sort_keys=True) in admissible

            row["unconstrained"] += 1 if ok(base) else 0
            fixed = dict(base)
            fixed["selected"] = answer_constraints.apply_constraints(
                packet, plan, scores, base["selected"])
            changed = fixed["selected"] != base["selected"]
            row["changed"] += 1 if changed else 0
            row["constrained"] += 1 if ok(fixed) else 0

        grand[receipt.name] = per_kind
        many_u = sum(per_kind[k]["unconstrained"] for k in MANY if k in per_kind)
        many_c = sum(per_kind[k]["constrained"] for k in MANY if k in per_kind)
        many_q = sum(per_kind[k]["questions"] for k in MANY if k in per_kind)
        all_u = sum(row["unconstrained"] for row in per_kind.values())
        all_c = sum(row["constrained"] for row in per_kind.values())
        all_q = sum(row["questions"] for row in per_kind.values())
        print(f"{receipt.name}:  MANY {many_u:3d} -> {many_c:3d} of {many_q}"
              f"   ALL {all_u:3d} -> {all_c:3d} of {all_q}", flush=True)

    print()
    print("=" * 100)
    print("THE DECLARED-CONSTRAINT LAYER, EVERY QUESTION, SIX RUNS")
    print("=" * 100)
    print()
    kinds = sorted({kind for row in grand.values() for kind in row})
    print(f"{'kind':>15} {'q':>5} {'unconstrained':>14} {'constrained':>12} {'lift':>9}"
          f" {'selections changed':>19}")
    print("-" * 100)
    totals = {kind: Counter() for kind in kinds}
    for name in sorted(grand):
        for kind, row in grand[name].items():
            for key in ("questions", "unconstrained", "constrained", "changed"):
                totals[kind][key] += row[key]
    for kind in kinds:
        row = totals[kind]
        base = row["unconstrained"] / row["questions"]
        fixed = row["constrained"] / row["questions"]
        print(f"{kind:>15} {row['questions']:5d} {base:13.4%} {fixed:11.4%} {fixed - base:+9.4%}"
              f" {row['changed'] / row['questions']:18.4%}")
    print("-" * 100)
    for label, members in (("ONE DECISION", [k for k in kinds if k not in MANY]),
                           ("MANY DECISIONS", [k for k in kinds if k in MANY]),
                           ("ALL", kinds)):
        q = sum(totals[k]["questions"] for k in members)
        u = sum(totals[k]["unconstrained"] for k in members)
        c = sum(totals[k]["constrained"] for k in members)
        print(f"{label:>15} {q:5d} {u / q:13.4%} {c / q:11.4%} {c / q - u / q:+9.4%}")
    print()
    print("unconstrained = slots.score_decisions, the run's own rule")
    print("constrained   = cncm.answer_constraints.apply_constraints on the same scores")
    print("Both arms read the RECORDED scores. No target enters either decoder; the truth is used")
    print("only to score the result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
