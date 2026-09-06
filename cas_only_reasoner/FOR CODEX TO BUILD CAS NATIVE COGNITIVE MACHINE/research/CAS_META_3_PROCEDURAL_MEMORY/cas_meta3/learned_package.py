"""Data-only candidate full-program packages, never qualified skills.

This side-by-side schema does not extend or alter the fixed-B registry. A
caller must supply its own expected content, lineage, compatibility and grant.
The producer identities are UNVERIFIED claims. In particular,
``policy_source_sha256`` means SHA-256 of canonical JSON of the producing
checkpoint's policy_source_sha256 file-map (the v3 writer's 14-file map), not
one Python file or a Git commit. A separate evidence reader must verify it.

Only the pinned pure IR, codec and topology checks run here. No curriculum is
drawn, no tensors/models are imported, and no package is stored or executed.
"""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from types import ModuleType

PACKAGE_SCHEMA = "cas-meta3-learned-program-package/0.1"
PACKAGE_KIND = "FULL_META2_PROGRAM_CANDIDATE"
BASELINE_SHA = "0917267b1354e5d036263eaa6ba9a7197eafb776"
META2_SOURCE_SHA = "ec9d161908ab4ed8a4fb300ca31cb089ac0c3b70"
IR_SCHEMA = "cas-meta2-program/0.1"
MAX_PACKAGE_BYTES = 262144
MAX_TREE_NODES = 32768
MAX_TREE_DEPTH = 24
MAX_CONTAINER_ITEMS = 8192
MAX_STRING_BYTES = 16384
CJT_IDS = ("A", "B", "C", "R")
DEPENDENCY_ROOT = Path(__file__).resolve().parents[2] / "CAS_META_2_COMPOSITION"
PINNED_DEPENDENCY_HASHES = {
    "cas_meta2/__init__.py": "07b7b2f1a52806b819e3820655fa578f3e5241ce2327695f157e542ce06a63da",
    "cas_meta2/ir.py": "02f3ce65ef9c3b54901a38abab2d4f9f272268e7c195f7001fb119bf1d384637",
    "cas_meta2/codec.py": "c6ca7f489f91e4b43225b7ffc4d496490f038c18842266b6d5da05570ca29030",
    "cas_meta2/curriculum.py": "c89a03e2f0c381ec4e9c2f8750fd5f5bf6d4b7836ca790d02e256c1cc334e384",
}
_NAMESPACE = "_cas_meta3_learned_package_pinned_dependencies"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_GIT = re.compile(r"[0-9a-f]{40}\Z")


class PackageError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise PackageError(code)


def _keys(value, names, code):
    _require(type(value) is dict and set(value) == set(names), code)


def _sha(value, code):
    _require(type(value) is str and _HEX.fullmatch(value) is not None, code)


def _tree(value):
    """Bound exact JSON types before serialization; do not coerce Python data."""
    active, nodes, string_bytes = set(), 0, 0
    stack = [(value, 0, False)]
    while stack:
        item, depth, leaving = stack.pop()
        if leaving:
            active.remove(id(item))
            continue
        nodes += 1
        _require(nodes <= MAX_TREE_NODES and depth <= MAX_TREE_DEPTH, "PACKAGE_TREE_CEILING")
        if type(item) in (dict, list):
            _require(id(item) not in active, "CYCLIC_PACKAGE")
            _require(len(item) <= MAX_CONTAINER_ITEMS, "PACKAGE_TREE_CEILING")
            active.add(id(item))
            stack.append((item, depth, True))
            if type(item) is dict:
                _require(all(type(key) is str for key in item), "NON_STRING_JSON_KEY")
                stack.extend((key, depth + 1, False) for key in item)
                children = item.values()
            else:
                children = item
            stack.extend((child, depth + 1, False) for child in children)
        elif type(item) is str:
            try:
                size = len(item.encode("utf-8"))
            except UnicodeError as error:
                raise PackageError("INVALID_UNICODE") from error
            _require(size <= MAX_STRING_BYTES, "PACKAGE_STRING_CEILING")
            string_bytes += size
            _require(string_bytes <= MAX_PACKAGE_BYTES, "PACKAGE_BYTE_CEILING")
        elif type(item) is int:
            _require(abs(item) <= 2**53 - 1, "PACKAGE_INTEGER_CEILING")
        elif type(item) is float:
            _require(math.isfinite(item), "NONFINITE_PACKAGE_VALUE")
        else:
            _require(item is None or type(item) is bool, "NON_JSON_PACKAGE_TYPE")


