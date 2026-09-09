"""Prepared neural diagnostic for the ln(3) flat-loss symptom.

Neural execution requires separate owner authorization; this module is the
fail-closed measurement spec. It runs ONLY inside an authorized AWS job and
measures the quantities the non-neural diagnostic cannot:

  1. per-record three scores and their spread (after the frozen projection,
     mean-pooling, the ^6 module, and the fixed readout),
  2. pairwise cosine similarity among the three option vectors and between
     the problem vector and each option vector,
  3. a same-example, alternative-target gradient test: loss values and
     per-matrix gradient norms (left.weight, merge.weight, right.weight) for
     each of the three targets, WITHOUT any optimizer step.
  4. per-record module OUTPUT vectors: norm per record and pairwise cosines
     across the first few records (near-constant output is measured, not
     assumed).
  5. individual TAG vectors before pooling — do different part names map to
     nearly the same numbers?
  6. OLD (sum-over-every-token) vs CORRECTED (sum-over-tokens-not-shared-by-
     all-three) option vectors on the SAME examples and SAME fixed weights:
     actual score spreads under both, not only cosine statistics.
  7. graph-edit response: valid synthetic graph edits → rebuilt public
     problem text → encoded → mean-pooled problem vector → module output —
     does the changed relationship survive encoding and change the output
     and the decision?

No weights are updated. Results are returned as a JSON-safe report for the
authorized run's evidence path.
"""
from __future__ import annotations

import json

from . import adapter, lessons
from .graph import Graph, require

DIAGNOSTIC_SCHEMA = "cas-graph-training-ln3-neural-diagnostic/1"


def _cosine(learner, a, b):
    dot = float(learner.torch.dot(a, b).item())
    norm_a = float(learner.torch.linalg.vector_norm(a).item())
    norm_b = float(learner.torch.linalg.vector_norm(b).item())
    return dot / (norm_a * norm_b + 1e-12)


def _option_vectors(learner, position):
    return learner._option_vectors[position]


def _problem_vector(learner, position):
    return learner._problem_vectors[position]


def measure_scores(learner):
    """Three scores + spread per record (no updates)."""
    rows = []
    for position, task in enumerate(learner.tasks):
        scores = learner.forward(position)
        rows.append({
            "record_id": task["record_id"], "op": task["op"],
            "scores": [float(value.item()) for value in scores],
            "spread": float((scores.max() - scores.min()).item()),
            "correct_slot": task["encoded_correct_index"],
            "correct_score": float(scores[task["encoded_correct_index"]].item())})
    return rows


def measure_option_geometry(learner):
    """Pairwise cosine among option vectors; problem-option cosine."""
    rows = []
    for position, task in enumerate(learner.tasks):
        options = _option_vectors(learner, position)
        problem = _problem_vector(learner, position)
        option_pairs = [_cosine(learner, options[i], options[j])
                        for i in range(3) for j in range(i + 1, 3)]
        problem_option = [_cosine(learner, problem, option) for option in options]
        rows.append({"record_id": task["record_id"], "op": task["op"],
                     "option_pair_cosines": option_pairs,
                     "problem_option_cosines": problem_option})
    return rows


