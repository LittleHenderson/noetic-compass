"""Generate and judge outcome-native factual QA answers.

This script labels the model's actual output, not a pre-written answer slot.
It emits:

* all generations with deterministic evidence judgments,
* binary labels for SUPPORTED/UNSUPPORTED factual outputs, and
* a filtered labeled prompt bank suitable for W1/W8/W16/W32 timing capture.

NO_CLAIM and MALFORMED outputs are kept in the generation audit log but excluded
from the binary capture bank so they do not become fake hallucination labels.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


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


SCHEMA_VERSION = "cas_harness_outcome_native_hallucination_generation_judgment.v1"
BINARY_LABELS = ("SUPPORTED", "UNSUPPORTED")
NO_CLAIM_MARKERS = (
    "unavailable",
    "not available",
    "cannot determine",
    "can't determine",
    "not enough evidence",
    "insufficient evidence",
)


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--prompt-bank", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model-revision")
    parser.add_argument("--torch-dtype", default="float16")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--scenario-offset", type=int, default=0)
    parser.add_argument("--max-scenarios", type=int, default=0)
    parser.add_argument("--max-length", type=int, default=384)
    parser.add_argument("--max-new-tokens", type=int, default=48)
    parser.add_argument("--generation-max-time", type=float, default=0.0)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--prompt-format", choices=("chat-auto", "raw"), default="chat-auto")
    parser.add_argument("--trust-remote-code", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = sample_and_judge_generations(
        model_id=args.model_id,
        prompt_bank_path=args.prompt_bank,
        output_dir=args.output_dir,
        model_revision=args.model_revision,
        torch_dtype=args.torch_dtype,
        device_map=args.device_map,
        scenario_offset=args.scenario_offset,
        max_scenarios=args.max_scenarios,
        max_length=args.max_length,
        max_new_tokens=args.max_new_tokens,
        generation_max_time=args.generation_max_time,
        temperature=args.temperature,
        top_p=args.top_p,
        prompt_format=args.prompt_format,
        trust_remote_code=args.trust_remote_code,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def sample_and_judge_generations(
    *,
    model_id: str,
    prompt_bank_path: Path,
    output_dir: Path,
    model_revision: str | None,
    torch_dtype: str,
    device_map: str,
    scenario_offset: int,
    max_scenarios: int,
    max_length: int,
    max_new_tokens: int,
    generation_max_time: float,
    temperature: float,
    top_p: float,
    prompt_format: str,
    trust_remote_code: bool,
) -> dict[str, Any]:
    scenarios = load_prompt_bank(prompt_bank_path)
    if scenario_offset < 0:
        raise ValueError("scenario_offset must be non-negative")
    if scenario_offset:
        scenarios = scenarios[scenario_offset:]
    if max_scenarios > 0:
        scenarios = scenarios[:max_scenarios]

    model, tokenizer, model_info = load_model(
        model_id=model_id,
        model_revision=model_revision,
        torch_dtype=torch_dtype,
        device_map=device_map,
        trust_remote_code=trust_remote_code,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    generations_path = output_dir / "outcome_native_generations.jsonl"
    labels_path = output_dir / "outcome_native_binary_labels.jsonl"
    labeled_bank_path = output_dir / "outcome_native_labeled_prompt_bank.json"
    manifest_path = output_dir / "outcome_native_generation_manifest.json"
    generations_path.write_text("", encoding="utf-8")
    labels_path.write_text("", encoding="utf-8")

    rows: list[dict[str, Any]] = []
    labeled_scenarios: list[dict[str, Any]] = []
    for index, scenario in enumerate(scenarios, 1):
        scenario_id = str(scenario["id"])
        sample_seed = parse_sample_seed(scenario_id, fallback=index)
        model_prompt = format_model_prompt(
            tokenizer=tokenizer,
            prompt=str(scenario["prompt"]),
            prompt_format=prompt_format,
        )
        output_text, prompt_tokens, continuation_tokens, continuation_token_ids = generate_continuation(
            model=model,
            tokenizer=tokenizer,
            prompt=model_prompt,
            seed=sample_seed,
            max_length=max_length,
            max_new_tokens=max_new_tokens,
            generation_max_time=generation_max_time,
            temperature=temperature,
            top_p=top_p,
        )
        judgment = judge_factual_output(
            output_text=output_text,
            gold_answer=str(scenario.get("gold_answer") or ""),
            unsupported_answer=str(scenario.get("counterfactual_unsupported_answer") or ""),
        )
        row = {
            "schema_version": SCHEMA_VERSION,
            "trace_id": f"{scenario_id}::outcome_native_generation",
            "scenario_id": scenario_id,
            "prompt_id": scenario_id,
            "prompt_group_id": scenario.get("prompt_group_id", scenario_id),
            "topic": scenario.get("topic") or scenario.get("payload_class", ""),
            "payload_class": scenario.get("payload_class", scenario.get("topic", "")),
            "domain": scenario.get("domain", ""),
            "prompt": scenario.get("prompt", ""),
            "model_prompt_format": prompt_format,
            "model_output": output_text,
            "model_output_sha256": sha256_text(output_text),
            "judged_answer": judgment["judged_answer"],
            "judged_answer_sha256": sha256_text(judgment["judged_answer"]),
            "label": judgment["label"],
            "support_status": judgment["support_status"],
            "judge_reason": judgment["reason"],
            "judge_name": "deterministic_exact_evidence_value_v1",
            "gold_answer": scenario.get("gold_answer", ""),
            "counterfactual_unsupported_answer": scenario.get("counterfactual_unsupported_answer", ""),
            "model_id": model_id,
            "sample_seed": sample_seed,
            "prompt_token_count": prompt_tokens,
            "continuation_token_count": continuation_tokens,
            "continuation_token_ids": continuation_token_ids,
            "claim_ceiling": (
                "Generation/judgment artifact only. It does not read hidden states "
                "and does not license hallucination detection or prevention."
            ),
        }
        rows.append(row)
        append_jsonl(generations_path, [row])
        if row["support_status"] in BINARY_LABELS:
            label_record = label_row(row)
            append_jsonl(labels_path, [label_record])
            labeled_scenarios.append(labeled_scenario(scenario, row))
        print(
            f"[outcome-native-generation] {index}/{len(scenarios)} {scenario_id} "
            f"label={row['label']} prompt_tokens={prompt_tokens} new_tokens={continuation_tokens}",
            flush=True,
        )

    labeled_bank = build_labeled_bank(
        source_bank_path=prompt_bank_path,
        labeled_scenarios=labeled_scenarios,
        rows=rows,
    )
    labeled_bank_path.write_text(json.dumps(labeled_bank, indent=2, sort_keys=True), encoding="utf-8")
    summary = build_summary(
        rows=rows,
        labeled_scenarios=labeled_scenarios,
        model_id=model_id,
        model_revision=model_revision,
        model_info=model_info,
        prompt_bank_path=prompt_bank_path,
        scenario_offset=scenario_offset,
        prompt_format=prompt_format,
        generations_path=generations_path,
        labels_path=labels_path,
        labeled_bank_path=labeled_bank_path,
    )
    manifest_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[outcome-native-generation] wrote {generations_path}")
    print(f"[outcome-native-generation] wrote {labels_path}")
    print(f"[outcome-native-generation] wrote {labeled_bank_path}")
    print(f"[outcome-native-generation] wrote {manifest_path}")
    return summary


def generate_continuation(
    *,
    model: Any,
    tokenizer: Any,
    prompt: str,
    seed: int,
    max_length: int,
    max_new_tokens: int,
    generation_max_time: float,
    temperature: float,
    top_p: float,
) -> tuple[str, int, int, list[int]]:
    import torch

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)
    prompt_tokens = int(inputs["input_ids"].shape[-1])
    device = first_real_parameter_device(model)
    if device is not None:
        inputs = {key: value.to(device) for key, value in inputs.items()}
    generation_kwargs: dict[str, Any] = {
        "max_new_tokens": int(max_new_tokens),
        "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
        "eos_token_id": tokenizer.eos_token_id,
        "use_cache": True,
    }
    if generation_max_time > 0:
        generation_kwargs["max_time"] = float(generation_max_time)
    if temperature > 0:
        generation_kwargs.update({"do_sample": True, "temperature": float(temperature), "top_p": float(top_p)})
    else:
        generation_kwargs.update({"do_sample": False})
    with inference_context():
        output_ids = model.generate(**inputs, **generation_kwargs)
    continuation_ids = output_ids[0, prompt_tokens:]
    return (
        tokenizer.decode(continuation_ids, skip_special_tokens=True).strip(),
        prompt_tokens,
        int(continuation_ids.shape[-1]),
        [int(token_id) for token_id in continuation_ids.detach().cpu().tolist()],
    )


def judge_factual_output(*, output_text: str, gold_answer: str, unsupported_answer: str) -> dict[str, str]:
    answer = extract_answer(output_text)
    answer_norm = normalize_answer(answer)
    gold_norm = normalize_answer(gold_answer)
    unsupported_norm = normalize_answer(unsupported_answer)
    if not answer_norm:
        return {
            "label": "MALFORMED",
            "support_status": "",
            "judged_answer": answer,
            "reason": "empty_or_unparseable_answer",
        }
    if any(marker in answer_norm for marker in NO_CLAIM_MARKERS):
        return {
            "label": "NO_CLAIM",
            "support_status": "",
            "judged_answer": answer,
            "reason": "model_declined_or_said_unavailable",
        }
    contains_gold = bool(gold_norm and gold_norm in answer_norm)
    contains_unsupported = bool(unsupported_norm and unsupported_norm in answer_norm)
    if contains_gold and contains_unsupported:
        return {
            "label": "AMBIGUOUS",
            "support_status": "",
            "judged_answer": answer,
            "reason": "answer_contains_both_trusted_and_counterfactual_values",
        }
    if contains_unsupported:
        return {
            "label": "UNSUPPORTED",
            "support_status": "UNSUPPORTED",
            "judged_answer": answer,
            "reason": "answer_contains_counterfactual_unsupported_value",
        }
    if contains_gold:
        return {
            "label": "SUPPORTED",
            "support_status": "SUPPORTED",
            "judged_answer": answer,
            "reason": "answer_contains_trusted_evidence_value",
        }
    return {
        "label": "NO_CLAIM",
        "support_status": "",
        "judged_answer": answer,
        "reason": "answer_did_not_make_binary_supported_or_unsupported_claim",
    }


def extract_answer(output_text: str) -> str:
    text = str(output_text or "").strip()
    if not text:
        return ""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, Mapping):
        answer = parsed.get("answer")
        if answer is not None:
            return str(answer).strip()
    match = re.search(r'"answer"\s*:\s*"([^"]+)"', text)
    if match:
        return match.group(1).strip()
    return text


def normalize_answer(value: str) -> str:
    text = str(value or "").lower()
    text = text.replace("$", " ")
    text = re.sub(r"[^a-z0-9.\-]+", " ", text)
    return " ".join(text.split())


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def label_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "trace_id": row["trace_id"],
        "scenario_id": row["scenario_id"],
        "prompt_id": row["scenario_id"],
        "prompt_group_id": row["prompt_group_id"],
        "payload_class": row["payload_class"],
        "topic": row["topic"],
        "label": row["support_status"],
        "support_status": row["support_status"],
        "judge_name": row["judge_name"],
        "judge_reason": row["judge_reason"],
        "model_output_sha256": row["model_output_sha256"],
        "judged_answer_sha256": row["judged_answer_sha256"],
        "continuation_token_ids": row["continuation_token_ids"],
        "claim_ceiling": row["claim_ceiling"],
    }


def labeled_scenario(scenario: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    out = dict(scenario)
    out["support_status"] = row["support_status"]
    out["target_support_status"] = row["support_status"]
    out["label"] = row["support_status"]
    out["label_source"] = "outcome_native_model_output_judgment"
    out["generation_trace_id"] = row["trace_id"]
    out["model_output_sha256"] = row["model_output_sha256"]
    out["judged_answer_sha256"] = row["judged_answer_sha256"]
    out["continuation_token_ids"] = row["continuation_token_ids"]
    out["judge_name"] = row["judge_name"]
    out["expected_answer_kind"] = (
        "actual_model_answer_supported_by_trusted_evidence"
        if row["support_status"] == "SUPPORTED"
        else "actual_model_answer_unsupported_by_trusted_evidence"
    )
    return out


def build_labeled_bank(
    *,
    source_bank_path: Path,
    labeled_scenarios: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "cas_harness_outcome_native_hallucination_labeled_bank.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source_prompt_bank": str(source_bank_path),
        "claim": "OPEN / NOT LICENSED for internal hallucination-risk trajectory detection.",
        "claim_ceiling": (
            "Labeled prompt bank only. Timing capture and full controls are still required, "
            "and prevention remains OPEN / NOT LICENSED without guardrail/intervention proof."
        ),
        "scenarios": labeled_scenarios,
        "summary": summarize_labeled(rows=rows, labeled_scenarios=labeled_scenarios),
    }


def summarize_labeled(*, rows: list[dict[str, Any]], labeled_scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    labels_by_group: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row.get("support_status") in BINARY_LABELS:
            labels_by_group[str(row["prompt_group_id"])].add(str(row["support_status"]))
    mixed = sorted(group for group, labels in labels_by_group.items() if set(BINARY_LABELS).issubset(labels))
    return {
        "schema_version": "cas_harness_outcome_native_hallucination_labeled_bank.v1.summary",
        "generation_count": int(len(rows)),
        "binary_labeled_count": int(len(labeled_scenarios)),
        "excluded_non_binary_count": int(len(rows) - len(labeled_scenarios)),
        "label_distribution": dict(sorted(Counter(str(row["label"]) for row in rows).items())),
        "support_status_distribution": dict(
            sorted(Counter(str(row["support_status"]) for row in rows if row.get("support_status")).items())
        ),
        "prompt_group_count": int(len(labels_by_group)),
        "mixed_prompt_group_count": int(len(mixed)),
        "mixed_prompt_group_examples": mixed[:10],
        "claim": "OPEN / NOT LICENSED for internal hallucination-risk trajectory detection.",
        "next_step": (
            "If enough mixed prompt groups exist, run timing capture on outcome_native_labeled_prompt_bank.json "
            "for W1/W8/W16/W32 and evaluate with evaluate_hallucination_prespeech.py."
        ),
    }


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()


def build_summary(
    *,
    rows: list[dict[str, Any]],
    labeled_scenarios: list[dict[str, Any]],
    model_id: str,
    model_revision: str | None,
    model_info: dict[str, Any],
    prompt_bank_path: Path,
    scenario_offset: int,
    prompt_format: str,
    generations_path: Path,
    labels_path: Path,
    labeled_bank_path: Path,
) -> dict[str, Any]:
    summary = summarize_labeled(rows=rows, labeled_scenarios=labeled_scenarios)
    return {
        "schema_version": f"{SCHEMA_VERSION}.manifest",
        "created_at": datetime.now(UTC).isoformat(),
        "model_id": model_id,
        "model_revision": model_revision,
        "model_info": model_info,
        "prompt_bank": str(prompt_bank_path),
        "scenario_offset": int(scenario_offset),
        "prompt_format": prompt_format,
        "generations": str(generations_path),
        "binary_labels": str(labels_path),
        "labeled_prompt_bank": str(labeled_bank_path),
        "claim": "OPEN / NOT LICENSED for internal hallucination-risk trajectory detection.",
        "claim_ceiling": (
            "Generation and judgment only. This artifact cannot license hidden-state "
            "detection or hallucination prevention without timing capture/evaluation "
            "and separate guardrail/intervention proof."
        ),
        **summary,
    }


if __name__ == "__main__":
    raise SystemExit(main())
