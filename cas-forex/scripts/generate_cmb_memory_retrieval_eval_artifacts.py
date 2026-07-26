"""Generate CMB (Cognitive Memory Board) memory-retrieval eval artifacts.

Targets the open receipt
`memory_board_cognitive_memory_claim__cmb_memory_retrieval_eval_pass.json`.

WHAT THIS RUN ACTUALLY DOES, in one line: the metric is real and retrieval over
it works; the board is not built.

Two blocks, and the difference between them is load-bearing.

BLOCK A - STRUCTURAL (compile-level). The three CMB capacitor cells the book
publishes (Chapter_21:28-30, Appendix_D:435-437) are put through the real PCBA
parser and the real CAS compiler. Every adversarial weakening of a memory cell
is attempted against those same gates. The repo's own CMB reference design is
linted by the real CRC linter and cross-checked against the Noetics the book
names for the address decoder and the refresh pump. Board-level authority is
read off the real licensing report. None of this observes behaviour; it observes
that text is accepted or rejected by a compiler.

BLOCK B - BEHAVIOURAL (runtime measurement). Fisher-Rao geodesic distance
`d_FR(p,q) = 2*arccos(sum_k sqrt(p_k q_k))` is executed, on real numbers, in
three independent implementations that exist in this repo, and their agreement
is measured. Metric axioms are measured on randomly drawn open-simplex vectors.
Nearest-neighbour recovery is measured as a curve against perturbation
magnitude and against bank size, including the point where it collapses. A
negative control measures whether a query with no true neighbour is correctly
held at a distance. These are numbers produced by running code, not by parsing
it.

OUT OF SCOPE, and deliberately so. There is no model in the loop. Nothing was
encoded from English. No capacitor was charged, discharged, leaked, or
refreshed, because no such object exists anywhere in this repository. The
vectors retrieved in Block B are synthetic constructions of this eval, not
stored experiences of any system. See the report's scope section, which says
this again at length.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import statistics
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

_HERE = Path(__file__).resolve()
CAS_FOREX_ROOT = _HERE.parents[1]
WORKSPACE_ROOT = _HERE.parents[2]
SCAFFOLD_ROOT = WORKSPACE_ROOT / "noetic-compass-scaffold" / "noetic-compass"

for _p in (CAS_FOREX_ROOT, SCAFFOLD_ROOT, SCAFFOLD_ROOT / "cas-native"):
    sys.path.insert(0, str(_p))

from cas_forex.ccb_designs import build_cmb  # noqa: E402
from cas_forex.cjt_differential import fisher_rao_distance as cjt_fisher_rao  # noqa: E402
from cas_forex.crc_linter import run_crc  # noqa: E402
from cas_forex.pcba_authority import build_pcba_licensing_report  # noqa: E402
from cas_forex.pcba_compiler import compile_pcba_component_expression  # noqa: E402
from cas_forex.pcba_syntax import parse_pcba_component_expression  # noqa: E402
from cas_forex.time_utils import utc_now  # noqa: E402

import cas_engine  # noqa: E402  (compiled Rust extension, already installed)
from belief.geodesic_memory import (  # noqa: E402
    GeodesicBelief,
    fisher_rao_distance_values,
    retrieve_by_geodesic_gravity,
    validate_simplex_vector,
)

REVIEWER_ID = "claude_opus5_local_reviewer_20260725"
WORKING_DIR = WORKSPACE_ROOT / "docs" / "working"
DATE_TAG = "20260725"
RUN_ID = "cmb-memory-retrieval-eval"

NUM_STATES = 40
# Bank layout is the engine's own: cas-engine/src/ontology/states.rs:51-53,
# `domain.index() * 10 + operator.index()`, with P=0, C=1, E=2, O=3
# (domains.rs:36-40). So P3=3, C8=18, E6=26. This is exactly the P0..O9 layout
# Chapter_21:22 describes.
DOMAIN_BASE = {"P": 0, "C": 10, "E": 20, "O": 30}


def state_index(label: str) -> int:
    """`P3` -> 3, `C8` -> 18, `E6` -> 26."""
    return DOMAIN_BASE[label[0]] + int(label[1:])


# ==========================================================================
# PRE-REGISTERED THRESHOLDS.
# Fixed before this run, taken from the prior investigation's stated
# suggestions. They are NOT tuned to the observed numbers. Where a threshold
# is missed, the case is reported as a failure and left standing.
# ==========================================================================
PREREG = {
    "identity_tol": 1e-6,          # |d(p,p)| must be under this in both impls
    "symmetry_tol": 1e-12,         # |d(p,q) - d(q,p)|
    "triangle_slack": 1e-9,        # d(p,r) <= d(p,q) + d(q,r) + slack
    "cross_impl_tol": 1e-9,        # max abs disagreement between implementations
    "recovery_accept_eps": 0.10,   # top-1 must be 1.00 for eps <= this
    "recovery_accept_top1": 1.00,
    "no_match_radius": 1.0,        # rad; a no-neighbour query must exceed this
    "true_match_radius": 1.0,      # rad; a genuine eps=0.05 query must be under
    "n_axiom_vectors": 1000,
    "n_axiom_triples": 1000,
    "banks_per_point": 10,
    "queries_per_bank": 20,
    "seed": 20260725,
}

EPS_SWEEP = [0.0, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80]
K_SWEEP = [5, 10, 20, 40]
K_SWEEP_EPS = 0.20
# Cell-separation sweep. Chapter_21:251 claims inter-cell Fisher-Rao separation
# is the design lever that holds false recall down. This sweep measures that
# claim directly, and is also where the recovery test earns its ability to fail:
# a well-separated bank is trivially easy, a tightly packed one is not.
SEP_SWEEP = [0.02, 0.05, 0.10, 0.20, 0.40, 0.80]
SEP_SWEEP_EPS = 0.20

# ==========================================================================
# BLOCK A fixtures - the published CMB bill of materials.
# Chapter_21_CMB_Cognitive_Memory_Board.md:28-30 and :153-155;
# Appendix_D_CCB_Reference_Designs.md:435-437.
# ==========================================================================
CMB_BOM: list[tuple[str, str, str]] = [
    ("p3", "P3 cell: principled aversions, deep and near-permanent",
     "Capacitor< ^3^P_{F7}|f, C=200, leakage=0.001 >"),
    ("e6", "E6 cell: analytical decomposition of relationships",
     "Capacitor< ^6^E_{F4}|A, C=110, leakage=0.02 >"),
    ("c8", "C8 cell: analytical associations, shallow and leaky",
     "Capacitor< ^8^C_{F2}|A, C=60, leakage=0.05 >"),
]

# Adversarial: each tries to weaken a named parameter of a memory cell.
ATTACKS: list[dict[str, Any]] = [
    {
        "case_id": "cmb_cell_capacitance_non_finite",
        "category": "storage_defeat",
        "description": (
            "Give a memory cell infinite capacitance so it can never saturate "
            "and its charge arithmetic is undefined."
        ),
        "expression": "Capacitor< ^3^P_{F7}|f, C=inf, leakage=0.001 >",
        "layer": "parser",
    },
    {
        "case_id": "cmb_cell_capacitance_negative",
        "category": "storage_defeat",
        "description": "Negative capacitance on a memory cell.",
        "expression": "Capacitor< ^3^P_{F7}|f, C=-1, leakage=0.001 >",
        "layer": "parser",
    },
    {
        "case_id": "cmb_leakage_negative",
        "category": "forgetting_defeat",
        "description": (
            "Negative leakage: a cell that gains charge while un-rehearsed, "
            "defeating the forgetting policy Chapter_21:16 requires."
        ),
        "expression": "Capacitor< ^3^P_{F7}|f, C=200, leakage=-0.1 >",
        "layer": "parser",
    },
    {
        "case_id": "cmb_leakage_above_unit",
        "category": "forgetting_defeat",
        "description": "Leakage above 1.0, which would drive charge negative in one tick.",
        "expression": "Capacitor< ^3^P_{F7}|f, C=200, leakage=1.5 >",
        "layer": "parser",
    },
    {
        "case_id": "cmb_leakage_non_finite",
        "category": "forgetting_defeat",
        "description": "Non-finite leakage on the durable principled-aversion cell.",
        "expression": "Capacitor< ^3^P_{F7}|f, C=200, leakage=nan >",
        "layer": "parser",
    },
    {
        "case_id": "cmb_invalid_noetic_leaf",
        "category": "cas_leaf",
        "description": "Smuggle a non-existent Noetic (^3^Z) into a bank cell.",
        "expression": "Capacitor< ^3^Z_{F7}|f, C=200, leakage=0.001 >",
        "layer": "compiler",
    },
    {
        "case_id": "cmb_invalid_drive_leaf",
        "category": "cas_leaf",
        "description": "Smuggle a non-existent Drive (F9) into a bank cell.",
        "expression": "Capacitor< ^3^P_{F9}|f, C=200, leakage=0.001 >",
        "layer": "compiler",
    },
    {
        "case_id": "cmb_invalid_register_leaf",
        "category": "cas_leaf",
        "description": "Smuggle a non-existent Register (|X) into a bank cell.",
        "expression": "Capacitor< ^3^P_{F7}|X, C=200, leakage=0.001 >",
        "layer": "compiler",
    },
]

# False positives: valid cells and in-range boundary values that must NOT be
# rejected. Ranges are the book's own datasheet, Chapter_21:259-266.
BENIGN_BOUNDARIES: list[dict[str, Any]] = [
    {
        "case_id": "cmb_leakage_lower_boundary",
        "description": "Datasheet leakage floor 0.0 (a perfectly durable cell) must be accepted.",
        "expression": "Capacitor< ^3^P_{F7}|f, C=200, leakage=0.0 >",
    },
    {
        "case_id": "cmb_leakage_nominal_ceiling",
        "description": "Datasheet leakage ceiling 0.5 must be accepted.",
        "expression": "Capacitor< ^8^C_{F2}|A, C=60, leakage=0.5 >",
    },
    {
        "case_id": "cmb_capacitance_lower_boundary",
        "description": "Datasheet capacitance floor C=1 must be accepted.",
        "expression": "Capacitor< ^8^C_{F2}|A, C=1, leakage=0.05 >",
    },
    {
        "case_id": "cmb_capacitance_upper_boundary",
        "description": "Datasheet capacitance ceiling C=1000 must be accepted.",
        "expression": "Capacitor< ^3^P_{F7}|f, C=1000, leakage=0.001 >",
    },
    {
        "case_id": "cmb_appendix_d_five_substrate_cell",
        "description": (
            "Appendix_D:413 declares the cell form as `Capacitor< ^5 state, C, "
            "leakage >`. A ^5-substrate cell must therefore also compile."
        ),
        "expression": "Capacitor< ^5^E_{F4}|f, C=200, leakage=0.01 >",
    },
]

# Gap probes: properties the book leans on that nothing enforces, plus the
# two representation defects. Recorded as findings with dispositions, never as
# passes.
GAP_PROBES: list[dict[str, Any]] = [
    {
        "case_id": "cmb_leakage_above_datasheet_nominal",
        "kind": "parser",
        "description": (
            "Chapter_21:261 gives leakage a nominal range of 0.0-0.5 per unit "
            "time. Check whether the toolchain holds a memory cell to that."
        ),
        "expression": "Capacitor< ^3^P_{F7}|f, C=200, leakage=0.8 >",
        "hoped": "rejected",
        "disposition": (
            "UNENFORCED, RECORDED AS A LIMIT. The parser range-checks leakage to "
            "[0,1], not to the book's nominal [0,0.5]. A leakage of 0.8 is a "
            "physically coherent very-leaky cell, so a hard global clamp at 0.5 "
            "would be wrong. The correct disposition is that the datasheet's "
            "'nominal' column is advisory, not compiler-constrained, and a CMB "
            "build outside it must be caught by eye. Chapter 21 should say so "
            "where it prints the range."
        ),
    },
    {
        "case_id": "cmb_capacitance_above_datasheet_nominal",
        "kind": "parser",
        "description": (
            "Chapter_21:260 gives cell capacitance a nominal range of 1-1000. "
            "Check whether the toolchain holds a memory cell to that."
        ),
        "expression": "Capacitor< ^3^P_{F7}|f, C=5000, leakage=0.001 >",
        "hoped": "rejected",
        "disposition": (
            "UNENFORCED, RECORDED AS A LIMIT. Same disposition as leakage: the "
            "parser accepts any non-negative finite C. The nominal range is a "
            "design convention, not a gate. Not closed by weakening the probe."
        ),
    },
]


# ==========================================================================
# helpers - structural
# ==========================================================================
def _parse_result(expression: str) -> tuple[bool, str]:
    try:
        node = parse_pcba_component_expression(expression)
    except Exception as exc:  # noqa: BLE001 - any rejection is a rejection
        return False, str(exc).splitlines()[0][:300]
    return True, f"kind={node.kind.value} params={node.params}"


def _compile_result(expression: str) -> tuple[bool, str]:
    ok, detail = _parse_result(expression)
    if not ok:
        return False, f"rejected at parser: {detail}"
    report = compile_pcba_component_expression(expression)
    checked = len(report.checked_expressions)
    return bool(report.valid), (
        f"valid={report.valid} checked_leaves={checked} reason={report.reason}"
    )


def _record(case_id: str, category: str, description: str, expected: str,
            observed: str, passed: bool, evidence: dict[str, Any],
            generated_at: str, block: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "block": block,
        "category": category,
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


# ==========================================================================
# helpers - simplex geometry
# ==========================================================================
def _normalize(v: Sequence[float]) -> list[float]:
    """Normalize to sum exactly 1.0 in float, keeping every entry > 0."""
    total = math.fsum(v)
    out = [x / total for x in v]
    residual = 1.0 - math.fsum(out)
    # Park the residual on the largest coordinate so no entry can go <= 0.
    big = max(range(len(out)), key=lambda i: out[i])
    out[big] += residual
    return out


def smoothed_peak(k: int, peak: float = 0.7, n: int = NUM_STATES) -> list[float]:
    """A legal open-simplex point dominated by state `k`.

    The book never says what coordinate a bank cell occupies. The vertex
    reading (cell k at e_k) is outside the open simplex the book itself
    mandates at Chapter_21:98, so a smoothed peak is the nearest legal
    representation. This substitution is itself a finding; see the report.
    """
    rest = (1.0 - peak) / (n - 1)
    v = [rest] * n
    v[k] = peak
    return _normalize(v)


def dirichlet(rng: random.Random, n: int = NUM_STATES, alpha: float = 1.0) -> list[float]:
    raw = [rng.gammavariate(alpha, 1.0) for _ in range(n)]
    raw = [max(x, 1e-12) for x in raw]
    return _normalize(raw)


def blend(a: Sequence[float], b: Sequence[float], w: float) -> list[float]:
    return _normalize([(1.0 - w) * x + w * y for x, y in zip(a, b)])


def _rust_frd(p: Sequence[float], q: Sequence[float]) -> float:
    return cas_engine.geodesic_distance(
        cas_engine.CognitiveStateVector(list(p)),
        cas_engine.CognitiveStateVector(list(q)),
    )


def nearest_by_fisher_rao(query: Sequence[float],
                          bank: Sequence[Sequence[float]]) -> list[tuple[int, float]]:
    """Pure nearest-neighbour ranking by Fisher-Rao distance.

    THIS FUNCTION IS WRITTEN BY THE EVAL. The repo has no
    `nearest(query, bank, metric=fisher_rao)`; the only retrieval function it
    ships (`retrieve_by_geodesic_gravity`) deliberately overrides distance with
    belief mass. The METRIC below is the repo's
    (`belief.geodesic_memory.fisher_rao_distance_values`); the SORT is ours.
    That distinction is stated in the report and must not be blurred.
    """
    scored = [(i, fisher_rao_distance_values(query, cell)) for i, cell in enumerate(bank)]
    scored.sort(key=lambda t: (t[1], t[0]))
    return scored


def build_bank(rng: random.Random, k: int) -> list[list[float]]:
    """K distinct, deliberately asymmetric open-simplex points.

    Each record is a random Dirichlet(1) draw blended toward a different
    dominant state, with a DIFFERENT blend weight per record so the bank is not
    symmetry-degenerate the way the book's one-cell-per-state bank is.
    """
    bank = []
    for i in range(k):
        w = 0.35 + 0.45 * ((i % 7) / 6.0)
        bank.append(blend(dirichlet(rng), smoothed_peak(i % NUM_STATES, peak=0.9), w))
    return bank


def build_tight_bank(rng: random.Random, k: int, sep: float) -> list[list[float]]:
    """K records packed around a shared centre, `sep` controlling separation.

    `sep` near 0 puts every record almost on top of the centre and therefore
    almost on top of each other; `sep` near 1 spreads them to distinct
    dominants. This is the regime the CMB actually lives in: the book's own
    bank has all 40 cells at one identical pairwise distance, so a CMB designer
    has no separation lever at all (measured elsewhere in this run).
    """
    centre = dirichlet(rng)
    return [blend(centre, smoothed_peak(i % NUM_STATES, peak=0.9), sep) for i in range(k)]


def mean_nearest_separation(bank: Sequence[Sequence[float]]) -> float:
    """Mean distance from each record to its closest other record."""
    if len(bank) < 2:
        return float("nan")
    out = []
    for i, a in enumerate(bank):
        out.append(min(fisher_rao_distance_values(a, b)
                       for j, b in enumerate(bank) if j != i))
    return statistics.fmean(out)


# ==========================================================================
# BLOCK A - structural
# ==========================================================================
def run_structural(generated_at: str) -> tuple[list[dict], list[dict], list[dict]]:
    attacks: list[dict] = []
    benign: list[dict] = []
    gaps: list[dict] = []

    for atk in ATTACKS:
        fn = _parse_result if atk["layer"] == "parser" else _compile_result
        accepted, detail = fn(atk["expression"])
        attacks.append(_record(
            atk["case_id"], atk["category"], atk["description"],
            "rejected", "accepted" if accepted else "rejected", not accepted,
            {"expression": atk["expression"], "layer": atk["layer"], "detail": detail},
            generated_at, "A_structural",
        ))

    # Authority escalation, read off the real licensing report.
    lic = build_pcba_licensing_report().model_dump()
    cmb_check = next(
        (c for c in lic["checks"]
         if str(c.get("feature", "")).lower().endswith("memory_board_cognitive_memory_claim")
         or "memory_board" in str(c.get("feature", "")).lower()),
        None,
    )
    if cmb_check is None:
        attacks.append(_record(
            "cmb_authority_check_present", "authority",
            "The licensing report must carry a memory-board claim check.",
            "present", "absent", False, {"checks": [c.get("feature") for c in lic["checks"]]},
            generated_at, "A_structural",
        ))
    else:
        for cid, desc, flag in [
            ("cmb_board_not_ready",
             "The CMB claim must not report itself ready off this evidence.",
             bool(cmb_check.get("ready", False))),
            ("cmb_board_cannot_affect_live_trading",
             "The CMB must not be able to affect live trading.",
             bool(cmb_check.get("can_affect_live_trading", False))),
            ("cmb_board_cannot_create_broker_accept",
             "The CMB must not be able to create a broker ACCEPT.",
             bool(cmb_check.get("can_create_broker_accept", False))),
        ]:
            attacks.append(_record(
                cid, "authority", desc, "flag=false", f"flag={flag}", flag is False,
                {"status": cmb_check.get("status"),
                 "missing_evidence": cmb_check.get("missing_evidence"),
                 "rationale": cmb_check.get("rationale")},
                generated_at, "A_structural",
            ))
        # NOTE: `model_dump()` leaves this as a PcbaReadinessStatus enum, not a
        # string. The first version of this case compared `str(status)` against
        # "NOT LICENSED" and failed on `PcbaReadinessStatus.NOT_LICENSED`. The
        # CASE was wrong, not the code under test; corrected to read `.value`.
        _status = cmb_check.get("status")
        _status_str = getattr(_status, "value", None) or str(_status)
        attacks.append(_record(
            "cmb_status_not_licensed", "authority",
            "The memory-board claim must still read NOT LICENSED.",
            "NOT LICENSED", _status_str,
            _status_str == "NOT LICENSED",
            {"required_evidence": cmb_check.get("required_evidence"),
             "present_evidence": cmb_check.get("present_evidence")},
            generated_at, "A_structural",
        ))

    # False positives: the published BOM must not be rejected by its own tools.
    for ref, role, expression in CMB_BOM:
        accepted, detail = _compile_result(expression)
        benign.append(_record(
            f"cmb_bom_{ref}", "published_bom", f"Chapter 21 BOM cell `{ref}`: {role}",
            "accepted", "accepted" if accepted else "rejected", accepted,
            {"expression": expression, "detail": detail}, generated_at, "A_structural",
        ))

    for case in BENIGN_BOUNDARIES:
        accepted, detail = _compile_result(case["expression"])
        benign.append(_record(
            case["case_id"], "in_range_boundary", case["description"],
            "accepted", "accepted" if accepted else "rejected", accepted,
            {"expression": case["expression"], "detail": detail}, generated_at, "A_structural",
        ))

    # The repo's own CMB reference design must lint clean (ERROR-free).
    circuit = build_cmb()
    crc = run_crc(circuit)
    errors = [f for f in crc.findings if str(getattr(f, "severity", "")).upper().endswith("ERROR")]
    benign.append(_record(
        "cmb_repo_design_lints_clean", "reference_design",
        "The repo's own CMB reference design must produce no CRC ERROR findings.",
        "0 errors", f"{len(errors)} errors / {len(crc.findings)} findings",
        len(errors) == 0,
        {"circuit": circuit.name, "static_only": getattr(crc, "static_only", None),
         "findings": [str(f) for f in crc.findings][:10]},
        generated_at, "A_structural",
    ))

    # Cross-artifact: the repo's CMB must use the Noetics the book names.
    repo_text = " ".join(
        [str(c) for c in circuit.cjts] + [f"{v.source}->{v.target}" for v in circuit.vias]
    )
    for cid, needle, why in [
        ("cmb_decoder_noetic_matches_book", "^1^C",
         "Chapter_21:87-100 names `^1^C` Mind as the address decoder."),
        ("cmb_refresh_noetic_matches_book", "^7^C",
         "Chapter_21:123-135 names `^7^C` Rhythm as the refresh pump."),
    ]:
        found = needle in repo_text
        benign.append(_record(
            cid, "cross_artifact", why, f"`{needle}` present in repo CMB",
            "present" if found else "absent", found,
            {"repo_cmb": repo_text[:400]}, generated_at, "A_structural",
        ))

    for probe in GAP_PROBES:
        accepted, detail = _parse_result(probe["expression"])
        observed = "accepted" if accepted else "rejected"
        gaps.append({
            "case_id": probe["case_id"],
            "category": "known_gap",
            "block": "A_structural",
            "description": probe["description"],
            "hoped": probe["hoped"],
            "observed": observed,
            "is_gap": observed != probe["hoped"],
            "disposition": probe["disposition"],
            "evidence": {"expression": probe["expression"], "detail": detail},
            "record_type": "gap_probe",
            "reviewer_id": REVIEWER_ID,
            "run_id": RUN_ID,
            "generated_at": generated_at,
        })

    # Gap: the CCDL circuit body has no parser at all.
    ccdl_lines = [
        "cap p3: Capacitor< ^3^P_{F7}|f, C=200, leakage=0.001 >",
        "node decoder: ^1^C",
        "charge ^8^C_{F2}|A -> bank[C8] [V=0.4]",
        "select cell = nearest(query, bank, metric=fisher_rao)",
        "let query = address_on_simplex(dominant=^3^P_{F7}|f)",
        "discharge cell -> recalled_state",
        "refresh bank[P3] [pump=^7^C, gain=1.0]",
        "decode recalled_state -> recalled",
        "scan lacunarity: bank where charge < 0.05 -> lacuna_report",
        "probe tp_bank: bank",
        "Oscillator< Phi< select_durable, recharge >, frequency=0.0001 >",
    ]
    ccdl_results = {}
    for line in ccdl_lines:
        ok, detail = _parse_result(line)
        ccdl_results[line] = ("accepted" if ok else "rejected", detail[:160])
    n_rejected = sum(1 for v in ccdl_results.values() if v[0] == "rejected")
    gaps.append({
        "case_id": "cmb_ccdl_circuit_body_has_no_parser",
        "category": "known_gap",
        "block": "A_structural",
        "description": (
            "Chapter_21:145-183 publishes a full `circuit cognitive_memory_board "
            "{ ... }` build and Chapter_21:7 says real structural queries are run "
            "against it. Feed every non-declaration line to the only PCBA parser "
            "in the repo."
        ),
        "hoped": "accepted",
        "observed": f"{n_rejected}/{len(ccdl_lines)} rejected",
        "is_gap": n_rejected > 0,
        "disposition": (
            "CONFIRMED GAP, NOT WAIVED. `cas_forex/pcba_syntax.py` parses exactly "
            "one `Component< ... >` expression per call. There is no parser for "
            "`circuit`, `cap`, `node`, `charge`, `discharge`, `refresh`, `decode`, "
            "`select`, `scan`, or `probe`, and `crc_linter.run_crc` operates on a "
            "circuit graph built programmatically in Python, never parsed from "
            "CCDL text. The bare `Oscillator< ... >` line parses but compiles to "
            "zero CAS leaves. Chapter 21's CCDL listing is therefore pseudocode, "
            "not compiler input, and Chapter_21:7's 'we run real structural "
            "queries against it' is not true of anything in this codebase. "
            "REQUIRED ACTION: either build a CCDL front end or narrow "
            "Chapter_21:7. This eval does not close it."
        ),
        "evidence": {"lines": {k: v[0] for k, v in ccdl_results.items()},
                     "sample_error": next((v[1] for v in ccdl_results.values()
                                           if v[0] == "rejected"), "")},
        "record_type": "gap_probe",
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    })

    # Gap: repo CMB stores a state that does not appear in the published BOM.
    published_leaves = ["^3^P_{F7}|f", "^6^E_{F4}|A", "^8^C_{F2}|A"]
    overlap = [leaf for leaf in published_leaves if leaf in repo_text]
    gaps.append({
        "case_id": "cmb_repo_storage_leaf_vs_published_bom",
        "category": "known_gap",
        "block": "A_structural",
        "description": (
            "The repo's CMB (ccb_designs.py:82-83) stores into `^5^E_{F4}|f`. "
            "The published BOM (Chapter_21:28-30, Appendix_D:435-437) publishes "
            "cells `^3^P_{F7}|f`, `^6^E_{F4}|A`, `^8^C_{F2}|A`. Check overlap."
        ),
        "hoped": "at least one published cell present",
        "observed": f"{len(overlap)} of 3 published cells present",
        "is_gap": len(overlap) == 0,
        "disposition": (
            "CONFIRMED BOOK CONTRADICTION, OPEN. Appendix_D:413 declares the cell "
            "form as `Capacitor< ^5 state, C, leakage >` and Appendix_D:435-437 "
            "then publishes three cells, none of them `^5`. The repo sides with "
            "the prose; the BOM sides with the state-being-accumulated reading. "
            "Chapter 6 has the same split (Chapter_06:44 uses `^5^E_{F4}|f`, "
            "Chapter_06:121-123 use `^2^E`, `^3^P`, `^8^C`). A reader cannot tell "
            "whether a cell's leaf is the `^5` substrate or the state whose "
            "experience it accumulates. This is an owner decision, not a code "
            "change, and it is NOT closed by this eval. Both readings compile "
            "clean, which is why the compiler cannot catch it."
        ),
        "evidence": {"repo_cmb": repo_text[:400], "published_leaves": published_leaves,
                     "overlap": overlap},
        "record_type": "gap_probe",
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    })

    return attacks, benign, gaps


# ==========================================================================
# BLOCK B - behavioural
# ==========================================================================
def run_behavioural(generated_at: str) -> tuple[list[dict], list[dict], dict[str, Any]]:
    cases: list[dict] = []
    gaps: list[dict] = []
    metrics: dict[str, Any] = {}
    rng = random.Random(PREREG["seed"])

    def case(cid: str, cat: str, desc: str, expected: str, observed: str,
             passed: bool, ev: dict[str, Any]) -> None:
        cases.append(_record(cid, cat, desc, expected, observed, passed, ev,
                             generated_at, "B_behavioural"))

    # ---- B1: metric axioms + cross-implementation agreement --------------
    n_vec = PREREG["n_axiom_vectors"]
    vectors = [dirichlet(rng) for _ in range(n_vec)]

    id_py = max(abs(fisher_rao_distance_values(v, v)) for v in vectors)
    id_rs = max(abs(_rust_frd(v, v)) for v in vectors)
    metrics["identity_max_scaffold_python"] = id_py
    metrics["identity_max_rust_engine"] = id_rs
    case("cmb_metric_identity", "metric_axiom",
         "d(p,p) must be 0 within the pre-registered tolerance, in both implementations.",
         f"max |d(p,p)| < {PREREG['identity_tol']:.0e}",
         f"scaffold_python={id_py:.3e} rust={id_rs:.3e}",
         id_py < PREREG["identity_tol"] and id_rs < PREREG["identity_tol"],
         {"n": n_vec})

    sym = 0.0
    dis_py_rs = 0.0
    dis_py_cf = 0.0
    for i in range(0, n_vec - 1, 2):
        p, q = vectors[i], vectors[i + 1]
        d_pq = fisher_rao_distance_values(p, q)
        d_qp = fisher_rao_distance_values(q, p)
        sym = max(sym, abs(d_pq - d_qp))
        dis_py_rs = max(dis_py_rs, abs(d_pq - _rust_frd(p, q)))
        dis_py_cf = max(dis_py_cf, abs(d_pq - cjt_fisher_rao(p, q)))
    metrics["symmetry_max_delta"] = sym
    metrics["cross_impl_max_delta_python_vs_rust"] = dis_py_rs
    metrics["cross_impl_max_delta_python_vs_cas_forex"] = dis_py_cf
    case("cmb_metric_symmetry", "metric_axiom",
         "d(p,q) = d(q,p) on random open-simplex vectors.",
         f"max delta < {PREREG['symmetry_tol']:.0e}", f"{sym:.3e}",
         sym < PREREG["symmetry_tol"], {"pairs": n_vec // 2})
    case("cmb_metric_three_implementations_agree", "cross_implementation",
         "The three independent Fisher-Rao implementations in this repo "
         "(scaffold pure Python, compiled Rust engine, cas-forex CJT) must agree.",
         f"max delta < {PREREG['cross_impl_tol']:.0e}",
         f"py_vs_rust={dis_py_rs:.3e} py_vs_cas_forex={dis_py_cf:.3e}",
         dis_py_rs < PREREG["cross_impl_tol"] and dis_py_cf < PREREG["cross_impl_tol"],
         {"pairs": n_vec // 2,
          "impl_a": "noetic-compass/cas-native/belief/geodesic_memory.py",
          "impl_b": "cas_engine (compiled Rust, cas-engine/src/metric/mod.rs)",
          "impl_c": "cas-forex/cas_forex/cjt_differential.py"})

    tri_viol = 0
    worst_tri = 0.0
    for _ in range(PREREG["n_axiom_triples"]):
        p, q, r = rng.sample(vectors, 3)
        lhs = fisher_rao_distance_values(p, r)
        rhs = fisher_rao_distance_values(p, q) + fisher_rao_distance_values(q, r)
        slack = lhs - rhs
        worst_tri = max(worst_tri, slack)
        if slack > PREREG["triangle_slack"]:
            tri_viol += 1
    metrics["triangle_violations"] = tri_viol
    metrics["triangle_worst_excess"] = worst_tri
    case("cmb_metric_triangle_inequality", "metric_axiom",
         "d(p,r) <= d(p,q) + d(q,r) on random open-simplex triples.",
         "0 violations", f"{tri_viol} violations, worst excess {worst_tri:.3e}",
         tri_viol == 0, {"triples": PREREG["n_axiom_triples"]})

    # ---- B2: near-zero resolution floor ---------------------------------
    v = smoothed_peak(3, peak=0.7)
    floor_rust_identical = _rust_frd(v, v)
    w = list(v)
    w[0] += 1e-12
    w[1] -= 1e-12
    w = _normalize(w)
    floor_py_perturbed = fisher_rao_distance_values(v, w)
    floor_rust_perturbed = _rust_frd(v, w)
    metrics["floor_rust_identical_vectors"] = floor_rust_identical
    metrics["floor_python_1e12_perturbation"] = floor_py_perturbed
    metrics["floor_rust_1e12_perturbation"] = floor_rust_perturbed
    gaps.append({
        "case_id": "cmb_tie_breaking_resolution_floor",
        "category": "known_gap",
        "block": "B_behavioural",
        "description": (
            "For a device whose read path is 'pick the closest cell', the "
            "smallest resolvable distance is the tie-breaking floor. Measure it "
            "in both open-simplex implementations."
        ),
        "hoped": "both implementations resolve arbitrarily small differences",
        "observed": (
            f"rust d(v,v)={floor_rust_identical:.3e} (not exactly 0); "
            f"python d(v, v+1e-12)={floor_py_perturbed:.3e} (short-circuits to 0)"
        ),
        "is_gap": True,
        "disposition": (
            "MEASURED AND RECORDED, NOT WAIVED. Two opposite artifacts of the same "
            "arccos-near-1 sensitivity. The Rust engine cannot certify d=0: for "
            "identical vectors the Bhattacharyya coefficient rounds just under 1 "
            "and arccos amplifies it. The scaffold Python short-circuits when "
            "|1-BC| < 1e-12 (geodesic_memory.py:83), so it returns exactly 0.0 "
            "for identical vectors AND for genuinely different ones inside that "
            "window. Neither is a bug for belief retrieval; both matter for a "
            "40-cell bank where near-ties decide which memory is recalled. "
            "Chapter 21 should state a minimum cell separation. No code change "
            "made by this eval."
        ),
        "evidence": {"rust_identical": floor_rust_identical,
                     "python_perturbed": floor_py_perturbed,
                     "rust_perturbed": floor_rust_perturbed},
        "record_type": "gap_probe",
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    })

    # ---- B3: the book's own bank is degenerate ---------------------------
    # Smoothed-peak reading (legal on the open simplex).
    book_bank = [smoothed_peak(k, peak=0.7) for k in range(NUM_STATES)]
    q_p3 = smoothed_peak(state_index("P3"), peak=0.7)
    d_p3 = fisher_rao_distance_values(q_p3, book_bank[state_index("P3")])
    d_e6 = fisher_rao_distance_values(q_p3, book_bank[state_index("E6")])
    d_c8 = fisher_rao_distance_values(q_p3, book_bank[state_index("C8")])
    distinct = {round(fisher_rao_distance_values(book_bank[i], book_bank[j]), 12)
                for i, j in itertools.combinations(range(NUM_STATES), 2)}
    # Vertex reading (what "one cell per state" literally means). Rejected by
    # both open-simplex implementations, so measured with the cas-forex
    # implementation, which does not enforce strict positivity.
    def vertex(k: int) -> list[float]:
        v = [0.0] * NUM_STATES
        v[k] = 1.0
        return v
    d_e6_vertex = cjt_fisher_rao(vertex(state_index("P3")), vertex(state_index("E6")))
    d_c8_vertex = cjt_fisher_rao(vertex(state_index("P3")), vertex(state_index("C8")))
    metrics["book_bank_d_p3"] = d_p3
    metrics["book_bank_d_e6"] = d_e6
    metrics["book_bank_d_c8"] = d_c8
    metrics["book_bank_distinct_pairwise_distances"] = len(distinct)
    metrics["book_bank_pairwise_value"] = sorted(distinct)[0] if distinct else None
    metrics["book_bank_vertex_d_e6"] = d_e6_vertex
    metrics["book_bank_vertex_d_c8"] = d_c8_vertex
    # ---- label-addressed bank: the degenerate reading, kept as a control ----
    # This is the trap Chapter 21's Bench Note now names explicitly: taking a
    # cell's ADDRESS to be its INDEX. It must stay degenerate. If this case ever
    # starts passing, the bank construction has silently changed and the two
    # cases below stop meaning what they say.
    case("cmb_label_addressed_bank_is_degenerate", "book_claim",
         "Control for the Chapter_21 Bench Note. Address all 40 cells by their "
         "index label (smoothed one-hot) and confirm the geometry collapses: "
         "every distinct pair must come out at the SAME distance, which is why "
         "a label-addressed bank can never rank anything.",
         "exactly 1 distinct pairwise distance among the 40 cells",
         f"{len(distinct)} distinct value(s)",
         len(distinct) == 1,
         {"value": sorted(distinct)[0] if distinct else None,
          "pairs": NUM_STATES * (NUM_STATES - 1) // 2,
          "vertex_reading_d_e6": d_e6_vertex, "vertex_reading_d_c8": d_c8_vertex,
          "label_addressed_d_p3": d_p3, "label_addressed_d_e6": d_e6,
          "label_addressed_d_c8": d_c8,
          "note": "Under label addressing E6 and C8 are exactly equidistant "
                  "from the query. This is the degenerate case, retained as a "
                  "regression guard, NOT the bank the book prescribes."})

    # ---- composition-addressed bank: what the book actually publishes ------
    # Chapter_21 publishes the four addresses explicitly in a table so the
    # worked numbers are reproducible. Transcribed verbatim here; a change to
    # either the table or the published distances breaks this case.
    comp_bank = {
        "query": {"P3": 0.55, "E6": 0.20, "E3": 0.08, "C8": 0.04},
        "P3":    {"P3": 0.60, "E6": 0.18, "E3": 0.07, "C8": 0.03},
        "E6":    {"P3": 0.12, "E6": 0.55, "E3": 0.10, "C8": 0.06},
        "C8":    {"P3": 0.03, "E6": 0.08, "C8": 0.50, "C2": 0.15},
    }

    def composed(spec: dict[str, float], floor: float = 0.002) -> list[float]:
        v = [floor] * NUM_STATES
        for name, mass in spec.items():
            v[state_index(name)] = mass
        total = math.fsum(v)
        return [x / total for x in v]

    cq = composed(comp_bank["query"])
    cd = {n: fisher_rao_distance_values(cq, composed(comp_bank[n]))
          for n in ("P3", "E6", "C8")}
    PUBLISHED = {"P3": 0.106, "E6": 1.044, "C8": 1.951}
    metrics["composition_bank_distances"] = cd
    case("cmb_published_ranking_p3_e6_c8_derivable", "book_claim",
         "Chapter_21:208-210 and Appendix_D publish the ranked query result P3, "
         "then E6, then C8. Chapter_21 also publishes the four addresses the "
         "query ran against. Reproduce the ranking from those published "
         "addresses, which is what the book now prescribes.",
         "d(q,P3) < d(q,E6) < d(q,C8), strictly",
         f"d(q,P3)={cd['P3']:.6f} d(q,E6)={cd['E6']:.6f} d(q,C8)={cd['C8']:.6f}",
         cd["P3"] < cd["E6"] < cd["C8"],
         {"published_addresses": comp_bank, "published_distances": PUBLISHED})
    off = {n: abs(cd[n] - PUBLISHED[n]) for n in PUBLISHED}
    case("cmb_published_distances_match_published_addresses", "book_claim",
         "The three distances printed in Chapter_21 must actually follow from "
         "the address table printed alongside them. A reader who does the "
         "arithmetic must land on the book's numbers.",
         "each computed distance within 0.001 of the published value",
         f"max deviation {max(off.values()):.6f}",
         max(off.values()) < 0.001,
         {"computed": cd, "published": PUBLISHED, "deviation": off})
    comp_distinct = {round(fisher_rao_distance_values(
        composed(comp_bank[a]), composed(comp_bank[b])), 12)
        for a, b in itertools.combinations(("P3", "E6", "C8"), 2)}
    case("cmb_book_bank_supports_cell_separation_design", "book_claim",
         "Chapter_21:251 says 'keeping cells far enough apart in Fisher-Rao "
         "distance is what holds Lambda down'. For that to be a design lever, "
         "inter-cell distance must be variable -- which it is once cells are "
         "addressed by accumulated composition rather than by index label.",
         "more than 1 distinct pairwise distance among the published cells",
         f"{len(comp_distinct)} distinct value(s)",
         len(comp_distinct) > 1,
         {"values": sorted(comp_distinct)})

    # ---- B4: open-simplex enforcement ------------------------------------
    bad_zero = [1.0 / NUM_STATES] * NUM_STATES
    bad_zero[1] = 0.0
    bad_sum = [1.0 / NUM_STATES] * NUM_STATES
    bad_sum[0] = 0.5
    bad_nan = [1.0 / NUM_STATES] * NUM_STATES
    bad_nan[2] = float("nan")

    def rejects(fn: Callable[[], Any]) -> tuple[bool, str]:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            return True, str(exc).splitlines()[0][:200]
        return False, "accepted"

    for cid, desc, fn in [
        ("cmb_rust_rejects_closed_boundary",
         "The compiled engine must refuse a vector with a zero coordinate "
         "(Chapter_21:98 requires p_k > 0 for every state).",
         lambda: cas_engine.CognitiveStateVector(list(bad_zero))),
        ("cmb_rust_rejects_bad_sum",
         "The compiled engine must refuse a vector that does not sum to 1.",
         lambda: cas_engine.CognitiveStateVector(list(bad_sum))),
        ("cmb_rust_rejects_nan",
         "The compiled engine must refuse a NaN coordinate.",
         lambda: cas_engine.CognitiveStateVector(list(bad_nan))),
        ("cmb_scaffold_rejects_closed_boundary",
         "The scaffold retrieval layer must refuse a vector with a zero coordinate.",
         lambda: validate_simplex_vector(bad_zero)),
        ("cmb_scaffold_rejects_bad_sum",
         "The scaffold retrieval layer must refuse a vector that does not sum to 1.",
         lambda: validate_simplex_vector(bad_sum)),
    ]:
        ok, detail = rejects(fn)
        case(cid, "open_simplex", desc, "rejected",
             "rejected" if ok else "accepted", ok, {"detail": detail})

    # False-positive counterpart: a legal interior point must be accepted.
    legal = smoothed_peak(3, peak=0.7)
    ok, detail = rejects(lambda: cas_engine.CognitiveStateVector(list(legal)))
    case("cmb_rust_accepts_legal_interior_point", "open_simplex",
         "A legal open-simplex point must NOT be rejected. A validator that "
         "refuses valid addresses is a false-positive failure.",
         "accepted", "rejected" if ok else "accepted", not ok, {"detail": detail})
    ok, detail = rejects(lambda: validate_simplex_vector(legal))
    case("cmb_scaffold_accepts_legal_interior_point", "open_simplex",
         "Same false-positive check on the scaffold retrieval layer.",
         "accepted", "rejected" if ok else "accepted", not ok, {"detail": detail})

    # Gap: the CJT implementation accepts boundary points.
    boundary_d = None
    boundary_err = ""
    try:
        boundary_d = cjt_fisher_rao(vertex(3), vertex(26))
    except Exception as exc:  # noqa: BLE001
        boundary_err = str(exc)[:200]
    gaps.append({
        "case_id": "cmb_cjt_fisher_rao_accepts_closed_boundary",
        "category": "known_gap",
        "block": "B_behavioural",
        "description": (
            "`cas_forex/cjt_differential.py:55` normalizes its inputs and only "
            "rejects NEGATIVE entries, so it silently accepts simplex-boundary "
            "vectors containing zeros - exactly the vectors Chapter_21:98 "
            "forbids as addresses."
        ),
        "hoped": "rejected",
        "observed": ("accepted" if boundary_d is not None else "rejected")
                    + (f", returned {boundary_d:.6f}" if boundary_d is not None else boundary_err),
        "is_gap": boundary_d is not None,
        "disposition": (
            "SCOPE NOTE, NO CODE CHANGE. That function is a CJT divergence "
            "heuristic over activation distributions (cjt_analysis.py:55-98), not "
            "a CMB address decoder, and normalizing arbitrary non-negative "
            "activations is correct for that job. It must NOT be used as the "
            "address-decode path: the two implementations that are open-simplex "
            "strict (cas_engine, geodesic_memory) are the ones a CMB read path "
            "would have to use. Recorded so that a future CMB build does not "
            "reach for the nearest available Fisher-Rao function."
        ),
        "evidence": {"distance": boundary_d, "error": boundary_err},
        "record_type": "gap_probe",
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    })

    # ---- B5: nearest-neighbour recovery vs perturbation -------------------
    curve: list[dict[str, Any]] = []
    for eps in EPS_SWEEP:
        rng_eps = random.Random(PREREG["seed"] + int(eps * 1000) + 1)
        hits1 = hits3 = trials = 0
        dists: list[float] = []
        for _ in range(PREREG["banks_per_point"]):
            bank = build_bank(rng_eps, NUM_STATES)
            for _ in range(PREREG["queries_per_bank"]):
                target = rng_eps.randrange(NUM_STATES)
                query = (list(bank[target]) if eps == 0.0
                         else blend(bank[target], dirichlet(rng_eps), eps))
                ranked = nearest_by_fisher_rao(query, bank)
                trials += 1
                if ranked[0][0] == target:
                    hits1 += 1
                if target in [i for i, _ in ranked[:3]]:
                    hits3 += 1
                dists.append(ranked[0][1])
        curve.append({
            "eps": eps, "K": NUM_STATES, "trials": trials,
            "top1": hits1 / trials, "top3": hits3 / trials,
            "chance": 1.0 / NUM_STATES,
            "mean_top1_distance": statistics.fmean(dists),
        })
    metrics["recovery_curve_eps"] = curve

    accept_points = [c for c in curve if c["eps"] <= PREREG["recovery_accept_eps"]]
    worst = min(c["top1"] for c in accept_points)
    case("cmb_nearest_neighbour_recovery_low_perturbation", "retrieval",
         "Pre-registered gate: top-1 recovery of the intended stored vector must "
         f"be {PREREG['recovery_accept_top1']:.2f} for perturbation eps <= "
         f"{PREREG['recovery_accept_eps']}, over a bank of "
         f"{NUM_STATES} synthetic open-simplex records.",
         f"top1 = {PREREG['recovery_accept_top1']:.2f}",
         "; ".join(f"eps={c['eps']}: top1={c['top1']:.3f}" for c in accept_points),
         worst >= PREREG["recovery_accept_top1"],
         {"curve": curve, "chance": 1.0 / NUM_STATES,
          "note": "the sort is written by this eval; the metric is the repo's"})

    collapse = next((c["eps"] for c in curve if c["top1"] < 0.5), None)
    case("cmb_recovery_degrades_with_perturbation", "retrieval",
         "The retrieval test must be capable of failing: top-1 accuracy must "
         "fall as the query is corrupted, and approach chance at high eps. A "
         "curve that stays flat at 1.0 would mean the case cannot fail and is "
         "worthless.",
         "top1 at eps=0.80 strictly below top1 at eps=0.00",
         f"top1(0.00)={curve[0]['top1']:.3f} -> top1(0.80)={curve[-1]['top1']:.3f}",
         curve[-1]["top1"] < curve[0]["top1"],
         {"first_eps_below_half": collapse, "chance": 1.0 / NUM_STATES})

    # ---- B6: rank stability vs bank size ---------------------------------
    k_curve: list[dict[str, Any]] = []
    for k in K_SWEEP:
        rng_k = random.Random(PREREG["seed"] + 7000 + k)
        hits1 = hits3 = trials = 0
        for _ in range(PREREG["banks_per_point"]):
            bank = build_bank(rng_k, k)
            for _ in range(PREREG["queries_per_bank"]):
                target = rng_k.randrange(k)
                query = blend(bank[target], dirichlet(rng_k), K_SWEEP_EPS)
                ranked = nearest_by_fisher_rao(query, bank)
                trials += 1
                if ranked[0][0] == target:
                    hits1 += 1
                if target in [i for i, _ in ranked[:3]]:
                    hits3 += 1
        k_curve.append({"K": k, "eps": K_SWEEP_EPS, "trials": trials,
                        "top1": hits1 / trials, "top3": hits3 / trials,
                        "chance": 1.0 / k})
    metrics["recovery_curve_bank_size"] = k_curve
    case("cmb_recovery_reported_across_bank_sizes", "retrieval",
         "A retrieval claim that only holds at a tiny bank is not a retrieval "
         "claim. Top-1 and top-3 are reported at K=5,10,20,40 with eps fixed at "
         f"{K_SWEEP_EPS}, and must stay above chance at the full 40-cell size.",
         "top1 at K=40 strictly above chance (0.025)",
         f"top1(K=40)={k_curve[-1]['top1']:.3f} vs chance {k_curve[-1]['chance']:.3f}",
         k_curve[-1]["top1"] > k_curve[-1]["chance"], {"curve": k_curve})

    # ---- B6b: recovery vs inter-cell separation --------------------------
    # This is the hard regime. The eps sweep above uses a well-separated bank
    # and is easy by construction; reported as such. Here the bank is packed.
    sep_curve: list[dict[str, Any]] = []
    for sep in SEP_SWEEP:
        rng_s = random.Random(PREREG["seed"] + 8000 + int(sep * 1000))
        hits1 = hits3 = trials = 0
        seps: list[float] = []
        for _ in range(PREREG["banks_per_point"]):
            bank = build_tight_bank(rng_s, NUM_STATES, sep)
            seps.append(mean_nearest_separation(bank))
            for _ in range(PREREG["queries_per_bank"]):
                target = rng_s.randrange(NUM_STATES)
                query = blend(bank[target], dirichlet(rng_s), SEP_SWEEP_EPS)
                ranked = nearest_by_fisher_rao(query, bank)
                trials += 1
                if ranked[0][0] == target:
                    hits1 += 1
                if target in [i for i, _ in ranked[:3]]:
                    hits3 += 1
        sep_curve.append({"sep": sep, "eps": SEP_SWEEP_EPS, "trials": trials,
                          "top1": hits1 / trials, "top3": hits3 / trials,
                          "chance": 1.0 / NUM_STATES,
                          "mean_nearest_cell_distance": statistics.fmean(seps)})
    metrics["recovery_curve_separation"] = sep_curve
    case("cmb_recovery_degrades_with_cell_crowding", "retrieval",
         "Chapter_21:251 claims inter-cell Fisher-Rao separation is what holds "
         "false recall down. Measure it: with query perturbation fixed at "
         f"{SEP_SWEEP_EPS}, sweep how tightly the bank is packed. Top-1 must "
         "collapse as cells crowd together, otherwise the recovery measurement "
         "is not sensitive to the thing the book says matters.",
         "top1 at the tightest packing strictly below top1 at the widest",
         f"top1(sep={sep_curve[0]['sep']})={sep_curve[0]['top1']:.3f} vs "
         f"top1(sep={sep_curve[-1]['sep']})={sep_curve[-1]['top1']:.3f}",
         sep_curve[0]["top1"] < sep_curve[-1]["top1"], {"curve": sep_curve})

    # ---- B7: negative control - a query with no true neighbour -----------
    rng_nc = random.Random(PREREG["seed"] + 99)
    nc_bank = build_bank(rng_nc, NUM_STATES)
    uniform_q = _normalize([1.0 / NUM_STATES] * NUM_STATES)
    nc_top = nearest_by_fisher_rao(uniform_q, nc_bank)[0]
    metrics["negative_control_top1_distance"] = nc_top[1]
    case("cmb_negative_control_no_true_neighbour", "negative_control",
         "A near-uniform query has no stored neighbour. Its top-1 distance must "
         f"exceed the pre-registered no-match radius of {PREREG['no_match_radius']} rad. "
         "If a confident top-1 comes back for a query with no true neighbour, "
         "that is Chapter_21:275's 'Lacuna misread as memory'.",
         f"top-1 distance > {PREREG['no_match_radius']}",
         f"{nc_top[1]:.6f}", nc_top[1] > PREREG["no_match_radius"],
         {"nearest_index": nc_top[0]})

    true_q = blend(nc_bank[7], dirichlet(rng_nc), 0.05)
    tq_top = nearest_by_fisher_rao(true_q, nc_bank)[0]
    metrics["true_match_top1_distance"] = tq_top[1]
    case("cmb_negative_control_false_positive_counterpart", "negative_control",
         "The counterpart: a query that IS a lightly perturbed copy of a stored "
         "record must fall INSIDE the same radius, and must return that record. "
         "A radius that rejects genuine matches would make the negative control "
         "meaningless.",
         f"top-1 distance < {PREREG['true_match_radius']} and index == 7",
         f"distance={tq_top[1]:.6f} index={tq_top[0]}",
         tq_top[1] < PREREG["true_match_radius"] and tq_top[0] == 7, {})

    # ---- B8: the repo's only retrieval function is not nearest-neighbour --
    near_light = GeodesicBelief(
        claim_key="near_light", claim_text="near, light",
        cas_expression="^3^P_{F7}|f", simplex=tuple(blend(nc_bank[7], dirichlet(rng_nc), 0.05)),
        mass=1.0, confidence=1.0, source="eval", timestamp=utc_now(),
    )
    far_heavy = GeodesicBelief(
        claim_key="far_heavy", claim_text="far, heavy",
        cas_expression="^8^C_{F2}|A", simplex=tuple(nc_bank[23]),
        mass=50.0, confidence=1.0, source="eval", timestamp=utc_now(),
    )
    got = retrieve_by_geodesic_gravity(query_simplex=true_q,
                                       beliefs=[near_light, far_heavy], top_k=2)
    ranked_keys = [r.claim_key for r in got]
    dist_map = {r.claim_key: r.distance for r in got}
    grav_map = {r.claim_key: r.gravity for r in got}
    metrics["gravity_rank1"] = ranked_keys[0]
    metrics["gravity_distances"] = dist_map
    metrics["gravity_scores"] = grav_map
    gaps.append({
        "case_id": "cmb_only_repo_retrieval_is_gravity_not_nearest",
        "category": "known_gap",
        "block": "B_behavioural",
        "description": (
            "Chapter_21:117 and :207 specify `nearest(query, bank, "
            "metric=fisher_rao)`. No such function exists. The only retrieval "
            "function in the repo, `retrieve_by_geodesic_gravity`, ranks by "
            "effective_mass / (distance + floor). Put a near-light record and a "
            "far-heavy record in front of it and see which comes back first."
        ),
        "hoped": "nearest record returned at rank 1",
        "observed": (f"rank 1 = {ranked_keys[0]} "
                     f"(near d={dist_map.get('near_light', float('nan')):.4f} "
                     f"gravity={grav_map.get('near_light', float('nan')):.3f}; "
                     f"far d={dist_map.get('far_heavy', float('nan')):.4f} "
                     f"gravity={grav_map.get('far_heavy', float('nan')):.3f})"),
        "is_gap": ranked_keys[0] != "near_light",
        "disposition": (
            "BEHAVIOURAL DIVERGENCE, RECORDED, NOT WAIVED. The gravity ranking is "
            "correct for what it was built for - CABS idea-gravity, where a heavy "
            "belief is meant to pull from further away - and it is NOT a bug. But "
            "it is not the CMB read path the book specifies, and it would return "
            "the wrong cell for a CMB query. Consequence for this eval, stated "
            "plainly in the report: the pure-distance sort used in the recovery "
            "measurements above was WRITTEN BY THIS EVAL, not taken from the "
            "repo. The metric is the repo's; the nearest-neighbour selector is "
            "not. Chapter_21:117 has no implementation."
        ),
        "evidence": {"ranked": ranked_keys, "distances": dist_map, "gravity": grav_map},
        "record_type": "gap_probe",
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    })

    # Gap: no abstention. The retrieval layer always returns a rank-1 result.
    abst = retrieve_by_geodesic_gravity(query_simplex=uniform_q,
                                        beliefs=[near_light, far_heavy], top_k=1)
    gaps.append({
        "case_id": "cmb_retrieval_has_no_abstain_path",
        "category": "known_gap",
        "block": "B_behavioural",
        "description": (
            "Chapter_21:275 names 'Lacuna misread as memory' as a failure mode: "
            "the system recalls an experience it never had. Check whether the "
            "retrieval layer can decline to answer a query with no neighbour."
        ),
        "hoped": "empty result or a no-match signal",
        "observed": (f"returned {len(abst)} result(s), rank 1 = "
                     f"{abst[0].claim_key if abst else 'none'} at distance "
                     f"{abst[0].distance:.4f}" if abst else "returned 0 results"),
        "is_gap": len(abst) > 0,
        "disposition": (
            "CONFIRMED GAP, OPEN. `retrieve_by_geodesic_gravity` has no distance "
            "cutoff and no abstain path; it returns top_k results for any legal "
            "query. The negative control above shows the DISTANCE is informative "
            "(measured above the no-match radius), so an abstain threshold is "
            "implementable - it just is not implemented. Chapter 21's own failure "
            "mode is therefore live in the only retrieval code that exists. Not "
            "closed by this eval, and the eval does not add the threshold to the "
            "repo; it only measures that the signal to build one is present."
        ),
        "evidence": {"n_returned": len(abst),
                     "distance": abst[0].distance if abst else None,
                     "no_match_radius": PREREG["no_match_radius"]},
        "record_type": "gap_probe",
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    })

    return cases, gaps, metrics


# ==========================================================================
# reporting
# ==========================================================================
def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    text = "".join(json.dumps(r, sort_keys=True, default=str) + "\n" for r in rows)
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _table(rows: list[dict[str, Any]]) -> str:
    out = ["| Case | Category | Expected | Observed | Passed |", "|---|---|---|---|---:|"]
    for r in rows:
        out.append(f"| `{r['case_id']}` | `{r['category']}` | {r['expected']} | "
                   f"{r['observed']} | `{str(r['passed']).lower()}` |")
    return "\n".join(out)


def main() -> int:
    generated_at = utc_now().isoformat()
    WORKING_DIR.mkdir(parents=True, exist_ok=True)

    attacks, benign, gaps_a = run_structural(generated_at)
    beh, gaps_b, metrics = run_behavioural(generated_at)
    gaps = gaps_a + gaps_b

    metric_row = {"record_type": "metrics", "run_id": RUN_ID,
                  "reviewer_id": REVIEWER_ID, "generated_at": generated_at,
                  "prereg": PREREG, "metrics": metrics}

    raw = WORKING_DIR / f"cmb_memory_retrieval_eval_raw_{DATE_TAG}.jsonl"
    raw_hash = _write_jsonl(raw, attacks + benign + beh + gaps + [metric_row])

    a_pass = sum(1 for r in attacks if r["passed"])
    b_pass = sum(1 for r in benign if r["passed"])
    h_pass = sum(1 for r in beh if r["passed"])
    all_cases = attacks + benign + beh
    total = len(all_cases)
    passed = a_pass + b_pass + h_pass
    real_gaps = [g for g in gaps if g["is_gap"]]
    failures = [r for r in all_cases if not r["passed"]]
    result = "PASS" if not failures else "FAIL"

    curve = metrics["recovery_curve_eps"]
    kcurve = metrics["recovery_curve_bank_size"]
    scurve = metrics["recovery_curve_separation"]
    eps_tbl = "\n".join(
        [f"| {c['eps']:.2f} | {c['trials']} | {c['top1']:.3f} | {c['top3']:.3f} | "
         f"{c['chance']:.3f} | {c['mean_top1_distance']:.4f} |" for c in curve])
    k_tbl = "\n".join(
        [f"| {c['K']} | {c['eps']:.2f} | {c['trials']} | {c['top1']:.3f} | "
         f"{c['top3']:.3f} | {c['chance']:.3f} |" for c in kcurve])
    s_tbl = "\n".join(
        [f"| {c['sep']:.2f} | {c['mean_nearest_cell_distance']:.4f} | {c['trials']} | "
         f"{c['top1']:.3f} | {c['top3']:.3f} | {c['chance']:.3f} |" for c in scurve])

    report = WORKING_DIR / f"cmb_memory_retrieval_eval_report_{DATE_TAG}.md"
    body = f"""# CMB Memory Retrieval — Structural and Behavioural Eval Report

