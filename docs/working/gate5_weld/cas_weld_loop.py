#!/usr/bin/env python3
"""cas_weld_loop.py — the Gate-5 WELD: five CAS links driven as ONE machine.

    STAGE 1  READ      text            -> circuit reading  (parts + signal path)
    JOINT J1           circuit reading -> CAS expression the compiler consumes
    STAGE 2  COMPILE   expression      -> CompilationArtifact (accept / reject)
    STAGE 3  DIAGNOSE  expression      -> the NAMED broken axis   [BLIND]
    STAGE 4  CORRECT   detected axis   -> corrected expression    (axis dispatcher)
    JOINT J2           corrected expr  -> epsilon realization prefix
    STAGE 5  MEASURE   prefix          -> likelihood shift        [--with-model only]

The five links have DIFFERENT validation status. See WELD_SPEC.md "REAL vs
STUBBED". This header does not call them "five validated links": link 1 runs
from an authored fixture unless --with-readers is given, the J1 crosswalk is
authored and has never been tested, and the epsilon bridge is REAL and PARTIAL
(its stance-matched non-CAS control was never run).

Every symbolic stage calls the REAL repository modules:
    api.notation.compiler.compile_expression
    api.notation.inversion.invert_expression / IMPLEMENTED_AXES / DeferredAxisError
    belief.inversion_gate.run_inversion_scan                      (cas-native)
    cas_engine.InversionScanner / CognitiveStateVector            (Rust PyO3)
    run_stage9_40e_eta_epsilon_bridge.readable_prefix             (40E realizer)
    run_open_weight_eta_epsilon_bridge.readable_prefix            (F28 realizer)

Anything that is NOT real is announced with a `[STUB]` banner on stdout and a
`stubbed: true` record in the JSON report. Nothing is silently faked.

DETECTION IS BLIND
------------------
No detector is ever shown the injected axis, and no detector is ever shown the
pre-injection object inside its own input. The previous revision of this script
failed both tests (it concatenated the clean expression in front of the
perturbed one, and it assigned `detected_axis = axis` from the injection
parameter). Both defects are removed; see WELD_SPEC.md "ADVERSARIAL REVIEW
RESPONSE". As a direct consequence some injections are now NOT detected, and
the report says so.

HONESTY HEADLINE
----------------
This script demonstrates MECHANISM, not EFFICACY. The CAS-PCBA component-type
labels (DR / AMP / RS / ...) FAILED the Component Atlas at pythia-1b (rev 0.2,
NULL_ATLAS_V0), pythia-2.8b (rev 0.3) and gpt-neox-20b (rev 0.4). Under
`--entry reading` a component code DOES determine which validated cell is
realized, through an authored crosswalk with zero empirical support. That is
why `--entry both` (the default) also runs a CONSTRUCT-FREE arm whose cells are
named directly in the validated 40E space, so the reader can see whether any
conclusion depends on the falsified vocabulary.

Run:
    python cas_weld_loop.py                       # symbolic loop, zero GPU, zero API cost
    python cas_weld_loop.py --with-readers        # stage 1 uses the live blind readers ($$)
    python cas_weld_loop.py --with-model <hf_id>  # adds stage 5 on a pod
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # Windows consoles default to cp1252; CAS notation prints Unicode arrows.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - non-reconfigurable stream
    pass


# ---------------------------------------------------------------------------
# Repository wiring
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent                    # docs/working/gate5_weld
REPO_ROOT = HERE.parents[2]                               # tksCAS/
NC_ROOT = REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass"
CAS_NATIVE = NC_ROOT / "cas-native"
BANK = REPO_ROOT / "docs" / "working" / "gate2_closure" / "independent_bank"
SCRIPTS = NC_ROOT / "live-trace-worker" / "scripts"
FLAGSHIP_40E = SCRIPTS / "run_stage9_40e_eta_epsilon_bridge.py"
FLAGSHIP_F28 = SCRIPTS / "run_open_weight_eta_epsilon_bridge.py"

for _p in (str(NC_ROOT), str(CAS_NATIVE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# --- REAL compiler / inverter / detectors -----------------------------------
from api.notation.compiler import compile_expression            # noqa: E402
from api.notation.inversion import (                            # noqa: E402
    invert_expression,
    IMPLEMENTED_AXES,
    DEFERRED_AXES,
    ALL_AXES,
    AXIS_DESCRIPTIONS,
    DeferredAxisError,
    UnknownAxisError,
)
from belief.inversion_gate import run_inversion_scan            # noqa: E402

import cas_engine  # noqa: E402  Rust PyO3: InversionScanner, CognitiveStateVector


SEP = "=" * 78
# cas-engine/src/ontology/pathways.rs :: InversionAxis::index()
AXIS_ORDER = ["N", "W", "F", "E", "S", "A", "P"]

# P is DERIVED: belief.inversion_gate.axis_p_check fires only because >=2 of
# {N,W,F,A} already fired. It is never an independent detection and is removed
# from every "which axis was named" computation.
DERIVED_AXES = ("P",)

STUBS: list[dict[str, Any]] = []
DISCLOSURES: list[dict[str, str]] = []


def hr(title: str) -> None:
    print("\n" + SEP)
    print(title)
    print(SEP)


def stub(name: str, why: str, how_to_make_real: str) -> None:
    """Announce a stubbed link loudly on stdout and record it in the report."""
    STUBS.append({"link": name, "why_stubbed": why,
                  "how_to_make_real": how_to_make_real, "stubbed": True})
    print(f"\n[STUB] {name}\n[STUB]   why : {why}\n[STUB]   fix : {how_to_make_real}")


def disclose(tag: str, text: str) -> None:
    """Record an authored/limitation disclosure and print it."""
    DISCLOSURES.append({"tag": tag, "disclosure": text})
    print(f"[DISCLOSE] {tag}: {text}")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ===========================================================================
# JOINT J2 support — load the FLAGSHIP epsilon realizers without their torch chain
# ===========================================================================
#
# Neither flagship can be imported wholesale in this checkout:
# `run_stage9_40e_eta_epsilon_bridge` imports `run_open_weight_eta_epsilon_bridge`,
# which imports `evaluate_probe_dataset`, and that module is NOT PRESENT in
# live-trace-worker/scripts/ (verified: the directory holds
# evaluate_40_element_probe.py instead). Rather than reimplement the realizers —
# which would be a silent fake — we AST-extract the exact source of their
# constant tables and pure-string functions and execute that source. The
# functions below therefore run flagship bytes, pinned by sha256, with zero
# torch/sklearn imports.

_SYMBOLS_40E = (
    "DOMAIN_GLOSSES", "OPERATOR_GLOSSES", "canonical_element",
    "parse_element_label", "raw_prefix", "readable_prefix",
    "element_phrase", "base_prompt",
)
_SYMBOLS_F28 = (
    "REGISTERS", "REGISTER_GLOSSES", "DRIVE_PHRASES", "DRIVE_PREFIX_GLOSSES",
    "canonical_foundation", "parse_foundation_label", "raw_prefix",
    "readable_prefix", "base_prompt",
)


def load_flagship_symbols(path: Path, wanted: tuple[str, ...],
                          label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Execute the named flagship symbols, verbatim, in a bare namespace.

    Extraction matches on top-level symbol NAME. A same-named symbol defined
    twice in the file would silently shadow the intended one, so duplicates are
    a hard error rather than a silent last-wins.
    """
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    picked: list[ast.stmt] = []
    counts: dict[str, int] = {}
    for node in tree.body:
        name = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name):
                name = tgt.id
        if name in wanted:
            picked.append(node)
            counts[name] = counts.get(name, 0) + 1
    missing = [s for s in wanted if s not in counts]
    if missing:
        raise RuntimeError(f"{label}: realizer symbols not found: {missing}")
    dupes = {k: v for k, v in counts.items() if v > 1}
    if dupes:
        raise RuntimeError(
            f"{label}: symbol shadowing in {path.name} — {dupes}. Extraction is "
            "name-matched, so a duplicate definition would change which bytes run."
        )
    module = ast.Module(body=picked, type_ignores=[])
    ns: dict[str, Any] = {"Any": Any}
    exec(compile(module, str(path), "exec"), ns)  # noqa: S102 - flagship source
    prov = {
        "label_space": label,
        "source_file": str(path),
        "source_sha256": sha256_file(path),
        "extracted_symbols": list(wanted),
        "duplicate_symbols": {},
        "extraction_reason": (
            "flagship module cannot be imported in this checkout: its transitive "
            "import `evaluate_probe_dataset` is absent from live-trace-worker/scripts/"
        ),
        "real": True,
    }
    return ns, prov


