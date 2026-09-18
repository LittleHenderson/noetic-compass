"""The one-world identity constraint, applied to `context` and `edge_account`, truth-free.

Pure Python. Standard library only. No torch, no device, no model, no training, no new run.
Reads the recorded score table and the frozen course. Targets are re-derived by the project's own
checker from the public snapshot and are used ONLY to score the result, never inside a decoder.

The gap this closes
-------------------
Round 32 lifted `context` 0.0000% -> 32.6190% by enforcing the declared participant cardinality — but
that arm **held `setting_ref` at the truth**, and the machine's own `setting_ref` is worth 0.0000% on
those questions. So the result was truth-assisted and worth no score.

Round 33 then showed the **joint candidate mechanism** works on a non-`correspondence` kind:
`definition`'s `FOCUS_WORLD_DECLARATION_IDENTITY` — the three fields are ONE world's declaration
triple, not three free choices — lifted it 0.0000% -> 10.2381%, truth-free, by enumerating the bank
and scoring each world's implied triple.

**`context` carries the same declaration.** `answers.answer_space` sets the setting from
`declaration_ref(focus.world_id, "setting")` and the participants from
`sorted(focus["declarations"]["participants"])` — both are the FOCUS world's own declaration. So the
same joint move applies, and it fixes both fields together with no truth at all.

`edge_account` is the other kind whose whole answer is one world's declaration — `focus["contains"]` —
so the same decoder is applied there, as the test of whether the mechanism is general or specific to
kinds whose scores carry signal.

The node correspondence
-----------------------
Candidate worlds have their own nodes. The only correspondence the packet offers is the alias
namespace, in which every world's nodes are n0..n3 in order. The decoders below map by that index and
say so; no graph isomorphism is solved and none is claimed.
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
KINDS = ("context", "edge_account")


def node_index(world) -> dict:
    return {node["ref"]: at for at, node in enumerate(world["nodes"])}


def main() -> int:
    frozen_course, _tokenizer, _ = worker_contract.load_material(HOME)
    receipts = sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/artifacts/final_predictions.json").is_file()
    )
    print(f"runs: {len(receipts)}", flush=True)

    totals = {}
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        predictions = json.loads((artifacts / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        scoring = {row["record_id"]: row for row in
                   json.loads((artifacts / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}
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
            admissible = {json.dumps(item["value"], sort_keys=True) for item in target["admissible_answers"]}
            scores = prediction["scores"]
            focus = next(world for world in packet["source"]["worlds"]
                         if world["world_id"] == query["focus_world_id"])
            aliases = {world["world_id"]: world for world in plan["aliases"]["worlds"]}
            row = rows.setdefault(kind, Counter())
            row["questions"] += 1

            def run(selected):
                decisions = {**prediction["decisions"], "selected": selected}
                try:
                    value = slots.assemble_answer(packet, decisions)["value"]
                except Exception:                                     # noqa: BLE001
                    return False
                return json.dumps(value, sort_keys=True) in admissible

            independent = {}
            for slot in plan["slots"]:
                per_symbol = scores[slot["slot_id"]]
                independent[slot["slot_id"]] = max(slot["symbols"],
                                                   key=lambda symbol: per_symbol[symbol])
            row["independent"] += 1 if run(independent) else 0

            # Field-level accuracy of the recorded machine, for the field the joint decoder leans on.
            if kind == "context":
                for slot in plan["slots"]:
                    if slot["field"] == "setting_ref":
                        row["setting_slots"] += 1
                        # the truth's setting symbol, for diagnosis only
                        from cas_meta2.typed_teaching import answers as _a
                        for world in plan["aliases"]["worlds"]:
                            if _a.declaration_ref(world["world_id"], "setting") == target["admissible_answers"][0]["value"]["setting_ref"]:
                                row["setting_hits"] += 1 if independent[slot["slot_id"]] == world["alias"] else 0

            # ---- the one-world joint decoder -------------------------------------------------
            best, best_score = None, None
            for world in packet["source"]["worlds"]:
                other = aliases[world["world_id"]]
                index = node_index(world)
                declared_participants = set(world["declarations"]["participants"])
                contains = {(edge["source"], edge["target"]) for edge in world["contains"]}
                implied, total = {}, 0.0
                ok = True
                for slot in plan["slots"]:
                    if kind == "context":
                        if slot["field"] == "setting_ref":
                            symbol = other["alias"]
                        else:
                            at = node_index(focus)[slot["coordinates"][0]]
                            ref = world["nodes"][at]["ref"] if at < len(world["nodes"]) else None
                            if ref is None:
                                ok = False
                                break
                            symbol = "PRESENT" if ref in declared_participants else "ABSENT"
                    else:
                        i = node_index(focus)[slot["coordinates"][0]]
                        j = node_index(focus)[slot["coordinates"][1]]
                        if i >= len(world["nodes"]) or j >= len(world["nodes"]):
                            ok = False
                            break
                        pair = (world["nodes"][i]["ref"], world["nodes"][j]["ref"])
                        symbol = "PRESENT" if pair in contains else "ABSENT"
                    if symbol not in slot["symbols"]:
                        ok = False
                        break
                    implied[slot["slot_id"]] = symbol
                    total += scores[slot["slot_id"]][symbol]
                if not ok:
                    continue
                if best_score is None or total > best_score:
                    best, best_score = implied, total
            if best is None:
                continue
            row["joint"] += 1 if run(best) else 0

        totals[receipt.name] = rows

    print()
    print("=" * 100)
    print("ONE-WORLD JOINT DECODER — recorded scores, six runs, NO truth in any decoder")
    print("=" * 100)
    print()
    print(f"{'run':>22} {'kind':>14} {'q':>4} {'independent':>13} {'joint':>10} {'lift':>10}"
          f" {'setting slot':>13}")
    print("-" * 100)
    grand = {}
    for name in sorted(totals):
        for kind in KINDS:
            row = totals[name].get(kind)
            if not row or "joint" not in row:
                continue
            questions = row["questions"]
            base, joint = row["independent"] / questions, row["joint"] / questions
            setting = (f"{row['setting_hits'] / row['setting_slots']:.4%}"
                       if row.get("setting_slots") else "")
            print(f"{name:>22} {kind:>14} {questions:4d} {base:12.4%} {joint:9.4%} {joint - base:+10.4%}"
                  f" {setting:>13}")
            agg = grand.setdefault(kind, Counter())
            for key in ("questions", "independent", "joint", "setting_slots", "setting_hits"):
                agg[key] += row.get(key, 0)
        print()
    print("-" * 100)
    for kind in KINDS:
        agg = grand.get(kind)
        if not agg:
            continue
        base, joint = agg["independent"] / agg["questions"], agg["joint"] / agg["questions"]
        setting = f"{agg['setting_hits'] / agg['setting_slots']:.4%}" if agg["setting_slots"] else ""
        print(f"{'ALL SIX RUNS':>22} {kind:>14} {agg['questions']:4d} {base:12.4%} {joint:9.4%}"
              f" {joint - base:+10.4%} {setting:>13}")
    print()
    print("joint = enumerate the bank, score each world's implied answer, take the argmax")
    print("setting slot = the recorded machine's per-slot accuracy on context.setting_ref")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
