"""Stage 2 syntax: six-node complete assignments, with original answer grammar.

Only syntactic enumeration changes. This module never reads graph truth.
"""
from itertools import permutations
from .answers import (answer_space, declaration_ref, make_answer, validate_answer,
                      validate_query, AnswerContractError, _require)

MAX_PERMUTATION_NODES = 6


def correspondence_candidates(public, query, *, max_nodes=MAX_PERMUTATION_NODES):
    """Bounded grammar-only candidates; includes wrong mappings and NO_MATCH.

    The only selection inputs are public scoped node inventories and a ceiling
    no larger than six. No graph edges or teacher labels enter permutation
    generation. Ten-node syntax admission does not admit 10! numerical work.
    """
    _require(type(max_nodes) is int and 1 <= max_nodes <= MAX_PERMUTATION_NODES,
             "TYPED_PERMUTATION_LIMIT")
    space = answer_space(public, query)
    _require(query["kind"] == "correspondence", "TYPED_CANDIDATES_KIND")
    inv = space["inventory"]
    left, right = sorted(inv["source_nodes"]), sorted(inv["target_nodes"])
    _require(max(len(left), len(right)) <= max_nodes, "TYPED_PERMUTATION_BOUND")
    candidates = [{"status": "NO_MATCH", "pairs": []}]
    if len(left) == len(right):
        candidates += [{"status": "MAPPING",
                        "pairs": [{"source": a, "target": b} for a, b in zip(left, row)]}
                       for row in permutations(right)]
    return candidates
