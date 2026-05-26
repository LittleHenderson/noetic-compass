"""Prepare a genuine large-model CAS Harness eval.

This script starts the API-side distributed audit control plane and writes a
worker launch manifest. It does not run inference by itself; the manifest
commands must be executed on machines that can load the target open weights.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
from typing import Any
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://noetic-compass-api.onrender.com"
TOKEN_ENV_VAR = "CAS_HARNESS_API_TOKEN"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a CAS Harness large-model distributed eval.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--bearer-token", default=os.environ.get(TOKEN_ENV_VAR))
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--parameter-count-b", type=float, required=True)
    parser.add_argument("--num-layers", type=int, default=None)
    parser.add_argument("--precision", default="bf16", choices=["fp16", "bf16", "int8", "int4"])
    parser.add_argument("--available-gpu-memory-gb", type=int, default=None)
    parser.add_argument("--minimum-worker-count", type=int, default=None)
    parser.add_argument("--scenario-path", required=True)
    parser.add_argument("--probe-weights-path", default=None)
    parser.add_argument("--cover-map-path", default=None)
    parser.add_argument("--model-revision", default=None)
    parser.add_argument("--torch-dtype", default="bf16")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--worker-url", default="http://localhost:8080")
    parser.add_argument("--gpu-type", default="unknown-gpu")
    parser.add_argument("--output", default="large_model_eval_launch_manifest.json")
    args = parser.parse_args(argv)

    request = {
        "model_id": args.model_id,
        "parameter_count_b": args.parameter_count_b,
        "precision": args.precision,
        "audit_depth": "FULL_INTERNAL",
    }
    if args.num_layers is not None:
        request["num_layers"] = args.num_layers
    if args.available_gpu_memory_gb is not None:
        request["available_gpu_memory_gb"] = args.available_gpu_memory_gb
    if args.minimum_worker_count is not None:
        request["minimum_worker_count"] = args.minimum_worker_count

    base_url = args.base_url.rstrip("/")
    session = post_json(
        base_url,
        "/api/cas-harness/audit/distributed/session",
        request,
        bearer_token=args.bearer_token,
    )
    audit_id = session["audit_id"]
    dispatch = post_json(
        base_url,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/dispatch",
        None,
        bearer_token=args.bearer_token,
    )
    fleet = post_json(
        base_url,
        f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/prepare",
        None,
        bearer_token=args.bearer_token,
    )

    manifest = build_launch_manifest(
        base_url=base_url,
        audit=session,
        dispatch=dispatch,
        fleet=fleet,
        bearer_token_env=TOKEN_ENV_VAR,
        scenario_path=args.scenario_path,
        probe_weights_path=args.probe_weights_path,
        cover_map_path=args.cover_map_path,
        model_revision=args.model_revision,
        torch_dtype=args.torch_dtype,
        device_map=args.device_map,
        worker_url=args.worker_url,
        gpu_type=args.gpu_type,
    )
    output_path = Path(args.output)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {output_path}")
    print(f"audit_id={audit_id}")
    print(f"workers={len(manifest['worker_commands'])}")
    print("Run the worker commands on machines that can load the target open weights.")
    return 0


def build_launch_manifest(
    *,
    base_url: str,
    audit: dict[str, Any],
    dispatch: dict[str, Any],
    fleet: dict[str, Any],
    bearer_token_env: str,
    scenario_path: str,
    probe_weights_path: str | None,
    cover_map_path: str | None,
    model_revision: str | None,
    torch_dtype: str,
    device_map: str,
    worker_url: str,
    gpu_type: str,
) -> dict[str, Any]:
    plan = dispatch["plan"]
    audit_id = audit["audit_id"]
    commands = []
    for assignment in dispatch["worker_evidence"]:
        worker_id = assignment["worker_id"]
        env = {
            "CAS_HARNESS_API_TOKEN": f"${bearer_token_env}",
            "CAS_FLEET_SCENARIO_PATH": scenario_path,
            "CAS_FLEET_TORCH_DTYPE": torch_dtype,
            "CAS_FLEET_DEVICE_MAP": device_map,
        }
        if probe_weights_path:
            env["CAS_FLEET_PROBE_WEIGHTS_PATH"] = probe_weights_path
        if cover_map_path:
            env["CAS_FLEET_COVER_MAP_PATH"] = cover_map_path
        if model_revision:
            env["CAS_FLEET_MODEL_REVISION"] = model_revision
        command = [
            "python",
            "live-trace-worker/scripts/run_fleet_worker.py",
            "--api-base-url",
            base_url,
            "--audit-id",
            audit_id,
            "--worker-id",
            worker_id,
            "--model-id",
            plan["model_id"],
            "--worker-url",
            worker_url,
            "--gpu-type",
            gpu_type,
            "--bearer-token",
            f"${bearer_token_env}",
            "--",
            "python",
            "live-trace-worker/scripts/run_open_weight_probe_shard.py",
        ]
        commands.append(
            {
                "worker_id": worker_id,
                "layer_start": assignment["layer_start"],
                "layer_end": assignment["layer_end"],
                "shard_id": assignment["shard_id"],
                "assigned_methods": assignment["assigned_methods"],
                "expected_outputs": assignment["expected_outputs"],
                "env": env,
                "command": " ".join(shlex.quote(part) for part in command),
            }
        )
    return {
        "schema_version": "cas_harness_large_model_eval_launch_manifest.v1",
        "audit_id": audit_id,
        "model_id": plan["model_id"],
        "parameter_count_b": plan["parameter_count_b"],
        "num_layers": plan["num_layers"],
        "recommended_worker_count": plan["recommended_worker_count"],
        "fleet_gate_status": fleet["verifier_gate_status"],
        "scenario_path": scenario_path,
        "probe_weights_path": probe_weights_path,
        "cover_map_path": cover_map_path,
        "worker_commands": commands,
        "honesty_contract": (
            "This manifest only launches real open-weight worker jobs. Missing model weights, "
            "probe weights, or cover maps must produce failed/missing receipts, not fake passes."
        ),
    }


def post_json(
    base_url: str,
    path: str,
    payload: dict[str, Any] | None,
    *,
    bearer_token: str | None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if bearer_token:
        headers["Authorization"] = (
            bearer_token if bearer_token.lower().startswith("bearer ") else f"Bearer {bearer_token}"
        )
    request = Request(f"{base_url}{path}", data=body, headers=headers, method="POST")
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
