from __future__ import annotations

import hashlib
import os
import sys
import unittest
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, localcontext
from enum import Enum
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import cas_ohm_v1.canonical as canonical_module  # noqa: E402
from cas_ohm_v1 import (  # noqa: E402
    ADMISSION_RING,
    COVARIANCE_LIMITATION,
    DISCLOSURE_STATUS,
    LICENSE_STATUS,
    RESEARCH_STATUS,
    ArtifactEvidence,
    ArtifactRef,
    AuthorityKey,
    AuthorityManifest,
    CalibrationProfile,
    Capability,
    CapabilityAttestation,
    CapabilityError,
    CJTQRecord,
    ClassificationMode,
    ControlBinding,
    CoordinateIdentity,
    CurrentClockReceipt,
    DirectionProvenance,
    DirectionSign,
    DoseResponseRegion,
    DriftState,
    EvidenceRegistry,
    FieldProvenance,
    FullScaleValue,
    GainStage,
    IFSMethod,
    InstrumentIdentity,
    MeasurementKind,
    MeasurementValue,
    ModelIdentity,
    NonClaimExtension,
    OperatingAssessment,
    OperatingClassification,
    OperationContext,
    ParentRef,
    Q4Band,
    QuantityKind,
    ResidualCensoring,
    ResistanceComponent,
    ResistanceRole,
    ReviewState,
    SemanticOutcome,
    SyntheticBoard,
    SyntheticFault,
    ToleranceProfile,
    TrustedCapabilityAuthority,
    TrustMode,
    Uncertainty,
    UnitKind,
    ValidationError,
    canonical_bytes,
    classify_sweep_point,
    compose_gains,
    diagnose_residual,
    normalize_flow,
    packet_eligibility,
    parallel_equivalent,
    parent_ref,
    predict_flow,
    q4_band,
    replay_network_equivalent,
    series_equivalent,
)
from cas_ohm_v1 import (  # noqa: E402
    TestPointIdentity as OhmTestPointIdentity,
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


class CasOhmV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        # Ephemeral fixture keys test signature integrity only; they are not authority.
        self.REVIEWER_PRIVATE_KEY = os.urandom(32)
        self.ATTACKER_PRIVATE_KEY = os.urandom(32)
        self.artifacts: dict[str, ArtifactEvidence] = {}
        for name in (
            "source",
            "raw",
            "control",
            "corpus",
            "rights",
            "code",
            "calibration-split",
            "validation-split",
            "drift-check",
            "fit-receipt",
            "dependency-lock",
            "unrelated",
        ):
            self.artifacts[name] = self.make_artifact(
                name, f"verified:{name}:v1".encode()
            )
        for name, payload in (
            ("weights", b"weights"),
            ("config", b"config"),
            ("tokenizer", b"tokenizer"),
            ("probe-code", b"probe-code"),
            ("direction-vector", b"direction-vector"),
        ):
            self.artifacts[name] = self.make_artifact(name, payload)
        self.capability_artifacts = {
            capability: self.make_artifact(
                f"capability-{capability.value.lower()}",
                f"validated:{capability.value}:profile-specific".encode(),
            )
            for capability in Capability
        }
        self.model = ModelIdentity(
            "model-x",
            "rev-1",
            sha256(b"weights"),
            sha256(b"config"),
            sha256(b"tokenizer"),
        )
        self.instrument = InstrumentIdentity(
            "probe-1", "activation-probe", "1.0", sha256(b"probe-code")
        )
        self.test_point = OhmTestPointIdentity(
            self.model,
            "resid_post.10",
            (3, 4),
            "steering-axis-1",
            sha256(b"direction-vector"),
            DirectionProvenance.PROBE_DERIVED,
            Decimal("1"),
            DirectionSign.POSITIVE,
            "residual-stream-post",
        )
        self.tolerances = ToleranceProfile(
            Decimal("0.1"),
            Decimal("0.05"),
            Decimal("0.01"),
            Decimal("0.95"),
            Decimal("0.10"),
        )
        self.profile = self.make_profile()
        reviewer_public_key = TrustedCapabilityAuthority.public_key_from_private(
            self.REVIEWER_PRIVATE_KEY
        )
        manifest = AuthorityManifest(
            "test-integrity-configuration",
            "1",
            TrustMode.INTEGRITY_CONFIGURATION,
            (AuthorityKey.from_public_key("reviewer-1", reviewer_public_key),),
        )
        manifest_ref = ArtifactRef(
            "authority-manifest",
            "memory://authority-manifest",
            manifest.sha256,
            "application/vnd.cas-ohm.authority-manifest+json",
        )
        self.artifacts["authority-manifest"] = ArtifactEvidence(
            manifest_ref, manifest.canonical_bytes
        )
        self.authority = TrustedCapabilityAuthority(manifest, manifest_ref)

    def make_artifact(self, name: str, payload: bytes) -> ArtifactEvidence:
        ref = ArtifactRef(
            name, f"memory://{name}", sha256(payload), "application/octet-stream"
        )
        return ArtifactEvidence(ref, payload)

    def uncertainty(
        self,
        unit: UnitKind,
        value: Decimal,
        radius: Decimal = Decimal("0.1"),
        standard: Decimal = Decimal("0.05"),
        *,
        nonnegative: bool = False,
    ) -> Uncertainty:
        lower = value - radius
        if nonnegative:
            lower = max(Decimal("0"), lower)
        return Uncertainty(
            unit,
            standard,
            lower,
            value + radius,
            Decimal("0.95"),
            "bootstrap-95",
        )

    def make_profile(self, **overrides: object) -> CalibrationProfile:
        full_scale = FullScaleValue(
            self.test_point.sha256,
            Decimal("10"),
            UnitKind.ACTIVATION,
            self.uncertainty(UnitKind.ACTIVATION, Decimal("10"), Decimal("0.2")),
            100,
            (self.artifacts["source"].ref,),
        )
        values: dict[str, object] = {
            "profile_id": "profile-1",
            "model": self.model,
            "created_at": "2026-08-01T00:00:00Z",
            "valid_from": "2026-08-02T00:00:00Z",
            "expires_at": "2027-08-02T00:00:00Z",
            "drift_state": DriftState.CURRENT,
            "drift_check_ref": self.artifacts["drift-check"].ref,
            "runtime_id": "python-3.14/cpu",
            "dtype": "decimal-exact-input/fp50-derived",
            "code_ref": self.artifacts["code"].ref,
            "dependency_lock_ref": self.artifacts["dependency-lock"].ref,
            "model_artifact_refs": tuple(
                self.artifacts[name].ref for name in ("weights", "config", "tokenizer")
            ),
            "corpus_ref": self.artifacts["corpus"].ref,
            "corpus_rights_ref": self.artifacts["rights"].ref,
            "calibration_split_ref": self.artifacts["calibration-split"].ref,
            "validation_split_ref": self.artifacts["validation-split"].ref,
            "random_seed": 1729,
            "randomization_method": "sha256-counter-v1",
            "instruments": (self.instrument,),
            "instrument_implementation_refs": (self.artifacts["probe-code"].ref,),
            "test_points": (self.test_point,),
            "direction_refs": (self.artifacts["direction-vector"].ref,),
            "ifs_method": IFSMethod.DECLARED_DESIGN_FULL_SCALE,
            "full_scales": (full_scale,),
            "ifs_percentile": None,
            "alpha_grid": (
                Decimal("-5"),
                Decimal("0"),
                Decimal("1"),
                Decimal("2"),
                Decimal("4"),
                Decimal("5"),
            ),
            "alpha_min": Decimal("-5"),
            "alpha_max": Decimal("5"),
            "fit_method_id": "held-out-inverse-slope-v1",
            "fit_receipt_ref": self.artifacts["fit-receipt"].ref,
            "uncertainty_method_id": "bootstrap-covariance-v1",
            "response_region_method_id": "local-slope-v1",
            "tolerances": self.tolerances,
            "control_refs": (self.artifacts["control"].ref,),
            "control_bindings": (
                ControlBinding(
                    self.artifacts["control"].ref,
                    self.test_point.sha256,
                    "negative-and-null-control-v1",
                ),
            ),
            "source_refs": (self.artifacts["source"].ref,),
            "review_state": ReviewState.REVIEWED,
        }
        values.update(overrides)
        return CalibrationProfile(**values)  # type: ignore[arg-type]

    def attestations(
        self,
        profile: CalibrationProfile,
        capabilities: tuple[Capability, ...] | None = None,
        *,
        private_key: bytes | None = None,
        reviewer_id: str = "reviewer-1",
    ) -> tuple[CapabilityAttestation, ...]:
        if capabilities is None:
            capabilities = tuple(Capability)
        signing_private_key = private_key or self.REVIEWER_PRIVATE_KEY
        return tuple(
            TrustedCapabilityAuthority.sign(
                profile.sha256,
                capability,
                self.capability_artifacts[capability].ref,
                reviewer_id,
                "2026-08-02T00:00:00Z",
                "2027-01-01T00:00:00Z",
                signing_private_key,
            )
            for capability in capabilities
        )

    def context(
        self,
        *,
        profile: CalibrationProfile | None = None,
        objects: tuple[object, ...] = (),
        capabilities: tuple[Capability, ...] | None = None,
        attestations: tuple[CapabilityAttestation, ...] | None = None,
        authority: TrustedCapabilityAuthority | None = None,
        artifact_evidence: tuple[ArtifactEvidence, ...] | None = None,
        as_of: str = "2026-08-04T00:00:00Z",
        current_clock_receipt: CurrentClockReceipt | None = None,
    ) -> OperationContext:
        selected_profile = profile or self.profile
        if artifact_evidence is None:
            artifact_evidence = tuple(self.artifacts.values()) + tuple(
                self.capability_artifacts.values()
            )
        object_values: dict[tuple[type[object], str], object] = {}
        for value in selected_profile.full_scales + objects:
            object_values[(type(value), value.sha256)] = value
        registry = EvidenceRegistry(artifact_evidence, tuple(object_values.values()))
        selected_attestations = attestations
        if selected_attestations is None:
            selected_attestations = self.attestations(selected_profile, capabilities)
        return OperationContext(
            selected_profile,
            registry,
            authority or self.authority,
            selected_attestations,
            as_of,
            current_clock_receipt,
        )

    def drive(
        self, value: str = "4", profile: CalibrationProfile | None = None
    ) -> MeasurementValue:
        selected = profile or self.profile
        return MeasurementValue(
            "alpha",
            QuantityKind.DRIVE_INTERVENTION,
            Decimal(value),
            UnitKind.ALPHA,
            MeasurementKind.DESIGN_VALUE,
            FieldProvenance(
                (self.artifacts["source"].ref,),
                "preregistered-alpha-dose",
                selected.sha256,
                test_point=self.test_point,
                dataset_split_ref=selected.validation_split_ref,
            ),
        )

    def external_assessment(
        self,
        context: OperationContext,
        classification: OperatingClassification,
    ) -> OperatingAssessment:
        return OperatingAssessment(
            classification,
            ClassificationMode.EXTERNAL_UNVERIFIED,
            "external-research-classification-v1",
            context.profile.sha256,
            self.test_point.sha256,
            self.artifacts["unrelated"].ref,
            (),
            None,
            None,
            context.profile.control_bindings,
            context.operation_binding(None, require_integrity=False),
        )

    def calibrated_resistance(
        self,
        value: str = "2",
        field_name: str = "R_calibrated",
        profile: CalibrationProfile | None = None,
    ) -> MeasurementValue:
        selected = profile or self.profile
        decimal_value = Decimal(value)
        return MeasurementValue(
            field_name,
            QuantityKind.EFFECTIVE_RESISTANCE,
            decimal_value,
            UnitKind.ALPHA_PER_ACTIVATION,
            MeasurementKind.MODEL_DERIVED,
            FieldProvenance(
                (self.artifacts["source"].ref,),
                selected.fit_method_id,
                selected.sha256,
                test_point=self.test_point,
                control_refs=selected.control_refs,
                control_bindings=selected.control_bindings,
                dataset_split_ref=selected.validation_split_ref,
                derivation_parents=(
                    parent_ref(
                        "held_out_fit_receipt", 0, self.artifacts["fit-receipt"]
                    ),
                ),
            ),
            self.uncertainty(
                UnitKind.ALPHA_PER_ACTIVATION,
                decimal_value,
                Decimal("0.1"),
                Decimal("0.04"),
            ),
            100,
            ResistanceRole.CALIBRATED_HELD_OUT,
        )

    def instrumented_flow(
        self,
        value: Decimal,
        *,
        profile: CalibrationProfile | None = None,
        radius: Decimal = Decimal("0.1"),
        field_name: str = "I_obs",
    ) -> MeasurementValue:
        selected = profile or self.profile
        return MeasurementValue(
            field_name,
            QuantityKind.FLOW_MAGNITUDE,
            value,
            UnitKind.ACTIVATION,
            MeasurementKind.INSTRUMENTED,
            FieldProvenance(
                (self.artifacts["source"].ref,),
                "activation-probe-v1",
                selected.sha256,
                instrument=self.instrument,
                test_point=self.test_point,
                raw_artifact_refs=(self.artifacts["raw"].ref,),
                control_refs=selected.control_refs,
                control_bindings=selected.control_bindings,
                dataset_split_ref=selected.validation_split_ref,
            ),
            self.uncertainty(
                UnitKind.ACTIVATION,
                value,
                radius,
                Decimal("0.05"),
                nonnegative=True,
            ),
            30,
        )

    def gain(self, name: str, value: str) -> MeasurementValue:
        decimal_value = Decimal(value)
        return MeasurementValue(
            name,
            QuantityKind.GAIN_MAGNITUDE,
            decimal_value,
            UnitKind.DIMENSIONLESS,
            MeasurementKind.MODEL_DERIVED,
            FieldProvenance(
                (self.artifacts["source"].ref,),
                "active-region-gain-fit",
                self.profile.sha256,
                test_point=self.test_point,
                control_refs=self.profile.control_refs,
                control_bindings=self.profile.control_bindings,
                dataset_split_ref=self.profile.validation_split_ref,
                derivation_parents=(
                    parent_ref("gain_fit_receipt", 0, self.artifacts["fit-receipt"]),
                ),
            ),
            self.uncertainty(
                UnitKind.DIMENSIONLESS,
                decimal_value,
                Decimal("0.05"),
                Decimal("0.02"),
                nonnegative=True,
            ),
            100,
        )

    def prediction_fixture(
        self, observed_value: Decimal = Decimal("1")
    ) -> tuple[
        OperationContext,
        MeasurementValue,
        MeasurementValue,
        MeasurementValue,
        MeasurementValue,
    ]:
        drive = self.drive()
        resistance = self.calibrated_resistance()
        base_context = self.context(objects=(drive, resistance))
        predicted = predict_flow(base_context, drive, resistance)
        observed = self.instrumented_flow(observed_value)
        context = self.context(objects=(drive, resistance, predicted, observed))
        return context, drive, resistance, predicted, observed

    def full_packet(self) -> tuple[OperationContext, CJTQRecord, dict[str, object]]:
        context, drive, resistance, predicted, observed = self.prediction_fixture()
        observations = SyntheticBoard(
            Decimal("2"),
            Decimal("0"),
            Decimal("100"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            SyntheticFault.NONE,
        ).sweep((Decimal("1"), Decimal("2"), Decimal("3")))
        sweep_artifact = self.make_artifact(
            "operating-sweep", canonical_bytes(observations)
        )
        self.artifacts["operating-sweep"] = sweep_artifact
        context = self.context(objects=(drive, resistance, predicted, observed))
        normalized = normalize_flow(context, observed, self.test_point)
        assessment = classify_sweep_point(
            context,
            observations,
            1,
            Decimal("2"),
            sweep_artifact.ref,
        )
        diagnostic = diagnose_residual(
            context,
            drive,
            predicted,
            observed,
            resistance,
            assessment,
        )
        fields = (
            drive,
            resistance,
            predicted,
            observed,
            normalized.q10,
            normalized.overload_ratio,
            diagnostic.residual,
            diagnostic.relative_error,
        )
        context = self.context(
            objects=(drive, resistance, predicted, observed, assessment)
        )
        packet_refs = (
            self.profile.all_artifact_refs()
            + (context.authority.manifest_ref, assessment.evidence_ref)
            + tuple(item.evidence_ref for item in context.attestations)
        )
        for field in fields:
            provenance = field.provenance
            packet_refs += (
                provenance.source_refs
                + provenance.raw_artifact_refs
                + provenance.control_refs
            )
            if provenance.dataset_split_ref is not None:
                packet_refs += (provenance.dataset_split_ref,)
        evidence_refs = tuple(
            sorted(
                {ref.sha256: ref for ref in packet_refs}.values(),
                key=lambda ref: ref.sha256,
            )
        )
        control_refs = self.profile.control_refs
        record = CJTQRecord(
            "record-1",
            self.profile.sha256,
            self.test_point.sha256,
            fields,
            assessment,
            evidence_refs,
            control_refs,
            self.profile.control_bindings,
            ReviewState.REVIEWED,
        )
        return (
            context,
            record,
            {
                "drive": drive,
                "resistance": resistance,
                "predicted": predicted,
                "observed": observed,
                "normalized": normalized,
                "diagnostic": diagnostic,
            },
        )

    def test_status_is_explicitly_research_only(self) -> None:
        self.assertEqual(
            (RESEARCH_STATUS, ADMISSION_RING, LICENSE_STATUS, DISCLOSURE_STATUS),
            ("OPEN", 4, "NOT LICENSED", "HELD"),
        )
        encoded = self.profile.canonical_bytes.decode()
        for marker in ("OPEN", "NOT LICENSED", "HELD"):
            self.assertIn(marker, encoded)

    def test_float_and_nonfinite_decimal_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            replace(self.drive(), value=1.0)  # type: ignore[arg-type]
        with self.assertRaises(ValidationError):
            replace(self.drive(), value=Decimal("Infinity"))

    def test_unsafe_control_bidi_and_format_unicode_is_rejected(self) -> None:
        for character in ("\x00", "\u202e", "\u2066", "\u200b"):
            unsafe = f"safe{character}unsafe"
            with (
                self.subTest(character=ord(character)),
                self.assertRaises(ValidationError),
            ):
                replace(self.artifacts["source"].ref, artifact_id=unsafe)
            with self.assertRaises(ValidationError):
                canonical_bytes(unsafe)
            with self.assertRaises(ValidationError):
                canonical_bytes({unsafe: "value"})

    def test_scale_and_unit_mixing_is_rejected(self) -> None:
        provenance = self.drive().provenance
        with self.assertRaises(ValidationError):
            MeasurementValue(
                "sat",
                QuantityKind.SATURATION_FRACTION,
                Decimal("8.5"),
                UnitKind.FRACTION,
                MeasurementKind.DESIGN_VALUE,
                provenance,
            )
        with self.assertRaises(ValidationError):
            MeasurementValue(
                "score-as-resistance",
                QuantityKind.CONSTRAINT_SCORE,
                Decimal("5"),
                UnitKind.ALPHA_PER_ACTIVATION,
                MeasurementKind.DESIGN_VALUE,
                provenance,
            )

    def test_canonicalization_is_type_injective(self) -> None:
        self.assertEqual(
            canonical_bytes({"first": 1, "second": 2}),
            canonical_bytes({"second": 2, "first": 1}),
        )
        self.assertNotEqual(canonical_bytes(UnitKind.Q10), canonical_bytes("Q10"))
        self.assertNotEqual(canonical_bytes((1, 2)), canonical_bytes([1, 2]))
        self.assertNotEqual(
            canonical_bytes(Decimal("1")), canonical_bytes({"$decimal": "1"})
        )
        self.assertNotEqual(
            canonical_bytes(UnitKind.Q10),
            canonical_bytes(
                {
                    "$enum": "cas_ohm_v1.model.UnitKind",
                    "value": "Q10",
                }
            ),
        )
        drive = self.drive()
        self.assertNotEqual(
            canonical_bytes(drive),
            canonical_bytes(
                {
                    "$object": "cas_ohm_v1.model.MeasurementValue",
                    "payload": drive.canonical_payload(),
                }
            ),
        )
        self.assertNotEqual(
            canonical_bytes(drive), canonical_bytes(drive.canonical_payload())
        )

    def test_canonicalization_and_arithmetic_ignore_ambient_context(self) -> None:
        context = self.context(
            objects=(self.drive("1"), self.calibrated_resistance("3"))
        )
        drive = self.drive("1")
        resistance = self.calibrated_resistance("3")
        expected = predict_flow(context, drive, resistance)
        long_value = Decimal("123456789012345678901234567890.123450000")
        expected_bytes = canonical_bytes({"value": long_value})
        with localcontext() as decimal_context:
            decimal_context.prec = 4
            observed = predict_flow(context, drive, resistance)
            observed_bytes = canonical_bytes({"value": long_value})
        self.assertEqual(expected.value, observed.value)
        self.assertEqual(expected_bytes, observed_bytes)

    def test_canonical_integer_bit_length_boundary_is_explicit(self) -> None:
        maximum = (1 << canonical_module.CANONICAL_MAX_INTEGER_BITS) - 1
        encoded = canonical_bytes(
            {"negative": -maximum, "positive": maximum}
        )
        self.assertIn(str(maximum).encode(), encoded)
        self.assertIn(str(-maximum).encode(), encoded)

        outside = 1 << canonical_module.CANONICAL_MAX_INTEGER_BITS
        for value in (outside, -outside):
            with (
                self.subTest(sign="negative" if value < 0 else "positive"),
                self.assertRaisesRegex(ValidationError, "bit length"),
            ):
                canonical_bytes({"value": value})

    def test_canonical_integer_conversion_failure_is_normalized(self) -> None:
        with (
            patch.object(
                canonical_module,
                "str",
                side_effect=ValueError("runtime conversion limit"),
                create=True,
            ),
            self.assertRaisesRegex(ValidationError, "conversion failed"),
        ):
            canonical_bytes(1)

    def test_measurements_are_frozen(self) -> None:
        measurement = self.drive()
        with self.assertRaises(FrozenInstanceError):
            measurement.value = Decimal("9")  # type: ignore[misc]

    def test_artifact_bytes_must_match_declared_hash(self) -> None:
        ref = ArtifactRef("bad", "memory://bad", sha256(b"expected"), "text/plain")
        with self.assertRaises(ValidationError):
            ArtifactEvidence(ref, b"tampered")

    def test_parent_roles_and_order_are_identity_bearing(self) -> None:
        first = parent_ref("first", 0, self.artifacts["fit-receipt"])
        second = parent_ref("second", 1, self.artifacts["source"])
        base = self.calibrated_resistance().provenance
        left = replace(base, derivation_parents=(first, second))
        right = replace(
            base,
            derivation_parents=(
                parent_ref("second", 0, self.artifacts["source"]),
                parent_ref("first", 1, self.artifacts["fit-receipt"]),
            ),
        )
        self.assertNotEqual(canonical_bytes(left), canonical_bytes(right))
        with self.assertRaises(ValidationError):
            replace(base, derivation_parents=(replace(first, position=1),))

    def test_wrong_role_or_unrelated_fit_parent_is_rejected(self) -> None:
        drive = self.drive()
        resistance = self.calibrated_resistance()
        wrong_parents = (
            (parent_ref("wrong_role", 0, self.artifacts["fit-receipt"]),),
            (parent_ref("held_out_fit_receipt", 0, self.artifacts["unrelated"]),),
        )
        for parents in wrong_parents:
            forged = replace(
                resistance,
                provenance=replace(resistance.provenance, derivation_parents=parents),
            )
            with self.subTest(parent=parents[0]), self.assertRaises(ValidationError):
                predict_flow(self.context(objects=(drive, forged)), drive, forged)

    def test_unresolved_parent_is_rejected_by_context(self) -> None:
        resistance = self.calibrated_resistance()
        fake = replace(
            resistance.provenance,
            derivation_parents=(
                ParentRef(
                    "held_out_fit_receipt", 0, "cas_ohm_v1.artifact-bytes", "F" * 64
                ),
            ),
        )
        forged = replace(resistance, provenance=fake)
        with self.assertRaises(ValidationError):
            self.context().validate_measurement(forged)

    def test_profile_digest_binds_complete_experiment_identity(self) -> None:
        changed_runtime = replace(self.profile, runtime_id="python-3.14/gpu")
        changed_seed = replace(self.profile, random_seed=1730)
        changed_grid = replace(
            self.profile,
            alpha_grid=(
                Decimal("-5"),
                Decimal("0"),
                Decimal("1"),
                Decimal("3"),
                Decimal("4"),
                Decimal("5"),
            ),
        )
        changed_fit_receipt = replace(
            self.profile, fit_receipt_ref=self.artifacts["unrelated"].ref
        )
        self.assertEqual(
            len(
                {
                    self.profile.sha256,
                    changed_runtime.sha256,
                    changed_seed.sha256,
                    changed_grid.sha256,
                    changed_fit_receipt.sha256,
                }
            ),
            5,
        )

    def test_profile_rejects_omitted_bindings_or_incoherent_range(self) -> None:
        invalid_overrides = (
            {"runtime_id": ""},
            {"dtype": ""},
            {"code_ref": None},
            {"fit_receipt_ref": None},
            {"instruments": ()},
            {"test_points": ()},
            {"full_scales": ()},
            {"source_refs": ()},
            {"alpha_grid": ()},
            {"alpha_min": Decimal("-4")},
            {"calibration_split_ref": self.profile.validation_split_ref},
        )
        for overrides in invalid_overrides:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                replace(self.profile, **overrides)

    def test_stale_failed_or_unreviewed_profile_cannot_form_context(self) -> None:
        stale = replace(self.profile, expires_at="2026-08-03T00:00:00Z")
        failed = replace(self.profile, drift_state=DriftState.FAILED)
        unreviewed = replace(self.profile, review_state=ReviewState.IN_REVIEW)
        for profile in (stale, failed, unreviewed):
            with (
                self.subTest(profile=profile.sha256),
                self.assertRaises(CapabilityError),
            ):
                self.context(profile=profile)

    def test_untrusted_or_tampered_capability_is_rejected(self) -> None:
        drive = self.drive()
        resistance = self.calibrated_resistance()
        attacker_attestations = self.attestations(
            self.profile,
            (Capability.OHMIC_PREDICTION,),
            private_key=self.ATTACKER_PRIVATE_KEY,
        )
        context = self.context(
            objects=(drive, resistance), attestations=attacker_attestations
        )
        with self.assertRaises(CapabilityError):
            predict_flow(context, drive, resistance)
        valid = self.attestations(self.profile, (Capability.OHMIC_PREDICTION,))[0]
        tampered = replace(valid, evidence_ref=self.artifacts["unrelated"].ref)
        context = self.context(objects=(drive, resistance), attestations=(tampered,))
        with self.assertRaises(CapabilityError):
            predict_flow(context, drive, resistance)
        unknown = self.attestations(
            self.profile,
            (Capability.OHMIC_PREDICTION,),
            reviewer_id="unknown-reviewer",
        )
        context = self.context(objects=(drive, resistance), attestations=unknown)
        with self.assertRaises(CapabilityError):
            predict_flow(context, drive, resistance)

    def test_capability_trust_roots_are_immutable(self) -> None:
        with self.assertRaises((FrozenInstanceError, AttributeError, TypeError)):
            self.authority.manifest = self.authority.manifest  # type: ignore[misc]

    def test_capability_rejects_unsigned_expired_and_wrong_scope(self) -> None:
        drive = self.drive()
        resistance = self.calibrated_resistance()
        valid = self.attestations(self.profile, (Capability.OHMIC_PREDICTION,))[0]
        with self.assertRaises(ValidationError):
            replace(valid, signature="")
        expired = TrustedCapabilityAuthority.sign(
            self.profile.sha256,
            Capability.OHMIC_PREDICTION,
            self.capability_artifacts[Capability.OHMIC_PREDICTION].ref,
            "reviewer-1",
            "2026-08-02T00:00:00Z",
            "2026-08-03T00:00:00Z",
            self.REVIEWER_PRIVATE_KEY,
        )
        wrong_capability = self.attestations(
            self.profile, (Capability.RESIDUAL_DIAGNOSIS,)
        )
        foreign_profile = replace(self.profile, profile_id="foreign-profile")
        wrong_profile = self.attestations(
            foreign_profile, (Capability.OHMIC_PREDICTION,)
        )
        cases = ((), (expired,), wrong_capability, wrong_profile)
        for attestations in cases:
            context = self.context(
                objects=(drive, resistance), attestations=attestations
            )
            with (
                self.subTest(attestations=attestations),
                self.assertRaises(CapabilityError),
            ):
                predict_flow(context, drive, resistance)

    def test_missing_capability_evidence_bytes_is_rejected(self) -> None:
        drive = self.drive()
        resistance = self.calibrated_resistance()
        artifacts = tuple(self.artifacts.values()) + tuple(
            artifact
            for capability, artifact in self.capability_artifacts.items()
            if capability is not Capability.OHMIC_PREDICTION
        )
        with self.assertRaises(ValidationError):
            self.context(objects=(drive, resistance), artifact_evidence=artifacts)

    def test_foreign_profile_measurement_is_rejected(self) -> None:
        foreign = replace(self.profile, profile_id="foreign")
        context = self.context(profile=foreign)
        with self.assertRaises(ValidationError):
            predict_flow(context, self.drive(), self.calibrated_resistance())

    def test_out_of_calibration_range_drive_is_rejected(self) -> None:
        resistance = self.calibrated_resistance()
        for value in ("-6", "100"):
            drive = self.drive(value)
            context = self.context(objects=(drive, resistance))
            with self.subTest(value=value), self.assertRaises(ValidationError):
                predict_flow(context, drive, resistance)

    def test_prediction_rejects_design_or_apparent_resistance(self) -> None:
        drive = self.drive()
        calibrated = self.calibrated_resistance()
        context = self.context(objects=(drive, calibrated))
        predicted = predict_flow(context, drive, calibrated)
        observed = self.instrumented_flow(Decimal("1"), radius=Decimal("0.05"))
        context = self.context(objects=(drive, calibrated, predicted, observed))
        diagnostic = diagnose_residual(
            context,
            drive,
            predicted,
            observed,
            calibrated,
            self.external_assessment(
                context,
                OperatingClassification(
                    DoseResponseRegion.ACTIVE, SemanticOutcome.INTENDED
                ),
            ),
        )
        self.assertIs(
            diagnostic.effective_resistance.resistance_role,
            ResistanceRole.APPARENT_SAME_SAMPLE,
        )
        context = self.context(
            objects=(
                drive,
                calibrated,
                predicted,
                observed,
                diagnostic.effective_resistance,
            )
        )
        with self.assertRaises(ValidationError):
            predict_flow(context, drive, diagnostic.effective_resistance)
        relabelled = replace(
            diagnostic.effective_resistance,
            resistance_role=ResistanceRole.CALIBRATED_HELD_OUT,
            provenance=replace(
                diagnostic.effective_resistance.provenance,
                dataset_split_ref=self.profile.validation_split_ref,
            ),
        )
        relabel_context = self.context(
            objects=(drive, calibrated, predicted, observed, relabelled)
        )
        with self.assertRaises(ValidationError):
            predict_flow(relabel_context, drive, relabelled)

    def test_prediction_propagates_uncertainty(self) -> None:
        drive = self.drive()
        resistance = self.calibrated_resistance()
        predicted = predict_flow(
            self.context(objects=(drive, resistance)), drive, resistance
        )
        self.assertEqual(predicted.value, Decimal("2"))
        self.assertIsNotNone(predicted.uncertainty)
        self.assertLess(predicted.uncertainty.lower, predicted.value)
        self.assertGreater(predicted.uncertainty.upper, predicted.value)

    def test_prediction_requires_calibration_sample_size(self) -> None:
        drive = self.drive()
        resistance = replace(self.calibrated_resistance(), sample_size=None)
        context = self.context(objects=(drive, resistance))
        with self.assertRaises(ValidationError):
            predict_flow(context, drive, resistance)

    def test_residual_rejects_design_value_as_observation(self) -> None:
        context, drive, resistance, predicted, observed = self.prediction_fixture()
        design_observed = replace(
            observed,
            measurement_kind=MeasurementKind.DESIGN_VALUE,
            provenance=replace(
                observed.provenance,
                instrument=None,
                raw_artifact_refs=(),
                derivation_parents=(),
            ),
        )
        context = self.context(objects=(drive, resistance, predicted, design_observed))
        with self.assertRaises(ValidationError):
            diagnose_residual(
                context,
                drive,
                predicted,
                design_observed,
                resistance,
                self.external_assessment(
                    context,
                    OperatingClassification(
                        DoseResponseRegion.ACTIVE, SemanticOutcome.INTENDED
                    ),
                ),
            )

    def test_residual_rejects_nonactive_regions(self) -> None:
        context, drive, resistance, predicted, observed = self.prediction_fixture()
        for region in (
            DoseResponseRegion.CUTOFF,
            DoseResponseRegion.SATURATION,
            DoseResponseRegion.NON_OHMIC,
            DoseResponseRegion.UNSTABLE,
        ):
            with self.subTest(region=region), self.assertRaises(ValidationError):
                diagnose_residual(
                    context,
                    drive,
                    predicted,
                    observed,
                    resistance,
                    self.external_assessment(
                        context,
                        OperatingClassification(region, SemanticOutcome.INTENDED),
                    ),
                )

    def test_residual_requires_assessed_controlled_uncertain_sample(self) -> None:
        context, drive, resistance, predicted, observed = self.prediction_fixture()
        with self.assertRaises(ValidationError):
            diagnose_residual(
                context,
                drive,
                predicted,
                observed,
                resistance,
                self.external_assessment(
                    context,
                    OperatingClassification(
                        DoseResponseRegion.ACTIVE, SemanticOutcome.UNASSESSED
                    ),
                ),
            )
        for inadmissible in (
            replace(observed, uncertainty=None),
            replace(observed, sample_size=None),
            replace(
                observed,
                provenance=replace(
                    observed.provenance,
                    control_refs=(),
                    control_bindings=(),
                ),
            ),
        ):
            narrowed_context = self.context(
                objects=(drive, resistance, predicted, inadmissible)
            )
            with (
                self.subTest(observation=inadmissible.sha256),
                self.assertRaises(ValidationError),
            ):
                diagnose_residual(
                    narrowed_context,
                    drive,
                    predicted,
                    inadmissible,
                    resistance,
                    self.external_assessment(
                        narrowed_context,
                        OperatingClassification(
                            DoseResponseRegion.ACTIVE, SemanticOutcome.INTENDED
                        ),
                    ),
                )

    def test_residual_censors_when_observed_interval_includes_zero(self) -> None:
        _, drive, resistance, predicted, _ = self.prediction_fixture()
        observed = self.instrumented_flow(Decimal("0.01"), radius=Decimal("0.02"))
        context = self.context(objects=(drive, resistance, predicted, observed))
        result = diagnose_residual(
            context,
            drive,
            predicted,
            observed,
            resistance,
            self.external_assessment(
                context,
                OperatingClassification(
                    DoseResponseRegion.ACTIVE, SemanticOutcome.INTENDED
                ),
            ),
        )
        self.assertIs(
            result.censoring, ResidualCensoring.OBSERVED_INTERVAL_INCLUDES_ZERO
        )
        self.assertIsNone(result.effective_resistance)
        self.assertIsNone(result.resistance_delta)

    def test_residual_outputs_propagated_uncertainty(self) -> None:
        context, drive, resistance, predicted, observed = self.prediction_fixture()
        result = diagnose_residual(
            context,
            drive,
            predicted,
            observed,
            resistance,
            self.external_assessment(
                context,
                OperatingClassification(
                    DoseResponseRegion.ACTIVE, SemanticOutcome.INTENDED
                ),
            ),
        )
        for value in (
            result.residual,
            result.relative_error,
            result.effective_resistance,
            result.resistance_delta,
        ):
            self.assertIsNotNone(value.uncertainty)

    def test_residual_rejects_unregistered_prediction(self) -> None:
        context, drive, resistance, predicted, observed = self.prediction_fixture()
        forged = replace(predicted, value=predicted.value + Decimal("0.1"))
        context = self.context(objects=(drive, resistance, forged, observed))
        with self.assertRaises(ValidationError):
            diagnose_residual(
                context,
                drive,
                forged,
                observed,
                resistance,
                self.external_assessment(
                    context,
                    OperatingClassification(
                        DoseResponseRegion.ACTIVE, SemanticOutcome.INTENDED
                    ),
                ),
            )

    def test_q4_boundaries_use_exact_prerounding_ratio(self) -> None:
        cases = (
            ("2.499999999999999999999999999999999999999999999999999999", Q4Band.Q1),
            ("2.5", Q4Band.Q2),
            ("2.500000000000000000000000000000000000000000000000000001", Q4Band.Q2),
            ("4.999999999999999999999999999999999999999999999999999999", Q4Band.Q2),
            ("5", Q4Band.Q3),
            ("5.000000000000000000000000000000000000000000000000000001", Q4Band.Q3),
            ("7.499999999999999999999999999999999999999999999999999999", Q4Band.Q3),
            ("7.5", Q4Band.Q4),
            ("7.500000000000000000000000000000000000000000000000000001", Q4Band.Q4),
            ("10", Q4Band.Q4),
        )
        for raw_value, expected in cases:
            observed = self.instrumented_flow(
                Decimal(raw_value), radius=Decimal("0.01")
            )
            context = self.context(objects=(observed,))
            normalized = normalize_flow(context, observed, self.test_point)
            with self.subTest(raw_value=raw_value):
                self.assertIs(q4_band(normalized), expected)

    def test_q4_rejects_rounded_measurement_without_exact_ratio(self) -> None:
        observed = self.instrumented_flow(Decimal("2.5"))
        normalized = normalize_flow(
            self.context(objects=(observed,)), observed, self.test_point
        )
        with self.assertRaises(ValidationError):
            q4_band(normalized.q10)  # type: ignore[arg-type]

    def test_normalization_propagates_uncertainty_and_retains_overload(self) -> None:
        observed = self.instrumented_flow(Decimal("12"))
        normalized = normalize_flow(
            self.context(objects=(observed,)), observed, self.test_point
        )
        self.assertEqual(normalized.q10.value, Decimal("10"))
        self.assertEqual(normalized.overload_ratio.value, Decimal("1.2"))
        self.assertIsNotNone(normalized.q10.uncertainty)
        self.assertIsNotNone(normalized.overload_ratio.uncertainty)

    def test_normalized_flow_rejects_inconsistent_exact_identity(self) -> None:
        observed = self.instrumented_flow(Decimal("2"))
        normalized = normalize_flow(
            self.context(objects=(observed,)), observed, self.test_point
        )
        with self.assertRaises(ValidationError):
            replace(
                normalized,
                exact_q10=replace(normalized.exact_q10, numerator=Decimal("3")),
            )
        with self.assertRaises(ValidationError):
            replace(
                normalized,
                exact_q10=replace(normalized.exact_q10, scale=Decimal("1")),
            )

    def test_normalization_requires_raw_sample_size(self) -> None:
        observed = replace(self.instrumented_flow(Decimal("2")), sample_size=None)
        with self.assertRaises(ValidationError):
            normalize_flow(self.context(objects=(observed,)), observed, self.test_point)

    def test_complete_packet_is_structural_but_not_authenticated(self) -> None:
        context, record, _ = self.full_packet()
        result = packet_eligibility(context, record)
        self.assertTrue(result.structurally_complete, result.structural_reasons)
        self.assertFalse(result.eligible)
        self.assertIn("EXTERNAL_AUTHORITY_NOT_ADMITTED", result.reasons)

    def test_one_instrumented_field_is_insufficient_for_packet(self) -> None:
        context, record, values = self.full_packet()
        incomplete = replace(record, fields=(values["observed"],))
        result = packet_eligibility(context, incomplete)
        self.assertFalse(result.eligible)
        self.assertTrue(
            any(
                reason.startswith("REQUIRED_FIELD_MISSING") for reason in result.reasons
            )
        )

    def test_unassessed_packet_classification_fails(self) -> None:
        context, record, _ = self.full_packet()
        external_unassessed = OperatingAssessment(
            OperatingClassification(
                DoseResponseRegion.UNASSESSED, SemanticOutcome.UNASSESSED
            ),
            ClassificationMode.EXTERNAL_UNVERIFIED,
            "external-human-classification-v1",
            self.profile.sha256,
            self.test_point.sha256,
            self.artifacts["unrelated"].ref,
            (),
            None,
            None,
            self.profile.control_bindings,
            context.operation_binding(None, require_integrity=False),
        )
        unassessed = replace(
            record,
            operating_assessment=external_unassessed,
        )
        result = packet_eligibility(context, unassessed)
        self.assertIn("OPERATING_CLASSIFICATION_NOT_ADMISSIBLE", result.reasons)

    def test_unrelated_record_evidence_cannot_cover_field_evidence(self) -> None:
        context, record, _ = self.full_packet()
        unrelated = replace(
            record,
            evidence_refs=(self.artifacts["unrelated"].ref,),
            control_refs=(self.artifacts["control"].ref,),
        )
        result = packet_eligibility(context, unrelated)
        self.assertFalse(result.eligible)
        self.assertTrue(
            any("EVIDENCE_NOT_IN_PACKET" in reason for reason in result.reasons)
        )

    def test_fake_packet_parent_is_unresolved(self) -> None:
        context, record, values = self.full_packet()
        normalized = values["normalized"]
        forged_provenance = replace(
            normalized.q10.provenance,
            derivation_parents=(
                ParentRef("raw_flow", 0, "cas_ohm_v1.artifact-bytes", "F" * 64),
                normalized.q10.provenance.derivation_parents[1],
            ),
        )
        forged_q = replace(normalized.q10, provenance=forged_provenance)
        fields = tuple(
            forged_q if field.field_name == "I_Q" else field for field in record.fields
        )
        result = packet_eligibility(context, replace(record, fields=fields))
        self.assertFalse(result.eligible)
        self.assertTrue(any("UNRESOLVED" in reason for reason in result.reasons))

    def test_packet_controls_are_required_and_linked(self) -> None:
        context, record, _ = self.full_packet()
        result = packet_eligibility(
            context, replace(record, control_refs=(), control_bindings=())
        )
        self.assertFalse(result.eligible)
        self.assertIn("RECORD_CONTROLS_MISSING", result.reasons)

    def test_profile_and_authority_evidence_must_be_inside_packet(self) -> None:
        context, record, _ = self.full_packet()
        omitted = self.profile.code_ref.sha256
        evidence_refs = tuple(
            ref for ref in record.evidence_refs if ref.sha256 != omitted
        )
        result = packet_eligibility(
            context, replace(record, evidence_refs=evidence_refs)
        )
        self.assertFalse(result.eligible)
        self.assertIn(
            f"PROFILE_OR_AUTHORITY_EVIDENCE_NOT_IN_PACKET:{omitted}", result.reasons
        )

    def test_packet_cross_field_values_are_recomputed(self) -> None:
        context, record, values = self.full_packet()
        predicted = values["predicted"]
        forged = replace(predicted, value=predicted.value + Decimal("0.01"))
        fields = tuple(
            forged if field.field_name == "I_pred" else field for field in record.fields
        )
        result = packet_eligibility(context, replace(record, fields=fields))
        self.assertFalse(result.eligible)
        self.assertTrue(
            "CROSS_FIELD_MISMATCH:I_pred" in result.reasons
            or any(
                reason.startswith("CROSS_FIELD_RECOMPUTATION_FAILED")
                for reason in result.reasons
            )
        )

    def coordinate(self, name: str) -> CoordinateIdentity:
        return CoordinateIdentity(
            name,
            QuantityKind.DRIVE_INTERVENTION,
            UnitKind.ALPHA,
            self.test_point.sha256,
        )

    def component(
        self,
        name: str,
        resistance: MeasurementValue,
        source: CoordinateIdentity,
        target: CoordinateIdentity,
    ) -> ResistanceComponent:
        return ResistanceComponent(
            name,
            resistance,
            source,
            target,
            DoseResponseRegion.ACTIVE,
            Decimal("0.99"),
        )

    def test_series_topology_and_children_are_retained(self) -> None:
        r1 = self.calibrated_resistance("2", "R1")
        r2 = self.calibrated_resistance("3", "R2")
        a, b, c = self.coordinate("a"), self.coordinate("b"), self.coordinate("c")
        components = (self.component("c1", r1, a, b), self.component("c2", r2, b, c))
        result = series_equivalent(self.context(objects=(r1, r2)), components)
        self.assertEqual(result.equivalent.value, Decimal("5"))
        self.assertEqual(result.components, components)
        self.assertIsNotNone(result.equivalent.uncertainty)

    def test_invalid_series_or_parallel_topology_is_rejected(self) -> None:
        r1 = self.calibrated_resistance("2", "R1")
        r2 = self.calibrated_resistance("3", "R2")
        a, b, c, d = (
            self.coordinate("a"),
            self.coordinate("b"),
            self.coordinate("c"),
            self.coordinate("d"),
        )
        context = self.context(objects=(r1, r2))
        with self.assertRaises(ValidationError):
            series_equivalent(
                context,
                (self.component("c1", r1, a, b), self.component("c2", r2, c, d)),
            )
        with self.assertRaises(ValidationError):
            parallel_equivalent(
                context,
                (self.component("c1", r1, a, b), self.component("c2", r2, a, c)),
            )

    def test_parallel_topology_computes_equivalent_with_uncertainty(self) -> None:
        r1 = self.calibrated_resistance("2", "R1")
        r2 = self.calibrated_resistance("3", "R2")
        a, b = self.coordinate("a"), self.coordinate("b")
        components = (self.component("c1", r1, a, b), self.component("c2", r2, a, b))
        result = parallel_equivalent(self.context(objects=(r1, r2)), components)
        self.assertEqual(result.equivalent.value, Decimal("1.2"))
        self.assertEqual(result.components, components)

    def test_network_aggregation_requires_component_sample_sizes(self) -> None:
        r1 = replace(self.calibrated_resistance("2", "R1"), sample_size=None)
        r2 = self.calibrated_resistance("3", "R2")
        a, b, c = self.coordinate("a"), self.coordinate("b"), self.coordinate("c")
        components = (
            self.component("c1", r1, a, b),
            self.component("c2", r2, b, c),
        )
        with self.assertRaises(ValidationError):
            series_equivalent(self.context(objects=(r1, r2)), components)

    def test_dimensionless_gain_rejects_cross_unit_coordinates(self) -> None:
        gain = self.gain("g", "2")
        alpha = CoordinateIdentity(
            "alpha",
            QuantityKind.DRIVE_INTERVENTION,
            UnitKind.ALPHA,
            self.test_point.sha256,
        )
        activation = CoordinateIdentity(
            "activation",
            QuantityKind.SIGNED_ACTIVATION,
            UnitKind.ACTIVATION,
            self.test_point.sha256,
        )
        with self.assertRaises(ValidationError):
            GainStage(
                "cross-unit",
                gain,
                alpha,
                activation,
                DoseResponseRegion.ACTIVE,
                Decimal("0.99"),
            )
        with self.assertRaises(ValidationError):
            CoordinateIdentity(
                "invalid",
                QuantityKind.DRIVE_INTERVENTION,
                UnitKind.ACTIVATION,
                self.test_point.sha256,
            )

    def test_gain_composition_validates_typed_chain_and_retains_stages(self) -> None:
        g1, g2 = self.gain("g1", "2"), self.gain("g2", "3")
        x = CoordinateIdentity(
            "x",
            QuantityKind.SIGNED_ACTIVATION,
            UnitKind.ACTIVATION,
            self.test_point.sha256,
        )
        y = replace(x, coordinate_id="y")
        z = replace(x, coordinate_id="z")
        stages = (
            GainStage("s1", g1, x, y, DoseResponseRegion.ACTIVE, Decimal("0.99")),
            GainStage("s2", g2, y, z, DoseResponseRegion.ACTIVE, Decimal("0.99")),
        )
        result = compose_gains(self.context(objects=(g1, g2)), stages)
        self.assertEqual(result.composed_gain.value, Decimal("6"))
        self.assertEqual(result.stages, stages)
        with self.assertRaises(ValidationError):
            compose_gains(
                self.context(objects=(g1, g2)),
                (stages[0], replace(stages[1], source_coordinate=x)),
            )
        missing_sample = replace(g1, sample_size=None)
        missing_stage = replace(stages[0], gain=missing_sample)
        with self.assertRaises(ValidationError):
            compose_gains(
                self.context(objects=(missing_sample, g2)),
                (missing_stage, stages[1]),
            )

    def test_configured_keys_and_clock_never_become_independent_authority(self) -> None:
        clock_artifact = self.make_artifact(
            "clock-provider-record", b"integrity-only-clock-provider-record"
        )
        self.artifacts["clock-provider-record"] = clock_artifact
        receipt = TrustedCapabilityAuthority.sign_current_clock_receipt(
            self.authority.manifest.sha256,
            clock_artifact.ref,
            "reviewer-1",
            "2026-08-05T00:00:00Z",
            "2026-08-05T00:00:01Z",
            "2026-08-05T00:05:00Z",
            self.REVIEWER_PRIVATE_KEY,
        )
        context = self.context(current_clock_receipt=receipt)
        self.assertEqual(context.replay_as_of, "2026-08-04T00:00:00Z")
        self.assertEqual(
            context.operation_binding(
                None, require_integrity=False
            ).clock_receipt_sha256,
            receipt.sha256,
        )
        self.assertFalse(context.authenticated_current)
        self.assertIn(
            "CLOCK_RECEIPT_IS_INTEGRITY_ONLY",
            context.authentication_reasons(Capability.OHMIC_PREDICTION),
        )
        context.require_integrity_attestation(Capability.OHMIC_PREDICTION)
        with self.assertRaises(CapabilityError):
            context.require_capability(Capability.OHMIC_PREDICTION)
        with self.assertRaises(CapabilityError):
            self.context(current_clock_receipt=replace(receipt, signature="0" * 128))
        object.__setattr__(receipt, "signature", "0" * 128)
        with self.assertRaises(ValidationError):
            context.operation_binding(None, require_integrity=False)

    def test_structural_networks_run_without_authenticated_capabilities(self) -> None:
        manifest = AuthorityManifest(
            "structural-research-manifest",
            "1",
            TrustMode.STRUCTURAL_RESEARCH_ONLY,
            (),
        )
        manifest_ref = ArtifactRef(
            "structural-authority-manifest",
            "memory://structural-authority-manifest",
            manifest.sha256,
            "application/vnd.cas-ohm.authority-manifest+json",
        )
        manifest_artifact = ArtifactEvidence(manifest_ref, manifest.canonical_bytes)
        authority = TrustedCapabilityAuthority(manifest, manifest_ref)
        r1 = self.calibrated_resistance("2", "R1")
        r2 = self.calibrated_resistance("3", "R2")
        a, b, c = self.coordinate("a"), self.coordinate("b"), self.coordinate("c")
        components = (
            self.component("c1", r1, a, b),
            self.component("c2", r2, b, c),
        )
        artifacts = (
            tuple(self.artifacts.values())
            + tuple(self.capability_artifacts.values())
            + (manifest_artifact,)
        )
        context = self.context(
            objects=(r1, r2),
            authority=authority,
            attestations=(),
            artifact_evidence=artifacts,
        )
        result = series_equivalent(context, components)
        self.assertEqual(result.equivalent.value, Decimal("5"))
        self.assertEqual(
            result.equivalent.provenance.operation_binding.trust_mode,
            TrustMode.STRUCTURAL_RESEARCH_ONLY,
        )
        with self.assertRaises(CapabilityError):
            context.require_capability(Capability.SERIES_EQUIVALENCE)

    def test_network_equivalent_requires_exact_factory_replay(self) -> None:
        r1 = self.calibrated_resistance("2", "R1")
        r2 = self.calibrated_resistance("3", "R2")
        a, b, c = self.coordinate("a"), self.coordinate("b"), self.coordinate("c")
        components = (
            self.component("c1", r1, a, b),
            self.component("c2", r2, b, c),
        )
        result = series_equivalent(self.context(objects=(r1, r2)), components)
        drive = self.drive()
        replay_context = self.context(objects=(drive, r1, r2) + components)
        replayed = replay_network_equivalent(replay_context, result.equivalent)
        self.assertEqual(replayed.sha256, result.sha256)
        predicted = predict_flow(replay_context, drive, result.equivalent)
        self.assertEqual(predicted.value, Decimal("0.8"))
        with self.assertRaises(ValidationError):
            replace(result.equivalent, field_name="relabelled-network")
        with self.assertRaises(ValidationError):
            replace(result, components=tuple(reversed(components)))

    def test_duplicate_and_cyclic_network_children_are_rejected(self) -> None:
        r1 = self.calibrated_resistance("2", "R1")
        r2 = self.calibrated_resistance("3", "R2")
        a, b, c = self.coordinate("a"), self.coordinate("b"), self.coordinate("c")
        c1 = self.component("c1", r1, a, b)
        context = self.context(objects=(r1, r2))
        with self.assertRaises(ValidationError):
            series_equivalent(context, (c1, c1))
        with self.assertRaises(ValidationError):
            series_equivalent(
                context,
                (c1, self.component("c2", r1, b, c)),
            )
        with self.assertRaises(ValidationError):
            series_equivalent(
                context,
                (c1, self.component("c2", r2, b, a)),
            )

    def test_registry_snapshots_reject_post_admission_mutation(self) -> None:
        artifact = self.make_artifact("snapshot", b"snapshot-bytes")
        registry = EvidenceRegistry((artifact,))
        replacement = ArtifactEvidence(artifact.ref, artifact.payload)
        object.__setattr__(registry, "artifacts", (replacement,))
        with self.assertRaises(ValidationError):
            registry.artifact_for(artifact.ref)

        registry = EvidenceRegistry((artifact,))
        object.__setattr__(artifact, "payload", b"mutated-bytes")
        with self.assertRaises(ValidationError):
            registry.artifact_for(artifact.ref)

        drive = self.drive()
        context = self.context(objects=(drive,))
        object.__setattr__(drive.provenance, "method_id", "mutated-method")
        with self.assertRaises(ValidationError):
            context.validate_measurement(drive)

    def test_canonical_registry_rejects_subclasses_cycles_and_resource_attacks(
        self,
    ) -> None:
        class MappingSubclass(dict):
            pass

        class IntegerSubclass(int):
            pass

        class ForeignEnum(str, Enum):
            VALUE = "VALUE"

        class ForeignCanonicalObject:
            def canonical_payload(self) -> dict[str, object]:
                return {"claim": "smuggled"}

        spoofed_artifact_type = type(
            "ArtifactRef",
            (),
            {
                "__module__": "cas_ohm_v1.model",
                "canonical_payload": lambda self: {"claim": "spoofed"},
            },
        )

        for value in (
            MappingSubclass({"x": 1}),
            IntegerSubclass(1),
            ForeignEnum.VALUE,
            ForeignCanonicalObject(),
            spoofed_artifact_type(),
            "bad-surrogate-\ud800",
        ):
            with (
                self.subTest(value=type(value).__name__),
                self.assertRaises(ValidationError),
            ):
                canonical_bytes(value)
        cycle: list[object] = []
        cycle.append(cycle)
        with self.assertRaises(ValidationError):
            canonical_bytes(cycle)
        nested: object = 0
        for _ in range(70):
            nested = [nested]
        with self.assertRaises(ValidationError):
            canonical_bytes(nested)
        with self.assertRaises(ValidationError):
            canonical_bytes([0] * 10_001)

    def test_exact_type_provenance_and_context_source_bytes_are_enforced(self) -> None:
        class ArtifactRefSubclass(ArtifactRef):
            pass

        base = self.artifacts["source"].ref
        subclass_ref = ArtifactRefSubclass(
            base.artifact_id, base.uri, base.sha256, base.media_type
        )
        with self.assertRaises(ValidationError):
            FieldProvenance((subclass_ref,), "invalid-subclass")
        missing_weights = tuple(
            artifact for name, artifact in self.artifacts.items() if name != "weights"
        ) + tuple(self.capability_artifacts.values())
        with self.assertRaises(ValidationError):
            self.context(artifact_evidence=missing_weights)

    def test_derived_outputs_bind_runtime_authority_and_covariance_limit(self) -> None:
        context, record, values = self.full_packet()
        eligibility = packet_eligibility(context, record)
        bindings = [
            values["predicted"].provenance.operation_binding,
            values["normalized"].q10.provenance.operation_binding,
            values["diagnostic"].residual.provenance.operation_binding,
            record.operating_assessment.operation_binding,
            eligibility.operation_binding,
        ]
        for binding in bindings:
            self.assertIsNotNone(binding)
            self.assertEqual(
                binding.authority_manifest_sha256,
                context.authority.manifest.sha256,
            )
            self.assertEqual(binding.runtime_id, self.profile.runtime_id)
            self.assertEqual(binding.code_ref, self.profile.code_ref)
            self.assertEqual(
                binding.dependency_lock_ref, self.profile.dependency_lock_ref
            )
            self.assertEqual(binding.covariance_limitation, COVARIANCE_LIMITATION)
            self.assertEqual(
                binding.attestation_sha256s,
                tuple(sorted(item.sha256 for item in context.attestations)),
            )

    def test_derived_result_containers_cannot_be_relabelled(self) -> None:
        context, record, values = self.full_packet()
        eligibility = packet_eligibility(context, record)
        r1 = self.calibrated_resistance("2", "R1")
        r2 = self.calibrated_resistance("3", "R2")
        a, b, c = self.coordinate("a"), self.coordinate("b"), self.coordinate("c")
        network = series_equivalent(
            self.context(objects=(r1, r2)),
            (
                self.component("c1", r1, a, b),
                self.component("c2", r2, b, c),
            ),
        )
        g1, g2 = self.gain("g1", "2"), self.gain("g2", "3")
        x = CoordinateIdentity(
            "x",
            QuantityKind.SIGNED_ACTIVATION,
            UnitKind.ACTIVATION,
            self.test_point.sha256,
        )
        y, z = replace(x, coordinate_id="y"), replace(x, coordinate_id="z")
        gain_result = compose_gains(
            self.context(objects=(g1, g2)),
            (
                GainStage("s1", g1, x, y, DoseResponseRegion.ACTIVE, Decimal("0.99")),
                GainStage("s2", g2, y, z, DoseResponseRegion.ACTIVE, Decimal("0.99")),
            ),
        )
        for value in (
            values["normalized"],
            values["diagnostic"],
            record.operating_assessment,
            eligibility,
            network,
            network.equivalent,
            gain_result,
        ):
            with (
                self.subTest(value=type(value).__name__),
                self.assertRaises((ValidationError, TypeError)),
            ):
                replace(value)

    def test_closed_packet_rejects_smuggled_claims_but_allows_typed_nonclaims(
        self,
    ) -> None:
        context, record, _ = self.full_packet()
        unrelated = self.artifacts["unrelated"].ref
        smuggled = replace(record, evidence_refs=record.evidence_refs + (unrelated,))
        result = packet_eligibility(context, smuggled)
        self.assertFalse(result.structurally_complete)
        self.assertIn(
            f"PACKET_EVIDENCE_OUTSIDE_CLOSED_SCHEMA:{unrelated.sha256}",
            result.structural_reasons,
        )
        extension = NonClaimExtension("x-nonclaim-test", "reviewer-note", unrelated)
        extended = replace(
            record,
            evidence_refs=record.evidence_refs + (unrelated,),
            extensions=(extension,),
        )
        extended_result = packet_eligibility(context, extended)
        self.assertTrue(
            extended_result.structurally_complete,
            extended_result.structural_reasons,
        )
        unknown = replace(self.drive(), field_name="unknown-claim")
        with self.assertRaises(ValidationError):
            replace(record, fields=record.fields + (unknown,))

    def test_arithmetic_context_is_fresh_even_if_exported_constant_is_mutated(
        self,
    ) -> None:
        original_precision = canonical_module.CAS_OHM_DECIMAL_PRECISION
        try:
            canonical_module.CAS_OHM_DECIMAL_PRECISION = 2
            with canonical_module.arithmetic_context() as first:
                first.prec = 3
            with canonical_module.arithmetic_context() as second:
                self.assertEqual(second.prec, 50)
            drive, resistance = self.drive("1"), self.calibrated_resistance("3")
            predicted = predict_flow(
                self.context(objects=(drive, resistance)), drive, resistance
            )
            self.assertEqual(
                predicted.value,
                Decimal("0.33333333333333333333333333333333333333333333333333"),
            )
        finally:
            canonical_module.CAS_OHM_DECIMAL_PRECISION = original_precision

    def board(self, fault: SyntheticFault, **overrides: Decimal) -> SyntheticBoard:
        values = {
            "base_resistance": Decimal("2"),
            "cutoff_drive": Decimal("0"),
            "saturation_flow": Decimal("100"),
            "hidden_resistance": Decimal("0"),
            "bypass_reduction": Decimal("0"),
            "off_axis_fraction": Decimal("0"),
            "fault": fault,
        }
        values.update(overrides)
        return SyntheticBoard(**values)

    def classify(
        self,
        observations: tuple[object, ...],
        expected_resistance: Decimal = Decimal("2"),
    ) -> OperatingAssessment:
        payload = canonical_bytes(observations)
        digest = sha256(payload)
        artifact = self.make_artifact(f"sweep-{digest[:12]}", payload)
        self.artifacts[f"sweep-{digest}"] = artifact
        return classify_sweep_point(
            self.context(),
            observations,  # type: ignore[arg-type]
            1,
            expected_resistance,
            artifact.ref,
        )

    def test_synthetic_regions_are_derived_from_numeric_sweeps(self) -> None:
        active = self.board(SyntheticFault.NONE).sweep(
            (Decimal("1"), Decimal("2"), Decimal("3"))
        )
        cutoff = self.board(SyntheticFault.CUTOFF, cutoff_drive=Decimal("2")).sweep(
            (Decimal("1"), Decimal("1.5"), Decimal("2"))
        )
        non_ohmic = self.board(SyntheticFault.NON_OHMIC).sweep(
            (Decimal("1"), Decimal("2"), Decimal("3"))
        )
        self.assertIs(
            self.classify(active).region,
            DoseResponseRegion.ACTIVE,
        )
        self.assertIs(
            self.classify(cutoff).region,
            DoseResponseRegion.CUTOFF,
        )
        self.assertIs(
            self.classify(non_ohmic).region,
            DoseResponseRegion.NON_OHMIC,
        )

    def test_saturation_threshold_edge_is_derived_as_saturation(self) -> None:
        observations = self.board(
            SyntheticFault.SATURATION, saturation_flow=Decimal("2")
        ).sweep((Decimal("3"), Decimal("4"), Decimal("5")))
        self.assertEqual(observations[1].flow, Decimal("2"))
        classification = self.classify(observations)
        self.assertIs(classification.region, DoseResponseRegion.SATURATION)

    def test_off_axis_semantics_are_derived_from_numeric_projection(self) -> None:
        observations = self.board(
            SyntheticFault.OFF_AXIS, off_axis_fraction=Decimal("0.5")
        ).sweep((Decimal("1"), Decimal("2"), Decimal("3")))
        classification = self.classify(observations)
        self.assertIs(classification.region, DoseResponseRegion.ACTIVE)
        self.assertIs(classification.semantic_outcome, SemanticOutcome.OFF_AXIS)

    def test_hidden_constraint_and_bypass_have_opposite_resistance_deltas(self) -> None:
        _, drive, resistance, predicted, _ = self.prediction_fixture()
        hidden_flow = (
            self.board(SyntheticFault.HIDDEN_CONSTRAINT, hidden_resistance=Decimal("2"))
            .observe(Decimal("4"))
            .flow
        )
        bypass_flow = (
            self.board(SyntheticFault.BYPASS, bypass_reduction=Decimal("1"))
            .observe(Decimal("4"))
            .flow
        )
        results = []
        for flow in (hidden_flow, bypass_flow):
            observed = self.instrumented_flow(flow, radius=Decimal("0.05"))
            local_context = self.context(
                objects=(drive, resistance, predicted, observed)
            )
            results.append(
                diagnose_residual(
                    local_context,
                    drive,
                    predicted,
                    observed,
                    resistance,
                    self.external_assessment(
                        local_context,
                        OperatingClassification(
                            DoseResponseRegion.ACTIVE, SemanticOutcome.INTENDED
                        ),
                    ),
                )
            )
        self.assertGreater(results[0].resistance_delta.value, 0)
        self.assertLess(results[1].resistance_delta.value, 0)


if __name__ == "__main__":
    unittest.main()
