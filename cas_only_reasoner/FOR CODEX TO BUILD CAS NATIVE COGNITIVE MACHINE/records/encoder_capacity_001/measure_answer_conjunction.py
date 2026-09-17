"""How many decisions does each question kind actually require, and from what alphabets?

Pure standard library. No torch, no device, no network. The slot plan is a deterministic
function of the public packet, so this measurement needs no targets and no model.

Why this matters
----------------
The recorded per-kind accuracy on the exposed 564-question course, after 160 updates:

    correspondence  82/88    93.18%
    reach           81/107   75.70%
    parts           12/53    22.64%
    analogy         11/70    15.71%
    role_set         3/36     8.33%
    context          0/70     0.00%
    definition       0/70     0.00%
    edge_account     0/70     0.00%

That ordering is not random and it is not explained by "hard" versus "easy". It lines up with
how the answer is assembled. A scored question is right only when the entire assembled answer
matches, so a kind whose answer requires 49 independent binary decisions is a conjunction over
49 events, while a kind whose answer is one choice from a candidate list is a single event.

This script measures that structure from the public slot plans:

    slots            how many decisions the assembled answer requires
    alphabets        the size of the choice at each slot
    free bits        sum of log2(alphabet) over slots — the least information the answer carries
    and, for the binary-heavy kinds, the conjunction depth

`free bits` is a lower bound on what has to be got right, and it is reported as a lower bound.
It is not an accuracy prediction: nothing here models how well any slot is learned, and
converting these numbers into a predicted score would need a per-slot accuracy that has not
been measured.
"""

from __future__ import annotations

import json
from pathlib import Path
import math
import sys
from collections import Counter, defaultdict

#: The eight kinds, in the order the study reports them.
KINDS = (
    "correspondence", "reach", "parts", "analogy",
    "role_set", "context", "definition", "edge_account",
)

#: Recorded exact-match accuracy on the exposed course at cursor 160, from
#: `final_scoring.json`. Quoted here so the structural numbers can be read beside them.
RECORDED_AFTER = {
    "correspondence": (82, 88),
    "reach": (81, 107),
    "parts": (12, 53),
    "analogy": (11, 70),
    "role_set": (3, 36),
    "context": (0, 70),
    "definition": (0, 70),
    "edge_account": (0, 70),
}

RECORDED_BEFORE = {
    "correspondence": (0, 88),
    "reach": (25, 107),
    "parts": (6, 53),
    "analogy": (5, 70),
    "role_set": (0, 36),
    "context": (3, 70),
    "definition": (0, 70),
    "edge_account": (0, 70),
}


def plan_structure() -> dict:
    """``record_id -> {"kind", "slots", "alphabets", "free_bits", "binary"}`` for the registry."""
    home = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(home / "research" / "CAS_META_2_COMPOSITION"))
    sys.path.insert(0, str(home))
    from cas_meta2.typed_teaching import course, slots as slots_module, worker_contract

    frozen, _tokenizer, _source = worker_contract.load_material(home)
    out: dict[str, dict] = {}
    total = len(frozen["registry"])
    for index, row in enumerate(frozen["registry"], 1):
        record_id = row["record_id"]
        try:
            packet = course.model_packet(frozen, record_id)
            plan = slots_module.compile_slots(packet)
        except Exception:  # noqa: BLE001 - reported, never guessed
            continue
        alphabets = [len(slot["symbols"]) for slot in plan["slots"]]
        out[record_id] = {
            "kind": packet["record"]["query"]["kind"],
            "slots": len(alphabets),
            "alphabets": alphabets,
            "free_bits": math.fsum(math.log2(size) for size in alphabets if size > 1),
            "binary": sum(1 for size in alphabets if size == 2),
            "wide": sum(1 for size in alphabets if size >= 8),
        }
        if index % 200 == 0:
            print(f"  slot plans built: {index}/{total}", flush=True)
    return out


