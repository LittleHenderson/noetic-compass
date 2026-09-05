"""Pure pinned-source packaging checks, without GPU or AWS execution."""
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("meta2_bundle_under_test",ROOT/"tools"/"build_launch_bundle.py")
bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle)


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT/"tests")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def members(self):
        p,m=bundle.PILOT,bundle.META1
        protected_name = "CASFORMER_v0_1/source.py"
        protected = b"# accepted test fixture\n"
        baseline = {"baseline_sha":bundle.BASELINE_SHA,"files":[{"path":protected_name,"sha256":sha256(protected).hexdigest()}]}
        return {p+"/cas_meta2/campaign.py":b"# campaign fixture\n",p+"/tests/test_policy_gpu.py":b"# GPU gate fixture\n",p+"/aws/launch.py":b"# launcher fixture\n",
                p+"/aws/launch_plan.json":b"{}",p+"/aws/budget.py":b"# budget fixture\n",p+"/requirements-gpu.txt":b"numpy==2.2.6\n",
                m+"/cas_meta1/execution.py":b"# helper fixture\n",m+"/tests/test_execution_contract.py":b"# tests fixture\n",
                m+"/BASELINE_MANIFEST.json":json.dumps(baseline).encode(),"research/"+protected_name:protected}

    def test_manifest_binds_all_five_packages(self):
        manifest = bundle.make_manifest(self.members(),"a"*40)
        self.assertEqual(manifest["schema_version"],2)
        self.assertEqual(manifest["included_packages"],list(bundle.PACKAGES))
        self.assertEqual(manifest["protected_baseline_files"],1)
        self.assertFalse(manifest["neural_execution_performed_during_packaging"])

    def test_every_member_has_exact_digest(self):
        members = self.members()
        manifest = bundle.make_manifest(members,"a"*40)
        self.assertEqual(manifest["files_sha256"],{key:sha256(value).hexdigest() for key,value in members.items()})

    def test_missing_campaign_rejected(self):
        members = self.members()
        del members[bundle.PILOT+"/cas_meta2/campaign.py"]
        with self.assertRaisesRegex(ValueError,"NOT_PRESENT_IN_PINNED"):
            bundle.make_manifest(members,"a"*40)

    def test_missing_budget_rejected(self):
        members = self.members()
        del members[bundle.PILOT+"/aws/budget.py"]
        with self.assertRaisesRegex(ValueError,"NOT_PRESENT_IN_PINNED"):
            bundle.make_manifest(members,"a"*40)

    def test_changed_accepted_source_rejected(self):
        members = self.members()
        members["research/CASFORMER_v0_1/source.py"] = b"changed"
        with self.assertRaisesRegex(ValueError,"GIT_BASELINE_BYTES_DIFFER"):
            bundle.make_manifest(members,"a"*40)

    def test_missing_accepted_source_rejected(self):
        members = self.members()
        del members["research/CASFORMER_v0_1/source.py"]
        with self.assertRaisesRegex(ValueError,"GIT_BASELINE_BYTES_DIFFER"):
            bundle.make_manifest(members,"a"*40)

    def test_wrong_baseline_revision_rejected(self):
        members = self.members()
        baseline = json.loads(members[bundle.META1+"/BASELINE_MANIFEST.json"])
        baseline["baseline_sha"] = "b"*40
        members[bundle.META1+"/BASELINE_MANIFEST.json"] = json.dumps(baseline).encode()
        with self.assertRaisesRegex(ValueError,"WRONG_ACCEPTED_BASELINE"):
            bundle.make_manifest(members,"a"*40)

    def test_size_limit_checked_without_large_file(self):
        with patch.object(bundle,"EXPANDED_LIMIT",1),self.assertRaisesRegex(ValueError,"SIZE_CEILING"):
            bundle.make_manifest(self.members(),"a"*40)

    def test_historical_gold_results_are_not_training_inputs(self):
        for package in ("CAS_META_1_LEARNED_SELECTION","CAS_META_2_COMPOSITION"):
            for folder in ("records","runs","__pycache__"):
                self.assertFalse(bundle.include_member(f"research/{package}/{folder}/predictions.jsonl"))

    def test_frozen_release_artifacts_are_preserved(self):
        self.assertTrue(bundle.include_member("research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/frozen.whl"))

    def test_source_and_curriculum_inputs_are_included(self):
        for name in (bundle.PILOT+"/cas_meta2/campaign.py",bundle.META1+"/data/dataset_manifest.json"):
            self.assertTrue(bundle.include_member(name))

    def test_unsafe_or_unexpected_source_paths_rejected(self):
        for name in ("../escape","research/CAS_META_2_COMPOSITION/../bad","research/CAS_META_2_COMPOSITION/a\\b","research/other/source.py"):
            with self.subTest(name=name),self.assertRaises(ValueError):
                bundle.include_member(name)

    def test_untracked_source_blocks_packaging(self):
        repo = self.base/"repo"
        root = repo/"research"/"CAS_META_2_COMPOSITION"
        root.mkdir(parents=True)
        def fake(command,**kwargs):
            if command[1:]==["rev-parse","--show-toplevel"]: return str(repo)+"\n"
            if command[1:]==["rev-parse","HEAD"]: return "a"*40+"\n"
            if "diff" in command: return ""
            if "ls-files" in command: return "research/CAS_META_2_COMPOSITION/cas_meta2/new.py\0"
            raise AssertionError("Archive creation reached despite untracked code")
        with patch.object(bundle,"ROOT",root),patch.object(bundle.subprocess,"check_output",side_effect=fake),self.assertRaisesRegex(ValueError,"UNTRACKED_SOURCE"):
            bundle.build(root/"test.zip")

    def test_tracked_dirty_source_blocks_packaging(self):
        repo = self.base/"repo"
        root = repo/"research"/"CAS_META_2_COMPOSITION"
        root.mkdir(parents=True)
        def fake(command,**kwargs):
            if command[1:]==["rev-parse","--show-toplevel"]: return str(repo)+"\n"
            if command[1:]==["rev-parse","HEAD"]: return "a"*40+"\n"
            if "diff" in command: return "research/CAS_META_2_COMPOSITION/cas_meta2/campaign.py\0"
            raise AssertionError("Archive creation reached despite dirty code")
        with patch.object(bundle,"ROOT",root),patch.object(bundle.subprocess,"check_output",side_effect=fake),self.assertRaisesRegex(ValueError,"TRACKED_SOURCE_CHANGES"):
            bundle.build(root/"test.zip")

    def test_output_outside_campaign_rejected(self):
        with self.assertRaisesRegex(ValueError,"OUTPUT_INSIDE_CAMPAIGN"):
            bundle.build(ROOT.parent/"not-owned.zip")


if __name__ == "__main__":
    unittest.main(verbosity=2)
