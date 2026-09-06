"""Cross-component source registration checks; no models or dataset generation.

AST inspection checks declarations, not runtime behavior. GPU test bodies remain
unexecuted here. Runtime, checkpoints, held-out outcomes and cleanup need AWS.
"""
import ast
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
FROZEN = {
    "cas_meta2/train_v2.py": "882976ac24fb808c2da8ab5e1a5f80388946693077e7dfdfd7a00d4e029c0665",
    "aws/launch_plan.json": "65bc41bf4bffe7a373dd9e8c9faa75561fd2d8940d32fd6d4283dbbb55f6f1f6",
    "cas_meta2/codec.py": "c6ca7f489f91e4b43225b7ffc4d496490f038c18842266b6d5da05570ca29030",
    "tools/build_launch_bundle.py": "48024414c5a8533ffff3a9d639e0d04d925ce0b1bff14bde5ece8cd904e04563",
    "cas_meta2/curriculum_v2.py": "a62e7acb23024a6f195e33af57a3a19cb513b5e7181a9a00370332ee37f1c5bd",
    "cas_meta2/ir.py": "02f3ce65ef9c3b54901a38abab2d4f9f272268e7c195f7001fb119bf1d384637",
    "tools/audit_stored_packet_v2.py": "4e519862283271e476fd1c543457542ecd3caae2bd805765713a954a4011ed22",
    "tools/experiment_profiles.py": "53008bfcf10dc10b53f531264cd0e1c6b283a30190a24787d0e2e6720c4c9dc5",
    "aws/budget.py": "77a845ea8669b775a28a940552a9212f667a9506e5586deff64baba06a82eda0",
    "cas_meta2/curriculum.py": "c89a03e2f0c381ec4e9c2f8750fd5f5bf6d4b7836ca790d02e256c1cc334e384",
    "cas_meta2/features_v2.py": "79dd26ad6183cde7e586dda2cd1b65d812e601e793d5c60e0658ad886c09b4dc",
    "cas_meta2/gpu_preflight_v2.py": "afe77f0ff9b5fa57952de6d0740c6a1ce9cec80da57973ecccb2713c9b3444d0",
    "aws/launch.py": "58fb3df85d8a5ed2137b0cea360fa7711bd609e9559b373dbf1296083caf2c5a",
    "cas_meta2/executor.py": "edeb83fd3468aaccacb871bc4561c97a78ae087bb47b9d8ad38f1a58fd7efb2a",
    "cas_meta2/native.py": "16131d98dcbd76d274a1c083e9bc5f100cadfbbba7dfcdb38282c23946c20512",
    "cas_meta2/campaign_v2.py": "e636e112578aeb30065784ed44992b23c50266f9239be680870c4a2bc6684c09",
    "tools/inspect_cloud_packet_v2.py": "262e213eaf8ee392f1c75730357500c5e93f358d1243ad2421ea4f8b6f06b7b2",
}


def read_spec():
    return json.loads((ROOT / "EXPERIMENT_V3.json").read_bytes())


def tree(relative):
    return ast.parse((ROOT / relative).read_text(encoding="utf-8"), filename=relative)


def assignment(relative, name):
    for node in tree(relative).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("Missing literal assignment: " + relative + ":" + name)


def class_fields(relative, name):
    cls = next(node for node in tree(relative).body if isinstance(node, ast.ClassDef) and node.name == name)
    return {node.target.id: node.value for node in cls.body if isinstance(node, ast.AnnAssign)}


