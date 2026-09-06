"""Analyze the pinned AWS JSON export. Never import SQLite or native libraries."""
import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from zipfile import ZipFile

JOB = "cas-meta2-20260906162339-56837284"
SOURCE = "37c591f3d6ae0606b27334c26d4392e0da94c675"
PLAN_SHA = "4b30978655ce99867b86f85d7eeab1575b9e6d735f259aa6a37084e886be0446"
ORIGINAL_JOB = "cas-meta2-20260906155525-195f5ad8"
ORIGINAL_ARCHIVE = "39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f"
DB_SHA = "41e3d9636cc9ffc026a87ca4bae3901cbf58dcff3c17039229c742f8898f14b2"
DB_BYTES = 1523712
DB_MEMBER = "qualification/cases/case_00/candidate_03/native.db"
EXPERIMENT = {"profile": "native_failure_sqlite_inspection_v8", "entrypoint": "read_only_sqlite_export"}
TABLES = frozenset(("store_metadata", "artifacts", "state_versions", "model_versions",
    "trace_events", "commit_receipts", "published_effects", "memory_records", "repair_frames",
    "repair_outcomes", "transition_batches", "causes", "candidate_effects", "verifier_receipts",
    "qualification_receipts", "state_intents", "model_intents", "memory_intents",
    "rejection_audits", "active_head"))
PHASES = ["READ", "CANDIDATE", "READINESS", "ROUTE", "EXECUTE", "OBSERVE",
          "VERIFY", "DIAGNOSE", "EMIT", "COMMIT", "TRACE"]
EXPECTED_CJTS = ["A", "B", "C", "R", "C", "R"]
LABELS = {"A": "L1", "B": "L3", "C": "L2", "R": "L1"}
MAX_BYTES = 32 * 1024**2
BOUNDARY = ("Saved-image JSON and hash/link examination only. No SQLite connection, "
    "tensor decoding, neural replay, new native execution, training or qualification. "
    "This cannot recover state that was never captured in the standalone image.")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(raw):
    return sha256(raw).hexdigest()


def loads(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False, "NONFINITE_JSON"))


def no_floats(value):
    if isinstance(value, dict):
        require(all(type(k) is str and k for k in value), "AUTHORITATIVE_JSON_KEYS")
        for child in value.values():
            no_floats(child)
    elif isinstance(value, list):
        for child in value:
            no_floats(child)
    else:
        require(value is None or type(value) in (str, int, bool), "AUTHORITATIVE_JSON_TYPE")


def canonical(value):
    no_floats(value)
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def payload(row, key="payload_json"):
    require(type(row.get(key)) is str, "PAYLOAD_TEXT_REQUIRED")
    raw = row[key].encode("ascii")
    hash_key = "public_payload_sha256" if key == "public_payload_json" else "payload_sha256"
    require(digest(raw) == row.get(hash_key), "PAYLOAD_HASH_MISMATCH")
    value = loads(raw)
    no_floats(value)
    require(type(value) is dict, "PAYLOAD_OBJECT_REQUIRED")
    return value


def unique_rows(rows, key):
    result = {}
    for row in rows:
        require(key in row and row[key] not in result, "DUPLICATE_OR_MISSING_ROW_ID:" + key)
        result[row[key]] = row
    return result


