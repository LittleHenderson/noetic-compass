from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import unittest

from cncm.math_api import find_math_counterexample
from cncm.math_engine import solve_linear_equation
from cncm.math_kernel import check_math_step
from cncm.math_model import (
    MathClaim,
    MathClaimStatus,
    MathStepOperation,
    MathStepProposal,
    Provenance,
)
from cncm.math_parser import parse_math_statement

from tests._support import ROOT


MATH_FIXTURES = ROOT / "fixtures" / "math"
MATH_GOLDENS = ROOT / "golden" / "math"


def encoded(value) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")


class MathFixtureTests(unittest.TestCase):
    def test_source_required_fixture_categories_are_present_and_honest(self) -> None:
        expected = {
            "arithmetic",
            "algebra",
            "transitive_relations",
            "contradiction",
            "counterexamples",
            "recursive_learning",
        }
        paths = sorted(MATH_FIXTURES.glob("*/case.json"))
        self.assertEqual({path.parent.name for path in paths}, expected)
        for path in paths:
            with self.subTest(category=path.parent.name):
                document = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(document["schema_version"], "cncm.math-fixture/0.1")
                if path.parent.name == "recursive_learning":
                    self.assertEqual(document["runtime_status"], "CONTRACT_ONLY")
                else:
                    self.assertEqual(document["runtime_status"], "EXECUTABLE")

    def test_executable_math_fixtures_match_exact_results(self) -> None:
        for path in sorted(MATH_FIXTURES.glob("*/case.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document["runtime_status"] != "EXECUTABLE":
                continue
            operation = document["operation"]
            with self.subTest(fixture=document["fixture_id"]):
                if operation == "solve_linear":
                    result = solve_linear_equation(
                        document["input"]["notation"],
                        document["input"]["variable"],
                    ).to_dict()
                    self.assertEqual(
                        result["terminal_status"],
                        document["expected"]["terminal_status"],
                    )
                    self.assertEqual(result["solution"], document["expected"]["solution"])
                    minimum = document["expected"].get("minimum_checked_steps", 0)
                    self.assertGreaterEqual(len(result["checked_steps"]), minimum)
                elif operation == "counterexample":
                    result = find_math_counterexample(
                        document["input"]["notation"],
                        document["input"]["bounds"],
                        max_assignments=document["input"]["max_assignments"],
                    ).to_dict()
                    self.assertEqual(result["status"], document["expected"]["status"])
                    self.assertEqual(result["assignment"], document["expected"]["assignment"])
                elif operation == "check_transitive_equal":
                    variables = tuple(document["input"]["variables"])
                    claims = tuple(
                        MathClaim.create(
                            statement=parse_math_statement(item, declared_variables=variables),
                            status=MathClaimStatus.GIVEN,
                            provenance=(Provenance("fixture", document["fixture_id"]),),
                        )
                        for item in document["input"]["premises"]
                    )
                    proposal = MathStepProposal.create(
                        operation=MathStepOperation.TRANSITIVE_EQUAL,
                        premise_claim_ids=(claims[0].claim_id, claims[1].claim_id),
                        proposed_conclusion=parse_math_statement(
                            document["input"]["conclusion"],
                            declared_variables=variables,
                        ),
                    )
                    self.assertEqual(
                        check_math_step(proposal, claims).accepted,
                        document["expected"]["accepted"],
                    )
                else:
                    self.fail(f"unsupported executable fixture operation: {operation}")

    def test_math_goldens_are_source_bound_and_contract_only_is_not_executed(self) -> None:
        manifest = json.loads(
            (ROOT / "golden" / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["schema_version"], "cncm.golden-manifest/0.2")
        self.assertEqual(len(manifest["entries"]), 8)
        self.assertEqual(len(manifest["math_entries"]), 6)
        source_sha = sha256((ROOT / "cas_reasoner.txt").read_bytes()).hexdigest()
        self.assertEqual(manifest["source_spec"]["sha256"], source_sha)

        entries = {entry["fixture"]: entry for entry in manifest["math_entries"]}
        self.assertEqual(entries.keys(), {
            "algebra",
            "arithmetic",
            "contradiction",
            "counterexamples",
            "recursive_learning",
            "transitive_relations",
        })
        for category, entry in entries.items():
            with self.subTest(category=category):
                case_path = MATH_FIXTURES / category / "case.json"
                case_bytes = case_path.read_bytes()
                case = json.loads(case_bytes)
                artifact_path = MATH_GOLDENS / f"{category}.json"
                artifact_bytes = artifact_path.read_bytes()
                artifact = json.loads(artifact_bytes)
                self.assertEqual(entry["case_sha256"], sha256(case_bytes).hexdigest())
                self.assertEqual(
                    entry["artifact_sha256"], sha256(artifact_bytes).hexdigest()
                )
                self.assertEqual(entry["source_spec_sha256"], source_sha)
                self.assertEqual(artifact["source_spec_sha256"], source_sha)
                self.assertEqual(artifact["fixture_definition"], case)
                self.assertEqual(entry["runtime_status"], case["runtime_status"])
                if category == "recursive_learning":
                    self.assertEqual(entry["runtime_status"], "CONTRACT_ONLY")
                    self.assertIsNone(entry["output_sha256"])
                    self.assertTrue(artifact["contract_only"])
                    self.assertNotIn("output", artifact)
                else:
                    self.assertEqual(entry["runtime_status"], "EXECUTABLE")
                    self.assertNotIn("contract_only", artifact)
                    self.assertEqual(
                        entry["output_sha256"],
                        sha256(encoded(artifact["output"])).hexdigest(),
                    )

    def test_browser_runtime_publishes_all_math_fixture_definitions(self) -> None:
        metadata = json.loads(
            (ROOT / "playground" / "public" / "runtime" / "runtime-meta.json")
            .read_text(encoding="utf-8")
        )
        records = {item["name"]: item for item in metadata["math_fixtures"]}
        self.assertEqual(len(records), 6)
        for category, record in records.items():
            with self.subTest(category=category):
                source = MATH_FIXTURES / category / "case.json"
                published = (
                    ROOT
                    / "playground"
                    / "public"
                    / "fixtures"
                    / "math"
                    / f"{category}.json"
                )
                source_bytes = source.read_bytes()
                self.assertEqual(published.read_bytes(), source_bytes)
                document = json.loads(source_bytes)
                self.assertEqual(record["fixture_id"], document["fixture_id"])
                self.assertEqual(record["operation"], document["operation"])
                self.assertEqual(record["runtime_status"], document["runtime_status"])
                self.assertEqual(record["sha256"], sha256(source_bytes).hexdigest())


if __name__ == "__main__":
    unittest.main()
