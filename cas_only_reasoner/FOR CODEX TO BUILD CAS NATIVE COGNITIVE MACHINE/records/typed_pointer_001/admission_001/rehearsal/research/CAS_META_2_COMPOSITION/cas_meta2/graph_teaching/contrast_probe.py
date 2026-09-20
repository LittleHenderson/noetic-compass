"""Zero-update contrast probe on the RETAINED checkpoints.

Executed on six retained curriculum checkpoints on 2026-09-16. Exact inputs,
raw results and conditional interpretation: records/graph6_contrast_001/RESULT.md.

Owner-directed (2026-09-10). The question this answers is not "can the learner be
trained further" but "when the learner answers a practised question correctly,
which changes break that answer". Four contrasts are applied to each correctly
answered practice case, with NO optimizer step ever taken:

  1. ``original`` — the practice case exactly as taught;
  2. ``renamed`` — every node relabelled consistently in the graph, the question
     AND the options (a correct answer must follow the renaming);
  3. ``reordered`` — the written connectors permuted, names unchanged (a correct
     answer must NOT change);
  4. ``rewired`` — one ``contains`` connection moved to another whole so the
     relationship itself changes (a correct answer must follow the structure).

Everything is derived from the stored graph by the deterministic reference
checker; nothing is hand-written, and the module never updates a parameter.
Renaming is label-invariant only if it is applied consistently: the option that
was correct must map to the correspondingly renamed option, which is what this
module builds and checks.

A fifth, separate reading is also recorded because the delivered result showed
``LIST_PARTS`` far below chance on new arrangements (control 5/90, varied 18/90):
``list_length_probe`` re-scores each correctly answered list question with its
option vectors permuted by length, so an option-length bias is visible directly
rather than inferred.
"""
from __future__ import annotations

import random
from contextlib import nullcontext
from itertools import permutations

from . import lessons, reference
from .graph import Graph, canonical, digest, require

PROBE_SCHEMA = "cas-graph-training-contrast-probe/1"
RESULT_SCHEMA = "cas-graph-training-contrast-probe-result/2"
CONTRASTS = ("original", "renamed", "reordered", "rewired")
CONTRAST_SEED = 20260927
MAX_CASES_PER_LEARNER = 30


def _rename_plan(graph, rng):
    """A consistent one-to-one relabelling of every node in the graph."""
    labels = [node.identifier for node in graph.nodes]
    replacements = ["r%02d_%s" % (index, label) for index, label in enumerate(labels)]
    rng.shuffle(replacements)
    return dict(zip(labels, replacements))


def rename_record(record, plan):
    """Apply the relabelling to graph, question, options and answer together."""
    def renamed(value):
        if isinstance(value, list):
            return sorted(renamed(item) for item in value)
        if isinstance(value, str) and value.startswith("via:"):
            return "via:" + plan.get(value[4:], value[4:])
        return plan.get(value, value)

    graph = record["graph"]
    nodes = [{"identifier": plan[node["identifier"]], "kind": node["kind"],
              "fields": [list(pair) for pair in node["fields"]]}
             for node in graph["nodes"]]
    relations = []
    for relation in graph["relations"]:
        content = list(relation["content"])
        if relation["kind"] == "contains":
            content = ["constituent", plan[content[1]]]
        relations.append({"kind": relation["kind"],
                          "source": plan[relation["source"]],
                          "target": plan[relation["target"]],
                          "content": content})
    return {"graph": {**graph, "nodes": nodes, "relations": relations},
            "question": {key: renamed(value) for key, value in record["question"].items()},
            "options": [renamed(option) for option in record["options"]],
            "correct": renamed(record["correct"])}


def reorder_record(record, rng):
    """Permute the written connectors and the node order; nothing else changes."""
    graph = record["graph"]
    nodes = list(graph["nodes"])
    relations = list(graph["relations"])
    rng.shuffle(nodes)
    rng.shuffle(relations)
    return {"graph": {**graph, "nodes": nodes, "relations": relations},
            "question": dict(record["question"]),
            "options": list(record["options"]),
            "correct": record["correct"]}


def _other_whole(graph, idea):
    for node in graph.nodes:
        if node.identifier != idea and reference.direct_parts(graph, node.identifier):
            return node.identifier
    return None


