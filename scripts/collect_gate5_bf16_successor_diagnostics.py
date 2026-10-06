#!/usr/bin/env python3
"""Retain the post-failure FP16/BF16 infrastructure diagnostics.

These commands are engineering diagnostics, not experimental arms. They bind
the observed v0.1 startup defect, the adapted BF16 choice, and the exact local
successor runtime without creating a prompt-injection or steering claim.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = (
    REPO_ROOT
    / "docs"
    / "working"
    / "project_coherence"
    / "gate5"
    / "model_smoke"
    / "diagnostics"
    / "bf16_successor_v0.1"
)
PARENT = "sha256:3d747b379938a5148e4a028ff8ba2f242847b17e8842f19f0d2c204b3fe9a95c"
SUCCESSOR = "sha256:33805740641bad585a25d1e8a614b264e5daa97b588d26bf01762a0278f14c7d"
CLAIM_BOUNDARY = (
    "RESEARCH ONLY / POST-FAILURE ADAPTED CANARY / NOT INDEPENDENT "
    "REPLICATION / NOT PRODUCT VALIDATION / NO PROMPT-INJECTION DEFENSE "
    "CLAIM / NO STEERING EFFICACY CLAIM / GATE 5 REMAINS OPEN"
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _run(command: Sequence[str], *, timeout: float = 180.0) -> dict[str, Any]:
    started = datetime.now(UTC)
    completed = subprocess.run(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )
    ended = datetime.now(UTC)
    return {
        "command": list(command),
        "returncode": completed.returncode,
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "completed_at": ended.isoformat().replace("+00:00", "Z"),
        "elapsed_seconds": round((ended - started).total_seconds(), 6),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _docker_prefix(image: str) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--memory",
        "6g",
        "--memory-swap",
        "6g",
        "--pids-limit",
        "512",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges=true",
        "--user",
        "10001:10001",
        "--entrypoint",
        "python",
        image,
    ]


def _write_result(name: str, result: dict[str, Any]) -> dict[str, Any]:
    stdout_path = OUTPUT_DIR / f"{name}.stdout.bin"
    stderr_path = OUTPUT_DIR / f"{name}.stderr.bin"
    stdout_path.write_bytes(result["stdout"])
    stderr_path.write_bytes(result["stderr"])
    return {
        "name": name,
        "command": result["command"],
        "returncode": result["returncode"],
        "started_at": result["started_at"],
        "completed_at": result["completed_at"],
        "elapsed_seconds": result["elapsed_seconds"],
        "stdout": {
            "path": stdout_path.relative_to(REPO_ROOT).as_posix(),
            "sha256": _sha256(result["stdout"]),
            "bytes": len(result["stdout"]),
        },
        "stderr": {
            "path": stderr_path.relative_to(REPO_ROOT).as_posix(),
            "sha256": _sha256(result["stderr"]),
            "bytes": len(result["stderr"]),
        },
    }


def main() -> int:
    if OUTPUT_DIR.exists():
        raise SystemExit(f"diagnostic output already exists: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True)

    parent_cache = _run(
        [
            *_docker_prefix(PARENT)[:-3],
            "--env",
            "TRITON_CACHE_DIR=/tmp/triton-cache",
            *_docker_prefix(PARENT)[-3:],
            "-c",
            "from app.runtime.model_loader import warm_load; warm_load()",
        ]
    )
    parent_nojit = _run(
        [
            *_docker_prefix(PARENT)[:-3],
            "--env",
            "TORCH_DISABLE_NATIVE_JIT=1",
            *_docker_prefix(PARENT)[-3:],
            "-c",
            "from app.runtime.model_loader import warm_load; warm_load()",
        ]
    )
    parent_bfloat16_code = (
        "import json,torch; "
        "from transformers import AutoModelForCausalLM,AutoTokenizer; "
        "mid='EleutherAI/pythia-160m'; "
        "rev='50f5173d932e8e61f858120bcb800b97af589f46'; "
        "tok=AutoTokenizer.from_pretrained(mid,revision=rev,local_files_only=True); "
        "model=AutoModelForCausalLM.from_pretrained(mid,revision=rev,"
        "use_safetensors=True,dtype=torch.bfloat16,attn_implementation='eager',"
        "local_files_only=True).eval().to('cuda'); "
        "inp=tok('Project Coherence Gate 5 runtime canary.',return_tensors='pt'); "
        "inp={k:v.to('cuda') for k,v in inp.items()}; "
        "out=model(**inp,output_attentions=True,use_cache=False); "
        "print(json.dumps({'dtype':str(next(model.parameters()).dtype),"
        "'native_bfloat16':bool(torch.cuda.is_bf16_supported(including_emulation=False)),"
        "'logits_finite':bool(torch.isfinite(out.logits).all().item()),"
        "'attention_finite':all(bool(torch.isfinite(x).all().item()) for x in out.attentions),"
        "'logit_elements':out.logits.numel(),"
        "'nonfinite_logits':int((~torch.isfinite(out.logits)).sum().item()),"
        "'attention_tensors':len(out.attentions)}))"
    )
    parent_bfloat16 = _run(
        [
            *_docker_prefix(PARENT)[:-3],
            "--env",
            "TORCH_DISABLE_NATIVE_JIT=1",
            *_docker_prefix(PARENT)[-3:],
            "-c",
            parent_bfloat16_code,
        ]
    )
    successor_policy_code = (
        "import hashlib,json,os,shutil; "
        "from pathlib import Path; "
        "from app.runtime.model_loader import warm_load; "
        "from torch._native.common_utils import check_native_jit_disabled; "
        "import torch._native.common_utils as native_common; "
        "import torch._native.triton_utils as native_triton; "
        "loaded=warm_load(); "
        "source=Path(native_common.__file__); "
        "triton_source=Path(native_triton.__file__); "
        "tmp_entries=sorted(str(p.relative_to('/tmp')) for p in Path('/tmp').rglob('*')); "
        "parameters=tuple(loaded.model.parameters()); "
        "print(json.dumps({'runtime_execution':loaded.manifest.runtime_execution.model_dump(),"
        "'policy_effective':bool(check_native_jit_disabled()),"
        "'policy_source_path':str(source),"
        "'policy_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),"
        "'triton_policy_source_path':str(triton_source),"
        "'triton_policy_source_sha256':hashlib.sha256(triton_source.read_bytes()).hexdigest(),"
        "'compiler_paths':{name:shutil.which(name) for name in ('cc','gcc','clang')},"
        "'root_worker_writable':os.access('/worker',os.W_OK),"
        "'tmp_entries':tmp_entries,"
        "'parameter_count':len(parameters),"
        "'parameter_dtypes':sorted({str(p.dtype) for p in parameters}),"
        "'parameter_devices':sorted({str(p.device.type) for p in parameters})}))"
    )
    successor_policy = _run(
        [*_docker_prefix(SUCCESSOR), "-c", successor_policy_code]
    )
    image_inspect = _run(
        ["docker", "image", "inspect", PARENT, SUCCESSOR], timeout=30.0
    )

    raw_results = {
        "parent_cache_redirect": parent_cache,
        "parent_nojit_float16": parent_nojit,
        "parent_custom_bfloat16": parent_bfloat16,
        "successor_policy_warm_load": successor_policy,
        "image_inspect": image_inspect,
    }
    entries = [_write_result(name, result) for name, result in raw_results.items()]
    decoded = {
        name: (result["stdout"] + result["stderr"]).decode("utf-8", errors="replace")
        for name, result in raw_results.items()
    }
    checks = {
        "parent_cache_redirect_exposed_absent_compiler": (
            parent_cache["returncode"] != 0
            and "Failed to find C compiler" in decoded["parent_cache_redirect"]
        ),
        "parent_nojit_float16_exposed_nonfinite_logits": (
            parent_nojit["returncode"] != 0
            and "nonfinite logits" in decoded["parent_nojit_float16"]
        ),
        "parent_custom_bfloat16_was_finite": (
            parent_bfloat16["returncode"] == 0
            and '"logits_finite": true' in decoded["parent_custom_bfloat16"]
            and '"attention_finite": true' in decoded["parent_custom_bfloat16"]
            and '"nonfinite_logits": 0' in decoded["parent_custom_bfloat16"]
        ),
        "successor_policy_warm_load_passed": (
            successor_policy["returncode"] == 0
            and '"policy_effective": true' in decoded["successor_policy_warm_load"]
            and '"parameter_dtypes": ["torch.bfloat16"]'
            in decoded["successor_policy_warm_load"]
            and '"parameter_devices": ["cuda"]'
            in decoded["successor_policy_warm_load"]
            and '"policy_source_sha256": "d9c486c9d0dea43f5aaf09c3ca37e0c23603ffb8f57378e42a99c0087cfef0c7"'
            in decoded["successor_policy_warm_load"]
            and '"triton_policy_source_sha256": "ca5da84d2cccdba259f953f1fdf98dea8297b3e70a6b43314b23cc235e6feba7"'
            in decoded["successor_policy_warm_load"]
            and '"cc": null' in decoded["successor_policy_warm_load"]
            and '"gcc": null' in decoded["successor_policy_warm_load"]
            and '"clang": null' in decoded["successor_policy_warm_load"]
        ),
        "image_inspection_retained": image_inspect["returncode"] == 0,
    }
    git_head = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.decode("ascii").strip()
    ledger = {
        "schema_version": "cas_harness_gate5_bf16_successor_diagnostics.v1",
        "status": "PASS" if all(checks.values()) else "FAIL_CLOSED",
        "adaptation_status": "POST-FAILURE ADAPTED CANARY / NOT INDEPENDENT REPLICATION",
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "collector_git_head": git_head,
        "collector_path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
        "collector_sha256": _sha256(Path(__file__).read_bytes()),
        "parent_image_id_and_digest": PARENT,
        "successor_image_id_and_digest": SUCCESSOR,
        "input_text": "Project Coherence Gate 5 runtime canary.",
        "checks": checks,
        "entries": entries,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    ledger_path = OUTPUT_DIR / "diagnostic_ledger.json"
    ledger_path.write_bytes(_json_bytes(ledger))
    print(ledger_path)
    print(ledger["status"])
    return 0 if ledger["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
