"""Regression tests for the c53 class of failure (SPEC 7.106, 2026-10-21): a HELM test pinned the sha256 of runtime records that
carried an absolute path, so the pin held on the laptop and failed on the Linux host. These tests make that class fail HERE, before
any seal:

  A. every stored 64-hex pin in a test_helm_*.py file must live in a file that imports helm_test_pins (the one machine-neutral
     canonicalizer), and that file must not hash records with a bare json.dumps + sha256 of its own;
  B. the pinned fixture of test_helm_cas_address.py, in canonical form, carries no absolute path, no user name or home directory,
     no platform / OS / interpreter word;
  C. the pinned fixture's hash is invariant to the machine's folders: computed with two different session folders and from two
     different working directories, the hash is the same;
  D. the machine-neutral canonicalizer itself behaves as documented on Windows and POSIX path forms.
Runs on the laptop and on the host (it is a test_helm_*.py file in the HELM cut), with no network and no exam data.
"""
import importlib
import os
import re
import subprocess
import sys
import tempfile
import unittest

import helm_test_pins as P

HERE = os.path.dirname(os.path.abspath(__file__))
HEX64 = re.compile(r"[\"']([0-9a-f]{64})[\"']")


RECORD_HASH_RX = re.compile(r"sha256\(\s*(?:json\.dumps|_canon\(|canon\()|canon_sha256\(")


def _hashes_records(src: str) -> bool:
    """True when the file hashes RUNTIME RECORDS (json.dumps output or a canonicalizer's output); a sha256 of file bytes is not that."""
    return RECORD_HASH_RX.search(src) is not None


def _test_files():
    return sorted(f for f in os.listdir(HERE) if f.startswith("test_helm_") and f.endswith(".py"))


class A_EveryPinGoesThroughTheNeutralCanonicalizer(unittest.TestCase):
    def test_pinned_files_import_helm_test_pins_and_do_not_hash_records_themselves(self):
        for name in _test_files():
            if name == "test_helm_pin_hygiene.py":
                continue
            with open(os.path.join(HERE, name), encoding="utf-8") as fh:
                src = fh.read()
            pins = HEX64.findall(src)
            # file-content pins (sha256 of bytes read from disk) are machine-neutral by nature; record pins are the risk:
            # a sha256 taken over json.dumps output or over a canonicalizer's output
            hashes_records = _hashes_records(src)
            if pins and hashes_records:
                self.assertIn("import helm_test_pins", src, "%s pins a hash of runtime records: it must hash through helm_test_pins" % name)
                self.assertNotRegex(src, r"hashlib\.sha256\(\s*json\.dumps", "%s hashes json.dumps directly; use helm_test_pins.canon_sha256" % name)
            if pins and "helm_test_pins" in src:
                self.assertNotIn("hashlib.sha256(_canon(", src, "%s: the local _canon must delegate to helm_test_pins" % name)

    def test_registry_of_record_pins(self):
        """The record pins known today; a new one must be added here on purpose (and go through helm_test_pins)."""
        found = {}
        for name in _test_files():
            with open(os.path.join(HERE, name), encoding="utf-8") as fh:
                src = fh.read()
            if _hashes_records(src) and HEX64.search(src):
                found[name] = HEX64.findall(src)
        self.assertEqual(sorted(found), ["test_helm_cas_address.py"], "a new record pin appeared: register it here and route it through helm_test_pins: %r" % found)


class B_PinnedFixtureCarriesNoMachineMaterial(unittest.TestCase):
    def test_cas_address_fixture_is_machine_neutral(self):
        T = importlib.import_module("test_helm_cas_address")
        with T.switches(cas="0", units_note=None):
            off = T.fixture_records()
        text = P.canon(off)
        self.assertEqual(P.offending(text), [], "machine-bound material in the pinned fixture")
        # and the raw (pre-neutral) records do carry the absolute brain folder: the canonicalizer is what removes it
        raw = T.json.dumps(off, sort_keys=True, default=str)
        self.assertTrue(any(k in raw for k in ("brain_dir",)), "fixture shape changed; re-check what neutral() must cover")


