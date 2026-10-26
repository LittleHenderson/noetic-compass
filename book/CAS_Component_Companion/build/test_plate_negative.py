#!/usr/bin/env python3
"""Negative controls for the companion guide's plate audits.

An audit that cannot fail proves nothing. This script breaks the symbol
library on purpose -- once per historical defect -- and requires the matching
audit to report a failure. It writes a scratch copy of `figures_preamble.tex`
under `build/plates_negative/` and points the audits at it through
CAS_FIGURES_PREAMBLE (library) or CAS_CHAPTERS (figure blocks), so the real
source is never modified.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
WORK = BUILD / "plates_negative"
STYLES = BUILD / "figures_preamble.tex"
CIRCUITS = BUILD.parent / "09_Board_Level_Schematics.md"

# (name, target file, exact current text, broken replacement, audit script)
CASES = [
    (
        "bridge rectifier, two diodes reversed",
        STYLES,
        r"\foreach \x/\y/\r in {-2/2/45,2/2/135,-2/-2/135,2/-2/45} {",
        r"\foreach \x/\y/\r in {-2/2/45,2/2/-45,-2/-2/-45,2/-2/45} {",
        "audit_symbol_invariants.py",
    ),
    (
        "current mirror wired to the emitter rail",
        STYLES,
        "    % diode connection: left base joined to left collector\n"
        "    \\draw[caswire] (-3.5mm,0) -- (-4.6mm,0) -- (-4.6mm,3.5mm) -- (-2mm,3.5mm);\n"
        "    % replicated bias line: left base feeds the right base\n"
        "    \\draw[caswire] (-3.5mm,0) -- (-3.5mm,-4.6mm) -- (3.5mm,-4.6mm) -- (3.5mm,0);",
        "    \\draw[caswire] (-3.5mm,0) -- (-3.5mm,-3mm) -- (-2mm,-3mm);",
        "audit_symbol_invariants.py",
    ),
    (
        "Schmitt hysteresis mark overflows the triangle",
        STYLES,
        r"\draw[caswire,line width=0.45pt] (-0.85mm,0.75mm)--(0.05mm,0.75mm)--(0.05mm,-0.75mm)--(0.95mm,-0.75mm);",
        r"\draw[caswire,line width=0.45pt] (-0.8mm,0.9mm)--(0.3mm,0.9mm)--(0.3mm,-0.9mm)--(1.4mm,-0.9mm);",
        "audit_symbol_invariants.py",
    ),
    (
        "relay linkage floats free of coil and armature",
        STYLES,
        r"\draw[caswire,dashed] (0,-1mm)--(0,2.33mm);",
        r"\draw[caswire,dashed] (0,-0.7mm)--(0,1.2mm);",
        "audit_symbol_invariants.py",
    ),
    (
        "circuit 6 takes the result from the MUX select stub",
        CIRCUITS,
        r"\node[casterm] (out) at (48,-11) {result}; \draw[flow] (48,12)--(out.north);",
        r"\node[casterm] (out) at (43,-8) {result}; \draw[flow] (43,8)--(out.north);",
        "audit_plate_geometry.py",
    ),
    (
        "circuit 7 leaves the current-mirror tail floating",
        CIRCUITS,
        "  \\draw[flow] (2,3.5)--(2,14.6)--(0,14.6);",
        "  \\draw[flow] (0,5)--(0,14.6);",
        "audit_plate_geometry.py",
    ),
    (
        "circuit 9 refresh line floats at both ends",
        CIRCUITS,
        "  \\draw[fbflow] (12,-6)--(12,8)--(-6,8);",
        "  \\draw[fbflow] (12,-4.5)--(12,10);",
        "audit_plate_geometry.py",
    ),
]


def run(script: str, env: dict) -> tuple[int, str]:
    done = subprocess.run([sys.executable, script], cwd=BUILD, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace")
    return done.returncode, done.stdout


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    originals = {STYLES: STYLES.read_text(encoding="utf-8"),
                 CIRCUITS: CIRCUITS.read_text(encoding="utf-8")}
    failures = []
    for name, target, good, bad, script in CASES:
        original = originals[target]
        if good not in original:
            failures.append(f"{name}: anchor text not found in {target.name}")
            continue
        # Both broken copies deliberately share the name `figures_preamble.tex`
        # for the library case; the chapter case keeps its own name so the
        # geometry audit can be pointed at it through CAS_CHAPTERS.
        broken = WORK / target.name
        broken.write_text(original.replace(good, bad, 1), encoding="utf-8")
        env = dict(os.environ,
                   CAS_FIGURES_PREAMBLE=str(broken),
                   CAS_CHAPTERS=str(broken))
        code, out = run(script, env)
        status = "detected" if code != 0 else "MISSED"
        print(f"{status:9} {name}  ({script})")
        if code == 0:
            failures.append(f"{name}: {script} still passed on the broken source")
    for name in {t.name for t in originals}:
        (WORK / name).unlink(missing_ok=True)
    if failures:
        print("\nFAIL negative controls")
        for f in failures:
            print("  " + f)
        return 1
    print(f"\nPASS all {len(CASES)} negative controls were detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
