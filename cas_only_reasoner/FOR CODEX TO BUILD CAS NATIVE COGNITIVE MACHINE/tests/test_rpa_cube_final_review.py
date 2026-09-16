"""Independent review of the final cube bridge's source and paging boundaries."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from tests.test_rpa_cube_adversarial import (bridge, BASE, document, lesson,
                                              ContractError, deny_forbidden_imports)
from cncm.canonical import digest

class FinalBoundaryReview(unittest.TestCase):
    def test_parser_duplicate_keys_are_rejected_before_schema_or_digest(self):
        with self.assertRaisesRegex(ContractError, "duplicate JSON key"):
            bridge._source_decode(b'{"x": 1, "\\u0078": 2}')

    def test_parser_nonfinite_literals_and_overflow_are_rejected(self):
        for raw in (b'{"x": NaN}', b'{"x": Infinity}', b'{"x": -Infinity}', b'{"x": 1e999}'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ContractError, "nonfinite"):
                bridge._source_decode(raw)

    def test_source_byte_and_canonical_identity_differ_by_whitespace(self):
        doc = document(BASE)
        receipt = doc._receipts[0]
        data = receipt.source_bytes + b"\n"
        alternate = bridge.cube_source_receipt(data,
            expected_file_sha256=sha256(data).hexdigest(),
            expected_bundle_digest=receipt.canonical_bundle_digest,
            source_namespace=receipt.source_namespace,
            observation_id=receipt.observation_id, observation_time=receipt.observation_time,
            record_version=receipt.record_version)
        self.assertEqual(alternate.canonical_bundle_digest, receipt.canonical_bundle_digest)
        self.assertNotEqual(alternate.source_file_sha256, receipt.source_file_sha256)
        with self.assertRaisesRegex(ContractError, "mismatch"):
            bridge.cube_source_receipt(data,
                expected_file_sha256=receipt.source_file_sha256,
                expected_bundle_digest=receipt.canonical_bundle_digest,
                source_namespace=receipt.source_namespace,
                observation_id=receipt.observation_id, observation_time=receipt.observation_time,
                record_version=receipt.record_version)

    def test_teacher_agreement_is_only_self_contained_consistency(self):
        # This is an explicit trust limitation, not proof of a source-grounded answer.
        forged = lesson(BASE)
        wrong_index = (forged["teacher_sidecar"]["encoded_correct_index"] + 1) % 3
        forged["teacher_sidecar"]["expected_answer"] = deepcopy(forged["learner_input"]["encoded_options"][wrong_index])
        forged["teacher_sidecar"]["encoded_correct_index"] = wrong_index
        forged["binding"]["teacher_sidecar_digest"] = digest(forged["teacher_sidecar"])
        result = bridge.check_teacher_target(forged, forged["teacher_sidecar"]["expected_answer"])
        self.assertTrue(result["agrees"])
        self.assertEqual(result["scope"], "SUPPLIED_EXPORT_LOCAL_CONSISTENCY_ONLY")
        self.assertIs(result["source_reconstructed"], False)
        self.assertIs(result["source_authenticity_established"], False)

    def test_catalog_revision_bool_cannot_impersonate_source_integer(self):
        doc = document(BASE)
        wire = doc.to_dict()
        wire["catalog"]["bundle"]["cube_nodes"][0]["revision"] = True
        with self.assertRaises(ContractError):
            bridge.load_cube_atlas_document(wire, source_receipts=doc._receipts)

    def test_catalog_path_float_cannot_impersonate_source_integer(self):
        doc = document(BASE)
        wire = doc.to_dict()
        first = next(iter(wire["catalog"]["cube_index"].values()))
        first["source_path"][1] = float(first["source_path"][1])
        with self.assertRaises(ContractError):
            bridge.load_cube_atlas_document(wire, source_receipts=doc._receipts)

    def test_wire_provenance_booleans_cannot_be_numeric(self):
        doc = document(BASE)
        wire = doc.to_dict()
        wire["source_receipt"]["authorship_authenticated"] = 0
        with self.assertRaises(ContractError):
            bridge.load_cube_atlas_document(wire, source_receipts=doc._receipts)

    def test_catalog_cursor_rejects_different_source_even_when_resealed(self):
        doc = document(BASE)
        cursor = bridge.catalog_page(doc, limit=2)["next_cursor"]
        changed = deepcopy(BASE)
        changed["cube_nodes"][0]["revision"] = 2
        other = document(changed)
        # Honest recomputation of cursor hash cannot preserve a changed catalog anchor.
        body = {key: value for key, value in cursor.items() if key != "cursor_digest"}
        cursor["cursor_digest"] = digest(body)
        with self.assertRaises(ContractError):
            bridge.catalog_page(other, limit=2, cursor=cursor)

    def test_catalog_cursor_limit_has_strict_integer_type_even_when_resealed(self):
        doc = document(BASE)
        original = bridge.catalog_page(doc, limit=1)["next_cursor"]
        for alias in (True, 1.0):
            cursor = deepcopy(original)
            cursor["limit"] = alias
            cursor["cursor_digest"] = digest({key: value for key, value in cursor.items() if key != "cursor_digest"})
            with self.subTest(alias=alias, type=type(alias).__name__), self.assertRaises(ContractError):
                bridge.catalog_page(doc, limit=1, cursor=cursor)

    def test_teacher_agreement_requires_matching_record_identity(self):
        first = lesson(BASE, question={"idea": "Bicycle"})
        second = lesson(BASE, question={"idea": "Cart"})
        mixed = {"learner_input": first["learner_input"],
                 "teacher_sidecar": second["teacher_sidecar"],
                 "binding": {**second["binding"], "public_input_digest": first["binding"]["public_input_digest"]}}
        # All copied fields/digests are from real accepted exports. The link is wrong.
        self.assertNotEqual(mixed["learner_input"]["record_id"], mixed["teacher_sidecar"]["record_id"])
        with self.assertRaises(ContractError):
            bridge.check_teacher_target(mixed, second["teacher_sidecar"]["expected_answer"])

    def test_teacher_agreement_requires_answer_index_coherence(self):
        changed = lesson(BASE)
        wrong_index = (changed["teacher_sidecar"]["encoded_correct_index"] + 1) % 3
        changed["teacher_sidecar"]["expected_answer"] = deepcopy(changed["learner_input"]["encoded_options"][wrong_index])
        changed["binding"]["teacher_sidecar_digest"] = digest(changed["teacher_sidecar"])
        with self.assertRaises(ContractError):
            bridge.check_teacher_target(changed, changed["teacher_sidecar"]["expected_answer"])

    def test_pages_each_resolve_to_exact_bound_source_record(self):
        doc = document(BASE)
        page = bridge.catalog_page(doc, limit=2)
        seen = []
        while True:
            for row in page["rows"]:
                self.assertEqual(row["record_digest"], digest(row["cube"]))
                self.assertEqual(row["cube"], BASE["cube_nodes"][row["source_path"][1]])
                seen.append(row["catalog_key"])
            if page["next_cursor"] is None:
                break
            page = bridge.catalog_page(doc, limit=2, cursor=page["next_cursor"])
        self.assertEqual(seen, sorted(doc.catalog["cube_index"]))

if __name__ == "__main__":
    source_file = Path(bridge.__file__)
    before = sha256(source_file.read_bytes()).hexdigest()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FinalBoundaryReview))
    after = sha256(source_file.read_bytes()).hexdigest()
    print(json.dumps({"adapter_sha256_before": before, "adapter_sha256_after": after,
        "source_unchanged": before == after, "tests": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "neural_calls": 0, "provider_calls": 0}))
    raise SystemExit(0 if result.wasSuccessful() and before == after else 1)
