"""Diagnose why the world-invariance section produced no observations. Minimal, fast.

Round 39's `measure_exposure_vs_structure.py` section 4 reported `records` 269 and 295 but `obs` 0,
with the `missing` and `undecided` counters also 0 -- meaning the inner loop over the six receipts
incremented nothing at all. This reproduces that logic on ONE record with prints at every step.
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
from cncm import answer_constraints  # noqa: E402

RECEIPTS = HOME / "records/typed_matched_001"


def main() -> int:
    frozen_course, _tokenizer, _ = worker_contract.load_material(HOME)
    receipts = sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/artifacts/final_predictions.json").is_file()
    )
    print(f"receipts found: {len(receipts)}  {[r.name for r in receipts]}")
    if not receipts:
        print("THE RECEIPTS LIST IS EMPTY -- that is the cause")
        return 0

    scores_for = {}
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        by_record = {
            prediction["record_id"]: prediction["scores"]
            for prediction in json.loads(
                (artifacts / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        }
        scores_for[receipt.name] = by_record
        print(f"  {receipt.name}: {len(by_record)} records with scores, "
              f"sample key {next(iter(by_record))[:40]}...")
    print()

    registry = frozen_course["registry"]
    print(f"registry: {len(registry)}")
    row = registry[0]
    record_id = row["record_id"]
    print(f"probing record {record_id[:48]}...")
    print(f"  kind: {row['query']['kind']}")

    packet = course.model_packet(frozen_course, record_id)
    plan = slots.compile_slots(packet)
    target = checker.derive_target(packet["source"], packet["record"]["query"])
    admissible = {json.dumps(item["value"], sort_keys=True) for item in target["admissible_answers"]}
    print(f"  plan slots {len(plan['slots'])}  admissible {len(admissible)}")

    hits = misses = undecided = observations = 0
    for receipt in receipts:
        scores = scores_for[receipt.name].get(record_id)
        if scores is None:
            misses += 1
            continue
        try:
            base = slots.score_decisions(packet, scores)
        except Exception as error:                                    # noqa: BLE001
            undecided += 1
            print(f"  {receipt.name}: score_decisions raised {type(error).__name__}: {error}")
            continue
        fixed = dict(base)
        fixed["selected"] = answer_constraints.apply_constraints(
            packet, plan, scores, base["selected"])
        for label, decisions in (("base", base), ("fixed", fixed)):
            try:
                value = slots.assemble_answer(packet, decisions)["value"]
                hit = json.dumps(value, sort_keys=True) in admissible
            except Exception:                                         # noqa: BLE001
                hit = False
            hits += 1 if hit else 0
        observations += 1
    print()
    print(f"observations {observations}   hits {hits}   missing {misses}   undecided {undecided}")
    print()
    if observations == 0:
        print("REPRODUCED: no observations on a single record either.")
        print("So the section-4 loop was not the problem -- the counters or the loop never ran.")
    else:
        print("The per-record logic WORKS. So section 4's failure was in the outer loop or counters.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
