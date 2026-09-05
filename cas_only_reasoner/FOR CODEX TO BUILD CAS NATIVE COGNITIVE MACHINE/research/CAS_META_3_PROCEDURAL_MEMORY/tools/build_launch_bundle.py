"""Build the fixed META3 native-memory demo from committed bytes only."""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("cas_meta3_bundle_frozen", ROOT / "aws/frozen_helpers.py")
frozen = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(frozen)
PACKAGES, PILOT = frozen.PACKAGES, frozen.PILOT
include_member = frozen.include_member


def make_manifest(members, head, upstream):
    frozen.require(all(name in members for name in frozen.REQUIRED), "META3_DEMO_SOURCE_NOT_READY_IN_COMMIT")
    frozen.require(sum(map(len, members.values())) <= frozen.EXPANDED_LIMIT, "ARCHIVE_EXPANDED_SIZE_CEILING")
    baseline = frozen.check_upstream(members, upstream)
    return {
        "schema": frozen.SCHEMA, "source_sha": head, "upstream_sha": frozen.UPSTREAM_SHA,
        "baseline_sha": frozen.BASELINE_SHA, "entrypoint": frozen.ENTRYPOINT,
        "pilot_dir": PILOT, "meta2_dir": frozen.META2, "meta1_dir": frozen.META1,
        "meta_runtime_dir": frozen.META_RUNTIME,
        "dependency_lock": frozen.META2 + "/requirements-gpu.txt",
        "wheel_paths": list(frozen.WHEELS), "included_packages": list(PACKAGES),
        "helper_files_sha256": {frozen.META2 + "/" + name: value for name, value in frozen.PINNED_FILES.items()},
        "upstream_files_sha256": {name: sha256(raw).hexdigest() for name, raw in sorted(upstream.items())},
        "files_sha256": {name: sha256(raw).hexdigest() for name, raw in sorted(members.items())},
        "protected_baseline_files": len(baseline["files"]),
        "artifact_roots": {"demo": "cloud_job/demo", "native": "meta2_native/meta3_<job>",
                           "regression": "meta1_runs"},
        "dependency_scope": "Unchanged pinned requirements and wheels; actual CUDA environment is separately receipted.",
        "excluded_inputs": "All META1/META2/META3 records and runs, including prior labels, checkpoints and budget records.",
        "learning_performed": False, "qualification_status": "UNQUALIFIED",
        "boundary": "Fresh-process registry retrieval is not native suspended-call restart or skill qualification.",
        "neural_execution_performed_during_packaging": False,
    }


def build(output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT) or output == ROOT or output.exists():
        raise ValueError("NEW_OUTPUT_INSIDE_META3_REQUIRED")
    repo, prefix = frozen.git_context(ROOT)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    source_paths = [prefix + name for name in PACKAGES]
    changes = subprocess.check_output(["git", "diff", "--name-only", "-z", "HEAD", "--", *source_paths], cwd=repo, text=True)
    if any(include_member("research/" + name[len(prefix):]) for name in changes.split("\0") if name.startswith(prefix)):
        raise ValueError("TRACKED_SOURCE_CHANGES_MUST_BE_COMMITTED_FIRST")
    untracked = subprocess.check_output(["git", "-c", "core.quotepath=false", "ls-files", "-z",
                                        "--others", "--exclude-standard", "--", *source_paths], cwd=repo, text=True)
    if any(include_member("research/" + name[len(prefix):]) for name in untracked.split("\0") if name.startswith(prefix)):
        raise ValueError("UNTRACKED_SOURCE_MUST_BE_COMMITTED_FIRST")
    frozen.verify_dependencies()
    members = frozen.git_members(repo, prefix, head)
    upstream = frozen.git_members(repo, prefix, frozen.UPSTREAM_SHA, frozen.UPSTREAM_PACKAGES)
    manifest = make_manifest(members, head, upstream)
    members["launch_manifest.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("ARCHIVE_CRC_FAILURE")
        for name, expected in manifest["files_sha256"].items():
            if sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("ARCHIVE_READBACK_HASH_FAILURE")
    return {"status": "CAS_META_3_PINNED_DEMO_PACKAGE_BUILT_GPU_NOT_RUN",
        "source_sha": head, "upstream_sha": frozen.UPSTREAM_SHA, "archive": str(output),
        "archive_sha256": sha256(output.read_bytes()).hexdigest(), "archive_bytes": output.stat().st_size,
        "files": len(members), "launch_manifest": manifest,
        "learning_performed": False, "qualification_status": "UNQUALIFIED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt_path = args.output.with_suffix(".receipt.json")
    if receipt_path.exists():
        raise ValueError("PACKAGE_RECEIPT_ALREADY_EXISTS")
    receipt = build(args.output)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in receipt.items() if key != "launch_manifest"}, indent=2))


if __name__ == "__main__":
    main()
