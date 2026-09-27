"""Pure-Python tests for the growth migration plan (no torch, no checkpoint, no learner). Fingerprint rows,
parameter objects and optimizer groups are TEST DOUBLES (plain Python objects and dicts in the source's own
shapes); no real checkpoint or optimizer was read to build them. Revision 0.2 adds the FORWARD-02 cases for the
four findings of PR #245 comment 5857009736 (the torch halves of those fixes are in numeric_gpu/)."""
import json
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import growth_migration_plan as gmp  # noqa: E402

PARENT_SHA = "5a8a306911bbe50b7d65e13227e8d4acfbaac871f2eb2b0ae0c0f5bb1b6e7341"
HEX = "ab" * 32


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
    assert mapping["mapping"] == "BY_VERIFIED_PARAMETER_IDENTITY_AND_EXACT_NAME"
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
    assert "CHECKED PRECONDITION" in gmp.TOLERANCES["initial_contribution_same_device_finite_inputs"]
    assert gmp.TOLERANCES["cross_device_or_hardware"].startswith("NO_CLAIM")
    assert "exactly zero while B is the zero matrix" in gmp.WHY_B_LEARNS_FIRST
    assert gmp.expected_new_parameter_count() == 624


def test_refusal_codes_are_a_closed_set():
    with pytest.raises(ValueError, match="UNKNOWN_REFUSAL_CODE:BOGUS"):
        gmp.PlanRefused("BOGUS")


# ------------------------------------------------------------------ FORWARD-02: the four findings, pure-Python halves

def test_finding1_plan_records_both_constructors_inside_the_seeded_fork():
    plan = gmp.build_plan(fingerprint_rows=double_rows(), parent_checkpoint_sha256=PARENT_SHA, parent_cursor=2940,
                          init_seed=gmp.RECORDED_INIT_SEED)
    assert plan.schema.endswith("/0.2")
    assert "A and B both constructed inside ONE" in plan.init_generator_scope
    assert "every CUDA generator are left exactly unchanged" in plan.init_generator_scope
    data = json.loads(gmp.plan_to_json(plan))
    data["init_generator_scope"] = "A only; forked CPU default generator"  # the 0.1 wording is no longer accepted
    with refused("INIT_POLICY_INVALID|PLAN_DIGEST_MISMATCH"):
        gmp.plan_from_json(json.dumps(data))


def test_finding2_binding_is_by_object_identity_and_refuses_foreign_duplicate_and_missing():
    a, b, c = object(), object(), object()  # TEST DOUBLES of parameter objects
    named = [("a.weight", a), ("b.weight", b), ("world_head.0.weight", c)]
    assert gmp.bind_group_parameters([a, b, c], named) == ("a.weight", "b.weight", "world_head.0.weight")
    assert gmp.bind_group_parameters([c, a, b], named) == ("world_head.0.weight", "a.weight", "b.weight")
    with refused("OPTIMIZER_BINDING_INVALID: foreign"):
        gmp.bind_group_parameters([a, b, object()], named)
    with refused("OPTIMIZER_BINDING_INVALID: duplicate"):
        gmp.bind_group_parameters([a, a, b, c], named)
    with refused("OPTIMIZER_BINDING_INVALID: module parameters absent"):
        gmp.bind_group_parameters([a, b], named)
    with refused("OPTIMIZER_BINDING_INVALID: one parameter object under two names"):
        gmp.bind_group_parameters([a, b, c], named + [("alias.weight", a)])


def test_finding2_mapping_indices_must_agree_with_verified_bindings_on_both_sides():
    old = ("a.weight", "world_head.0.weight")
    new = old + gmp.NEW_PARAMETER_NAMES
    mapping = gmp.optimizer_state_mapping(old, new)
    assert gmp.check_mapping_against_bindings(mapping, old, new) is True
    with refused("OPTIMIZER_BINDING_INVALID: old index"):
        gmp.check_mapping_against_bindings(mapping, ("world_head.0.weight", "a.weight"), new)
    with refused("OPTIMIZER_BINDING_INVALID: new index"):
        gmp.check_mapping_against_bindings(mapping, old, ("a.weight", "world_head.0.weight") + gmp.NEW_PARAMETER_NAMES[::-1])
    with refused("OPTIMIZER_BINDING_INVALID: the verified new group has parameters"):
        gmp.check_mapping_against_bindings(mapping, old, new + ("extra.weight",))


def test_finding2_group_settings_are_preserved_and_a_supplied_config_must_match():
    group = {"params": [object()], "lr": 0.003, "betas": (0.9, 0.999), "eps": 1e-08, "weight_decay": 0.01,
             "amsgrad": False, "maximize": False, "foreach": False, "capturable": False, "differentiable": False,
             "fused": False, "initial_lr": 0.003}  # TEST DOUBLE of the source's single AdamW group
    settings = gmp.group_settings(group)
    assert "params" not in settings and settings["initial_lr"] == 0.003 and settings["foreach"] is False
    config = {"learning_rate": 0.003, "weight_decay": 0.01, "betas": [0.9, 0.999], "eps": 1e-08}
    assert gmp.validate_optimizer_config(settings, config) is settings
    assert gmp.validate_optimizer_config(settings, None) is settings
    with refused("OPTIMIZER_CONFIG_MISMATCH: learning_rate=0.001"):
        gmp.validate_optimizer_config(settings, dict(config, learning_rate=0.001))
    with refused("OPTIMIZER_CONFIG_MISMATCH: optimizer_config lacks eps"):
        gmp.validate_optimizer_config(settings, {k: v for k, v in config.items() if k != "eps"})
    assert gmp.settings_preserved(settings, dict(group)) == sorted(settings)
    with refused("OPTIMIZER_GROUP_SETTINGS_NOT_PRESERVED: lr"):
        gmp.settings_preserved(settings, dict(group, lr=0.001))
    with refused("OPTIMIZER_GROUP_SETTINGS_NOT_PRESERVED: initial_lr"):
        gmp.settings_preserved(settings, {k: v for k, v in group.items() if k != "initial_lr"})
    with refused("OPTIMIZER_GROUPS_UNSUPPORTED"):
        gmp.group_settings({"lr": 0.003})


