"""Independent pure-bridge source/input boundary regression probes."""
import sys
from pathlib import Path
import importlib.abc
import unittest
from copy import deepcopy
import hashlib
import json

class DenyForbidden(importlib.abc.MetaPathFinder):
    blocked = {"torch", "numpy", "boto3", "botocore", "requests", "cas_cjt"}
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in self.blocked or fullname.endswith(".learner"):
            raise AssertionError("forbidden import: " + fullname)
sys.meta_path.insert(0, DenyForbidden())
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from cncm import rpa_cube_adapter as bridge
from cncm.canonical import canonical_json
from cncm.model import ContractError
cube_node = bridge.cube_node
BASE = cube_node.load_bundle()

def document(bundle):
    data = canonical_json(bundle).encode("utf-8")
    identity = cube_node.bundle_digest(bundle)
    return bridge.cube_atlas_from_bytes(data, expected_file_sha256=hashlib.sha256(data).hexdigest(),
        expected_bundle_digest=identity, source_namespace="cube-adversarial-review",
        observation_id="review-001", observation_time="2026-09-16T18:00:00Z", record_version=1)

def lesson(bundle, operation="LIST_PARTS", question=None):
    if question is None:
        question = {"idea": "Bicycle"}
    return bridge.compile_atlas_lesson(document(bundle), bundle=bundle,
        expected_bundle_digest=cube_node.bundle_digest(bundle), operation=operation,
        question=question, assistance="unassisted")

class CubeBoundaryReview(unittest.TestCase):
    def test_no_private_answer_fields_in_views(self):
        foreign = deepcopy(BASE)
        foreign["views"][0]["correct"] = "teacher-only private answer"
        with self.assertRaises(ContractError):
            document(foreign)

    def test_no_private_answer_fields_in_context(self):
        foreign = deepcopy(BASE)
        foreign["context"]["expected_answer"] = "teacher-only private answer"
        with self.assertRaises(ContractError):
            document(foreign)

    def test_no_option_tag_truncation(self):
        mapping = {value: ("prefix_" + "x" * 290 + "_" + value) for value in cube_node.view_labels(BASE, "view_context").values()}
        foreign = cube_node.rename_bundle(BASE, mapping)
        try:
            result = lesson(foreign, question={"idea": mapping["Bicycle"]})
        except ContractError:
            return
        observations = result["learner_input"]["public"]["observations"]
        options = result["learner_input"]["encoded_options"]
        self.assertEqual([row["tag"] for row in observations], [str(value) for value in options],
                         "public option tags were silently truncated")

    def test_source_document_reseal_does_not_accept_foreign_catalog(self):
        doc = document(BASE)
        wire = doc.to_dict()
        wire["catalog"]["bundle"]["status"] = "WORLD_TRUTH"
        with self.assertRaises(ContractError):
            bridge.load_cube_atlas_document(wire, source_receipts=doc._receipts)

    def test_partial_decomposition_rejects_nonoutgoing_branch(self):
        foreign = deepcopy(BASE)
        cube = foreign["cube_nodes"][0]
        nonoutgoing = next(row for row in foreign["branches"] if row["source_node_id"] != cube["node_id"])
        cube["faces"]["face_5"]["structured"]["completeness"] = "partial"
        cube["faces"]["face_5"]["structured"]["direct_branch_refs"] = [nonoutgoing["branch_id"]]
        with self.assertRaises(ContractError):
            document(foreign)

    def test_partial_view_is_not_silently_expanded_to_all_branches(self):
        foreign = deepcopy(BASE)
        selected = next(row for row in foreign["views"] if row["view_id"] == "view_context")
        selected["branch_refs"] = selected["branch_refs"][:-1]
        with self.assertRaises(ContractError):
            document(foreign)

    def test_duplicate_view_branch_is_refused(self):
        foreign = deepcopy(BASE)
        selected = next(row for row in foreign["views"] if row["view_id"] == "view_context")
        selected["branch_refs"].append(selected["branch_refs"][0])
        with self.assertRaises(ContractError):
            document(foreign)

    def test_namespace_identity_separated(self):
        first = bridge.canonical_cube_id("source-a", "context", "node_001")
        second = bridge.canonical_cube_id("source-b", "context", "node_001")
        self.assertNotEqual(first, second)

    def test_containment_not_runtime_transition(self):
        doc = document(BASE)
        self.assertEqual({link.relation.value for link in doc.atlas.links}, {"contains_part"})
        self.assertEqual(len(doc.atlas.nodes), 43)
        self.assertEqual(len(doc.atlas.links), 47)

if __name__ == "__main__":
    unittest.main(verbosity=2)
