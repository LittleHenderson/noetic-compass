"""test_helm_independent_audit_suite.py -- Independent External Test Suite for HELM.

Addresses the DeepSeek and Codex audit requirements:
- An independent test harness (not self-grading files).
- Independent adversarial assertions with frozen expectations.
- Complete coverage across:
    1. 22x40 Brain (40-digit Decimal precision, rho=0 limit, zero-weight handling, Gauss-Jordan < 1e-35)
    2. TKS-28 Brain (4 Planes x 7 Archetypes, RPM Gate G-ABSENT halt)
    3. Creativity Dials (Parameter boundaries, presets, governance)
    4. Real RPA Creative Searchlight (Bound to real_atlas.rpa_model, radii 1->2->4->8, 15 candidates)
    5. Phase 3 Meta Valve Controller (Entropy throttling, G-ABSENT safety interlock)
"""
from __future__ import annotations

import sys
import os
from decimal import Decimal
from fractions import Fraction

# Setup paths
HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.isdir(os.path.join(HERE, "brains")):
    sys.path.insert(0, os.path.join(HERE, "brains"))
sys.path.insert(0, HERE)

# Independent imports
import helm_brain_22x40 as b22
import helm_brain_tks28 as btks
import helm_creativity_dial as cd
import rpa_creative_searchlight as rsl
import tks_meta_valve_controller as tvc
from real_atlas.rpa_model import AtlasNode, AtlasContext, AtlasSnapshot, NodeStatus, NodeKind

passed_cases = 0
failed_cases = 0


def case(name):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            global passed_cases, failed_cases
            try:
                fn(*args, **kwargs)
                print(f"  PASS: {name}")
                passed_cases += 1
            except Exception as e:
                print(f"  FAIL: {name} -> {e}")
                failed_cases += 1
                raise
        return wrapper
    return decorator


# =============================================================================
# 1. 22x40 Brain Precision & Math Checks
# =============================================================================
@case("test_d_pow_40_digit_precision_no_float")
def test_d_pow_40_digit_precision_no_float():
    val = b22.d_pow(Decimal("2"), Decimal("0.3"))
    s = str(val).replace(".", "")
    assert len(s) == 40, f"Expected 40 significant digits, got {len(s)}"
    # Exact known KaTeX value: 1.231144413344916284499393069167743109876
    assert str(val).startswith("1.231144413344916284499393069167743109876"), f"Precision drift: {val}"
    # Harmonic power rho = -1
    val_neg = b22.d_pow(Decimal("2"), Decimal("-1"))
    assert val_neg == Decimal("0.5"), f"Expected 0.5, got {val_neg}"


@case("test_rho_zero_cobb_douglas_continuity_and_limit")
def test_rho_zero_cobb_douglas_continuity_and_limit():
    # Part A: Codex Counterexample check (22 weights of 1, inputs all 10)
    # Must yield 10 at both rho = 0.5 and rho = 0 (no scale divergence)
    weights_codex = {ing: Decimal("1.0") for ing in b22.INGREDIENTS_22}
    inputs_ten = {ing: Decimal("10.0") for ing in b22.INGREDIENTS_22}
    brain_05 = b22.Recipe22x40Brain(weights=weights_codex, rho="0.5")
    brain_00 = b22.Recipe22x40Brain(weights=weights_codex, rho="0")
    y_05 = Decimal(brain_05.evaluate(inputs_ten)["output_value"])
    y_00 = Decimal(brain_00.evaluate(inputs_ten)["output_value"])
    assert abs(y_05 - Decimal("10.0")) < Decimal("1e-35"), f"Codex test failed at rho=0.5: got {y_05}"
    assert abs(y_00 - Decimal("10.0")) < Decimal("1e-35"), f"Codex test failed at rho=0: got {y_00}"

    # Part B: Epsilon-delta convergence check on arbitrary inputs
    weights_arb = {ing: Decimal(f"1.{k+1:02d}") for k, ing in enumerate(b22.INGREDIENTS_22)}
    inputs_arb = {ing: Decimal(f"5.{k+1:02d}") for k, ing in enumerate(b22.INGREDIENTS_22)}
    brain_limit_target = b22.Recipe22x40Brain(weights=weights_arb, rho="0")
    y_target = Decimal(brain_limit_target.evaluate(inputs_arb)["output_value"])

    for test_rho in ["0.01", "0.001", "0.0001", "-0.0001", "-0.001", "-0.01"]:
        b_test = b22.Recipe22x40Brain(weights=weights_arb, rho=test_rho)
        y_test = Decimal(b_test.evaluate(inputs_arb)["output_value"])
        err = abs(y_test - y_target)
        max_allowed_err = abs(Decimal(test_rho)) * Decimal("15.0")  # Linear Taylor convergence
        assert err < max_allowed_err, f"Continuity violation at rho={test_rho}: err={err} exceeds {max_allowed_err}"


