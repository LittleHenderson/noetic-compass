"""Structural diagram diff and similarity scoring for the CAS-SDG-Bench tri-channel benchmark.

Compares two compiler diagram dicts (as produced by ``build_diagram`` /
``CompilationArtifact.diagram()``) and produces diagnostic-grade similarity
scores beyond a bare equality check.

All functions are pure (no mutation, no I/O) and operate on plain Python dicts.
No numpy, torch, or other heavy dependencies — stdlib only, plus the sibling
``diagram_graph`` module for canonical identity.

Color fields (``"color": "#rrggbb"`` on nodes) are handled in a
forward-compatible way: functions tolerate their absence silently and activate
color-specific metrics only when the diagram carries sufficient color coverage.
This allows the palette compiler (PR #9) to land independently.
"""

from __future__ import annotations

import json

from .diagram_graph import (
    canonical_node_key,
    canonical_container_key,
    canonical_graph_keys,
    diagram_summary,
    extract_node_axes,
)


# ---------------------------------------------------------------------------
# Set diff
# ---------------------------------------------------------------------------

def diagram_set_diff(predicted: dict, ground_truth: dict) -> dict:
    """Symmetric set diff of nodes, containers, and edges between two diagrams.

    Uses ``canonical_node_key`` / ``canonical_container_key`` from
    ``diagram_graph`` for element identity, so auto-generated ``id`` fields
    and emission order do not affect the result.

    Returns::

        {
            "nodes_added":       list[str],   # in predicted, absent from GT
            "nodes_removed":     list[str],   # in GT, absent from predicted
            "nodes_common":      list[str],   # in both
            "containers_added":  list[str],
            "containers_removed":list[str],
            "containers_common": list[str],
            "edges_added":       list[str],
            "edges_removed":     list[str],
            "edges_common":      list[str],
        }

    All lists are sorted for deterministic output.
    """
    gt_keys = canonical_graph_keys(ground_truth)
    pred_keys = canonical_graph_keys(predicted)

    gt_nodes = set(gt_keys["node_keys"])
    pred_nodes = set(pred_keys["node_keys"])
    gt_containers = set(gt_keys["container_keys"])
    pred_containers = set(pred_keys["container_keys"])
    gt_edges = set(gt_keys["edge_keys"])
    pred_edges = set(pred_keys["edge_keys"])

    return {
        "nodes_added": sorted(pred_nodes - gt_nodes),
        "nodes_removed": sorted(gt_nodes - pred_nodes),
        "nodes_common": sorted(gt_nodes & pred_nodes),
        "containers_added": sorted(pred_containers - gt_containers),
        "containers_removed": sorted(gt_containers - pred_containers),
        "containers_common": sorted(gt_containers & pred_containers),
        "edges_added": sorted(pred_edges - gt_edges),
        "edges_removed": sorted(gt_edges - pred_edges),
        "edges_common": sorted(gt_edges & pred_edges),
    }


# ---------------------------------------------------------------------------
# Axis substitution counts
# ---------------------------------------------------------------------------

def _substitution_pairs(
    removed: list[dict],
    added: list[dict],
    target_axis: str,
    other_axes: tuple[str, ...],
) -> dict:
    """Count ``(gt_value, pred_value)`` pairs for ``target_axis`` where all
    ``other_axes`` match exactly between a removed GT node and an added
    predicted node of the same ``kind`` and ``role``.

    Only nodes that carry parseable values for ``target_axis`` (via
    ``extract_node_axes``) participate.  Returns a dict with string
    representation of the tuple key, e.g. ``"(3, 5)"``, so the result is
    directly JSON-serializable.
    """
    counts: dict[str, int] = {}
    for gt_node in removed:
        gt_axes = extract_node_axes(gt_node)
        if target_axis not in gt_axes:
            continue
        gt_val = gt_axes[target_axis]
        gt_others = {ax: gt_axes.get(ax) for ax in other_axes}
        gt_kind = gt_node.get("kind")
        gt_role = gt_node.get("role")

        for pred_node in added:
            if pred_node.get("kind") != gt_kind or pred_node.get("role") != gt_role:
                continue
            pred_axes = extract_node_axes(pred_node)
            if target_axis not in pred_axes:
                continue
            pred_val = pred_axes[target_axis]
            if pred_val == gt_val:
                continue
            pred_others = {ax: pred_axes.get(ax) for ax in other_axes}
            if pred_others == gt_others:
                key = str((gt_val, pred_val))
                counts[key] = counts.get(key, 0) + 1

    return counts


