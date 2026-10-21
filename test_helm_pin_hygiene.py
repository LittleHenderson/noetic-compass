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
        self.assertEqual(P.neutral(a)["trace"][0]["brain"]["brain_dir"], "<path>/HELM_R1_W1_20261015_v3")

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
