"""Untouched final panel for GRAPH6_CURRICULUM_002 (owner-directed).

The owner asked for a NEW final panel: the previous 90-case panel has been
examined and is therefore development material. A read-only pool check showed
that the frozen lesson generator cannot supply one: its structural pattern space
is already covered by the teaching set and the examined panel (0 of 2,840
families in a fresh family-seed region could offer a triple whose three cases are
all new by label-invariant signature). New instances of the same four templates
would only repeat patterns the candidate has already been measured on.

This module therefore builds the final panel from a NEW shape bank: twelve
topologies that appear in neither the teaching templates nor the varied
curriculum, using the SAME node/relation vocabulary ("idea" nodes, "contains"
connectors, `constituent` content), the SAME three operations, the SAME
three-unmarked-option answer contract, and answers computed by the SAME
deterministic reference checker. Difficulty is declared, not assumed: every
shape has at least three top-level ideas and at least one nested whole, and the
panel keeps the previous panel's balanced coverage (30 families, one question per
operation, reach labels 10 / 10 / 10).

Every case is excluded by exact record id AND by label-invariant signature
against: the teaching dataset (seed 20260909), the previously examined panel
(seed 20260920), and the varied curriculum built for this candidate.
"""
from __future__ import annotations

import random

from . import fresh_panel, lessons, reference
from .graph import Graph, Node, Relation, canonical, digest, require

FINAL_PANEL_SCHEMA = "cas-graph-training-final-panel/1"
FINAL_PANEL_SEED = 20260930
FINAL_FAMILY_COUNT = 30
FINAL_OPS = tuple(lessons.WHOLE_PART_OPS)
EXCLUDED_CURRICULUM_SEEDS = (20260925,)      # curriculum.CURRICULUM_SEED

# Twelve shapes used by no teaching template and no curriculum family.
FINAL_SHAPES = (
    {"harbour": ("pier", "crane", "shed"), "pier": ("post", "deck"),
     "depot": ("crane", "ramp")},
    {"orchard": ("row", "gate", "shed"), "row": ("trunk", "stump"),
     "field": ("row", "hedge")},
    {"kitchen": ("sink", "oven", "shelf"), "oven": ("rack", "tray"),
     "pantry": ("shelf", "bin")},
    {"station": ("platform", "ticket", "clock"), "platform": ("bench", "lamp"),
     "depot": ("ticket", "ramp")},
    {"workshop": ("bench", "vice", "toolbox"), "bench": ("clamp", "saw"),
     "garage": ("bench", "jack")},
    {"library": ("shelf", "desk", "lamp"), "shelf": ("book", "label"),
     "study": ("desk", "chair")},
    {"gallery": ("wall", "frame", "bench"), "frame": ("canvas", "glass"),
     "studio": ("frame", "easel")},
    {"bakery": ("oven", "counter", "tray"), "oven": ("rack", "door"),
     "shop": ("counter", "scale")},
    {"marina": ("buoy", "rope", "net"), "buoy": ("float", "ring"),
     "dock": ("rope", "cleat")},
    {"clinic": ("bed", "cabinet", "lamp"), "cabinet": ("drawer", "shelf"),
     "ward": ("bed", "screen")},
    {"quarry": ("pit", "crane", "shed"), "pit": ("bench", "ladder"),
     "yard": ("crane", "stack")},
    {"temple": ("pillar", "altar", "gate"), "pillar": ("base", "capital"),
     "shrine": ("altar", "lantern")},
)

FINAL_LABEL_STYLES = (
    ("q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8"),
    ("unit_a", "unit_b", "unit_c", "unit_d", "unit_e", "unit_f", "unit_g", "unit_h"),
    ("x01", "x02", "x03", "x04", "x05", "x06", "x07", "x08"),
    ("zulu", "yankee", "xray", "whiskey", "victor", "uniform", "tango", "sierra"),
    ("piece_1", "piece_2", "piece_3", "piece_4", "piece_5", "piece_6",
     "piece_7", "piece_8"),
    ("green_box", "red_box", "blue_box", "grey_box", "white_box", "black_box",
     "amber_box", "violet_box"),
)


def _label_map(names, style, rng):
    labels = list(style)
    while len(labels) < len(names):
        labels.append("%s_%d" % (style[0], len(labels) + 1))
    labels = labels[:len(names)]
    rng.shuffle(labels)
    return dict(zip(sorted(names), labels))


def _build_graph(shape, label_map, rng):
    names = sorted(set(shape) | {part for parts in shape.values() for part in parts})
    nodes = [Node(label_map[name], "idea", ()) for name in names]
    relations = [Relation("contains", label_map[idea], label_map[part],
                          content=("constituent", label_map[part]))
                 for idea, parts in shape.items() for part in parts]
    rng.shuffle(nodes)
    rng.shuffle(relations)
    return Graph(nodes=tuple(nodes), relations=tuple(relations)).validate()


def _list_options(rng, correct, graph, idea):
    """Three unmarked list options; the wrong ones omit a required part, bring in
    a part of another whole, or both, and two of them match the correct length."""
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
        primary = primary + [fresh[0]]
        secondary = [part for position, part in enumerate(correct) if position != size - 1]
        secondary = secondary + [fresh[-1] if len(fresh) > 1 else fresh[0]]
    else:
        primary = [part for position, part in enumerate(correct) if position != 0]
        secondary = list(correct)
    options = [list(correct), primary[:size], secondary[:size]]
    if options[1] == options[0]:
        options[1] = [part for part in reversed(correct)]
    if options[2] in (options[0], options[1]):
        options[2] = [part for part in correct[1:]] + [correct[0]]
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