def read_packet(path, expected_sha):
    require(re.fullmatch("[a-f0-9]{64}", expected_sha), "ARCHIVE_SHA_REQUIRED")
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_BYTES,
            "BOUNDED_REGULAR_ARCHIVE_REQUIRED")
    raw = path.read_bytes()
    require(digest(raw) == expected_sha, "ARCHIVE_HASH_MISMATCH")
    with ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        require(len(names) <= 32 and len(names) == len(set(names)) ==
                len({n.casefold() for n in names}), "DUPLICATE_OR_EXCESSIVE_MEMBERS")
        require(sum(i.file_size for i in infos) <= MAX_BYTES, "EXPANDED_PACKET_BOUND")
        for item in infos:
            name = item.filename
            parts = name.split("/")
            require(not item.is_dir() and name == item.orig_filename and
                    not PurePosixPath(name).is_absolute() and
                    not any(p in ("", ".", "..") for p in parts) and
                    "\\" not in name and ":" not in name and "\x00" not in name and
                    not item.flag_bits & 1 and
                    stat.S_IFMT(item.external_attr >> 16) in (0, stat.S_IFREG),
                    "UNSAFE_ZIP_MEMBER")
        index_name = "artifact_collection_receipt.json"
        require(index_name in names, "COLLECTION_RECEIPT_MISSING")
        index = loads(archive.read(index_name))
        require(index.get("job") == JOB and index.get("source_sha") == SOURCE and
                index.get("parent_source_sha") == SOURCE and index.get("experiment") == EXPERIMENT,
                "COLLECTION_IDENTITY")
        require(type(index.get("files")) is dict and
                set(index["files"]) == set(names) - {index_name}, "EXACT_COLLECTION_INDEX")
        files = {}
        for name, identity in index["files"].items():
            value = archive.read(name)
            require(identity == {"bytes": len(value), "sha256": digest(value)},
                    "COLLECTION_MEMBER_HASH:" + name)
            files[name] = value
        receipt = loads(files["inspection/receipt.json"])
        require(receipt.get("job") == JOB and receipt.get("source_sha") == SOURCE and
                receipt.get("parent_source_sha") == SOURCE and receipt.get("experiment") == EXPERIMENT and
                receipt.get("schema") == "cas-meta2-native-failure-inspection/8",
                "EXPORT_RECEIPT_IDENTITY")
        return index, receipt, files, {"path": str(path.resolve()), "bytes": len(raw),
                                     "sha256": expected_sha, "indexed_files": len(files)}


