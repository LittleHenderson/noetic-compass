"""Pure experiment-dispatch checks. No models, AWS calls or ledger writes."""
import ast
import builtins
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


launch = load("meta2_launch_v2_test", ROOT / "aws/launch.py")
bundle = load("meta2_bundle_v2_test", ROOT / "tools/build_launch_bundle.py")
profiles = launch.profiles


class ExperimentDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("CAS_META2_PURE_TEST_TMP"))
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.plan = json.loads(launch.PLAN_FILE.read_bytes())
        self.source = "b" * 40

    def members(self):
        p, m = bundle.PILOT, bundle.META1
        members = {p + "/" + name: b"# source fixture; never imported\n" for name in profiles.V2_LOCAL_FILES}
        members.update({p + "/cas_meta2/campaign.py": b"# old campaign\n",
            p + "/tests/test_policy_gpu.py": b"# GPU gate fixture\n",
            p + "/aws/launch.py": b"# local launcher fixture\n",
            p + "/aws/launch_plan.json": json.dumps(self.plan).encode(),
            p + "/aws/budget.py": b"# shared budget fixture\n",
            p + "/requirements-gpu.txt": b"numpy==2.2.6\n",
            m + "/cas_meta1/execution.py": b"# frozen helper\n",
            m + "/tests/test_execution_contract.py": b"# GPU contract fixture\n",
            "research/CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/__init__.py": b"# runtime\n"})
        members[profiles.V2_SPEC] = json.dumps({"schema": "cas-meta2-experiment/2",
            "profile": "learning_v2", "entrypoint": "cas_meta2.campaign_v2",
            "training": {"seed": 7, "declared_fixture": True}}, sort_keys=True).encode()
        dist = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
        wheels = [dist + "casformer_reference-0.1.0-py3-none-any.whl", dist + "cas_neural_cjt-0.2.0-py3-none-any.whl"]
        for name in wheels:
            members[name] = name.encode()
        baseline = {"baseline_sha": launch.ACCEPTED_BASELINE, "files": [
            {"path": name.removeprefix("research/"), "sha256": sha256(members[name]).hexdigest()} for name in wheels]}
        members[m + "/BASELINE_MANIFEST.json"] = json.dumps(baseline).encode()
        return members

    def manifest(self, members=None, *, profile="learning_v2"):
        return bundle.make_manifest(members or self.members(), self.source, experiment_profile=profile)

    def archive(self, members, manifest):
        path = self.base / "source.zip"
        with zipfile.ZipFile(path, "w") as archive:
            for name, raw in members.items():
                archive.writestr(name, raw)
            archive.writestr("launch_manifest.json", json.dumps(manifest))
        return path

    def validate(self, members, manifest):
        path = self.archive(members, manifest)
        baseline_digest = sha256(members[bundle.META1 + "/BASELINE_MANIFEST.json"]).hexdigest()
        with patch.object(launch, "ACCEPTED_BASELINE_MANIFEST_SHA256", baseline_digest):
            return launch.validate_archive(path, launch.digest(path), self.source, self.plan)

    def config(self, manifest):
        return {**self.plan, "job": "cas-meta2-profile-fixture", "bucket": "fixture-bucket",
            "archive_sha256": "a" * 64, "smoke_only": False, "manifest": manifest}

    def test_default_manifest_does_not_opt_in_from_v2_files(self):
        manifest = self.manifest(profile="default")
        self.assertNotIn("experiment", manifest)
        self.assertEqual(profiles.entrypoint(manifest), "cas_meta2.campaign")
        self.assertEqual(self.validate(self.members(), manifest), manifest)

    def test_default_manifest_accepts_original_member_set(self):
        members = self.members()
        for name in profiles.V2_LOCAL_FILES:
            del members[bundle.PILOT + "/" + name]
        manifest = self.manifest(members, profile="default")
        self.assertNotIn("experiment", manifest)

    def test_v2_manifest_binds_profile_module_and_exact_spec_bytes(self):
        members = self.members()
        manifest = self.manifest(members)
        self.assertEqual(manifest["experiment"], {"profile": "learning_v2",
            "entrypoint": "cas_meta2.campaign_v2", "spec_path": profiles.V2_SPEC,
            "spec_sha256": sha256(members[profiles.V2_SPEC]).hexdigest()})
        self.assertEqual(self.validate(members, manifest), manifest)

    def test_every_v2_module_and_dispatch_helper_is_required(self):
        for name in profiles.V2_LOCAL_FILES:
            members = self.members()
            del members[bundle.PILOT + "/" + name]
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "EXPERIMENT_V2_SOURCE_MISSING"):
                self.manifest(members)

    def test_unknown_profile_names_are_refused(self):
        for name in ("v2", "cas_meta2.campaign_v2", "../learning_v2", "", None, 2):
            with self.subTest(profile=name), self.assertRaisesRegex(ValueError, "NOT_ALLOWLISTED"):
                self.manifest(profile=name)

    def test_unknown_profile_module_path_or_extra_fields_are_refused(self):
        for changes in ({"profile": "default"}, {"entrypoint": "other.module"},
                        {"spec_path": "../../EXPERIMENT_V2.json"}, {"arguments": ["--unsafe"]}):
            manifest = self.manifest()
            manifest["experiment"].update(changes)
            with self.subTest(changes=changes), self.assertRaises(launch.LaunchRefused):
                launch.experiment_record(manifest)

    def test_null_or_incomplete_experiment_is_not_legacy_fallback(self):
        for value in (None, {}, [], "learning_v2"):
            manifest = self.manifest()
            manifest["experiment"] = value
            with self.subTest(value=value), self.assertRaises(launch.LaunchRefused):
                launch.experiment_record(manifest)

    def test_spec_sha_must_match_manifest_member_digest(self):
        manifest = self.manifest()
        manifest["experiment"]["spec_sha256"] = "0" * 64
        with self.assertRaisesRegex(launch.LaunchRefused, "SPEC_MANIFEST_DIGEST_MISMATCH"):
            self.validate(self.members(), manifest)

    def test_spec_bytes_cannot_change_behind_declared_digest(self):
        manifest = self.manifest()
        with self.assertRaisesRegex(launch.LaunchRefused, "SPEC_BYTES_MISMATCH"):
            launch.experiment_record(manifest, lambda _: b"changed")

    def test_wrong_spec_schema_rejected_even_with_recomputed_hashes(self):
        members = self.members()
        manifest = self.manifest(members)
        document = json.loads(members[profiles.V2_SPEC])
        document["schema"] = "other/1"
        members[profiles.V2_SPEC] = json.dumps(document).encode()
        digest = sha256(members[profiles.V2_SPEC]).hexdigest()
        manifest["files_sha256"][profiles.V2_SPEC] = digest
        manifest["experiment"]["spec_sha256"] = digest
        with self.assertRaisesRegex(launch.LaunchRefused, "SPEC_IDENTITY_MISMATCH"):
            self.validate(members, manifest)

    def test_duplicate_and_nonfinite_spec_fields_are_rejected(self):
        valid = self.members()[profiles.V2_SPEC].decode()
        for suffix in (',"profile":"learning_v2"}', ',"not_finite":NaN}', ',"overflow":1e999}'):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                profiles.validate_v2_spec((valid[:-1] + suffix).encode())

    def test_spec_without_new_source_is_refused_at_launcher_too(self):
        manifest = self.manifest()
        del manifest["files_sha256"][bundle.PILOT + "/cas_meta2/train_v2.py"]
        with self.assertRaisesRegex(launch.LaunchRefused, "V2_SOURCE_MISSING"):
            launch.experiment_record(manifest)

    def test_remote_entrypoint_is_selected_only_by_manifest(self):
        for profile, expected in (("default", "cas_meta2.campaign"), ("learning_v2", "cas_meta2.campaign_v2")):
            code = launch.remote_program(self.config(self.manifest(profile=profile)))
            compile(code, "<remote-not-executed>", "exec")
            tree = ast.parse(code)
            assignments = [node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "argv" for target in node.targets)]
            self.assertEqual(len(assignments), 1)
            self.assertEqual(assignments[0].elts[2].value, expected)
            self.assertNotIn("__CAS_META2_ENTRYPOINT__", code)

    def test_remote_preserves_cutoff_gates_paths_and_failure_artifacts(self):
        code = launch.remote_program(self.config(self.manifest()))
        for fragment in ("cloud_deadline_confirmed", "tests/test_execution_contract.py", "tests/test_policy_gpu.py",
            "effective_campaign_seconds = min(CONFIG['compute_seconds_max'],int(deadline-time.time()-180))",
            "seconds=effective_campaign_seconds,deadline=deadline", "os.killpg(process.pid,signal.SIGKILL)",
            "out = package / m['pilot_dir'] / 'runs' / 'cloud_job'", "predictions.jsonl",
            "CAMPAIGN_EXPERIMENT_IDENTITY_MISMATCH", "complete['experiment'] = m['experiment']",
            "job_record['experiment'] = m['experiment']"):
            self.assertIn(fragment, code)
        self.assertLess(code.index("cloud_deadline_confirmed"), code.index("'torch==2.11.0'"))

    def test_profile_validation_precedes_budget_read_or_provider_import(self):
        manifest = self.manifest()
        manifest["experiment"]["entrypoint"] = "arbitrary.module"
        args = types.SimpleNamespace(approved_cap_usd="400.00")
        with patch.object(launch.budget, "read_ledger", side_effect=AssertionError("BUDGET_REACHED")):
            with self.assertRaisesRegex(launch.LaunchRefused, "NOT_ALLOWLISTED"):
                launch.execute(args, self.plan, manifest)

    def test_local_v2_modules_spec_and_dispatch_helpers_are_bound(self):
        members = self.members()
        manifest = self.manifest(members)
        local = self.base / "pilot"
        for name, raw in members.items():
            if name.startswith(bundle.PILOT + "/"):
                path = local / name.removeprefix(bundle.PILOT + "/")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
        with patch.object(launch, "PILOT_ROOT", local), patch.object(launch, "__file__", str(local / "aws/launch.py")), \
             patch.object(launch, "PLAN_FILE", local / "aws/launch_plan.json"), \
             patch.object(launch.budget, "__file__", str(local / "aws/budget.py")), \
             patch.object(launch.subprocess, "check_output", return_value=self.source + "\n"):
            hashes = launch.verify_launcher_identity(manifest)
            self.assertEqual(len(hashes), 4 + len(profiles.V2_LOCAL_FILES))
            for relative in profiles.V2_LOCAL_FILES:
                path = local / relative
                prior = path.read_bytes()
                path.write_bytes(prior + b"\n# changed")
                with self.subTest(path=relative), self.assertRaisesRegex(launch.LaunchRefused, "LOCAL_LAUNCHER_ARCHIVE_IDENTITY_MISMATCH"):
                    launch.verify_launcher_identity(manifest)
                path.write_bytes(prior)

    def test_shared_budget_ledger_and_plan_are_unchanged(self):
        launch.validate_approval("400.00", self.plan)
        self.assertEqual(launch.budget.CANONICAL_LEDGER, ROOT / "records/budget/campaign_ledger.json")
        with patch.object(launch.budget, "reserve_budget", return_value={}) as reserve:
            launch.reserve_budget("fixture", self.source, "a" * 64, self.plan)
        reserve.assert_called_once_with("fixture", self.source, "a" * 64, "7.00", self.plan)
        self.assertEqual((self.plan["instance_type"], self.plan["runtime_seconds_max"]), ("g7.2xlarge", 7200))

    def test_default_dispatch_helper_tampering_is_rejected(self):
        members = self.members()
        manifest = self.manifest(members, profile="default")
        local = self.base / "default-pilot"
        for name, raw in members.items():
            if name.startswith(bundle.PILOT + "/"):
                path = local / name.removeprefix(bundle.PILOT + "/")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
        with patch.object(launch, "PILOT_ROOT", local), patch.object(launch, "__file__", str(local / "aws/launch.py")), \
             patch.object(launch, "PLAN_FILE", local / "aws/launch_plan.json"), \
             patch.object(launch.budget, "__file__", str(local / "aws/budget.py")), \
             patch.object(launch.subprocess, "check_output", return_value=self.source + "\n"):
            self.assertEqual(len(launch.verify_launcher_identity(manifest)), 5)
            (local / "tools/experiment_profiles.py").write_bytes(b"changed")
            with self.assertRaisesRegex(launch.LaunchRefused, "LOCAL_LAUNCHER_ARCHIVE_IDENTITY_MISMATCH"):
                launch.verify_launcher_identity(manifest)

    def test_v2_packet_requires_matching_collection_and_completion_profiles(self):
        experiment = self.manifest()["experiment"]
        path = self.base / "artifact.zip"
        record = {"job": "fixture", "source_sha": self.source, "returncode": 0,
                  "partial_evidence": False, "omitted_full_file_count": 0, "experiment": experiment}
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("artifact_collection_receipt.json", json.dumps(record))
        result = {"sha256": launch.digest(path), "bytes": path.stat().st_size,
                  "returncode": 0, "experiment": experiment}
        launch.verify_downloaded_packet(path, result, "fixture", self.source, self.plan, experiment=experiment)
        del result["experiment"]
        with self.assertRaisesRegex(launch.LaunchRefused, "RESULT_EXPERIMENT_IDENTITY_MISMATCH"):
            launch.verify_downloaded_packet(path, result, "fixture", self.source, self.plan, experiment=experiment)

    def test_all_dispatch_imports_are_pure(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name == "torch" or name.startswith("torch.") or name == "boto3" or name.startswith("boto3.") or name.startswith("cas_meta2"):
                raise AssertionError("FORBIDDEN_NEURAL_OR_PROVIDER_IMPORT:" + name)
            return original(name, *args, **kwargs)
        with patch.object(builtins, "__import__", side_effect=guarded):
            load("pure_launch_fixture", ROOT / "aws/launch.py")
            load("pure_bundle_fixture", ROOT / "tools/build_launch_bundle.py")


if __name__ == "__main__":
    unittest.main(verbosity=2)