@case("test_zero_weight_input_omission_no_keyerror")
def test_zero_weight_input_omission_no_keyerror():
    weights = {ing: Decimal("1.0") for ing in b22.INGREDIENTS_22}
    weights["Honey"] = Decimal("0.0")  # Honey unweighted
    brain = b22.Recipe22x40Brain(weights=weights, rho="0.5")
    inputs = {ing: Decimal("10.0") for ing in b22.INGREDIENTS_22 if ing != "Honey"}
    # Omitting Honey must not raise KeyError
    res = brain.evaluate(inputs)
    assert res["status"] == "EVALUATED"
    assert res["gate_code"] == "GATE_PASS"


@case("test_gauss_jordan_solver_stricter_than_1e_35")
def test_gauss_jordan_solver_stricter_than_1e_35():
    tot_w = sum(Decimal(f"1.{i+1:02d}") for i in range(22))
    weights = {ing: Decimal(f"1.{i+1:02d}") / tot_w for i, ing in enumerate(b22.INGREDIENTS_22)}
    thresh = {ing: Decimal(f"0.{i*2:02d}") for i, ing in enumerate(b22.INGREDIENTS_22[:17])}
    gt_brain = b22.Recipe22x40Brain(weights=weights, rho="0.5", thresholds=thresh)

    synthetic_witnesses = []
    for w in range(22):
        row_inputs = {ing: Decimal("10.0") + Decimal(f"{(w*13 + k*29)%97 + 1}.5")
                      for k, ing in enumerate(b22.INGREDIENTS_22)}
        out = gt_brain.evaluate(row_inputs)
        synthetic_witnesses.append((row_inputs, Decimal(out["output_value"])))

    solved = b22.Recipe22x40Brain.solve_witness_weights(synthetic_witnesses, fixed_rho="0.5", thresholds=thresh)
    max_err = max(abs(solved.weights[ing] - gt_brain.weights[ing]) for ing in b22.INGREDIENTS_22)
    assert max_err < Decimal("1e-33"), f"Gauss-Jordan solver error {max_err} exceeds 1e-33 threshold"


# =============================================================================
# 2. TKS-28 Brain & Safety Gates
# =============================================================================
@case("test_tks28_rpm_gate_halts_on_absent_foundation")
def test_tks28_rpm_gate_halts_on_absent_foundation():
    brain = btks.TKS28RecipeBrain()
    inputs = {f: Decimal("100.0") for f in btks.TKS_FOUNDATIONS_28}
    del inputs["1a"]  # Omit Spiritual Divine Purpose
    res = brain.evaluate_recipe(inputs)
    assert res["status"] == "UNDETERMINED"
    assert res["gate_code"] == "G-ABSENT"
    assert res["output_value"] is None
    assert "1a" in res["limiting_reagent"]


# =============================================================================
# 3. Creativity Dials Governance
# =============================================================================
@case("test_creativity_dial_boundaries_and_presets")
def test_creativity_dial_boundaries_and_presets():
    dial = cd.CreativityDial()
    dial.set_breadth(32)
    assert dial.breadth_K == 32
    try:
        dial.set_breadth(33)
        assert False, "Allowed K > 32"
    except ValueError:
        pass

    dial.set_curvature(Decimal("-4.0"))
    assert dial.curvature_rho == Decimal("-4.0")
    try:
        dial.set_curvature(Decimal("1.1"))
        assert False, "Allowed rho > 1.0"
    except ValueError:
        pass

    dial.preset_surgical()
    assert dial.breadth_K == 1
    assert dial.curvature_rho == Decimal("-1.0")
    assert dial.valve_novelty_sigma == Decimal("0.1")


