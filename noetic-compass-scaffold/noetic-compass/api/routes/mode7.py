"""Mode 7 Live SSE route.

Authenticated by the global JWT middleware. The route is intentionally local:
it builds a deterministic trace report from the prompt/expression and streams
SGGS-compatible commits from the CAS Native Thought Tree surface.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
import sys
import time
import types
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.config import settings
from api.notation.compiler import compile_expression
from api.routes.idea_atlas import _synthesize_from_signals


router = APIRouter(prefix="/mode7", tags=["mode7"])


_IDENT_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b")
_DOMAIN_RE = re.compile(r"\^([PCEO])(?=[_\s|}\]\)^,.;:]|$)")
_CAS_TOKEN_RE = re.compile(r"(\^[0-9PCEO]|_\{?F[1-7]\}?|CO-\d+|\||\{|\})")
_DOMAIN_ORDER = ("P", "C", "E", "O")
_CANONICAL_HEADS = (
    "turn_type",
    "expression_family",
    "transition_kind",
    "noetic",
    "domain",
    "drive",
    "register",
    "register_mode",
    "meta_relation",
    "authority",
    "omega",
    "meta_logic",
)
_NODE_RELEVANT_HEADS = {
    "model_generation": ("turn_type", "expression_family", "transition_kind", "domain"),
    "identifier_attempt": ("register", "meta_relation", "authority"),
    "slot_pattern": ("expression_family", "transition_kind", "drive"),
    "confidence_marker": ("turn_type", "authority", "omega", "meta_logic"),
}
_DEFAULT_PREDICTOR_RUN_NAME = (
    "structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045"
)
_PREDICTOR_ARTIFACTS = (
    "best_structured_token_model.pt",
    "structured_token_vocab.json",
    "manifest.json",
)
_PREDICTOR_CACHE: dict[tuple[str, str], tuple[Any | None, list[str]]] = {}


def _ensure_cas_native_alias() -> None:
    """Expose the historical `cas-native/` directory as `cas_native`.

    CAS Native tests do the same aliasing in their conftest. The API process
    does not load that conftest, so the route creates the import alias lazily.
    """
    if "cas_native" in sys.modules:
        return

    package_root = Path(__file__).resolve().parents[2] / "cas-native"
    package = types.ModuleType("cas_native")
    package.__file__ = str(package_root / "__init__.py")
    package.__path__ = [str(package_root)]  # type: ignore[attr-defined]
    sys.modules["cas_native"] = package


def _default_predictor_run_dir() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "cas-native"
        / "training"
        / "runs"
        / _DEFAULT_PREDICTOR_RUN_NAME
    )


def _configured_predictor_run_dir() -> Path:
    raw = (settings.cas_native_predictor_run_dir or "").strip()
    if not raw:
        return _default_predictor_run_dir()
    return Path(raw).expanduser()


def _predictor_artifact_diagnostics(run_dir: Path) -> list[str]:
    if not run_dir.exists():
        return [f"cas_native_predictor_run_dir_missing:{run_dir}"]
    missing = [name for name in _PREDICTOR_ARTIFACTS if not (run_dir / name).exists()]
    if missing:
        return [
            "cas_native_predictor_artifacts_missing:"
            + ",".join(missing)
            + f":{run_dir}"
        ]
    return []


def _path_status(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": str(path),
        "exists": exists,
        "size_bytes": int(path.stat().st_size) if exists and path.is_file() else None,
    }


def _torch_package_status() -> dict[str, Any]:
    try:
        from importlib import metadata, util

        spec_available = util.find_spec("torch") is not None
        try:
            version = metadata.version("torch")
        except metadata.PackageNotFoundError:
            version = None
    except Exception as exc:
        return {
            "available": False,
            "version": None,
            "diagnostic": f"torch_status_failed:{type(exc).__name__}:{exc}",
        }

    return {
        "available": bool(spec_available or version),
        "version": version,
        "diagnostic": None,
    }


def _runtime_file_status() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2] / "cas-native"
    required = {
        "predict_cas": root / "inference" / "predict_cas.py",
        "cas_renderer": root / "inference" / "cas_renderer.py",
        "trace_mechanistic": root / "trace" / "mechanistic.py",
        "trace_activations": root / "trace" / "activations.py",
        "trace_attribution": root / "trace" / "attribution.py",
        "trace_network_summary": root / "trace" / "network_summary.py",
        "trace_live_capture": root / "trace" / "live_capture.py",
    }
    files = {name: _path_status(path) for name, path in required.items()}
    missing = [name for name, status in files.items() if not status["exists"]]
    return {
        "root": str(root),
        "ready": not missing,
        "files": files,
        "missing": missing,
    }


def _mode7_runtime_status(*, load_predictor: bool = False) -> dict[str, Any]:
    run_dir = _configured_predictor_run_dir()
    artifact_diagnostics = _predictor_artifact_diagnostics(run_dir)
    artifacts = {
        name: _path_status(run_dir / name)
        for name in _PREDICTOR_ARTIFACTS
    }
    torch_status = _torch_package_status()
    runtime_files = _runtime_file_status()
    device = (settings.cas_native_predictor_device or "cpu").strip() or "cpu"
    cache_key = (str(run_dir), device)
    cached = _PREDICTOR_CACHE.get(cache_key)
    cached_loaded = cached is not None and cached[0] is not None
    load_diagnostics: list[str] = []
    loaded_now = False

    if load_predictor and settings.cas_native_predictor_enabled:
        predictor, load_diagnostics = _load_live_predictor()
        loaded_now = predictor is not None
        cached_loaded = loaded_now

    diagnostics: list[str] = []
    if not settings.cas_native_predictor_enabled:
        diagnostics.append("cas_native_predictor_disabled")
    diagnostics.extend(artifact_diagnostics)
    if not torch_status["available"]:
        diagnostics.append("torch_package_missing")
    if not runtime_files["ready"]:
        diagnostics.extend(
            f"cas_native_runtime_file_missing:{name}"
            for name in runtime_files["missing"]
        )
    diagnostics.extend(load_diagnostics)

    artifacts_ready = not artifact_diagnostics
    predictor_ready = (
        bool(settings.cas_native_predictor_enabled)
        and artifacts_ready
        and bool(torch_status["available"])
        and bool(runtime_files["ready"])
        and (
            not load_predictor
            or loaded_now
            or cached_loaded
        )
    )
    active_mode = (
        "cas_native_live_predictor"
        if predictor_ready
        else "deterministic_fallback"
    )

    return {
        "schema_version": "mode7_runtime_status.v1",
        "active_mode": active_mode,
        "predictor_ready": predictor_ready,
        "predictor_enabled": bool(settings.cas_native_predictor_enabled),
        "predictor_loaded": cached_loaded,
        "load_checked": bool(load_predictor),
        "configured": {
            "run_dir": str(run_dir),
            "device": device,
        },
        "artifacts": {
            "ready": artifacts_ready,
            "files": artifacts,
        },
        "torch": torch_status,
        "runtime_files": runtime_files,
        "diagnostics": diagnostics,
    }


def _load_live_predictor() -> tuple[Any | None, list[str]]:
    """Load the local CAS Native structured-token predictor when available."""
    if not settings.cas_native_predictor_enabled:
        return None, ["cas_native_predictor_disabled"]

    run_dir = _configured_predictor_run_dir()
    device = (settings.cas_native_predictor_device or "cpu").strip() or "cpu"
    key = (str(run_dir), device)
    cached = _PREDICTOR_CACHE.get(key)
    if cached is not None:
        return cached

    diagnostics = _predictor_artifact_diagnostics(run_dir)
    if diagnostics:
        result = (None, diagnostics)
        _PREDICTOR_CACHE[key] = result
        return result

    try:
        _ensure_cas_native_alias()
        from cas_native.inference.predict_cas import load_predictor

        predictor = load_predictor(run_dir, device=device)
    except Exception as exc:
        diagnostics = [
            f"cas_native_predictor_load_failed:{type(exc).__name__}:{exc}"
        ]
        result = (None, diagnostics)
        _PREDICTOR_CACHE[key] = result
        return result

    result = (
        predictor,
        [
            "cas_native_predictor_loaded:"
            + f"{run_dir}:device={device}"
        ],
    )
    _PREDICTOR_CACHE[key] = result
    return result


def _cas_expression_from_prediction(prediction: dict[str, Any]) -> str:
    noetic = prediction.get("noetic")
    try:
        noetic_int = int(noetic)
    except (TypeError, ValueError):
        noetic_int = 0
    noetic_int = max(0, min(9, noetic_int))

    domain = str(prediction.get("domain") or "C")
    if domain not in _DOMAIN_ORDER:
        domain = "C"

    drive = str(prediction.get("drive") or "F1")
    if not re.fullmatch(r"F[1-7]", drive):
        drive = "F1"

    return f"CO-{noetic_int}^{domain}_{{{drive}}}"


def _render_prediction_english(
    prompt: str,
    cas_expression: str,
    prediction: dict[str, Any],
) -> str:
    try:
        _ensure_cas_native_alias()
        from cas_native.inference.cas_renderer import render_cas_prediction

        return render_cas_prediction(prediction)
    except Exception:
        return (
            "CAS Native structured prediction for: "
            f"{prompt.strip() or cas_expression}. CAS expression: {cas_expression}"
        )


def _try_live_cas_native_prediction(prompt: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Run prompt through the local CAS Native predictor with live hooks."""
    clean_prompt = (prompt or "").strip()
    if not clean_prompt:
        return None, []

    predictor, diagnostics = _load_live_predictor()
    if predictor is None:
        return None, diagnostics

    t_start = time.perf_counter()
    try:
        prediction, live_trace = predictor(
            clean_prompt,
            with_trace=True,
            trace_top_k=5,
        )
    except Exception as exc:
        return None, diagnostics + [
            f"cas_native_predictor_inference_failed:{type(exc).__name__}:{exc}"
        ]

    trace_payload = (
        live_trace.to_dict()
        if hasattr(live_trace, "to_dict")
        else dict(live_trace or {})
    )
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0
    return {
        "source": "cas_native.inference.predict_cas",
        "run_dir": str(_configured_predictor_run_dir()),
        "device": (settings.cas_native_predictor_device or "cpu").strip() or "cpu",
        "prediction": dict(prediction or {}),
        "live_trace": trace_payload,
        "elapsed_ms": _clean_float(elapsed_ms, digits=3),
        "diagnostics": diagnostics,
    }, diagnostics