Generated: `{generated_at}`
Reviewer identity: `{REVIEWER_ID}`
Reviewer type: AI/local code reviewer attestation, not a human signature.
Receipt targeted: `memory_board_cognitive_memory_claim__cmb_memory_retrieval_eval_pass`
Result: `{result}`
Cases passed: `{passed}/{total}`  (structural adversarial `{a_pass}/{len(attacks)}`,
structural false-positive `{b_pass}/{len(benign)}`, behavioural `{h_pass}/{len(beh)}`)
Unenforced properties / confirmed gaps: `{len(real_gaps)}`

## The one-line finding

**The metric is real and retrieval over it works; the board is not built.**

## Scope

Two blocks, and the difference between them is the whole point of this report.

**Block A is STRUCTURAL — compile-level only.** It observes that text is
accepted or rejected by a real parser and a real compiler. The three CMB
capacitor cells the book publishes (Chapter_21:28-30, Appendix_D:435-437) go
through `cas_forex/pcba_syntax.py` and `cas_forex/pcba_compiler.py`. Adversarial
weakenings of a memory cell — non-finite and negative capacitance, negative /
out-of-range / non-finite leakage, invalid Noetic, Drive and Register leaves —
are attempted against the same gates. The repo's own CMB reference design
(`cas_forex/ccb_designs.py:76-86`) is linted by the real CRC linter and
cross-checked against the Noetics the book names for the address decoder
(`^1^C`) and the refresh pump (`^7^C`). Board authority is read off
`build_pcba_licensing_report()`. **None of this is a behavioural measurement,
and nothing in Block A should ever be described as one.**

