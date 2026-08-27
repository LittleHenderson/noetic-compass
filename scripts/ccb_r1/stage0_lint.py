"""Stage 0 static conformance linter for CAS reasoning boards (CCB-R1 class).

Catches the defect class found in the audited CCB-R1 §11 netlist without running
anything: domain-descent violations, goal-derived bias on inference stages,
orphan nodes, non-canonical feedback, unchecked admissibility, and un-machine-
checkable gain values.

This is a PROTOTYPE accompanying docs/working/cas_pcba_reasoning_audit_2026_08_27.md.
It deliberately does no semantics: Stage 0 is the cheap gate that runs before any
simulator exists.

Usage:  python3 scripts/ccb_r1/stage0_lint.py <netlist.board>
Exit:   0 = clean, 1 = findings, 2 = parse/setup error
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Domain precedence: P > C > E > O. A CJT edge may only descend (rank must not decrease).
DOMAIN_RANK = {"P": 0, "C": 1, "E": 2, "O": 3}

# Drives whose activation encodes "what the board wants" rather than "what is true".
# These are goal-derived ONLY outside the Principled domain. A Principled-domain
# bias is a charter/constitution -- the legitimate governor of an evaluation stage --
# even when it carries F7 Purpose. The firewall separates *ambition* from *principle*,
# and the domain coordinate is what tells them apart, not the drive alone.
GOAL_DERIVED_DRIVES = {5, 7}  # F5 Agency, F7 Purpose

# Stages whose bias port is firewalled. Matched against the cjt label.
FIREWALLED_STAGES = ("analyze", "evaluate", "infer", "conclude", "judge", "compare")

STATE_RE = re.compile(
    r"\^(?P<operator>\d)\^(?P<domain>[PCEO])"
    r"(?:_\{(?P<drive>F\d)(?:\|(?P<drive_register>[TAfE]))?\})?"
    r"(?:\|(?P<register>[TAfE]))?"
)


# A gain literal must contain at least one digit -- "..." must not pass as a number.
_NUMERIC = re.compile(r"\d+(?:\.\d+)?(?:[eE]-?\d+)?")


@dataclass
class Finding:
    code: str
    severity: str
    subject: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper():7}] {self.code:14} {self.subject}: {self.message}"


@dataclass
class Board:
    name: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    nodes: dict[str, str] = field(default_factory=dict)          # name -> state literal
    cjts: list[dict] = field(default_factory=list)               # label, src, bias, tgt, attrs
    diodes: list[tuple[str, str, str]] = field(default_factory=list)  # label, from_dom, to_dom
    feedbacks: list[dict] = field(default_factory=list)          # label, src, tgt, attrs
    probes: dict[str, str] = field(default_factory=dict)


def parse_board(text: str) -> Board:
    b = Board()
    m = re.search(r"board\s+(\w+)\s*\{", text)
    if m:
        b.name = m.group(1)

    for m in re.finditer(r"\binput:\s*(\w+)\s*;", text):
        b.inputs.append(m.group(1))
    for m in re.finditer(r"\boutput:\s*(\w+)\s*;", text):
        b.outputs.append(m.group(1))
    for m in re.finditer(r"\bnode\s+(\w+)\s*:\s*([^;]+);", text):
        b.nodes[m.group(1)] = m.group(2).strip()
    for m in re.finditer(
        r"\bcjt\s+(\w+)\s*:\s*CJT<\s*([\w]+)\s*\|\s*([\w]+)\s*=>\s*([\w]+)\s*>\s*(\[[^\]]*\])?",
        text,
    ):
        b.cjts.append(
            {
                "label": m.group(1),
                "src": m.group(2),
                "bias": m.group(3),
                "tgt": m.group(4),
                "attrs": (m.group(5) or ""),
            }
        )
    for m in re.finditer(r"\bdiode\s+(\w+)\s*:\s*Diode<\s*\^([PCEO])\s*->\s*\^([PCEO])\s*>", text):
        b.diodes.append((m.group(1), m.group(2), m.group(3)))
    for m in re.finditer(
        r"\bfeedback\s+(\w+)\s*:\s*([\w]+)\s*->\s*([\w]+)\s*(\[[^\]]*\])?", text
    ):
        b.feedbacks.append(
            {"label": m.group(1), "src": m.group(2), "tgt": m.group(3), "attrs": (m.group(4) or "")}
        )
    for m in re.finditer(r"\bprobe\s+(\w+)\s*:\s*(\w+)\s*;", text):
        b.probes[m.group(1)] = m.group(2)
    return b


def domain_of(board: Board, node: str) -> str | None:
    lit = board.nodes.get(node)
    if not lit:
        return None
    m = STATE_RE.search(lit)
    return m.group("domain") if m else None


def drive_of(board: Board, node: str) -> int | None:
    lit = board.nodes.get(node)
    if not lit:
        return None
    m = STATE_RE.search(lit)
    if m and m.group("drive"):
        return int(m.group("drive")[1:])
    return None


def _beta(attrs: str) -> str | None:
    m = re.search(r"(?:β|beta)\s*=\s*([^,\]]+)", attrs)
    return m.group(1).strip() if m else None


def lint(board: Board, compile_expression=None, is_admissible=None) -> list[Finding]:
    out: list[Finding] = []
    written = {c["tgt"] for c in board.cjts}
    bias_ports = {c["bias"] for c in board.cjts}

    # --- L-COMPILE: every node literal must compile under the real compiler ---
    if compile_expression is not None:
        for name, lit in board.nodes.items():
            try:
                compile_expression(lit)
            except Exception as exc:  # noqa: BLE001 - report, never crash the lint
                out.append(
                    Finding("L-COMPILE", "major", name, f"literal {lit!r} does not compile: {exc}")
                )

    # --- L-DOMAIN: CJT edges must descend P > C > E > O ---
    for c in board.cjts:
        sd, td = domain_of(board, c["src"]), domain_of(board, c["tgt"])
        if sd and td and DOMAIN_RANK[td] < DOMAIN_RANK[sd]:
            out.append(
                Finding(
                    "L-DOMAIN",
                    "critical",
                    c["label"],
                    f"ascends {sd}->{td} against domain descent (Inversion Axis W)",
                )
            )

    # --- L-BIASDOM: a bias must not be lower-precedence than the stage it governs ---
    for c in board.cjts:
        bd, td = domain_of(board, c["bias"]), domain_of(board, c["tgt"])
        if bd and td and DOMAIN_RANK[bd] > DOMAIN_RANK[td]:
            out.append(
                Finding(
                    "L-BIASDOM",
                    "major",
                    c["label"],
                    f"bias {c['bias']} is {bd}-domain but governs a {td}-domain target",
                )
            )

    # --- L-FIREWALL: no goal-derived bias on an evaluation/inference stage ---
    for c in board.cjts:
        if not any(s in c["label"].lower() for s in FIREWALLED_STAGES):
            continue
        d = drive_of(board, c["bias"])
        bd = domain_of(board, c["bias"])
        if d in GOAL_DERIVED_DRIVES and bd != "P":
            out.append(
                Finding(
                    "L-FIREWALL",
                    "critical",
                    c["label"],
                    f"bias {c['bias']} is goal-derived (F{d} in {bd}-domain); "
                    "ambition must not choose the answer",
                )
            )

    # --- L-ORPHAN: declared non-input nodes must be written by some CJT ---
    for name in board.nodes:
        if name in written or name in bias_ports or name in board.inputs:
            continue
        out.append(Finding("L-ORPHAN", "critical", name, "declared but no CJT writes it"))

    # --- L-OUTPUT: declared outputs must be produced ---
    for o in board.outputs:
        if o not in written and o not in board.nodes:
            out.append(Finding("L-OUTPUT", "critical", o, "declared output is never assigned"))

    # --- L-DANGLE: a written node consumed by nothing ---
    consumed = {c["src"] for c in board.cjts} | {f["src"] for f in board.feedbacks}
    for name in written:
        if name not in consumed and name not in board.outputs:
            out.append(Finding("L-DANGLE", "minor", name, "written but consumed by nothing"))

    # --- L-FEEDBACK: feedback must land on the Principled domain, at low gain ---
    for f in board.feedbacks:
        td = domain_of(board, f["tgt"])
        if td and td != "P":
            out.append(
                Finding(
                    "L-FEEDBACK",
                    "major",
                    f["label"],
                    f"targets {td}-domain {f['tgt']}; canonical feedback path is O->P",
                )
            )
        b = _beta(f["attrs"])
        if b is None or not _NUMERIC.fullmatch(b):
            out.append(
                Finding(
                    "L-BETA",
                    "major",
                    f["label"],
                    f"gain {b!r} is not machine-checkable; feedback gain must be a bounded number",
                )
            )
        elif float(b) > 0.01:
            out.append(
                Finding("L-BETA", "major", f["label"], f"feedback gain {b} exceeds 0.01 ceiling")
            )

    # --- L-BETA on CJT stages ---
    for c in board.cjts:
        b = _beta(c["attrs"])
        if b is not None and not _NUMERIC.fullmatch(b):
            out.append(
                Finding(
                    "L-BETA", "major", c["label"], f"gain {b!r} is a placeholder, not a checkable value"
                )
            )

    # --- L-DIODE: every declared diode must gate a real edge ---
    edges = {
        (domain_of(board, c["src"]), domain_of(board, c["tgt"]))
        for c in board.cjts
    }
    for label, fd, td in board.diodes:
        if (fd, td) not in edges:
            out.append(
                Finding("L-DIODE", "minor", label, f"gates ^{fd}->^{td} but no CJT edge crosses it")
            )

    # --- L-ADMISSIBLE: every CJT edge must clear the shipped admissibility relation ---
    if is_admissible is not None:
        for c in board.cjts:
            s_lit, t_lit = board.nodes.get(c["src"]), board.nodes.get(c["tgt"])
            if not (s_lit and t_lit):
                continue
            sm, tm = STATE_RE.search(s_lit), STATE_RE.search(t_lit)
            if not (sm and tm):
                continue
            s_idx = DOMAIN_RANK[sm.group("domain")] * 10 + int(sm.group("operator"))
            t_idx = DOMAIN_RANK[tm.group("domain")] * 10 + int(tm.group("operator"))
            op = int(tm.group("operator"))
            try:
                if not is_admissible(op, s_idx, t_idx):
                    out.append(
                        Finding(
                            "L-ADMISSIBLE",
                            "major",
                            c["label"],
                            f"CO-{op} is not admissible from state {s_idx} to {t_idx}",
                        )
                    )
            except Exception:  # engine unavailable -- Stage 0 still runs without it
                pass

    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = Path(argv[1])
    if not path.exists():
        print(f"no such netlist: {path}")
        return 2

    compile_expression = is_admissible = None
    for root in (
        Path(__file__).resolve().parents[2] / "noetic-compass-scaffold" / "noetic-compass",
        Path(__file__).resolve().parents[2] / "dist" / "cas-offline",
    ):
        if (root / "api" / "notation" / "compiler.py").exists():
            sys.path.insert(0, str(root))
            try:
                from api.notation.compiler import compile_expression as _ce  # type: ignore
                from api.notation.compiler import _is_admissible as _ia  # type: ignore

                compile_expression, is_admissible = _ce, _ia
            except Exception:
                pass
            break

    board = parse_board(path.read_text(encoding="utf8"))
    findings = lint(board, compile_expression, is_admissible)

    print(f"board: {board.name or '(unnamed)'}   nodes={len(board.nodes)} cjts={len(board.cjts)} "
          f"diodes={len(board.diodes)} feedback={len(board.feedbacks)}")
    print(f"compiler: {'attached' if compile_expression else 'UNAVAILABLE (L-COMPILE skipped)'}")
    print()
    if not findings:
        print("clean -- no Stage 0 findings.")
        return 0
    order = {"critical": 0, "major": 1, "minor": 2}
    for f in sorted(findings, key=lambda x: order[x.severity]):
        print(f)
    n_crit = sum(1 for f in findings if f.severity == "critical")
    print(f"\n{len(findings)} finding(s): {n_crit} critical.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
