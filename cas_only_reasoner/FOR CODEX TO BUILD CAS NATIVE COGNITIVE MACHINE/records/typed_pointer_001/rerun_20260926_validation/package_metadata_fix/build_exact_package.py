"""PROSPECTIVE: exact-source package build with public-only Git metadata scope.

No scientific file is patched. During this process only, intercept the exact
_committed_rows ls-tree directory-size request and ask real Git for the same
inventory's exact file paths instead. Original per-row object/size/hash checks
still run. Never supplies fabricated Git output or adds absent protected blobs.
This script has not been executed; new paid admission is required.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

SOURCE = "a5fcf527b5f2c47a3a9b1f170977c55371845af0"


def digest(raw):
    return sha256(raw).hexdigest()


def run(project_root, output, payload_manifest, payload_manifest_sha256, source_sha):
    if source_sha != SOURCE:
        raise ValueError("EXACT_A5FCF527_SOURCE_REQUIRED")
    project = project_root.resolve(strict=True)
    transport_raw = payload_manifest.read_bytes()
    if digest(transport_raw) != payload_manifest_sha256:
        raise ValueError("FROZEN_PAYLOAD_MANIFEST_HASH")
    transport = json.loads(transport_raw)
    if transport["source_commit"] != SOURCE:
        raise ValueError("TRANSPORT_SOURCE_COMMIT")
    if transport["schema"] not in {"helm.validation.payload/1", "helm.package-only.payload/1"}:
        raise ValueError("KNOWN_PUBLIC_PAYLOAD_SCHEMA_REQUIRED")
    sys.path[:0] = [str(project), str(project / "research/CAS_META_2_COMPOSITION")]
    from aws import typed_pointer_launch as launch
    from cas_meta2.typed_teaching import pointer_contract as contract

    original_git = launch.shared._run_git
    if original_git(["rev-parse", "HEAD"], launch.GIT_ROOT).decode().strip() != SOURCE:
        raise ValueError("CHECKOUT_SOURCE_COMMIT")
    if project != launch.PROJECT.resolve():
        raise ValueError("EXPLICIT_PROJECT_ROOT")
    before = contract.input_inventory(project)
    names = [row["path"] for row in before]
    if len(names) != len(set(names)):
        raise ValueError("UNIQUE_PUBLIC_INVENTORY_REQUIRED")
    expected_members = set(launch.package_data_files(rows=before))
    transported = {row["path"]: row for row in transport["files"]}
    prefix = launch.shared.GIT_PREFIX
    source_bindings = []
    for name in sorted(expected_members):
        row = transported.get("repo/" + prefix + name)
        if row is None:
            raise ValueError("MEMBER_NOT_IN_ORIGINAL_PUBLIC_ALLOWLIST:" + name)
        actual = (project / name).read_bytes()
        committed = original_git(["-c", "core.autocrlf=false", "show", SOURCE + ":" + prefix + name], launch.GIT_ROOT)
        if len(actual) != row["bytes"] or digest(actual) != row["sha256"] or actual != committed:
            raise ValueError("EXACT_SOURCE_BYTES_REQUIRED:" + name)
        source_bindings.append({"path": name, "bytes": len(actual), "sha256": digest(actual),
                                "equal_to_original_commit": True})
    exact_paths = [prefix + name for name in names]
    directory_paths = sorted({prefix + name.split("/")[0] + "/" for name in names})
    expected_query = ["-c", "core.autocrlf=false", "ls-tree", "-r", "-l", "-z", SOURCE, "--", *directory_paths]
    exact_query = ["-c", "core.autocrlf=false", "ls-tree", "-r", "-l", "-z", SOURCE, "--", *exact_paths]
    calls = []

    def inventory_metadata_only(arguments, cwd):
        if list(arguments) != expected_query:
            return original_git(arguments, cwd)
        if Path(cwd).resolve() != launch.GIT_ROOT.resolve():
            raise ValueError("METADATA_QUERY_REPOSITORY")
        if contract.input_inventory(project) != before:
            raise ValueError("INVENTORY_CHANGED_DURING_BUILD")
        raw = original_git(exact_query, cwd)
        found = {}
        for entry in raw.split(b"\0"):
            if not entry:
                continue
            metadata, separator, name = entry.partition(b"\t")
            fields = metadata.split()
            if not separator or len(fields) != 4 or fields[1] != b"blob":
                raise ValueError("REAL_GIT_BLOB_METADATA_REQUIRED")
            path = name.decode("utf-8")
            if path in found or path not in exact_paths or not fields[3].isdigit():
                raise ValueError("EXACT_REAL_GIT_METADATA_SCOPE")
            found[path] = {"object_id": fields[2].decode("ascii"), "bytes": int(fields[3])}
        if set(found) != set(exact_paths):
            raise ValueError("MISSING_PUBLIC_INVENTORY_METADATA")
        calls.append({"original_argv": expected_query, "actual_git_argv": exact_query,
                      "returned_path_count": len(found), "git_stdout_sha256": digest(raw),
                      "real_git_output": True, "fabricated_output": False})
        return raw

    launch.shared._run_git = inventory_metadata_only
    try:
        committed_rows = launch.frozen_inputs(SOURCE)
        if committed_rows != before:
            raise ValueError("COMMITTED_INPUT_INVENTORY_CHANGED")
        if set(launch.package_data_files(rows=committed_rows)) != expected_members:
            raise ValueError("PACKAGE_MEMBER_SET_CHANGED")
        evidence_before = launch.evidence_contract()
        if evidence_before["required_count"] != 128:
            raise ValueError("REQUIRED_ARTIFACT_COUNT_MUST_REMAIN_128")
        receipt = launch.build_pointer_package(output, source_sha=SOURCE)
        if not calls:
            raise ValueError("SCOPED_METADATA_QUERY_NOT_EXERCISED")
        after = contract.input_inventory(project)
        if after != before or launch.evidence_contract() != evidence_before:
            raise ValueError("SOURCE_OR_EVIDENCE_CONTRACT_CHANGED")
        manifest = receipt["manifest"]
        if manifest["source_sha"] != SOURCE or manifest["inputs"] != before:
            raise ValueError("SHIPPED_SOURCE_INPUTS_CHANGED")
        if manifest["typed_design"]["passes"] != 20 or manifest["typed_design"]["optimizer_config"]["learning_rate"] != 0.003:
            raise ValueError("SCIENTIFIC_DESIGN_CHANGED")
        if not {"results/evidence/main_checkpoint_1470.pt", "results/evidence/main_checkpoint_1470.json"}.issubset(
                set(launch.run_evidence.contract_keys(evidence_before))):
            raise ValueError("MANDATORY_PASS10_STATE_CHANGED")
    finally:
        launch.shared._run_git = original_git

    report = {
        "schema": "helm.package-only.public-metadata-scope/1",
        "source_sha": SOURCE, "status": "PACKAGE_BUILT_WITH_EXACT_SOURCE_AND_REAL_GIT",
        "script_sha256": digest(Path(__file__).read_bytes()),
        "payload_manifest_sha256": payload_manifest_sha256,
        "scientific_files_modified": False, "scientific_source_bindings": source_bindings,
        "scope": "Only the live packaging process's exact ls-tree directory metadata query was narrowed to the already-declared inventory file paths; all other Git calls were unchanged.",
        "original_per_row_object_size_sha256_validation": "UNCHANGED_AND_EXECUTED",
        "protected_blob_bodies_added": False, "git_objects_synthesized": False,
        "required_artifact_count": 128, "metadata_calls": calls,
        "package_archive_sha256": receipt["archive_sha256"],
        "package_manifest_sha256": receipt["manifest_sha256"],
        "package_member_count": receipt["member_count"],
        "limits": "Packaging evidence only; no test rerun, CUDA validation, training or scientific result.",
    }
    (output / "metadata_scope_receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "source_sha": SOURCE,
                      "archive_sha256": receipt["archive_sha256"], "metadata_calls": len(calls)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--payload-manifest", type=Path, required=True)
    parser.add_argument("--payload-manifest-sha256", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    run(args.project_root, args.output, args.payload_manifest, args.payload_manifest_sha256, args.source_sha)
