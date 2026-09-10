"""Varied relationship curriculum for GRAPH6_CURRICULUM_002 (owner-directed).

The measured problem is not that the module cannot learn: familiar-example
learning replicated in all three independent candidates, but fresh transfer did
not reach the registered bar, and `LIST_PARTS` was weakest on the new panel
(6/30, 10/30, 7/30 after training). The owner's proposed hypothesis is that the
learner needs more varied practice that separates the RELATIONSHIP from familiar
names, layouts and answer patterns. This module builds that curriculum; it does
not claim the hypothesis is true.

What stays exactly as it is:

* the answer contract — three unmarked options, the learner selects one;
* the ^6 module, the frozen encoder, the parameter scope and the scoring
  semantics (this module only produces lesson records);
* every answer is computed by the deterministic reference checker from the
  stored graph; nothing in a graph marks the answer.

What varies (the "golden thread": keep the rule recognizable, change the
details):

* consistent renaming of every node;
* harmless reordering of the written connections;
* meaningful rewiring (one connection moves to another whole, so the answer
  changes and the learner must follow the structure);
* `LIST_PARTS` distractors that omit a required part, that bring in a part
  belonging to another whole, and that are the same length as the correct list,
  so "choose the longest/shortest list" cannot solve the lesson;
* nested wholes, so "directly contained" and "reached through another part"
  stay distinguished;
* maintained `FIND_SHARED_PART` and `REACHED_VIA` practice.

The control curriculum is the EXISTING lesson generator, unchanged.
"""
from __future__ import annotations

import random

from . import lessons, reference
from .graph import Graph, Node, Relation, canonical, digest, require

CURRICULUM_SCHEMA = "cas-graph-training-varied-curriculum/1"
CURRICULUM_SEED = 20260925
FROZEN_DATASET_SEED = 20260909
VARIED_SPLIT = "curriculum_varied"
OPS = ("LIST_PARTS", "FIND_SHARED_PART", "REACHED_VIA")
FAMILY_COUNT = 10
RECORDS_PER_OP = 10
TOTAL_RECORDS = FAMILY_COUNT * len(OPS)

# Ten base shapes: every one has at least three top-level ideas (so the three
# operations are all answerable) and at least one nested whole (so "directly
# contained" and "reached through another part" differ).
BASE_SHAPES = (
    {"bicycle": ("wheel", "frame", "pedals"), "cart": ("wheel", "platform"),
     "wheel": ("rim", "hub")},
    {"lamp": ("shade", "bulb", "base"), "torch": ("bulb", "case"),
     "bulb": ("glass", "filament")},
    {"sandwich": ("bread", "filling"), "burger": ("bun", "patty"),
     "filling": ("cheese", "lettuce")},
    {"house": ("roof", "walls", "door"), "cabin": ("roof", "window"),
     "door": ("knob", "panel")},
    {"car": ("engine", "wheel", "body"), "bike": ("wheel", "frame"),
     "engine": ("piston", "valve")},
    {"tree": ("trunk", "branch", "root"), "bush": ("stem", "leaf"),
     "branch": ("twig", "leaf")},
    {"kettle": ("lid", "spout", "body"), "pot": ("lid", "handle"),
     "lid": ("knob", "rim")},
    {"laptop": ("screen", "keyboard", "battery"), "tablet": ("screen", "battery"),
     "keyboard": ("key", "frame")},
    {"garden": ("soil", "fence", "path"), "pot": ("soil", "plant"),
     "fence": ("post", "rail")},
    {"clock": ("dial", "hands", "case"), "watch": ("dial", "strap"),
     "hands": ("hour", "minute")},
)