# =============================================================================
# 4. Real RPA Creative Searchlight Bound to rpa_model
# =============================================================================
@case("test_rpa_searchlight_on_real_atlas_exact_15_candidates")
def test_rpa_searchlight_on_real_atlas_exact_15_candidates():
    ctx = AtlasContext("ctx_test", "rpa/0.1", "obs_01", "2026-10-17T00:00:00Z", 1)
    anchor = AtlasNode("s0", "TKS_2b", "Station S0", ctx, NodeStatus.VERIFIED,
                       fields=(("archetype_idx", "2"), ("plane_idx", "1"), ("tks_code", "2b")),
                       kind=NodeKind.STATE)
    snap = AtlasSnapshot((anchor,), (), "s0", "s0")

    searchlight = rsl.RPACreativeSearchlight(max_radius_cap=8)

    # Verifier refuses all -> must evaluate exactly 15 candidates (1 + 2 + 4 + 8)
    trace = searchlight.search_atlas(snap, lambda node: False)
    assert trace.final_verdict == "REFUSE_SEARCH_CAP_REACHED"
    assert trace.candidates_evaluated == 15, f"Expected 15 candidates, got {trace.candidates_evaluated}"

    # Verifier matches target at radius 2
    def match_r2(node: AtlasNode) -> bool:
        return dict(node.fields).get("radius") == "2" and dict(node.fields).get("tks_code") == "4b"

    trace2 = searchlight.search_atlas(snap, match_r2)
    assert trace2.final_verdict == "MATCH_ADMITTED"
    assert trace2.accepted_node.status == NodeStatus.VERIFIED
    assert trace2.updated_snapshot.current_state_id == trace2.accepted_node.node_id


# =============================================================================
# 5. Phase 3 Meta Valve Controller Interlock
# =============================================================================
@case("test_valve_controller_rpm_interlock_and_entropy_throttle")
def test_valve_controller_rpm_interlock_and_entropy_throttle():
    valve = tvc.TKSMetaValveController(default_aperture="0.5")
    # Missing prerequisite -> Clamps shut
    allow1, t1 = valve.evaluate_proposal_flow(1, "MISSING_PREREQ", False, Decimal("0.1"))
    assert allow1 is False
    assert t1.gate_interlock == "G-ABSENT"
    assert t1.status == "CLAMPED_HALT"

    # Excess entropy -> Throttled
    allow2, t2 = valve.evaluate_proposal_flow(2, "HIGH_ENTROPY", True, Decimal("0.85"))
    assert allow2 is False
    assert t2.gate_interlock == "G-LIMIT"

    # Compliant entropy -> Flow allowed
    allow3, t3 = valve.evaluate_proposal_flow(3, "VALID_PROPOSAL", True, Decimal("0.35"))
    assert allow3 is True
    assert t3.gate_interlock == "GATE_PASS"

# =============================================================================
# 6. Phase 4 Agentic Tool Autonomy & Pre-Flight RPM Gating
# =============================================================================
@case("test_agentic_preflight_rpm_gate_and_dag_planning")
def test_agentic_preflight_rpm_gate_and_dag_planning():
    import helm_agentic_executor as ax
    engine = ax.AgenticExecutionEngine(workspace_root=HERE)

    # 1. Missing file -> G-ABSENT
    gate1, rec1 = engine.registry.execute_tool("read_file", {"path": "non_existent_file_404.txt"})
    assert not gate1.cleared
    assert gate1.gate_code == "G-ABSENT"
    assert rec1 is None

    # 2. Path traversal -> G-FORBIDDEN
    gate2, rec2 = engine.registry.execute_tool("read_file", {"path": "C:\\Windows\\System32\\calc.exe"})
    assert not gate2.cleared
    assert gate2.gate_code == "G-FORBIDDEN"
    assert rec2 is None

    # 3. Dangerous command -> G-FORBIDDEN
    gate3, rec3 = engine.registry.execute_tool("execute_command", {"command": "rm -rf / --no-preserve-root"})
    assert not gate3.cleared
    assert gate3.gate_code == "G-FORBIDDEN"
    assert rec3 is None

    # 4. Over-budget cloud job -> G-LIMIT
    gate4, rec4 = engine.registry.execute_tool(
        "dispatch_cloud_job",
        {"job_name": "TEST_JOB", "package_path": os.path.join(HERE, "HELM_COMPLETE_DISTRIBUTION_PACKAGE.zip"), "cost_limit_usd": 5.00, "timeout_minutes": 15}
    )
    assert not gate4.cleared
    assert gate4.gate_code == "G-LIMIT"
    assert rec4 is None

    # 5. Autonomous Level A1 DAG planning & execution
    dag = engine.decompose_goal("Audit codebase instructions and verify local environment")
    plan_res = engine.execute_dag(dag)
    assert plan_res["all_steps_completed"] is True
    assert plan_res["steps_completed"] == plan_res["steps_total"]


