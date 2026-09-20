"""Untouched final panel for GRAPH6_CURRICULUM_002 (owner-directed, corrected).

Two corrections drive this version.

1. **The earlier draft was not structurally new.** Twelve proposed shapes were
   checked with a label-invariant graph calculation and reduced to only TWO
   distinct directed connection patterns (shapes 1,3,4,6,8,9,10,11,12 shared one
   pattern; 2,5,7 shared the other). Renaming objects is not novelty. This module
   therefore ENUMERATES genuinely distinct arrangements and proves distinctness.

2. **New arrangements must not become a harder test.** Every pattern here stays
   inside the teaching difficulty range (8-10 idea nodes, 6-9 `contains`
   connectors — teaching templates are 8/6, 8/8, 9/7, 10/9), uses ONLY the
   supported vocabulary (the words the teaching material already uses; no
   unfamiliar labels and no deeper nesting than the teaching material has), and
   keeps the same three operations, the same three-unmarked-option contract, and
   answers from the same deterministic checker.

Every case is excluded by exact record id AND by label-invariant signature
against the teaching dataset (seed 20260909), the previously examined panel
(seed 20260920), and the varied curriculum built for this candidate. Patterns
isomorphic to a teaching template or to a curriculum shape are excluded at the
pattern level as well.
"""
from __future__ import annotations

import itertools
import random
from collections import Counter

from . import curriculum, fresh_panel, lessons, reference
from .graph import Graph, Node, Relation, canonical, digest, require

FINAL_PANEL_SCHEMA = "cas-graph-training-final-panel/1"
FINAL_PANEL_SEED = 20260930
FINAL_FAMILY_COUNT = 30
FINAL_OPS = tuple(lessons.WHOLE_PART_OPS)
EXCLUDED_CURRICULUM_SEEDS = (20260925,)      # curriculum.CURRICULUM_SEED

# ONLY words the teaching material already uses. No new vocabulary is introduced.
SUPPORTED_VOCABULARY = (
    "bicycle", "wheel", "frame", "pedals", "cart", "platform", "handle", "rim",
    "hub", "spokes", "lamp", "shade", "bulb", "base", "glass", "filament", "cup",
    "bowl", "sandwich", "bread", "filling", "burger", "bun", "patty", "cheese",
    "lettuce", "house", "roof", "walls", "door", "knob", "panel", "cabin", "window",
)

# Difficulty envelope taken from the teaching material itself.
MIN_NODES, MAX_NODES = 8, 10
MIN_RELATIONS, MAX_RELATIONS = 6, 9
MAX_DIRECT_PARTS = 3      # teaching material never asks for more than three parts
MAX_DEPTH = 3             # teaching material's deepest chain


def _shape_record(shape):
    nodes = sorted(set(shape) | {part for parts in shape.values() for part in parts})
    return {"nodes": [{"identifier": name, "kind": "idea", "fields": []}
                      for name in nodes],
            "relations": [{"kind": "contains", "source": idea, "target": part,
                           "content": ["constituent", part]}
                          for idea, parts in shape.items() for part in parts]}


def pattern_key(shape):
    """Label-invariant identity of a directed connection pattern."""
    record = _shape_record(shape)
    node_ids = fresh_panel._structural_ids({"graph": record})
    edges = sorted((relation["kind"], node_ids[relation["source"]],
                    node_ids[relation["target"]])
                   for relation in record["relations"])
    return (tuple(sorted(node_ids.values())), tuple(edges))


def pattern_stats(shape):
    nodes = sorted(set(shape) | {part for parts in shape.values() for part in parts})
    relations = sum(len(parts) for parts in shape.values())
    depths = {}
    for whole in shape:
        depth, frontier = 0, [whole]
        seen = {whole}
        while frontier:
            depth += 1
            frontier = [part for node in frontier
                        for part in shape.get(node, ()) if part not in seen]
            seen.update(frontier)
        depths[whole] = depth
    return {"nodes": len(nodes), "relations": relations,
            "wholes": len(shape), "max_depth": max(depths.values()),
            "max_direct_parts": max(len(parts) for parts in shape.values()),
            "has_nested_whole": any(part in shape for parts in shape.values()
                                    for part in parts),
            "has_shared_part": len({part for parts in shape.values() for part in parts})
            < sum(len(parts) for parts in shape.values())}


