"""Pure saved-repair source packaging. Building a ZIP does not authorize a run."""
from hashlib import sha256
import importlib.util
import io
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
PILOT = "research/CAS_META_2_COMPOSITION/"
MANIFEST_NAME = "saved_repair_source_manifest.json"
SCHEMA = "cas-meta2-saved-repair-source-package/8"
EXPERIMENT = {"profile": "saved_native_repair_v8", "entrypoint": "cas_meta2.saved_repair_gpu_v8"}
HELPER_SHA = "9925514d1d017cd6b247f3db634a276cc3b4b7ce69cfc858758b32e8e66d4bf7"
BASE_SHA = "d93a39f3a264c23f27ac7dcdd2779eca665150a6bd739820651e953958e8f7d3"
BASE_BYTES = 8086367
BASE_SOURCE = "b61b011c3d53ae49a1f7f988397df632e95e82a6"
BASE_MANIFEST = "a19590941a53a7c3aa0a343501a7330ea5f89e56f10454ad82603eb4c6d0b69d"
DATA_PATH = "data/prior_failure.zip"
DATA_SHA = "39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f"
DATA_BYTES = 893323
ADDITIONS = ("cas_meta2/saved_repair_v8.py", "cas_meta2/saved_repair_gpu_v8.py", "aws/saved_repair_package_v8.py")
MEMBER_COUNT = 644


def _helper():
    path = Path(__file__).with_name("child_qualification_package_v8.py")
    if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (path, *path.parents)):
        raise ValueError("SAVED_REPAIR_PACKAGE_HELPER_LINK")
    if not path.is_file() or path.stat().st_size > 1024**2 or sha256(path.read_bytes()).hexdigest() != HELPER_SHA:
        raise ValueError("SAVED_REPAIR_PACKAGE_HELPER_CHANGED")
    spec = importlib.util.spec_from_file_location("saved_repair_private_pure_package", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


h = _helper()
require, digest, canonical, decode = h.require, h.digest, h.canonical, h.decode
read_file, no_links, checked_names, zip_members = h.read_file, h.no_links, h.checked_names, h.zip_members


def base_identity(members):
    require(len(members) == 639, "SAVED_REPAIR_BASE_MEMBER_COUNT")
    base = h.validate_members(members, source_sha=BASE_SOURCE, manifest_sha256=BASE_MANIFEST)
    return {"source_sha": BASE_SOURCE, "archive_sha256": BASE_SHA, "archive_bytes": BASE_BYTES,
        "manifest_sha256": BASE_MANIFEST, "root_manifest": h.MANIFEST_NAME, "member_count": 639,
        "package_layout": base["base"]["package_layout"]}


def manifest_for(members, source_sha):
    require(type(source_sha) is str and re.fullmatch("[a-f0-9]{40}", source_sha), "SAVED_REPAIR_COMMIT_REQUIRED")
    extras = {PILOT + n for n in ADDITIONS} | {DATA_PATH}
    require(extras <= set(members), "SAVED_REPAIR_ADDITIONS_REQUIRED")
    base = base_identity({n: raw for n, raw in members.items() if n not in extras})
    require(len(members[DATA_PATH]) == DATA_BYTES and digest(members[DATA_PATH]) == DATA_SHA,
            "SAVED_REPAIR_DATA_BYTES_CHANGED")
    return {"schema": SCHEMA, "root_manifest": MANIFEST_NAME, "source_sha": source_sha,
        "experiment": EXPERIMENT, "base": base, "additions": sorted(PILOT + n for n in ADDITIONS),
        "data": {"path": DATA_PATH, "sha256": DATA_SHA, "bytes": DATA_BYTES,
                 "original_job": "cas-meta2-20260906155525-195f5ad8", "role": "inert_prior_failure_archive"},
        "files_sha256": {n: digest(raw) for n, raw in sorted(members.items())},
        "files_bytes": {n: len(raw) for n, raw in sorted(members.items())},
        "launch_enabled": False, "training": False, "native_execution": False, "reservation_created": False,
        "outer_caller_restored": False, "boundary": "Source and inert prior evidence only; not permission to execute or proof of repair."}


def validate_members(members, *, source_sha, manifest_sha256):
    require(len(members) == MEMBER_COUNT, "SAVED_REPAIR_PACKAGE_MEMBER_COUNT")
    checked_names(members)
    raw = members.get(MANIFEST_NAME, b"")
    require(digest(raw) == manifest_sha256, "SAVED_REPAIR_MANIFEST_HASH")
    document = decode(raw)
    require(document == manifest_for({n: v for n, v in members.items() if n != MANIFEST_NAME}, source_sha),
            "SAVED_REPAIR_SOURCE_CLOSURE_CHANGED")
    return document


def inspect_archive(path, *, expected_sha256, expected_source_sha, expected_manifest_sha256):
    raw = read_file(path, 16 * 1024**2)
    require(digest(raw) == expected_sha256, "SAVED_REPAIR_ARCHIVE_HASH")
    return validate_members(zip_members(raw), source_sha=expected_source_sha, manifest_sha256=expected_manifest_sha256)


def verify_extracted(package, manifest, *, imported_paths=()):
    package = no_links(package)
    mapping, sizes = manifest["files_sha256"], manifest["files_bytes"]
    checked_names(mapping)
    require(set(mapping) == set(sizes) and len(mapping) == MEMBER_COUNT - 1
            and all(type(n) is int and 0 <= n <= 128 * 1024**2 for n in sizes.values())
            and sum(sizes.values()) <= 128 * 1024**2, "SAVED_REPAIR_EXTRACTED_BOUND")
    members = {n: read_file(package / n, sizes[n]) for n in mapping}
    members[MANIFEST_NAME] = read_file(package / MANIFEST_NAME)
    require(validate_members(members, source_sha=manifest["source_sha"],
            manifest_sha256=digest(canonical(manifest))) == manifest, "SAVED_REPAIR_EXTRACTED_CHANGED")
    for path in imported_paths:
        path = no_links(path)
        require(path.is_relative_to(package) and path.relative_to(package).as_posix() in members,
                "SAVED_REPAIR_IMPORT_OUTSIDE_PACKAGE")
    return {"source_sha": manifest["source_sha"], "files_verified": len(members),
            "manifest_sha256": digest(canonical(manifest))}


def committed_additions(source_sha):
    require(type(source_sha) is str and re.fullmatch("[a-f0-9]{40}", source_sha), "SAVED_REPAIR_COMMIT_REQUIRED")
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, timeout=60)
    require(git("rev-parse", source_sha + "^{commit}").decode().strip() == source_sha, "SAVED_REPAIR_EXACT_COMMIT")
    repo = Path(git("rev-parse", "--show-toplevel").decode().strip())
    files = {}
    for relative in ADDITIONS:
        path = no_links(ROOT / relative)
        raw = read_file(path, 1024**2)
        require(raw == git("cat-file", "blob", source_sha + ":" + path.relative_to(repo).as_posix()),
                "SAVED_REPAIR_UNCOMMITTED_SOURCE:" + relative)
        files[PILOT + relative] = raw
    return files