def examine_export(export, receipt):
    require(export.get("job") == JOB and export.get("source_sha") == SOURCE and
            export.get("parent_source_sha") == SOURCE and
            export.get("plan_sha256") == receipt.get("plan_sha256") == PLAN_SHA, "EXPORT_IDENTITY")
    require(export.get("database") == receipt.get("database"), "DATABASE_IDENTITY_AGREEMENT")
    database = export["database"]
    require(database.get("sha256") == DB_SHA and database.get("bytes") == DB_BYTES and
            database.get("archive_sha256") == ORIGINAL_ARCHIVE and database.get("member") == DB_MEMBER and
            database.get("sidecars_present") is False and
            database.get("historical_uncaptured_state_recovered") is False, "EXACT_DATABASE_PIN")
    require(export.get("quick_check") == "ok" and export.get("read_only_uri") is True and
            export.get("query_only") is True and export.get("trusted_schema") is False and
            export.get("authorizer_select_only") is True, "READ_ONLY_EXPORT_RECEIPTS")
    require(set(export.get("tables", {})) == TABLES, "EXACT_TABLE_SET")
    schema = export.get("schema", [])
    triggers = {table + "_immutable_" + action for table in TABLES - {"store_metadata", "active_head"}
                for action in ("update", "delete")}
    require(len(schema) == 56 and {r["name"] for r in schema if r["type"] == "table"} == TABLES and
            {r["name"] for r in schema if r["type"] == "trigger"} == triggers and
            all(r["type"] in ("table", "trigger") for r in schema), "EXPORTED_SCHEMA_OBJECTS")
    rows, documents, hash_counts = {}, {}, {"payload_json": 0, "public_payload_json": 0, "opaque_blobs": 0}
    for table, saved in export["tables"].items():
        columns = saved["columns"]
        current = saved["rows"]
        require(len(columns) == len(set(columns)) and saved["row_count"] == len(current) <= 10000,
                "EXPORTED_ROW_SHAPE")
        require(all(set(row) == set(columns) for row in current), "EXPORTED_COLUMNS")
        rows[table] = current
        documents[table] = []
        for row in current:
            if "payload_json" in row:
                documents[table].append(payload(row))
                hash_counts["payload_json"] += 1
            if "public_payload_json" in row:
                payload(row, "public_payload_json")
                hash_counts["public_payload_json"] += 1
            for value in row.values():
                if isinstance(value, dict):
                    require(set(value) == {"encoding", "bytes", "sha256", "data"} and
                            value["encoding"] == "base64", "OPAQUE_BLOB_SHAPE")
                    blob = base64.b64decode(value["data"], validate=True)
                    require(len(blob) == value["bytes"] and digest(blob) == value["sha256"],
                            "OPAQUE_BLOB_HASH")
                    if table == "artifacts":
                        # Frozen artifacts.py:59 binds metadata plus bytes; its
                        # artifact SHA is intentionally not the raw BLOB SHA.
                        metadata = loads(row["metadata_json"])
                        metadata_text = json.dumps(metadata, ensure_ascii=True, sort_keys=True,
                                                   separators=(",", ":"), allow_nan=False)
                        require(type(metadata) is dict and metadata_text == row["metadata_json"],
                                "ARTIFACT_METADATA_CANONICAL")
                        header = json.dumps({"encoding": row["encoding"], "kind": row["kind"],
                            "media_type": row["media_type"], "metadata": metadata,
                            "payload_byte_length": len(blob)}, ensure_ascii=True, sort_keys=True,
                            separators=(",", ":"), allow_nan=False).encode("ascii")
                        bound = digest(header + b"\n" + blob)
                        require(row.get("sha256") == bound and row.get("byte_length") == len(blob) and
                                row.get("artifact_id") == "artifact-" + bound[:24], "ARTIFACT_BOUND_IDENTITY")
                    hash_counts["opaque_blobs"] += 1
    total = sum(len(v) for v in rows.values())
    require(total == export.get("total_rows") == receipt.get("total_rows") and total <= 50000,
            "TOTAL_ROW_COUNT")
    counts = {name: len(value) for name, value in rows.items()}
    require(counts == receipt.get("table_counts"), "TABLE_COUNT_RECEIPT")
    metadata = unique_rows(rows["store_metadata"], "key")
    require(metadata.get("schema_version", {}).get("value") == "cas.neural-cjt.sqlite-store/0.2",
            "STORE_SCHEMA_VERSION")
    commits = unique_rows(rows["commit_receipts"], "receipt_id")
    traces = sorted(rows["trace_events"], key=lambda r: r["sequence"])
    require(0 < len(traces) <= 6 and len(commits) == len(traces), "TRACE_COMMIT_COUNT")
    for value in rows.values():
        if value and "record_id" in value[0]:
            unique_rows(value, "record_id")
    states = unique_rows(rows["state_versions"], "state_digest")
    previous_digest = previous_state = None
    previous_effects, tick_rows, selected = {}, [], []
    for ordinal, row in enumerate(traces, 1):
        trace = payload(row)
        require(row["sequence"] == ordinal and type(trace.get("tick")) is int and trace["tick"] == ordinal,
                "ONE_BASED_CONTIGUOUS_TICKS")
        require(trace.get("trace_digest") == row["trace_digest"] and trace.get("trace_id") == row["trace_id"] and
                trace.get("previous_trace_digest") == row["previous_trace_digest"] == previous_digest and
                trace.get("pre_state_digest") == row["pre_state_digest"] and
                trace.get("post_state_digest") == row["post_state_digest"], "TRACE_ROW_IDENTITY")
        require(previous_state is None or trace["pre_state_digest"] == previous_state, "STATE_CHAIN")
        for state_key, digest_key in (("state_before", "pre_state_digest"), ("state_after", "post_state_digest")):
            state_digest = trace[digest_key]
            require(state_digest in states and payload(states[state_digest]) == trace[state_key], "STORED_STATE_TRACE_JOIN")
        body = {k: v for k, v in trace.items() if k not in ("trace_id", "trace_digest")}
        require(trace["trace_id"] == "trace-" + digest(canonical(body))[:24] and
                trace["trace_digest"] == digest(canonical({**body, "trace_id": trace["trace_id"]})),
                "TRACE_CANONICAL_DIGEST")
        require(trace.get("schema_version") == "cas.neural-cjt.tick-trace/0.2" and
                trace.get("contract_type") == "TICK_TRACE" and trace.get("sealed") is True,
                "TRACE_CONTRACT")
        phases = trace["phases"]
        require([p["phase"] for p in phases] == PHASES and all(p["tick"] == ordinal for p in phases),
                "ELEVEN_PHASE_ORDER")
        phases = {p["phase"]: p for p in phases}
        commit_id = trace["commit_receipt_id"]
        require(commit_id in commits, "TRACE_COMMIT_MISSING")
        commit_row = commits[commit_id]
        commit = payload(commit_row)
        require(commit_row["trace_digest"] == trace["trace_digest"] and
                commit_row["pre_state_digest"] == trace["pre_state_digest"] and
                commit_row["post_state_digest"] == trace["post_state_digest"] and
                commit.get("receipt_id") == commit_id and commit.get("trace_id") == trace["trace_id"] and
                commit.get("tick") == ordinal and commit.get("disposition") == "COMMITTED" and
                commit.get("authorized") is True and commit.get("atomic") is True,
                "COMMIT_TRACE_JOIN")
        owned = {}
        for table, id_key in (("candidate_effects", "candidate_effect_id"), ("verifier_receipts", "receipt_id"),
                              ("causes", "cause_id"), ("published_effects", "published_effect_id"),
                              ("repair_frames", "repair_id"), ("repair_outcomes", "outcome_id")):
            found = [record for record in rows[table] if record["commit_receipt_id"] == commit_id]
            owned[table] = [payload(record) for record in found]
            require(all(doc.get(id_key) == record["record_id"] for doc, record in zip(owned[table], found)),
                    "DOCUMENT_ROW_IDENTITY:" + table)
            embedded = [trace["cause"]] if table == "causes" else trace.get(table)
            if embedded is not None:
                require({d[id_key]: d for d in embedded} == {d[id_key]: d for d in owned[table]},
                        "TRACE_DOCUMENT_AGREEMENT:" + table)
        require(len(owned["candidate_effects"]) == len(owned["verifier_receipts"]) ==
                len(owned["causes"]) == 1, "SINGLE_NATIVE_OPERATION_REQUIRED")
        candidate, verifier, cause = (owned[name][0] for name in ("candidate_effects", "verifier_receipts", "causes"))
        cjt = candidate["producer_cjt_id"]
        require(cjt == EXPECTED_CJTS[ordinal - 1] and
                phases["EXECUTE"]["outputs"]["executed_cjt_ids"] == [cjt], "SEALED_ACTION_CJT_PREFIX")
        require(candidate["tick"] == verifier["tick"] == cause["tick"] == ordinal and
                candidate["parent_cause_id"] == verifier["cause_id"] == cause["cause_id"] == trace["cause_id"] and
                candidate["candidate_effect_id"] == verifier["candidate_effect_id"] and
                candidate["candidate_digest"] == verifier["candidate_effect_digest"],
                "CANDIDATE_VERIFIER_CAUSE_JOIN")
        evidence = [e for e in trace["semantic_evidence"] if e["evidence_id"] in verifier["evidence_refs"]]
        require(len(evidence) == 1, "UNAMBIGUOUS_AUTHORED_EVIDENCE")
        evidence = evidence[0]
        marker = "evidence-digest:" + evidence["evidence_digest"]
        evidence_body = {k: v for k, v in evidence.items() if k != "evidence_digest"}
        evidence_body["provenance"] = [p for p in evidence["provenance"] if p != marker]
        require(marker in evidence["provenance"] and marker in verifier["evidence_refs"] and
                digest(canonical(evidence_body)) == evidence["evidence_digest"], "EVIDENCE_DIGEST_BINDING")
        expected, actual = evidence["expected_content"], candidate["content"]
        require(expected["symbol"] == LABELS[cjt] and
                expected["operation_id"] == actual["operation_id"] == candidate["operation_id"] and
                expected["effect_kind"] == actual["effect_kind"], "AUTHORED_LABEL_CONTRACT")
        published_ids = [doc["published_effect_id"] for doc in owned["published_effects"]]
        require(set(published_ids) == set(trace["published_effect_ids"]) ==
                set(commit["published_effect_ids"]), "PUBLISHED_EFFECT_JOIN")
        for effect in owned["published_effects"]:
            require(effect["candidate_effect_id"] == candidate["candidate_effect_id"] and
                    effect["verifier_receipt_id"] == verifier["receipt_id"], "PUBLICATION_OWNERSHIP")
        parent_effect = cause.get("parent_effect_id")
        parent_tick = None if parent_effect is None else previous_effects.get(parent_effect)
        require((ordinal == 1 and parent_effect is None) or parent_tick == ordinal - 1,
                "SEALED_ACTION_INPUT_PREFIX")
        require(phases["VERIFY"]["outputs"]["dispositions"] == [verifier["disposition"]] and
                phases["DIAGNOSE"]["outputs"]["reason_codes"] == list(verifier["reason_codes"]),
                "PHASE_VERIFIER_AGREEMENT")
        returnable = verifier["disposition"] == "ACCEPT" and len(published_ids) == 1
        tick_rows.append({
            "tick": ordinal, "cjt": cjt, "parent_effect_id": parent_effect, "input_from_tick": parent_tick,
            "expected_content": expected, "decoded_content": actual,
            "disposition": verifier["disposition"], "semantic_outcome": verifier["semantic_outcome"],
            "reason_codes": verifier["reason_codes"], "repair_required": verifier["repair_required"],
            "published_effect_count": len(published_ids), "returnable_to_single_run_wrapper": returnable,
            "trace_id": trace["trace_id"], "trace_digest": trace["trace_digest"],
            "commit_receipt_id": commit_id, "candidate_effect_id": candidate["candidate_effect_id"],
            "verifier_receipt_id": verifier["receipt_id"],
            "operating_regions": phases["OBSERVE"]["outputs"]["operating_regions"],
            "repair_frames": owned["repair_frames"], "repair_outcomes": owned["repair_outcomes"],
        })
        selected.append({"trace": trace, "commit_row": commit_row, "owned_documents": owned})
        for effect_id in published_ids:
            previous_effects[effect_id] = ordinal
        previous_digest, previous_state = trace["trace_digest"], trace["post_state_digest"]
    heads = rows["active_head"]
    require(len(heads) == 1 and heads[0].get("singleton") == 1 and
            heads[0].get("trace_digest") == previous_digest and
            heads[0].get("state_digest") == previous_state and
            heads[0].get("commit_receipt_id") == tick_rows[-1]["commit_receipt_id"], "ACTIVE_HEAD_JOIN")
    final_trace = selected[-1]["trace"]
    require(heads[0].get("model_digest") == final_trace["post_model_digest"] and
            heads[0].get("state_version") == final_trace["state_after"]["state_version"], "ACTIVE_HEAD_VERSION")
    bad = [row for row in tick_rows if not row["returnable_to_single_run_wrapper"]]
    require(len(bad) <= 1 and (not bad or bad[0]["tick"] == len(tick_rows)), "NONRETURNABLE_IS_TERMINAL")
    return {
        "status": "SAVED_IMAGE_RECORDS_CHECKED", "database": database, "hash_checks": hash_counts,
        "table_counts": counts, "total_rows": total, "stored_committed_ticks_in_failed_attempt": len(tick_rows),
        "accepted_returnable_ticks_in_failed_attempt": sum(r["returnable_to_single_run_wrapper"] for r in tick_rows),
        "nonreturnable_stored_ticks": len(bad), "first_nonreturnable": bad[0] if bad else None,
        "ticks": tick_rows, "head": heads[0], "boundary": BOUNDARY,
        "neural_reproduction": False, "whole_task_qualification": False,
        "uncaptured_historical_state_recovered": False, "full_native_store_verifier_run": False,
    }, selected


