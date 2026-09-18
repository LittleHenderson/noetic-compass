"""The self-link opening, and the honest metric for edges.

Pure Python. Standard library only. No torch, no device, no model, no training, no new run.
Recorded score table plus the frozen course. Targets are re-derived by the project's own checker.

Two things this settles, both raised by an independent audit of round 32.

1. SELF-LINKS. The audit measured that the fitted readout marks 35 self-link slots (X -> X) as
   PRESENT, and that none of the 267 self-link slots in that run is a real edge. A slot type that is
   never PRESENT is a declared constraint of exactly the kind that lifted `parts` by 44.9686 points in
   round 33. This file checks the claim across all six runs and on the RECORDED scores, and tests
   forcing self-link slots ABSENT.

2. THE METRIC. Per-slot accuracy is a poor target here: after the round-32 direction fix only
   20.2138% of edge slots are PRESENT, so always answering ABSENT earns 79.7862% for free. The audit's
   recommendation is adopted -- report EDGES FOUND and FALSE ALARMS, and the balanced accuracy
   (the mean of the two), which is 50% for a coin flip.
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
    print(f"runs: {len(receipts)}", flush=True)

    # ---- does any world in the whole course have a self-link? --------------------------------
    self_edges = Counter()
    worlds_seen = 0
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        for prediction in json.loads((artifacts / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]:
            packet = course.model_packet(frozen_course, prediction["record_id"])
            for world in packet["source"]["worlds"]:
                worlds_seen += 1
                for edge in world["contains"]:
                    self_edges["self" if edge["source"] == edge["target"] else "proper"] += 1
    print(f"world declarations inspected: {worlds_seen}")
    print(f"declared edges: proper {self_edges['proper']}   self-links {self_edges['self']}")
    print()

    grand = {}
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        predictions = json.loads((artifacts / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        scoring = {row["record_id"]: row for row in
                   json.loads((artifacts / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}
        row = Counter()
        for prediction in predictions:
            record_id = prediction["record_id"]
            if scoring[record_id]["kind"] != "edge_account":
                continue
            packet = course.model_packet(frozen_course, record_id)
            query = packet["record"]["query"]
            plan = slots.compile_slots(packet)
            target = checker.derive_target(packet["source"], query)
            admissible = {json.dumps(item["value"], sort_keys=True) for item in target["admissible_answers"]}
            truth = target["admissible_answers"][0]["value"]
            scores = prediction["scores"]
            focus = next(world for world in packet["source"]["worlds"]
                         if world["world_id"] == query["focus_world_id"])
            k = len(focus["contains"])
            row["questions"] += 1

            edges = [(slot, slot["coordinates"][0], slot["coordinates"][1]) for slot in plan["slots"]]
            true_present = {(item["source"], item["target"]) for item in truth["edges"]}

            def run(selected):
                decisions = {**prediction["decisions"], "selected": selected}
                try:
                    value = slots.assemble_answer(packet, decisions)["value"]
                except Exception:                                     # noqa: BLE001
                    return False
                return json.dumps(value, sort_keys=True) in admissible

            independent = {}
            for slot, _a, _b in edges:
                per_symbol = scores[slot["slot_id"]]
                independent[slot["slot_id"]] = max(slot["symbols"],
                                                   key=lambda symbol: per_symbol[symbol])

            # confusion, on the recorded machine
            for slot, a, b in edges:
                said = independent[slot["slot_id"]] == "PRESENT"
                real = (a, b) in true_present
                is_self = a == b
                row["bits"] += 1
                row["self_slots"] += 1 if is_self else 0
                row["self_said_present"] += 1 if (is_self and said) else 0
                row["self_true_present"] += 1 if (is_self and real) else 0
                row["tp"] += 1 if (said and real) else 0
                row["fp"] += 1 if (said and not real) else 0
                row["fn"] += 1 if (not said and real) else 0
                row["tn"] += 1 if (not said and not real) else 0

            row["independent"] += 1 if run(independent) else 0

            # (a) force self-link slots ABSENT
            no_self = dict(independent)
            for slot, a, b in edges:
                if a == b:
                    no_self[slot["slot_id"]] = "ABSENT"
            row["no_self"] += 1 if run(no_self) else 0
            row["no_self_bits"] += sum(1 for slot, a, b in edges
                                       if no_self[slot["slot_id"]] == ("PRESENT" if (a, b) in true_present else "ABSENT"))

            # (b) self-links ABSENT, then the declared cardinality k over the remaining slots
            nonself = sorted([item for item in edges if item[1] != item[2]],
                             key=lambda item: (scores[item[0]["slot_id"]]["PRESENT"]
                                               - scores[item[0]["slot_id"]]["ABSENT"]), reverse=True)
            both = dict(no_self)
            for rank, (slot, _a, _b) in enumerate(nonself):
                both[slot["slot_id"]] = "PRESENT" if rank < k else "ABSENT"
            row["both"] += 1 if run(both) else 0
            row["both_bits"] += sum(1 for slot, a, b in edges
                                    if both[slot["slot_id"]] == ("PRESENT" if (a, b) in true_present else "ABSENT"))

        for key, value in row.items():
            grand[key] = grand.get(key, 0) + value

    bits = grand["bits"]
    tp, fp, fn, tn = grand["tp"], grand["fp"], grand["fn"], grand["tn"]
    found = tp / (tp + fn) if (tp + fn) else float("nan")
    clean = tn / (tn + fp) if (tn + fp) else float("nan")
    print("=" * 100)
    print("THE RECORDED MACHINE ON EDGE SLOTS — all six runs, 6,174 slots")
    print("=" * 100)
    print()
    print(f"  true edges (PRESENT)          {tp + fn:6d}   of {bits} slots")
    print(f"  true non-edges (ABSENT)       {tn + fp:6d}")
    print(f"  edges FOUND                   {tp:6d}   {found:8.4%}   of real edges")
    print(f"  edges MISSED                  {fn:6d}   {fn / (tp + fn):8.4%}")
    print(f"  FALSE ALARMS                  {fp:6d}   {fp / (tn + fp):8.4%}   of non-edges")
    print(f"  balanced accuracy             {0.5 * (found + clean):8.4%}   (coin flip = 50%)")
    print(f"  plain per-slot accuracy       {(tp + tn) / bits:8.4%}   (always-ABSENT = {(tn + fp) / bits:8.4%})")
    print()
    print(f"  self-link slots               {grand['self_slots']:6d}"
          f"   true self-edges {grand['self_true_present']}")
    print(f"  self-links called PRESENT     {grand['self_said_present']:6d}"
          f"   {grand['self_said_present'] / grand['self_slots']:8.4%} of them")
    print()
    print("=" * 100)
    print("DECODERS ON THE RECORDED SCORES")
    print("=" * 100)
    print()
    questions = grand["questions"]
    for label, key, bitkey in (("independent (the run's own rule)", "independent", None),
                               ("self-links forced ABSENT", "no_self", "no_self_bits"),
                               ("self-links ABSENT + declared cardinality", "both", "both_bits")):
        exact = grand[key] / questions
        cell = f"  bits {grand[bitkey] / bits:8.4%}" if bitkey else ""
        print(f"  {label:>40}   exact {exact:8.4%}  ({grand[key]} of {questions}){cell}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