def _pairs(items):
    value = {}
    for key, item in items:
        _require(key not in value, "DUPLICATE_JSON_FIELD")
        value[key] = item
    return value


def _decode(raw):
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_PACKAGE_BYTES, "PACKAGE_BYTE_CEILING")
    def forbidden(_):
        raise PackageError("NONFINITE_PACKAGE_VALUE")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=forbidden)
    except PackageError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise PackageError("INVALID_PACKAGE_JSON") from error
    _require(type(value) is dict, "PACKAGE_OBJECT_REQUIRED")
    _tree(value)
    return value


def canonical_package(package):
    """Content bytes only; canonicalization is not admission or qualification."""
    value = _decode(package) if type(package) is bytes else package
    _require(type(value) is dict, "PACKAGE_OBJECT_REQUIRED")
    _tree(value)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    _require(0 < len(raw) <= MAX_PACKAGE_BYTES, "PACKAGE_BYTE_CEILING")
    return raw


def package_digest(package):
    return sha256(canonical_package(package)).hexdigest()


def _dependency_bytes():
    raw = {}
    for name, checksum in PINNED_DEPENDENCY_HASHES.items():
        path = DEPENDENCY_ROOT / name
        try:
            _require(not path.is_symlink() and not path.parent.is_symlink()
                     and not DEPENDENCY_ROOT.is_symlink() and path.is_file(), "UNTRUSTED_PURE_DEPENDENCY_PATH")
            payload = path.read_bytes()
        except OSError as error:
            raise PackageError("PURE_DEPENDENCY_UNAVAILABLE") from error
        _require(sha256(payload).hexdigest() == checksum, "PINNED_PURE_DEPENDENCY_CHANGED")
        raw[name] = payload
    return raw


def dependency_receipt():
    _dependency_bytes()
    return {"schema": "cas-meta3-learned-package-dependencies/0.1", "source_sha": META2_SOURCE_SHA,
            "files_sha256": dict(PINNED_DEPENDENCY_HASHES), "binding": "LITERAL_SHA256_PINS",
            "verified_against_git": False}


def verify_dependency_git():
    """Build-time read-only check of the literal pins against actual Git bytes."""
    receipt = dependency_receipt()
    try:
        root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=DEPENDENCY_ROOT,
                    check=True, capture_output=True, text=True, timeout=15).stdout.strip()).resolve()
        for name, checksum in PINNED_DEPENDENCY_HASHES.items():
            relative = (DEPENDENCY_ROOT / name).resolve().relative_to(root).as_posix()
            raw = subprocess.run(["git", "show", META2_SOURCE_SHA + ":" + relative], cwd=root,
                                  check=True, capture_output=True, timeout=15).stdout
            _require(sha256(raw).hexdigest() == checksum, "PINNED_GIT_OBJECT_MISMATCH")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        if isinstance(error, PackageError):
            raise
        raise PackageError("PINNED_GIT_OBJECT_UNAVAILABLE") from error
    return {**receipt, "verified_against_git": True}


@contextmanager
def _pure_dependencies():
    """Execute only freshly checked fixed source bytes, never a .pyc or plugin.

    A private package namespace avoids accepting a preloaded cas_meta2 module
    from another checkout. No sys.path edit or ordinary dependency discovery.
    """
    raw = _dependency_bytes()  # Check ALL dependencies before the first exec.
    _require(not any(name == _NAMESPACE or name.startswith(_NAMESPACE + ".")
                     for name in sys.modules), "UNTRUSTED_PRELOADED_PURE_NAMESPACE")
    loaded = {}
    try:
        for short, relative in (("", "cas_meta2/__init__.py"), ("ir", "cas_meta2/ir.py"),
                                ("codec", "cas_meta2/codec.py"), ("curriculum", "cas_meta2/curriculum.py")):
            name = _NAMESPACE + ("." + short if short else "")
            module = ModuleType(name)
            module.__file__ = str(DEPENDENCY_ROOT / relative)
            module.__package__ = _NAMESPACE
            if not short:
                module.__path__ = [str(DEPENDENCY_ROOT / "cas_meta2")]
            sys.modules[name] = module
            loaded[name] = module
            exec(compile(raw[relative], module.__file__, "exec"), module.__dict__)
        _dependency_bytes()
        yield loaded[_NAMESPACE + ".ir"], loaded[_NAMESPACE + ".codec"], loaded[_NAMESPACE + ".curriculum"]
    finally:
        for name, module in reversed(tuple(loaded.items())):
            if sys.modules.get(name) is module:
                del sys.modules[name]


