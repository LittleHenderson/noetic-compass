"""Byte-preserving offline source archive. This never reserves or launches AWS."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PILOT = "research/CAS_META_2_COMPOSITION/"
V7_SHA = "42f9164754312f12850d9b8789c062fa7fb8069f"
V7_ARCHIVE_SHA256 = "f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9"
ADDITIONS = (
    "cas_meta2/diagnostic_v8/__init__.py", "cas_meta2/diagnostic_v8/bundle.py",
    "cas_meta2/diagnostic_v8/sites.py", "cas_meta2/diagnostic_v8/gpu.py",
    "tests/test_diagnostic_v8_bundle.py", "tests/test_diagnostic_v8_sites.py",
    "tests/test_diagnostic_v8_gpu_contract.py", "tools/check_prefix_diagnostic_v8.py",
    "tools/package_prefix_diagnostic_v8.py", "tools/replay_prefix_panel_v8.py",
    "records/child_call_v8_diagnostic_001/README.md",
)


def require(value, message):
    if not value:
        raise ValueError(message)


def regular(path):
    path = Path(path).absolute()
    require(path.is_file() and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                                      for p in (path, *path.parents)), "V8_SOURCE_FILE_MISSING_OR_LINK")
    return path


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def safe_name(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name
            and not name.startswith("/") and all(p not in ("", ".", "..") for p in name.split("/")),
            "V8_SOURCE_MEMBER_PATH_INVALID")
    return name


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def build(original, output):
    original = regular(original)
    require(sha256(original.read_bytes()).hexdigest() == V7_ARCHIVE_SHA256, "V8_FROZEN_ARCHIVE_CHANGED")
    repo = Path(git("rev-parse", "--show-toplevel").decode().strip())
    source_sha = git("rev-parse", "HEAD").decode().strip()
    output = Path(output).absolute()
    require(not output.exists() and output.resolve().is_relative_to((ROOT/"records/child_call_v8_diagnostic_001").resolve())
            and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (output, *output.parents)),
            "V8_NEW_IN_SCOPE_PACKAGE_DIRECTORY_REQUIRED")
    with zipfile.ZipFile(original) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) == len({n.casefold() for n in names}) == 604,
                "V8_FROZEN_ARCHIVE_COVERAGE_CHANGED")
        for name in names:
            safe_name(name)
        prior = json.loads(archive.read("launch_manifest.json"))
        frozen = prior["files_sha256"]
        require(prior["source_sha"] == V7_SHA and prior["protected_baseline_files"] == 316
                and len(frozen) == 603 and set(names) == set(frozen) | {"launch_manifest.json"},
                "V8_FROZEN_SOURCE_CLOSURE_CHANGED")
        members = {name: archive.read(name) for name in names}
    requests = []
    for name, expected in frozen.items():
        path = regular(ROOT.parents[1] / name)
        raw = members[name]
        require(sha256(raw).hexdigest() == expected and path.read_bytes() == raw, "V8_FROZEN_SOURCE_CHANGED:" + name)
        requests.append((V7_SHA + ":" + path.relative_to(repo).as_posix(), raw))
    for relative in ADDITIONS:
        path = regular(ROOT / relative)
        name = PILOT + relative
        require(name not in members, "V8_ADDITION_OVERWRITES_FROZEN_SOURCE")
        members[name] = path.read_bytes()
        requests.append((source_sha + ":" + path.relative_to(repo).as_posix(), members[name]))
    response = subprocess.run(["git", "cat-file", "--batch"], cwd=ROOT,
                              input=("\n".join(ref for ref, _ in requests) + "\n").encode(),
                              check=True, capture_output=True).stdout
    offset = 0
    for ref, raw in requests:
        end = response.index(b"\n", offset)
        header = response[offset:end].split()
        require(len(header) == 3 and header[1] == b"blob", "V8_COMMITTED_SOURCE_REQUIRED:" + ref)
        count = int(header[2])
        offset = end + 1
        require(response[offset:offset+count] == raw, "V8_WORKTREE_DIFFERS_FROM_PINNED_COMMIT:" + ref)
        offset += count
        require(response[offset:offset+1] == b"\n", "V8_GIT_BATCH_FORMAT")
        offset += 1
    require(offset == len(response), "V8_GIT_BATCH_EXTRA_DATA")
    manifest = {"schema": "cas-meta2-prefix-source-package/8", "source_sha": source_sha,
                "frozen_v7_source_sha": V7_SHA, "frozen_v7_archive_sha256": V7_ARCHIVE_SHA256,
                "frozen_source_files": 603, "protected_baseline_files": 316,
                "addition_count": len(ADDITIONS), "launch_enabled": False,
                "files_sha256": {name: sha256(raw).hexdigest() for name, raw in sorted(members.items())},
                "boundary": "Source package only; no model execution, paid reservation or launch. Development bundle is separate."}
    members["prefix_source_manifest.json"] = canonical(manifest)
    output.mkdir(parents=True, exist_ok=False)
    target = output / "source.zip"
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    with zipfile.ZipFile(target) as archive:
        require(set(archive.namelist()) == set(members), "V8_ARCHIVE_COVERAGE_MISMATCH")
        require(all(archive.read(name) == raw for name, raw in members.items()), "V8_ARCHIVE_BYTES_MISMATCH")
    receipt = {**manifest, "archive_sha256": sha256(target.read_bytes()).hexdigest(),
               "archive_bytes": target.stat().st_size, "member_count": len(members),
               "prefix_manifest_sha256": sha256(members["prefix_source_manifest.json"]).hexdigest()}
    with (output/"receipt.json").open("xb") as stream:
        stream.write(canonical(receipt))
    print(json.dumps({"source_sha": source_sha, "archive": str(target),
                      "archive_sha256": receipt["archive_sha256"], "members": len(members)}))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v7-source-archive", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    build(args.v7_source_archive, args.output)
