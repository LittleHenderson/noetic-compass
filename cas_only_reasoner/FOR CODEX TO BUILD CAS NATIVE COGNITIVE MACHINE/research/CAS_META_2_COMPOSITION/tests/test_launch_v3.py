"""Pure v3 launch contracts: no GPU, provider access or real ledger mutations."""
import ast
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launch = load("meta2_launch_v3_pure_test", ROOT / "aws/launch_v3.py")
bundle = load("meta2_bundle_v3_pure_test", ROOT / "tools/build_launch_bundle_v3.py")
profiles = launch.profiles


def fixture_members(plan):
    p, m = bundle.PILOT, bundle.META1
    members = {p + "/" + name: b"# inert source fixture\n" for name in profiles.V3_LOCAL_FILES}
    members.update({
        p + "/aws/launch_plan.json": json.dumps(plan).encode(),
        p + "/requirements-gpu.txt": b"numpy==2.2.6\n",
        m + "/cas_meta1/execution.py": b"# frozen helper fixture\n",
        m + "/tests/test_execution_contract.py": b"# no actual GPU test\n",
        "research/CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/__init__.py": b"# frozen runtime fixture\n",
    })
    members[profiles.V3_SPEC] = json.dumps({"schema": "cas-meta2-experiment/3",
        "profile": "learning_v3", "entrypoint": "cas_meta2.campaign_v3"}).encode()
    dist = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
    wheels = [dist + "casformer_reference-0.1.0-py3-none-any.whl",
              dist + "cas_neural_cjt-0.2.0-py3-none-any.whl"]
    for name in wheels:
        members[name] = b"inert wheel fixture " + name.encode()
    members[m + "/BASELINE_MANIFEST.json"] = json.dumps({
        "baseline_sha": launch.ACCEPTED_BASELINE, "files": [
            {"path": name.removeprefix("research/"), "sha256": sha256(members[name]).hexdigest()}
            for name in wheels]}).encode()
    return members


def fixture_manifest(members):
    baseline_digest = sha256(members[bundle.META1 + "/BASELINE_MANIFEST.json"]).hexdigest()
    with patch.object(bundle, "BASELINE_MANIFEST_SHA256", baseline_digest):
        return bundle.make_manifest(members, "b" * 40)


