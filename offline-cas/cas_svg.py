"""Dependency-free SVG renderer for CAS compiler diagram payloads.

The renderer mirrors the dashboard's current visual families without pulling in
React or browser code. It consumes the `artifact.diagram()` dict emitted by the
Python compiler and returns a standalone SVG string.
"""

from __future__ import annotations

from collections import defaultdict, deque
from html import escape
import math
from typing import Any


W = 920
H = 560
ATOM_R = 21


def _color(kind: str) -> str:
    if "cluster" in kind or kind == "meta_set":
        return "#14b8a6"
    if kind == "state":
        return "#38bdf8"
    if kind == "noetic":
        return "#22d3ee"
    if kind == "drive":
        return "#f59e0b"
    if kind == "domain":
        return "#34d399"
    if kind == "register":
        return "#f472b6"
    if kind in {"foundation", "subfoundation"}:
        return "#fbbf24"
    if kind in {"call", "operator"}:
        return "#c084fc"
    if kind in {"production_target", "emergent"}:
        return "#a78bfa"
    return "#94a3b8"


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_") or "item"


def _label(value: str, max_len: int = 28) -> str:
    return value if len(value) <= max_len else value[: max_len - 1] + "..."


def _rect_w(label: str) -> float:
    return max(58.0, min(240.0, len(_label(label)) * 7.0 + 28.0))


def _layout_family(layouts: list[str], diagram: dict[str, Any]) -> str:
    if "grid" in layouts:
        return "grid"
    if "petals" in layouts:
        return "petals"
    if "fractal" in layouts:
        return "fractal"
    if diagram.get("containers") and ("containment" in layouts or "topos" in layouts):
        return "containment"
    if "recipe" in layouts or "dependency" in layouts:
        return "dependency"
    return "radial"


def _display_items(diagram: dict[str, Any]) -> list[dict[str, Any]]:
    containers = [
        {
            "id": c["id"],
            "kind": c.get("kind", "meta_set"),
            "label": f"{c.get('label', c['id'])}{f' ({c.get('cardinality')})' if isinstance(c.get('cardinality'), int) else ''}",
            "role": c.get("element_type"),
            "container": True,
        }
        for c in diagram.get("containers", [])
    ]
    nodes = [dict(n, container=False) for n in diagram.get("nodes", [])]
    return (containers + nodes)[:72]


def _radial(items: list[dict[str, Any]]) -> tuple[dict[str, tuple[float, float]], dict[str, Any]]:
    pos: dict[str, tuple[float, float]] = {}
    containers = [it for it in items if it.get("container")]
    atoms = [it for it in items if not it.get("container")]
    if containers:
        gap = W / (len(containers) + 1)
        for i, item in enumerate(containers, 1):
            pos[item["id"]] = (gap * i, 48)
    cx, cy = W / 2, H / 2 + 36
    r = min(W, H) * 0.31
    offset = math.pi / max(len(atoms), 1)
    for i, item in enumerate(atoms):
        a = math.tau * i / max(len(atoms), 1) - math.pi / 2 + offset
        pos[item["id"]] = (cx + math.cos(a) * r, cy + math.sin(a) * r)
    return pos, {}


def _dependency(items: list[dict[str, Any]], edges: list[dict[str, Any]]) -> tuple[dict[str, tuple[float, float]], dict[str, Any]]:
    ids = {it["id"] for it in items}
    incoming: dict[str, list[str]] = {item["id"]: [] for item in items}
    outgoing: dict[str, list[str]] = {item["id"]: [] for item in items}
    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        if source in ids and target in ids:
            incoming[target].append(source)
            outgoing[source].append(target)
    rank: dict[str, int] = {}
    q: deque[str] = deque()
    for item_id in ids:
        if not incoming[item_id]:
            rank[item_id] = 0
            q.append(item_id)
    while q:
        item_id = q.popleft()
        for target in outgoing[item_id]:
            new_rank = rank[item_id] + 1
            if target not in rank or rank[target] < new_rank:
                rank[target] = new_rank
                q.append(target)
    for item_id in ids:
        rank.setdefault(item_id, 0)
    lanes: dict[int, list[str]] = defaultdict(list)
    for item_id, r in rank.items():
        lanes[r].append(item_id)
    ranks = sorted(lanes)
    pos: dict[str, tuple[float, float]] = {}
    for i, r in enumerate(ranks):
        lane = lanes[r]
        x = 90 if len(ranks) == 1 else 90 + i * ((W - 180) / (len(ranks) - 1))
        for j, item_id in enumerate(lane):
            y = 72 + (j + 0.5) * ((H - 144) / max(len(lane), 1))
            pos[item_id] = (x, y)
    return pos, {}