@pytest.mark.parametrize("relative,expected", sorted(FROZEN.items()))
def test_frozen_execution_and_old_evidence_paths_are_not_rewritten(relative, expected):
    assert len(expected) == 64
    assert sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_training_registration_matches_actual_dataclass_without_importing_torch():
    fields = class_fields("cas_meta2/train_v3.py", "TrainingConfig")
    spec = read_spec()["training"]
    assert set(fields) == set(spec)
    for name, node in fields.items():
        if name != "policy":
            value = ast.literal_eval(node)
            assert type(value) is type(spec[name]) and value == spec[name], name
    policy = {name: ast.literal_eval(node) for name, node in class_fields("cas_meta2/policy.py", "PolicyConfig").items()}
    factory = fields["policy"]
    assert isinstance(factory, ast.Call) and isinstance(factory.func, ast.Name) and factory.func.id == "field"
    deferred = next(item.value for item in factory.keywords if item.arg == "default_factory")
    assert isinstance(deferred, ast.Lambda) and isinstance(deferred.body, ast.Call)
    assert isinstance(deferred.body.func, ast.Name) and deferred.body.func.id == "PolicyConfig"
    policy.update({item.arg: ast.literal_eval(item.value) for item in deferred.body.keywords})
    assert policy == spec["policy"]
    assert all(type(policy[key]) is type(value) for key, value in spec["policy"].items())
    assert policy == assignment("cas_meta2/gpu_preflight_copy_v3.py", "REGISTERED_POLICY")


def test_data_counts_depths_and_steps_align_across_registration():
    spec = read_spec()
    curriculum, training = spec["curriculum"], spec["training"]
    assert curriculum["seed"] == training["curriculum_seed"] == assignment("cas_meta2/curriculum_v3.py", "DEFAULT_SEED") == 20260919
    assert curriculum["counts"] == assignment("cas_meta2/curriculum_v3.py", "DEFAULT_COUNTS") == {"train": 3072, "validation": 96, "test": 72}
    assert curriculum["training_depth_counts"] == {str(d): training["training_examples_per_depth"] for d in (1, 2, 3)}
    assert curriculum["validation_depth_counts"] == spec["selection"]["fixed_depth_denominators"] == {str(d): training["validation_examples_per_depth"] for d in (1, 2, 3)}
    assert curriculum["test_groups"] == {name: training["test_triplets"] for name in ("same_depth", "wording_shift", "deeper_calls")}
    assert assignment("cas_meta2/gpu_preflight_copy_v3.py", "REGISTERED_TRAINING_ROWS") == 3072
    assert assignment("cas_meta2/gpu_preflight_copy_v3.py", "REGISTERED_BATCH_SIZE") == training["batch_size"] == 16
    assert curriculum["counts"]["train"] // training["batch_size"] == 192
    assert training["epochs"] * 192 == 11520
    assert len(spec["evaluation"]["arms"]) * curriculum["counts"]["test"] == 360


def test_exact_exclusion_assets_are_portable_and_no_targets_are_generated():
    spec = read_spec()["curriculum"]["exclusions"]
    base_raw = (ROOT / "cas_meta2/exclusions_v3.json").read_bytes()
    development_raw = (ROOT / "cas_meta2/development_exclusions_v3.json").read_bytes()
    assert sha256(base_raw).hexdigest() == spec["base_asset_sha256"] == assignment("cas_meta2/curriculum_v3.py", "EXCLUSION_ASSET_SHA256")
    assert sha256(development_raw).hexdigest() == spec["development_asset_sha256"] == assignment("cas_meta2/curriculum_v3.py", "DEVELOPMENT_EXCLUSION_ASSET_SHA256")
    base, development = json.loads(base_raw), json.loads(development_raw)
    graphs = set().union(*(set(origin["graph_signatures"]) for origin in base["origins"].values()))
    extra = set(development["graph_signatures"])
    assert len(graphs) == spec["base_count"] == 4312
    assert len(extra) == spec["development_count"] == 177
    assert len(graphs & extra) == spec["overlap_count"] == 1
    assert len(graphs | extra) == spec["combined_count"] == 4488


def test_fixed_loss_values_match_specification():
    spec = read_spec()["loss"]
    assert assignment("cas_meta2/selection_v3.py", "SEMANTIC_LOSS_WEIGHT") == spec["semantic_weight"] == 3
    assert assignment("cas_meta2/selection_v3.py", "STRUCTURAL_LOSS_WEIGHT") == spec["structural_weight"] == 1
    assert spec["padding_weight"] == 0 and spec["same_for_all_learned_families"] is True
    assert read_spec()["selection"]["train_probe_used_for_selection"] is False