def measure_module_outputs(learner):
    """Per-record module output vector: norm per record and pairwise cosines
    across the first few records (the near-constant-output hypothesis behind
    FIND_SHARED_PART's residual flatness — measured, not assumed)."""
    torch = learner.torch
    vectors = []
    for position in range(len(learner.tasks)):
        value = learner.module(learner._problem_vectors[position].unsqueeze(0))[0]
        vectors.append(value)
    norms = [float(torch.linalg.vector_norm(value).item()) for value in vectors]
    per_record = [{"record_id": learner.tasks[position]["record_id"],
                   "op": learner.tasks[position]["op"],
                   "output_norm": norms[position]}
                  for position in range(len(learner.tasks))]
    limit = min(8, len(vectors))
    cosines = []
    for i in range(limit):
        for j in range(i + 1, limit):
            dot = float(torch.dot(vectors[i], vectors[j]).item())
            cosines.append(dot / (norms[i] * norms[j] + 1e-12))
    return {"per_record": per_record,
            "pairwise_cosines_first_records": limit,
            "pairwise_cosines": cosines,
            "output_norm_stats": {"min": min(norms), "max": max(norms),
                                  "median": sorted(norms)[len(norms) // 2]}}


def measure_tag_vectors(learner, limit=10):
    """Individual tag embeddings BEFORE pooling: do different part names
    already map to nearly the same numbers? Norms per distinct tag token and
    pairwise cosines among the first few."""
    torch = learner.torch
    encoder = learner.framework.encoder
    vocabulary = encoder["tokenizer"].vocabulary
    observation_id = vocabulary.index("[OBS]")
    distinct = []
    for task in learner.tasks:
        _, slot_ids = encoder["encode"](task["public"])
        for slot in (0, 1, 2):
            for token_id in slot_ids[slot]:
                if token_id != observation_id and token_id not in distinct:
                    distinct.append(token_id)
        if len(distinct) >= limit:
            break
    rows = []
    vectors = []
    for token_id in distinct[:limit]:
        vector = encoder["embed"](token_id)
        vectors.append(vector)
        rows.append({"tag": vocabulary[token_id],
                     "norm": float(torch.linalg.vector_norm(vector).item())})
    cosines = [_cosine(learner, vectors[i], vectors[j])
               for i in range(len(vectors)) for j in range(i + 1, len(vectors))]
    return {"tag_rows": rows, "pairwise_cosines": cosines,
            "tags_measured": len(vectors)}


def measure_representation_comparison(learner):
    """OLD (sum over every token occurrence) vs CORRECTED (sum over tokens
    NOT shared by all three) option vectors on the SAME examples and SAME
    fixed weights: actual score spreads under both, plus both cosine sets.
    Removing an identical vector from every option only shifts all scores
    equally (softmax-invariant); because shared tokens occur with DIFFERENT
    counts per option, the removal can change score differences — this
    measurement reports whether it actually does, without any update."""
    torch = learner.torch
    rows = []
    for position, task in enumerate(learner.tasks):
        _, slot_ids = learner.framework.encoder["encode"](task["public"])
        sequences = [slot_ids[slot] for slot in (0, 1, 2)]
        old = [learner._sum(sequence) for sequence in sequences]
        new = learner._option_vectors[position]
        value = learner.module(learner._problem_vectors[position].unsqueeze(0))[0]

        def score_values(vectors):
            return [float(torch.dot(value, vector).item()) for vector in vectors]

        scores_old = score_values(old)
        scores_new = score_values(new)
        rows.append({
            "record_id": task["record_id"], "op": task["op"],
            "scores_old": scores_old, "scores_new": scores_new,
            "spread_old": max(scores_old) - min(scores_old),
            "spread_new": max(scores_new) - min(scores_new),
            "argmax_old": scores_old.index(max(scores_old)),
            "argmax_new": scores_new.index(max(scores_new)),
            "option_pair_cosines_old": [_cosine(learner, old[i], old[j])
                                        for i in range(3) for j in range(i + 1, 3)],
            "option_pair_cosines_new": [_cosine(learner, new[i], new[j])
                                         for i in range(3) for j in range(i + 1, 3)],
        })
    return rows


def _graph_edits(record):
    """Valid synthetic graph edits (no answers involved): (a) retarget one
    contains connector; (b) append one node field; (c) a SAME-TOKEN-COUNT
    rewiring — swap the sources of two contains connectors, preserving the
    problem token multiset exactly while changing the relationships; (d) a
    connection-list REORDER — same graph, same multiset, different written
    order (the equivalence control for the rewiring contrast)."""
    edits = []
    edited = json.loads(json.dumps(record["graph"]))
    contains = [relation for relation in edited["relations"]
                if relation["kind"] == "contains"]
    if contains:
        source = contains[0]["source"]
        taken = {relation["target"] for relation in contains}
        other = next(node["identifier"] for node in edited["nodes"]
                     if node["identifier"] != source
                     and node["identifier"] not in taken)
        contains[0]["target"] = other
        contains[0]["content"] = ["constituent", other]
        edits.append(("connector_retarget", edited))
    edited = json.loads(json.dumps(record["graph"]))
    edited["nodes"][0]["fields"].append(["edited", "marker"])
    edits.append(("node_contents", edited))
    edited = json.loads(json.dumps(record["graph"]))
    contains = [relation for relation in edited["relations"]
                if relation["kind"] == "contains"]
    existing = {(relation["kind"], relation["source"], relation["target"])
                for relation in edited["relations"]}
    pairs = [(i, j) for i in range(len(contains)) for j in range(i + 1, len(contains))
             if contains[i]["source"] != contains[j]["source"]
             and (contains[i]["kind"], contains[j]["source"], contains[i]["target"])
             not in existing
             and (contains[i]["kind"], contains[i]["source"], contains[j]["target"])
             not in existing]
    if pairs:
        i, j = pairs[0]
        contains[i]["source"], contains[j]["source"] = (
            contains[j]["source"], contains[i]["source"])
        edits.append(("connector_rewire_same_tokens", edited))
    edited = json.loads(json.dumps(record["graph"]))
    edited["relations"].reverse()
    edits.append(("connection_list_reorder", edited))
    return edits


def measure_graph_edit_response(learner, records, arm, limit=3):
    """Relevant graph changes: rebuild the PUBLIC problem text through the
    SAME lessons framing, encode with the RELATIONSHIP-PRESERVING problem
    encoder, and run the module. Reports whether the changed relationship
    survives encoding and changes the module output and the decision — for
    both representations, zero updates."""
    torch = learner.torch
    rows = []
    for record in [row for row in records if row["op"] == "LIST_PARTS"][:limit]:
        baseline_public = adapter.public_records(record, arm)["public"]
        baseline_ids, _ = learner.framework.encoder["encode"](baseline_public)
        baseline_vector = learner.framework.encoder["encode_problem"](baseline_public)
        value = learner.module(baseline_vector.unsqueeze(0))[0]
        position = learner._index[record["record_id"]]
        options = learner._option_vectors[position]
        for edit_kind, edited_graph in _graph_edits(record):
            edited_public = {
                "problem": lessons._render_prompt(
                    record["op"], Graph.from_record(edited_graph),
                    record["question"], arm)[:8192],
                "observations": baseline_public["observations"]}
            edited_ids, _ = learner.framework.encoder["encode"](edited_public)
            edited_vector = learner.framework.encoder["encode_problem"](edited_public)
            changed = learner.module(edited_vector.unsqueeze(0))[0]
            norm_value = float(torch.linalg.vector_norm(value).item())
            norm_changed = float(torch.linalg.vector_norm(changed).item())
            difference_squared = (norm_value ** 2 + norm_changed ** 2
                                  - 2 * float(torch.dot(value, changed).item()))
            difference_norm = max(0.0, difference_squared) ** 0.5
            baseline_scores = [float(torch.dot(value, option).item())
                               for option in options]
            edited_scores = [float(torch.dot(changed, option).item())
                             for option in options]
            rows.append({
                "record_id": record["record_id"], "edit": edit_kind,
                "problem_token_count_before": len(baseline_ids),
                "problem_token_count_after": len(edited_ids),
                "problem_token_multiset_equal": sorted(baseline_ids) == sorted(edited_ids),
                "output_norm_baseline": norm_value,
                "output_norm_edited": norm_changed,
                "output_cosine": _cosine(learner, value, changed),
                "output_difference_norm": difference_norm,
                "scores_baseline": baseline_scores,
                "scores_edited": edited_scores,
                "argmax_baseline": baseline_scores.index(max(baseline_scores)),
                "argmax_edited": edited_scores.index(max(edited_scores)),
            })
    return rows


def check_target_independence(records, arm):
    """Pure check (no torch): changing the PRIVATE corrective target leaves
    the PUBLIC record byte-identical — the learner's encoded input cannot
    depend on the answer. The public contract has no target field; this
    verifies it end to end on permitted training/practice records."""
    rows = []
    for record in records:
        baseline = adapter.public_records(record, arm)["public"]
        alternatives = [option for option in record["options"]
                        if option != record["correct"]]
        if not alternatives:
            continue
        altered = dict(record)
        altered["correct"] = alternatives[0]
        changed = adapter.public_records(altered, arm)["public"]
        rows.append({"record_id": record["record_id"],
                     "public_unchanged": baseline == changed})
    return rows


def measure_gradient_test(learner, position):
    """Same example, three alternative targets, NO optimizer step.

    Returns per-target loss and per-matrix gradient norms. The forward is
    recomputed INSIDE the per-target loop so each backward consumes its own
    graph (attempt 001's preserved error was a second backward through an
    already-freed graph). The module forward is deterministic (dropout 0.0),
    so the three recomputations return identical scores. Weight decay is
    0.0 in the learner, so any parameter movement in the recorded pilot came
    from these task gradients.
    """
    task = learner.tasks[position]
    module = learner.module
    results = []
    for target in (0, 1, 2):
        module.zero_grad()
        scores = learner.forward(position)  # fresh graph per target
        loss = learner.torch.nn.functional.cross_entropy(
            scores.unsqueeze(0),
            learner.torch.tensor([target], device=learner.device))
        loss.backward()
        norms = {}
        for name, parameter in module.named_parameters():
            if parameter.grad is not None:
                norms[name] = float(
                    learner.torch.linalg.vector_norm(parameter.grad).item())
        results.append({"target": target,
                        "loss": float(loss.item()),
                        "gradient_norms": norms,
                        "correct_target": task["encoded_correct_index"]})
    return {"record_id": task["record_id"], "op": task["op"], "results": results}


def launch(*, run_id, learner, records=None, arm="cas"):
    """Authorized-run measurement; no updates are performed."""
    require(type(run_id) is str and run_id, "RUN_ID_REQUIRED")
    require(learner is not None, "LEARNER_REQUIRED")
    require(arm in ("cas", "generic"), "ARM_UNKNOWN")
    report = {"schema": DIAGNOSTIC_SCHEMA, "run_id": run_id,
              "scores": measure_scores(learner),
              "option_geometry": measure_option_geometry(learner),
              "module_outputs": measure_module_outputs(learner),
              "tag_vectors": measure_tag_vectors(learner),
              "representation_comparison": measure_representation_comparison(learner),
              "graph_edit_response": (measure_graph_edit_response(learner, records, arm)
                                      if records else []),
              "target_independence": (check_target_independence(records, arm)
                                      if records else []),
              "gradient_test": [measure_gradient_test(learner, position)
                                for position in range(min(3, len(learner.tasks)))],
              "boundary": ("measurement only; no optimizer step was taken; "
                           "weights unchanged by this diagnostic")}
    return report
