"""Pure, closed experiment dispatch; no models, provider calls or budget state."""
from hashlib import sha256
import json
import math
import re

PILOT = "research/CAS_META_2_COMPOSITION"
PROFILE_NAMES = ("default", "learning_v2")
DEFAULT_ENTRYPOINT = "cas_meta2.campaign"
V2_ENTRYPOINT = "cas_meta2.campaign_v2"
V2_SPEC = PILOT + "/EXPERIMENT_V2.json"
V2_LOCAL_FILES = (
    "cas_meta2/features_v2.py", "cas_meta2/selection_v2.py",
    "cas_meta2/curriculum_v2.py", "cas_meta2/train_v2.py",
    "cas_meta2/campaign_v2.py", "EXPERIMENT_V2.json",
    "cas_meta2/gpu_preflight_v2.py", "tests/test_learning_v2_gpu.py",
    "tools/experiment_profiles.py", "tools/build_launch_bundle.py",
)
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


def validate_v2_spec(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= 1024 * 1024:
        raise ValueError("EXPERIMENT_SPEC_SIZE_INVALID")
    document = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=_constant, parse_float=_float)
    fixed = {"schema": "cas-meta2-experiment/2", "profile": "learning_v2",
             "entrypoint": V2_ENTRYPOINT}
    if type(document) is not dict or any(type(document.get(k)) is not str or document[k] != v
                                         for k, v in fixed.items()):
        raise ValueError("EXPERIMENT_SPEC_IDENTITY_MISMATCH")
    return document


def make_record(members, profile="default"):
    validate_profile_name(profile)
    if profile == "default":
        return None  # Preserve the original manifest, with no implicit v2 selection.
    if any(PILOT + "/" + name not in members for name in V2_LOCAL_FILES):
        raise ValueError("EXPERIMENT_V2_SOURCE_MISSING")
    validate_v2_spec(members[V2_SPEC])
    return {"profile": "learning_v2", "entrypoint": V2_ENTRYPOINT,
            "spec_path": V2_SPEC, "spec_sha256": sha256(members[V2_SPEC]).hexdigest()}


def validate_manifest(manifest, read_member=None):
    """An absent profile means old behavior; any supplied profile must be exact."""
    if "experiment" not in manifest:
        return None
    record = manifest["experiment"]
    if type(record) is not dict or set(record) != {"profile", "entrypoint", "spec_path", "spec_sha256"}:
        raise ValueError("EXPERIMENT_MANIFEST_FIELDS_INVALID")
    if record["profile"] != "learning_v2" or record["entrypoint"] != V2_ENTRYPOINT or record["spec_path"] != V2_SPEC:
        raise ValueError("EXPERIMENT_MANIFEST_IDENTITY_NOT_ALLOWLISTED")
    digest = record["spec_sha256"]
    if type(digest) is not str or not SHA256.fullmatch(digest):
        raise ValueError("EXPERIMENT_SPEC_DIGEST_INVALID")
    mapping = manifest.get("files_sha256", {})
    if type(mapping) is not dict or any(PILOT + "/" + name not in mapping for name in V2_LOCAL_FILES):
        raise ValueError("EXPERIMENT_V2_SOURCE_MISSING")
    if mapping[V2_SPEC] != digest:
        raise ValueError("EXPERIMENT_SPEC_MANIFEST_DIGEST_MISMATCH")
    if read_member is not None:
        raw = read_member(V2_SPEC)
        if sha256(raw).hexdigest() != digest:
            raise ValueError("EXPERIMENT_SPEC_BYTES_MISMATCH")
        validate_v2_spec(raw)
    return dict(record)


def entrypoint(manifest):
    record = validate_manifest(manifest)
    return DEFAULT_ENTRYPOINT if record is None else record["entrypoint"]