def test_budget_and_all_phase_reserves_share_the_unchanged_plan():
    spec = read_spec()
    execution = spec["execution"]
    plan = json.loads((ROOT / "aws/launch_plan.json").read_bytes())
    assert execution["max_wall_seconds"] == sum(execution["phase_seconds"].values()) == plan["compute_seconds_max"] == 6600
    assert execution["hard_resource_cutoff_seconds"] == plan["runtime_seconds_max"] == 7200
    assert execution["phase_seconds"]["paired_training"] == spec["training"]["max_training_seconds"] == 2700
    assert execution["phase_seconds"]["prediction_seal"] + execution["phase_seconds"]["native_evaluation"] + execution["phase_seconds"]["final_evidence"] == 3060
    assert execution["total_owner_cap_usd"] == plan["owner_task_cap_usd"] == "400.00"
    assert execution["per_launch_reserved_cap_usd"] == plan["per_launch_reserved_cap_usd"] == "7.00"
    assert execution["automatic_retries"] == plan["automatic_retries"] == 0
    assert execution["shared_budget_ledger"] == "records/budget/campaign_ledger.json"
    assert read_spec()["protected"]["baseline_sha"] == "0917267b1354e5d036263eaa6ba9a7197eafb776"


def test_gpu_registration_counts_are_separate_from_local_checks():
    gates = read_spec()["gpu_gates"]
    assert gates["launcher_early"] == {"old_policy": 4, "copy_policy": 10, "weighted_loss": 13, "native_contract": 4}
    assert gates["campaign"] == {"actual_copy_modes": 3, "trainer_integration": 2}
    assert gates["actual_copy_test_file"] == "tests/test_gpu_preflight_copy_v3_gpu.py"
    assert gates["trainer_test_file"] == "tests/test_train_v3_gpu.py"
    assert gates["preflight"] == "cas_meta2.gpu_preflight_copy_v3.run_preflight"


def test_manifest_profile_includes_every_new_execution_dependency():
    path = ROOT / "tools/experiment_profiles_v3.py"
    definition = importlib.util.spec_from_file_location("root_cross_v3_profile", path)
    profiles = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(profiles)
    assert profiles.V3_ENTRYPOINT == read_spec()["entrypoint"] == "cas_meta2.campaign_v3"
    assert profiles.V3_SPEC == "research/CAS_META_2_COMPOSITION/EXPERIMENT_V3.json"
    required = {"cas_meta2/" + name for name in (
        "campaign_v3.py", "train_v3.py", "policy_v3.py", "features_v3.py", "grammar_v3.py",
        "loss_v3.py", "selection_v3.py", "curriculum_v3.py", "exclusions_v3.json",
        "development_exclusions_v3.json", "gpu_preflight_copy_v3.py", "gpu_preflight_v3.py")}
    required |= {"EXPERIMENT_V3.json", "aws/launch_v3.py", "tools/experiment_profiles_v3.py",
        "tools/build_launch_bundle_v3.py", "tools/inspect_cloud_packet_v3.py", "tools/audit_stored_packet_v3.py",
        "tests/test_policy_v3_gpu.py", "tests/test_loss_v3_gpu.py", "tests/test_train_v3_gpu.py",
        "tests/test_gpu_preflight_copy_v3_gpu.py"}
    assert required <= set(profiles.V3_LOCAL_FILES)
    assert len(profiles.V3_LOCAL_FILES) == len(set(profiles.V3_LOCAL_FILES))
    assert all((ROOT / name).is_file() for name in profiles.V3_LOCAL_FILES)


