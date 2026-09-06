"""Offline, additive B/R source packaging. No providers, models, or reservations."""
import argparse
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import stat
import subprocess
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
PILOT = "research/CAS_META_2_COMPOSITION/"
SCHEMA = "cas-meta2-br-source-package/8"
MANIFEST_NAME = "br_source_manifest.json"
BASE_SOURCE_SHA = "13f424981d7434b1a92815d1ad5759d543bbd3be"
BASE_ARCHIVE_SHA256 = "c1e784440b408a81d28efd00444fe69680972b9ef6ce14b5c298598dc6e83be1"
BASE_ARCHIVE_BYTES = 7952045
BASE_MEMBER_COUNT = 616
BASE_MANIFEST_SHA256 = "10f3283e5dcb3045dac2131e021d3ca383c35ae8b34c9e439e7fc82ff58cdd9c"
BASELINE_SHA = "0917267b1354e5d036263eaa6ba9a7197eafb776"
BASELINE_MANIFEST = "research/CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json"
BASELINE_MANIFEST_SHA256 = "476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0"
BASELINE_FILES = 316
MAX_ARCHIVE_BYTES = 16 * 1024**2
MAX_EXPANDED_BYTES = 128 * 1024**2
MAX_ADDITION_BYTES = 4 * 1024**2
WHEEL_PREFIX = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
WHEELS = (WHEEL_PREFIX + "casformer_reference-0.1.0-py3-none-any.whl",
          WHEEL_PREFIX + "cas_neural_cjt-0.2.0-py3-none-any.whl")
ADDITIONS = (
    "cas_meta2/br_construction_v8.py", "cas_meta2/br_witness_v8.py",
    "cas_meta2/br_snapshot_v8.py", "cas_meta2/child_scaffold_v8.py",
    "tests/test_br_construction_v8.py", "tests/test_br_witness_v8.py",
    "tests/test_br_snapshot_v8.py", "tests/test_br_snapshot_capture_v8.py",
    "tests/test_child_scaffold_v8.py", "aws/br_package_v8.py",
    "tests/test_br_package_v8.py", "tools/check_br_snapshot_v8.py",
    "tools/check_child_call_preparation_v8.py",
)


class PackageRefused(ValueError):
    pass


def require(value, reason):
    if not value:
        raise PackageRefused(reason)


def digest(raw):
    return sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decode(raw):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, "BR_DUPLICATE_JSON_KEY")
            out[key] = value
        return out
    try:
        return json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda _: require(False, "BR_NONFINITE_JSON"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise PackageRefused("BR_INVALID_JSON") from error


def safe_name(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name
            and not any(ord(c) < 32 for c in name)
            and all(p not in ("", ".", "..") and not p.endswith((" ", "."))
                    for p in name.split("/")), "BR_UNSAFE_MEMBER_PATH")
    return name


def checked_names(names):
    names = [safe_name(n) for n in names]
    lowered = {n.casefold() for n in names}
    require(len(names) == len(lowered), "BR_MEMBER_COLLISION")
    require(not any("/".join(n.split("/")[:i]).casefold() in lowered
                    for n in names for i in range(1, len(n.split("/")))), "BR_FILE_DIRECTORY_COLLISION")
    return names


def no_links(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "BR_SOURCE_OR_OUTPUT_LINK")
    return path


def read_file(path, maximum=MAX_ARCHIVE_BYTES):
    path = no_links(path)
    metadata = path.stat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1
            and metadata.st_size <= maximum, "BR_BOUNDED_REGULAR_FILE_REQUIRED")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, "BR_FILE_SIZE_LIMIT")
    return raw


def zip_members(raw):
    require(len(raw) <= MAX_ARCHIVE_BYTES, "BR_ARCHIVE_SIZE_LIMIT")
    with ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        # ZipInfo.filename can normalize Windows separators or truncate NULs.
        checked_names([i.orig_filename for i in infos])
        require(all(i.orig_filename == i.filename for i in infos), "BR_UNSAFE_MEMBER_PATH")
        require(all(not i.is_dir() and stat.S_IFMT(i.external_attr >> 16) in (0, stat.S_IFREG)
                    and not i.flag_bits & 1 for i in infos), "BR_ZIP_LINK_SPECIAL_OR_ENCRYPTED")
        require(sum(i.file_size for i in infos) <= MAX_EXPANDED_BYTES, "BR_EXPANDED_SIZE_LIMIT")
        return {i.filename: archive.read(i) for i in infos}


