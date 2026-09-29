"""Typed preparation for the existing guarded intervention path; no runner.

This module cannot load a model, install a hook or execute a serialized action.
The separately admitted caller uses diagnostic_intervention.apply on a freshly
restored forward. Arithmetic node_state replacement remains unsupported.
"""
from dataclasses import asdict
import math

from .. import diagnostic_intervention as intervention
from ..diagnostic_configuration import CORE_ROUNDS, LEARNER_SHA256, RawCapture, capture_digest
from ..observation import reload_configuration_inputs
from .contracts import require

SITE = "graph.round_update"


def consumer_schedule(site=SITE, *, round_index):
    require(site == SITE, "CB1_CONSUMER_SITE_UNSUPPORTED")
    require(type(round_index) is int and 0 <= round_index < CORE_ROUNDS, "CB1_CONSUMER_ROUND")
    return {"site": site, "module": "core_block", "hook": "post",
        "round_index": round_index, "expected_total_hits": CORE_ROUNDS, "targeted_hits": 1,
        "semantics": "CORE_UPDATE_BEFORE_RESIDUAL_NOT_FINAL_NODE_STATE",
        "execution": "FRESH_GRAPH_FORWARD_REQUIRED; NO_CACHED_GRAPHFORWARD_OBJECT",
        "descendants_in_order": ["round_residual_and_RMS", "remaining_graph_rounds",
            "GraphForward.hidden", "_encode_query", "pointer_key", "_pooled_worlds",
            "edge_head", "node_head", "head_logits", "slot_scores", "score_decisions", "assemble_answer"],
        "recompute_policy": "ORIGINAL_FORWARD_CONTROL_FLOW; NOT_REPLAY_OF_STORED_DESCENDANTS",
        "passive_emitter": "UNCHANGED_READ_ONLY", "execution_authorized": False}


def _prepare(capture, *, native_values=None, max_abs_delta=None, donor_provenance=None,
             hypothesis_id, predicted_change):
    require(type(capture) is RawCapture, "CB1_TYPED_CAPTURE_REQUIRED")
    require(capture.site == SITE and capture.source_sha256 == LEARNER_SHA256,
            "CB1_CONSUMER_SOURCE_SITE")
    require(len(capture.shape) == 2 and capture.shape[1] == 64 and 0 < capture.shape[0] <= 10,
            "CB1_CONSUMER_DIMENSIONS")
    require(capture.call_index == capture.round_index, "CB1_SINGLE_FORWARD_CAPTURE_REQUIRED")
    schedule = consumer_schedule(round_index=capture.round_index)
    kwargs = dict(site=SITE, checkpoint_sha256=capture.checkpoint_sha256,
        input_sha256=capture.input_sha256, source_sha256=capture.source_sha256,
        rows=tuple(range(capture.shape[0])), coordinates=tuple(range(64)),
        round_index=capture.round_index, hypothesis_id=hypothesis_id, predicted_change=predicted_change)
    if native_values is None:
        require(max_abs_delta is None and donor_provenance is None, "CB1_NOOP_DONOR_FIELDS_UNEXPECTED")
        declaration = intervention.declare(action="NO_OP_CONTROL", **kwargs)
    else:
        # Absolute replacement values. Claude must apply sigma to a delta and
        # add that delta to h before calling this; no bias/normalization guessed.
        require(type(native_values) in (list, tuple)
                and len(native_values) == capture.shape[0] * 64, "CB1_REPLACEMENT_DIMENSIONS")
        require(type(max_abs_delta) in (int, float) and math.isfinite(max_abs_delta)
                and max_abs_delta > 0, "CB1_DELTA_LIMIT_REQUIRED")
        require(donor_provenance in ("STIMULUS_ONLY", "GOLD_INFORMED"), "CB1_DONOR_PROVENANCE_REQUIRED")
        donor = intervention.donor(input_sha256=capture.input_sha256,
            capture_digest=capture_digest(capture), checkpoint_sha256=capture.checkpoint_sha256,
            provenance=donor_provenance, basis=capture.basis, dtype=capture.dtype,
            device=capture.device, values=native_values)
        require(len(donor.values) == capture.shape[0] * 64, "CB1_REPLACEMENT_DIMENSIONS")
        require(len(capture.signed_values) == len(donor.values)
                and all(math.isfinite(old) and abs(new - old) <= max_abs_delta
                        for new, old in zip(donor.values, capture.signed_values)), "CB1_DELTA_LIMIT")
        schedule["max_abs_native_delta"] = max_abs_delta
        declaration = intervention.declare(action="SAME_INPUT_PATCH", donor=donor, **kwargs)
    return declaration, schedule


def prepare_consumer_declaration(host, event_digest, *, round_index, native_values=None,
                                 max_abs_delta=None, donor_provenance=None, hypothesis_id, predicted_change):
    """Only an existing host-anchored COMPLETE single-input capture is eligible.

    Returns existing Declaration data, not authority. The caller must bind the
    restored model and a new finite admission; this packet adds neither.
    """
    loaded = reload_configuration_inputs(host, event_digest)
    require(loaded["complete"], "CB1_CAPTURE_INCOMPLETE")
    require(type(round_index) is int and 0 <= round_index < CORE_ROUNDS, "CB1_CONSUMER_ROUND")
    series = loaded["capture_series"][SITE]
    require(len(series) == CORE_ROUNDS, "CB1_CAPTURE_CALL_COUNT")
    declaration, schedule = _prepare(series[round_index], native_values=native_values, max_abs_delta=max_abs_delta,
        donor_provenance=donor_provenance, hypothesis_id=hypothesis_id, predicted_change=predicted_change)
    return {"declaration": declaration, "schedule": schedule,
            "anchor": loaded["receipt_sha256"], "execution_authorized": False,
            "preparer": "EXTERNAL_CODEX_CB1_ADAPTER",
            "library_actor": declaration.actor,
            "actual_execution_actor": "MUST_BE_RECORDED_BY_GUARDED_CALLER"}


def verify_consumer_receipt(declaration, receipt):
    """Refuse missed/double hooks, dimension drift, mutation or stale/no forward."""
    intervention.verify_receipt(intervention.receipt_to_json(receipt), declaration)
    require(declaration.site == SITE and receipt.model_binding == "CALLER_VERIFIED",
            "CB1_CONSUMER_BINDING")
    require(receipt.hooks_removed and receipt.parameters_unchanged and not receipt.errors,
            "CB1_CONSUMER_CLEANUP_OR_STATE")
    require(len(receipt.hits) == CORE_ROUNDS and sum(h["targeted"] for h in receipt.hits) == 1,
            "CB1_CONSUMER_HITS")
    require([h["round_index"] for h in receipt.hits] == list(range(CORE_ROUNDS)), "CB1_CONSUMER_ORDER")
    require(all(h["shape"] == [len(declaration.rows), 64] for h in receipt.hits), "CB1_CONSUMER_DIMENSIONS")
    expected = ("NO_OP_VERIFIED",) if declaration.action == "NO_OP_CONTROL" else ("APPLIED", "APPLIED_NO_CHANGE")
    require(receipt.status in expected, "CB1_CONSUMER_NOT_APPLIED")
    return {"status": receipt.status, "hook_receipt": asdict(receipt),
            "downstream_output_parity": "SEPARATE_WITNESS_REQUIRED",
            "state_rng_optimizer_parity": "SEPARATE_GUARDED_CALLER_CHECK_REQUIRED",
            "promotion": False}