def enumerate_patterns():
    """Every distinct contains-DAG inside the teaching difficulty envelope."""
    found = {}
    for wholes in (3, 4):
        for counts in itertools.product((1, 2, 3), repeat=wholes):
            for nested_slots in range(0, 3):
                for nested_index in itertools.combinations(range(wholes), nested_slots):
                    for nested_sizes in itertools.product((1, 2), repeat=nested_slots):
                        for shared in (False, True):
                            shape = {}
                            for index, count in enumerate(counts):
                                shape["w%d" % index] = tuple(
                                    "p%d_%d" % (index, j) for j in range(count))
                            for slot, index in enumerate(nested_index):
                                parts = shape["w%d" % index]
                                if not parts:
                                    continue
                                shape[parts[0]] = tuple(
                                    "n%d_%d" % (index, j)
                                    for j in range(nested_sizes[slot]))
                            if shared and len(shape) >= 2:
                                keys = sorted(shape)
                                if shape[keys[0]]:
                                    shape[keys[1]] = tuple(shape[keys[1]]) + (shape[keys[0]][0],)
                            stats = pattern_stats(shape)
                            if not (MIN_NODES <= stats["nodes"] <= MAX_NODES):
                                continue
                            if not (MIN_RELATIONS <= stats["relations"] <= MAX_RELATIONS):
                                continue
                            if stats["max_direct_parts"] < 2 or not stats["has_nested_whole"]:
                                continue
                            if stats["max_direct_parts"] > MAX_DIRECT_PARTS:
                                continue
                            if stats["max_depth"] > MAX_DEPTH:
                                continue
                            found.setdefault(pattern_key(shape), shape)
    return found


def excluded_pattern_keys():
    """Patterns that may not be used: teaching templates and curriculum shapes."""
    keys = {pattern_key(template) for template in lessons.WHOLE_PART_TEMPLATES}
    keys |= {pattern_key(shape) for shape in curriculum.BASE_SHAPES}
    return keys


def _supports_all_reach(shape, probe_seed=7):
    """True when the checker can ask all three reach questions about this
    arrangement. Reach availability is label-invariant, so a probe label
    assignment is enough."""
    family = _family(shape, probe_seed)
    return all(_reach_case(family, label) is not None
               for label in ("direct", "via", "absent"))


def select_patterns(count=FINAL_FAMILY_COUNT, *, seed=FINAL_PANEL_SEED):
    """Deterministically pick `count` DISTINCT patterns, spread over the
    (nodes, relations) buckets, excluding teaching/curriculum patterns and
    keeping only arrangements that support all three reach questions."""
    banned = excluded_pattern_keys()
    found = {key: shape for key, shape in enumerate_patterns().items()
             if key not in banned and _supports_all_reach(shape)}
    buckets = {}
    for key, shape in found.items():
        stats = pattern_stats(shape)
        buckets.setdefault((stats["nodes"], stats["relations"]), []).append((key, shape))
    for entries in buckets.values():
        entries.sort(key=lambda item: item[0])
    ordered_buckets = sorted(buckets)
    selected, index = [], 0
    while len(selected) < count:
        progressed = False
        for bucket in ordered_buckets:
            entries = buckets[bucket]
            if index < len(entries):
                selected.append(entries[index])
                progressed = True
                if len(selected) >= count:
                    break
        if not progressed:
            break
        index += 1
    require(len(selected) >= count, "FINAL_PANEL_PATTERN_POOL_EXHAUSTED")
    return selected


def _label_shape(shape, family_seed):
    """Give the placeholder pattern supported-vocabulary labels."""
    rng = random.Random(family_seed)
    placeholders = sorted(set(shape) | {part for parts in shape.values()
                                        for part in parts})
    words = list(SUPPORTED_VOCABULARY)
    offset = family_seed % len(words)
    words = words[offset:] + words[:offset]
    require(len(words) >= len(placeholders), "FINAL_PANEL_VOCABULARY_TOO_SMALL")
    labels = words[:len(placeholders)]
    rng.shuffle(labels)
    mapping = dict(zip(placeholders, labels))
    return {mapping[whole]: tuple(mapping[part] for part in parts)
            for whole, parts in shape.items()}


def _build_graph(shape, rng):
    nodes = sorted(set(shape) | {part for parts in shape.values() for part in parts})
    node_objects = [Node(name, "idea", ()) for name in nodes]
    relations = [Relation("contains", idea, part,
                          content=("constituent", part))
                 for idea, parts in shape.items() for part in parts]
    rng.shuffle(node_objects)
    rng.shuffle(relations)
    return Graph(nodes=tuple(node_objects), relations=tuple(relations)).validate()


