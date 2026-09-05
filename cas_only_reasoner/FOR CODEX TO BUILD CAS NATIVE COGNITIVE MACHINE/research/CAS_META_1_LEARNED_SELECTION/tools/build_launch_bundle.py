"""Create a source-pinned AWS ZIP from Git, never from scratch outputs."""
import argparse
from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("CAS_META_1_LEARNED_SELECTION", "CASFORMER_v0_3_META_LOGIC_WIP",
            "CAS_CJT_TRANSFORMER_v0_2", "CASFORMER_v0_1")


def build(output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError("NEW_OUTPUT_INSIDE_PILOT_REQUIRED")
    repo = Path(subprocess.check_output(["git","rev-parse","--show-toplevel"],cwd=ROOT,text=True).strip())
    head = subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    prefix = ROOT.parent.relative_to(repo).as_posix() + "/"
    source_paths = [prefix + name for name in PACKAGES]
    tracked_changes = subprocess.check_output(["git","diff","--name-only","HEAD","--",*source_paths],cwd=repo,text=True)
    if tracked_changes.strip():
        raise ValueError("TRACKED_SOURCE_CHANGES_MUST_BE_COMMITTED_FIRST")
    raw_archive = subprocess.check_output(["git","-c","core.autocrlf=false","archive",
                                          "--format=zip",head,"--",*source_paths],cwd=repo)
    members = {}
    with zipfile.ZipFile(io.BytesIO(raw_archive)) as source:
        for info in source.infolist():
            if info.is_dir():
                continue
            if not info.filename.startswith(prefix):
                raise ValueError("UNEXPECTED_GIT_ARCHIVE_PATH")
            relative = "research/" + info.filename[len(prefix):]
            members[relative] = source.read(info)
    pilot = "research/CAS_META_1_LEARNED_SELECTION"
    required = [pilot + "/cas_meta1/train.py", pilot + "/data/dataset_manifest.json",
                pilot + "/BASELINE_MANIFEST.json"]
    if any(name not in members for name in required):
        raise ValueError("PILOT_NOT_PRESENT_IN_PINNED_COMMIT")
    baseline = json.loads(members[pilot + "/BASELINE_MANIFEST.json"])
    for item in baseline["files"]:
        path = "research/" + item["path"]
        if sha256(members[path]).hexdigest() != item["sha256"]:
            raise ValueError("GIT_BASELINE_BYTES_DIFFER:" + path)
    if sum(map(len, members.values())) > 512 * 1024 * 1024:
        raise ValueError("ARCHIVE_EXPANDED_SIZE_CEILING")
    dist = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
    manifest = {
        "schema_version": 1, "source_sha": head, "baseline_sha": baseline["baseline_sha"],
        "pilot_dir": pilot, "data_dir": pilot + "/data",
        "dependency_lock": pilot + "/requirements-gpu.txt",
        "dependency_scope": "Pinned direct requirements; full remote resolved environment must be receipted.",
        "wheel_paths": [dist + "casformer_reference-0.1.0-py3-none-any.whl",
                        dist + "cas_neural_cjt-0.2.0-py3-none-any.whl"],
        "files_sha256": {name: sha256(raw).hexdigest() for name, raw in sorted(members.items())},
        "neural_execution_performed_during_packaging": False,
    }
    members["launch_manifest.json"] = (json.dumps(manifest,sort_keys=True,indent=2)+"\n").encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info,raw)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("ARCHIVE_CRC_FAILURE")
        for name, expected in manifest["files_sha256"].items():
            if sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("ARCHIVE_READBACK_HASH_FAILURE")
    return {"status":"CAS_META_1_PINNED_LAUNCH_PACKAGE_BUILT_GPU_NOT_RUN",
            "source_sha":head,"baseline_sha":baseline["baseline_sha"],
            "archive":str(output),"archive_sha256":sha256(output.read_bytes()).hexdigest(),
            "archive_bytes":output.stat().st_size,"files":len(members),
            "protected_baseline_files":len(baseline["files"]),
            "launch_manifest":manifest}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    receipt = build(args.output)
    receipt_path = args.output.with_suffix(".receipt.json")
    if receipt_path.exists():
        raise ValueError("PACKAGE_RECEIPT_ALREADY_EXISTS")
    receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in receipt.items() if k!="launch_manifest"},indent=2))
