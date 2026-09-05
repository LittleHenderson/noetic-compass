"""Pinned META2 dependencies and committed-byte inputs for the separate META3 launcher.

This module has no provider or neural imports. Shared code is checked before
any of its modules are imported. The canonical budget lives only in META2.
"""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
META2_ROOT = ROOT.parent / "CAS_META_2_COMPOSITION"
UPSTREAM_SHA = "410bce98307a5644db51928459b73391c7066b72"
BASELINE_SHA = "0917267b1354e5d036263eaa6ba9a7197eafb776"
BASELINE_MANIFEST_SHA = "476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0"
PILOT = "research/CAS_META_3_PROCEDURAL_MEMORY"
META2 = "research/CAS_META_2_COMPOSITION"
META1 = "research/CAS_META_1_LEARNED_SELECTION"
META_RUNTIME = "research/CASFORMER_v0_3_META_LOGIC_WIP"
ENTRYPOINT = "cas_meta3.native_demo"
SCHEMA = "cas-meta3-launch/1"
PACKAGES = ("CAS_META_3_PROCEDURAL_MEMORY", "CAS_META_2_COMPOSITION",
            "CAS_META_1_LEARNED_SELECTION", "CASFORMER_v0_3_META_LOGIC_WIP",
            "CAS_CJT_TRANSFORMER_v0_2", "CASFORMER_v0_1")
UPSTREAM_PACKAGES = PACKAGES[1:]
EXPANDED_LIMIT = 512 * 1024 * 1024
PINNED_FILES = {
    "aws/launch.py": "58fb3df85d8a5ed2137b0cea360fa7711bd609e9559b373dbf1296083caf2c5a",
    "aws/budget.py": "77a845ea8669b775a28a940552a9212f667a9506e5586deff64baba06a82eda0",
    "tools/experiment_profiles.py": "53008bfcf10dc10b53f531264cd0e1c6b283a30190a24787d0e2e6720c4c9dc5",
    "requirements-gpu.txt": "9d0be7810014ec3a58a112dc0024a74060400dc841523abd405e5fb579179379",
}
DIST = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
WHEELS = [DIST + "casformer_reference-0.1.0-py3-none-any.whl",
          DIST + "cas_neural_cjt-0.2.0-py3-none-any.whl"]
REQUIRED = (
    PILOT + "/aws/launch.py", PILOT + "/aws/launch_plan.json",
    PILOT + "/aws/frozen_helpers.py", PILOT + "/tools/build_launch_bundle.py",
    PILOT + "/cas_meta3/native_demo.py", PILOT + "/cas_meta3/registry.py",
    PILOT + "/cas_meta3/linker.py", PILOT + "/tests/test_native_demo.py",
    PILOT + "/tools/audit_native_demo.py", PILOT + "/tests/test_native_demo_audit.py",
    PILOT + "/tools/inspect_cloud_packet.py", PILOT + "/tests/test_packet_inspection.py",
    PILOT + "/tests/test_native_semantic_checks.py", PILOT + "/tests/test_native_audit_integration.py",
    META1 + "/tests/test_execution_contract.py", META1 + "/BASELINE_MANIFEST.json",
    META2 + "/tests/test_policy_gpu.py",
    *(META2 + "/" + name for name in PINNED_FILES),
    *WHEELS,
)


def require(value, reason):
    if not value:
        raise ValueError(reason)


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def constant(value):
        raise ValueError("NONFINITE_JSON:" + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=constant)


def verify_dependencies(root=None):
    root = Path(root or META2_ROOT).resolve()
    checked = {}
    # Complete this loop before importing ANY old module.
    for name, expected in PINNED_FILES.items():
        path = root / name
        require(path.is_file() and not path.is_symlink()
                and not any(getattr(parent, "is_junction", lambda: False)() or parent.is_symlink()
                            for parent in (path, *path.parents)), "PINNED_HELPER_LINK_OR_FILE_INVALID")
        actual = sha256(path.read_bytes()).hexdigest()
        require(actual == expected, "IMMUTABLE_META2_DEPENDENCY_CHANGED:" + name)
        checked[META2 + "/" + name] = actual
    return checked


