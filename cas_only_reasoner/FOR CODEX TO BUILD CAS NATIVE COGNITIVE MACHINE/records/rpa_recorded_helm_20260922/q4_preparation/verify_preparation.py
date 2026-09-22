"""Create metadata-only Q4 preparation evidence; never execute a neural job.

Run using the intended CUDA interpreter with the project authorization
dependency directory explicitly selected by PYTHONPATH and
HELM_Q4_AUTH_DEPENDENCY_DIR. Output files are created exclusively.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

RECORD = Path(__file__).resolve().parent
PROJECT = RECORD.parents[2]
LAB = PROJECT / "research/helm_cas_expression_lab"
sys.path.insert(0, str(LAB))

import q4_checkpoint as checkpoint
import q4_runtime_metadata as runtime
import q4_smoke_job as job


def write_new(name, value):
    with (RECORD / name).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def main():
    # The public RFC8032 vector validates the algorithm/library only. There is
    # no generated owner key, private material, job signature, or authorization.
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    import cryptography
    public = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    # RFC 8032 section 7.1 TEST 1, retaining its four 32-digit lines.
    # https://www.rfc-editor.org/rfc/rfc8032.txt
    signature = bytes.fromhex("e5564300c360ac729086e2cc806e828a"
                              "84877f1eb8e5d974d873e06522490155"
                              "5fb8821590a33bacc61e39701cf9b46b"
                              "d25bf5f0595bbe24655141438e7a100b")
    Ed25519PublicKey.from_public_bytes(public).verify(signature, b"")
    plan = job.prepare_plan(data_dir=LAB / "data/q3_v0_7",
        data_version="helm-cas-expression-lab.q3-behaviour-records/0.7",
        output=RECORD / "q4_smoke_output", seed=20260921, width=64,
        max_updates=128, max_wall_seconds=1800, train_examples=2048,
        dev_examples=16, device="cuda:0")
    if job.validate_plan(plan) != plan or "torch" in sys.modules:
        raise RuntimeError("metadata mismatch or prohibited torch import")
    if plan["environment"]["torch_build"]["status"] != "CUDA_BUILD_RUNTIME_UNPROBED":
        raise RuntimeError("intended CUDA build metadata not established")
    bound = runtime.dependency_manifest()
    if bound is None or not Path(cryptography.__file__).resolve().is_relative_to(Path(bound["root"])):
        raise RuntimeError("cryptography import did not use the bound project copy")
    commands = []
    for args in (["nvidia-smi", "--query-gpu=index,name,uuid,memory.total", "--format=csv,noheader"],
                 ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"]):
        try:
            result = subprocess.run(args, text=True, capture_output=True, timeout=10)
            commands.append({"command": args, "returncode": result.returncode,
                             "stdout": result.stdout, "stderr": result.stderr})
        except (OSError, subprocess.TimeoutExpired) as exc:
            commands.append({"command": args, "returncode": None, "stdout": "", "stderr": str(exc)})
    process_query = commands[1]
    receipt = {
        "schema": "helm-cas-expression-lab.q4-preparation-verification/0.1",
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": checkpoint.digest(checkpoint.canonical(plan)),
        "metadata_revalidation": "PASS", "signature_verifier_import": "PASS",
        "signature_algorithm_known_vector": "RFC8032_TEST_VECTOR_1_VERIFIED_NOT_OWNER_AUTHORIZATION",
        "cryptography_import_path": cryptography.__file__, "environment": runtime.environment_metadata(),
        "hardware_metadata": commands, "torch_imported": False, "model_loaded": False,
        "neural_execution": "NOT_RUN", "owner_authorization": "NOT_FOUND_IN_REVIEWED_Q4_RECORDS",
        "cuda_runtime_status": "NOT_PROBED",
        "gpu_idle_status": "NOT_IDLE_OR_UNKNOWN" if process_query["returncode"] != 0 or process_query["stdout"].strip()
                           else "NO_COMPUTE_PIDS_REPORTED_AT_QUERY",
        "output_directory_exists": Path(plan["output"]).exists(),
        "dependency_manifest_sha256": bound["manifest_sha256"],
        "dependency_scope": "Project copy only; existing GPU environment untouched",
    }
    if receipt["output_directory_exists"]:
        raise RuntimeError("proposed output already exists; no reuse")
    write_new("plan.json", plan)
    write_new("dependency_manifest.json", bound)
    write_new("preparation_verification.json", receipt)
    print(json.dumps({key: receipt[key] for key in (
        "plan_sha256", "metadata_revalidation", "signature_algorithm_known_vector", "torch_imported",
        "neural_execution", "cuda_runtime_status", "gpu_idle_status", "output_directory_exists",
        "dependency_manifest_sha256")}, indent=2))


if __name__ == "__main__":
    main()