def test_campaign_phase_and_gate_constants_match_registered_spec():
    spec = read_spec()
    relative = "cas_meta2/campaign_v3.py"
    assert assignment(relative, "PHASE_SECONDS") == spec["execution"]["phase_seconds"]
    assert assignment(relative, "MAX_WALL_SECONDS") == spec["execution"]["max_wall_seconds"]
    assert assignment(relative, "WORKERS") == spec["execution"]["native_workers"]
    assert list(assignment(relative, "ARMS")) == spec["evaluation"]["arms"]
    assert assignment(relative, "GPU_GROUPS") == {
        "actual_copy": (spec["gpu_gates"]["actual_copy_test_file"], 3, "actual_copy_gpu_tests"),
        "trainer": (spec["gpu_gates"]["trainer_test_file"], 2, "trainer_gpu_tests"),
    }
    trainer_cases = {node.name for node in tree(spec["gpu_gates"]["trainer_test_file"]).body
                     if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
    assert trainer_cases == {
        "test_real_paired_update_and_format3_checkpoint_reload",
        "test_real_cuda_outer_cleanup_with_explicit_mock_inner_frame",
    }
    gate_function = next(node for node in tree(relative).body
                         if isinstance(node, ast.FunctionDef) and node.name == "run_gpu_gates")
    command = next(node.value for node in ast.walk(gate_function) if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "command" for target in node.targets))
    arguments = [node.value if isinstance(node, ast.Constant) else None for node in command.elts]
    # pyproject defaults to not-gpu; the cloud gates must explicitly override it.
    assert any(arguments[index:index + 2] == ["-m", "gpu"] for index in range(len(arguments) - 1))


def test_auditor_hash_patterns_accept_real_source_hashes():
    # Exercise the actual literal without importing the stateful audit tools.
    patterns = {target.id: re.compile(ast.literal_eval(node.value.args[0]))
                for node in tree("tools/inspect_cloud_packet_v3.py").body
                if isinstance(node, ast.Assign) for target in node.targets
                if isinstance(target, ast.Name) and target.id in ("SHA256", "SHA1")}
    assert set(patterns) == {"SHA256", "SHA1"}
    for name, count in (("SHA256", 64), ("SHA1", 40)):
        pattern = patterns[name]
        assert pattern.fullmatch("a" * count)
        for wrong in ("a" * (count - 1), "a" * (count + 1), "G" * count, "a" * count + "\n"):
            assert pattern.fullmatch(wrong) is None


def test_generated_launcher_passes_required_gpu_authorization_to_campaign():
    definition = importlib.util.spec_from_file_location("root_cross_v3_launcher", ROOT / "aws/launch_v3.py")
    launch = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(launch)
    profile = launch.profiles
    # An inert manifest only exercises command construction, not archive/launch.
    members = {profile.PILOT + "/" + name: b"inert source fixture\n" for name in profile.V3_LOCAL_FILES}
    members[profile.V3_SPEC] = (ROOT / "EXPERIMENT_V3.json").read_bytes()
    manifest = {"experiment": profile.make_record(members),
                "files_sha256": {name: sha256(raw).hexdigest() for name, raw in members.items()}}
    remote = ast.parse(launch.remote_program({"manifest": manifest}))
    assignments = {target.id: node for node in ast.walk(remote) if isinstance(node, ast.Assign)
                   for target in node.targets if isinstance(target, ast.Name)}
    assert assignments["argv"].value.elts[2].value == read_spec()["entrypoint"]
    campaign_line = assignments["argv"].lineno
    flags = []
    for node in ast.walk(remote):
        if isinstance(node, ast.Assign) and node.lineno < campaign_line:
            for target in node.targets:
                if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                        and target.value.id == "env" and isinstance(target.slice, ast.Constant)
                        and target.slice.value == "CAS_META2_RUN_GPU_TESTS"):
                    flags.append((node.lineno, ast.literal_eval(node.value)))
        if (isinstance(node, ast.Call) and node.lineno < campaign_line
                and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "env" and node.func.attr == "pop" and node.args
                and isinstance(node.args[0], ast.Constant)):
            assert node.args[0].value != "CAS_META2_RUN_GPU_TESTS"
    assert flags and sorted(flags)[-1][1] == "1"
    assert assignments["policy_expected_tests"].value.value == 27
