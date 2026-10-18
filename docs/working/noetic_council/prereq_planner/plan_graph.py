"""plan_graph.py -- Prerequisite-graph planner (replaces keyword matching).

SPECIFICATION IMPLEMENTATION:
SPEC_PREREQUISITE_GRAPH_PLANNER_20261018.md

Architecture:
1. Parse: English request -> CCE prerequisite sentences (Form 1) or temporal markers (Form 2).
2. Nodes: PlanNode for every production target omega (leaf or internal).
3. Edges: PlanEdge(before, after, source) with mandatory source tracking.
4. Cycle detection: Refuses contradictions with PLAN_CYCLE.
5. Depth computation: Evaluates depth against HORIZON = 12 using dwp_engine_v2/depth.py.
6. Kahn's algorithm: Deterministic topological sort by vibration desc, omega asc.
7. Emission: Ordered steps, edges with sources, and tamper-proof digest.

CLAIM CEILING:
MECHANISM ONLY. ORDERING IS DERIVED FROM STATED PREREQUISITES. NO UNDERSTANDING OF THE REQUEST IS CLAIMED.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set

HERE = os.path.dirname(os.path.abspath(__file__))
COUNCIL = os.path.dirname(HERE)

for path in (
    os.path.join(COUNCIL, "language_v3"),
    os.path.join(COUNCIL, "dwp_engine_v2"),
    os.path.join(COUNCIL, "the_loop_v3"),
    os.path.join(COUNCIL, "repair_performer"),
):
    if path not in sys.path:
        sys.path.insert(0, path)

import cce
import depth as depth_engine

CLAIM_CEILING = (
    "MECHANISM ONLY. ORDERING IS DERIVED FROM STATED PREREQUISITES. "
    "NO UNDERSTANDING OF THE REQUEST IS CLAIMED."
)

# Refusal codes specified in Section 6
PLAN_EMPTY = "PLAN_EMPTY"
PLAN_CYCLE = "PLAN_CYCLE"
PLAN_HORIZON = "PLAN_HORIZON"
PLAN_UNDECLARED_OMEGA = "PLAN_UNDECLARED_OMEGA"
PLAN_ORDER_VIOLATION = "PLAN_ORDER_VIOLATION"
PLAN_EDGE_WITHOUT_SOURCE = "PLAN_EDGE_WITHOUT_SOURCE"
PLAN_REPAIR_FAILED = "PLAN_REPAIR_FAILED"


class PlanRefusal(Exception):
    """Typed refusal for prerequisite graph planning."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class PlanNode:
    """The production target node."""
    omega: str
    recipe: Optional[dict]
    needs: tuple[str, ...]
    depth: int
    kind: str  # 'leaf' when needs == (), 'internal' otherwise
    vibration: int = 0


@dataclass(frozen=True)
class PlanEdge:
    """Directed prerequisite edge from before to after."""
    before: str
    after: str
    source: str  # Mandatory: exact sentence that produced this edge


@dataclass(frozen=True)
class PlanResult:
    """Deterministic output of the prerequisite graph planner."""
    nodes: tuple[PlanNode, ...]
    edges: tuple[PlanEdge, ...]
    order: tuple[str, ...]
    order_source: str
    digest: str

    def as_dict(self) -> dict:
        return {
            "order": list(self.order),
            "order_source": self.order_source,
            "digest": self.digest,
            "nodes": [
                {
                    "omega": n.omega,
                    "depth": n.depth,
                    "kind": n.kind,
                    "needs": list(n.needs),
                    "vibration": n.vibration,
                }
                for n in self.nodes
            ],
            "edges": [
                {"before": e.before, "after": e.after, "source": e.source}
                for e in self.edges
            ],
        }


def _phrase_to_omega(phrase: str) -> str:
    """Extract or normalize an action/production target from an English phrase."""
    lower = phrase.lower().strip()
    # Check for direct omega notation
    m_omega = re.search(r"(Ω_\w+|Ω|\b[A-Za-z]_\w+)", phrase)
    if m_omega and ("needs" in lower or phrase.strip().startswith("Ω")):
        return m_omega.group(1)

    # Standard tool actions recognized by the spec
    if re.search(r"\b(git|commit|log|diff|branch|repo|state|recover)\b", lower):
        return "git"
    if re.search(r"\b(verify|verifying|verification|test|tests|test suite|benchmark|check tests)\b", lower):
        return "verify"
    if re.search(r"\b(write|writing|code|synthesize|synthesizing|script|implement)\b", lower):
        return "synthesize"
    if re.search(r"\b(read|reading|inspect|inspecting|cat|examine)\b", lower):
        return "inspect"
    if re.search(r"\b(system.*design|design.*system|architecture)\b", lower):
        return "design"
    if re.search(r"\b(web|app|scaffold|dashboard)\b", lower):
        return "scaffold"

    clean = re.sub(r"[^\w\s-]", "", lower).strip()
    tokens = clean.split()
    return tokens[0] if tokens else "step"


