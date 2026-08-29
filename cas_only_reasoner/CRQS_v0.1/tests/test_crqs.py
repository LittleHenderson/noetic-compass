"""CRQS v0.1: the qualification standard as executable rules."""

from crqs.difficulty import AXES, difficulty_index, grade_task
from crqs.gates import gates_pass, hard_gate_violations
from crqs.generations import GENERATIONS, index_of, next_level
from crqs.qualify import (design_ceiling, demonstrated_level, qualify)
from crqs.report import format_report
from crqs.vector import compute_vector
from crqs.workflow import run_workflow
from conftest import load_manifest

CNCM = load_manifest("manifest_cncm.json")
CAS_RR = load_manifest("manifest_cas_rr.json")
KERNEL = load_manifest("manifest_kernel.json")


# --------------------------------------------------------------------------
def test_nine_axes_and_di_range():
    axes = {a: 0 for a in AXES}
    assert difficulty_index(axes) == 0
    assert difficulty_index({a: 4 for a in AXES}) == 36


def test_banding_examples():
    assert grade_task({a: 0 for a in AXES})["grade"] == "D0"
    axes = {a: 0 for a in AXES}
    axes["depth"] = 3
    assert grade_task(axes)["grade"] == "D1"


def test_hard_floor_blocks_mislabeling():
    # A recursive task cannot be graded below D6, whatever its DI.
    axes = {a: 0 for a in AXES}
    axes["recursion"] = 3
    result = grade_task(axes)
    # DI=3 alone would band to D1; the recursion floor forces D6.
    assert result["raw_grade"] == "D1"
    assert result["hard_floor"] == "D6"
    assert result["grade"] == "D6"


def test_novel_research_floor_is_d10():
    axes = {a: 0 for a in AXES}
    result = grade_task(axes, novel_research=True)
    assert result["grade"] == "D10"


def test_self_modification_floor_is_d9():
    axes = {a: 0 for a in AXES}
    result = grade_task(axes, self_modification=True)
    assert result["grade"] == "D9"


def test_generation_scale_sequence():
    levels = [g["level"] for g in GENERATIONS]
    assert "CAS-G6" in levels and "CAS-GΩ" in levels
    assert next_level("CAS-G6") == "CAS-G7"
    assert next_level("CAS-G10") == "CAS-GΩ"


# --------------------------------------------------------------------------
def test_design_ceiling_gated_by_tools():
    # Every topology flag through G10 is present (language, math,
    # long-term goals, self-model): the ceiling is the top tier.
    assert design_ceiling(CNCM) == "CAS-G10"
    # The prototype and the kernel alone still cap at G6: no tools.
    assert design_ceiling(CAS_RR) == "CAS-G6"
    assert design_ceiling(KERNEL) == "CAS-G6"


def test_demonstrated_level_strict_sequential():
    demo = demonstrated_level(KERNEL)
    assert demo["level"] == "CAS-G4"
    demo = demonstrated_level(CNCM)
    # suite walk reaches G10, but the stable difficulty is D9: the D10
    # floor claim was REFUTED and withdrawn (the D8 integration row is
    # below the stable D9 self-improvement row)
    assert demo["level"] == "CAS-G9"
    assert demo["stable_difficulty"] == "D9"
    assert demo["peak_difficulty"] is None


def test_qualified_level_is_the_minimum():
    q = qualify(CNCM)
    # POST-AUDIT HONEST LEVEL: the D10 floor claim and the E6 tier
    # were both REFUTED (2026-08-28) - the D10 rested on planted
    # discovery pairs, and same-session self-commissioned AI audits
    # are E5 supporting evidence, not independent replication. The
    # machinery through G10 exists (ceiling CAS-G10); the earned
    # level is G9 at E5.
    assert q["qualified_level"] == "CAS-G9 / E5 / A0"
    assert q["design_ceiling"] == "CAS-G10"
    q = qualify(KERNEL)
    assert q["qualified_level"] == "CAS-G4 / E4 / A0"


def test_blocking_deficiency_names_the_gate():
    # The assembled machine no longer blocks on tools; the kernel alone
    # still does.
    q = qualify(KERNEL)
    assert q["blocking"]["kind"] == "missing prerequisite machinery"
    assert "tool" in q["blocking"]["detail"]
    assert q["next_target"] == "CAS-G7"
    assert q["blocking"]["recommendations"]