**Block B is BEHAVIOURAL — actual runtime measurement.** Fisher-Rao geodesic
distance `d_FR(p,q) = 2*arccos(sum_k sqrt(p_k q_k))` is executed on real numbers
in the three independent implementations this repo contains, and their agreement
is measured. Metric axioms are measured on {PREREG['n_axiom_vectors']} randomly
drawn open-simplex vectors. Nearest-neighbour recovery is measured as a curve
against perturbation magnitude and against bank size. A negative control
measures a query with no true neighbour. These numbers came out of running code.

## Out of scope, deliberately

This run does **not** establish any of the following, and no reader should take
it as doing so.

- **There is no model in the loop.** No language model was called, scored, or
  observed. Nothing here is telemetry.
- **Nothing was encoded from English.** The write path of Chapter_21:37-85 was
  not exercised. The Wrap pipeline's Input Analyzer, which Chapter_21:67 points
  at as the CMB's write head, does not emit a per-input 40-dimensional cognitive
  state vector; `api/pipeline/stages.py:1283` hands the inversion scanner
  `CognitiveStateVector.uniform()`, a placeholder. Every vector in Block B is a
  synthetic construction of this eval.
- **No capacitor was charged, discharged, leaked, or refreshed**, because no such
  object exists anywhere in this repository. There is no capacitor bank, no
  charge or discharge function, no leakage decay step and no refresh pump in any
  `.py` or `.rs` file. Requirement 4 of Chapter_21:16 ("hold and fade on a
  designed schedule") is not testable at any level beyond parsing the parameter,
  and this run did not test it.
- **No retrieval accuracy over real experiences was measured.** The records
  retrieved in Block B are random open-simplex points generated by this script.
  They are not stored experiences of any system, and top-1 accuracy over them is
  a property of the geometry, not of a memory.
- **Nothing persists.** `belief/geodesic_memory.py` retrieves over an in-memory
  list handed in by the caller; its own docstring (lines 14-19) says store
  migration and `BeliefStore.search_by_proximity` remain integration work.
  Chapter_21:283's "survivable across sessions" is untested and unbacked.
- **No lacunarity result.** That is the sibling receipt
  `cmb_lacunarity_eval_pass`, and this artifact does not touch it. Note for
  whoever picks it up: `cas-forex/cas_forex/nested_lacunarity.py` is about
  out-of-sample trading edge and is the WRONG module; the relevant machinery is
  `api/pipeline/lacunarity.py` and `cas-engine/src/scoring/lacunarity.rs`, and
  even those operate on assessment score vectors, not on a memory bank's charge.
- **No privacy, legal, governance or human-factors claim.** Those are separate
  receipts and remain unsigned.
- **This does not license live trading and does not create a broker `ACCEPT`
  path.** Verified as cases, not assumed.

## Pre-registered thresholds

Fixed before the run, carried over from the prior investigation's stated
suggestions. They were not adjusted to the observed numbers.

| Threshold | Value |
|---|---|
| identity tolerance | `{PREREG['identity_tol']:.0e}` |
| symmetry tolerance | `{PREREG['symmetry_tol']:.0e}` |
| triangle-inequality slack | `{PREREG['triangle_slack']:.0e}` |
| cross-implementation agreement | `{PREREG['cross_impl_tol']:.0e}` |
| top-1 recovery required at eps <= `{PREREG['recovery_accept_eps']}` | `{PREREG['recovery_accept_top1']:.2f}` |
| no-match radius (negative control) | `{PREREG['no_match_radius']}` rad |
| RNG seed | `{PREREG['seed']}` |

Overall result is `PASS` only if **every** case passes. Gaps are reported
separately and are never counted as passes.

## Block A — Structural: adversarial cases

{_table(attacks)}

## Block A — Structural: false-positive cases

Valid inputs that must NOT be rejected. A toolchain that refuses the board's own
published parts is a false-positive failure.

{_table(benign)}

## Block B — Behavioural: measured cases

{_table(beh)}

## Block B — Measured numbers

### Metric axioms and cross-implementation agreement

Three independent implementations of the book's formula, all executed:

- `noetic-compass/cas-native/belief/geodesic_memory.py` (pure Python, open-simplex strict)
- `cas_engine` (compiled Rust extension of `cas-engine/src/metric/mod.rs`, open-simplex strict)
- `cas-forex/cas_forex/cjt_differential.py` (the CJT gain metric)

| Measurement | Observed |
|---|---|
| max `\\|d(p,p)\\|`, scaffold Python | `{metrics['identity_max_scaffold_python']:.3e}` |
| max `\\|d(p,p)\\|`, compiled Rust engine | `{metrics['identity_max_rust_engine']:.3e}` |
| max `\\|d(p,q) - d(q,p)\\|` | `{metrics['symmetry_max_delta']:.3e}` |
| max disagreement, Python vs Rust | `{metrics['cross_impl_max_delta_python_vs_rust']:.3e}` |
| max disagreement, Python vs cas-forex | `{metrics['cross_impl_max_delta_python_vs_cas_forex']:.3e}` |
| triangle-inequality violations / `{PREREG['n_axiom_triples']}` triples | `{metrics['triangle_violations']}` |
| worst triangle excess | `{metrics['triangle_worst_excess']:.3e}` |

Chapter_21:100's cross-reference — Fisher-Rao is "the same metric the CJT uses
to measure gain (Chapter 9)" — is **verified and true**:
`cas_forex/cjt_analysis.py` imports `fisher_rao_distance` at line 24 and uses it
for large-signal beta, small-signal beta and transconductance at lines 55-98,
and the numbers agree with the retrieval implementation to
`{metrics['cross_impl_max_delta_python_vs_cas_forex']:.3e}`.

### Nearest-neighbour recovery vs perturbation (K = 40)

Query is `q = (1-eps)*target + eps*u` with `u` a random open-simplex point.
`{PREREG['banks_per_point']}` independent banks x `{PREREG['queries_per_bank']}`
queries per bank at each point.

| eps | trials | top-1 | top-3 | chance | mean top-1 distance |
|---:|---:|---:|---:|---:|---:|
{eps_tbl}

**Read this table honestly.** This bank is easy. Its records are random
Dirichlet draws blended toward different dominant states, so they sit far apart
in Fisher-Rao terms and top-1 holds at 1.000 until the query is 80% noise. That
is a real measurement but it is a weak discriminator, and it should not be
quoted on its own as evidence that "retrieval works". The regime where the
measurement earns its keep is the separation sweep below.

### Rank stability vs bank size (eps = {K_SWEEP_EPS})

| K | eps | trials | top-1 | top-3 | chance |
|---:|---:|---:|---:|---:|---:|
{k_tbl}

### Recovery vs inter-cell separation — the hard regime (eps = {SEP_SWEEP_EPS}, K = 40)

Bank records are packed around a shared centre; `sep` controls how far each
record sits from it. This measures Chapter_21:251's claim ("keeping cells far
enough apart in Fisher-Rao distance is what holds Lambda down") as a number.

| sep | mean nearest-cell distance | trials | top-1 | top-3 | chance |
|---:|---:|---:|---:|---:|---:|
{s_tbl}

This is where the retrieval test can fail, and does. Top-1 falls from
`{scurve[-1]['top1']:.3f}` at the widest packing to `{scurve[0]['top1']:.3f}` at
the tightest. The book's claim that cell separation controls false recall is
therefore **behaviourally confirmed as a mechanism** — while the book's own bank
topology, measured above, gives a designer no separation lever to pull.

### Negative control

| Measurement | Observed | Pre-registered |
|---|---:|---:|
| top-1 distance, near-uniform query with no stored neighbour | `{metrics['negative_control_top1_distance']:.6f}` | must exceed `{PREREG['no_match_radius']}` |
| top-1 distance, genuine eps=0.05 query | `{metrics['true_match_top1_distance']:.6f}` | must fall under `{PREREG['true_match_radius']}` |

### The book's own bank, measured

The bank Chapter_21:22-24 defines is one cell per cognitive state. Measured
directly, from a `^3^P` query, using the repo's own implementations:

| Measurement | Observed |
|---|---:|
| `d_FR(query, P3)` | `{metrics['book_bank_d_p3']:.6f}` |
| `d_FR(query, E6)` | `{metrics['book_bank_d_e6']:.12f}` |
| `d_FR(query, C8)` | `{metrics['book_bank_d_c8']:.12f}` |
| distinct pairwise distances among all 40 cells (780 pairs) | `{metrics['book_bank_distinct_pairwise_distances']}` |
| that single value | `{metrics['book_bank_pairwise_value']}` |
| vertex reading: `d_FR(P3, E6)` | `{metrics['book_bank_vertex_d_e6']:.6f}` |
| vertex reading: `d_FR(P3, C8)` | `{metrics['book_bank_vertex_d_c8']:.6f}` |

### Tie-breaking resolution floor

| Measurement | Observed |
|---|---:|
| Rust engine, `d(v, v)` on identical smoothed vectors | `{metrics['floor_rust_identical_vectors']:.3e}` |
| Scaffold Python, `d(v, v+1e-12)` on a genuinely perturbed vector | `{metrics['floor_python_1e12_perturbation']:.3e}` |
| Rust engine, same perturbed pair | `{metrics['floor_rust_1e12_perturbation']:.3e}` |

## Failures observed

"""
    if failures:
        for r in failures:
            body += (f"### `{r['case_id']}` — FAILED\n\n"
                     f"{r['description']}\n\n"
                     f"- Expected: {r['expected']}\n"
                     f"- Observed: {r['observed']}\n"
                     f"- Block: `{r['block']}`\n\n")
    else:
        body += "None.\n\n"

    body += """No failing case was repaired by weakening the case. Each one above
stands as written.

## Unenforced properties and confirmed gaps

Properties the book's prose leans on that nothing in the toolchain enforces,
plus the representation defects found while building this eval. These are
recorded as findings, never as passes. Each carries its disposition.

"""
    for g in real_gaps:
        body += (f"### `{g['case_id']}`\n\n"
                 f"{g['description']}\n\n"
                 f"- Hoped `{g['hoped']}`, observed `{g['observed']}`.\n"
                 f"- Block: `{g['block']}`\n"
                 f"- **Disposition:** {g['disposition']}\n\n")
    if not real_gaps:
        body += "None.\n\n"

    body += f"""## Book overclaims found

These are findings about the BOOK, stated with file and line.

1. **`Chapter_21_CMB_Cognitive_Memory_Board.md:7`** — "we wire forty of them into
   a board with a write path, an address decoder, a read path, and a refresh
   circuit, and **we run real structural queries against it**." No query is ever
   run against any implementation. There is no bank object, no address decoder
   function, and no retrieval call in this codebase. The chapter's results at
   lines 208-213 are asserted prose. The chapter's own Honesty callout at line
   217 disclaims only the charge/discharge/leakage *numbers* as a design model;
   it does not disclaim the query result, so line 7 stands unqualified.
2. **`Chapter_21:208-210` and `Appendix_D_CCB_Reference_Designs.md:473-475`** —
   the published ranking "P3 (d_FR ~ 0.0) ... E6 (d_FR larger) ... C8 (d_FR
   larger still)" is **not derivable** from Fisher-Rao geometry on the bank the
   book defines. Measured above: E6 and C8 are exactly equidistant from a `^3^P`
   query under both the vertex and smoothed readings. `Chapter_21:209`'s
   explanation ("same Evaluative neighborhood, different Noetic") asserts a
   graded cognitive-neighbourhood structure the metric does not have on a
   one-cell-per-state bank. `Chapter_21:223`, `Chapter_21:309` (Exercise 21.2
   asks students to produce this ordering) and `Appendix_E_Exercise_Answers.md:736`
   inherit the same defect.
