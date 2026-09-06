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
PROFILE_NAMES = ("decoder_ablation_v4",)
V4_ENTRYPOINT = "cas_meta2.ablation_campaign_v4"
V4_SPEC = PILOT + "/EXPERIMENT_ABLATION_V4.json"
V4_LOCAL_FILES = (
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
V4_LOCAL_FILES += ("cas_meta2/grammar_viability_v4.py", "cas_meta2/predict_viability_v4.py", "cas_meta2/pytest_no_aliases_v4.py", "cas_meta2/ablation_inputs_v4.py", "cas_meta2/ablation_predict_v4.py", "cas_meta2/ablation_campaign_v4.py", "EXPERIMENT_ABLATION_V4.json", "aws/launch_ablation_v4.py", "tools/experiment_profiles_ablation_v4.py", "tools/build_launch_bundle_ablation_v4.py", "tests/test_predict_viability_v4_gpu.py", "tests/test_launch_ablation_v4.py", "records/decoder_ablation_inputs_v4_001/inputs.zip", "records/decoder_dataset_reconstruction_v4_001/dataset/train.json", "records/decoder_dataset_reconstruction_v4_001/dataset/validation.json", "records/decoder_dataset_reconstruction_v4_001/dataset/test_public.json", "records/decoder_dataset_reconstruction_v4_001/dataset/test_private.json", "records/decoder_dataset_reconstruction_v4_001/dataset/dataset_manifest.json",)
EXTRA_INPUTS = {PILOT + "/" + key: value for key, value in json.loads(r'''{"records/decoder_ablation_inputs_v4_001/inputs.zip":"bbb538f9a6cad0ecde46106f542edac9dd64e3188568cb96b2ca550ff854ee93","records/decoder_dataset_reconstruction_v4_001/dataset/train.json":"579a1bfdda64702b4357f57b75c9c9b6e0710a9262c1da41d5aeec1ca1404359","records/decoder_dataset_reconstruction_v4_001/dataset/validation.json":"badbffa8e54d3cadb8a12d1e7d84d79a055b0c1073f4fe48fa068270cddea249","records/decoder_dataset_reconstruction_v4_001/dataset/test_public.json":"553413b0ddc4bd877c3a012fe709bd8bd8836d0d1e0fc9058a8e602153140f62","records/decoder_dataset_reconstruction_v4_001/dataset/test_private.json":"b08ca2f7be8d2ef88988a8a6c15edec087124abdaed788795a795cd541dff65c","records/decoder_dataset_reconstruction_v4_001/dataset/dataset_manifest.json":"c0ad48a1a1c6834775bf18ee31971d491de3ed804d4f6469c97d4194968a2dce"}''').items()}
FIXED_SPEC = json.loads(r'''{"schema":"cas-meta2-decoder-ablation-experiment/0.1","profile":"decoder_ablation_v4","entrypoint":"cas_meta2.ablation_campaign_v4","purpose":"RETROSPECTIVE_DECODER_DIAGNOSTIC","training_permitted":false,"fresh_held_out_claim_permitted":false,"source_release_accepted":false,"learning_source_sha":"ec9d161908ab4ed8a4fb300ca31cb089ac0c3b70","input_archive_sha256":"bbb538f9a6cad0ecde46106f542edac9dd64e3188568cb96b2ca550ff854ee93","modes":["v3","viability_v4"],"max_wall_seconds":6600,"task_count":72,"arms_per_mode":5}''')
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


def validate_ablation_spec(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= 1024 * 1024:
        raise ValueError("EXPERIMENT_SPEC_SIZE_INVALID")
    document = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=_constant, parse_float=_float)
    if json.dumps(document, sort_keys=True) != json.dumps(FIXED_SPEC, sort_keys=True):
        raise ValueError("EXPERIMENT_SPEC_IDENTITY_MISMATCH")
    return document


def make_record(members, profile="decoder_ablation_v4"):
    validate_profile_name(profile)
    if any(PILOT + "/" + name not in members for name in V4_LOCAL_FILES):
        raise ValueError("EXPERIMENT_V3_SOURCE_MISSING")
    validate_ablation_spec(members[V4_SPEC])
    if any(sha256(members[name]).hexdigest() != digest for name, digest in EXTRA_INPUTS.items()):
        raise ValueError("PRESERVED_ABLATION_INPUT_CHANGED")
    return {"profile": "decoder_ablation_v4", "entrypoint": V4_ENTRYPOINT,
            "spec_path": V4_SPEC, "spec_sha256": sha256(members[V4_SPEC]).hexdigest()}


def validate_manifest(manifest, read_member=None):
    """No legacy fallback: the retrospective record and every registered source are required."""
    if type(manifest) is not dict or "experiment" not in manifest:
        raise ValueError("EXPERIMENT_V3_MANIFEST_REQUIRED")
    record = manifest["experiment"]
    if type(record) is not dict or set(record) != {"profile", "entrypoint", "spec_path", "spec_sha256"}:
        raise ValueError("EXPERIMENT_MANIFEST_FIELDS_INVALID")
    if record["profile"] != "decoder_ablation_v4" or record["entrypoint"] != V4_ENTRYPOINT or record["spec_path"] != V4_SPEC:
        raise ValueError("EXPERIMENT_MANIFEST_IDENTITY_NOT_ALLOWLISTED")
    digest = record["spec_sha256"]
    if type(digest) is not str or not SHA256.fullmatch(digest):
        raise ValueError("EXPERIMENT_SPEC_DIGEST_INVALID")
    mapping = manifest.get("files_sha256", {})
    if type(mapping) is not dict or any(PILOT + "/" + name not in mapping for name in V4_LOCAL_FILES):
        raise ValueError("EXPERIMENT_V3_SOURCE_MISSING")
    if any(mapping.get(name) != expected for name, expected in EXTRA_INPUTS.items()):
        raise ValueError("PRESERVED_ABLATION_INPUT_CHANGED")
    if mapping[V4_SPEC] != digest:
        raise ValueError("EXPERIMENT_SPEC_MANIFEST_DIGEST_MISMATCH")
    if read_member is not None:
        raw = read_member(V4_SPEC)
        if sha256(raw).hexdigest() != digest:
            raise ValueError("EXPERIMENT_SPEC_BYTES_MISMATCH")
        validate_ablation_spec(raw)
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
