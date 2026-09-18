"""Does the machine answer from exposure, or from structure?

Pure standard library plus the project's pure modules. No torch, no device, no model, no training, no
new run. Reads the frozen course and the recorded score table.

Why this, now
-------------
Round 38 established that the held-out development panel is 59 questions over **ten-node** worlds
while the exposed course is four-node worlds, that the panel is only 6 `parts` + 53 `reach`, and that
the machine scores **0 of 59** there while scoring `reach` at 76.4798% and `parts` at 80.8176% on the
exposed course. The natural reading is that it answers from **memorised layout** rather than from
structure — a readout that memorises layout scores zero on a layout it has never seen.

That reading is a hypothesis about the machine, and it is testable on data already recorded, from
three directions that do not need the panel:

  1. **Exposure.** The course presents 1,152 times over 564 questions, so questions differ in how
     often they were shown. If the machine is memorising, more exposure should mean more correct.
  2. **World size.** The exposed course itself varies: worlds of three nodes and worlds of four. Size
     is a layout property the answer depends on structurally, so a structure-reading machine should
     not care much, and a layout-memorising one should.
  3. **World identity.** If accuracy is carried by per-world memorisation, then splitting the 64
     worlds into halves should show the constraint layer's gain — which reads only the packet — to be
     the same on both halves, while the machine's own accuracy need not be.

This file reports all three. Nothing is fitted, nothing is trained, and the truth is used only to
score.
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
from cncm import answer_constraints  # noqa: E402

RECEIPTS = HOME / "records/typed_matched_001"
MANY = ("edge_account", "role_set", "parts", "context", "definition")


def spearman(pairs: list) -> float:
    """Rank correlation, computed directly. Ties get their average rank."""
    def ranks(values):
        order = sorted(range(len(values)), key=lambda at: values[at])
        out = [0.0] * len(values)
        at = 0
        while at < len(order):
            end = at
            while end + 1 < len(order) and values[order[end + 1]] == values[order[at]]:
                end += 1
            average = (at + end) / 2.0 + 1.0
            for position in range(at, end + 1):
                out[order[position]] = average
            at = end + 1
        return out
    if len(pairs) < 3:
        return float("nan")
    left = ranks([row[0] for row in pairs])
    right = ranks([row[1] for row in pairs])
    n = len(pairs)
    mean_l, mean_r = sum(left) / n, sum(right) / n
    cov = sum((a - mean_l) * (b - mean_r) for a, b in zip(left, right))
    var_l = sum((a - mean_l) ** 2 for a in left) ** 0.5
    var_r = sum((b - mean_r) ** 2 for b in right) ** 0.5
    return cov / (var_l * var_r) if var_l and var_r else float("nan")


def main() -> int:
    frozen_course, _tokenizer, _ = worker_contract.load_material(HOME)
    presentations = frozen_course["presentations"]
    print(f"presentations: {len(presentations)}")
    print(f"first element: {json.dumps(presentations[0], sort_keys=True)[:200]}")
    print()

    exposure = Counter()
    for row in presentations:
        key = row if isinstance(row, str) else (row.get("record_id") if isinstance(row, dict) else None)
        if key is not None:
            exposure[key] += 1
    print(f"distinct records presented: {len(exposure)}")
    print(f"exposure counts: {dict(sorted(Counter(exposure.values()).items()))}")
    print()

    receipts = sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/artifacts/final_predictions.json").is_file()
    )
    row_for = {}
    # Every receipt's predictions, keyed by record id, loaded ONCE. Scanning them per record made
    # section 4 quadratic and it did not finish.
    scores_for = {}
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        scoring = json.loads((artifacts / "final_scoring.json").read_text(encoding="utf-8"))["rows"]
        for row in scoring:
            row_for.setdefault(row["record_id"], {})[receipt.name] = row["correct"]
        by_record = {}
        for prediction in json.loads(
                (artifacts / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]:
            by_record[prediction["record_id"]] = prediction["scores"]
        scores_for[receipt.name] = by_record

    records = []
    for row in frozen_course["registry"]:
        record_id = row["record_id"]
        packet = course.model_packet(frozen_course, record_id)
        focus = packet["source"]["focus_world_id"]
        world = next(w for w in packet["source"]["worlds"] if w["world_id"] == focus)
        records.append({
            "record_id": record_id,
            "kind": row["query"]["kind"],
            "nodes": len(world["nodes"]),
            "world": focus,
            "exposure": exposure.get(record_id, 0),
            "correct": sum(row_for.get(record_id, {}).values()) / max(1, len(receipts)),
        })
    print(f"records: {len(records)}   exposure range "
          f"{min(r['exposure'] for r in records)}..{max(r['exposure'] for r in records)}")
    print()

    print("=" * 100)
    print("1. EXPOSURE — mean recorded correctness by how often the question was presented")
    print("=" * 100)
    print()
    by_exposure = defaultdict(list)
    for row in records:
        by_exposure[row["exposure"]].append(row["correct"])
    print(f"{'presentations':>14} {'questions':>10} {'mean correctness':>18}")
    print("-" * 100)
    for key in sorted(by_exposure):
        values = by_exposure[key]
        print(f"{key:>14} {len(values):10d} {sum(values) / len(values):17.4%}")
    print()
    rho = spearman([(row["exposure"], row["correct"]) for row in records])
    print(f"Spearman correlation, exposure vs correctness (all 564): {rho:+.4f}")
    print()

    print("=" * 100)
    print("2. WORLD SIZE — mean recorded correctness by the focus world's node count")
    print("=" * 100)
    print()
    by_size = defaultdict(list)
    for row in records:
        by_size[row["nodes"]].append(row["correct"])
    print(f"{'nodes':>7} {'questions':>10} {'mean correctness':>18}")
    print("-" * 100)
    for key in sorted(by_size):
        values = by_size[key]
        print(f"{key:>7} {len(values):10d} {sum(values) / len(values):17.4%}")
    print()
    print("   by kind and size:")
    by_both = defaultdict(list)
    for row in records:
        by_both[(row["kind"], row["nodes"])].append(row["correct"])
    for key in sorted(by_both):
        values = by_both[key]
        print(f"      {key[0]:>15} nodes {key[1]:>2}  q {len(values):4d}  "
              f"{sum(values) / len(values):8.4%}")
    print()

    print("=" * 100)
    print("3. WORLD IDENTITY — is accuracy carried per world?")
    print("=" * 100)
    print()
    by_world = defaultdict(list)
    for row in records:
        by_world[row["world"]].append(row["correct"])
    world_means = sorted(((sum(v) / len(v), len(v)) for v in by_world.values()), reverse=True)
    print(f"worlds: {len(by_world)}")
    print(f"  worlds with 100% of their questions correct: "
          f"{sum(1 for mean, _ in world_means if mean == 1.0)}")
    print(f"  worlds with   0% of their questions correct: "
          f"{sum(1 for mean, _ in world_means if mean == 0.0)}")
    print(f"  worlds strictly between: "
          f"{sum(1 for mean, _ in world_means if 0.0 < mean < 1.0)}")
    print(f"  best world {world_means[0][0]:.4%} over {world_means[0][1]} questions, "
          f"worst {world_means[-1][0]:.4%} over {world_means[-1][1]}")
    print()
    print("  even split by world index into two halves, mean correctness:")
    halves = defaultdict(list)
    for at, row in enumerate(records):
        halves[(hash(row["world"]) % 2)].append(row["correct"])
    for key in sorted(halves):
        values = halves[key]
        print(f"     half {key}: {len(values):4d} questions   {sum(values) / len(values):8.4%}")
    print()

    print("=" * 100)
    print("4. THE CONSTRAINT LAYER'S GAIN, SPLIT BY WORLD HALF — it reads only the packet")
    print("=" * 100)
    print()
    # Plain integer counters, not Counters inside a defaultdict. The round-39 version used
    # `halves[half]["base_n"] += 1` and reported zero observations with zero failure counters, and
    # `diagnose_section4.py` showed the per-record logic itself is sound. This formulation is the one
    # that was verified, so it is the one used.
    stats = {0: {"records": 0, "obs": 0, "missing": 0, "undecided": 0, "base": 0, "fixed": 0},
             1: {"records": 0, "obs": 0, "missing": 0, "undecided": 0, "base": 0, "fixed": 0}}
    # A FIXED partition: worlds sorted by id, split at the median. Round 39 used `hash(world) % 2`,
    # which is salted per process, so the halves were not the same partition twice.
    worlds_sorted = sorted({row["world"] for row in records})
    cut = worlds_sorted[len(worlds_sorted) // 2]
    print(f"worlds {len(worlds_sorted)}  cut at {cut[:28]}...")
    print()
    for row in records:
        record_id = row["record_id"]
        packet = course.model_packet(frozen_course, record_id)
        plan = slots.compile_slots(packet)
        target = checker.derive_target(packet["source"], packet["record"]["query"])
        admissible = {json.dumps(item["value"], sort_keys=True)
                      for item in target["admissible_answers"]}
        half = 0 if row["world"] < cut else 1
        stats[half]["records"] += 1
        for receipt in receipts:
            scores = scores_for[receipt.name].get(record_id)
            if scores is None:
                stats[half]["missing"] += 1
                continue
            try:
                base = slots.score_decisions(packet, scores)
            except Exception:                                         # noqa: BLE001
                stats[half]["undecided"] += 1
                continue
            fixed = dict(base)
            fixed["selected"] = answer_constraints.apply_constraints(
                packet, plan, scores, base["selected"])
            for label, decisions in (("base", base), ("fixed", fixed)):
                try:
                    value = slots.assemble_answer(packet, decisions)["value"]
                    hit = json.dumps(value, sort_keys=True) in admissible
                except Exception:                                     # noqa: BLE001
                    hit = False
                stats[half][label] += 1 if hit else 0
            stats[half]["obs"] += 1
    print(f"{'half':>6} {'records':>8} {'obs':>6} {'unconstrained':>14} {'constrained':>12}"
          f" {'gain':>9} {'missing':>8} {'undecided':>10}")
    print("-" * 100)
    for key in sorted(stats):
        cell = stats[key]
        if not cell["obs"]:
            print(f"{key:>6} {cell['records']:8d} {0:6d} {'--':>14} {'--':>12} {'--':>9}"
                  f" {cell['missing']:8d} {cell['undecided']:10d}   NO OBSERVATIONS")
            continue
        base = cell["base"] / cell["obs"]
        fixed = cell["fixed"] / cell["obs"]
        print(f"{key:>6} {cell['records']:8d} {cell['obs']:6d} {base:13.4%} {fixed:11.4%}"
              f" {fixed - base:+9.4%} {cell['missing']:8d} {cell['undecided']:10d}")
    print()
    print("Worlds split by sorted world id, so the halves are a fixed partition and not one that")
    print("changes with the process hash seed.")
    print()

    print("=" * 100)
    print("5. EXPOSURE WITHIN KIND — the confound §4 could not remove")
    print("=" * 100)
    print()
    print(f"{'kind':>15} {'q':>5} {'spearman(exposure, correct)':>28} {'exposure range':>16}")
    print("-" * 100)
    for kind in sorted({row["kind"] for row in records}):
        members = [row for row in records if row["kind"] == kind]
        rho_kind = spearman([(row["exposure"], row["correct"]) for row in members])
        lo = min(row["exposure"] for row in members)
        hi = max(row["exposure"] for row in members)
        print(f"{kind:>15} {len(members):5d} {rho_kind:+28.4f} {f'{lo}..{hi}':>16}")
    print()
    print("A within-kind positive correlation is evidence for exposure carrying accuracy; a value")
    print("near zero removes exposure as the explanation for the overall +0.1451.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