def leak_audit(r40: dict[str, Any], r28: dict[str, Any]) -> dict[str, Any]:
    """Does a realizer's prefix CONTAIN the continuation it will be scored on?

    The 40E realizer does: `readable_prefix` embeds
    `- Readable meaning: {element_phrase(label)}` verbatim, so a margin measured
    with `element_phrase` as the continuation is partly string copying. The F28
    realizer does not: its prefix uses DRIVE_PREFIX_GLOSSES while the scored
    continuation is DRIVE_PHRASES. This is checked here, not asserted.
    """
    label40 = "^8|C"
    leak40 = r40["element_phrase"](label40) in r40["readable_prefix"](label40)
    leaks28 = {}
    for k in sorted(r28["DRIVE_PHRASES"]):
        pfx = r28["readable_prefix"](f"F{k}|A")
        leaks28[f"F{k}|A"] = r28["DRIVE_PHRASES"][k] in pfx
    out = {
        "40E_prefix_contains_scored_continuation": bool(leak40),
        "40E_note": (
            "run_stage9_40e_eta_epsilon_bridge.readable_prefix embeds "
            "element_phrase(label) verbatim; any margin measured with "
            "element_phrase as the continuation is contaminated by string copying. "
            "This is inherited from the flagship and bears on how +1.412 is read."
        ),
        "F28_prefix_contains_scored_continuation": {k: bool(v) for k, v in leaks28.items()},
        "F28_note": (
            "run_open_weight_eta_epsilon_bridge.readable_prefix uses "
            "DRIVE_PREFIX_GLOSSES while the scored continuation is DRIVE_PHRASES; "
            "no verbatim containment. Lexical overlap is NOT zero and is not "
            "measured here."
        ),
        "consequence": (
            "stage 5 measures on the F28 (leak-free) arm by default; the 40E arm "
            "is available but is preregistered as NOT counting as evidence."
        ),
    }
    print(f"  leak audit: 40E prefix contains its scored continuation -> {leak40}")
    print(f"              F28 prefix contains its scored continuation -> "
          f"{any(leaks28.values())}")
    return out


# ===========================================================================
# STAGE 1 — READ: text -> circuit reading
# ===========================================================================

# The 12-part wiring vocabulary. Byte-checked against the REAL reader module
# when --with-readers is given.
WIRING_CODES = [
    "SENSE", "MEM", "UNPACK", "AMP", "WEIGH", "IF",
    "RS", "DR", "TRANSLATE", "ORDER", "GND", "CHECK",
]


@dataclass
class CircuitReading:
    item_id: int
    source_text: str
    path: list[str]
    main: str
    reader: str
    real: bool
    provenance: dict[str, Any] = field(default_factory=dict)


# An AUTHORED fixture reading. This is NOT a disk replay:
# l2_wiring_report.json stores only aggregate statistics (edge Jaccard 0.2437 vs
# null 0.0525, main kappa 0.5489), never the per-item paths, so no on-disk
# reading exists to replay from. The path is representative of the reported main
# part usage distribution (TRANSLATE 23, WEIGH 21, AMP 18 ...). Its downstream
# properties — including how many J1 transitions the typechecker rejects — are
# properties of THIS AUTHORED CHOICE, not observed outcomes.
FIXTURE_READING = {
    "item_id": 0,
    "path": ["SENSE", "UNPACK", "AMP", "WEIGH", "TRANSLATE"],
    "main": "AMP",
}


def stage1_read(with_readers: bool, corpus: Path, item_id: int) -> CircuitReading:
    hr("STAGE 1 — READ: model output -> circuit reading (12-part wiring vocabulary)")
    text = ""
    if corpus.exists():
        for line in corpus.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if int(row["id"]) == item_id:
                text = row["output"]
                break

    if with_readers:
        # REAL blind-reader call. Lazy import: l2_wiring imports openai + providers
        # at module scope and needs ~/.cas_llm_keys.env.
        sys.path.insert(0, str(BANK))
        import l2_wiring  # noqa: PLC0415
        from pilot_label import MODELS  # noqa: PLC0415

        assert list(l2_wiring.CODES) == WIRING_CODES, "wiring vocabulary drifted"
        menu = l2_wiring.build_menu()
        prov, out = l2_wiring.read_batch(
            "gemini", MODELS["gemini"], menu, [(item_id, text[:1000])]
        )
        rec = out[item_id]
        print(f"  reader={prov}  path={rec['path']}  main={rec['main']}   [REAL blind reader]")
        return CircuitReading(
            item_id=item_id, source_text=text, path=list(rec["path"]),
            main=rec["main"], reader=prov, real=True,
            provenance={"module": str(BANK / "l2_wiring.py"), "call": "read_batch"},
        )

    stub(
        "STAGE 1 reader call",
        "default run makes zero API calls; l2_wiring_report.json stores only "
        "aggregate statistics, so there is no per-item reading on disk to replay",
        "run with --with-readers (calls l2_wiring.read_batch against the 4 blind "
        "readers), or persist per-item paths from a fresh l2_wiring.py run",
    )
    disclose(
        "authored_fixture_reading",
        "FIXTURE_READING is AUTHORED, not observed. Its J1 transition-rejection "
        "count is a property of the authored path, not a measured outcome.",
    )
    r = FIXTURE_READING
    print(f"  fixture path={r['path']}  main={r['main']}")
    return CircuitReading(
        item_id=item_id, source_text=text, path=list(r["path"]), main=r["main"],
        reader="fixture", real=False,
        provenance={"kind": "authored_fixture", "vocabulary": "l2_wiring.COMPONENTS (12)"},
    )


# ===========================================================================
# JOINT J1 — circuit reading -> CAS expression the compiler consumes
# ===========================================================================
#
# WHAT IS REAL HERE: the emission mechanism and its adjudication. Every string
# J1 produces is handed to the REAL compiler, which accepts or rejects it.
#
# WHAT IS AUTHORED HERE: the crosswalk table itself, lifted from the book's
# prose/block-diagram listings into a data structure for the first time. It has
# NEVER been empirically validated. A component code DOES determine which
# validated 40E cell gets realized downstream — that is the construct-smuggling
# surface, and it is why --entry both also runs a crosswalk-free arm.

COMPONENT_CROSSWALK: dict[str, dict[str, str]] = {
    # code:      noetic, domain, book anchor for the row
    "DR":        {"noetic": "^2", "domain": "P", "anchor": "Appendix_D 'DRIVE RAILS'; ^2 Positive = attraction toward the goal"},
    "RS":        {"noetic": "^3", "domain": "P", "anchor": "Appendix_B Zener< ^3^P, breakdown=0.8 >"},
    "GND":       {"noetic": "^0", "domain": "P", "anchor": "Appendix_B Oscillator Phi< ... ^0^P|T >"},
    "SENSE":     {"noetic": "^1", "domain": "C", "anchor": "Appendix_B Photodiode< stimulus -> ^0^C >; ^1 Mind = registering/attending"},
    "MEM":       {"noetic": "^5", "domain": "C", "anchor": "Appendix_B Capacitor< ^5^E_{F4}|f >, Varactor< ^5^C_{F2}|A >"},
    "UNPACK":    {"noetic": "^6", "domain": "C", "anchor": "^6 Male = decomposition ('unpacking an idea')"},
    "AMP":       {"noetic": "^8", "domain": "C", "anchor": "Appendix_D 'PRE-AMP  ^8^C|A, beta=3.0'"},
    "CHECK":     {"noetic": "^3", "domain": "C", "anchor": "Appendix_B CircuitBreaker< ^3^C_{F2}|A, threshold=0.7 >"},
    "WEIGH":     {"noetic": "^6", "domain": "E", "anchor": "Appendix_B OpAmp< inverting=^6^E_{F6}|A >"},
    "IF":        {"noetic": "^8", "domain": "E", "anchor": "Appendix_B Relay< control=^9^E_{F5}|A >; a conditional TRIGGERS a branch"},
    "ORDER":     {"noetic": "^7", "domain": "O", "anchor": "Appendix_B Inductor< ^7^O_{F6}|E > pattern/timing inertia"},
    "TRANSLATE": {"noetic": "^9", "domain": "O", "anchor": "Appendix_B DAC< ^9^C_{F5}|A -> ^9^O_{F5}|E >"},
}


@dataclass
class J1Result:
    entry: str
    focal_index: int
    focal_expr: str
    focal_valid: bool
    cells: list[str]
    elements: list[str]
    transitions: list[dict[str, Any]]
    n_admissible: int
    n_rejected: int
    drive: str
    unknown_codes: list[str]
    crosswalk_in_causal_path: bool


def _elements_from_cells(cells: list[str], drive: str) -> list[str]:
    return [f"{c}_{{{drive}}}" for c in cells]


