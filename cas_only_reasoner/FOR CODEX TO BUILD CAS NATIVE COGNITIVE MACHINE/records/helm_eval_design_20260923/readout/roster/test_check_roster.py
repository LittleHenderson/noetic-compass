#!/usr/bin/env python3
"""Acceptance tests for check_roster.py (readout plan item 2). Pure Python, no torch, seconds.

Acceptance (as stated in the build order):
  1. On the committed switch-ON smoke receipt (read-only) it reports pass_01 and final present and the
     four evidence files absent, as expected for a reduced run.
  2. On a synthetic full receipt it passes.
  3. A flipped byte fails by name.
  4. A missing file fails by name.
Also covered: a sidecar update count that is off, a worker update total that is off, and the
unchanged arm's own 48-name list.

Synthetic receipts are built in the system temp folder, outside every git tree, and deleted after.
The smoke receipt path can be overridden with the environment variable ROSTER_SMOKE_RECEIPT.
Run (on this laptop from C:\\):  python -B "<abs path>\\test_check_roster.py" -v
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_roster as cr  # noqa: E402

SMOKE_RECEIPT = os.environ.get("ROSTER_SMOKE_RECEIPT") or (
    "C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
    "_worktrees/helm-on-launch-20260924/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
    "records/typed_pointer_001/receipt_analogy_on_smoke_20260917")
# From the smoke receipt's collected_inventory.json (commit 1ddf6a1e).
SMOKE_PASS_01_SHA = "46bbfbf40d4989fd5b4abc8b12229d7662b467ffa8c0e484bb33053a5fea272b"
SMOKE_FINAL_SHA = "5b896bec3d0be48367aeda9cb9b0a5319e9517c78d5b0f4c62601bf34cbf9725"
EVIDENCE_LABELS = ("main_checkpoint_0294", "main_checkpoint_0588", "main_checkpoint_0882", "main_checkpoint_1176")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def build_full_receipt(folder, arm="repaired", mutate=None, reduced_record=True):
    """A synthetic registered-schedule receipt with the six roster checkpoints and a worker report."""
    root = Path(folder)
    collected = root / "collected"
    names = list(cr.EXPECTED_LEARNABLE[arm])
    run_digest = "ab" * 32
    blobs, sidecars = {}, {}
    for label, kind, pt, side, updates in cr.ROSTER:
        blob = ("synthetic checkpoint %s at %d updates\n" % (label, updates)).encode("utf-8") + bytes(range(256))
        blobs[pt] = blob
        pin = {"bytes": len(blob), "sha256": _sha(blob), "path": "/opt/cas-graph6curr/package/" + pt,
               "run_identity_digest": run_digest,
               "metadata": {"cursor": updates, "model_revision": updates,
                            "counters": {"optimizer_updates": updates}, "learnable_names": names}}
        sidecars[side] = ({"schema": cr.PARTIAL_SIDECAR_SCHEMA, "completed_main_updates": updates,
                           "main_course_complete": False, "checkpoint": pin, "boundary": "synthetic"}
                          if kind == "evidence" else pin)
    worker = {
        "schedule_plan_mode": "REGISTERED", "completed_main_updates": 1470, "main_updates": 1470,
        "global_updates": 1488,
        "pass_summaries": [{"pass": number, "cursor_end": 147 * number} for number in range(1, 11)],
        "global_actual_work": {
            "expected_updates": 1488, "totals": {"optimizer_updates": 1488, "backward_calls": 1488},
            "phases": [{"phase": "course_p00", "delta": {"optimizer_updates": 0}},
                       {"phase": "main_training", "delta": {"optimizer_updates": 1470}},
                       {"phase": "interference_training", "delta": {"optimizer_updates": 16}},
                       {"phase": "replay_1", "delta": {"optimizer_updates": 1}},
                       {"phase": "replay_2", "delta": {"optimizer_updates": 1}}]},
    }
    if mutate is not None:
        mutate(sidecars, worker)
    payloads = dict(blobs)
    payloads.update({side: json.dumps(body, sort_keys=True).encode("utf-8") for side, body in sidecars.items()})
    payloads[cr.WORKER_REPORT] = json.dumps(worker, sort_keys=True).encode("utf-8")
    for relative, data in payloads.items():
        path = collected / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    inventory = {"schema": "cas.run-evidence-inventory/1", "job": "synthetic-%s-job" % arm, "prefix": "",
                 "failures": [], "file_count": len(payloads),
                 "files": [{"relative_path": relative, "key": relative, "bytes": len(data), "sha256": _sha(data)}
                           for relative, data in sorted(payloads.items())]}
    (root / cr.INVENTORY).write_bytes(json.dumps(inventory, sort_keys=True).encode("utf-8"))
    if reduced_record:  # R17 carries this record with a null schedule; Helm 2.0 receipts do not carry it.
        (root / cr.REDUCED_RECORD).write_bytes(json.dumps({"reduced_schedule": None}).encode("utf-8"))
    return root


def _run_main(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cr.main(argv)
    return code, out.getvalue()


class SmokeReceipt(unittest.TestCase):
    """Acceptance 1: the committed switch-ON smoke receipt, read-only."""

    def setUp(self):
        if not Path(SMOKE_RECEIPT).is_dir():
            self.skipTest("smoke receipt not on this machine: %s" % SMOKE_RECEIPT)

    def test_reduced_run_pass01_and_final_present_evidence_absent(self):
        report = cr.check_receipt(SMOKE_RECEIPT, "repaired")
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["schedule_mode"], "REDUCED")
        self.assertEqual(report["verdict"], "ROSTER_REDUCED_RUN_CONSISTENT")
        rows = {row["label"]: row for row in report["rows"]}
        self.assertEqual(sorted(rows), sorted(label for label, *_ in cr.ROSTER))
        for label, sha in (("pass_01", SMOKE_PASS_01_SHA), ("final", SMOKE_FINAL_SHA)):
            self.assertEqual(rows[label]["status"], "OK")
            self.assertEqual(rows[label]["sha256"], sha)
            self.assertEqual(rows[label]["expected_updates"], 8)
            self.assertEqual(set(rows[label]["updates"].values()), {8})
            self.assertEqual(rows[label]["learnable_names"], 53)
        for label in EVIDENCE_LABELS:
            self.assertEqual(rows[label]["status"], "ABSENT_EXPECTED_REDUCED_RUN")
        # Reduced plan: 8 main + 0 interference + 2 replay = 10.
        self.assertEqual(report["update_totals"]["got"]["global_updates"], 10)
        code, text = _run_main(["--arm", "repaired", SMOKE_RECEIPT])
        self.assertEqual(code, 3)
        self.assertIn("ROSTER_VERDICT: ROSTER_REDUCED_RUN_CONSISTENT", text)


class SyntheticReceipts(unittest.TestCase):

    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix="roster_test_")
        self.folder = Path(self._temp.name) / "receipt"
        self.folder.mkdir()

    def tearDown(self):
        self._temp.cleanup()

    def test_full_repaired_receipt_passes(self):
        """Acceptance 2."""
        build_full_receipt(self.folder)
        report = cr.check_receipt(self.folder, "repaired")
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["verdict"], "ROSTER_COMPLETE")
        self.assertEqual([row["expected_updates"] for row in report["rows"]], [147, 294, 588, 882, 1176, 1470])
        self.assertTrue(all(row["status"] == "OK" and row["learnable_names"] == 53 for row in report["rows"]))
        self.assertEqual(report["update_totals"]["got"]["global_updates"], 1488)
        code, text = _run_main(["--arm", "repaired", str(self.folder)])
        self.assertEqual(code, 0)
        self.assertIn("ROSTER_VERDICT: ROSTER_COMPLETE", text)

    def test_flipped_byte_fails_by_name(self):
        """Acceptance 3."""
        build_full_receipt(self.folder)
        target = self.folder / "collected" / "results/evidence/main_checkpoint_0588.pt"
        data = bytearray(target.read_bytes())
        data[40] ^= 0x01
        target.write_bytes(bytes(data))
        report = cr.check_receipt(self.folder, "repaired")
        self.assertEqual(report["problems"], ["results/evidence/main_checkpoint_0588.pt=SHA256_MISMATCH"])
        self.assertEqual(report["verdict"], "ROSTER_PROBLEM")
        code, text = _run_main(["--arm", "repaired", str(self.folder)])
        self.assertEqual(code, 1)
        self.assertIn("PROBLEM results/evidence/main_checkpoint_0588.pt=SHA256_MISMATCH", text)

    def test_missing_file_fails_by_name(self):
        """Acceptance 4: final.pt deleted after collection; and an evidence file never collected at all."""
        build_full_receipt(self.folder)
        (self.folder / "collected" / "results/artifacts/final.pt").unlink()
        report = cr.check_receipt(self.folder, "repaired")
        self.assertEqual(report["problems"], ["results/artifacts/final.pt=MISSING"])
        self.assertEqual(report["verdict"], "ROSTER_PROBLEM")
        self.assertEqual(_run_main(["--arm", "repaired", str(self.folder)])[0], 1)

        other = Path(self._temp.name) / "never_collected"
        other.mkdir()
        build_full_receipt(other)
        gone = "results/evidence/main_checkpoint_1176.pt"
        (other / "collected" / gone).unlink()
        inventory = json.loads((other / cr.INVENTORY).read_text(encoding="utf-8"))
        inventory["files"] = [entry for entry in inventory["files"] if entry["relative_path"] != gone]
        (other / cr.INVENTORY).write_text(json.dumps(inventory), encoding="utf-8")
        report = cr.check_receipt(other, "repaired")
        self.assertEqual(sorted(report["problems"]), sorted([gone + "=NOT_IN_INVENTORY", gone + "=MISSING",
                                                             "results/evidence/main_checkpoint_1176.json="
                                                             "SIDECAR_PIN_DIFFERS_FROM_INVENTORY"]))

    def test_sidecar_update_count_off_fails_by_name(self):
        def mutate(sidecars, worker):
            sidecars["results/evidence/main_checkpoint_0882.json"]["completed_main_updates"] = 881
        build_full_receipt(self.folder, mutate=mutate)
        report = cr.check_receipt(self.folder, "repaired")
        self.assertEqual(report["problems"], ["results/evidence/main_checkpoint_0882.json=UPDATE_COUNT_MISMATCH"])

    def test_worker_update_total_off_fails_by_name(self):
        def mutate(sidecars, worker):
            worker["global_updates"] = 1487
        build_full_receipt(self.folder, mutate=mutate)
        report = cr.check_receipt(self.folder, "repaired")
        self.assertEqual(report["problems"], ["results/artifacts/worker_report.json=UPDATE_TOTAL_MISMATCH"])
        self.assertIn("global_updates: expected 1488, got 1487", report["problem_details"][0]["detail"])

    def test_unchanged_arm_uses_its_own_48_name_list(self):
        build_full_receipt(self.folder, arm="unchanged", reduced_record=False)
        report = cr.check_receipt(self.folder, "unchanged")
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["verdict"], "ROSTER_COMPLETE")
        self.assertTrue(all(row["learnable_names"] == 48 for row in report["rows"]))
        wrong_arm = cr.check_receipt(self.folder, "repaired")
        self.assertEqual(wrong_arm["problems"], [side + "=LEARNABLE_NAMES_MISMATCH" for *_x, side, _n in cr.ROSTER])

    def test_name_lists(self):
        self.assertEqual(len(cr.REPAIRED_53), 53)
        self.assertEqual(len(cr.UNCHANGED_48), 48)
        self.assertEqual([n for n in cr.REPAIRED_53 if not n.startswith("analogy_head.")], list(cr.UNCHANGED_48))


if __name__ == "__main__":
    unittest.main()
