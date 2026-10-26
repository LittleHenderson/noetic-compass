#!/usr/bin/env python3
"""Source regression lock for the companion guide's ten cognitive schematics.

This checker freezes reviewed source strings -- terminal coordinates, typed
state literals, Domain styles, and shared-symbol conventions -- so that a
later edit cannot silently drop a reviewed connection. It is deliberately
narrow: it can only catch a change to something someone already wrote down.

The defect classes it *cannot* catch are covered by the two geometric audits,
which read the compiled PDF instead of the source:

  audit_plate_geometry.py        every wire endpoint must land on other ink
  audit_symbol_invariants.py     each glyph must be electrically itself

and `test_plate_negative.py` proves all three can actually fail.
"""
from __future__ import annotations

import re
import sys

import plates


def circuit(text: str, number: int) -> str:
    """One `## Circuit N` section, from its heading to the next one."""
    start = re.search(rf"^## Circuit {number} — .+$", text, re.MULTILINE)
    if not start:
        raise AssertionError(f"missing Circuit {number}")
    end = re.search(r"^## (?:Circuit \d+ —|)\S", text[start.end():], re.MULTILINE)
    stop = start.end() + (end.start() if end else len(text) - start.end())
    return text[start.start():stop]


def require(haystack: str, needle: str, label: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"{label}: missing reviewed connection `{needle}`")


def forbid(haystack: str, needle: str, label: str) -> None:
    if needle in haystack:
        raise AssertionError(f"{label}: forbidden stale form `{needle}`")


