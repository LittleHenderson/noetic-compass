"""Render the canonical 2D notation map as a self-contained interactive HTML.

Reads the live ``canonical_layout_payload()`` from
``cas_native.atlas.notation_2d_map`` and emits an SVG-based visualization
with hover tooltips, a colour-coded legend, and no external dependencies.

The script is **count-agnostic**: whatever primitives the payload returns
at runtime — 157 today, 169 if the Ω_* group lands, more later — are
rendered without code change. Coordinates are pulled straight from the
payload; viewport auto-fits the data extent with a small padding.

Usage::

    python tools/visualize_notation_map.py
    python tools/visualize_notation_map.py --output path/to/out.html

The default output path is ``tools/notation_map_viz.html`` (committed
alongside this script so reviewers can open it without running anything).
"""
from __future__ import annotations

import argparse
import html
import json
import sys
import types
from pathlib import Path

# ── Package mapping ───────────────────────────────────────────────────
# The on-disk directory ``cas-native/`` is exposed under the importable
# name ``cas_native`` (mirrors cas-native/atlas/tests/conftest.py).
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
_CAS_NATIVE_DIR = _PROJECT_ROOT / "cas-native"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

if "cas_native" not in sys.modules:
    _pkg = types.ModuleType("cas_native")
    _pkg.__file__ = str(_CAS_NATIVE_DIR / "__init__.py")
    _pkg.__path__ = [str(_CAS_NATIVE_DIR)]
    sys.modules["cas_native"] = _pkg

from cas_native.atlas import notation_2d_map as nm  # noqa: E402


# ── Colour scheme ─────────────────────────────────────────────────────
#
# Sixteen distinguishable colours grouped by family so related kinds
# share a hue band:
#
#   Structural CAS (blues / indigos):
#     noetic, domain, drive, register, cognitive_state
#   Operational (oranges / reds):
#     operation, inversion_axis
#   Foundation grid (purples):
#     foundation
#   Production / RPM (warm yellows / browns):
#     production, rpm_pathway
#   Set primitives (greens):
#     set_constructor, set_relation, set_operation, combinator
#   Authority / cardinality (greys / teals):
#     authority_set, cardinality_kind
#
# Each value is a hex colour readable on a near-white background.
KIND_COLOR: dict[str, str] = {
    # Structural — blues
    "noetic":            "#1f3a93",  # deep blue
    "domain":            "#2e86de",  # mid blue
    "drive":             "#48dbfb",  # cyan
    "register":          "#5f27cd",  # indigo
    "cognitive_state":   "#54a0ff",  # light blue
    # Operational — reds / oranges
    "operation":         "#ee5253",  # red
    "inversion_axis":    "#ff9f43",  # orange
    # Foundation — purple
    "foundation":        "#9b59b6",  # purple
    # Production / RPM — warm
    "production":        "#f1c40f",  # gold
    "rpm_pathway":       "#a0522d",  # sienna
    # Set primitives — greens
    "set_constructor":   "#16a085",  # teal-green
    "set_relation":      "#27ae60",  # green
    "set_operation":     "#2ecc71",  # bright green
    "combinator":        "#7cb342",  # olive-green
    # Authority / cardinality — greys / teals
    "authority_set":     "#34495e",  # slate
    "cardinality_kind":  "#7f8c8d",  # cool grey
}

# Fallback for unknown kinds (e.g. if Agent E adds a new kind like
# "emergent_register" for the Ω_* group). Hot pink so it stands out
# visually and prompts the operator to update KIND_COLOR.
UNKNOWN_KIND_COLOR = "#ff1493"


# ── SVG / HTML generation ─────────────────────────────────────────────


def _viewport_from_primitives(
    primitives: list[dict],
    padding: float = 1.0,
) -> tuple[float, float, float, float]:
    """Compute (min_x, min_y, max_x, max_y) with padding."""
    if not primitives:
        # Degenerate fallback; render a 1×1 box centred on origin.
        return (-1.0, -1.0, 1.0, 1.0)
    xs = [p["x"] for p in primitives]
    ys = [p["y"] for p in primitives]
    return (
        min(xs) - padding,
        min(ys) - padding,
        max(xs) + padding,
        max(ys) + padding,
    )