def main() -> int:
    scoring = {
        row["record_id"]: row["kind"]
        for row in json.loads(
            (
                Path(__file__).resolve().parents[2]
                / "records/typed_matched_001/receipt_20260919_m/collected/results"
                / "artifacts/final_scoring.json"
            ).read_text(encoding="utf-8")
        )["rows"]
    }
    print(f"scored questions: {len(scoring)}")
    print("building the public slot plan for every registry packet...")
    structure = plan_structure()
    print(f"  slot plans built: {len(structure)}")
    print()

    per_kind: dict[str, list[dict]] = defaultdict(list)
    for record_id, kind in scoring.items():
        entry = structure.get(record_id)
        if entry is not None:
            per_kind[kind].append(entry)

    print("=" * 104)
    print("WHAT EACH KIND'S ANSWER REQUIRES")
    print("=" * 104)
    print()
    print(
        f"{'kind':>15} {'n':>4} {'slots med':>10} {'slots max':>10} {'binary med':>11}"
        f" {'wide med':>9} {'bits med':>9} {'bits max':>9} {'before':>9} {'after':>9}"
    )
    print("-" * 104)

    def median(values):
        ordered = sorted(values)
        return ordered[len(ordered) // 2] if ordered else 0

    summary = {}
    for kind in KINDS:
        entries = per_kind.get(kind, [])
        if not entries:
            continue
        slots = [e["slots"] for e in entries]
        binary = [e["binary"] for e in entries]
        wide = [e["wide"] for e in entries]
        bits = [e["free_bits"] for e in entries]
        before = RECORDED_BEFORE.get(kind)
        after = RECORDED_AFTER.get(kind)
        summary[kind] = {
            "n": len(entries),
            "slots_median": median(slots),
            "slots_max": max(slots),
            "binary_median": median(binary),
            "wide_median": median(wide),
            "bits_median": median(bits),
            "bits_max": max(bits),
        }
        print(
            f"{kind:>15} {len(entries):4d} {median(slots):10d} {max(slots):10d}"
            f" {median(binary):11d} {median(wide):9d} {median(bits):9.1f} {max(bits):9.1f}"
            f" {100 * before[0] / before[1]:8.2f}% {100 * after[0] / after[1]:8.2f}%"
        )

    print()
    print("=" * 104)
    print("THE STRUCTURE AGAINST THE OUTCOME")
    print("=" * 104)
    print()
    print(
        f"{'kind':>15} {'decisions (median)':>19} {'binary share':>13} {'free bits':>10}"
        f" {'after':>9}   reading"
    )
    print("-" * 104)
    for kind in KINDS:
        if kind not in summary:
            continue
        row = summary[kind]
        after = RECORDED_AFTER[kind]
        rate = 100 * after[0] / after[1]
        share = row["binary_median"] / row["slots_median"] if row["slots_median"] else 0.0
        if row["slots_median"] <= 2 and row["binary_median"] <= 1:
            reading = "one decision from a candidate list"
        elif share >= 0.9:
            reading = f"conjunction over ~{row['binary_median']} binary decisions"
        elif row["wide_median"] >= 2:
            reading = f"{row['wide_median']} wide identifications + assembly"
        else:
            reading = "mixed assembly"
        print(
            f"{kind:>15} {row['slots_median']:19d} {100 * share:12.0f}%"
            f" {row['bits_median']:10.1f} {rate:8.2f}%   {reading}"
        )

    print()
    print("=" * 104)
    print("READING")
    print("=" * 104)
    print()
    print(
        "The two kinds that work are the two whose answer is a single decision from a candidate\n"
        "list. The kinds that fail are the ones whose answer is a conjunction of many decisions,\n"
        "or requires several independent wide identifications, or both. `edge_account` is the\n"
        "extreme case: its answer is a conjunction of edge-presence decisions over all node\n"
        "pairs, every one of which must be right, and it has never been answered correctly.\n"
        "\n"
        "This is a statement about the shape of the task, measured from public data. It is not\n"
        "an accuracy model: `free bits` is a lower bound on the information the answer carries,\n"
        "not a prediction of how often the machine will get it right, and no per-slot accuracy\n"
        "has been measured here."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
