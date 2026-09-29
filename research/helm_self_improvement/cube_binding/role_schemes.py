"""CAS-HH-RDE-01-CB1 / A -- bounded role grammar over PUBLIC cube structure (source-only, NOT RUN).

WHAT THIS MODULE IS. The first of Claude's three CB1-A files. It turns a public graph (the cube's branch
records: `source_node_id --predicate--> target_node_id`, schema `cas.cube-node/0.1` section 4) or a small
event frame (the doctor/teacher fixture of the manager directive section 3) into a canonical multiset of
BINDINGS: (filler, role path, occurrence). Everything a binding is derived from is public structure. No
evaluator answer, solved path, correctness label or split/audit identifier is accepted as input: the field
names of the historical cube validator's forbidden list are refused here too.

WHY THE ROLE PATHS ARE BOUNDED. A role path is a tuple of vocabulary words from a finite grammar declared
by the scheme (predicate word, direction word, depth). It is never a per-example identifier: two graphs with
the same shape produce the same role vocabulary, so a fitted reconstructor cannot memorise examples through
their roles. Occurrence keys (the concrete node path that produced a binding) are carried separately and
are NOT part of the role; they keep multiplicity honest (the same filler reached by two paths is two
bindings) without entering the fitted features.

THE FOUR SCHEMES (manager directive section 7.2, "identity-only / atomic pair / relation-argument roles"):
  IDENTITY_ONLY      graph scope; every node once with role ("present",). The bag-of-fillers baseline.
  ENDPOINT_BAG       graph scope; each edge contributes (source, ("<p>","source")) and (target, ("<p>","target")).
                     Roles but no pairing. This is the section 3.1 counterexample scheme: it CANNOT
                     distinguish  A>B, C>D  from  A>D, C>B. Kept as a named control, never as a hypothesis.
  RELATION_ENDPOINT  receiving-row scope; for the row of node i: (i, ("self",)), then every node reachable
                     from i by following the predicate forward up to `max_path_length` hops as
                     (j, ("<p>", "out", depth)) and backward as (j, ("<p>", "in", depth)). Pairing is
                     preserved because one endpoint of every binding is the receiving row itself. This is
                     the first CB1 hypothesis scheme for row-wise sites such as `graph.round_update`.
  EVENT_FRAME        event scope; a declared predicate profile names its argument roles (e.g. help ->
                     helper, recipient); each participant is (filler, ("<p>", "<role>")). Surface form
                     (active/passive, which word is the syntactic subject) is NOT an input to the binding.
ATOMIC_PAIR is not a scheme here: it is a reconstructor kind (`reconstructor.py`) that uses the
RELATION_ENDPOINT paths but looks each (filler, role) pair up as one unanalysable symbol.

WHAT IT PROVES. Only that the symbolic fixtures distinguish or collapse the structures they should
(CB03, CB04, CB05, CB07 data-only rows). Nothing about HELM. Authority OBSERVATION_ONLY_NO_PROMOTION.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..diagnostic_configuration import AUTHORITY, canonical, digest

SCHEME_SCHEMA = "helm.cube-binding.role-scheme/0.1"
BINDING_SET_SCHEMA = "helm.cube-binding.binding-set/0.1"
SCHEME_KINDS = ("IDENTITY_ONLY", "ENDPOINT_BAG", "RELATION_ENDPOINT", "EVENT_FRAME")
SCOPES = {"IDENTITY_ONLY": "GRAPH", "ENDPOINT_BAG": "GRAPH", "RELATION_ENDPOINT": "RECEIVING_ROW",
          "EVENT_FRAME": "EVENT"}
# Copied from `cube_node.FORBIDDEN_FIELD_NAMES` / `FORBIDDEN_PREDICATES` at scientific ref c45f775f
# (cube_node.py sha256 9d3363a9...), relationship SEMANTIC_CORRESPONDENCE: that module is not importable here.
FORBIDDEN_FIELDS = ("correct", "correct_index", "answer", "solution", "expected", "target", "gold",
                    "on_correct_path", "successful_path", "split", "family_id", "audit_id", "receipt_sha256")
FORBIDDEN_PREDICATES = ("answer", "correct", "solution", "expected")
DEFAULT_PREDICATES = ("contains",)      # the only predicate with an existing cube profile; direction whole -> part
MAX_PATH_LENGTH_LIMIT = 4
MAX_NODES = 256
MAX_EDGES = 1024
BRANCH_FIELDS = ("source_node_id", "predicate", "target_node_id")


class RoleSchemeRefused(ValueError):
    def __init__(self, code, detail=""):
        super().__init__(code if not detail else "%s: %s" % (code, detail))
        self.code = code


def _refuse(code, detail=""):
    raise RoleSchemeRefused(code, detail)


def _identifier(value, code):
    if type(value) is not str or not value or value.strip() != value:
        _refuse(code, repr(value))
    return value


@dataclass(frozen=True)
class Scheme:
    schema: str
    kind: str
    scope: str
    predicates: tuple            # graph schemes: predicate names; EVENT_FRAME: (predicate, roles...) tuples
    max_path_length: int
    filler_vocabulary: tuple
    role_vocabulary: tuple       # tuple of role paths (tuples of str); finite and shape-independent
    authority: str = AUTHORITY

    def role_index(self, path):
        try:
            return self.role_vocabulary.index(tuple(path))
        except ValueError:
            _refuse("ROLE_UNKNOWN", repr(path))

    def filler_index(self, filler):
        try:
            return self.filler_vocabulary.index(filler)
        except ValueError:
            _refuse("FILLER_UNKNOWN", repr(filler))


def scheme_digest(scheme):
    return digest({"schema": scheme.schema, "kind": scheme.kind, "scope": scheme.scope,
                   "predicates": [list(p) if isinstance(p, tuple) else p for p in scheme.predicates],
                   "max_path_length": scheme.max_path_length, "filler_vocabulary": list(scheme.filler_vocabulary),
                   "role_vocabulary": [list(r) for r in scheme.role_vocabulary]})


def _role_vocabulary(kind, predicates, max_path_length):
    if kind == "IDENTITY_ONLY":
        return (("present",),)
    if kind == "ENDPOINT_BAG":
        return tuple((p, end) for p in predicates for end in ("source", "target"))
    if kind == "RELATION_ENDPOINT":
        roles = [("self",)]
        for p in predicates:
            for direction in ("out", "in"):
                for depth in range(1, max_path_length + 1):
                    roles.append((p, direction, str(depth)))
        return tuple(roles)
    # EVENT_FRAME: predicates are (predicate, role, role, ...) profiles
    return tuple((profile[0], role) for profile in predicates for role in profile[1:])


def declare_scheme(kind, *, filler_vocabulary, predicates=DEFAULT_PREDICATES, max_path_length=2):
    """A finite, shape-independent grammar. The vocabulary is fixed at declaration; unknowns refuse later."""
    if kind not in SCHEME_KINDS:
        _refuse("SCHEME_KIND", repr(kind))
    fillers = tuple(filler_vocabulary)
    if not fillers or len(set(fillers)) != len(fillers) or len(fillers) > MAX_NODES:
        _refuse("FILLER_VOCABULARY", "non-empty, distinct, at most %d" % MAX_NODES)
    for f in fillers:
        _identifier(f, "FILLER_VOCABULARY")
    if type(max_path_length) is not int or not 1 <= max_path_length <= MAX_PATH_LENGTH_LIMIT:
        _refuse("MAX_PATH_LENGTH", "1..%d, got %r" % (MAX_PATH_LENGTH_LIMIT, max_path_length))
    if kind == "EVENT_FRAME":
        profiles = []
        for profile in predicates:
            profile = tuple(profile)
            if len(profile) < 2 or len(set(profile[1:])) != len(profile[1:]):
                _refuse("PREDICATE_PROFILE", "(predicate, role, role, ...) with distinct roles required")
            for word in profile:
                _identifier(word, "PREDICATE_PROFILE")
            if profile[0] in FORBIDDEN_PREDICATES or any(r in FORBIDDEN_FIELDS for r in profile[1:]):
                _refuse("PREDICATE_FORBIDDEN", repr(profile))
            profiles.append(profile)
        if not profiles:
            _refuse("PREDICATE_PROFILE", "empty")
        preds = tuple(profiles)
    else:
        preds = tuple(_identifier(p, "PREDICATE") for p in predicates)
        if not preds or len(set(preds)) != len(preds):
            _refuse("PREDICATE", "non-empty distinct predicate names required")
        if any(p in FORBIDDEN_PREDICATES for p in preds):
            _refuse("PREDICATE_FORBIDDEN", repr(preds))
    return Scheme(SCHEME_SCHEMA, kind, SCOPES[kind], preds, max_path_length, fillers,
                  _role_vocabulary(kind, preds, max_path_length))


@dataclass(frozen=True)
class Binding:
    filler: str
    role_path: tuple      # in the scheme's role vocabulary
    occurrence: tuple     # concrete structural path (node ids / event id); NOT a fitted feature


@dataclass(frozen=True)
class BindingSet:
    schema: str
    scheme_digest: str
    scope: str
    receiving: object     # receiving node id (RECEIVING_ROW), event id (EVENT), or None (GRAPH)
    bindings: tuple       # canonical order
    truncated: int        # paths cut by max_path_length or node/edge limits; never reported as "absent"

    def records(self):
        return tuple((b.filler, b.role_path) for b in self.bindings)   # what the reconstructor consumes

    def multiplicity(self, filler, role_path):
        return sum(1 for b in self.bindings if b.filler == filler and b.role_path == tuple(role_path))


def binding_set_digest(binding_set):
    return digest({"schema": binding_set.schema, "scheme_digest": binding_set.scheme_digest,
                   "scope": binding_set.scope, "receiving": binding_set.receiving,
                   "bindings": [[b.filler, list(b.role_path), list(b.occurrence)] for b in binding_set.bindings],
                   "truncated": binding_set.truncated})


def _finish(scheme, receiving, bindings, truncated):
    ordered = tuple(sorted(bindings, key=lambda b: (b.role_path, b.filler, b.occurrence)))
    return BindingSet(BINDING_SET_SCHEMA, scheme_digest(scheme), scheme.scope, receiving, ordered, truncated)


# ---------------------------------------------------------------------------------------------------------
# Public graph input (cube branch records) -> bindings
# ---------------------------------------------------------------------------------------------------------

def public_graph(scheme, branches, *, nodes=None):
    """Validate branch records; refuse answer-bearing fields, unknown predicates or fillers, dangling refs."""
    if scheme.kind == "EVENT_FRAME":
        _refuse("SCHEME_SCOPE", "EVENT_FRAME takes event frames, not a graph")
    branches = tuple(branches)
    if len(branches) > MAX_EDGES:
        _refuse("EDGE_LIMIT", "%d > %d" % (len(branches), MAX_EDGES))
    node_ids = list(nodes) if nodes is not None else []
    for n in node_ids:
        scheme.filler_index(_identifier(n, "NODE_ID"))
    if len(set(node_ids)) != len(node_ids):
        _refuse("NODE_ID", "duplicate node ids")
    edges = []
    for branch in branches:
        if not isinstance(branch, dict):
            _refuse("BRANCH_RECORD", repr(type(branch)))
        forbidden = sorted(k for k in branch if k in FORBIDDEN_FIELDS)
        if forbidden:
            _refuse("ANSWER_BEARING_FIELD", ",".join(forbidden))
        for key in BRANCH_FIELDS:
            if key not in branch:
                _refuse("BRANCH_RECORD", "missing %s" % key)
        source, predicate, target = (_identifier(branch[k], "BRANCH_RECORD") for k in BRANCH_FIELDS)
        if predicate not in scheme.predicates:
            _refuse("PREDICATE_UNSUPPORTED", predicate)
        scheme.filler_index(source)
        scheme.filler_index(target)
        if source == target:
            _refuse("SELF_EDGE", source)
        for n in (source, target):
            if n not in node_ids:
                if nodes is not None:
                    _refuse("DANGLING_REFERENCE", n)
                node_ids.append(n)
        edges.append((source, predicate, target))
    if len(set(edges)) != len(edges):
        _refuse("DUPLICATE_EDGE", "the same directed edge twice is one fact, not two occurrences")
    if len(node_ids) > MAX_NODES:
        _refuse("NODE_LIMIT", "%d > %d" % (len(node_ids), MAX_NODES))
    return {"nodes": tuple(node_ids), "edges": tuple(edges)}


def graph_bindings(scheme, graph, *, receiving=None):
    """Bindings under the scheme. RELATION_ENDPOINT needs `receiving` (the row's node); graph schemes refuse it."""
    nodes, edges = graph["nodes"], graph["edges"]
    if scheme.kind == "IDENTITY_ONLY":
        if receiving is not None:
            _refuse("SCHEME_SCOPE", "IDENTITY_ONLY has graph scope")
        return _finish(scheme, None, [Binding(n, ("present",), (n,)) for n in nodes], 0)
    if scheme.kind == "ENDPOINT_BAG":
        if receiving is not None:
            _refuse("SCHEME_SCOPE", "ENDPOINT_BAG has graph scope")
        out = []
        for source, p, target in edges:
            out.append(Binding(source, (p, "source"), (source, p, target)))
            out.append(Binding(target, (p, "target"), (source, p, target)))
        return _finish(scheme, None, out, 0)
    if scheme.kind != "RELATION_ENDPOINT":
        _refuse("SCHEME_SCOPE", scheme.kind)
    if receiving is None or receiving not in nodes:
        _refuse("RECEIVING_NODE", repr(receiving))
    out = [Binding(receiving, ("self",), (receiving,))]
    truncated = 0
    for p in scheme.predicates:
        forward = {}
        backward = {}
        for s, q, t in edges:
            if q == p:
                forward.setdefault(s, []).append(t)
                backward.setdefault(t, []).append(s)
        for direction, adjacency in (("out", forward), ("in", backward)):
            frontier = [(receiving,)]
            for depth in range(1, scheme.max_path_length + 1):
                next_frontier = []
                for path in frontier:
                    for nxt in adjacency.get(path[-1], ()):
                        if nxt in path:        # a cycle would loop; `contains` forbids them, other predicates need a policy
                            _refuse("CYCLE", "->".join(path + (nxt,)))
                        new_path = path + (nxt,)
                        out.append(Binding(nxt, (p, direction, str(depth)), new_path))
                        next_frontier.append(new_path)
                frontier = next_frontier
            # anything one hop beyond the bound is truncated, counted, never reported absent
            for path in frontier:
                truncated += len(adjacency.get(path[-1], ()))
    return _finish(scheme, receiving, out, truncated)


def row_binding_sets(scheme, graph):
    """One binding set per node row, in the graph's node order (the row order a row-wise site would use)."""
    return tuple(graph_bindings(scheme, graph, receiving=n) for n in graph["nodes"])


# ---------------------------------------------------------------------------------------------------------
# Event frames (semantic fixture; data-only)
# ---------------------------------------------------------------------------------------------------------

def event_bindings(scheme, *, event_id, predicate, participants, surface=None):
    """participants: iterable of (occurrence_id, filler, role). `surface` (e.g. active/passive, syntactic
    subject) is accepted only to be recorded as ignored: it is never part of a binding."""
    if scheme.kind != "EVENT_FRAME":
        _refuse("SCHEME_SCOPE", "event frames need an EVENT_FRAME scheme")
    _identifier(event_id, "EVENT_ID")
    profile = next((pr for pr in scheme.predicates if pr[0] == predicate), None)
    if profile is None:
        _refuse("PREDICATE_UNSUPPORTED", repr(predicate))
    roles = profile[1:]
    out, seen_occ, seen_roles = [], set(), set()
    for occurrence_id, filler, role in participants:
        _identifier(occurrence_id, "OCCURRENCE_ID")
        scheme.filler_index(filler)
        if role not in roles:
            _refuse("ROLE_UNKNOWN", "%s not in %r" % (role, roles))
        if occurrence_id in seen_occ:
            _refuse("OCCURRENCE_ID", "duplicate %s" % occurrence_id)
        if role in seen_roles:
            _refuse("ROLE_CARDINALITY", "%s filled twice in one event" % role)
        seen_occ.add(occurrence_id)
        seen_roles.add(role)
        out.append(Binding(filler, (predicate, role), (event_id, occurrence_id)))
    if seen_roles != set(roles):
        _refuse("ROLE_CARDINALITY", "event %s misses %r" % (event_id, sorted(set(roles) - seen_roles)))
    if surface is not None and not isinstance(surface, dict):
        _refuse("SURFACE", "surface annotations are a dict, and they are ignored by design")
    return _finish(scheme, event_id, out, 0)


def scene_bindings(scheme, frames):
    """Several events in one scene: the union keeps event identity in every occurrence key."""
    if scheme.kind != "EVENT_FRAME":
        _refuse("SCHEME_SCOPE", "scenes are made of event frames")
    ids = [f.receiving for f in frames]
    if len(set(ids)) != len(ids):
        _refuse("EVENT_ID", "duplicate event id in scene")
    bindings = [b for f in frames for b in f.bindings]
    return _finish(scheme, tuple(ids), bindings, sum(f.truncated for f in frames))


# ---------------------------------------------------------------------------------------------------------
# Comparison and serialization
# ---------------------------------------------------------------------------------------------------------

def same_records(a, b):
    """True when two binding sets present the SAME fitted input (fillers x roles, with multiplicity)."""
    return sorted(a.records()) == sorted(b.records())


def distinguishes(scheme, sets_a, sets_b):
    """Do the per-row / per-scope binding records differ anywhere? Used by the CB03/CB05 fixtures."""
    sets_a, sets_b = tuple(sets_a), tuple(sets_b)
    if len(sets_a) != len(sets_b):
        return True
    return any(not same_records(x, y) for x, y in zip(sets_a, sets_b))


def scheme_to_json(scheme):
    return canonical({"schema": scheme.schema, "kind": scheme.kind, "scope": scheme.scope,
                      "predicates": [list(p) if isinstance(p, tuple) else p for p in scheme.predicates],
                      "max_path_length": scheme.max_path_length, "filler_vocabulary": list(scheme.filler_vocabulary),
                      "role_vocabulary": [list(r) for r in scheme.role_vocabulary],
                      "scheme_digest": scheme_digest(scheme), "authority": scheme.authority})


def scheme_from_json(text, *, retained_scheme_digest):
    """Reload requires the externally retained digest; a self-declared digest inside the text is not trusted."""
    import json
    body = json.loads(text)
    if body.get("schema") != SCHEME_SCHEMA:
        _refuse("SCHEME_SCHEMA", repr(body.get("schema")))
    kind = body.get("kind")
    preds = body.get("predicates") or ()
    preds = tuple(tuple(p) for p in preds) if kind == "EVENT_FRAME" else tuple(preds)
    scheme = declare_scheme(kind, filler_vocabulary=tuple(body.get("filler_vocabulary") or ()),
                            predicates=preds, max_path_length=body.get("max_path_length"))
    if scheme_digest(scheme) != retained_scheme_digest:
        _refuse("SCHEME_DIGEST_MISMATCH", "reloaded scheme is not the retained one")
    if tuple(tuple(r) for r in body.get("role_vocabulary") or ()) != scheme.role_vocabulary:
        _refuse("SCHEME_DIGEST_MISMATCH", "role vocabulary in text differs from the grammar's")
    return scheme
