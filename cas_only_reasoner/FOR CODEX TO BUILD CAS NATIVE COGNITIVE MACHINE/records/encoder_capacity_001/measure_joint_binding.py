"""Would deciding the world ONCE instead of once per slot fix the reference slots?

Pure standard library. No torch, no device, no network, no target opened. It reads the frozen
receipts and rebuilds the public slot plans.

The defect this tests
---------------------
`records/encoder_capacity_001/TWO_DEFECTS_RESULT.md` measured that a `definition` answer cites
the focus world's declared `kind` and a **different world's** declared `function`, in 70 of 70
answers. Both references are declarations of the focus world: the query supplies no arguments
(`_ARGUMENTS["definition"]` is empty) and `answers.declaration_ref` builds every reference from
one `world_id`. The three `context` answers that were ever correct — all at cursor 0 — each
named the focus world and nothing else.

The cause is structural. `_forward` produces **one vector per slot** and the readout takes an
**independent argmax per slot**. So the same question — "which world is this about?" — is asked
at every world-typed slot and answered separately each time, with nothing forcing the answers to
agree.

The fix this measures
---------------------
Ask it once. For each question, take every slot whose alphabet is the world-alias codebook,
and decide them **jointly**: pick the world that maximises the summed score across those slots.
Then every world-typed slot in that question takes that one value. This is inference-time
constraint satisfaction drawn from the answer schema — all references to a world inside one
answer denote the same world — and it is not leakage: the machine still has to identify the
world, and the constraint says nothing about which world it is.

This script measures, from the recorded scores and the public slot plans, what that discipline
would produce. It needs no target because the focus world is public.

What it measures
----------------
    world-typed slots      how many slots in a question are a world identification
    independent pick       what each slot says on its own (the recorded behaviour)
    joint pick             what the slots say when decided together
    focus world rank       where the focus world sits in each slot's own ranking

    agreement              how often the independent picks already agree with each other
    focus rate             how often each discipline names the focus world

`focus rate` is NECESSARY and not SUFFICIENT: naming the focus world does not make the rest of
the answer right. The script reports the remaining defect's size alongside it and does not add
the two together.
"""

from __future__ import annotations

import json
from pathlib import Path
import math
import re
import sys
from collections import Counter, defaultdict

ARTIFACTS = (
    Path(__file__).resolve().parents[2]
    / "records/typed_matched_001/receipt_20260919_m/collected/results/artifacts"
)

#: A world-alias symbol, ``W0`` … ``W64``.
ALIAS = re.compile(r"^W\d+$")

#: Kinds whose answer is about exactly one world.
ONE_WORLD_KINDS = ("context", "definition", "parts", "edge_account", "reach")


def load(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def public_context() -> dict:
    """``record_id -> {"kind", "focus_alias", "world_slots"}`` from the frozen public material.

    ``world_slots`` maps slot_id to its symbol list, for slots whose alphabet is the world-alias
    codebook. The focus alias is read from the packet's own query, never guessed.
    """
    home = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(home / "research" / "CAS_META_2_COMPOSITION"))
    sys.path.insert(0, str(home))
    from cas_meta2.typed_teaching import course, input_frames, slots as slots_module, worker_contract

    frozen, _tokenizer, _source = worker_contract.load_material(home)
    out: dict[str, dict] = {}
    total = len(frozen["registry"])
    for index, row in enumerate(frozen["registry"], 1):
        record_id = row["record_id"]
        try:
            packet = course.model_packet(frozen, record_id)
            plan = slots_module.compile_slots(packet)
            frame = input_frames.compile_packet(packet)
        except Exception:  # noqa: BLE001 - reported, never guessed
            continue
        aliases = {a["world_id"]: a["alias"] for a in frame["aliases"]}
        focus_world = packet["record"]["query"]["focus_world_id"]
        world_slots = {
            slot["slot_id"]: tuple(slot["symbols"])
            for slot in plan["slots"]
            if slot["symbols"] and all(ALIAS.match(symbol) for symbol in slot["symbols"])
        }
        out[record_id] = {
            "kind": packet["record"]["query"]["kind"],
            "focus_alias": aliases.get(focus_world),
            "world_slots": world_slots,
        }
        if index % 200 == 0:
            print(f"  public context built: {index}/{total}", flush=True)
    return out


def ranks(scores: dict, symbol: str) -> int | None:
    """1-based rank of ``symbol`` in one slot's score dict, ties broken by symbol order."""
    if symbol not in scores:
        return None
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    for position, (name, _value) in enumerate(ordered, 1):
        if name == symbol:
            return position
    return None


def joint_pick(per_slot: dict, symbols: tuple) -> str:
    """The world maximising the summed score across the slots that must agree."""
    totals = {symbol: 0.0 for symbol in symbols}
    for scores in per_slot.values():
        for symbol in symbols:
            totals[symbol] += float(scores.get(symbol, 0.0))
    return max(sorted(totals), key=lambda symbol: totals[symbol])