def parse_prerequisites(request: str, allow_temporal: bool = True) -> Tuple[List[str], List[PlanEdge], str]:
    """Parse request into omega nodes and directed prerequisite edges."""
    text = request.strip()
    if not text:
        raise PlanRefusal(PLAN_EMPTY, "the request is empty")

    edges: List[PlanEdge] = []
    omegas: Set[str] = set()
    order_source = "NONE"

    # -------------------------------------------------------------------------
    # Form 1: Explicit CCE prerequisite sentences (F22)
    # -------------------------------------------------------------------------
    is_cce = False
    try:
        parsed_cce = cce.parse(text)
        relations = parsed_cce.get("relations", [])
        for r in relations:
            if r[0] == "needs_first":
                is_cce = True
                after_omega = r[1]
                before_omega = r[2]
                source_sentence = f"{after_omega} needs {before_omega} first."
                edges.append(PlanEdge(before=before_omega, after=after_omega, source=source_sentence))
                omegas.add(after_omega)
                omegas.add(before_omega)
                order_source = "CCE_PREREQUISITE"
    except Exception:
        pass

    if is_cce and edges:
        return sorted(omegas), edges, order_source

    if not allow_temporal:
        # Reverted temporal mode for bite check (emulating old keyword planner with fixed chain)
        omega_tokens = []
        if re.search(r"\b(write|writing|code|synthesize)\b", text, re.I):
            omega_tokens.append("synthesize")
        if re.search(r"\b(verify|test|tests)\b", text, re.I):
            omega_tokens.append("verify")
        if re.search(r"\b(git|commit|log|diff|state|recover)\b", text, re.I):
            omega_tokens.append("git")
        fallback_edges = []
        if "synthesize" in omega_tokens and "git" in omega_tokens:
            fallback_edges.append(PlanEdge(before="synthesize", after="git", source="OLD_FIXED_CHAIN"))
        return omega_tokens, fallback_edges, "OLD_KEYWORD_CHAIN"

    # -------------------------------------------------------------------------
    # Form 2: Temporal discourse markers (F16)
    # -------------------------------------------------------------------------
    # 1. 'Before X, Y' or 'Prior to X, Y' -> Y comes BEFORE X
    m_before = re.match(r"^(?:before|prior to)\s+(.+?),\s*(.+)$", text, re.IGNORECASE)
    if m_before:
        action_x = m_before.group(1).strip()
        action_y = m_before.group(2).strip()
        omega_x = _phrase_to_omega(action_x)
        omega_y = _phrase_to_omega(action_y)
        edge = PlanEdge(before=omega_y, after=omega_x, source=text)
        edges.append(edge)
        omegas.add(omega_y)
        omegas.add(omega_x)
        return sorted(omegas), edges, "TEMPORAL_BEFORE"

    # 2. 'First X ... then Y' -> X comes BEFORE Y
    m_first = re.search(r"^first\s+(.+?)(?:;|,)?\s*then\s+(.+)$", text, re.IGNORECASE)
    if m_first:
        action_x = m_first.group(1).strip()
        action_y = m_first.group(2).strip()
        omega_x = _phrase_to_omega(action_x)
        omega_y = _phrase_to_omega(action_y)
        edge = PlanEdge(before=omega_x, after=omega_y, source=text)
        edges.append(edge)
        omegas.add(omega_x)
        omegas.add(omega_y)
        return sorted(omegas), edges, "TEMPORAL_FIRST_THEN"

    # 3. 'After X, Y' -> X comes BEFORE Y
    m_after = re.match(r"^after\s+(.+?),\s*(.+)$", text, re.IGNORECASE)
    if m_after:
        action_x = m_after.group(1).strip()
        action_y = m_after.group(2).strip()
        omega_x = _phrase_to_omega(action_x)
        omega_y = _phrase_to_omega(action_y)
        edge = PlanEdge(before=omega_x, after=omega_y, source=text)
        edges.append(edge)
        omegas.add(omega_x)
        omegas.add(omega_y)
        return sorted(omegas), edges, "TEMPORAL_AFTER"

    # 4. Sequential connectors: ', then', 'then', ', finally', ';'
    if re.search(r"\b(then|finally)\b|;", text, re.IGNORECASE):
        delims = r"(?:;\s*|,\s*(?:then\s+|and\s+then\s+|and\s+|finally\s+)?|\s+then\s+|\s+and\s+then\s+|\s+finally\s+)"
        parts = [p.strip() for p in re.split(delims, text, flags=re.IGNORECASE) if p.strip()]

        if len(parts) > 1:
            extracted_omegas = []
            for part in parts:
                om = _phrase_to_omega(part)
                extracted_omegas.append(om)
                omegas.add(om)

            for i in range(len(extracted_omegas) - 1):
                b_om = extracted_omegas[i]
                a_om = extracted_omegas[i + 1]
                if b_om != a_om:
                    edge = PlanEdge(before=b_om, after=a_om, source=text)
                    edges.append(edge)

            return sorted(omegas), edges, "TEMPORAL_SEQUENCE"

    # 5. Single action (no temporal markers)
    single_om = _phrase_to_omega(text)
    omegas.add(single_om)
    return sorted(omegas), edges, "NONE"


