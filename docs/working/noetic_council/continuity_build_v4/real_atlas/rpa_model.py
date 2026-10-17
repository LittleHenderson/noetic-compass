"""Bounded symbolic CAS Recursive Possibility Atlas representation.

Implements typed finite regions, declared part projections, witnessed overlap,
shared-field consistency and navigation. It is not a general sheaf, an infinite
planner, a geometric embedding, a probability model, or a mutation authority.
Status/evidence references describe supplied records; this module authenticates
neither observations nor principals. A host must bind the present to its own
verified source. Navigation never changes that supplied current-state record.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, fields, replace
from enum import Enum
from fractions import Fraction
import re

from .canonical import canonical_json, digest, to_primitive
from .model import ContractError

CONTEXT_SCHEMA = "cas.rpa.context/0.1"
NODE_SCHEMA = "cas.rpa.node/0.1"
LINK_SCHEMA = "cas.rpa.link/0.1"
OVERLAP_SCHEMA = "cas.rpa.overlap/0.1"
SNAPSHOT_SCHEMA = "cas.rpa.snapshot/0.1"
MAX_NODES = 512
MAX_LINKS = 2048
MAX_MEMBERS = 512
MAX_DEPTH = 32
MAX_ATLAS_BYTES = 8 * 1024 * 1024
MAX_FIELD_VALUE = 262144
_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}\Z")
_RATIONAL = re.compile(r"(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")


class NodeStatus(str, Enum):
    OBSERVED = "observed"
    HYPOTHETICAL = "hypothetical"
    UNKNOWN = "unknown"
    REJECTED = "rejected"
    VERIFIED = "verified"


class NodeKind(str, Enum):
    IDEA_CONTEXT = "idea_context"
    STATE = "state"
    REGION = "region"
    EVIDENCE = "evidence"


class LinkType(str, Enum):
    CONTAINS_PART = "contains_part"
    REFINES_STATE = "refines_state"
    REACHABLE_VIA = "reachable_via"
    OVERLAPS_WITH = "overlaps_with"
    REFERENCES_SAME_IDEA = "references_same_idea"


def require(condition, label):
    if not condition:
        raise ContractError(label)


def identifier(value, label):
    require(type(value) is str and _ID.fullmatch(value) is not None, label + " identifier invalid")


def text(value, label, maximum=256, *, empty=False):
    require(type(value) is str and (empty or bool(value)) and len(value) <= maximum,
            label + " text invalid")


def integer(value, label, maximum, minimum=0):
    require(type(value) is int and minimum <= value <= maximum, label + " integer invalid")


def identifiers(value, label, maximum=MAX_MEMBERS, *, canonical=True):
    require(type(value) is tuple and len(value) <= maximum, label + " tuple invalid")
    for item in value:
        identifier(item, label)
    if canonical:
        require(value == tuple(sorted(set(value))), label + " must be sorted and unique")


def decode_fields(value, kind, schema):
    required = {item.name for item in fields(kind)} | {"schema_version"}
    require(type(value) is dict and set(value) == required, kind.__name__ + " fields invalid")
    require(type(value["schema_version"]) is str and value["schema_version"] == schema,
            kind.__name__ + " version invalid")
    return {key: item for key, item in value.items() if key != "schema_version"}


def wire_list(value, label, maximum):
    require(type(value) is list and len(value) <= maximum, label + " list invalid")
    return tuple(value)


def wire_pairs(value, label, maximum):
    wire_list(value, label, maximum)
    require(all(type(row) is list and len(row) == 2 for row in value), label + " pairs invalid")
    return tuple(tuple(row) for row in value)


def schema_wire(value, schema):
    return {"schema_version": schema, **to_primitive(value)}


@dataclass(frozen=True, slots=True)
class AtlasContext:
    context_id: str
    model_version: str
    observation_id: str
    observation_time: str
    record_version: int

    def __post_init__(self):
        identifier(self.context_id, "context")
        identifier(self.observation_id, "observation")
        text(self.model_version, "model version")
        text(self.observation_time, "observation time")
        integer(self.record_version, "record version", 1_000_000)

    def to_dict(self):
        return schema_wire(self, CONTEXT_SCHEMA)

    @classmethod
    def from_dict(cls, value):
        return cls(**decode_fields(value, cls, CONTEXT_SCHEMA))


def validate_profile40(profile, basis):
    if profile is None:
        require(basis is None, "profile basis without profile")
        return
    require(type(profile) is tuple and len(profile) == 40, "profile needs exactly forty coordinates")
    text(basis, "profile basis", 1024)
    total = Fraction(0)
    for coordinate in profile:
        # Forty bounded128-bit fractions limit the sum's denominator to5120bits.
        # Decimal conversion is bounded first; no float or unbounded integer enters.
        require(type(coordinate) is str and 1 <= len(coordinate) <= 79
                and _RATIONAL.fullmatch(coordinate) is not None, "profile rational syntax invalid")
        parts = coordinate.split("/")
        require(all(len(part) <= 39 for part in parts), "profile integer text bound exceeded")
        numerator, denominator = int(parts[0]), int(parts[1]) if len(parts) == 2 else 1
        require(numerator.bit_length() <= 128 and denominator.bit_length() <= 128,
                "profile integer bit bound exceeded")
        fraction = Fraction(numerator, denominator)
        require(str(fraction) == coordinate and fraction > 0,
                "profile coordinates must be canonical and strictly positive")
        total += fraction
    require(total == 1, "profile coordinates must sum exactly to one")


@dataclass(frozen=True, slots=True)
class AtlasNode:
    node_id: str
    idea_id: str
    label: str
    context: AtlasContext
    status: NodeStatus
    fields: tuple[tuple[str, str], ...] = ()
    members: tuple[str, ...] | None = None
    profile40: tuple[str, ...] | None = None
    profile_basis: str | None = None
    expansion_ref: str | None = None
    kind: NodeKind = NodeKind.IDEA_CONTEXT
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self):
        identifier(self.node_id, "node")
        identifier(self.idea_id, "canonical idea")
        text(self.label, "node label", 512)
        require(type(self.context) is AtlasContext and type(self.status) is NodeStatus
                and type(self.kind) is NodeKind, "node context/status/kind must be typed")
        require(type(self.fields) is tuple and len(self.fields) <= 64, "node fields invalid")
        for row in self.fields:
            require(type(row) is tuple and len(row) == 2, "node field pair invalid")
            identifier(row[0], "field")
            text(row[1], "field value", MAX_FIELD_VALUE, empty=True)
        require(tuple(key for key, _ in self.fields) == tuple(sorted({key for key, _ in self.fields})),
                "node fields must be sorted and unique")
        if self.members is not None:
            identifiers(self.members, "finite region members")
        validate_profile40(self.profile40, self.profile_basis)
        if self.expansion_ref is not None:
            text(self.expansion_ref, "expansion reference", 512)
        identifiers(self.evidence_refs, "node evidence", 64)

    @property
    def view_key(self):
        # Distinct projections/refinements may share both idea and context.
        # Their view ID remains significant; changed versions remain significant.
        return self.node_id, self.idea_id, digest(self.context.to_dict())

    @property
    def region_digest(self):
        return digest({"node_id": self.node_id, "context": self.context.to_dict(), "members": self.members})

    def to_dict(self):
        return {**schema_wire(self, NODE_SCHEMA), "context": self.context.to_dict()}

    @classmethod
    def from_dict(cls, value):
        body = decode_fields(value, cls, NODE_SCHEMA)
        body["context"] = AtlasContext.from_dict(body["context"])
        require(type(body["status"]) is str and type(body["kind"]) is str, "node status/kind wire invalid")
        try:
            body["status"], body["kind"] = NodeStatus(body["status"]), NodeKind(body["kind"])
        except ValueError as exc:
            raise ContractError("unknown node status/kind") from exc
        body["fields"] = wire_pairs(body["fields"], "node fields", 64)
        body["members"] = None if body["members"] is None else wire_list(body["members"], "members", MAX_MEMBERS)
        body["profile40"] = None if body["profile40"] is None else wire_list(body["profile40"], "profile", 40)
        body["evidence_refs"] = wire_list(body["evidence_refs"], "evidence", 64)
        return cls(**body)


@dataclass(frozen=True, slots=True)
class AtlasLink:
    link_id: str
    source_id: str
    target_id: str
    relation: LinkType
    projection: str | None = None
    action_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    certificate_id: str | None = None
    transition_status: str | None = None

    def __post_init__(self):
        for name in ("link_id", "source_id", "target_id"):
            identifier(getattr(self, name), name)
        require(type(self.relation) is LinkType, "link relation must be typed")
        identifiers(self.evidence_refs, "link evidence", 64)
        if self.relation is LinkType.CONTAINS_PART:
            text(self.projection, "declared part projection", 512)
        else:
            require(self.projection is None, "only part links declare projections")
        if self.relation is LinkType.REACHABLE_VIA:
            identifier(self.action_id, "transition action")
            require(type(self.transition_status) is str and self.transition_status in
                    {"candidate", "observed", "rejected"}, "transition status invalid")
            if self.transition_status in {"observed", "rejected"}:
                require(bool(self.evidence_refs), "observed transition needs evidence reference")
        else:
            require(self.action_id is None and self.transition_status is None,
                    "only transition links declare actions")
        if self.relation is LinkType.OVERLAPS_WITH:
            identifier(self.certificate_id, "overlap certificate")
        else:
            require(self.certificate_id is None, "only overlap links reference certificates")

    def to_dict(self):
        return schema_wire(self, LINK_SCHEMA)

    @classmethod
    def from_dict(cls, value):
        body = decode_fields(value, cls, LINK_SCHEMA)
        require(type(body["relation"]) is str, "link relation wire invalid")
        try:
            body["relation"] = LinkType(body["relation"])
        except ValueError as exc:
            raise ContractError("unknown link relation") from exc
        body["evidence_refs"] = wire_list(body["evidence_refs"], "link evidence", 64)
        return cls(**body)


@dataclass(frozen=True, slots=True)
class OverlapCertificate:
    certificate_id: str
    node_ids: tuple[str, ...]
    witness_id: str
    context: AtlasContext
    region_digests: tuple[tuple[str, str], ...]

    def __post_init__(self):
        identifiers(self.node_ids, "overlap nodes", 16)
        require(len(self.node_ids) >= 2, "overlap certificate needs at least two regions")
        identifier(self.witness_id, "overlap witness")
        require(type(self.context) is AtlasContext and type(self.region_digests) is tuple,
                "overlap context/digests invalid")
        require(all(type(row) is tuple and len(row) == 2 for row in self.region_digests),
                "overlap digest pairs invalid")
        require(tuple(key for key, _ in self.region_digests) == self.node_ids, "overlap digest scope mismatch")
        require(all(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value)
                    for _, value in self.region_digests), "overlap digest invalid")
        require(self.certificate_id == "overlap-" + digest(self._body()), "overlap certificate digest mismatch")

    def _body(self):
        return {"schema_version": OVERLAP_SCHEMA, "node_ids": list(self.node_ids),
                "witness_id": self.witness_id, "context": self.context.to_dict(),
                "region_digests": [list(row) for row in self.region_digests]}

    def to_dict(self):
        return {"certificate_id": self.certificate_id, **self._body()}

    @classmethod
    def from_dict(cls, value):
        body = decode_fields(value, cls, OVERLAP_SCHEMA)
        body["node_ids"] = wire_list(body["node_ids"], "overlap nodes", 16)
        body["region_digests"] = wire_pairs(body["region_digests"], "overlap digests", 16)
        body["context"] = AtlasContext.from_dict(body["context"])
        return cls(**body)


def certify_overlap(nodes, witness_id=None):
    require(type(nodes) is tuple and 2 <= len(nodes) <= 16 and all(type(n) is AtlasNode for n in nodes),
            "overlap requires a bounded tuple of typed regions")
    require(len({node.node_id for node in nodes}) == len(nodes), "overlap contains duplicate node")
    ordered = tuple(sorted(nodes, key=lambda node: node.node_id))
    context = ordered[0].context
    require(all(node.context == context and node.members is not None for node in ordered),
            "overlap needs explicit finite sets in the same context/version/observation")
    common = set(ordered[0].members)
    for node in ordered[1:]:
        common.intersection_update(node.members)
    require(bool(common), "regions have no common witness")
    selected = min(common) if witness_id is None else witness_id
    identifier(selected, "overlap witness")
    require(selected in common, "witness is not a member of every region")
    body = {"schema_version": OVERLAP_SCHEMA, "node_ids": [node.node_id for node in ordered],
            "witness_id": selected, "context": context.to_dict(),
            "region_digests": [[node.node_id, node.region_digest] for node in ordered]}
    return OverlapCertificate.from_dict({"certificate_id": "overlap-" + digest(body), **body})


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    node_ids: tuple[str, ...]
    same_context: bool
    shared_fields: tuple[str, ...]
    conflicting_fields: tuple[str, ...]

    @property
    def compatible(self):
        return self.same_context and not self.conflicting_fields

    def to_dict(self):
        return {**to_primitive(self), "compatible": self.compatible,
                "boundary": "shared-field consistency only; not a sheaf gluing proof"}


def compatibility(nodes):
    require(type(nodes) is tuple and 2 <= len(nodes) <= 16 and all(type(n) is AtlasNode for n in nodes),
            "compatibility needs a bounded tuple of typed views")
    require(len({node.node_id for node in nodes}) == len(nodes), "duplicate compatibility view")
    values = {}
    occurrences = {}
    for node in nodes:
        for key, value in node.fields:
            values.setdefault(key, set()).add(value)
            occurrences[key] = occurrences.get(key, 0) + 1
    shared = tuple(sorted(key for key, count in occurrences.items() if count > 1))
    conflicts = tuple(key for key in shared if len(values[key]) > 1)
    return CompatibilityReport(tuple(sorted(node.node_id for node in nodes)),
        all(node.context == nodes[0].context for node in nodes), shared, conflicts)


@dataclass(frozen=True, slots=True)
class DeferredExpansion:
    source_id: str
    link_id: str | None
    target_id: str | None
    reason: str
    expansion_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ExpansionResult:
    root_id: str
    max_depth: int
    max_nodes: int
    visited_node_ids: tuple[str, ...]
    traversed_link_ids: tuple[str, ...]
    revisited_link_ids: tuple[str, ...]
    deferred: tuple[DeferredExpansion, ...]

    def to_dict(self):
        return {**to_primitive(self), "nodes_used": len(self.visited_node_ids),
                "boundary": "finite supplied graph only; deferred does not mean impossible"}


@dataclass(frozen=True, slots=True)
class AtlasSnapshot:
    nodes: tuple[AtlasNode, ...]
    links: tuple[AtlasLink, ...]
    current_state_id: str
    focus_node_id: str
    hypothesis_branch_id: str | None = None
    overlap_certificates: tuple[OverlapCertificate, ...] = ()

    def __post_init__(self):
        require(type(self.nodes) is tuple and 1 <= len(self.nodes) <= MAX_NODES
                and all(type(node) is AtlasNode for node in self.nodes), "atlas node bound/type invalid")
        # Every field character costs at least one serialized byte. Reject the
        # potentially largest content before creating any aggregate JSON string;
        # the exact byte check below also includes escaping and all metadata.
        require(sum(len(value) for node in self.nodes for _, value in node.fields) <= MAX_ATLAS_BYTES,
                "atlas field text bound exceeded before serialization")
        require(type(self.links) is tuple and len(self.links) <= MAX_LINKS
                and all(type(link) is AtlasLink for link in self.links), "atlas link bound/type invalid")
        require(type(self.overlap_certificates) is tuple and len(self.overlap_certificates) <= 128
                and all(type(cert) is OverlapCertificate for cert in self.overlap_certificates),
                "atlas overlap certificate bound/type invalid")
        nodes = {node.node_id: node for node in self.nodes}
        require(len(nodes) == len(self.nodes), "duplicate atlas node ID")
        require(len({link.link_id for link in self.links}) == len(self.links), "duplicate atlas link")
        identifier(self.current_state_id, "current state")
        identifier(self.focus_node_id, "focus node")
        require(self.current_state_id in nodes and self.focus_node_id in nodes, "atlas navigation reference missing")
        current = nodes[self.current_state_id]
        require(current.kind is NodeKind.STATE and current.status in {NodeStatus.OBSERVED, NodeStatus.VERIFIED},
                "current state must reference a supplied observed/verified state record")
        if self.hypothesis_branch_id is not None:
            identifier(self.hypothesis_branch_id, "hypothesis branch")
            require(self.hypothesis_branch_id in nodes
                    and nodes[self.hypothesis_branch_id].status is NodeStatus.HYPOTHETICAL,
                    "hypothesis handle must reference a hypothetical node")
        certificates = {cert.certificate_id: cert for cert in self.overlap_certificates}
        require(len(certificates) == len(self.overlap_certificates), "duplicate overlap certificate")
        for cert in self.overlap_certificates:
            require(all(key in nodes for key in cert.node_ids), "overlap references absent node")
            expected = certify_overlap(tuple(nodes[key] for key in cert.node_ids), cert.witness_id)
            require(expected == cert, "overlap certificate does not reconstruct")
        contains = {key: [] for key in nodes}
        indegree = {key: 0 for key in nodes}
        for link in self.links:
            require(link.source_id in nodes and link.target_id in nodes, "atlas link endpoint missing")
            source, target = nodes[link.source_id], nodes[link.target_id]
            if link.relation is LinkType.CONTAINS_PART:
                contains[source.node_id].append(target.node_id)
                indegree[target.node_id] += 1
            elif link.relation is LinkType.REFINES_STATE:
                require(source.context == target.context and source.members is not None and target.members is not None,
                        "refinement needs explicit same-context finite membership sets")
                require(set(target.members) <= set(source.members), "refinement child is not a subset of parent")
                require(source.node_id == target.node_id or compatibility((source, target)).compatible,
                        "refinement shared fields conflict")
            elif link.relation is LinkType.REFERENCES_SAME_IDEA:
                require(source.idea_id == target.idea_id, "same-idea link must share a canonical idea ID")
            elif link.relation is LinkType.OVERLAPS_WITH:
                cert = certificates.get(link.certificate_id)
                require(cert is not None and source.node_id in cert.node_ids and target.node_id in cert.node_ids,
                        "overlap link has no bound common-witness certificate")
        ready = deque(sorted(key for key, count in indegree.items() if count == 0))
        seen = 0
        while ready:
            key = ready.popleft()
            seen += 1
            for child in contains[key]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
        require(seen == len(nodes), "contains_part cycle is prohibited")
        require(len(canonical_json(self.to_dict()).encode("utf-8")) <= MAX_ATLAS_BYTES, "atlas byte bound exceeded")

    @property
    def snapshot_digest(self):
        return digest(self.to_dict())

    def node_map(self):
        return {node.node_id: node for node in self.nodes}

    def focus(self, node_id):
        """Return another navigation view; preserve every record and present ID."""
        return replace(self, focus_node_id=node_id)

    def with_hypothesis(self, node_id):
        return replace(self, hypothesis_branch_id=node_id)

    def expand(self, *, max_depth=3, max_nodes=100, relations=None, root_id=None):
        integer(max_depth, "expansion depth", MAX_DEPTH)
        integer(max_nodes, "expansion node budget", MAX_NODES, 1)
        selected = tuple(LinkType) if relations is None else relations
        require(type(selected) is tuple and len(selected) <= len(LinkType)
                and all(type(item) is LinkType for item in selected)
                and len(set(selected)) == len(selected), "expansion relations invalid")
        root = self.focus_node_id if root_id is None else root_id
        identifier(root, "expansion root")
        nodes = self.node_map()
        require(root in nodes, "expansion root missing")
        adjacency = {key: [] for key in nodes}
        for link in sorted(self.links, key=lambda item: item.link_id):
            if link.relation in selected:
                adjacency[link.source_id].append(link)
        queue, visited, keys = deque(((root, 0),)), [root], {nodes[root].view_key}
        traversed, revisited, deferred = [], [], []
        while queue:
            node_id, depth = queue.popleft()
            node = nodes[node_id]
            if node.expansion_ref is not None:
                deferred.append(DeferredExpansion(node_id, None, None, "generator_not_expanded", node.expansion_ref))
            for link in adjacency[node_id]:
                key = nodes[link.target_id].view_key
                if key in keys:
                    traversed.append(link.link_id)
                    revisited.append(link.link_id)
                elif depth >= max_depth:
                    deferred.append(DeferredExpansion(node_id, link.link_id, link.target_id, "max_depth"))
                elif len(visited) >= max_nodes:
                    deferred.append(DeferredExpansion(node_id, link.link_id, link.target_id, "max_nodes"))
                else:
                    keys.add(key)
                    visited.append(link.target_id)
                    traversed.append(link.link_id)
                    queue.append((link.target_id, depth + 1))
        return ExpansionResult(root, max_depth, max_nodes, tuple(visited), tuple(traversed),
                               tuple(revisited), tuple(deferred))

    def to_dict(self):
        return {"schema_version": SNAPSHOT_SCHEMA,
                "nodes": [node.to_dict() for node in sorted(self.nodes, key=lambda row: row.node_id)],
                "links": [link.to_dict() for link in sorted(self.links, key=lambda row: row.link_id)],
                "current_state_id": self.current_state_id,
                "focus_node_id": self.focus_node_id, "hypothesis_branch_id": self.hypothesis_branch_id,
                "overlap_certificates": [cert.to_dict() for cert in
                    sorted(self.overlap_certificates, key=lambda row: row.certificate_id)]}

    def flat_graph(self):
        """The same records and edges for a matched ordinary graph presentation."""
        return self.to_dict()

    @classmethod
    def from_dict(cls, value):
        body = decode_fields(value, cls, SNAPSHOT_SCHEMA)
        body["nodes"] = tuple(AtlasNode.from_dict(node) for node in wire_list(body["nodes"], "nodes", MAX_NODES))
        body["links"] = tuple(AtlasLink.from_dict(link) for link in wire_list(body["links"], "links", MAX_LINKS))
        body["overlap_certificates"] = tuple(OverlapCertificate.from_dict(cert)
            for cert in wire_list(body["overlap_certificates"], "overlap certificates", 128))
        return cls(**body)
