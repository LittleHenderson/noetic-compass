"""The systematic scan: every slot cell whose answer is constant across ALL worlds.

Pure Python. Standard library only. No torch, no device, no model, no training, no new run.

Why this round exists
---------------------
An independent audit pointed out that the fitted readout marks self-link slots (X -> X) PRESENT, and
that none is a real edge. Checked against the whole course that turned out to be structural: across
216,576 world declarations and 649,728 declared edges there are **zero** self-links. Forcing self-link
slots ABSENT, truth-free, moved `edge_account` from 0.0000% to 4.2857%.

**That was one instance of a general class.** A slot whose symbol is the same in every world is a slot
that needs no reader at all -- the composer can be told the answer once. This file finds every such
cell by construction rather than by luck, over all 64 worlds in the bank, and then measures what
hard-coding them is worth on the recorded scores.

How a cell is identified
------------------------
Not by question and not by world, but by a **structural key**: the kind, the field, and the slot's
coordinates reduced to node positions within its own world. `edge_account`'s key is the ordered pair
of node positions (i, j); `parts`' and `context`'s is the single position i, plus -- for `parts` --
the position of the supplied `whole`, because the answer depends on it. A cell is structural when
every world in the bank gives it the same symbol.

This is deliberately stricter than "constant in the exposed course": a cell that is constant over all
64 worlds' declarations is a property of the task, and it is safe to hard-code.
"""

from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter, defaultdict

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa: E402

RECEIPTS = HOME / "records/typed_matched_001"
KINDS = ("edge_account", "parts", "context")


def positions(world) -> dict:
    return {node["ref"]: at for at, node in enumerate(world["nodes"])}