# Label styles used only by this curriculum: the learner must not rely on the
# teaching labels. Each style keeps labels unique and free of option literals.
VARIED_LABEL_STYLES = (
    ("alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"),
    ("A", "B", "C", "D", "E", "F", "G", "H"),
    ("obj1", "obj2", "obj3", "obj4", "obj5", "obj6", "obj7", "obj8"),
    ("idea_a", "idea_b", "idea_c", "idea_d", "idea_e", "idea_f", "idea_g", "idea_h"),
    ("n01", "n02", "n03", "n04", "n05", "n06", "n07", "n08"),
    ("whole", "part", "unit", "piece", "chunk", "block", "section", "fragment"),
    ("red_thing", "blue_thing", "green_thing", "grey_thing", "white_thing",
     "black_thing", "amber_thing", "violet_thing"),
    ("one", "two", "three", "four", "five", "six", "seven", "eight"),
)

VARIATION_KINDS = (
    "renamed", "renamed_reordered", "renamed_rewired", "renamed_reordered",
    "renamed_rewired", "renamed_reordered", "renamed_rewired",
    "renamed_reordered", "renamed_rewired", "renamed_reordered",
)

# LIST_PARTS distractor profiles: which wrong list appears next to the correct
# one. Every profile includes a mistake the owner named (a required part left
# out, or a part that belongs to another whole), and profiles A and B produce
# competing lists of the SAME length as the correct answer.
LIST_PROFILES = (
    "same_length_omission",     # (correct - one part) + one foreign part
    "same_length_foreign",      # another whole's parts, same length
    "same_length_omission",
    "extra_foreign_part",       # correct + one foreign part
    "same_length_foreign",
    "same_length_omission",
    "same_length_foreign",
    "extra_foreign_part",
    "short_subset",             # correct - one part
    "same_length_omission",
)


def _label_map(names, style, rng):
    labels = list(style)
    while len(labels) < len(names):
        labels.append("%s%d" % (style[0], len(labels) + 1))
    labels = labels[:len(names)]
    rng.shuffle(labels)
    return dict(zip(sorted(names), labels))


def _shape_after_rewire(shape, rng):
    """Move one connection from a whole with several parts to another whole.

    The graph stays valid and the checker-derived answers change, so the learner
    must follow the structure rather than memorise a part list.
    """
    rewritten = {idea: list(parts) for idea, parts in shape.items()}
    donors = [idea for idea, parts in rewritten.items() if len(parts) > 1]
    receivers = [idea for idea in rewritten]
    if not donors:
        return rewritten, False
    donor = donors[rng.randrange(len(donors))]
    moved = rewritten[donor].pop(rng.randrange(len(rewritten[donor])))
    receivers = [idea for idea in receivers if idea != donor]
    receiver = receivers[rng.randrange(len(receivers))]
    rewritten[receiver] = sorted(set(rewritten[receiver]) | {moved})
    return rewritten, True


def _build_graph(shape, label_map, rng, reorder):
    names = sorted(set(shape) | {part for parts in shape.values() for part in parts})
    nodes = [Node(label_map[name], "idea", ()) for name in names]
    relations = []
    for idea, parts in shape.items():
        for part in parts:
            relations.append(Relation("contains", label_map[idea], label_map[part],
                                      content=("constituent", label_map[part])))
    if reorder:
        rng.shuffle(relations)
        rng.shuffle(nodes)
    return Graph(nodes=tuple(nodes), relations=tuple(relations)).validate()


