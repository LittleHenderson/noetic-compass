"""Build helm_hub/device_figures.html: the HELM Cube drawings as static inline SVG figures for the hub's device page.

Source of truth: the design-canvas boards copied into docs/working/helm_cube_device_concept_v0/drawings/*.dc.html (the same files
published to the private design canvas). This script lifts each board's <svg> block, makes its element ids unique per figure,
replaces the one template hole ({{glow}}) with its default colour, and builds the light-mode grid (a template on the canvas) as
static SVG. No network, no rendering. Run: python helm_hub/make_device_figures.py
"""
from __future__ import annotations

import html
import re
from pathlib import Path

HUB = Path(__file__).resolve().parent
ROOT = HUB.parent
DRAW = ROOT / "docs" / "working" / "helm_cube_device_concept_v0" / "drawings"
OUT = HUB / "device_figures.html"

SVG_RE = re.compile(r"<svg\b[^>]*>.*?</svg>", re.S)


def svgs(name: str) -> list[str]:
    t = (DRAW / name).read_text(encoding="utf-8")
    return [s for s in SVG_RE.findall(t) if 'width="0"' not in s[:80]]


def scoped(svg: str, prefix: str) -> str:
    ids = re.findall(r'\bid="([^"]+)"', svg)
    for i in ids:
        svg = svg.replace(f'id="{i}"', f'id="{prefix}-{i}"').replace(f"url(#{i})", f"url(#{prefix}-{i})")
    svg = svg.replace("{{glow}}", "#FFE3B8")
    svg = re.sub(r'\sclass="(?:speak|buzz)"', "", svg)
    # responsive root: keep the viewBox, drop the fixed size
    head, rest = svg.split(">", 1)
    head = re.sub(r'\swidth="\d+"', "", head, count=1)
    head = re.sub(r'\sheight="\d+"', "", head, count=1)
    return head + ' style="width:100%;height:auto;display:block">' + rest


EDGES = {
    "e1": "M60,16 L98.1,38", "e2": "M98.1,38 L60,60", "e3": "M60,60 L21.9,38", "e4": "M21.9,38 L60,16",
    "e5": "M98.1,38 L98.1,82", "e6": "M60,60 L60,104", "e7": "M21.9,38 L21.9,82", "e8": "M98.1,82 L60,104", "e9": "M60,104 L21.9,82",
}
ALL = list(EDGES)


def but(ks):
    return [k for k in ALL if k not in ks]


MODES = [
    ("Asleep", "off", "#2C2C31", [], [], "Off. A plain black box.", 0),
    ("Awake", "after a shake", "#F4F1EA", ALL, [], "One sweep along all twelve edges, then dim.", 0),
    ("Listening", "mics live", "#67D8E8", ["e1", "e2", "e5", "e8"], but(["e1", "e2", "e5", "e8"]), "The edges nearest the person speaking glow brighter.", 0),
    ("Thinking", "gate check", "#E9B949", ["e1", "e9"], [], "Two points of light travel along the edges.", 0),
    ("Speaking", "voice out", "#FFE3B8", ALL, [], "Brightness follows the voice: a pulse per syllable.", 0),
    ("Asking", "a question", "#B79CFF", ALL, [], "Short, short, long, every 2 seconds. Then it listens.", 0),
    ("Missing input", "undetermined", "#F2A93B", but(["e6"]), [], "One dark edge: the gap is what is missing.", 0),
    ("Declined", "refusal", "#C08A3E", ["e8"], [], "Shrinks to one edge and fades. Not red.", 0),
    ("Privacy, soft", "5 taps", "#E5484D", ALL, [], "Slow breathing. A software mute.", 0),
    ("Privacy, hard", "hardware switch", "#E5484D", ALL, [], "Steady red, powered through the switch.", 0),
    ("Camera on", "a camera powered", "#3DDC84", [], [], "A green dot on that face, wired to the camera.", 4),
    ("Charging", "on the pad", "#F4F1EA", ["e5", "e6", "e7", "e8"], [], "One buzz; lit edges show the charge level.", 0),
    ("Pairing", "setup window", "#4C8DF6", ["e1", "e2", "e3"], [], "A chase; fewer stay lit as time runs out.", 0),
    ("Low battery, error", "battery or network", "#F07A2B", ALL, [], "Orange blinks.", 0),
    ("Eye report", "report filed", "#2BB5A6", ["e4"], [], "One blip: a report is in the app.", 0),
    ("Updating", "firmware", "#F4F1EA", ["e5", "e6", "e7"], [], "A slow chase along the edges.", 0),
]