def main() -> int:
    frozen_course, _tokenizer, _ = worker_contract.load_material(HOME)
    predictions = json.loads(
        (RECEIPTS / "receipt_20260919_m/collected/results/artifacts/final_predictions.json")
        .read_text(encoding="utf-8"))["predictions"]

    # ---- the scan: every world in the bank, every kind, every structural cell -----------------
    cells = defaultdict(Counter)
    for prediction in predictions:
        packet = course.model_packet(frozen_course, prediction["record_id"])
        query = packet["record"]["query"]
        kind = query["kind"]
        if kind not in KINDS:
            continue
        focus = next(world for world in packet["source"]["worlds"]
                     if world["world_id"] == query["focus_world_id"])
        whole = query["arguments"].get("whole")
        whole_at = positions(focus).get(whole) if whole else None
        focus_positions = positions(focus)
        for world in packet["source"]["worlds"]:
            index = positions(world)
            contains = {(edge["source"], edge["target"]) for edge in world["contains"]}
            participants = set(world["declarations"]["participants"])
            refs = [node["ref"] for node in world["nodes"]]
            for slot in slots.compile_slots(packet)["slots"]:
                if kind == "edge_account":
                    if slot["field"] != "edge":
                        continue
                    i = focus_positions[slot["coordinates"][0]]
                    j = focus_positions[slot["coordinates"][1]]
                    if i >= len(refs) or j >= len(refs):
                        continue
                    key = ("edge_account", "edge", (i, j))
                    symbol = "PRESENT" if (refs[i], refs[j]) in contains else "ABSENT"
                elif kind == "parts":
                    if slot["field"] != "node" or whole_at is None:
                        continue
                    i = focus_positions[slot["coordinates"][0]]
                    if i >= len(refs) or whole_at >= len(refs):
                        continue
                    key = ("parts", "node", (whole_at, i))
                    symbol = "PRESENT" if (refs[whole_at], refs[i]) in contains else "ABSENT"
                else:
                    if slot["field"] != "participant":
                        continue
                    i = focus_positions[slot["coordinates"][0]]
                    if i >= len(refs):
                        continue
                    key = ("context", "participant", i)
                    symbol = "PRESENT" if refs[i] in participants else "ABSENT"
                cells[key][symbol] += 1

    print("=" * 100)
    print("STRUCTURAL SCAN — cells with the SAME symbol in every world of the bank")
    print("=" * 100)
    print()
    constants = {}
    for key in sorted(cells):
        counts = cells[key]
        if len(counts) == 1:
            symbol = next(iter(counts))
            constants[key] = symbol
            print(f"  CONSTANT  {key!s:>40}  ->  {symbol:>8}   ({counts[symbol]} observations)")
    if not constants:
        print("  none")
    print()
    mixed = [key for key in cells if len(cells[key]) > 1]
    print(f"cells scanned: {len(cells)}   constant: {len(constants)}   mixed: {len(mixed)}")
    print()

    # ---- what hard-coding the constants is worth, on the recorded scores ---------------------
    grand = Counter()
    for receipt in sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/artifacts/final_predictions.json").is_file()
    ):
        artifacts = receipt / "collected/results/artifacts"
        preds = json.loads((artifacts / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        scoring = {row["record_id"]: row for row in
                   json.loads((artifacts / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}
        row = Counter()
        for prediction in preds:
            record_id = prediction["record_id"]
            kind = scoring[record_id]["kind"]
            if kind not in KINDS:
                continue
            packet = course.model_packet(frozen_course, record_id)
            query = packet["record"]["query"]
            plan = slots.compile_slots(packet)
            target = checker.derive_target(packet["source"], query)
            admissible = {json.dumps(item["value"], sort_keys=True) for item in target["admissible_answers"]}
            focus = next(world for world in packet["source"]["worlds"]
                         if world["world_id"] == query["focus_world_id"])
            focus_positions = positions(focus)
            whole = query["arguments"].get("whole")
            whole_at = focus_positions.get(whole) if whole else None
            key_counter = row.setdefault(kind, Counter()) if False else None
            row[f"{kind}_questions"] += 1

            def run(selected):
                decisions = {**prediction["decisions"], "selected": selected}
                try:
                    value = slots.assemble_answer(packet, decisions)["value"]
                except Exception:                                     # noqa: BLE001
                    return False
                return json.dumps(value, sort_keys=True) in admissible

            independent = {}
            for slot in plan["slots"]:
                per_symbol = prediction["scores"][slot["slot_id"]]
                independent[slot["slot_id"]] = max(slot["symbols"],
                                                   key=lambda symbol: per_symbol[symbol])
            row[f"{kind}_independent"] += 1 if run(independent) else 0

            hard = dict(independent)
            applied = 0
            for slot in plan["slots"]:
                if kind == "edge_account" and slot["field"] == "edge":
                    i = focus_positions[slot["coordinates"][0]]
                    j = focus_positions[slot["coordinates"][1]]
                    key = ("edge_account", "edge", (i, j))
                elif kind == "parts" and slot["field"] == "node" and whole_at is not None:
                    i = focus_positions[slot["coordinates"][0]]
                    key = ("parts", "node", (whole_at, i))
                elif kind == "context" and slot["field"] == "participant":
                    i = focus_positions[slot["coordinates"][0]]
                    key = ("context", "participant", i)
                else:
                    continue
                if key in constants:
                    hard[slot["slot_id"]] = constants[key]
                    applied += 1
            row[f"{kind}_hardcoded"] += 1 if run(hard) else 0
            row[f"{kind}_applied"] += applied
        for key, value in row.items():
            grand[key] += value

    print("=" * 100)
    print("WHAT HARD-CODING THE STRUCTURAL CONSTANTS IS WORTH — recorded scores, six runs")
    print("=" * 100)
    print()
    print(f"{'kind':>15} {'q':>5} {'independent':>13} {'constants applied':>13} {'hard-coded':>13} {'lift':>10}")
    print("-" * 100)
    for kind in KINDS:
        questions = grand[f"{kind}_questions"]
        base = grand[f"{kind}_independent"] / questions
        hard = grand[f"{kind}_hardcoded"] / questions
        print(f"{kind:>15} {questions:5d} {base:12.4%} {grand[f'{kind}_applied']:13d}"
              f" {hard:12.4%} {hard - base:+10.4%}")
    print()
    print("A cell is CONSTANT when every one of the 64 worlds in the bank gives it the same symbol.")
    print("Those are properties of the task, not of the run, so hard-coding them costs nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
