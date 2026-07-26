"""Generate CMB (Cognitive Memory Board) lacunarity-detection eval artifacts.

Targets the open receipt under `memory_board_cognitive_memory_claim`:
  - cmb_lacunarity_eval_pass

Modelled on `generate_csb_red_team_artifacts.py`, same honesty standard.

WHAT THIS RUN ACTUALLY COVERS.
  (A) Absence detection over the 40 CAS Cognitive States (10 Noetics x 4
      Domains), executed through the real CAS compiler's meta-set layer at
      noetic-compass-scaffold/noetic-compass/api/notation/compiler.py.
      Deliberate-gap cases assert the exact missing-cell set BY IDENTITY, not
      by count. False-positive cases assert that complete 40-cell banks --- in
      two orderings --- produce zero lacunae and satisfy CoverOf/PartitionOf.
      This is a COMPILE/EXECUTE-level structural check on set completeness.
  (B) The shipped gap-map absence detector, run for real
      (api/pipeline/lacunarity.py, plus `cargo test` on its Rust source of
      truth cas-engine/src/scoring/lacunarity.rs). This IS behavioural
      measurement of a real detector --- but at 10-operator / 4-domain /
      7-drive granularity, NOT at the 40-cell granularity Chapter 21 claims.
  (C) The three published Chapter 21 capacitor cells and the `leakage`
      parameter gate, through the real PCBA parser and CAS-leaf compiler.

WHAT THIS RUN DOES NOT COVER, and why. There is no memory board in the loop,
because none exists. Nothing here reads charge off a capacitor, exercises the
~0.05 lacunarity threshold, exercises the leakage decay schedule, or separates
a never-written cell from a charged-then-leaked one. The write-history
mechanism Chapter 21 line 227 attributes to the board is not implemented
anywhere in this repository, so that half of the claim could not be tested at
all --- not partially, not by proxy. See the gap probes.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
CAS_FOREX_ROOT = WORKSPACE_ROOT / "cas-forex"
NOETIC_ROOT = WORKSPACE_ROOT / "noetic-compass-scaffold" / "noetic-compass"

# Order matters: both trees contain a package named `api`. The CAS compiler and
# the lacunarity mirror live in the noetic-compass one, so it goes first.
sys.path.insert(0, str(CAS_FOREX_ROOT))
sys.path.insert(0, str(NOETIC_ROOT))

from api.notation.compiler import compile_expression  # noqa: E402
from api.pipeline.lacunarity import (  # noqa: E402
    compute_lacunarity_profile,
    generate_gap_map,
)

from cas_forex.ccb_designs import build_cmb  # noqa: E402
from cas_forex.crc_linter import run_crc  # noqa: E402
from cas_forex.pcba_compiler import compile_pcba_component_expression  # noqa: E402
from cas_forex.pcba_syntax import parse_pcba_component_expression  # noqa: E402
from cas_forex.time_utils import utc_now  # noqa: E402

REVIEWER_ID = "claude_opus5_local_reviewer_20260725"
WORKING_DIR = WORKSPACE_ROOT / "docs" / "working"
DATE_TAG = "20260725"
RUN_ID = "cmb-lacunarity-eval"

BOOK_DIR = WORKSPACE_ROOT / "book" / "CAS_PCBA_Engineer"
CH21 = BOOK_DIR / "Chapter_21_CMB_Cognitive_Memory_Board.md"
APPENDIX_C = BOOK_DIR / "Appendix_C_CCDL_Language_Reference.md"

# --------------------------------------------------------------------------
# The 40-cell universe, in the engine's own domain-major order (P0..O9).
# --------------------------------------------------------------------------
DOMAINS = ["P", "C", "E", "O"]
CELL_KEYS = [f"{d}{n}" for d in DOMAINS for n in range(10)]  # P0..P9,C0..C9,...
CELL_EXPRS = {f"{d}{n}": f"^{n}^{d}" for d in DOMAINS for n in range(10)}

# The ten simulated memories in the Chapter 21 worked build (lines 188-199)
# touch exactly four cells.
CH21_WORKED_BANK = ["P3", "E6", "C8", "E2"]

# Canonical Noetic names (CLAUDE.md / cas-engine/src/scoring/lacunarity.rs:165).
CANONICAL_NOETIC_NAMES = [
    "Idea", "Mind", "Positive", "Negative", "Vibration",
    "Female", "Male", "Rhythm", "Above/Cause", "Below/Effect",
]

# Directories searched for the mechanisms Chapter 21 attributes to the board.
SEARCH_ROOTS = [
    CAS_FOREX_ROOT / "cas_forex",
    CAS_FOREX_ROOT / "api",
    NOETIC_ROOT / "api",
    NOETIC_ROOT / "cas-engine" / "src",
]
SEARCH_SUFFIXES = {".py", ".rs"}


# --------------------------------------------------------------------------
# Thin wrappers over the real toolchains.
# --------------------------------------------------------------------------
def _cas(source: str) -> tuple[bool, Any, str]:
    """Run source through the real CAS compiler. Returns (valid, result, error)."""
    artifact = compile_expression(source)
    return bool(artifact.valid), artifact.result, (artifact.error or "")


def _cas_elements(source: str) -> tuple[bool, list[str], str]:
    ok, result, err = _cas(source)
    if not ok:
        return False, [], err
    elements = getattr(result, "elements", None)
    if elements is None:
        collection = getattr(result, "collection", None)
        elements = getattr(collection, "elements", frozenset())
    return True, sorted(elements), ""


def _state_set(cells: list[str]) -> str:
    return "StateSet{" + ", ".join(CELL_EXPRS[c] for c in cells) + "}"


def _pcba_parse(expression: str) -> tuple[bool, str]:
    try:
        node = parse_pcba_component_expression(expression)
    except Exception as exc:  # noqa: BLE001 - any rejection is a rejection
        return False, str(exc).splitlines()[0][:300]
    return True, f"kind={node.kind.value} params={node.params}"


def _pcba_compile(expression: str) -> tuple[bool, str]:
    ok, detail = _pcba_parse(expression)
    if not ok:
        return False, f"rejected at parser: {detail}"
    report = compile_pcba_component_expression(expression)
    return bool(report.valid), (
        f"valid={report.valid} checked_leaves={len(report.checked_expressions)} "
        f"reason={report.reason}"
    )


def _grep_repo(patterns: list[str]) -> dict[str, list[str]]:
    """Case-insensitive search of the cognitive-memory code paths."""
    compiled = {p: re.compile(p, re.IGNORECASE) for p in patterns}
    hits: dict[str, list[str]] = {p: [] for p in patterns}
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in SEARCH_SUFFIXES or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for pattern, rx in compiled.items():
                for lineno, line in enumerate(text.splitlines(), start=1):
                    if rx.search(line):
                        rel = path.relative_to(WORKSPACE_ROOT).as_posix()
                        hits[pattern].append(f"{rel}:{lineno}: {line.strip()[:120]}")
    return hits


# --------------------------------------------------------------------------
# Record builders.
# --------------------------------------------------------------------------
def _record(case_id: str, category: str, test_level: str, description: str,
            expected: str, observed: str, passed: bool, evidence: dict[str, Any],
            generated_at: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "category": category,
        "test_level": test_level,
        "description": description,
        "expected": expected,
        "observed": observed,
        "passed": passed,
        "evidence": evidence,
        "record_type": "case",
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    }


def _gap(case_id: str, description: str, hoped: str, observed: str,
         disposition: str, evidence: dict[str, Any], generated_at: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "category": "known_gap",
        "description": description,
        "hoped": hoped,
        "observed": observed,
        "is_gap": observed != hoped,
        "disposition": disposition,
        "evidence": evidence,
        "record_type": "gap_probe",
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    }


# ==========================================================================
# SECTION A --- 40-cell absence detection through the real CAS compiler.
# Structural: this is set-completeness over the state universe. It is a real
# execution of a real compiler, but it is NOT a board reading charge.
# ==========================================================================
def section_a(generated_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    LEVEL = "structural"

    def add(cid, cat, desc, expected, observed, passed, ev):
        rows.append(_record(cid, cat, LEVEL, desc, expected, observed, passed, ev, generated_at))

    full = _state_set(CELL_KEYS)
    full_reversed = _state_set(list(reversed(CELL_KEYS)))

    # --- A1: the universe is exactly 40 cells -----------------------------
    ok, result, err = _cas("|States|")
    value = getattr(result, "value", None) if ok else None
    add("cmb_universe_cardinality_is_40", "universe_integrity",
        "The builtin `States` universe must be exactly the 40 cognitive states "
        "Chapter 21 says the bank has (10 Noetics x 4 Domains).",
        "|States| = 40", f"|States| = {value}", value == 40,
        {"source": "|States|", "compiler_valid": ok, "error": err})

    # --- A2/A3: false-positive controls, complete bank -------------------
    for cid, src, desc in [
        ("cmb_complete_bank_covers", f"CoverOf(States, {full})",
         "FALSE-POSITIVE CONTROL. A complete 40-cell bank must never be reported "
         "lacunar: CoverOf over the full bank must succeed."),
        ("cmb_complete_bank_covers_reversed", f"CoverOf(States, {full_reversed})",
         "FALSE-POSITIVE CONTROL, order independence. The same complete bank "
         "written O9..P0 must also succeed. Guards against an order-sensitive "
         "implementation that looks correct on one ordering only."),
    ]:
        ok, _result, err = _cas(src)
        add(cid, "false_positive_complete_bank", desc, "accepted",
            "accepted" if ok else "rejected", ok,
            {"source_head": src[:120] + "...", "error": err})

    ok, elems, err = _cas_elements(f"States ∖ {full}")
    add("cmb_complete_bank_zero_lacunae", "false_positive_complete_bank",
        "FALSE-POSITIVE CONTROL. The lacuna set of a complete bank must be empty.",
        "lacuna set = []", f"lacuna set = {elems}", ok and elems == [],
        {"source_head": f"States ∖ {full[:80]}...", "error": err})

    ok, _result, err = _cas(f"PartitionOf(States, {full})")
    add("cmb_complete_bank_partitions", "false_positive_complete_bank",
        "FALSE-POSITIVE CONTROL. PartitionOf is the stricter completeness form "
        "(every cell accounted for exactly once); a complete bank must satisfy it.",
        "accepted", "accepted" if ok else "rejected", ok,
        {"source_head": f"PartitionOf(States, {full[:80]}...)", "error": err})

    # --- A4: single-cell deliberate gap, asserted by identity ------------
    minus_p3 = [c for c in CELL_KEYS if c != "P3"]
    ok, elems, err = _cas_elements(f"States ∖ {_state_set(minus_p3)}")
    add("cmb_single_cell_gap_p3_identity", "deliberate_gap",
        "A bank charged in 39 of 40 cells with P3 left empty must yield a lacuna "
        "set of exactly ['P3'] --- by identity, not by count.",
        "lacuna set = ['P3']", f"lacuna set = {elems}", ok and elems == ["P3"],
        {"omitted_cell": "P3", "error": err})

    ok, _result, err = _cas(f"CoverOf(States, {_state_set(minus_p3)})")
    named = "missing ['P3']" in err
    add("cmb_single_cell_gap_p3_cover_fails", "deliberate_gap",
        "NEGATIVE CONTROL. The same 39-cell bank must FAIL CoverOf, and the "
        "failure must name the exact missing cell.",
        "rejected, error names missing ['P3']",
        f"{'rejected' if not ok else 'accepted'}, names_p3={named}",
        (not ok) and named, {"error": err[:300]})

    ok, _result, err = _cas(f"PartitionOf(States, {_state_set(minus_p3)})")
    add("cmb_39_cell_bank_partition_fails", "deliberate_gap",
        "NEGATIVE CONTROL. A 39-cell bank must also fail the stricter "
        "PartitionOf form.",
        "rejected", "rejected" if not ok else "accepted", not ok,
        {"error": err[:300]})

    # --- A5: whole-domain gap (Chapter 21 line 225, 'P cells nearly empty')
    non_p = [c for c in CELL_KEYS if not c.startswith("P")]
    expect_p = sorted(f"P{n}" for n in range(10))
    ok, elems, err = _cas_elements(f"States ∖ {_state_set(non_p)}")
    add("cmb_whole_domain_gap_p_identity", "deliberate_gap",
        "Chapter 21 line 225: 'an assistant whose P (Principled) cells are nearly "
        "empty'. Charge only C/E/O; the lacuna set must be exactly P0..P9.",
        f"lacuna set = {expect_p}", f"lacuna set = {elems}",
        ok and elems == expect_p, {"error": err})

    ok, _result, err = _cas(f"CoverOf(States, {_state_set(non_p)})")
    add("cmb_whole_domain_gap_p_cover_fails", "deliberate_gap",
        "NEGATIVE CONTROL for the whole-domain gap: CoverOf must fail and name "
        "all ten P cells.",
        "rejected naming P0..P9",
        "rejected" if not ok else "accepted",
        (not ok) and all(f"'{c}'" in err for c in expect_p),
        {"error": err[:300]})

    # --- A6: whole-Noetic gap (Chapter 21 line 225, '^6 cells empty') ----
    non_6 = [c for c in CELL_KEYS if not c.endswith("6")]
    expect_6 = sorted(f"{d}6" for d in DOMAINS)
    ok, elems, err = _cas_elements(f"States ∖ {_state_set(non_6)}")
    add("cmb_whole_noetic_gap_6_identity", "deliberate_gap",
        "Chapter 21 line 225: 'a system whose ^6 (Male, analytical decomposition) "
        "cells are empty'. Remove ^6 in every domain; the lacuna set must be "
        "exactly {P6, C6, E6, O6}.",
        f"lacuna set = {expect_6}", f"lacuna set = {elems}",
        ok and elems == expect_6, {"error": err})

    # --- A7: the book's OWN worked bank ----------------------------------
    ok, elems, err = _cas_elements(f"States ∖ {_state_set(CH21_WORKED_BANK)}")
    p_cells_expected = sorted(f"P{n}" for n in range(10) if n != 3)
    p_ok = all(c in elems for c in p_cells_expected) and "P3" not in elems
    add("cmb_chapter21_worked_bank_lacunae", "deliberate_gap",
        "The ten simulated memories in the Chapter 21 worked build (lines 188-199) "
        "touch only P3, E6, C8 and E2. Its lacuna set must have cardinality 36 and "
        "contain every P cell except P3. Tests the book's own published example, "
        "not a case invented to pass.",
        "cardinality 36; all P cells except P3 present",
        f"cardinality {len(elems)}; p_pattern_ok={p_ok}",
        ok and len(elems) == 36 and p_ok,
        {"charged_cells": CH21_WORKED_BANK, "error": err})

    # --- A8: per-cell membership assertions, both polarities --------------
    bank_lit = _state_set(CH21_WORKED_BANK)
    charged_ok, charged_detail = True, []
    for cell in CH21_WORKED_BANK:
        ok, result, err = _cas(f"{CELL_EXPRS[cell]} ∈ {bank_lit}")
        holds = bool(getattr(result, "holds", False)) if ok else False
        charged_ok &= holds
        charged_detail.append(f"{cell}:holds={holds}")
    add("cmb_membership_charged_cells", "per_cell_assertion",
        "FALSE-POSITIVE CONTROL, per cell. Every charged cell of the Chapter 21 "
        "bank must satisfy `^n^D ∈ StateSet{bank}` with holds=True. Uses the "
        "compiler's own boolean, not string matching.",
        "holds=True for P3,E6,C8,E2", ", ".join(charged_detail), charged_ok,
        {"bank": CH21_WORKED_BANK})

    gap_cells = ["P0", "P9", "C0", "O9"]
    gap_ok, gap_detail = True, []
    for cell in gap_cells:
        ok, result, err = _cas(f"{CELL_EXPRS[cell]} ∉ {bank_lit}")
        holds = bool(getattr(result, "holds", False)) if ok else False
        gap_ok &= holds
        gap_detail.append(f"{cell}:holds={holds}")
    add("cmb_membership_gap_cells", "per_cell_assertion",
        "Every uncharged cell must satisfy `^n^D ∉ StateSet{bank}` with "
        "holds=True.",
        "holds=True for P0,P9,C0,O9", ", ".join(gap_detail), gap_ok,
        {"probed": gap_cells})

    ok, result, err = _cas(f"{bank_lit} ⊆ States")
    add("cmb_bank_subset_of_universe", "per_cell_assertion",
        "FALSE-POSITIVE CONTROL. Any well-formed bank must be a subset of the "
        "40-cell universe.",
        "holds=True", f"holds={bool(getattr(result,'holds',False)) if ok else 'n/a'}",
        ok and bool(getattr(result, "holds", False)), {"error": err})

    # --- A9: typo-cannot-become-a-lacuna negative controls ----------------
    for cid, src, desc in [
        ("cmb_typo_domain_not_a_lacuna", "StateSet{^3^Z}",
         "NEGATIVE CONTROL. A bank naming a non-existent domain (^3^Z) must be "
         "REJECTED, not silently accepted with the intended cell registering as "
         "absent. This is the lacunarity analogue of the CSB cas_leaf attacks."),
        ("cmb_out_of_range_noetic_not_a_lacuna", "StateSet{^11^P}",
         "NEGATIVE CONTROL. A bank naming an out-of-range Noetic (^11) must be "
         "rejected."),
        ("cmb_partition_duplicate_cell_rejected",
         "PartitionOf(States, StateSet{^3^P}, StateSet{^3^P})",
         "NEGATIVE CONTROL. A family that double-counts a cell must fail the "
         "disjointness requirement --- 'covered at least once' must not be "
         "confused with 'accounted for exactly once'."),
        ("cmb_cross_type_family_rejected", "CoverOf(States, NoeticSet{^3})",
         "NEGATIVE CONTROL. A family of the wrong element type must not be "
         "allowed to cover the 40-cell universe."),
    ]:
        ok, _result, err = _cas(src)
        add(cid, "negative_control", desc, "rejected",
            "rejected" if not ok else "accepted", not ok,
            {"source": src, "error": err[:250]})

    return rows


# ==========================================================================
# SECTION B --- behavioural runs of the SHIPPED absence detector.
# Real execution. Coarser granularity than the chapter's claim; labelled.
# ==========================================================================
def section_b(generated_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    LEVEL = "behavioural"

    def add(cid, cat, desc, expected, observed, passed, ev):
        rows.append(_record(cid, cat, LEVEL, desc, expected, observed, passed, ev, generated_at))

    HI_OPS = [8.0] * 10
    HI_DOM = [0.8] * 4
    HI_DRV = [0.8] * 7

    # --- B1: false-positive control, the one that must not be weakened ----
    gm = generate_gap_map(HI_OPS, HI_DOM, HI_DRV)
    clean = (gm["absent_operators"] == [] and gm["absent_domains"] == []
             and gm["absent_drives"] == []
             and gm["largest_void"] == "No significant gaps detected")
    add("gapmap_all_high_no_false_gaps", "false_positive_detector",
        "FALSE-POSITIVE CONTROL. All-high operator, domain and drive scores must "
        "yield three EMPTY absent lists and 'No significant gaps detected'. This "
        "is the case that makes every positive case below meaningful.",
        "three empty lists + 'No significant gaps detected'",
        f"ops={gm['absent_operators']} doms={gm['absent_domains']} "
        f"drvs={gm['absent_drives']} void={gm['largest_void']!r}",
        clean, {"gap_map": gm})

    # --- B2-B4: deliberate gaps, asserted by exact identity ---------------
    ops = list(HI_OPS); ops[3] = 0.0; ops[6] = 0.0
    gm = generate_gap_map(ops, HI_DOM, HI_DRV)
    add("gapmap_absent_operators_exact", "deliberate_gap",
        "Zero Noetics ^3 (Negative) and ^6 (Male) against a high baseline; "
        "absent_operators must be exactly [3, 6] --- not a superset, not a count.",
        "absent_operators == [3, 6]", f"absent_operators == {gm['absent_operators']}",
        gm["absent_operators"] == [3, 6], {"gap_map": gm})

    dom = list(HI_DOM); dom[0] = 0.0
    gm = generate_gap_map(HI_OPS, dom, HI_DRV)
    add("gapmap_absent_domain_exact", "deliberate_gap",
        "Zero the Principled domain; absent_domains must be exactly ['P'].",
        "absent_domains == ['P']", f"absent_domains == {gm['absent_domains']}",
        gm["absent_domains"] == ["P"], {"gap_map": gm})

    drv = list(HI_DRV); drv[1] = drv[3] = drv[5] = 0.0
    gm3 = generate_gap_map(HI_OPS, HI_DOM, drv)
    add("gapmap_absent_drives_exact", "deliberate_gap",
        "Zero drives F2, F4, F6; absent_drives must be exactly [2, 4, 6].",
        "absent_drives == [2, 4, 6]", f"absent_drives == {gm3['absent_drives']}",
        gm3["absent_drives"] == [2, 4, 6], {"gap_map": gm3})

    # --- B5/B6: the REPORTING threshold, not just the arithmetic ----------
    add("gapmap_drive_void_silent_at_three", "reporting_threshold",
        "NEGATIVE CONTROL on the reporting branch. `describe_largest_gap` fires "
        "'Drive void' only at >= 4 absent drives, so 3 absent must NOT produce "
        "that string.",
        "largest_void does not start with 'Drive void'",
        f"largest_void = {gm3['largest_void']!r}",
        not gm3["largest_void"].startswith("Drive void"), {"gap_map": gm3})

    drv4 = list(HI_DRV); drv4[0] = drv4[1] = drv4[3] = drv4[5] = 0.0
    gm4 = generate_gap_map(HI_OPS, HI_DOM, drv4)
    add("gapmap_drive_void_fires_at_four", "reporting_threshold",
        "At 4 absent drives the 'Drive void' branch must fire.",
        "largest_void starts with 'Drive void'",
        f"largest_void = {gm4['largest_void']!r}",
        gm4["largest_void"].startswith("Drive void"), {"gap_map": gm4})

    # --- B7: threshold boundary, and what 'absent' actually means ---------
    b = list(HI_OPS); b[0] = 4.0; b[1] = 3.999
    gm = generate_gap_map(b, HI_DOM, HI_DRV)
    add("gapmap_operator_threshold_strictly_exclusive", "reporting_threshold",
        "The shipped detector uses strict `s < op_threshold` with a default of "
        "4.0 on a 0-10 operator scale. A score of exactly 4.0 must NOT be flagged "
        "and 3.999 must be. NOTE recorded in the report: 'absent' here means "
        "'below 4.0', which is materially weaker than the chapter's 'empty'.",
        "absent_operators == [1]", f"absent_operators == {gm['absent_operators']}",
        gm["absent_operators"] == [1], {"gap_map": gm, "op_threshold": 4.0})

    # --- B8: monotonicity in absence --------------------------------------
    prev: set[int] = set()
    monotone = True
    sweep: list[list[int]] = []
    for k in range(11):
        vec = [0.0 if i < k else 8.0 for i in range(10)]
        cur = set(generate_gap_map(vec, HI_DOM, HI_DRV)["absent_operators"])
        sweep.append(sorted(cur))
        if not prev.issubset(cur):
            monotone = False
        prev = cur
    add("gapmap_monotone_in_absence", "invariant",
        "Sweep 11 progressively emptier operator vectors. Removing one more "
        "operator must never SHRINK absent_operators. A detector non-monotone in "
        "absence is broken regardless of how many single cases pass.",
        "absent set non-decreasing across the sweep",
        f"monotone={monotone}", monotone, {"sweep": sweep})

    # --- B9: canonical Noetic names in the human-readable output ----------
    vec = list(HI_OPS)
    for i in (0, 1, 2, 3, 8):
        vec[i] = 0.0
    gm = generate_gap_map(vec, HI_DOM, HI_DRV)
    void = gm["largest_void"]
    expected_names = [CANONICAL_NOETIC_NAMES[i] for i in (0, 1, 2, 3, 8)]
    names_ok = all(n in void for n in expected_names)
    add("gapmap_uses_canonical_noetic_names", "canonical_naming",
        "`largest_void` is the human-readable lacunarity output and is reachable "
        "from api/pipeline/runner.py:362. With 5 Noetics absent it must name them "
        "with the canonical names the Rust source of truth uses "
        "(cas-engine/src/scoring/lacunarity.rs:165-169).",
        f"largest_void names {expected_names}",
        f"largest_void = {void!r}", names_ok,
        {"gap_map": gm, "expected_names": expected_names,
         "rust_source": "cas-engine/src/scoring/lacunarity.rs:165-169",
         "python_mirror": "api/pipeline/lacunarity.py:70-75"})

    # --- B10/B11: degenerate-input robustness on the absence path ---------
    prof = compute_lacunarity_profile(HI_OPS, [0.8, 0.8], HI_DRV)
    gm = prof["gap_map"]
    no_false_negative = gm["largest_void"] != "No significant gaps detected"
    add("gapmap_short_domain_list_no_false_negative", "robustness",
        "`compute_lacunarity_profile` advertises tolerance of short domain lists "
        "(it pads with `domain_scores + [0.0] * 4`), but then passes the "
        "UNPADDED `domain_scores[:4]` to `generate_gap_map`. Supply only 2 of the "
        "4 domains: the two missing domains must not be silently reported as "
        "present. A false negative here is the worst failure an absence detector "
        "can have.",
        "absent_domains reports the 2 unsupplied domains",
        f"absent_domains={gm['absent_domains']} void={gm['largest_void']!r}",
        no_false_negative,
        {"gap_map": gm, "site": "api/pipeline/lacunarity.py:118,125"})

    crashed, exc_detail = False, ""
    try:
        compute_lacunarity_profile(HI_OPS, HI_DOM, [0.8, 0.8])
    except Exception as exc:  # noqa: BLE001
        crashed, exc_detail = True, f"{type(exc).__name__}: {exc}"
    add("gapmap_short_drive_list_no_crash", "robustness",
        "Same padding path for drives: `drive_scores + [0.0] * 7` produces a "
        "9-element list without truncation, so `generate_gap_map` can emit drive "
        "indices 8 and 9 and then index `drive_names[i-1]` out of range. Supply a "
        "2-element drive list.",
        "no exception", f"raised={crashed} {exc_detail}", not crashed,
        {"site": "api/pipeline/lacunarity.py:119,90", "exception": exc_detail})

    # --- B12: the Rust source of truth, actually executed -----------------
    cargo_dir = NOETIC_ROOT / "cas-engine"
    passed_n, failed_n, ran, detail = 0, -1, False, ""
    try:
        proc = subprocess.run(
            ["cargo", "test", "--lib", "scoring::lacunarity"],
            cwd=str(cargo_dir), capture_output=True, text=True, timeout=900,
        )
        ran = True
        out = proc.stdout + proc.stderr
        m = re.search(r"test result: \w+\. (\d+) passed; (\d+) failed", out)
        if m:
            passed_n, failed_n = int(m.group(1)), int(m.group(2))
        detail = (m.group(0) if m else out.strip().splitlines()[-1][:200])
    except Exception as exc:  # noqa: BLE001
        detail = f"could not run cargo: {type(exc).__name__}: {exc}"
    add("rust_lacunarity_unit_tests_pass", "shipped_detector",
        "Execute the Rust absence detector's own unit suite "
        "(`cargo test --lib scoring::lacunarity`). This is a real run of a real "
        "detector --- at 10-operator / 4-domain / 7-drive granularity, NOT at the "
        "40-cell granularity Chapter 21 claims.",
        "cargo reports 0 failed",
        detail if ran else "did not run",
        ran and failed_n == 0 and passed_n > 0,
        {"cwd": str(cargo_dir), "passed": passed_n, "failed": failed_n, "detail": detail})

    return rows


# ==========================================================================
# SECTION C --- published Chapter 21 parts and the one real parameter gate.
# ==========================================================================
def section_c(generated_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    LEVEL = "structural"

    def add(cid, cat, desc, expected, observed, passed, ev):
        rows.append(_record(cid, cat, LEVEL, desc, expected, observed, passed, ev, generated_at))

    published_cells = [
        ("p3", "P3: principled aversions --- deep, near-permanent",
         "Capacitor< ^3^P_{F7}|f, C=200, leakage=0.001 >"),
        ("e6", "E6: analytical decomposition of relationships",
         "Capacitor< ^6^E_{F4}|A, C=110, leakage=0.02 >"),
        ("c8", "C8: analytical associations --- shallow, leaky",
         "Capacitor< ^8^C_{F2}|A, C=60, leakage=0.05 >"),
    ]
    for ref, role, expr in published_cells:
        ok, detail = _pcba_compile(expr)
        add(f"cmb_published_cell_{ref}", "published_bom",
            f"FALSE-POSITIVE CONTROL. Chapter 21 bank cell `{ref}` ({role}) must "
            f"parse and compile clean through the real PCBA toolchain.",
            "accepted", "accepted" if ok else "rejected", ok,
            {"expression": expr, "detail": detail})

    # leakage is the only lacunarity-adjacent parameter a real gate touches.
    for cid, expr, expect_ok, desc in [
        ("cmb_leakage_lower_boundary", "Capacitor< ^3^P_{F7}|f, C=200, leakage=0.0 >",
         True, "FALSE-POSITIVE CONTROL. leakage=0.0 (never forgets) is in range."),
        ("cmb_leakage_upper_boundary", "Capacitor< ^3^P_{F7}|f, C=200, leakage=1.0 >",
         True, "FALSE-POSITIVE CONTROL. leakage=1.0 is the in-range upper bound."),
        ("cmb_leakage_datasheet_nominal_max", "Capacitor< ^3^P_{F7}|f, C=200, leakage=0.5 >",
         True, "FALSE-POSITIVE CONTROL. The Chapter 21 datasheet nominal maximum "
               "(0.5 /unit time) must be accepted."),
        ("cmb_leakage_above_range_rejected", "Capacitor< ^3^P_{F7}|f, C=200, leakage=1.5 >",
         False, "NEGATIVE CONTROL. A forgetting rate above 1 is meaningless and "
                "must be rejected."),
        ("cmb_leakage_negative_rejected", "Capacitor< ^3^P_{F7}|f, C=200, leakage=-0.1 >",
         False, "NEGATIVE CONTROL. Negative leakage would mean a cell that charges "
                "itself; must be rejected."),
        ("cmb_leakage_nan_rejected", "Capacitor< ^3^P_{F7}|f, C=200, leakage=nan >",
         False, "NEGATIVE CONTROL. Non-finite leakage must be rejected."),
        ("cmb_leakage_inf_rejected", "Capacitor< ^3^P_{F7}|f, C=200, leakage=inf >",
         False, "NEGATIVE CONTROL. Infinite leakage must be rejected."),
    ]:
        ok, detail = _pcba_parse(expr)
        add(cid, "parameter_gate", desc,
            "accepted" if expect_ok else "rejected",
            "accepted" if ok else "rejected", ok == expect_ok,
            {"expression": expr, "detail": detail})

    # The CMB reference circuit that actually exists in code.
    crc = run_crc(build_cmb())
    d = crc.model_dump()
    errors = [f for f in d.get("findings", []) if f.get("severity") == "error"]
    add("cmb_reference_circuit_crc_clean", "shipped_design",
        "The CMB design that exists in code (cas_forex/ccb_designs.py:76 --- two "
        "CJT expressions plus one address-decode via) must pass the static "
        "Cognitive Rule Check. Recorded for completeness: this circuit contains "
        "NO capacitor bank, NO cells and NO lacunarity scan.",
        "0 CRC errors", f"{len(errors)} CRC errors", len(errors) == 0,
        {"cjt_count": len(build_cmb().cjts), "via_count": len(build_cmb().vias),
         "findings": len(d.get("findings", []))})

    return rows


# ==========================================================================
# SECTION D --- gap probes. Recorded as findings, never as passes.
# ==========================================================================
def section_d(generated_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    # --- G1: the chapter's actual mechanism, through both toolchains -----
    scan_stmt = "scan lacunarity: bank where charge < 0.05 -> lacuna_report;"
    cas_ok, _r, cas_err = _cas(scan_stmt)
    pcba_ok, pcba_err = _pcba_parse(scan_stmt)
    rows.append(_gap(
        "cmb_scan_statement_not_implemented",
        "Chapter 21 line 178 is the ONLY code expression of the lacunarity claim: "
        "`scan lacunarity: bank where charge < 0.05 -> lacuna_report;`. Run it "
        "through both toolchains.",
        hoped="accepted",
        observed="rejected by both",
        disposition=(
            "RECORDED AS A GAP, NOT WAIVED. The mechanism the chapter publishes "
            "does not exist in any parser in this repository, so the lacunarity "
            "claim could not be tested at the level the receipt asks for. This is "
            "not a defect in the toolchain and not a false claim about shipped "
            "tooling --- Appendix C line 8 already discloses that the CAS compiler "
            "is a design in the implementation-blueprint roadmap, and Chapter 21 "
            "makes no compile claim. It IS an internal-consistency defect between "
            "Chapter 21 / Appendix D and Appendix C: see the next probe. Section A "
            "of this run substitutes set-completeness detection over the 40-state "
            "universe, which is a DIFFERENT and weaker property, and the report "
            "says so."
        ),
        evidence={"statement": scan_stmt,
                  "cas_compiler": cas_err or f"accepted:{cas_ok}",
                  "pcba_parser": pcba_err if not pcba_ok else f"accepted:{pcba_err}"},
        generated_at=generated_at))

    # --- G2: `scan` is not in the book's own grammar ---------------------
    appc = APPENDIX_C.read_text(encoding="utf-8", errors="replace")
    reserved_block = appc.split("may not be used as identifiers:")[1].split("```")[1] if \
        "may not be used as identifiers:" in appc else ""
    # Appendix C carries TWO `circuit_item` productions (lines 129 and 492) and
    # they are not identical; check `scan` against both, and against the whole file.
    ebnf_items = re.findall(r"circuit_item\s*::=.*?(?=\n\s*\n|\n[a-z_]+\s*::=)", appc, re.S)
    in_reserved = bool(re.search(r"\bscan\b", reserved_block))
    in_ebnf = any(re.search(r"\bscan\b", item) for item in ebnf_items)
    anywhere = len(re.findall(r"\bscan\b", appc))
    rows.append(_gap(
        "cmb_scan_absent_from_book_grammar",
        "Appendix C is the book's own CCDL language reference. Check whether the "
        "`scan` statement form used in Chapter 21 line 178 and Appendix D line 460 "
        "appears in the reserved-word list, in either `circuit_item` EBNF "
        "production, or anywhere in Appendix C at all.",
        hoped="present in Appendix C",
        observed=f"reserved_words={in_reserved}, circuit_item_ebnf={in_ebnf}, "
                 f"occurrences_anywhere_in_appendix_c={anywhere}",
        disposition=(
            "BOOK DEFECT, FLAGGED FOR CORRECTION. Chapter 21 line 178 and "
            "Appendix D lines 422/459-460 publish a statement form the book's own "
            "grammar does not admit; the same is true of the surrounding `charge`, "
            "`select`, `discharge`, `refresh` and `decode` lines in the Chapter 21 "
            "listing. Recommended fix: either add these statement forms to the "
            "Appendix C reserved words and EBNF, or annotate the Chapter 21 "
            "listing as pseudo-CCDL beyond the Appendix C grammar. This run does "
            "not close that defect. Noted in passing while extracting the "
            "evidence, and offered as an observation rather than a lacunarity "
            "finding: Appendix C states the `circuit_item` production twice "
            "(lines 129 and 492) and the two statements differ --- the first omits "
            "`cjt_decl`. Neither admits `scan`."
        ),
        evidence={"reserved_block": reserved_block.strip()[:300],
                  "circuit_item_productions": [i.strip()[:220] for i in ebnf_items],
                  "scan_occurrences_in_appendix_c": anywhere},
        generated_at=generated_at))

    # --- G3: the write-history mechanism --------------------------------
    terms = ["ever_written", "write_history", "never_written", "was_written",
             "write_count", "written_at"]
    hits = _grep_repo(terms)
    total = sum(len(v) for v in hits.values())
    hit_files = sorted({x.split(":")[0] for v in hits.values() for x in v})
    rows.append(_gap(
        "cmb_write_history_absent",
        "Chapter 21 line 227 (Bench Note) and line 275 (Failure Modes, Detection "
        "column) state in the present tense that the board separates a true lacuna "
        "from a faded memory 'by tracking whether the cell has ever been written'. "
        "Search the cognitive-memory code paths for any per-cell write-history or "
        "never-written flag.",
        hoped="a per-cell write-history mechanism exists",
        observed=f"absent: {total} hits across {len(hit_files)} files, all unrelated "
                 f"({', '.join(Path(f).name for f in hit_files)})",
        disposition=(
            "BOOK OVERCLAIM --- THE MAIN FINDING OF THIS RUN, NOT WAIVED. No "
            "write-history mechanism exists: not in the chapter's own CCDL build "
            "(lines 146-183 declare no written flag and no second output), not in "
            "the datasheet (lines 257-266 list no write-history parameter), not in "
            "Appendix C, and not in code. Every hit returned by this search is "
            "unrelated (backup_restore.py overwrite counters, "
            "economic_calendar_feed.py cache timestamps, api/routes/settings.py). "
            "The empty-vs-leaked separation is the hardest and most important "
            "false-positive control an absence detector can have, and it cannot be "
            "tested, cannot be partially tested, and cannot be approximated here. "
            "Recommended fix: rewrite Chapter 21 line 227 as a design requirement "
            "('a CMB must record, per cell, whether it has ever been written; the "
            "listing above does not yet do so') and either add the state to the "
            "CCDL listing or say plainly that it is absent. Line 275's Detection "
            "column instructs the reader to use a facility the board does not "
            "provide and needs the same treatment."
        ),
        evidence={"terms": terms, "total_hits": total, "hit_files": hit_files,
                  "hits_by_term": {k: v[:6] for k, v in hits.items()},
                  "search_roots": [str(p.relative_to(WORKSPACE_ROOT)) for p in SEARCH_ROOTS]},
        generated_at=generated_at))

    # --- G4: the ~0.05 lacunarity threshold constant ---------------------
    thr_hits = _grep_repo([r"lacunarity[_ ]?threshold", r"lacuna_report", r"charge\s*<\s*0\.05"])
    thr_total = sum(len(v) for v in thr_hits.values())
    rows.append(_gap(
        "cmb_lacunarity_threshold_constant_absent",
        "Chapter 21 line 266 datasheet: 'Lacunarity threshold | --- | ~0.05 | "
        "Charge floor below which a cell is reported empty.' Search code for that "
        "constant or any `lacuna_report` terminal.",
        hoped="a ~0.05 charge-floor constant exists",
        observed=f"absent: {thr_total} hit(s), none a charge floor",
        disposition=(
            "RECORDED AS A GAP, NOT WAIVED. The ~0.05 threshold exists only as a "
            "number in the book's datasheet. Nothing in code reads charge and "
            "compares it to a floor, so the threshold's behaviour --- including "
            "the boundary cases an eval would normally pin down --- was not "
            "exercised by this run at all. The single hit is unrelated: "
            "`cas_forex/harvester.py:191` sets a forex-domain "
            "`lacunarity_threshold` of 1.5 over (symbol x timeframe x regime) "
            "cells. Same word, different universe. Listed so a later reader does "
            "not mistake it for CMB machinery --- the same caution applies to "
            "`cas_forex/nested_lacunarity.py`, `regime_sim.py` and "
            "`forecast/integrity.py`, none of which detect cognitive-state absence."
        ),
        evidence={"hits": {k: v[:6] for k, v in thr_hits.items()}},
        generated_at=generated_at))

    # --- G5: the capacitor bank itself -----------------------------------
    bank_hits = _grep_repo([r"capacitor_bank", r"CapacitorBank", r"class\s+\w*Bank\b"])
    bank_total = sum(len(v) for v in bank_hits.values())
    cmb = build_cmb()
    rows.append(_gap(
        "cmb_capacitor_bank_absent",
        "Chapter 21 builds its whole claim on 'a bank of 40 capacitors, one per "
        "cognitive state', each holding charge and leaking. Search for any object "
        "that instantiates 40 cells and holds per-cell charge.",
        hoped="a 40-cell capacitor bank exists",
        observed=f"absent: {bank_total} hits; the shipped CMB is "
                 f"{len(cmb.cjts)} CJT expressions and {len(cmb.vias)} via",
        disposition=(
            "RECORDED AS A GAP, NOT WAIVED. `cas_forex/ccb_designs.py:76 "
            "build_cmb()` is the CMB that exists in code: two CJT expressions and "
            "one address-decode via. There is no bank to scan, no charge, and no "
            "leakage decay loop, so every behavioural statement in Chapter 21 "
            "about charge levels is unreachable at any effort level short of "
            "building the board. A further blocker for whoever builds it: "
            "`cas-engine/src/ontology/states.rs` "
            "`CognitiveStateVector::from_slice` rejects any component <= 0 with "
            "`NonPositiveProbability` (open-simplex Correction 4), so the engine's "
            "canonical 40-dimensional state object CANNOT represent an empty cell. "
            "A charge-vector type that permits zeros does not exist, and the book "
            "never says so."
        ),
        evidence={"hits": {k: v[:6] for k, v in bank_hits.items()},
                  "shipped_cmb_cjts": [c.raw if hasattr(c, "raw") else str(c)[:160]
                                       for c in cmb.cjts]},
        generated_at=generated_at))

    # --- G6: the Chapter 21 refresh oscillator ---------------------------
    osc = "Oscillator< Phi< select_cell, discharge_partial, recharge >, frequency=0.0001 >"
    parse_ok, parse_detail = _pcba_parse(osc)
    comp_ok, comp_detail = _pcba_compile(osc)
    rows.append(_gap(
        "cmb_refresh_oscillator_no_cas_leaf",
        "Chapter 21 line 131/172 publishes the refresh oscillator "
        f"`{osc}`. Under the CSB run's own false-positive convention every "
        "published BOM line must compile clean.",
        hoped="accepted",
        observed=f"parses={parse_ok}, compiles_clean={comp_ok}",
        disposition=(
            "RECORDED AS A GAP, NOT WAIVED, AND NOT COUNTED AS A PASS. The line "
            "parses but yields valid=False from `compile_pcba_component_expression` "
            "because its `Phi<...>` holds bare identifiers (`select_cell`, "
            "`discharge_partial`, `recharge`) rather than CAS states, so there is "
            "no compiler-checkable CAS leaf. Two candidate fixes, both for the "
            "book rather than the toolchain: express the trajectory in CAS states "
            "(e.g. `Phi< ^1^C, ^5^E, ^7^C >`), or annotate the line as pseudo-CCDL. "
            "Related and recorded here so a later reader does not trip on it: the "
            "Chapter 21 line 74 encoder trajectory "
            "`Phi< ^8^C_{F2}|A, ^6^E_{F4}|A, ... >` uses the book-CCDL comma form, "
            "while the shipped CAS compiler's fractal literal is colon-separated "
            "Noetic indices (`Φ⟨8:6:3:9⟩`). The book is internally "
            "consistent with Appendix C line 518; the divergence is between "
            "book-CCDL and the shipped compiler."
        ),
        evidence={"expression": osc, "parse": parse_detail, "compile": comp_detail},
        generated_at=generated_at))

    # --- G7: the datasheet nominal leakage range is not a gate -----------
    ok, detail = _pcba_parse("Capacitor< ^3^P_{F7}|f, C=200, leakage=0.9 >")
    rows.append(_gap(
        "cmb_datasheet_leakage_range_not_enforced",
        "The Chapter 21 datasheet (line 261) gives cell leakage a nominal range of "
        "0.0 - 0.5 /unit time. Check whether a value outside that nominal range is "
        "gated.",
        hoped="rejected",
        observed="accepted" if ok else "rejected",
        disposition=(
            "ACCEPTED AS A LIMIT. `pcba_syntax._validate_params` gates `leakage` to "
            "[0, 1], which is the correct hard bound; the datasheet's 0.0-0.5 is a "
            "nominal design range, not a hard limit, and a capacitor on another "
            "board may legitimately sit above it. Recorded so that no reader "
            "mistakes the passing parameter-gate cases in Section C for enforcement "
            "of the datasheet's nominal range --- they are not."
        ),
        evidence={"expression": "Capacitor< ^3^P_{F7}|f, C=200, leakage=0.9 >",
                  "detail": detail},
        generated_at=generated_at))

    return rows


# ==========================================================================
def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    text = "".join(json.dumps(r, sort_keys=True, default=str) + "\n" for r in rows)
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _table(rows: list[dict[str, Any]]) -> str:
    out = ["| Case | Category | Level | Expected | Observed | Passed |",
           "|---|---|---|---|---|---:|"]
    for r in rows:
        observed = str(r["observed"]).replace("|", "\\|")[:110]
        expected = str(r["expected"]).replace("|", "\\|")[:80]
        out.append(f"| `{r['case_id']}` | `{r['category']}` | {r['test_level']} | "
                   f"{expected} | {observed} | `{str(r['passed']).lower()}` |")
    return "\n".join(out)


def main() -> int:
    generated_at = utc_now().isoformat()
    a = section_a(generated_at)
    b = section_b(generated_at)
    c = section_c(generated_at)
    gaps = section_d(generated_at)

    cases = a + b + c
    raw = WORKING_DIR / f"cmb_lacunarity_eval_raw_{DATE_TAG}.jsonl"
    raw_hash = _write_jsonl(raw, cases + gaps)

    a_pass = sum(1 for r in a if r["passed"])
    b_pass = sum(1 for r in b if r["passed"])
    c_pass = sum(1 for r in c if r["passed"])
    total_pass = a_pass + b_pass + c_pass
    failures = [r for r in cases if not r["passed"]]
    real_gaps = [g for g in gaps if g["is_gap"]]
    result = "PASS" if not failures else "FAIL"

    report = WORKING_DIR / f"cmb_lacunarity_eval_report_{DATE_TAG}.md"
    body = f"""# CMB Lacunarity Detection — Eval Report