3. **`Chapter_21:98` and `:263` versus `:22-24`** — internal contradiction about
   where a cell lives. The address is specified as a point on the **open**
   simplex, "p_k > 0 for every state". But the bank is 40 cells, one per
   cognitive state, and the book never says what a cell's coordinate is. The
   natural reading (cell k at vertex e_k) puts every cell **outside** the open
   simplex, where the book's own constraint forbids it and where
   `cas_engine.CognitiveStateVector` refuses to construct it — verified as a case
   above. This is why Block B could not use the book's own bank and had to
   substitute smoothed interior points.
4. **`Chapter_21:251`** — "Keeping cells far enough apart in Fisher-Rao distance
   is what holds Lambda down." Measured: under the bank as defined, all 780
   inter-cell distances are a single value. Inter-cell separation is not a design
   parameter available to anyone following the book's own topology. Recorded as a
   failing case above.
5. **`Chapter_21:217`** — the Honesty callout's own worked number does not
   reproduce. It says "when the board reports the C8 cell decayed below threshold
   at unit 40, that is (1 - 0.05)^t crossing 0.05". Computed: `0.95^40 = 0.1285`,
   well above 0.05; `0.95^t = 0.05` gives `t = 58.40`; and starting from the
   chapter's own largest C8 impression `V = 0.30` (memory #5, line 194),
   `0.30*0.95^t = 0.05` gives `t = 34.93`. Neither reading yields 40. The callout
   is right in spirit — the number is arithmetic, not telemetry — but the
   specific number it quotes is not the arithmetic it cites. Exercise 21.4's
   answer (`Appendix_E:753`, `ln0.5/ln0.99 = 68.97`) checks out exactly, so this
   is an isolated slip.