def main() -> int:
    predictions = {row["record_id"]: row for row in load("final_predictions.json")["predictions"]}
    initial = {row["record_id"]: row for row in load("initial_predictions.json")["predictions"]}
    final_scoring = {row["record_id"]: row for row in load("final_scoring.json")["rows"]}
    print(f"predictions: {len(predictions)}   scored: {len(final_scoring)}")
    print("building the public slot plans and focus aliases...")
    public = public_context()
    print(f"  built: {len(public)}")
    print()

    for label, prediction_set in (
        ("after 160 updates (cursor 160)", predictions),
        ("before teaching (cursor 0)", initial),
    ):
        print("=" * 100)
        print(f"JOINT VERSUS INDEPENDENT WORLD DECISION — {label}")
        print("=" * 100)
        print()
        stats = defaultdict(lambda: Counter())
        rank_hist = defaultdict(lambda: Counter())
        for record_id, entry in public.items():
            kind = entry["kind"]
            if kind not in ONE_WORLD_KINDS:
                continue
            focus = entry["focus_alias"]
            world_slots = entry["world_slots"]
            prediction = prediction_set.get(record_id)
            bucket = stats[kind]
            bucket["questions"] += 1
            if focus is None or prediction is None or not world_slots:
                bucket["undecidable"] += 1
                continue
            bucket["readable"] += 1
            scores = prediction["scores"]
            per_slot = {}
            for slot_id, symbols in world_slots.items():
                slot_scores = scores.get(slot_id)
                if isinstance(slot_scores, dict) and slot_scores:
                    per_slot[slot_id] = slot_scores
            if not per_slot:
                bucket["no_scores"] += 1
                continue
            bucket["with_scores"] += 1
            symbols = tuple(sorted({s for group in world_slots.values() for s in group}))
            independent = {
                slot_id: max(sorted(slot_scores), key=lambda s: slot_scores[s])
                for slot_id, slot_scores in per_slot.items()
            }
            joint = joint_pick(per_slot, symbols)
            independent_focus = sum(1 for pick in independent.values() if pick == focus)
            bucket["slots"] += len(independent)
            bucket["slots_naming_focus"] += independent_focus
            bucket["all_slots_agree"] += 1 if len(set(independent.values())) == 1 else 0
            bucket["any_slot_names_focus"] += 1 if independent_focus else 0
            if joint == focus:
                bucket["joint_names_focus"] += 1
                bucket["joint_rescues"] += 1 if independent_focus < len(independent) else 0
            else:
                bucket["joint_wrong"] += 1
            for slot_id, slot_scores in per_slot.items():
                rank = ranks(slot_scores, focus)
                if rank is not None:
                    rank_hist[kind][min(rank, 6)] += 1
        print(
            f"{'kind':>15} {'q':>4} {'slots':>6} {'indep focus':>12} {'agree':>7}"
            f" {'any focus':>10} {'joint focus':>12} {'rescued':>8}"
        )
        print("-" * 100)
        for kind in sorted(stats):
            bucket = stats[kind]
            slots = bucket["slots"]
            print(
                f"{kind:>15} {bucket['with_scores']:4d} {slots:6d}"
                f" {bucket['slots_naming_focus']:6d} ({100 * bucket['slots_naming_focus'] / max(1, slots):5.1f}%)"
                f" {(100 * bucket['all_slots_agree'] / max(1, bucket['with_scores'])):6.1f}%"
                f" {(100 * bucket['any_slot_names_focus'] / max(1, bucket['with_scores'])):9.1f}%"
                f" {(100 * bucket['joint_names_focus'] / max(1, bucket['with_scores'])):11.1f}%"
                f" {bucket['joint_rescues']:8d}"
            )
        print()
        print("focus-world rank within each world-typed slot's own ranking:")
        print(f"{'kind':>15}" + "".join(f"{('# ' + str(r)):>8}" for r in range(1, 6)) + f"{'6+':>8}{'n':>7}")
        for kind in sorted(rank_hist):
            row = rank_hist[kind]
            total = sum(row.values())
            print(
                f"{kind:>15}"
                + "".join(f"{row[r]:8d}" for r in range(1, 6))
                + f"{row[6]:8d}{total:7d}"
            )
        print()
        readable = sum(stats[k]["with_scores"] for k in stats)
        independent_any = sum(stats[k]["any_slot_names_focus"] for k in stats)
        joint_any = sum(stats[k]["joint_names_focus"] for k in stats)
        rescues = sum(stats[k]["joint_rescues"] for k in stats)
        print(f"one-world kinds together: {readable} questions with world-typed slots")
        print(f"  independent picks name the focus world at some slot : {independent_any}  ({100 * independent_any / max(1, readable):.2f}%)")
        print(f"  joint decision names the focus world                : {joint_any}  ({100 * joint_any / max(1, readable):.2f}%)")
        print(f"  questions where the joint decision rescues disagreeing slots: {rescues}")
        print()

    print("=" * 100)
    print("WHAT THIS DOES AND DOES NOT SHOW")
    print("=" * 100)
    print()
    print(
        "It shows what a joint decision over the slots that must agree would name, measured from\n"
        "the recorded scores. It does not score those answers: the target is sealed, and naming\n"
        "the focus world is necessary but not sufficient. `edge_account` is the standing proof of\n"
        "that — 70 of 70 of its answers already name the focus world and none is correct, so a\n"
        "fix to the reference slots cannot move it. The remaining defect for the set-valued kinds\n"
        "is a separate one and is not measured here."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