def _list_options(rng, correct, graph, idea, profile):
    """Three unmarked options for LIST_PARTS with a declared distractor profile.

    Rule: every wrong option must contain a mistake the owner named — a required
    part left out, or a part that belongs to another whole. Profiles A and B
    build ALL three options at the correct length, so the longest/shortest-list
    shortcut cannot solve those lessons; profiles C and D keep one deliberately
    longer (extra part) or shorter (missing part) option so both pure mistake
    kinds are taught. Every family's metadata records the lengths honestly.
    """
    size = len(correct)
    foreign_pool = []
    for node in graph.nodes:
        if node.identifier == idea:
            continue
        parts = reference.direct_parts(graph, node.identifier)
        if parts and parts != correct:
            foreign_pool.append(list(parts))
    foreign_pool.sort()
    foreign_parts = sorted({part for parts in foreign_pool for part in parts})
    fresh_foreign = [part for part in foreign_parts if part not in correct]

    def length_variant(omit_index, foreign_index):
        """A wrong list of exactly `size` entries: drop one correct part and add
        one foreign part (or, when size is 1, just take a foreign part)."""
        kept = [part for position, part in enumerate(correct)
                if position != omit_index % size]
        if len(kept) < size and fresh_foreign:
            kept = kept + [fresh_foreign[foreign_index % len(fresh_foreign)]]
        while len(kept) < size and fresh_foreign:
            kept.append(fresh_foreign[(foreign_index + len(kept)) % len(fresh_foreign)])
        return kept[:size]

    if not fresh_foreign:                    # degenerate family: no foreign part
        primary = list(correct)
        secondary = list(correct)
    elif profile == "same_length_omission":
        primary = length_variant(0, 0)
        secondary = length_variant(1, 1)
    elif profile == "same_length_foreign":
        primary = length_variant(size - 1, 0)
        secondary = length_variant(0, 1)
    elif profile == "extra_foreign_part":
        primary = list(correct) + [fresh_foreign[0]]
        secondary = length_variant(0, 0)
    elif profile == "short_subset":
        primary = [part for position, part in enumerate(correct) if position != 0]
        secondary = length_variant(0, 0)
    else:
        primary = length_variant(0, 0)
        secondary = length_variant(1, 1)

    options = [list(correct), list(primary), list(secondary)]
    rng.shuffle(options)
    require(options.count(list(correct)) == 1 and len(options) == 3,
            "VARIED_LIST_OPTIONS_INVALID")
    wrong = [option for option in options if option != list(correct)]
    lengths = [len(option) for option in options]
    return options, {"profile": profile,
                     "option_lengths": lengths,
                     "equal_length": len(set(lengths)) == 1,
                     "omits_required_part": any(
                         not set(correct) <= set(option) for option in wrong),
                     "brings_foreign_part": any(
                         set(option) - set(correct) for option in wrong),
                     "distractor_overlap_with_correct": sorted(
                         len(set(option) & set(correct)) for option in wrong),
                     "correct_is_unique_longest": (lengths.count(max(lengths)) == 1
                                                   and len(correct) == max(lengths)),
                     "correct_is_unique_shortest": (lengths.count(min(lengths)) == 1
                                                    and len(correct) == min(lengths)),
                     "wrong_options_omitting_a_required_part": sum(
                         1 for option in wrong if not set(correct) <= set(option)),
                     "wrong_options_bringing_a_foreign_part": sum(
                         1 for option in wrong if set(option) - set(correct))}


def _shared_options(rng, correct, graph, part_names):
    """Three unmarked options for FIND_SHARED_PART.

    The retained-error review measured that neither the teaching records nor the
    examined panel ever offered three options of equal length for this operation,
    and that the model never chose "none" when "none" was the answer (0 of 60
    wrong before training, 0 of 46 after) while the examined panel answered
    "none" in 21 of 30 cases. The builder therefore prefers distractors of the
    SAME character length as the correct option and keeps "none" in play.
    """
    correct_length = len(correct)
    same_length = [name for name in part_names
                   if name != correct and len(name) == correct_length]
    other = [name for name in part_names if name != correct and name not in same_length]
    distractors = same_length + other
    if correct != "none":
        distractors.append("none")
    else:
        distractors.append(next((name for name in part_names if len(name) == 4), None))
    options = [correct]
    for candidate in distractors:
        if candidate and candidate not in options and len(options) < 3:
            options.append(candidate)
    rng.shuffle(options)
    require(options.count(correct) == 1 and len(options) == 3,
            "VARIED_SHARED_OPTIONS_INVALID")
    return options, {"option_lengths": sorted(len(option) for option in options),
                     "equal_length": len({len(option) for option in options}) == 1,
                     "none_is_an_option": "none" in options}


