"""Graph→^6 adapter contract: exactly what enters the module, what it
predicts, how each operation is scored, and which parameters update.

Pure core (no torch at module level). The real torch path lives in
``real_framework.py`` and is imported lazily by the trainer only for an AWS
run.

The chain, verbatim from the review:

    Public graph + question
              |
              v
    Actual ^6 neural computation   (the decompose module)
              |
              v
    Predicted parts, shared part, or path
              |
              v
    Training correction            (deterministic checker, never during inference)
              |
              v
    Updates to the permitted ^6 parameters only

Encoding contract:
- ``encode_graph`` renders the graph record into a deterministic token
  sequence: node lines (label, kind, contents) then connector lines (source,
  kind, target, content). The question and options are appended by
  ``build_task``. Nothing in the encoding carries the answer.
- The real encoder maps tokens to ids through the campaign's frozen public
  tokenizer; the embedding layer is FROZEN for the run (only the module's
  own parameters learn).

Output contract:
- The module returns one d_model vector. A FROZEN readout scores each option
  by dot product against the option's mean embedded representation; the
  prediction is the argmax. No learned head exists outside the module, so the
  training signal can only change the module's parameters.

Scoring contract (per operation, all against the checker-derived answer):
- LIST_PARTS: option = sorted part list; scored by option index.
- FIND_SHARED_PART: option = shared constituent or 'none'.
- REACHED_VIA: option = 'direct' | 'via:<constituent>' | 'absent'.
"""
from __future__ import annotations

import json
import math
import random

from .graph import Graph
from .lessons import EXERCISE_SCHEMA

ADAPTER_SCHEMA = "cas-meta2-graph-teaching-adapter/1"


def require(condition, code):
    if not condition:
        raise ValueError(code)


def encode_graph(graph_record):
    """Deterministic token sequence for one graph (no question, no answer)."""
    graph = Graph.from_record(graph_record)
    tokens = []
    for node in graph.nodes:
        fields = " ".join("%s=%s" % (name, value) for name, value in node.fields)
        tokens.append("node")
        tokens.append(node.identifier)
        tokens.append("kind=" + node.kind)
        if fields:
            tokens.append(fields)
    for relation in graph.relations:
        tokens.append("rel")
        tokens.append(relation.source)
        tokens.append(relation.kind)
        tokens.append(relation.target)
        tokens.append("common=" + ",".join(map(str, relation.content)))
    return tokens


def build_task(record, arm):
    """Full module input for one exercise: tokens, options, correct index."""
    require(record.get("schema") == EXERCISE_SCHEMA, "TASK_RECORD_SCHEMA")
    require(arm in ("cas", "generic"), "ARM_UNKNOWN")
    tokens = encode_graph(record["graph"])
    tokens.append("question")
    for key in ("op", "idea", "a", "b", "part", "object", "field", "value",
                "request", "requirements"):
        if key in record["question"]:
            tokens.append(str(record["question"][key]))
    tokens.append("options")
    for option in record["options"]:
        tokens.append(str(option))
    correct = record["correct"]
    options = record["options"]
    require(options.count(correct) == 1, "TASK_CORRECT_OPTION_MISSING")
    return {"record_id": record["record_id"], "op": record["op"], "arm": arm,
            "tokens": tokens, "options": options,
            "correct_index": options.index(correct),
            "correct": correct, "graph": record["graph"],
            "prompt": record["framings"][arm]}


def option_vector(tokens_for_option, embedder):
    """Frozen readout support: mean embedding of one option's tokens."""
    vectors = [embedder(token) for token in tokens_for_option]
    require(vectors, "OPTION_EMBEDDING_REQUIRED")
    size = len(vectors[0])
    mean = [sum(vector[dim] for vector in vectors) / len(vectors)
            for dim in range(size)]
    return mean


def readout(prediction_vector, option_vectors):
    """Frozen dot-product scores over options."""
    scores = [sum(p * v for p, v in zip(prediction_vector, vector))
              for vector in option_vectors]
    return scores


def predict(prediction_vector, option_vectors):
    """Argmax selection — the module's own answer, computed at inference."""
    scores = readout(prediction_vector, option_vectors)
    return max(range(len(scores)), key=lambda index: scores[index])


def score(prediction_vector, option_vectors, correct_index):
    """Cross-entropy value (pure formula; the real run uses the torch version
    for backprop)."""
    scores = readout(prediction_vector, option_vectors)
    maximum = max(scores)
    shifted = [value - maximum for value in scores]
    log_denominator = math.log(sum(math.exp(value) for value in shifted))
    return -(scores[correct_index] - maximum - log_denominator)


def scoring_table():
    return {
        "LIST_PARTS": {"target": "sorted direct parts list",
                       "scored": "option index over part-list options"},
        "FIND_SHARED_PART": {"target": "shared constituent or 'none'",
                             "scored": "option index over part/none options"},
        "REACHED_VIA": {"target": "direct | via:<constituent> | absent",
                        "scored": "option index over reach options"},
    }


def public_records(record, arm):
    """One frozen public record per exercise: problem + EXACTLY 3 observations.

    Boundary (owner ruling): the public exercise is THREE UNMARKED choices;
    the learner decides which answers the question. The private target is
    NEVER used to order, position, mark, or specially encode a choice: the
    three options are ordered deterministically from the PUBLIC content only
    (digest of the record id), so changing or removing the private target
    does not change the encoded input. The separate target is returned as
    ``encoded_correct_index`` for the checker's corrective feedback during
    training only.

    Padding uses the literal 'none_of_the_above' option, which never collides
    with lesson options (part names, 'none', or part lists).

    Choice meanings (the three-slot interface does not change the lessons):
    LIST_PARTS option = the COMPLETE sorted list of direct constituents;
    FIND_SHARED_PART option = ONE shared constituent or 'none';
    REACHED_VIA option = the COMPLETE reach label (direct | via:<constituent>
    | absent).
    """
    from ..codec import validate_public  # frozen public contract (pure)
    from .graph import digests
    require(record.get("schema") == EXERCISE_SCHEMA, "TASK_RECORD_SCHEMA")
    require(arm in ("cas", "generic"), "ARM_UNKNOWN")
    options = list(record["options"])
    correct = record["correct"]
    require(options.count(correct) == 1, "TASK_CORRECT_OPTION_MISSING")
    pad = "none_of_the_above"
    ordered = [option for option in options if option != pad]
    if len(ordered) > 3:  # never drop the correct option
        ordered = [correct] + [option for option in ordered if option != correct][:2]
    while len(ordered) < 3:
        ordered.append(pad)
    # public-content-derived deterministic order; NEVER correct-first
    seed = int(digests(record["record_id"] + ":" + arm)[:8], 16)
    random.Random(seed).shuffle(ordered)
    require(len(ordered) == 3 and ordered.count(correct) == 1, "PUBLIC_OPTION_ENCODING")
    observations = [{"slot": index, "tag": str(option)[:256], "values": [0.0] * 8}
                    for index, option in enumerate(ordered)]
    public = {"problem": record["framings"][arm][:8192], "observations": observations}
    validate_public(public)
    return {"public": public, "encoded_options": ordered,
            "encoded_correct_index": ordered.index(correct),
            "record_id": record["record_id"], "op": record["op"],
            "correct": correct}