def _list_options(rng, correct, graph, idea):
    size = len(correct)
    foreign = []
    for node in graph.nodes:
        if node.identifier == idea:
            continue
        parts = reference.direct_parts(graph, node.identifier)
        if parts and parts != correct:
            foreign.append(list(parts))
    foreign_parts = sorted({part for parts in foreign for part in parts})
    fresh = [part for part in foreign_parts if part not in correct]
    if fresh:
        primary = [part for position, part in enumerate(correct) if position != 0]
        primary = (primary + [fresh[0]])[:size]
        secondary = [part for position, part in enumerate(correct) if position != size - 1]
        secondary = (secondary + [fresh[-1]])[:size]
    else:
        primary = [part for position, part in enumerate(correct) if position != 0]
        secondary = list(correct)
    options = [list(correct), list(primary), list(secondary)]
    if options[1] == options[0]:
        options[1] = list(reversed(correct))
    if options[2] in (options[0], options[1]):
        options[2] = list(correct[1:]) + [correct[0]]
    rng.shuffle(options)
    require(options.count(list(correct)) == 1 and len(options) == 3,
            "FINAL_LIST_OPTIONS_INVALID")
    return options


def _shared_options(rng, correct, part_names):
    distractors = [name for name in part_names if name != correct]
    if correct != "none":
        distractors.append("none")
    options = [correct]
    for candidate in distractors:
        if candidate not in options and len(options) < 3:
            options.append(candidate)
    rng.shuffle(options)
    require(options.count(correct) == 1 and len(options) == 3,
            "FINAL_SHARED_OPTIONS_INVALID")
    return options


def _reach_options(rng, correct, direct):
    distractors = sorted({"direct", "absent"} - {correct})
    for constituent in direct:
        distractors.append("via:" + constituent)
    options = [correct]
    for candidate in distractors:
        if candidate not in options and len(options) < 3:
            options.append(candidate)
    rng.shuffle(options)
    require(options.count(correct) == 1 and len(options) == 3,
            "FINAL_REACH_OPTIONS_INVALID")
    return options


def _family(pattern_shape, family_seed):
    shape = _label_shape(pattern_shape, family_seed)
    rng = random.Random(family_seed)
    graph = _build_graph(shape, rng)
    top_ideas = sorted(shape)
    part_names = sorted({relation.target for relation in graph.relations
                         if relation.kind == "contains"})
    records = []

    idea = sorted(top_ideas, key=lambda identifier: (
        -len(reference.direct_parts(graph, identifier)), identifier))[0]
    correct = reference.direct_parts(graph, idea)
    question = {"idea": idea}
    records.append(lessons._record(
        fresh_panel.PANEL_SPLIT, family_seed, "whole_part", "LIST_PARTS", graph,
        question, correct, _list_options(rng, correct, graph, idea),
        reference.derivation_for("LIST_PARTS", graph, question)))

    a, b = top_ideas[0], top_ideas[1]
    shared = reference.shared_parts(graph, a, b)
    answer = shared[0] if shared else "none"
    question = {"a": a, "b": b}
    records.append(lessons._record(
        fresh_panel.PANEL_SPLIT, family_seed, "whole_part", "FIND_SHARED_PART",
        graph, question, answer, _shared_options(rng, answer, part_names),
        reference.derivation_for("FIND_SHARED_PART", graph, question)))
    return {"graph": graph, "records": records, "top_ideas": top_ideas}


def _reach_case(family, wanted):
    """One REACHED_VIA question of this family with the wanted reach label.

    `transitive_parts - direct_parts` contains the nested whole ITSELF (a direct
    part) as well as its sub-parts, so the via candidate is chosen by asking the
    checker for each candidate's actual reach kind rather than by position.
    """
    graph = family["graph"]
    for root in family["top_ideas"]:
        direct = reference.direct_parts(graph, root)
        reachable = reference.transitive_parts(graph, root)
        options = []
        if direct:
            options.append((root, direct[0], "direct", direct))
        for part in reachable:
            if part in direct:
                continue
            kind = reference.reach_kind(graph, part, root)
            if kind.startswith("via:"):
                options.append((root, part, kind, direct))
                break
        others = [node.identifier for node in graph.nodes
                  if node.identifier != root and node.identifier not in reachable]
        if others:
            options.append((root, others[0], "absent", direct))
        for root_, part, kind, direct_ in options:
            if kind.split(":")[0] == wanted:
                return root_, part, kind, direct_
    return None


