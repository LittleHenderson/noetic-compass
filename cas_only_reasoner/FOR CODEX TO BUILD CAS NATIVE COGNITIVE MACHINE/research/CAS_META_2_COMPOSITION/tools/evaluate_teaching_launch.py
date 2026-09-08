"""Teacher-only evaluation of a pinned collected ZIP; no model/provider calls.

The original archive is retained. Both prediction packets must pass the frozen
scorer's public-only admission and agree before either opens private targets.
An incomplete guest run produces an exposure summary, never a final score.
"""
import argparse
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import re
import stat
import sys
import zipfile

LIMIT = 2684354560
FORBIDDEN = frozenset(("torch", "numpy", "sqlite3", "_sqlite3", "casformer", "cas_cjt",
                       "cas_meta", "boto3", "botocore", "tensorflow", "jax"))


def require(condition, reason):
    if not condition:
        raise ValueError("COLLECTED_TEACHING:" + reason)


def _safe(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (path, *path.parents)), "LINK_PATH_REJECTED")
    return path


def _file_hash(path, maximum=LIMIT):
    path = _safe(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= maximum, "FILE_BOUND_OR_TYPE")
    digest, length = sha256(), 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            length += len(chunk)
            require(length <= maximum, "STREAM_BYTE_LIMIT")
            digest.update(chunk)
    require(length == info.st_size and path.stat().st_size == info.st_size, "FILE_CHANGED_DURING_READ")
    return digest.hexdigest(), length


def extract_verified(archive, output, expected_sha256):
    """Fresh, streaming, case-collision-safe extraction; no archive deletion."""
    require(re.fullmatch(r"[0-9a-f]{64}", expected_sha256 or "") is not None, "ARCHIVE_PIN_REQUIRED")
    before, _ = _file_hash(archive)
    require(before == expected_sha256, "ARCHIVE_PIN_MISMATCH")
    root = _safe(output)
    require(not root.exists() and root.parent.is_dir(), "FRESH_EXTRACTION_ROOT_REQUIRED")
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        require(0 < len(entries) <= 20000, "ARCHIVE_MEMBER_COUNT_BOUND")
        names, directories, total = set(), set(), 0
        for entry in entries:
            require(entry.orig_filename == entry.filename, "ARCHIVE_PATH_REJECTED")
            name = entry.filename.rstrip("/") if entry.is_dir() else entry.filename
            parts = name.split("/")
            require(re.fullmatch(r"[A-Za-z0-9_./-]+", name or "") is not None
                    and parts[0] in {"train", "predict1", "predict2", "driver", "bootstrap_evidence", "input"}
                    and all(part not in ("", ".", "..") and not part.endswith(".") for part in parts)
                    and all(not re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part, re.I) for part in parts),
                    "ARCHIVE_PATH_REJECTED")
            require(name.casefold() not in names, "ARCHIVE_CASE_OR_DUPLICATE_COLLISION")
            names.add(name.casefold())
            kind = stat.S_IFMT(entry.external_attr >> 16)
            require(kind in ((0, stat.S_IFDIR) if entry.is_dir() else (0, stat.S_IFREG))
                    and not entry.flag_bits & 1 and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                    "ARCHIVE_LINK_TYPE_OR_ENCODING_REJECTED")
            if entry.is_dir():
                require(entry.file_size == 0, "DIRECTORY_PAYLOAD_REJECTED")
                directories.add(name.casefold())
            total += entry.file_size
            require(total <= LIMIT, "EXPANDED_ARCHIVE_BYTE_LIMIT")
        for name in names:
            require(not any(prefix in names and prefix not in directories
                        for prefix in ["/".join(name.split("/")[:i]) for i in range(1, len(name.split("/")))]),
                    "ARCHIVE_FILE_DIRECTORY_COLLISION")
        root.mkdir()
        observed = 0
        for entry in entries:
            target = _safe(root / entry.filename)
            require(target.is_relative_to(root), "ARCHIVE_PATH_ESCAPE")
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            _safe(target)
            count = 0
            with package.open(entry) as source, target.open("xb") as destination:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    count += len(chunk)
                    observed += len(chunk)
                    require(count <= entry.file_size and observed <= LIMIT, "EXPANDED_STREAM_BYTE_LIMIT")
                    destination.write(chunk)
            require(count == entry.file_size, "ARCHIVE_MEMBER_SIZE_MISMATCH")
    require(_file_hash(archive)[0] == before, "ARCHIVE_CHANGED_DURING_EXTRACTION")
    return {"root": str(root), "archive_sha256": before, "expanded_bytes": observed,
            "members": len(entries), "original_archive_retained": True}


