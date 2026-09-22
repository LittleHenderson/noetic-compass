"""R2 structural-memory interface, not learned computation or compression.

Input structure is deliberately retained. An input parser or a model prediction
may supply it; a reconstruction target must never be passed as visible input.
Node vectors are caller-supplied. This module learns/evaluates no CAS operation.
"""
from dataclasses import dataclass, replace

from learner_q4_decoder import DecodeLimits, ast_to_tokens, tokens_to_ast
from learner_q4_representation import Bottleneck, Q4InputError

SCHEMA = "helm-cas-expression-lab.q4-structured-memory/0.1"


@dataclass(frozen=True, slots=True)
class MemoryNode:
    position: int
    parent: int | None
    role: str
    kind: str
    attributes: tuple[tuple[str, str | None], ...]
    children: tuple[int, ...]
    vector: Bottleneck


@dataclass(frozen=True, slots=True)
class StructuredMemory:
    nodes: tuple[MemoryNode, ...]
    origin: str
    model_identity: str
    context: tuple[tuple[str, str], ...]
    schema: str = SCHEMA
    representation_kind: str = "R2_STRUCTURED_MEMORY_NOT_STRICT_COMPRESSION"


def from_structure(ast: dict, vectors: tuple[Bottleneck, ...], *, origin: str,
                   model_identity: str, context: tuple[tuple[str, str], ...] = ()) -> StructuredMemory:
    """Retain ordered syntax/roles plus explicit node vectors and input context.

Only the versioned Q4 codec subset is admitted. The exact model identity is an
audit label, not a learned feature. Context must be input context, not a target
or result trace; a caller still owns that visibility decision.
"""
    if origin not in ("INPUT_STRUCTURE", "MODEL_PREDICTION"):
        raise Q4InputError("INVALID_INPUT: memory origin must be input or prediction")
    if type(model_identity) is not str or not 1 <= len(model_identity) <= 128:
        raise Q4InputError("INVALID_INPUT: bounded model identity required")
    if (type(context) is not tuple or len(context) > 16
            or any(type(pair) is not tuple or len(pair) != 2
                   or any(type(value) is not str or len(value) > 256 for value in pair) for pair in context)
            or len({pair[0] for pair in context}) != len(context)):
        raise Q4InputError("INVALID_INPUT: bounded unique context pairs required")
    if (type(vectors) is not tuple or not vectors or len(vectors) > DecodeLimits().max_nodes
            or any(type(vector) is not Bottleneck for vector in vectors)
            or len({len(vector.values) for vector in vectors}) != 1):
        raise Q4InputError("INVALID_INPUT: same-width finite vectors, one per node required")
    # Make a validated independent copy; never retain the caller's mutable AST.
    tree = tokens_to_ast(ast_to_tokens(ast))
    rows = []

    def visit(node, parent, role):
        position = len(rows)
        rows.append(None)
        if position >= len(vectors):
            raise Q4InputError("INVALID_INPUT: fewer vectors than nodes")
        children = ()
        if node["node"] == "BinaryExpr":
            children = (visit(node["left"], position, "left"), visit(node["right"], position, "right"))
        attributes = tuple(sorted((key, value) for key, value in node.items()
                                  if key not in ("node", "left", "right")))
        rows[position] = MemoryNode(position, parent, role, node["node"], attributes, children, vectors[position])
        return position

    visit(tree, None, "root")
    if len(rows) != len(vectors):
        raise Q4InputError("INVALID_INPUT: more vectors than nodes")
    return StructuredMemory(tuple(rows), origin, model_identity, context)


def replace_vector(memory: StructuredMemory, position: int, vector: Bottleneck) -> StructuredMemory:
    """Controlled intervention hook, with NO answer/reference correction logic.

The caller chooses the intervention before scoring. This only replaces the
named node vector; structure, context, identity, and all other nodes stay fixed.
"""
    if (type(memory) is not StructuredMemory or type(position) is not int
            or not 0 <= position < len(memory.nodes) or type(vector) is not Bottleneck
            or len(vector.values) != len(memory.nodes[position].vector.values)):
        raise Q4InputError("INVALID_INPUT: valid same-width node intervention required")
    nodes = list(memory.nodes)
    nodes[position] = replace(nodes[position], vector=vector)
    return replace(memory, nodes=tuple(nodes))
