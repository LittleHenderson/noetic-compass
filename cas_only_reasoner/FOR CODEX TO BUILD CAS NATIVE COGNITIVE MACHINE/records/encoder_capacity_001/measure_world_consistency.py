"""Measure whether the recorded answers name the world the question was about.

Pure standard library. No torch, no device, no network. Reads only the frozen receipts of
`typed_matched_001/receipt_20260919_m` and the frozen public course material, both already on
disk.

The observation that prompted this
----------------------------------
Three of the eight question kinds score exactly zero before AND after teaching: `context`
(3/70 then 0/70), `definition` (0/70 then 0/70) and `edge_account` (0/70 then 0/70). That is
210 of 564 questions, 37% of the exposed course, never once answered.

Inspecting one `definition` answer shows a possible reason that needs no private target. The
answer cites two declarations:

    kind_ref     = world-7afc0b967.../decl/kind       <- the focus world
    function_ref = world-6f7b0ac1f.../decl/function   <- a DIFFERENT world

Both are declarations of **the same world**, because the question is about the focus world.
The machine named two different worlds for the two halves of one answer.

So this script asks a question that needs no target:

    How often does an answer name the world the question was about?

The focus world is public — it is a field of the packet's own query — so it is read, never
guessed. Naming it is NECESSARY and not SUFFICIENT: an answer can name the focus world and
still be wrong about the edges, the nodes, or the declarations. Both counts are reported, so a
kind that names the focus world in every answer while never being correct is visible as having
a different defect.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from collections import Counter, defaultdict

ARTIFACTS = (
    Path(__file__).resolve().parents[2]
    / "records/typed_matched_001/receipt_20260919_m/collected/results/artifacts"
)

#: ``world-`` followed by 64 hex characters, as the declarations are spelled.
WORLD = re.compile(r"world-[0-9a-f]{64}")

#: Kinds whose answer is about exactly one world. `analogy` and `correspondence` name two by
#: construction; `role_set` names none.
ONE_WORLD_KINDS = ("context", "definition", "parts", "edge_account", "reach")


def load(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def worlds_named(answer: dict) -> tuple[str, ...]:
    """Every distinct world identifier the answer's value mentions, in first-seen order."""
    value = answer.get("value")
    if value is None:
        return ()
    text = json.dumps(value, sort_keys=True)
    seen: list[str] = []
    for match in WORLD.findall(text):
        if match not in seen:
            seen.append(match)
    return tuple(seen)


def focus_worlds() -> dict[str, str]:
    """``record_id -> focus_world_id`` for the whole public registry.

    The focus world is public: it is a field of the packet's own query, and the packets are
    rebuilt from the frozen public material. It is read here, never guessed, so that
    "named the focus world" is a statement about the world the question was actually about.
    """
    home = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(home / "research" / "CAS_META_2_COMPOSITION"))
    sys.path.insert(0, str(home))
    from cas_meta2.typed_teaching import course, worker_contract

    frozen, _tokenizer, _source = worker_contract.load_material(home)
    out: dict[str, str] = {}
    total = len(frozen["registry"])
    for index, row in enumerate(frozen["registry"], 1):
        record_id = row["record_id"]
        try:
            packet = course.model_packet(frozen, record_id)
            out[record_id] = packet["record"]["query"]["focus_world_id"]
        except Exception:  # noqa: BLE001 - an unreadable packet is reported, not guessed
            continue
        if index % 200 == 0:
            print(f"  focus worlds read: {index}/{total}", flush=True)
    return out