def _reach_options(rng, correct, direct_parts):
    reachable = {"direct", "absent"}
    distractors = sorted(reachable - {correct})
    for constituent in direct_parts:
        distractors.append("via:" + constituent)
    options = [correct]
    for candidate in distractors:
        if candidate not in options and len(options) < 3:
            options.append(candidate)
    rng.shuffle(options)
    require(options.count(correct) == 1 and len(options) == 3,
            "VARIED_REACH_OPTIONS_INVALID")
    return options


def varied_family(index, *, seed=CURRICULUM_SEED):
    """One varied lesson family: shape, label style, rewiring, three records."""
    require(0 <= index < FAMILY_COUNT, "VARIED_FAMILY_INDEX")
    family_seed = seed * 100 + index
    rng = random.Random(family_seed)
    kind = VARIATION_KINDS[index]
    shape = {idea: tuple(parts) for idea, parts in BASE_SHAPES[index].items()}
    rewired = False
    if kind == "renamed_rewired":
        shape, rewired = _shape_after_rewire(shape, rng)
    style = VARIED_LABEL_STYLES[index % len(VARIED_LABEL_STYLES)]
    names = sorted(set(shape) | {part for parts in shape.values() for part in parts})
    label_map = _label_map(names, style, rng)
    graph = _build_graph(shape, label_map, rng, reorder="reordered" in kind)
    top_ideas = sorted(label_map[idea] for idea in shape)
    part_names = sorted({relation.target for relation in graph.relations
                         if relation.kind == "contains"})
    records = []

    # ---- LIST_PARTS: the complete direct part list ------------------------
    # The questioned whole is chosen with at least two direct parts, so the
    # omission and equal-length distractors are meaningful for every family.
    def _part_count(identifier):
        return len(reference.direct_parts(graph, identifier))

    idea = sorted(top_ideas, key=lambda identifier: (-_part_count(identifier),
                                                     identifier))[0]
    correct = reference.direct_parts(graph, idea)
    require(correct, "VARIED_LIST_PARTS_EMPTY")
    options, option_meta = _list_options(rng, correct, graph, idea,
                                         LIST_PROFILES[index])
    question = {"idea": idea}
    records.append(lessons._record(
        VARIED_SPLIT, family_seed, "whole_part", "LIST_PARTS", graph, question,
        correct, options, reference.derivation_for("LIST_PARTS", graph, question)))

    # ---- FIND_SHARED_PART: maintained practice ----------------------------
    a = top_ideas[0]
    b = top_ideas[1]
    shared = reference.shared_parts(graph, a, b)
    answer = shared[0] if shared else "none"
    question = {"a": a, "b": b}
    shared_options, shared_meta = _shared_options(rng, answer, graph, part_names)
    records.append(lessons._record(
        VARIED_SPLIT, family_seed, "whole_part", "FIND_SHARED_PART", graph, question,
        answer, shared_options,
        reference.derivation_for("FIND_SHARED_PART", graph, question)))

    # ---- REACHED_VIA: direct / through another part / absent --------------
    # The wanted label rotates over the three reach kinds, and the root is
    # chosen so that the wanted label is actually available in this family; the
    # achieved label is recorded either way.
    wanted = ("direct", "via", "absent")[index % 3]
    reach_candidates = []
    for candidate_root in top_ideas:
        direct = reference.direct_parts(graph, candidate_root)
        nested = [part for part in reference.transitive_parts(graph, candidate_root)
                  if part not in direct]
        others = [node.identifier for node in graph.nodes
                  if node.identifier != candidate_root
                  and node.identifier not in reference.transitive_parts(graph,
                                                                        candidate_root)]
        if direct:
            reach_candidates.append((candidate_root, direct[0], "direct", direct))
        if nested:
            reach_candidates.append((candidate_root, nested[0],
                                     reference.reach_kind(graph, nested[0],
                                                          candidate_root), direct))
        if others:
            reach_candidates.append((candidate_root, others[0], "absent", direct))
    matching = [item for item in reach_candidates
                if item[2].split(":")[0] == wanted]
    root, part, correct_reach, direct = (matching[0] if matching else reach_candidates[0])
    question = {"part": part, "idea": root}
    records.append(lessons._record(
        VARIED_SPLIT, family_seed, "whole_part", "REACHED_VIA", graph, question,
        correct_reach, _reach_options(rng, correct_reach, direct),
        reference.derivation_for("REACHED_VIA", graph, question)))

    for record in records:
        record["variation"] = {"family_index": index, "kind": kind,
                               "rewired": rewired,
                               "label_style": list(style),
                               "relation_order_shuffled": "reordered" in kind,
                               **option_meta}
        if record["op"] == "FIND_SHARED_PART":
            record["variation"].update(
                {"shared_" + key: value for key, value in shared_meta.items()})
    return {"family_index": index, "family_seed": family_seed, "kind": kind,
            "shape": shape, "graph": graph, "records": records}