def build_plan(request: str, allow_temporal: bool = True) -> PlanResult:
    """Build, validate, and topologically order a prerequisite plan graph."""
    omegas, edges, order_source = parse_prerequisites(request, allow_temporal=allow_temporal)

    if not omegas:
        raise PlanRefusal(PLAN_EMPTY, "no production targets or steps found in request")

    # Edge integrity check: every edge MUST carry source
    for edge in edges:
        if not edge.source or not edge.source.strip():
            raise PlanRefusal(PLAN_EDGE_WITHOUT_SOURCE, f"edge ({edge.before} -> {edge.after}) has no source sentence")

    # Map needs for each omega
    needs_map: Dict[str, List[str]] = {om: [] for om in omegas}
    for edge in edges:
        if edge.after not in needs_map:
            raise PlanRefusal(PLAN_UNDECLARED_OMEGA, f"edge references undeclared target '{edge.after}'")
        if edge.before not in needs_map:
            raise PlanRefusal(PLAN_UNDECLARED_OMEGA, f"edge references undeclared prerequisite '{edge.before}'")
        if edge.before not in needs_map[edge.after]:
            needs_map[edge.after].append(edge.before)

    # -------------------------------------------------------------------------
    # Cycle Detection
    # -------------------------------------------------------------------------
    adj: Dict[str, List[str]] = {om: [] for om in omegas}
    in_degrees: Dict[str, int] = {om: 0 for om in omegas}

    for edge in edges:
        adj[edge.before].append(edge.after)
        in_degrees[edge.after] += 1

    # Kahn's test for acyclicity
    q = [om for om, deg in in_degrees.items() if deg == 0]
    visited_count = 0
    while q:
        curr = q.pop(0)
        visited_count += 1
        for nxt in adj[curr]:
            in_degrees[nxt] -= 1
            if in_degrees[nxt] == 0:
                q.append(nxt)

    if visited_count != len(omegas):
        # Contradiction: cycle detected
        cycle_members = [om for om, deg in in_degrees.items() if deg > 0]
        raise PlanRefusal(PLAN_CYCLE, f"contradiction: cycle detected among {sorted(cycle_members)}")

    # -------------------------------------------------------------------------
    # Depth Computation & HORIZON Validation (Section 4 & depth.py)
    # -------------------------------------------------------------------------
    depth_map: Dict[str, int] = {}

    def get_depth(om: str) -> int:
        if om in depth_map:
            return depth_map[om]
        needs = needs_map[om]
        if not needs:
            d = 0
        else:
            d = 1 + max(get_depth(req) for req in needs)
        depth_map[om] = d
        return d

    for om in omegas:
        d = get_depth(om)
        verdict = depth_engine.check_depth(d)
        if verdict == depth_engine.DepthVerdict.STRUCTURAL_DEADLOCK:
            raise PlanRefusal(
                PLAN_HORIZON,
                f"node '{om}' at depth {d} reaches or exceeds recursion HORIZON {depth_engine.HORIZON}"
            )

    # -------------------------------------------------------------------------
    # Deterministic Kahn's Topological Sort (Section 4, Step 6)
    # Tie-breaking: vibration descending, then omega alphabetically
    # -------------------------------------------------------------------------
    kahn_in_degrees: Dict[str, int] = {om: len(needs_map[om]) for om in omegas}
    kahn_adj: Dict[str, List[str]] = {om: [] for om in omegas}
    for edge in edges:
        kahn_adj[edge.before].append(edge.after)

    ready_queue: List[str] = [om for om, deg in kahn_in_degrees.items() if deg == 0]
    sorted_order: List[str] = []

    while ready_queue:
        # Deterministic tie-break: vibration descending, omega alphabetically ascending
        ready_queue.sort(key=lambda x: (0, x))  # vibration defaults to 0
        curr = ready_queue.pop(0)
        sorted_order.append(curr)

        for neighbor in kahn_adj[curr]:
            kahn_in_degrees[neighbor] -= 1
            if kahn_in_degrees[neighbor] == 0:
                ready_queue.append(neighbor)

    # Build PlanNode objects in sorted order
    plan_nodes: List[PlanNode] = []
    for om in sorted_order:
        needs = tuple(needs_map[om])
        d = depth_map[om]
        kind = "leaf" if len(needs) == 0 else "internal"
        plan_nodes.append(PlanNode(
            omega=om,
            recipe=None,
            needs=needs,
            depth=d,
            kind=kind,
            vibration=0
        ))

    # Compute deterministic plan digest
    canonical_repr = json.dumps({
        "order": sorted_order,
        "nodes": [(n.omega, n.depth, n.needs) for n in plan_nodes],
        "edges": [(e.before, e.after, e.source) for e in edges]
    }, sort_keys=True)
    digest = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()

    return PlanResult(
        nodes=tuple(plan_nodes),
        edges=tuple(edges),
        order=tuple(sorted_order),
        order_source=order_source,
        digest=digest
    )