def _color_substitution_pairs(
    removed: list[dict],
    added: list[dict],
) -> dict:
    """Count ``(gt_color, pred_color)`` pairs for nodes where kind+role match
    and the color field differs.  Nodes without a ``color`` field are skipped.
    """
    counts: dict[str, int] = {}
    for gt_node in removed:
        gt_color = gt_node.get("color")
        if gt_color is None:
            continue
        gt_kind = gt_node.get("kind")
        gt_role = gt_node.get("role")
        gt_axes = extract_node_axes(gt_node)

        for pred_node in added:
            if pred_node.get("kind") != gt_kind or pred_node.get("role") != gt_role:
                continue
            pred_color = pred_node.get("color")
            if pred_color is None or pred_color == gt_color:
                continue
            # All structural axes must match for this to be a color-only substitution.
            pred_axes = extract_node_axes(pred_node)
            if pred_axes == gt_axes:
                key = str((gt_color, pred_color))
                counts[key] = counts.get(key, 0) + 1

    return counts


def diagram_axis_substitution_counts(predicted: dict, ground_truth: dict) -> dict:
    """Count per-axis substitutions between two diagrams.

    A substitution on axis X occurs when a GT node is absent from the predicted
    diagram while a structurally similar predicted node is added — with all
    axes other than X matching, but X differing.

    Returns::

        {
            "noetic_substitutions":   {str: int},  # e.g. {"(4, 5)": 12}
            "domain_substitutions":   {str: int},
            "drive_substitutions":    {str: int},
            "register_substitutions": {str: int},
            "color_substitutions":    {str: int},  # empty dict if no color metadata
        }

    All count dicts have string keys of the form ``"(gt_val, pred_val)"`` for
    JSON serializability.  ``color_substitutions`` is only populated when at
    least one diagram carries a ``color`` field on any node; otherwise an empty
    dict is returned (forward-compatible with PR #9 palette).
    """
    diff = diagram_set_diff(predicted, ground_truth)

    gt_by_key = {canonical_node_key(n): n for n in (ground_truth.get("nodes") or [])}
    pred_by_key = {canonical_node_key(n): n for n in (predicted.get("nodes") or [])}

    removed = [gt_by_key[k] for k in diff["nodes_removed"] if k in gt_by_key]
    added = [pred_by_key[k] for k in diff["nodes_added"] if k in pred_by_key]

    noetic_subs = _substitution_pairs(
        removed, added, "noetic", ("domain", "drive", "register")
    )
    domain_subs = _substitution_pairs(
        removed, added, "domain", ("noetic", "drive", "register")
    )
    drive_subs = _substitution_pairs(
        removed, added, "drive", ("noetic", "domain", "register")
    )
    register_subs = _substitution_pairs(
        removed, added, "register", ("noetic", "domain", "drive")
    )

    # Color: forward-compatible — only populated when color metadata is present.
    all_gt_nodes = ground_truth.get("nodes") or []
    all_pred_nodes = predicted.get("nodes") or []
    has_color = any("color" in n for n in all_gt_nodes) or any(
        "color" in n for n in all_pred_nodes
    )
    color_subs = _color_substitution_pairs(removed, added) if has_color else {}

    return {
        "noetic_substitutions": noetic_subs,
        "domain_substitutions": domain_subs,
        "drive_substitutions": drive_subs,
        "register_substitutions": register_subs,
        "color_substitutions": color_subs,
    }


# ---------------------------------------------------------------------------
# Similarity score
# ---------------------------------------------------------------------------

def _safe_rate(numerator: int, denominator: int, empty_value: float = 1.0) -> float:
    """Return ``numerator / denominator``, or ``empty_value`` when denominator is zero."""
    if denominator == 0:
        return empty_value
    return numerator / denominator


def _color_match_rate(
    predicted: dict,
    ground_truth: dict,
    common_node_keys: list[str],
    gt_by_key: dict,
    pred_by_key: dict,
) -> float | None:
    """Return the color match rate for common nodes, or ``None``.

    Returns ``None`` unless both diagrams carry ``color`` on >= 50 % of their
    nodes, in line with the forward-compatibility contract for PR #9.
    """
    gt_nodes = ground_truth.get("nodes") or []
    pred_nodes = predicted.get("nodes") or []
    if not gt_nodes or not pred_nodes:
        return None

    gt_color_frac = sum(1 for n in gt_nodes if "color" in n) / len(gt_nodes)
    pred_color_frac = sum(1 for n in pred_nodes if "color" in n) / len(pred_nodes)
    if gt_color_frac < 0.5 or pred_color_frac < 0.5:
        return None

    match = total = 0
    for key in common_node_keys:
        gt_n = gt_by_key.get(key)
        pred_n = pred_by_key.get(key)
        if gt_n is None or pred_n is None:
            continue
        total += 1
        if gt_n.get("color") == pred_n.get("color"):
            match += 1

    return _safe_rate(match, total)


