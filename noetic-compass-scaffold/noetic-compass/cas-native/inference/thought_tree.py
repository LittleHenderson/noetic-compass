"""Thought Tree builder — UI-ready node-edge graph from a cas-explain report.

This is the Phase 1 (2D, JSON-serializable) version of the Thought Tree
that the Living Thought Atlas UI eventually consumes. Per
`docs/working/cas_thought_tree_idea_atlas_codex_audit_2026_05_13.md`:
share canonical graph identity (kind + role + normalized_label +
axis_attrs) so the same tree can render in 2D today and 3D in Phase 2.

Public surface:
- `build_thought_tree(report) -> dict` — JSON-ready tree structure.
- `count_nodes(tree) -> int`
- `count_edges(tree) -> int`

Bounded scope (per `decisions.md` 2026-05-13T17:30Z):
- Pure function. No model call.
- Builds from existing cas-explain fields. No new tensors.
- No 3D rendering, no visual layout, no SGGS integration.
- Mode 7 ghost-branch alternates are deferred to v1+.

Node types (from `cas_thought_tree_idea_atlas_codex_audit_2026_05_13.md`
Thought Tree spec):
- `user_prompt`: the input CAS expression (root)
- `model_generation`: the model's English output
- `identifier_attempt`: per expected identifier, copied or missed
- `slot_pattern`: summary of the slot trace structure
- `confidence_marker`: confidence band + caveat as a node
"""
from __future__ import annotations

from typing import Any, Optional


def _node(
    kind: str,
    label: str,
    role: str = "",
    text: Optional[str] = None,
    children: Optional[list[dict[str, Any]]] = None,
    verification: Optional[dict[str, Any]] = None,
    **axis_attrs: Any,
) -> dict[str, Any]:
    """Build a single Thought Tree node with the canonical graph-
    identity fields per Codex's UI audit:
        node_key = kind + role + normalized_label + axis_attrs

    Returns a JSON-serializable dict the UI can consume directly.
    """
    node: dict[str, Any] = {
        "kind": kind,
        "role": role,
        "label": label,
        "normalized_label": label.strip().lower() if label else "",
    }
    if text is not None:
        node["text"] = text
    if axis_attrs:
        node["axis_attrs"] = axis_attrs
    if verification:
        node["verification"] = verification
    node["children"] = children or []
    return node