def varied_records(*, seed=CURRICULUM_SEED):
    """The varied curriculum: 30 records, 10 per operation."""
    records = [record
               for index in range(FAMILY_COUNT)
               for record in varied_family(index, seed=seed)["records"]]
    require(len(records) == TOTAL_RECORDS, "VARIED_RECORD_COUNT")
    validate_curriculum(records)
    return records


def control_records(*, seed=FROZEN_DATASET_SEED):
    """The existing curriculum, unchanged: the 30 train+practice records."""
    from . import trainer
    records = trainer.training_records(seed)
    require(len(records) == TOTAL_RECORDS, "CONTROL_RECORD_COUNT")
    return records


def schedule(records):
    """Balanced operation schedule: every three consecutive updates cover the
    three operations once. Deterministic; the same schedule shape is used for
    both curricula, so exposure is comparable."""
    by_op = {op: [record for record in records if record["op"] == op] for op in OPS}
    for op in OPS:
        require(len(by_op[op]) == RECORDS_PER_OP, "SCHEDULE_OP_COUNT:" + op)
    ordered = []
    for position in range(RECORDS_PER_OP):
        for op in OPS:
            ordered.append(by_op[op][position])
    return ordered


def exposure(records, updates, *, tokenizer=None, arm="cas"):
    """What the learner actually receives: examples, families, repeats, tokens."""
    from . import adapter
    ordered = schedule(records)
    delivered = [ordered[index % len(ordered)] for index in range(updates)]
    counts = {}
    for record in delivered:
        counts[record["record_id"]] = counts.get(record["record_id"], 0) + 1
    per_op = {op: sum(1 for record in delivered if record["op"] == op) for op in OPS}
    tokens = None
    if tokenizer is not None:
        tokens = sum(len(tokenizer.encode_public(
            adapter.public_records(record, arm)["public"])["ids"])
            for record in delivered)
    return {"records_delivered": len(delivered),
            "distinct_records": len(counts),
            "distinct_families": len({record["family_seed"] for record in delivered}),
            "deliveries_per_record": {"min": min(counts.values()),
                                      "max": max(counts.values()),
                                      "mean": sum(counts.values()) / len(counts)},
            "deliveries_by_op": per_op,
            "tokens_processed": tokens,
            "arm": arm,
            "schedule": "round-robin over operations, position-major"}


def validate_curriculum(records):
    require(len(records) == TOTAL_RECORDS, "CURRICULUM_RECORD_COUNT")
    for op in OPS:
        require(sum(1 for record in records if record["op"] == op) == RECORDS_PER_OP,
                "CURRICULUM_OP_COUNT:" + op)
    ids = [record["record_id"] for record in records]
    require(len(ids) == len(set(ids)), "CURRICULUM_DUPLICATE_RECORD")
    for record in records:
        require(record["family"] == "whole_part", "CURRICULUM_FAMILY")
        require(record["op"] in OPS, "CURRICULUM_OP")
        require(len(record["options"]) == 3, "CURRICULUM_OPTION_COUNT")
        require(record["options"].count(record["correct"]) == 1,
                "CURRICULUM_CORRECT_OPTION")
        graph = Graph.from_record(record["graph"])
        question = record["question"]
        if record["op"] == "LIST_PARTS":
            expected = reference.direct_parts(graph, question["idea"])
        elif record["op"] == "FIND_SHARED_PART":
            shared = reference.shared_parts(graph, question["a"], question["b"])
            expected = shared[0] if shared else "none"
        else:
            expected = reference.reach_kind(graph, question["part"], question["idea"])
        require(expected == record["correct"],
                "CURRICULUM_ANSWER_NOT_CHECKER_DERIVED:" + record["record_id"])
    return records


