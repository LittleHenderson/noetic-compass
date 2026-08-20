from __future__ import annotations

import hashlib
import hmac
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
SRC = BASE / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from weld_v3.actor import run_actor_phase  # noqa: E402
from weld_v3.adjudicate import adjudicate  # noqa: E402
from weld_v3.core import (  # noqa: E402
    FIXED_PIPELINE,
    WeldProtocolError,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    utc_now,
)
from weld_v3.freeze import create_freeze  # noqa: E402
from weld_v3.runtime import ISOLATION_CONTRACT, version_evidence_bytes  # noqa: E402


TARGET_ID = "a" * 32
CONTROL_ID = "b" * 32


MOCK_ADAPTER = r'''
import hashlib
import json
import os
import sys
from pathlib import Path

PIPELINE = [
    "INGEST_PUBLIC_CARRIER",
    "J1_CONTRACT_GATE",
    "COMPILE_OR_VALIDATE_ARTIFACT",
    "DIAGNOSE",
    "LOCALIZE",
    "REPAIR",
    "VERIFY",
    "J2_CONTRACT_GATE",
    "STAGE5_CONTRACT_GATE",
    "EMIT_DECISION",
]

if sys.argv[1:] == ["--version-json"]:
    print('{"adapter":"weld-v3-mock","version":"1.0.0"}')
    raise SystemExit(0)

if "WELD_TRUTH_PATH" in os.environ or (Path.cwd() / "sealed_truth.json").exists():
    raise SystemExit(91)

raw = sys.stdin.buffer.read()
case = json.loads(raw.decode("utf-8"))
signal = case["carrier"]["fixture_signal"]
decision = {
    "repair": "REPAIR_ACCEPTED",
    "intact": "NO_REPAIR_NEEDED",
}[signal]
output = {
    "schema_version": "weld-v3-actor-output/1",
    "case_id": case["case_id"],
    "input_sha256": hashlib.sha256(raw).hexdigest(),
    "pipeline_id": "WELD-V3-FIXED-PIPELINE-1",
    "pipeline_trace": PIPELINE,
    "decision": decision,
    "diagnosis_code": "MOCK_FIXED_DIAGNOSIS",
    "localization_ref": "mock:one-pipeline",
    "repair_ref": "mock:one-pipeline" if decision == "REPAIR_ACCEPTED" else None,
    "verification_code": "MOCK_FIXED_VERIFY",
    "model_adapter_status": {"J1": "NOT_RUN", "J2": "NOT_RUN", "STAGE5": "NOT_RUN"},
}
sys.stdout.write(json.dumps(output, sort_keys=True, separators=(",", ":")))
'''.lstrip()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def public_cases(
    *,
    leak_truth_key: bool = False,
    mismatch_control_profile: bool = False,
    mismatch_control_shape: bool = False,
    numeric_mismatch: bool = False,
    boolean_mismatch: bool = False,
    token_length_mismatch: bool = False,
    control_signal: str = "intact",
) -> dict:
    common_profile = {
        "carrier_kind": "MODEL_FACING_ARTIFACT_CHAIN",
        "artifact_slots": [
            "CIRCUIT_READING",
            "CAS_EXPRESSION",
            "COMPILATION_ARTIFACT",
            "CORRECTED_EXPRESSION",
            "EPSILON_PREFIX",
            "HELD_OUT_CONTINUATION",
        ],
        "available_contracts": ["J1", "J2", "STAGE5"],
        "missingness_pattern": "CONTRACTS_ONLY_NO_MODEL_EXECUTION",
        "shape_sha256": "f" * 64,
    }
    control_profile = dict(common_profile)
    if mismatch_control_profile:
        control_profile["missingness_pattern"] = "DIFFERENT_INFORMATION"

    def make_case(
        case_id: str,
        signal: str,
        seed: str,
        profile: dict,
        *,
        add_shape_field: bool = False,
        observation_count: int = 7,
        feature_enabled: bool = True,
        surface_tokens: str = "aa b",
    ) -> dict:
        carrier = {
            "artifact_chain": {
                "circuit_reading_sha256": seed * 64,
                "cas_expression_sha256": "2" * 64,
                "compilation_artifact_sha256": "3" * 64,
                "corrected_expression_sha256": "4" * 64,
                "epsilon_prefix_sha256": "5" * 64,
                "held_out_continuation_sha256": "6" * 64,
            },
            "fixture_signal": signal,
            "observation_count": observation_count,
            "feature_enabled": feature_enabled,
            "surface_tokens": surface_tokens,
        }
        if add_shape_field:
            carrier["extra_public_bytes"] = "shape-mismatch"
        if leak_truth_key:
            carrier["truth"] = "must never reach actor"
        return {
            "schema_version": "weld-v3-public-case/1",
            "case_id": case_id,
            "carrier_kind": "MOCK_CONTRACT_FIXTURE",
            "carrier": carrier,
            "information_profile": profile,
            "model_adapter_status": {"J1": "NOT_RUN", "J2": "NOT_RUN", "STAGE5": "NOT_RUN"},
        }

    return {
        "schema_version": "weld-v3-public-cases/1",
        "cases": [
            make_case(TARGET_ID, "repair", "1", common_profile),
            make_case(
                CONTROL_ID,
                control_signal,
                "7",
                control_profile,
                add_shape_field=mismatch_control_shape,
                observation_count=8 if numeric_mismatch else 7,
                feature_enabled=not boolean_mismatch,
                surface_tokens="a bb" if token_length_mismatch else "aa b",
            ),
        ],
    }


