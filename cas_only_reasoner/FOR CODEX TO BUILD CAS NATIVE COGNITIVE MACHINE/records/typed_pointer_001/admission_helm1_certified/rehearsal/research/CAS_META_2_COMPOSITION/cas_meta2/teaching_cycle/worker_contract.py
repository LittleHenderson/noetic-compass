"""Worker-safe training bundle verification, before any neural import.

The allowlist contains supplied training/development lessons only. Teacher-side
construction code, construction seeds, and final evaluation data never belong
in this bundle. A verified bundle is not a claim of learning or AWS identity.
"""
from __future__ import annotations

from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import re
import stat
from zipfile import ZipFile

SCHEMA = "cas-meta2-teaching-cycle-training-bundle/1"
MANIFEST_NAME = "manifest.json"
ARCHIVE_BYTES_MAX = 32 * 1024**2
EXPANDED_BYTES_MAX = 64 * 1024**2
FILE_BYTES_MAX = 8 * 1024**2
JSON_BYTES_MAX = 2 * 1024**2
WORKER_FILES = (
    "cas_meta2/__init__.py", "cas_meta2/codec.py", "cas_meta2/features_v2.py", "cas_meta2/policy.py",
    "cas_meta2/teaching_cycle/__init__.py", "cas_meta2/teaching_cycle/lesson_contract.py",
    "cas_meta2/teaching_cycle/guided_application.py", "cas_meta2/teaching_cycle/controller.py",
    "cas_meta2/teaching_cycle/gpu_adapter.py", "cas_meta2/teaching_cycle/journal.py",
    "cas_meta2/teaching_cycle/runner.py", "cas_meta2/teaching_cycle/worker_contract.py",
    "cas_meta2/teaching_cycle/worker.py",
)
WHEEL_NAME = "wheels/casformer_reference-0.1.0-py3-none-any.whl"
WHEEL_SHA256 = "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee"
CASE_FILES = ("train.json", "development.json")
PAYLOAD_FILES = frozenset((*WORKER_FILES, WHEEL_NAME, *CASE_FILES))
ALL_FILES = PAYLOAD_FILES | {MANIFEST_NAME}
DIRECTORIES = frozenset(str(parent).replace("\\", "/") for name in PAYLOAD_FILES
                        for parent in Path(name).parents if str(parent) != ".")
PROFILE = {"version": 2, "batch_size": 32, "seed": 7,
    "training_cases_count": 256, "development_cases_count": 64,
    "allocation": {"minimum_full_cycles": 1024, "maximum_cycles": 4096,
        "development_interval": 256, "consistent_checks": 3,
        "readiness_accuracy": 0.90, "minimum_unique_families": 256,
        "minimum_cycles_per_family": 4, "development_cases_count": 64}}


class BundleError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise BundleError("TEACHING_BUNDLE:" + reason)


def digest(raw):
    return sha256(raw).hexdigest()


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise BundleError("TEACHING_BUNDLE:NONFINITE_OR_INVALID_JSON") from error


def canonical_sha256(value):
    return digest(canonical(value))


def decode_json(raw):
    require(type(raw) is bytes and 0 < len(raw) <= JSON_BYTES_MAX, "JSON_BYTES_BOUND")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def nonfinite(value):
        raise BundleError("TEACHING_BUNDLE:NONFINITE_JSON")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
        canonical(value)  # Also rejects overflow-to-infinity decimal literals.
        return value
    except (UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, BundleError):
            raise
        raise BundleError("TEACHING_BUNDLE:INVALID_JSON") from error


def _pin(value, length=64):
    return type(value) is str and re.fullmatch(r"[a-f0-9]{" + str(length) + r"}", value) is not None


def safe_path(path):
    path = Path(path).absolute()
    require(".." not in path.parts, "PARENT_PATH")
    for ancestor in (path, *path.parents):
        require(not ancestor.is_symlink() and not getattr(ancestor, "is_junction", lambda: False)(),
                "LINKED_PATH")
    return path


def read_regular(path, maximum):
    path = safe_path(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "NONREGULAR_OR_HARDLINK")
    require(0 < info.st_size <= maximum, "FILE_BYTES_BOUND")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1 and
                (opened.st_dev, opened.st_ino, opened.st_size) ==
                (info.st_dev, info.st_ino, info.st_size), "FILE_CHANGED_DURING_OPEN")
        raw = stream.read(maximum + 1)
    require(len(raw) == info.st_size and len(raw) <= maximum, "FILE_CHANGED_DURING_READ")
    return raw