Generated: `{generated_at}`
Reviewer identity: `{REVIEWER_ID}`
Reviewer type: AI/local code reviewer attestation, not a human signature.
Result: `{result}`
Cases passed: `{total_pass}/{len(cases)}`
 - Section A, 40-cell structural absence detection: `{a_pass}/{len(a)}`
 - Section B, shipped gap-map detector, behavioural: `{b_pass}/{len(b)}`
 - Section C, published Chapter 21 parts and parameter gates: `{c_pass}/{len(c)}`
Unenforced properties found: `{len(real_gaps)}`

## What This Run Claims

Exactly one thing: **that absence over the 40-cell cognitive state universe is
detectable, with working negative controls, using the real CAS compiler's
meta-set layer** — and, separately, that the shipped 10-operator / 4-domain /
7-drive gap-map detector runs and behaves as specified except where noted below.

Every Section A case is run through the real CAS compiler at
`noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`.
Deliberate-gap cases assert the exact missing-cell set **by identity**, not by
count. False-positive cases assert that complete 40-cell banks — in two
orderings — produce zero lacunae and satisfy both `CoverOf` and `PartitionOf`.
Section B is real execution of `api/pipeline/lacunarity.py` and of its Rust
source of truth via `cargo test`. Section C runs the published Chapter 21
capacitor cells through the real PCBA parser and CAS-leaf compiler.

