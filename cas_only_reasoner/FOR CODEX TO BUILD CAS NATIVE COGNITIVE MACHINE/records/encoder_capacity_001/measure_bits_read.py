"""Does the machine read the bits it is asked for?

Pure Python. No torch, no device. Packets rebuilt from the frozen course; targets re-derived by
the project's own checker from the public snapshot only.

The question this settles
------------------------
Round 26 measured the central result as exact-answer accuracy per decision shape:

    ONE DECISION                      (correspondence, reach, analogy)   11.32% -> 65.66%
    MANY INDEPENDENT DECISIONS        (edge_account, role_set, parts,
     ABOUT ONE ENTITY                  context, definition)               3.01% ->  5.02%

and three of those five kinds (`context`, `definition`, `edge_account`) scored 0.00% — not one
correct answer in 1,260 attempts. The round-26 record could say that only as a headline. An exact
match rate of 0.00% is compatible with two very different machines:

  (a) the machine reads most of the bits and loses the answer in composition, or
  (b) the machine reads none of the bits and is guessing.

Every composition fix on the table — extending the joint candidate branch, snapping to an
entity-consistent completion, re-weighting — only helps under (a). Under (b) no composer can help,
because a composer cannot invent information the readout never carried.

What changed to make this measurable
------------------------------------
The answer to every many-decision question is a **field of the packet that the learner can see**.
For `edge_account` the checker reads `focus["contains"]` and the slots are exactly the sixteen
directed pairs of the focus's four nodes. For `parts`, `role_set` and the `context` participants it
is the same shape: N binary slots whose PRESENT set IS the answer. That makes per-bit scoring
possible with no private material at all — the true symbol for each slot follows from the derived
answer by the same mapping `assemble_answer` uses, in the same direction.

So this measures, per kind:

    selected  vs truth, slot by slot      -- how many of the N bits the decoder chose correctly
    argmax    vs truth, slot by slot      -- the same for the raw readout argmax
    whole-answer matches                  -- for both, to show the two rules coincide here
    bits-correct histogram                -- 0..N, to separate "reads most" from "reads none"

and validates the whole pipeline against the run's own record: assembling the derived truth
through `slots.assemble_answer` must reproduce the recorded per-question `correct` flag exactly.
If it does not, the derivation is wrong and nothing below it may be read.
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

from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa: E402

RECEIPTS = HOME / "records/typed_matched_001"

#: Kinds whose answer is an N-bit PRESENT set over N independent binary slots.
BINARY = ("edge_account", "parts", "role_set", "context")

#: Slots that carry an N-bit set, by kind: field name -> True if that field's PRESENT set is scored.
SET_FIELD = {
    "edge_account": "edge",
    "parts": "node",
    "role_set": "role",
    "context": "participant",
}


def true_symbols(kind: str, plan: dict, answer: dict) -> dict:
    """The true symbol of every set-valued slot, read out of the derived answer.

    Mirrors `slots.assemble_answer` exactly, in the opposite direction. Only the set-valued
    fields are returned; alias-valued fields (`context.setting_ref`, `definition.*`) are not bits.
    """
    value = answer["value"]
    field = SET_FIELD[kind]
    if kind == "edge_account":
        present = {tuple(sorted((row["source"], row["target"]))) for row in value["edges"]}
    elif kind == "parts":
        present = set(value["nodes"])
    elif kind == "role_set":
        present = set(value["roles"])
    elif kind == "context":
        present = set(value["participants"])
    else:
        raise AssertionError(kind)
    out = {}
    for slot in plan["slots"]:
        if slot["field"] != field:
            continue
        if kind == "edge_account":
            key = tuple(sorted((slot["coordinates"][0], slot["coordinates"][1])))
        else:
            key = slot["coordinates"][0]
        out[slot["slot_id"]] = "PRESENT" if key in present else "ABSENT"
    return out


def main() -> int:
    frozen, _tokenizer, _ = worker_contract.load_material(HOME)
    wanted = [row for row in sys.argv[1:] if not row.startswith("-")]
    receipts = sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/artifacts/final_predictions.json").is_file()
        and (not wanted or directory.name in wanted)
    )
    print(f"runs: {[row.name for row in receipts]}", flush=True)
    print(flush=True)

    summary = {}
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        predictions = json.loads((artifacts / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        scoring = {row["record_id"]: row for row in
                   json.loads((artifacts / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}

        agree = disagree = 0
        per_kind = {}
        for prediction in predictions:
            record_id = prediction["record_id"]
            packet = course.model_packet(frozen, record_id)
            query = packet["record"]["query"]
            kind = query["kind"]
            if kind not in BINARY:
                # `derive_target` for `analogy` and `correspondence` runs an exhaustive
                # isomorphism search over all 64 worlds; those kinds carry no binary slots and
                # are out of scope here.
                continue
            plan = slots.compile_slots(packet)
            target = checker.derive_target(packet["source"], query)
            truth = target["admissible_answers"][0]

            # Pipeline validation: the answer this file derived must, when compared to the answer
            # the machine submitted, reproduce the run's own correctness flag for every question.
            # Anything else means the derivation is wrong and nothing below it may be read.
            derived_ok = (json.dumps(truth, sort_keys=True)
                          == json.dumps(prediction["answer"], sort_keys=True))
            if derived_ok == scoring[record_id]["correct"]:
                agree += 1
            else:
                disagree += 1

            truth_symbols = true_symbols(kind, plan, truth)
            selected = prediction["decisions"]["selected"]
            scores = prediction["scores"]
            slot_ids = sorted(truth_symbols)
            row = per_kind.setdefault(kind, {
                "questions": 0, "bits": 0, "selected_hits": 0, "argmax_hits": 0,
                "selected_exact": 0, "argmax_exact": 0, "hist": Counter(), "all_absent": 0,
                "truth_present": 0, "slot_counts": Counter(), "hits_if_absent": 0, "hits_if_present": 0,
            })
            row["questions"] += 1
            row["slot_counts"][len(slot_ids)] += 1
            row["all_absent"] += 1 if not any(v == "PRESENT" for v in truth_symbols.values()) else 0
            row["truth_present"] += sum(1 for v in truth_symbols.values() if v == "PRESENT")
            got_selected = got_argmax = 0
            for slot_id in slot_ids:
                want = truth_symbols[slot_id]
                row["bits"] += 1
                row["selected_hits"] += 1 if selected.get(slot_id) == want else 0
                # What a constant decoder would have earned on this same slot.
                row["hits_if_absent"] += 1 if want == "ABSENT" else 0
                row["hits_if_present"] += 1 if want == "PRESENT" else 0
                per_symbol = scores[slot_id]
                best = max(per_symbol.values())
                pick = sorted(name for name, value in per_symbol.items() if value == best)[0]
                row["argmax_hits"] += 1 if pick == want else 0
                got_selected += 1 if selected.get(slot_id) == want else 0
                got_argmax += 1 if pick == want else 0
            # Bucketed by fraction correct, because slot counts vary (9 or 16 for edge_account).
            row["hist"][round(10 * got_selected / len(slot_ids))] += 1
            row["selected_exact"] += 1 if got_selected == len(slot_ids) else 0
            row["argmax_exact"] += 1 if got_argmax == len(slot_ids) else 0
        summary[receipt.name] = {"per_kind": per_kind, "agree": agree, "disagree": disagree,
                                 "questions": len(predictions)}
        print(f"{receipt.name}: pipeline validation agree={agree} disagree={disagree}"
              f"  of {sum(row['questions'] for row in per_kind.values())} binary questions"
              f" ({len(predictions)} total)", flush=True)
    print()

    print("=" * 112)
    print("BITS READ PER KIND, FINAL CURSOR — the distinction between 'reads most' and 'reads none'")
    print("=" * 112)
    print()
    header = (f"{'run':>22} {'kind':>15} {'q':>4} {'bits':>6} {'selected':>10} {'argmax':>10}"
              f" {'exact(sel)':>11} {'chance':>8} {'always-A':>9} {'always-P':>9} {'vs best const':>14}")
    print(header)
    print("-" * 112)
    for name in sorted(summary):
        for kind in BINARY:
            row = summary[name]["per_kind"].get(kind)
            if not row:
                continue
            bits, questions = row["bits"], row["questions"]
            present = row["truth_present"] / bits
            chance = present * present + (1 - present) * (1 - present)
            const = max(row["hits_if_absent"], row["hits_if_present"]) / bits
            print(f"{name:>22} {kind:>15} {questions:4d} {bits:6d}"
                  f" {row['selected_hits'] / bits:9.4%} {row['argmax_hits'] / bits:9.4%}"
                  f" {row['selected_exact'] / questions:10.4%}"
                  f" {chance:8.4%} {row['hits_if_absent'] / bits:9.4%} {row['hits_if_present'] / bits:9.4%}"
                  f" {row['selected_hits'] / bits - const:+13.4%}")
        print()
    print("chance       = p^2 + (1-p)^2 for p = the truth PRESENT rate of that kind's slots")
    print("always-A/P   = what a decoder that always answered that symbol would have earned")
    print("vs best const= the machine's per-bit accuracy minus the better of those two constants")
    print()

    print("=" * 112)
    print("BITS-CORRECT HISTOGRAM, FINAL CURSOR, ALL RUNS — bucketed by fraction of the question's slots")
    print("=" * 112)
    print()
    for kind in BINARY:
        totals = Counter()
        entries = 0
        for name in sorted(summary):
            row = summary[name]["per_kind"].get(kind)
            if not row:
                continue
            totals.update(row["hist"])
            entries += row["questions"]
        if not entries:
            continue
        counts = summary["receipt_20260919_m"]["per_kind"][kind]["slot_counts"]
        print(f"{kind}   ({entries} questions, slot counts {dict(sorted(counts.items()))})")
        for bucket in sorted(totals):
            count = totals[bucket]
            bar = "#" * int(round(50 * count / entries))
            print(f"   {bucket * 10:3d}% correct  {count:4d}  {count / entries:7.2%}  {bar}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