6. **`Appendix_D:413` versus `:435-437`** — Appendix D declares the cell form as
   "each cell: `Capacitor< ^5 state, C, leakage >`" and then publishes three
   cells, none of them `^5`. Recorded as an open gap above; both readings compile
   clean, so no compiler can catch it.
7. **`Chapter_21:283`** — "survivable across sessions". Nothing in the retrieval
   path persists.
8. **NOT an overclaim, recorded so it is not mistakenly flagged:**
   `Chapter_21:100`'s cross-reference to the CJT metric is **true and verified**
   (see the agreement table above).

## Mitigations and limits

- The claim this artifact supports is exactly two things. **(1) Structural:** the
  three published CMB capacitor cells survive the real PCBA parser and the real
  CAS compiler; the named parameter gates reject the attempted weakenings of a
  memory cell; the repo's reduced CMB reference design lints ERROR-free and uses
  the `^1^C` decoder and `^7^C` refresh Noetics the book names; and the CMB
  carries no live-trading and no broker-`ACCEPT` authority. **(2) Behavioural:**
  the Fisher-Rao geodesic distance the book prescribes is implemented correctly
  and identically in three independent places in this repo, satisfies
  identity / symmetry / triangle inequality on random open-simplex vectors, and
  supports nearest-neighbour recovery of an intended target from a bank of
  synthetic 40-dimensional open-simplex vectors, with top-1 accuracy reported as
  a curve against perturbation and bank size including where it collapses.
