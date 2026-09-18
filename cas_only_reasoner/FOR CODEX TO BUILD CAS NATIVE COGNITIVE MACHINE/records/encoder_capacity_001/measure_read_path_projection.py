"""What would a read path buy? Exact-answer projection from a memoriser, no leakage by question.

Pure Python. Standard library plus the project's pure modules. No torch, no device, no learned
weights, no training, no run.

Why this is the number that matters
-----------------------------------
`receipt_20260919_m` records, on the exposed course:

    ONE DECISION                    265 q   11.32% -> 65.66%
    MANY DECISIONS ABOUT ONE ENTITY 299 q    3.01% ->  5.02%

and on the held-out development panel (59 questions, zero overlap with the exposed course) the
machine never gets a single question right: 0/59 at cursor 0 and 0/59 at cursor 160.

Meanwhile `measure_binding_variants.py` measured that a plain lookup keyed on (world alias,
coordinates), fitted on four fifths of the questions and scored on the held-out fifth, recovers the
per-bit labels at **96.4508% for `edge_account`** and **98.5926% for `context`**, while the trained
machine reads the same bits at 53.5471% and 40.8240%. A linear probe on the frozen slot vector
reaches **96.3758%** on `context`.

So the per-bit information is in the slot's name and is trivially recoverable. This file converts
that into the number that decides whether the fix is worth a GPU run: **exact-answer accuracy.**

Method
------
Five folds by question. Fit on four fifths of the exposed course, predict every slot of the held-out
fifth, assemble the answer with the project's own `slots.assemble_answer`, compare to the answer the
project's own `checker.derive_target` derives from the public snapshot. Nothing from the held-out
fifth enters the fit, and the truth is never a fit input.

The projection's regime, stated plainly
---------------------------------------
A memoriser needs the (world, field, coordinates) key to have been exposed. So this measures the
regime **seen world, unseen question** — which is exactly the regime of the exposed course and of
the retention panel. It is **not** a claim about unseen worlds, and it is not a claim about the
development panel, whose packets are not in the frozen course and whose targets therefore cannot be
derived at all.

It is also a **lower bound** on a read path, not the read path. `focus["contains"]` and
`focus["declarations"]` are visible fields of the test packet, so a machine that reads them needs no
exposure whatever. Where the memoriser fails for want of coverage, a read path still succeeds.
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
COMP = HOME / "research" / "CAS_META_2_COMPOSITION"
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(COMP))

from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa: E402

RECEIPT = HOME / "records/typed_matched_001/receipt_20260919_m"
FOLDS = 5


def slot_key(slot) -> tuple:
    return (slot["field"], slot["group"], slot["scope_alias"], tuple(slot["coordinates"]))


def main() -> int:
    frozen_course, _tokenizer, _ = worker_contract.load_material(HOME)
    predictions = json.loads(
        (RECEIPT / "collected/results/artifacts/final_predictions.json").read_text(encoding="utf-8")
    )["predictions"]

    # One pass: every question's plan, truth, and the machine's own decision, cached.
    cases = []
    for index, prediction in enumerate(predictions):
        packet = course.model_packet(frozen_course, prediction["record_id"])
        query = packet["record"]["query"]
        plan = slots.compile_slots(packet)
        truth = checker.derive_target(packet["source"], query)["admissible_answers"][0]
        cases.append({"fold": index % FOLDS, "kind": plan["kind"], "packet": packet, "plan": plan,
                      "truth": truth["value"], "recorded": prediction["decisions"],
                      "recorded_value": prediction["answer"]["value"]})
    print(f"questions: {len(cases)}", flush=True)

    per_kind = defaultdict(Counter)
    for fold in range(FOLDS):
        table = defaultdict(Counter)
        fallback = defaultdict(Counter)
        for case in cases:
            if case["fold"] == fold:
                continue
            selected = case["recorded"]["selected"]
            for slot in case["plan"]["slots"]:
                if slot["slot_id"] not in selected:
                    continue
                table[(case["kind"],) + slot_key(slot)][selected[slot["slot_id"]]] += 1
                fallback[case["kind"]][selected[slot["slot_id"]]] += 1

        for case in cases:
            if case["fold"] != fold:
                continue
            kind, plan = case["kind"], case["plan"]
            row = per_kind[kind]
            row["questions"] += 1
            row["recorded"] += 1 if (json.dumps(case["recorded_value"], sort_keys=True)
                                     == json.dumps(case["truth"], sort_keys=True)) else 0
            if kind == "correspondence":
                # Candidate-valued: a per-slot lookup cannot express it. Report it, do not score it.
                row["skipped"] += 1
                continue
            guess = dict(case["recorded"]["selected"])
            for slot in plan["slots"]:
                key = (kind,) + slot_key(slot)
                if key in table:
                    guess[slot["slot_id"]] = table[key].most_common(1)[0][0]
                    row["seen"] += 1
                else:
                    guess[slot["slot_id"]] = fallback[kind].most_common(1)[0][0]
                row["coverable"] += 1
            decisions = {**case["recorded"], "selected": guess}
            try:
                assembled = slots.assemble_answer(case["packet"], decisions)
            except Exception:                                        # noqa: BLE001
                row["unassemblable"] += 1
                continue
            row["lookup"] += 1 if (json.dumps(assembled["value"], sort_keys=True)
                                   == json.dumps(case["truth"], sort_keys=True)) else 0
            for slot in plan["slots"]:
                row["slot_hits"] += 1 if guess[slot["slot_id"]] == case["recorded"]["selected"].get(slot["slot_id"]) else 0

    print()
    print("=" * 106)
    print("EXACT-ANSWER ACCURACY — 5-fold by question, fit on four fifths of the exposed course")
    print("=" * 106)
    print()
    print(f"{'kind':>15} {'q':>5} {'recorded':>10} {'lookup':>10} {'lift':>9}"
          f" {'key coverage':>13} {'slot agreement':>15}")
    print("-" * 106)
    one = Counter()
    many = Counter()
    for kind in sorted(per_kind, key=lambda name: -per_kind[name]["questions"]):
        row = per_kind[kind]
        questions = row["questions"]
        scored = questions - row["skipped"]
        lookup = row["lookup"] / scored if scored else float("nan")
        rec = row["recorded"] / questions
        cover = row["seen"] / row["coverable"] if row["coverable"] else float("nan")
        agree = row["slot_hits"] / row["coverable"] if row["coverable"] else float("nan")
        print(f"{kind:>15} {questions:5d} {rec:10.4%} {lookup:10.4%} {lookup - rec:+9.4%}"
              f" {cover:13.4%} {agree:15.4%}")
        target = many if kind in ("edge_account", "role_set", "parts", "context", "definition") else one
        target["questions"] += questions
        target["recorded"] += row["recorded"]
        target["lookup"] += row["lookup"]
        target["scored"] += scored
    print("-" * 106)
    for label, target in (("ONE DECISION", one), ("MANY DECISIONS", many)):
        print(f"{label:>15} {target['questions']:5d} {target['recorded'] / target['questions']:10.4%}"
              f" {target['lookup'] / target['scored']:10.4%}"
              f" {target['lookup'] / target['scored'] - target['recorded'] / target['questions']:+9.4%}")
    total_q = one["questions"] + many["questions"]
    total_r = one["recorded"] + many["recorded"]
    total_l = one["lookup"] + many["lookup"]
    total_s = one["scored"] + many["scored"]
    print("-" * 106)
    print(f"{'ALL':>15} {total_q:5d} {total_r / total_q:10.4%} {total_l / total_s:10.4%}"
          f" {total_l / total_s - total_r / total_q:+9.4%}")
    print()
    print("recorded = the machine's own exact-answer accuracy, recomputed from its submitted answers")
    print("lookup   = the same, using symbols memorised from the other four fifths")
    print("lift     = lookup minus recorded, in points")
    print("correspondence is reported but not scored: its answer is a candidate id, not a symbol")
    print("           per slot, and a symbol lookup cannot express it.")
    print()
    print("REGIME: seen world, unseen question. Not a claim about unseen worlds, and not about the")
    print("development panel, whose packets are absent from the frozen course.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
