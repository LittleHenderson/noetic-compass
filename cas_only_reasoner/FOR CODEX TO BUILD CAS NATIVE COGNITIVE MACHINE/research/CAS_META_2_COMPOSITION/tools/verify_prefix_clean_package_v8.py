"""Reproduce the frozen pure suite from its ZIP, with declared external data.

No model deserialization, native execution, provider access, or budget change.
The exact archive is extracted to a new in-scope directory. Its own test runner
executes there, not from the current worktree's Python source.
"""
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records/child_call_v8_diagnostic_001"
SOURCE_SHA = "13f424981d7434b1a92815d1ad5759d543bbd3be"
ARCHIVE_SHA = "c1e784440b408a81d28efd00444fe69680972b9ef6ce14b5c298598dc6e83be1"
EXTRACTION_SHA = "9bf40771df6dd7f67189d402d6bcfd8e05bd8cd997b71a6825fff21da105ae98"
PILOT = "research/CAS_META_2_COMPOSITION"
HISTORICAL = {
    "aws_full_002": (62269330, "e22412583114e50cbf9e60d8b22864bfb4ca76e6ccecedee7a0f72976ec37ae0"),
    "aws_learning_v2_001": (59648802, "0d1b13aa711685cc488bdfdb981d8682d3d1b02b8e67530a3742add44dd13e93"),
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def regular(path):
    path = Path(path).absolute()
    require(path.is_file() and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                                      for p in (path, *path.parents)), "V8_CLEAN_REGULAR_FILE_REQUIRED")
    return path


def file_hash(path):
    with regular(path).open("rb") as stream:
        return __import__("hashlib").file_digest(stream, "sha256").hexdigest()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "V8_CLEAN_DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    result = json.loads(raw, object_pairs_hook=pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("V8_CLEAN_NONFINITE_JSON")))
    json.dumps(result, allow_nan=False)
    return result


def safe_name(name):
    require(type(name) is str and name and not name.startswith("/")
            and "\\" not in name and ":" not in name
            and all(p not in ("", ".", "..") for p in name.split("/")), "V8_CLEAN_UNSAFE_MEMBER")
    return name


def inspect_archive(path):
    require(file_hash(path) == ARCHIVE_SHA, "V8_CLEAN_ARCHIVE_CHANGED")
    with ZipFile(regular(path)) as archive:
        infos = archive.infolist()
        names = [safe_name(info.filename) for info in infos]
        require(len(names) == len(set(names)) == len({n.casefold() for n in names}) == 616,
                "V8_CLEAN_ARCHIVE_COVERAGE")
        require(sum(info.file_size for info in infos) <= 128 * 1024**2
                and all(not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16) for info in infos),
                "V8_CLEAN_ARCHIVE_SIZE_OR_LINK")
        raw = archive.read("prefix_source_manifest.json")
        manifest = decode(raw)
        require(manifest.get("schema") == "cas-meta2-prefix-source-package/8"
                and manifest.get("source_sha") == SOURCE_SHA
                and manifest.get("frozen_source_files") == 603
                and manifest.get("protected_baseline_files") == 316
                and manifest.get("addition_count") == 11, "V8_CLEAN_SOURCE_IDENTITY")
        mapping = manifest["files_sha256"]
        require(type(mapping) is dict and len(mapping) == 615
                and set(names) == set(mapping) | {"prefix_source_manifest.json"}, "V8_CLEAN_MANIFEST_COVERAGE")
        for name, expected in mapping.items():
            require(type(expected) is str and re.fullmatch("[0-9a-f]{64}", expected)
                    and sha256(archive.read(name)).hexdigest() == expected, "V8_CLEAN_MEMBER_CHANGED:" + name)
    return {**mapping, "prefix_source_manifest.json": sha256(raw).hexdigest()}


def source_snapshot(directory, mapping):
    return {name: file_hash(directory / name) for name in sorted(mapping)}


def parse_counts(text):
    lines = [line for line in text.splitlines() if re.search(r"\b\d+ passed\b", line)]
    if not lines:
        return None
    line = lines[-1]
    labels = {"tests_passed": "passed", "subtests_passed": "subtests passed",
              "skipped": "skipped", "failed": "failed", "errors": "errors?"}
    return {key: int(match[1]) if (match := re.search(r"\b(\d+) " + label + r"\b", line)) else 0
            for key, label in labels.items()}


