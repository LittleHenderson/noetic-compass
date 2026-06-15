"""Generate matched-prompt outputs without W0 capture.

This is the fast behavior-screening path for v6 matched-prompt campaigns. It
does not read hidden states and cannot support any internal detector claim by
itself. It only produces completed generations so a stronger judge can decide
whether the safe instruction chain stayed INTACT or BROKE before spending on
all-layer W0 capture.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_enabled_predicate_capture import (  # noqa: E402
    HEURISTIC_VERIFIER,
    classify_behavior,
    first_real_parameter_device,
    format_model_prompt,
    inference_context,
    load_model,
    load_prompt_bank,
    parse_sample_seed,
)


SCHEMA_VERSION = "cas_harness_matched_prompt_generation_only.v1"


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
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--generation-max-time", type=float, default=0.0)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--prompt-format", choices=("chat-auto", "raw"), default="chat-auto")
    parser.add_argument("--trust-remote-code", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = sample_generations(
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


def sample_generations(
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
    generations_path = output_dir / "matched_prompt_generations.jsonl"
    labels_path = output_dir / "matched_prompt_generation_heuristic_labels.jsonl"
    checkpoint_rows_path = output_dir / "matched_prompt_generation_checkpoint_rows.jsonl"
    metadata_path = output_dir / "matched_prompt_generation_manifest.json"
    generations_path.write_text("", encoding="utf-8")
    labels_path.write_text("", encoding="utf-8")
    checkpoint_rows_path.write_text("", encoding="utf-8")

    rows: list[dict[str, Any]] = []
    for index, scenario in enumerate(scenarios, 1):
        sample_seed = parse_sample_seed(str(scenario["id"]), fallback=index)
        model_prompt = format_model_prompt(
            tokenizer=tokenizer,
            prompt=str(scenario["prompt"]),
            prompt_format=prompt_format,
        )
        output_text, prompt_tokens, continuation_tokens = generate_continuation_cached(
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
        label = classify_behavior(output_text)
        row = {
            "schema_version": SCHEMA_VERSION,
            "trace_id": f"{scenario['id']}::generation_only",
            "scenario_id": scenario["id"],
            "prompt_id": scenario["id"],
            "prompt_group_id": scenario.get("prompt_group_id", derive_prompt_group_id(str(scenario["id"]))),
            "payload_class": scenario.get("payload_class", ""),
            "prompt": scenario["prompt"],
            "model_prompt_format": prompt_format,
            "model_output": output_text,
            "label": label,
            "verifier": HEURISTIC_VERIFIER,
            "model_id": model_id,
            "sample_seed": sample_seed,
            "prompt_token_count": prompt_tokens,
            "continuation_token_count": continuation_tokens,
            "claim_ceiling": (
                "Generation-only screening artifact. It does not read hidden states and cannot "
                "license internal detection, prevention, removal, reversal, or causal claims."
            ),
        }
        rows.append(row)
        append_jsonl(generations_path, [row])
        append_jsonl(labels_path, [label_row(row)])
        append_jsonl(checkpoint_rows_path, [checkpoint_row(row)])
        print(
            f"[matched-generation] {index}/{len(scenarios)} {scenario['id']} "
            f"label={label} prompt_tokens={prompt_tokens} new_tokens={continuation_tokens}",
            flush=True,
        )

    summary = build_summary(
        rows=rows,
        model_id=model_id,
        model_revision=model_revision,
        model_info=model_info,
        prompt_bank_path=prompt_bank_path,
        scenario_offset=scenario_offset,
        prompt_format=prompt_format,
        generations_path=generations_path,
        labels_path=labels_path,
        checkpoint_rows_path=checkpoint_rows_path,
    )
    metadata_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[matched-generation] wrote {generations_path}")
    print(f"[matched-generation] wrote {labels_path}")
    print(f"[matched-generation] wrote {checkpoint_rows_path}")
    print(f"[matched-generation] wrote {metadata_path}")
    return summary


def generate_continuation_cached(
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
) -> tuple[str, int, int]:
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
    )


def label_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "trace_id": row["trace_id"],
        "scenario_id": row["scenario_id"],
        "prompt_id": row["scenario_id"],
        "prompt_group_id": row["prompt_group_id"],
        "payload_class": row["payload_class"],
        "label": row["label"],
        "verifier": row["verifier"],
        "claim_ceiling": row["claim_ceiling"],
    }


def checkpoint_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "trace_id": row["trace_id"],
        "scenario_id": row["scenario_id"],
        "prompt_group_id": row["prompt_group_id"],
        "payload_class": row["payload_class"],
        "label": row["label"],
        "verifier": row["verifier"],
        "sample_seed": row["sample_seed"],
        "prompt_token_count": row["prompt_token_count"],
        "continuation_token_count": row["continuation_token_count"],
    }


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()


def build_summary(
    *,
    rows: list[dict[str, Any]],
    model_id: str,
    model_revision: str | None,
    model_info: dict[str, Any],
    prompt_bank_path: Path,
    scenario_offset: int,
    prompt_format: str,
    generations_path: Path,
    labels_path: Path,
    checkpoint_rows_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "model_id": model_id,
        "model_revision": model_revision,
        "model_info": model_info,
        "prompt_bank": str(prompt_bank_path),
        "scenario_offset": int(scenario_offset),
        "prompt_format": prompt_format,
        "row_count": int(len(rows)),
        "behavior_distribution": dict(sorted(Counter(row["label"] for row in rows).items())),
        "payload_class_distribution": dict(sorted(Counter(row["payload_class"] for row in rows).items())),
        "generations": str(generations_path),
        "heuristic_labels": str(labels_path),
        "checkpoint_rows": str(checkpoint_rows_path),
        "claim": "OPEN / NOT LICENSED for pre-speech detection.",
        "important_limit": (
            "This generation-only run does not capture or evaluate hidden states. Use it only "
            "to screen behavior labels before spending on W0 capture."
        ),
    }


def derive_prompt_group_id(scenario_id: str) -> str:
    return str(scenario_id).split("::", 1)[0]


if __name__ == "__main__":
    raise SystemExit(main())