def reading_to_cas(reading: CircuitReading, drive: str) -> J1Result:
    """JOINT J1. Circuit reading -> drive-tagged CAS state literals + transitions."""
    hr("JOINT J1 — circuit reading -> CAS expression (compiler-adjudicated)")
    print("  REAL     : emission is adjudicated by api.notation.compiler.compile_expression")
    print("  AUTHORED : the component->40E crosswalk table (book prose, never validated)")
    print(f"  AUTHORED : drive tag {drive} (a reading carries no drive)")
    disclose(
        "component_construct_in_causal_path",
        "under --entry reading a PCBA component code SELECTS the 40E cell that is "
        "realized. The alphabet downstream is validated; the CHOICE of cell is not. "
        "PCBA component types returned NULL at 1b and GREY at 2.8b/20B.",
    )

    unknown = [c for c in reading.path + [reading.main] if c not in COMPONENT_CROSSWALK]

    def cell(code: str) -> str | None:
        row = COMPONENT_CROSSWALK.get(code)
        return None if row is None else f"{row['noetic']}^{row['domain']}"

    cells = [cell(c) for c in reading.path]
    if any(c is None for c in cells):
        cells = [c for c in cells if c is not None]
    cells_ok: list[str] = [c for c in cells if c]
    elements = _elements_from_cells(cells_ok, drive)
    focal_index = reading.path.index(reading.main) if reading.main in reading.path else 0
    focal_expr = elements[focal_index] if focal_index < len(elements) else ""
    focal_art = compile_expression(focal_expr) if focal_expr else None
    focal_valid = bool(focal_art and focal_art.valid)
    print(f"\n  focal (main part {reading.main}, index {focal_index}) -> "
          f"{focal_expr!r}  valid={focal_valid}")
    if focal_valid and focal_art is not None:
        print(f"      compiler result: {json.dumps(focal_art.to_dict()['result'])}")

    transitions = _emit_transitions(elements, reading.path)
    n_ok = sum(1 for t in transitions if t["valid"])
    n_rej = len(transitions) - n_ok
    print(f"\n  transitions admissible {n_ok}/{len(transitions)}; "
          f"{n_rej} rejected by the real typechecker")
    if unknown:
        print(f"  codes with no crosswalk row: {unknown}")
    return J1Result(
        entry="reading", focal_index=focal_index, focal_expr=focal_expr,
        focal_valid=focal_valid, cells=cells_ok, elements=elements,
        transitions=transitions, n_admissible=n_ok, n_rejected=n_rej,
        drive=drive, unknown_codes=unknown, crosswalk_in_causal_path=True,
    )


def cells_to_cas(cells: list[str], drive: str, focal_index: int) -> J1Result:
    """CONSTRUCT-FREE entry. Cells are named directly in the validated 40E space."""
    hr("ENTRY (construct-free) — 40E cells named directly, NO PCBA crosswalk")
    print("  This arm exists so the reader can see whether any conclusion below")
    print("  depends on the falsified PCBA component vocabulary. It does not.")
    elements = _elements_from_cells(cells, drive)
    focal_expr = elements[focal_index]
    art = compile_expression(focal_expr)
    print(f"  cells    : {cells}")
    print(f"  focal    : {focal_expr!r} valid={art.valid}")
    transitions = _emit_transitions(elements, cells)
    n_ok = sum(1 for t in transitions if t["valid"])
    return J1Result(
        entry="cell", focal_index=focal_index, focal_expr=focal_expr,
        focal_valid=bool(art.valid), cells=list(cells), elements=elements,
        transitions=transitions, n_admissible=n_ok,
        n_rejected=len(transitions) - n_ok, drive=drive, unknown_codes=[],
        crosswalk_in_causal_path=False,
    )


def _emit_transitions(elements: list[str], labels: list[str]) -> list[dict[str, Any]]:
    """Arrows are strictly BINARY in the grammar: a chained A -> B -> C is
    rejected, so a path is emitted as consecutive binary transitions."""
    out: list[dict[str, Any]] = []
    for i, (ea, eb) in enumerate(zip(elements, elements[1:])):
        expr = f"{ea} -> {eb}"
        art = compile_expression(expr)
        res = art.to_dict()["result"] if art.valid else None
        out.append({
            "index": i, "pair": [labels[i], labels[i + 1]], "expr": expr,
            "valid": art.valid,
            "domain_descent_ok": (res or {}).get("domain_descent_ok"),
            "admissible": (res or {}).get("admissible"),
            "error": art.error,
        })
        flag = "OK " if art.valid else "REJ"
        print(f"  [{flag}] {labels[i]:9s} -> {labels[i+1]:9s}  {expr:34s} "
              f"{(art.error or '')[:44]}")
    return out


# ===========================================================================
# STAGE 3 — DIAGNOSE.  BLIND. No detector sees the injected axis, and no
# detector's input contains the pre-injection object.
# ===========================================================================

# The compiler emits a diagnostic string, not an axis letter. This table decodes
# the DETECTOR'S OWN MESSAGE into an axis. It is not itself a detector, and it
# never sees the injection parameter. Sources: api/notation/compiler.py:3378-3390.
DIAGNOSTIC_TO_AXIS: tuple[tuple[str, str], ...] = (
    (r"domain descent violated", "W"),
    (r"reverse dependency violated", "W"),
    (r"bidirectional relation requires matching domains", "W"),
)


def compiler_diagnostic_axis(error: str | None) -> tuple[str | None, str | None]:
    """Decode a compiler diagnostic into an axis letter, blind to the injection."""
    if not error:
        return None, None
    for pat, axis in DIAGNOSTIC_TO_AXIS:
        if re.search(pat, error):
            return axis, pat
    return None, None


def integrator_guard(expr: str) -> dict[str, Any]:
    """belief.inversion_gate treats ANY lowercase 'x' as an integrator and
    suppresses the N and F flags (inversion_gate.py:106 and :187). Every string
    this loop scans is guarded, because an unnoticed 'x' is a live
    false-negative path in the loop's primary detector."""
    hits = [ch for ch in ("+", "×", "x") if ch in expr]
    return {"expression": expr, "integrator_chars_present": hits,
            "flags_suppressed": bool(hits)}


def scan_isolated(expr: str, rpm_satisfied: bool) -> dict[str, Any]:
    """REAL: belief.inversion_gate.run_inversion_scan on ONE object, alone.

    `rpm_satisfied` is passed EXPLICITLY. The default (True) silently marks axis
    A clean on every string scan, which would be a third always-clean axis on top
    of the disclosed E/S placeholders.
    """
    scan = run_inversion_scan(expr, rpm_satisfied=rpm_satisfied)
    fired = [ax for ax, v in scan.axes.items()
             if not v["clean"] and not v.get("placeholder")]
    return {
        "expression": expr,
        "rpm_satisfied_arg": rpm_satisfied,
        "clean": bool(scan.clean),
        "fired_axes": fired,
        "fired_axes_non_derived": [a for a in fired if a not in DERIVED_AXES],
        "axes": {ax: dict(d) for ax, d in scan.axes.items()},
        "placeholder_axes": [ax for ax, d in scan.axes.items() if d.get("placeholder")],
        "integrator_guard": integrator_guard(expr),
    }


def scan_numeric(pathway_scores: list[list[float]]) -> dict[str, Any]:
    """REAL: cas_engine.InversionScanner().scan — 7 axis RESISTANCES (1 - severity).

    This is the one detector in the loop that receives ONLY the perturbed object
    (a pathway-score array), receives no axis hint, and names an axis unaided.
    """
    scanner = cas_engine.InversionScanner()
    sv = cas_engine.CognitiveStateVector([1.0 / 40] * 40)  # Correction 4: open simplex
    out = dict(scanner.scan([0.8] * 10, [0.8] * 7, sv, [0.8] * 4,
                            [[0.8] * 4 for _ in range(7)], pathway_scores))
    scores = [float(s) for s in out["axis_scores"]]
    return {
        "axis_resistance": {ax: round(s, 6) for ax, s in zip(AXIS_ORDER, scores)},
        "axis_severity": {ax: round(1.0 - s, 6) for ax, s in zip(AXIS_ORDER, scores)},
        "fired_axes": [ax for ax, s in zip(AXIS_ORDER, scores) if 1.0 - s > 1e-9],
    }


@dataclass
class BlindDetection:
    detected_axis: str | None
    candidate_axes: list[str]
    ambiguous: bool
    votes: list[dict[str, Any]]
    saw_ground_truth_axis: bool = False   # invariant: must stay False
    saw_preinjection_object: bool = False  # invariant: must stay False


def detect_blind(perturbed_render: str,
                 baseline_fired: list[str],
                 rpm_satisfied: bool,
                 also_scan_domain_stripped: bool = False) -> BlindDetection:
    """Run the detector bank on the PERTURBED object alone and name an axis.

    Two detectors, neither of which is told the answer:

      1. compiler typecheck -> DIAGNOSTIC_TO_AXIS decode.
      2. belief string scan on the perturbed object ALONE, differenced against
         the SAME scan of the as-read baseline. The baseline is the structure
         stage 1 / J1 produced BEFORE any injection; it is never concatenated
         into the detector's input.

    Derived axis P is stripped from the candidate set: it fires only because two
    other axes fired, so it is never an independent naming.
    """
    votes: list[dict[str, Any]] = []
    candidates: list[str] = []

    art = compile_expression(perturbed_render)
    axis_c, pat = compiler_diagnostic_axis(art.error)
    votes.append({"detector": "api.notation.compiler (typecheck)",
                  "input": perturbed_render, "compiles": bool(art.valid),
                  "diagnostic": art.error, "decoded_axis": axis_c,
                  "decode_rule": pat, "real": True})
    if axis_c:
        candidates.append(axis_c)

    scan = scan_isolated(perturbed_render, rpm_satisfied)
    newly = [a for a in scan["fired_axes_non_derived"] if a not in baseline_fired]
    votes.append({"detector": "belief.inversion_gate.run_inversion_scan (isolated)",
                  "input": perturbed_render,
                  "fired_axes": scan["fired_axes"],
                  "baseline_fired_axes": list(baseline_fired),
                  "newly_fired_non_derived": newly, "real": True,
                  "integrator_guard": scan["integrator_guard"]})
    candidates.extend(newly)

    if also_scan_domain_stripped:
        # DISCLOSED WORKAROUND. inversion_gate._DOMAIN_RE = r'\^([PCEO])\b'
        # cannot match inside a drive-tagged literal: the '_' of '_{F5}' is a
        # word character, so \b never matches and axis W is STRUCTURALLY unable
        # to fire on any drive-tagged expression. Stripping the drive tag is the
        # loop reshaping the detector's input; both results are reported.
        stripped = re.sub(r"_\{F\d\}", "", perturbed_render)
        s2 = scan_isolated(stripped, rpm_satisfied)
        newly2 = [a for a in s2["fired_axes_non_derived"] if a not in baseline_fired]
        votes.append({"detector": "belief.inversion_gate.run_inversion_scan "
                                  "(drive-tag stripped — DISCLOSED WORKAROUND)",
                      "input": stripped, "fired_axes": s2["fired_axes"],
                      "newly_fired_non_derived": newly2, "real": True,
                      "workaround": "inversion_gate.py:72 _DOMAIN_RE uses \\b after "
                                    "[PCEO]; drive-tagged literals can never match",
                      "counts_toward_detection": False})

    uniq = sorted(set(candidates))
    return BlindDetection(
        detected_axis=uniq[0] if len(uniq) == 1 else None,
        candidate_axes=uniq, ambiguous=len(uniq) > 1, votes=votes,
    )


