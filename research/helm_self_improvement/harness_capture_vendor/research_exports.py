"""Exact Harness persistence functions with an explicit research-only backend.

Only the named function ASTs are loaded. Production account/storage imports,
environment-default destinations, verdict generation and harvest are excluded.
This uses the legacy local packet/hash-log path; it is NOT S3 Object Lock.
The existing TrustedHost supplies custody and independently anchors the files.
"""
import ast
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
WRITER_SHA="5c66026cff30adb133ce23e94c968cb86104608a5fef9d304253b706615079e3"
FUNCTIONS=("evidence_packet_without_hashes_sha256", "append_evidence_packet_hash_log_entry",
           "write_evidence_packet_to_store", "load_evidence_packet_from_store",
           "_sha256_json", "_canonical_json", "_packet_without_hashes_sha256",
           "_safe_trace_id", "_packet_path", "_hash_log_path", "_write_packet_to_store",
           "_load_packet_from_store", "_append_hash_log_entry", "_last_hash_log_entry_sha256",
           "_load_hash_log_entry", "_iter_hash_log_entries", "_hash_log_lines_are_parseable",
           "_hash_log_entry_sha256")


def local_evidence_functions(destination):
    raw=(HERE/"cas_harness_merged_evidence_packets.py").read_bytes()
    if hashlib.sha256(raw).hexdigest()!=WRITER_SHA:raise ValueError("HARNESS_WRITER_SOURCE_CHANGED")
    nodes={n.name:n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
    tree=ast.Module(body=[ast.ImportFrom(module="__future__",names=[ast.alias(name="annotations")],level=0)]
                    +[nodes[name] for name in FUNCTIONS],type_ignores=[])
    ast.fix_missing_locations(tree)
    namespace={"hashlib":hashlib,"json":json,"Path":Path,"datetime":datetime,"UTC":UTC,
               "active_evidence_packet_storage_scope":lambda:None,
               "_packet_store_dir":lambda:Path(destination),
               "ImmutableEvidenceConflict":ValueError}
    exec(compile(tree,"PINNED_HARNESS_LOCAL_EVIDENCE_EXPORTS","exec"),namespace)
    return SimpleNamespace(**{name:namespace[name] for name in FUNCTIONS})


def definition_lock():
    from .cas_harness_tks_definition_lock import tks_definition_lock_status
    return tks_definition_lock_status(
        definition_path=HERE/"tks_owner_locked_definitions_20260603.json",
        probe_bundle_manifest_path=HERE/"tks_definition_probe_bundle_manifest.v1.json")