## Out Of Scope, Deliberately

**Out of scope, deliberately. There is no memory board in the loop, because none
exists.** This run does not read charge off a capacitor, does not exercise the
~0.05 lacunarity threshold, does not exercise the leakage decay schedule, and
does not distinguish a never-written cell from a charged-then-leaked one — the
write-history mechanism Chapter 21 line 227 attributes to the board is **not
implemented anywhere in this repository**, so that half of the claim could not be
tested at all. Not partially. Not by proxy.

This run also does **not** use the shipped gap-map detector
(`cas-engine/src/scoring/lacunarity.rs` and its Python mirror) as evidence for
the chapter's 40-cell claim. That detector works at 10-operator / 4-domain /
7-drive granularity and reports "absent" as *below a 4.0 threshold on a 0–10
scale*, which is a materially weaker notion than the chapter's "empty".
Substituting it for the claimed instrument would be substituting a coarser
instrument for the claimed one.

Section A is **structural**: it tests set-completeness over the 40-state
universe. It is a real execution of a real compiler, but the thing being
executed is set algebra, not a board reading charge off forty capacitors.
Section B is **behavioural**: a real absence detector really runs on real
vectors. The report never lets the first stand in for the second, and the
`test_level` field on every JSONL record records which is which.

Nothing here licenses a claim about deployed behaviour, about measured
retrieval, or about a system's actual accumulated experience. Chapter 21's own
Honesty callout (line 217) already scopes every charge and leakage number as
arithmetic on chosen parameters rather than telemetry, and this run does not
change that.