def curriculum_identity(records):
    return digest(canonical([{"op": record["op"], "record_id": record["record_id"],
                              "correct": record["correct"],
                              "options": record["options"]}
                             for record in records]))


def curriculum_report(records=None):
    """Audit numbers for the varied curriculum (no training, no GPU)."""
    records = records if records is not None else varied_records()
    lists = [record for record in records if record["op"] == "LIST_PARTS"]
    return {
        "schema": "cas-graph-training-varied-curriculum-report/1",
        "curriculum_seed": CURRICULUM_SEED,
        "record_count": len(records),
        "records_per_op": {op: sum(1 for record in records if record["op"] == op)
                           for op in OPS},
        "family_count": len({record["family_seed"] for record in records}),
        "identity": curriculum_identity(records),
        "variation_kinds": {kind: sum(1 for record in records
                                      if record["variation"]["kind"] == kind)
                            for kind in sorted({record["variation"]["kind"]
                                                for record in records})},
        "rewired_families": len({record["variation"]["family_index"] for record in records
                                 if record["variation"]["rewired"]}),
        "reordered_families": len({record["variation"]["family_index"]
                                   for record in records
                                   if record["variation"]["relation_order_shuffled"]}),
        "distinct_label_styles": len({tuple(record["variation"]["label_style"])
                                      for record in records}),
        "list_parts": {
            "equal_length_lessons": sum(1 for record in lists
                                        if record["variation"]["equal_length"]),
            "lessons_with_a_missing_part_option": sum(
                1 for record in lists
                if record["variation"]["omits_required_part"]),
            "lessons_with_a_foreign_part_option": sum(
                1 for record in lists
                if record["variation"]["brings_foreign_part"]),
            "wrong_options_omitting_a_required_part": sum(
                record["variation"]["wrong_options_omitting_a_required_part"]
                for record in lists),
            "wrong_options_bringing_a_foreign_part": sum(
                record["variation"]["wrong_options_bringing_a_foreign_part"]
                for record in lists),
            "correct_is_unique_longest": sum(
                1 for record in lists
                if record["variation"]["correct_is_unique_longest"]),
            "correct_is_unique_shortest": sum(
                1 for record in lists
                if record["variation"]["correct_is_unique_shortest"]),
            "profiles": {profile: sum(1 for record in lists
                                      if record["variation"]["profile"] == profile)
                         for profile in sorted({record["variation"]["profile"]
                                                for record in lists})},
        },
        "reach_answers": {label: sum(
            1 for record in records if record["op"] == "REACHED_VIA"
            and record["correct"].split(":")[0] == label)
            for label in ("direct", "via", "absent")},
        "shared_part_answers": {label: sum(
            1 for record in records if record["op"] == "FIND_SHARED_PART"
            and (record["correct"] == "none") == (label == "none"))
            for label in ("part", "none")},
        "find_shared_part": {
            "equal_length_lessons": sum(
                1 for record in records if record["op"] == "FIND_SHARED_PART"
                and record["variation"].get("shared_equal_length")),
            "lessons_offering_none": sum(
                1 for record in records if record["op"] == "FIND_SHARED_PART"
                and record["variation"].get("shared_none_is_an_option")),
            "none_is_the_answer": sum(
                1 for record in records if record["op"] == "FIND_SHARED_PART"
                and record["correct"] == "none"),
        },
        "exposure_at_256_updates": exposure(records, 256),
        "boundary": ("curriculum construction only: no training, no checkpoint "
                     "selection, no tokenizer fitting, no answer exposure"),
    }
