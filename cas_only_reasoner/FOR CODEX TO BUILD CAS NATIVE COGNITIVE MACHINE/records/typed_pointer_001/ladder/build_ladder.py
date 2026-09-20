"""F3 -- THE DIFFICULTY LADDER. Build it, verify it, and score the mechanism-free rules on it.

WHY THIS EXISTS
---------------
The frozen 18 is a GATE: it says pass or fail. It cannot show a curve. Eighteen yes/no questions
about four-node worlds give nineteen possible scores, and ELEVEN of them are already reachable by
a rule that learns nothing (`AUDIT_REPORT_20260920_INDEPENDENT.md`). You cannot draw a learning
curve on that, and you certainly cannot see a scaling law.

This ladder is the measuring instrument that sits BESIDE the frozen 18 and never replaces it.
`BRAIN_LINEAGE.md` rule 4 is absolute: the frozen 18 and the pass mark do not move. Nothing in
this file reads, writes, or imports them.

THE DIFFICULTY AXIS IS HOP DISTANCE
-----------------------------------
A `reach` question asks whether a part sits inside a whole, and through what. The honest measure
of difficulty is HOW MANY CONTAINMENT LINKS SEPARATE THEM. That axis is continuous, it is the
thing Helm 1.0's broken loop could not climb, and it is exactly what F1 was meant to unlock:
a loop that iterates reaches distance k at round k, and one that does not is stuck at 1 forever.

World size is the second axis. It is reported separately because size and distance are different
kinds of hard: a 40-node world with a 1-hop question is a search problem, and a 6-node world with
a 4-hop question is a chaining problem.

THE BASELINE SHIPS WITH THE LADDER
----------------------------------
Every rung carries the score of a rule that LEARNS NOTHING, computed here, in the same artifact.
This is the habit the audit produced: a win by mechanism M is uninterpretable until it beats the
cheapest method WITHOUT M. The one-hop rule scores 1.00 on `parts` and `edge_account` at every
size and FALLS OFF A CLIFF at hop distance 2 -- and that cliff is precisely where Helm 1.0 lived.
A model that stays above the cliff at distance >= 2 has done something no zero-learning rule can.
A model that tracks the cliff has not, however good its headline number looks.

WHAT THIS FILE DOES NOT DO
--------------------------
It does not run a model. It does not claim a result. It builds the questions, proves they are
disjoint from everything the study ever taught or held, computes the zero-learning curves, and
writes both to disk with a digest. Running a brain on it is a separate job, on a GPU, for an
owner who has authorised it.

Usage:  python records/typed_pointer_001/ladder/build_ladder.py [--out DIR]
Cost:   $0. Pure Python, no torch, no CUDA, a few seconds.
"""
import argparse
import hashlib
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "CAS_META_2_COMPOSITION"))

SCHEMA = "cncm.helm-difficulty-ladder/0.1"
# The rungs. Sizes span an order of magnitude so a scaling curve has somewhere to go; the frozen
# study's worlds are all 4 nodes, and its development panel is 10, so 4 and 10 are the two rungs
# that connect this ladder back to work that already exists.
SIZES = (4, 6, 10, 16, 25, 40)
# Hop distances asked at every size that can hold them. 0 means "not reachable at all" -- the
# ABSENT control, without which a model that always says VIA would look good at every distance.
DISTANCES = (1, 2, 3, 4, 5)
QUESTIONS_PER_CELL = 12          # per (size, distance) cell, before availability trimming
LADDER_SEED = 20260920           # the ladder's own seed, distinct from every study seed


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"))
                          .encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------
# LABELS. Disjoint from every label the frozen study uses, and PROVEN so below rather than hoped.
# ---------------------------------------------------------------------------------------------
LABEL_POOL = (
    "Anvil Auger Ballast Barrel Beacon Bellows Billet Blade Bobbin Bollard Boom Bracket Buffer "
    "Bulkhead Bushing Caliper Camshaft Canopy Capstan Cartridge Casing Caster Catch Chassis "
    "Chute Cinch Clamp Cleat Collar Column Conduit Coupler Cowling Cradle Crank Crucible Cuff "
    "Damper Derrick Diaphragm Dowel Drum Ferrule Fitting Flange Flywheel Gasket Gimbal Girder "
    "Governor Grommet Gudgeon Hanger Harness Hopper Housing Impeller Jig Journal Keel Keyway "
    "Ladle Lattice Lever Linkage Louvre Lug Mandrel Mantle Mast Mount Nacelle Nozzle Pallet "
    "Panel Pawl Pedestal Pillar Piston Plenum Plunger Pulley Quill Rack Rail Ratchet Reamer "
    "Reservoir Ribbon Rocker Roller Rotor Rudder Sabot Saddle Scuttle Seal Shackle Sheave "
    "Shim Shroud Sleeve Slide Sluice Socket Spacer Spar Spigot Spindle Spline Spool Sprocket "
    "Stanchion Stator Strut Stud Sump Swivel Tappet Tensioner Thimble Throttle Tiller Trunnion "
    "Turret Valve Vane Wedge Winch Yoke"
).split()


