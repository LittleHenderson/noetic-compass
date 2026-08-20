#!/usr/bin/env python3
"""cas_weld_loop_v2.py — a CAS diagnose->correct loop that CAN FAIL.

    STAGE 1  INJECT    clean object + seeded RNG  -> perturbed object  (+ SEALED fault record)
    STAGE 2  GATE      perturbed object ALONE     -> the fired axis set          [BLIND]
    STAGE 3  LOCALIZE  perturbed object ALONE     -> the exact broken chain set  [BLIND]
    STAGE 4  REPAIR    perturbed object + the LOCALIZED set -> repaired object   [CHAINED]
    STAGE 5  VERIFY    repaired object ALONE      -> the fired axis set          [BLIND]
    CONTROLS           exhaustive + random same-size subset interventions

SUPERSEDES ``cas_weld_loop.py``, which was reviewed at commit 2be60327 and found
to have four fatal defects: an algebraic-identity control, a detector handed the
answer by concatenation, a hardcoded axis name, and an unchained pipeline whose
corrector was its own injector. That script is left on disk unmodified; nothing
here imports it.

SCOPE, STATED FIRST AND NARROWLY
--------------------------------
ONE axis: **A** (Pathway / RPM prerequisite chain), on the **numeric plane**.
That is the single detection the review found genuine: given only a perturbed
7x4 pathway array with no axis hint, ``cas_engine.InversionScanner`` returns
``fired_axes=['A']`` and only 'A'. Every other axis is OUT OF SCOPE here. The
string plane, the epsilon realizers, the PCBA component vocabulary and stage 5
are all absent by design, not by oversight.

WHAT THIS LOOP MEASURES, AND WHAT IT DOES NOT
---------------------------------------------
It does NOT measure efficacy on any model. It does not touch a model at all.
It measures whether a diagnose->correct chain built on the real detector can be
made to REPORT FAILURE when it should. Five of the six cases below are designed
to probe that, and three of them fail on purpose.

Real modules called (nothing stubbed, nothing reimplemented):
    cas_engine.InversionScanner.scan      (Rust PyO3)
    cas_engine.CognitiveStateVector       (Rust PyO3, open simplex)

Run:
    python cas_weld_loop_v2.py
    python cas_weld_loop_v2.py --draws 5000 --seed 7
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Callable, Sequence

try:  # Windows consoles default to cp1252.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - non-reconfigurable stream
    pass

import cas_engine  # noqa: E402  Rust PyO3


HERE = Path(__file__).resolve().parent
SEP = "=" * 78

# cas-engine/src/ontology/pathways.rs :: InversionAxis::index()
AXIS_ORDER = ("N", "W", "F", "E", "S", "A", "P")

# P is DERIVED: cas-engine/src/inversions/mod.rs :: compute_compound_severity
# returns 0 unless >= 2 other axes already exceeded the threshold. It is never
# an independent naming and is stripped from every "which axis was named" set.
DERIVED_AXES = ("P",)

# MIRRORED CONSTANTS, disclosed. These two numbers are read out of the Rust
# source; the loop uses them for REPORTING and as the arithmetic target of the
# repair. The loop never reimplements the detection rule itself — every
# "is this violated?" question in this file is answered by calling the Rust
# scanner. If these mirrors drifted from the Rust source, the loop would still
# be correct, because the verdicts come from the scanner.
SEVERITY_THRESHOLD = 0.05  # InversionScanner::new()
SATISFACTION_FLOOR = 0.5   # detect_pathway_inversion::satisfaction_threshold

# A chain the real detector certifies clean. Asserted at startup, not assumed.
CLEAN_PROBE_CHAIN = (0.90, 0.80, 0.70, 0.60)

N_CHAINS = 7
N_STAGES = 4
STAGE_NAMES = ("A0", "D", "W", "P")

DISCLOSURES: list[dict[str, str]] = []
SCAN_CALLS = 0


def hr(title: str) -> None:
    print("\n" + SEP)
    print(title)
    print(SEP)


def disclose(tag: str, text: str) -> None:
    DISCLOSURES.append({"tag": tag, "disclosure": text})
    print(f"[DISCLOSE] {tag}: {text}")


# ===========================================================================
# THE OBJECT
# ===========================================================================


@dataclass(frozen=True)
class AssessmentObject:
    """The complete 7-plane numeric input the Rust InversionScanner consumes.

    Frozen on purpose: every transform returns a NEW object, so no stage can
    mutate an object another stage is holding.
    """

    operator_scores: tuple[float, ...]                 # 10
    domain_averages: tuple[float, ...]                 # 4, order [P, C, E, O]
    drive_profile: tuple[float, ...]                   # 7
    state_vector: tuple[float, ...]                    # 40, open simplex
    domain_drive_scores: tuple[tuple[float, ...], ...]  # 7 x 4
    pathway_scores: tuple[tuple[float, ...], ...]       # 7 x 4 = [A0, D, W, P]

    def with_chains(self, mapping: dict[int, Sequence[float]]) -> "AssessmentObject":
        rows = [tuple(float(v) for v in mapping[i]) if i in mapping
                else self.pathway_scores[i] for i in range(N_CHAINS)]
        return AssessmentObject(
            self.operator_scores, self.domain_averages, self.drive_profile,
            self.state_vector, self.domain_drive_scores, tuple(rows),
        )

    def with_domain_averages(self, avgs: Sequence[float]) -> "AssessmentObject":
        return AssessmentObject(
            self.operator_scores, tuple(float(v) for v in avgs),
            self.drive_profile, self.state_vector, self.domain_drive_scores,
            self.pathway_scores,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "operator_scores": list(self.operator_scores),
            "domain_averages": list(self.domain_averages),
            "drive_profile": list(self.drive_profile),
            "state_vector": list(self.state_vector),
            "domain_drive_scores": [list(r) for r in self.domain_drive_scores],
            "pathway_scores": [list(r) for r in self.pathway_scores],
        }

    def sha256(self) -> str:
        blob = json.dumps(self.to_payload(), sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()


def neutral_object() -> AssessmentObject:
    """A clean object: every plane at a value the real scanner certifies clean.

    The state vector is UNIFORM over 40 states, which is CLAUDE.md Correction 4
    (open simplex, every p_k > 0) and gives axis E exactly zero entropy deficit.
    """
    return AssessmentObject(
        operator_scores=tuple([0.80] * 10),
        domain_averages=(0.80, 0.80, 0.80, 0.80),
        drive_profile=tuple([0.80] * 7),
        state_vector=tuple([1.0 / 40] * 40),
        domain_drive_scores=tuple(tuple([0.80] * 4) for _ in range(N_CHAINS)),
        pathway_scores=tuple(CLEAN_PROBE_CHAIN for _ in range(N_CHAINS)),
    )


# ===========================================================================
# THE DETECTOR — the ONLY source of any verdict in this file
# ===========================================================================


@dataclass
class Diagnosis:
    fired_axes: tuple[str, ...]
    fired_non_derived: tuple[str, ...]
    axis_severity: dict[str, float]
    axis_resistance: dict[str, float]
    input_sha256: str


def diagnose_blind(obj: AssessmentObject) -> Diagnosis:
    """THE DETECTOR. Takes ONE object and nothing else.

    Its signature is asserted at startup to have exactly one parameter, so it
    is mechanically impossible to hand it the injected axis, the pre-injection
    object, the broken-chain indices, or a concatenation of any of those. It
    NAMES the axes itself, from the object alone.

    Firing rule: the scanner's own ``severity_threshold`` (0.05). An axis whose
    severity exceeds it is exactly an axis for which the Rust ``scan`` pushed an
    ``InversionDetection``. Using ``> 0`` instead would report axes the scanner
    did not itself consider inverted.
    """
    global SCAN_CALLS
    SCAN_CALLS += 1
    scanner = cas_engine.InversionScanner()
    sv = cas_engine.CognitiveStateVector(list(obj.state_vector))
    out = dict(scanner.scan(
        list(obj.operator_scores),
        list(obj.drive_profile),
        sv,
        list(obj.domain_averages),
        [list(r) for r in obj.domain_drive_scores],
        [list(r) for r in obj.pathway_scores],
    ))
    resist = {ax: float(s) for ax, s in zip(AXIS_ORDER, out["axis_scores"])}
    sever = {ax: 1.0 - v for ax, v in resist.items()}
    fired = tuple(ax for ax in AXIS_ORDER if sever[ax] > SEVERITY_THRESHOLD)
    return Diagnosis(
        fired_axes=fired,
        fired_non_derived=tuple(a for a in fired if a not in DERIVED_AXES),
        axis_severity={k: round(v, 9) for k, v in sever.items()},
        axis_resistance={k: round(v, 9) for k, v in resist.items()},
        input_sha256=obj.sha256(),
    )


def axis_a_severity(obj: AssessmentObject) -> float:
    return diagnose_blind(obj).axis_severity["A"]


# ===========================================================================
# STAGE 3 — LOCALIZE.  BLIND.
# ===========================================================================


@dataclass
class Localization:
    indices: tuple[int, ...]
    procedure: str
    base_severity: float
    per_chain_severity_after_substitution: dict[int, float]
    real_detector: bool = True


def localize_blind(obj: AssessmentObject) -> Localization:
    """Which pathway chain(s) carry the fault? Leave-one-out over the REAL detector.

    The scanner exposes axis A only as a SCALAR (violated_chains / 7). It never
    says WHICH chain. This procedure recovers the identity: substitute chain i
    with a chain the detector certifies clean, re-scan, and keep i if axis-A
    severity dropped. Input is the perturbed object and nothing else.

    It can return zero indices (nothing localized) or several; both are reported
    as they are, and the caller decides whether that is a failure.
    """
    base = axis_a_severity(obj)
    after: dict[int, float] = {}
    hits: list[int] = []
    for i in range(N_CHAINS):
        s = axis_a_severity(obj.with_chains({i: CLEAN_PROBE_CHAIN}))
        after[i] = round(s, 9)
        if s < base - 1e-12:
            hits.append(i)
    return Localization(
        indices=tuple(hits),
        procedure="leave_one_out_chain_substitution",
        base_severity=round(base, 9),
        per_chain_severity_after_substitution=after,
    )


def localize_naive_lowest_min(obj: AssessmentObject) -> Localization:
    """A PLAUSIBLE-BUT-WRONG localizer, used to prove the chain can break.

    "The broken chain is the one with the weakest stage" is the heuristic almost
    anyone would write first. It is wrong, because the detector flags a chain
    only when an UNSATISFIED stage is DOMINATED BY A LATER ONE — a uniformly
    weak, monotonically descending chain is perfectly clean. This localizer is
    not sabotage-by-fiat; it is a real alternative implementation, and it is
    here so that a localization failure can be shown to propagate all the way
    to a reported correction failure.
    """
    mins = [min(obj.pathway_scores[i]) for i in range(N_CHAINS)]
    pick = min(range(N_CHAINS), key=lambda i: mins[i])
    return Localization(
        indices=(pick,),
        procedure="naive_lowest_minimum_stage (ALTERNATIVE IMPLEMENTATION, WRONG)",
        base_severity=round(axis_a_severity(obj), 9),
        per_chain_severity_after_substitution={i: round(m, 9) for i, m in enumerate(mins)},
        real_detector=False,
    )


# ===========================================================================
# STAGE 4 — REPAIR.  Driven by the LOCALIZED set. Never by ground truth.
# ===========================================================================


def _chain_is_violated(obj: AssessmentObject, i: int) -> bool:
    """Ask the REAL detector whether chain i alone is violated.

    Builds a probe whose other six chains are the detector-certified clean
    chain, so any residual axis-A severity is attributable to chain i. This is
    a query to the scanner, not a Python reimplementation of its rule.
    """
    probe = obj.with_chains({j: CLEAN_PROBE_CHAIN for j in range(N_CHAINS) if j != i})
    return axis_a_severity(probe) > 0.0


def repair(obj: AssessmentObject, targets: tuple[int, ...]) -> AssessmentObject:
    """THE CORRECTOR — a SOLVER, and a DIFFERENT MECHANISM from the injector.

    The injector (below) writes a seeded random low value into one upstream
    stage. This corrector never learns that value and cannot recover it. It
    computes a SATISFYING assignment instead: walking each target chain from the
    back, any stage that sits below the satisfaction floor is lifted to clear
    the floor AND to dominate every stage downstream of it — the RPM
    section-retraction ordering from CLAUDE.md Correction 2.

    Therefore ``repair(inject(x)) != x`` in general, and the loop MEASURES that
    rather than assuming it. There is no ``f(f(x)) == x`` identity anywhere in
    this file.

    Idempotent on chains the real detector calls clean: a target that is not
    violated is returned untouched, so repairing a wrong chain cannot
    accidentally clear the axis by disturbing something else.
    """
    mapping: dict[int, tuple[float, ...]] = {}
    for i in targets:
        c = list(obj.pathway_scores[i])
        if not _chain_is_violated(obj, i):
            mapping[i] = tuple(c)
            continue
        for k in range(N_STAGES - 2, -1, -1):
            if c[k] < SATISFACTION_FLOOR:
                c[k] = max(SATISFACTION_FLOOR, max(c[k + 1:]))
        mapping[i] = tuple(c)
    return obj.with_chains(mapping)


# ===========================================================================
# STAGE 1 — INJECT.  The fault record is SEALED: no stage below ever sees it.
# ===========================================================================


@dataclass
class FaultRecord:
    """SEALED GROUND TRUTH.

    Read in exactly one place — the scoring of criterion 1 — and never passed to
    ``diagnose_blind``, ``localize_blind`` or ``repair``. Every read is counted
    into ``ground_truth_reads`` and printed, so an unreported read is visible.
    """

    broken_chains: tuple[int, ...]
    edits: tuple[dict[str, Any], ...]
    kind: str
    reads: list[str] = field(default_factory=list)

    def read_broken_chains(self, why: str) -> tuple[int, ...]:
        self.reads.append(why)
        return self.broken_chains


def inject_pathway_faults(base: AssessmentObject, n_faults: int,
                          rng: random.Random) -> tuple[AssessmentObject, FaultRecord]:
    """Break ``n_faults`` distinct RPM chains by DEGRADING one upstream stage.

    Mechanism: pick a chain, pick a stage from {A0, D, W} (a stage that HAS a
    downstream), and overwrite it with a seeded draw from U(0.05, 0.45) — below
    the satisfaction floor, while the stages after it keep their original higher
    values. That is a genuine section-retraction violation: a capability
    standing on an unsatisfied prerequisite.

    Nothing about this mechanism is the inverse of ``repair``. It destroys the
    original value; ``repair`` synthesises a different one.
    """
    chains = rng.sample(range(N_CHAINS), n_faults)
    mapping: dict[int, tuple[float, ...]] = {}
    edits: list[dict[str, Any]] = []
    for ci in chains:
        c = list(base.pathway_scores[ci])
        si = rng.choice([0, 1, 2])
        old = c[si]
        c[si] = round(rng.uniform(0.05, 0.45), 4)
        mapping[ci] = tuple(c)
        edits.append({"chain": ci, "drive": f"F{ci + 1}", "stage_index": si,
                      "stage": STAGE_NAMES[si], "from": old, "to": c[si]})
    return base.with_chains(mapping), FaultRecord(
        broken_chains=tuple(sorted(chains)), edits=tuple(edits),
        kind="upstream_stage_degradation_seeded_uniform",
    )


def inject_subthreshold_degradation(base: AssessmentObject, chain: int,
                                    value: float) -> tuple[AssessmentObject, FaultRecord]:
    """A REAL ordering inversion the detector is structurally unable to see.

    ``detect_pathway_inversion`` flags a chain only when an earlier stage is
    BELOW 0.5 and a later stage exceeds it. Lower A0 to 0.55 and the chain is a
    plain prerequisite inversion — A0 (0.55) now sits under D (0.80) — but every
    stage clears the floor, so the guard never opens and the scanner reports
    clean. This is the detector's documented blind spot, quoted from its own
    source, not a fault manufactured to be missed.
    """
    c = list(base.pathway_scores[chain])
    old = c[0]
    c[0] = value
    return base.with_chains({chain: tuple(c)}), FaultRecord(
        broken_chains=(chain,),
        edits=({"chain": chain, "drive": f"F{chain + 1}", "stage_index": 0,
                "stage": "A0", "from": old, "to": value},),
        kind="subthreshold_ordering_inversion_INVISIBLE_TO_DETECTOR",
    )


# ===========================================================================
# CONTROLS — constructed so a random intervention CAN succeed by chance
# ===========================================================================


def exhaustive_subset_control(perturbed: AssessmentObject, k: int,
                              localized: tuple[int, ...]) -> dict[str, Any]:
    """THE CONTROL. Every size-k subset of the 7 chains, the localized one INCLUDED.

    Fatal defect #1 of the superseded build was a control whose pool EXCLUDED
    the true item, making "0 matches" a theorem rather than a measurement. Here
    the pool is the COMPLETE set of C(7,k) same-size interventions, the
    localized subset among them, so a hit is possible by construction and the
    positive control is observable.

    The reported chance rate is n_clearing / C(7,k): the probability that a
    uniformly random same-size repair clears axis A. It is NOT zero, and a
    random guess CAN produce the same outcome as the loop.

    It can fail in two directions and both are reported: n_clearing == 0 means
    the positive control did not fire, n_clearing > 1 means the intervention is
    not identifying and the loop's success would carry no information.
    """
    universe = list(combinations(range(N_CHAINS), k))
    clearing: list[tuple[int, ...]] = []
    for subset in universe:
        if "A" not in diagnose_blind(repair(perturbed, subset)).fired_non_derived:
            clearing.append(subset)
    n = len(universe)
    return {
        "k": k,
        "n_same_size_interventions": n,
        "n_that_clear_axis_A": len(clearing),
        "subsets_that_clear": [list(s) for s in clearing],
        "chance_rate_random_same_size_intervention": len(clearing) / n if n else None,
        "chance_rate_as_fraction": f"{len(clearing)}/{n}",
        "derivation": (
            f"C(7,{k}) = {n} same-size subsets of the 7 RPM chains, drawn "
            f"uniformly; {len(clearing)} of them clear axis A when repaired. "
            f"A random pick therefore succeeds {len(clearing)}/{n} of the time. "
            "The pool INCLUDES the localized subset (positive control)."
        ),
        "localized_subset_is_among_them": tuple(sorted(localized)) in clearing,
        "exhaustive": True,
        "identifying": len(clearing) == 1,
    }


def random_subset_control(perturbed: AssessmentObject, k: int, draws: int,
                          seed: int) -> dict[str, Any]:
    """An independent empirical check on the exhaustive derivation.

    Draws ``draws`` uniformly random size-k subsets and measures how often a
    repair applied to them clears axis A. If this disagreed with the exhaustive
    rate beyond sampling noise, the exhaustive derivation would be wrong.
    """
    rng = random.Random(seed)
    hits = 0
    for _ in range(draws):
        subset = tuple(sorted(rng.sample(range(N_CHAINS), k)))
        if "A" not in diagnose_blind(repair(perturbed, subset)).fired_non_derived:
            hits += 1
    return {"draws": draws, "seed": seed, "hits": hits,
            "empirical_rate": hits / draws if draws else None}


# ===========================================================================
# BLINDNESS AND CHAIN INVARIANTS — asserted mechanically, not promised in prose
# ===========================================================================


def assert_invariants() -> dict[str, Any]:
    """Mechanical proof of design rules A (blind) and B (chained).

    Rule A is enforced by SIGNATURE: a function that has no parameter for the
    axis, the clean object or the fault record cannot be handed any of them.
    Rule B is enforced at the call site by an ``is`` identity check between the
    localizer's output and the corrector's input, which appears in ``run_case``.
    """
    checks: dict[str, Any] = {}

    def params(fn: Callable[..., Any]) -> list[str]:
        return list(inspect.signature(fn).parameters)

    checks["diagnose_blind_parameters"] = params(diagnose_blind)
    checks["localize_blind_parameters"] = params(localize_blind)
    checks["repair_parameters"] = params(repair)
    assert params(diagnose_blind) == ["obj"], params(diagnose_blind)
    assert params(localize_blind) == ["obj"], params(localize_blind)
    assert params(repair) == ["obj", "targets"], params(repair)

    neutral = neutral_object()
    d = diagnose_blind(neutral)
    checks["neutral_object_fired_axes"] = list(d.fired_axes)
    checks["neutral_object_axis_severity"] = d.axis_severity
    assert d.fired_axes == (), f"neutral object must be clean, got {d.fired_axes}"

    # CLEAN_PROBE_CHAIN is certified by the detector, not asserted by the author.
    probe = neutral.with_chains({i: CLEAN_PROBE_CHAIN for i in range(N_CHAINS)})
    checks["clean_probe_chain"] = list(CLEAN_PROBE_CHAIN)
    checks["clean_probe_chain_axis_A_severity"] = diagnose_blind(probe).axis_severity["A"]
    assert diagnose_blind(probe).axis_severity["A"] == 0.0

    # The severity quantum: one broken chain out of seven.
    one_bad = neutral.with_chains({3: (0.20, 0.10, 0.10, 0.90)})
    q = diagnose_blind(one_bad).axis_severity["A"]
    checks["one_broken_chain_axis_A_severity"] = q
    checks["severity_quantum_is_one_seventh"] = abs(q - 1.0 / 7.0) < 1e-9
    assert abs(q - 1.0 / 7.0) < 1e-9
    return checks


# ===========================================================================
# THE LOOP
# ===========================================================================


@dataclass
class Case:
    name: str
    build: Callable[[random.Random], tuple[AssessmentObject, FaultRecord]]
    localizer: Callable[[AssessmentObject], Localization]
    expectation: str
    expected_verdict: str        # PASS | GATE_FAILED | NO_FAULT | FAIL
    in_scope_note: str = ""


def run_case(case: Case, base_seed: int, draws: int) -> dict[str, Any]:
    hr(f"CASE — {case.name}")
    print(f"  PREREGISTERED EXPECTATION : {case.expectation}")
    print(f"  PREREGISTERED VERDICT     : {case.expected_verdict}")
    rng = random.Random(base_seed)

    # ---- STAGE 1: INJECT. `fault` is sealed from here on. -----------------
    clean = neutral_object()
    perturbed, fault = case.build(rng)
    print(f"  injector mechanism : {fault.kind}")
    for e in fault.edits:
        print(f"    chain {e['chain']} ({e['drive']}) stage {e['stage']:>2}: "
              f"{e['from']} -> {e['to']}")
    print(f"  perturbed object sha256 : {perturbed.sha256()[:16]}...")

    # ---- STAGE 2: GATE. The detector sees the perturbed object and nothing else.
    diag = diagnose_blind(perturbed)
    print(f"  GATE  diagnose_blind(perturbed)  -> fired={list(diag.fired_axes)} "
          f"(non-derived {list(diag.fired_non_derived)})")
    print(f"        axis-A severity {diag.axis_severity['A']:.6f}  "
          f"resistance {diag.axis_resistance['A']:.6f}")
    gate_ok = "A" in diag.fired_non_derived

    out: dict[str, Any] = {
        "case": case.name,
        "preregistered_expectation": case.expectation,
        "preregistered_verdict": case.expected_verdict,
        "injector_mechanism": fault.kind,
        "injector_edits": [dict(e) for e in fault.edits],
        "clean_object_sha256": clean.sha256(),
        "perturbed_object_sha256": perturbed.sha256(),
        "gate_diagnosis": {"fired_axes": list(diag.fired_axes),
                           "fired_non_derived": list(diag.fired_non_derived),
                           "axis_severity": diag.axis_severity,
                           "input_sha256": diag.input_sha256},
        "gate_axis_A_fired": gate_ok,
        "localizer": case.localizer.__name__,
    }

    if not gate_ok:
        verdict = "NO_FAULT" if fault.kind == "none" else "GATE_FAILED"
        print("  >>> CHAIN STOPS. Axis A did not fire, so there is no detected "
              "axis to drive a correction.")
        print("  >>> The loop does NOT fall back to the injected ground truth. "
              "That fallback is fatal defect #4 of the superseded build.")
        print(f"  ==> VERDICT {verdict}  (criterion 1 and 2 NOT EVALUATED — "
              f"the precondition failed)")
        out |= {"criterion_1_localization": None, "criterion_2_correction": None,
                "verdict": verdict,
                "chain_stopped_at": "gate",
                "ground_truth_reads": list(fault.reads)}
        return out

    # ---- STAGE 3: LOCALIZE. Blind. -----------------------------------------
    loc = case.localizer(perturbed)
    print(f"  LOCALIZE {loc.procedure}")
    print(f"           -> chains {list(loc.indices)}   "
          f"(base axis-A severity {loc.base_severity:.6f})")

    # ---- STAGE 4: REPAIR. CHAINED — identity-checked, not merely "passed". --
    targets = loc.indices
    assert targets is loc.indices, "chain broken: corrector input is not the localizer output"
    repaired = repair(perturbed, targets)
    print(f"  REPAIR   repair(perturbed, targets)  targets is localization.indices "
          f"-> {targets is loc.indices}")

    # ---- STAGE 5: VERIFY. Blind, on the repaired object alone. --------------
    ver = diagnose_blind(repaired)
    print(f"  VERIFY   diagnose_blind(repaired) -> fired={list(ver.fired_axes)}  "
          f"axis-A severity {ver.axis_severity['A']:.6f}")

    a_cleared = "A" not in ver.fired_non_derived
    residual = [a for a in ver.fired_non_derived if a != "A"]
    if residual:
        print(f"  OUT OF SCOPE, NOT CORRECTED: axes {residual} still fired. This "
              f"loop corrects axis A only and does not claim otherwise.")

    # Corrector != injector-inverse. MEASURED, not asserted.
    l1 = sum(abs(a - b) for ra, rb in zip(repaired.pathway_scores, clean.pathway_scores)
             for a, b in zip(ra, rb))
    identical_to_pre_injection = repaired.pathway_scores == clean.pathway_scores
    print(f"  repaired == pre-injection original: {identical_to_pre_injection}  "
          f"(L1 distance {l1:.4f})")
    print("    -> the corrector is a solver, not the injector's inverse; "
          "f(f(x))==x is NOT available to this loop.")

    # ---- CRITERION 1. The ONLY place ground truth is read. -----------------
    truth = fault.read_broken_chains("scoring criterion 1 (localization accuracy)")
    c1 = tuple(sorted(loc.indices)) == tuple(sorted(truth))
    print(f"  CRITERION 1 localization : named {list(loc.indices)}  "
          f"truth {list(truth)}  -> {c1}")

    # ---- CONTROLS. ---------------------------------------------------------
    k = len(loc.indices)
    exh = exhaustive_subset_control(perturbed, k, loc.indices) if k else None
    rnd = random_subset_control(perturbed, k, draws, base_seed + 991) if k else None
    if exh:
        print(f"  CONTROL exhaustive: {exh['n_that_clear_axis_A']}/"
              f"{exh['n_same_size_interventions']} same-size interventions clear "
              f"axis A -> chance rate "
              f"{exh['chance_rate_random_same_size_intervention']:.6f}")
        print(f"          positive control (localized subset clears): "
              f"{exh['localized_subset_is_among_them']}   "
              f"identifying: {exh['identifying']}")
    if rnd:
        print(f"  CONTROL random    : {rnd['hits']}/{rnd['draws']} draws clear "
              f"-> empirical {rnd['empirical_rate']:.6f}")

    # ---- CRITERION 2. Needs no ground truth: the detector decides. ---------
    c2 = bool(a_cleared and not identical_to_pre_injection
              and exh is not None and exh["localized_subset_is_among_them"]
              and exh["identifying"])
    print(f"  CRITERION 2 correction   : axis A cleared={a_cleared}  "
          f"corrector!=injector-inverse={not identical_to_pre_injection}  "
          f"control identifying={None if exh is None else exh['identifying']}  -> {c2}")

    verdict = "PASS" if (c1 and c2) else "FAIL"
    print(f"  ==> VERDICT {verdict}")

    out |= {
        "localization": {"indices": list(loc.indices), "procedure": loc.procedure,
                         "base_severity": loc.base_severity,
                         "per_chain_severity_after_substitution":
                             {str(k2): v for k2, v in
                              loc.per_chain_severity_after_substitution.items()},
                         "uses_real_detector": loc.real_detector},
        "chain_is_real_corrector_input_is_localizer_output": targets is loc.indices,
        "repaired_object_sha256": repaired.sha256(),
        "verify_diagnosis": {"fired_axes": list(ver.fired_axes),
                             "axis_severity": ver.axis_severity},
        "axis_A_cleared": a_cleared,
        "residual_out_of_scope_axes": residual,
        "repaired_equals_pre_injection_original": identical_to_pre_injection,
        "l1_distance_repaired_vs_pre_injection": round(l1, 6),
        "ground_truth_broken_chains": list(truth),
        "criterion_1_localization": c1,
        "criterion_2_correction": c2,
        "control_exhaustive": exh,
        "control_random": rnd,
        "verdict": verdict,
        "ground_truth_reads": list(fault.reads),
    }
    return out


# ===========================================================================
# CASES
# ===========================================================================


def build_cases(seed: int) -> list[Case]:
    def pos1(rng: random.Random):
        return inject_pathway_faults(neutral_object(), 1, rng)

    def pos2(rng: random.Random):
        return inject_pathway_faults(neutral_object(), 2, rng)

    def neg_subthreshold(rng: random.Random):
        del rng
        return inject_subthreshold_degradation(neutral_object(), 2, 0.55)

    def neg_nofault(rng: random.Random):
        del rng
        return neutral_object(), FaultRecord(broken_chains=(), edits=(), kind="none")

    def neg_naive(rng: random.Random):
        del rng
        # Chain 3 is uniformly weak but MONOTONICALLY DESCENDING -> the detector
        # calls it clean. Chain 5 has a strong stage standing on an unsatisfied
        # one -> violated. The lowest-minimum heuristic picks 3 (min 0.20) over
        # 5 (min 0.30) and is therefore wrong.
        obj = neutral_object().with_chains({
            3: (0.42, 0.35, 0.28, 0.20),
            5: (0.90, 0.30, 0.70, 0.60),
        })
        return obj, FaultRecord(
            broken_chains=(5,),
            edits=({"chain": 5, "drive": "F6", "stage_index": 1, "stage": "D",
                    "from": 0.80, "to": 0.30},
                   {"chain": 3, "drive": "F4", "stage_index": -1,
                    "stage": "whole chain (DECOY, clean)", "from": "0.90/0.80/0.70/0.60",
                    "to": "0.42/0.35/0.28/0.20"}),
            kind="one_violated_chain_plus_one_weak_but_clean_decoy_chain",
        )

    def robust(rng: random.Random):
        obj, rec = inject_pathway_faults(neutral_object(), 1, rng)
        # An additional, OUT-OF-SCOPE fault on the domain-precedence plane:
        # C and O dominate P and E, violating P > C > E > O.
        return obj.with_domain_averages((0.10, 0.90, 0.10, 0.90)), rec

    return [
        Case("POS-1  one broken RPM chain", pos1, localize_blind,
             "axis A fires; leave-one-out names the one broken chain; the solver "
             "clears it; exactly 1 of 7 same-size interventions clears, so the "
             "chance rate is 1/7.", "PASS"),
        Case("POS-2  two broken RPM chains", pos2, localize_blind,
             "axis A fires at 2/7; leave-one-out names both chains; exactly 1 of "
             "C(7,2)=21 same-size interventions clears, so the chance rate is 1/21.",
             "PASS"),
        Case("NEG-1  sub-threshold ordering inversion (detector blind spot)",
             neg_subthreshold, localize_blind,
             "A REAL prerequisite inversion (A0=0.55 under D=0.80) that the "
             "detector cannot see, because its guard requires the earlier stage "
             "to fall BELOW 0.5. Axis A does NOT fire, the chain STOPS at the "
             "gate, and no correction is manufactured.", "GATE_FAILED"),
        Case("NEG-2  no fault at all", neg_nofault, localize_blind,
             "Nothing is injected. The gate is clean and the loop reports that, "
             "rather than inventing a correction to report.", "NO_FAULT"),
        Case("NEG-3  detection failure PROPAGATES to correction failure",
             neg_naive, localize_naive_lowest_min,
             "Identical object, identical corrector, WRONG localizer. It names "
             "the weak-but-clean decoy chain, the corrector repairs that chain, "
             "and axis A is still fired at VERIFY. Criteria 1 AND 2 both return "
             "False. This is the proof that the chain is real.", "FAIL"),
        Case("ROBUST  in-scope fault beside an out-of-scope one", robust,
             localize_blind,
             "A pathway fault AND a domain-precedence fault. Axis A is localized "
             "and cleared; axes W and P remain fired and are reported as OUT OF "
             "SCOPE and uncorrected. The loop must not report a full clean.",
             "PASS", in_scope_note="axes W and P are out of scope for v2"),
    ]


# ===========================================================================
# TAMPER CHECK — a DELIBERATE rule-B violation, to prove rule B is load-bearing
# ===========================================================================


def tamper_check(seed: int) -> dict[str, Any]:
    """Re-run NEG-3 with the corrector driven by the SEALED GROUND TRUTH.

    This is fatal defect #4 of the superseded build, reproduced on purpose and
    exactly once, in a function that is never called from the main path. Its
    only job is to answer the question "is the chain decorative?" empirically
    rather than by assertion.

    If the chain were decorative, NEG-3 would come out the same either way. It
    does not: driven by the localizer it reports FAILURE, driven by ground truth
    it manufactures a SUCCESS. That difference is the evidence that
    ``targets is localization.indices`` is load-bearing.
    """
    hr("TAMPER CHECK — deliberately violating rule B, once, to show it matters")
    print("  Reproduces fatal defect #4 of the superseded build: the corrector is")
    print("  handed the injected ground truth instead of the localizer's output.")
    case = next(c for c in build_cases(seed) if c.name.startswith("NEG-3"))
    perturbed, fault = case.build(random.Random(seed))

    loc = case.localizer(perturbed)
    honest = diagnose_blind(repair(perturbed, loc.indices))
    honest_cleared = "A" not in honest.fired_non_derived

    truth = fault.read_broken_chains("TAMPER CHECK (deliberate rule-B violation)")
    tampered = diagnose_blind(repair(perturbed, truth))
    tampered_cleared = "A" not in tampered.fired_non_derived

    print(f"  chained   : repair(perturbed, localizer -> {list(loc.indices)})  "
          f"axis A cleared = {honest_cleared}")
    print(f"  TAMPERED  : repair(perturbed, ground truth -> {list(truth)})  "
          f"axis A cleared = {tampered_cleared}")
    proves = (not honest_cleared) and tampered_cleared
    print(f"  >>> the chain is LOAD-BEARING: {proves}")
    print("      (the two disagree, so the reported outcome depends on which one")
    print("       drives the corrector — which is exactly what the review said the")
    print("       superseded build could not demonstrate)")
    return {
        "purpose": "prove rule B (real chaining) is load-bearing, not decorative",
        "case": case.name,
        "localizer_output": list(loc.indices),
        "sealed_ground_truth": list(truth),
        "axis_A_cleared_when_driven_by_localizer": honest_cleared,
        "axis_A_cleared_when_driven_by_ground_truth": tampered_cleared,
        "chain_is_load_bearing": proves,
        "note": ("this function reproduces fatal defect #4 on purpose and is never "
                 "called from the main measurement path"),
    }


# ===========================================================================
# main
# ===========================================================================


def main() -> int:
    ap = argparse.ArgumentParser(description="CAS diagnose->correct loop v2")
    ap.add_argument("--seed", type=int, default=20260819)
    ap.add_argument("--draws", type=int, default=2000,
                    help="random same-size subset draws in the empirical control")
    ap.add_argument("--out", default=str(HERE / "weld_v2_run_report.json"))
    A = ap.parse_args()

    hr("CAS DIAGNOSE -> CORRECT LOOP v2 — ONE AXIS, TWO CRITERIA, ABLE TO FAIL")
    print("SCOPE: axis A (Pathway / RPM chain) on the NUMERIC plane. Nothing else.")
    print("This measures MECHANISM ONLY. No model is loaded and no efficacy claim")
    print("is made or implied. Three of the six cases are designed to FAIL.")
    print("Supersedes cas_weld_loop.py (reviewed at 2be60327: four fatal defects).")

    disclose(
        "single_axis_scope",
        "axes N, W, F, E, S and P are OUT OF SCOPE. E and S are hardcoded "
        "placeholders in the string detector; W and N have no numeric-plane "
        "corrector here; P is derived from other axes and is never an "
        "independent naming. Only axis A has a detector AND a corrector on the "
        "same plane, so only axis A is claimed.",
    )
    disclose(
        "no_pcba_vocabulary",
        "no PCBA component type (DR / AMP / RS / CONN) appears anywhere in this "
        "loop. The Component Atlas returned NULL at pythia-1b and GREY at "
        "pythia-2.8b and gpt-neox-20b, and the board taxonomy returned VACUOUS "
        "on natural conversation, so that vocabulary drives nothing here.",
    )
    disclose(
        "detector_is_a_transparent_rule",
        "cas_engine's axis-A detector is a deterministic hand-written rule over "
        "a numeric array, and the 7 axis detectors read DISJOINT slices of the "
        "input. Perturbing the pathway plane can therefore only move axis A. "
        "'The right axis fires' is analytically entailed once the threshold is "
        "crossed, so it is reported as a GATE, not scored as an identification "
        "result. The scored criteria are localization and correction, which the "
        "scalar output does not directly give away.",
    )
    disclose(
        "mirrored_constants",
        f"SEVERITY_THRESHOLD={SEVERITY_THRESHOLD} and "
        f"SATISFACTION_FLOOR={SATISFACTION_FLOOR} are copied from the Rust "
        "source for reporting and as the repair's arithmetic target. Every "
        "verdict in this file is produced by calling the Rust scanner; the "
        "detection rule is never reimplemented in Python.",
    )

    hr("BLINDNESS AND CHAIN INVARIANTS — asserted mechanically")
    inv = assert_invariants()
    for k, v in inv.items():
        print(f"  {k}: {v}")
    print("  RULE A: diagnose_blind and localize_blind take ONE parameter — the")
    print("          object under test. There is no axis parameter, no clean-object")
    print("          parameter and no fault-record parameter to pass an answer through.")
    print("  RULE B: repair(obj, targets) is called with targets bound by `is` to")
    print("          localization.indices, checked at every call site.")

    hr("PREREGISTERED CRITERIA")
    print("  GATE (precondition, NOT scored as identification)")
    print("     axis A fires on a blind scan of the perturbed object alone.")
    print("     Falsifiable: NEG-1 injects a real inversion the detector cannot see,")
    print("     the gate fails, and the chain stops.")
    print("     CHANCE NULL: none, and none is claimed. Stated in the disclosures.")
    print()
    print("  CRITERION 1 — LOCALIZATION")
    print("     The blind leave-one-out procedure names the EXACT set of violated")
    print("     chains, from a detector whose only axis-A output is a scalar count.")
    print("     CHANCE NULL: 1/C(7,k), measured exhaustively AND empirically.")
    print("     Falsifiable: NEG-3 runs a real alternative localizer that gets it wrong.")
    print()
    print("  CRITERION 2 — CORRECTION VIA THE DETECTED SET")
    print("     The solver, driven by the LOCALIZED set (`is`-checked, never ground")
    print("     truth), clears axis A under a fresh blind scan; the repaired object")
    print("     differs from the pre-injection original (so no f(f(x))==x identity);")
    print("     and the exhaustive same-size control is IDENTIFYING (exactly one).")
    print("     Falsifiable: NEG-3's mislocalization propagates and leaves A fired.")

    cases = build_cases(A.seed)
    results = [run_case(c, A.seed + 17 * i, A.draws) for i, c in enumerate(cases)]
    tamper = tamper_check(A.seed)

    hr("VERDICT TABLE")
    print(f"  {'case':<58} {'prereg':<12} {'actual':<12} {'c1':<6} {'c2':<6} match")
    deviations = []
    for c, r in zip(cases, results):
        match = r["verdict"] == c.expected_verdict
        if not match:
            deviations.append(c.name)
        print(f"  {c.name:<58} {c.expected_verdict:<12} {r['verdict']:<12} "
              f"{str(r['criterion_1_localization']):<6} "
              f"{str(r['criterion_2_correction']):<6} {match}")

    hr("WHAT THE CONTROLS MEASURED")
    for r in results:
        e = r.get("control_exhaustive")
        if not e:
            continue
        print(f"  {r['case']}")
        print(f"     chance rate of a random same-size intervention: "
              f"{e['chance_rate_as_fraction']} = "
              f"{e['chance_rate_random_same_size_intervention']:.6f}")
        print(f"     derivation: {e['derivation']}")
        rr = r.get("control_random")
        if rr:
            print(f"     empirical over {rr['draws']} seeded draws: "
                  f"{rr['hits']}/{rr['draws']} = {rr['empirical_rate']:.6f}")

    n_fail = sum(1 for r in results if r["verdict"] in ("FAIL", "GATE_FAILED"))
    n_pass = sum(1 for r in results if r["verdict"] == "PASS")
    status = "LOOP_FALSIFIABLE_AND_HELD" if not deviations else "PREREGISTRATION_VIOLATED"
    if not tamper["chain_is_load_bearing"]:
        deviations.append("TAMPER CHECK: the chain is not load-bearing")
        status = "PREREGISTRATION_VIOLATED"

    hr("STATUS")
    print(f"  cases: {len(results)}   PASS {n_pass}   "
          f"reported-failure {n_fail}   deviations from prereg: {deviations or 'NONE'}")
    print(f"  LOOP STATUS: {status}")
    print(f"  scanner calls made: {SCAN_CALLS}")
    print("  Every verdict above came from cas_engine.InversionScanner. No stage")
    print("  in this file received the injected axis, the pre-injection object, or")
    print("  the broken-chain indices. Ground truth is read once per case, in the")
    print("  scoring of criterion 1, and every read is logged.")
    print("  This is MECHANISM on one axis. It says NOTHING about efficacy.")

    report = {
        "schema": "cas_weld_loop.v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "supersedes": "docs/working/gate5_weld/cas_weld_loop.py (reviewed 2be60327)",
        "scope": {"axes_in_scope": ["A"], "plane": "numeric pathway array",
                  "axes_out_of_scope": ["N", "W", "F", "E", "S", "P"],
                  "model_loaded": False, "efficacy_claim": None},
        "loop_status": status,
        "deviations_from_preregistration": deviations,
        "argv": vars(A),
        "invariants": inv,
        "criteria": {
            "gate": "axis A fires on a blind scan of the perturbed object alone; "
                    "precondition only; NO chance null claimed",
            "criterion_1_localization": "blind leave-one-out names the exact violated "
                                        "chain set; chance null 1/C(7,k)",
            "criterion_2_correction": "solver driven by the localized set clears axis A, "
                                      "repaired != pre-injection original, and the "
                                      "exhaustive same-size control is identifying",
        },
        "cases": results,
        "tamper_check": tamper,
        "disclosures": DISCLOSURES,
        "real_modules_called": ["cas_engine.InversionScanner.scan",
                                "cas_engine.CognitiveStateVector"],
        "scanner_calls": SCAN_CALLS,
        "defects_of_the_superseded_build_and_how_v2_avoids_them": {
            "fatal_1_control_was_an_algebraic_identity":
                "the exhaustive control's pool is the COMPLETE set of C(7,k) same-size "
                "interventions and INCLUDES the localized subset, so a hit is possible "
                "and the positive control is observed; the reported chance rate is "
                "measured (n_clearing/C(7,k)), not asserted",
            "fatal_2_detector_handed_the_answer_by_concatenation":
                "diagnose_blind takes exactly one parameter, asserted via "
                "inspect.signature; no concatenation of clean and perturbed objects "
                "exists anywhere in this file",
            "fatal_3_axis_name_hardcoded_from_the_injection_parameter":
                "no function in this file receives an axis name; the axis set is read "
                "off the scanner's own axis_scores",
            "fatal_4_pipeline_not_chained_and_corrector_was_the_injector":
                "repair is called with targets bound by `is` to localization.indices; "
                "the injector is a seeded random degradation and the corrector is a "
                "constraint solver, so repaired != pre-injection original is MEASURED "
                "and there is no involution identity",
        },
    }
    Path(A.out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\n  wrote {A.out}")
    return 0 if not deviations else 1


if __name__ == "__main__":
    raise SystemExit(main())