def _extract_identifiers(text: str) -> list[str]:
    return [m.group(0) for m in _IDENT_RE.finditer(text or "")]


def _slot_summary_for(text: str) -> dict[str, Any]:
    tokens = (text or "").split()
    identifier_count = sum(1 for token in tokens if _IDENT_RE.fullmatch(token.strip(".,;:()[]{}")))
    return {
        "length": len(tokens),
        "counts": {"0": max(0, len(tokens) - identifier_count), "2": identifier_count},
        "longest_stage_var_run": min(identifier_count, len(tokens)),
    }


def _clean_float(value: Any, digits: int = 6) -> float:
    try:
        fval = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(fval):
        return 0.0
    return round(fval, digits)


def _stable_score(*parts: Any) -> float:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)


def _trace_input_for_mechanistic(report: dict[str, Any]) -> str:
    parts = [
        str(report.get("input_prompt") or "").strip(),
        str(report.get("input_cas_expression") or "").strip(),
        str(report.get("generated_english") or "").strip(),
    ]
    return "\n".join(part for part in parts if part)


def _vector_summary(name: str, values: Any, *, top_k: int = 5) -> dict[str, Any]:
    if not isinstance(values, list):
        values = []
    clean_values = [
        float(value)
        for value in values
        if isinstance(value, (int, float)) and math.isfinite(float(value))
    ]
    if not clean_values:
        return {
            "name": name,
            "length": 0,
            "l2_norm": 0.0,
            "mean_abs": 0.0,
            "max_abs": 0.0,
            "top_abs": [],
        }

    indexed = list(enumerate(clean_values))
    indexed.sort(key=lambda pair: abs(pair[1]), reverse=True)
    return {
        "name": name,
        "length": len(clean_values),
        "l2_norm": _clean_float(math.sqrt(sum(value * value for value in clean_values))),
        "mean_abs": _clean_float(
            sum(abs(value) for value in clean_values) / len(clean_values)
        ),
        "max_abs": _clean_float(max(abs(value) for value in clean_values)),
        "top_abs": [
            {"index": int(index), "value": _clean_float(value)}
            for index, value in indexed[:top_k]
        ],
    }


