#!/usr/bin/env python3
"""Honest two-pass diagram-loop invariance evaluation.

CRITICAL INVARIANT — NO ORACLE LEAK
====================================
``compile_to_graph`` must NEVER be called on the ground-truth ``cas_expression``
field of any eval record in this module.  Every call to ``compile_to_graph``
must receive a string that originated from the model's own structured-head
predictions (pass-1 output).

The leaky anti-pattern is:

    # WRONG — oracle leak
    variant["prior_diagram"] = compile_to_graph(record["cas_expression"])

The honest pattern implemented here is:

    # CORRECT — self-prediction prior
    predicted = canonical_predictions[record["id"]]          # model's own prediction
    variant["prior_diagram"] = compile_to_graph(predicted)   # never ground truth

Any future modification to this file must preserve this invariant.  If you are
not sure whether a ``compile_to_graph`` call is safe, grep for the source of the
string being passed in and confirm it comes from ``canonical_predictions``, not
from a record's ``cas_expression`` field.

Two-pass protocol
-----------------
Pass 1: text-only inference on canonical eval records.
    ``predict_canonical`` runs the model with ``graph_batch=None`` and returns a
    ``{record_id: predicted_cas_expression}`` mapping.

Pass 2: paraphrase eval with self-prediction priors.
    ``compile_self_prediction_priors`` uses pass-1 outputs to build
    ``prior_diagram`` graphs.  These are attached to paraphrase variants.
    The model is then run on each variant with the self-prediction prior.

Reported metrics (four conditions):
    canonical_text_only         — pass-1 accuracy (text-only, no prior)
    canonical_with_self_prior   — canonical prompts re-run with self prior
    paraphrase_text_only        — paraphrase variants with no prior
    paraphrase_with_self_prior  — paraphrase variants with self prior (lever test)
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import torch

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

_CAS_NATIVE_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _CAS_NATIVE_ROOT.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(_CAS_NATIVE_ROOT / "__init__.py")
    package.__path__ = [str(_CAS_NATIVE_ROOT)]
    sys.modules["cas_native"] = package

from cas_native.model.structured_prediction import (
    AUTHORITY_LABELS,
    DOMAIN_LABELS,
    DRIVE_LABELS,
    EXPRESSION_FAMILY_LABELS,
    META_RELATION_LABELS,
    REGISTER_LABELS,
    REGISTER_MODE_LABELS,
    StructuredPredictionHead,
    TRANSITION_KIND_LABELS,
    TURN_TYPE_LABELS,
)
from cas_native.model.structured_token_embedding import (
    StructuredTokenEmbedding,
    StructuredTokenStructuredPredictor,
)
from cas_native.model.graph_encoder import GraphEncoder
from cas_native.model.graph_text_fusion import GraphTextFusion
from cas_native.training.diagram_serialization import NODE_FEATURE_DIM, EDGE_FEATURE_DIM
from cas_native.tokenizer.vocabulary import StructuredTokenVocabulary
from cas_native.training.structured_prediction_ingest import (
    batch_targets_from_records,
    load_level3_jsonl,
)
from cas_native.training.structured_token_adapter import (
    records_to_structured_token_sequences,
    tokens_to_structured_token_batch,
)
from cas_native.training.paraphrase_templates import (
    EVAL_PARAPHRASE_TEMPLATES,
    apply_template,
)
from cas_native.training.diagram_serialization import (
    compile_to_graph,
    serialize_diagram_for_batch,
)

# ---------------------------------------------------------------------------
# Scalar head configuration (mirrors train_structured_prediction._SCALAR_HEAD_PAIRS)
# ---------------------------------------------------------------------------

_SCALAR_HEAD_PAIRS: tuple[tuple[str, str], ...] = (
    ("turn_type", "turn_type_logits"),
    ("expression_family", "expression_family_logits"),
    ("transition_kind", "transition_kind_logits"),
    ("noetic", "noetic_logits"),
    ("domain", "domain_logits"),
    ("drive", "drive_logits"),
    ("register_mode", "register_mode_logits"),
    ("authority", "authority_logits"),
    ("has_omega", "omega_logits"),
    ("has_meta_logic", "meta_logic_logits"),
)

_SCALAR_HEAD_LABELS: dict[str, tuple[Any, ...]] = {
    "turn_type": TURN_TYPE_LABELS,
    "expression_family": EXPRESSION_FAMILY_LABELS,
    "transition_kind": TRANSITION_KIND_LABELS,
    "noetic": tuple(range(10)),
    "domain": DOMAIN_LABELS,
    "drive": DRIVE_LABELS,
    "register_mode": REGISTER_MODE_LABELS,
    "authority": AUTHORITY_LABELS,
    "has_omega": (False, True),
    "has_meta_logic": (False, True),
}

_EVAL_LOGIT_KEYS: tuple[str, ...] = tuple(pair[1] for pair in _SCALAR_HEAD_PAIRS) + (
    "register_logits",
    "meta_relation_logits",
)

EVAL_PARAPHRASE_SOURCE_LABEL = "diagloop_honest_eval_template"


# ---------------------------------------------------------------------------
# Pass 1 — text-only canonical inference
# ---------------------------------------------------------------------------


def predict_canonical(
    model: StructuredTokenStructuredPredictor,
    vocabulary: StructuredTokenVocabulary,
    records: list[dict[str, Any]],
    *,
    token_sequences: list[list[Any]] | None = None,
    device: str = "cpu",
    batch_size: int = 64,
    max_length: int = 256,
) -> dict[str, str]:
    """Run pass-1 text-only inference and return a record_id → predicted CAS string map.

    The model is called with ``graph_batch=None``.  No ground-truth information
    is used.  The returned strings are built solely from the model's structured-
    head argmax predictions.

    INVARIANT: this function never reads ``record["cas_expression"]``.
    """
    dev = torch.device(device)
    model.eval()

    if token_sequences is None:
        token_sequences = records_to_structured_token_sequences(records)
    if len(token_sequences) != len(records):
        raise ValueError(
            "token_sequences length must match records length: "
            f"{len(token_sequences)} != {len(records)}"
        )

    chunks: dict[str, list[torch.Tensor]] = {key: [] for key in _EVAL_LOGIT_KEYS}
    with torch.no_grad():
        for start in range(0, len(records), batch_size):
            batch_sequences = token_sequences[start : start + batch_size]
            batch = tokens_to_structured_token_batch(
                batch_sequences,
                vocabulary,
                max_length=max_length,
                device=dev,
            )
            # Pass 1: text-only — graph_batch is never provided
            batch_outputs = model(batch)
            for key in _EVAL_LOGIT_KEYS:
                chunks[key].append(batch_outputs[key])

    model.train()
    outputs = {key: torch.cat(parts, dim=0) for key, parts in chunks.items()}
    predictions_per_record = _decode_predictions(outputs, len(records))

    result: dict[str, str] = {}
    for i, record in enumerate(records):
        record_id = str(record.get("id") or f"__idx_{i}")
        result[record_id] = _predictions_to_cas_string(predictions_per_record[i])
    return result


# ---------------------------------------------------------------------------
# Pass 2 preparation — build self-prediction priors
# ---------------------------------------------------------------------------


def compile_self_prediction_priors(
    canonical_predictions: dict[str, str],
    eval_records: list[dict[str, Any]],
    *,
    variants_per_record: int = 3,
) -> list[dict[str, Any]]:
    """Generate paraphrase variants with self-prediction priors attached.

    For each eval record the prior graph is compiled from the MODEL'S OWN
    prediction captured in pass 1.  It is NEVER compiled from the record's
    ground-truth ``cas_expression`` field.

    When the model's canonical prediction is empty or syntactically invalid,
    ``compile_to_graph`` returns ``None`` and that ``None`` is stored as
    ``prior_diagram`` (zero-attention fallback in pass 2).

    Args:
        canonical_predictions: ``{record_id: predicted_cas_string}`` from pass 1.
        eval_records: Held-out eval records (ground truth only used for scoring,
            not for building priors).
        variants_per_record: Number of EVAL_PARAPHRASE_TEMPLATES variants to
            generate per record.

    Returns:
        List of paraphrase variant dicts, each with ``prior_diagram`` set to a
        graph compiled from the model's own pass-1 prediction.
    """
    if variants_per_record <= 0:
        raise ValueError("variants_per_record must be positive")

    variants: list[dict[str, Any]] = []
    for record in eval_records:
        record_id = str(record.get("id") or "")
        # Retrieve the MODEL'S OWN prediction — NEVER read cas_expression here
        predicted_expr = canonical_predictions.get(record_id, "")
        # Build prior from model's own prediction, not ground truth
        prior_diagram = _safe_compile(predicted_expr)

        for index in range(variants_per_record):
            template = EVAL_PARAPHRASE_TEMPLATES[index % len(EVAL_PARAPHRASE_TEMPLATES)]
            variant = apply_template(
                record,
                template,
                paraphrase_index=index,
                paraphrase_source=EVAL_PARAPHRASE_SOURCE_LABEL,
            )
            variant["prior_diagram"] = prior_diagram
            variant["prior_diagram_source"] = "self_prediction"
            variant["canonical_prediction"] = predicted_expr
            variants.append(variant)

    return variants


# ---------------------------------------------------------------------------
# Pass 2 — paraphrase inference with self-prediction priors
# ---------------------------------------------------------------------------


def _run_pass2_inference(
    model: StructuredTokenStructuredPredictor,
    vocabulary: StructuredTokenVocabulary,
    variants: list[dict[str, Any]],
    *,
    token_sequences: list[list[Any]] | None = None,
    device: str = "cpu",
    batch_size: int = 64,
    max_length: int = 256,
) -> list[dict[str, Any]]:
    """Run pass-2 inference on paraphrase variants with self-prediction priors.

    The prior_diagram attached to each variant (a graph compiled from the
    model's own pass-1 prediction) is serialised into ``graph_batch`` and
    passed to the model.  Ground-truth ``cas_expression`` is never used here.
    """
    dev = torch.device(device)
    model.eval()

    if token_sequences is None:
        token_sequences = records_to_structured_token_sequences(variants)

    chunks: dict[str, list[torch.Tensor]] = {key: [] for key in _EVAL_LOGIT_KEYS}
    with torch.no_grad():
        for start in range(0, len(variants), batch_size):
            batch_variants = variants[start : start + batch_size]
            batch_sequences = token_sequences[start : start + batch_size]
            batch = tokens_to_structured_token_batch(
                batch_sequences,
                vocabulary,
                max_length=max_length,
                device=dev,
            )
            # Pass 2: provide prior graphs built from pass-1 self-predictions
            prior_graphs = [v.get("prior_diagram") for v in batch_variants]
            graph_batch = serialize_diagram_for_batch(prior_graphs, device=str(dev))
            batch_outputs = model(batch, graph_batch=graph_batch)
            for key in _EVAL_LOGIT_KEYS:
                chunks[key].append(batch_outputs[key])

    model.train()
    return {key: torch.cat(parts, dim=0) for key, parts in chunks.items()}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _build_sample_list(
    outputs: dict[str, torch.Tensor],
    targets_all: dict[str, torch.Tensor],
    records: list[dict[str, Any]],
    *,
    extra_fields: dict[str, list[Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build per-sample dicts from model outputs and ground-truth targets."""
    n = len(records)
    correct: dict[str, list[bool]] = {}
    predictions: dict[str, list[Any]] = {}

    for target_key, logit_key in _SCALAR_HEAD_PAIRS:
        if target_key in targets_all and logit_key in outputs:
            preds = outputs[logit_key].argmax(dim=-1)
            correct[target_key] = (preds == targets_all[target_key]).cpu().tolist()
            predictions[target_key] = _scalar_label_values(
                preds, _SCALAR_HEAD_LABELS[target_key]
            )

    if "registers" in targets_all and "register_logits" in outputs:
        reg_pred = (outputs["register_logits"].sigmoid() >= 0.5).to(
            targets_all["registers"].dtype
        )
        correct["registers"] = (
            (reg_pred == targets_all["registers"]).all(dim=-1).cpu().tolist()
        )
        predictions["registers"] = _multi_label_values(reg_pred, REGISTER_LABELS)

    if "meta_relations" in targets_all and "meta_relation_logits" in outputs:
        mr_pred = (outputs["meta_relation_logits"].sigmoid() >= 0.5).to(
            targets_all["meta_relations"].dtype
        )
        correct["meta_relations"] = (
            (mr_pred == targets_all["meta_relations"]).all(dim=-1).cpu().tolist()
        )
        predictions["meta_relations"] = _multi_label_values(
            mr_pred, META_RELATION_LABELS
        )

    head_keys = list(correct.keys())
    all_exact = [all(correct[key][i] for key in head_keys) for i in range(n)]

    samples: list[dict[str, Any]] = []
    for i, record in enumerate(records):
        entry: dict[str, Any] = {
            "id": record.get("id"),
            "base_id": record.get("base_id"),
            "paraphrase_index": record.get("paraphrase_index"),
            "bucket": record.get("bucket"),
            "all_heads_exact": bool(all_exact[i]),
            "head_correct": {key: bool(correct[key][i]) for key in head_keys},
            "prediction": {key: predictions[key][i] for key in head_keys},
        }
        if extra_fields:
            for field_name, field_list in extra_fields.items():
                entry[field_name] = field_list[i]
        samples.append(entry)

    return samples


def _aggregate_manifest(
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    n = len(samples)
    if n == 0:
        return {"n": 0, "all_heads_exact": 0, "all_heads_exact_rate": 0.0, "by_bucket": {}}
    all_exact_count = sum(1 for s in samples if s["all_heads_exact"])
    head_keys = list(samples[0].get("head_correct", {}).keys())
    per_head = {
        key: sum(1 for s in samples if s["head_correct"].get(key, False)) / n
        for key in head_keys
    }
    by_bucket: dict[str, dict[str, Any]] = defaultdict(lambda: {"n": 0, "exact": 0})
    for sample in samples:
        bucket = str(sample.get("bucket") or "unknown")
        by_bucket[bucket]["n"] += 1
        if sample["all_heads_exact"]:
            by_bucket[bucket]["exact"] += 1
    bucket_summary = {
        bucket: {
            "n": data["n"],
            "all_heads_exact": data["exact"],
            "all_heads_exact_rate": data["exact"] / data["n"],
        }
        for bucket, data in sorted(by_bucket.items())
    }
    return {
        "n": n,
        "all_heads_exact": all_exact_count,
        "all_heads_exact_rate": all_exact_count / n,
        "per_head_acc": per_head,
        "by_bucket": bucket_summary,
    }


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def evaluate_diagram_loop_honest(
    run_dir: Path,
    eval_input: Path,
    *,
    checkpoint: Path | None = None,
    out_dir: Path | None = None,
    prefix: str = "diagloop_honest",
    variants_per_record: int = 3,
    limit: int | None = None,
    device: str = "cpu",
    batch_size: int = 64,
    max_length: int | None = None,
    d_model: int | None = None,
    bottleneck_dim: int | None = None,
) -> dict[str, Any]:
    """Honest two-pass diagram-loop eval orchestrator.

    Loads the model from ``run_dir``, runs pass-1 text-only inference to build
    self-prediction priors, then runs pass-2 paraphrase inference with those
    priors.  Writes three output artifacts under ``out_dir`` (defaults to
    ``run_dir``):

    - ``<prefix>_report.md``   — human-readable summary
    - ``<prefix>_report.json`` — structured report
    - ``<prefix>_samples.jsonl`` — per-record detail rows

    INVARIANT: ``compile_to_graph`` is NEVER called on any record's ground-truth
    ``cas_expression`` field in this function or any function it calls.
    """
    manifest_config = _manifest_config(run_dir)
    d_model = int(d_model or manifest_config.get("d_model", 128))
    bottleneck_dim = int(bottleneck_dim or manifest_config.get("bottleneck_dim", 64))
    max_length = int(max_length or manifest_config.get("max_length", 256))
    checkpoint = checkpoint or (run_dir / "best_structured_token_model.pt")

    vocabulary = StructuredTokenVocabulary.load(run_dir / "structured_token_vocab.json")
    embedding = StructuredTokenEmbedding(vocab_size=len(vocabulary), d_model=d_model)
    from cas_native.model.structured_prediction import StructuredPredictionHead
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim)
    graph_encoder = GraphEncoder(NODE_FEATURE_DIM, EDGE_FEATURE_DIM, hidden_dim=64)
    graph_fusion = GraphTextFusion(d_text=d_model, d_graph=64)
    model = StructuredTokenStructuredPredictor(embedding, head, graph_encoder, graph_fusion)
    model.load_state_dict(
        torch.load(checkpoint, map_location=device, weights_only=True)
    )
    model.to(torch.device(device))

    canonical_records = load_level3_jsonl(eval_input, limit=limit)
    if not canonical_records:
        raise ValueError("eval_input produced no records")

    # ---- Pass 1: text-only canonical inference ----
    canonical_token_sequences = records_to_structured_token_sequences(canonical_records)
    canonical_predictions = predict_canonical(
        model,
        vocabulary,
        canonical_records,
        token_sequences=canonical_token_sequences,
        device=device,
        batch_size=batch_size,
        max_length=max_length,
    )

    # ---- Score pass-1 canonical (text-only) ----
    canonical_targets = batch_targets_from_records(canonical_records, device=device)
    canonical_chunks: dict[str, list[torch.Tensor]] = {k: [] for k in _EVAL_LOGIT_KEYS}
    dev = torch.device(device)
    model.eval()
    with torch.no_grad():
        for start in range(0, len(canonical_records), batch_size):
            batch_seq = canonical_token_sequences[start : start + batch_size]
            batch = tokens_to_structured_token_batch(
                batch_seq, vocabulary, max_length=max_length, device=dev
            )
            out = model(batch)
            for key in _EVAL_LOGIT_KEYS:
                canonical_chunks[key].append(out[key])
    model.train()
    canonical_outputs = {k: torch.cat(v, 0) for k, v in canonical_chunks.items()}
    canonical_samples = _build_sample_list(
        canonical_outputs, canonical_targets, canonical_records
    )

    # ---- Build paraphrase variants with self-prediction priors ----
    paraphrase_variants = compile_self_prediction_priors(
        canonical_predictions,
        canonical_records,
        variants_per_record=variants_per_record,
    )

    # ---- Pass 2a: paraphrase text-only (no prior) ----
    para_text_only_records = [
        {k: v for k, v in variant.items() if k != "prior_diagram"}
        for variant in paraphrase_variants
    ]
    para_text_only_seqs = records_to_structured_token_sequences(para_text_only_records)
    para_text_only_chunks: dict[str, list[torch.Tensor]] = {k: [] for k in _EVAL_LOGIT_KEYS}
    para_text_only_targets = batch_targets_from_records(
        para_text_only_records, device=device
    )
    model.eval()
    with torch.no_grad():
        for start in range(0, len(para_text_only_records), batch_size):
            batch_seq = para_text_only_seqs[start : start + batch_size]
            batch = tokens_to_structured_token_batch(
                batch_seq, vocabulary, max_length=max_length, device=dev
            )
            out = model(batch)
            for key in _EVAL_LOGIT_KEYS:
                para_text_only_chunks[key].append(out[key])
    model.train()
    para_text_only_outputs = {k: torch.cat(v, 0) for k, v in para_text_only_chunks.items()}
    para_text_only_samples = _build_sample_list(
        para_text_only_outputs, para_text_only_targets, para_text_only_records
    )

    # ---- Pass 2b: paraphrase with self-prediction priors ----
    para_prior_seqs = records_to_structured_token_sequences(paraphrase_variants)
    para_prior_targets = batch_targets_from_records(paraphrase_variants, device=device)
    para_prior_outputs = _run_pass2_inference(
        model,
        vocabulary,
        paraphrase_variants,
        token_sequences=para_prior_seqs,
        device=device,
        batch_size=batch_size,
        max_length=max_length,
    )
    canonical_prediction_list = [
        paraphrase_variants[i]["canonical_prediction"]
        for i in range(len(paraphrase_variants))
    ]
    prior_source_list = [
        paraphrase_variants[i]["prior_diagram_source"]
        for i in range(len(paraphrase_variants))
    ]
    para_prior_samples = _build_sample_list(
        para_prior_outputs,
        para_prior_targets,
        paraphrase_variants,
        extra_fields={
            "canonical_prediction": canonical_prediction_list,
            "prior_diagram_source": prior_source_list,
        },
    )

    # ---- Assemble report ----
    canonical_manifest = _aggregate_manifest(canonical_samples)
    para_text_only_manifest = _aggregate_manifest(para_text_only_samples)
    para_prior_manifest = _aggregate_manifest(para_prior_samples)

    report = {
        "canonical_text_only": canonical_manifest["all_heads_exact_rate"],
        "paraphrase_text_only": para_text_only_manifest["all_heads_exact_rate"],
        "paraphrase_with_self_prior": para_prior_manifest["all_heads_exact_rate"],
        "paraphrase_lift_pp": (
            para_prior_manifest["all_heads_exact_rate"]
            - para_text_only_manifest["all_heads_exact_rate"]
        ) * 100.0,
        "n_canonical": canonical_manifest["n"],
        "n_paraphrase": para_prior_manifest["n"],
        "per_head_canonical_text_only": canonical_manifest.get("per_head_acc", {}),
        "per_head_paraphrase_with_self_prior": para_prior_manifest.get("per_head_acc", {}),
        "by_bucket_canonical": canonical_manifest["by_bucket"],
        "by_bucket_paraphrase_with_self_prior": para_prior_manifest["by_bucket"],
    }

    out_dir = out_dir or run_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_json(out_dir / f"{prefix}_report.json", report)
    _write_samples(out_dir / f"{prefix}_samples.jsonl", para_prior_samples)
    _write_markdown_report(out_dir / f"{prefix}_report.md", report)

    return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_compile(predicted_expr: str) -> dict | None:
    """Wrap compile_to_graph to return None on any error without crashing."""
    try:
        return compile_to_graph(predicted_expr)
    except Exception:
        return None


def _predictions_to_cas_string(prediction: dict[str, Any]) -> str:
    """Convert a structured-head prediction dict to a CAS expression string.

    This is a best-effort reconstruction from the model's own head outputs.
    It does not need to be perfect — it just needs to be the model's prediction,
    not the ground truth.
    """
    noetic = prediction.get("noetic")
    domain = prediction.get("domain")
    drive = prediction.get("drive")
    register_mode = prediction.get("register_mode")

    if noetic is None:
        return ""

    parts: list[str] = [f"^{noetic}"]
    if domain and str(domain) not in ("", "None"):
        parts.append(f"^{domain}")
    if drive and str(drive) not in ("", "None", "none"):
        parts.append(f"_{{F{_drive_index(str(drive))}}}")
    if register_mode and str(register_mode) not in ("", "None", "none", "neutral"):
        parts.append(f"|{_register_abbrev(str(register_mode))}")
    return "".join(parts)


def _drive_index(drive_label: str) -> str:
    """Extract drive number from a drive label like 'F3' or 'unity'."""
    if drive_label.startswith("F") and drive_label[1:].isdigit():
        return drive_label[1:]
    _drive_map = {
        "unity": "1", "wisdom": "2", "vitality": "3",
        "connection": "4", "agency": "5", "structure": "6", "purpose": "7",
    }
    return _drive_map.get(drive_label.lower(), drive_label)


def _register_abbrev(mode: str) -> str:
    """Map register_mode label to single-character CAS register abbreviation."""
    _map = {
        "transcendent": "T",
        "analytical": "A",
        "affective": "f",
        "embodied": "E",
    }
    return _map.get(mode.lower(), mode[:1].upper() if mode else "")


def _decode_predictions(
    outputs: dict[str, torch.Tensor],
    n: int,
) -> list[dict[str, Any]]:
    """Decode raw logit outputs into per-record prediction dicts."""
    result: list[dict[str, Any]] = [{} for _ in range(n)]
    for target_key, logit_key in _SCALAR_HEAD_PAIRS:
        if logit_key in outputs:
            preds = outputs[logit_key].argmax(dim=-1)
            labels = _SCALAR_HEAD_LABELS[target_key]
            for i, idx in enumerate(preds.cpu().tolist()):
                result[i][target_key] = labels[int(idx)]
    return result


def _scalar_label_values(indices: torch.Tensor, labels: tuple[Any, ...]) -> list[Any]:
    return [labels[int(i)] for i in indices.detach().cpu().tolist()]


def _multi_label_values(
    values: torch.Tensor, labels: tuple[str, ...]
) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in values.detach().cpu():
        rows.append([labels[i] for i, v in enumerate(row.tolist()) if float(v) >= 0.5])
    return rows


def _manifest_config(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "manifest.json"
    if not path.exists():
        return {}
    return dict(json.loads(path.read_text(encoding="utf-8")).get("config", {}))


def _write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def _write_samples(path: Path, samples: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, sort_keys=True) + "\n")


def _write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Diagram-Loop Honest Two-Pass Eval Report",
        "",
        "> **Protocol**: self-prediction priors only — no oracle, no ground-truth leak.",
        "",
        "## Four-Condition Summary",
        "",
        "| Condition | Exact Rate |",
        "|---|---:|",
        f"| Canonical text-only (pass 1) | {report['canonical_text_only']:.3f} |",
        f"| Paraphrase text-only | {report['paraphrase_text_only']:.3f} |",
        f"| Paraphrase with self-prior (pass 2) | {report['paraphrase_with_self_prior']:.3f} |",
        f"| **Honest lever lift (pp)** | **{report['paraphrase_lift_pp']:+.1f} pp** |",
        "",
        "## Per-Head Accuracy — Canonical Text-Only",
        "",
        "| Head | Rate |",
        "|---|---:|",
    ]
    for head, rate in sorted(
        report.get("per_head_canonical_text_only", {}).items(),
        key=lambda item: item[1],
    ):
        lines.append(f"| {head} | {rate:.3f} |")
    lines.extend(
        [
            "",
            "## Per-Head Accuracy — Paraphrase with Self-Prior",
            "",
            "| Head | Rate |",
            "|---|---:|",
        ]
    )
    for head, rate in sorted(
        report.get("per_head_paraphrase_with_self_prior", {}).items(),
        key=lambda item: item[1],
    ):
        lines.append(f"| {head} | {rate:.3f} |")
    lines.extend(["", "## Bucket Breakdown — Paraphrase with Self-Prior", "", "| Bucket | n | Exact Rate |", "|---|---:|---:|"])
    for bucket, data in sorted(report.get("by_bucket_paraphrase_with_self_prior", {}).items()):
        lines.append(f"| {bucket} | {data['n']} | {data['all_heads_exact_rate']:.3f} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--eval-input", required=True, type=Path)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--prefix", default="diagloop_honest")
    parser.add_argument("--variants-per-record", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-length", type=int, default=None)
    parser.add_argument("--d-model", type=int, default=None)
    parser.add_argument("--bottleneck-dim", type=int, default=None)
    args = parser.parse_args()

    report = evaluate_diagram_loop_honest(
        run_dir=args.run_dir,
        eval_input=args.eval_input,
        checkpoint=args.checkpoint,
        out_dir=args.out_dir,
        prefix=args.prefix,
        variants_per_record=args.variants_per_record,
        limit=args.limit,
        device=args.device,
        batch_size=args.batch_size,
        max_length=args.max_length,
        d_model=args.d_model,
        bottleneck_dim=args.bottleneck_dim,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
