"""operations.py -- The three operations over the Unified Cube Store.

Implements Sections 1, 4, 7 of SPEC_CUBE_STORE_UNIFIED_20261018.md:
  1. LIST_PARTS(W): 'what are the direct parts of W' <-> 'what do we have in stock'
  2. FIND_SHARED_PART(A, B): 'what do A and B have in common' <-> shared constituent analysis
  3. REACHED_VIA(W, X): 'how is X reached from W' (direct | via:<intermediate> | absent)

Every answered operation cites the operation run and the cube(s) it read (Section 7, T1).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from cube import CubeNode
from store import CubeStore


@dataclass
class OperationReceipt:
    operation: str
    cubes_read: List[str] = field(default_factory=list)
    success: bool = True
    output: Any = None
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "cubes_read": list(self.cubes_read),
            "success": self.success,
            "output": self.output,
            "detail": self.detail,
        }


def list_parts(store: CubeStore, whole_id: str, view_profile: str = "LearnerView") -> OperationReceipt:
    """LIST_PARTS(W): retrieves direct constituents of whole_id.
    Operates over outgoing 'contains' branches and node decomposition.
    """
    node = store.get_cube(whole_id, view_profile=view_profile)
    if node is None:
        return OperationReceipt(
            operation="LIST_PARTS",
            cubes_read=[],
            success=False,
            output=None,
            detail=f"Whole node {whole_id!r} not found in store.",
        )

    cubes_read = [whole_id]
    direct_branches = store.get_outgoing_branches(whole_id, predicate="contains")

    parts: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    # 1. Inspect outgoing branches
    for b in direct_branches:
        target_id = b.target_node_id
        cubes_read.append(target_id)
        target_node = store.get_cube(target_id, view_profile=view_profile)
        label = target_node.core.label if target_node else target_id
        amount = b.commonality.get("amount") if b.commonality else None
        key = f"{amount}_{label}" if amount else label
        if key not in seen:
            seen.add(key)
            parts.append({
                "node_id": target_id,
                "label": label,
                "amount": amount,
                "kind": target_node.core.kind if target_node else "instance"
            })

    # 2. Also check face 5 if structured direct_branch_refs are populated
    f5 = node.faces.get("face_5")
    if f5 and f5.availability == "populated":
        for ref in f5.structured.get("direct_branch_refs", []):
            if ref not in seen:
                seen.add(ref)
                ref_node = store.get_cube(ref, view_profile=view_profile)
                if ref_node:
                    cubes_read.append(ref)
                    parts.append({
                        "node_id": ref,
                        "label": ref_node.core.label,
                        "amount": None,
                        "kind": ref_node.core.kind
                    })

    detail_str = f"Found {len(parts)} direct part(s) of '{node.core.label}'"
    return OperationReceipt(
        operation="LIST_PARTS",
        cubes_read=sorted(set(cubes_read)),
        success=True,
        output=parts,
        detail=detail_str
    )


def find_shared_part(
    store: CubeStore,
    node_a_id: str,
    target_or_query: Any,
    view_profile: str = "LearnerView"
) -> OperationReceipt:
    """FIND_SHARED_PART(A, B): identifies shared direct constituents.
    - If target_or_query is a node_id for node B: finds direct parts common to A and B.
    - If target_or_query is a list of queried items (e.g. ['Flour', 'Sugar']):
      verifies if those items are shared direct parts of node A.
    """
    cubes_read = [node_a_id]
    rec_a = list_parts(store, node_a_id, view_profile=view_profile)
    if not rec_a.success:
        return OperationReceipt(
            operation="FIND_SHARED_PART",
            cubes_read=cubes_read,
            success=False,
            output=None,
            detail=f"Node {node_a_id!r} could not be inspected."
        )
    cubes_read.extend(rec_a.cubes_read)

    parts_a = {p["label"].lower(): p for p in (rec_a.output or [])}

    # Case 1: comparing two cube nodes in the store
    if isinstance(target_or_query, str) and target_or_query in store.nodes:
        node_b_id = target_or_query
        cubes_read.append(node_b_id)
        rec_b = list_parts(store, node_b_id, view_profile=view_profile)
        cubes_read.extend(rec_b.cubes_read)
        parts_b = {p["label"].lower(): p for p in (rec_b.output or [])}

        common_keys = set(parts_a.keys()).intersection(set(parts_b.keys()))
        common = [parts_a[k]["label"] for k in common_keys]
        return OperationReceipt(
            operation="FIND_SHARED_PART",
            cubes_read=sorted(set(cubes_read)),
            success=True,
            output=common if common else None,
            detail=f"Shared constituent between '{node_a_id}' and '{node_b_id}': {common or 'None'}"
        )

    # Case 2: verifying requested parts against inventory / node_a
    # e.g. "Do we have 50 Flour and 30 Sugar or not"
    query_items = target_or_query if isinstance(target_or_query, list) else [str(target_or_query)]
    matched = []
    missing = []
    for item in query_items:
        clean = item.strip().lower()
        found = False
        for k, p in parts_a.items():
            if clean in k or k in clean:
                matched.append(p)
                found = True
                break
        if not found:
            missing.append(item)

    is_complete_match = (len(missing) == 0 and len(matched) > 0)
    return OperationReceipt(
        operation="FIND_SHARED_PART",
        cubes_read=sorted(set(cubes_read)),
        success=is_complete_match,
        output={"matched": matched, "missing": missing, "all_matched": is_complete_match},
        detail=f"Matched {len(matched)}/{len(query_items)} queried items on '{node_a_id}'."
    )


def reached_via(
    store: CubeStore,
    source_id: str,
    target_id: str,
    view_profile: str = "LearnerView"
) -> OperationReceipt:
    """REACHED_VIA(W, X): distinguishes direct edge, via:<constituent> path, or absent."""
    if source_id not in store.nodes or target_id not in store.nodes:
        return OperationReceipt(
            operation="REACHED_VIA",
            cubes_read=[n for n in (source_id, target_id) if n in store.nodes],
            success=False,
            output="absent",
            detail="Source or target node not found in store."
        )

    cubes_read = [source_id]

    # 1. Check direct connection
    direct = [b for b in store.get_outgoing_branches(source_id) if b.target_node_id == target_id]
    if direct:
        cubes_read.append(target_id)
        return OperationReceipt(
            operation="REACHED_VIA",
            cubes_read=sorted(set(cubes_read)),
            success=True,
            output="direct",
            detail=f"Direct branch exists: '{source_id}' -> '{target_id}'"
        )

    # 2. Check 2-hop / intermediate path
    for b in store.get_outgoing_branches(source_id):
        mid = b.target_node_id
        cubes_read.append(mid)
        second_hop = [b2 for b2 in store.get_outgoing_branches(mid) if b2.target_node_id == target_id]
        if second_hop:
            cubes_read.append(target_id)
            mid_node = store.get_cube(mid, view_profile=view_profile)
            mid_label = mid_node.core.label if mid_node else mid
            return OperationReceipt(
                operation="REACHED_VIA",
                cubes_read=sorted(set(cubes_read)),
                success=True,
                output=f"via:{mid_label}",
                detail=f"Path exists from '{source_id}' to '{target_id}' via '{mid_label}'."
            )

    return OperationReceipt(
        operation="REACHED_VIA",
        cubes_read=sorted(set(cubes_read)),
        success=True,
        output="absent",
        detail=f"No path found between '{source_id}' and '{target_id}' in declared graph."
    )
