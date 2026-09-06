"""Pure, closed experiment dispatch; no models, provider calls or budget state."""
from hashlib import sha256
import io
from pathlib import Path, PurePosixPath
import stat
import subprocess
import json
import math
import re

PILOT = "research/CAS_META_2_COMPOSITION"
PROFILE_NAMES = ("known_example_fit_v5",)
V5_ENTRYPOINT = "cas_meta2.fit_campaign_v5"
V5_SPEC = PILOT + "/EXPERIMENT_FIT_V5.json"
V5_LOCAL_FILES = (
    "cas_meta2/features_v3.py", "cas_meta2/grammar_v3.py", "cas_meta2/policy_v3.py",
    "cas_meta2/selection_v3.py", "cas_meta2/loss_v3.py", "cas_meta2/train_v3.py",
    "cas_meta2/curriculum_v3.py", "cas_meta2/exclusions_v3.json",
    "cas_meta2/development_exclusions_v3.json", "cas_meta2/campaign_v3.py",
    "cas_meta2/gpu_preflight_v3.py", "cas_meta2/gpu_preflight_copy_v3.py",
    "EXPERIMENT_V3.json", "aws/launch_v3.py", "aws/budget.py",
    "aws/launch_plan.json", "requirements-gpu.txt",
    "tools/experiment_profiles_v3.py", "tools/build_launch_bundle_v3.py",
    "tools/inspect_cloud_packet_v3.py", "tools/audit_stored_packet_v3.py",
    "tests/test_policy_gpu.py", "tests/test_policy_v3_gpu.py",
    "tests/test_loss_v3_gpu.py", "tests/test_gpu_preflight_copy_v3_gpu.py",
    "tests/test_train_v3_gpu.py", "tests/test_gpu_preflight_v3_gpu.py",
    "tests/test_features_v3.py", "tests/test_grammar_v3.py",
    "tests/test_policy_v3_static.py", "tests/test_selection_v3.py",
    "tests/test_loss_v3.py", "tests/test_train_v3_static.py",
    "tests/test_curriculum_v3.py", "tests/test_gpu_preflight_v3_static.py",
    "tests/test_gpu_preflight_copy_v3_static.py", "tests/test_campaign_v3_static.py",
    "tests/test_launch_v3.py", "tests/test_bundle_v3.py",
    "tests/test_inspect_cloud_packet_v3.py", "tests/test_audit_stored_packet_v3.py",
    "tests/test_v3_integration_static.py",
)
V5_LOCAL_FILES += ("cas_meta2/fit_diagnostic_v5.py","cas_meta2/fit_campaign_v5.py","cas_meta2/pytest_no_aliases_v4.py","EXPERIMENT_FIT_V5.json","aws/launch_fit_v5.py","tools/experiment_profiles_fit_v5.py","tools/build_launch_bundle_fit_v5.py","tests/test_fit_diagnostic_v5.py","tests/test_fit_diagnostic_v5_gpu.py","tests/test_fit_profile_v5.py","tests/test_launch_fit_v5.py","records/decoder_dataset_reconstruction_v4_001/dataset/train.json",)
EXTRA_INPUTS = {PILOT + "/records/decoder_dataset_reconstruction_v4_001/dataset/train.json": "579a1bfdda64702b4357f57b75c9c9b6e0710a9262c1da41d5aeec1ca1404359"}
FIXED_SPEC = json.loads(r'''{"schema":"cas-meta2-fit-experiment/0.1","profile":"known_example_fit_v5","entrypoint":"cas_meta2.fit_campaign_v5","purpose":"TRAINING_ONLY_FIT_DIAGNOSTIC","training_permitted":true,"fresh_held_out_claim_permitted":false,"source_release_accepted":false,"training_sha256":"579a1bfdda64702b4357f57b75c9c9b6e0710a9262c1da41d5aeec1ca1404359","fit_task_count":24,"vocabulary_training_count":3072,"epochs":200,"batch_size":8,"optimizer_steps_per_family":600,"families":["cas","generic"],"seed":7,"worker_max_seconds":2700,"max_wall_seconds":3600,"checkpoint_selection":"none"}''')
SHA256 = re.compile(r"[a-f0-9]{64}\Z")


def validate_profile_name(profile):
    if type(profile) is not str or profile not in PROFILE_NAMES:
        raise ValueError("EXPERIMENT_PROFILE_NOT_ALLOWLISTED")
    return profile


def _pairs(items):
    result = {}
    for name, value in items:
        if name in result:
            raise ValueError("DUPLICATE_EXPERIMENT_SPEC_KEY")
        result[name] = value
    return result


def _constant(value):
    raise ValueError("NONFINITE_EXPERIMENT_SPEC_VALUE")


def _float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("NONFINITE_EXPERIMENT_SPEC_VALUE")
    return number


def validate_fit_spec(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= 1024 * 1024:
        raise ValueError("EXPERIMENT_SPEC_SIZE_INVALID")
    document = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=_constant, parse_float=_float)
    if json.dumps(document, sort_keys=True) != json.dumps(FIXED_SPEC, sort_keys=True):
        raise ValueError("EXPERIMENT_SPEC_IDENTITY_MISMATCH")
    return document