def _family(shape_index, style_index, family_seed):
    rng = random.Random(family_seed)
    shape = {idea: tuple(parts) for idea, parts in FINAL_SHAPES[shape_index].items()}
    style = FINAL_LABEL_STYLES[style_index % len(FINAL_LABEL_STYLES)]
    names = sorted(set(shape) | {part for parts in shape.values() for part in parts})
    label_map = _label_map(names, style, rng)
    graph = _build_graph(shape, label_map, rng)
    top_ideas = sorted(label_map[idea] for idea in shape)
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

    return {"shape_index": shape_index, "style_index": style_index,
            "family_seed": family_seed, "graph": graph, "records": records,
            "top_ideas": top_ideas}


def _reach_case(family, wanted):
    """One REACHED_VIA record of this family matching the wanted reach label."""
    graph = family["graph"]
    for root in family["top_ideas"]:
        direct = reference.direct_parts(graph, root)
        nested = [part for part in reference.transitive_parts(graph, root)
                  if part not in direct]
        others = [node.identifier for node in graph.nodes
                  if node.identifier != root
                  and node.identifier not in reference.transitive_parts(graph, root)]
        options = []
        if direct:
            options.append((root, direct[0], "direct", direct))
        if nested:
            options.append((root, nested[0],
                            reference.reach_kind(graph, nested[0], root), direct))
        if others:
            options.append((root, others[0], "absent", direct))
        for root_, part, kind, direct_ in options:
            if kind.split(":")[0] == wanted:
                return root_, part, kind, direct_
    return None


def _family_plan(seed=FINAL_PANEL_SEED, family_count=FINAL_FAMILY_COUNT):
    """Deterministic (shape, label style, family seed) plan."""
    plan = []
    for index in range(family_count):
        shape_index = (index + seed % len(FINAL_SHAPES)) % len(FINAL_SHAPES)
        style_index = (index * 2 + seed % len(FINAL_LABEL_STYLES)) % len(FINAL_LABEL_STYLES)
        plan.append((shape_index, style_index, seed * 100 + index))
    return plan


def build_final_panel(*, panel_seed=FINAL_PANEL_SEED,
                      family_count=FINAL_FAMILY_COUNT,
                      excluded_seeds=fresh_panel.EXCLUDED_DATASET_SEEDS,
                      excluded_panels=fresh_panel.EXAMINED_PANEL_SEEDS,
                      excluded_curricula=EXCLUDED_CURRICULUM_SEEDS):
    """The untouched final panel: 30 families, one question per operation."""
    used_ids, used_signatures = fresh_panel.used_index(
        excluded_seeds, excluded_panels, excluded_curricula)
    reach_quota = {"direct": family_count // 3, "via": family_count // 3,
                   "absent": family_count // 3}
    families = []
    rejected = {"used_case": 0, "no_reach_case": 0, "duplicate_pattern": 0}
    seen_triples = set()
    plan = _family_plan(panel_seed, family_count * 3)
    for shape_index, style_index, family_seed in plan:
        if len(families) >= family_count:
            break
        family = _family(shape_index, style_index, family_seed)
        wanted = ("direct", "via", "absent")[len(families) % 3]
        reach = _reach_case(family, wanted)
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
        triple = digest(canonical(sorted(case["signature"] for case in cases)))
        if triple in seen_triples:
            rejected["duplicate_pattern"] += 1
            continue
        seen_triples.add(triple)
        family_id = "family_%02d" % (len(families) + 1)
        for case in cases:
            case["family_id"] = family_id
        families.append({"family_id": family_id, "family_seed": family_seed,
                         "shape_index": shape_index, "style_index": style_index,
                         "family_signature": triple, "cases": cases})
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
        "distinct_shape_patterns": len({family["shape_index"] for family in families}),
        "distinct_family_patterns": len({family["family_signature"] for family in families}),
        "distinct_case_patterns": len({case["signature"] for case in cases}),
        "families": families,
        "cases": cases,
        "boundary": ("untouched final panel: new shape bank, same node/relation "
                     "vocabulary and the same three-operation answer contract; "
                     "excluded from training, checkpoint selection, tokenizer "
                     "fitting and curriculum design"),
    }
    validate_final_panel(panel)
    return panel


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
    used_ids, used_signatures = fresh_panel.used_index(
        panel["excluded_dataset_seeds"], tuple(panel["excluded_panels"]),
        tuple(panel["excluded_curriculum_seeds"]))
    require(not (set(ids) & used_ids), "FINAL_PANEL_REUSES_USED_CASE")
    require(not ({case["signature"] for case in cases} & used_signatures),
            "FINAL_PANEL_REUSES_RENAMED_USED_CASE")
    for label in ("direct", "via", "absent"):
        require(panel["reach_label_counts"][label] >= 8,
                "FINAL_PANEL_REACH_COVERAGE:" + label)
    for family in panel["families"]:
        require(len(family["cases"]) == len(FINAL_OPS), "FINAL_PANEL_FAMILY_INCOMPLETE")
        require({case["op"] for case in family["cases"]} == set(FINAL_OPS),
                "FINAL_PANEL_FAMILY_OPS")
        require(all(case["family_id"] == family["family_id"] for case in family["cases"]),
                "FINAL_PANEL_FAMILY_GROUPING")
    for case in cases:
        record = case["record"]
        require(record["family"] == "whole_part", "FINAL_PANEL_FAMILY")
        require(len(record["options"]) == 3, "FINAL_PANEL_OPTION_COUNT")
        require(record["options"].count(record["correct"]) == 1,
                "FINAL_PANEL_CORRECT_OPTION")
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
    return panel


def final_panel_digest(panel):
    return digest(canonical([{"family_id": family["family_id"],
                              "family_seed": family["family_seed"],
                              "cases": [{"op": case["op"], "record_id": case["record_id"]}
                                        for case in family["cases"]]}
                             for family in panel["families"]]))