class LaunchV3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("CAS_META2_PURE_TEST_TMP"))
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.plan = json.loads(launch.PLAN_FILE.read_bytes())
        self.members = fixture_members(self.plan)
        self.manifest = fixture_manifest(self.members)

    def config(self):
        return {**self.plan, "job": "cas-meta2-v3-fixture", "bucket": "fixture-bucket",
                "archive_sha256": "a" * 64, "smoke_only": False, "manifest": self.manifest}

    def source_zip(self, manifest=None):
        path = self.base / "source.zip"
        with zipfile.ZipFile(path, "w") as archive:
            for name, raw in self.members.items():
                archive.writestr(name, raw)
            archive.writestr("launch_manifest.json", json.dumps(manifest or self.manifest))
        return path

    def validate_archive(self, path):
        baseline_digest = sha256(self.members[bundle.META1 + "/BASELINE_MANIFEST.json"]).hexdigest()
        with patch.object(launch, "ACCEPTED_BASELINE_MANIFEST_SHA256", baseline_digest):
            return launch.validate_archive(path, launch.digest(path), "b" * 40, self.plan)

    def test_exact_v3_archive_validates_without_provider_or_model(self):
        self.assertEqual(self.validate_archive(self.source_zip()), self.manifest)

    def test_missing_profile_never_falls_back(self):
        del self.manifest["experiment"]
        with self.assertRaisesRegex(launch.LaunchRefused, "V3_MANIFEST_REQUIRED"):
            launch.experiment_record(self.manifest)

    def test_default_and_v2_profiles_refused(self):
        for value in ("default", "learning_v2", "other", None, 3):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "NOT_ALLOWLISTED"):
                profiles.make_record(self.members, value)

    def test_arbitrary_entrypoint_refused_before_budget_or_lock(self):
        self.manifest["experiment"]["entrypoint"] = "other.module"
        with patch.object(launch.budget, "read_ledger", side_effect=AssertionError("LEDGER_REACHED")), \
             patch.object(launch, "campaign_execution_lock", side_effect=AssertionError("LOCK_REACHED")):
            with self.assertRaisesRegex(launch.LaunchRefused, "NOT_ALLOWLISTED"):
                launch.execute(types.SimpleNamespace(approved_cap_usd="400.00"), self.plan, self.manifest)

    def test_extra_profile_fields_are_refused(self):
        self.manifest["experiment"]["argv"] = ["--other"]
        with self.assertRaisesRegex(launch.LaunchRefused, "FIELDS_INVALID"):
            launch.experiment_record(self.manifest)

    def test_spec_hash_and_schema_both_bound(self):
        self.manifest["experiment"]["spec_sha256"] = "0" * 64
        with self.assertRaisesRegex(launch.LaunchRefused, "SPEC_MANIFEST_DIGEST_MISMATCH"):
            self.validate_archive(self.source_zip())

    def test_v3_remote_command_and_gpu_gate_count(self):
        code = launch.remote_program(self.config())
        tree = ast.parse(code)
        compile(code, "<never-executed-remote>", "exec")
        assignments = {target.id: node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                       for target in node.targets if isinstance(target, ast.Name)}
        self.assertEqual(assignments["argv"].elts[2].value, "cas_meta2.campaign_v3")
        paths = [node.value for node in assignments["policy_argv"].elts if isinstance(node, ast.Constant)]
        self.assertEqual([value for value in paths if value.startswith("tests/")],
                         ["tests/test_policy_gpu.py", "tests/test_policy_v3_gpu.py", "tests/test_loss_v3_gpu.py"])
        self.assertEqual(assignments["policy_expected_tests"].value, 27)
        self.assertNotIn("test_learning_v2_gpu.py", code)

    def test_remote_gates_finish_before_campaign_and_effective_deadline(self):
        code = launch.remote_program(self.config())
        self.assertLess(code.index("(out/'gpu_policy_receipt.json')"),
                        code.index("effective_campaign_seconds ="))
        self.assertIn("min(CONFIG['compute_seconds_max'],int(deadline-time.time()-180))", code)
        self.assertIn("seconds=effective_campaign_seconds,deadline=deadline", code)
        self.assertLess(code.index("cloud_deadline_confirmed"), code.index("'torch==2.11.0'"))

    def test_v3_campaign_keeps_explicit_aws_gpu_test_authorization(self):
        code = launch.remote_program(self.config())
        tree = ast.parse(code)
        flag_assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                    and target.value.id == "env" and isinstance(target.slice, ast.Constant)
                    and target.slice.value == "CAS_META2_RUN_GPU_TESTS" for target in node.targets)]
        self.assertTrue(flag_assignments)
        self.assertEqual(flag_assignments[-1].value.value, "1")
        self.assertNotIn("env.pop('CAS_META2_RUN_GPU_TESTS')", code)
        self.assertLess(code.index("# V3 performs its real-data CUDA gates"),
                        code.index("effective_campaign_seconds ="))
        self.assertIn("env['CAS_META2_AWS_JOB_ID'] = CONFIG['job']", code)

    def test_remote_fixed_roots_status_and_complete_evidence(self):
        code = launch.remote_program(self.config())
        for fragment in ("out = package / m['pilot_dir'] / 'runs' / 'cloud_job'",
                         "'--output',str(out/'campaign')", "predictions.jsonl", "predictions_seal.json",
                         "for checkpoint in ('initial','best','last')",
                         "cas-meta2-campaign-receipt/3",
                         "CAS_META_2_V3_AWS_CAMPAIGN_COMPLETED", "CAS_META_2_V3_AWS_SMOKE_COMPLETED",
                         "campaign_receipt.get('completed') is not True",
                         "CAMPAIGN_EXPERIMENT_IDENTITY_MISMATCH"):
            self.assertIn(fragment, code)

    def test_remote_partial_bundle_and_worker_cleanup_preserved(self):
        code = launch.remote_program(self.config())
        for fragment in ("os.killpg(process.pid,signal.SIGTERM)", "os.killpg(process.pid,signal.SIGKILL)",
                         "partial_evidence=partial", "omitted_full_file_count=len(files)-len(selected)",
                         "MANDATORY_CHECKPOINT_AND_PREDICTIONS_EXCEED_FAILURE_PACKET_CEILING",
                         "COMPRESSED_ARTIFACT_CEILING", "CONFIG['evidence_expanded_bytes_max']"):
            self.assertIn(fragment, code)

    def test_cleanup_functions_match_frozen_old_launcher_exactly(self):
        old = ast.parse((ROOT / "aws/launch.py").read_text())
        new = ast.parse((ROOT / "aws/launch_v3.py").read_text())
        select = lambda tree: {n.name: ast.dump(n, include_attributes=False) for n in tree.body
                               if isinstance(n, ast.FunctionDef)}
        old_functions, new_functions = select(old), select(new)
        for name in ("check_tag", "confirm_deleted_volumes", "remove_owned_auxiliary_resources",
                     "reconcile_instance", "verify_schedule", "terminate_owned_instance",
                     "build_evidence_bundle", "sample_artifact_bytes", "user_data", "validate_approval",
                     "reserve_budget"):
            with self.subTest(function=name):
                self.assertEqual(new_functions[name], old_functions[name])

    def test_shared_budget_plan_and_reservation_exact(self):
        launch.validate_approval("400.00", self.plan)
        self.assertEqual(launch.budget.CANONICAL_LEDGER, ROOT / "records/budget/campaign_ledger.json")
        self.assertEqual(launch.PLAN_FILE, ROOT / "aws/launch_plan.json")
        with patch.object(launch.budget, "reserve_budget", return_value={}) as reserve:
            launch.reserve_budget("fixture", "b" * 40, "a" * 64, self.plan)
        reserve.assert_called_once_with("fixture", "b" * 40, "a" * 64, "7.00", self.plan)

    def test_launch_limits_cannot_change(self):
        for key, wrong in (("instance_type", "g4dn.xlarge"), ("runtime_seconds_max", 7201),
                           ("compute_seconds_max", 6601), ("per_launch_reserved_cap_usd", "8.00")):
            changed = dict(self.plan, **{key: wrong})
            with self.subTest(key=key), self.assertRaises(launch.LaunchRefused):
                launch.validate_approval("400.00", changed)

    def install_local_fixture(self):
        homebase = self.base / "home"
        pilot = homebase / bundle.PILOT
        for name, raw in self.members.items():
            target = homebase / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        return pilot

    def identity_context(self, pilot):
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch.object(launch, "PILOT_ROOT", pilot))
        stack.enter_context(patch.object(launch.budget, "CANONICAL_LEDGER", pilot / "records/budget/campaign_ledger.json"))
        stack.enter_context(patch.object(launch, "_BUDGET_SHA256",
            self.manifest["files_sha256"][bundle.PILOT + "/aws/budget.py"]))
        stack.enter_context(patch.object(launch, "_PROFILE_IMPORT_SHA256",
            self.manifest["files_sha256"][bundle.PILOT + "/tools/experiment_profiles_v3.py"]))
        stack.enter_context(patch.object(profiles, "git_context", return_value=(self.base, "fake/")))
        stack.enter_context(patch.object(profiles, "git_members", return_value=self.members))
        return stack

    def test_every_source_member_bound_to_git_and_local(self):
        pilot = self.install_local_fixture()
        with self.identity_context(pilot):
            self.assertEqual(launch.verify_launcher_identity(self.manifest), self.manifest["files_sha256"])
            path = pilot / "cas_meta2/development_exclusions_v3.json"
            path.write_bytes(b"changed")
            with self.assertRaisesRegex(launch.LaunchRefused, "LOCAL_SOURCE_ARCHIVE_IDENTITY_MISMATCH"):
                launch.verify_launcher_identity(self.manifest)

    def test_manifest_and_local_collusion_cannot_override_git(self):
        pilot = self.install_local_fixture()
        name = bundle.PILOT + "/cas_meta2/train_v3.py"
        (pilot / "cas_meta2/train_v3.py").write_bytes(b"wrong")
        self.manifest["files_sha256"][name] = sha256(b"wrong").hexdigest()
        with self.identity_context(pilot):
            with self.assertRaisesRegex(launch.LaunchRefused, "SOURCE_COMMIT_MANIFEST_BYTES_MISMATCH"):
                launch.verify_launcher_identity(self.manifest)

    def test_source_member_omission_or_addition_refused(self):
        pilot = self.install_local_fixture()
        self.manifest["files_sha256"]["research/CASFORMER_v0_1/uncommitted.py"] = "a" * 64
        with self.identity_context(pilot):
            with self.assertRaisesRegex(launch.LaunchRefused, "MEMBER_SET_MISMATCH"):
                launch.verify_launcher_identity(self.manifest)

    def test_loaded_profile_bytes_are_bound(self):
        pilot = self.install_local_fixture()
        with self.identity_context(pilot), patch.object(launch, "_PROFILE_IMPORT_SHA256", "0" * 64):
            with self.assertRaisesRegex(launch.LaunchRefused, "PROFILE_CHANGED_AFTER_IMPORT"):
                launch.verify_launcher_identity(self.manifest)

    def test_paid_cli_preimport_checks_use_real_git_bytes_not_manifest(self):
        pilot = self.install_local_fixture()
        homebase = pilot.parents[1]
        def git(argv, **kwargs):
            if argv[1:3] == ["rev-parse", "--show-toplevel"]:
                return str(homebase)
            if argv[1] == "rev-parse":
                return "b" * 40
            self.assertEqual(argv[1], "show")
            return self.members[argv[2].split(":", 1)[1]]
        with patch.object(launch, "__file__", str(pilot / "aws/launch_v3.py")), \
             patch.object(launch.subprocess, "check_output", side_effect=git):
            self.assertEqual(len(launch.verify_cli_source_before_helper_import("b" * 40)), 6)
            (pilot / "tools/experiment_profiles_v3.py").write_bytes(b"changed helper")
            with self.assertRaisesRegex(ValueError, "PREIMPORT_EXECUTABLE_SOURCE_MISMATCH"):
                launch.verify_cli_source_before_helper_import("b" * 40)

    def test_preimport_check_rejects_short_or_implicit_source(self):
        for source in (None, "HEAD", "b" * 39):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "EXACT_SOURCE_SHA_REQUIRED"):
                launch.verify_cli_source_before_helper_import(source)

    def test_paid_cli_guard_precedes_helper_execution(self):
        source = (ROOT / "aws/launch_v3.py").read_text()
        self.assertLess(source.index("verify_cli_source_before_helper_import(_early_args.source_sha)"),
                        source.index("_BUDGET_SPEC.loader.exec_module"))
        self.assertLess(source.index("verify_cli_source_before_helper_import(_early_args.source_sha)"),
                        source.index("_PROFILE_SPEC.loader.exec_module"))
        self.assertIn("description=__doc__, allow_abbrev=False", source)

    def test_execution_lock_rejects_overlap_and_preserves_first_owner(self):
        path = self.base / "execution.lock"
        with patch.object(launch, "EXECUTION_LOCK_FILE", path):
            with launch.campaign_execution_lock():
                original = path.read_bytes()
                with self.assertRaisesRegex(launch.LaunchRefused, "ALREADY_LOCKED"):
                    with launch.campaign_execution_lock():
                        self.fail("second caller entered")
                self.assertEqual(path.read_bytes(), original)
            self.assertFalse(path.exists())

    def test_execution_lock_does_not_delete_changed_owner(self):
        path = self.base / "execution.lock"
        with patch.object(launch, "EXECUTION_LOCK_FILE", path):
            with self.assertRaisesRegex(launch.LaunchRefused, "OWNERSHIP_CHANGED"):
                with launch.campaign_execution_lock():
                    path.write_bytes(b"different owner")
            self.assertEqual(path.read_bytes(), b"different owner")

    def test_source_refusal_precedes_all_writes_and_provider_imports(self):
        with patch.object(launch, "verify_launcher_identity", side_effect=launch.LaunchRefused("SOURCE_BAD")), \
             patch.object(launch, "campaign_execution_lock", side_effect=AssertionError("LOCK_REACHED")), \
             patch.object(launch.budget, "read_ledger", side_effect=AssertionError("BUDGET_REACHED")):
            with self.assertRaisesRegex(launch.LaunchRefused, "SOURCE_BAD"):
                launch.execute(types.SimpleNamespace(approved_cap_usd="400.00"), self.plan, self.manifest)

    def test_download_requires_matching_experiment_and_complete_collection(self):
        artifact = self.base / "result.zip"
        collection = {"job": "fixture", "source_sha": "b" * 40, "returncode": 0,
                      "partial_evidence": False, "omitted_full_file_count": 0,
                      "experiment": self.manifest["experiment"]}
        with zipfile.ZipFile(artifact, "w") as archive:
            archive.writestr("artifact_collection_receipt.json", json.dumps(collection))
        result = {"bytes": artifact.stat().st_size, "sha256": launch.digest(artifact),
                  "returncode": 0, "experiment": self.manifest["experiment"]}
        self.assertEqual(launch.verify_downloaded_packet(artifact, result, "fixture", "b" * 40,
                          self.plan, experiment=self.manifest["experiment"]), collection)
        result["experiment"] = {}
        with self.assertRaisesRegex(launch.LaunchRefused, "EXPERIMENT_IDENTITY_MISMATCH"):
            launch.verify_downloaded_packet(artifact, result, "fixture", "b" * 40,
                                           self.plan, experiment=self.manifest["experiment"])
