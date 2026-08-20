"""Truth-blind actor phase for WELD v3.

There is deliberately no truth parameter and no adjudication import here.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .core import (
    ACTOR_RECEIPT_SCHEMA,
    WeldProtocolError,
    canonical_json_bytes,
    load_json,
    sha256_bytes,
    sha256_file,
    utc_now,
    validate_actor_output,
    validate_protocol,
    validate_public_cases,
    write_exclusive_json,
)
from .freeze import verify_freeze
from .runtime import adapter_command, attest_binding


ACTOR_RECEIPT_FILENAME = "actor_receipt.json"


def _clean_actor_environment(work_dir: Path) -> dict[str, str]:
    clean: dict[str, str] = {
        "WELD_V3_PHASE": "ACTOR_COMMITMENT_ONLY",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "TEMP": str(work_dir),
        "TMP": str(work_dir),
    }
    for name in ("SYSTEMROOT", "WINDIR", "COMSPEC"):
        if name in os.environ:
            clean[name] = os.environ[name]
    return clean


def _invoke_case(
    command: list[str], case: Mapping[str, Any], work_dir: Path, sequence: int
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if any(work_dir.iterdir()):
        raise WeldProtocolError("each case must start in its own empty working directory")
    input_bytes = canonical_json_bytes(case)
    started_utc = utc_now()
    try:
        completed = subprocess.run(
            command,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=work_dir,
            env=_clean_actor_environment(work_dir),
            shell=False,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise WeldProtocolError(f"actor adapter invocation failed: {exc}") from exc
    completed_utc = utc_now()
    if completed.returncode != 0:
        raise WeldProtocolError(
            f"actor adapter returned {completed.returncode}; stderr_sha256="
            f"{sha256_bytes(completed.stderr)}"
        )
    if completed.stderr:
        raise WeldProtocolError("actor adapter wrote to the forbidden stderr channel")
    try:
        output = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise WeldProtocolError(f"actor adapter returned invalid JSON: {exc}") from exc
    validated = validate_actor_output(output, case)
    if any(work_dir.iterdir()):
        raise WeldProtocolError("an actor case left cross-case state in its working directory")
    invocation = {
        "sequence": sequence,
        "case_id": case["case_id"],
        "adapter_invoked": True,
        "started_utc": started_utc,
        "completed_utc": completed_utc,
        "input_sha256": sha256_bytes(input_bytes),
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
        "returncode": completed.returncode,
        "isolated_cwd_token": sha256_bytes(str(work_dir.resolve()).encode("utf-8")),
    }
    return validated, invocation


def run_actor_phase(freeze_path: Path) -> Mapping[str, Any]:
    receipt = verify_freeze(freeze_path)
    root = Path(receipt["prereg_root_absolute"])
    result_dir = Path(receipt["result_dir_absolute"])
    if result_dir.exists() and (not result_dir.is_dir() or any(result_dir.iterdir())):
        raise WeldProtocolError("actor result directory must be absent or empty")

    protocol = validate_protocol(load_json(root / "protocol.json"))
    cases = validate_public_cases(load_json(root / "public_cases.json"))
    binding = load_json(root / "runtime_binding.json")
    allow_mock = receipt["profile"] == "MOCK_TEST_ONLY" and receipt["mock_authorized"] is True
    pre_attestation = attest_binding(binding, allow_mock=allow_mock)
    if pre_attestation != receipt["runtime_attestation"]:
        raise WeldProtocolError("runtime attestation differs from the freeze-time attestation")

    command = adapter_command(binding)
    outputs: list[Mapping[str, Any]] = []
    invocations: list[Mapping[str, Any]] = []
    cwd_tokens: set[str] = set()
    result_dir.parent.mkdir(parents=True, exist_ok=True)
    for sequence, case in enumerate(sorted(cases, key=lambda item: item["case_id"]), start=1):
        with tempfile.TemporaryDirectory(
            prefix=f"weld-v3-case-{sequence:06d}-", dir=result_dir.parent
        ) as temporary:
            output, invocation = _invoke_case(command, case, Path(temporary), sequence)
            if invocation["isolated_cwd_token"] in cwd_tokens:
                raise WeldProtocolError("case working directory was reused")
            cwd_tokens.add(invocation["isolated_cwd_token"])
            outputs.append(output)
            invocations.append(invocation)

    post_attestation = attest_binding(binding, allow_mock=allow_mock)
    if post_attestation != pre_attestation:
        raise WeldProtocolError("runtime or adapter changed during the actor phase")

    actor_receipt = {
        "schema_version": ACTOR_RECEIPT_SCHEMA,
        "phase_status": "SEALED",
        "actor_completed_utc": utc_now(),
        "freeze_id": receipt["freeze_id"],
        "freeze_receipt_sha256": sha256_file(freeze_path.resolve()),
        "protocol_id": protocol["protocol_id"],
        "profile": receipt["profile"],
        "claim_ceiling": (
            "MOCK_PROTOCOL_TEST_ONLY"
            if receipt["profile"] == "MOCK_TEST_ONLY"
            else "ENGINEERED_NOT_VALIDATED"
        ),
        "public_cases_sha256": sha256_file(root / "public_cases.json"),
        "runtime_pre_attestation": pre_attestation,
        "runtime_post_attestation": post_attestation,
        "truth_channel": "COMMITMENT_ONLY_NO_PLAINTEXT_ARGUMENT",
        "adapter_command_shape": (
            "ONE_BOUND_RUST_EXECUTABLE_NO_CASE_ARGUMENTS"
            if receipt["profile"] == "PRODUCTION_RUST"
            else "ONE_BOUND_MOCK_ADAPTER_NO_CASE_ARGUMENTS"
        ),
        "cross_case_cwd_policy": "FRESH_EMPTY_UNIQUE_CWD_PER_CASE",
        "invocation_count": len(invocations),
        "invocations": invocations,
        "outputs": outputs,
    }
    result_dir.mkdir(parents=True, exist_ok=True)
    write_exclusive_json(result_dir / ACTOR_RECEIPT_FILENAME, actor_receipt)
    return actor_receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the truth-blind WELD-v3 actor phase")
    parser.add_argument("freeze_receipt", type=Path)
    args = parser.parse_args()
    receipt = run_actor_phase(args.freeze_receipt)
    print(sha256_bytes(canonical_json_bytes(receipt)))


if __name__ == "__main__":
    main()
