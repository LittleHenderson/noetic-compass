from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests._support import FIXTURES, ROOT


class CliTests(unittest.TestCase):
    def invoke(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "cncm", *arguments],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

    def test_check_accepts_valid_and_rejects_invalid_packet(self) -> None:
        valid_path = FIXTURES / "deduction" / "problem.json"
        valid = self.invoke("check", "--problem", str(valid_path))
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertTrue(json.loads(valid.stdout)["valid"])

        with tempfile.TemporaryDirectory() as temporary:
            invalid_path = Path(temporary) / "invalid.json"
            invalid_path.write_text("{}\n", encoding="utf-8")
            invalid = self.invoke("check", "--problem", str(invalid_path))
        self.assertEqual(invalid.returncode, 2)
        self.assertFalse(json.loads(invalid.stdout)["valid"])

    def test_run_replay_and_verify_happy_path(self) -> None:
        problem = FIXTURES / "deduction" / "problem.json"
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            trace = target / "trace.json"
            final_state = target / "final_state.json"
            evidence = target / "evidence.json"
            bundle = target / "bundle.json"
            run = self.invoke(
                "run",
                "--problem",
                str(problem),
                "--trace",
                str(trace),
                "--final-state",
                str(final_state),
                "--evidence",
                str(evidence),
                "--bundle",
                str(bundle),
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            summary = json.loads(run.stdout)
            self.assertEqual(summary["terminal_status"], "CONCLUDED")
            for artifact in (trace, final_state, evidence, bundle):
                self.assertTrue(artifact.is_file())
                json.loads(artifact.read_text(encoding="utf-8"))

            replay = self.invoke("replay", "--problem", str(problem), "--against", str(trace))
            self.assertEqual(replay.returncode, 0, replay.stderr)
            self.assertTrue(json.loads(replay.stdout)["matches"])

            verify = self.invoke("verify", "--bundle", str(bundle))
            self.assertEqual(verify.returncode, 0, verify.stderr)
            self.assertTrue(json.loads(verify.stdout)["valid"])

    def test_replay_and_verify_return_four_for_tampered_artifacts(self) -> None:
        problem = FIXTURES / "transitive_reasoning" / "problem.json"
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            trace = target / "trace.json"
            bundle = target / "bundle.json"
            run = self.invoke(
                "run",
                "--problem",
                str(problem),
                "--trace",
                str(trace),
                "--bundle",
                str(bundle),
            )
            self.assertEqual(run.returncode, 0, run.stderr)

            trace_document = json.loads(trace.read_text(encoding="utf-8"))
            trace_document[0]["scheduled_components"].append("tampered")
            trace.write_text(json.dumps(trace_document), encoding="utf-8")
            replay = self.invoke("replay", "--problem", str(problem), "--against", str(trace))
            self.assertEqual(replay.returncode, 4)
            self.assertFalse(json.loads(replay.stdout)["matches"])

            bundle_document = json.loads(bundle.read_text(encoding="utf-8"))
            bundle_document["evidence"]["diagnostics"].append("tampered")
            bundle.write_text(json.dumps(bundle_document), encoding="utf-8")
            verify = self.invoke("verify", "--bundle", str(bundle))
            self.assertEqual(verify.returncode, 4)
            self.assertFalse(json.loads(verify.stdout)["valid"])

    def test_golden_verifier_reports_valid_json(self) -> None:
        completed = subprocess.run(
            [sys.executable, "tools/verify_goldens.py"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertIs(report["valid"], True)


if __name__ == "__main__":
    unittest.main()
