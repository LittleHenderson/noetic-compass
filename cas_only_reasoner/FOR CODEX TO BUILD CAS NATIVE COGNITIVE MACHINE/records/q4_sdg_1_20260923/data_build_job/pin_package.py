"""Coordinator tool (laptop, pure Python, no torch, no AWS): pin the B lesson package from the data-build job's digests.

Review item A1: the package identity depends on the compiler engine, so the pin must name the engine and must come
from ONE build made with `--expect-engine python`, rebuilt byte for byte. This tool reads ONLY
  results/build_digests.json   (the machine's two-build comparison and its proposed pin entry)
  results/manifest.json        (the package manifest: counts, hashes, stats; no row, no target)
  launch_record.json, watch_record.json   (provenance and the measured cost bound)
and never a row file. It refuses unless: both builds were byte-identical; the verify with the pinned compiler passed;
the manifest on disk hashes (LF) to the digest the machine reported; its files, seeds, size and engine equal the
frozen B package of q4_ab_rules.py. Then it writes ONE entry into research/helm_cas_expression_lab/Q4_SDG_DATA_PINS.json
(an identical existing entry is a no-op; a different one is PIN_CONFLICT). q4_sdg_curriculum.check_pin reads
`manifest_sha256` from that entry; q4_ab_prep.read_pin_entry reads the rest.

    python pin_package.py --check      # print what would be written; change nothing
    python pin_package.py --write
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
LAB = HERE.parents[1] / "research" / "helm_cas_expression_lab"
PINS = LAB / "Q4_SDG_DATA_PINS.json"
sys.path.insert(0, str(LAB))
import q4_ab_rules as rules  # noqa: E402

EXPECTED_FILES = tuple(sorted("%s_%s_%s.jsonl" % (kind, lesson, split) for kind in ("visible", "sealed")
                              for lesson in ("A", "B", "C") for split in ("train", "dev", "feedback")))


class PinError(ValueError):
    pass


def _json(path):
    try:
        return json.loads(pathlib.Path(path).read_bytes().decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise PinError("UNREADABLE: %s (%s)" % (pathlib.Path(path).name, type(error).__name__)) from None


def pin_entry(results, launch=None, watch=None):
    """The entry to write, after every check. `results` is the downloaded results folder."""
    results = pathlib.Path(results)
    digests = _json(results / "build_digests.json")
    manifest_bytes = (results / "manifest.json").read_bytes().replace(b"\r\n", b"\n")
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    entry = digests.get("pin_entry", {})
    if digests.get("status") != "REBUILD_BYTE_IDENTICAL_AND_VERIFIED" or digests.get("rebuild_byte_identical") is not True \
            or digests.get("verify_exit_code") != 0 or digests.get("manifest_files_match_disk") is not True:
        raise PinError("NOT_PINNABLE: the machine did not report two identical, verified builds")
    if hashlib.sha256(manifest_bytes).hexdigest() != entry.get("manifest_sha256"):
        raise PinError("MANIFEST_DIGEST_DIFFERS: results/manifest.json is not the manifest the machine hashed")
    for key in ("engine", "size", "seed", "feedback_seed"):
        if entry.get(key) != rules.B_PACKAGE[key]:
            raise PinError("NOT_THE_FROZEN_PACKAGE: %s is %r" % (key, entry.get(key)))
    declared = {n: {"sha256": v["sha256"], "records": v["records"]} for n, v in manifest.get("files", {}).items()}
    if (manifest.get("schema") != rules.B_PACKAGE["schema"] or manifest.get("compiler", {}).get("engine") != "python"
            or manifest.get("seed") != rules.B_PACKAGE["seed"] or manifest.get("feedback_seed") != rules.B_PACKAGE["feedback_seed"]
            or manifest.get("size_train_pool_declared") != rules.B_PACKAGE["size"]
            or declared != entry.get("files") or tuple(sorted(declared)) != EXPECTED_FILES):
        raise PinError("MANIFEST_FIELDS_DIFFER from the frozen package or from the machine's digests")
    provenance = {"job": "records/q4_sdg_1_20260923/data_build_job",
                  "build_digests_sha256": hashlib.sha256((results / "build_digests.json").read_bytes()).hexdigest(),
                  "pinned_by": "Claude coordinator (transcribed_by_agent: true; not an owner signature)",
                  "label": rules.LABEL}
    if launch is not None:
        provenance.update(instance_id=launch.get("instance_id"), source_commit=launch.get("identity", {}).get("source_commit"),
                          bundle_sha256=launch.get("bundle", {}).get("sha256"), ami=launch.get("ami"))
    if watch is not None:
        provenance.update(cost_upper_bound_usd=watch.get("cost_upper_bound_usd"), watch_outcome=watch.get("outcome"))
    return {"data_dir": rules.B_PACKAGE["data_dir"], "manifest_sha256": entry["manifest_sha256"],
            "engine": entry["engine"], "size": entry["size"], "seed": entry["seed"],
            "feedback_seed": entry["feedback_seed"], "files": entry["files"], "counts": entry.get("counts"),
            "provenance": provenance}


def write_pin(entry, pins_path=PINS, now=None):
    pins = _json(pins_path)
    versions = pins.setdefault("data_versions", {})
    schema = rules.B_PACKAGE["schema"]
    if schema in versions:
        if versions[schema].get("manifest_sha256") != entry["manifest_sha256"]:
            raise PinError("PIN_CONFLICT: a different package is already pinned for %s" % schema)
        return versions[schema], False
    entry = dict(entry, provenance=dict(entry["provenance"], pinned_utc=(now or datetime.datetime.now(
        datetime.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")))
    versions[schema] = entry
    pins["status"] = "PINNED_FROM_THE_AWS_DATA_BUILD_JOB (data_build_job/pin_package.py)"
    pathlib.Path(pins_path).write_bytes((json.dumps(pins, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    return entry, True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    launch = _json(HERE / "launch_record.json") if (HERE / "launch_record.json").is_file() else None
    watch = _json(HERE / "watch_record.json") if (HERE / "watch_record.json").is_file() else None
    entry = pin_entry(HERE / "results", launch, watch)
    if args.check:
        print(json.dumps(entry, indent=1, sort_keys=True))
        print("PIN_CHECK_PASS (nothing written)")
        return 0
    written, changed = write_pin(entry)
    print(json.dumps(written, indent=1, sort_keys=True))
    print("PIN_WRITTEN" if changed else "PIN_ALREADY_PRESENT_IDENTICAL")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PinError as error:
        print("PIN_REFUSED: %s" % error, file=sys.stderr)
        sys.exit(1)