def base_identity(members):
    """Validate preserved base members, including accepted weights and wheel bytes."""
    require(len(members) == BASE_MEMBER_COUNT, "BR_BASE_MEMBER_COUNT")
    prefix_raw = members.get("prefix_source_manifest.json", b"")
    require(digest(prefix_raw) == BASE_MANIFEST_SHA256, "BR_BASE_MANIFEST_CHANGED")
    prefix = decode(prefix_raw)
    require(prefix.get("schema") == "cas-meta2-prefix-source-package/8"
            and prefix.get("source_sha") == BASE_SOURCE_SHA
            and prefix.get("protected_baseline_files") == BASELINE_FILES
            and prefix.get("frozen_source_files") == 603
            and prefix.get("addition_count") == 11 and prefix.get("launch_enabled") is False,
            "BR_BASE_SOURCE_IDENTITY")
    mapping = prefix["files_sha256"]
    require(set(members) == set(mapping) | {"prefix_source_manifest.json"}
            and all(digest(members[n]) == h for n, h in mapping.items()), "BR_BASE_MEMBER_CHANGED")
    baseline_raw = members[BASELINE_MANIFEST]
    require(digest(baseline_raw) == BASELINE_MANIFEST_SHA256, "BR_BASELINE_MANIFEST_CHANGED")
    baseline = decode(baseline_raw)
    require(baseline.get("baseline_sha") == BASELINE_SHA and len(baseline["files"]) == BASELINE_FILES,
            "BR_ACCEPTED_BASELINE_IDENTITY")
    baseline_names = [safe_name("research/" + item["path"]) for item in baseline["files"]]
    checked_names(baseline_names)
    require(all(digest(members[n]) == item["sha256"] for n, item in zip(baseline_names, baseline["files"])),
            "BR_ACCEPTED_BASELINE_BYTES_CHANGED")
    old = decode(members["launch_manifest.json"])
    layout = {k: old[k] for k in ("pilot_dir", "meta1_dir", "meta_runtime_dir", "dependency_lock", "wheel_paths")}
    require(layout == {"pilot_dir": PILOT.rstrip("/"), "meta1_dir": "research/CAS_META_1_LEARNED_SELECTION",
            "meta_runtime_dir": "research/CASFORMER_v0_3_META_LOGIC_WIP",
            "dependency_lock": PILOT + "requirements-gpu.txt", "wheel_paths": list(WHEELS)},
            "BR_BASE_PACKAGE_LAYOUT")
    identities = lambda names: {n: {"sha256": digest(members[n]), "bytes": len(members[n])} for n in names}
    return {"source_sha": BASE_SOURCE_SHA, "archive_sha256": BASE_ARCHIVE_SHA256,
            "archive_bytes": BASE_ARCHIVE_BYTES, "member_count": BASE_MEMBER_COUNT,
            "prefix_manifest_sha256": BASE_MANIFEST_SHA256,
            "prefix_manifest_role": "Preserved inert base metadata, not the B/R root manifest.",
            "accepted_baseline": {"source_sha": BASELINE_SHA, "manifest_path": BASELINE_MANIFEST,
                "manifest_sha256": BASELINE_MANIFEST_SHA256, "file_count": BASELINE_FILES},
            "package_layout": layout, "wheels": identities(WHEELS),
            "dependency_lock": identities([layout["dependency_lock"]])[layout["dependency_lock"]]}


def inspect_base(path):
    raw = read_file(path)
    require(len(raw) == BASE_ARCHIVE_BYTES and digest(raw) == BASE_ARCHIVE_SHA256, "BR_EXACT_FROZEN_BASE_REQUIRED")
    members = zip_members(raw)
    return members, base_identity(members)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, timeout=60)


def committed_additions(source_sha):
    require(type(source_sha) is str and re.fullmatch("[a-f0-9]{40}", source_sha), "BR_EXACT_COMMIT_REQUIRED")
    require(git("rev-parse", source_sha + "^{commit}").decode().strip() == source_sha, "BR_EXACT_COMMIT_REQUIRED")
    repo = Path(git("rev-parse", "--show-toplevel").decode().strip())
    files = {}
    for relative in ADDITIONS:
        name = safe_name(PILOT + relative)
        path = no_links(ROOT / relative)
        raw = read_file(path, MAX_ADDITION_BYTES)
        committed = git("cat-file", "blob", source_sha + ":" + path.relative_to(repo).as_posix())
        require(raw == committed, "BR_ADDITION_NOT_COMMITTED:" + relative)
        files[name] = raw
    checked_names([PILOT + n for n in ADDITIONS])
    return files


def manifest_for(members, base, source_sha):
    return {"schema": SCHEMA, "source_sha": source_sha, "root_manifest": MANIFEST_NAME,
            "base": base, "additions": sorted(PILOT + n for n in ADDITIONS),
            "files_sha256": {n: digest(v) for n, v in sorted(members.items())},
            "files_bytes": {n: len(v) for n, v in sorted(members.items())},
            "launch_enabled": False, "neural_execution": False, "native_execution": False,
            "training": False, "reservation_created": False,
            "boundary": "Source package only. Native B/R construction requires a separately bound worker permit. "
                        "No development checkpoint bundle or new training is included."}