def _sidecar(**overrides):
    fields = dict(enabled=True, hidden=16, input_width=38, init_seed=gmp.RECORDED_INIT_SEED, plan_digest=HEX,
                  state_sha256="cd" * 32, optimizer_state_sha256="ef" * 32,
                  optimizer_parameter_names=("a.weight", "world_head.0.weight") + gmp.NEW_PARAMETER_NAMES)
    fields.update(overrides)
    return gmp.build_sidecar(**fields)


def test_finding3_sidecar_carries_enabled_seed_sizes_and_digests_and_round_trips(tmp_path):
    sidecar = _sidecar()
    assert sidecar["schema"] == gmp.SIDECAR_SCHEMA and sidecar["enabled"] is True
    assert sidecar["files"] == {"grown_state.pt": "cd" * 32, "grown_optimizer.pt": "ef" * 32}
    (tmp_path / gmp.SIDECAR_FILE).write_text(gmp.sidecar_to_json(sidecar))
    reloaded = gmp.sidecar_from_json((tmp_path / gmp.SIDECAR_FILE).read_text(), expected_plan_digest=HEX)
    assert reloaded == sidecar
    with refused("SIDECAR_MISMATCH: plan_digest"):
        gmp.sidecar_from_json(gmp.sidecar_to_json(sidecar), expected_plan_digest="00" * 32)


def test_finding3_tampered_or_malformed_sidecar_is_refused():
    sidecar = _sidecar()
    data = json.loads(gmp.sidecar_to_json(sidecar))
    data["enabled"] = False  # flipping enabled without re-signing is caught by the digest
    with refused("SIDECAR_MISMATCH: sidecar_digest"):
        gmp.sidecar_from_json(json.dumps(data))
    data = json.loads(gmp.sidecar_to_json(sidecar))
    data["schema"] = "something/else"
    with refused("SIDECAR_SCHEMA_INVALID"):
        gmp.sidecar_from_json(json.dumps(data))
    with refused("SIDECAR_SCHEMA_INVALID: enabled must be a bool"):
        _sidecar(enabled=1)
    with refused("SIDECAR_SCHEMA_INVALID: state_sha256 must be 64"):
        _sidecar(state_sha256="deadbeef")
    with refused("SIDECAR_SCHEMA_INVALID: optimizer_parameter_names"):
        _sidecar(optimizer_parameter_names=("a.weight", "a.weight"))
    with refused("INIT_SEED_MISSING"):
        _sidecar(init_seed=None)


def test_finding4_tolerances_state_the_intermediate_precondition_and_gradient_counterexamples():
    t = gmp.TOLERANCES
    assert t["nonfinite_intermediates"].startswith("REFUSED_BEFORE_B (SPECIALIST_NONFINITE_INTERMEDIATE)")
    assert "finfo(float32).max" in t["nonfinite_intermediates"] and "0.0 x inf = nan" in t["nonfinite_intermediates"]
    assert "Finite x alone does NOT imply finite h" in t["initial_contribution_same_device_finite_inputs"]
    assert "x = 0 gives GELU(0) = 0 and dL/dB = 0" in t["trainability_probe"]
    assert "zero upstream gradient gives dL/dB = 0" in t["trainability_probe"]
    assert "sum loss (dL/dy = 1)" in t["trainability_probe"]
    assert "x = 0 and a zero upstream gradient are counterexamples" in gmp.WHY_B_LEARNS_FIRST
    assert "nonzero whenever A is nonzero" not in gmp.WHY_B_LEARNS_FIRST  # the 0.1 over-broad wording is gone
    for code in ("SPECIALIST_NONFINITE_INTERMEDIATE", "OPTIMIZER_BINDING_INVALID", "OPTIMIZER_CONFIG_MISMATCH",
                 "OPTIMIZER_STATE_INCOMPATIBLE", "OPTIMIZER_GROUP_SETTINGS_NOT_PRESERVED", "SIDECAR_MISSING",
                 "SIDECAR_MISMATCH", "SIDECAR_SCHEMA_INVALID", "SPECIALIST_NOT_ATTACHED"):
        assert code in gmp.REFUSALS


def test_file_sha256_matches_hashlib(tmp_path):
    import hashlib
    path = tmp_path / "blob.bin"
    path.write_bytes(b"\x00\x01" * 3000)
    assert gmp.file_sha256(path) == hashlib.sha256(b"\x00\x01" * 3000).hexdigest()
