"""Offline source package for full one-child task qualification, never training.

The byte-pinned B/R packaging helpers are loaded from the shipped sibling file.
The immutable prefix package and all thirteen B/R additions remain unchanged.
"""
import argparse
import io
from pathlib import Path
import re
import stat
import subprocess
from types import ModuleType
from hashlib import sha256
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
PILOT = "research/CAS_META_2_COMPOSITION/"
SCHEMA = "cas-meta2-child-qualification-source-package/8"
MANIFEST_NAME = "child_qualification_source_manifest.json"
HELPER_SHA256 = "23a30b7e4e3862702699e078bee953436be630f1390127f8668f519c1119b2e8"
BR_SOURCE_SHA = "d047540a635ecccdd2cfd4d96ee3b43da59f7ce7"
BR_ARCHIVE_SHA256 = "1b13fbeb96465e2122b1709b87c99cdd06860f78a2bc4bbbfa4874e96ef7658a"
BR_PRESERVED_FILES = {
    "aws/br_package_v8.py": HELPER_SHA256,
    "cas_meta2/br_construction_v8.py": "96b9fcff510d74863ce720fcc2f0c1f6f730d7ce808e59ef59bbac660d108719",
    "cas_meta2/br_snapshot_v8.py": "fe11da6ae0399d58f22093c3a13e2b5faec481d75de260af818a7b98cd0ee5d0",
    "cas_meta2/br_witness_v8.py": "5cffd02a8653dcc8c1e90a2d571ce2c3a4ed4bbfb0b90093883130c808af7c5f",
    "cas_meta2/child_scaffold_v8.py": "4ca4f80dc173d3567cd7cb32a146299c4fc9b5b8e2db797a0d6612ac5aa1570b",
    "tests/test_br_construction_v8.py": "895188e7a43ed778fe1c9060435651798de512519d3b442ce0ddd561edb4738f",
    "tests/test_br_package_v8.py": "271f211b50de9d993a21a50b87702f16bdcf821f0f734919efcba3b225b306e0",
    "tests/test_br_snapshot_capture_v8.py": "be627866d9d38fd956f41b0cc2289c8c368d726abafd6fc4864f068aaf5f4d46",
    "tests/test_br_snapshot_v8.py": "7ecd15783de57b3ba2778e17275ef8db074f207a5487842f0109a6549409b133",
    "tests/test_br_witness_v8.py": "b7907a524f7d2ffb2b9f2a8cfb0450e32168b0cbe6796da5a40d8557198fc632",
    "tests/test_child_scaffold_v8.py": "ac69f4470ce20226899346fb71aafdfcc27f04f23a5072ebf46b1698591f3d08",
    "tools/check_br_snapshot_v8.py": "4801d72d5492b6e85bf810b16e86d4a3938286ae5cd0e63fad43efb6d5b1b2f7",
    "tools/check_child_call_preparation_v8.py": "7846c3ce82a4a65893b5989ae9b4cf386c386381a0a0c421ccb9c05c87c33db1",
}
NEW_ADDITIONS = (
    "cas_meta2/child_curriculum_v8.py",
    "cas_meta2/child_qualification_v8.py",
    "cas_meta2/child_qualification_gpu_v8.py",
    "tests/test_child_curriculum_v8.py",
    "tests/test_child_qualification_v8.py",
    "tests/test_child_qualification_gpu_v8.py",
    "aws/child_qualification_package_v8.py",
    "tests/test_child_qualification_package_v8.py",
    "tools/check_child_qualification_v8.py",
)
ADDITIONS = tuple(BR_PRESERVED_FILES) + NEW_ADDITIONS
EXPERIMENT = {"entrypoint": "cas_meta2.child_qualification_gpu_v8",
              "profile": "one_child_full_task_qualification_v8"}


def helper_bytes():
    path = Path(__file__).with_name("br_package_v8.py").absolute()
    if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
           for p in (path, *path.parents)):
        raise ValueError("CHILD_QUALIFICATION_HELPER_LINK")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 1024**2:
        raise ValueError("CHILD_QUALIFICATION_HELPER_FILE")
    with path.open("rb") as stream:
        raw = stream.read(1024**2 + 1)
    if sha256(raw).hexdigest() != HELPER_SHA256:
        raise ValueError("CHILD_QUALIFICATION_HELPER_CHANGED")
    return path, raw