def rewire_record(record, rng):
    """Move one ``contains`` connection from the asked whole to another whole.

    Returns ``None`` when this case cannot be rewired cleanly: the moved part must
    not already be a part of the receiving whole (that would duplicate a connector
    and the graph would refuse it), and the asked whole must keep at least one
    part so the question is still answerable.
    """
    graph = Graph.from_record(record["graph"])
    question = record["question"]
    if record["op"] != "LIST_PARTS":
        return None
    idea = question["idea"]
    parts = reference.direct_parts(graph, idea)
    if len(parts) < 2:
        return None
    receivers = [node.identifier for node in graph.nodes
                 if node.identifier != idea
                 and reference.direct_parts(graph, node.identifier)]
    movable = {part: [receiver for receiver in receivers
                      if part not in reference.direct_parts(graph, receiver)]
               for part in parts}
    movable = {part: options for part, options in movable.items() if options}
    if not movable:
        return None
    moved = sorted(movable)[rng.randrange(len(movable))]
    receiver = sorted(movable[moved])[rng.randrange(len(movable[moved]))]
    relations = []
    for relation in record["graph"]["relations"]:
        if (relation["kind"] == "contains" and relation["source"] == idea
                and relation["target"] == moved):
            relations.append({**relation, "source": receiver})
        else:
            relations.append(relation)
    edited = {**record["graph"], "nodes": list(record["graph"]["nodes"]),
              "relations": relations}
    edited_graph = Graph.from_record(edited)
    correct = reference.direct_parts(edited_graph, idea)
    options = [list(correct), list(parts), sorted(set(correct) | {moved})]
    deduped = []
    for option in options:
        if option not in deduped:
            deduped.append(option)
    while len(deduped) < 3:
        deduped.append(sorted(set(parts) - set(correct)) or list(parts))
    return {"graph": edited, "question": dict(question), "options": deduped[:3],
            "correct": correct}


def correctly_answered(learner, practice_predictions):
    """The practice records this learner answered correctly (from its own result)."""
    return [record_id for record_id, row in practice_predictions.items() if row]


def build_probe_cases(records, correct_ids, *, seed=CONTRAST_SEED,
                      maximum=MAX_CASES_PER_LEARNER):
    """For each correctly answered practice case, build the four contrasts."""
    rng = random.Random(seed)
    by_id = {record["record_id"]: record for record in records}
    cases = []
    for record_id in sorted(correct_ids)[:maximum]:
        record = by_id.get(record_id)
        if record is None:
            continue
        plan = _rename_plan(Graph.from_record(record["graph"]), rng)
        variants = {"original": {"graph": record["graph"], "question": record["question"],
                                 "options": list(record["options"]),
                                 "correct": record["correct"]},
                    "renamed": rename_record(record, plan),
                    "reordered": reorder_record(record, rng)}
        rewired = rewire_record(record, rng)
        variants["rewired"] = rewired
        cases.append({"record_id": record_id, "op": record["op"], "plan": plan,
                      "variants": variants})
    return cases


def validate_probe_cases(cases):
    """Every contrast must be well formed, and the correct answer must remain
    present exactly once. For a renamed case the correct option must be the
    renamed original — that is what makes the contrast meaningful."""
    for case in cases:
        for name, variant in case["variants"].items():
            if variant is None:
                continue
            Graph.from_record(variant["graph"]).validate()
            require(variant["options"].count(variant["correct"]) == 1,
                    "PROBE_CORRECT_OPTION:%s:%s" % (case["record_id"], name))
            require(len(variant["options"]) == 3,
                    "PROBE_OPTION_COUNT:%s:%s" % (case["record_id"], name))
        original = case["variants"]["original"]
        renamed = case["variants"]["renamed"]
        plan = case["plan"]
        expected = original["correct"]
        if isinstance(expected, list):
            expected = sorted(plan.get(item, item) for item in expected)
        elif isinstance(expected, str) and expected.startswith("via:"):
            expected = "via:" + plan.get(expected[4:], expected[4:])
        else:
            expected = plan.get(expected, expected)
        require(renamed["correct"] == expected,
                "PROBE_RENAME_NOT_CONSISTENT:" + case["record_id"])
    return cases


def probe_digest(cases):
    """Bind graph, question, ordered options and rename map, not just choices."""
    return digest(canonical(cases))


def _unrename(value, plan):
    reverse = {new: old for old, new in plan.items()}
    if isinstance(value, list):
        return sorted(_unrename(item, plan) for item in value)
    if isinstance(value, str) and value.startswith("via:"):
        return "via:" + reverse.get(value[4:], value[4:])
    return reverse.get(value, value)


def public_probe_input(record, variant, *, arm="cas"):
    """Re-render changed structure and bypass the retained training-ID cache.

    The inherited ID is used only for the original public option shuffle, so
    renaming/reordering cannot confound the comparison with a new choice order.
    The learner receives an ID derived from answer-free public bytes instead.
    """
    from . import adapter
    graph = Graph.from_record(variant["graph"])
    changed = {**record, **variant, "framings": {
        arm: lessons._render_prompt(record["op"], graph, variant["question"], arm)}}
    task = adapter.public_records(changed, arm)
    public = {key: task[key] for key in ("public", "encoded_options", "op")}
    public["record_id"] = "contrast:" + digest(canonical(public))
    return public