def mode_cell(name, state, color, lit, dim, motion, dot) -> str:
    d_lit = " ".join(EDGES[k] for k in lit)
    d_dim = " ".join(EDGES[k] for k in dim)
    parts = [
        f'<svg viewBox="0 0 120 120" role="img" aria-label="{html.escape(name)}: {html.escape(motion)}" style="width:100%;max-width:120px;height:auto;display:block">',
        '<polygon points="60,16 98.1,38 60,60 21.9,38" fill="#2C2C31"></polygon>',
        '<polygon points="21.9,38 60,60 60,104 21.9,82" fill="#1A1A1D"></polygon>',
        '<polygon points="60,60 98.1,38 98.1,82 60,104" fill="#111113"></polygon>',
        '<path d="M60,16 L98.1,38 L60,60 L21.9,38 Z M98.1,38 L98.1,82 L60,104 L21.9,82 L21.9,38 M60,60 L60,104" fill="none" stroke="#333338" stroke-width="2" stroke-linejoin="round"></path>',
        '<g filter="url(#modes-edgeglow)">',
    ]
    if d_dim:
        parts.append(f'<path d="{d_dim}" fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" opacity="0.35"></path>')
    if d_lit:
        parts.append(f'<path d="{d_lit}" fill="none" stroke="{color}" stroke-width="2.8" stroke-linecap="round"></path>')
    if dot:
        parts.append(f'<circle cx="79" cy="71" r="{dot}" fill="#3DDC84"></circle>')
    parts.append("</g></svg>")
    return (f'<div style="display:flex;flex-direction:column;gap:4px">{"".join(parts)}'
            f'<div style="font-size:13px;font-weight:600;color:#F4F2EC">{html.escape(name)}</div>'
            f'<div style="font-size:11px;color:#A7A39A">{html.escape(state)}</div>'
            f'<div style="font-size:12px;line-height:1.4;color:#CFCBC2">{html.escape(motion)}</div></div>')


def figure(svg: str, caption: str, dark: bool = False) -> str:
    bg = "#121214" if dark else "#E8E6E1"
    return (f'<figure style="margin:16px 0;padding:16px;border-radius:12px;background:{bg}">{svg}'
            f'<figcaption style="margin-top:10px;font-size:13px;line-height:1.5;color:{"#CFCBC2" if dark else "#2E2C29"}">{caption}</figcaption></figure>')


def build() -> str:
    main = svgs("Main.dc.html")[0]
    faces = svgs("Faces.dc.html")
    charging = svgs("Charging.dc.html")[0]
    sensing = svgs("Sensing.dc.html")[0]
    display = svgs("Display.dc.html")[0]
    grid = "".join(mode_cell(*m) for m in MODES)
    defs = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs><filter id="modes-edgeglow" x="-40%" y="-40%" '
            'width="180%" height="180%"><feGaussianBlur stdDeviation="3.2" result="b"></feGaussianBlur><feMerge><feMergeNode in="b"></feMergeNode>'
            '<feMergeNode in="b"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge></filter></defs></svg>')
    modes = (f'<figure style="margin:16px 0;padding:16px;border-radius:12px;background:#121214">{defs}'
             f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:18px 14px">{grid}</div>'
             '<figcaption style="margin-top:10px;font-size:13px;line-height:1.5;color:#CFCBC2">The light modes. Every mode lives on the twelve edges; '
             'each can be told apart by its motion alone. Green is kept for one job: a camera is on.</figcaption></figure>')
    xray = ('<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px">'
            + "".join(f"<div>{scoped(s, f'xray{i}')}</div>" for i, s in enumerate(faces)) + "</div>")
    out = [
        "<!-- generated by helm_hub/make_device_figures.py from docs/working/helm_cube_device_concept_v0/drawings/; do not edit by hand -->",
        figure(scoped(main, "hero"), "Off, it is a plain black box: every face the same. Speaking, light glows along all twelve edges and pulses with each syllable. "
               "A tennis ball (67 mm) drawn to the same scale."),
        modes,
        figure(xray, "X-ray, to scale (64 mm face). Left: a side face, with a centred camera, the green camera-on dot, a depth-sensor window, a microphone pinhole in "
               "the edge seam, the sound slot and the edge light. Right: the charge face, with the magnet ring and coil, a corner camera, the dock sensor and the "
               "haptic motor. From outside, both look the same.", dark=True),
        figure(scoped(charging, "charge"), "Charging: magnetic pull turns the right face down; it snaps on and buzzes once; lit edges show the charge level. "
               "The docked face rests and the other five keep working."),
        figure(scoped(sensing, "sense"), "Knowing where it is: a gyroscope feels each turn, a small depth sensor behind each face measures the walls, Wi-Fi gives a "
               "distance to the router. Space it never measured stays undetermined and is never drawn in by guess."),
        figure(scoped(display, "disp"), "Another version, not the main one: the display cube. Black glass over screens; a dark screen gives no light, so off it is "
               "still a plain black box."),
    ]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    print("wrote", OUT, OUT.stat().st_size, "bytes")