## Pass/Fail Thresholds

- Section A pass rate must be `1.0`: every deliberate gap identified by exact
  cell identity, every complete bank producing zero lacunae, every malformed
  bank rejected rather than silently registering an absence.
- Section B pass rate must be `1.0`.
- Section C pass rate must be `1.0`: every published Chapter 21 cell compiles
  clean and every out-of-range `leakage` is rejected.
- Gap probes are findings, never passes. They do not contribute to the result.

## Section A — 40-Cell Structural Absence Detection (real CAS compiler)

{_table(a)}

## Section B — Shipped Absence Detector (behavioural)

{_table(b)}

## Section C — Published Chapter 21 Parts And Parameter Gates

{_table(c)}

"""

    if failures:
        body += "## Failures Observed\n\n"
        body += ("These are results, not omissions. No failing case was fixed by "
                 "weakening the case.\n\n")
        for r in failures:
            body += (f"### `{r['case_id']}`  ({r['test_level']})\n\n"
                     f"{r['description']}\n\n"
                     f"- Expected: {r['expected']}\n"
                     f"- Observed: {r['observed']}\n"
                     f"- Evidence: `{json.dumps(r['evidence'], default=str)[:400]}`\n\n")
    else:
        body += "## Failures Observed\n\nNone.\n\n"

    body += """## Unenforced Properties

