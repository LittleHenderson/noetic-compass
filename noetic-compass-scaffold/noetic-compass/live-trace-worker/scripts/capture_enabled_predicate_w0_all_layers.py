"""Capture all W0/W1/W8 timing hidden-state layers for an enabled-predicate bank.

By default this records prompt-final W0 before any answer token exists. It can
also record W1/W8 early-generation pre-display states. W1/W8 do generate a
short internal prefix, but that prefix is saved as a control so evaluators can
reject hidden-state claims that are merely reading early output text.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import hashlib
import re
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_enabled_predicate_capture import (  # noqa: E402
    first_real_parameter_device,
    format_model_prompt,
    inference_context,
    load_model,
    load_prompt_bank,
    parse_sample_seed,
)


SCHEMA_VERSION = "cas_harness_enabled_predicate_w0_all_layers_capture.v1"


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--prompt-bank", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--label-path", action="append", type=Path, default=[])
    parser.add_argument("--model-revision")
    parser.add_argument("--torch-dtype", default="float16")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--max-scenarios", type=int, default=0)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--prompt-format", choices=("chat-auto", "raw"), default="chat-auto")
    parser.add_argument("--layers", default="all", help="'all' or comma-separated hidden_states indices")
    parser.add_argument(
        "--timing-point",
        default="W0",
        help=(
            "Timing state to capture: W0 before generation, WN after N generated tokens, "
            "or PRE_ANSWER immediately before the judged answer value appears in the forced continuation."
        ),
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for WN prefix capture. Default 0 preserves greedy historical behavior.",
    )
    parser.add_argument("--top-p", type=float, default=0.95, help="Sampling top-p for WN prefix capture.")
    parser.add_argument("--trust-remote-code", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = capture_w0_all_layers(
        model_id=args.model_id,
        prompt_bank_path=args.prompt_bank,
        output_dir=args.output_dir,
        label_paths=tuple(args.label_path),
        model_revision=args.model_revision,
        torch_dtype=args.torch_dtype,
        device_map=args.device_map,
        max_scenarios=args.max_scenarios,
        max_length=args.max_length,
        prompt_format=args.prompt_format,
        layers_arg=args.layers,
        timing_point=args.timing_point,
        temperature=args.temperature,
        top_p=args.top_p,
        trust_remote_code=args.trust_remote_code,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def capture_w0_all_layers(
    *,
    model_id: str,
    prompt_bank_path: Path,
    output_dir: Path,
    label_paths: tuple[Path, ...],
    model_revision: str | None,
    torch_dtype: str,
    device_map: str,
    max_scenarios: int,
    max_length: int,
    prompt_format: str,
    layers_arg: str,
    timing_point: str = "W0",
    temperature: float = 0.0,
    top_p: float = 0.95,
    trust_remote_code: bool,
) -> dict[str, Any]:
    timing_mode = parse_timing_mode(timing_point)
    scenarios = load_prompt_bank(prompt_bank_path)
    if max_scenarios > 0:
        scenarios = scenarios[:max_scenarios]
    label_map = load_label_map(label_paths)
    model, tokenizer, model_info = load_model(
        model_id=model_id,
        model_revision=model_revision,
        torch_dtype=torch_dtype,
        device_map=device_map,
        trust_remote_code=trust_remote_code,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / "enabled_predicate_w0_all_layers_dataset.npz"
    metadata_path = output_dir / "enabled_predicate_w0_all_layers_manifest.json"
    rows_path = output_dir / "enabled_predicate_w0_all_layers_rows.jsonl"

    features: list[np.ndarray] = []
    rows: list[dict[str, Any]] = []
    resolved_layers: list[int] | None = None
    for index, scenario in enumerate(scenarios, 1):
        model_prompt = format_model_prompt(
            tokenizer=tokenizer,
            prompt=str(scenario["prompt"]),
            prompt_format=prompt_format,
        )
        support_status = normalise_support_status(scenario.get("support_status") or scenario.get("target_support_status"))
        row_timing = resolve_scenario_timing(
            tokenizer=tokenizer,
            scenario=scenario,
            timing_mode=timing_mode,
            support_status=support_status,
        )
        layer_vectors, layer_indices, token_count, generated_prefix_text, generated_prefix_token_count = (
            capture_timing_layers(
                model=model,
                tokenizer=tokenizer,
                prompt=model_prompt,
                max_length=max_length,
                layers_arg=layers_arg,
                timing_index=row_timing["timing_index"],
                seed=parse_sample_seed(str(scenario.get("id") or scenario.get("scenario_id") or index), fallback=index),
                temperature=temperature,
                top_p=top_p,
                forced_token_ids=parse_token_id_list(scenario.get("continuation_token_ids")),
            )
        )
        if resolved_layers is None:
            resolved_layers = layer_indices
        elif resolved_layers != layer_indices:
            raise RuntimeError(f"Layer set changed during capture: {resolved_layers} vs {layer_indices}")
        features.append(layer_vectors)
        scenario_id = str(scenario["id"])
        label = label_map.get(scenario_id) or label_map.get(f"{scenario_id}::capture")
        label_source = "label_jsonl" if label else "expected_behavior"
        if not label:
            if support_status:
                label = support_status
                label_source = "scenario_support_status"
            else:
                label = str(scenario.get("expected_behavior") or "")
        if not support_status:
            support_status = normalise_support_status(label)
        domain = scenario.get("domain") or scenario.get("expected_cas_axes", {}).get("domain", "")
        topic = scenario.get("topic") or scenario.get("payload_class", "")
        row = {
            "trace_id": f"{scenario_id}::{row_timing['timing_point'].lower()}_all_layers",
            "scenario_id": scenario_id,
            "timing_point": row_timing["timing_point"],
            "timing_index": row_timing["timing_index"],
            "timing_mode": row_timing["timing_mode"],
            "answer_boundary_token_index": row_timing.get("answer_boundary_token_index", -1),
            "answer_boundary_found": row_timing.get("answer_boundary_found", False),
            "answer_boundary_target_label": row_timing.get("answer_boundary_target_label", ""),
            "answer_boundary_target_sha256": row_timing.get("answer_boundary_target_sha256", ""),
            "prompt_group_id": scenario.get("prompt_group_id", derive_prompt_group_id(scenario_id)),
            "payload_class": scenario.get("payload_class", ""),
            "domain": domain,
            "encoding": scenario.get("encoding", ""),
            "prompt_injection_status": scenario.get("prompt_injection_status", ""),
            "support_status": support_status or "",
            "topic": topic,
            "evidence_source": scenario.get("evidence_source", ""),
            "retrieval_condition": scenario.get("retrieval_condition", ""),
            "retrieval_score_bucket": scenario.get("retrieval_score_bucket", ""),
            "challenge_mode": scenario.get("challenge_mode", ""),
            "cjt_role": scenario.get("cjt_role", ""),
            "cjt_family": scenario.get("cjt_family", ""),
            "cjt_pair_role": scenario.get("cjt_pair_role", ""),
            "trusted_authority": scenario.get("trusted_authority", ""),
            "pcba_expected_signal": scenario.get("pcba_expected_signal", ""),
            "qa_pair_id": scenario.get("qa_pair_id") or scenario.get("factual_pair_id", ""),
            "factual_pair_id": scenario.get("factual_pair_id") or scenario.get("qa_pair_id", ""),
            "evidence_doc_id": scenario.get("evidence_doc_id") or scenario.get("evidence_id", ""),
            "evidence_text": scenario.get("evidence_text", ""),
            "gold_answer": scenario.get("gold_answer", ""),
            "candidate_answer": scenario.get("candidate_answer", ""),
            "expected_answer_kind": scenario.get("expected_answer_kind", ""),
            "generation_trace_id": scenario.get("generation_trace_id", ""),
            "model_output_sha256": scenario.get("model_output_sha256", ""),
            "judged_answer_sha256": scenario.get("judged_answer_sha256", ""),
            "judge_name": scenario.get("judge_name", ""),
            "prompt": scenario["prompt"],
            "model_prompt_format": prompt_format,
            "expected_behavior": scenario.get("expected_behavior", ""),
            "target_enabled_predicate": scenario.get("target_enabled_predicate", ""),
            "target_operator": scenario.get("target_operator", ""),
            "label": str(label),
            "label_source": label_source,
            "prompt_token_count": token_count,
            "generated_prefix_text": generated_prefix_text,
            "generated_prefix_token_count": generated_prefix_token_count,
        }
        rows.append(row)
        print(
            f"[w0-all-layers] {index}/{len(scenarios)} {scenario_id} "
            f"timing={row_timing['timing_point']} index={row_timing['timing_index']} "
            f"label={label} layers={len(layer_indices)} "
            f"prompt_tokens={token_count} generated_prefix_tokens={generated_prefix_token_count}",
            flush=True,
        )

    if resolved_layers is None:
        raise RuntimeError("No rows captured.")
    write_npz(
        rows=rows,
        features=np.stack(features, axis=0).astype(np.float32),
        layers=np.asarray(resolved_layers, dtype=np.int64),
        path=dataset_path,
    )
    rows_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    summary = build_summary(
        rows=rows,
        model_id=model_id,
        model_revision=model_revision,
        model_info=model_info,
        prompt_bank_path=prompt_bank_path,
        label_paths=label_paths,
        prompt_format=prompt_format,
        dataset_path=dataset_path,
        metadata_path=metadata_path,
        rows_path=rows_path,
        layers=resolved_layers,
        max_length=max_length,
        timing_point=timing_mode["label"],
        timing_index=timing_mode["index"],
        temperature=temperature,
        top_p=top_p,
    )
    metadata_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[w0-all-layers] wrote {dataset_path}")
    print(f"[w0-all-layers] wrote {rows_path}")
    print(f"[w0-all-layers] wrote {metadata_path}")
    return summary


def capture_timing_layers(
    *,
    model: Any,
    tokenizer: Any,
    prompt: str,
    max_length: int,
    layers_arg: str,
    timing_index: int = 0,
    seed: int = 0,
    temperature: float = 0.0,
    top_p: float = 0.95,
    forced_token_ids: list[int] | None = None,
) -> tuple[np.ndarray, list[int], int, str, int]:
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)
    token_count = int(inputs["input_ids"].shape[-1])
    device = first_real_parameter_device(model)
    if device is not None:
        inputs = {key: value.to(device) for key, value in inputs.items()}

    return capture_layers_at_timing_index(
        model=model,
        tokenizer=tokenizer,
        inputs=inputs,
        layers_arg=layers_arg,
        token_count=token_count,
        timing_index=timing_index,
        seed=seed,
        temperature=temperature,
        top_p=top_p,
        forced_token_ids=forced_token_ids,
    )


def capture_layers_at_timing_index(
    *,
    model: Any,
    tokenizer: Any,
    inputs: dict[str, Any],
    layers_arg: str,
    token_count: int,
    timing_index: int,
    seed: int = 0,
    temperature: float = 0.0,
    top_p: float = 0.95,
    forced_token_ids: list[int] | None = None,
) -> tuple[np.ndarray, list[int], int, str, int]:
    if timing_index < 0:
        raise RuntimeError("timing_index must be non-negative.")
    input_ids = inputs["input_ids"]
    attention_mask = inputs.get("attention_mask")
    generated_token_ids: list[int] = []
    if timing_index > 0:
        import torch

        if forced_token_ids is not None:
            if len(forced_token_ids) < timing_index:
                raise RuntimeError(
                    f"Forced continuation has {len(forced_token_ids)} tokens; cannot capture W{timing_index}."
                )
            generated_token_ids = [int(token_id) for token_id in forced_token_ids[:timing_index]]
            generated = torch.tensor([generated_token_ids], dtype=input_ids.dtype, device=input_ids.device)
            input_ids = torch.cat([input_ids, generated], dim=-1)
        else:
            torch.manual_seed(int(seed))
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(int(seed))
            generation_kwargs: dict[str, Any] = {
                "max_new_tokens": int(timing_index),
                "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
                "eos_token_id": tokenizer.eos_token_id,
                "use_cache": True,
            }
            if temperature > 0:
                generation_kwargs.update({"do_sample": True, "temperature": float(temperature), "top_p": float(top_p)})
            else:
                generation_kwargs.update({"do_sample": False})
            generation_inputs = {"input_ids": input_ids}
            if attention_mask is not None:
                generation_inputs["attention_mask"] = attention_mask
            with inference_context():
                output_ids = model.generate(**generation_inputs, **generation_kwargs)
            generated = output_ids[:, token_count:]
            generated_token_ids = [int(token_id) for token_id in generated[0].detach().cpu().tolist()]
            input_ids = output_ids
        if attention_mask is not None:
            added_mask = torch.ones(
                (attention_mask.shape[0], generated.shape[-1]),
                dtype=attention_mask.dtype,
                device=attention_mask.device,
            )
            attention_mask = torch.cat([attention_mask, added_mask], dim=-1)

    final_inputs = {"input_ids": input_ids}
    if attention_mask is not None:
        final_inputs["attention_mask"] = attention_mask
    with inference_context():
        output = model(**final_inputs, use_cache=False, output_hidden_states=True, return_dict=True)
    hidden_states = getattr(output, "hidden_states", None)
    if hidden_states is None:
        raise RuntimeError("Model did not return hidden_states; cannot capture timing layers.")
    layer_indices = parse_layers_arg(layers_arg, hidden_state_count=len(hidden_states))
    vectors = np.stack(
        [
            hidden_states[layer][0, -1].detach().float().cpu().numpy().astype(np.float32)
            for layer in layer_indices
        ],
        axis=0,
    )
    generated_prefix_text = ""
    if generated_token_ids:
        generated_prefix_text = tokenizer.decode(generated_token_ids, skip_special_tokens=False)
    return vectors, layer_indices, token_count, generated_prefix_text, len(generated_token_ids)


def capture_prompt_final_layers(
    *,
    model: Any,
    tokenizer: Any,
    prompt: str,
    max_length: int,
    layers_arg: str,
) -> tuple[np.ndarray, list[int], int]:
    vectors, layer_indices, token_count, _, _ = capture_timing_layers(
        model=model,
        tokenizer=tokenizer,
        prompt=prompt,
        max_length=max_length,
        layers_arg=layers_arg,
    )
    return vectors, layer_indices, token_count


def parse_timing_point(value: Any) -> tuple[str, int]:
    text = str(value or "W0").strip().upper()
    if not text.startswith("W") or not text[1:].isdigit():
        raise RuntimeError(f"Timing point must look like W0, W1, or W8; got {value!r}.")
    index = int(text[1:])
    if index < 0:
        raise RuntimeError(f"Timing point must be non-negative; got {value!r}.")
    return f"W{index}", index


def parse_timing_mode(value: Any) -> dict[str, Any]:
    text = str(value or "W0").strip().upper().replace("-", "_")
    if text in {"PREANSWER", "PRE_ANSWER", "BEFORE_ANSWER", "PRE_ANSWER_TOKEN"}:
        return {
            "mode": "pre_answer",
            "label": "PRE_ANSWER",
            "index": -1,
        }
    label, index = parse_timing_point(text)
    return {
        "mode": "fixed",
        "label": label,
        "index": index,
    }


def resolve_scenario_timing(
    *,
    tokenizer: Any,
    scenario: dict[str, Any],
    timing_mode: dict[str, Any],
    support_status: str | None,
) -> dict[str, Any]:
    if timing_mode["mode"] != "pre_answer":
        return {
            "timing_mode": "fixed",
            "timing_point": timing_mode["label"],
            "timing_index": int(timing_mode["index"]),
            "answer_boundary_token_index": -1,
            "answer_boundary_found": False,
            "answer_boundary_target_label": "",
            "answer_boundary_target_sha256": "",
        }
    token_ids = parse_token_id_list(scenario.get("continuation_token_ids"))
    if not token_ids:
        raise RuntimeError("PRE_ANSWER timing requires scenario continuation_token_ids.")
    target_label, target_answer = answer_target_for_pre_answer(
        scenario=scenario,
        support_status=support_status,
    )
    if not target_answer:
        raise RuntimeError("PRE_ANSWER timing requires gold/counterfactual answer metadata.")
    boundary_index = first_answer_token_boundary(
        tokenizer=tokenizer,
        token_ids=token_ids,
        target_answer=target_answer,
    )
    timing_index = max(0, boundary_index - 1)
    return {
        "timing_mode": "pre_answer",
        "timing_point": "PRE_ANSWER",
        "timing_index": int(timing_index),
        "answer_boundary_token_index": int(boundary_index),
        "answer_boundary_found": True,
        "answer_boundary_target_label": target_label,
        "answer_boundary_target_sha256": sha256_text(str(target_answer)),
    }


def answer_target_for_pre_answer(*, scenario: dict[str, Any], support_status: str | None) -> tuple[str, str]:
    label = normalise_support_status(support_status)
    if label == "UNSUPPORTED":
        return "UNSUPPORTED", str(scenario.get("counterfactual_unsupported_answer") or "")
    if label == "SUPPORTED":
        return "SUPPORTED", str(scenario.get("gold_answer") or "")
    return "", ""


def first_answer_token_boundary(*, tokenizer: Any, token_ids: list[int], target_answer: str) -> int:
    target_norm = normalize_answer_for_match(target_answer)
    if not target_norm:
        raise RuntimeError("PRE_ANSWER target answer normalizes to empty string.")
    for index in range(1, len(token_ids) + 1):
        prefix_text = tokenizer.decode(token_ids[:index], skip_special_tokens=True)
        if target_norm in normalize_answer_for_match(prefix_text):
            return index
    raise RuntimeError(
        "Could not locate answer value in continuation_token_ids for PRE_ANSWER timing."
    )


def normalize_answer_for_match(value: Any) -> str:
    text = str(value or "").lower()
    text = text.replace("$", " ")
    text = re.sub(r"[^a-z0-9.\-]+", " ", text)
    return " ".join(text.split())


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def parse_layers_arg(layers_arg: str, *, hidden_state_count: int) -> list[int]:
    value = str(layers_arg or "all").strip().lower()
    if value == "all":
        return list(range(hidden_state_count))
    layers = [int(part.strip()) for part in value.split(",") if part.strip()]
    bad = [layer for layer in layers if layer < 0 or layer >= hidden_state_count]
    if bad:
        raise RuntimeError(f"Requested layers {bad} outside hidden_states range 0..{hidden_state_count - 1}.")
    if not layers:
        raise RuntimeError("No layers requested.")
    return layers


def load_label_map(paths: tuple[Path, ...]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for path in paths:
        if not path:
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                label = str(row.get("label") or "").strip()
                if not label:
                    continue
                for key_name in ("scenario_id", "prompt_id", "trace_id"):
                    key = str(row.get(key_name) or "").strip()
                    if key:
                        labels[key] = label
    return labels


def write_npz(*, rows: list[dict[str, Any]], features: np.ndarray, layers: np.ndarray, path: Path) -> None:
    np.savez_compressed(
        path,
        features=features,
        layers=layers,
        prompts=np.asarray([row["prompt"] for row in rows], dtype=object),
        scenario_ids=np.asarray([row["scenario_id"] for row in rows], dtype=object),
        prompt_group_ids=np.asarray([row.get("prompt_group_id", row["scenario_id"]) for row in rows], dtype=object),
        trace_ids=np.asarray([row["trace_id"] for row in rows], dtype=object),
        timing_points=np.asarray([row.get("timing_point", "W0") for row in rows], dtype=object),
        timing_indices=np.asarray([row.get("timing_index", 0) for row in rows], dtype=np.int64),
        timing_modes=np.asarray([row.get("timing_mode", "fixed") for row in rows], dtype=object),
        answer_boundary_token_indices=np.asarray(
            [row.get("answer_boundary_token_index", -1) for row in rows],
            dtype=np.int64,
        ),
        answer_boundary_founds=np.asarray(
            [bool(row.get("answer_boundary_found", False)) for row in rows],
            dtype=bool,
        ),
        answer_boundary_target_labels=np.asarray(
            [row.get("answer_boundary_target_label", "") for row in rows],
            dtype=object,
        ),
        answer_boundary_target_sha256s=np.asarray(
            [row.get("answer_boundary_target_sha256", "") for row in rows],
            dtype=object,
        ),
        axis_names=np.asarray(
            [
                "behavior",
                "expected_behavior",
                "payload_class",
                "domain",
                "encoding",
                "prompt_injection_status",
                "support_status",
                "topic",
                "evidence_source",
                "retrieval_condition",
                "retrieval_score_bucket",
                "challenge_mode",
                "cjt_role",
                "cjt_family",
                "cjt_pair_role",
                "trusted_authority",
                "pcba_expected_signal",
                "target_operator",
            ],
            dtype=object,
        ),
        labels_behavior=np.asarray([row["label"] for row in rows], dtype=object),
        labels_expected_behavior=np.asarray([row["expected_behavior"] for row in rows], dtype=object),
        labels_payload_class=np.asarray([row["payload_class"] for row in rows], dtype=object),
        labels_domain=np.asarray([row["domain"] for row in rows], dtype=object),
        labels_encoding=np.asarray([row.get("encoding", "") for row in rows], dtype=object),
        labels_prompt_injection_status=np.asarray(
            [row.get("prompt_injection_status", "") for row in rows],
            dtype=object,
        ),
        labels_support_status=np.asarray([row.get("support_status", "") for row in rows], dtype=object),
        labels_topic=np.asarray([row.get("topic", row.get("payload_class", "")) for row in rows], dtype=object),
        labels_evidence_source=np.asarray([row.get("evidence_source", "") for row in rows], dtype=object),
        labels_retrieval_condition=np.asarray([row.get("retrieval_condition", "") for row in rows], dtype=object),
        labels_retrieval_score_bucket=np.asarray(
            [row.get("retrieval_score_bucket", "") for row in rows],
            dtype=object,
        ),
        labels_challenge_mode=np.asarray([row.get("challenge_mode", "") for row in rows], dtype=object),
        labels_cjt_role=np.asarray([row.get("cjt_role", "") for row in rows], dtype=object),
        labels_cjt_family=np.asarray([row.get("cjt_family", "") for row in rows], dtype=object),
        labels_cjt_pair_role=np.asarray([row.get("cjt_pair_role", "") for row in rows], dtype=object),
        labels_trusted_authority=np.asarray([row.get("trusted_authority", "") for row in rows], dtype=object),
        labels_pcba_expected_signal=np.asarray(
            [row.get("pcba_expected_signal", "") for row in rows],
            dtype=object,
        ),
        labels_target_operator=np.asarray([row["target_operator"] for row in rows], dtype=object),
        labels_target_enabled_predicate=np.asarray(
            [row["target_enabled_predicate"] for row in rows],
            dtype=object,
        ),
        qa_pair_ids=np.asarray([row.get("qa_pair_id", "") for row in rows], dtype=object),
        factual_pair_ids=np.asarray([row.get("factual_pair_id", "") for row in rows], dtype=object),
        evidence_doc_ids=np.asarray([row.get("evidence_doc_id", "") for row in rows], dtype=object),
        evidence_texts=np.asarray([row.get("evidence_text", "") for row in rows], dtype=object),
        gold_answers=np.asarray([row.get("gold_answer", "") for row in rows], dtype=object),
        candidate_answers=np.asarray([row.get("candidate_answer", "") for row in rows], dtype=object),
        expected_answer_kinds=np.asarray([row.get("expected_answer_kind", "") for row in rows], dtype=object),
        generation_trace_ids=np.asarray([row.get("generation_trace_id", "") for row in rows], dtype=object),
        model_output_sha256s=np.asarray([row.get("model_output_sha256", "") for row in rows], dtype=object),
        judged_answer_sha256s=np.asarray([row.get("judged_answer_sha256", "") for row in rows], dtype=object),
        judge_names=np.asarray([row.get("judge_name", "") for row in rows], dtype=object),
        label_sources=np.asarray([row["label_source"] for row in rows], dtype=object),
        prompt_token_counts=np.asarray([row["prompt_token_count"] for row in rows], dtype=np.int64),
        generated_prefix_texts=np.asarray([row.get("generated_prefix_text", "") for row in rows], dtype=object),
        generated_prefix_token_counts=np.asarray(
            [row.get("generated_prefix_token_count", 0) for row in rows],
            dtype=np.int64,
        ),
    )


def build_summary(
    *,
    rows: list[dict[str, Any]],
    model_id: str,
    model_revision: str | None,
    model_info: dict[str, Any],
    prompt_bank_path: Path,
    label_paths: tuple[Path, ...],
    prompt_format: str,
    dataset_path: Path,
    metadata_path: Path,
    rows_path: Path,
    layers: list[int],
    max_length: int,
    timing_point: str = "W0",
    timing_index: int = 0,
    temperature: float = 0.0,
    top_p: float = 0.95,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "model_id": model_id,
        "model_revision": model_revision,
        "model_info": model_info,
        "prompt_bank": str(prompt_bank_path),
        "label_paths": [str(path) for path in label_paths],
        "prompt_format": prompt_format,
        "max_length": int(max_length),
        "timing_point": timing_point,
        "timing_index": int(timing_index),
        "timing_generation": {
            "temperature": float(temperature),
            "top_p": float(top_p),
            "mode": "sampled" if temperature > 0 else "greedy",
        },
        "timing_mode_distribution": dict(
            sorted(Counter(row.get("timing_mode", "fixed") for row in rows).items())
        ),
        "answer_boundary_found_distribution": dict(
            sorted(Counter(bool(row.get("answer_boundary_found", False)) for row in rows).items())
        ),
        "answer_boundary_token_index_distribution": dict(
            sorted(
                Counter(
                    int(row.get("answer_boundary_token_index", -1))
                    for row in rows
                    if int(row.get("answer_boundary_token_index", -1)) >= 0
                ).items()
            )
        ),
        "timing_index_distribution": dict(
            sorted(Counter(int(row.get("timing_index", 0)) for row in rows).items())
        ),
        "row_count": int(len(rows)),
        "layers": [int(layer) for layer in layers],
        "layer_count": int(len(layers)),
        "feature_shape": [int(len(rows)), int(len(layers)), int(model_info.get("hidden_size") or 0)],
        "behavior_distribution": dict(sorted(Counter(row["label"] for row in rows).items())),
        "expected_behavior_distribution": dict(sorted(Counter(row["expected_behavior"] for row in rows).items())),
        "payload_class_distribution": dict(sorted(Counter(row["payload_class"] for row in rows).items())),
        "support_status_distribution": dict(
            sorted(Counter(row.get("support_status", "") for row in rows if row.get("support_status", "")).items())
        ),
        "topic_distribution": dict(
            sorted(Counter(row.get("topic", "") for row in rows if row.get("topic", "")).items())
        ),
        "evidence_source_distribution": dict(
            sorted(Counter(row.get("evidence_source", "") for row in rows if row.get("evidence_source", "")).items())
        ),
        "retrieval_condition_distribution": dict(
            sorted(
                Counter(
                    row.get("retrieval_condition", "") for row in rows if row.get("retrieval_condition", "")
                ).items()
            )
        ),
        "retrieval_score_bucket_distribution": dict(
            sorted(
                Counter(
                    row.get("retrieval_score_bucket", "")
                    for row in rows
                    if row.get("retrieval_score_bucket", "")
                ).items()
            )
        ),
        "challenge_mode_distribution": dict(
            sorted(Counter(row.get("challenge_mode", "") for row in rows if row.get("challenge_mode", "")).items())
        ),
        "label_source_distribution": dict(sorted(Counter(row["label_source"] for row in rows).items())),
        "generated_prefix_token_count_distribution": dict(
            sorted(Counter(int(row.get("generated_prefix_token_count", 0)) for row in rows).items())
        ),
        "dataset": str(dataset_path),
        "rows": str(rows_path),
        "manifest": str(metadata_path),
        "claim": (
            "OPEN / NOT LICENSED for pre-speech detection."
            if timing_point == "W0"
            else "OPEN / NOT LICENSED for pre-display timing detection."
        ),
        "important_limit": (
            "This is hidden-state capture only. W0 is prompt-stage before any generated token; "
            "W1/W8 are early-generation pre-display states; PRE_ANSWER is the state immediately "
            "before the judged answer value appears in the forced continuation. All timing states "
            "must beat generated-prefix text controls before any internal detector claim is considered."
        ),
    }


def derive_prompt_group_id(scenario_id: str) -> str:
    return str(scenario_id).split("::", 1)[0]


def normalise_support_status(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    aliases = {
        "SUPPORT": "SUPPORTED",
        "GROUNDED": "SUPPORTED",
        "TRUE_SUPPORTED": "SUPPORTED",
        "UNSUPPORT": "UNSUPPORTED",
        "UNSUPPORTED_CLAIM": "UNSUPPORTED",
        "HALLUCINATED": "UNSUPPORTED",
        "HALLUCINATION": "UNSUPPORTED",
    }
    text = aliases.get(text, text)
    return text if text in {"SUPPORTED", "UNSUPPORTED"} else None


def parse_token_id_list(value: Any) -> list[int] | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise RuntimeError("continuation_token_ids string must be JSON list.") from exc
    if not isinstance(value, list):
        raise RuntimeError("continuation_token_ids must be a list of token ids.")
    return [int(token_id) for token_id in value]


if __name__ == "__main__":
    raise SystemExit(main())