def build_package(base_archive, evidence_archive, output, *, source_sha):
    output = no_links(output)
    require(not output.exists() and output.parent.is_dir() and output.is_relative_to((ROOT / "records").absolute())
            and output != ROOT / "records", "SAVED_REPAIR_NEW_OUTPUT_REQUIRED")
    base_raw = read_file(base_archive, 16 * 1024**2)
    require(len(base_raw) == BASE_BYTES and digest(base_raw) == BASE_SHA, "SAVED_REPAIR_IMMUTABLE_BASE_CHANGED")
    data_raw = read_file(evidence_archive, 1024**2)
    require(len(data_raw) == DATA_BYTES and digest(data_raw) == DATA_SHA, "SAVED_REPAIR_DATA_BYTES_CHANGED")
    base, added = zip_members(base_raw), committed_additions(source_sha)
    checked_names([*base, *added, DATA_PATH, MANIFEST_NAME])
    members = {**base, **added, DATA_PATH: data_raw}
    manifest = manifest_for(members, source_sha)
    members[MANIFEST_NAME] = canonical(manifest)
    require(sum(map(len, members.values())) <= 128 * 1024**2, "SAVED_REPAIR_EXPANDED_BOUND")
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED, compresslevel=6) as zipped:
        for name, raw in sorted(members.items()):
            info = ZipInfo(name, date_time=(2026, 9, 6, 0, 0, 0))
            info.compress_type, info.external_attr = ZIP_DEFLATED, 0o100644 << 16
            zipped.writestr(info, raw)
    raw = buffer.getvalue()
    require(len(raw) <= 16 * 1024**2 and zip_members(raw) == members, "SAVED_REPAIR_PACKAGE_READBACK")
    validate_members(members, source_sha=source_sha, manifest_sha256=digest(canonical(manifest)))
    require(committed_additions(source_sha) == added and read_file(base_archive) == base_raw
            and read_file(evidence_archive) == data_raw, "SAVED_REPAIR_INPUT_CHANGED_DURING_PACKAGE")
    output.mkdir()
    with (output / "source.zip").open("xb") as stream:
        stream.write(raw)
    require(read_file(output / "source.zip", 16 * 1024**2) == raw, "SAVED_REPAIR_PERSISTED_ARCHIVE_CHANGED")
    receipt = {"schema": "cas-meta2-saved-repair-package-receipt/8", "status": "SOURCE_ONLY_NO_LAUNCH",
        "archive": str(output / "source.zip"), "archive_sha256": digest(raw), "archive_bytes": len(raw),
        "source_sha": source_sha, "manifest_sha256": digest(canonical(manifest)),
        "member_count": len(members), "manifest": manifest}
    with (output / "receipt.json").open("xb") as stream:
        stream.write(canonical(receipt))
    return receipt


build = build_package
