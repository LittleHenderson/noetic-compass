"""Is the `edge_account` truth reachable at all?

Pure Python. No torch, no device. One question, printed in full.

`measure_field_bottleneck.py` reported that giving `edge_account` the true symbol for **every one of
its slots** still scores 0.0000% — while the same substitution takes `role_set` and `parts` to
100.0000%. `edge_account` has exactly one field, so that arm gives the answer outright. If the answer
is still wrong, then `slots.assemble_answer` cannot express the truth, and **no machine can ever
score a correct `edge_account` answer** — which would make that kind's recorded 0.0000% a property of
the task rather than of the model.

This prints the assembled answer against every admissible answer, side by side, for one question.
"""

from __future__ import annotations

import json
import pathlib
import sys

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa: E402

RECEIPT = HOME / "records/typed_matched_001/receipt_20260919_m"


def main() -> int:
    frozen_course, _tokenizer, _ = worker_contract.load_material(HOME)
    predictions = json.loads(
        (RECEIPT / "collected/results/artifacts/final_predictions.json").read_text(encoding="utf-8")
    )["predictions"]

    shown = 0
    for prediction in predictions:
        packet = course.model_packet(frozen_course, prediction["record_id"])
        query = packet["record"]["query"]
        if query["kind"] != "edge_account":
            continue
        plan = slots.compile_slots(packet)
        target = checker.derive_target(packet["source"], query)
        truth = target["admissible_answers"][0]["value"]
        focus = next(world for world in packet["source"]["worlds"]
                     if world["world_id"] == query["focus_world_id"])

        print("=" * 100)
        print(f"record {prediction['record_id'][:48]}...")
        print("=" * 100)
        print(f"admissible answers: {len(target['admissible_answers'])}")
        print(f"focus declared `contains`: {json.dumps(focus['contains'])}")
        print()
        print(f"truth value: {json.dumps(truth, sort_keys=True)}")
        print(f"truth edge order: {[ (row['source'][-2:], row['target'][-2:]) for row in truth['edges'] ]}")
        print()

        selected = {}
        for slot in plan["slots"]:
            key = (slot["coordinates"][0], slot["coordinates"][1])
            present = {(row["source"], row["target"]) for row in truth["edges"]}
            selected[slot["slot_id"]] = "PRESENT" if key in present else "ABSENT"
        print(f"true PRESENT slots: {sum(1 for value in selected.values() if value == 'PRESENT')}"
              f" of {len(selected)}   (truth has {len(truth['edges'])} edges)")

        decisions = {**prediction["decisions"], "selected": selected}
        try:
            assembled = slots.assemble_answer(packet, decisions)["value"]
        except Exception as error:                                    # noqa: BLE001
            print(f"assemble_answer RAISED: {type(error).__name__}: {error}")
            return 1
        print(f"assembled  : {json.dumps(assembled, sort_keys=True)}")
        print(f"assembled edge order: {[ (row['source'][-2:], row['target'][-2:]) for row in assembled['edges'] ]}")
        print()
        same = json.dumps(assembled, sort_keys=True) == json.dumps(truth, sort_keys=True)
        print(f"assembled == admissible_answers[0] ?  {same}")
        if not same:
            left = {(row["source"], row["target"]) for row in assembled["edges"]}
            right = {(row["source"], row["target"]) for row in truth["edges"]}
            print(f"   as SETS equal? {left == right}")
            print(f"   only in assembled: {sorted(left - right)}")
            print(f"   only in truth    : {sorted(right - left)}")
        shown += 1
        if shown >= 2:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