def evaluate_collected(parent_result, archive, complete_marker, material_root, output, *,
                       parent_sha256, archive_sha256, complete_sha256, reader=None):
    from cas_meta2.teaching_cycle import evaluation as scorer
    reads = scorer._Reader(reader)
    parent = reads.json(parent_result, parent_sha256)
    complete = reads.json(complete_marker, complete_sha256)
    require(type(parent) is dict and parent.get("schema") == "cas-teaching-cycle-parent-lifecycle/2"
            and parent.get("status") in ("TEACHING_CYCLE_COLLECTED_NOT_SCORED", "TEACHING_INCOMPLETE", "TEACHING_CYCLE_BLOCKED"),
            "PARENT_RESULT_INVALID")
    bindings = parent.get("bindings")
    require(type(bindings) is dict and all(scorer._pin(bindings.get(key)) for key in (
        "source_sha256", "manifest_sha256", "archive_sha256", "material_receipt_sha256", "public_sets_sha256", "scorer_sha256")),
        "PARENT_BINDINGS_REQUIRED")
    require(_file_hash(scorer.__file__, 1024 * 1024)[0] == bindings["scorer_sha256"], "FROZEN_SCORER_SOURCE_MISMATCH")
    require(type(complete) is dict and complete.get("schema") == "cas-teaching-guest-complete/1"
            and complete.get("job") == parent.get("job") and complete.get("run_id") == parent.get("job")
            and complete.get("source_sha256") == bindings["source_sha256"]
            and complete.get("manifest_sha256") == bindings["manifest_sha256"]
            and complete.get("material_sha256") == bindings["material_receipt_sha256"], "COMPLETE_IDENTITY_MISMATCH")
    require(type(parent.get("archive")) is dict and parent["archive"].get("sha256") == archive_sha256
            and parent["archive"].get("local_bytes_verified") is True
            and complete.get("artifact") == {"key": "results/artifacts.zip", "sha256": archive_sha256,
                                               "bytes": parent["archive"].get("bytes")}, "PARENT_ARCHIVE_BINDING_MISMATCH")
    require(_file_hash(archive)[1] == parent["archive"]["bytes"], "ARCHIVE_BYTES_MISMATCH")
    root = _safe(output)
    require(not root.exists() and root.parent.is_dir() and not root.is_relative_to(_safe(material_root)), "FRESH_OUTPUT_OUTSIDE_MATERIAL_REQUIRED")
    root.mkdir()
    extracted = root / "extracted"
    extraction = extract_verified(archive, extracted, archive_sha256)
    status = complete.get("status")
    source_copy = extracted / "input/source.zip"
    source_available = source_copy.is_file()
    campaign_path, campaign_root = extracted / "train/campaign_summary.json", extracted / "train/campaign"
    if source_available:
        require(_file_hash(source_copy)[0] == bindings["archive_sha256"], "WORKER_BUNDLE_ARCHIVE_MISMATCH")
    else:
        require(status == "BLOCKED" and not campaign_path.is_file(), "SOURCE_COPY_REQUIRED_FOR_TEACHING_RESULTS")
    common = {"schema": "cas-teaching-collected-evaluation/1", "parent_sha256": parent_sha256,
              "archive_sha256": archive_sha256, "complete_sha256": complete_sha256, "extraction": extraction,
              "source_copy_available": source_available,
              "native_execution": "UNEXECUTED", "retention_after_intervening_learning": "UNEXECUTED"}
    if status in ("TEACHING_INCOMPLETE", "BLOCKED"):
        summary = None
        if campaign_path.is_file():
            require(scorer._pin(complete.get("campaign_summary_sha256")), "PARTIAL_CAMPAIGN_PIN_REQUIRED")
            campaign = reads.json(campaign_path, complete.get("campaign_summary_sha256"))
            require(campaign.get("source_sha256") == bindings["source_sha256"]
                    and campaign.get("manifest_sha256") == bindings["manifest_sha256"]
                    and campaign.get("run_id") == parent["job"], "PARTIAL_CAMPAIGN_IDENTITY_MISMATCH")
            summary = {arm: {key: report.get(key) for key in ("run_id", "cursor", "allocation_finished", "exposure",
                        "observed_optimizer_steps", "observed_teaching_examples", "development_curve")}
                       for arm, report in campaign.get("arms", {}).items()}
        report = {**common, "status": "PARTIAL_EXPOSURE_ONLY" if source_available else "INFRASTRUCTURE_FAILURE_ONLY", "guest_status": status,
                  "exposure": summary, "private_targets_opened": False, "final_scores": None,
                  "boundary": "Recorded worker exposure only, not independently verified learning."}
    else:
        require(status == "COMPLETE" and parent["status"] == "TEACHING_CYCLE_COLLECTED_NOT_SCORED", "FULL_PARENT_AND_GUEST_COMPLETION_REQUIRED")
        require(_file_hash(extracted / "input/public.json")[0] == bindings["public_sets_sha256"], "RELEASED_PUBLIC_FILE_MISMATCH")
        require(complete.get("training_ready_sha256") == parent.get("training_ready_sha256")
                and complete.get("campaign_summary_sha256") == parent.get("campaign_summary_sha256")
                and complete.get("prediction_seals") == parent.get("prediction_seals"), "PARENT_GUEST_TRAINING_BINDING_MISMATCH")
        seals = complete["prediction_seals"]
        require(type(seals) is list and len(seals) == 2 and [row.get("run_index") for row in seals] == [1, 2], "TWO_PREDICTION_SEALS_REQUIRED")
        admitted, arguments = [], []
        for index, seal in enumerate(seals, 1):
            require(seal.get("key") == f"results/predict{index}/prediction_seal.json", "PREDICTION_SEAL_KEY_MISMATCH")
            args = dict(prediction_root=extracted / f"predict{index}", material_root=material_root,
                        campaign_summary_path=campaign_path, campaign_root=campaign_root,
                        expected_seal_sha256=seal["sha256"], expected_campaign_sha256=complete["campaign_summary_sha256"],
                        expected_material_sha256=bindings["material_receipt_sha256"], expected_source_sha256=bindings["source_sha256"],
                        expected_bundle_manifest_sha256=bindings["manifest_sha256"])
            admitted.append(scorer._admit(**args, reader=reads))
            arguments.append(args)
        require(admitted[0][2] == admitted[1][2], "FRESH_READER_PREDICTIONS_CHANGED")
        pids = []
        for name in sorted(scorer.PREDICTION_NAMES):
            first = reads.json(extracted / "predict1" / name)
            second = reads.json(extracted / "predict2" / name)
            require(all(first[key] == second[key] for key in ("checkpoint", "public_sha256", "predictions", "arm", "phase", "split", "run_id", "source_sha256")),
                    "FRESH_READER_IDENTITY_CHANGED")
            require(first["pid"] != second["pid"], "FRESH_READER_PID_REUSED")
            pids = [first["pid"], second["pid"]]
        # Both complete packets have passed, including equality, before this gate.
        scores = [scorer.score_packet(**args, reader=reader) for args in arguments]
        score_files = [scorer.write_fresh_json(root / f"reader{index}_score.json", value) for index, value in enumerate(scores, 1)]
        report = {**common, "status": "TWO_READERS_SCORED", "reader_comparison": {
            "prediction_files_compared": 24, "predictions_equal": True, "checkpoint_and_public_identities_equal": True,
            "distinct_reported_pids": pids, "boundary": "Packet and recorded process identity agreement, not retention after new learning."},
            "scores": score_files, "comparison": scores[0]["comparison"],
            "private_targets_opened": True, "provider_identity_proved": False}
    receipt = scorer.write_fresh_json(root / "evaluation.json", report)
    return {"report": report, "receipt": receipt}


def main(argv=None):
    require(not FORBIDDEN.intersection(sys.modules), "FORBIDDEN_MODULE_ALREADY_LOADED")
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in FORBIDDEN:
                raise RuntimeError("COLLECTED_TEACHING:FORBIDDEN_IMPORT:" + fullname)
    sys.meta_path.insert(0, Guard())
    def audit(event, args):
        if event.startswith("socket.") or event == "sqlite3.connect":
            raise RuntimeError("COLLECTED_TEACHING:FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("parent-result", "archive", "complete-marker", "material-root", "output", "parent-sha256", "archive-sha256", "complete-sha256"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    result = evaluate_collected(**vars(args))
    print(json.dumps({"status": result["report"]["status"], **result["receipt"]}))
    require(not FORBIDDEN.intersection(sys.modules), "FORBIDDEN_MODULE_LOADED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