def _kind_counts(primitives: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in primitives:
        counts[p["kind"]] = counts.get(p["kind"], 0) + 1
    return counts


def _render_html(payload: dict) -> str:
    """Build the self-contained HTML document."""
    layout_version = str(payload.get("layout_version", "unknown"))
    scope = str(payload.get("scope", ""))
    boundary = str(payload.get("boundary", ""))
    primitives: list[dict] = list(payload.get("primitives", []))  # type: ignore[arg-type]
    total = len(primitives)

    min_x, min_y, max_x, max_y = _viewport_from_primitives(primitives)
    # SVG y axis points DOWN; CAS layout has +y = up (e.g. Operations sit at
    # y=2.5, Production at y=5.5, RPM at y=-8..-9.5). Flip y when emitting.
    width_units = max_x - min_x
    height_units = max_y - min_y

    # Pixel scale: target ~1100px canvas width.
    scale = 1100.0 / width_units if width_units > 0 else 50.0
    svg_w = width_units * scale
    svg_h = height_units * scale
    radius_px = 5.5  # dot radius in screen px

    def to_screen(x: float, y: float) -> tuple[float, float]:
        sx = (x - min_x) * scale
        # Flip y so +y CAS space points up on screen.
        sy = (max_y - y) * scale
        return (sx, sy)

    # ── Dots ──
    dot_lines: list[str] = []
    counts = _kind_counts(primitives)
    for p in primitives:
        prim_id = str(p["primitive"])
        kind = str(p["kind"])
        x_f = float(p["x"])
        y_f = float(p["y"])
        cx, cy = to_screen(x_f, y_f)
        color = KIND_COLOR.get(kind, UNKNOWN_KIND_COLOR)
        title = f"{prim_id}  [{kind}]  ({x_f:.3f}, {y_f:.3f})"
        dot_lines.append(
            "<circle "
            f'class="dot" '
            f'data-id="{html.escape(prim_id, quote=True)}" '
            f'data-kind="{html.escape(kind, quote=True)}" '
            f'data-x="{x_f:.3f}" data-y="{y_f:.3f}" '
            f'cx="{cx:.2f}" cy="{cy:.2f}" r="{radius_px:.2f}" '
            f'fill="{color}" stroke="#222" stroke-width="0.5">'
            f"<title>{html.escape(title)}</title>"
            "</circle>"
        )

    # ── Axes (lightweight reference cross at origin) ──
    origin_sx, origin_sy = to_screen(0.0, 0.0)
    axis_lines = [
        # Vertical line at x=0 of CAS space
        f'<line x1="{origin_sx:.2f}" y1="0" x2="{origin_sx:.2f}" y2="{svg_h:.2f}" '
        'stroke="#e3e6ea" stroke-width="1" stroke-dasharray="4 4"/>',
        # Horizontal line at y=0 of CAS space
        f'<line x1="0" y1="{origin_sy:.2f}" x2="{svg_w:.2f}" y2="{origin_sy:.2f}" '
        'stroke="#e3e6ea" stroke-width="1" stroke-dasharray="4 4"/>',
    ]

    # ── Legend ──
    # Show every kind we know about (so the legend is stable even if a
    # rarely-used kind has zero entries in some build), plus any unknown
    # kinds discovered at runtime.
    known_order = list(KIND_COLOR.keys())
    runtime_kinds = sorted({str(p["kind"]) for p in primitives})
    unknown_kinds = [k for k in runtime_kinds if k not in KIND_COLOR]
    legend_kinds = known_order + unknown_kinds

    legend_items: list[str] = []
    for k in legend_kinds:
        color = KIND_COLOR.get(k, UNKNOWN_KIND_COLOR)
        n = counts.get(k, 0)
        label = html.escape(k)
        legend_items.append(
            '<li class="legend-item">'
            f'<span class="legend-swatch" style="background:{color};"></span>'
            f'<span class="legend-label">{label}</span>'
            f'<span class="legend-count">({n})</span>'
            "</li>"
        )

    # ── HTML scaffolding ──
    title_text = f"Notation 2D Map — {layout_version}"
    page_title = html.escape(title_text)
    layout_version_esc = html.escape(layout_version)
    scope_esc = html.escape(scope)
    boundary_esc = html.escape(boundary)

    # Inline CSS + JS — fully self-contained, no CDN.
    style = """
:root {
  --bg: #ffffff;
  --fg: #1a1a1a;
  --muted: #555;
  --card: #f7f8fa;
  --border: #d0d4da;
}
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0;
  background: var(--bg);
  color: var(--fg);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica,
               Arial, sans-serif;
}
header {
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--card);
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 16px;
}
header h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
header .meta {
  font-size: 12px;
  color: var(--muted);
}
.layout {
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: 16px;
  padding: 16px;
}
.canvas-wrap {
  border: 1px solid var(--border);
  background: var(--bg);
  border-radius: 6px;
  overflow: auto;
  position: relative;
}
svg { display: block; }
.dot { cursor: pointer; transition: r 0.08s ease; }
.dot:hover { r: 8; stroke: #000; stroke-width: 1.2; }
aside.legend {
  border: 1px solid var(--border);
  background: var(--card);
  border-radius: 6px;
  padding: 12px 14px;
  font-size: 12px;
  max-height: 80vh;
  overflow-y: auto;
}
aside.legend h2 {
  margin: 0 0 8px 0;
  font-size: 13px;
  font-weight: 600;
}
ul.legend-list { list-style: none; margin: 0; padding: 0; }
.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
}
.legend-swatch {
  width: 14px; height: 14px;
  border-radius: 50%;
  border: 1px solid #222;
  flex: 0 0 auto;
}
.legend-label { flex: 1 1 auto; }
.legend-count { color: var(--muted); }
#tooltip {
  position: fixed;
  pointer-events: none;
  background: rgba(20, 20, 24, 0.95);
  color: #fff;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.4;
  font-family: ui-monospace, Menlo, Consolas, "Courier New", monospace;
  display: none;
  z-index: 1000;
  box-shadow: 0 2px 6px rgba(0,0,0,0.25);
}
footer {
  padding: 8px 20px 16px;
  font-size: 11px;
  color: var(--muted);
}
""".strip()

    # Vanilla JS for hover tooltip — no framework, no CDN.
    script = """
(function() {
  const tip = document.getElementById('tooltip');
  const svg = document.getElementById('map');
  if (!tip || !svg) return;
  function show(evt) {
    const t = evt.target;
    if (!t || t.tagName !== 'circle') return;
    const id = t.getAttribute('data-id') || '';
    const kind = t.getAttribute('data-kind') || '';
    const x = t.getAttribute('data-x') || '';
    const y = t.getAttribute('data-y') || '';
    tip.innerHTML =
      '<div><strong>' + escapeHtml(id) + '</strong></div>' +
      '<div>kind: ' + escapeHtml(kind) + '</div>' +
      '<div>(' + escapeHtml(x) + ', ' + escapeHtml(y) + ')</div>';
    tip.style.display = 'block';
    move(evt);
  }
  function move(evt) {
    const pad = 14;
    let x = evt.clientX + pad;
    let y = evt.clientY + pad;
    const r = tip.getBoundingClientRect();
    if (x + r.width > window.innerWidth) x = evt.clientX - r.width - pad;
    if (y + r.height > window.innerHeight) y = evt.clientY - r.height - pad;
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
  }
  function hide() { tip.style.display = 'none'; }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function(c) {
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
    });
  }
  svg.addEventListener('mouseover', show);
  svg.addEventListener('mousemove', move);
  svg.addEventListener('mouseout', function(evt) {
    if (evt.target && evt.target.tagName === 'circle') hide();
  });
})();
""".strip()

    svg_body = (
        f'<svg id="map" xmlns="http://www.w3.org/2000/svg" '
        f'width="{svg_w:.0f}" height="{svg_h:.0f}" '
        f'viewBox="0 0 {svg_w:.2f} {svg_h:.2f}">'
        + "".join(axis_lines)
        + "".join(dot_lines)
        + "</svg>"
    )

    extents_str = (
        f"x ∈ [{min_x + 1.0:.2f}, {max_x - 1.0:.2f}], "
        f"y ∈ [{min_y + 1.0:.2f}, {max_y - 1.0:.2f}]"
    )

    body = f"""
<header>
  <h1>{page_title}</h1>
  <div class="meta"><strong>{total}</strong> primitives</div>
  <div class="meta">extents: {html.escape(extents_str)}</div>
</header>
<div class="layout">
  <div class="canvas-wrap">
    {svg_body}
  </div>
  <aside class="legend">
    <h2>Legend (kind &rarr; colour)</h2>
    <ul class="legend-list">
      {''.join(legend_items)}
    </ul>
  </aside>
</div>
<div id="tooltip" role="tooltip"></div>
<footer>
  <div><strong>layout_version:</strong> {layout_version_esc}</div>
  <div><strong>scope:</strong> {scope_esc}</div>
  <div style="margin-top:4px;">{boundary_esc}</div>
</footer>
""".strip()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{page_title}</title>
<style>
{style}
</style>
</head>
<body>
{body}
<script>
{script}
</script>
</body>
</html>
"""


# ── CLI ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        "-o",
        default=str(_HERE / "notation_map_viz.html"),
        help="Output HTML path (default: tools/notation_map_viz.html).",
    )
    args = parser.parse_args(argv)

    payload = nm.canonical_layout_payload()
    html_text = _render_html(payload)

    out_path = Path(args.output)
    if not out_path.is_absolute():
        # Relative paths are relative to CWD, matching `python tools/...` UX.
        out_path = Path.cwd() / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8")

    summary = {
        "status": "RENDERED",
        "output": str(out_path),
        "layout_version": payload.get("layout_version"),
        "primitive_count": len(payload.get("primitives", [])),  # type: ignore[arg-type]
        "kind_counts": _kind_counts(list(payload.get("primitives", []))),  # type: ignore[arg-type]
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