def report_markdown(result):
    lines = ["# Saved native-failure record analysis", "", result["boundary"], ""]
    if result["status"] != "SAVED_IMAGE_RECORDS_CHECKED":
        return "\n".join(lines + ["The inspection packet did not support a completed record analysis.",
                                 "", "Status: " + result["status"], ""])
    first = result["first_nonreturnable"]
    if first:
        lines += [f"The first stored nonreturnable operation is tick {first['tick']}, CJT {first['cjt']}.",
                  f"Its recorded label is {first['decoded_content']['symbol']}; the authored expected label is "
                  f"{first['expected_content']['symbol']}. The verifier recorded {first['disposition']}: "
                  + ", ".join(first["reason_codes"]) + ".", ""]
    else:
        lines += ["No nonreturnable operation was found in this saved image. The reported failure remains unresolved.", ""]
    lines += [f"The failed full execution retained {result['stored_committed_ticks_in_failed_attempt']} committed native ticks; "
              f"{result['accepted_returnable_ticks_in_failed_attempt']} had accepted, singly published effects.",
              "These are not additional completed full tasks, a neural replay, or proof of training readiness.", "",
              "| Tick | CJT | Input tick | Expected | Recorded | Verifier | Published |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in result["ticks"]:
        lines.append(f"| {row['tick']} | {row['cjt']} | {row['input_from_tick']} | "
                     f"{row['expected_content']['symbol']} | {row['decoded_content']['symbol']} | "
                     f"{row['disposition']} | {row['published_effect_count']} |")
    lines += ["", "Checks: indexed packet bytes, exported payload hashes, opaque blob hashes, trace digests, "
              "eleven-phase order, contiguous ticks, state chain, final head, receipt ownership, "
              "candidate/effect/evidence links and the sealed R_CR operation/input prefix.",
              "The original 21 ticks in the four completed executions are separate evidence and are not re-audited here.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    script_path = Path(__file__).resolve()
    script_before = script_path.read_bytes()
    output = args.output.absolute()
    require(not output.exists() and ".." not in output.parts and
            output.parent.resolve() == script_path.parent and
            not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (output, *output.parents)),
            "FRESH_NONLINK_OUTPUT_REQUIRED")
    index, receipt, files, archive_identity = read_packet(args.archive, args.archive_sha256)
    result = {"status": "INSPECTION_INCOMPLETE_OR_FAILED", "boundary": BOUNDARY}
    selected = []
    if (index.get("returncode") == 0 and index.get("partial_evidence") is False and
            index.get("omitted_full_file_count") == 0 and
            receipt.get("status") == "NATIVE_FAILURE_DATABASE_EXPORTED" and
            receipt.get("input_unchanged") is True and receipt.get("failure") is None):
        require(receipt.get("training") is False and receipt.get("native_execution") is False and
                receipt.get("sqlite_read_only") is True and receipt.get("archive_sha256") == ORIGINAL_ARCHIVE and
                receipt.get("source_archive_sha256") == ORIGINAL_ARCHIVE, "RECEIPT_READ_ONLY_SCOPE")
        result, selected = examine_export(loads(files["inspection/export.json"]), receipt)
    result.update(result_archive=archive_identity, inspection_receipt=receipt, collection_receipt=index,
                  original_job=ORIGINAL_JOB, inspection_job=JOB, source_sha=SOURCE)
    input_after = args.archive.read_bytes()
    script_after = script_path.read_bytes()
    require(len(input_after) == archive_identity["bytes"] and digest(input_after) == archive_identity["sha256"],
            "INPUT_ARCHIVE_CHANGED_DURING_ANALYSIS")
    require(script_after == script_before, "ANALYZER_CHANGED_DURING_ANALYSIS")
    unchanged = {"input_archive_sha256_before": archive_identity["sha256"],
                 "input_archive_sha256_after": digest(input_after),
                 "analyzer_sha256_before": digest(script_before), "analyzer_sha256_after": digest(script_after),
                 "input_archive_unchanged": True, "analyzer_unchanged": True}
    result["unchanged_checks"] = unchanged
    output.mkdir(parents=True, exist_ok=False)
    outputs = {"analysis.json": encode(result),
               "selected_records.json": encode(selected),
               "REPORT.md": report_markdown(result).encode()}
    for name, raw in outputs.items():
        require(len(raw) <= MAX_BYTES, "OUTPUT_BOUND")
        with (output / name).open("xb") as stream:
            stream.write(raw)
    execution = {"schema": "native-failure-json-analysis-command/8",
                 "command": [sys.executable, *sys.argv], "finished_utc": datetime.now(timezone.utc).isoformat(),
                 "analyzer_sha256": digest(script_before), "unchanged_checks": unchanged,
                 "result_archive": archive_identity, "status": result["status"],
                 "files": {name: {"bytes": len(raw), "sha256": digest(raw)} for name, raw in outputs.items()},
                 "boundary": BOUNDARY}
    with (output / "command_receipt.json").open("xb") as stream:
        stream.write(encode(execution))
    print(json.dumps({"status": result["status"],
                      "stored_committed_ticks_in_failed_attempt": result.get("stored_committed_ticks_in_failed_attempt"),
                      "first_nonreturnable_tick": (result.get("first_nonreturnable") or {}).get("tick")}, sort_keys=True))
    return 0 if result["status"] == "SAVED_IMAGE_RECORDS_CHECKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
