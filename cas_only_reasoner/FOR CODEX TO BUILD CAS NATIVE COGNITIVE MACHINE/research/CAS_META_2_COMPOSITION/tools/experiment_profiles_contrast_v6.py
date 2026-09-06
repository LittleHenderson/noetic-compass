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
PROFILE_NAMES = ("contrast_learning_v6",)
V6_ENTRYPOINT = "cas_meta2.contrast_v6.campaign"
V6_SPEC = PILOT + "/EXPERIMENT_CONTRAST_V6.json"
V6_LOCAL_FILES = (
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
V6_LOCAL_FILES += ("cas_meta2/contrast_v6/__init__.py","cas_meta2/contrast_v6/curriculum.py","cas_meta2/contrast_v6/data.py","cas_meta2/contrast_v6/train.py","cas_meta2/contrast_v6/checks.py","cas_meta2/contrast_v6/evaluation.py","cas_meta2/contrast_v6/campaign.py","cas_meta2/pytest_no_aliases_v4.py","EXPERIMENT_CONTRAST_V6.json","aws/launch_contrast_v6.py","tools/experiment_profiles_contrast_v6.py","tools/build_launch_bundle_contrast_v6.py","tests/test_contrast_v6_curriculum.py","tests/test_contrast_v6_data.py","tests/test_contrast_v6_train.py","tests/test_contrast_v6_train_gpu.py","tests/test_contrast_v6_checks.py","tests/test_contrast_v6_campaign.py","tests/test_launch_contrast_v6.py","tests/test_contrast_v6_profile.py","records/contrast_v6_bundle_probe_001/dataset/manifest.json","records/contrast_v6_bundle_probe_001/trainer_input/validation.json","records/contrast_v6_bundle_probe_001/dataset/train.json","records/contrast_v6_bundle_probe_001/dataset/test_private.json","records/contrast_v6_bundle_probe_001/dataset/test_public.json","records/contrast_v6_bundle_probe_001/trainer_input/test_public.json","records/contrast_v6_bundle_probe_001/trainer_input/manifest.json","records/contrast_v6_bundle_probe_001/trainer_input/train.json","records/contrast_v6_exclusions_001/inventory.json","records/contrast_v6_bundle_probe_001/dataset/validation.json","records/decoder_dataset_reconstruction_v4_001/dataset/train.json",)
EXTRA_INPUTS = {"research/CAS_META_2_COMPOSITION/records/contrast_v6_bundle_probe_001/dataset/manifest.json":"36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1","research/CAS_META_2_COMPOSITION/records/contrast_v6_bundle_probe_001/trainer_input/validation.json":"26869a0c61007185e9fb76445297b2b231ff107ff15ad9a37fd7288bc855549d","research/CAS_META_2_COMPOSITION/records/contrast_v6_bundle_probe_001/dataset/train.json":"e9032b27ac10364120e7eb7a8844eb43da40985a42cc6ab0629c88f874ae8a17","research/CAS_META_2_COMPOSITION/records/contrast_v6_bundle_probe_001/dataset/test_private.json":"8c62b9d591fd5f1ad6c8d2ed598315f91b9183d2e480709a0f12241ba0b49fff","research/CAS_META_2_COMPOSITION/records/contrast_v6_bundle_probe_001/dataset/test_public.json":"cfec9cdbd9519887b9b08b7349d0bc264d1b327bb1efc89d9325eb7a57535e6a","research/CAS_META_2_COMPOSITION/records/contrast_v6_bundle_probe_001/trainer_input/test_public.json":"cfec9cdbd9519887b9b08b7349d0bc264d1b327bb1efc89d9325eb7a57535e6a","research/CAS_META_2_COMPOSITION/records/contrast_v6_bundle_probe_001/trainer_input/manifest.json":"36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1","research/CAS_META_2_COMPOSITION/records/contrast_v6_bundle_probe_001/trainer_input/train.json":"e9032b27ac10364120e7eb7a8844eb43da40985a42cc6ab0629c88f874ae8a17","research/CAS_META_2_COMPOSITION/records/contrast_v6_exclusions_001/inventory.json":"1a8f7f39bee35f14ef002dfe90f2c6760cbe5c70436c7606fad32ee03f4c1256","research/CAS_META_2_COMPOSITION/records/contrast_v6_bundle_probe_001/dataset/validation.json":"26869a0c61007185e9fb76445297b2b231ff107ff15ad9a37fd7288bc855549d","research/CAS_META_2_COMPOSITION/records/decoder_dataset_reconstruction_v4_001/dataset/train.json":"579a1bfdda64702b4357f57b75c9c9b6e0710a9262c1da41d5aeec1ca1404359"}
FIXED_SPEC = json.loads(r'''{"schema":"cas-meta2-contrast-experiment/6","profile":"contrast_learning_v6","entrypoint":"cas_meta2.contrast_v6.campaign","purpose":"LEARN_INPUT_BINDING_AND_CHILD_CALL_COMPOSITION","curriculum_seed":2026092601,"curriculum":{"train_flat":128,"train_pairs_per_cell":64,"validation_flat":32,"validation_pairs_per_cell":8,"test_triplets":24},"training":{"seed":7,"epochs":200,"batch_size":16,"prediction_batch_size":16,"validation_interval":10,"max_seconds":3300},"exclusion_inventory_sha256":"1a8f7f39bee35f14ef002dfe90f2c6760cbe5c70436c7606fad32ee03f4c1256","train_count":640,"validation_count":96,"test_count":72,"matched_test_triplets":24,"optimizer_steps_per_family":8000,"gpu_gate_max_seconds":900,"native_max_seconds":1800,"max_wall_seconds":6300,"training_permitted":true,"private_test_labels_in_trainer":false,"automatic_retry":false,"automatic_promotion":false,"source_release_accepted":false,"decoder":"unchanged_v3","arms":["cas_untrained","cas_trained","generic_untrained","generic_trained","rule"]}''')
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


def validate_contrast_spec(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= 1024 * 1024:
        raise ValueError("EXPERIMENT_SPEC_SIZE_INVALID")
    document = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=_constant, parse_float=_float)
    if json.dumps(document, sort_keys=True) != json.dumps(FIXED_SPEC, sort_keys=True):
        raise ValueError("EXPERIMENT_SPEC_IDENTITY_MISMATCH")
    return document


def make_record(members, profile="contrast_learning_v6"):
    validate_profile_name(profile)
    if any(PILOT + "/" + name not in members for name in V6_LOCAL_FILES):
        raise ValueError("EXPERIMENT_V3_SOURCE_MISSING")
    validate_contrast_spec(members[V6_SPEC])
    if any(sha256(members[name]).hexdigest() != digest for name, digest in EXTRA_INPUTS.items()):
        raise ValueError("PINNED_CONTRAST_INPUT_CHANGED")
    return {"profile": "contrast_learning_v6", "entrypoint": V6_ENTRYPOINT,
            "spec_path": V6_SPEC, "spec_sha256": sha256(members[V6_SPEC]).hexdigest()}


def validate_manifest(manifest, read_member=None):
    """No legacy fallback: the contrast learning record and every registered source are required."""
    if type(manifest) is not dict or "experiment" not in manifest:
        raise ValueError("EXPERIMENT_V3_MANIFEST_REQUIRED")
    record = manifest["experiment"]
    if type(record) is not dict or set(record) != {"profile", "entrypoint", "spec_path", "spec_sha256"}:
        raise ValueError("EXPERIMENT_MANIFEST_FIELDS_INVALID")
    if record["profile"] != "contrast_learning_v6" or record["entrypoint"] != V6_ENTRYPOINT or record["spec_path"] != V6_SPEC:
        raise ValueError("EXPERIMENT_MANIFEST_IDENTITY_NOT_ALLOWLISTED")
    digest = record["spec_sha256"]
    if type(digest) is not str or not SHA256.fullmatch(digest):
        raise ValueError("EXPERIMENT_SPEC_DIGEST_INVALID")
    mapping = manifest.get("files_sha256", {})
    if type(mapping) is not dict or any(PILOT + "/" + name not in mapping for name in V6_LOCAL_FILES):
        raise ValueError("EXPERIMENT_V3_SOURCE_MISSING")
    if any(mapping.get(name) != expected for name, expected in EXTRA_INPUTS.items()):
        raise ValueError("PINNED_CONTRAST_INPUT_CHANGED")
    if mapping[V6_SPEC] != digest:
        raise ValueError("EXPERIMENT_SPEC_MANIFEST_DIGEST_MISMATCH")
    if read_member is not None:
        raw = read_member(V6_SPEC)
        if sha256(raw).hexdigest() != digest:
            raise ValueError("EXPERIMENT_SPEC_BYTES_MISMATCH")
        validate_contrast_spec(raw)
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
