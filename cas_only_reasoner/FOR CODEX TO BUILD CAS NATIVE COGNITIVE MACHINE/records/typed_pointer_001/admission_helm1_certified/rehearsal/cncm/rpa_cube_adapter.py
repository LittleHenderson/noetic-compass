"""Pure, source-bound cube inspection and graph-teaching preparation.

Observed means that the supplied authored bytes were loaded. It does not mean
world truth, a learner prediction, a delivered lesson, or runtime execution.
The unchanged research compiler is invoked only as a deterministic teacher.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field, replace
from hashlib import sha256
import json
import math
import re

from .canonical import canonical_json, digest
from .model import ContractError
from .rpa_model import (AtlasContext, AtlasLink, AtlasNode, AtlasSnapshot,
                        LinkType, NodeKind, NodeStatus, identifier, require)
from research.CAS_META_2_COMPOSITION.cas_meta2.graph_teaching import cube_node, cube_profile

DOCUMENT_SCHEMA = "cncm.rpa-cube-document/0.1"
SOURCE_SCHEMA = "cncm.rpa-cube-source/0.1"
LESSON_SCHEMA = "cncm.rpa-cube-lesson/0.1"
ENCODING_SCHEMA = "cncm.rpa-cube-public-input/0.1"
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_CATALOG_BYTES = 12 * 1024 * 1024
MAX_DOCUMENT_BYTES = 24 * 1024 * 1024
MAX_LESSON_BYTES = 2 * 1024 * 1024
MAX_CUBES = 64
MAX_PAGE = 20
SCOPE = "LOADED_AUTHORED_SNAPSHOT_NOT_WORLD_TRUTH_OR_RUNTIME_STATE"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_BUNDLE_KEYS = {"schema_version", "status", "usage", "context", "lesson_family_id",
                "sources", "cube_nodes", "branches", "views", "mappings",
                "learner_view_requirement"}


def _sha(value, label):
    require(type(value) is str and _SHA.fullmatch(value) is not None, label + " invalid")


def _bounded(value, maximum, label):
    """Bound JSON structure before recursion/serialization, including cycles."""
    stack = [(value, 0, frozenset())]
    count = characters = 0
    while stack:
        item, depth, ancestors = stack.pop()
        count += 1
        require(count <= 200_000 and depth <= 32, label + " structure bound exceeded")
        if type(item) in (list, dict):
            require(id(item) not in ancestors, label + " cycle")
            require(len(item) <= 100_000, label + " collection bound exceeded")
            lineage = ancestors | {id(item)}
            if type(item) is dict:
                require(all(type(key) is str for key in item), label + " key type")
                entries = list(item.keys()) + list(item.values())
            else:
                entries = item
            stack.extend((child, depth + 1, lineage) for child in entries)
        elif type(item) is str:
            characters += len(item)
            require(characters <= maximum, label + " text bound exceeded")
        elif type(item) is int:
            require(item.bit_length() <= 128, label + " integer bound exceeded")
        elif type(item) is float:
            require(math.isfinite(item), label + " nonfinite number")
        else:
            require(item is None or type(item) is bool, label + " non-JSON value")
    encoded = canonical_json(value)
    require(len(encoded.encode("utf-8")) <= maximum, label + " byte bound exceeded")
    return encoded


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "source duplicate JSON key")
        result[key] = value
    return result


def _source_decode(source_bytes):
    require(type(source_bytes) is bytes and 0 < len(source_bytes) <= MAX_SOURCE_BYTES,
            "source byte bound/type invalid")
    try:
        value = json.loads(source_bytes.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=lambda value: (_ for _ in ()).throw(
                               ContractError("source nonfinite number")))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ContractError("source JSON invalid: " + str(exc)[:200]) from exc
    _validate_bundle(value)
    return value


def _validate_bundle(bundle):
    _bounded(bundle, MAX_SOURCE_BYTES, "cube bundle")
    require(type(bundle) is dict and _BUNDLE_KEYS <= set(bundle)
            and set(bundle) <= _BUNDLE_KEYS | {"relation_profiles"}, "cube bundle fields invalid")
    # The legacy validator scans only nodes/branches. This new public identity
    # also binds context/views/provenance, so reject private target metadata in
    # every part of the source, including additions to otherwise valid records.
    prohibited = set(cube_node.FORBIDDEN_FIELD_NAMES) | {
        "target", "targets", "private_target", "teacher_target", "derived_answer",
        "encoded_correct_index", "answer_refs", "expected", "correct_answer"}
    pending = [bundle]
    while pending:
        item = pending.pop()
        if type(item) is dict:
            require(not any(key.lower() in prohibited for key in item),
                    "private target field prohibited anywhere in public source")
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
    for key, cap in (("cube_nodes", MAX_CUBES), ("branches", 1024), ("views", 16),
                     ("mappings", 64), ("sources", 128)):
        require(type(bundle[key]) is list and 0 < len(bundle[key]) <= cap,
                key + " count bound/type invalid")
    # containment_graph currently rewrites every predicate to contains. Refuse
    # broader profiles before calling any of that compiler's graph helpers.
    profiles = bundle.get("relation_profiles", {"stored_predicates": ["contains"]})
    require(type(profiles) is dict and set(profiles) == {"stored_predicates"}
            and profiles["stored_predicates"] == ["contains"],
            "only the declared contains profile is supported")
    require(all(type(row) is dict and row.get("predicate") == "contains"
                for row in bundle["branches"]), "unsupported branch predicate")
    try:
        cube_node.validate_bundle(bundle)
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError) as exc:
        raise ContractError("cube validation failed: " + str(exc)[:300]) from exc
    # The source validator does not check these crosslinks. Preserve and check
    # them here instead of leaving dangling face/view/mapping references.
    views = {row["view_id"] for row in bundle["views"]}
    mappings = {row["mapping_id"] for row in bundle["mappings"]}
    branch_ids = {row["branch_id"] for row in bundle["branches"]}
    for view in bundle["views"]:
        refs = view["branch_refs"]
        # The frozen graph helper and prompt use every source branch, ignoring
        # view.branch_refs. The first bridge supports complete presentations
        # only; accepting a partial view would silently widen that input.
        require(len(refs) == len(set(refs)) and set(refs) == branch_ids,
                "unsupported partial or duplicate branch view; complete view coverage required")
    for node in bundle["cube_nodes"]:
        face5 = node["faces"]["face_5"]
        if face5["availability"] == "populated":
            refs = face5["structured"]["direct_branch_refs"]
            own = {row["branch_id"] for row in bundle["branches"]
                   if row["source_node_id"] == node["node_id"]}
            require(type(refs) is list and all(type(ref) is str for ref in refs)
                    and len(refs) == len(set(refs)) and set(refs) <= own,
                    "face direct inventory must be a unique subset of its own outgoing branches")
        for face in node["faces"].values():
            structured = face["structured"]
            for key, allowed in (("view_refs", views), ("mapping_refs", mappings)):
                if key in structured:
                    refs = structured[key]
                    require(type(refs) is list and all(type(ref) is str for ref in refs)
                            and len(refs) == len(set(refs))
                            and all(ref in allowed for ref in refs), "face crosslink unresolved: " + key)
    return bundle


@dataclass(frozen=True, slots=True)
class CubeSourceReceipt:
    """Identity receipt with original bytes retained privately for revalidation.

    This is host-supplied observation metadata, not an authenticated principal.
    Neither constructing nor deserializing this receipt authenticates authorship.
    """
    source_namespace: str
    source_file_sha256: str
    canonical_bundle_digest: str
    observation_id: str
    observation_time: str
    record_version: int
    source_bytes: bytes = field(repr=False)

    def __post_init__(self):
        identifier(self.source_namespace, "source namespace")
        _sha(self.source_file_sha256, "source file SHA-256")
        _sha(self.canonical_bundle_digest, "canonical bundle digest")
        AtlasContext("source", "authored-cube/0.1", self.observation_id,
                     self.observation_time, self.record_version)
        bundle = _source_decode(self.source_bytes)
        require(sha256(self.source_bytes).hexdigest() == self.source_file_sha256,
                "source file SHA-256 mismatch")
        require(cube_node.bundle_digest(bundle) == self.canonical_bundle_digest,
                "canonical bundle digest mismatch")

    def to_dict(self):
        return {"schema_version": SOURCE_SCHEMA, "source_namespace": self.source_namespace,
                "source_file_sha256": self.source_file_sha256,
                "source_bytes": len(self.source_bytes),
                "canonical_bundle_digest": self.canonical_bundle_digest,
                "bundle_schema": cube_node.CUBE_BUNDLE_SCHEMA,
                "observation_id": self.observation_id, "observation_time": self.observation_time,
                "record_version": self.record_version, "scope": SCOPE,
                "authorship_authenticated": False, "world_truth_established": False}


def cube_source_receipt(source_bytes, *, expected_file_sha256, expected_bundle_digest,
                        source_namespace, observation_id, observation_time, record_version):
    return CubeSourceReceipt(source_namespace, expected_file_sha256, expected_bundle_digest,
                             observation_id, observation_time, record_version, source_bytes)


def canonical_cube_id(source_namespace, context_id, cube_node_id):
    identifier(source_namespace, "source namespace")
    require(all(type(value) is str and 0 < len(value) <= 512
                for value in (context_id, cube_node_id)), "cube identity fields invalid")
    return "cube-" + digest([source_namespace, context_id, cube_node_id])


def _bound_source(bundle, expected_bundle_digest, source_receipt):
    require(type(source_receipt) is CubeSourceReceipt, "verified typed source receipt required")
    _sha(expected_bundle_digest, "expected bundle digest")
    source_receipt.__post_init__()
    _validate_bundle(bundle)
    require(cube_node.bundle_digest(bundle) == expected_bundle_digest
            == source_receipt.canonical_bundle_digest, "source/bundle digest mismatch")
    return deepcopy(bundle)


def _projection(bundle, receipt, view_id, *, hypothetical=False):
    labels = cube_node.view_labels(bundle, view_id)
    scope_key = digest([receipt.to_dict(), view_id, hypothetical])
    context = AtlasContext("context-" + digest([receipt.source_namespace, bundle["context"]["context_id"]]),
                           "authored-cube/0.1:" + receipt.canonical_bundle_digest,
                           receipt.observation_id, receipt.observation_time, receipt.record_version)
    status = NodeStatus.HYPOTHETICAL if hypothetical else NodeStatus.OBSERVED
    state_id = "loaded-" + scope_key
    evidence = "source-" + digest(receipt.to_dict())
    nodes = [AtlasNode(state_id, "snapshot-" + receipt.canonical_bundle_digest,
                       "Hypothetical authored snapshot" if hypothetical else "Loaded authored snapshot",
                       context, status, kind=NodeKind.STATE,
                       fields=tuple(sorted({"scope": SCOPE, "view_id": view_id,
                           "source_bundle_digest": receipt.canonical_bundle_digest,
                           "source_status": bundle["status"],
                           "world_assumption": bundle["context"].get("world_assumption", "unspecified"),
                           "contains_inventory_complete": str(bundle["context"]["contains_inventory_complete"]).lower()
                       }.items())), evidence_refs=(evidence,))]
    links, index, lookup = [], {}, {}
    for position, cube in enumerate(bundle["cube_nodes"]):
        idea = canonical_cube_id(receipt.source_namespace, cube["context_id"], cube["node_id"])
        node_id = "view-" + digest([scope_key, idea, cube["revision"]])
        key = "catalog-" + digest([receipt.source_namespace, cube["context_id"],
                                  cube["node_id"], cube["revision"]])
        lookup[cube["node_id"]] = node_id
        index[key] = {"source_namespace": receipt.source_namespace, "context_id": cube["context_id"],
                      "cube_node_id": cube["node_id"], "revision": cube["revision"],
                      "idea_id": idea, "atlas_node_id": node_id,
                      "source_path": ["cube_nodes", position], "record_digest": digest(cube)}
        nodes.append(AtlasNode(node_id, idea, labels[cube["node_id"]], context, status,
                               fields=(("catalog_key", key), ("source_node_id", cube["node_id"])),
                               evidence_refs=(evidence,)))
        links.append(AtlasLink("entry-" + digest([scope_key, key]), state_id, node_id,
                               LinkType.CONTAINS_PART, projection="authored_snapshot.cube_record:" + key,
                               evidence_refs=(evidence,)))
        for face_key in cube_node.FACE_KEYS:
            face = cube["faces"][face_key]
            face_id = "face-" + digest([scope_key, key, face_key])
            face_status = (NodeStatus.UNKNOWN if face["availability"] == "unknown" else status)
            if hypothetical:
                face_status = NodeStatus.HYPOTHETICAL
            nodes.append(AtlasNode(face_id, "face-idea-" + digest([idea, face_key]),
                                   labels[cube["node_id"]] + " / " + face_key,
                                   context, face_status, kind=NodeKind.EVIDENCE,
                                   fields=(("availability", face["availability"]), ("catalog_key", key),
                                           ("face_path", "faces." + face_key),
                                           ("role", cube_node.FACE_ROLES[face_key])),
                                   evidence_refs=(evidence,)))
            links.append(AtlasLink("face-link-" + digest([scope_key, key, face_key]), node_id, face_id,
                                   LinkType.CONTAINS_PART, projection="cube_record.faces." + face_key,
                                   evidence_refs=(evidence,)))
    for branch in bundle["branches"]:
        links.append(AtlasLink("branch-" + digest([scope_key, branch["branch_id"]]),
                               lookup[branch["source_node_id"]], lookup[branch["target_node_id"]],
                               LinkType.CONTAINS_PART, projection="source_contains_branch:" + branch["branch_id"],
                               evidence_refs=(evidence,)))
    catalog = {"bundle": bundle, "cube_index": index}
    _bounded(catalog, MAX_CATALOG_BYTES, "cube catalog")
    return nodes, links, state_id, catalog


@dataclass(frozen=True, slots=True)
class CubeAtlasDocument:
    """Immutable storage; all dictionary exports are fresh deep copies.

    Consumers receiving wire JSON must use load_cube_atlas_document with external
    receipts. This private backing string is not a substitute for source checks.
    """
    _wire_json: str = field(repr=False)
    _receipts: tuple[CubeSourceReceipt, ...] = field(repr=False)

    def to_dict(self):
        require(type(self._wire_json) is str and len(self._wire_json) <= MAX_DOCUMENT_BYTES,
                "cube document backing byte/text bound invalid")
        try:
            return json.loads(self._wire_json, object_pairs_hook=_unique_object)
        except (ValueError, RecursionError) as exc:
            raise ContractError("cube document backing JSON invalid") from exc

    @property
    def atlas(self):
        return AtlasSnapshot.from_dict(self.to_dict()["atlas"])

    @property
    def catalog(self):
        return self.to_dict()["catalog"]

    @property
    def document_digest(self):
        return digest(self.to_dict())

    def focus(self, node_id):
        wire = self.to_dict()
        wire["atlas"] = self.atlas.focus(node_id).to_dict()
        return CubeAtlasDocument(_bounded(wire, MAX_DOCUMENT_BYTES, "cube document"), self._receipts)

    def with_hypothesis(self, hypothesis):
        """Attach one separately source-bound hypothetical graph; never commit it."""
        _revalidate_document(self)
        _revalidate_document(hypothesis)
        wire, proposed = self.to_dict(), hypothesis.to_dict()
        require(not wire["hypotheses"] and not proposed["hypotheses"], "only one finite hypothesis supported")
        receipt = hypothesis._receipts[0]
        nodes, links, root, catalog = _projection(proposed["catalog"]["bundle"], receipt,
                                                  proposed["view_id"], hypothetical=True)
        base = self.atlas
        merged = AtlasSnapshot(base.nodes + tuple(nodes), base.links + tuple(links),
                               base.current_state_id, root, root)
        wire["atlas"] = merged.to_dict()
        wire["hypotheses"] = [{"source_receipt": receipt.to_dict(), "view_id": proposed["view_id"],
                               "catalog": catalog, "base_current_state_id": base.current_state_id,
                               "hypothesis_state_id": root}]
        return CubeAtlasDocument(_bounded(wire, MAX_DOCUMENT_BYTES, "cube document"), self._receipts + (receipt,))


def cube_atlas_from_bundle(bundle, *, expected_bundle_digest, source_receipt, view_id="view_context"):
    bundle = _bound_source(bundle, expected_bundle_digest, source_receipt)
    nodes, links, state_id, catalog = _projection(bundle, source_receipt, view_id)
    atlas = AtlasSnapshot(tuple(nodes), tuple(links), state_id, state_id)
    wire = {"schema_version": DOCUMENT_SCHEMA, "source_receipt": source_receipt.to_dict(),
            "view_id": view_id, "catalog": catalog, "atlas": atlas.to_dict(), "hypotheses": [],
            "scope": SCOPE}
    return CubeAtlasDocument(_bounded(wire, MAX_DOCUMENT_BYTES, "cube document"), (source_receipt,))


def cube_atlas_from_bytes(source_bytes, *, expected_file_sha256, expected_bundle_digest,
                          source_namespace, observation_id, observation_time, record_version,
                          view_id="view_context"):
    receipt = cube_source_receipt(source_bytes, expected_file_sha256=expected_file_sha256,
                                  expected_bundle_digest=expected_bundle_digest,
                                  source_namespace=source_namespace, observation_id=observation_id,
                                  observation_time=observation_time, record_version=record_version)
    return cube_atlas_from_bundle(_source_decode(source_bytes), expected_bundle_digest=expected_bundle_digest,
                                  source_receipt=receipt, view_id=view_id)


def load_cube_atlas_document(value, *, source_receipts):
    """Wire identity is checked against external original source receipts."""
    require(type(source_receipts) is tuple and 1 <= len(source_receipts) <= 2
            and all(type(row) is CubeSourceReceipt for row in source_receipts), "source receipts invalid")
    document = CubeAtlasDocument(_bounded(value, MAX_DOCUMENT_BYTES, "cube document"), source_receipts)
    _revalidate_document(document)
    return document


def _revalidate_document(document):
    require(type(document) is CubeAtlasDocument, "typed cube document required")
    wire = document.to_dict()
    require(type(wire) is dict and set(wire) == {"schema_version", "source_receipt", "view_id",
            "catalog", "atlas", "hypotheses", "scope"}, "cube document fields invalid")
    require(type(wire["hypotheses"]) is list and len(wire["hypotheses"]) <= 1
            and len(document._receipts) == 1 + len(wire["hypotheses"]), "hypothesis source count mismatch")
    expected = cube_atlas_from_bundle(_source_decode(document._receipts[0].source_bytes),
                                      expected_bundle_digest=document._receipts[0].canonical_bundle_digest,
                                      source_receipt=document._receipts[0], view_id=wire["view_id"]).to_dict()
    if wire["hypotheses"]:
        hypothesis = wire["hypotheses"][0]
        receipt = document._receipts[1]
        receipt.__post_init__()
        nodes, links, root, catalog = _projection(_source_decode(receipt.source_bytes), receipt,
                                                  hypothesis["view_id"], hypothetical=True)
        base = AtlasSnapshot.from_dict(expected["atlas"])
        expected["atlas"] = AtlasSnapshot(base.nodes + tuple(nodes), base.links + tuple(links),
                                           base.current_state_id, root, root).to_dict()
        expected["hypotheses"] = [{"source_receipt": receipt.to_dict(), "view_id": hypothesis["view_id"],
                                  "catalog": catalog, "base_current_state_id": base.current_state_id,
                                  "hypothesis_state_id": root}]
    actual_atlas = AtlasSnapshot.from_dict(wire["atlas"])
    expected["atlas"]["focus_node_id"] = actual_atlas.focus_node_id
    expected["atlas"]["hypothesis_branch_id"] = actual_atlas.hypothesis_branch_id
    # Python equality conflates True/1 and 0.0/0. Source JSON scalar types are
    # part of their identity, so reconstruction requires exact canonical bytes.
    require(canonical_json(wire) == canonical_json(expected), "stale or corrupted source projection")


def catalog_page(document, *, offset=0, limit=20, cursor=None):
    _revalidate_document(document)
    require(type(offset) is int and offset >= 0 and type(limit) is int and 1 <= limit <= MAX_PAGE,
            "catalog page bounds invalid")
    wire = document.to_dict()
    catalog = wire["catalog"]
    anchor = digest({"source_receipt": wire["source_receipt"], "view_id": wire["view_id"], "catalog": catalog})
    if cursor is not None:
        require(type(cursor) is dict and set(cursor) == {"anchor", "next_offset", "limit", "cursor_digest"},
                "catalog cursor fields invalid")
        require(type(cursor["next_offset"]) is int and type(cursor["limit"]) is int,
                "catalog cursor integer types invalid")
        _sha(cursor["anchor"], "catalog cursor anchor")
        _sha(cursor["cursor_digest"], "catalog cursor digest")
        body = {key: value for key, value in cursor.items() if key != "cursor_digest"}
        require(digest(body) == cursor["cursor_digest"] and cursor["anchor"] == anchor
                and cursor["limit"] == limit and offset == 0, "catalog cursor mismatch")
        offset = cursor["next_offset"]
    keys = sorted(catalog["cube_index"])
    require(type(offset) is int and 0 <= offset <= len(keys), "catalog offset invalid")
    stop = min(len(keys), offset + limit)
    rows = [{"catalog_key": key, **catalog["cube_index"][key],
             "cube": deepcopy(catalog["bundle"]["cube_nodes"][catalog["cube_index"][key]["source_path"][1]])}
            for key in keys[offset:stop]]
    next_cursor = None
    if stop < len(keys):
        body = {"anchor": anchor, "next_offset": stop, "limit": limit}
        next_cursor = {**body, "cursor_digest": digest(body)}
    return {"anchor": anchor, "offset": offset, "stop": stop, "total": len(keys), "rows": rows,
            "deferred": len(keys) - stop, "next_cursor": next_cursor,
            "boundary": "Unreturned rows are deferred, not absent."}


def _witness(bundle, view_id, operation, question, answer):
    by_label = {value: key for key, value in cube_node.view_labels(bundle, view_id).items()}
    outgoing = {node["node_id"]: [] for node in bundle["cube_nodes"]}
    for branch in sorted(bundle["branches"], key=lambda row: row["branch_id"]):
        outgoing[branch["source_node_id"]].append(branch)
    canonical_question = {key: by_label[value] for key, value in question.items()}
    if operation == "LIST_PARTS":
        branches = [row["branch_id"] for row in outgoing[canonical_question["idea"]]]
        return canonical_question, branches, [branches], "complete_direct_inventory"
    if operation == "FIND_SHARED_PART":
        # Both whole inventories also justify 'none' under declared completeness.
        branches = sorted({row["branch_id"] for key in ("a", "b")
                           for row in outgoing[canonical_question[key]]})
        return canonical_question, branches, [branches], "two_complete_direct_inventories"
    root, target = canonical_question["idea"], canonical_question["part"]
    queue, seen, inspected = deque([(root, [])]), {root}, set()
    allowed_first = by_label[answer[4:]] if answer.startswith("via:") else None
    while queue:
        node, path = queue.popleft()
        for branch in outgoing[node]:
            child = branch["target_node_id"]
            inspected.add(branch["branch_id"])
            if node == root and allowed_first is not None and child != allowed_first:
                continue
            chain = path + [branch["branch_id"]]
            if child == target:
                return canonical_question, chain, [chain], "directed_contains_path"
            if child not in seen:
                seen.add(child)
                queue.append((child, chain))
    require(answer == "absent", "teacher witness path missing")
    return canonical_question, sorted(inspected), [], "complete_reachable_inventory_absence"


def compile_atlas_lesson(document, *, bundle, expected_bundle_digest, operation, question,
                         assistance, encoding_context=None):
    """Prepare prediction input and a separate teacher record; never predict.

    There is intentionally no private-target argument. The frozen compiler's
    disclosure audit needs a target, so its teacher-shaped case is derived from
    the supplied complete authored graph, then discarded at the learner boundary.
    """
    _revalidate_document(document)
    wire = document.to_dict()
    bundle = _bound_source(bundle, expected_bundle_digest, document._receipts[0])
    require(bundle == wire["catalog"]["bundle"], "lesson source differs from projection")
    shapes = {"LIST_PARTS": {"idea"}, "FIND_SHARED_PART": {"a", "b"},
              "REACHED_VIA": {"part", "idea"}}
    require(type(operation) is str and operation in shapes, "unsupported scored operation; Why is teacher-only and How needs an action contract")
    require(type(question) is dict and set(question) == shapes[operation], "public question fields invalid")
    labels = set(cube_node.view_labels(bundle, wire["view_id"]).values())
    require(all(type(value) is str and value in labels for value in question.values()), "question label unresolved")
    require(assistance in ("guided", "unassisted"), "unsupported bridge assistance level")
    require(bundle["context"]["contains_inventory_complete"] is True,
            "complete scored answer requires declared complete inventory")
    public_case = {"op": operation, "question": deepcopy(question)}
    try:
        answer = cube_profile.derived_answer(bundle, public_case, wire["view_id"])
        compiled = cube_profile.compile_public_exercise(bundle, {**public_case, "correct": answer},
                                                        assistance=assistance, view_id=wire["view_id"])
    except (ValueError, KeyError, TypeError) as exc:
        raise ContractError("teacher compilation failed: " + str(exc)[:300]) from exc
    profile = compiled["visibility"]["profile"]["profile_id"]
    context = {"schema_version": ENCODING_SCHEMA, "compiler_schema": cube_profile.LESSON_V2_SCHEMA,
               "visibility_profile_id": profile, "source_namespace": document._receipts[0].source_namespace,
               "source_context_id": bundle["context"]["context_id"], "view_id": wire["view_id"],
               "content_revision": expected_bundle_digest, "encoded_cache_identity": None}
    if encoding_context is not None:
        require(type(encoding_context) is dict and set(encoding_context) == {
            "model_checkpoint_digest", "tokenizer_digest", "encoder_digest"}, "encoding context fields invalid")
        for key, value in encoding_context.items():
            _sha(value, key)
        context["encoded_cache_identity"] = deepcopy(encoding_context)
    public = deepcopy(compiled["encoding"]["public"])
    options = deepcopy(compiled["encoding"]["encoded_options"])
    require(type(public) is dict and set(public) == {"problem", "observations"}
            and type(public["problem"]) is str and type(public["observations"]) is list
            and len(public["observations"]) == 3, "compiler public contract changed")
    for slot, observation in enumerate(public["observations"]):
        require(type(observation) is dict and set(observation) == {"slot", "tag", "values"}
                and observation["slot"] == slot and type(observation["tag"]) is str
                and type(observation["values"]) is list and len(observation["values"]) == 8
                and all(type(value) in (int, float) and math.isfinite(value)
                        for value in observation["values"]), "compiler observation contract changed")
    require(type(options) is list and len(options) == 3, "compiler ordered options changed")
    # The frozen codec slices tags at 256 characters and prompts at 8192.
    # A faithful bridge refuses a lossy result instead of handing the learner
    # identical/truncated choices or a question with missing graph facts.
    require(public["problem"] == compiled["record"]["framings"]["cas"],
            "lossy compiler public problem encoding")
    require(all(observation["tag"] == str(options[slot])
                for slot, observation in enumerate(public["observations"]))
            and len({observation["tag"] for observation in public["observations"]}) == 3,
            "lossy or ambiguous compiler option encoding")
    input_id = "cube-input-" + digest({"public": public, "encoded_options": options, "encoding_context": context})
    learner = {"record_id": input_id, "public": public, "encoded_options": options}
    canonical_question, branch_ids, paths, basis = _witness(bundle, wire["view_id"], operation, question, answer)
    semantic_id = "cube-question-" + digest({"source_namespace": document._receipts[0].source_namespace,
                    "context_id": bundle["context"]["context_id"], "operation": operation,
                    "question": canonical_question})
    teacher = {"record_id": input_id, "source_bundle_digest": expected_bundle_digest,
               "operation": operation, "question": deepcopy(question), "expected_answer": deepcopy(answer),
               "encoded_correct_index": compiled["encoding"]["encoded_correct_index"],
               "reference_branch_ids": branch_ids, "reference_paths": paths, "witness_basis": basis,
               "assistance_level": assistance, "visibility_profile_id": profile,
               "visibility": deepcopy(compiled["visibility"]),
               "answer_status": "GRAPH_DERIVED_TEACHER_REFERENCE_NOT_LEARNER_PREDICTION",
               "why_status": "STRUCTURAL_TEACHER_WITNESS_ONLY", "how_status": "UNSUPPORTED_NO_ACTION_CONTRACT",
               "scope": SCOPE}
    binding = {"schema_version": LESSON_SCHEMA, "semantic_question_id": semantic_id,
               "encoding_context": context, "public_input_digest": digest(learner),
               "teacher_sidecar_digest": digest(teacher), "source_receipt_digest": digest(wire["source_receipt"]),
               "base_current_state_id": wire["atlas"]["current_state_id"],
               "compiler_calls": 1, "neural_calls": 0, "optimizer_updates": 0,
               "delivered_neural_lessons": 0, "competence_established": False,
               "cache_identity_bound": encoding_context is not None,
               "cache_identity_scope": "Supplied identity metadata only; no cache or encoder capability was probed."}
    export = {"learner_input": learner, "teacher_sidecar": teacher, "binding": binding}
    _bounded(export, MAX_LESSON_BYTES, "lesson export")
    return export


def check_teacher_target(lesson, supplied_target):
    """Check local agreement of a supplied export, without source authority.

    Matching hashes and internally coherent fields cannot authenticate a source
    or establish a graph-derived answer. For source-grounded verification,
    recompile through compile_atlas_lesson with a source-bound document. This
    helper never changes the learner input or reconstructs that source.
    """
    _bounded(lesson, MAX_LESSON_BYTES, "lesson export")
    _bounded(supplied_target, MAX_LESSON_BYTES, "supplied target")
    require(type(lesson) is dict and set(lesson) == {"learner_input", "teacher_sidecar", "binding"},
            "lesson export fields invalid")
    learner, teacher, binding = lesson["learner_input"], lesson["teacher_sidecar"], lesson["binding"]
    require(type(learner) is dict and set(learner) == {"record_id", "public", "encoded_options"}
            and type(teacher) is dict and type(binding) is dict,
            "teacher agreement record shape invalid")
    require({"record_id", "encoded_correct_index", "expected_answer", "visibility_profile_id",
             "source_bundle_digest"} <= set(teacher)
            and {"schema_version", "encoding_context", "public_input_digest", "teacher_sidecar_digest"} <= set(binding),
            "teacher agreement fields missing")
    require(digest(learner) == binding["public_input_digest"]
            and digest(teacher) == binding["teacher_sidecar_digest"],
            "lesson export digest mismatch")
    require(type(learner["record_id"]) is str and learner["record_id"] == teacher["record_id"],
            "teacher and learner record identity mismatch")
    context = binding["encoding_context"]
    _sha(teacher["source_bundle_digest"], "teacher source bundle digest")
    require(type(teacher["visibility_profile_id"]) is str, "teacher visibility identity invalid")
    require(type(context) is dict and context.get("schema_version") == ENCODING_SCHEMA
            and binding["schema_version"] == LESSON_SCHEMA
            and context.get("visibility_profile_id") == teacher["visibility_profile_id"]
            and context.get("content_revision") == teacher["source_bundle_digest"],
            "teacher agreement encoding context mismatch")
    expected_id = "cube-input-" + digest({"public": learner["public"],
        "encoded_options": learner["encoded_options"], "encoding_context": context})
    require(learner["record_id"] == expected_id, "teacher agreement public identity mismatch")
    options, index = learner["encoded_options"], teacher["encoded_correct_index"]
    require(type(options) is list and len(options) == 3 and type(index) is int and 0 <= index < 3,
            "teacher agreement option/index invalid")
    require(len({canonical_json(option) for option in options}) == 3
            and canonical_json(options[index]) == canonical_json(teacher["expected_answer"]),
            "teacher target does not match its encoded option")
    public = learner["public"]
    require(type(public) is dict and set(public) == {"problem", "observations"}
            and type(public["problem"]) is str and type(public["observations"]) is list
            and len(public["observations"]) == 3, "teacher agreement public shape invalid")
    for slot, observation in enumerate(public["observations"]):
        require(type(observation) is dict and set(observation) == {"slot", "tag", "values"}
                and type(observation["slot"]) is int and observation["slot"] == slot
                and observation["tag"] == str(options[slot]) and type(observation["values"]) is list
                and len(observation["values"]) == 8
                and all(type(value) in (int, float) and math.isfinite(value) for value in observation["values"]),
                "teacher agreement observation/choice mismatch")
    require(canonical_json(supplied_target) == canonical_json(teacher["expected_answer"]),
            "supplied teacher target disagrees with the supplied teacher reference")
    return {"agrees": True, "record_id": learner["record_id"],
            "scope": "SUPPLIED_EXPORT_LOCAL_CONSISTENCY_ONLY", "source_reconstructed": False,
            "source_authenticity_established": False,
            "boundary": "Local target agreement only; no source authenticity, learner performance or world truth established."}