def build_final_panel(*, panel_seed=FINAL_PANEL_SEED,
                      family_count=FINAL_FAMILY_COUNT,
                      excluded_seeds=fresh_panel.EXCLUDED_DATASET_SEEDS,
                      excluded_panels=fresh_panel.EXAMINED_PANEL_SEEDS,
                      excluded_curricula=EXCLUDED_CURRICULUM_SEEDS):
    """The untouched final panel: `family_count` DISTINCT patterns, one question
    per operation, reach labels balanced."""
    used_ids, used_signatures = fresh_panel.used_index(
        excluded_seeds, excluded_panels, excluded_curricula)
    patterns = select_patterns(family_count + 15, seed=panel_seed)
    families = []
    rejected = {"used_case": 0, "no_reach_case": 0}
    for index, (key, pattern_shape) in enumerate(patterns):
        if len(families) >= family_count:
            break
        family_seed = panel_seed * 100 + index
        wanted = ("direct", "via", "absent")[len(families) % 3]
        family = _family(pattern_shape, family_seed)
        reach = _reach_case(family, wanted)
        if reach is None:
            # this arrangement cannot supply the wanted reach label; use whatever
            # reach question it does support rather than dropping the family
            for fallback in ("direct", "via", "absent"):
                reach = _reach_case(family, fallback)
                if reach is not None:
                    break
        if reach is None:
            rejected["no_reach_case"] += 1
            continue
        root, part, kind, direct = reach
        question = {"part": part, "idea": root}
        reach_record = lessons._record(
            fresh_panel.PANEL_SPLIT, family_seed, "whole_part", "REACHED_VIA",
            family["graph"], question, kind,
            _reach_options(random.Random(family_seed + 7), kind, direct),
            reference.derivation_for("REACHED_VIA", family["graph"], question))
        cases = [fresh_panel._case_item("pending", family_seed, record["op"], record)
                 for record in family["records"] + [reach_record]]
        if any(case["record_id"] in used_ids
               or case["signature"] in used_signatures for case in cases):
            rejected["used_case"] += 1
            continue
        family_id = "family_%02d" % (len(families) + 1)
        for case in cases:
            case["family_id"] = family_id
        families.append({"family_id": family_id, "family_seed": family_seed,
                         "pattern_key": digest(canonical(key)),
                         "pattern_stats": pattern_stats(pattern_shape),
                         "family_signature": digest(canonical(sorted(
                             case["signature"] for case in cases))),
                         "cases": cases})
    cases = [case for family in families for case in family["cases"]]
    panel = {
        "schema": FINAL_PANEL_SCHEMA,
        "panel_seed": panel_seed,
        "family_count": len(families),
        "case_count": len(cases),
        "ops": list(FINAL_OPS),
        "cases_per_op": {op: sum(1 for case in cases if case["op"] == op)
                         for op in FINAL_OPS},
        "excluded_dataset_seeds": list(excluded_seeds),
        "excluded_panels": list(excluded_panels),
        "excluded_curriculum_seeds": list(excluded_curricula),
        "excluded_case_ids": len(used_ids),
        "excluded_signatures": len(used_signatures),
        "rejected": rejected,
        "reach_label_counts": {label: sum(
            1 for case in cases if case["op"] == "REACHED_VIA"
            and fresh_panel._reach_label(case["record"]["correct"]) == label)
            for label in ("direct", "via", "absent")},
        "distinct_patterns": len({family["pattern_key"] for family in families}),
        "distinct_family_patterns": len({family["family_signature"] for family in families}),
        "distinct_case_patterns": len({case["signature"] for case in cases}),
        "pattern_pool_size": len(enumerate_patterns()),
        "families": families,
        "cases": cases,
        "boundary": ("untouched final panel: newly ENUMERATED arrangements inside "
                     "the teaching difficulty envelope, supported vocabulary "
                     "only, same three-operation answer contract; excluded from "
                     "training, checkpoint selection, tokenizer fitting and "
                     "curriculum design"),
    }
    validate_final_panel(panel)
    return panel


def difficulty_report(panel):
    """Compare the panel's structure with the teaching material, so nobody has
    to assume 'still contains-graphs' means 'equally difficult'."""
    teaching = [template for template in lessons.WHOLE_PART_TEMPLATES]
    teaching_stats = [pattern_stats(shape) for shape in teaching]
    panel_stats = [family["pattern_stats"] for family in panel["families"]]

    def distribution(rows, key):
        return dict(sorted(Counter(row[key] for row in rows).items()))

    labels = {node["identifier"] for family in panel["families"]
              for case in family["cases"]
              for node in case["record"]["graph"]["nodes"]}
    teaching_words = set(SUPPORTED_VOCABULARY)
    return {
        "teaching": {"nodes": distribution(teaching_stats, "nodes"),
                     "relations": distribution(teaching_stats, "relations"),
                     "max_depth": distribution(teaching_stats, "max_depth"),
                     "max_direct_parts": distribution(teaching_stats, "max_direct_parts")},
        "panel": {"nodes": distribution(panel_stats, "nodes"),
                  "relations": distribution(panel_stats, "relations"),
                  "max_depth": distribution(panel_stats, "max_depth"),
                  "max_direct_parts": distribution(panel_stats, "max_direct_parts")},
        "vocabulary": {"labels_used": len(labels),
                       "labels_outside_supported_vocabulary":
                           sorted(labels - teaching_words)},
        "distinct_patterns": panel["distinct_patterns"],
        "pattern_pool_size": panel["pattern_pool_size"],
    }


