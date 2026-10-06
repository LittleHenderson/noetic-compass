"""The continuation-bundle checker: completeness, byte verification, exact comparison.

Preparation tooling for neural-learning plan v1 §2/§6. These tests use
synthetic byte files; no model, no torch, no inference. Passing them says the
tool is consistent, not that anything learned.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "helm_neural"))

import bundle_check as bc  # noqa: E402

PLAN = {"id": "helm-neural-plan", "version": "v1", "sha256": "0" * 64}
BINDING = {"source_revision": "abc123", "seed": 7, "operator_record": "op-1", "approval": "job-1"}


def make_bundle(root: Path, *, model: bytes = b"weights-v1", with_optimizer: bool = False) -> dict:
    files = {
        "model_state": ("endpoint.bin", model),
        "bound_identities": ("identities.json", b'{"decoder": "d1"}'),
        "constraint_rows": ("rows.json", b"[1,2,3]"),
        "parameter_reference": ("original.bin", b"weights-v0"),
        "cursor": ("cursor.json", b'{"accepted": 64, "refused": 0}'),
        "path_totals": ("path.json", b'{"cumulative": 3200000}'),
        "admission_identities": ("admission.json", b'{"matrices": ["left", "right", "merge"]}'),
    }
    members: dict = {}
    for name, (fname, data) in files.items():
        (root / fname).write_bytes(data)
        members[name] = fname
    if with_optimizer:
        (root / "opt.bin").write_bytes(b"adam-state")
        members["optimizer_state"] = "opt.bin"
    else:
        members["optimizer_state"] = (None, "no optimizer: pure direction updates (m_direction)")
    members["schedule_state"] = (None, "no schedule: fixed step")
    members["rng_state"] = (None, "no stochastic step: deterministic direction")
    manifest = bc.build_manifest(root, members, plan=PLAN, binding=BINDING)
    (root / "manifest.json").write_text(json.dumps(manifest))
    return manifest


class CompletenessTests(unittest.TestCase):
    def test_a_full_bundle_is_complete_and_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            m = make_bundle(Path(d))
            self.assertTrue(bc.complete(m).ok)
            self.assertTrue(bc.verify(m, Path(d)).ok)

    def test_a_missing_member_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            m = make_bundle(Path(d))
            del m["members"]["cursor"]
            r = bc.complete(m)
            self.assertFalse(r.ok)
            self.assertEqual([(f.member, f.kind) for f in r.findings], [("cursor", "missing")])

    def test_only_optimizer_schedule_and_rng_may_be_declared_absent_and_must_say_why(self):
        with tempfile.TemporaryDirectory() as d:
            m = make_bundle(Path(d))
            m["members"]["model_state"] = {"absent": "lost"}
            self.assertIn(("model_state", "undeclared"), [(f.member, f.kind) for f in bc.complete(m).findings])
            m = make_bundle(Path(d))
            m["members"]["rng_state"] = {"absent": ""}
            self.assertIn(("rng_state", "undeclared"), [(f.member, f.kind) for f in bc.complete(m).findings])

    def test_the_launch_binding_and_plan_version_are_required(self):
        with tempfile.TemporaryDirectory() as d:
            m = make_bundle(Path(d))
            m["binding"]["approval"] = ""
            m["plan"] = {"id": "x"}
            kinds = {(f.member, f.kind) for f in bc.complete(m).findings}
            self.assertIn(("binding.approval", "missing"), kinds)
            self.assertIn(("plan", "missing"), kinds)


class VerificationTests(unittest.TestCase):
    def test_a_changed_byte_is_a_mismatch_and_a_deleted_file_is_unreadable(self):
        with tempfile.TemporaryDirectory() as d:
            m = make_bundle(Path(d))
            (Path(d) / "endpoint.bin").write_bytes(b"weights-v1!")
            r = bc.verify(m, Path(d))
            self.assertEqual([(f.member, f.kind) for f in r.findings], [("model_state", "mismatch")])
            os.remove(Path(d) / "rows.json")
            kinds = {(f.member, f.kind) for f in bc.verify(m, Path(d)).findings}
            self.assertIn(("constraint_rows", "unreadable"), kinds)


class ComparisonTests(unittest.TestCase):
    def test_two_saves_of_the_same_state_are_exact_equal(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ma, mb = make_bundle(Path(a)), make_bundle(Path(b))
            self.assertTrue(bc.compare(ma, mb).ok)

    def test_a_continuation_that_diverges_is_named_member_by_member(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ma = make_bundle(Path(a), model=b"weights-128-reference")
            mb = make_bundle(Path(b), model=b"weights-128-after-restart", with_optimizer=True)
            r = bc.compare(ma, mb)
            self.assertFalse(r.ok)
            self.assertEqual(
                sorted((f.member, f.kind) for f in r.findings),
                [("model_state", "differs"), ("optimizer_state", "absent_vs_present")],
            )

    def test_the_command_line_reports_and_exits_as_documented(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            make_bundle(Path(a)); make_bundle(Path(b), model=b"other")
            tool = str(REPO / "scripts" / "helm_neural" / "bundle_check.py")
            ok = subprocess.run([sys.executable, "-I", tool, "verify", str(Path(a) / "manifest.json")], capture_output=True, text=True)
            self.assertEqual((ok.returncode, ok.stdout.strip()), (0, "ok"))
            diff = subprocess.run([sys.executable, "-I", tool, "--json", "compare", str(Path(a) / "manifest.json"), str(Path(b) / "manifest.json")], capture_output=True, text=True)
            self.assertEqual(diff.returncode, 2)
            self.assertEqual(json.loads(diff.stdout)["findings"][0]["member"], "model_state")
            bad = subprocess.run([sys.executable, "-I", tool, "complete", str(Path(a) / "endpoint.bin")], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 3)
            self.assertIn("E-BUNDLE-003", bad.stderr)


if __name__ == "__main__":
    unittest.main()
