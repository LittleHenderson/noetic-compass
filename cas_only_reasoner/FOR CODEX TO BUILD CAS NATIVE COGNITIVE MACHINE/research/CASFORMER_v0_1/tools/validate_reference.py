"""Run independent, no-training CASformer v0.1 engineering checks."""

from __future__ import annotations

import argparse
import ast
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

import torch


ROOT = Path(__file__).resolve().parents[1]
HOMEBASE = ROOT.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from casformer import (  # noqa: E402
    CASControl,
    CASformerBlock,
    CASformerConfig,
    CASformerLanguageModel,
    DifferentialConductanceLinear,
    DifferentiableConductanceCircuit,
    make_trace,
    verify_trace,
)
from casformer.baselines import compiled_ohmic_attention  # noqa: E402
from build_source_manifest import build_manifest  # noqa: E402


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tensor_sha256(value: torch.Tensor) -> str:
    raw = value.detach().to(device="cpu").contiguous().numpy().tobytes()
    return hashlib.sha256(raw).hexdigest()


def maximum_difference(left: torch.Tensor, right: torch.Tensor) -> float:
    return float((left - right).abs().max().item())


def verify_source_manifest(path: Path) -> tuple[bool, list[str]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    expected = build_manifest()
    for field in (
        "schema_version",
        "status",
        "casformer_version",
        "file_count",
        "aggregate_sha256",
    ):
        if manifest.get(field) != expected[field]:
            errors.append(f"manifest:{field}")

    entries = manifest.get("files", [])
    if not isinstance(entries, list):
        errors.append("malformed:files")
        entries = []
    declared_paths = {
        entry["path"]
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }
    expected_paths = {entry["path"] for entry in expected["files"]}
    for missing in sorted(expected_paths - declared_paths):
        errors.append(f"unbound:{missing}")
    for extra in sorted(declared_paths - expected_paths):
        errors.append(f"unexpected:{extra}")

    for entry in entries:
        if (
            not isinstance(entry, dict)
            or not {"path", "bytes", "sha256"}.issubset(entry)
            or not isinstance(entry.get("path"), str)
        ):
            errors.append("malformed:file-entry")
            continue
        source = (ROOT / entry["path"]).resolve()
        try:
            source.relative_to(ROOT)
        except ValueError:
            errors.append(f"outside-root:{entry['path']}")
            continue
        if not source.is_file():
            errors.append(f"missing:{entry['path']}")
            continue
        if source.stat().st_size != entry["bytes"]:
            errors.append(f"bytes:{entry['path']}")
        if file_sha256(source) != entry["sha256"]:
            errors.append(f"sha256:{entry['path']}")
    return not errors, errors


def verify_source_references(path: Path) -> tuple[bool, list[str], int]:
    references = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    sources = references.get("sources", [])
    if references.get("schema_version") != "cas.casformer.source-references/0.1":
        errors.append("references:schema_version")
    if not isinstance(references.get("instruction_boundary"), str) or not references.get(
        "instruction_boundary"
    ):
        errors.append("references:instruction_boundary")
    if not isinstance(sources, list) or not sources:
        errors.append("references:sources")
        sources = []
    declared_paths: set[str] = set()
    for entry in sources:
        if (
            not isinstance(entry, dict)
            or not {"path", "bytes", "sha256", "role"}.issubset(entry)
            or not isinstance(entry.get("path"), str)
        ):
            errors.append("references:malformed-entry")
            continue
        if entry["path"] in declared_paths:
            errors.append(f"references:duplicate:{entry['path']}")
            continue
        declared_paths.add(entry["path"])
        declared = Path(entry["path"])
        source = declared if declared.is_absolute() else HOMEBASE / declared
        if not source.is_file():
            errors.append(f"missing:{entry['path']}")
            continue
        if source.stat().st_size != entry["bytes"]:
            errors.append(f"bytes:{entry['path']}")
        if file_sha256(source) != entry["sha256"]:
            errors.append(f"sha256:{entry['path']}")
    return not errors, errors, len(sources)


def git_identity() -> dict[str, Any]:
    try:
        repository = Path(
            subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=HOMEBASE,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        ).resolve()
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=HOMEBASE,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=HOMEBASE,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        relative_source = ROOT.relative_to(repository).as_posix()
        tracked = subprocess.run(
            ["git", "ls-files", "--", relative_source],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all", "--", relative_source],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        commit_contains_source = bool(tracked) and not status
        return {
            "commit": commit,
            "branch": branch or "DETACHED",
            "source_path": relative_source,
            "source_files_tracked": bool(tracked),
            "source_worktree_clean": not status,
            "commit_contains_exact_source": commit_contains_source,
            "commit_identity_scope": (
                "SOURCE_IDENTITY" if commit_contains_source else "AMBIENT_REPOSITORY_ONLY"
            ),
        }
    except (OSError, subprocess.CalledProcessError):
        return {
            "commit": "UNAVAILABLE",
            "branch": "UNAVAILABLE",
            "commit_contains_exact_source": False,
            "commit_identity_scope": "UNAVAILABLE",
        }


def find_static_cncm_imports() -> tuple[list[str], int]:
    """Find direct Python imports of this research package in the CNCM kernel."""

    hits: list[str] = []
    scanned = 0
    for path in sorted((HOMEBASE / "cncm").rglob("*.py")):
        scanned += 1
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            if any(name == "casformer" or name.startswith("casformer.") for name in imported):
                hits.append(path.relative_to(HOMEBASE).as_posix())
                break
    return hits, scanned


def run_checks(source_manifest: Path) -> dict[str, Any]:
    torch.manual_seed(20260903)
    torch.use_deterministic_algorithms(True)
    dtype = torch.float64
    config = CASformerConfig(
        d_model=8,
        num_heads=2,
        num_relations=3,
        num_layers=1,
        d_ff=16,
        initial_cutoff=0.1,
        initial_saturation=20.0,
    )
    block = CASformerBlock(config).to(dtype=dtype).eval()
    x = torch.randn(2, 4, 8, dtype=dtype, requires_grad=True)
    control = CASControl.uniform(
        x,
        num_heads=2,
        causal=True,
        profile_id="casformer-v0.1-validation",
        provenance="tools/validate_reference.py",
        control_tick=2,
        feedback_source_tick=1,
    )
    output, telemetry = block(x, control)

    compiled_attention, compiled_current, compiled_total = compiled_ohmic_attention(
        telemetry.attention.semantic_scores,
        control.drive,
        control.total_resistance,
        control.readiness,
        control.region_multiplier,
        control.candidate_path_mask,
    )

    drive_scaled_control = replace(control, drive=control.drive * 3)
    _, drive_scaled = block(x, drive_scaled_control)
    joint_scaled_control = replace(
        control,
        drive=control.drive * 3,
        resistance_capability=control.resistance_capability * 3,
        resistance_policy=control.resistance_policy * 3,
        resistance_context=control.resistance_context * 3,
        resistance_resource=control.resistance_resource * 3,
    )
    _, joint_scaled = block(x, joint_scaled_control)

    permission = control.permission_mask.clone()
    permission[..., -1] = False
    _, masked = block(x, replace(control, permission_mask=permission))

    differential = DifferentialConductanceLinear(4, 3, bias=False).to(dtype=dtype)
    differential_input = torch.randn(5, 4, dtype=dtype)
    differential_output = differential(differential_input)
    direct_output = torch.nn.functional.linear(
        differential_input, differential.effective_weight
    )
    differential_block = CASformerBlock(
        replace(config, linear_weight_mode="differential_conductance")
    ).to(dtype=dtype).eval()
    with torch.no_grad():
        differential_block_output, _ = differential_block(x.detach(), control)

    circuit = DifferentiableConductanceCircuit(damping=0.1)
    circuit_result = circuit(
        torch.tensor([[-1.0, 1.0]], dtype=dtype),
        torch.tensor([2.0], dtype=dtype),
        torch.tensor([[[1.0], [-1.0]]], dtype=dtype),
    )

    loss = output.square().mean() + telemetry.cjt_gate.mean()
    loss.backward()
    gradients_finite = all(
        parameter.grad is not None and bool(torch.isfinite(parameter.grad).all().item())
        for parameter in block.parameters()
        if parameter.requires_grad
    ) and x.grad is not None and bool(torch.isfinite(x.grad).all().item())

    trace = make_trace(telemetry, control, layer_index=0, include_tensors=True)
    manifest_valid, manifest_errors = verify_source_manifest(source_manifest)
    references_valid, reference_errors, reference_count = verify_source_references(
        ROOT / "SOURCE_REFERENCES.json"
    )

    # A real causal language-model forward pass, still without training.
    language_model = CASformerLanguageModel(
        config, vocab_size=23, max_sequence_length=8
    ).to(dtype=dtype).eval()
    token_ids = torch.tensor([[1, 5, 2, 7]], dtype=torch.long)
    language_control = CASControl.uniform(
        torch.zeros(1, 4, 8, dtype=dtype), num_heads=2, causal=True
    )
    with torch.no_grad():
        logits, _ = language_model(token_ids, language_control)

    cncm_import_hits, cncm_python_files_scanned = find_static_cncm_imports()

    metrics = {
        "compiled_attention_max_abs_error": maximum_difference(
            telemetry.attention.attention, compiled_attention
        ),
        "compiled_current_max_abs_error": maximum_difference(
            telemetry.attention.current, compiled_current
        ),
        "compiled_total_current_max_abs_error": maximum_difference(
            telemetry.attention.total_current, compiled_total
        ),
        "common_drive_attention_max_abs_drift": maximum_difference(
            telemetry.attention.attention, drive_scaled.attention.attention
        ),
        "common_drive_total_current_ratio": float(
            (drive_scaled.attention.total_current / telemetry.attention.total_current)
            .mean()
            .item()
        ),
        "joint_scale_attention_max_abs_drift": maximum_difference(
            telemetry.attention.attention, joint_scaled.attention.attention
        ),
        "joint_scale_total_current_max_abs_drift": maximum_difference(
            telemetry.attention.total_current, joint_scaled.attention.total_current
        ),
        "masked_current_max_abs": float(masked.attention.current[..., -1].abs().max().item()),
        "masked_attention_max_abs": float(
            masked.attention.attention[..., -1].abs().max().item()
        ),
        "differential_direct_max_abs_error": maximum_difference(
            differential_output, direct_output
        ),
        "differential_gauge_ratio": float(differential.gauge_ratio().item()),
        "differential_weight_block_parameter_count": sum(
            parameter.numel() for parameter in differential_block.parameters()
        ),
        "circuit_solve_residual_max_abs": float(
            circuit_result.solve_residual.abs().max().item()
        ),
        "language_logits_shape": list(logits.shape),
        "parameter_count_block": sum(parameter.numel() for parameter in block.parameters()),
        "source_reference_count": reference_count,
        "cncm_python_files_scanned_for_static_imports": cncm_python_files_scanned,
        "cncm_static_casformer_import_hits": cncm_import_hits,
        "output_sha256": tensor_sha256(output),
    }
    checks = {
        "source_manifest_current": manifest_valid,
        "source_references_current": references_valid,
        "compiled_attention_twin": metrics["compiled_attention_max_abs_error"] < 1e-12,
        "compiled_current_twin": metrics["compiled_current_max_abs_error"] < 1e-12,
        "common_drive_available_flow_scales": abs(
            metrics["common_drive_total_current_ratio"] - 3.0
        )
        < 1e-12,
        "common_drive_allocation_invariant": metrics[
            "common_drive_attention_max_abs_drift"
        ] < 1e-12,
        "joint_drive_resistance_invariant": max(
            metrics["joint_scale_attention_max_abs_drift"],
            metrics["joint_scale_total_current_max_abs_drift"],
        )
        < 1e-12,
        "hard_mask_exact_zero": metrics["masked_current_max_abs"] == 0.0
        and metrics["masked_attention_max_abs"] == 0.0,
        "differential_pair_matches_direct_signed_map": metrics[
            "differential_direct_max_abs_error"
        ]
        < 1e-12,
        "differential_conductance_weight_mode_forward": bool(
            torch.isfinite(differential_block_output).all().item()
        ),
        "circuit_solve": metrics["circuit_solve_residual_max_abs"] < 1e-12,
        "finite_forward": bool(torch.isfinite(output).all().item()),
        "nominal_finite_backward": gradients_finite,
        "trace_digest_valid": verify_trace(trace),
        "trace_has_zero_authority": not any(trace.payload["authority"].values()),
        "causal_language_model_forward": metrics["language_logits_shape"] == [1, 4, 23],
        "cncm_no_static_direct_casformer_import_detected": not cncm_import_hits,
    }
    return {
        "checks": checks,
        "metrics": metrics,
        "source_manifest_errors": manifest_errors,
        "source_reference_errors": reference_errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "CASFORMER_V0_1_VALIDATION_RECEIPT.json",
    )
    parser.add_argument(
        "--source-manifest", type=Path, default=ROOT / "SOURCE_MANIFEST.json"
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    source_manifest = (
        args.source_manifest
        if args.source_manifest.is_absolute()
        else ROOT / args.source_manifest
    )
    if not source_manifest.is_file():
        raise SystemExit(f"source manifest not found: {source_manifest}")

    results = run_checks(source_manifest)
    passed = all(results["checks"].values())
    receipt = {
        "schema_version": "cas.casformer.validation-receipt/0.1",
        "status": "CORE_ENGINEERING_CHECKS_PASSED" if passed else "VALIDATION_FAILED",
        "scope": "ENGINEERING_VALIDATION_ONLY",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "pytorch": torch.__version__,
            "device": "cpu",
            "cuda_available": torch.cuda.is_available(),
            "platform": platform.platform(),
        },
        "git": git_identity(),
        "source_manifest": {
            "path": source_manifest.relative_to(ROOT).as_posix(),
            "sha256": file_sha256(source_manifest),
        },
        **results,
        "claims": {
            "software_reference_implementation": "IMPLEMENTED",
            "neural_training": "NOT_RUN",
            "language_capability": "NOT_ESTABLISHED",
            "reasoning_capability": "NOT_ESTABLISHED",
            "cas_specific_advantage": "NOT_ESTABLISHED",
            "cncm_kernel_integration": "ABSENT",
            "production_readiness": "NOT_ESTABLISHED",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
