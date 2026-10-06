from __future__ import annotations

import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = (
    REPO_ROOT
    / "docs"
    / "working"
    / "project_coherence"
    / "gate1"
    / "tks_v8"
    / "TKS_V8_CORE_PROTOTYPE_MANIFEST_v0.1.json"
)


class ManifestBoundaryTests(unittest.TestCase):
    def test_research_transfer_and_formalization_are_not_overclaimed(self) -> None:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(payload["admission_ring"], 4)
        self.assertEqual(payload["license_status"], "NOT LICENSED")
        formal = payload["formal_verification"]
        self.assertEqual(formal["status"], "PARTIAL / PRESENT")
        self.assertIn("LEAN_PROOF_MANIFEST", formal["manifest_ref"])
        self.assertTrue(any("Universal" in item for item in formal["open_scope"]))
        self.assertTrue(any("shortlex" in item for item in formal["open_scope"]))
        self.assertTrue(any("matrix" in item for item in formal["open_scope"]))
        self.assertEqual(payload["validation_snapshot"]["result"], "PASS")
        self.assertEqual(payload["validation_snapshot"]["tests_run"], 20)
        self.assertEqual(
            payload["validation_snapshot"]["bounded_exhaustive_cases"][
                "lift_functor_composition_pairs_through_size_three"
            ],
            1678,
        )
        self.assertFalse(payload["integration_boundary"]["active_cas_compiler_modified"])
        self.assertEqual(
            payload["integration_boundary"]["canonical_tks_v8_status"], "OPEN"
        )
        research = next(
            claim for claim in payload["claims"] if claim["kind"] == "RESEARCH_TRANSFER"
        )
        self.assertEqual(research["status"], "OPEN")
        self.assertEqual(research["admission_ring"], 4)
        self.assertEqual(research["license_status"], "NOT LICENSED")


if __name__ == "__main__":
    unittest.main()
