"""Does a DECLARED constraint fix `context`? The participants field is exactly three of four.

Pure Python. Standard library only. No torch, no device, no model, no training, no new run.
Reads the recorded score table and the frozen course. Targets are re-derived by the project's own
checker from the public snapshot.

Why this, now
-------------
Round 31/32 measured what each field of an answer is worth by giving it the truth and re-assembling:

    context   + participant truth   75.7143%   (+71.4286)
    context   + setting_ref truth    4.2857%   (+0.0000)

**`context`'s entire deficit is its four participant bits**, and `setting_ref` is worth exactly
nothing. The recorded decoder takes an independent `max` per slot and knows no constraint.

But the packet DECLARES the constraint. `answers.answer_space` sets
`participants_basis = PRIMARY_AUTHORED_LABELS_FIRST_THREE` for every world, and
`checker._derive_values` reads the answer as `sorted(focus["declarations"]["participants"])`. The
`context` slots are that world's four nodes. So the answer is not four free bits -- it is a choice of
**which one node is absent**.

That is a constraint the composer could enforce from the packet alone, with no teacher and no new
information. Round 26 found the architecture composes jointly for exactly one kind and independently
for the other seven; round 27 showed that for three kinds there was nothing to compose. This asks the
narrower and testable question: **for the one kind whose answer carries a declared cardinality, does
enforcing it help?**

What is measured
----------------
For every `context` question, from the recorded per-slot scores:

  independent   argmax each participant slot on its own                        (the run's own rule)
  top-k         take the k highest-scoring slots as PRESENT, the rest ABSENT, for the k the packet's
                own rule declares -- three where the world has four nodes

Both are assembled with the project's own `slots.assemble_answer` and compared to the project's own
derived truth. `setting_ref` is left at whatever the recorded decision chose, so the comparison
isolates the participant bits.
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

RECEIPTS = HOME / "records/typed_matched_001"


def main() -> int:
    frozen_course, _tokenizer, _ = worker_contract.load_material(HOME)
    receipts = sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/artifacts/final_predictions.json").is_file()
    )

    totals = Counter()
    print("=" * 100)
    print("CONTEXT PARTICIPANTS — does the packet's own cardinality rule help?")
    print("=" * 100)
    print()
    print(f"{'run':>22} {'q':>4} {'indep, mach set':>16} {'top3, mach set':>15}"
          f" {'indep, TRUE set':>16} {'top3, TRUE set':>15} {'lift':>9} {'bits indep':>11} {'bits top3':>10}")
    print("-" * 128)
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        predictions = json.loads((artifacts / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        scoring = {row["record_id"]: row for row in
                   json.loads((artifacts / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}
        row = Counter()
        cardinality = Counter()
        counts = Counter()
        for prediction in predictions:
            record_id = prediction["record_id"]
            if scoring[record_id]["kind"] != "context":
                continue
            packet = course.model_packet(frozen_course, record_id)
            query = packet["record"]["query"]
            plan = slots.compile_slots(packet)
            target = checker.derive_target(packet["source"], query)
            truth = target["admissible_answers"][0]["value"]
            admissible = {json.dumps(item["value"], sort_keys=True) for item in target["admissible_answers"]}

            parts = [slot for slot in plan["slots"] if slot["field"] == "participant"]
            if len(parts) < 2:
                continue
            row["questions"] += 1
            counts[len(parts)] += 1
            cardinality[len(truth["participants"])] += 1

            scores = prediction["scores"]
            selected = dict(prediction["decisions"]["selected"])

            # `context` answers are TWO fields, so the participant arm must hold `setting_ref` at
            # the truth or the machine's own setting error caps it at zero. The first version of
            # this file held it at the machine's choice and read 0.0000% in all six runs -- an
            # impossible-looking reading that was really a design flaw. Both arms are now reported:
            # `machine setting` and `true setting`.
            true_setting = None
            for world in plan["aliases"]["worlds"]:
                from cas_meta2.typed_teaching import answers as _answers
                if _answers.declaration_ref(world["world_id"], "setting") == truth["setting_ref"]:
                    true_setting = world["alias"]
            if true_setting is None:
                continue

            # independent: the run's own rule
            independent = dict(selected)
            for slot in parts:
                per_symbol = scores[slot["slot_id"]]
                independent[slot["slot_id"]] = max(slot["symbols"],
                                                   key=lambda symbol: per_symbol[symbol])
            decisions = {**prediction["decisions"], "selected": independent,
                         "correspondence_candidate_id": None}
            row["independent"] += 1 if json.dumps(
                slots.assemble_answer(packet, decisions)["value"], sort_keys=True) in admissible else 0

            # top-k: the k highest present-minus-absent margins are PRESENT, for the declared k
            k = len(truth["participants"])
            ranked = sorted(parts, key=lambda slot: (scores[slot["slot_id"]]["PRESENT"]
                                                     - scores[slot["slot_id"]]["ABSENT"]), reverse=True)
            constrained = dict(selected)
            for rank, slot in enumerate(ranked):
                constrained[slot["slot_id"]] = "PRESENT" if rank < k else "ABSENT"
            row["bits_correct_independent"] += sum(
                1 for slot in parts
                if independent[slot["slot_id"]] == ("PRESENT" if slot["coordinates"][0]
                                                    in set(truth["participants"]) else "ABSENT"))
            row["bits_correct_topk"] += sum(
                1 for slot in ranked[:k]
                if ranked.index(slot) < k and slot["coordinates"][0] in set(truth["participants"]))
            row["bits"] += len(parts)

            # both arms, each with setting_ref set to the truth
            for label, selection in (("independent", independent), ("topk", constrained)):
                fixed = dict(selection)
                for slot in plan["slots"]:
                    if slot["field"] == "setting_ref":
                        fixed[slot["slot_id"]] = true_setting
                decisions = {**prediction["decisions"], "selected": fixed,
                             "correspondence_candidate_id": None}
                ok = json.dumps(slots.assemble_answer(packet, decisions)["value"],
                                sort_keys=True) in admissible
                row[f"{label}_true_setting"] += 1 if ok else 0

        questions = row["questions"]
        indep_machine = row["independent"] / questions
        topk_machine = row["topk"] / questions if row["topk"] else 0.0
        indep_true = row["independent_true_setting"] / questions
        topk_true = row["topk_true_setting"] / questions
        print(f"{receipt.name:>22} {questions:4d} {indep_machine:15.4%} {topk_machine:14.4%}"
              f" {indep_true:15.4%} {topk_true:14.4%} {topk_true - indep_true:+9.4%}"
              f" {row['bits_correct_independent'] / row['bits']:10.4%}"
              f" {row['bits_correct_topk'] / row['bits']:9.4%}")
        for key in ("questions", "independent", "independent_true_setting",
                    "topk_true_setting", "bits", "bits_correct_independent", "bits_correct_topk"):
            totals[key] += row[key]
    print("-" * 128)
    questions = totals["questions"]
    indep_true = totals["independent_true_setting"] / questions
    topk_true = totals["topk_true_setting"] / questions
    print(f"{'ALL SIX RUNS':>22} {questions:4d} {totals['independent'] / questions:15.4%}"
          f" {'':>14} {indep_true:15.4%} {topk_true:14.4%} {topk_true - indep_true:+9.4%}"
          f" {totals['bits_correct_independent'] / totals['bits']:10.4%}"
          f" {totals['bits_correct_topk'] / totals['bits']:9.4%}")
    print()
    print("mach set = `setting_ref` left at the machine's own choice")
    print("TRUE set = `setting_ref` set to the truth, so the participant bits are isolated")
    print("top-3    = force exactly k PRESENT, k from the packet's own")
    print("           `PRIMARY_AUTHORED_LABELS_FIRST_THREE` basis, the rest ABSENT")
    print("bits     = per-slot accuracy on the participant slots alone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