def diagram_similarity_score(predicted: dict, ground_truth: dict) -> dict:
    """Produce similarity dimensions for two diagrams.

    Returns::

        {
            "structural_match_rate":  float,       # |common nodes| / max(|GT|, |pred|)
            "edge_match_rate":        float,        # same for edges
            "axis_value_match_rate":  float,        # of common nodes, fraction with identical axes
            "exact_graph_hash_match": bool,
            "containers_match_rate":  float,
            "color_match_rate":       float | None, # None when color coverage < 50 %
        }

    All rates are in ``[0.0, 1.0]``.  Empty diagrams on both sides yield 1.0
    (identical) rather than NaN.
    """
    diff = diagram_set_diff(predicted, ground_truth)
    gt_summary = diagram_summary(ground_truth)
    pred_summary = diagram_summary(predicted)

    # --- structural_match_rate (nodes) ---
    n_common = len(diff["nodes_common"])
    structural_match_rate = _safe_rate(
        n_common, max(gt_summary["node_count"], pred_summary["node_count"])
    )

    # --- edge_match_rate ---
    e_common = len(diff["edges_common"])
    edge_match_rate = _safe_rate(
        e_common, max(gt_summary["edge_count"], pred_summary["edge_count"])
    )

    # --- containers_match_rate ---
    c_common = len(diff["containers_common"])
    containers_match_rate = _safe_rate(
        c_common, max(gt_summary["container_count"], pred_summary["container_count"])
    )

    # --- axis_value_match_rate ---
    # For nodes that share the same canonical key (structurally matched),
    # check whether their axis metadata also matches.  If neither node carries
    # parseable axis info, the pair is counted as matching (trivially correct).
    gt_by_key = {canonical_node_key(n): n for n in (ground_truth.get("nodes") or [])}
    pred_by_key = {canonical_node_key(n): n for n in (predicted.get("nodes") or [])}

    axis_match = axis_total = 0
    for key in diff["nodes_common"]:
        gt_n = gt_by_key.get(key)
        pred_n = pred_by_key.get(key)
        if gt_n is None or pred_n is None:
            continue
        axis_total += 1
        gt_axes = extract_node_axes(gt_n)
        pred_axes = extract_node_axes(pred_n)
        if gt_axes == pred_axes:
            axis_match += 1

    axis_value_match_rate = _safe_rate(axis_match, axis_total)

    # --- exact_graph_hash_match ---
    exact_graph_hash_match = gt_summary["graph_hash"] == pred_summary["graph_hash"]

    # --- color_match_rate (forward-compatible) ---
    color_rate = _color_match_rate(
        predicted, ground_truth, diff["nodes_common"], gt_by_key, pred_by_key
    )

    return {
        "structural_match_rate": structural_match_rate,
        "edge_match_rate": edge_match_rate,
        "axis_value_match_rate": axis_value_match_rate,
        "exact_graph_hash_match": exact_graph_hash_match,
        "containers_match_rate": containers_match_rate,
        "color_match_rate": color_rate,
    }


# ---------------------------------------------------------------------------
# Headline diagnostic report
# ---------------------------------------------------------------------------

def diagram_diff_report(predicted: dict, ground_truth: dict) -> dict:
    """Combine all diagnostic information into a single JSON-serializable dict.

    Suitable for logging, serialising to JSONL alongside benchmark results, or
    surfacing in a dashboard.  Contains no numpy types, no Python sets, and no
    tuple keys — all values are plain Python scalars, lists, or dicts.

    Returns::

        {
            "ground_truth_summary": {...},   # from diagram_summary
            "predicted_summary":    {...},
            "set_diff":             {...},   # from diagram_set_diff
            "axis_substitutions":   {...},   # from diagram_axis_substitution_counts
            "similarity":           {...},   # from diagram_similarity_score
        }
    """
    set_diff = diagram_set_diff(predicted, ground_truth)
    axis_subs = diagram_axis_substitution_counts(predicted, ground_truth)
    similarity = diagram_similarity_score(predicted, ground_truth)
    gt_summary = diagram_summary(ground_truth)
    pred_summary = diagram_summary(predicted)

    return {
        "ground_truth_summary": gt_summary,
        "predicted_summary": pred_summary,
        "set_diff": set_diff,
        "axis_substitutions": axis_subs,
        "similarity": similarity,
    }