# Compile only the checked, shipped pure packaging helper bytes. This avoids
# importing an unbound module from site-packages or writing helper bytecode.
_helper_path, _helper_raw = helper_bytes()
helpers = ModuleType("_child_qualification_pinned_br_package_v8")
helpers.__file__ = str(_helper_path)
exec(compile(_helper_raw, str(_helper_path), "exec"), helpers.__dict__)
del _helper_raw
PackageRefused = helpers.PackageRefused
require, digest, canonical = helpers.require, helpers.digest, helpers.canonical
decode, safe_name, checked_names = helpers.decode, helpers.safe_name, helpers.checked_names
no_links, read_file, zip_members = helpers.no_links, helpers.read_file, helpers.zip_members
BASE_MEMBER_COUNT = helpers.BASE_MEMBER_COUNT
MAX_ARCHIVE_BYTES = helpers.MAX_ARCHIVE_BYTES
MAX_EXPANDED_BYTES = helpers.MAX_EXPANDED_BYTES
MAX_ADDITION_BYTES = helpers.MAX_ADDITION_BYTES


def base_identity(members):
    identity = helpers.base_identity(members)
    identity["prefix_manifest_role"] = (
        "Preserved inert base metadata, not the child-qualification root manifest.")
    return identity


def inspect_base(path):
    members, _ = helpers.inspect_base(path)
    return members, base_identity(members)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, timeout=60)


def committed_additions(source_sha):
    require(type(source_sha) is str and re.fullmatch("[a-f0-9]{40}", source_sha),
            "CHILD_QUALIFICATION_EXACT_COMMIT_REQUIRED")
    require(git("rev-parse", source_sha + "^{commit}").decode().strip() == source_sha,
            "CHILD_QUALIFICATION_EXACT_COMMIT_REQUIRED")
    repo = Path(git("rev-parse", "--show-toplevel").decode().strip())
    checked_names([PILOT + n for n in ADDITIONS])
    files = {}
    for relative in ADDITIONS:
        path = no_links(ROOT / relative)
        raw = read_file(path, MAX_ADDITION_BYTES)
        committed = git("cat-file", "blob", source_sha + ":" + path.relative_to(repo).as_posix())
        require(raw == committed, "CHILD_QUALIFICATION_ADDITION_NOT_COMMITTED:" + relative)
        if relative in BR_PRESERVED_FILES:
            require(digest(raw) == BR_PRESERVED_FILES[relative],
                    "CHILD_QUALIFICATION_PRESERVED_BR_CHANGED:" + relative)
        files[safe_name(PILOT + relative)] = raw
    return files


def manifest_for(members, base, source_sha):
    return {
        "schema": SCHEMA, "source_sha": source_sha, "root_manifest": MANIFEST_NAME,
        "base": base, "additions": sorted(PILOT + n for n in ADDITIONS),
        "preserved_br": {"source_sha": BR_SOURCE_SHA, "archive_sha256": BR_ARCHIVE_SHA256,
                         "files_sha256": {PILOT + n: h for n, h in sorted(BR_PRESERVED_FILES.items())}},
        "experiment": dict(EXPERIMENT),
        "files_sha256": {n: digest(v) for n, v in sorted(members.items())},
        "files_bytes": {n: len(v) for n, v in sorted(members.items())},
        "launch_enabled": False, "neural_execution": False, "native_execution": False,
        "training": False, "reservation_created": False,
        "old_br_launch_authorized": False,
        "boundary": "Source package only. Full one-child task qualification requires a separately "
                    "bound worker permit for this exact root manifest and experiment. Historical "
                    "launch metadata is inert. No old B/R launch, training, or checkpoint bundle is authorized.",
    }


def validate_members(members, *, source_sha, manifest_sha256):
    helper_bytes()
    require(type(source_sha) is str and re.fullmatch("[a-f0-9]{40}", source_sha),
            "CHILD_QUALIFICATION_EXACT_COMMIT_REQUIRED")
    raw = members.get(MANIFEST_NAME, b"")
    require(digest(raw) == manifest_sha256, "CHILD_QUALIFICATION_ROOT_MANIFEST_CHANGED")
    manifest = decode(raw)
    content = {n: v for n, v in members.items() if n != MANIFEST_NAME}
    additions = {PILOT + n for n in ADDITIONS}
    require(additions <= set(content), "CHILD_QUALIFICATION_ADDITIONS_MISSING")
    base = base_identity({n: v for n, v in content.items() if n not in additions})
    for relative, pin in BR_PRESERVED_FILES.items():
        require(digest(content[PILOT + relative]) == pin,
                "CHILD_QUALIFICATION_PRESERVED_BR_CHANGED:" + relative)
    require(manifest == manifest_for(content, base, source_sha),
            "CHILD_QUALIFICATION_SOURCE_MANIFEST_CLOSURE_CHANGED")
    return manifest