class C_PinIsInvariantToTheMachineFolders(unittest.TestCase):
    CODE = ("import json, test_helm_cas_address as T\n"
            "with T.switches(cas='0', units_note=None):\n"
            "    print(T.fixture_sha256(T.fixture_records()))\n")

    def _pin(self, cwd, env):
        out = subprocess.run([sys.executable, "-X", "utf8", "-B", "-c", self.CODE], cwd=cwd, env=env, capture_output=True, text=True, timeout=600)
        self.assertEqual(out.returncode, 0, out.stderr[-1500:])
        sha = out.stdout.strip().splitlines()[-1]
        self.assertRegex(sha, r"^[0-9a-f]{64}$")
        return sha

    def test_same_hash_when_the_licensed_brain_folder_moves_and_is_renamed(self):
        """The c53 failure, reproduced and refused: the brain folder under the HOST's name and parent (.../sources/w1/HELM_R1_W1_20261015)
        must give the same pin as the laptop's default folder (.../HELM_R1_W1_20261015_v3). This covers brain_dir AND the receipt hashes
        the loop computes over it."""
        import shutil
        import helm_brain_canonical as HBC
        default_dir = os.environ.get(HBC.BRAIN_DIR_ENV) or HBC.DEFAULT_BRAIN_DIR
        self.assertTrue(os.path.isdir(default_dir), default_dir)
        with tempfile.TemporaryDirectory() as td:
            moved = os.path.join(td, "sources", "w1", "HELM_R1_W1_20261015")      # the host's layout and name
            shutil.copytree(default_dir, moved)
            base_env = dict(os.environ, PYTHONPATH=HERE, PYTHONDONTWRITEBYTECODE="1")
            a = self._pin(HERE, dict(base_env, HELM_SESSION_DIR=os.path.join(td, "s_default"), HELM_CANONICAL_BRAIN_DIR=default_dir))
            b = self._pin(td, dict(base_env, HELM_SESSION_DIR=os.path.join(td, "s_moved"), HELM_CANONICAL_BRAIN_DIR=moved))
        self.assertEqual(a, b, "the pinned hash depends on the licensed brain folder's path or name (the c53 failure)")

    def test_same_hash_from_two_session_dirs_and_two_cwds(self):
        code = ("import json, test_helm_cas_address as T\n"
                "with T.switches(cas='0', units_note=None):\n"
                "    print(T.fixture_sha256(T.fixture_records()))\n")
        shas = []
        for i in range(2):
            with tempfile.TemporaryDirectory() as td:
                env = dict(os.environ, HELM_SESSION_DIR=os.path.join(td, "sessions%d" % i), PYTHONPATH=HERE, PYTHONDONTWRITEBYTECODE="1")
                cwd = HERE if i == 0 else td
                out = subprocess.run([sys.executable, "-X", "utf8", "-B", "-c", code], cwd=cwd, env=env, capture_output=True, text=True, timeout=600)
                self.assertEqual(out.returncode, 0, out.stderr[-1500:])
                shas.append(out.stdout.strip().splitlines()[-1])
        self.assertEqual(shas[0], shas[1], "the pinned hash depends on the machine's folders")
        self.assertRegex(shas[0], r"^[0-9a-f]{64}$")


class D_TheCanonicalizerItself(unittest.TestCase):
    def test_windows_and_posix_paths_neutralize_alike(self):
        a = {"trace": [{"brain": {"brain_dir": r"C:\Users\someone\Documents\Codex\2026-10-15\r1_wave1\HELM_R1_W1_20261015_v3"}}]}
        b = {"trace": [{"brain": {"brain_dir": "/opt/helm-shared-r2/sources/w1/HELM_R1_W1_20261015_v3"}}]}
        self.assertEqual(P.canon(a), P.canon(b))
        self.assertEqual(P.neutral(a)["trace"][0]["brain"]["brain_dir"], "<stripped:brain_dir>")
        self.assertEqual(P.neutral({"f": r"C:\Users\x\y\HELM_R1_W1_20261015_v3"})["f"], "<path>/HELM_R1_W1_20261015_v3")

    def test_machine_bound_leaves_are_stripped(self):
        obj = {"trace": [{"brain": {"brain_dir": "/opt/x/HELM_R1_W1_20261015", "version": "v3"}, "receipt_hash": "83dffbdaa2cd2c52"}],
               "results": [{"receipt_hash": "5d3e5e22888cb84c", "loop_status": "ok"}]}
        n = P.neutral(obj)
        self.assertEqual(n["trace"][0]["brain"]["brain_dir"], "<stripped:brain_dir>")
        self.assertEqual(n["trace"][0]["receipt_hash"], "<stripped:receipt_hash>")
        self.assertEqual(n["results"][0]["receipt_hash"], "<stripped:receipt_hash>")
        self.assertEqual(n["results"][0]["loop_status"], "ok")
        self.assertEqual(n["trace"][0]["brain"]["version"], "v3")

    def test_relative_names_and_plain_text_are_untouched(self):
        for s in ("rb/brain.py", "Topic: Ω_Bread.", "We have 2 or 3 cups sugar.", "flour", "", "3/4"):
            self.assertEqual(P.neutral(s), s)

    def test_offending_finds_machine_words_and_home(self):
        self.assertIn("win32", P.offending('{"a":"win32"}'))
        self.assertEqual(P.offending('{"a":"<path>/HELM_R1_W1_20261015_v3","b":"rb/brain.py"}'), [])
        home = os.path.expanduser("~").replace("\\", "\\\\")
        self.assertTrue(P.offending('{"a":"%s\\\\x"}' % home))


if __name__ == "__main__":
    unittest.main()