def _compatibility(value):
    _keys(value, ("baseline_sha", "meta2_source_sha", "ir_schema", "native_schema_sha256", "model_digest",
                  "parameter_bytes_sha256", "software_digest", "topology_sha256", "operation_contracts", "decoder_contracts"),
          "INVALID_COMPATIBILITY_FIELDS")
    _require(value["baseline_sha"] == BASELINE_SHA and value["meta2_source_sha"] == META2_SOURCE_SHA
             and value["ir_schema"] == IR_SCHEMA, "UNSUPPORTED_COMPATIBILITY_VERSION")
    for field in ("native_schema_sha256", "model_digest", "parameter_bytes_sha256", "software_digest", "topology_sha256"):
        _sha(value[field], "INVALID_COMPATIBILITY_DIGEST")
    _keys(value["operation_contracts"], ("^6",), "INVALID_OPERATION_IDENTITIES")
    _keys(value["decoder_contracts"], CJT_IDS, "INVALID_DECODER_IDENTITIES")
    for checksum in (*value["operation_contracts"].values(), *value["decoder_contracts"].values()):
        _sha(checksum, "INVALID_COMPATIBILITY_DIGEST")


def _program_contract(program, binding):
    with _pure_dependencies() as (ir, codec, curriculum):
        try:
            codec.validate_action({"program": program, "binding": binding})
            bounds = ir.validate_program(program)
            plan = curriculum.check_native_topology(program)
            _require(bool(plan["runs"]) and plan["return_node"] >= 0 and all(
                row["output_node"] >= 0 for row in plan["events"] if row["kind"] == "RETURN"),
                "ACCEPTED_EFFECT_RESULT_REQUIRED")
            scope = sorted({node for proc in program["procedures"].values() for node in proc["allowed_cjts"]})
            return {"bounds": bounds, "required_cjts": scope,
                    "executed_cjts": sorted({row["cjt_id"] for row in plan["runs"]}),
                    "return_node": plan["return_node"],
                    "output_producer_cjt_id": plan["runs"][plan["return_node"]]["cjt_id"]}
        except (ir.IRValidationError, codec.PolicyContractError, curriculum.CurriculumError) as error:
            raise PackageError("INVALID_NATIVE_PROGRAM:" + str(error)) from error