def validate_final_panel(panel):
    require(panel["schema"] == FINAL_PANEL_SCHEMA, "FINAL_PANEL_SCHEMA")
    require(panel["family_count"] == len(panel["families"]) == FINAL_FAMILY_COUNT,
            "FINAL_PANEL_FAMILY_COUNT")
    cases = panel["cases"]
    require(len(cases) == panel["case_count"] == FINAL_FAMILY_COUNT * len(FINAL_OPS),
            "FINAL_PANEL_CASE_COUNT")
    for op in FINAL_OPS:
        require(panel["cases_per_op"][op] == FINAL_FAMILY_COUNT,
                "FINAL_PANEL_CASES_PER_OP:" + op)
    ids = [case["record_id"] for case in cases]
    require(len(ids) == len(set(ids)), "FINAL_PANEL_DUPLICATE_CASE_ID")
    pattern_keys = [family["pattern_key"] for family in panel["families"]]
    require(len(pattern_keys) == len(set(pattern_keys)),
            "FINAL_PANEL_PATTERNS_NOT_DISTINCT")
    banned = {digest(canonical(key)) for key in excluded_pattern_keys()}
    require(not (set(pattern_keys) & banned), "FINAL_PANEL_PATTERN_IS_TEACHING_OR_CURRICULUM")
    for family in panel["families"]:
        stats = family["pattern_stats"]
        require(MIN_NODES <= stats["nodes"] <= MAX_NODES,
                "FINAL_PANEL_NODE_RANGE")
        require(MIN_RELATIONS <= stats["relations"] <= MAX_RELATIONS,
                "FINAL_PANEL_RELATION_RANGE")
    used_ids, used_signatures = fresh_panel.used_index(
        panel["excluded_dataset_seeds"], tuple(panel["excluded_panels"]),
        tuple(panel["excluded_curriculum_seeds"]))
    require(not (set(ids) & used_ids), "FINAL_PANEL_REUSES_USED_CASE")
    require(not ({case["signature"] for case in cases} & used_signatures),
            "FINAL_PANEL_REUSES_RENAMED_USED_CASE")
    for label in ("direct", "via", "absent"):
        require(panel["reach_label_counts"][label] >= 8,
                "FINAL_PANEL_REACH_COVERAGE:" + label)
    supported = set(SUPPORTED_VOCABULARY)
    for case in cases:
        record = case["record"]
        require(record["family"] == "whole_part", "FINAL_PANEL_FAMILY")
        require(len(record["options"]) == 3, "FINAL_PANEL_OPTION_COUNT")
        require(record["options"].count(record["correct"]) == 1,
                "FINAL_PANEL_CORRECT_OPTION")
        labels = {node["identifier"] for node in record["graph"]["nodes"]}
        require(labels <= supported, "FINAL_PANEL_UNSUPPORTED_VOCABULARY")
        graph = Graph.from_record(record["graph"])
        question = record["question"]
        if record["op"] == "LIST_PARTS":
            expected = reference.direct_parts(graph, question["idea"])
        elif record["op"] == "FIND_SHARED_PART":
            shared = reference.shared_parts(graph, question["a"], question["b"])
            expected = shared[0] if shared else "none"
        else:
            expected = reference.reach_kind(graph, question["part"], question["idea"])
        require(expected == record["correct"], "FINAL_PANEL_ANSWER_NOT_CHECKER_DERIVED")
    for family in panel["families"]:
        require(len(family["cases"]) == len(FINAL_OPS), "FINAL_PANEL_FAMILY_INCOMPLETE")
        require({case["op"] for case in family["cases"]} == set(FINAL_OPS),
                "FINAL_PANEL_FAMILY_OPS")
        require(all(case["family_id"] == family["family_id"] for case in family["cases"]),
                "FINAL_PANEL_FAMILY_GROUPING")
    return panel


def final_panel_digest(panel):
    return digest(canonical([{"family_id": family["family_id"],
                              "family_seed": family["family_seed"],
                              "pattern_key": family["pattern_key"],
                              "cases": [{"op": case["op"], "record_id": case["record_id"]}
                                        for case in family["cases"]]}
                             for family in panel["families"]]))