def load_helpers():
    before = verify_dependencies()
    spec = importlib.util.spec_from_file_location("cas_meta3_frozen_meta2_launch", META2_ROOT / "aws/launch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(verify_dependencies() == before, "META2_DEPENDENCY_CHANGED_DURING_IMPORT")
    require(Path(module.budget.CANONICAL_LEDGER).resolve() ==
            (META2_ROOT / "records/budget/campaign_ledger.json").resolve(),
            "SHARED_CANONICAL_BUDGET_REQUIRED")
    return module


def include_member(name):
    parts = PurePosixPath(name).parts
    require(len(parts) >= 3 and parts[0] == "research" and parts[1] in PACKAGES,
            "UNEXPECTED_GIT_ARCHIVE_PATH")
    require("\\" not in name and ":" not in name
            and all(part not in ("", ".", "..") for part in name.split("/")), "UNSAFE_GIT_ARCHIVE_PATH")
    if parts[1] in PACKAGES[:3]:
        if parts[2] in ("records", "runs", "__pycache__", ".pytest_cache"):
            return False
        if any(part in ("__pycache__", ".pytest_cache") for part in parts):
            return False
    return True


def git_context(root=ROOT):
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True).strip())
    prefix = Path(root).resolve().parent.relative_to(repo.resolve()).as_posix() + "/"
    return repo, prefix


def git_members(repo, prefix, commit, packages=PACKAGES):
    require(bool(re.fullmatch(r"[a-f0-9]{40}", commit)), "EXACT_SOURCE_SHA_REQUIRED")
    require(tuple(packages) in (PACKAGES, UPSTREAM_PACKAGES), "EXACT_PACKAGE_SET_REQUIRED")
    resolved = subprocess.check_output(["git", "rev-parse", commit + "^{commit}"], cwd=repo, text=True).strip()
    require(resolved == commit, "EXACT_COMMIT_REQUIRED")
    raw = subprocess.check_output(["git", "-c", "core.autocrlf=false", "archive", "--format=zip",
                                   commit, "--", *(prefix + name for name in packages)], cwd=repo)
    result, aliases, total = {}, set(), 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            require(info.filename.startswith(prefix), "UNEXPECTED_GIT_PREFIX")
            name = "research/" + info.filename[len(prefix):]
            if not include_member(name):
                continue
            require(name.casefold() not in aliases and not stat.S_ISLNK(info.external_attr >> 16),
                    "DUPLICATE_OR_SYMLINK_GIT_SOURCE")
            aliases.add(name.casefold())
            total += info.file_size
            require(total <= EXPANDED_LIMIT, "ARCHIVE_EXPANDED_SIZE_CEILING")
            result[name] = archive.read(info)
    return result


def check_upstream(members, upstream):
    require(upstream, "FROZEN_UPSTREAM_SOURCE_REQUIRED")
    actual = {name: raw for name, raw in members.items() if not name.startswith(PILOT + "/")}
    require(actual == upstream, "FROZEN_UPSTREAM_SOURCE_CHANGED")
    for name, expected in PINNED_FILES.items():
        require(sha256(members[META2 + "/" + name]).hexdigest() == expected,
                "FROZEN_HELPER_BYTE_MISMATCH:" + name)
    baseline_raw = members[META1 + "/BASELINE_MANIFEST.json"]
    require(sha256(baseline_raw).hexdigest() == BASELINE_MANIFEST_SHA, "PROTECTED_BASELINE_MANIFEST_CHANGED")
    baseline = strict_json(baseline_raw)
    require(baseline["baseline_sha"] == BASELINE_SHA, "WRONG_ACCEPTED_BASELINE")
    for entry in baseline["files"]:
        name = "research/" + entry["path"]
        require(name in members and sha256(members[name]).hexdigest() == entry["sha256"],
                "ACCEPTED_SOURCE_OR_WHEEL_CHANGED:" + name)
    return baseline