def _validate(package, *, expected_digest, trusted_compatibility, permitted_cjts,
              expected_parent_digest, expected_version):
    _sha(expected_digest, "INVALID_EXPECTED_PACKAGE_DIGEST")
    raw = canonical_package(package)
    _require(sha256(raw).hexdigest() == expected_digest, "EXPECTED_PACKAGE_DIGEST_MISMATCH")
    value = _decode(raw)
    _keys(value, ("schema", "kind", "program", "binding", "io", "required_cjts", "compatibility", "provenance",
                  "lineage", "memory_requirements", "qualification_status"), "UNEXPECTED_PACKAGE_FIELDS")
    _require(value["schema"] == PACKAGE_SCHEMA and value["kind"] == PACKAGE_KIND, "UNSUPPORTED_PACKAGE_KIND")
    _require(value["qualification_status"] == "UNQUALIFIED", "QUALIFICATION_CLAIM_FORBIDDEN")
    _require(type(value["memory_requirements"]) is list and not value["memory_requirements"], "UNSUPPORTED_MEMORY_REQUIREMENTS")
    _tree(trusted_compatibility)
    _compatibility(value["compatibility"])
    _compatibility(trusted_compatibility)
    _require(value["compatibility"] == trusted_compatibility, "CALLER_COMPATIBILITY_MISMATCH")
    _require(type(permitted_cjts) in (list, tuple, set, frozenset)
             and all(type(node) is str and node in CJT_IDS for node in permitted_cjts)
             and len(permitted_cjts) == len(set(permitted_cjts)), "INVALID_CALLER_CJT_GRANT")
    _require(type(expected_version) is int and 1 <= expected_version <= 2**31 - 1, "INVALID_EXPECTED_VERSION")
    if expected_parent_digest is not None:
        _sha(expected_parent_digest, "INVALID_EXPECTED_PARENT_DIGEST")
    _require((expected_version == 1) == (expected_parent_digest is None), "INVALID_EXPECTED_LINEAGE")
    _keys(value["lineage"], ("version", "parent_package_sha256"), "INVALID_LINEAGE_FIELDS")
    _require(type(value["lineage"]["version"]) is int and value["lineage"]["version"] == expected_version
             and value["lineage"]["parent_package_sha256"] == expected_parent_digest, "CALLER_LINEAGE_MISMATCH")
    _require(expected_parent_digest != expected_digest, "SELF_PARENT_FORBIDDEN")
    _require(type(value["binding"]) is int and value["binding"] in (0, 1, 2), "INVALID_OBSERVATION_BINDING")
    contract = _program_contract(value["program"], value["binding"])
    _require(type(value["required_cjts"]) is list and value["required_cjts"] == contract["required_cjts"], "DERIVED_CJT_SCOPE_MISMATCH")
    _require(set(value["required_cjts"]) <= set(permitted_cjts), "CALLER_CJT_SCOPE_DENIED")
    expected_io = {
        "input": {"kind": "OBSERVATION_SLOT", "slot": value["binding"], "dtype": "float32", "shape": [1, 2, 4]},
        "output": {"kind": "ACCEPTED_EFFECT", "producer_cjt_id": contract["output_producer_cjt_id"],
                   "dtype": "float32", "shape": [1, 2, 4]},
    }
    # Canonical bytes distinguish bool from int and float from int in shapes.
    _require(canonical_package(value["io"]) == canonical_package(expected_io), "DERIVED_IO_CONTRACT_MISMATCH")
    provenance = value["provenance"]
    _keys(provenance, ("source_program_sha256", "policy_source_sha256", "policy_checkpoint_sha256",
                       "producer_source_sha", "producer_evidence_sha256", "verification_status"), "INVALID_PROVENANCE_FIELDS")
    _require(provenance["verification_status"] == "UNVERIFIED", "PROVENANCE_VERIFICATION_CLAIM_FORBIDDEN")
    for field in ("source_program_sha256", "policy_source_sha256", "policy_checkpoint_sha256", "producer_evidence_sha256"):
        _sha(provenance[field], "INVALID_PROVENANCE_DIGEST")
    _require(type(provenance["producer_source_sha"]) is str and _GIT.fullmatch(provenance["producer_source_sha"]) is not None,
             "INVALID_PRODUCER_SOURCE_SHA")
    _require(provenance["source_program_sha256"] == contract["bounds"]["program_sha256"], "SOURCE_PROGRAM_DIGEST_MISMATCH")
    return value, contract


def validate_package(package, *, expected_digest, trusted_compatibility, permitted_cjts,
                     expected_parent_digest, expected_version):
    """Return detached admitted data; this does not prove producer or ancestry."""
    return _validate(package, expected_digest=expected_digest, trusted_compatibility=trusted_compatibility,
                     permitted_cjts=permitted_cjts, expected_parent_digest=expected_parent_digest,
                     expected_version=expected_version)[0]


def admission_receipt(package, *, expected_digest, trusted_compatibility, permitted_cjts,
                      expected_parent_digest, expected_version):
    value, contract = _validate(package, expected_digest=expected_digest, trusted_compatibility=trusted_compatibility,
                                permitted_cjts=permitted_cjts, expected_parent_digest=expected_parent_digest,
                                expected_version=expected_version)
    receipt = {"schema": "cas-meta3-learned-package-admission/0.1", "status": "DATA_ONLY_ADMITTED",
               "package_sha256": expected_digest, "package_schema": PACKAGE_SCHEMA,
               "qualification_status": "UNQUALIFIED", "provenance_verified": False,
               "parent_evidence_verified": False, "learning_success_established": False,
               "execution_performed": False, "promotion_granted": False,
               "lineage": value["lineage"], "program_contract": contract,
               "dependency": dependency_receipt()}
    return {**receipt, "receipt_sha256": sha256(canonical_package(receipt)).hexdigest()}