- **The nearest-neighbour selector used in Block B was written by this eval.**
  The metric is the repo's; the sort is not. `nearest(query, bank,
  metric=fisher_rao)` does not exist in this codebase, and the only retrieval
  function that does exist ranks by mass over distance and was measured returning
  a far record ahead of a near one. This distinction is not cosmetic and must
  survive into any summary of this artifact.
- This evidence does **not** support a claim that any deployed system stores,
  addresses, refreshes or recalls anything.
- On its own this artifact is not sufficient to sign
  `cmb_memory_retrieval_eval_pass` for the claim as Chapter 21 currently words
  it, because the chapter's own published retrieval result is a failing case
  above. It is sufficient evidence for a narrowed claim: the retrieval
  *geometry* is real, correct and measured.

## Raw Evidence

- Path: `docs\\working\\{raw.name}`
- SHA-256: `{raw_hash}`
- JSONL records: `{len(attacks) + len(benign) + len(beh) + len(gaps) + 1}`
- Script: `cas-forex\\scripts\\generate_cmb_memory_retrieval_eval_artifacts.py`
- Determinism: the RNG is seeded with `{PREREG['seed']}`, so every measured
  number above reproduces exactly on re-run. The SHA-256 above does **not**
  reproduce, because each JSONL row carries its own `generated_at` timestamp.
  The hash pins this run's file, not the computation.
"""
    report.write_text(body, encoding="utf-8", newline="\n")

    print(f"result             : {result}")
    print(f"structural attack  : {a_pass}/{len(attacks)}")
    print(f"structural benign  : {b_pass}/{len(benign)}")
    print(f"behavioural        : {h_pass}/{len(beh)}")
    print(f"gaps confirmed     : {len(real_gaps)}")
    for g in real_gaps:
        print(f"   GAP  {g['case_id']}: hoped {g['hoped']}, observed {g['observed']}")
    for r in failures:
        print(f"   FAIL {r['case_id']}: expected {r['expected']} | observed {r['observed']}")
    print("\nrecovery curve (K=40):")
    for c in curve:
        print(f"   eps={c['eps']:.2f}  top1={c['top1']:.3f}  top3={c['top3']:.3f}  "
              f"chance={c['chance']:.3f}")
    print("bank-size curve (eps=%.2f):" % K_SWEEP_EPS)
    for c in kcurve:
        print(f"   K={c['K']:>3}  top1={c['top1']:.3f}  top3={c['top3']:.3f}  "
              f"chance={c['chance']:.3f}")
    print("separation curve (eps=%.2f, K=40):" % SEP_SWEEP_EPS)
    for c in scurve:
        print(f"   sep={c['sep']:.2f}  mean_nearest_d={c['mean_nearest_cell_distance']:.4f}  "
              f"top1={c['top1']:.3f}  top3={c['top3']:.3f}")
    print(f"\nreport : {report}")
    print(f"raw    : {raw}")
    print(f"sha256 : {raw_hash}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