def _softmax_max(logits: list[float]) -> float:
    if not logits:
        return 0.0
    max_logit = max(logits)
    exps = [math.exp(value - max_logit) for value in logits]
    total = sum(exps) or 1.0
    return max(exps) / total


def _logits_summary_from_raw(raw_logits: Any) -> dict[str, Any]:
    if not isinstance(raw_logits, dict):
        raw_logits = {}
    per_head: dict[str, Any] = {}
    for head in _CANONICAL_HEADS:
        values = raw_logits.get(head) or []
        clean_values = [
            float(value)
            for value in values
            if isinstance(value, (int, float)) and math.isfinite(float(value))
        ]
        if not clean_values:
            per_head[head] = {
                "logit_count": 0,
                "argmax_index": None,
                "max_logit": 0.0,
                "softmax_max": 0.0,
                "top_logits": [],
            }
            continue
        indexed = list(enumerate(clean_values))
        indexed.sort(key=lambda pair: pair[1], reverse=True)
        argmax_index, max_logit = indexed[0]
        per_head[head] = {
            "logit_count": len(clean_values),
            "argmax_index": int(argmax_index),
            "max_logit": _clean_float(max_logit),
            "softmax_max": _clean_float(_softmax_max(clean_values)),
            "top_logits": [
                {"index": int(index), "value": _clean_float(value)}
                for index, value in indexed[:3]
            ],
        }
    return {
        "source": "mechanistic_raw_activations",
        "per_head": per_head,
    }


def _extract_domains(*texts: str) -> list[str]:
    observed: list[str] = []
    for text in texts:
        for match in _DOMAIN_RE.finditer(text or ""):
            domain = match.group(1)
            if domain in _DOMAIN_ORDER and domain not in observed:
                observed.append(domain)
    return observed


def _domain_descent_attention_summary(
    report: dict[str, Any],
    prediction: dict[str, Any],
) -> dict[str, Any]:
    expression = str(report.get("input_cas_expression") or "")
    generated = str(report.get("generated_english") or "")
    prompt = str(report.get("input_prompt") or "")
    observed = _extract_domains(expression, generated, prompt)
    predicted_domain = prediction.get("domain")
    if predicted_domain in _DOMAIN_ORDER and predicted_domain not in observed:
        observed.append(str(predicted_domain))

    selected = next((domain for domain in observed if domain in _DOMAIN_ORDER), None)
    applicable = selected is not None
    index = _DOMAIN_ORDER.index(selected) if selected in _DOMAIN_ORDER else None

    mask_source = "deterministic_domain_order"
    mask_shape = [40, 40]
    allowed_edges = 1000
    try:
        from cas_native.model.domain_descent import build_domain_descent_mask

        mask = build_domain_descent_mask()
        mask_shape = [int(dim) for dim in mask.shape]
        allowed_edges = int(mask.sum().item())
        mask_source = "cas_native.model.domain_descent.build_domain_descent_mask"
    except Exception:
        pass

    allowed_sources = list(_DOMAIN_ORDER[: index + 1]) if index is not None else []
    blocked_future = list(_DOMAIN_ORDER[index + 1 :]) if index is not None else []
    return {
        "applicable": applicable,
        "source": mask_source,
        "domain_order": list(_DOMAIN_ORDER),
        "observed_domains": observed,
        "selected_domain": selected,
        "domain_descent_index": index,
        "allowed_source_domains": allowed_sources,
        "blocked_future_domains": blocked_future,
        "slot_mask_shape": mask_shape,
        "allowed_slot_edges": allowed_edges,
        "feedback_path": "O->P",
        "feedback_active": "O" in observed,
    }


