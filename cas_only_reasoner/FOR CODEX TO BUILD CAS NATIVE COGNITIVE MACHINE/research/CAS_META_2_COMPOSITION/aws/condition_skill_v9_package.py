"""Source package builder for the condition-skill v9 launch. Pure until run.

Every member byte is read from Git objects at the exact source commit with
`git -c core.autocrlf=false`; the working tree is never zipped. The package
carries the v9 candidate, its frozen dataset and records, the launch plan,
requirements, and all 316 frozen baseline files across v0.1, v0.2 and META-0,
including the two immutable wheels required by the trainer. Bounds cover
member count, per-file
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
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
GIT_PREFIX = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
PILOT = "research/CAS_META_2_COMPOSITION/"
META1 = "research/CAS_META_1_LEARNED_SELECTION/"
SCHEMA = "cas-meta2-condition-skill-v9-source-package/9"
MANIFEST_NAME = "condition_skill_v9_source_manifest.json"
BASELINE_MANIFEST = META1 + "BASELINE_MANIFEST.json"
BASELINE_SHA = "0917267b1354e5d036263eaa6ba9a7197eafb776"
BASELINE_MANIFEST_SHA256 = "476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0"
BASELINE_FILES = 316
BASELINE_ROOTS = ("CASFORMER_v0_1", "CAS_CJT_TRANSFORMER_v0_2",
                  "CASFORMER_v0_3_META_LOGIC_WIP")
WHEEL_PREFIX = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
WHEELS = {
    WHEEL_PREFIX + "casformer_reference-0.1.0-py3-none-any.whl":
        "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee",
    WHEEL_PREFIX + "cas_neural_cjt-0.2.0-py3-none-any.whl":
        "6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9",
}
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
    PILOT + "cas_meta2/__init__.py",
    PILOT + "cas_meta2/condition_skill_v9/__init__.py",
    PILOT + "cas_meta2/condition_skill_v9/data.py",
    PILOT + "cas_meta2/condition_skill_v9/bundle.py",
    PILOT + "cas_meta2/condition_skill_v9/train.py",
    PILOT + "aws/__init__.py",
    PILOT + "aws/budget.py",
    PILOT + "aws/condition_skill_v9_resource_plan.py",
    PILOT + "aws/condition_skill_v9_package.py",
    PILOT + "aws/condition_skill_v9_remote.py",
    PILOT + "aws/condition_skill_v9_launch.py",
    PILOT + "requirements-gpu.txt",
    PILOT + "tools/check_condition_skill_v9.py",
    PILOT + "tools/verify_condition_skill_v9_publication_packet.py",
    PILOT + "tests/test_condition_skill_v9_data.py",
    PILOT + "tests/test_condition_skill_v9_bundle.py",
    PILOT + "tests/test_condition_skill_v9_train_boundary.py",
    PILOT + "tests/test_condition_skill_v9_packet_verifier.py",
    PILOT + "tests/test_condition_skill_v9_resource_plan.py",
    PILOT + "tests/test_condition_skill_v9_package.py",
    PILOT + "tests/test_condition_skill_v9_remote.py",
    PILOT + "tests/test_condition_skill_v9_launch.py",
    PILOT + "tests/test_budget.py",
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
    # Capture bytes in memory: no system-temp writes outside the CNCM homebase.
    process = subprocess.run(["git"] + args, cwd=str(cwd), stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=60,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if process.returncode != 0:
        message = process.stderr.decode("utf-8", "replace")[:2000]
        raise ValueError("PACKAGE_GIT_FAILED:" + message)
    return 0, process.stdout


def safe_name(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name
            and not any(ord(char) < 32 for char in name)
            and all(part not in ("", ".", "..") and not part.endswith((" ", "."))
                    for part in name.split("/")), "PACKAGE_UNSAFE_MEMBER_PATH")
    return name


def checked_names(names):
    names = [safe_name(name) for name in names]
    folded = {name.casefold() for name in names}
    require(len(names) == len(folded), "PACKAGE_MEMBER_COLLISION")
    require(not any("/".join(name.split("/")[:i]).casefold() in folded
                    for name in names for i in range(1, len(name.split("/")))),
            "PACKAGE_FILE_DIRECTORY_COLLISION")
    return names


def no_links(path):
    path = Path(path).absolute()
    require(".." not in path.parts
            and not any(part.is_symlink() or getattr(part, "is_junction", lambda: False)()
                        for part in (path, *path.parents)), "PACKAGE_PATH_LINK_OR_ESCAPE")
    return path


def file_metadata(path, maximum):
    path = no_links(path)
    metadata = path.stat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1
            and 0 <= metadata.st_size <= maximum, "PACKAGE_BOUNDED_REGULAR_FILE_REQUIRED")
    return path, metadata


def read_file(path, maximum):
    """Reject unsafe metadata before opening, then bound the actual read too."""
    path, before = file_metadata(path, maximum)
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1
                and (opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino)
                and 0 <= opened.st_size <= maximum, "PACKAGE_FILE_CHANGED_BEFORE_READ")
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    require(len(raw) <= maximum and len(raw) == opened.st_size == after.st_size
            and opened.st_mtime_ns == after.st_mtime_ns and after.st_nlink == 1,
            "PACKAGE_FILE_CHANGED_DURING_READ")
    return raw


def archive_members(raw):
    """Check every directory entry before reading any compressed member."""
    require(type(raw) is bytes and len(raw) <= MAX_ARCHIVE_BYTES, "PACKAGE_ARCHIVE_BOUND")
    with ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        require(0 < len(infos) <= MAX_MEMBER_COUNT, "PACKAGE_ARCHIVE_MEMBER_COUNT_BOUND")
        checked_names([info.orig_filename for info in infos])
        require(all(info.orig_filename == info.filename for info in infos),
                "PACKAGE_ARCHIVE_NORMALIZED_MEMBER_NAME")
        require(all(not info.is_dir() and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
                    and not info.flag_bits & 1 for info in infos),
                "PACKAGE_ARCHIVE_NONREGULAR_OR_ENCRYPTED_MEMBER")
        require(all(type(info.file_size) is int and 0 <= info.file_size <= MAX_MEMBER_BYTES
                    for info in infos), "PACKAGE_ARCHIVE_MEMBER_SIZE_BOUND")
        require(sum(info.file_size for info in infos) <= MAX_EXPANDED_BYTES,
                "PACKAGE_ARCHIVE_EXPANDED_BOUND")
        members = {}
        for info in infos:
            raw_member = archive.read(info)
            require(len(raw_member) == info.file_size, "PACKAGE_ARCHIVE_MEMBER_SIZE_CHANGED")
            members[info.filename] = raw_member
    return members


def git_key(path):
    """Archive paths are homebase-relative; Git object keys are repository-relative."""
    path = safe_name(path)
    require(path.startswith("research/"), "PACKAGE_GIT_MEMBER_SCOPE")
    return GIT_PREFIX + path


def git_bytes(root, commit, path):
    code, raw = _run_git(["-c", "core.autocrlf=false", "show", commit + ":" + git_key(path)], root)
    require(code == 0, "PACKAGE_GIT_SHOW_FAILED:" + path)
    return raw


def git_tree_paths(root, commit, directory):
    code, raw = _run_git(["-c", "core.autocrlf=false", "ls-tree", "-rz", "--full-tree",
                          commit, "--", git_key(directory)], root)
    require(code == 0, "PACKAGE_GIT_LS_TREE_FAILED:" + directory)
    paths = []
    for record in raw.decode("utf-8").split("\0"):
        if not record:
            continue
        metadata, name = record.split("\t", 1)
        mode, kind, _ = metadata.split(" ", 2)
        require(mode in ("100644", "100755") and kind == "blob", "PACKAGE_GIT_REGULAR_FILE_REQUIRED")
        require(name.startswith(GIT_PREFIX + directory + "/"), "PACKAGE_GIT_TREE_SCOPE")
        paths.append(name.removeprefix(GIT_PREFIX))
    require(paths, "PACKAGE_GIT_SOURCE_DIRECTORY_EMPTY:" + directory)
    return checked_names(paths)


def git_blob(root, commit, path):
    code, raw = _run_git(["-c", "core.autocrlf=false", "rev-parse", commit + ":" + git_key(path)], root)
    require(code == 0, "PACKAGE_GIT_REV_PARSE_FAILED:" + path)
    return raw.strip()


def baseline_records(raw):
    require(digest(raw) == BASELINE_MANIFEST_SHA256, "PACKAGE_BASELINE_MANIFEST_CHANGED")
    document = json.loads(raw.decode("utf-8"))
    require(document.get("schema") == "cas-meta1.protected-baseline/1"
            and document.get("baseline_sha") == BASELINE_SHA
            and document.get("path_base") == "sibling research directory"
            and type(document.get("files")) is list
            and len(document["files"]) == BASELINE_FILES, "PACKAGE_BASELINE_MANIFEST_SHAPE")
    records = {}
    for item in document["files"]:
        require(type(item) is dict and set(item) == {"path", "sha256"}
                and type(item["path"]) is str
                and item["path"].split("/", 1)[0] in BASELINE_ROOTS,
                "PACKAGE_BASELINE_PATH")
        name = safe_name("research/" + item["path"])
        require(name not in records and type(item["sha256"]) is str
                and re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) is not None,
                "PACKAGE_BASELINE_RECORD")
        records[name] = item["sha256"]
    checked_names(records)
    return records


def baseline_identity(members):
    require(BASELINE_MANIFEST in members, "PACKAGE_BASELINE_MANIFEST_MISSING")
    records = baseline_records(members[BASELINE_MANIFEST])
    for name, expected in records.items():
        require(name in members and digest(members[name]) == expected,
                "PACKAGE_BASELINE_BYTES_CHANGED:" + name)
    for name, expected in WHEELS.items():
        require(name in records and name in members and digest(members[name]) == expected,
                "PACKAGE_FROZEN_WHEEL_CHANGED:" + name)
    return {"path": BASELINE_MANIFEST, "baseline_sha": BASELINE_SHA,
            "manifest_sha256": BASELINE_MANIFEST_SHA256, "files_verified": len(records)}


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
    baseline = git_bytes_fn(root, commit, BASELINE_MANIFEST)
    names.update(baseline_records(baseline))
    checked_names(names)
    members = {}
    for name in sorted(names):
        raw = git_bytes_fn(root, commit, name)
        require(len(raw) <= MAX_MEMBER_BYTES, "PACKAGE_MEMBER_TOO_LARGE:" + name)
        members[name] = raw
    require(members, "PACKAGE_EMPTY_MEMBERS")
    require(len(members) <= MAX_MEMBER_COUNT, "PACKAGE_MEMBER_COUNT_BOUND")
    require(sum(map(len, members.values())) <= MAX_EXPANDED_BYTES, "PACKAGE_EXPANDED_BOUND")
    baseline_identity(members)
    return members


def manifest_for(members, source_sha, baseline_sha):
    require(baseline_sha == BASELINE_SHA, "PACKAGE_BASELINE_SHA_CHANGED")
    baseline = baseline_identity(members)
    return {
        "schema": SCHEMA,
        "source_sha": source_sha,
        "root_manifest": MANIFEST_NAME,
        "experiment": EXPERIMENT,
        "git_path_prefix": GIT_PREFIX,
        "baseline_manifest": baseline,
        "package_layout": {"pilot_dir": PILOT.rstrip("/"), "meta1_dir": META1.rstrip("/"),
                           "meta_runtime_dir": "research/CASFORMER_v0_3_META_LOGIC_WIP",
                           "dependency_lock": PILOT + "requirements-gpu.txt",
                           "wheel_paths": list(WHEELS)},
        "wheels": {name: {"sha256": expected, "bytes": len(members[name])}
                   for name, expected in WHEELS.items()},
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
    require(len(members) <= MAX_MEMBER_COUNT and all(type(raw) is bytes and len(raw) <= MAX_MEMBER_BYTES
                                                   for raw in members.values())
            and sum(map(len, members.values())) <= MAX_EXPANDED_BYTES,
            "PACKAGE_MEMBERS_BOUND")
    checked_names(members)
    raw = members.get(MANIFEST_NAME, b"")
    require(digest(raw) == manifest_sha256, "PACKAGE_ROOT_MANIFEST_HASH")
    document = json.loads(raw.decode("utf-8"))
    require(type(document.get("source_sha")) is str
            and re.fullmatch(r"[a-f0-9]{40}", document["source_sha"]) is not None,
            "PACKAGE_MANIFEST_SOURCE_SHA")
    require(document["source_sha"] == source_sha, "PACKAGE_SOURCE_SHA_MISMATCH")
    content = {name: value for name, value in members.items() if name != MANIFEST_NAME}
    require(set(EXPLICIT_FILES).issubset(content), "PACKAGE_EXPLICIT_MEMBER_MISSING")
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
    readback = archive_members(raw)
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
    raw = read_file(path, MAX_ARCHIVE_BYTES)
    require(digest(raw) == expected_sha256, "PACKAGE_ARCHIVE_HASH")
    members = archive_members(raw)
    return validate_members(members, source_sha=expected_source_sha,
                            manifest_sha256=expected_manifest_sha256)


def verify_extracted(package, manifest, *, imported_paths=()):
    """Rehash every declared member against the extracted directory."""
    package = no_links(package)
    require(package.is_dir(), "PACKAGE_EXTRACTED_DIRECTORY_REQUIRED")
    require(type(manifest) is dict and type(manifest.get("files_bytes")) is dict
            and type(manifest.get("files_sha256")) is dict, "PACKAGE_EXTRACTED_MANIFEST_SHAPE")
    sizes = manifest["files_bytes"]
    checked_names([*sizes, MANIFEST_NAME])
    require(set(sizes) == set(manifest["files_sha256"])
            and manifest.get("members") == sorted(sizes)
            and type(manifest.get("member_count")) is int
            and 0 < manifest["member_count"] == len(sizes) + 1 <= MAX_MEMBER_COUNT
            and all(type(value) is int and 0 <= value <= MAX_MEMBER_BYTES for value in sizes.values())
            and all(type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value)
                    for value in manifest["files_sha256"].values())
            and sum(sizes.values()) <= MAX_EXPANDED_BYTES, "PACKAGE_EXTRACTED_BOUND")
    for name in imported_paths:
        require(type(name) is str and safe_name(name) in sizes, "PACKAGE_IMPORT_OUTSIDE_PACKAGE:" + str(name))
    resolved_root = package.resolve(strict=True)
    paths = {}
    for name in (*sizes, MANIFEST_NAME):
        path = no_links(package / name)
        require(path.resolve(strict=True).is_relative_to(resolved_root), "PACKAGE_EXTRACTED_PATH_ESCAPE")
        path, metadata = file_metadata(path, MAX_MEMBER_BYTES)
        require(name == MANIFEST_NAME or metadata.st_size == sizes[name], "PACKAGE_EXTRACTED_SIZE:" + name)
        paths[name] = path
    members = {}
    for name, size in sizes.items():
        raw = read_file(paths[name], size)
        require(digest(raw) == manifest["files_sha256"][name], "PACKAGE_EXTRACTED_HASH:" + name)
        members[name] = raw
    members[MANIFEST_NAME] = read_file(paths[MANIFEST_NAME], MAX_MEMBER_BYTES)
    require(validate_members(members, source_sha=manifest["source_sha"],
                             manifest_sha256=digest(members[MANIFEST_NAME])) == manifest,
            "PACKAGE_EXTRACTED_MANIFEST_CHANGED")
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