def _existing_labels():
    """Every node label the frozen study ever showed, taught or held.

    Read from the contract's own material rather than retyped, so this cannot go stale. If the
    material cannot be loaded the build REFUSES: a disjointness claim nobody checked is worse
    than no claim, and a silent fallback here would be exactly the kind of unchecked assumption
    the audit was written to catch.
    """
    from cas_meta2.typed_teaching import pointer_contract as contract
    frozen, _, _ = contract.load_material(ROOT)
    labels = set()
    for world in frozen["bank"]["worlds"]:
        for node in world["nodes"]:
            labels.add(node["label"])
    if not labels:
        raise SystemExit("LADDER_REFUSED:NO_LABELS_READ_FROM_MATERIAL")
    return labels


# ---------------------------------------------------------------------------------------------
# WORLDS
# ---------------------------------------------------------------------------------------------
def _build_world(rng, size, target_depth, labels):
    """One DAG of `size` nodes holding a chain at least `target_depth` links long.

    Nodes are laid out in a topological order and every link runs forwards, so the graph is
    acyclic by construction rather than by rejection sampling. The spine `0 -> 1 -> ... -> d`
    guarantees the depth the rung needs; the remaining links are drawn from the forward pairs so
    that larger worlds get genuinely branchier, not just longer.
    """
    depth = min(target_depth, size - 1)
    edges = {(index, index + 1) for index in range(depth)}
    forward = [(a, b) for a in range(size) for b in range(a + 1, size) if (a, b) not in edges]
    rng.shuffle(forward)
    # Extra links scale with size but stay sparse, so a node's child set stays small enough that
    # `parts` remains a readable question rather than a memory test.
    for pair in forward[:max(0, size // 2)]:
        edges.add(pair)
    chosen = rng.sample(labels, size)
    return {"size": size, "labels": chosen, "edges": sorted(edges)}


def _adjacency(world):
    children = {index: set() for index in range(world["size"])}
    for source, target in world["edges"]:
        children[source].add(target)
    return children


def _distances(world):
    """Shortest hop distance from every node to every node it reaches. Plain breadth-first."""
    children = _adjacency(world)
    out = {}
    for start in range(world["size"]):
        seen, frontier, step = {start: 0}, [start], 0
        while frontier:
            step += 1
            nxt = []
            for node in frontier:
                for child in children[node]:
                    if child not in seen:
                        seen[child] = step
                        nxt.append(child)
            frontier = nxt
        del seen[start]
        out[start] = seen
    return out


def _via(world, whole, part):
    """The FIRST DIRECT CONSTITUENT of `whole` on a shortest path to `part`, chosen lexically.

    This mirrors the frozen study's own `first_direct_constituent_lexical_v1` rule: among the
    children of `whole` that lie on a shortest route to `part`, take the one whose LABEL sorts
    first. Ties are therefore broken by name and not by node index, which is what stops the
    answer from depending on the order the nodes happened to be written down in.
    """
    children, distance = _adjacency(world), _distances(world)
    best = None
    target = distance[whole][part]
    for child in children[whole]:
        if child == part and target == 1:
            return None                      # DIRECT: there is no intermediate to name
        if distance.get(child, {}).get(part) == target - 1:
            label = world["labels"][child]
            if best is None or label < best[0]:
                best = (label, child)
    return None if best is None else best[1]


# ---------------------------------------------------------------------------------------------
# QUESTIONS AND GOLD ANSWERS
# ---------------------------------------------------------------------------------------------
def _questions(rng, world, world_id):
    """`parts`, `edge_account` and `reach` questions, the last stratified by hop distance.

    `reach` carries the ladder's difficulty axis. `parts` and `edge_account` are held at ONE hop
    on purpose: they are the control that says whether a fall-off is caused by DISTANCE or merely
    by SIZE. If a model's `parts` score also collapses at 40 nodes, the problem is search, not
    chaining, and the two must not be confused.
    """
    distance, children = _distances(world), _adjacency(world)
    rows = []

    def add(kind, hops, arguments, answer):
        rows.append({"kind": kind, "hop_distance": hops, "world_id": world_id,
                     "size": world["size"], "arguments": arguments, "answer": answer})

    for node in range(world["size"]):
        add("parts", 1, {"whole": world["labels"][node]},
            {"nodes": sorted(world["labels"][child] for child in children[node])})
    add("edge_account", 1, {},
        {"edges": sorted([world["labels"][a], world["labels"][b]] for a, b in world["edges"])})

    by_distance = {}
    for whole, reached in distance.items():
        for part, hops in reached.items():
            by_distance.setdefault(hops, []).append((whole, part))
    unreachable = [(a, b) for a in range(world["size"]) for b in range(world["size"])
                   if a != b and b not in distance[a]]
    for hops in DISTANCES:
        pairs = by_distance.get(hops, [])
        rng.shuffle(pairs)
        for whole, part in pairs[:QUESTIONS_PER_CELL]:
            via = _via(world, whole, part)
            add("reach", hops,
                {"whole": world["labels"][whole], "part": world["labels"][part]},
                {"state": "DIRECT" if hops == 1 else "VIA",
                 "via": None if via is None else world["labels"][via]})
    # The ABSENT control. Without it a model that answers VIA to everything scores well at every
    # distance and the ladder says nothing.
    rng.shuffle(unreachable)
    for whole, part in unreachable[:QUESTIONS_PER_CELL]:
        add("reach", 0, {"whole": world["labels"][whole], "part": world["labels"][part]},
            {"state": "ABSENT", "via": None})
    return rows


# ---------------------------------------------------------------------------------------------
# SCORING. Exact match AND a continuous score, because a step function hides every partial gain.
# ---------------------------------------------------------------------------------------------
def score(kind, predicted, gold):
    """`(exact, graded)`. `graded` is in [0, 1] and is the column a curve should be drawn on.

    `parts` and `edge_account` are SETS, so the graded score is F1 between the predicted set and
    the gold set -- a model that finds three of four links scores 0.86 rather than 0. `reach` is
    a pair, so it splits: half for the state, half for naming the right intermediate. Exact match
    is kept beside it because it is what the frozen grader speaks, and the two must be reported
    together or the ladder becomes a way of flattering a model.
    """
    if predicted is None:
        return 0.0, 0.0
    if kind in ("parts", "edge_account"):
        key = "nodes" if kind == "parts" else "edges"
        got = {tuple(row) if isinstance(row, list) else row for row in predicted.get(key, [])}
        want = {tuple(row) if isinstance(row, list) else row for row in gold[key]}
        if not got and not want:
            return 1.0, 1.0
        hit = len(got & want)
        precision = hit / len(got) if got else 0.0
        recall = hit / len(want) if want else 0.0
        f1 = 0.0 if hit == 0 else 2 * precision * recall / (precision + recall)
        return float(got == want), f1
    state_right = predicted.get("state") == gold["state"]
    via_right = predicted.get("via") == gold["via"]
    return float(state_right and via_right), 0.5 * state_right + 0.5 * via_right


# ---------------------------------------------------------------------------------------------
# THE MECHANISM-FREE BASELINES. These ship WITH the ladder so no score can be quoted without them.
# ---------------------------------------------------------------------------------------------
def one_hop(world, row):
    """The checker's own rule applied to the input, ONE adjacency hop and no learned weights.

    This is Helm 1.0's ceiling. `parts` and `edge_account` are exact at every size; `reach` is
    right only when the part is a direct child, and says ABSENT for everything further away.
    """
    children, labels = _adjacency(world), world["labels"]
    if row["kind"] == "parts":
        whole = labels.index(row["arguments"]["whole"])
        return {"nodes": sorted(labels[child] for child in children[whole])}
    if row["kind"] == "edge_account":
        return {"edges": sorted([labels[a], labels[b]] for a, b in world["edges"])}
    whole = labels.index(row["arguments"]["whole"])
    part = labels.index(row["arguments"]["part"])
    if part in children[whole]:
        return {"state": "DIRECT", "via": None}
    return {"state": "ABSENT", "via": None}


def rank_last(world, row):
    """Point at the alphabetically last label, reading no links at all. The pure guessing rule."""
    last = sorted(world["labels"])[-1]
    if row["kind"] == "parts":
        return {"nodes": [last]}
    if row["kind"] == "edge_account":
        return {"edges": []}
    return {"state": "VIA", "via": last}


def constant(world, row):
    """The single commonest answer shape per kind, input-blind. `_worst_case` for a learner."""
    if row["kind"] == "parts":
        return {"nodes": []}
    if row["kind"] == "edge_account":
        return {"edges": []}
    return {"state": "ABSENT", "via": None}


def true_oracle(world, row):
    """The gold answer. A ceiling of 1.00 by construction, so a number below it here is a BUG."""
    return row["answer"]


BASELINES = (("one_hop_adjacency", one_hop), ("rank_last_guess", rank_last),
             ("constant_answer", constant), ("true_oracle_ceiling", true_oracle))
# The three that LEARN NOTHING. `true_oracle_ceiling` is the gold answer and is a bug-check, not
# a competitor, so it is excluded from the envelope below.
ZERO_LEARNING = ("one_hop_adjacency", "rank_last_guess", "constant_answer")
# THE LINE A MODEL MUST BEAT, per cell: the best any zero-learning rule manages there. Two things
# found by running the baselines against this very ladder, and fixed rather than left to fool
# somebody later:
#   * `rank_last_guess` scores about 0.53 on `reach` at EVERY distance >= 2, because half the
#     graded score is the state and "VIA" is the right state for everything two hops or further.
#     So the bar at distance 2+ is 0.53, NOT 0. A model at 0.40 there is WORSE than guessing.
#   * `constant_answer` RISES with world size on `parts` -- 0.250 at n=4 to 0.567 at n=40 --
#     because bigger worlds have more leaf nodes, whose correct answer is the empty set, and F1
#     scores an empty prediction against an empty gold as 1.0. Answering NOTHING therefore gets
#     better as the task gets bigger. That is why `parts` is also reported over the NON-EMPTY
#     subset: a model must be able to say "nothing", but it must not be paid for saying it.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(pathlib.Path(__file__).resolve().parent))
    arguments = parser.parse_args()
    out = pathlib.Path(arguments.out)
    out.mkdir(parents=True, exist_ok=True)

    existing = _existing_labels()
    pool = sorted(set(LABEL_POOL) - existing)
    if len(pool) < max(SIZES):
        raise SystemExit("LADDER_REFUSED:LABEL_POOL_TOO_SMALL:%d" % len(pool))

    rng = random.Random(LADDER_SEED)
    worlds, rows = {}, []
    for size in SIZES:
        for replicate in range(3):
            world = _build_world(rng, size, max(DISTANCES) + 1, pool)
            world_id = "ladder-%d-%d-%s" % (size, replicate, _digest(world)[:16])
            worlds[world_id] = world
            rows.extend(_questions(rng, world, world_id))

    # PROOF OF DISJOINTNESS, not a promise of it.
    used = {label for world in worlds.values() for label in world["labels"]}
    overlap = sorted(used & existing)
    if overlap:
        raise SystemExit("LADDER_REFUSED:LABEL_OVERLAP:%s" % ",".join(overlap))

    ladder = {"schema": SCHEMA, "seed": LADDER_SEED, "sizes": list(SIZES),
              "distances": list(DISTANCES), "questions_per_cell": QUESTIONS_PER_CELL,
              "worlds": worlds, "questions": rows,
              "frozen_study_labels_seen": len(existing),
              "labels_used_by_this_ladder": len(used),
              "label_overlap_with_the_frozen_study": overlap,
              "boundary": ("A measuring instrument, not a gate. It sits BESIDE the frozen 18 and "
                           "never replaces it; nothing here reads or writes the study's own "
                           "population, threshold or label.")}
    ladder["digest"] = _digest({key: ladder[key] for key in ("worlds", "questions", "seed")})

    # Baselines, per (kind, hop distance) and per (kind, size).
    cells = {}
    for name, rule in BASELINES:
        for row in rows:
            world = worlds[row["world_id"]]
            exact, graded = score(row["kind"], rule(world, row), row["answer"])
            kinds = [row["kind"]]
            # `parts` is scored twice: over everything, and over the questions whose correct
            # answer is NOT the empty set. See the note on `ZERO_LEARNING` for why.
            if row["kind"] == "parts" and row["answer"]["nodes"]:
                kinds.append("parts_non_empty")
            for kind in kinds:
                for axis, value in (("hop", row["hop_distance"]), ("size", row["size"])):
                    cell = cells.setdefault((name, kind, axis, value), [0, 0.0, 0])
                    cell[0] += exact
                    cell[1] += graded
                    cell[2] += 1
    # The envelope: per cell, the best a rule that learns nothing achieves there.
    envelope = {}
    for (name, kind, axis, value), cell in cells.items():
        if name not in ZERO_LEARNING:
            continue
        key = ("best_zero_learning", kind, axis, value)
        current = envelope.get(key)
        graded = cell[1] / cell[2]
        if current is None or graded > current[1] / current[2]:
            envelope[key] = list(cell)
    cells.update(envelope)
    baselines = {"schema": "cncm.helm-difficulty-ladder-baselines/0.1",
                 "ladder_digest": ladder["digest"],
                 "note": ("The zero-learning curves. A model's score on this ladder is "
                          "uninterpretable until it is drawn against `best_zero_learning`, the "
                          "envelope of every rule here that learns nothing. `one_hop_adjacency` "
                          "is the single most important of them: it is what Helm 1.0's "
                          "architecture could compute and no more, and it falls from 1.000 at "
                          "one hop to 0.000 at two."),
                 "the_line_to_beat": "best_zero_learning",
                 "zero_learning_rules": list(ZERO_LEARNING),
                 "cells": [{"baseline": name, "kind": kind, "axis": axis, "value": value,
                            "exact": round(cell[0] / cell[2], 6),
                            "graded": round(cell[1] / cell[2], 6), "questions": cell[2]}
                           for (name, kind, axis, value), cell in sorted(cells.items(),
                                                                         key=lambda kv: str(kv[0]))]}

    (out / "ladder_v0_1.json").write_text(json.dumps(ladder, indent=1, sort_keys=True),
                                          encoding="utf-8")
    (out / "ladder_baselines_v0_1.json").write_text(json.dumps(baselines, indent=1,
                                                               sort_keys=True), encoding="utf-8")

    # The chart, in text, because this has to be readable in a terminal and in a commit message.
    print("LADDER %s  digest %s" % (SCHEMA, ladder["digest"][:16]))
    print("worlds %d   questions %d   labels %d, overlap with the frozen study: %d"
          % (len(worlds), len(rows), len(used), len(overlap)))
    by_hop = {}
    for row in rows:
        by_hop.setdefault(row["hop_distance"], set()).add(row["world_id"])
    print("\nREACH by hop distance -- graded score, 0 = the ABSENT control")
    header = "  %-22s" % "baseline"
    keys = sorted({row["hop_distance"] for row in rows if row["kind"] == "reach"})
    print(header + "".join("%8s" % ("d=%d" % key) for key in keys))
    for name in [row[0] for row in BASELINES] + ["best_zero_learning"]:
        line = "  %-22s" % name
        for key in keys:
            hit = [c for c in baselines["cells"] if c["baseline"] == name
                   and c["kind"] == "reach" and c["axis"] == "hop" and c["value"] == key]
            line += "%8s" % ("%.3f" % hit[0]["graded"] if hit else "-")
        print(line)
    print("\nPARTS and EDGE_ACCOUNT by world size -- the SIZE control, always one hop")
    sizes = sorted({row["size"] for row in rows})
    print("  %-22s" % "baseline/kind" + "".join("%8s" % ("n=%d" % s) for s in sizes))
    for name in [row[0] for row in BASELINES] + ["best_zero_learning"]:
        for kind in ("parts", "parts_non_empty", "edge_account"):
            line = "  %-22s" % ("%s %s" % (name[:12], kind[:9]))
            for size in sizes:
                hit = [c for c in baselines["cells"] if c["baseline"] == name
                       and c["kind"] == kind and c["axis"] == "size" and c["value"] == size]
                line += "%8s" % ("%.3f" % hit[0]["graded"] if hit else "-")
            print(line)
    print("\nwrote %s and %s" % ((out / "ladder_v0_1.json").name,
                                 (out / "ladder_baselines_v0_1.json").name))
    print("LADDER_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