def check(output, archive, extraction, historical_records=None):
    output = Path(output).absolute()
    require(not output.exists() and output.resolve().is_relative_to(RECORDS.resolve())
            and output.resolve() != RECORDS.resolve()
            and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                        for p in (output, *output.parents)), "V8_CLEAN_NEW_IN_SCOPE_OUTPUT_REQUIRED")
    archive = regular(archive)
    mapping = inspect_archive(archive)
    extraction = Path(extraction).absolute()
    upstream_receipt = regular(extraction.parent / "extraction_receipt.json")
    require(extraction.is_dir() and file_hash(upstream_receipt) == EXTRACTION_SHA,
            "V8_CLEAN_PINNED_EXTERNAL_EXTRACTION_REQUIRED")
    historical_records = Path(historical_records or ROOT / "records").absolute()
    historical = {}
    for directory, (size, expected) in HISTORICAL.items():
        path = regular(historical_records / directory / "cloud_artifacts.zip")
        require(path.stat().st_size == size and file_hash(path) == expected,
                "V8_CLEAN_HISTORICAL_REGRESSION_PACKET_CHANGED:" + directory)
        historical[directory] = {"path": str(path), "bytes": size, "sha256": expected}
    test_spec = importlib.util.find_spec("pytest")
    require(test_spec is not None and test_spec.origin is not None, "V8_CLEAN_PYTEST_REQUIRED")
    library = regular(test_spec.origin).parent.parent
    runner_digest = file_hash(__file__)
    output.mkdir(parents=True, exist_ok=False)
    package = output / "package"
    package.mkdir()
    with ZipFile(archive) as zipped:
        for name in sorted(mapping):
            target = package / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(zipped.read(name))
    before = source_snapshot(package, mapping)
    require(before == mapping, "V8_CLEAN_EXTRACTED_SOURCE_CHANGED")
    pilot = package / PILOT
    for directory, descriptor in historical.items():
        target = pilot / "records" / directory / "cloud_artifacts.zip"
        target.parent.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(descriptor["path"], target)
        require(file_hash(target) == descriptor["sha256"], "V8_CLEAN_HISTORICAL_COPY_CHANGED")
        descriptor["staged_path"] = str(target)
    runner = pilot / "tools/check_prefix_diagnostic_v8.py"
    temporary = pilot / "records/child_call_v8_diagnostic_001/clean_pytest_tmp"
    command = [sys.executable, "-I", "-B", str(runner), "--child", str(temporary), str(library)]
    env = os.environ.copy()
    env.update(CAS_META2_V8_TEST_EXTRACTION=str(extraction), PYTHONPATH="",
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1", PYTEST_ADDOPTS="-rs")
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    timed_out = False
    process = None
    code = None
    start_error = None
    # Windows CreateProcess rejects very long working-directory names even
    # when Python can read those files. The isolated child adds only its own
    # extracted package and explicit pytest library; current source is absent.
    child_cwd = ROOT
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        try:
            process = subprocess.Popen(command, cwd=child_cwd, env=env, stdout=stdout, stderr=stderr)
            try:
                code = process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                code = process.wait(timeout=15)
        except OSError as error:
            start_error = {"type": type(error).__name__, "message": str(error)}
    after = source_snapshot(package, mapping)
    stdout_text = (output / "stdout.txt").read_text(encoding="utf-8", errors="replace")
    counts = parse_counts(stdout_text)
    unchanged = before == after == mapping and runner_digest == file_hash(__file__)
    external_unchanged = file_hash(upstream_receipt) == EXTRACTION_SHA and all(
        file_hash(d["path"]) == file_hash(d["staged_path"]) == d["sha256"] for d in historical.values())
    complete = code == 0 and not timed_out and unchanged and external_unchanged and counts == {
        "tests_passed": 313, "subtests_passed": 5, "skipped": 0, "failed": 0, "errors": 0}
    receipt = {
        "schema": "cas-meta2-clean-prefix-source-check/8",
        "status": "CLEAN_ARCHIVE_PURE_SUITE_REPRODUCED" if complete else "CLEAN_ARCHIVE_CHECK_FAILED",
        "source_sha": SOURCE_SHA, "archive": str(archive), "archive_sha256": ARCHIVE_SHA,
        "source_members": len(mapping), "extracted_package": str(package),
        "external_data": {"extraction": str(extraction), "receipt": str(upstream_receipt),
                          "receipt_sha256": EXTRACTION_SHA,
                          "note": "Required input dependency; source ZIP alone is not the complete test dataset."},
        "historical_regression_data": historical,
        "historical_data_boundary": "Two already-opened pre-V7 packets used only by frozen grammar regression tests. Not diagnostic model inputs or new final tasks.",
        "external_data_unchanged": external_unchanged,
        "runner_sha256": runner_digest, "command": command, "cwd": str(child_cwd),
        "explicit_environment": {key: env[key] for key in ("CAS_META2_V8_TEST_EXTRACTION", "PYTHONPATH",
                                                          "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE", "PYTEST_ADDOPTS")},
        "python": sys.version, "pid": process.pid if process is not None else None, "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(), "wall_seconds": time.monotonic() - tick,
        "process_timeout_seconds": 180, "timed_out": timed_out, "exit_code": code,
        "process_start_error": start_error, "counts": counts,
        "source_before": before, "source_after": after, "source_unchanged": unchanged,
        "outputs": {name: {"bytes": (output / name).stat().st_size, "sha256": file_hash(output / name)}
                    for name in ("stdout.txt", "stderr.txt")},
        "boundary": "Frozen ZIP source in a new directory, external pinned development fixture, pure tests only. Not a wheel installation, CUDA execution, native result, or paid launch.",
    }
    with (output / "receipt.json").open("xb") as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
    print(json.dumps({"status": receipt["status"], "receipt": str(output / "receipt.json"),
                      "sha256": file_hash(output / "receipt.json"), "counts": counts, "exit_code": code}))
    return 0 if complete else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", required=True)
    parser.add_argument("--archive", default=str(RECORDS / "source_001/source.zip"))
    parser.add_argument("--extraction", default=str(ROOT / "records/prototype_v7_partial_review_001/extracted_001"))
    parser.add_argument("--historical-records-root", default=str(ROOT / "records"))
    args = parser.parse_args()
    raise SystemExit(check(args.output, args.archive, args.extraction, args.historical_records_root))
