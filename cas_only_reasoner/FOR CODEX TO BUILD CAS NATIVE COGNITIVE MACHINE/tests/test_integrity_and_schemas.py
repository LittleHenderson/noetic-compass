from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from cncm.canonical import canonical_json
from cncm.engine import CognitiveMachine, replay
from cncm.model import ProblemPacket
from cncm.verification import validate_problem, verify_bundle

from tests._support import ROOT, SCHEMAS, fixture_document, fixture_packet


def walk_refs(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref":
                yield child
            yield from walk_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_refs(child)


def resolve_pointer(document, fragment: str):
    if fragment in ("", "#"):
        return document
    if not fragment.startswith("#/"):
        raise AssertionError(f"unsupported JSON pointer fragment: {fragment}")
    current = document
    for raw in fragment[2:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        else:
            current = current[token]
    return current


class IntegrityAndSchemaTests(unittest.TestCase):
    def test_authority_manifest_binds_homebase_source_and_phase_zero_artifacts(self) -> None:
        manifest = json.loads((ROOT / "AUTHORITY_MANIFEST.yaml").read_text(encoding="utf-8"))
        snapshot = manifest["authority_source_snapshot"]
        source_path = (ROOT / snapshot["path"]).resolve()
        self.assertEqual(source_path, (ROOT / "cas_reasoner.txt").resolve())
        source_bytes = source_path.read_bytes()
        self.assertEqual(snapshot["bytes"], len(source_bytes))
        self.assertEqual(snapshot["lines"], source_bytes.count(b"\n"))
        self.assertEqual(snapshot["sha256"], sha256(source_bytes).hexdigest())

        expected = {
            "AUTHORITY_MANIFEST.yaml",
            "spec/CAS_CORE_ONTOLOGY_v0.1.md",
            "spec/FOUNDATION_DRIVE_ADAPTER_v0.1.md",
            "spec/COMPILER_RUNTIME_BOUNDARY_v0.1.md",
            "spec/CAS_KERNEL_IR_v0.1.md",
            "spec/NON_GOALS_v0.1.md",
            "spec/CONFORMANCE_PLAN_v0.1.md",
        }
        phase_zero = manifest["phase_0_contracts"]
        self.assertEqual(set(phase_zero["required_artifacts"]), expected)
        self.assertTrue(phase_zero["artifact_set_present"])
        self.assertEqual(phase_zero["exit_gate"], "OPEN")
        for relative in expected:
            with self.subTest(artifact=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_exact_replay_reproduces_state_trace_and_evidence(self) -> None:
        packet = fixture_packet("transitive_reasoning")
        first = CognitiveMachine().run(packet)
        second = CognitiveMachine().run(packet)
        self.assertEqual(canonical_json(first.to_dict()), canonical_json(second.to_dict()))
        self.assertTrue(replay(packet, first))

    def test_trace_chain_and_evidence_bundle_verify(self) -> None:
        result = CognitiveMachine().run(fixture_packet("deduction"))
        report = verify_bundle(result.to_dict())
        self.assertTrue(report.valid, report.errors)
        previous_hash = ""
        previous_event_id = None
        for event in result.trace:
            self.assertTrue(event.sealed)
            self.assertEqual(event.previous_event_hash, previous_hash)
            self.assertEqual(event.parent_event_id, previous_event_id)
            self.assertEqual(event.event_hash, event.computed_hash())
            previous_hash = event.event_hash
            previous_event_id = event.event_id
        self.assertEqual(result.final_state.trace_head, result.trace[-1].event_hash)

    def test_trace_state_and_evidence_tampering_are_detected(self) -> None:
        bundle = CognitiveMachine().run(fixture_packet("deduction")).to_dict()
        mutations = []

        bad_trace = copy.deepcopy(bundle)
        bad_trace["trace"][0]["scheduled_components"].append("tampered_component")
        mutations.append(("trace", bad_trace))

        bad_state = copy.deepcopy(bundle)
        bad_state["final_state"]["logical_tick"] += 1
        mutations.append(("state", bad_state))

        bad_evidence = copy.deepcopy(bundle)
        bad_evidence["evidence"]["diagnostics"].append("tampered")
        mutations.append(("evidence", bad_evidence))

        for label, tampered in mutations:
            with self.subTest(label=label):
                report = verify_bundle(tampered)
                self.assertFalse(report.valid)
                self.assertTrue(report.errors)

    def test_every_fixture_satisfies_runtime_problem_contract(self) -> None:
        fixture_paths = sorted((ROOT / "fixtures").glob("*/problem.json"))
        self.assertTrue(fixture_paths)
        for path in fixture_paths:
            with self.subTest(fixture=path.parent.name):
                document = json.loads(path.read_text(encoding="utf-8"))
                report = validate_problem(document)
                self.assertTrue(report.valid, report.errors)
                self.assertIsInstance(ProblemPacket.from_dict(document), ProblemPacket)

    def test_schema_documents_parse_and_all_refs_resolve_within_schema_root(self) -> None:
        expected = {
            "conjecture.schema.json",
            "apprenticeship_lineage.schema.json",
            "apprenticeship_qualification_receipt.schema.json",
            "dialogue_act.schema.json",
            "dialogue_state.schema.json",
            "dialogue_turn.schema.json",
            "grammar_construction.schema.json",
            "language_lesson_packet.schema.json",
            "language_promotion_receipt.schema.json",
            "language_qualification_receipt.schema.json",
            "machine_state.schema.json",
            "math_claim.schema.json",
            "math_counterexample.schema.json",
            "math_evidence_packet.schema.json",
            "math_expression.schema.json",
            "math_object.schema.json",
            "math_problem_packet.schema.json",
            "math_result.schema.json",
            "math_rule.schema.json",
            "math_statement.schema.json",
            "math_strategy.schema.json",
            "proposition.schema.json",
            "proof_step.schema.json",
            "referent.schema.json",
            "response_plan.schema.json",
            "rule.schema.json",
            "semantic_frame.schema.json",
            "semantic_packet.schema.json",
            "teacher_role_assignment.schema.json",
            "teaching_episode.schema.json",
            "intent.schema.json",
            "branch_frame.schema.json",
            "cas_ohm_stage_record.schema.json",
            "rpm_frame.schema.json",
            "trace_event.schema.json",
            "version_lineage.schema.json",
            "theorem.schema.json",
            "evidence_packet.schema.json",
            "problem_packet.schema.json",
        }
        paths = sorted(SCHEMAS.glob("*.schema.json"))
        self.assertEqual({path.name for path in paths}, expected)
        documents = {
            path.resolve(): json.loads(path.read_text(encoding="utf-8")) for path in paths
        }
        ids = []
        schema_root = SCHEMAS.resolve()
        for path, document in documents.items():
            with self.subTest(schema=path.name):
                self.assertEqual(
                    document.get("$schema"),
                    "https://json-schema.org/draft/2020-12/schema",
                )
                self.assertIsInstance(document.get("$id"), str)
                ids.append(document["$id"])
                for reference in walk_refs(document):
                    self.assertIsInstance(reference, str)
                    target_name, separator, fragment_text = reference.partition("#")
                    if target_name:
                        self.assertNotIn("://", target_name, "remote schema refs are prohibited")
                        target = (path.parent / target_name).resolve()
                    else:
                        target = path
                    self.assertEqual(target.parent, schema_root, "schema ref escaped schema root")
                    self.assertIn(target, documents, f"missing schema target: {target.name}")
                    fragment = f"#{fragment_text}" if separator else ""
                    resolve_pointer(documents[target], fragment)
        self.assertEqual(len(ids), len(set(ids)), "schema $id values must be unique")

    def test_cas_ohm_attention_contract_is_non_authoritative_and_not_integrated(self) -> None:
        manifest = json.loads((ROOT / "AUTHORITY_MANIFEST.yaml").read_text(encoding="utf-8"))
        contract = manifest["cas_ohm_attention_protocol"]
        self.assertEqual(
            contract["status"],
            "ADOPTED-DESIGN-DIRECTION / CONTRACT-ONLY / NOT-RUNTIME-INTEGRATED",
        )
        self.assertFalse(contract["current_runtime_reads_record"])
        self.assertFalse(contract["current_runtime_emits_record"])
        self.assertFalse(contract["current_scheduler_uses_cas_ohm"])
        self.assertEqual(
            contract["wire_version"],
            manifest["wire_versions"]["cas_ohm_stage_record_contract_only"],
        )

        schema = json.loads(
            (SCHEMAS / "cas_ohm_stage_record.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "cncm.cas-ohm-stage/0.1",
        )
        authority = schema["$defs"]["authorityBoundary"]["properties"]
        for field in (
            "truth_authority",
            "meaning_authority",
            "proof_authority",
            "validity_authority",
            "commitment_authority",
            "permission_authority",
            "memory_occurrence_authority",
            "memory_write_authority",
            "state_mutation_authority",
            "halt_authority",
            "causal_identification_authority",
            "external_action_authority",
            "self_modification_authority",
            "emits_cncm_intents",
        ):
            with self.subTest(field=field):
                self.assertIs(authority[field]["const"], False)

        self.assertEqual(
            schema["properties"]["substrate"]["enum"],
            ["NATIVE_COMPUTATIONAL", "NEURAL_MODEL"],
        )
        serialized_schema = canonical_json(schema)
        for required_contract in (
            '"splits_disjoint":{"const":true}',
            '"same_sample_reconstruction":{"const":false}',
            '"semanticOutcome"',
            '"sidecar_chain_digest"',
            '"policy_blocked"',
            '"verifier_passed"',
        ):
            with self.subTest(required_contract=required_contract):
                self.assertIn(required_contract, serialized_schema)

        prohibited = set(contract["prohibited_authorities"])
        self.assertTrue(
            {
                "permission",
                "memory occurrence",
                "state mutation",
                "halt",
                "causal identification",
            }.issubset(prohibited)
        )

        protocol = (
            ROOT / "spec" / "CAS_OHM_ATTENTION_INTEGRATION_PROTOCOL_v0.1.md"
        ).read_text(encoding="utf-8")
        self.assertIn("CAS-Ohm governs flow.", protocol)
        self.assertIn("The verifier governs validity.", protocol)
        self.assertIn("HUMAN_BIOLOGICAL", protocol)
        self.assertIn("AttentionAllocationPlan", protocol)
        self.assertIn("NOT INTEGRATED INTO CNCM-RRK RUNTIME 0.1.0", protocol)

    def test_project_source_has_no_reference_to_forbidden_sibling(self) -> None:
        forbidden_token = "CAS" + "_RRK_v0.1"
        source_paths = sorted((ROOT / "cncm").glob("*.py")) + [ROOT / "pyproject.toml"]
        self.assertTrue(source_paths)
        for path in source_paths:
            with self.subTest(source=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn(forbidden_token, source)
                self.assertNotIn("cas_only_reasoner/CAS" + "_RRK", source.replace("\\", "/"))

    def test_current_cncm_surfaces_have_no_cross_project_audit_tokens(self) -> None:
        paths = (
            sorted((ROOT / "cncm").glob("*.py"))
            + sorted((ROOT / "spec").glob("*.md"))
            + sorted((ROOT / "docs").glob("*.md"))
            + sorted((ROOT / "playground" / "app").glob("*.tsx"))
            + sorted((ROOT / "playground" / "lib").glob("*.ts"))
            + sorted((ROOT / "playground" / "scripts").glob("*.py"))
            + [ROOT / "AUTHORITY_MANIFEST.yaml", ROOT / "README_HANDOFF.md"]
        )
        forbidden = ("pythia", "91.72%", "95.625%", "cas-production-closure")
        for path in paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8").lower()
            for token in forbidden:
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