def sealed_truth() -> dict:
    return {
        "schema_version": "weld-v3-sealed-truth/1",
        "protocol_id": "WELD-V3-SEALED-FIXED-PIPELINE-2",
        "pairs": [
            {
                "pair_id": "opaque-pair-01",
                "target_case_id": TARGET_ID,
                "control_case_id": CONTROL_ID,
                "target_expected_decision": "REPAIR_ACCEPTED",
                "control_expected_decision": "NO_REPAIR_NEEDED",
            }
        ],
    }


class Bundle:
    def __init__(
        self,
        root: Path,
        *,
        control_signal: str = "intact",
        leak_truth_key: bool = False,
        mismatch_control_profile: bool = False,
        mismatch_control_shape: bool = False,
        numeric_mismatch: bool = False,
        boolean_mismatch: bool = False,
        token_length_mismatch: bool = False,
        production_without_sources: bool = False,
        fake_python_as_rust: bool = False,
    ) -> None:
        self.root = root
        self.prereg = root / "prereg"
        self.result = root / "result"
        self.truth_path = root / "custodian" / "sealed_truth.json"
        self.commitment_evidence_path = root / "custodian" / "external_commitment_evidence.json"
        self.actor_seal_path = root / "custodian" / "actor_receipt_seal.json"
        self.release_path = root / "custodian" / "custodian_release.json"
        self.adapter = root / "mock_adapter.py"
        self.custodian_id = "external-test-custodian"
        self.commitment_receipt_id = "external-commitment-receipt-test-001"
        self.salt = bytes(range(32))
        self.hmac_key = bytes(range(32, 64))
        self.prereg.mkdir(parents=True)
        self.adapter.write_text(MOCK_ADAPTER, encoding="utf-8", newline="\n")

        protocol = json.loads((BASE / "protocol" / "protocol.json").read_text(encoding="utf-8"))
        contracts = json.loads(
            (BASE / "adapter_contracts" / "model_adapter_contracts.json").read_text(
                encoding="utf-8"
            )
        )
        write_json(self.prereg / "protocol.json", protocol)
        write_json(
            self.prereg / "public_cases.json",
            public_cases(
                leak_truth_key=leak_truth_key,
                mismatch_control_profile=mismatch_control_profile,
                mismatch_control_shape=mismatch_control_shape,
                numeric_mismatch=numeric_mismatch,
                boolean_mismatch=boolean_mismatch,
                token_length_mismatch=token_length_mismatch,
                control_signal=control_signal,
            ),
        )
        write_json(self.prereg / "model_adapter_contracts.json", contracts)

        truth = sealed_truth()
        self.truth = truth
        write_json(
            self.commitment_evidence_path,
            {
                "schema_version": "weld-v3-external-commitment-evidence/1",
                "custodian_id": self.custodian_id,
                "external_commitment_receipt_id": self.commitment_receipt_id,
                "created_utc": "2026-08-20T00:00:00Z",
                "entropy_source": "EXTERNAL_OS_CSPRNG_AT_LEAST_256_BITS",
                "hmac_key_size_bytes": len(self.hmac_key),
                "salt_size_bytes": len(self.salt),
                "commitment_status": "EXTERNALLY_ANCHORED_BEFORE_FREEZE",
                "external_anchor_id": "mock-external-anchor-commitment-001",
            },
        )
        truth_bytes = canonical_json_bytes(truth)
        message = b"WELD-V3-SEALED-TRUTH-V2\x00" + self.salt + b"\x00" + truth_bytes
        truth_hmac = hmac.new(self.hmac_key, message, hashlib.sha256).hexdigest()
        write_json(
            self.prereg / "truth_commitment.json",
            {
                "schema_version": "weld-v3-truth-commitment/2",
                "algorithm": "hmac-sha256",
                "domain_separator": "WELD-V3-SEALED-TRUTH-V2",
                "salt_hex": self.salt.hex(),
                "hmac_key_sha256": hashlib.sha256(self.hmac_key).hexdigest(),
                "sealed_truth_hmac_sha256": truth_hmac,
                "custodian_id": self.custodian_id,
                "external_commitment_receipt_id": self.commitment_receipt_id,
                "external_commitment_receipt_sha256": sha256_file(
                    self.commitment_evidence_path
                ),
                "entropy_source": "EXTERNAL_OS_CSPRNG_AT_LEAST_256_BITS",
                "hmac_key_size_bytes": len(self.hmac_key),
                "salt_size_bytes": len(self.salt),
                "custody": "EXTERNAL_UNAVAILABLE_DURING_ACTOR_PHASE",
                "commitment_status": "EXTERNALLY_COMMITTED",
            },
        )

        executable = Path(sys.executable).resolve()
        runtime_probe = version_evidence_bytes([str(executable), "--version"])
        adapter_probe = version_evidence_bytes(
            [str(executable), str(self.adapter.resolve()), "--version-json"]
        )
        production = production_without_sources or fake_python_as_rust
        profile = "PRODUCTION_RUST" if production else "MOCK_TEST_ONLY"
        adapter_language = "rust" if production else "python-mock"
        adapter_path = executable if production else self.adapter.resolve()
        adapter_version_probe = runtime_probe if production else adapter_probe
        source_bindings = []
        rust_version_claim = None
        if fake_python_as_rust:
            crate_root = root / "fake-cas-engine"
            cargo_toml = crate_root / "Cargo.toml"
            cargo_lock = crate_root / "Cargo.lock"
            scanner = crate_root / "src" / "inversions" / "mod.rs"
            cargo_toml.parent.mkdir(parents=True, exist_ok=True)
            scanner.parent.mkdir(parents=True, exist_ok=True)
            cargo_toml.write_text(
                '[package]\nname = "cas-engine"\nversion = "0.1.1"\n',
                encoding="utf-8",
                newline="\n",
            )
            cargo_lock.write_text(
                'version = 3\n\n[[package]]\nname = "cas-engine"\nversion = "0.1.1"\n',
                encoding="utf-8",
                newline="\n",
            )
            scanner.write_text("// fake source identity only\n", encoding="utf-8", newline="\n")
            source_bindings = [
                {
                    "label": label,
                    "absolute_path": str(path.resolve()),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
                for label, path in (
                    ("Cargo.toml", cargo_toml),
                    ("Cargo.lock", cargo_lock),
                    ("scanner_source", scanner),
                )
            ]
            rust_version_claim = {
                "schema_version": "weld-v3-rust-version/1",
                "language": "rust",
                "binary_kind": "RUST_NATIVE_EXECUTABLE",
                "crate_name": "cas-engine",
                "crate_version": "0.1.1",
                "protocol_id": "WELD-V3-SEALED-FIXED-PIPELINE-2",
                "rustc_version": "rustc fake-test",
                "target_triple": "fake-test-target",
                "cargo_toml_sha256": sha256_file(cargo_toml),
                "cargo_lock_sha256": sha256_file(cargo_lock),
                "scanner_source_sha256": sha256_file(scanner),
            }
        binding = {
            "schema_version": "weld-v3-runtime-binding/1",
            "profile": profile,
            "binding_status": "BOUND",
            "runtime": {
                "absolute_path": str(executable),
                "sha256": sha256_file(executable),
                "size_bytes": executable.stat().st_size,
                "version_argv": ["--version"],
                "version_evidence_sha256": sha256_bytes(runtime_probe),
            },
            "adapter": {
                "absolute_path": str(adapter_path),
                "sha256": sha256_file(adapter_path),
                "size_bytes": adapter_path.stat().st_size,
                "version_argv": ["--version"] if production else ["--version-json"],
                "version_evidence_sha256": sha256_bytes(adapter_version_probe),
                "language": adapter_language,
                "crate_name": "cas-engine" if production else "weld-v3-mock",
                "crate_version": "0.1.1" if production else "test-1.0.0",
            },
            "rust_version_claim": rust_version_claim,
            "source_bindings": source_bindings,
            "isolation_contract": dict(ISOLATION_CONTRACT),
        }
        write_json(self.prereg / "runtime_binding.json", binding)
        self.freeze_path = self.prereg / "freeze_receipt.json"

    def freeze(self) -> dict:
        return dict(create_freeze(self.prereg, self.result, allow_mock=True))

    def release_truth(self) -> None:
        if not self.actor_seal_path.is_file():
            raise AssertionError("test must externally seal actor receipt before truth release")
        write_json(self.truth_path, self.truth)
        actor_path = self.result / "actor_receipt.json"
        write_json(
            self.release_path,
            {
                "schema_version": "weld-v3-custodian-release/1",
                "release_status": "RELEASED_AFTER_EXTERNALLY_ANCHORED_ACTOR_RECEIPT",
                "custodian_id": self.custodian_id,
                "external_commitment_receipt_id": self.commitment_receipt_id,
                "actor_receipt_seal_sha256": sha256_file(self.actor_seal_path),
                "actor_receipt_sha256": sha256_file(actor_path),
                "hmac_key_hex": self.hmac_key.hex(),
                "released_utc": utc_now(),
                "external_release_receipt_id": "mock-external-release-receipt-001",
            },
        )

    def seal_actor_receipt(self) -> None:
        actor_path = self.result / "actor_receipt.json"
        actor = json.loads(actor_path.read_text(encoding="utf-8"))
        write_json(
            self.actor_seal_path,
            {
                "schema_version": "weld-v3-actor-receipt-seal/1",
                "seal_status": "EXTERNALLY_ANCHORED",
                "freeze_id": actor["freeze_id"],
                "actor_receipt_sha256": sha256_file(actor_path),
                "actor_receipt_size_bytes": actor_path.stat().st_size,
                "actor_invocation_count": actor["invocation_count"],
                "actor_output_count": len(actor["outputs"]),
                "custodian_id": self.custodian_id,
                "external_anchor_id": "mock-external-actor-seal-001",
                "seal_nonce_hex": bytes(range(64, 96)).hex(),
                "sealed_utc": utc_now(),
                "truth_release_status_at_seal": "NOT_RELEASED",
            },
        )

    def adjudicate(self) -> dict:
        return dict(
            adjudicate(
                self.freeze_path,
                self.truth_path.resolve(),
                self.actor_seal_path.resolve(),
                self.release_path.resolve(),
                self.commitment_evidence_path.resolve(),
            )
        )


class WeldV3ProtocolTests(unittest.TestCase):
    def test_end_to_end_mock_uses_one_pipeline_and_truth_is_released_later(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary))
            freeze = bundle.freeze()
            self.assertEqual(freeze["profile"], "MOCK_TEST_ONLY")
            self.assertFalse(bundle.truth_path.exists())

            actor = run_actor_phase(bundle.freeze_path)
            self.assertFalse(bundle.truth_path.exists())
            self.assertEqual(actor["truth_channel"], "COMMITMENT_ONLY_NO_PLAINTEXT_ARGUMENT")
            self.assertEqual(len(actor["outputs"]), 2)
            for output in actor["outputs"]:
                self.assertEqual(tuple(output["pipeline_trace"]), FIXED_PIPELINE)
                self.assertEqual(
                    output["model_adapter_status"],
                    {"J1": "NOT_RUN", "J2": "NOT_RUN", "STAGE5": "NOT_RUN"},
                )

            bundle.seal_actor_receipt()
            bundle.release_truth()
            result = bundle.adjudicate()
            self.assertEqual(result["overall_verdict"], "PASS")
            self.assertEqual(result["claim_ceiling"], "MOCK_PROTOCOL_TEST_ONLY")
            pair = result["pair_results"][0]
            self.assertEqual(pair["target_verdict"], "PASS")
            self.assertEqual(pair["control_verdict"], "PASS")
            self.assertEqual(pair["information_match_verdict"], "PASS")

    def test_control_is_verdict_bearing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary), control_signal="repair")
            bundle.freeze()
            run_actor_phase(bundle.freeze_path)
            bundle.seal_actor_receipt()
            bundle.release_truth()
            result = bundle.adjudicate()
            pair = result["pair_results"][0]
            self.assertEqual(pair["target_verdict"], "PASS")
            self.assertEqual(pair["control_verdict"], "FAIL")
            self.assertEqual(pair["pair_verdict"], "FAIL")
            self.assertEqual(result["overall_verdict"], "FAIL")

    def test_information_mismatch_fails_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary), mismatch_control_profile=True)
            bundle.freeze()
            run_actor_phase(bundle.freeze_path)
            bundle.seal_actor_receipt()
            bundle.release_truth()
            result = bundle.adjudicate()
            pair = result["pair_results"][0]
            self.assertEqual(pair["target_verdict"], "PASS")
            self.assertEqual(pair["control_verdict"], "PASS")
            self.assertEqual(pair["information_match_verdict"], "FAIL")
            self.assertEqual(result["overall_verdict"], "FAIL")

    def test_mechanically_observed_carrier_shape_mismatch_fails_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary), mismatch_control_shape=True)
            bundle.freeze()
            run_actor_phase(bundle.freeze_path)
            bundle.seal_actor_receipt()
            bundle.release_truth()
            result = bundle.adjudicate()
            pair = result["pair_results"][0]
            self.assertEqual(pair["target_verdict"], "PASS")
            self.assertEqual(pair["control_verdict"], "PASS")
            self.assertEqual(pair["information_match_verdict"], "FAIL")
            self.assertEqual(result["overall_verdict"], "FAIL")

    def test_public_truth_key_is_rejected_before_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary), leak_truth_key=True)
            with self.assertRaisesRegex(WeldProtocolError, "forbidden truth-bearing key"):
                bundle.freeze()

    def test_frozen_public_input_mutation_blocks_actor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary))
            bundle.freeze()
            with (bundle.prereg / "public_cases.json").open("ab") as stream:
                stream.write(b" ")
            with self.assertRaisesRegex(WeldProtocolError, "frozen file changed"):
                run_actor_phase(bundle.freeze_path)

    def test_bound_adapter_mutation_blocks_actor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary))
            bundle.freeze()
            with bundle.adapter.open("a", encoding="utf-8") as stream:
                stream.write("\n# mutation after freeze\n")
            with self.assertRaisesRegex(WeldProtocolError, "bound file byte count changed"):
                run_actor_phase(bundle.freeze_path)

    def test_result_must_not_precede_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary))
            bundle.result.mkdir()
            (bundle.result / "premature.txt").write_text("result first", encoding="utf-8")
            with self.assertRaisesRegex(WeldProtocolError, "preregistration must precede results"):
                bundle.freeze()

    def test_truth_hash_mismatch_blocks_adjudication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary))
            bundle.freeze()
            run_actor_phase(bundle.freeze_path)
            bundle.seal_actor_receipt()
            bundle.release_truth()
            with bundle.truth_path.open("ab") as stream:
                stream.write(b" ")
            with self.assertRaisesRegex(WeldProtocolError, "does not match"):
                bundle.adjudicate()

    def test_production_profile_requires_rust_source_pins(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary), production_without_sources=True)
            with self.assertRaisesRegex(WeldProtocolError, "production source bindings"):
                bundle.freeze()

    def test_fake_python_executable_cannot_claim_production_rust(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary), fake_python_as_rust=True)
            with self.assertRaisesRegex(WeldProtocolError, "did not emit one JSON object"):
                bundle.freeze()

    def test_zero_invocation_fabricated_receipt_is_rejected_even_if_sealed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary))
            bundle.freeze()
            run_actor_phase(bundle.freeze_path)
            actor_path = bundle.result / "actor_receipt.json"
            actor = json.loads(actor_path.read_text(encoding="utf-8"))
            actor["invocation_count"] = 0
            actor["invocations"] = []
            write_json(actor_path, actor)
            bundle.seal_actor_receipt()
            bundle.release_truth()
            with self.assertRaisesRegex(WeldProtocolError, "no adapter invocations"):
                bundle.adjudicate()

    def test_actor_receipt_mutation_after_truth_release_breaks_external_seal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary))
            bundle.freeze()
            run_actor_phase(bundle.freeze_path)
            bundle.seal_actor_receipt()
            bundle.release_truth()
            with (bundle.result / "actor_receipt.json").open("ab") as stream:
                stream.write(b" ")
            with self.assertRaisesRegex(WeldProtocolError, "changed after its external seal"):
                bundle.adjudicate()

    def test_actor_attestations_must_equal_freeze_not_only_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary))
            bundle.freeze()
            run_actor_phase(bundle.freeze_path)
            actor_path = bundle.result / "actor_receipt.json"
            actor = json.loads(actor_path.read_text(encoding="utf-8"))
            forged = {"same_forged_attestation": True}
            actor["runtime_pre_attestation"] = forged
            actor["runtime_post_attestation"] = forged
            write_json(actor_path, actor)
            bundle.seal_actor_receipt()
            bundle.release_truth()
            with self.assertRaisesRegex(WeldProtocolError, "differ from the freeze"):
                bundle.adjudicate()

    def test_low_entropy_repeated_salt_is_rejected_before_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary))
            path = bundle.prereg / "truth_commitment.json"
            commitment = json.loads(path.read_text(encoding="utf-8"))
            commitment["salt_hex"] = "00" * 32
            write_json(path, commitment)
            with self.assertRaisesRegex(WeldProtocolError, "byte-diversity"):
                bundle.freeze()

    def test_numeric_value_mismatch_fails_information_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary), numeric_mismatch=True)
            bundle.freeze()
            run_actor_phase(bundle.freeze_path)
            bundle.seal_actor_receipt()
            bundle.release_truth()
            result = bundle.adjudicate()
            self.assertEqual(result["pair_results"][0]["information_match_verdict"], "FAIL")

    def test_boolean_value_mismatch_fails_information_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary), boolean_mismatch=True)
            bundle.freeze()
            run_actor_phase(bundle.freeze_path)
            bundle.seal_actor_receipt()
            bundle.release_truth()
            result = bundle.adjudicate()
            self.assertEqual(result["pair_results"][0]["information_match_verdict"], "FAIL")

    def test_equal_byte_strings_with_different_token_lengths_do_not_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary), token_length_mismatch=True)
            bundle.freeze()
            run_actor_phase(bundle.freeze_path)
            bundle.seal_actor_receipt()
            bundle.release_truth()
            result = bundle.adjudicate()
            self.assertEqual(result["pair_results"][0]["information_match_verdict"], "FAIL")

    def test_nested_result_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary))
            bundle.result = bundle.prereg / "nested-result"
            with self.assertRaisesRegex(WeldProtocolError, "must not be nested"):
                bundle.freeze()

    def test_each_case_has_a_unique_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Bundle(Path(temporary))
            bundle.freeze()
            actor = run_actor_phase(bundle.freeze_path)
            tokens = [record["isolated_cwd_token"] for record in actor["invocations"]]
            self.assertEqual(actor["invocation_count"], len(actor["outputs"]))
            self.assertEqual(len(tokens), len(set(tokens)))

    def test_control_plane_has_no_ambient_cas_import_or_numeric_decision_rule(self) -> None:
        sources = list((BASE / "src" / "weld_v3").glob("*.py"))
        combined = "\n".join(path.read_text(encoding="utf-8").casefold() for path in sources)
        self.assertNotIn("import cas_engine", combined)
        for path in (BASE / "src" / "weld_v3" / "actor.py", BASE / "src" / "weld_v3" / "adjudicate.py"):
            text = path.read_text(encoding="utf-8").casefold()
            self.assertNotIn("severity", text)
            self.assertNotIn("satisfaction", text)
            self.assertNotIn("mean_logprob", text)


if __name__ == "__main__":
    unittest.main()