def test_next_target_is_g10_with_the_true_gap_named():
    q = qualify(CNCM)
    assert not q["blocking"]
    assert q["next_target"] == "CAS-G10"
    upgrade = " ".join(q["estimated_upgrade"])
    assert "STABLE D10" in upgrade


def test_e6_requires_external_evaluators_with_claim_linkage():
    """AUDIT CLOSURE: self-commissioned same-session audits carry
    external:false and stay E5; E6 needs two records that are
    external, claim-linked, reproduced, and artifact-backed."""
    import copy
    from crqs.evidence import tier_from_manifest
    # the CNCM's own records are external:false -> E5
    assert tier_from_manifest(CNCM) == "E5"
    # a fully external pair earns E6
    strong = copy.deepcopy(CNCM)
    for record in strong["evidence"]["replications"]:
        record["external"] = True
    assert tier_from_manifest(strong) == "E6"
    # but not without claim linkage or artifact
    for missing in ("claim", "artifact"):
        weak = copy.deepcopy(strong)
        for record in weak["evidence"]["replications"]:
            record.pop(missing)
        assert tier_from_manifest(weak) == "E5"
    # whitespace evaluator refused
    blank = copy.deepcopy(strong)
    for record in blank["evidence"]["replications"]:
        record["evaluator"] = "   "
    assert tier_from_manifest(blank) == "E5"


def test_replications_disclosed_in_report_with_caveat():
    text = format_report(qualify(CNCM))
    assert "Independent replications" in text
    assert "reader judges the independence" in text
    assert "human/organizational replication OPEN" in text


# --------------------------------------------------------------------------
def test_hard_gates_block_everything():
    manifest = load_manifest("manifest_cncm.json")
    manifest["evidence"]["violations"]["authority"] = 1
    q = qualify(manifest)
    # the hard gate zeroes the GENERATION; the evidence tier
    # still reports honestly (E5 here)
    assert q["qualified_level"] == "CAS-G0 / E5 / A0"
    assert q["critical_violations"] == 1
    assert not gates_pass(manifest["evidence"])


def test_performance_gate_coverage():
    manifest = load_manifest("manifest_cncm.json")
    manifest["evidence"]["coverage"] = 0.5
    assert not gates_pass(manifest["evidence"])


def test_precision_and_coverage_pairing_present():
    manifest = load_manifest("manifest_cncm.json")
    assert manifest["evidence"]["precision"] == 1.0
    assert "coverage" in manifest["evidence"]


# --------------------------------------------------------------------------
def test_capability_vector_12_dimensions():
    vector = compute_vector(CNCM)
    assert len(vector) == 12
    assert all(0.0 <= v <= 5.0 for v in vector.values())
    q = qualify(CNCM)
    assert vector[q["strongest"]] == 5.0
    assert vector["traceability"] == 5.0
    assert vector["governance"] == 5.0
    assert q["weakest_dimensions"]


def test_skill_profile_separate():
    q = qualify(CNCM)
    assert q["skill_profile"]["Mathematics"] == 4.5
    assert q["skill_profile"]["Vision"] == 0.0
    assert q["skill_profile"]["Tool use"] == 3.0


# --------------------------------------------------------------------------
def test_report_contains_section_10_fields():
    text = format_report(qualify(CNCM))
    for field in ("Qualified level:", "Design ceiling:",
                  "Reference-model benchmark:", "Core capability vector:",
                  "Critical violations:", "Deterministic replay:",
                  "Recommended next target:", "Estimated upgrade:"):
        assert field in text
    assert "CAS-G9 / E5 / A0" in text
    assert "CAS-G10" in text  # design ceiling
    assert "Recommended next target" in text
    assert "NOT RUN" in text


def test_kernel_report_still_names_the_upgrade():
    # The kernel alone stays blocked at the G7 tool gate, so its report
    # keeps the Estimated upgrade section.
    text = format_report(qualify(KERNEL))
    assert "Estimated upgrade:" in text


def test_workflow_has_fifteen_steps():
    report, steps = run_workflow(CNCM)
    assert len(steps) == 15
    assert steps[0]["name"] == "inspect topology"
    assert steps[14]["name"] == "seal qualification report"


def test_qualification_is_deterministic():
    a = format_report(qualify(CNCM))
    b = format_report(qualify(CNCM))
    assert a == b


def test_rmb_stays_separate():
    q = qualify(CNCM)
    assert q["rmb"]["status"] == "NOT RUN"
    assert q["qualified_level"].startswith("CAS-G")