def main() -> int:
    final = {row["record_id"]: row for row in load("final_predictions.json")["predictions"]}
    initial = {row["record_id"]: row for row in load("initial_predictions.json")["predictions"]}
    initial_scoring = {row["record_id"]: row for row in load("initial_scoring.json")["rows"]}
    final_scoring = {row["record_id"]: row for row in load("final_scoring.json")["rows"]}
    print(f"predictions at cursor 160: {len(final)}")
    print(f"predictions at cursor   0: {len(initial)}")
    print(f"scored rows: {len(final_scoring)}")
    print()
    print("reading the public focus world for every registry packet...")
    focus = focus_worlds()
    print(f"  focus worlds read: {len(focus)}")
    print()

    for label, prediction_set, scoring in (
        ("after 160 updates (cursor 160)", final, final_scoring),
        ("before teaching (cursor 0)", initial, initial_scoring),
    ):
        print("=" * 98)
        print(f"WORLD IDENTITY IN THE RECORDED ANSWERS — {label}")
        print("=" * 98)
        print()
        per_kind = defaultdict(lambda: Counter())
        for record_id, row in scoring.items():
            bucket = per_kind[row["kind"]]
            bucket["questions"] += 1
            bucket["correct"] += 1 if row["correct"] else 0
            prediction = prediction_set.get(record_id)
            true_world = focus.get(record_id)
            if prediction is None or true_world is None:
                bucket["unread"] += 1
                continue
            named = worlds_named(prediction["answer"])
            bucket["read"] += 1
            if not named:
                bucket["names_none"] += 1
            elif named == (true_world,):
                bucket["focus_only"] += 1
                bucket["focus_named"] += 1
                bucket["focus_named_correct"] += 1 if row["correct"] else 0
            elif true_world in named:
                bucket["focus_plus"] += 1
                bucket["focus_named"] += 1
                bucket["focus_named_correct"] += 1 if row["correct"] else 0
            else:
                bucket["other_only"] += 1
        print(
            f"{'kind':>15} {'focus':>7} {'focus+':>7} {'other':>7} {'none':>6}"
            f" {'focus%':>8} {'correct':>8} {'corr|focus':>11}"
        )
        print("-" * 98)
        for kind in sorted(per_kind):
            bucket = per_kind[kind]
            read = bucket["read"]
            rate = 100 * bucket["focus_named"] / read if read else 0.0
            mark = "" if kind in ONE_WORLD_KINDS else "   (two worlds expected)"
            print(
                f"{kind:>15} {bucket['focus_only']:7d} {bucket['focus_plus']:7d}"
                f" {bucket['other_only']:7d} {bucket['names_none']:6d}"
                f" {rate:7.2f}% {bucket['correct']:8d} {bucket['focus_named_correct']:11d}{mark}"
            )
        print()
        one_world = [k for k in per_kind if k in ONE_WORLD_KINDS]
        read = sum(per_kind[k]["read"] for k in one_world)
        named = sum(per_kind[k]["focus_named"] for k in one_world)
        correct = sum(per_kind[k]["correct"] for k in one_world)
        named_correct = sum(per_kind[k]["focus_named_correct"] for k in one_world)
        other_only = sum(per_kind[k]["other_only"] for k in one_world)
        none_named = sum(per_kind[k]["names_none"] for k in one_world)
        print(f"the five one-world kinds together ({read} readable answers):")
        print(f"  named the focus world at all    : {named}  ({100 * named / read:.2f}%)")
        print(f"    of those, correct             : {named_correct}  ({100 * named_correct / max(1, named):.2f}%)")
        print(f"  named only other worlds         : {other_only}  ({100 * other_only / read:.2f}%)")
        print(f"  named no world at all           : {none_named}  ({100 * none_named / read:.2f}%)")
        print(f"  correct, any naming             : {correct}  ({100 * correct / read:.2f}%)")
        missed = read - named
        if missed:
            print(
                f"  among answers that did NOT name the focus world, "
                f"{correct - named_correct} of {missed} are correct "
                f"({100 * (correct - named_correct) / missed:.2f}%)"
            )
        print()

    print("=" * 98)
    print("WHAT THIS MEASURES, AND WHAT IT DOES NOT")
    print("=" * 98)
    print()
    print(
        "Naming the focus world is NECESSARY and not SUFFICIENT. An answer can name the focus\n"
        "world and still be wrong about the edges, the nodes or the declarations. A kind that\n"
        "names the focus world in every answer while never being correct therefore has a\n"
        "different defect, and this measurement does not diagnose that one."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
