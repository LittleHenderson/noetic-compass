"""Ablation: does the joint candidate branch actually cause `correspondence`'s accuracy?

Pure Python. No torch, no device, no training. Recorded scores, plus targets re-derived by the
project's own checker from the public snapshot only.

Why this ablation was owed
--------------------------
Round 26 established, by reading `slots.score_decisions`, that the architecture composes **jointly
for exactly one kind** (`correspondence`) and **per-slot independently for the other seven**, and
that the joint kind is the one that works (93.18%-96.59% against 0.00%-33.96% elsewhere). That
record said plainly that the joint branch had **not** been shown to *cause* the accuracy: no
ablation was run. This is that ablation.

The two rules
-------------
Recorded (joint), `_candidate_scores`: each enumerated candidate implies a symbol for every slot of
the group; score the candidate by the summed log probability of the symbols it implies; take the
argmax over candidates. NO_MATCH competes on the mode slot's own log probability, and MAPPING
candidates are normalized over all syntactic bijections.

Ablated (independent), `score_decisions`'s other branch: argmax each slot on its own. The mode slot
chooses NO_MATCH or MAPPING; for MAPPING, each source node independently takes its highest-scoring
target alias. Nothing coordinates the source nodes.

So the ablation asks: if the same readout were decoded independently, as seven of the eight kinds
are, what would `correspondence` have scored?

This is a decoder-only ablation. It re-decodes recorded scores; it runs no model and changes no
number the run produced.
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


def independent_answer(plan: dict, scores: dict) -> dict:
    """The other branch of `score_decisions`, transposed onto the correspondence group."""
    mode_slot = plan["slots"][0]
    per_symbol = scores[mode_slot["slot_id"]]
    mode = max(mode_slot["symbols"], key=lambda symbol: per_symbol[symbol])
    if mode == "NO_MATCH":
        return {"status": "NO_MATCH", "pairs": []}
    pairs = []
    for slot in plan["slots"][1:]:
        row = scores[slot["slot_id"]]
        target = max(slot["symbols"], key=lambda symbol: row[symbol])
        pairs.append({"source": slot["coordinates"][0], "target": target})
    return {"status": "MAPPING", "pairs": pairs}


def admissible(plan: dict, value: dict) -> tuple:
    """`answers._payload`'s correspondence rule, minus the alias indirection."""
    if value["status"] == "NO_MATCH":
        return value["pairs"] == [], "NO_MATCH"
    alias = {node["alias"]: node["ref"] for world in plan["aliases"]["worlds"] for node in world["nodes"]}
    sources = [pair["source"] for pair in value["pairs"]]
    targets = sorted(alias[pair["target"]] for pair in value["pairs"])
    want_sources = sorted(slot["coordinates"][0] for slot in plan["slots"][1:])
    want_targets = sorted({alias[symbol] for slot in plan["slots"][1:] for symbol in slot["symbols"]})
    if sources != want_sources:
        return False, "SOURCE_COVERAGE"
    if targets != want_targets:
        return False, "NOT_A_BIJECTION"
    return True, "MAPPING"


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

    combined = Counter()
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        predictions = json.loads((artifacts / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        scoring = {row["record_id"]: row for row in
                   json.loads((artifacts / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}

        tally = Counter()
        for prediction in predictions:
            record_id = prediction["record_id"]
            if scoring[record_id]["kind"] != "correspondence":
                continue
            packet = course.model_packet(frozen, record_id)
            query = packet["record"]["query"]
            plan = slots.compile_slots(packet)
            scores = prediction["scores"]
            truth = checker.derive_target(packet["source"], query)["admissible_answers"][0]
            recorded = prediction["answer"]

            tally["questions"] += 1
            tally[f"candidates_{len(plan['correspondence_candidates'])}"] += 1
            independently = independent_answer(plan, scores)
            ok, why = admissible(plan, independently)
            tally["independent_admissible"] += 1 if ok else 0
            tally[f"independent_blocked_{why}"] += 1
            ablated = independent_value(plan, independently)
            if ok:
                tally["independent_correct"] += 1 if (json.dumps(ablated, sort_keys=True)
                                                       == json.dumps(truth["value"], sort_keys=True)) else 0
            tally["joint_correct"] += 1 if (json.dumps(recorded["value"], sort_keys=True)
                                            == json.dumps(truth["value"], sort_keys=True)) else 0
            tally["rules_agree"] += 1 if (json.dumps(recorded["value"], sort_keys=True)
                                          == json.dumps(ablated, sort_keys=True)) else 0
            tally["joint_is_no_match"] += 1 if recorded["value"]["status"] == "NO_MATCH" else 0
            tally["independent_is_no_match"] += 1 if independently["status"] == "NO_MATCH" else 0
            tally["truth_is_no_match"] += 1 if truth["value"]["status"] == "NO_MATCH" else 0

        for key in sorted(tally):
            combined[key] += tally[key]
        questions = tally["questions"]
        print(f"{receipt.name}: questions={questions}", flush=True)
        print(f"   joint (recorded) correct          {tally['joint_correct']:4d}  {tally['joint_correct'] / questions:9.4%}")
        print(f"   independent admissible            {tally['independent_admissible']:4d}"
              f"  {tally['independent_admissible'] / questions:9.4%}")
        print(f"   independent correct               {tally['independent_correct']:4d}"
              f"  {tally['independent_correct'] / questions:9.4%}")
        print(f"   the two rules agree               {tally['rules_agree']:4d}  {tally['rules_agree'] / questions:9.4%}")
        print(f"   blocked: NOT_A_BIJECTION          {tally['independent_blocked_NOT_A_BIJECTION']:4d}"
              f"  {tally['independent_blocked_NOT_A_BIJECTION'] / questions:9.4%}")
        print(f"   blocked: SOURCE_COVERAGE          {tally['independent_blocked_SOURCE_COVERAGE']:4d}"
              f"  {tally['independent_blocked_SOURCE_COVERAGE'] / questions:9.4%}")
        print(f"   joint picked NO_MATCH             {tally['joint_is_no_match']:4d}"
              f"  {tally['joint_is_no_match'] / questions:9.4%}")
        print(f"   independent picked NO_MATCH       {tally['independent_is_no_match']:4d}"
              f"  {tally['independent_is_no_match'] / questions:9.4%}")
        print(f"   truth is NO_MATCH                 {tally['truth_is_no_match']:4d}"
              f"  {tally['truth_is_no_match'] / questions:9.4%}")
        print(f"   candidate counts                  "
              f"{ {k.split('_')[1]: v for k, v in tally.items() if k.startswith('candidates_')} }")
        print(flush=True)

    questions = combined["questions"]
    print("=" * 104)
    print(f"ALL RUNS  ({questions} correspondence questions)")
    print("=" * 104)
    print()
    for key in ("joint_correct", "independent_admissible", "independent_correct", "rules_agree"):
        print(f"   {key:>26}  {combined[key]:5d}  {combined[key] / questions:9.4%}")
    print()
    print("If `independent_admissible` is low, the joint branch is not a refinement of the")
    print("per-slot rule -- it is the only thing standing between the readout and an answer that")
    print("the answer contract would reject outright.")
    return 0


def independent_value(plan: dict, value: dict) -> dict:
    """The ablated value in the same reference space as the derived truth."""
    alias = {node["alias"]: node["ref"] for world in plan["aliases"]["worlds"] for node in world["nodes"]}
    if value["status"] == "NO_MATCH":
        return {"status": "NO_MATCH", "pairs": []}
    return {"status": "MAPPING",
            "pairs": [{"source": pair["source"], "target": alias[pair["target"]]}
                      for pair in value["pairs"]]}


if __name__ == "__main__":
    raise SystemExit(main())
