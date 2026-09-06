"""Pure committed-source packaging tests; never build a model or contact AWS."""
import io
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from test_launch_v3 import bundle, fixture_manifest, fixture_members, launch, profiles


class BundleV3Tests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(launch.PLAN_FILE.read_bytes())
        self.members = fixture_members(self.plan)

    def test_fixed_profile_spec_and_source_inventory(self):
        manifest = fixture_manifest(self.members)
        self.assertEqual(manifest["experiment"], {
            "profile": "learning_v3", "entrypoint": "cas_meta2.campaign_v3",
            "spec_path": profiles.V3_SPEC, "spec_sha256": sha256(self.members[profiles.V3_SPEC]).hexdigest()})
        for name in ("cas_meta2/exclusions_v3.json", "cas_meta2/development_exclusions_v3.json",
                     "cas_meta2/gpu_preflight_copy_v3.py", "tests/test_train_v3_gpu.py",
                     "tools/inspect_cloud_packet_v3.py", "tools/audit_stored_packet_v3.py",
                     "tests/test_v3_integration_static.py"):
            self.assertIn(name, profiles.V3_LOCAL_FILES)
        self.assertEqual(set(manifest["files_sha256"]), set(self.members))

    def test_every_registered_v3_file_is_required(self):
        for name in profiles.V3_LOCAL_FILES:
            members = dict(self.members)
            del members[bundle.PILOT + "/" + name]
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "V3_SOURCE_MISSING"):
                fixture_manifest(members)

    def test_duplicate_nonfinite_and_overflow_spec_refused(self):
        valid = self.members[profiles.V3_SPEC].decode()
        for suffix in (',"profile":"learning_v3"}', ',"bad":NaN}', ',"bad":1e999}'):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                profiles.validate_v3_spec((valid[:-1] + suffix).encode())

    def test_wrong_spec_schema_refused_even_with_new_hash(self):
        value = json.loads(self.members[profiles.V3_SPEC])
        value["schema"] = "cas-meta2-experiment/2"
        self.members[profiles.V3_SPEC] = json.dumps(value).encode()
        with self.assertRaisesRegex(ValueError, "SPEC_IDENTITY_MISMATCH"):
            fixture_manifest(self.members)

    def test_absent_or_wrong_manifest_record_refused(self):
        for bad in (None, {}, [], "learning_v3"):
            with self.subTest(record=bad), self.assertRaises(ValueError):
                profiles.validate_manifest({"experiment": bad})

    def test_manifest_hash_without_matching_spec_bytes_refused(self):
        manifest = fixture_manifest(self.members)
        with self.assertRaisesRegex(ValueError, "SPEC_BYTES_MISMATCH"):
            profiles.validate_manifest(manifest, lambda _: b"changed")

    def test_known_accepted_manifest_digest_is_not_self_declared(self):
        with self.assertRaisesRegex(ValueError, "PROTECTED_BASELINE_MANIFEST_CHANGED"):
            bundle.make_manifest(self.members, "b" * 40)

    def test_historical_records_and_runs_excluded_not_assets(self):
        for pilot in ("CAS_META_1_LEARNED_SELECTION", "CAS_META_2_COMPOSITION"):
            for directory in ("records", "runs", "__pycache__", ".pytest_cache"):
                self.assertFalse(bundle.include_member("research/" + pilot + "/" + directory + "/x.json"))
        self.assertTrue(bundle.include_member(bundle.PILOT + "/cas_meta2/exclusions_v3.json"))
        self.assertTrue(bundle.include_member(bundle.PILOT + "/cas_meta2/development_exclusions_v3.json"))
        self.assertTrue(bundle.include_member("research/CASFORMER_v0_1/records/frozen.json"))

    def test_unsafe_and_unknown_source_paths_refused(self):
        for name in ("../escape", "research/CAS_META_2_COMPOSITION/../escape",
                     "research/CAS_META_2_COMPOSITION//x", "research/CAS_META_3_PROCEDURAL_MEMORY/x",
                     "research/CAS_META_2_COMPOSITION/a:b", "research/CAS_META_2_COMPOSITION/a\\b"):
            with self.subTest(path=name), self.assertRaises(ValueError):
                profiles.include_member(name)
            with self.subTest(builder_path=name), self.assertRaises(ValueError):
                bundle.include_member(name)

    def test_archive_requires_full_external_sha(self):
        for invalid in ("HEAD", "main", "b" * 39, "", None):
            with self.subTest(source=invalid), self.assertRaisesRegex(ValueError, "EXACT_SOURCE_SHA_REQUIRED"):
                profiles.git_members(Path("."), "prefix/", invalid)

    def git_zip(self, entries):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            for name, raw, mode in entries:
                info = zipfile.ZipInfo("prefix/" + name.removeprefix("research/"))
                info.external_attr = mode << 16
                archive.writestr(info, raw)
        return stream.getvalue()

    def test_git_members_are_from_exact_source_commit(self):
        raw = self.git_zip([(bundle.PILOT + "/one.py", b"committed bytes", 0o100644)])
        with patch.object(profiles.subprocess, "check_output", side_effect=["b" * 40 + "\n", raw]) as git:
            result = profiles.git_members(Path("."), "prefix/", "b" * 40)
        self.assertEqual(result, {bundle.PILOT + "/one.py": b"committed bytes"})
        self.assertIn("b" * 40, git.call_args_list[-1].args[0])
        self.assertIn("archive", git.call_args_list[-1].args[0])

    def test_git_source_case_aliases_refused(self):
        raw = self.git_zip([(bundle.PILOT + "/one.py", b"one", 0o100644),
                           (bundle.PILOT + "/ONE.py", b"two", 0o100644)])
        with patch.object(profiles.subprocess, "check_output", side_effect=["b" * 40, raw]):
            with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_SYMLINK"):
                profiles.git_members(Path("."), "prefix/", "b" * 40)

    def test_git_symlink_source_refused(self):
        raw = self.git_zip([(bundle.PILOT + "/one.py", b"elsewhere", stat.S_IFLNK | 0o777)])
        with patch.object(profiles.subprocess, "check_output", side_effect=["b" * 40, raw]):
            with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_SYMLINK"):
                profiles.git_members(Path("."), "prefix/", "b" * 40)

    def test_git_expanded_ceiling_checked_before_member_read(self):
        raw = self.git_zip([(bundle.PILOT + "/one.py", b"longer than one byte", 0o100644)])
        with patch.object(profiles.subprocess, "check_output", side_effect=["b" * 40, raw]), \
             patch.object(profiles, "EXPANDED_LIMIT", 1):
            with self.assertRaisesRegex(ValueError, "EXPANDED_SIZE_CEILING"):
                profiles.git_members(Path("."), "prefix/", "b" * 40)

    def test_build_default_is_only_learning_v3(self):
        self.assertEqual(bundle.build.__kwdefaults__, {"experiment_profile": "learning_v3"})
        self.assertEqual(profiles.PROFILE_NAMES, ("learning_v3",))

    def test_build_refuses_existing_output_without_git_or_neural_work(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("CAS_META2_PURE_TEST_TMP")) as tmp:
            root = Path(tmp)
            target = root / "already.zip"
            target.write_bytes(b"preserve")
            with patch.object(bundle, "ROOT", root), \
                 patch.object(bundle.subprocess, "check_output", side_effect=AssertionError("GIT_REACHED")):
                with self.assertRaisesRegex(ValueError, "NEW_OUTPUT"):
                    bundle.build(target)
            self.assertEqual(target.read_bytes(), b"preserve")

    def test_builder_cli_helper_check_precedes_profile_import(self):
        source = (Path(bundle.__file__)).read_text()
        self.assertLess(source.index("    verify_cli_helpers_before_import()"),
                        source.index("_PROFILE_SPEC.loader.exec_module"))

    def test_committed_fixture_build_is_complete_deterministic_and_read_back(self):
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory(dir=os.environ.get("CAS_META2_PURE_TEST_TMP")) as tmp:
            repo = Path(tmp)
            root = repo / bundle.PILOT
            for name, raw in self.members.items():
                path = repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            def git(argv, **kwargs):
                if argv[1:3] == ["rev-parse", "--show-toplevel"]:
                    return str(repo)
                if argv[1:3] == ["rev-parse", "HEAD"]:
                    return "b" * 40
                return ""  # No dirty or untracked source in this synthetic commit.
            with ExitStack() as stack:
                stack.enter_context(patch.object(bundle, "ROOT", root))
                stack.enter_context(patch.object(bundle, "__file__", str(root / "tools/build_launch_bundle_v3.py")))
                stack.enter_context(patch.object(bundle, "_PROFILE_IMPORT_SHA256",
                    sha256(self.members[bundle.PILOT + "/tools/experiment_profiles_v3.py"]).hexdigest()))
                stack.enter_context(patch.object(bundle, "BASELINE_MANIFEST_SHA256",
                    sha256(self.members[bundle.META1 + "/BASELINE_MANIFEST.json"]).hexdigest()))
                stack.enter_context(patch.object(bundle.subprocess, "check_output", side_effect=git))
                stack.enter_context(patch.object(bundle.profiles, "git_members", side_effect=lambda *a: dict(self.members)))
                first = bundle.build(root / "first.zip")
                second = bundle.build(root / "second.zip")
                self.assertEqual(first["archive_sha256"], second["archive_sha256"])
                self.assertEqual(first["launch_manifest"]["files_sha256"], fixture_manifest(self.members)["files_sha256"])
                with zipfile.ZipFile(first["archive"]) as archive:
                    self.assertEqual(set(archive.namelist()), set(self.members) | {"launch_manifest.json"})
                    self.assertIsNone(archive.testzip())
                (root / "tools/experiment_profiles_v3.py").write_bytes(b"uncommitted change")
                with self.assertRaisesRegex(ValueError, "BUNDLE_HELPER_NOT_COMMITTED_BYTES"):
                    bundle.build(root / "rejected.zip")
                self.assertFalse((root / "rejected.zip").exists())
