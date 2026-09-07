"""Source package builder for the condition-skill v9 launch. Pure until run.

Every member byte is read from Git objects at the exact source commit with
`git -c core.autocrlf=false`; the working tree is never zipped. The package
carries the v9 candidate, its frozen dataset and records, the launch plan,
requirements, and the frozen baseline closure (CASFORMER v0.1 sources and the
META-1 baseline manifest files). Bounds are enforced on member count, per-file
bytes, expanded bytes, and archive bytes.

Building a package does not authorize a run. The manifest stays
`launch_enabled:false`, `reservation_created:false`, and the launcher must
bind a separate worker permit for this exact manifest before any execution.
"""
from __future__ import annotations

import argparse
import io
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
PILOT = "research/CAS_META_2_COMPOSITION/"
META1 = "research/CAS_META_1_LEARNED_SELECTION/"
SCHEMA = "cas-meta2-condition-skill-v9-source-package/9"
MANIFEST_NAME = "condition_skill_v9_source_manifest.json"
BASELINE_MANIFEST = META1 + "BASELINE_MANIFEST.json"
EXPERIMENT = {"profile": "condition_skill_v9", "entrypoint": "cas_meta2.condition_skill_v9.train"}
MAX_MEMBER_BYTES = 4 * 1024**2
MAX_MEMBER_COUNT = 2000
MAX_EXPANDED_BYTES = 96 * 1024**2
MAX_ARCHIVE_BYTES = 24 * 1024**2

SOURCE_DIRS = (
    "research/CASFORMER_v0_1/casformer",
    "research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt",
    META1 + "cas_meta1",
)

EXPLICIT_FILES = (
    PILOT + "cas_meta2/condition_skill_v9/__init__.py",
    PILOT + "cas_meta2/condition_skill_v9/data.py",
    PILOT + "cas_meta2/condition_skill_v9/bundle.py",
    PILOT + "cas_meta2/condition_skill_v9/train.py",
    PILOT + "aws/condition_skill_v9_resource_plan.py",
    PILOT + "aws/condition_skill_v9_package.py",
    PILOT + "requirements-gpu.txt",
    PILOT + "tools/check_condition_skill_v9.py",
    PILOT + "tools/verify_condition_skill_v9_publication_packet.py",
    PILOT + "tests/test_condition_skill_v9_data.py",
    PILOT + "tests/test_condition_skill_v9_bundle.py",
    PILOT + "tests/test_condition_skill_v9_train_boundary.py",
    PILOT + "tests/test_condition_skill_v9_packet_verifier.py",
    PILOT + "tests/test_condition_skill_v9_resource_plan.py",
    PILOT + "records/condition_skill_v9_001/PROTOCOL.md",
    PILOT + "records/condition_skill_v9_001/OWNER_256_RECORD_RULING.md",
    PILOT + "records/condition_skill_v9_001/OWNER_PHASE_APPROVAL.json",
    PILOT + "records/condition_skill_v9_001/OWNER_METRIC_AMENDMENT.json",
    PILOT + "records/condition_skill_v9_001/dataset_001/manifest.json",
    PILOT + "records/condition_skill_v9_001/dataset_001/train.json",
    PILOT + "records/condition_skill_v9_001/dataset_001/validation.json",
    PILOT + "records/condition_skill_v9_001/dataset_001/test_instances.public.json",
    PILOT + "records/condition_skill_v9_001/dataset_001/test_instances.targets.json",
    PILOT + "records/condition_skill_v9_001/dataset_001/test_direction_pair.public.json",
    PILOT + "records/condition_skill_v9_001/dataset_001/test_direction_pair.targets.json",
    BASELINE_MANIFEST,
)


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def digest(raw):
    return sha256(raw).hexdigest()


