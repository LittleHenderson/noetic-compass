"""Pure-Python tests for the growth migration plan (no torch, no checkpoint, no learner). Fingerprint rows are
TEST DOUBLES in the source's own ``name:dtype:shape`` format; no real checkpoint was read to build them."""
import json
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import growth_migration_plan as gmp  # noqa: E402

PARENT_SHA = "5a8a306911bbe50b7d65e13227e8d4acfbaac871f2eb2b0ae0c0f5bb1b6e7341"


def double_rows():
    """A test double of a parent fingerprint: the world head as in the source plus a few other heads."""
    return [
        "world_head.0.weight:torch.float32:(64, 38)", "world_head.2.bias:torch.float32:(64,)",
        "world_head.2.weight:torch.float32:(64,)", "world_head.3.bias:torch.float32:(1,)",
        "world_head.3.weight:torch.float32:(1, 64)", "world_projection.weight:torch.float32:(64, 196)",
        "role_head.0.weight:torch.float32:(64, 256)", "round_mix:torch.float32:(8,)",
    ]


def refused(code):
    return pytest.raises(gmp.PlanRefused, match="^" + code)


def test_source_constants_match_the_exact_learner():
    assert gmp.WIDTH == 64 and gmp.DECL_VECTOR_WIDTH == 32 and gmp.WORLD_CANDIDATE_WIDTH == 38
    assert gmp.WORLD_HEAD_SOURCE_LINES == (856, 858) and gmp.OPTIMIZER_SOURCE_LINE == 1840
    assert gmp.LEARNER_SOURCE_FILE_SHA256.startswith("0f424d86")


def test_plan_builds_validates_and_counts():
    plan = gmp.build_plan(fingerprint_rows=double_rows(), parent_checkpoint_sha256=PARENT_SHA, parent_cursor=2940,
                          init_seed=20260927)
    summary = gmp.validate_plan(plan)
    assert summary["original_parameters"] == 8 and summary["new_parameters"] == 2
    assert summary["new_scalar_count"] == 16 * 38 + 16 == 624
    assert plan.new_shapes == {"world_specialist.A.weight": [16, 38], "world_specialist.B.weight": [1, 16]}
    assert plan.learnable_names_after == tuple(sorted(plan.original_names + gmp.NEW_PARAMETER_NAMES))
    assert plan.init_policy["world_specialist.A.weight"] != "ZERO" and plan.init_policy["world_specialist.B.weight"] == "ZERO"


def test_plan_json_round_trip_is_consistent(tmp_path):
    plan = gmp.build_plan(fingerprint_rows=double_rows(), parent_checkpoint_sha256=PARENT_SHA, parent_cursor=2940,
                          init_seed=20260927)
    text = gmp.plan_to_json(plan)
    (tmp_path / "plan.json").write_text(text)
    reloaded = gmp.plan_from_json((tmp_path / "plan.json").read_text())
    assert reloaded == plan and reloaded.plan_digest == plan.plan_digest


def test_tampered_plan_json_is_refused(tmp_path):
    plan = gmp.build_plan(fingerprint_rows=double_rows(), parent_checkpoint_sha256=PARENT_SHA, parent_cursor=2940,
                          init_seed=20260927)
    data = json.loads(gmp.plan_to_json(plan))
    data["hidden"] = 32
    with refused("NEW_SHAPES_INVALID|PLAN_DIGEST_MISMATCH|COUNT_MISMATCH"):
        gmp.plan_from_json(json.dumps(data))


@pytest.mark.parametrize("kwargs,code", [
    ({"hidden": 0}, "HIDDEN_SIZE_INVALID"), ({"hidden": 512}, "HIDDEN_SIZE_INVALID"),
    ({"input_width": 40}, "INPUT_WIDTH_INVALID"), ({"init_seed": None}, "INIT_SEED_MISSING"),
])
def test_bad_sizes_and_missing_seed_are_refused(kwargs, code):
    base = dict(fingerprint_rows=double_rows(), parent_checkpoint_sha256=PARENT_SHA, parent_cursor=2940, init_seed=1)
    base.update(kwargs)
    with refused(code):
        gmp.build_plan(**base)


def test_parent_without_world_head_is_refused():
    rows = [r for r in double_rows() if not r.startswith("world_head.0.weight")]
    with refused("WORLD_HEAD_NOT_FOUND"):
        gmp.build_plan(fingerprint_rows=rows, parent_checkpoint_sha256=PARENT_SHA, parent_cursor=2940, init_seed=1)


def test_name_collision_and_bad_rows_are_refused():
    with refused("NAME_COLLISION"):
        gmp.build_plan(fingerprint_rows=double_rows() + ["world_specialist.A.weight:torch.float32:(16, 38)"],
                       parent_checkpoint_sha256=PARENT_SHA, parent_cursor=2940, init_seed=1)
    with refused("FINGERPRINT_ROW_INVALID"):
        gmp.parse_fingerprint_rows(["no-colon-row"])
    with refused("FINGERPRINT_ROW_INVALID"):
        gmp.parse_fingerprint_rows(double_rows() + [double_rows()[0]])


def test_both_zero_initialization_is_refused():
    plan = gmp.build_plan(fingerprint_rows=double_rows(), parent_checkpoint_sha256=PARENT_SHA, parent_cursor=2940,
                          init_seed=1)
    data = json.loads(gmp.plan_to_json(plan))
    data["init_policy"]["world_specialist.A.weight"] = "ZERO"
    with refused("INIT_POLICY_INVALID|PLAN_DIGEST_MISMATCH"):
        gmp.plan_from_json(json.dumps(data))


def test_optimizer_state_mapping_is_by_name_and_refuses_reordering():
    old = ["a.weight", "b.weight", "world_head.0.weight"]
    new = old + list(gmp.NEW_PARAMETER_NAMES)
    mapping = gmp.optimizer_state_mapping(old, new)
    assert mapping["mapping"] == "BY_EXACT_NAME"
    assert mapping["preserved"]["b.weight"] == {"old_index": 1, "new_index": 1}
    assert set(mapping["new"]) == set(gmp.NEW_PARAMETER_NAMES)
    assert mapping["new"]["world_specialist.B.weight"]["parameter_init"] == "ZERO"
    assert mapping["new"]["world_specialist.A.weight"]["state_init"]["step"] == "zero scalar tensor"
    with refused("PARAMETER_ORDER_CHANGED"):
        gmp.optimizer_state_mapping(old, ["b.weight", "a.weight", "world_head.0.weight"] + list(gmp.NEW_PARAMETER_NAMES))
    with refused("ORIGINAL_NAME_MISSING"):
        gmp.optimizer_state_mapping(old, ["a.weight", "world_head.0.weight"] + list(gmp.NEW_PARAMETER_NAMES))
    with refused("NEW_NAMES_INVALID"):
        gmp.optimizer_state_mapping(old, old + ["world_specialist.C.weight"])


def test_tolerances_and_learning_order_are_stated_before_any_result():
    assert "EXACT" in gmp.TOLERANCES["initial_contribution_same_device_finite_inputs"]
    assert gmp.TOLERANCES["cross_device_or_hardware"].startswith("NO_CLAIM")
    assert "exactly zero while B is the zero matrix" in gmp.WHY_B_LEARNS_FIRST
    assert gmp.expected_new_parameter_count() == 624


def test_refusal_codes_are_a_closed_set():
    with pytest.raises(ValueError, match="UNKNOWN_REFUSAL_CODE:BOGUS"):
        gmp.PlanRefused("BOGUS")
