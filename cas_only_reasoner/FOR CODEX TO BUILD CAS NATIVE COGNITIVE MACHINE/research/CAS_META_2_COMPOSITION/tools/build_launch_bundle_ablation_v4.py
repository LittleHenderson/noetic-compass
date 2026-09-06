"""Build a META2 AWS source ZIP from committed Git bytes, without neural work."""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import importlib.util
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def verify_cli_helpers_before_import():
    """The standalone builder runs only its own committed helper bytes."""
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip()).resolve()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for relative in ("tools/build_launch_bundle_ablation_v4.py", "tools/experiment_profiles_ablation_v4.py"):
        path = ROOT / relative
        if not path.is_file() or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                                    for p in (path, *path.parents)):
            raise ValueError("PREIMPORT_BUNDLE_SOURCE_LINK_OR_FILE_INVALID:" + relative)
        raw = subprocess.check_output(["git", "show", head + ":" + path.relative_to(repo).as_posix()], cwd=repo)
        if path.read_bytes() != raw:
            raise ValueError("PREIMPORT_BUNDLE_HELPER_NOT_COMMITTED:" + relative)


if __name__ == "__main__":
    verify_cli_helpers_before_import()

_PROFILE_SPEC = importlib.util.spec_from_file_location("cas_meta2_bundle_profiles_ablation_v4", ROOT / "tools/experiment_profiles_ablation_v4.py")
_PROFILE_IMPORT_SHA256 = sha256((ROOT / "tools/experiment_profiles_ablation_v4.py").read_bytes()).hexdigest()
profiles = importlib.util.module_from_spec(_PROFILE_SPEC)
_PROFILE_SPEC.loader.exec_module(profiles)
PACKAGES = ("CAS_META_2_COMPOSITION", "CAS_META_1_LEARNED_SELECTION",
            "CASFORMER_v0_3_META_LOGIC_WIP", "CAS_CJT_TRANSFORMER_v0_2", "CASFORMER_v0_1")
PILOT = "research/CAS_META_2_COMPOSITION"
META1 = "research/CAS_META_1_LEARNED_SELECTION"
BASELINE_SHA = "0917267b1354e5d036263eaa6ba9a7197eafb776"
EXPANDED_LIMIT = 512 * 1024 * 1024
BASELINE_MANIFEST_SHA256 = "476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0"


def include_member(relative):
    parts = PurePosixPath(relative).parts
    if len(parts) < 3 or parts[0] != "research" or parts[1] not in PACKAGES:
        raise ValueError("UNEXPECTED_GIT_ARCHIVE_PATH")
    if any(part in ("", ".", "..") for part in relative.split("/")) or "\\" in relative or ":" in relative:
        raise ValueError("UNSAFE_GIT_ARCHIVE_PATH")
    # Historical job receipts, checkpoints and source ZIPs are evidence, not new
    # training inputs. Frozen accepted packages are included without filtering.
    if relative in profiles.EXTRA_INPUTS:
        return True
    if parts[1] in ("CAS_META_1_LEARNED_SELECTION", "CAS_META_2_COMPOSITION"):
        if parts[2] in ("records", "runs", "__pycache__", ".pytest_cache"):
            return False
        if any(part in ("__pycache__", ".pytest_cache") for part in parts):
            return False
    return True