def make_record(members, profile="known_example_fit_v5"):
    validate_profile_name(profile)
    if any(PILOT + "/" + name not in members for name in V5_LOCAL_FILES):
        raise ValueError("EXPERIMENT_V3_SOURCE_MISSING")
    validate_fit_spec(members[V5_SPEC])
    if any(sha256(members[name]).hexdigest() != digest for name, digest in EXTRA_INPUTS.items()):
        raise ValueError("PINNED_FIT_TRAINING_INPUT_CHANGED")
    return {"profile": "known_example_fit_v5", "entrypoint": V5_ENTRYPOINT,
            "spec_path": V5_SPEC, "spec_sha256": sha256(members[V5_SPEC]).hexdigest()}


def validate_manifest(manifest, read_member=None):
    """No legacy fallback: the known-example fit record and every registered source are required."""
    if type(manifest) is not dict or "experiment" not in manifest:
        raise ValueError("EXPERIMENT_V3_MANIFEST_REQUIRED")
    record = manifest["experiment"]
    if type(record) is not dict or set(record) != {"profile", "entrypoint", "spec_path", "spec_sha256"}:
        raise ValueError("EXPERIMENT_MANIFEST_FIELDS_INVALID")
    if record["profile"] != "known_example_fit_v5" or record["entrypoint"] != V5_ENTRYPOINT or record["spec_path"] != V5_SPEC:
        raise ValueError("EXPERIMENT_MANIFEST_IDENTITY_NOT_ALLOWLISTED")
    digest = record["spec_sha256"]
    if type(digest) is not str or not SHA256.fullmatch(digest):
        raise ValueError("EXPERIMENT_SPEC_DIGEST_INVALID")
    mapping = manifest.get("files_sha256", {})
    if type(mapping) is not dict or any(PILOT + "/" + name not in mapping for name in V5_LOCAL_FILES):
        raise ValueError("EXPERIMENT_V3_SOURCE_MISSING")
    if any(mapping.get(name) != expected for name, expected in EXTRA_INPUTS.items()):
        raise ValueError("PINNED_FIT_TRAINING_INPUT_CHANGED")
    if mapping[V5_SPEC] != digest:
        raise ValueError("EXPERIMENT_SPEC_MANIFEST_DIGEST_MISMATCH")
    if read_member is not None:
        raw = read_member(V5_SPEC)
        if sha256(raw).hexdigest() != digest:
            raise ValueError("EXPERIMENT_SPEC_BYTES_MISMATCH")
        validate_fit_spec(raw)
    return dict(record)


def entrypoint(manifest):
    record = validate_manifest(manifest)
    return record["entrypoint"]

PACKAGES = ("CAS_META_2_COMPOSITION", "CAS_META_1_LEARNED_SELECTION",
            "CASFORMER_v0_3_META_LOGIC_WIP", "CAS_CJT_TRANSFORMER_v0_2", "CASFORMER_v0_1")
EXPANDED_LIMIT = 512 * 1024 * 1024


def include_member(relative):
    parts = PurePosixPath(relative).parts
    if len(parts) < 3 or parts[0] != "research" or parts[1] not in PACKAGES:
        raise ValueError("UNEXPECTED_GIT_ARCHIVE_PATH")
    if any(part in ("", ".", "..") for part in relative.split("/")) or "\\" in relative or ":" in relative:
        raise ValueError("UNSAFE_GIT_ARCHIVE_PATH")
    if relative in EXTRA_INPUTS:
        return True
    if parts[1] in PACKAGES[:2]:
        if parts[2] in ("records", "runs", "__pycache__", ".pytest_cache"):
            return False
        if any(part in ("__pycache__", ".pytest_cache") for part in parts):
            return False
    return True


def git_context(root):
    root = Path(root).resolve()
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"],
                                       cwd=root, text=True).strip()).resolve()
    prefix = root.parent.relative_to(repo).as_posix() + "/"
    return repo, prefix


def git_members(repo, prefix, source_sha):
    """Read actual committed bytes, not a working-tree hash or manifest assertion."""
    if type(source_sha) is not str or not re.fullmatch(r"[a-f0-9]{40}", source_sha):
        raise ValueError("EXACT_SOURCE_SHA_REQUIRED")
    resolved = subprocess.check_output(["git", "rev-parse", source_sha + "^{commit}"],
                                       cwd=repo, text=True).strip()
    if resolved != source_sha:
        raise ValueError("SOURCE_COMMIT_NOT_AVAILABLE")
    raw = subprocess.check_output(["git", "-c", "core.autocrlf=false", "archive", "--format=zip",
                                   source_sha, "--", *(prefix + name for name in PACKAGES)], cwd=repo)
    import zipfile
    members, aliases, total = {}, set(), 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if not info.filename.startswith(prefix):
                raise ValueError("UNEXPECTED_GIT_ARCHIVE_PREFIX")
            name = "research/" + info.filename[len(prefix):]
            if not include_member(name):
                continue
            if name.casefold() in aliases or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("DUPLICATE_OR_SYMLINK_GIT_SOURCE")
            aliases.add(name.casefold())
            total += info.file_size
            if total > EXPANDED_LIMIT:
                raise ValueError("ARCHIVE_EXPANDED_SIZE_CEILING")
            members[name] = archive.read(info)
    if not members:
        raise ValueError("EMPTY_SOURCE_COMMIT")
    return members