def _node_verification(report: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Return the runtime Verification Stack block for the generation node.

    Stage 21C producer linkage: the Atlas drawer opens only when a
    thought-tree node carries ``verification.evidence_packet_trace_id``.
    The source report may provide that id either inside the verification
    block or as a top-level ``evidence_packet_trace_id``. This helper
    merges the two without inventing verdicts.

    No gold labels are used here. The function only forwards runtime
    Stack fields already present on the report.
    """
    raw = report.get("verification")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    verification = dict(raw)
    trace_id = verification.get("evidence_packet_trace_id") or report.get(
        "evidence_packet_trace_id"
    )
    if isinstance(trace_id, str) and trace_id:
        verification["evidence_packet_trace_id"] = trace_id
    return verification


def _identifier_node(
    identifier: str,
    status: str,
    input_position: Optional[int],
    output_position: Optional[int],
) -> dict[str, Any]:
    """Build an identifier_attempt node. status ∈ {'copied', 'missed'}."""
    return _node(
        kind="identifier_attempt",
        role=status,
        label=identifier,
        input_position=input_position,
        output_position=output_position,
        status=status,
    )


def _slot_pattern_node(slot_summary: dict[str, Any]) -> dict[str, Any]:
    """Summary of the slot trace as a tree node. Compresses the per-
    position trace to a single descriptive node so the UI doesn't have
    to render hundreds of dots; per-position detail lives in the
    traceability_v0 trace's raw_trace field."""
    length = slot_summary.get("length", 0) or 0
    longest = slot_summary.get("longest_stage_var_run", 0) or 0
    counts = slot_summary.get("counts", {}) or {}
    stage_var_count = int(counts.get("2", 0)) if isinstance(counts, dict) else 0
    if length <= 0:
        label = "no tokens generated"
    elif longest >= 5:
        label = f"long identifier sequence ({longest} positions)"
    elif longest >= 1 or stage_var_count >= 1:
        label = f"recognized {stage_var_count} identifier position(s)"
    else:
        label = "only joining words generated"
    return _node(
        kind="slot_pattern",
        role="summary",
        label=label,
        length=length,
        longest_stage_var_run=longest,
        stage_var_count=stage_var_count,
    )


def _confidence_node(plain: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Build a confidence marker IF the plain-english layer surfaces
    a caveat or a non-strong qualitative band. Returns None if confidence
    is strong + no caveat — no need to clutter the tree."""
    band = plain.get("qualitative_coverage")
    caveat = plain.get("confidence_caveat")
    if band == "strong" and not caveat:
        return None
    label_parts = []
    if band:
        label_parts.append(f"coverage: {band}")
    if caveat:
        label_parts.append("caveat present")
    return _node(
        kind="confidence_marker",
        role=band or "unknown",
        label=" — ".join(label_parts) if label_parts else "uncertain",
        caveat=caveat,
        band=band,
    )


def _expected_identifier_positions(
    expected: list[str], emitted: list[str],
) -> dict[str, tuple[Optional[int], Optional[int]]]:
    """For each expected identifier, find its first input position and
    first output position. Inputs are listed in the order the
    cas-explain pipeline emits in `identifiers.expected`; outputs are
    in `identifiers.emitted`. Returns mapping identifier → (input_pos,
    output_pos), with None where unmatched."""
    out: dict[str, tuple[Optional[int], Optional[int]]] = {}
    for ident in expected:
        in_pos: Optional[int] = None
        for i, e in enumerate(expected):
            if e == ident:
                in_pos = i
                break
        out_pos: Optional[int] = None
        for j, e in enumerate(emitted):
            if e == ident:
                out_pos = j
                break
        out[ident] = (in_pos, out_pos)
    return out


def _canonical_node_key(node: dict[str, Any]) -> str:
    """Build the canonical graph-identity key per Codex audit `f3f59fa`:
    `node_key = kind + role + normalized_label + axis_attrs`.

    Two nodes with the same canonical key represent the same idea
    across renders — the future Thought Tree / Idea Atlas uses this
    to recognize "this is the same identifier" / "this is the same
    decision" across utterances, sessions, and replays.

    Stable serialization: axis_attrs is sorted by key so the same
    semantic content always produces the same string. Pipe-separated
    to avoid collision with field content.
    """
    parts = [
        str(node.get("kind") or ""),
        str(node.get("role") or ""),
        str(node.get("normalized_label") or ""),
    ]
    axis = node.get("axis_attrs") or {}
    if isinstance(axis, dict) and axis:
        axis_parts = [
            f"{k}={axis[k]}" for k in sorted(axis.keys())
        ]
        parts.append(",".join(axis_parts))
    else:
        parts.append("")
    return "|".join(parts)


def _canonical_edge_key(
    source_key: str, target_key: str, kind: str, label: str = "",
) -> str:
    """Build the canonical edge key per Codex audit `f3f59fa`:
    `edge_key = source_key + target_key + kind + label`.

    Same semantic edge produces the same key across renders, so the
    UI can dedupe edges when merging traces from multiple turns into
    the session-level Atlas.
    """
    return "|".join([source_key, target_key, kind, label])


def _flatten(root: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Depth-first traversal producing flat `nodes` + `edges` arrays
    alongside the nested tree. Each node gets a stable `id` (n0, n1,
    n2 in DFS order) AND a canonical `node_key` per Codex audits
    `f3f59fa` (graph identity scheme) + `7926698` (keys must live in
    the trace, not be UI-derived).

    Per-record id vs canonical key:
    - `id` (n0, n1, …) is stable within ONE trace, used for edge
      source/target pointers and per-render display.
    - `node_key` (kind+role+normalized_label+axis_attrs) is stable
      ACROSS renders, used by the future Atlas to recognize the same
      idea seen in different traces/sessions.
    """
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    counter = {"n": 0, "e": 0}

    def _walk(node: dict[str, Any], parent_id: Optional[str],
              parent_key: Optional[str]) -> tuple[str, str]:
        node_id = f"n{counter['n']}"
        counter["n"] += 1
        node_key = _canonical_node_key(node)
        # Copy the visible fields; omit `children` from the flat record
        # since edges encode parent→child.
        flat = {
            "id": node_id,
            "node_key": node_key,
            "kind": node.get("kind"),
            "role": node.get("role"),
            "label": node.get("label"),
            "normalized_label": node.get("normalized_label"),
        }
        if "text" in node:
            flat["text"] = node["text"]
        if "axis_attrs" in node:
            flat["axis_attrs"] = node["axis_attrs"]
        if "verification" in node:
            flat["verification"] = node["verification"]
        nodes.append(flat)
        # Stamp id + node_key onto the nested node so the two views
        # agree and the Atlas can use either view consistently.
        node["id"] = node_id
        node["node_key"] = node_key
        if parent_id is not None and parent_key is not None:
            edge_id = f"e{counter['e']}"
            counter["e"] += 1
            edge_kind = "parent_child"
            edges.append({
                "id": edge_id,
                "edge_key": _canonical_edge_key(
                    parent_key, node_key, edge_kind, label="",
                ),
                "source": parent_id,
                "target": node_id,
                "source_key": parent_key,
                "target_key": node_key,
                "kind": edge_kind,
            })
        for child in node.get("children", []) or []:
            _walk(child, node_id, node_key)
        return node_id, node_key

    _walk(root, None, None)
    return nodes, edges


def build_thought_tree(report: dict[str, Any]) -> dict[str, Any]:
    """Build the JSON-ready Thought Tree from a cas-explain report.

    Args:
        report: the dict produced by `cas_cli._cmd_explain` (must
            contain `input_cas_expression`, `generated_english`,
            `identifiers`, `slot_summary`, `plain_english`).

    Returns:
        Dict with:
          - `root`: nested tree for display (cards, indentation)
          - `nodes`: flat list of node objects with stable ids (for
            graph algorithms, force-directed layout, queries)
          - `edges`: flat list of edge objects linking ids (parent→child)
          - `node_count`, `edge_count`: integers
        JSON-serializable. The UI's `dashboard/src/lib/casGraph/`
        consumer translates this into canonical graph-identity records
        per Codex `f3f59fa`. Flat `nodes` + `edges` per Codex `95fcecf`.
    """
    cas_expression = report.get("input_cas_expression") or ""
    generated = report.get("generated_english") or ""
    idents = report.get("identifiers", {}) or {}
    expected = list(idents.get("expected", []) or [])
    emitted = list(idents.get("emitted", []) or [])
    copied_set = set(idents.get("copied", []) or [])
    slot_summary = report.get("slot_summary", {}) or {}
    plain = report.get("plain_english", {}) or {}
    verification = _node_verification(report)

    # identifier_attempt children of model_generation — Nth-occurrence
    # semantics so repeats become separate entries with distinct output
    # positions (per Codex audit `95fcecf`).
    used_emitted: dict[str, list[int]] = {}
    for j, e in enumerate(emitted):
        used_emitted.setdefault(e, []).append(j)
    cursor: dict[str, int] = {}
    ident_children: list[dict[str, Any]] = []
    for in_pos, ident in enumerate(expected):
        positions = used_emitted.get(ident, [])
        next_idx = cursor.get(ident, 0)
        if next_idx < len(positions):
            out_pos: Optional[int] = positions[next_idx]
            cursor[ident] = next_idx + 1
            status = "copied"
        else:
            out_pos = None
            status = "missed" if ident not in copied_set else "missed"
        ident_children.append(
            _identifier_node(ident, status, in_pos, out_pos)
        )

    # model_generation children: identifier attempts + slot pattern + confidence
    gen_children: list[dict[str, Any]] = list(ident_children)
    gen_children.append(_slot_pattern_node(slot_summary))
    conf_node = _confidence_node(plain)
    if conf_node is not None:
        gen_children.append(conf_node)

    gen_node = _node(
        kind="model_generation",
        role="output",
        label=plain.get("short_answer") or "model output",
        text=generated,
        children=gen_children,
        verification=verification,
    )

    root = _node(
        kind="user_prompt",
        role="input",
        label=cas_expression[:80] + ("..." if len(cas_expression) > 80 else ""),
        text=cas_expression,
        children=[gen_node],
    )

    flat_nodes, flat_edges = _flatten(root)

    return {
        "root": root,
        "nodes": flat_nodes,
        "edges": flat_edges,
        "node_count": count_nodes(root),
        "edge_count": count_edges(root),
    }


def count_nodes(node: dict[str, Any]) -> int:
    """Total nodes in the tree rooted at `node`, inclusive."""
    if not isinstance(node, dict):
        return 0
    n = 1
    for child in node.get("children", []) or []:
        n += count_nodes(child)
    return n


def count_edges(node: dict[str, Any]) -> int:
    """Total parent→child edges in the tree."""
    if not isinstance(node, dict):
        return 0
    children = node.get("children", []) or []
    return len(children) + sum(count_edges(c) for c in children)