def main() -> int:
    chapters = plates.read_chapters()
    text = "\n".join(chapters.values())
    preamble = plates.STYLES.read_text(encoding="utf-8")
    c = {n: circuit(text, n) for n in range(1, 11)}

    # Circuit 1: exact CJT local terminals (top/effect at x=0.9, bias at x=-4).
    # TP1 taps the base lead, never the base bar.
    require(c[1], r"(cause.south)--(0.9,14)", "sch-01")
    require(c[1], r"(bias.east)--(-4,10)", "sch-01")
    require(c[1], r"(0.9,6)--(effect.north)", "sch-01")
    require(c[1], r"\node[cblock", "sch-01 cognitive Domain")
    require(c[1], r"\node[casprobe] at (-3,10)", "sch-01 probe on the base lead")

    # Circuit 2: block widths leave an 8.5 mm gap, each diode sits at the gap
    # midpoint, and the Zener guard lands on the middle diode's anode lead.
    require(c[2], r"\node[pblock,text width=19mm] (p) at (-44.4,8)", "sch-02 P block")
    require(c[2], r"\node[oblock,text width=19mm] (o) at (44.4,8)", "sch-02 O block")
    require(c[2], r"\coordinate (m\a) at ($(\a.east)!0.5!(\b.west)$)", "sch-02 gap midpoint")
    require(c[2], r"\pic[scale=0.7] at (m\a) {casdiode}", "sch-02 diode in the gap")
    require(c[2], r"\draw[flowmini] (\a.east) -- ($(m\a)+(-2.8mm,0)$)", "sch-02 forward lead")
    require(c[2], r"\draw[flowmini] ($(m\a)+(2.8mm,0)$) -- (\b.west)", "sch-02 forward lead")
    require(c[2], r"\draw[flowmini] (z.south) -- (0,22)", "sch-02 Zener upper lead")
    require(c[2], r"\draw[flowmini] (0,14) -- (0,11) -- (-2.8,11) -- (-2.8,8)", "sch-02 guard landing")
    forbid(c[2], r"(p.east)--(-32,8)", "sch-02 backwards arrow")

    # Circuit 3: mixed-Domain bias states use matching P/C/E styles.
    require(c[3], r"\node[pblock", "sch-03 P bias")
    require(c[3], r"\node[cblock", "sch-03 C bias")
    require(c[3], r"\node[eblock", "sch-03 E bias")

    # Circuit 4: the source wire stops at both R_fb terminals.
    require(c[4], r"\draw[flow] (outcome)--(-29,15)", "sch-04 R_fb left terminal")
    require(c[4], r"\draw[flow] (-21,15)--(0,15)", "sch-04 R_fb right terminal")

    # Circuit 5: the Schmitt output is routed from its actual +5 mm lead.
    require(c[5], r"(43,10)--(48,10)--(48,-7)--(stable.east)", "sch-05")

    # Circuit 6: typed outputs, independent pass/stop accents, reachable fuse sense,
    # and the result taken from the MUX output lead rather than its select stub.
    require(c[6], r"\textasciicircum9\textasciicircum C\_\{F2\}|A", "sch-06 GREEN state")
    require(c[6], r"\textasciicircum9\textasciicircum P\_\{F7\}|T", "sch-06 RED state")
    require(c[6], r"draw=casGreen", "sch-06 pass accent")
    require(c[6], r"draw=casRed", "sch-06 stop accent")
    require(c[6], r"\draw[fbflow] (red.east)--(5,0)--(5,24)--(13,24)", "sch-06 fuse sense")
    require(c[6], r"\fill[casNedge] (13,24) circle (0.45mm)", "sch-06 fuse junction dot")
    require(c[6], r"\node[casterm] (out) at (48,-11) {result}; \draw[flow] (48,12)--(out.north)",
            "sch-06 result from the MUX output lead")
    require(c[6], r"\draw[fbflow] (5,0)--(5,-19)--(30,-19)--(30,8)--(43,8)", "sch-06 select drive")
    forbid(c[6], r"\draw[flow] (43,8)--(out.north)", "sch-06 select mis-tap")
    require(c[6], r"$0.05<0.1$", "sch-06 threshold reachability")
    require(c[6], "cuts the green path, never the refusal path", "sch-06 polarity")

    # Circuit 7: Evaluative bias, biased mirror, and both matched branches land on
    # load inputs; the mirror's output collector drives the pair's shared tail.
    require(c[7], r"\node[eblock", "sch-07 E bias")
    require(c[7], r"\draw[flow] (bias.east)--(-3.5,0)", "sch-07 bias at the mirror base")
    require(c[7], r"\draw[flow] (2,3.5)--(2,14.6)--(0,14.6)", "sch-07 mirror output to tail")
    require(c[7], r"(18,1)--(20,1)", "sch-07 upper load input")
    require(c[7], r"(16,-1)--(20,-1)", "sch-07 lower load input")
    require(c[7], r"(30,0)--(35,0)--(35,-13)--(diff.east)", "sch-07 output")

    # Circuit 8: passive leads are connected in segments; the tank drives the PLL.
    for needle in (r"(internal.east)--(-31,14)", r"(-23,14)--(-12,14)",
                   r"(-4,14)--(tank.west)", r"(reference.east)--(-31,-8)",
                   r"(-23,-8)--(7.5,-8)", r"(18.5,-8)--(28,-8)--(rhythm.south)",
                   r"(tank.south)--(13,0)--(13,-5.4)"):
        require(c[8], needle, "sch-08")

    # Circuit 9: open switch remains open; leakage, refresh, and recall split at
    # documented junctions that carry a junction dot.
    require(c[9], r"(exp.east)--(-34,14)", "sch-09 switch input")
    require(c[9], r"(-26,14)--(-14,14)", "sch-09 switch output")
    require(c[9], r"(-6,14)--(-6,6)", "sch-09 leakage tap")
    require(c[9], r"(-6,-2)--(-6,-10)", "sch-09 leakage reference")
    require(c[9], r"\fill[casNedge] (-6,14) circle (0.45mm)", "sch-09 retention junction dot")
    require(c[9], r"\draw[fbflow] (12,-6)--(12,8)--(-6,8)", "sch-09 refresh return")
    require(c[9], r"\fill[casNedge] (-6,8) circle (0.45mm)", "sch-09 refresh junction dot")
    forbid(c[9], r"(exp)--(-14,14)", "sch-09")

    # Circuit 10: every line names a scalar/control; the rails are bonded to one
    # supply bus, and power-good order is explicit.
    for term in ("F3-rail brownout", "power-good", "thermal monitor", "silent cutoff"):
        require(c[10], term, "sch-10 typed control")
    require(c[10], r"\draw[caswire] (-45,27.5)--(45,27.5)", "sch-10 supply bus")
    require(c[10], r"\draw[caswire] (0,27.5)--(regs.north)", "sch-10 bus to regulators")

    # Shared symbols: conventional input polarity, recognizable hysteresis,
    # four correctly oriented bridge diodes, and bounded inductor geometry.
    require(preamble, r"at (-2mm,1.6mm) {$+$}", "op-amp polarity")
    require(preamble, r"at (-2mm,-1.6mm) {$-$}", "op-amp polarity")
    forbid(preamble, r"\sqcap", "Schmitt symbol")
    require(preamble, "pics/casbridge", "bridge symbol")
    # Regression lock only. The polarity itself is verified by
    # audit_symbol_invariants.py, which derives the required direction from the
    # declared AC / DC+ / DC- node roles instead of comparing to a literal.
    require(preamble, r"\foreach \x/\y/\r in {-2/2/45,2/2/135,-2/-2/135,2/-2/45}",
            "bridge four diodes")
    require(preamble, r"\useasboundingbox (-4mm,-1mm) rectangle (4mm,1mm)", "inductor bounds")
    require(preamble, r"Latex[length=2mm,width=1.6mm,line width=0pt]", "arrowhead apex on endpoint")

    labels = re.findall(r"\\label\{(fig:[^}]+)\}", text)
    if len(labels) != 17 or len(set(labels)) != 17:
        raise AssertionError(f"expected 17 unique figure labels, got {len(labels)} / {len(set(labels))} unique")

    print("PASS companion source regression lock")
    print("circuits=10 figures=17 reviewed_connections=52")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