def inspect_archive(path, *, expected_sha256, expected_source_sha, expected_manifest_sha256):
    raw = read_file(path)
    require(digest(raw) == expected_sha256, "CHILD_QUALIFICATION_SOURCE_ARCHIVE_CHANGED")
    return validate_members(zip_members(raw), source_sha=expected_source_sha,
                            manifest_sha256=expected_manifest_sha256)


def verify_extracted(package, manifest, *, imported_paths=()):
    """Rehash every declared source member and check actual imported paths."""
    package = no_links(package)
    require(package.is_dir(), "CHILD_QUALIFICATION_PACKAGE_DIRECTORY_REQUIRED")
    checked_names(manifest["files_sha256"])
    require(set(manifest["files_bytes"]) == set(manifest["files_sha256"])
            and len(manifest["files_bytes"]) == BASE_MEMBER_COUNT + len(ADDITIONS)
            and all(type(n) is int and 0 <= n <= MAX_EXPANDED_BYTES for n in manifest["files_bytes"].values())
            and sum(manifest["files_bytes"].values()) <= MAX_EXPANDED_BYTES,
            "CHILD_QUALIFICATION_EXTRACTED_SIZE_LIMIT")
    members = {n: read_file(package / n, manifest["files_bytes"][n]) for n in manifest["files_sha256"]}
    members[MANIFEST_NAME] = read_file(package / MANIFEST_NAME)
    checked = validate_members(members, source_sha=manifest["source_sha"],
                               manifest_sha256=digest(canonical(manifest)))
    require(checked == manifest, "CHILD_QUALIFICATION_EXTRACTED_MANIFEST_CHANGED")
    for path in imported_paths:
        path = no_links(path)
        require(path.is_relative_to(package) and path.relative_to(package).as_posix() in members,
                "CHILD_QUALIFICATION_IMPORTED_SOURCE_OUTSIDE_PACKAGE")
    return {"source_sha": manifest["source_sha"], "files_verified": len(members),
            "manifest_sha256": digest(canonical(manifest))}


def build_package(base_archive, output, *, source_sha):
    helper_bytes()
    output = no_links(output)
    require(not output.exists() and output.parent.is_dir()
            and output.is_relative_to((ROOT / "records").absolute()) and output != ROOT / "records",
            "CHILD_QUALIFICATION_NEW_IN_SCOPE_OUTPUT_REQUIRED")
    members, base = inspect_base(base_archive)
    additions = committed_additions(source_sha)
    checked_names([*members, *additions, MANIFEST_NAME])
    members = {**members, **additions}
    manifest = manifest_for(members, base, source_sha)
    members[MANIFEST_NAME] = canonical(manifest)
    require(sum(map(len, members.values())) <= MAX_EXPANDED_BYTES, "CHILD_QUALIFICATION_EXPANDED_SIZE_LIMIT")
    packed = io.BytesIO()
    with ZipFile(packed, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in sorted(members.items()):
            info = ZipInfo(name, date_time=(2026, 9, 6, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    raw = packed.getvalue()
    require(len(raw) <= MAX_ARCHIVE_BYTES, "CHILD_QUALIFICATION_ARCHIVE_SIZE_LIMIT")
    require(zip_members(raw) == members, "CHILD_QUALIFICATION_ARCHIVE_READBACK_CHANGED")
    validate_members(members, source_sha=source_sha, manifest_sha256=digest(members[MANIFEST_NAME]))
    require(committed_additions(source_sha) == additions, "CHILD_QUALIFICATION_ADDITIONS_CHANGED_DURING_PACKAGING")
    require(inspect_base(base_archive)[0] == {n: v for n, v in members.items()
            if n not in additions and n != MANIFEST_NAME}, "CHILD_QUALIFICATION_BASE_CHANGED_DURING_PACKAGING")
    helper_bytes()
    output.mkdir(exist_ok=False)
    target = output / "source.zip"
    with target.open("xb") as stream:
        stream.write(raw)
    require(read_file(target) == raw, "CHILD_QUALIFICATION_STORED_ARCHIVE_CHANGED")
    receipt = {"schema": "cas-meta2-child-qualification-source-package-receipt/8",
               "status": "SOURCE_ONLY_NO_LAUNCH", "archive": str(target),
               "archive_sha256": digest(raw), "archive_bytes": len(raw),
               "manifest_sha256": digest(members[MANIFEST_NAME]), "member_count": len(members),
               "source_sha": source_sha, "manifest": manifest}
    with (output / "receipt.json").open("xb") as stream:
        stream.write(canonical(receipt))
    return receipt


# Same operation and signature as the established packager.
build = build_package


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-archive", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = build_package(args.base_archive, args.output, source_sha=args.source_sha)
    print(helpers.json.dumps({k: v for k, v in result.items() if k != "manifest"}, sort_keys=True))
