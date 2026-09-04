"""Reproduce the v0.2 fail-closed compute-plan mismatch rejection.

This evidence-layer probe loads fixture builders from the pinned source tree,
but it imports ``cas_cjt`` from the installed environment.  It deliberately
changes one otherwise well-formed compute-plan value and rebinds every direct
downstream reference before asking the coordinator to commit the batch.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from importlib.metadata import distribution
import json
from dataclasses import replace
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
from typing import Any

import cas_cjt
from cas_cjt.contracts import canonical_digest, canonical_json
from cas_cjt.proposals import state_update_intents_for_successor
from cas_cjt.state import advance_bias
from cas_cjt.types import OperatingRegion, SemanticOutcome, TickPhase


PROBE_ID = "casformer-v0.2.compute-plan-mismatch/1"
EXPECTED_REASON = "COMPUTE_PLAN_NOT_REPRODUCIBLE"
AUTHORITATIVE_TABLES = (
    "published_effects",
    "memory_records",
    "repair_frames",
    "repair_outcomes",
    "transition_batches",
    "candidate_effects",
    "verifier_receipts",
    "qualification_receipts",
    "state_intents",
    "model_intents",
    "memory_intents",
    "commit_receipts",
)


def _thaw(value: Any) -> Any:
    """Return a mutable JSON value from a frozen contract mapping."""

    return json.loads(canonical_json(value))


def _load_frozen_helpers(source_root: Path) -> ModuleType:
    helper_path = source_root / "tests" / "test_network_coordinator.py"
    if not helper_path.is_file():
        raise AssertionError("PINNED_HELPER_MODULE_MISSING")
    module_name = "casformer_v02_frozen_network_test_helpers"
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    if spec is None or spec.loader is None:
        raise AssertionError("PINNED_HELPER_MODULE_NOT_LOADABLE")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _assert_installed_package(source_root: Path) -> None:
    module_file = getattr(cas_cjt, "__file__", None)
    if not isinstance(module_file, str) or not module_file:
        raise AssertionError("CAS_CJT_IMPORT_LOCATION_UNAVAILABLE")
    try:
        Path(module_file).resolve().relative_to(source_root)
    except ValueError:
        pass
    else:
        raise AssertionError("CAS_CJT_IMPORTED_FROM_PINNED_SOURCE_NOT_WHEEL")
    installed_distribution = distribution("cas-neural-cjt")
    if installed_distribution.version != "0.2.0":
        raise AssertionError("CAS_CJT_INSTALLED_VERSION_NOT_0_2_0")
    distribution_root = Path(
        installed_distribution.locate_file("")
    ).resolve()
    try:
        Path(module_file).resolve().relative_to(distribution_root)
    except ValueError as error:
        raise AssertionError(
            "CAS_CJT_IMPORT_NOT_FROM_INSTALLED_DISTRIBUTION"
        ) from error
    wheel_metadata = tuple(
        item
        for item in (installed_distribution.files or ())
        if str(item).replace("\\", "/").endswith(".dist-info/WHEEL")
    )
    if len(wheel_metadata) != 1 or not Path(
        installed_distribution.locate_file(wheel_metadata[0])
    ).is_file():
        raise AssertionError("CAS_CJT_WHEEL_METADATA_MISSING")


def _table_counts(store: Any) -> dict[str, int]:
    return {
        table: store._connection.execute(
            f"SELECT COUNT(*) AS count FROM {table}"
        ).fetchone()["count"]
        for table in AUTHORITATIVE_TABLES
    }


def _forge_plan_bindings(
    helpers: ModuleType,
    records: tuple[Any, ...],
) -> tuple[tuple[Any, ...], dict[str, Any], Any]:
    route = next(item for item in records if item.phase is TickPhase.ROUTE)
    observe = next(item for item in records if item.phase is TickPhase.OBSERVE)
    forged_plan = _thaw(route.outputs["compute_plan"])
    original_value = _thaw(forged_plan["reasoning_step_quanta"])
    if original_value != [[3]]:
        raise AssertionError("UNEXPECTED_FROZEN_COMPUTE_PLAN_BASELINE")
    forged_plan["reasoning_step_quanta"] = [[2]]

    manifest = _thaw(route.inputs["control_binding_manifest"])
    manifest["compute_plan"] = _thaw(forged_plan)
    rebound = helpers._replace_phase(
        records,
        TickPhase.ROUTE,
        inputs={
            **dict(route.inputs),
            "control_binding_manifest": manifest,
        },
        outputs={
            **dict(route.outputs),
            "compute_plan": _thaw(forged_plan),
        },
    )
    diagnostics = {
        **dict(observe.diagnostics),
        "control_binding_digest": canonical_digest(manifest),
    }
    rebound = tuple(
        replace(item, diagnostics=diagnostics)
        if item.phase is TickPhase.OBSERVE
        else item
        for item in rebound
    )
    return rebound, forged_plan, original_value


def _run(source_root: Path) -> dict[str, Any]:
    source_root = source_root.resolve()
    manifest_path = source_root / "SOURCE_MANIFEST.json"
    if not manifest_path.is_file():
        raise AssertionError("PINNED_SOURCE_MANIFEST_MISSING")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("file_count") != 50:
        raise AssertionError("PINNED_SOURCE_FILE_COUNT_NOT_50")
    _assert_installed_package(source_root)
    helpers = _load_frozen_helpers(source_root)

    with TemporaryDirectory(ignore_cleanup_errors=True) as temporary_directory:
        fixture = helpers._open(Path(temporary_directory))
        try:
            original = helpers._batch(
                fixture,
                batch_id="compute-plan-reproduction-mismatch",
            )
            preliminary_phases, _, _ = _forge_plan_bindings(
                helpers,
                original.phase_records,
            )
            candidate = helpers._bind_candidate_to_phases(
                fixture.candidate,
                preliminary_phases,
            )
            receipt = helpers._reidentify_receipt(
                fixture.receipt,
                candidate_effect_id=candidate.candidate_effect_id,
                candidate_effect_digest=candidate.candidate_digest,
            )

            old_bias = fixture.state.by_cjt_id[candidate.producer_cjt_id]
            accepted_bias = advance_bias(
                old_bias,
                tick=fixture.cause.tick,
                region=OperatingRegion.ACTIVE,
                semantic_outcome=SemanticOutcome.INTENDED,
                verifier_receipt_id=receipt.receipt_id,
                cause_id=fixture.cause.cause_id,
                effect_id=candidate.candidate_effect_id,
            )
            after = fixture.state.successor(
                biases=(
                    accepted_bias if item.bias_id == old_bias.bias_id else item
                    for item in fixture.state.biases
                )
            )
            state_intents = state_update_intents_for_successor(
                old_bias,
                accepted_bias,
                tick=fixture.cause.tick,
                receipt=receipt,
                issuer_id=candidate.producer_cjt_id,
            )

            clean_final_phases = helpers._phases(
                tick=1,
                before=fixture.state,
                after=after,
                cause_id=fixture.cause.cause_id,
                candidate_ids=(candidate.candidate_effect_id,),
                receipt_ids=(receipt.receipt_id,),
                operation_ids=("^6",),
                operation_contract_ids=(fixture.contract.contract_id,),
                state_intent_ids=tuple(
                    item.intent_id for item in state_intents
                ),
                artifact_ids=(candidate.content_ref.artifact_id,),
            )
            final_phases, forged_plan, original_value = _forge_plan_bindings(
                helpers,
                clean_final_phases,
            )
            if (
                helpers._bind_candidate_to_phases(
                    fixture.candidate,
                    final_phases,
                )
                != candidate
            ):
                raise AssertionError("CANDIDATE_CONTROL_BINDING_NOT_REBOUND")
            by_phase = {item.phase: item for item in final_phases}
            poisoned = replace(
                original,
                state_after=after,
                candidate_effects=(candidate,),
                verifier_receipts=(receipt,),
                state_intents=state_intents,
                phase_records=final_phases,
                compute_plan=forged_plan,
                compute_observations=by_phase[
                    TickPhase.OBSERVE
                ].outputs["compute_observations"],
            )

            before_head = fixture.store.head
            before_traces = fixture.store.trace_events()
            before_counts = _table_counts(fixture.store)
            before_audits = fixture.store.rejection_audits()
            helpers._assert_rejected_atomically(
                fixture,
                poisoned,
                EXPECTED_REASON,
            )
            after_head = fixture.store.head
            after_traces = fixture.store.trace_events()
            after_counts = _table_counts(fixture.store)
            after_audits = fixture.store.rejection_audits()
            rejection = after_audits[-1]
            integrity = fixture.store.verify_integrity()

            exact_assertions = {
                "authoritative_table_counts_unchanged": (
                    after_counts == before_counts
                ),
                "head_unchanged": after_head == before_head,
                "integrity": integrity is True,
                "rejection_audit_delta": (
                    len(after_audits) - len(before_audits)
                ),
                "rejection_reason_exact": rejection["reason_codes"]
                == [EXPECTED_REASON],
                "rejection_state_advanced": rejection["state_advanced"],
                "rejection_visibility": rejection["visibility"],
                "traces_unchanged": after_traces == before_traces,
            }
            if exact_assertions != {
                "authoritative_table_counts_unchanged": True,
                "head_unchanged": True,
                "integrity": True,
                "rejection_audit_delta": 1,
                "rejection_reason_exact": True,
                "rejection_state_advanced": False,
                "rejection_visibility": "NON_AUTHORITATIVE",
                "traces_unchanged": True,
            }:
                raise AssertionError("ATOMIC_REJECTION_ASSERTIONS_FAILED")

            return {
                "assertions": exact_assertions,
                "cas_neural_cjt_version": "0.2.0",
                "cas_cjt_imported_from_installed_distribution": True,
                "declared_plan_mutation": {
                    "field": "reasoning_step_quanta",
                    "from": original_value,
                    "to": [[2]],
                },
                "expected_reason": EXPECTED_REASON,
                "observed_reason_codes": rejection["reason_codes"],
                "plan_bindings_rebound": [
                    "batch.compute_plan",
                    "route.outputs.compute_plan",
                    "route.inputs.control_binding_manifest.compute_plan",
                    "observe.diagnostics.control_binding_digest",
                    "candidate.provenance_and_digest",
                    "verifier_receipt.identity_and_digest",
                    "successor_bias_and_network_state",
                    "state_update_intents",
                    "phase_cross_references",
                ],
                "probe_id": PROBE_ID,
                "source_file_count": manifest["file_count"],
                "source_manifest_aggregate_sha256": manifest[
                    "aggregate_sha256"
                ],
                "source_manifest_sha256": hashlib.sha256(
                    manifest_bytes
                ).hexdigest(),
                "status": "PASS",
                "trace_count_after": len(after_traces),
                "trace_count_before": len(before_traces),
            }
        finally:
            fixture.store.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce the CASformer v0.2 compute-plan mismatch rejection."
        )
    )
    parser.add_argument(
        "source_root",
        type=Path,
        help="Pinned CAS_CJT_TRANSFORMER_v0_2 source root",
    )
    arguments = parser.parse_args()
    try:
        result = _run(arguments.source_root)
    except Exception as error:
        failure = {
            "error_type": type(error).__name__,
            "expected_reason": EXPECTED_REASON,
            "probe_id": PROBE_ID,
            "status": "FAIL",
        }
        print(json.dumps(failure, sort_keys=True, separators=(",", ":")))
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