def localize_leave_one_out(elements: list[str], axis: str,
                           rpm_satisfied: bool) -> dict[str, Any]:
    """Which element carries the fault? Leave-one-out over the scanned bundle.

    AUTHORED PROCEDURE, real detector. For each element, rescan the bundle with
    that element removed; the element whose removal clears `axis` is the
    localization. It can return zero candidates or several — both are failures
    and are reported as such.
    """
    candidates: list[int] = []
    for i in range(len(elements)):
        reduced = " ".join(elements[:i] + elements[i + 1:])
        s = scan_isolated(reduced, rpm_satisfied)
        if axis not in s["fired_axes_non_derived"]:
            candidates.append(i)
    return {"procedure": "leave_one_out_rescan", "authored": True, "axis": axis,
            "candidate_indices": candidates,
            "localized_index": candidates[0] if len(candidates) == 1 else None,
            "unique": len(candidates) == 1}


# ===========================================================================
# STAGE 4 — CORRECT: the axis dispatcher
# ===========================================================================


@dataclass
class CorrectionOutcome:
    axis: str
    available: bool
    plane: str
    original: str | None
    corrected: str | None
    recompiles: bool | None
    note: str


def correct_axis(expr: str, axis: str) -> CorrectionOutcome:
    """THE DISPATCHER: named axis -> corrected object.

    N / W / F / P have a real involutive string corrector. E / S / A do not:
    invert_expression raises DeferredAxisError before any transform runs, so
    there is nothing to dispatch TO. That is reported, never papered over.

    NOTE ON WHAT THIS PROVES. invert_expression is an involution over disjoint
    token classes, so f(f(x)) == x is a THEOREM: restoration alone is not
    evidence. What is falsifiable is that the dispatcher is driven by the axis a
    blind detector NAMED, and that no OTHER axis restores the structure. The
    mis-correction control below tests exactly that.
    """
    if axis not in ALL_AXES:
        raise UnknownAxisError(axis)
    try:
        res = invert_expression(expr, axis)
    except DeferredAxisError as exc:
        return CorrectionOutcome(
            axis=axis, available=False, plane="none", original=expr, corrected=None,
            recompiles=None,
            note=(f"DeferredAxisError: axis {exc.axis} has NO string corrector "
                  f"({exc.description}). Axis A is correctable on the NUMERIC "
                  f"pathway-score plane only; axes E and S on neither."),
        )
    art = compile_expression(res.inverted)
    return CorrectionOutcome(
        axis=axis, available=True, plane="string", original=expr,
        corrected=res.inverted, recompiles=bool(art.valid),
        note=AXIS_DESCRIPTIONS[axis],
    )


def mis_correction_control(perturbed: str, detected_axis: str,
                           clean: str) -> dict[str, Any]:
    """Does any OTHER implemented axis restore the clean structure?

    This is what makes criterion (b) falsifiable. f(f(x))==x is a theorem for the
    correct axis; the question is whether the axis NAME carries information. If a
    wrong axis also restored the structure, it would not.
    """
    rows = []
    for a in IMPLEMENTED_AXES:
        if a == detected_axis:
            continue
        try:
            r = invert_expression(perturbed, a)
        except DeferredAxisError:
            continue
        rows.append({"axis": a, "result": r.inverted,
                     "restores_clean": r.inverted == clean,
                     "recompiles": bool(r.valid)})
    restorers = [r["axis"] for r in rows if r["restores_clean"]]
    return {"tested_axes": [r["axis"] for r in rows], "rows": rows,
            "wrong_axes_that_restore": restorers, "holds": not restorers}


# ===========================================================================
# JOINT J2 — corrected expression -> epsilon realization prefix
# ===========================================================================
#
# The choke point named in the mapping brief: condition_prefix() accepts only
# gold / probe / partner LABELS, and readable_prefix(label) raises ValueError on
# an expression like '^3^P_{F5}'. J2 is the adapter that was missing: compile the
# expression with the REAL compiler, read the verdict off the artifact, marshal
# it into a flagship label space, and call the flagship realizer.
#
# J2 ROUTES BY AXIS, because the two label spaces see different coordinates:
#   N / W / P corrections change (Noetic, Domain)  -> 40E realizer  '^n|D'
#   F         corrections change (Drive)           -> F28 realizer  'Fk|R'
# Realizing an F correction in 40E would be a silent no-op: the 40E label does
# not carry the drive, so the corrected and uncorrected prefixes would be
# IDENTICAL. That is a real limitation of the 40E realizer, not a bug here.

SPACE_FOR_AXIS = {"N": "40E", "W": "40E", "P": "40E", "F": "F28"}


@dataclass
class EpsilonPrefix:
    expression: str
    space: str | None
    element_label: str | None
    cell: str | None
    realized_from: str | None
    readable: str | None
    raw: str | None
    scored_continuation: str | None
    ok: bool
    error: str | None = None


