"""Serializable, non-authoritative trace records for CASformer experiments."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

import torch
from torch import Tensor

from .core import CASFORMER_VERSION, CASControl, CASformerTelemetry, OperatingRegion


TRACE_SCHEMA_VERSION = "cas.casformer.trace/0.1"
TRACE_STATUS = "NEURAL_PROXY_UNVALIDATED"
_AUTHORITY_FIELDS = {
    "truth",
    "meaning",
    "proof",
    "validity",
    "commitment",
    "permission",
    "memory_occurrence",
    "memory_write",
    "state_mutation",
    "halt",
    "causal_identification",
    "external_action",
    "self_modification",
    "emits_cncm_intents",
}
_SUMMARY_FIELDS = {
    "semantic_scores",
    "semantic_allocation",
    "total_resistance",
    "conductance",
    "edge_current",
    "attention",
    "total_current",
    "diagnostic_features",
    "beta",
    "cjt_preactivation",
    "cjt_gate",
    "cjt_candidate",
    "cjt_effect",
    "effective_path_mask",
}
_TENSOR_FIELDS = _SUMMARY_FIELDS | {"operating_region"}
_REGION_FIELDS = {item.name for item in OperatingRegion}
_REQUIRED_PAYLOAD_FIELDS = {
    "schema_version",
    "casformer_version",
    "mode",
    "status",
    "authority",
    "profile_id",
    "provenance",
    "drive_provenance",
    "resistance_provenance",
    "control_tick",
    "feedback_source_tick",
    "layer_index",
    "summaries",
    "operating_region_counts",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _stable_mean(values: list[int | float | bool]) -> float:
    """Mean finite values without overflowing a finite mathematical result."""

    count = len(values)
    if count == 0:
        raise ValueError("stable mean requires at least one value")
    numeric = [float(value) for value in values]
    mean = math.fsum(value / count for value in numeric)
    return min(max(mean, min(numeric)), max(numeric))


def _summary(value: Tensor) -> dict[str, Any]:
    detached = value.detach().to(device="cpu", dtype=torch.float64)
    if detached.numel() == 0:
        return {"shape": list(detached.shape), "count": 0}
    values = detached.reshape(-1).tolist()
    return {
        "shape": list(detached.shape),
        "count": detached.numel(),
        "minimum": min(values),
        "maximum": max(values),
        "mean": _stable_mean(values),
    }


def _values(value: Tensor) -> Any:
    return value.detach().to(device="cpu").tolist()


def _is_nonnegative_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        converted = float(value)
    except (OverflowError, ValueError):
        return False
    return math.isfinite(converted)


def _contains_only_finite_json(value: Any) -> bool:
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _contains_only_finite_json(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return all(_contains_only_finite_json(item) for item in value)
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return _is_finite_number(value)
    return value is None or isinstance(value, str)


def _serialized_tensor(value: Any) -> tuple[list[int], list[int | float | bool]] | None:
    if not isinstance(value, list):
        return None
    if not value:
        return [0], []
    child_results: list[tuple[list[int], list[int | float | bool]]] = []
    for item in value:
        if isinstance(item, list):
            child = _serialized_tensor(item)
            if child is None:
                return None
            child_results.append(child)
        elif isinstance(item, bool) or _is_finite_number(item):
            child_results.append(([], [item]))
        else:
            return None
    first_shape = child_results[0][0]
    if any(shape != first_shape for shape, _ in child_results[1:]):
        return None
    leaves = [leaf for _, values in child_results for leaf in values]
    return [len(value), *first_shape], leaves


def _valid_summary(summary: Any) -> bool:
    if not isinstance(summary, dict) or not {"shape", "count"}.issubset(summary):
        return False
    if not isinstance(summary["shape"], list) or not all(
        _is_nonnegative_integer(size) for size in summary["shape"]
    ):
        return False
    if not _is_nonnegative_integer(summary["count"]):
        return False
    expected_count = math.prod(summary["shape"])
    if summary["count"] != expected_count:
        return False
    statistic_fields = {"minimum", "maximum", "mean"}
    expected_fields = {"shape", "count"} | (statistic_fields if expected_count else set())
    if set(summary) != expected_fields:
        return False
    if expected_count:
        if not all(_is_finite_number(summary[field]) for field in statistic_fields):
            return False
        if not summary["minimum"] <= summary["mean"] <= summary["maximum"]:
            return False
    return True


def _valid_payload_contract(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if not _REQUIRED_PAYLOAD_FIELDS.issubset(payload):
        return False
    if not set(payload).issubset(_REQUIRED_PAYLOAD_FIELDS | {"tensors"}):
        return False
    if (
        payload["schema_version"] != TRACE_SCHEMA_VERSION
        or payload["casformer_version"] != CASFORMER_VERSION
        or payload["mode"] != "NEURAL_PROXY"
        or payload["status"] != TRACE_STATUS
    ):
        return False
    authority = payload["authority"]
    if (
        not isinstance(authority, dict)
        or set(authority) != _AUTHORITY_FIELDS
        or any(value is not False for value in authority.values())
    ):
        return False
    if not isinstance(payload["profile_id"], str) or not payload["profile_id"]:
        return False
    if not isinstance(payload["provenance"], str) or not payload["provenance"]:
        return False
    if not isinstance(payload["drive_provenance"], str) or not payload["drive_provenance"]:
        return False
    if (
        not isinstance(payload["resistance_provenance"], str)
        or not payload["resistance_provenance"]
    ):
        return False
    if not _is_nonnegative_integer(payload["control_tick"]):
        return False
    feedback_tick = payload["feedback_source_tick"]
    if feedback_tick is not None and (
        not _is_nonnegative_integer(feedback_tick)
        or feedback_tick >= payload["control_tick"]
    ):
        return False
    if not _is_nonnegative_integer(payload["layer_index"]):
        return False
    summaries = payload["summaries"]
    if (
        not isinstance(summaries, dict)
        or set(summaries) != _SUMMARY_FIELDS
        or not all(_valid_summary(summary) for summary in summaries.values())
    ):
        return False
    region_counts = payload["operating_region_counts"]
    if (
        not isinstance(region_counts, dict)
        or set(region_counts) != _REGION_FIELDS
        or not all(_is_nonnegative_integer(count) for count in region_counts.values())
        or sum(region_counts.values()) != summaries["cjt_gate"]["count"]
    ):
        return False
    if "tensors" in payload:
        tensors = payload["tensors"]
        if (
            not isinstance(tensors, dict)
            or set(tensors) != _TENSOR_FIELDS
            or not _contains_only_finite_json(tensors)
        ):
            return False
        decoded_tensors: dict[
            str, tuple[list[int], list[int | float | bool]]
        ] = {}
        for name, serialized in tensors.items():
            decoded = _serialized_tensor(serialized)
            if decoded is None:
                return False
            decoded_tensors[name] = decoded
            shape, leaves = decoded
            summary_name = "cjt_gate" if name == "operating_region" else name
            summary = summaries[summary_name]
            if shape != summary["shape"] or len(leaves) != summary["count"]:
                return False
            if name == "operating_region":
                allowed_regions = {int(item) for item in OperatingRegion}
                if any(
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or value not in allowed_regions
                    for value in leaves
                ):
                    return False
                tensor_region_counts = {
                    item.name: sum(value == int(item) for value in leaves)
                    for item in OperatingRegion
                }
                if tensor_region_counts != region_counts:
                    return False
            elif name == "effective_path_mask":
                if any(not isinstance(value, bool) for value in leaves):
                    return False
            elif any(isinstance(value, bool) for value in leaves):
                return False
            if name in summaries and leaves:
                numeric = [float(value) for value in leaves]
                comparisons = {
                    "minimum": min(numeric),
                    "maximum": max(numeric),
                    "mean": _stable_mean(numeric),
                }
                if any(
                    not math.isclose(
                        comparisons[field],
                        float(summary[field]),
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    )
                    for field in comparisons
                ):
                    return False
        mask_shape, mask_values = decoded_tensors["effective_path_mask"]
        redacted_route_fields = {
            "semantic_scores",
            "semantic_allocation",
            "total_resistance",
            "conductance",
            "edge_current",
            "attention",
        }
        for name in redacted_route_fields:
            shape, values = decoded_tensors[name]
            if shape != mask_shape or any(
                not is_open and float(value) != 0.0
                for is_open, value in zip(mask_values, values, strict=True)
            ):
                return False
    return True


@dataclass(frozen=True)
class CASformerTrace:
    payload: dict[str, Any]
    payload_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload, "payload_sha256": self.payload_sha256}


def make_trace(
    telemetry: CASformerTelemetry,
    control: CASControl,
    *,
    layer_index: int,
    include_tensors: bool = True,
) -> CASformerTrace:
    """Build a detached trace that carries no semantic or authority verdict.

    Full tensors are included by default so verification can check tensor
    summaries, operating-region counts, types, shapes, and closed-route
    redaction against the serialized values. An explicitly requested compact
    trace can only receive structural, summary, authority, and checksum checks.
    """

    if not _is_nonnegative_integer(layer_index):
        raise ValueError("layer_index must be a nonnegative integer")
    if not isinstance(control.profile_id, str) or not control.profile_id:
        raise ValueError("control.profile_id must be a nonempty string")
    if not isinstance(control.provenance, str) or not control.provenance:
        raise ValueError("control.provenance must be a nonempty string")
    if not isinstance(control.drive_provenance, str) or not control.drive_provenance:
        raise ValueError("control.drive_provenance must be a nonempty string")
    if (
        not isinstance(control.resistance_provenance, str)
        or not control.resistance_provenance
    ):
        raise ValueError("control.resistance_provenance must be a nonempty string")
    if not _is_nonnegative_integer(control.control_tick):
        raise ValueError("control.control_tick must be a nonnegative integer")
    if control.feedback_source_tick is not None and (
        not _is_nonnegative_integer(control.feedback_source_tick)
        or control.feedback_source_tick >= control.control_tick
    ):
        raise ValueError("control.feedback_source_tick must name an earlier tick")

    region = telemetry.operating_region.detach().to(device="cpu")
    region_counts = {
        item.name: int((region == int(item)).sum().item()) for item in OperatingRegion
    }
    attention = telemetry.attention
    payload: dict[str, Any] = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "casformer_version": CASFORMER_VERSION,
        "mode": "NEURAL_PROXY",
        "status": TRACE_STATUS,
        "authority": {
            "truth": False,
            "meaning": False,
            "proof": False,
            "validity": False,
            "commitment": False,
            "permission": False,
            "memory_occurrence": False,
            "memory_write": False,
            "state_mutation": False,
            "halt": False,
            "causal_identification": False,
            "external_action": False,
            "self_modification": False,
            "emits_cncm_intents": False,
        },
        "profile_id": control.profile_id,
        "provenance": control.provenance,
        "drive_provenance": control.drive_provenance,
        "resistance_provenance": control.resistance_provenance,
        "control_tick": control.control_tick,
        "feedback_source_tick": control.feedback_source_tick,
        "layer_index": layer_index,
        "summaries": {
            "semantic_scores": _summary(attention.semantic_scores),
            "semantic_allocation": _summary(attention.semantic_allocation),
            "total_resistance": _summary(attention.total_resistance),
            "conductance": _summary(attention.conductance),
            "edge_current": _summary(attention.current),
            "attention": _summary(attention.attention),
            "total_current": _summary(attention.total_current),
            "diagnostic_features": _summary(attention.diagnostic_features),
            "beta": _summary(telemetry.beta),
            "cjt_preactivation": _summary(telemetry.cjt_preactivation),
            "cjt_gate": _summary(telemetry.cjt_gate),
            "cjt_candidate": _summary(telemetry.cjt_candidate),
            "cjt_effect": _summary(telemetry.cjt_effect),
            "effective_path_mask": _summary(attention.effective_path_mask),
        },
        "operating_region_counts": region_counts,
    }
    if include_tensors:
        payload["tensors"] = {
            "semantic_scores": _values(attention.semantic_scores),
            "semantic_allocation": _values(attention.semantic_allocation),
            "total_resistance": _values(attention.total_resistance),
            "conductance": _values(attention.conductance),
            "edge_current": _values(attention.current),
            "attention": _values(attention.attention),
            "total_current": _values(attention.total_current),
            "diagnostic_features": _values(attention.diagnostic_features),
            "beta": _values(telemetry.beta),
            "cjt_preactivation": _values(telemetry.cjt_preactivation),
            "cjt_gate": _values(telemetry.cjt_gate),
            "cjt_candidate": _values(telemetry.cjt_candidate),
            "cjt_effect": _values(telemetry.cjt_effect),
            "operating_region": _values(telemetry.operating_region),
            "effective_path_mask": _values(attention.effective_path_mask),
        }

    encoded = _canonical_json(payload).encode("ascii")
    return CASformerTrace(payload=payload, payload_sha256=hashlib.sha256(encoded).hexdigest())


def verify_trace(trace: CASformerTrace | dict[str, Any]) -> bool:
    """Verify the frozen zero-authority contract and the payload checksum.

    Full-tensor records also receive cross-field consistency and closed-route
    redaction checks. Compact summary-only records cannot receive those checks.
    This detects accidental changes and rejects contract-invalid fields, but it
    is not a signature, identity proof, append-only chain, or WORM retention
    receipt, so it does not authenticate who created the trace.
    """

    if isinstance(trace, CASformerTrace):
        raw = trace.to_dict()
    elif isinstance(trace, dict):
        raw = dict(trace)
    else:
        return False
    supplied = raw.pop("payload_sha256", None)
    try:
        contract_valid = _valid_payload_contract(raw)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False
    if (
        not isinstance(supplied, str)
        or len(supplied) != 64
        or supplied != supplied.lower()
        or any(character not in "0123456789abcdef" for character in supplied)
        or not contract_valid
    ):
        return False
    try:
        encoded = _canonical_json(raw).encode("ascii")
    except (TypeError, ValueError):
        return False
    return hashlib.sha256(encoded).hexdigest() == supplied
