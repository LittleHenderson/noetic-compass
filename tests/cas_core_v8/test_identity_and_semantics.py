from __future__ import annotations

from decimal import Decimal
from enum import Enum, IntEnum
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import cas_core_v8.identity as identity_module

from cas_core_v8 import (
    AdmissionStatus,
    ArtifactIdentity,
    CanonicalizationError,
    CrosswalkRelation,
    FrozenList,
    LicenseStatus,
    ResearchBoundary,
    SemanticCrosswalk,
    SemanticNamespace,
    SemanticRef,
    SemanticValidationError,
    canonical_json_bytes,
)


DIGEST_A = "A" * 64
DIGEST_B = "B" * 64


class TextCode(str, Enum):
    OPEN = "OPEN"


class NumericCode(IntEnum):
    ONE = 1


class IdentityTests(unittest.TestCase):
    def test_raw_and_lf_identities_are_both_preserved(self) -> None:
        identity = ArtifactIdentity.from_bytes(b"a\r\nb\r\n")
        self.assertEqual(identity.raw_bytes, 6)
        self.assertEqual(identity.canonical_lf_bytes, 4)
        self.assertEqual(identity.crlf_sequences, 2)
        self.assertEqual(identity.lone_lf_sequences, 0)
        self.assertEqual(identity.lone_cr_sequences, 0)
        self.assertEqual(identity.line_ending_profile, "CRLF")
        self.assertNotEqual(identity.raw_sha256, identity.canonical_lf_sha256)
        self.assertEqual(
            canonical_json_bytes(identity), canonical_json_bytes(identity.to_dict())
        )

    def test_lone_cr_is_counted_and_never_mislabeled(self) -> None:
        cr_only = ArtifactIdentity.from_bytes(b"a\rb")
        self.assertEqual(cr_only.lone_cr_sequences, 1)
        self.assertEqual(cr_only.line_ending_profile, "CR")
        mixed = ArtifactIdentity.from_bytes(b"a\r\nb\rc\n")
        self.assertEqual(mixed.line_ending_profile, "MIXED")

    def test_canonical_json_is_order_stable_and_decimal_exact(self) -> None:
        left = canonical_json_bytes({"z": Decimal("1.230"), "a": [2, 1]})
        right = canonical_json_bytes({"a": [2, 1], "z": Decimal("1.230")})
        self.assertEqual(left, right)
        self.assertEqual(
            left,
            b'{"a":[2,1],"z":{"$cas$type":"decimal","value":"1.230"}}\n',
        )

    def test_decimal_is_type_distinct_and_reserved_tag_cannot_collide(self) -> None:
        self.assertNotEqual(
            canonical_json_bytes({"value": Decimal("1.0")}),
            canonical_json_bytes({"value": "1.0"}),
        )
        with self.assertRaises(CanonicalizationError):
            canonical_json_bytes({"$cas$type": "decimal", "value": "1.0"})

    def test_canonical_json_rejects_binary_float_and_set(self) -> None:
        with self.assertRaises(CanonicalizationError):
            canonical_json_bytes({"value": 0.1})
        with self.assertRaises(CanonicalizationError):
            canonical_json_bytes({"values": {1, 2}})

    def test_canonical_integer_bit_length_boundary_is_explicit(self) -> None:
        maximum = (1 << identity_module.CANONICAL_MAX_INTEGER_BITS) - 1
        encoded = canonical_json_bytes({"negative": -maximum, "positive": maximum})
        self.assertIn(str(maximum).encode(), encoded)

        outside = 1 << identity_module.CANONICAL_MAX_INTEGER_BITS
        for value in (outside, -outside):
            with self.subTest(sign="negative" if value < 0 else "positive"):
                with self.assertRaisesRegex(CanonicalizationError, "bit length"):
                    canonical_json_bytes({"value": value})

    def test_enums_and_tuples_are_type_distinct_from_json_scalars_and_arrays(self) -> None:
        self.assertNotEqual(
            canonical_json_bytes({"value": TextCode.OPEN}),
            canonical_json_bytes({"value": "OPEN"}),
        )
        self.assertNotEqual(
            canonical_json_bytes({"value": NumericCode.ONE}),
            canonical_json_bytes({"value": 1}),
        )
        self.assertNotEqual(
            canonical_json_bytes({"value": [1, 2]}),
            canonical_json_bytes({"value": (1, 2)}),
        )
        self.assertEqual(
            canonical_json_bytes({"value": FrozenList((1, 2))}),
            canonical_json_bytes({"value": [1, 2]}),
        )

    def test_unicode_control_and_format_characters_are_rejected_everywhere(self) -> None:
        for value in ("line\nbreak", "invisible\u200djoiner"):
            with self.subTest(value=repr(value)), self.assertRaises(
                CanonicalizationError
            ):
                canonical_json_bytes({"value": value})
        with self.assertRaises(CanonicalizationError):
            canonical_json_bytes({"bad\u200dkey": "value"})

    def test_canonical_json_has_cycle_depth_node_and_size_limits(self) -> None:
        cyclic: list[object] = []
        cyclic.append(cyclic)
        with self.assertRaisesRegex(CanonicalizationError, "cycle"):
            canonical_json_bytes(cyclic)

        deep: object = "leaf"
        for _ in range(identity_module.CANONICAL_MAX_DEPTH + 1):
            deep = [deep]
        with self.assertRaisesRegex(CanonicalizationError, "depth"):
            canonical_json_bytes(deep)

        with self.assertRaisesRegex(CanonicalizationError, "node count"):
            canonical_json_bytes(
                list(range(identity_module.CANONICAL_MAX_NODES + 1))
            )
        with self.assertRaisesRegex(CanonicalizationError, "maximum size"):
            canonical_json_bytes("x" * (identity_module.CANONICAL_MAX_BYTES + 1))

    def test_identifier_ascii_rules_do_not_forbid_prose_unicode(self) -> None:
        self.assertIn("Caf", canonical_json_bytes({"note": "Café"}).decode())
        for local_id in ("Ｆ1", "Fé", " F1", "F 1"):
            with self.subTest(local_id=local_id), self.assertRaises(
                SemanticValidationError
            ):
                SemanticRef(
                    namespace=SemanticNamespace.TKS_FOUNDATION,
                    local_id=local_id,
                    version="v1",
                    source_id="SRC-A",
                    definition_sha256=DIGEST_A,
                )


class SemanticIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.foundation = SemanticRef(
            namespace=SemanticNamespace.TKS_FOUNDATION,
            local_id="F1",
            version="TKS Foundations 1.0",
            source_id="SRC-TKS-F28-CROSSWALK",
            definition_sha256=DIGEST_A,
        )
        self.drive = SemanticRef(
            namespace=SemanticNamespace.CAS_DRIVE,
            local_id="F1",
            version="CAS v7.7",
            source_id="SRC-CAS77-NORMATIVE-REGISTERED",
            definition_sha256=DIGEST_B,
        )

    def test_cross_system_identity_is_rejected(self) -> None:
        with self.assertRaises(SemanticValidationError):
            SemanticCrosswalk(
                crosswalk_id="bad-identity",
                source=self.foundation,
                target=self.drive,
                relation=CrosswalkRelation.IDENTITY,
                source_artifact_sha256=DIGEST_A,
                note="same numeric position",
            )

    def test_explicit_alignment_is_serializable_without_identity_claim(self) -> None:
        crosswalk = SemanticCrosswalk(
            crosswalk_id="foundation-drive-position-1",
            source=self.foundation,
            target=self.drive,
            relation=CrosswalkRelation.ALIGNMENT,
            source_artifact_sha256=DIGEST_A,
            note="Named positional crosswalk; definition identity is not asserted.",
        )
        self.assertEqual(crosswalk.to_dict()["relation"], "ALIGNMENT")
        self.assertEqual(crosswalk.to_dict()["boundary"]["status"], "OPEN")
        self.assertNotEqual(
            crosswalk.to_dict()["source"]["qualified_id"],
            crosswalk.to_dict()["target"]["qualified_id"],
        )

    def test_default_research_boundary_is_fail_closed(self) -> None:
        boundary = ResearchBoundary.ring4_open().to_dict()
        self.assertEqual(boundary["status"], "OPEN")
        self.assertEqual(boundary["license_status"], "NOT LICENSED")
        self.assertFalse(boundary["public_disclosure_authorized"])

    def test_ring4_boundary_rejects_accept_license_and_disclosure(self) -> None:
        with self.assertRaises(SemanticValidationError):
            ResearchBoundary(
                admission_ring=4,
                status=AdmissionStatus.ACCEPT,
                license_status=LicenseStatus.LICENSED,
                public_disclosure_authorized=True,
            )

    def test_qualified_id_is_structural_not_delimiter_ambiguous(self) -> None:
        left = SemanticRef(
            namespace=SemanticNamespace.TKS_FOUNDATION,
            local_id="y",
            version="v:x",
            source_id="SRC-A",
            definition_sha256=DIGEST_A,
        )
        right = SemanticRef(
            namespace=SemanticNamespace.TKS_FOUNDATION,
            local_id="x:y",
            version="v",
            source_id="SRC-B",
            definition_sha256=DIGEST_B,
        )
        self.assertNotEqual(left.qualified_id, right.qualified_id)
        self.assertTrue(left.qualified_id.startswith("semantic-ref.v1:"))

    def test_qualified_id_injectively_binds_source_and_definition(self) -> None:
        baseline = SemanticRef(
            namespace=SemanticNamespace.TKS_FOUNDATION,
            local_id="F1",
            version="v1",
            source_id="SRC-A",
            definition_sha256=DIGEST_A,
        )
        different_source = SemanticRef(
            namespace=baseline.namespace,
            local_id=baseline.local_id,
            version=baseline.version,
            source_id="SRC-B",
            definition_sha256=baseline.definition_sha256,
        )
        different_definition = SemanticRef(
            namespace=baseline.namespace,
            local_id=baseline.local_id,
            version=baseline.version,
            source_id=baseline.source_id,
            definition_sha256=DIGEST_B,
        )
        self.assertEqual(
            (baseline.namespace, baseline.local_id, baseline.version),
            (
                different_source.namespace,
                different_source.local_id,
                different_source.version,
            ),
        )
        self.assertEqual(
            (baseline.namespace, baseline.local_id, baseline.version),
            (
                different_definition.namespace,
                different_definition.local_id,
                different_definition.version,
            ),
        )
        self.assertEqual(
            len(
                {
                    baseline.qualified_id,
                    different_source.qualified_id,
                    different_definition.qualified_id,
                }
            ),
            3,
        )

    def test_semantic_identity_rejects_invisible_format_characters(self) -> None:
        with self.assertRaises(SemanticValidationError):
            SemanticRef(
                namespace=SemanticNamespace.TKS_FOUNDATION,
                local_id="F\u200d1",
                version="v1",
                source_id="SRC-A",
                definition_sha256=DIGEST_A,
            )

    def test_boundary_and_semantic_subclasses_cannot_override_identity(self) -> None:
        class BoundaryVariant(ResearchBoundary):
            def __eq__(self, other: object) -> bool:
                return True

        boundary = object.__new__(BoundaryVariant)
        object.__setattr__(boundary, "admission_ring", 3)
        object.__setattr__(boundary, "status", AdmissionStatus.ACCEPT)
        object.__setattr__(boundary, "license_status", LicenseStatus.LICENSED)
        object.__setattr__(boundary, "public_disclosure_authorized", True)

        class SemanticRefVariant(SemanticRef):
            def __eq__(self, other: object) -> bool:
                return True

        target = object.__new__(SemanticRefVariant)
        object.__setattr__(target, "namespace", SemanticNamespace.CAS_DRIVE)
        object.__setattr__(target, "local_id", self.foundation.local_id)
        object.__setattr__(target, "version", self.foundation.version)
        object.__setattr__(target, "source_id", self.foundation.source_id)
        object.__setattr__(
            target, "definition_sha256", self.foundation.definition_sha256
        )

        with self.assertRaisesRegex(SemanticValidationError, "SemanticRef"):
            SemanticCrosswalk(
                crosswalk_id="typed-identity-check",
                source=self.foundation,
                target=target,
                relation=CrosswalkRelation.IDENTITY,
                source_artifact_sha256=DIGEST_A,
                note="Equality overrides are not semantic identity.",
            )
        with self.assertRaisesRegex(SemanticValidationError, "Ring 4"):
            SemanticCrosswalk(
                crosswalk_id="typed-boundary-check",
                source=self.foundation,
                target=self.foundation,
                relation=CrosswalkRelation.IDENTITY,
                source_artifact_sha256=DIGEST_A,
                note="A boundary subclass is not the research boundary.",
                boundary=boundary,
            )


if __name__ == "__main__":
    unittest.main()
