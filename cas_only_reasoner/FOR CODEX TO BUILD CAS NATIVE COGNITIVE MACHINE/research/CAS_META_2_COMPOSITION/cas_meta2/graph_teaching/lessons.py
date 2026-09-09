"""Lesson families and exercise generation for the graph-first candidate.

Two families:
- ``binding`` (lesson 1): object nodes with color/shape/value fields and a
  request naming required properties; the learner reads inside, identifies the
  connection, follows it, and selects. This is the tiny reusable lesson built
  on the binding problem.
- ``whole_part`` (^6 specialist curriculum): idea nodes connected by
  ``contains``; structured requests LIST_PARTS, FIND_SHARED_PART, REACHED_VIA.
  This family targets the registered ``cas.cjt.operation.^6.decompose/0.2``
  module (see TARGETED_SPECIALIST_PLAN.md).

Every answer is computed by the deterministic reference checker. The graph
never contains an answer edge. CAS and generic framings are computed from the
same graph bytes; only the CAS framing adds the three Noetic questions.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from .graph import (Graph, Node, Relation, canonical, digest, require)
from . import reference

EXERCISE_SCHEMA = "cas-meta2-graph-teaching-exercise/1"

BINDING_OPS = ("READ_VALUE", "CONTAINING_NODE", "IDENTIFY_CONNECTION",
               "FOLLOW_ONE_HOP", "FOLLOW_TWO_HOPS", "CHANGE_REQUEST")
WHOLE_PART_OPS = ("LIST_PARTS", "FIND_SHARED_PART", "REACHED_VIA")

COLORS = ("red", "blue", "green")
SHAPES = ("square", "triangle", "circle")
KIND_POOL = ("has_color", "has_shape", "has_value", "contains", "triggers")

WHOLE_PART_TEMPLATES = (
    {"bicycle": ("wheel", "frame", "pedals"),
     "cart": ("wheel", "platform", "handle"),
     "wheel": ("rim", "hub", "spokes")},
    {"lamp": ("shade", "bulb", "base"),
     "bulb": ("glass", "filament"),
     "cup": ("handle", "bowl")},
    {"sandwich": ("bread", "filling"),
     "burger": ("bun", "patty"),
     "filling": ("cheese", "lettuce")},
    {"house": ("roof", "walls", "door"),
     "door": ("knob", "panel"),
     "cabin": ("roof", "walls", "window")},
)

LABEL_STYLES = (
    tuple("%s_%s" % (prefix, index) for prefix, index in
          zip(("alpha", "beta", "gamma", "delta", "epsilon", "zeta"),
              range(1, 7))),
    ("A", "B", "C", "D", "E", "F"),
    ("obj1", "obj2", "obj3", "obj4", "obj5", "obj6"),
    ("idea1", "idea2", "idea3", "idea4", "idea5", "idea6"),
)

SPLIT_BASES = {"train": 0, "practice": 1000, "validation": 2000, "test": 3000}
DEFAULT_COUNTS = {"train": 48, "practice": 16, "validation": 16, "test": 16}


def _rng(seed):
    return random.Random(seed)


def binding_family(seed):
    """Three objects; distinct shapes and (color, shape) pairs; a shared color."""
    rng = _rng(seed)
    colors = list(COLORS)
    shapes = list(SHAPES)
    rng.shuffle(colors)
    rng.shuffle(shapes)
    used_colors = [colors[0], colors[0], colors[1]]
    values = [1, 2, 3]
    rng.shuffle(values)
    style = LABEL_STYLES[seed % len(LABEL_STYLES)]
    labels = list(style[:3])
    rng.shuffle(labels)
    objects = [{"label": labels[i], "color": used_colors[i],
                "shape": shapes[i], "value": values[i]} for i in range(3)]
    nodes = []
    relations = []
    value_nodes = {}
    for item in objects:
        nodes.append(Node(item["label"], "object",
                          (("color", item["color"]), ("shape", item["shape"]),
                           ("value", item["value"]))))
        for field in ("color", "shape", "value"):
            key = (field, item[field])
            if key not in value_nodes:
                value_nodes[key] = "val_" + str(item[field])
                nodes.append(Node(value_nodes[key], "property_value",
                                  (("field", field), ("value", item[field]))))
            relations.append(Relation("has_" + field, item["label"], value_nodes[key],
                                      content=(field, item[field])))
    graph = Graph(nodes=tuple(nodes), relations=tuple(relations)).validate()
    meta = {"objects": objects, "value_nodes": value_nodes}
    return graph, meta


def whole_part_family(seed):
    """Idea nodes connected by contains; labels renamed per family."""
    rng = _rng(seed)
    template = WHOLE_PART_TEMPLATES[seed % len(WHOLE_PART_TEMPLATES)]
    names = sorted(set(template) | {part for parts in template.values() for part in parts})
    style = LABEL_STYLES[(seed // 4) % len(LABEL_STYLES)]
    labels = list(style)
    while len(labels) < len(names):
        labels.append(style[0] + str(len(labels) + 1))
    labels = labels[:len(names)]
    rng.shuffle(labels)
    label_map = dict(zip(names, labels))
    nodes = [Node(label, "idea", ()) for label in labels]
    relations = []
    for idea, parts in template.items():
        for part in parts:
            relations.append(Relation("contains", label_map[idea], label_map[part],
                                      content=("constituent", label_map[part])))
    rng.shuffle(relations)
    graph = Graph(nodes=tuple(nodes), relations=tuple(relations)).validate()
    return graph, {"template": template, "label_map": label_map}


def _shuffled_options(rng, correct, distractors):
    """Deterministic PUBLIC choice list: exactly up to 3 unmarked options
    (the three-slot interface). The private target is recorded separately and
    never influences which choices appear."""
    options = [correct]
    for candidate in distractors:
        if candidate not in options and len(options) < 3:
            options.append(candidate)
    rng.shuffle(options)
    require(2 <= len(options) <= 3 and options.count(correct) == 1, "OPTIONS_INVALID")
    return options


def _with_requests(graph, requests, object_labels=()):
    """Attach request + requirement nodes (triggers bring objects into view)."""
    nodes = list(graph.nodes)
    relations = list(graph.relations)
    for label, specs in requests:
        nodes.append(Node(label, "request", ()))
        for index, (field, value) in enumerate(specs):
            req_label = label + "_req" + str(index)
            nodes.append(Node(req_label, "requirement",
                              (("property", field), ("value", value))))
            relations.append(Relation("requires", label, req_label,
                                      content=(field, value)))
        for obj in object_labels:
            relations.append(Relation("triggers", label, obj,
                                      content=("under_consideration", obj)))
    return Graph(nodes=tuple(nodes), relations=tuple(relations)).validate()


def _record(split, family_seed, family, op, graph, question, correct, options,
            derivation):
    framings = {"cas": _render_prompt(op, graph, question, arm="cas"),
                "generic": _render_prompt(op, graph, question, arm="generic")}
    core = {"schema": EXERCISE_SCHEMA, "split": split, "family_seed": family_seed,
            "family": family, "op": op, "graph": graph.to_record(),
            "question": question, "options": options, "correct": correct,
            "reference": derivation, "framings": framings}
    return {**core, "record_id": digest(canonical(core))}


def _binding_exercises(seed, split):
    graph, meta = binding_family(seed)
    rng = _rng(seed * 7 + 3)
    objects = meta["objects"]
    records = []

    # READ_VALUE
    target = objects[seed % 3]
    field = ("color", "shape", "value")[seed % 3]
    correct = str(target[field])
    distractors = sorted({str(item[field]) for item in objects if str(item[field]) != correct})
    graph2, question = graph, {"object": target["label"], "field": field}
    records.append(_record(split, seed, "binding", "READ_VALUE", graph2, question,
                           correct, _shuffled_options(rng, correct, distractors),
                           reference.derivation_for("READ_VALUE", graph2, question)))

    # CONTAINING_NODE (the value field is distinct per object)
    target = objects[(seed + 1) % 3]
    correct = target["label"]
    distractors = [item["label"] for item in objects if item["label"] != correct]
    question = {"field": "value", "value": target["value"]}
    records.append(_record(split, seed, "binding", "CONTAINING_NODE", graph, question,
                           correct, _shuffled_options(rng, correct, distractors),
                           reference.derivation_for("CONTAINING_NODE", graph, question)))

    # IDENTIFY_CONNECTION
    target = objects[(seed + 2) % 3]
    value_node = meta["value_nodes"][("color", target["color"])]
    correct = "has_color"
    distractors = [kind for kind in KIND_POOL if kind != correct]
    question = {"source": target["label"], "target": value_node}
    records.append(_record(split, seed, "binding", "IDENTIFY_CONNECTION", graph, question,
                           correct, _shuffled_options(rng, correct, distractors),
                           reference.derivation_for("IDENTIFY_CONNECTION", graph, question)))

    # FOLLOW_ONE_HOP (shape is unique per object)
    target = objects[seed % 3]
    specs = (("shape", target["shape"]),)
    graph2 = _with_requests(graph, (("request", specs),), [o["label"] for o in objects])
    correct = reference.select_object(graph2, "request")
    require(correct == target["label"], "ONE_HOP_UNEXPECTED")
    distractors = [o["label"] for o in objects if o["label"] != correct]
    question = {"request": "request", "requirements": [list(specs[0])]}
    records.append(_record(split, seed, "binding", "FOLLOW_ONE_HOP", graph2, question,
                           correct, _shuffled_options(rng, correct, distractors),
                           reference.derivation_for("FOLLOW_ONE_HOP", graph2, question)))

    # FOLLOW_TWO_HOPS
    specs = (("color", target["color"]), ("shape", target["shape"]))
    graph2 = _with_requests(graph, (("request", specs),), [o["label"] for o in objects])
    correct = reference.select_object(graph2, "request")
    distractors = [o["label"] for o in objects if o["label"] != correct]
    question = {"request": "request", "requirements": [list(pair) for pair in specs]}
    records.append(_record(split, seed, "binding", "FOLLOW_TWO_HOPS", graph2, question,
                           correct, _shuffled_options(rng, correct, distractors),
                           reference.derivation_for("FOLLOW_TWO_HOPS", graph2, question)))

    # CHANGE_REQUEST
    first = objects[seed % 3]
    second = objects[(seed + 1) % 3]
    graph2 = _with_requests(graph, (("request_a", (("shape", first["shape"]),)),
                                    ("request_b", (("shape", second["shape"]),))),
                            [o["label"] for o in objects])
    correct = reference.select_object(graph2, "request_b")
    require(correct == second["label"], "CHANGE_REQUEST_UNEXPECTED")
    distractors = [o["label"] for o in objects if o["label"] != correct]
    question = {"request_a": "request_a", "request_b": "request_b",
                "from_requirements": [["shape", first["shape"]]],
                "to_requirements": [["shape", second["shape"]]]}
    records.append(_record(split, seed, "binding", "CHANGE_REQUEST", graph2, question,
                           correct, _shuffled_options(rng, correct, distractors),
                           reference.derivation_for("CHANGE_REQUEST", graph2, question)))
    return records


def _whole_part_exercises(seed, split):
    graph, meta = whole_part_family(seed)
    rng = _rng(seed * 11 + 5)
    template = meta["template"]
    top_ideas = sorted(meta["label_map"][name] for name in template)
    records = []

    # LIST_PARTS on two different top-level ideas
    for offset in (0, 1):
        idea = top_ideas[offset % len(top_ideas)]
        correct = reference.direct_parts(graph, idea)
        distractors = []
        nested = [part for part in reference.transitive_parts(graph, idea)
                  if part not in correct]
        if nested:
            distractors.append(sorted(correct + nested[:1]))
        if len(correct) > 1:
            distractors.append(sorted(correct[:-1]))
        other = top_ideas[(offset + 1) % len(top_ideas)]
        other_parts = reference.direct_parts(graph, other)
        if other_parts and other_parts != correct:
            distractors.append(sorted(other_parts))
        question = {"idea": idea}
        records.append(_record(split, seed, "whole_part", "LIST_PARTS", graph, question,
                               correct, _shuffled_options(rng, correct, distractors),
                               reference.derivation_for("LIST_PARTS", graph, question)))

    # FIND_SHARED_PART on two pairs of top-level ideas
    part_names = sorted({relation.target for relation in graph.relations
                         if relation.kind == "contains"})
    second = (seed + 2) % len(top_ideas)
    if second == 0:
        second = 1
    pairs = [(top_ideas[0], top_ideas[1]), (top_ideas[0], top_ideas[second])]
    for a, b in pairs:
        shared = reference.shared_parts(graph, a, b)
        if len(shared) > 1:
            continue  # keep the lesson at single-shared-part answers
        answer = shared[0] if shared else "none"
        distractors = [item for item in part_names if item != answer]
        if "none" not in distractors:
            distractors.append("none")
        question = {"a": a, "b": b}
        records.append(_record(split, seed, "whole_part", "FIND_SHARED_PART", graph,
                               question, answer, _shuffled_options(rng, answer, distractors),
                               reference.derivation_for("FIND_SHARED_PART", graph, question)))

    # REACHED_VIA: direct, via, absent
    root = top_ideas[seed % len(top_ideas)]
    direct_parts = reference.direct_parts(graph, root)
    nested_parts = [part for part in reference.transitive_parts(graph, root)
                    if part not in direct_parts]
    others = [node.identifier for node in graph.nodes
              if node.identifier != root
              and node.identifier not in reference.transitive_parts(graph, root)]
    candidates = []
    if direct_parts:
        candidates.append((direct_parts[0], "direct"))
    if nested_parts:
        candidates.append((nested_parts[0], reference.reach_kind(graph, nested_parts[0], root)))
    if others:
        candidates.append((others[0], "absent"))
    for part, correct in candidates:
        reachable = {"direct", "absent"}
        distractors = sorted(reachable - {correct})
        for constituent in direct_parts:
            distractors.append("via:" + constituent)
        question = {"part": part, "idea": root}
        records.append(_record(split, seed, "whole_part", "REACHED_VIA", graph, question,
                               correct, _shuffled_options(rng, correct, distractors),
                               reference.derivation_for("REACHED_VIA", graph, question)))
    return records


def build_dataset(seed=20260909, counts=None):
    counts = dict(DEFAULT_COUNTS if counts is None else counts)
    splits = {}
    for split, count in counts.items():
        records, family = [], 0
        while len(records) < count:
            family_seed = seed + SPLIT_BASES[split] + family
            family += 1
            fresh = _binding_exercises(family_seed, split)
            fresh += _whole_part_exercises(family_seed, split)
            for record in fresh:
                if len(records) < count and all(
                        record["record_id"] != item["record_id"] for item in records):
                    records.append(record)
        splits[split] = records
    return splits


def build_dataset_files(root, seed=20260909, counts=None):
    counts = dict(DEFAULT_COUNTS if counts is None else counts)
    root = Path(root)
    require(root.exists() and root.is_dir(), "DATASET_ROOT_DIRECTORY_REQUIRED")
    require(not any((root / name).exists() for name in
                    ("train.json", "practice.json", "validation.json", "test.json",
                     "receipt.json")), "DATASET_FILES_MUST_NOT_EXIST")
    splits = build_dataset(seed=seed, counts=counts)
    receipt = {"schema": "cas-meta2-graph-teaching-dataset-receipt/1",
               "seed": seed, "counts": counts, "files": {}}
    for name, records in splits.items():
        raw = json.dumps(records, sort_keys=True, indent=2).encode("utf-8")
        (root / (name + ".json")).write_bytes(raw)
        receipt["files"][name + ".json"] = {"bytes": len(raw),
                                            "sha256": digest(raw)}
    receipt_raw = json.dumps(receipt, sort_keys=True, indent=2).encode("utf-8")
    (root / "receipt.json").write_bytes(receipt_raw)
    return {"path": str(root), "receipt": receipt, "seed": seed}


def _render_prompt(op, graph, question, arm):
    """Teaching prompt: same graph for both arms; CAS adds the Noetic framing."""
    lines = [graph.render().rstrip()]
    if op == "READ_VALUE":
        request = ("What is the {field} of {object}?"
                   .format(field=question["field"], object=question["object"]))
    elif op == "CONTAINING_NODE":
        request = ("Which object contains {field}={value}?"
                   .format(field=question["field"], value=question["value"]))
    elif op == "IDENTIFY_CONNECTION":
        request = ("Which named relation holds between {source} and the value {target}?"
                   .format(source=question["source"], target=question["target"]))
    elif op in ("FOLLOW_ONE_HOP", "FOLLOW_TWO_HOPS"):
        request = ("The request requires " + " and ".join(
            "%s=%s" % (field, value) for field, value in question["requirements"])
                   + ". Which object satisfies the request?")
    elif op == "CHANGE_REQUEST":
        request = ("The request changes from " + " and ".join(
            "%s=%s" % (field, value) for field, value in question["from_requirements"])
                   + " to " + " and ".join(
            "%s=%s" % (field, value) for field, value in question["to_requirements"])
                   + ". Which object is selected now?")
    elif op == "LIST_PARTS":
        request = "LIST_PARTS({idea}): what does it directly contain?".format(
            idea=question["idea"])
    elif op == "FIND_SHARED_PART":
        request = ("FIND_SHARED_PART({a}, {b}): which constituent idea do they share?"
                   .format(a=question["a"], b=question["b"]))
    elif op == "REACHED_VIA":
        request = ("REACHED_VIA({part}, {idea}): is it directly inside, reached "
                   "through another constituent, or absent?".format(
                       part=question["part"], idea=question["idea"]))
    else:
        raise ValueError("UNKNOWN_OPERATION:" + op)
    if arm == "cas":
        lines.append("^8 What brought these ideas into consideration? "
                     "The request triggers them; triggering is not deduction.")
        lines.append("^6 What is inside each idea? Read its fields and its "
                     "outgoing connectors; the branch IS the connector.")
        lines.append("^9 What follows from the operation? The selection the "
                     "checker derives; nothing in the graph marks it.")
    else:
        lines.append("Read the graph. Answer the request.")
    lines.append(request)
    lines.append("Choose one option.")
    return "\n".join(lines) + "\n"
