"""Operational helpers for validation study runs and archived study artifacts."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.llm_connectors.registry import get_connector
from api.models import DialConfigSchema
from api.pipeline.runner import WrapPipelineRunner


def validation_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "validation"


def studies_dir() -> Path:
    path = validation_dir() / "studies"
    path.mkdir(parents=True, exist_ok=True)
    return path


def scenarios_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "scenarios"


def default_prompts_path() -> Path:
    return scenarios_dir() / "sample_prompts.json"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "study"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_prompt_texts(prompts_path: Path, *, count: int | None = None) -> list[str]:
    """Load prompts from a supported validation/scenario file format."""
    payload = _load_json(prompts_path)
    prompts: list[str] = []

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, str):
                prompts.append(item)
            elif isinstance(item, dict):
                text = item.get("prompt") or item.get("prompt_text")
                if isinstance(text, str) and text.strip():
                    prompts.append(text.strip())
    elif isinstance(payload, dict):
        if isinstance(payload.get("scenarios"), list):
            for item in payload["scenarios"]:
                if not isinstance(item, dict):
                    continue
                text = item.get("prompt_text") or item.get("prompt")
                if isinstance(text, str) and text.strip():
                    prompts.append(text.strip())
        elif isinstance(payload.get("prompts"), list):
            for item in payload["prompts"]:
                if isinstance(item, str):
                    prompts.append(item.strip())
                elif isinstance(item, dict):
                    text = item.get("prompt") or item.get("prompt_text")
                    if isinstance(text, str) and text.strip():
                        prompts.append(text.strip())

    prompts = [prompt for prompt in prompts if prompt]
    if count is not None:
        prompts = prompts[: max(0, count)]
    return prompts


def available_prompt_collections() -> list[dict[str, str]]:
    """Return prompt collection metadata for admin workflows."""
    collections: list[dict[str, str]] = [
        {
            "id": "sample_prompts",
            "label": "Sample Prompts",
            "path": str(default_prompts_path().relative_to(Path(__file__).resolve().parent.parent.parent)),
            "kind": "sample",
        },
        {
            "id": "augmented_library",
            "label": "Augmented Library",
            "path": str((scenarios_dir() / "augmented_library.json").relative_to(Path(__file__).resolve().parent.parent.parent)),
            "kind": "augmented",
        },
    ]

    catalog_dir = scenarios_dir() / "catalog"
    for path in sorted(catalog_dir.glob("*.json")):
        payload = _load_json(path)
        metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
        label = str(metadata.get("name") or path.stem.replace("_", " ").title())
        collections.append(
            {
                "id": path.stem,
                "label": label,
                "path": str(path.relative_to(Path(__file__).resolve().parent.parent.parent)),
                "kind": "catalog",
            }
        )
    return collections


def resolve_prompt_collection(identifier: str | None) -> Path:
    if not identifier:
        return default_prompts_path()

    project_root = Path(__file__).resolve().parent.parent.parent
    candidate = project_root / identifier
    if candidate.exists():
        return candidate

    if identifier == "sample_prompts":
        return default_prompts_path()
    if identifier == "augmented_library":
        return scenarios_dir() / "augmented_library.json"

    catalog_candidate = scenarios_dir() / "catalog" / f"{identifier}.json"
    if catalog_candidate.exists():
        return catalog_candidate

    raise FileNotFoundError(f"prompt collection not found: {identifier}")


async def run_study(
    *,
    provider: str,
    count: int,
    prompts_path: Path,
    dials: list[int] | None = None,
    model: str | None = None,
    scoring_mode: str = "heuristic_fallback",
    scoring_provider: str | None = None,
    scoring_model: str | None = None,
    study_label: str | None = None,
) -> dict:
    prompts = load_prompt_texts(prompts_path, count=count)
    dial_values = dials or [6] * 10
    started = datetime.now(timezone.utc)
    monotonic_start = asyncio.get_running_loop().time()
    results: list[dict[str, Any]] = []
    successes = 0
    failures = 0

    try:
        connector = get_connector(provider, model=model)
    except Exception as exc:
        for index, prompt in enumerate(prompts):
            results.append({"index": index, "prompt": prompt, "error": str(exc)})
        elapsed_seconds = round(asyncio.get_running_loop().time() - monotonic_start, 2)
        return {
            "summary": {
                "study_date": started.isoformat(),
                "provider": provider,
                "model": model,
                "study_label": study_label or prompts_path.stem,
                "prompt_source": str(prompts_path.relative_to(Path(__file__).resolve().parent.parent.parent)),
                "prompt_count": len(prompts),
                "successes": 0,
                "failures": len(prompts),
                "status": "failed",
                "elapsed_seconds": elapsed_seconds,
                "dial_config": dial_values,
                "scoring_mode": scoring_mode,
                "scoring_provider": scoring_provider,
                "scoring_model": scoring_model,
                "error": str(exc),
            },
            "results": results,
        }

    runner = WrapPipelineRunner(connector=connector, dial_config=DialConfigSchema(values=dial_values))

    for index, prompt in enumerate(prompts):
        try:
            result = await runner.run(
                prompt,
                scoring_mode=scoring_mode,
                scoring_provider=scoring_provider,
                scoring_model=scoring_model,
            )
            data = result.model_dump(mode="json")
            op_stage = next((s for s in data["stages"] if s["stage"] == "operator_scoring"), None)
            dc_stage = next((s for s in data["stages"] if s["stage"] == "domain_coherence"), None)
            rpm_stage = next((s for s in data["stages"] if s["stage"] == "rpm_gate"), None)
            results.append(
                {
                    "index": index,
                    "prompt": prompt,
                    "composite": data["nccs"]["composite"],
                    "certification": data["nccs"]["certification"],
                    "operator_profile": data["nccs"]["operator_profile"],
                    "domain_coherence": data["nccs"]["domain_coherence"],
                    "drive_rpm_integrity": data["nccs"]["drive_rpm_integrity"],
                    "pathway_quality": data["nccs"]["pathway_quality"],
                    "inversion_resistance": data["nccs"]["inversion_resistance"],
                    "social_engineering": data["nccs"].get("social_engineering"),
                    "bias_flags": data["nccs"].get("bias_flags"),
                    "operator_scores": op_stage["data"]["scores"] if op_stage and op_stage.get("data") else [],
                    "domain_averages": dc_stage["data"]["domain_averages"] if dc_stage and dc_stage.get("data") else [],
                    "drive_scores": rpm_stage["data"]["drive_scores"] if rpm_stage and rpm_stage.get("data") else [],
                    "llm_response": data.get("llm_response"),
                    "provenance": data.get("provenance", {}),
                }
            )
            successes += 1
        except Exception as exc:
            failures += 1
            results.append(
                {
                    "index": index,
                    "prompt": prompt,
                    "error": str(exc),
                }
            )

    elapsed_seconds = round(asyncio.get_running_loop().time() - monotonic_start, 2)
    composites = [float(item["composite"]) for item in results if "composite" in item]
    summary: dict[str, Any] = {
        "study_date": started.isoformat(),
        "provider": provider,
        "model": model or getattr(connector, "model", None),
        "study_label": study_label or prompts_path.stem,
        "prompt_source": str(prompts_path.relative_to(Path(__file__).resolve().parent.parent.parent)),
        "prompt_count": len(prompts),
        "successes": successes,
        "failures": failures,
        "status": "success" if failures == 0 else ("failed" if successes == 0 else "partial"),
        "elapsed_seconds": elapsed_seconds,
        "dial_config": dial_values,
        "scoring_mode": scoring_mode,
        "scoring_provider": scoring_provider,
        "scoring_model": scoring_model,
    }

    if composites:
        avg = sum(composites) / len(composites)
        std = (sum((c - avg) ** 2 for c in composites) / max(1, len(composites) - 1)) ** 0.5
        summary["composite_mean"] = round(avg, 2)
        summary["composite_std"] = round(std, 2)
        summary["composite_min"] = round(min(composites), 2)
        summary["composite_max"] = round(max(composites), 2)

        certifications: dict[str, int] = {}
        for item in results:
            certification = str(item.get("certification", "error"))
            certifications[certification] = certifications.get(certification, 0) + 1
        summary["certifications"] = certifications

        all_op_scores = [item["operator_scores"] for item in results if item.get("operator_scores")]
        if all_op_scores:
            n = len(all_op_scores)
            summary["operator_averages"] = [round(sum(scores[i] for scores in all_op_scores) / n, 4) for i in range(10)]

        all_domain_scores = [item["domain_averages"] for item in results if item.get("domain_averages")]
        if all_domain_scores:
            n = len(all_domain_scores)
            summary["domain_averages"] = [round(sum(scores[i] for scores in all_domain_scores) / n, 4) for i in range(4)]

    return {"summary": summary, "results": results}


def write_study_bundle(bundle: dict, *, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return output_path


def archive_study_bundle(bundle: dict) -> Path:
    summary = bundle.get("summary", {})
    study_date = str(summary.get("study_date") or datetime.now(timezone.utc).isoformat())
    safe_timestamp = study_date.replace(":", "").replace("+00:00", "Z")
    provider = _slugify(str(summary.get("provider") or "unknown"))
    label = _slugify(str(summary.get("study_label") or "study"))
    filename = f"{safe_timestamp}__{provider}__{label}.json"
    return write_study_bundle(bundle, output_path=studies_dir() / filename)


async def run_and_archive_study(
    *,
    provider: str,
    count: int,
    prompts_path: Path,
    output_path: Path | None = None,
    dials: list[int] | None = None,
    model: str | None = None,
    scoring_mode: str = "heuristic_fallback",
    scoring_provider: str | None = None,
    scoring_model: str | None = None,
    study_label: str | None = None,
    update_default_output: bool = True,
) -> dict:
    bundle = await run_study(
        provider=provider,
        count=count,
        prompts_path=prompts_path,
        dials=dials,
        model=model,
        scoring_mode=scoring_mode,
        scoring_provider=scoring_provider,
        scoring_model=scoring_model,
        study_label=study_label,
    )
    archive_path = archive_study_bundle(bundle)
    resolved_output = output_path or (validation_dir() / "baseline_results.json")
    if update_default_output:
        write_study_bundle(bundle, output_path=resolved_output)
    return {
        "bundle": bundle,
        "archive_path": archive_path,
        "output_path": resolved_output if update_default_output else None,
    }


async def run_suite_matrix(
    *,
    provider: str,
    suite_ids: list[str] | None = None,
    count_per_suite: int = 10,
    dials: list[int] | None = None,
    model: str | None = None,
    scoring_mode: str = "heuristic_fallback",
    scoring_provider: str | None = None,
    scoring_model: str | None = None,
) -> dict:
    collections = available_prompt_collections()
    collection_lookup = {item["id"]: item for item in collections}
    selected_ids = suite_ids or [item["id"] for item in collections if item["id"] != "augmented_library"]
    runs: list[dict[str, Any]] = []

    for suite_id in selected_ids:
        if suite_id not in collection_lookup:
            runs.append(
                {
                    "suite_id": suite_id,
                    "status": "failed",
                    "error": f"unknown suite: {suite_id}",
                }
            )
            continue
        info = collection_lookup[suite_id]
        prompts_path = resolve_prompt_collection(info["path"])
        try:
            result = await run_and_archive_study(
                provider=provider,
                count=count_per_suite,
                prompts_path=prompts_path,
                dials=dials,
                model=model,
                scoring_mode=scoring_mode,
                scoring_provider=scoring_provider,
                scoring_model=scoring_model,
                study_label=info["id"],
                update_default_output=False,
            )
            bundle = result["bundle"]
            summary = bundle.get("summary", {})
            runs.append(
                {
                    "suite_id": suite_id,
                    "label": info["label"],
                    "status": summary.get("status"),
                    "provider": summary.get("provider"),
                    "model": summary.get("model"),
                    "successes": summary.get("successes"),
                    "failures": summary.get("failures"),
                    "prompt_count": summary.get("prompt_count"),
                    "composite_mean": summary.get("composite_mean"),
                    "archive_path": str(result["archive_path"]),
                }
            )
        except Exception as exc:
            runs.append(
                {
                    "suite_id": suite_id,
                    "label": info["label"],
                    "status": "failed",
                    "error": str(exc),
                }
            )

    success_count = sum(1 for item in runs if item.get("status") == "success")
    partial_count = sum(1 for item in runs if item.get("status") == "partial")
    failed_count = sum(1 for item in runs if item.get("status") == "failed")
    return {
        "provider": provider,
        "suite_count": len(runs),
        "success_count": success_count,
        "partial_count": partial_count,
        "failed_count": failed_count,
        "runs": runs,
    }


def list_study_artifacts() -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for path in sorted(studies_dir().glob("*.json"), reverse=True):
        bundle = _load_json(path)
        if not isinstance(bundle, dict):
            continue
        summary = bundle.get("summary", {})
        if not isinstance(summary, dict):
            continue
        artifacts.append(
            {
                "filename": path.name,
                "path": str(path.relative_to(Path(__file__).resolve().parent.parent.parent)),
                "provider": summary.get("provider"),
                "model": summary.get("model"),
                "scoring_mode": summary.get("scoring_mode"),
                "scoring_provider": summary.get("scoring_provider"),
                "scoring_model": summary.get("scoring_model"),
                "study_label": summary.get("study_label"),
                "prompt_source": summary.get("prompt_source"),
                "prompt_count": summary.get("prompt_count"),
                "successes": summary.get("successes"),
                "failures": summary.get("failures"),
                "status": summary.get("status"),
                "composite_mean": summary.get("composite_mean"),
                "composite_std": summary.get("composite_std"),
                "study_date": summary.get("study_date"),
            }
        )
    return artifacts