def _containment(
    items: list[dict[str, Any]],
    containers: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> tuple[dict[str, tuple[float, float]], dict[str, Any]]:
    pos: dict[str, tuple[float, float]] = {}
    regions: dict[str, tuple[float, float, float, float]] = {}
    point_members: set[str] = set()
    contained_in: dict[str, str] = {}
    container_ids = {c["id"] for c in containers}
    for c in containers:
        for child in c.get("contains", []):
            contained_in[child] = c["id"]
    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        label = (edge.get("label") or "").strip()
        if source not in container_ids or target not in container_ids:
            continue
        if label in {"⊆", "⊂"}:
            contained_in.setdefault(source, target)
        elif label in {"⊇", "⊃"}:
            contained_in.setdefault(target, source)
        elif label == "∈":
            point_members.add(source)
            contained_in.setdefault(source, target)

    roots = [c for c in containers if c["id"] not in contained_in]
    if not roots:
        return _radial(items)
    outer = max(roots, key=lambda c: len(c.get("contains", [])))
    by_id = {c["id"]: c for c in containers}
    child_containers: dict[str, list[str]] = defaultdict(list)
    for child, parent in contained_in.items():
        if child in container_ids:
            child_containers[parent].append(child)

    def atoms_for(container_id: str, seen: set[str] | None = None) -> set[str]:
        seen = seen or set()
        if container_id in seen:
            return set()
        seen.add(container_id)
        atom_ids: set[str] = set()
        c = by_id.get(container_id, {})
        for child in c.get("contains", []):
            if child in container_ids:
                atom_ids |= atoms_for(child, seen)
            else:
                atom_ids.add(child)
        for child in child_containers.get(container_id, []):
            atom_ids |= atoms_for(child, seen)
        return atom_ids

    cx, cy, r = W / 2, H / 2 + 18, min(W, H) * 0.31
    outer_atoms = atoms_for(outer["id"])
    atom_items = [it for it in items if not it.get("container") and it["id"] in outer_atoms]
    for i, item in enumerate(atom_items):
        a = math.tau * i / max(len(atom_items), 1) - math.pi / 2
        pos[item["id"]] = (cx + math.cos(a) * r, cy + math.sin(a) * r)
    pos[outer["id"]] = (cx, cy)
    regions[outer["id"]] = (cx, cy, r + 42, r + 42)
    for c in containers:
        if c["id"] == outer["id"]:
            continue
        member_pos = [pos[mid] for mid in atoms_for(c["id"]) if mid in pos]
        if member_pos:
            xs = [p[0] for p in member_pos]
            ys = [p[1] for p in member_pos]
            icx, icy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            rx = max((max(xs) - min(xs)) / 2 + 34, 72)
            ry = max((max(ys) - min(ys)) / 2 + 34, 42)
        else:
            icx, icy, rx, ry = cx, cy, 72, 42
        pos[c["id"]] = (icx, icy - ry - 12)
        regions[c["id"]] = (icx, icy, rx, ry)
    for item in items:
        if item["id"] not in pos:
            pos[item["id"]] = (W - 78 - len(pos) % 8 * 58, H - 42)
    return pos, {"regions": regions, "point_members": point_members}


def _grid(items: list[dict[str, Any]], containers: list[dict[str, Any]]) -> tuple[dict[str, tuple[float, float]], dict[str, Any]]:
    pos: dict[str, tuple[float, float]] = {}
    rows = sorted(
        [it for it in items if it.get("kind") == "noetic"],
        key=lambda it: int("".join(ch for ch in it["label"] if ch.isdigit()) or "0"),
    )
    cols = sorted(
        [it for it in items if it.get("kind") == "domain"],
        key=lambda it: "PCEO".find(it["label"]) if it["label"] in "PCEO" else 99,
    )
    x0, y0 = 220.0, 90.0
    cell_w = (W - x0 - 70) / max(len(cols), 1)
    cell_h = (H - y0 - 58) / max(len(rows), 1)
    for i, row in enumerate(rows):
        pos[row["id"]] = (x0 - 58, y0 + cell_h * (i + 0.5))
    for i, col in enumerate(cols):
        pos[col["id"]] = (x0 + cell_w * (i + 0.5), y0 - 34)
    for c in containers:
        if c.get("element_type") == "noetic":
            pos[c["id"]] = (x0 - 58, 36)
        elif c.get("element_type") == "domain":
            pos[c["id"]] = (x0 + cell_w * max(len(cols), 1) / 2, 36)
    for item in items:
        if item["id"] not in pos and item.get("kind") == "call":
            pos[item["id"]] = (W - 116, H - 38)
    return pos, {"grid": (x0, y0, cell_w, cell_h, len(rows), len(cols))}


def _petals(
    items: list[dict[str, Any]],
    containers: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> tuple[dict[str, tuple[float, float]], dict[str, Any]]:
    pos: dict[str, tuple[float, float]] = {}
    base_edges = [e for e in edges if e.get("kind") in {"cover_base", "partition_base"}]
    member_edges = [e for e in edges if e.get("kind") in {"cover_member", "partition_member"}]
    base_id = base_edges[0]["source"] if base_edges else None
    by_id = {c["id"]: c for c in containers}
    members = [by_id[e["source"]] for e in member_edges if e.get("source") in by_id]
    if not members:
        members = [c for c in containers if c["id"] != base_id]
    cx, cy, inner_r, outer_r = W / 2, H / 2 + 8, 58.0, min(W, H) * 0.37
    if base_id:
        pos[base_id] = (cx, cy)
    sectors = []
    for i, c in enumerate(members):
        start = -math.pi / 2 + math.tau * i / max(len(members), 1)
        end = -math.pi / 2 + math.tau * (i + 1) / max(len(members), 1)
        mid = (start + end) / 2
        sectors.append((c["id"], c["label"], _color(c.get("kind", "")), start, end))
        pos[c["id"]] = (cx + math.cos(mid) * (outer_r + 34), cy + math.sin(mid) * (outer_r + 34))
        for j, child in enumerate(c.get("contains", [])):
            spread = (j - (len(c.get("contains", [])) - 1) / 2) * ((end - start) * 0.16)
            rr = inner_r + (outer_r - inner_r) * (0.5 + 0.1 * (j % 2))
            pos[child] = (cx + math.cos(mid + spread) * rr, cy + math.sin(mid + spread) * rr)
    for item in items:
        if item["id"] not in pos and item.get("kind") == "call":
            pos[item["id"]] = (cx, cy)
    return pos, {"petals": (cx, cy, inner_r, outer_r, sectors)}


def _fractal(items: list[dict[str, Any]], edges: list[dict[str, Any]]) -> tuple[dict[str, tuple[float, float]], dict[str, Any]]:
    step_ids = {
        edge[key]
        for edge in edges
        if edge.get("kind") == "fractal_step"
        for key in ("source", "target")
        if edge.get(key)
    }
    ordered = [it for it in items if it.get("role") == "fractal_step" or it["id"] in step_ids]
    ordered.sort(key=lambda it: int(it.get("step") or 0))
    pos: dict[str, tuple[float, float]] = {}
    branches = []
    for i, item in enumerate(ordered):
        amp = max(34.0, 150.0 / (i + 1))
        x = W / 2 if i == 0 else W / 2 + (-1 if i % 2 else 1) * amp
        y = 66 + i * min(88, (H - 150) / max(len(ordered) - 1, 1))
        pos[item["id"]] = (x, y)
        if i < len(ordered) - 1:
            branches.append((x, y + 18, x - amp * 0.52, y + 48, 0.18))
            branches.append((x, y + 18, x + amp * 0.52, y + 48, 0.18))
    return pos, {"branches": branches}


def _layout(diagram: dict[str, Any], items: list[dict[str, Any]]) -> tuple[str, dict[str, tuple[float, float]], dict[str, Any]]:
    family = _layout_family(list(diagram.get("layouts", [])), diagram)
    containers = diagram.get("containers", [])
    edges = diagram.get("edges", [])
    if family == "grid":
        pos, extra = _grid(items, containers)
    elif family == "petals":
        pos, extra = _petals(items, containers, edges)
    elif family == "fractal":
        pos, extra = _fractal(items, edges)
    elif family == "containment":
        pos, extra = _containment(items, containers, edges)
    elif family == "dependency":
        pos, extra = _dependency(items, edges)
    else:
        pos, extra = _radial(items)
    return family, pos, extra


def _wedge(cx: float, cy: float, inner_r: float, outer_r: float, start: float, end: float) -> str:
    large = 1 if end - start > math.pi else 0
    p0 = (cx + math.cos(start) * outer_r, cy + math.sin(start) * outer_r)
    p1 = (cx + math.cos(end) * outer_r, cy + math.sin(end) * outer_r)
    p2 = (cx + math.cos(end) * inner_r, cy + math.sin(end) * inner_r)
    p3 = (cx + math.cos(start) * inner_r, cy + math.sin(start) * inner_r)
    return (
        f"M {p0[0]:.1f} {p0[1]:.1f} A {outer_r:.1f} {outer_r:.1f} 0 {large} 1 {p1[0]:.1f} {p1[1]:.1f} "
        f"L {p2[0]:.1f} {p2[1]:.1f} A {inner_r:.1f} {inner_r:.1f} 0 {large} 0 {p3[0]:.1f} {p3[1]:.1f} Z"
    )


def _clip(a: tuple[float, float], b: tuple[float, float], radius: float) -> tuple[float, float]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    dist = math.hypot(dx, dy)
    if not dist:
        return a
    return (a[0] + dx / dist * radius, a[1] + dy / dist * radius)


def render_svg(diagram: dict[str, Any], result: dict[str, Any] | None = None, title: str = "CAS Diagram") -> str:
    """Render a compiler diagram payload to standalone SVG."""
    items = _display_items(diagram)
    family, pos, extra = _layout(diagram, items)
    item_by_id = {item["id"]: item for item in items}
    if result is not None and not isinstance(result, dict):
        title = str(result)
        result = {}
    else:
        result = result or {}
    holds = result.get("holds") if result.get("kind") == "meta_assertion" else None
    edge_color = "#22c55e" if holds is True else "#ef4444" if holds is False else "#38bdf8"
    truth = " ✓" if holds is True else " ✗" if holds is False else ""
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(title)}">',
        "<defs>",
        '<filter id="soft"><feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#020617" flood-opacity="0.35"/></filter>',
        f'<marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="{edge_color}"/></marker>',
        "</defs>",
        '<rect width="100%" height="100%" rx="18" fill="#020617"/>',
        '<circle cx="100" cy="80" r="220" fill="#0f766e" opacity="0.10"/>',
        '<circle cx="850" cy="500" r="260" fill="#1d4ed8" opacity="0.10"/>',
        f'<text x="24" y="34" fill="#cbd5e1" font-family="ui-monospace, Consolas, monospace" font-size="14" font-weight="700">{escape(title)}</text>',
        f'<text x="24" y="54" fill="#64748b" font-family="ui-monospace, Consolas, monospace" font-size="11">layout: {escape(family)}</text>',
    ]

    if "grid" in extra:
        x0, y0, cw, ch, rows, cols = extra["grid"]
        parts.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{cw*cols:.1f}" height="{ch*rows:.1f}" rx="12" fill="#0f172a" stroke="#14b8a6" stroke-opacity="0.45"/>')
        for i in range(cols + 1):
            x = x0 + i * cw
            parts.append(f'<line x1="{x:.1f}" y1="{y0:.1f}" x2="{x:.1f}" y2="{y0+ch*rows:.1f}" stroke="#14b8a6" stroke-opacity="0.18"/>')
        for i in range(rows + 1):
            y = y0 + i * ch
            parts.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x0+cw*cols:.1f}" y2="{y:.1f}" stroke="#14b8a6" stroke-opacity="0.18"/>')
        for r in range(rows):
            for c in range(cols):
                parts.append(f'<circle cx="{x0+cw*(c+0.5):.1f}" cy="{y0+ch*(r+0.5):.1f}" r="2.2" fill="#67e8f9" opacity="0.34"/>')

    if "petals" in extra:
        cx, cy, inner_r, outer_r, sectors = extra["petals"]
        for _sid, label, color, start, end in sectors:
            parts.append(f'<path d="{_wedge(cx, cy, inner_r, outer_r, start+0.015, end-0.015)}" fill="{color}24" stroke="{color}" stroke-opacity="0.75" stroke-width="1.2"/>')
            mid = (start + end) / 2
            parts.append(f'<text x="{cx+math.cos(mid)*(outer_r+72):.1f}" y="{cy+math.sin(mid)*(outer_r+72):.1f}" text-anchor="middle" fill="#cbd5e1" font-size="10" font-family="ui-monospace, Consolas, monospace">{escape(_label(label, 14))}</text>')
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{inner_r-6:.1f}" fill="#020617" stroke="#38bdf8" stroke-opacity="0.55"/>')

    for x1, y1, x2, y2, opacity in extra.get("branches", []):
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#38bdf8" stroke-width="1" stroke-opacity="{opacity}"/>')

    for cid, region in extra.get("regions", {}).items():
        item = item_by_id.get(cid)
        if not item:
            continue
        cx, cy, rx, ry = region
        color = _color(item.get("kind", ""))
        parts.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{color}18" stroke="{color}" stroke-width="1.4" stroke-dasharray="5 4"/>')

    visible = set(pos)
    for edge in diagram.get("edges", [])[:80]:
        source, target = edge.get("source"), edge.get("target")
        if source not in visible or target not in visible:
            continue
        a, b = pos[source], pos[target]
        start = _clip(a, b, 24)
        end = _clip(b, a, 24)
        parts.append(f'<line x1="{start[0]:.1f}" y1="{start[1]:.1f}" x2="{end[0]:.1f}" y2="{end[1]:.1f}" stroke="{edge_color}" stroke-width="1.7" stroke-opacity="0.9" marker-end="url(#arrow)"/>')
        edge_label = edge.get("label")
        if edge_label:
            parts.append(f'<text x="{(start[0]+end[0])/2:.1f}" y="{(start[1]+end[1])/2-5:.1f}" text-anchor="middle" fill="{edge_color}" font-size="11" font-weight="700" font-family="ui-monospace, Consolas, monospace">{escape(str(edge_label) + truth)}</text>')

    point_members = extra.get("point_members", set())
    for item in items:
        if item["id"] not in pos:
            continue
        x, y = pos[item["id"]]
        color = _color(item.get("kind", ""))
        label = _label(str(item.get("label", item["id"])))
        if item.get("container") and item["id"] not in point_members:
            rw = _rect_w(label)
            parts.append(f'<g filter="url(#soft)"><rect x="{x-rw/2:.1f}" y="{y-15:.1f}" width="{rw:.1f}" height="30" rx="8" fill="#0d1117" stroke="{color}" stroke-width="1.2"/><text x="{x:.1f}" y="{y+4:.1f}" text-anchor="middle" fill="#f8fafc" font-size="10" font-weight="700" font-family="ui-monospace, Consolas, monospace">{escape(label)}</text></g>')
        else:
            r = 17 if item["id"] in point_members else ATOM_R
            parts.append(f'<g filter="url(#soft)"><circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}30" stroke="{color}" stroke-width="1.4"/><text x="{x:.1f}" y="{y+4:.1f}" text-anchor="middle" fill="#f8fafc" font-size="10" font-weight="700" font-family="ui-monospace, Consolas, monospace">{escape(_label(label, 8))}</text></g>')
    parts.append("</svg>")
    return "\n".join(parts)


def render_html(svg: str, title: str = "CAS Diagram") -> str:
    """Wrap an SVG string in a standalone offline HTML document."""
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>{escape(title)}</title>
<style>
  body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: #020617; color: #e2e8f0; }}
  main {{ width: min(96vw, 1100px); padding: 24px; }}
  svg {{ width: 100%; height: auto; box-shadow: 0 24px 80px rgba(0,0,0,.45); }}
</style>
<main>
{svg}
</main>
</html>
"""