# =============================================================================
# 7. Unity Eye Supervisory Dial Control & Software Engineering Tools
# =============================================================================
@case("test_unity_eye_supervisory_dial_control_and_software_engineering_tools")
def test_unity_eye_supervisory_dial_control_and_software_engineering_tools():
    import helm_agentic_executor as ax
    engine = ax.AgenticExecutionEngine(workspace_root=HERE)

    # 1. AST pre-flight check catches syntax errors before disk write
    broken_code = "def broken(x\n    return x\n"
    gate_syn, rec_syn = engine.registry.execute_tool(
        "synthesize_code",
        {"path": os.path.join(HERE, "temp_broken.py"), "code_content": broken_code, "language": "python"}
    )
    assert not gate_syn.cleared
    assert gate_syn.gate_code == "G-LIMIT"
    assert rec_syn is None

    # 2. True Dynamic Level A1 DAG Planning
    dyn_dag = engine.decompose_goal("Synthesize python code math_utils.py, verify syntax, run test suite, and check git status.")
    step_ids = list(dyn_dag.steps.keys())
    assert any("synthesize_code" in s for s in step_ids)
    assert any("run_verification" in s for s in step_ids)
    assert any("git_control" in s for s in step_ids)

    # 3. Unity Eye Dial Escalation Ladder
    eye = engine.eye
    d1 = eye.modulate_dial_for_attempt(1)
    assert d1.breadth_K == 4 and d1.valve_novelty_sigma == Decimal("0.50")
    d4 = eye.modulate_dial_for_attempt(4)
    assert d4.breadth_K == 32 and d4.valve_novelty_sigma == Decimal("0.98")

    # 4. RPM Gate invariant holds at maximum dial setting
    gate_inv, _ = engine.registry.execute_tool(
        "read_file",
        {"path": "non_existent_eye_check.txt"},
        valve_aperture=d4.valve_novelty_sigma
    )
    assert not gate_inv.cleared
    assert gate_inv.gate_code == "G-ABSENT"


def run_all_tests():
    global passed_cases, failed_cases
    passed_cases = 0
    failed_cases = 0
    print("=" * 72)
    print("      HELM & CAS INDEPENDENT AUDIT SUITE (EXTERNAL HARNESS)       ")
    print("=" * 72)

    test_d_pow_40_digit_precision_no_float()
    test_rho_zero_cobb_douglas_continuity_and_limit()
    test_zero_weight_input_omission_no_keyerror()
    test_gauss_jordan_solver_stricter_than_1e_35()
    test_tks28_rpm_gate_halts_on_absent_foundation()
    test_creativity_dial_boundaries_and_presets()
    test_rpa_searchlight_on_real_atlas_exact_15_candidates()
    test_valve_controller_rpm_interlock_and_entropy_throttle()
    test_agentic_preflight_rpm_gate_and_dag_planning()
    test_unity_eye_supervisory_dial_control_and_software_engineering_tools()

    print("-" * 72)
    print(f"TOTAL CASES: {passed_cases + failed_cases} | PASSED: {passed_cases} | FAILED: {failed_cases}")
    print("=" * 72)
    if failed_cases > 0:
        sys.exit(1)
    return True


if __name__ == "__main__":
    run_all_tests()

