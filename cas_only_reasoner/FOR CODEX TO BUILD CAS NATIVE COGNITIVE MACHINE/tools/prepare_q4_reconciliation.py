"""Prepare a new metadata-only Q4 record; never load a model or issue approval."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
LAB = PROJECT / "research/helm_cas_expression_lab"


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    record = args.out.resolve()
    if not record.is_relative_to(PROJECT / "records") or record.exists():
        raise ValueError("Use a new, absent directory inside this checkout's records directory.")
    sys.path.insert(0, str(LAB))
    import q4_checkpoint as checkpoint
    import q4_runtime_metadata as runtime
    import q4_smoke_job as job
    plan = job.prepare_plan(
        data_dir=LAB / "data/q3_v0_7",
        data_version="helm-cas-expression-lab.q3-behaviour-records/0.7",
        output=record / "q4_smoke_output", seed=20260921, width=64,
        max_updates=128, max_wall_seconds=1800, train_examples=2048,
        dev_examples=16, device="cuda:0")
    if job.validate_plan(plan) != plan or "torch" in sys.modules:
        raise RuntimeError("Plan drift or unexpected Torch import")
    if plan["environment"]["torch_build"]["status"] != "CUDA_BUILD_RUNTIME_UNPROBED":
        raise RuntimeError("Use the intended CUDA interpreter for static build metadata.")
    dependency = runtime.dependency_manifest()
    if dependency is None:
        raise RuntimeError("An existing bound authorization dependency directory is required.")
    # This is source/dependency inspection, not a signature or GPU capability test.
    record.mkdir(parents=True, exist_ok=False)
    write_new(record / "plan.json", plan)
    write_new(record / "dependency_manifest.json", dependency)
    receipt = {
        "schema": "cas.q4-fresh-preparation/0.1",
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "repository_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip(),
        "plan_canonical_sha256": checkpoint.digest(checkpoint.canonical(plan)),
        "plan_file_sha256": hashlib.sha256((record / "plan.json").read_bytes()).hexdigest(),
        "metadata_revalidation": "PASS",
        "neural_execution": "NOT_RUN", "torch_imported": False,
        "cuda_execution": "NOT_PROBED", "gpu_capacity": "NOT_QUERIED",
        "owner_authorization": "NOT_SUPPLIED",
        "owner_trust_anchor": "EXTERNALLY_ESTABLISHED_MATERIAL_STILL_REQUIRED",
        "proposed_output_exists": Path(plan["output"]).exists(),
        "test_functions": 0, "test_cases": 0,
        "history": "New preparation for this checkout. Does not replace any prior receipt or authorize a run.",
        "command": [sys.executable, *sys.argv],
    }
    if receipt["proposed_output_exists"]:
        raise RuntimeError("Preparation must not create a neural output directory.")
    write_new(record / "verification.json", receipt)
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
