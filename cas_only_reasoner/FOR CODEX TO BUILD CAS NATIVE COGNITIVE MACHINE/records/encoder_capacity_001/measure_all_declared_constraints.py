"""Do the OTHER declared constraints work? edge_account, parts, definition.

Pure Python. Standard library only. No torch, no device, no model, no training, no new run.
Reads the recorded score table and the frozen course. Targets are re-derived by the project's own
checker from the public snapshot.

Round 32 measured that `context`'s participants are exactly three of four by the packet's own
`PRIMARY_AUTHORED_LABELS_FIRST_THREE` basis, and that forcing that cardinality on the RECORDED scores
took the participant bits 40.0125% -> 60.9863% and the exact answer 0.0000% -> 32.6190%, six for six.

Three more kinds carry declared structure of the same sort, and none of it is read:

  edge_account  the answer is exactly `focus["contains"]`, a list the packet supplies, so its SIZE is
                declared per question. Force exactly that many PRESENT slots.
  parts         the answer is `{b : (whole, b) in contains}`, so its size is declared too -- the count
                of declared edges whose source is the supplied `whole`.
  definition    `FOCUS_WORLD_DECLARATION_IDENTITY`: the three fields are ONE world's declaration
                triple, not three free choices. Enumerate the bank's worlds, score each world's
                implied triple, take the argmax -- the same joint-candidate move `correspondence`
                already uses.

Each is compared against the run's own independent per-slot decoder on the same recorded scores, with
the other fields held at the truth where a kind has more than one field, so the arm isolates what it
claims to isolate.
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

from cas_meta2.typed_teaching import answers, checker, course, slots, worker_contract  # noqa: E402

RECEIPTS = HOME / "records/typed_matched_001"
KINDS = ("edge_account", "parts", "definition")


def load(receipt):
    artifacts = receipt / "collected/results/artifacts"
    predictions = json.loads((artifacts / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
    scoring = {row["record_id"]: row for row in
               json.loads((artifacts / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}
    return predictions, scoring


def margin(scores, slot, symbol):
    return scores[slot["slot_id"]][symbol]


def main() -> int:
    frozen_course, _tokenizer, _ = worker_contract.load_material(HOME)
    receipts = sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/artifacts/final_predictions.json").is_file()
    )
    print(f"runs: {len(receipts)}", flush=True)

    totals = {}
    for receipt in receipts:
        predictions, scoring = load(receipt)
        rows = {}
        for prediction in predictions:
            record_id = prediction["record_id"]
            kind = scoring[record_id]["kind"]
            if kind not in KINDS:
                continue
            packet = course.model_packet(frozen_course, record_id)
            query = packet["record"]["query"]
            plan = slots.compile_slots(packet)
            target = checker.derive_target(packet["source"], query)
            truth = target["admissible_answers"][0]["value"]
            admissible = {json.dumps(item["value"], sort_keys=True) for item in target["admissible_answers"]}
            scores = prediction["scores"]
            focus = next(world for world in packet["source"]["worlds"]
                         if world["world_id"] == query["focus_world_id"])
            aliases = {world["world_id"]: world for world in plan["aliases"]["worlds"]}
            row = rows.setdefault(kind, Counter())

            def run(selected, row=row, packet=packet, admissible=admissible, prediction=prediction):
                decisions = {**prediction["decisions"], "selected": selected}
                try:
                    value = slots.assemble_answer(packet, decisions)["value"]
                except Exception:                                     # noqa: BLE001
                    return False
                return json.dumps(value, sort_keys=True) in admissible

            # ---- the run's own independent decoder -------------------------------------------
            independent = {}
            for slot in plan["slots"]:
                per_symbol = scores[slot["slot_id"]]
                independent[slot["slot_id"]] = max(slot["symbols"],
                                                   key=lambda symbol: per_symbol[symbol])
            row["questions"] += 1
            row["independent"] += 1 if run(independent) else 0

            if kind in ("edge_account", "parts"):
                if kind == "edge_account":
                    field, k = "edge", len(focus["contains"])
                else:
                    whole = query["arguments"]["whole"]
                    field = "node"
                    k = sum(1 for edge in focus["contains"] if edge["source"] == whole)
                candidates = [slot for slot in plan["slots"] if slot["field"] == field]
                if not candidates or k > len(candidates):
                    continue
                ranked = sorted(candidates, key=lambda slot: (scores[slot["slot_id"]]["PRESENT"]
                                                              - scores[slot["slot_id"]]["ABSENT"]),
                                reverse=True)
                constrained = dict(independent)
                for rank, slot in enumerate(ranked):
                    constrained[slot["slot_id"]] = "PRESENT" if rank < k else "ABSENT"
                row["constrained"] += 1 if run(constrained) else 0
                row["k"] += k

            elif kind == "definition":
                # FOCUS_WORLD_DECLARATION_IDENTITY: one world's declaration triple, not three free
                # choices. Enumerate the bank and score each world's implied triple.
                by_field = {slot["field"]: slot for slot in plan["slots"]}
                if set(by_field) != {"whole", "kind_ref", "function_ref"}:
                    continue
                best, best_score = None, None
                for world in packet["source"]["worlds"]:
                    other = aliases[world["world_id"]]
                    declared = {node["ref"]: node["alias"] for node in other["nodes"]}
                    triple = {"whole": declared.get(world["declared_whole"]),
                              "kind_ref": other["alias"], "function_ref": other["alias"]}
                    if triple["whole"] is None:
                        continue
                    if any(triple[field] not in by_field[field]["symbols"] for field in triple):
                        continue
                    total = sum(scores[by_field[field]["slot_id"]][symbol]
                                for field, symbol in triple.items())
                    if best_score is None or total > best_score:
                        best, best_score = triple, total
                if best is None:
                    continue
                constrained = dict(independent)
                for field, symbol in best.items():
                    constrained[by_field[field]["slot_id"]] = symbol
                row["constrained"] += 1 if run(constrained) else 0

        totals[receipt.name] = rows

    print()
    print("=" * 100)
    print("DO THE OTHER DECLARED CONSTRAINTS WORK? — recorded scores, six runs")
    print("=" * 100)
    print()
    print(f"{'run':>22} {'kind':>14} {'q':>4} {'independent':>13} {'constrained':>13} {'lift':>10}")
    print("-" * 100)
    grand = {}
    for name in sorted(totals):
        for kind in KINDS:
            row = totals[name].get(kind)
            if not row or "constrained" not in row:
                continue
            questions = row["questions"]
            base = row["independent"] / questions
            fixed = row["constrained"] / questions
            print(f"{name:>22} {kind:>14} {questions:4d} {base:12.4%} {fixed:12.4%} {fixed - base:+10.4%}")
            agg = grand.setdefault(kind, Counter())
            for key in ("questions", "independent", "constrained"):
                agg[key] += row[key]
        print()
    print("-" * 100)
    for kind in KINDS:
        agg = grand.get(kind)
        if not agg:
            continue
        base = agg["independent"] / agg["questions"]
        fixed = agg["constrained"] / agg["questions"]
        print(f"{'ALL SIX RUNS':>22} {kind:>14} {agg['questions']:4d} {base:12.4%} {fixed:12.4%}"
              f" {fixed - base:+10.4%}")
    print()
    print("edge_account  force exactly len(focus['contains']) PRESENT slots, top-k by margin")
    print("parts         force exactly the declared count of edges from the supplied `whole`")
    print("definition    force the three fields to one world's declaration triple, argmax over the bank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