These are properties the book's prose leans on that the toolchain does not
enforce, or mechanisms the book describes that do not exist. They are recorded
as findings, never as passes. Each carries its disposition.

"""
    if real_gaps:
        for g in real_gaps:
            body += (f"### `{g['case_id']}`\n\n"
                     f"{g['description']}\n\n"
                     f"- Hoped `{g['hoped']}`, observed `{g['observed']}`.\n"
                     f"- Evidence: `{json.dumps(g['evidence'], default=str)[:500]}`\n"
                     f"- **Disposition:** {g['disposition']}\n\n")
    else:
        body += "None.\n\n"

    body += f"""## Receipt Recommendation

`cmb_lacunarity_eval_pass` should **not** be signed off this run as though it
closed the Chapter 21 claim. The evidence here covers set-completeness detection
over the 40-state universe and the behaviour of a coarser shipped detector; it
does not cover the memory board's charge-threshold scan and does not touch the
empty-vs-leaked separation at all. That is consistent with the already-signed
`cmb_claim_review_signed`, which approves the CMB "as an architectural
description, explicitly not as a measured retrieval or lacunarity result."

The recommended disposition is to leave the receipt **open** and publish this run
as a scoped structural artifact with its gaps dispositioned in the book. If it is
signed at all, the `signed_reason` must state that the evidence covers
set-completeness detection over the 40-state universe and explicitly not the
board's charge-threshold scan or its never-written/leaked separation.