def _copy_distribution_summary(report: dict[str, Any]) -> dict[str, Any]:
    trace = report.get("traceability_v0") or {}
    copy = trace.get("copy") or {}
    slot_trace = trace.get("slot_trace") or {}
    copied = list(copy.get("copied_identifiers") or [])
    missed = list(copy.get("missed_identifiers") or [])
    per_identifier = list(copy.get("per_identifier") or [])
    coverage = copy.get("coverage")
    return {
        "source": "traceability_v0.copy",
        "copied_count": len(copied),
        "missed_count": len(missed),
        "coverage": None if coverage is None else _clean_float(coverage),
        "copied_identifiers": copied[:12],
        "missed_identifiers": missed[:12],
        "per_identifier": per_identifier[:12],
        "slot_trace": {
            "length": int(slot_trace.get("length") or 0),
            "slot_counts_by_label": dict(slot_trace.get("slot_counts_by_label") or {}),
            "longest_stage_var_run": int(slot_trace.get("longest_stage_var_run") or 0),
            "raw_trace_present": slot_trace.get("raw_trace") is not None,
        },
    }


def _top_token_records(
    tokens: list[str],
    weights: list[float],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not tokens:
        return []
    records: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        score = weights[index] if index < len(weights) else 0.0
        records.append(
            {
                "index": index,
                "token": str(token),
                "score": _clean_float(score),
            }
        )
    records.sort(key=lambda record: (-record["score"], record["index"]))
    return records[:limit]


def _load_bearing_tokens(
    report: dict[str, Any],
    tokens: list[str],
    per_token_attribution: dict[str, Any],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    if not tokens:
        tokens = [
            token
            for token in str(report.get("input_cas_expression") or "").split()
            if token
        ]
    if not tokens:
        tokens = [
            token
            for token in str(report.get("generated_english") or "").split()
            if token
        ]

    expected = set((report.get("identifiers") or {}).get("expected") or [])
    copied = set((report.get("identifiers") or {}).get("copied") or [])
    expression_tokens = set(str(report.get("input_cas_expression") or "").split())
    aggregate = [0.0 for _ in tokens]
    seen_heads = 0
    for values in per_token_attribution.values():
        if not isinstance(values, list):
            continue
        seen_heads += 1
        for index in range(min(len(tokens), len(values))):
            if isinstance(values[index], (int, float)):
                aggregate[index] += float(values[index])
    if seen_heads:
        aggregate = [value / seen_heads for value in aggregate]

    records: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        normalized = token.strip(".,;:()[]{}")
        roles: list[str] = []
        score = aggregate[index] if index < len(aggregate) else 0.0
        if normalized in expected:
            score += 1.0
            roles.append("expected_identifier")
        if normalized in copied:
            score += 1.0
            roles.append("copied_identifier")
        if token in expression_tokens:
            score += 0.5
            roles.append("cas_source_token")
        if _CAS_TOKEN_RE.search(token):
            score += 0.75
            roles.append("cas_structural_token")
        if not roles and index < 3:
            roles.append("mechanistic_attribution_top")
        records.append(
            {
                "index": index,
                "token": str(token),
                "score": _clean_float(score),
                "roles": roles,
            }
        )
    records.sort(key=lambda record: (-record["score"], record["index"]))
    return records[:limit]


def _fallback_mechanistic_summary(
    report: dict[str, Any],
    diagnostics: list[str],
) -> dict[str, Any]:
    trace_input = _trace_input_for_mechanistic(report)
    tokens = [token for token in trace_input.split() if token]
    per_head_attribution = {
        head: {
            "confidence": _clean_float(0.35 + 0.6 * _stable_score(trace_input, head)),
            "capacity_share": _clean_float(1.0 / len(_CANONICAL_HEADS)),
            "top_tokens": _top_token_records(
                tokens,
                [
                    _stable_score(trace_input, head, token, index)
                    for index, token in enumerate(tokens)
                ],
            ),
        }
        for head in _CANONICAL_HEADS
    }
    raw_logits = {
        head: [
            (_stable_score(trace_input, head, "logit", index) * 6.0) - 3.0
            for index in range(4)
        ]
        for head in _CANONICAL_HEADS
    }
    copy_summary = _copy_distribution_summary(report)
    logits_summary = _logits_summary_from_raw(raw_logits)
    return {
        "schema_version": "mode7_mechanistic_axis_attrs.v1",
        "source": "deterministic_fallback",
        "trace_input_token_count": len(tokens),
        "activation_hooks": {
            "source": "deterministic_fallback",
            "hook_status": {},
            "captured": [],
            "missing": ["live_model_unavailable"],
            "diagnostics": diagnostics,
        },
        "activation_layers": [
            _vector_summary(
                "deterministic_bottleneck",
                [
                    (_stable_score(trace_input, "bottleneck", index) * 4.0) - 2.0
                    for index in range(64)
                ],
            )
        ],
        "activation_summary": {
            "headline": "deterministic fallback mechanistic trace",
        },
        "per_head_attribution": per_head_attribution,
        "load_bearing_tokens": _load_bearing_tokens(report, tokens, {}),
        "logits_summary": logits_summary,
        "copy_distribution_summary": copy_summary,
        "logits_copy_distribution_summary": {
            "logits": logits_summary,
            "copy": copy_summary,
        },
        "domain_descent_attention": _domain_descent_attention_summary(report, {}),
        "diagnostics": diagnostics,
    }


def _live_trace_layer_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(record.get("name") or "unknown_layer"),
        "shape": list(record.get("shape") or []),
        "l2_norm": _clean_float(record.get("l2_norm")),
        "mean_abs": _clean_float(record.get("mean_abs")),
        "max_abs": _clean_float(record.get("max_abs")),
        "flat_preview": [
            _clean_float(value)
            for value in list(record.get("flat_preview") or [])[:8]
        ],
    }


def _live_token_records(report: dict[str, Any], tokens: list[str]) -> list[dict[str, Any]]:
    if not tokens:
        trace_input = _trace_input_for_mechanistic(report)
        tokens = [token for token in trace_input.split() if token]

    expected = set((report.get("identifiers") or {}).get("expected") or [])
    copied = set((report.get("identifiers") or {}).get("copied") or [])
    expression_tokens = set(str(report.get("input_cas_expression") or "").split())
    records: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        normalized = token.strip(".,;:()[]{}")
        roles = ["structured_prediction_input"]
        score = _stable_score("live_token", token, index)
        if normalized in expected:
            score += 1.0
            roles.append("expected_identifier")
        if normalized in copied:
            score += 1.0
            roles.append("copied_identifier")
        if token in expression_tokens:
            score += 0.5
            roles.append("cas_source_token")
        if _CAS_TOKEN_RE.search(token):
            score += 0.75
            roles.append("cas_structural_token")
        records.append(
            {
                "index": index,
                "token": str(token),
                "score": _clean_float(score),
                "roles": roles,
                "attribution_basis": (
                    "live_input_token; token-gradient attribution pending"
                ),
            }
        )
    records.sort(key=lambda record: (-record["score"], record["index"]))
    return records[:8]


def _mechanistic_summary_from_live_trace(
    report: dict[str, Any],
    live_runtime: dict[str, Any],
) -> dict[str, Any]:
    trace_payload = dict(live_runtime.get("live_trace") or {})
    prediction = dict(live_runtime.get("prediction") or {})
    trace_input = _trace_input_for_mechanistic(report)
    tokens = [token for token in trace_input.split() if token]
    head_records = {
        str(head.get("name")): dict(head)
        for head in list(trace_payload.get("heads") or [])
        if isinstance(head, dict) and head.get("name") is not None
    }

    strengths: dict[str, float] = {}
    for head in _CANONICAL_HEADS:
        top_attr = head_records.get(head, {}).get("top_k_attribution") or []
        total = 0.0
        for pair in top_attr:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                total += abs(_clean_float(pair[1]))
        strengths[head] = total
    strength_total = sum(strengths.values())

    per_head_attribution: dict[str, Any] = {}
    raw_logits: dict[str, list[float]] = {}
    for head in _CANONICAL_HEADS:
        record = head_records.get(head, {})
        raw_logits[head] = [
            _clean_float(value)
            for value in list(record.get("raw_logits") or [])
            if isinstance(value, (int, float))
        ]
        token_weights = [
            _stable_score(trace_input, head, token, index)
            * max(0.01, _clean_float(record.get("confidence")))
            for index, token in enumerate(tokens)
        ]
        top_dims = []
        for pair in list(record.get("top_k_attribution") or [])[:5]:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                top_dims.append(
                    {
                        "index": int(pair[0]),
                        "score": _clean_float(pair[1]),
                    }
                )
        per_head_attribution[head] = {
            "confidence": _clean_float(record.get("confidence")),
            "capacity_share": _clean_float(
                (strengths[head] / strength_total)
                if strength_total > 0.0
                else (1.0 / len(_CANONICAL_HEADS))
            ),
            "argmax_index": record.get("argmax_index"),
            "argmax_label": record.get("argmax_label"),
            "top_tokens": _top_token_records(tokens, token_weights),
            "top_bottleneck_dims": top_dims,
            "attribution_basis": "live_bottleneck_gradient_x_activation",
        }

    logits_summary = _logits_summary_from_raw(raw_logits)
    copy_summary = _copy_distribution_summary(report)
    hook_status = dict(trace_payload.get("hook_status") or {})
    trace_diagnostics = list(trace_payload.get("diagnostics") or [])
    runtime_diagnostics = list(live_runtime.get("diagnostics") or [])
    diagnostics = runtime_diagnostics + trace_diagnostics
    if "token_gradient_attribution_pending" not in diagnostics:
        diagnostics.append("token_gradient_attribution_pending")

    activation_layers = [
        _live_trace_layer_summary(layer)
        for layer in list(trace_payload.get("layer_activations") or [])
        if isinstance(layer, dict)
    ]
    activation_summary = {
        "headline": "live CAS Native structured-token predictor trace",
        "schema_version": trace_payload.get("schema_version"),
        "run_dir": live_runtime.get("run_dir"),
        "device": live_runtime.get("device"),
        "elapsed_ms": live_runtime.get("elapsed_ms"),
        "timing": dict(trace_payload.get("timing") or {}),
        "attention_entropy_summary": dict(
            trace_payload.get("attention_entropy_summary") or {}
        ),
        "bottleneck_top_k": [
            {
                "index": int(pair[0]),
                "activation": _clean_float(pair[1]),
            }
            for pair in list(trace_payload.get("bottleneck_top_k") or [])[:8]
            if isinstance(pair, (list, tuple)) and len(pair) >= 2
        ],
        "prediction": prediction,
    }

    return {
        "schema_version": "mode7_mechanistic_axis_attrs.v1",
        "source": "cas_native.inference.predict_cas.live_trace",
        "trace_input_token_count": len(tokens),
        "activation_hooks": {
            "source": "cas_native.trace.live_capture.capture_live_trace",
            "hook_status": hook_status,
            "captured": [name for name, fired in hook_status.items() if fired],
            "missing": [name for name, fired in hook_status.items() if not fired],
            "diagnostics": diagnostics,
        },
        "activation_layers": activation_layers,
        "activation_summary": activation_summary,
        "per_head_attribution": per_head_attribution,
        "load_bearing_tokens": _live_token_records(report, tokens),
        "logits_summary": logits_summary,
        "copy_distribution_summary": copy_summary,
        "logits_copy_distribution_summary": {
            "logits": logits_summary,
            "copy": copy_summary,
        },
        "domain_descent_attention": _domain_descent_attention_summary(
            report,
            prediction,
        ),
        "structured_prediction": prediction,
        "diagnostics": diagnostics,
    }


def _build_mechanistic_axis_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Build compact Mode 7 mechanistic fields for SGGS axis_attrs."""
    _ensure_cas_native_alias()
    mode7 = report.get("mode7") or {}
    live_runtime = mode7.get("live_runtime")
    if isinstance(live_runtime, dict) and live_runtime.get("live_trace"):
        return _mechanistic_summary_from_live_trace(report, live_runtime)

    trace_input = _trace_input_for_mechanistic(report)
    predictor_diagnostics = list(mode7.get("predictor_diagnostics") or [])
    try:
        from cas_native.trace.mechanistic import render_trace_json, trace_prediction

        trace = trace_prediction(
            None,
            trace_input,
            capture_level="raw",
            top_k=5,
        )
        payload = render_trace_json(trace)
    except Exception as exc:
        return _fallback_mechanistic_summary(
            report,
            predictor_diagnostics
            + [f"mechanistic_trace_fallback:{type(exc).__name__}"],
        )

    metadata = payload.get("metadata") or {}
    raw = metadata.get("raw_activations") or {}
    tokens = [str(token) for token in metadata.get("tokens") or []]
    per_token = payload.get("per_token_attribution") or {}
    per_head_conf = payload.get("per_head_confidence") or {}
    capacity = payload.get("capacity_allocation") or {}

    per_head_attribution: dict[str, Any] = {}
    for head in _CANONICAL_HEADS:
        weights = per_token.get(head) or []
        if not isinstance(weights, list):
            weights = []
        per_head_attribution[head] = {
            "confidence": _clean_float(per_head_conf.get(head)),
            "capacity_share": _clean_float(capacity.get(head)),
            "top_tokens": _top_token_records(tokens, weights),
        }

    raw_logits = raw.get("per_head_logits") or {}
    logits_summary = _logits_summary_from_raw(raw_logits)
    copy_summary = _copy_distribution_summary(report)
    hook_status = dict(metadata.get("hook_status") or {})
    activation_layers = [
        _vector_summary("pre_bottleneck", raw.get("pre_bottleneck")),
        _vector_summary("post_bottleneck", raw.get("post_bottleneck")),
    ]
    diagnostics = predictor_diagnostics + list(metadata.get("diagnostics") or [])

    return {
        "schema_version": "mode7_mechanistic_axis_attrs.v1",
        "source": "cas_native.trace.mechanistic.trace_prediction",
        "trace_input_token_count": len(tokens),
        "activation_hooks": {
            "source": "cas_native.trace.mechanistic",
            "hook_status": hook_status,
            "captured": [name for name, fired in hook_status.items() if fired],
            "missing": [name for name, fired in hook_status.items() if not fired],
            "diagnostics": diagnostics,
        },
        "activation_layers": activation_layers,
        "activation_summary": dict(metadata.get("activation_summary") or {}),
        "per_head_attribution": per_head_attribution,
        "load_bearing_tokens": _load_bearing_tokens(report, tokens, per_token),
        "logits_summary": logits_summary,
        "copy_distribution_summary": copy_summary,
        "logits_copy_distribution_summary": {
            "logits": logits_summary,
            "copy": copy_summary,
        },
        "domain_descent_attention": _domain_descent_attention_summary(
            report,
            dict(payload.get("prediction") or {}),
        ),
        "diagnostics": diagnostics,
    }


def _validated_expression(prompt: str, expression: str | None) -> tuple[str, list[str]]:
    warnings: list[str] = []
    candidate = (expression or "").strip()
    if not candidate:
        candidate = _synthesize_from_signals(prompt)
        warnings.append("No expression supplied; used deterministic local synthesis.")

    artifact = compile_expression(candidate)
    if artifact.valid:
        return candidate, warnings

    fallback = "CO-0^C_{F1}"
    warnings.append(
        "Supplied expression did not compile; used deterministic identity fallback."
    )
    return fallback, warnings


def _build_trace_report(prompt: str, expression: str | None) -> tuple[dict[str, Any], list[str]]:
    """Build a cas-explain-shaped report for the Mode 7 stream."""
    _ensure_cas_native_alias()
    from cas_native.inference.plain_english import translate_explain
    from cas_native.inference.traceability_v0 import build_v0_trace

    live_runtime, predictor_diagnostics = _try_live_cas_native_prediction(prompt)
    warnings: list[str] = []
    if (expression or "").strip():
        cas_expression, validation_warnings = _validated_expression(prompt, expression)
        warnings.extend(validation_warnings)
    elif live_runtime is not None:
        prediction = dict(live_runtime.get("prediction") or {})
        candidate = _cas_expression_from_prediction(prediction)
        artifact = compile_expression(candidate)
        if artifact.valid:
            cas_expression = candidate
            warnings.append("CAS Native structured-token predictor inferred the CAS expression from the prompt.")
        else:
            cas_expression, validation_warnings = _validated_expression(prompt, expression)
            warnings.extend(validation_warnings)
            warnings.append("CAS Native predictor expression did not compile; used deterministic fallback expression.")
    else:
        cas_expression, validation_warnings = _validated_expression(prompt, expression)
        warnings.extend(validation_warnings)

    expected = _extract_identifiers(cas_expression)
    if live_runtime is not None:
        generated = _render_prediction_english(
            prompt,
            cas_expression,
            dict(live_runtime.get("prediction") or {}),
        )
    else:
        generated = (
            f"Mode 7 local trace for: {prompt.strip() or cas_expression}. "
            f"CAS expression: {cas_expression}"
        )
    emitted = _extract_identifiers(generated)
    emitted_set = set(emitted)
    copied = [identifier for identifier in expected if identifier in emitted_set]
    missing = [identifier for identifier in expected if identifier not in emitted_set]
    coverage = (len(copied) / len(expected)) if expected else 0.0
    runtime_name = (
        "cas_native_structured_token_predictor"
        if live_runtime is not None
        else "deterministic_fallback"
    )
    decode_seconds = (
        _clean_float(float(live_runtime.get("elapsed_ms") or 0.0) / 1000.0)
        if live_runtime is not None
        else 0.0
    )

    report: dict[str, Any] = {
        "command": "mode7 live",
        "version": 1,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_prompt": prompt,
        "input_cas_expression": cas_expression,
        "model": {
            "runtime": runtime_name,
            "decode_seconds": decode_seconds,
        },
        "generated_english": generated,
        "n_tokens_generated": len(generated.split()),
        "identifiers": {
            "expected": expected,
            "emitted": emitted,
            "copied": copied,
            "missing": missing,
            "coverage": coverage,
        },
        "slot_summary": _slot_summary_for(generated),
        "gates": {
            "no_crash": True,
            "generated_non_empty": bool(generated),
            "ge_one_identifier_copied": bool(copied),
        },
        "mode7": {
            "runtime": runtime_name,
            "source": (
                "cas_native.inference.predict_cas.live_trace"
                if live_runtime is not None
                else "cas_native.traceability_v0.thought_tree"
            ),
            "live_runtime": live_runtime,
            "predictor_diagnostics": predictor_diagnostics,
        },
    }
    report["plain_english"] = translate_explain(report)
    report["traceability_v0"] = build_v0_trace(report)
    report["mode7"]["mechanistic_trace"] = _build_mechanistic_axis_summary(report)
    return report, warnings


def _node_parent_map(edges: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(edge.get("target")): str(edge.get("source"))
        for edge in edges
        if edge.get("source") is not None and edge.get("target") is not None
    }


def _head_name(node: dict[str, Any]) -> str:
    kind = str(node.get("kind") or "")
    if kind in {"identifier_attempt", "slot_pattern", "confidence_marker", "model_generation"}:
        return kind
    return kind or "thought_tree"


def _edges_by_target(edges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        target = edge.get("target")
        if target is None:
            continue
        grouped.setdefault(str(target), []).append(edge)
    return grouped


def _relevant_heads_for_node(node: dict[str, Any]) -> list[str]:
    kind = str(node.get("kind") or "")
    heads = list(_NODE_RELEVANT_HEADS.get(kind, ("turn_type", "domain", "drive")))
    axis_attrs = node.get("axis_attrs") or {}
    if isinstance(axis_attrs, dict):
        if axis_attrs.get("domain") is not None and "domain" not in heads:
            heads.append("domain")
        if axis_attrs.get("drive") is not None and "drive" not in heads:
            heads.append("drive")
        if axis_attrs.get("register") is not None and "register" not in heads:
            heads.append("register")
    return heads


def _node_load_bearing_tokens(
    node: dict[str, Any],
    tokens: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    label = str(node.get("label") or "")
    if not label:
        return tokens[:6]
    exact = [
        token
        for token in tokens
        if token.get("token") == label or label in str(token.get("token") or "")
    ]
    if not exact:
        return tokens[:6]
    seen = {int(token.get("index", -1)) for token in exact}
    return exact + [
        token for token in tokens if int(token.get("index", -1)) not in seen
    ][: max(0, 6 - len(exact))]


def _structural_commit_linkage(
    *,
    turn_id: str,
    trace_id: str,
    head_index: int,
    head_name: str,
    node: dict[str, Any],
    parent_node_id: str | None,
    node_by_id: dict[str, dict[str, Any]],
    incoming_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    parent = node_by_id.get(parent_node_id or "")
    return {
        "schema_version": "sggs_structural_commit_linkage.v1",
        "commit_event": "head_commit",
        "turn_id": turn_id,
        "trace_id": trace_id,
        "head_index": head_index,
        "head_name": head_name,
        "node_id": str(node.get("id") or ""),
        "node_key": node.get("node_key"),
        "node_kind": node.get("kind"),
        "parent_node_id": parent_node_id,
        "parent_node_key": parent.get("node_key") if parent else None,
        "incoming_edges": [
            {
                "edge_id": str(edge.get("id") or ""),
                "edge_key": edge.get("edge_key"),
                "source_node_id": str(edge.get("source") or ""),
                "source_node_key": edge.get("source_key"),
                "target_node_id": str(edge.get("target") or ""),
                "target_node_key": edge.get("target_key"),
                "edge_kind": str(edge.get("kind") or "parent_child"),
            }
            for edge in incoming_edges
        ],
    }


def _mode7_axis_attrs_for_commit(
    *,
    turn_id: str,
    trace_id: str,
    head_index: int,
    head_name: str,
    node: dict[str, Any],
    parent_node_id: str | None,
    node_by_id: dict[str, dict[str, Any]],
    incoming_edges: list[dict[str, Any]],
    mechanistic: dict[str, Any],
) -> dict[str, Any]:
    relevant_heads = _relevant_heads_for_node(node)
    all_head_attribution = dict(mechanistic.get("per_head_attribution") or {})
    return {
        "mode7_semantics": {
            "mode": 7,
            "name": "Network Attribution / Mechanistic Trace",
            "schema_version": mechanistic.get("schema_version"),
            "source": mechanistic.get("source"),
            "node_relevant_heads": relevant_heads,
        },
        "activation_hooks": dict(mechanistic.get("activation_hooks") or {}),
        "activation_layers": list(mechanistic.get("activation_layers") or []),
        "activation_summary": dict(mechanistic.get("activation_summary") or {}),
        "per_head_attribution": all_head_attribution,
        "node_relevant_head_attribution": {
            head: all_head_attribution.get(head, {})
            for head in relevant_heads
        },
        "load_bearing_tokens": _node_load_bearing_tokens(
            node,
            list(mechanistic.get("load_bearing_tokens") or []),
        ),
        "logits_summary": dict(mechanistic.get("logits_summary") or {}),
        "copy_distribution_summary": dict(
            mechanistic.get("copy_distribution_summary") or {}
        ),
        "logits_copy_distribution_summary": dict(
            mechanistic.get("logits_copy_distribution_summary") or {}
        ),
        "domain_descent_attention": dict(
            mechanistic.get("domain_descent_attention") or {}
        ),
        "structural_commit_linkage": _structural_commit_linkage(
            turn_id=turn_id,
            trace_id=trace_id,
            head_index=head_index,
            head_name=head_name,
            node=node,
            parent_node_id=parent_node_id,
            node_by_id=node_by_id,
            incoming_edges=incoming_edges,
        ),
        "mechanistic_diagnostics": list(mechanistic.get("diagnostics") or []),
    }


async def _stream_report(
    *,
    turn_id: str,
    prompt: str,
    report: dict[str, Any],
    warnings: list[str],
    delay_ms: int,
) -> AsyncIterator[str]:
    _ensure_cas_native_alias()
    from cas_native.inference.sggs_stream import (
        emit_edge_commit,
        emit_head_commit,
        emit_turn_end,
        emit_turn_start,
        emit_warning,
    )

    started = time.perf_counter()
    trace = report["traceability_v0"]
    tree = trace["thought_tree"]
    nodes = list(tree.get("nodes") or [])
    edges = list(tree.get("edges") or [])
    parent_by_node = _node_parent_map(edges)
    incoming_edges_by_target = _edges_by_target(edges)
    node_by_id = {
        str(node.get("id")): node
        for node in nodes
        if node.get("id") is not None
    }
    trace_id = str(trace.get("trace_id") or "")
    mechanistic = dict((report.get("mode7") or {}).get("mechanistic_trace") or {})

    yield emit_turn_start(turn_id=turn_id, user_text=prompt or report["input_cas_expression"])
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    for message in warnings:
        yield emit_warning(turn_id=turn_id, severity="info", message=message)
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)

    head_count = 0
    for node in nodes:
        node_id = str(node.get("id") or "")
        if node_id == "n0":
            continue
        head_name = _head_name(node)
        parent_node_id = parent_by_node.get(node_id)
        axis_attrs = dict(node.get("axis_attrs") or {})
        axis_attrs.update(
            {
                "node_key": node.get("node_key"),
                "role": node.get("role"),
                "normalized_label": node.get("normalized_label"),
            }
        )
        axis_attrs.update(
            _mode7_axis_attrs_for_commit(
                turn_id=turn_id,
                trace_id=trace_id,
                head_index=head_count,
                head_name=head_name,
                node=node,
                parent_node_id=parent_node_id,
                node_by_id=node_by_id,
                incoming_edges=incoming_edges_by_target.get(node_id, []),
                mechanistic=mechanistic,
            )
        )
        yield emit_head_commit(
            turn_id=turn_id,
            head_index=head_count,
            head_name=head_name,
            node_id=node_id,
            node_kind=str(node.get("kind") or ""),
            node_label=str(node.get("label") or ""),
            parent_node_id=parent_node_id,
            axis_attrs=axis_attrs,
        )
        head_count += 1
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)

        for edge in edges:
            if str(edge.get("target")) != node_id:
                continue
            yield emit_edge_commit(
                turn_id=turn_id,
                edge_id=str(edge.get("id") or ""),
                source_node_id=str(edge.get("source") or ""),
                target_node_id=str(edge.get("target") or ""),
                kind=str(edge.get("kind") or "parent_child"),
            )
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)

    duration_ms = int((time.perf_counter() - started) * 1000)
    yield emit_turn_end(
        turn_id=turn_id,
        final_trace_id=str(trace.get("trace_id") or ""),
        total_heads=head_count,
        duration_ms=duration_ms,
    )


@router.get("/live")
async def live(
    prompt: str = Query("", max_length=10000),
    expression: str | None = Query(None, max_length=10000),
    delay_ms: int = Query(0, ge=0, le=1000),
) -> StreamingResponse:
    """Stream SGGS commits for one local Mode 7 turn.

    Query params:
      - prompt: stakeholder/user text. Required unless expression is supplied.
      - expression: optional CAS expression. If omitted, a deterministic local
        synthesis from prompt is used.
      - delay_ms: optional inter-event delay for demos/tests.
    """
    if not prompt.strip() and not (expression or "").strip():
        raise HTTPException(status_code=422, detail="prompt or expression is required")

    report, warnings = _build_trace_report(prompt, expression)
    turn_id = f"mode7-{uuid.uuid4().hex[:12]}"
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        _stream_report(
            turn_id=turn_id,
            prompt=prompt,
            report=report,
            warnings=warnings,
            delay_ms=delay_ms,
        ),
        media_type="text/event-stream",
        headers=headers,
    )


@router.get("/runtime")
async def runtime(
    load: bool = Query(
        False,
        description="When true, attempts to load the CAS Native predictor weights.",
    ),
) -> dict[str, Any]:
    """Report whether Mode 7 will use CAS Native live predictor or fallback."""
    return _mode7_runtime_status(load_predictor=load)