def _run_git(args, cwd):
    # File redirection only: no stdio pipes, so the sandboxed harness cannot
    # break this with an EPERM on named-pipe capture.
    handle_out, out_path = tempfile.mkstemp(prefix="cas_v9_pkg_out_")
    os.close(handle_out)
    handle_err, err_path = tempfile.mkstemp(prefix="cas_v9_pkg_err_")
    os.close(handle_err)
    try:
        with open(out_path, "wb") as out, open(err_path, "wb") as err:
            process = subprocess.run(["git"] + args, cwd=str(cwd), stdout=out, stderr=err,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if process.returncode != 0:
            message = Path(err_path).read_bytes().decode("utf-8", "replace")[:2000]
            raise ValueError("PACKAGE_GIT_FAILED:" + message)
        return 0, Path(out_path).read_bytes()
    finally:
        for path in (out_path, err_path):
            try:
                os.unlink(path)
            except OSError:
                pass


def git_bytes(root, commit, path):
    code, raw = _run_git(["-c", "core.autocrlf=false", "show", commit + ":" + path], root)
    require(code == 0, "PACKAGE_GIT_SHOW_FAILED:" + path)
    return raw


def git_tree_paths(root, commit, directory):
    code, raw = _run_git(["-c", "core.autocrlf=false", "ls-tree", "-r", "--name-only",
                          commit, "--", directory], root)
    require(code == 0, "PACKAGE_GIT_LS_TREE_FAILED:" + directory)
    return [line for line in raw.decode("utf-8").splitlines() if line]


def git_blob(root, commit, path):
    code, raw = _run_git(["-c", "core.autocrlf=false", "rev-parse", commit + ":" + path], root)
    require(code == 0, "PACKAGE_GIT_REV_PARSE_FAILED:" + path)
    return raw.strip()


def resolve_members(root, commit, *, git_bytes_fn=git_bytes, git_paths_fn=git_tree_paths):
    """Resolve the complete member set from exact Git objects at the commit.

    Members are the explicit file list, every regular file under the frozen
    source directories, and the baseline closure named by the committed
    BASELINE_MANIFEST.json. Nothing from the working tree is read.
    """
    require(type(commit) is str and re.fullmatch(r"[a-f0-9]{40}", commit) is not None,
            "PACKAGE_EXACT_COMMIT_REQUIRED")
    names = set(EXPLICIT_FILES)
    for directory in SOURCE_DIRS:
        names.update(git_paths_fn(root, commit, directory))
    baseline = json.loads(git_bytes_fn(root, commit, BASELINE_MANIFEST).decode("utf-8"))
    require(type(baseline.get("files")) is list, "PACKAGE_BASELINE_MANIFEST_SHAPE")
    for item in baseline["files"]:
        require(type(item.get("path")) is str and item["path"].startswith("CASFORMER_v0_1/"),
                "PACKAGE_BASELINE_PATH")
        names.add(META1 + item["path"])
    members = {}
    for name in sorted(names):
        raw = git_bytes_fn(root, commit, name)
        require(len(raw) <= MAX_MEMBER_BYTES, "PACKAGE_MEMBER_TOO_LARGE:" + name)
        members[name] = raw
    require(members, "PACKAGE_EMPTY_MEMBERS")
    require(len(members) <= MAX_MEMBER_COUNT, "PACKAGE_MEMBER_COUNT_BOUND")
    require(sum(map(len, members.values())) <= MAX_EXPANDED_BYTES, "PACKAGE_EXPANDED_BOUND")
    return members


def manifest_for(members, source_sha, baseline_sha):
    return {
        "schema": SCHEMA,
        "source_sha": source_sha,
        "root_manifest": MANIFEST_NAME,
        "experiment": EXPERIMENT,
        "baseline_manifest": {"path": BASELINE_MANIFEST, "baseline_sha": baseline_sha},
        "members": sorted(members),
        "files_sha256": {name: digest(raw) for name, raw in sorted(members.items())},
        "files_bytes": {name: len(raw) for name, raw in sorted(members.items())},
        "member_count": len(members) + 1,  # content members plus the root manifest
        "expanded_bytes": sum(map(len, members.values())),
        "launch_enabled": False,
        "training": True,
        "native_execution": False,
        "reservation_created": False,
        "automatic_retries": 0,
        "boundary": ("Source package only. The paid run requires a separately bound worker "
                     "permit for this exact manifest, dataset pins, and provider identity. "
                     "Private test targets are part of the frozen dataset and must stay "
                     "unread until the trainer seals its blind predictions."),
    }


def validate_members(members, *, source_sha, manifest_sha256):
    """Recompute the manifest closure over member bytes; any drift fails."""
    require(type(members) is dict and members, "PACKAGE_MEMBERS_REQUIRED")
    raw = members.get(MANIFEST_NAME, b"")
    require(digest(raw) == manifest_sha256, "PACKAGE_ROOT_MANIFEST_HASH")
    document = json.loads(raw.decode("utf-8"))
    require(type(document.get("source_sha")) is str
            and re.fullmatch(r"[a-f0-9]{40}", document["source_sha"]) is not None,
            "PACKAGE_MANIFEST_SOURCE_SHA")
    require(document["source_sha"] == source_sha, "PACKAGE_SOURCE_SHA_MISMATCH")
    content = {name: value for name, value in members.items() if name != MANIFEST_NAME}
    baseline = json.loads(content[BASELINE_MANIFEST].decode("utf-8"))
    require(document == manifest_for(content, source_sha, baseline.get("baseline_sha")),
            "PACKAGE_SOURCE_CLOSURE_CHANGED")
    return document


def build_package(output, *, source_sha, git_bytes_fn=git_bytes, git_paths_fn=git_tree_paths):
    output = Path(output).absolute()
    require(not output.exists() and output.parent.is_dir()
            and output.is_relative_to((ROOT / "records").absolute())
            and output != ROOT / "records", "PACKAGE_NEW_SCOPED_OUTPUT_REQUIRED")
    members = resolve_members(ROOT, source_sha, git_bytes_fn=git_bytes_fn,
                              git_paths_fn=git_paths_fn)
    baseline = json.loads(members[BASELINE_MANIFEST].decode("utf-8"))
    manifest = manifest_for(members, source_sha, baseline.get("baseline_sha"))
    members[MANIFEST_NAME] = canonical(manifest)
    require(sum(map(len, members.values())) <= MAX_EXPANDED_BYTES, "PACKAGE_EXPANDED_BOUND")
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED, compresslevel=6) as zipped:
        for name in sorted(members):
            info = ZipInfo(name, date_time=(2026, 9, 7, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, members[name])
    raw = buffer.getvalue()
    require(len(raw) <= MAX_ARCHIVE_BYTES, "PACKAGE_ARCHIVE_BOUND")
    readback = {}
    with ZipFile(io.BytesIO(raw)) as zipped:
        require(not any(member.endswith("/") for member in zipped.namelist()),
                "PACKAGE_ARCHIVE_HAS_DIRECTORY_ENTRIES")
        for name in zipped.namelist():
            require(name in members, "PACKAGE_ARCHIVE_UNEXPECTED_MEMBER:" + name)
            readback[name] = zipped.read(name)
    require(readback == members, "PACKAGE_ARCHIVE_READBACK")
    validate_members(members, source_sha=source_sha, manifest_sha256=digest(members[MANIFEST_NAME]))
    output.mkdir()
    with (output / "source.zip").open("xb") as stream:
        stream.write(raw)
    receipt = {"schema": "cas-meta2-condition-skill-v9-package-receipt/9",
               "status": "SOURCE_ONLY_NO_LAUNCH",
               "archive": str(output / "source.zip"),
               "archive_sha256": digest(raw), "archive_bytes": len(raw),
               "source_sha": source_sha,
               "manifest_sha256": digest(members[MANIFEST_NAME]),
               "member_count": len(members), "manifest": manifest}
    with (output / "receipt.json").open("xb") as stream:
        stream.write(canonical(receipt))
    return receipt


def inspect_archive(path, *, expected_sha256, expected_source_sha, expected_manifest_sha256):
    path = Path(path).absolute()
    require(stat.S_ISREG(path.stat().st_mode), "PACKAGE_ARCHIVE_FILE_REQUIRED")
    raw = path.read_bytes()
    require(len(raw) <= MAX_ARCHIVE_BYTES and digest(raw) == expected_sha256,
            "PACKAGE_ARCHIVE_HASH")
    members = {}
    with ZipFile(io.BytesIO(raw)) as zipped:
        for name in zipped.namelist():
            members[name] = zipped.read(name)
    return validate_members(members, source_sha=expected_source_sha,
                            manifest_sha256=expected_manifest_sha256)


def verify_extracted(package, manifest, *, imported_paths=()):
    """Rehash every declared member against the extracted directory."""
    package = Path(package).absolute()
    require(package.is_dir(), "PACKAGE_EXTRACTED_DIRECTORY_REQUIRED")
    sizes = manifest["files_bytes"]
    require(set(sizes) == set(manifest["files_sha256"])
            and manifest["member_count"] == len(sizes) + 1
            and all(type(value) is int and 0 <= value <= MAX_MEMBER_BYTES for value in sizes.values())
            and sum(sizes.values()) <= MAX_EXPANDED_BYTES, "PACKAGE_EXTRACTED_BOUND")
    members = {}
    for name, size in sizes.items():
        path = package / name
        require(path.is_file() and path.stat().st_size == size, "PACKAGE_EXTRACTED_SIZE:" + name)
        raw = path.read_bytes()
        require(digest(raw) == manifest["files_sha256"][name], "PACKAGE_EXTRACTED_HASH:" + name)
        members[name] = raw
    members[MANIFEST_NAME] = (package / MANIFEST_NAME).read_bytes()
    require(validate_members(members, source_sha=manifest["source_sha"],
                             manifest_sha256=digest(members[MANIFEST_NAME])) == manifest,
            "PACKAGE_EXTRACTED_MANIFEST_CHANGED")
    for path in imported_paths:
        require((package / path).is_relative_to(package)
                and path in members, "PACKAGE_IMPORT_OUTSIDE_PACKAGE:" + str(path))
    return {"source_sha": manifest["source_sha"], "files_verified": len(members),
            "manifest_sha256": digest(members[MANIFEST_NAME])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", help="exact 40-hex source commit")
    parser.add_argument("--output", help="fresh directory under records/")
    arguments = parser.parse_args()
    require(arguments.build and arguments.output, "PACKAGE_BUILD_ARGS_REQUIRED")
    receipt = build_package(arguments.output, source_sha=arguments.build)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