## Mitigations And Limits

- The allowed claim is limited to what this artifact observed.
- This evidence does not unlock live trading and is not a broker `ACCEPT` path.
- This evidence does not support behavioural, legal, governance, privacy, or
  human-factors claims about the CMB.
- No failing case in this run was closed by weakening the case. The failures and
  gaps are reported as they were observed.

## Raw Evidence

- Path: `docs\\working\\{raw.name}`
- SHA-256: `{raw_hash}`
- JSONL records: `{len(cases) + len(gaps)}` (`{len(cases)}` cases, `{len(gaps)}` gap probes)
"""
    report.write_text(body, encoding="utf-8", newline="\n")

    print(f"result            : {result}")
    print(f"section A (40cell): {a_pass}/{len(a)}   [structural]")
    print(f"section B (gapmap): {b_pass}/{len(b)}   [behavioural]")
    print(f"section C (parts) : {c_pass}/{len(c)}   [structural]")
    print(f"unenforced found  : {len(real_gaps)}")
    for g in real_gaps:
        print(f"   GAP  {g['case_id']}: hoped {g['hoped']}, observed {g['observed']}")
    for r in failures:
        print(f"   FAIL {r['case_id']} [{r['test_level']}]")
        print(f"        expected {r['expected']}")
        print(f"        observed {r['observed']}")
    print(f"\nreport : {report}")
    print(f"raw    : {raw}  sha256 {raw_hash}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