def list_length_inputs(public):
    """Every slot permutation, ordered by public list length; targets unused.

    This exposes slot sensitivity and chosen lengths. It cannot alone prove
    that a preference for longer options caused a wrong semantic answer.
    """
    ordered = sorted(public["encoded_options"], key=lambda x: (len(x), canonical(x)))
    for options in permutations(ordered):
        task = {**public, "encoded_options": list(options), "public": {
            **public["public"], "observations": [
                {"slot": index, "tag": str(option)[:256], "values": [0.0] * 8}
                for index, option in enumerate(options)]}}
        task["record_id"] = "contrast:length:" + digest(canonical({
            key: task[key] for key in ("public", "encoded_options", "op")}))
        yield task


def summarise(per_case):
    """Answer-change statistics: the reading the owner asked for."""
    summary = {name: {"attempted": 0, "correct": 0} for name in CONTRASTS}
    changes = {"renamed_changed_answer": 0, "reordered_changed_answer": 0,
               "rewired_changed_answer": 0}
    for row in per_case:
        for name in CONTRASTS:
            entry = row.get(name)
            if entry is None:
                continue
            summary[name]["attempted"] += 1
            summary[name]["correct"] += int(entry["correct"])
        if row.get("renamed") and row["renamed"].get(
                "predicted_in_original_names", row["renamed"]["predicted"]
                ) != row["original"]["predicted"]:
            changes["renamed_changed_answer"] += 1
        if row.get("reordered") and row["reordered"]["predicted"] != row["original"]["predicted"]:
            changes["reordered_changed_answer"] += 1
        if row.get("rewired") and row["rewired"]["predicted"] != row["original"]["predicted"]:
            changes["rewired_changed_answer"] += 1
    return {"accuracy": {name: {**stats,
                                "rate": (stats["correct"] / stats["attempted"]
                                         if stats["attempted"] else None)}
                         for name, stats in summary.items()},
            "answer_changes": changes,
            "boundary": ("zero optimizer steps were taken; the probe only records "
                         "which option the retained learner selects")}


def run_probe(*, torch, learner, records, practice_predictions, device=None,
              seed=CONTRAST_SEED, arm="cas"):
    """Record the four contrasts for each correctly answered practice case.

    The learner must already exist (loaded from a retained checkpoint); this
    function never calls ``step`` and never touches an optimizer.
    """
    require(arm in ("cas", "generic"), "PROBE_ARM")
    correct_ids = {record_id for record_id, row in practice_predictions.items()
                   if row}
    cases = validate_probe_cases(build_probe_cases(records, correct_ids, seed=seed))
    per_case, lengths = [], []
    by_id = {record["record_id"]: record for record in records}
    module = getattr(learner, "module", None)
    training = getattr(module, "training", None)
    identity = getattr(learner, "checkpoint_identity", None)
    before = identity() if identity else None
    if module is not None:
        module.eval()
    try:
        with torch.no_grad() if torch is not None else nullcontext():
            for case in cases:
                row = {"record_id": case["record_id"], "op": case["op"]}
                for name, variant in case["variants"].items():
                    if variant is None:
                        row[name] = None
                        continue
                    task = public_probe_input(by_id[case["record_id"]], variant, arm=arm)
                    predicted = learner.predict(task)
                    require(predicted in task["encoded_options"], "PROBE_PREDICTION_NOT_OPTION")
                    row[name] = {"predicted": predicted,
                                 "correct": predicted == variant["correct"],
                                 "options": list(task["encoded_options"]),
                                 "public_input_sha256": digest(canonical(task))}
                    if name == "renamed":
                        row[name]["predicted_in_original_names"] = _unrename(predicted, case["plan"])
                    if name == "original" and case["op"] == "LIST_PARTS":
                        for length_task in list_length_inputs(task):
                            choice = learner.predict(length_task)
                            require(choice in length_task["encoded_options"], "PROBE_PREDICTION_NOT_OPTION")
                            lengths.append({"record_id": case["record_id"],
                                "public_input_sha256": digest(canonical(length_task)),
                                "options": length_task["encoded_options"],
                                "option_lengths": [len(x) for x in length_task["encoded_options"]],
                                "predicted": choice, "chosen_length": len(choice),
                                "chosen_slot": length_task["encoded_options"].index(choice),
                                "correct": choice == variant["correct"]})
                per_case.append(row)
    finally:
        if module is not None and training is not None:
            module.train(training)
    after = identity() if identity else None
    require(before == after, "PROBE_WEIGHTS_CHANGED")
    return {"schema": RESULT_SCHEMA, "cases": len(per_case),
            "probe_digest": probe_digest(cases),
            "per_case": per_case, "summary": summarise(per_case),
            "arm": arm, "list_length_probe": lengths,
            "parameter_digest_before": before, "parameter_digest_after": after,
            "weights_unchanged": True if before is not None else None,
            "length_probe_boundary": "Slot sensitivity and chosen lengths; not causal proof of length bias.",
            "optimizer_steps_taken": 0}
