"""Probe: what shape is a real packet, for the world-reading ablation?

Pure Python. No torch, no device, no target opened. Builds packets from the frozen course.

Why
---
Round 26 established that `slots.score_decisions` composes jointly for exactly one kind
(`correspondence`) and per-slot independently for all seven others, and that the joint kind is
the one that works (93.18%-96.59%) while the five many-decision kinds sit at 0.00%-33.96%.

Before writing the ablation that asks "would a joint composer fix the other kinds?", I need to
know whether the packet even exposes the structure a joint composer would enumerate:
per-world declared edges, in a reference space comparable with the slot coordinates.
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
COMP = HOME / "research" / "CAS_META_2_COMPOSITION"
sys.path.insert(0, str(COMP))
sys.path.insert(0, str(HOME))

from cas_meta2.typed_teaching import course, slots, worker_contract  # noqa: E402

RECEIPT = HOME / "records/typed_matched_001/receipt_20260919_m"


def main() -> int:
    frozen, _tokenizer, _ = worker_contract.load_material(HOME)
    payload = json.loads(
        (RECEIPT / "collected/results/artifacts/final_predictions.json").read_text(encoding="utf-8")
    )
    predictions = payload["predictions"]
    print(f"predictions: {len(predictions)}")

    by_record = {row["record_id"]: row for row in predictions}
    print(f"distinct record_ids: {len(by_record)}")
    print()

    kinds = Counter()
    shown = 0
    for record_id, prediction in sorted(by_record.items()):
        packet = course.model_packet(frozen, record_id)
        query = packet["record"]["query"]
        kind = query["kind"]
        kinds[kind] += 1
        if kind != "edge_account" or shown >= 1:
            continue
        shown += 1

        print("=" * 100)
        print(f"RECORD {record_id}   kind {kind}")
        print("=" * 100)
        print()
        print("top-level packet keys:", list(packet))
        print("record keys:", list(packet["record"]))
        print("source keys:", list(packet["source"]))
        print("query:", json.dumps(query, sort_keys=True)[:400])
        print()
        bank = packet["source"]["bank"]
        print("bank keys:", list(bank))
        worlds = packet["source"]["worlds"]
        print("bank world_ids:", len(bank["world_ids"]))
        print("source.worlds:", len(worlds))
        first = worlds[0]
        print("world keys:", list(first))
        print("declarations keys:", list(first["declarations"]))
        print()
        print("--- world 0 declarations ---")
        print(json.dumps(first["declarations"], sort_keys=True)[:1200])
        print()
        print("--- world 0 nodes ---")
        print(json.dumps(first["nodes"], sort_keys=True)[:600])
        print()

        focus_id = query["focus_world_id"]
        focus = next(row for row in worlds if row["world_id"] == focus_id)
        print(f"focus_world_id {focus_id}")
        print("focus declarations:", json.dumps(focus["declarations"], sort_keys=True)[:1200])
        print()
        focus_nodes = sorted({node["ref"] for node in focus["nodes"]})
        print("focus node refs:", focus_nodes)
        print()
        other_nodes = set()
        for row in worlds:
            if row["world_id"] != focus_id:
                other_nodes |= {node["ref"] for node in row["nodes"]}
        print("other worlds' node refs (sample):", sorted(other_nodes)[:12])
        print(f"focus refs shared with other worlds: {len(set(focus_nodes) & other_nodes)} of {len(focus_nodes)}")
        print()

        plan = slots.compile_slots(packet)
        print("plan keys:", list(plan))
        print("slots:", len(plan["slots"]))
        for slot in plan["slots"][:4]:
            print("   ", {k: (v if k != "symbols" else list(v)) for k, v in slot.items() if k != "scope_alias"})
        print()
        print("decision_contract:", json.dumps(plan["decision_contract"], sort_keys=True)[:800])
        print()
        print("edges key present in declarations?", "edges" in focus["declarations"])

    print()
    print("=" * 100)
    print("KIND COUNTS (564 records)")
    print("=" * 100)
    for kind, count in sorted(kinds.items(), key=lambda row: -row[1]):
        print(f"{kind:>16} {count:6d}")
    print(f"{'TOTAL':>16} {sum(kinds.values()):6d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