def validate_members(members, *, source_sha, manifest_sha256):
    require(type(source_sha) is str and re.fullmatch("[a-f0-9]{40}", source_sha), "BR_EXACT_COMMIT_REQUIRED")
    raw = members.get(MANIFEST_NAME, b"")
    require(digest(raw) == manifest_sha256, "BR_ROOT_MANIFEST_CHANGED")
    manifest = decode(raw)
    content = {n: v for n, v in members.items() if n != MANIFEST_NAME}
    additions = {PILOT + n for n in ADDITIONS}
    require(additions <= set(content), "BR_ADDITIONS_MISSING")
    base_members = {n: v for n, v in content.items() if n not in additions}
    base = base_identity(base_members)
    require(manifest == manifest_for(content, base, source_sha), "BR_SOURCE_MANIFEST_CLOSURE_CHANGED")
    return manifest


def inspect_archive(path, *, expected_sha256, expected_source_sha, expected_manifest_sha256):
    raw = read_file(path)
    require(digest(raw) == expected_sha256, "BR_SOURCE_ARCHIVE_CHANGED")
    return validate_members(zip_members(raw), source_sha=expected_source_sha,
                            manifest_sha256=expected_manifest_sha256)


def verify_extracted(package, manifest, *, imported_paths=()):
    """Rehash every declared file; caller supplies actual module paths before use."""
    package = no_links(package)
    require(package.is_dir(), "BR_PACKAGE_DIRECTORY_REQUIRED")
    checked_names(manifest["files_sha256"])
    require(set(manifest["files_bytes"]) == set(manifest["files_sha256"])
            and len(manifest["files_bytes"]) == BASE_MEMBER_COUNT + len(ADDITIONS)
            and all(type(n) is int and 0 <= n <= MAX_EXPANDED_BYTES for n in manifest["files_bytes"].values())
            and sum(manifest["files_bytes"].values()) <= MAX_EXPANDED_BYTES, "BR_EXTRACTED_SIZE_LIMIT")
    members = {n: read_file(package / n, manifest["files_bytes"][n]) for n in manifest["files_sha256"]}
    members[MANIFEST_NAME] = read_file(package / MANIFEST_NAME)
    checked = validate_members(members, source_sha=manifest["source_sha"], manifest_sha256=digest(canonical(manifest)))
    require(checked == manifest, "BR_EXTRACTED_MANIFEST_CHANGED")
    for path in imported_paths:
        path = no_links(path)
        require(path.is_relative_to(package) and path.relative_to(package).as_posix() in members,
                "BR_IMPORTED_SOURCE_OUTSIDE_PACKAGE")
    return {"source_sha": manifest["source_sha"], "files_verified": len(members),
            "manifest_sha256": digest(canonical(manifest))}


def build(base_archive, output, *, source_sha):
    output = no_links(output)
    require(not output.exists() and output.parent.is_dir()
            and output.is_relative_to((ROOT / "records").absolute()) and output != ROOT / "records",
            "BR_NEW_IN_SCOPE_OUTPUT_REQUIRED")
    members, base = inspect_base(base_archive)
    additions = committed_additions(source_sha)
    checked_names([*members, *additions, MANIFEST_NAME])
    members = {**members, **additions}
    manifest = manifest_for(members, base, source_sha)
    members[MANIFEST_NAME] = canonical(manifest)
    require(sum(map(len, members.values())) <= MAX_EXPANDED_BYTES, "BR_EXPANDED_SIZE_LIMIT")
    packed = io.BytesIO()
    with ZipFile(packed, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in sorted(members.items()):
            info = ZipInfo(name, date_time=(2026, 9, 6, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    raw = packed.getvalue()
    require(len(raw) <= MAX_ARCHIVE_BYTES, "BR_ARCHIVE_SIZE_LIMIT")
    require(zip_members(raw) == members, "BR_ARCHIVE_READBACK_CHANGED")
    validate_members(members, source_sha=source_sha, manifest_sha256=digest(members[MANIFEST_NAME]))
    require(committed_additions(source_sha) == additions, "BR_ADDITIONS_CHANGED_DURING_PACKAGING")
    require(inspect_base(base_archive)[0] == {n: v for n, v in members.items()
            if n not in additions and n != MANIFEST_NAME}, "BR_BASE_CHANGED_DURING_PACKAGING")
    output.mkdir(exist_ok=False)
    target = output / "source.zip"
    with target.open("xb") as stream:
        stream.write(raw)
    require(read_file(target) == raw, "BR_STORED_ARCHIVE_CHANGED")
    receipt = {"schema": "cas-meta2-br-source-package-receipt/8", "status": "SOURCE_ONLY_NO_LAUNCH",
               "archive": str(target), "archive_sha256": digest(raw), "archive_bytes": len(raw),
               "manifest_sha256": digest(members[MANIFEST_NAME]), "member_count": len(members),
               "source_sha": source_sha, "manifest": manifest}
    with (output / "receipt.json").open("xb") as stream:
        stream.write(canonical(receipt))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-archive", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = build(args.base_archive, args.output, source_sha=args.source_sha)
    print(json.dumps({k: v for k, v in result.items() if k != "manifest"}, sort_keys=True))