def make_manifest(members, head, *, experiment_profile="decoder_ablation_v4"):
    experiment = profiles.make_record(members, experiment_profile)
    required = [PILOT + "/cas_meta2/ablation_campaign_v4.py", PILOT + "/tests/test_policy_gpu.py", PILOT + "/aws/launch_ablation_v4.py",
                PILOT + "/aws/launch_plan.json", PILOT + "/aws/budget.py",
                PILOT + "/requirements-gpu.txt", META1 + "/cas_meta1/execution.py",
                META1 + "/tests/test_execution_contract.py", META1 + "/BASELINE_MANIFEST.json"]
    if any(name not in members for name in required):
        raise ValueError("CAMPAIGN_SOURCE_NOT_PRESENT_IN_PINNED_COMMIT")
    baseline_raw = members[META1 + "/BASELINE_MANIFEST.json"]
    if sha256(baseline_raw).hexdigest() != BASELINE_MANIFEST_SHA256:
        raise ValueError("PROTECTED_BASELINE_MANIFEST_CHANGED")
    baseline = json.loads(baseline_raw)
    if baseline.get("baseline_sha") != BASELINE_SHA:
        raise ValueError("WRONG_ACCEPTED_BASELINE")
    for item in baseline["files"]:
        name = "research/" + item["path"]
        if name not in members or sha256(members[name]).hexdigest() != item["sha256"]:
            raise ValueError("GIT_BASELINE_BYTES_DIFFER:" + name)
    if sum(map(len, members.values())) > EXPANDED_LIMIT:
        raise ValueError("ARCHIVE_EXPANDED_SIZE_CEILING")
    dist = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
    manifest = {"schema_version": 2, "source_sha": head, "baseline_sha": BASELINE_SHA,
            "pilot_dir": PILOT, "meta1_dir": META1,
            "meta_runtime_dir": "research/CASFORMER_v0_3_META_LOGIC_WIP",
            "dependency_lock": PILOT + "/requirements-gpu.txt",
            "dependency_scope": "Pinned direct requirements; actual remote resolved environment is receipted.",
            "wheel_paths": [dist + "casformer_reference-0.1.0-py3-none-any.whl",
                            dist + "cas_neural_cjt-0.2.0-py3-none-any.whl"],
            "included_packages": list(PACKAGES),
            "excluded_inputs": "Historical records excluded except exact pinned retrospective input archive and reconstructed dataset; no training permitted.",
            "files_sha256": {name: sha256(raw).hexdigest() for name, raw in sorted(members.items())},
            "protected_baseline_files": len(baseline["files"]),
            "neural_execution_performed_during_packaging": False}
    if experiment is not None:
        manifest["experiment"] = experiment
    return manifest


def build(output, *, experiment_profile="decoder_ablation_v4"):
    profiles.validate_profile_name(experiment_profile)
    output = Path(output).resolve()
    if (not output.is_relative_to(ROOT) or output.exists() or output == ROOT
            or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                   for p in (output, *output.parents))):
        raise ValueError("NEW_OUTPUT_INSIDE_CAMPAIGN_REQUIRED")
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    prefix = ROOT.parent.relative_to(repo).as_posix() + "/"
    source_paths = [prefix + name for name in PACKAGES]
    changes = subprocess.check_output(["git", "diff", "--name-only", "-z", "HEAD", "--", *source_paths], cwd=repo, text=True)
    # Budget/receipts legitimately change between paid jobs; the bundle excludes
    # them. Every included tracked source byte must match the committed revision.
    if any(include_member("research/" + name[len(prefix):]) for name in changes.split("\0") if name.startswith(prefix)):
        raise ValueError("TRACKED_SOURCE_CHANGES_MUST_BE_COMMITTED_FIRST")
    untracked = subprocess.check_output(["git", "-c", "core.quotepath=false", "ls-files", "-z", "--others", "--exclude-standard", "--", *source_paths], cwd=repo, text=True)
    if any(include_member("research/" + name[len(prefix):]) for name in untracked.split("\0") if name.startswith(prefix)):
        raise ValueError("UNTRACKED_SOURCE_MUST_BE_COMMITTED_FIRST")
    members = profiles.git_members(repo, prefix, head)
    # These executing helper bytes must be the same committed source being packed.
    for local in (Path(__file__), ROOT / "tools/experiment_profiles_ablation_v4.py"):
        name = PILOT + "/" + local.relative_to(ROOT).as_posix()
        if (not local.is_file() or local.is_symlink() or name not in members
                or local.read_bytes() != members[name]):
            raise ValueError("BUNDLE_HELPER_NOT_COMMITTED_BYTES:" + name)
    if _PROFILE_IMPORT_SHA256 != sha256(members[PILOT + "/tools/experiment_profiles_ablation_v4.py"]).hexdigest():
        raise ValueError("PROFILE_CHANGED_AFTER_IMPORT")
    manifest = make_manifest(members, head, experiment_profile=experiment_profile)
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
    return {"status": "CAS_META_2_ABLATION_V4_PINNED_PACKAGE_BUILT_GPU_NOT_RUN",
            "source_sha": head, "baseline_sha": BASELINE_SHA, "archive": str(output),
            "archive_sha256": sha256(output.read_bytes()).hexdigest(),
            "archive_bytes": output.stat().st_size, "files": len(members),
            "protected_baseline_files": manifest["protected_baseline_files"], "launch_manifest": manifest}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--experiment-profile", choices=profiles.PROFILE_NAMES, default="decoder_ablation_v4")
    args = parser.parse_args()
    receipt_path = args.output.with_suffix(".receipt.json")
    if receipt_path.exists():
        raise ValueError("PACKAGE_RECEIPT_ALREADY_EXISTS")
    receipt = build(args.output, experiment_profile=args.experiment_profile)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in receipt.items() if key != "launch_manifest"}, indent=2))