def validate_payloads(manifest_raw, payloads, expected_manifest_sha256):
    """Validate bytes first; lesson imports happen only after full hash closure."""
    require(_pin(expected_manifest_sha256) and digest(manifest_raw) == expected_manifest_sha256,
            "MANIFEST_PIN_MISMATCH")
    manifest = decode_json(manifest_raw)
    require(type(manifest) is dict and set(manifest) == {"schema", "source_commit", "source_sha256",
        "training_cases_sha256", "development_cases_sha256", "profile", "files"}, "MANIFEST_FIELDS")
    require(manifest["schema"] == SCHEMA and _pin(manifest["source_commit"], 40), "MANIFEST_IDENTITY")
    require(canonical(manifest["profile"]) == canonical(PROFILE), "PROFILE_CHANGED")
    require(type(payloads) is dict and set(payloads) == PAYLOAD_FILES, "PAYLOAD_INVENTORY")
    require(type(manifest["files"]) is dict and set(manifest["files"]) == PAYLOAD_FILES,
            "MANIFEST_INVENTORY")
    total = len(manifest_raw)
    for name, raw in payloads.items():
        entry = manifest["files"][name]
        require(type(entry) is dict and set(entry) == {"sha256", "bytes"}
                and _pin(entry["sha256"]) and type(entry["bytes"]) is int, "FILE_MANIFEST_FIELDS")
        require(type(raw) is bytes and 0 < len(raw) <= FILE_BYTES_MAX and
                entry["bytes"] == len(raw) and entry["sha256"] == digest(raw), "FILE_IDENTITY:" + name)
        total += len(raw)
        require(total <= EXPANDED_BYTES_MAX, "EXPANDED_BYTES_BOUND")
    require(digest(payloads[WHEEL_NAME]) == WHEEL_SHA256, "FROZEN_WHEEL_CHANGED")
    require(manifest["source_sha256"] == canonical_sha256({name: digest(payloads[name])
                                                          for name in WORKER_FILES}), "SOURCE_MAPPING_CHANGED")
    train, development = (decode_json(payloads[name]) for name in CASE_FILES)
    require(type(train) is list and len(train) == PROFILE["training_cases_count"] and
            type(development) is list and len(development) == PROFILE["development_cases_count"],
            "CASE_COUNTS_CHANGED")
    # This renderer has no task generator, final data or construction seed.
    from .lesson_contract import _case_check
    families = set()
    for split, cases in (("train", train), ("development", development)):
        for case in cases:
            _case_check(case)
            require(case["split"] == split, "CASE_SPLIT_CHANGED")
            require(case["family_id"] not in families, "FAMILY_LEAKAGE_OR_DUPLICATE")
            families.add(case["family_id"])
    require(manifest["training_cases_sha256"] == canonical_sha256(sorted(train, key=lambda c: c["family_id"])),
            "TRAINING_CASES_PIN_MISMATCH")
    require(manifest["development_cases_sha256"] == canonical_sha256(development),
            "DEVELOPMENT_CASES_PIN_MISMATCH")
    return {"manifest": manifest, "manifest_sha256": expected_manifest_sha256,
            "training_cases": train, "development_cases": development}


def load_bundle(root, expected_manifest_sha256):
    root = safe_path(root)
    require(root.is_dir(), "BUNDLE_DIRECTORY_REQUIRED")
    found, directories = set(), set()
    pending = [root]
    while pending:
        directory = pending.pop()
        for path in directory.iterdir():
            safe_path(path)
            name = path.relative_to(root).as_posix()
            if path.is_dir():
                require(name in DIRECTORIES and name not in directories, "UNEXPECTED_DIRECTORY:" + name)
                directories.add(name)
                pending.append(path)
            else:
                require(name in ALL_FILES and name not in found, "UNEXPECTED_FILE:" + name)
                found.add(name)
    require(found == ALL_FILES and directories == DIRECTORIES, "BUNDLE_INVENTORY")
    manifest_raw = read_regular(root / MANIFEST_NAME, JSON_BYTES_MAX)
    require(_pin(expected_manifest_sha256) and digest(manifest_raw) == expected_manifest_sha256,
            "MANIFEST_PIN_MISMATCH")
    payloads = {name: read_regular(root / name, FILE_BYTES_MAX) for name in sorted(PAYLOAD_FILES)}
    return validate_payloads(manifest_raw, payloads, expected_manifest_sha256)


def archive_payloads(path, expected_archive_sha256, expected_manifest_sha256):
    """Bounded ZIP admission. No extraction or imported bundle code runs here."""
    raw = read_regular(path, ARCHIVE_BYTES_MAX)
    require(_pin(expected_archive_sha256) and digest(raw) == expected_archive_sha256, "ARCHIVE_PIN_MISMATCH")
    payloads, total = {}, 0
    with ZipFile(io.BytesIO(raw)) as zipped:
        infos = zipped.infolist()
        require(len(infos) == len(ALL_FILES) and len(infos) <= 20, "ARCHIVE_INVENTORY_COUNT")
        for info in infos:
            name = info.filename
            require(name in ALL_FILES and name not in payloads and not info.is_dir()
                    and not info.flag_bits & 1 and
                    stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG), "ARCHIVE_MEMBER_INVALID")
            maximum = JSON_BYTES_MAX if name == MANIFEST_NAME else FILE_BYTES_MAX
            require(0 < info.file_size <= maximum, "ARCHIVE_MEMBER_BYTES_BOUND")
            total += info.file_size
            require(total <= EXPANDED_BYTES_MAX, "EXPANDED_BYTES_BOUND")
            with zipped.open(info) as stream:
                member = stream.read(info.file_size + 1)
            require(len(member) == info.file_size, "ARCHIVE_MEMBER_CHANGED")
            payloads[name] = member
    manifest_raw = payloads.pop(MANIFEST_NAME)
    validated = validate_payloads(manifest_raw, payloads, expected_manifest_sha256)
    return manifest_raw, payloads, validated


def extract_bundle(archive, destination, expected_archive_sha256, expected_manifest_sha256):
    """Write only after complete ZIP validation; verify every extracted byte."""
    destination = safe_path(destination)
    require(not destination.exists() and destination.parent.is_dir(), "FRESH_DESTINATION_REQUIRED")
    manifest_raw, payloads, _ = archive_payloads(archive, expected_archive_sha256, expected_manifest_sha256)
    destination.mkdir()
    for name, raw in {MANIFEST_NAME: manifest_raw, **payloads}.items():
        target = safe_path(destination / name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    return load_bundle(destination, expected_manifest_sha256)