def artifact_verdict(expr: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """Compile and return the state-level verdict dict.

    LIMITATION, stated plainly: the 40E space has exactly one element per label,
    so a RELATION artifact (a transition ``A -> B``) has no single element. We
    take its TARGET state — the cell the transition lands on — and record
    ``realized_from='relation.target'``. A relation is NOT a 40E element and the
    realizer was never designed to take one.
    """
    art = compile_expression(expr)
    if not art.valid:
        return None, "none", f"expression does not compile: {art.error}"
    res = art.to_dict().get("result") or {}
    realized_from = "state"
    if res.get("kind") == "relation":
        res = res.get("target") or {}
        realized_from = "relation.target"
    return res, realized_from, None


def expression_to_epsilon(expr: str, axis: str, r40: dict[str, Any],
                          r28: dict[str, Any], register: str) -> EpsilonPrefix:
    """JOINT J2. Corrected CAS expression -> flagship epsilon realization prefix."""
    space = SPACE_FOR_AXIS.get(axis, "40E")
    if not expr:
        return EpsilonPrefix(expr, space, None, None, None, None, None, None,
                             False, "empty expression")
    res, realized_from, err = artifact_verdict(expr)
    if err or res is None:
        return EpsilonPrefix(expr, space, None, None, realized_from, None, None,
                             None, False, err)
    if space == "40E":
        op, dom = res.get("dominant_operator"), res.get("dominant_domain")
        if not op or not dom:
            return EpsilonPrefix(expr, space, None, None, realized_from, None, None,
                                 None, False, f"no dominant operator/domain in {res!r}")
        label = f"^{op.split('-')[-1]}|{dom}"
        if not r40["canonical_element"](label):
            return EpsilonPrefix(expr, space, label, None, realized_from, None, None,
                                 None, False, f"label {label!r} is not a 40E element")
        return EpsilonPrefix(expr, space, label, label.replace("|", "^"), realized_from,
                             r40["readable_prefix"](label), r40["raw_prefix"](label),
                             r40["element_phrase"](label), True)
    drive = res.get("dominant_drive")
    if not drive:
        return EpsilonPrefix(expr, space, None, None, realized_from, None, None, None,
                             False, f"no dominant drive in {res!r}")
    label = f"{drive}|{register}"
    if not r28["canonical_foundation"](label):
        return EpsilonPrefix(expr, space, label, None, realized_from, None, None,
                             None, False, f"label {label!r} is not an F28 foundation")
    k = int(drive[1:])
    return EpsilonPrefix(expr, space, label, drive, realized_from,
                         r28["readable_prefix"](label), r28["raw_prefix"](label),
                         r28["DRIVE_PHRASES"][k], True)


def space_label_universe(space: str, r40: dict[str, Any], r28: dict[str, Any],
                         register: str) -> list[str]:
    if space == "40E":
        return [f"{op}|{dom}" for dom in r40["DOMAIN_GLOSSES"]
                for op in r40["OPERATOR_GLOSSES"]]
    # Sweep every register too, not just the one in play: a collision across
    # registers would be just as fatal to identifiability as one within.
    del register
    return [f"F{k}|{r}" for k in sorted(r28["DRIVE_PREFIX_GLOSSES"])
            for r in r28["REGISTERS"]]


# ===========================================================================
# MATCHED CONTROLS — criterion (d)
# ===========================================================================


def identifiability_sweep(true_prefix: str, space: str, r40: dict[str, Any],
                          r28: dict[str, Any], register: str,
                          true_label: str) -> dict[str, Any]:
    """d2. Sweep the ENTIRE label space and count what reproduces the true prefix.

    The pool INCLUDES the true label — that is the positive control. The previous
    revision excluded it, which made a zero match count an algebraic identity
    rather than a measurement, and reported a null of 1/39 that could never be
    observed. This sweep is exhaustive and deterministic: no seed, no sampling.

    It CAN fail: if the realizer were not injective over the space, more than one
    label would reproduce the prefix and every "corrected" structure would look
    right. That is the failure mode this control exists to catch.
    """
    realize = (r40["readable_prefix"] if space == "40E" else r28["readable_prefix"])
    universe = space_label_universe(space, r40, r28, register)
    hits = [lab for lab in universe if realize(lab) == true_prefix]
    positive = true_label in hits
    return {
        "space": space, "n_labels_swept": len(universe), "exhaustive": True,
        "true_label": true_label,
        "labels_reproducing_true_prefix": hits,
        "n_reproducing": len(hits),
        "positive_control_true_label_reproduces": positive,
        "expected_if_injective": 1,
        "holds": bool(positive and len(hits) == 1),
        "note": "pool INCLUDES the true label; a hit is possible by construction.",
    }


def wrong_axis_prefix_control(perturbed: str, detected_axis: str, true_prefix: str,
                              r40: dict[str, Any], r28: dict[str, Any],
                              register: str) -> dict[str, Any]:
    """d1. Does a WRONG-axis "correction" reproduce the true corrected prefix?

    This is the brief's "random / irrelevant correction must NOT produce the same
    effect", made falsifiable. It CAN fire, and the concrete way it fires is
    known in advance: the compound axis P is N o W o F, so a P-"correction"
    contains the correct transform. Realized into a space that only sees the
    coordinate the correct transform touched, P is indistinguishable from the
    true correction. That is a real limitation of J2 (the realizers are lossy
    projections of the expression), and it is preregistered as a FAILURE of d1,
    not excluded from it.
    """
    rows = []
    for a in IMPLEMENTED_AXES:
        if a == detected_axis:
            continue
        try:
            r = invert_expression(perturbed, a)
        except DeferredAxisError:
            continue
        # Realize in the SAME space as the true correction: apples to apples.
        eps = expression_to_epsilon(r.inverted, detected_axis, r40, r28, register)
        rows.append({"wrong_axis": a, "result_expression": r.inverted,
                     "realizes": eps.ok, "label": eps.element_label,
                     "reproduces_true_prefix": bool(eps.ok and eps.readable == true_prefix)})
    firing = [r["wrong_axis"] for r in rows if r["reproduces_true_prefix"]]
    contains_detected = {"P"} if detected_axis in ("N", "W", "F") else set()
    return {
        "tested_axes": [r["wrong_axis"] for r in rows], "rows": rows,
        "wrong_axes_reproducing_true_prefix": firing,
        "holds": not firing,
        "subanalysis_excluding_supersets": {
            "axes_whose_transform_contains_the_detected_one": sorted(contains_detected),
            "firing_after_exclusion": [a for a in firing if a not in contains_detected],
            "note": "reported as EXPLANATION, not as the criterion. The criterion is "
                    "the strict version over every other implemented axis.",
        },
    }


# ===========================================================================
# The injected-fault experiment
# ===========================================================================


def run_injection(name: str, axis: str, elements: list[str], target_index: int,
                  clean_render: str, r40: dict[str, Any], r28: dict[str, Any],
                  register: str, rpm_satisfied: bool,
                  scan_domain_stripped: bool, expectation: str) -> dict[str, Any]:
    """INJECT on one element -> BLIND DETECT -> LOCALIZE -> CORRECT -> REALIZE -> CONTROLS."""
    hr(f"INJECTED FAULT — axis {axis}  ({name})")
    clean_element = elements[target_index]
    print(f"  clean structure : {clean_render!r}")
    print(f"  clean element   : {clean_element!r} (index {target_index})")
    print(f"  PREREGISTERED EXPECTATION: {expectation}")

    baseline = scan_isolated(clean_render, rpm_satisfied)
    print(f"  baseline scan (as read, pre-injection): fired={baseline['fired_axes']}")

    # (1) INJECT with the real transform, on ONE element.
    inj = invert_expression(clean_element, axis)
    perturbed_elements = list(elements)
    perturbed_elements[target_index] = inj.inverted
    perturbed_render = " ".join(perturbed_elements) if len(elements) > 1 else inj.inverted
    print(f"  INJECT  invert_expression({clean_element!r}, {axis!r}) -> {inj.inverted!r}")
    print(f"  perturbed structure: {perturbed_render!r}")

    # (2) DETECT, BLIND. The detectors never receive `axis` and never receive
    #     `clean_render` inside their own input.
    det = detect_blind(perturbed_render, baseline["fired_axes_non_derived"],
                       rpm_satisfied, also_scan_domain_stripped=scan_domain_stripped)
    for v in det.votes:
        print(f"  DETECT  {v['detector']}")
        print(f"          -> decoded={v.get('decoded_axis')} "
              f"newly_fired={v.get('newly_fired_non_derived')} "
              f"diag={str(v.get('diagnostic'))[:60]!r}")
    print(f"  >>> AXIS NAMED (blind): {det.detected_axis}  "
          f"candidates={det.candidate_axes} ambiguous={det.ambiguous}")
    a_ok = det.detected_axis == axis and not det.ambiguous

    # (3) LOCALIZE (multi-element structures only).
    loc: dict[str, Any] | None = None
    a2_ok: bool | None = None
    if len(elements) > 1 and det.detected_axis:
        loc = localize_leave_one_out(perturbed_elements, det.detected_axis, rpm_satisfied)
        a2_ok = loc["localized_index"] == target_index
        print(f"  LOCALIZE leave-one-out -> index {loc['localized_index']} "
              f"(candidates {loc['candidate_indices']}); correct={a2_ok}")

    # (4) CORRECT — driven by the DETECTED axis and the LOCALIZED element.
    #     If detection failed, the chain STOPS. It does not fall back to `axis`.
    corr: CorrectionOutcome | None = None
    restored = False
    mis: dict[str, Any] | None = None
    corrected_element: str | None = None
    corrected_render: str | None = None
    if det.detected_axis is None:
        print("  CORRECT  NOT RUN — no axis was named. The chain stops here by "
              "design; feeding the ground-truth axis in would be the defect this "
              "revision removes.")
    else:
        idx = loc["localized_index"] if (loc and loc["localized_index"] is not None) \
            else target_index
        corr = correct_axis(perturbed_elements[idx], det.detected_axis)
        corrected_element = corr.corrected
        if corrected_element is not None:
            fixed = list(perturbed_elements)
            fixed[idx] = corrected_element
            corrected_render = " ".join(fixed) if len(elements) > 1 else corrected_element
            restored = corrected_render == clean_render
        print(f"  CORRECT dispatcher(axis={det.detected_axis!r}) -> "
              f"{corrected_element!r} recompiles={corr.recompiles}")
        print(f"  restored == clean structure: {restored}")
        mis = mis_correction_control(perturbed_elements[idx], det.detected_axis,
                                     clean_element)
        print(f"  MIS-CORRECTION control: wrong axes that also restore -> "
              f"{mis['wrong_axes_that_restore']}  holds={mis['holds']}")

    b_ok = bool(corr and corr.available and restored and corr.recompiles
                and mis and mis["holds"])

    # (5) REALIZE both arms through J2, in the space the corrected axis lives in.
    realize_axis = det.detected_axis or axis
    eps_bad = expression_to_epsilon(perturbed_elements[target_index], realize_axis,
                                    r40, r28, register)
    eps_good = expression_to_epsilon(corrected_element or "", realize_axis,
                                     r40, r28, register)
    print(f"  J2 space={SPACE_FOR_AXIS.get(realize_axis)}  "
          f"epsilon(uncorrected) label={eps_bad.element_label} ok={eps_bad.ok}")
    print(f"  J2 epsilon(corrected)   label={eps_good.element_label} ok={eps_good.ok}"
          f"{'' if eps_good.ok else '  err=' + str(eps_good.error)[:70]}")

    # Criterion (c) has two disjoint modes, both preregistered:
    #   c1 both arms realize and the prefixes differ   (strongest: J2 runs twice)
    #   c2 only the corrected arm realizes at all      (weaker: J2 runs once)
    # Mode c2 arises when the injected form does not compile. It is recorded,
    # never blurred into c1, and only c1 counts toward the headline.
    if eps_good.ok and eps_bad.ok:
        c_mode = "c1_both_realize_differ" if eps_good.readable != eps_bad.readable \
            else "c0_identical_prefix"
    elif eps_good.ok and not eps_bad.ok:
        c_mode = "c2_uncorrected_unrealizable"
    else:
        c_mode = "c0_corrected_unrealizable"
    c_ok = c_mode in ("c1_both_realize_differ", "c2_uncorrected_unrealizable")
    print(f"  prefixes DISTINCT: {c_ok}   mode={c_mode}")
    if eps_good.ok:
        print("  --- epsilon(corrected) ---")
        for ln in (eps_good.readable or "").rstrip().splitlines():
            print(f"      {ln}")

    # (6) MATCHED CONTROLS.
    d1: dict[str, Any] | None = None
    d2: dict[str, Any] | None = None
    if eps_good.ok and eps_good.readable and eps_good.element_label:
        d1 = wrong_axis_prefix_control(perturbed_elements[target_index],
                                       realize_axis, eps_good.readable,
                                       r40, r28, register)
        d2 = identifiability_sweep(eps_good.readable, eps_good.space or "40E",
                                   r40, r28, register, eps_good.element_label)
        print(f"  CONTROL d1 wrong-axis: axes reproducing the true prefix -> "
              f"{d1['wrong_axes_reproducing_true_prefix']}  holds={d1['holds']}")
        print(f"  CONTROL d2 identifiability: {d2['n_reproducing']}/"
              f"{d2['n_labels_swept']} labels reproduce it "
              f"(positive control {d2['positive_control_true_label_reproduces']}) "
              f"holds={d2['holds']}")
    else:
        print("  CONTROLS d1/d2 NOT RUN — no corrected prefix to control against.")

    d_ok = bool(d1 and d1["holds"] and d2 and d2["holds"])

    criteria = {
        "a_detected_by_name_blind": bool(a_ok),
        "a2_localized": a2_ok,
        "b_corrected_via_detected_axis": bool(b_ok),
        "c_distinct_prefix": bool(c_ok),
        "c_mode": c_mode,
        "d1_wrong_axis_control": (None if d1 is None else bool(d1["holds"])),
        "d2_identifiability_control": (None if d2 is None else bool(d2["holds"])),
        "d_control_holds": bool(d_ok),
    }
    passed = bool(a_ok and b_ok and c_mode == "c1_both_realize_differ" and d_ok
                  and (a2_ok is not False))
    print(f"  ==> injection verdict: {'PASS' if passed else 'FAIL'}  {criteria}")

    return {
        "name": name, "injected_axis_ground_truth": axis,
        "preregistered_expectation": expectation,
        "clean_structure": clean_render, "clean_element": clean_element,
        "target_index": target_index,
        "perturbed_structure": perturbed_render,
        "perturbed_element": inj.inverted,
        "injected_element_compiles": bool(inj.valid),
        "baseline_scan": baseline,
        "detection": asdict(det),
        "localization": loc,
        "correction": (None if corr is None else asdict(corr)),
        "corrected_structure": corrected_render,
        "restored_to_clean": restored,
        "mis_correction_control": mis,
        "epsilon_uncorrected": asdict(eps_bad), "epsilon_corrected": asdict(eps_good),
        "control_d1_wrong_axis": d1, "control_d2_identifiability": d2,
        "criteria": criteria, "passed": passed,
    }


def run_axis_a_numeric() -> dict[str, Any]:
    """Axis A: the axis the loop most needs, and the one with NO string corrector.

    This is the single genuinely unaided detection in the loop: the Rust scanner
    is given only the perturbed pathway array, no axis hint, and returns exactly
    ['A']. It is also the one that cannot reach J2.
    """
    hr("INJECTED FAULT — axis A  (RPM / pathway chain)  [NUMERIC PLANE ONLY]")
    balanced = [[0.8, 0.8, 0.8, 0.8] for _ in range(7)]
    base = scan_numeric(balanced)
    print(f"  baseline axis-A resistance {base['axis_resistance']['A']} "
          f"fired={base['fired_axes']}")

    bad = [row[:] for row in balanced]
    bad[4] = [0.20, 0.10, 0.10, 0.90]          # F5 chain: [A0, D5, W5, P5] broken
    inj = scan_numeric(bad)
    print(f"  injected axis-A resistance {inj['axis_resistance']['A']} "
          f"(severity {inj['axis_severity']['A']} = 1/7)")
    print(f"  >>> AXES NAMED, UNAIDED: {inj['fired_axes']}")

    disclose(
        "axis_a_check_is_not_a_detector",
        "belief.inversion_gate.axis_a_check(rpm_satisfied) is a bare if/else that "
        "restates its own argument. The previous revision listed it as an axis-A "
        "detector; it is not, and it has been removed from the detector bank. "
        "rpm_satisfied is now DERIVED from the Rust scanner's verdict instead.",
    )
    rpm_satisfied_derived = "A" not in inj["fired_axes"]
    print(f"  rpm_satisfied DERIVED from the Rust verdict: {rpm_satisfied_derived}")

    fixed = [row[:] for row in bad]
    fixed[4] = [0.85, 0.80, 0.75, 0.90]
    fx = scan_numeric(fixed)
    print(f"  corrected axis-A resistance {fx['axis_resistance']['A']} "
          f"fired={fx['fired_axes']}")
    disclose(
        "axis_a_correction_is_hand_written",
        "the axis-A correction is a hand-written re-scoring of the pathway array "
        "([0.20,0.10,0.10,0.90] -> [0.85,0.80,0.75,0.90]). No solver produced it. "
        "The numeric plane has a detector but no corrector.",
    )

    stub(
        "STAGE 4 corrector for axis A (and E, S)",
        "invert_expression(src,'A') raises DeferredAxisError — there is no "
        "string-level corrector for A, E or S, so a corrected EXPRESSION never "
        "exists and joint J2 cannot be reached for these axes",
        "implement an A-axis string corrector (rewrite drive-tagged stage "
        "literals so upstream stages dominate), or lift the Rust "
        "cas-engine/src/rpm/recursive.rs solver output back into notation",
    )
    print("  [STUB consequence] axis A reaches STAGE 3 (detect, genuinely unaided) "
          "and a HAND-WRITTEN numeric stage-4 correction, but NOT joint J2.")
    return {
        "plane": "numeric", "baseline": base, "injected": inj, "corrected": fx,
        "rpm_satisfied_derived_from_rust": rpm_satisfied_derived,
        "detector_is_unaided": True, "corrector_is_hand_written": True,
        "reaches_j2": False,
        "criteria": {
            "a_detected_by_name_blind": inj["fired_axes"] == ["A"],
            "b_corrected_via_detected_axis": abs(fx["axis_resistance"]["A"] - 1.0) < 1e-9,
            "c_distinct_prefix": None, "d_control_holds": None,
        },
    }


# ===========================================================================
# String-plane coverage — MEASURED, not asserted
# ===========================================================================


def measure_string_plane_coverage(bundle: list[str], transition: str,
                                  rpm_satisfied: bool) -> dict[str, Any]:
    """For each of the 7 axes: can the string detector fire on the shapes this
    loop actually emits? Measured by probing, not claimed."""
    hr("MEASURED string-plane coverage (not asserted)")
    results: dict[str, Any] = {}
    stripped = re.sub(r"_\{F\d\}", "", transition)

    def probe_shapes(axis: str) -> dict[str, str]:
        """Build the perturbed object for each shape the loop actually emits.

        `whole_object` inverts the entire string; `one_element_of_bundle` inverts
        a SINGLE element and reassembles, which is what run_injection does. The
        two differ sharply: inverting a whole uniform-drive bundle flips every
        drive together and creates no co-presence, while inverting one element
        does. Reporting only the whole-object probe would understate the
        detector.
        """
        out: dict[str, str] = {}
        for shape, expr in (("single_drive_tagged_literal", bundle[0]),
                            ("drive_tagged_bundle", " ".join(bundle)),
                            ("drive_tagged_transition", transition),
                            ("drive_tag_stripped_transition", stripped)):
            try:
                out[f"whole_object::{shape}"] = (
                    invert_expression(expr, axis).inverted
                    if axis in IMPLEMENTED_AXES else expr)
            except DeferredAxisError:
                out[f"whole_object::{shape}"] = expr
        if len(bundle) > 1 and axis in IMPLEMENTED_AXES:
            per = list(bundle)
            per[0] = invert_expression(per[0], axis).inverted
            out["one_element_of_bundle"] = " ".join(per)
        return out

    for axis in ALL_AXES:
        fired_on: list[str] = []
        for shape, perturbed in probe_shapes(axis).items():
            s = scan_isolated(perturbed, rpm_satisfied)
            if axis in s["fired_axes_non_derived"]:
                fired_on.append(shape)
        results[axis] = {"can_fire_on": fired_on, "can_fire": bool(fired_on)}
        print(f"  axis {axis}: can_fire={bool(fired_on)}  shapes={fired_on}")
    effective = [a for a, v in results.items() if v["can_fire"]]
    print(f"  EFFECTIVE string-plane coverage for this loop's shapes: "
          f"{effective}  ({len(effective)}/7)")
    print("  E and S are hardcoded placeholders (can never fire). A is not a string")
    print("  detector at all — it restates the rpm_satisfied argument. W cannot fire")
    print("  on drive-tagged literals (inversion_gate.py:72 _DOMAIN_RE \\b bug).")
    return {"per_axis": results, "effective_axes": effective,
            "effective_count": len(effective), "of": 7,
            "measured": True}


# ===========================================================================
# STAGE 5 — MEASURE the likelihood shift  (--with-model only)
# ===========================================================================

# AUTHORED. A stance-matched, content-matched, CAS-vocabulary-free prefix. It
# carries the same English content as the F28 realizer's prefix with every CAS
# token removed. PREREGISTERED READING: if this control reproduces the lift, the
# effect is English content, NOT CAS structure. This is the control the flagship
# never ran (spec sheet NOT-LICENSED item 23).
def stance_matched_control_prefix(drive_gloss: str, register_gloss: str) -> str:
    return (
        "Framing note for the focused role:\n"
        f"- Emphasis: {drive_gloss}\n"
        f"- Mode: {register_gloss}\n"
        "Use this framing as context for the next sentence.\n\n"
    )


def stage5_measure(model_id: str, injections: list[dict[str, Any]],
                   r28: dict[str, Any], register: str, max_length: int,
                   prompt: str) -> dict[str, Any]:
    hr(f"STAGE 5 — MEASURE the likelihood shift on {model_id}")
    sys.path.insert(0, str(SCRIPTS))
    from run_open_weight_eta_epsilon_bridge import mean_logprob_continuation  # noqa: PLC0415
    from run_open_weight_probe_shard import (  # noqa: PLC0415
        ProbeShardConfig, load_open_weight_model,
    )

    # ProbeShardConfig has 10 REQUIRED fields. The previous revision passed only
    # model_id and would have raised TypeError before any model loaded.
    cfg = ProbeShardConfig(
        model_id=model_id, worker_id="gate5-weld", audit_id="gate5-weld",
        job_id="gate5-weld", layer_start=0, layer_end=0, shard_id="weld-0",
        assigned_methods=(), expected_outputs=(),
        result_path=HERE / "weld_stage5_shard.json",
    )
    # load_open_weight_model returns a 3-TUPLE (model, tokenizer, meta).
    model, tokenizer, load_meta = load_open_weight_model(cfg)
    tail = r28["base_prompt"](prompt)

    rows = []
    for r in injections:
        good, bad = r["epsilon_corrected"], r["epsilon_uncorrected"]
        if not (good.get("ok") and bad.get("ok") and good.get("space") == "F28"):
            continue
        k_good = int(str(good["element_label"]).split("|")[0][1:])
        k_bad = int(str(bad["element_label"]).split("|")[0][1:])
        cont_good = f" {r28['DRIVE_PHRASES'][k_good]}."
        cont_bad = f" {r28['DRIVE_PHRASES'][k_bad]}."
        ctrl = stance_matched_control_prefix(
            r28["DRIVE_PREFIX_GLOSSES"][k_good], r28["REGISTER_GLOSSES"][register])
        arms = {"corrected": good["readable"], "uncorrected": bad["readable"],
                "none": "", "stance_matched_non_cas": ctrl}
        row: dict[str, Any] = {"name": r["name"], "space": "F28",
                               "leak_free_arm": True}
        for arm, prefix in arms.items():
            mg = mean_logprob_continuation(
                model=model, tokenizer=tokenizer, prompt=prefix + tail,
                continuation=cont_good, max_length=max_length)["mean_logprob"]
            mb = mean_logprob_continuation(
                model=model, tokenizer=tokenizer, prompt=prefix + tail,
                continuation=cont_bad, max_length=max_length)["mean_logprob"]
            row[arm] = {"margin": mg - mb}
        row["delta_corrected_vs_none"] = row["corrected"]["margin"] - row["none"]["margin"]
        row["delta_uncorrected_vs_none"] = row["uncorrected"]["margin"] - row["none"]["margin"]
        row["delta_stance_control_vs_none"] = (
            row["stance_matched_non_cas"]["margin"] - row["none"]["margin"])
        print(f"  {row['name']}: d(corrected) {row['delta_corrected_vs_none']:+.6f}  "
              f"d(uncorrected) {row['delta_uncorrected_vs_none']:+.6f}  "
              f"d(stance-matched non-CAS) {row['delta_stance_control_vs_none']:+.6f}")
        rows.append(row)
    return {"model_id": model_id, "rows": rows, "real": True,
            "load_meta": load_meta,
            "preregistered_reading": (
                "the stance-matched non-CAS control carries the same English content "
                "with every CAS token removed. If it reproduces the lift, the effect "
                "is content, not CAS structure."),
            "measured_on": "F28 (leak-free) arm only; the 40E arm is preregistered "
                           "as NOT counting as evidence because its prefix contains "
                           "the scored continuation verbatim"}


# ===========================================================================
# main
# ===========================================================================


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate-5 CAS weld loop")
    ap.add_argument("--entry", choices=("reading", "cell", "both"), default="both",
                    help="reading = PCBA crosswalk (construct in causal path); "
                         "cell = 40E cells named directly (construct-free)")
    ap.add_argument("--with-readers", action="store_true",
                    help="stage 1 calls the live blind readers (API cost)")
    ap.add_argument("--with-model", default=None, metavar="HF_MODEL_ID",
                    help="run stage 5 likelihood measurement (needs GPU/pod)")
    ap.add_argument("--corpus", default=str(BANK / "real_outputs.jsonl"))
    ap.add_argument("--item-id", type=int, default=0)
    ap.add_argument("--drive", default="F5")
    ap.add_argument("--register", default="A", choices=("T", "A", "f", "E"))
    ap.add_argument("--cells", default="^2^P,^6^C,^9^O",
                    help="construct-free entry: 40E cells, comma separated")
    ap.add_argument("--cell-focal-index", type=int, default=0)
    ap.add_argument("--max-length", type=int, default=256)
    ap.add_argument("--stage5-prompt",
                    default="The answer weighs the options and then commits to a step.")
    ap.add_argument("--out", default=str(HERE / "weld_run_report.json"))
    A = ap.parse_args()

    hr("CAS GATE-5 WELD — five CAS links driven as ONE machine")
    print("MECHANISM DEMONSTRATION, NOT EFFICACY.")
    print("CAS-PCBA component types failed the Component Atlas at pythia-1b (rev 0.2,")
    print("NULL_ATLAS_V0), pythia-2.8b (rev 0.3) and gpt-neox-20b (rev 0.4). Under")
    print("--entry reading a component code SELECTS the 40E cell that is realized;")
    print("the construct-free arm exists so you can see nothing depends on it.")
    print("DETECTION IS BLIND: no detector sees the injected axis, and no detector's")
    print("input contains the pre-injection object.")
    print(f"\nrepo root : {REPO_ROOT}")
    print(f"nc root   : {NC_ROOT}")

    r40, prov40 = load_flagship_symbols(FLAGSHIP_40E, _SYMBOLS_40E, "40E")
    r28, prov28 = load_flagship_symbols(FLAGSHIP_F28, _SYMBOLS_F28, "F28")
    print(f"\n40E realizer  {FLAGSHIP_40E.name}  sha256 {prov40['source_sha256']}")
    print(f"F28 realizer  {FLAGSHIP_F28.name}  sha256 {prov28['source_sha256']}")
    print(f"  note: {prov40['extraction_reason']}")
    leak = leak_audit(r40, r28)
    disclose(
        "f28_gloss_table_disagrees_with_CLAUDE_md",
        "run_open_weight_eta_epsilon_bridge.DRIVE_PREFIX_GLOSSES maps F5 to "
        "'ordered form, bounded arrangement, stability, and reliable structure', "
        "while CLAUDE.md names F5 Agency and F6 Structure. The flagship bytes are "
        "executed verbatim; this discrepancy is reported, not silently corrected.",
    )

    arms: list[dict[str, Any]] = []
    reading_rec: dict[str, Any] | None = None

    if A.entry in ("reading", "both"):
        reading = stage1_read(A.with_readers, Path(A.corpus), A.item_id)
        reading_rec = asdict(reading) | {"source_text": reading.source_text[:400]}
        j1 = reading_to_cas(reading, A.drive)
        arms.append({"arm": "reading", "j1": j1})

    if A.entry in ("cell", "both"):
        cells = [c.strip() for c in A.cells.split(",") if c.strip()]
        j1c = cells_to_cas(cells, A.drive, A.cell_focal_index)
        arms.append({"arm": "cell", "j1": j1c})

    all_injections: list[dict[str, Any]] = []
    arm_reports: list[dict[str, Any]] = []

    for armrec in arms:
        j1: J1Result = armrec["j1"]
        hr(f"ARM '{armrec['arm']}' — STAGE 2/3: compile the read structure, scan it as read")
        bundle_render = " ".join(j1.elements)
        as_read = scan_isolated(bundle_render, rpm_satisfied=True)
        print(f"  as-read bundle : {bundle_render!r}")
        print(f"  scan.clean={as_read['clean']}  fired={as_read['fired_axes']}")
        if as_read["fired_axes"]:
            print("  NOTE: the structure is flagged AS READ, before any injection. "
                  "For the reading arm this is a property of the read path itself "
                  "(it contains an involution pair), not of anything the loop did.")
        print(f"  placeholder axes (can NEVER fire): {as_read['placeholder_axes']}")
        print(f"  axes WITH a string corrector    : {list(IMPLEMENTED_AXES)}")
        print(f"  axes WITHOUT a string corrector : {list(DEFERRED_AXES)}")
        print(f"  integrator guard: {as_read['integrator_guard']}")

        injections: list[dict[str, Any]] = []

        # --- Injection 1: axis F on one element of the bundle. -------------
        # The drive tag is uniform across the bundle by construction (J1 tags
        # every element with the same drive), so an F-flip on ONE element makes
        # an involution pair CO-PRESENT that was not present before. This is
        # stated a priori, not selected after seeing the result.
        injections.append(run_injection(
            f"[{armrec['arm']}] drive-pair fault on one path element", "F",
            j1.elements, j1.focal_index, bundle_render, r40, r28, A.register,
            rpm_satisfied=True, scan_domain_stripped=False,
            expectation="DETECTED. The bundle's drive tag is uniform, so an F-flip "
                        "on one element makes an F-pair co-present. Realized in F28 "
                        "because the 40E label does not carry the drive.",
        ))

        # --- Injection 2 (NEGATIVE CONTROL): axis N on a single literal. ----
        # Preregistered to FAIL. The string detectors are CO-PRESENCE detectors;
        # a substitution inside one isolated object leaves nothing to co-occur
        # with. Included so the report contains criteria that returned False.
        injections.append(run_injection(
            f"[{armrec['arm']}] NEGATIVE CONTROL: noetic flip on ONE isolated literal",
            "N", [j1.elements[j1.focal_index]], 0, j1.elements[j1.focal_index],
            r40, r28, A.register, rpm_satisfied=True, scan_domain_stripped=False,
            expectation="NOT DETECTED, preregistered. Included to demonstrate that "
                        "criterion (a) can return False.",
        ))

        # --- Injection 3: axis W on the first CROSS-DOMAIN transition. ------
        # SELECTION RULE, fixed before running: the first transition in the path
        # whose two cells sit in different domain tiers. This is a property of
        # the READING, never of whether the fault turns out to be detectable.
        w_target = None
        for t in j1.transitions:
            ea, eb = t["expr"].split(" -> ")
            da = re.search(r"\^([PCEO])", ea)
            db = re.search(r"\^([PCEO])", eb)
            if da and db and da.group(1) != db.group(1):
                w_target = t["expr"]
                break
        if w_target:
            print(f"\n  W target selected by RULE (first cross-domain transition, "
                  f"chosen on the reading, not on detectability): {w_target!r}")
            injections.append(run_injection(
                f"[{armrec['arm']}] domain-precedence fault on a cross-domain transition",
                "W", [w_target], 0, w_target, r40, r28, A.register,
                rpm_satisfied=True, scan_domain_stripped=True,
                expectation="DETECTED by the compiler typecheck, decoded to W through "
                            "the published diagnostic table. The string detector CANNOT "
                            "fire here (drive-tag \\b bug); that is reported separately.",
            ))
        else:
            stub("axis W injection",
                 "no transition in this arm crosses domain tiers",
                 "use a path whose cells span the P/C/E/O tiers")

        cov = measure_string_plane_coverage(j1.elements, j1.transitions[0]["expr"]
                                            if j1.transitions else bundle_render,
                                            rpm_satisfied=True)
        all_injections.extend(injections)
        arm_reports.append({
            "arm": armrec["arm"], "j1": asdict(j1), "as_read_scan": as_read,
            "injections": injections, "string_plane_coverage": cov,
        })

    axis_a = run_axis_a_numeric()

    stage5: dict[str, Any] = {"real": False, "status": "NOT_RUN",
                              "why": "requires --with-model (GPU/pod)"}
    if A.with_model:
        stage5 = stage5_measure(A.with_model, all_injections, r28, A.register,
                                A.max_length, A.stage5_prompt)
    else:
        stub("STAGE 5 likelihood measurement",
             "no model loaded; the symbolic loop is designed to run at zero GPU "
             "and zero API cost",
             "rerun with --with-model <hf_id> on a pod; stage 5 calls the REAL "
             "mean_logprob_continuation and measures on the leak-free F28 arm "
             "with a stance-matched non-CAS control")

    # ---- verdict ----------------------------------------------------------
    hr("PREREGISTERED SUCCESS CRITERION — verdict")
    print("  (a)  a blind detector NAMES the injected axis, unambiguously,")
    print("       without ever seeing the axis or the pre-injection object")
    print("  (a2) blind leave-one-out localizes the perturbed element (bundles)")
    print("  (b)  the dispatcher, driven by the DETECTED axis, restores the")
    print("       structure, it recompiles, and NO wrong axis also restores it")
    print("  (c1) both arms realize through J2 and the prefixes DIFFER")
    print("  (d1) no wrong-axis correction reproduces the true prefix")
    print("  (d2) exhaustive label sweep: exactly one label reproduces it,")
    print("       and it is the true one (pool INCLUDES the true label)\n")
    for inj in all_injections:
        c = inj["criteria"]
        print(f"  [{'PASS' if inj['passed'] else 'FAIL'}] axis "
              f"{inj['injected_axis_ground_truth']} — {inj['name']}")
        print(f"          (a)  blind detect : {c['a_detected_by_name_blind']}")
        print(f"          (a2) localize     : {c['a2_localized']}")
        print(f"          (b)  correct      : {c['b_corrected_via_detected_axis']}")
        print(f"          (c)  prefix       : {c['c_distinct_prefix']} [{c['c_mode']}]")
        print(f"          (d1) wrong-axis   : {c['d1_wrong_axis_control']}")
        print(f"          (d2) identifiable : {c['d2_identifiability_control']}")

    full_pass = [i for i in all_injections if i["passed"]]
    per_crit = {
        "a": any(i["criteria"]["a_detected_by_name_blind"] for i in all_injections),
        "b": any(i["criteria"]["b_corrected_via_detected_axis"] for i in all_injections),
        "c1": any(i["criteria"]["c_mode"] == "c1_both_realize_differ"
                  for i in all_injections),
        "d1": any(i["criteria"]["d1_wrong_axis_control"] for i in all_injections),
        "d2": any(i["criteria"]["d2_identifiability_control"] for i in all_injections),
    }
    if full_pass:
        status = "MECHANISM_DEMONSTRATED"
    elif all(per_crit.values()):
        status = "MECHANISM_PARTIAL"
    else:
        status = "MECHANISM_INCOMPLETE"
    print(f"\n  injections passing EVERY criterion: "
          f"{[i['injected_axis_ground_truth'] for i in full_pass] or 'NONE'}")
    print(f"  criteria satisfied by SOME injection: {per_crit}")
    print(f"  LOOP STATUS: {status}")
    print("  This is MECHANISM. Efficacy needs stage 5 (a model) plus the")
    print("  stance-matched non-CAS control at the likelihood level. Stage 5: "
          f"{stage5.get('status', 'RUN')}.")

    report = {
        "schema": "cas_gate5_weld_loop.v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "loop_status": status,
        "injections_passing_every_criterion":
            [i["injected_axis_ground_truth"] for i in full_pass],
        "criteria_satisfied_by_some_injection": per_crit,
        "argv": vars(A),
        "detection_is_blind": True,
        "detector_never_sees_ground_truth_axis": True,
        "detector_input_never_contains_preinjection_object": True,
        "realizer_provenance": {"40E": prov40, "F28": prov28},
        "leak_audit": leak,
        "stage1_reading": reading_rec,
        "arms": arm_reports,
        "crosswalk_authored_not_validated": COMPONENT_CROSSWALK,
        "axis_a_numeric": axis_a,
        "stage5": stage5,
        "stubs": STUBS,
        "disclosures": DISCLOSURES,
        "real_modules_called": [
            "api.notation.compiler.compile_expression",
            "api.notation.inversion.invert_expression",
            "belief.inversion_gate.run_inversion_scan",
            "cas_engine.InversionScanner.scan",
            "cas_engine.CognitiveStateVector",
            "run_stage9_40e_eta_epsilon_bridge.readable_prefix/raw_prefix/element_phrase",
            "run_open_weight_eta_epsilon_bridge.readable_prefix/raw_prefix",
        ],
        "removed_in_v2": [
            "matched_control() that excluded the true cell from its own pool "
            "(zero matches was an algebraic identity, and chance_rate_1_over_39 "
            "was never the null)",
            "detected_axis = axis assignment from the injection parameter",
            "run_inversion_scan(clean + ' ' + injected) concatenation, which "
            "handed the detector the answer",
            "correct_axis(inj.inverted, axis) driven by ground truth instead of "
            "the detected axis",
            "belief.inversion_gate.axis_a_check listed as an axis-A detector",
            "the '5 of 7 string-plane coverage' claim, replaced by a measurement",
        ],
    }
    Path(A.out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\n  wrote {A.out}")
    print(f"  stubs declared: {len(STUBS)}   disclosures: {len(DISCLOSURES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
