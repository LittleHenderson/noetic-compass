"""Build or verify the byte-bound publication packet for condition_skill_v9.

BUILD resolves a committed source SHA, enumerates its changed paths, reads each
file's exact Git object bytes with `git -c core.autocrlf=false`, and writes a
fresh LF-only packet. It never reads working-tree bytes.

VERIFY re-checks a packet: strict duplicate-key JSON, schema/type/path safety,
exact changed-file coverage of the source commit, source-commit ancestry under
HEAD, and byte-count/SHA-256/Git-blob identity for every bound file. It writes
nothing.

This tool is evidence plumbing only: it does not run neural, provider, or
database work and it creates no reservation.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

SCHEMA = "cas-meta2-condition-skill-publication-packet/9"
REPORT_SCHEMA = "cas-meta2-condition-skill-publication-verification/9"
ALLOWED_PREFIX = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
EXPLICITLY_ALLOWED_PATHS = ("CHANGELOG.md",)


def _path_allowed(path):
    return path.startswith(ALLOWED_PREFIX) or path in EXPLICITLY_ALLOWED_PATHS


def require(condition, code):
    if not condition:
        raise ValueError(code)


def strict_load(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "PACKET_DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: require(False, "PACKET_NONFINITE_JSON"))
    require(type(value) is dict, "PACKET_OBJECT_REQUIRED")
    return value


def validate_structure(packet):
    require(packet.get("schema") == SCHEMA, "PACKET_SCHEMA")
    require(type(packet.get("source_commit")) is str
            and re.fullmatch(r"[a-f0-9]{40}", packet["source_commit"]) is not None,
            "PACKET_SOURCE_COMMIT")
    base = packet.get("base_commit")
    require(base is None or (type(base) is str and re.fullmatch(r"[a-f0-9]{40}", base) is not None),
            "PACKET_BASE_COMMIT")
    files = packet.get("files")
    require(type(files) is list and files, "PACKET_FILES")
    paths = []
    for entry in files:
        require(type(entry) is dict and set(entry) == {"path", "bytes", "sha256", "git_blob"},
                "PACKET_ENTRY_FIELDS")
        path = entry["path"]
        require(type(path) is str and _path_allowed(path)
                and not path.startswith("/") and "\\" not in path
                and path == path.replace("//", "/")
                and all(part not in ("", ".", "..") for part in path.split("/")),
                "PACKET_ENTRY_PATH")
        require(type(entry["bytes"]) is int and entry["bytes"] > 0, "PACKET_ENTRY_BYTES")
        require(type(entry["sha256"]) is str
                and re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]) is not None,
                "PACKET_ENTRY_SHA256")
        require(type(entry["git_blob"]) is str
                and re.fullmatch(r"[a-f0-9]{40}", entry["git_blob"]) is not None,
                "PACKET_ENTRY_BLOB")
        paths.append(path)
    require(len(set(paths)) == len(paths), "PACKET_DUPLICATE_PATH")
    require(sorted(paths) == paths, "PACKET_PATHS_NOT_SORTED")
    return packet


def _run_git(args, cwd):
    # File redirection only: no stdio pipes, so the sandboxed harness cannot
    # break this with an EPERM on named-pipe capture.
    handle_out, out_path = tempfile.mkstemp(prefix="cas_v9_packet_out_")
    os.close(handle_out)
    handle_err, err_path = tempfile.mkstemp(prefix="cas_v9_packet_err_")
    os.close(handle_err)
    try:
        with open(out_path, "wb") as out, open(err_path, "wb") as err:
            process = subprocess.run(["git"] + args, cwd=str(cwd), stdout=out, stderr=err,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if process.returncode != 0:
            message = Path(err_path).read_bytes().decode("utf-8", "replace")[:2000]
            raise ValueError("GIT_COMMAND_FAILED:" + message)
        return 0, Path(out_path).read_bytes()
    finally:
        for path in (out_path, err_path):
            try:
                os.unlink(path)
            except OSError:
                pass


def git_bytes(root, commit, path):
    code, raw = _run_git(["-c", "core.autocrlf=false", "show", commit + ":" + path], root)
    require(code == 0, "GIT_SHOW_FAILED:" + path)
    return raw


def git_blob(root, commit, path):
    code, raw = _run_git(["-c", "core.autocrlf=false", "rev-parse", commit + ":" + path], root)
    require(code == 0, "GIT_REV_PARSE_FAILED:" + path)
    return raw


def git_changed_paths(root, commit, base=None):
    args = ["-c", "core.autocrlf=false", "diff-tree", "--no-commit-id", "--name-only", "-r"]
    args += [commit] if base is None else [base, commit]
    code, raw = _run_git(args, root)
    require(code == 0, "GIT_DIFF_TREE_FAILED")
    return [line for line in raw.decode("utf-8").splitlines() if line]


def git_is_ancestor(root, commit, head):
    try:
        code, _ = _run_git(["-c", "core.autocrlf=false", "merge-base", "--is-ancestor", commit, head], root)
    except ValueError:
        return False
    return code == 0


def build_packet(root, commit, base=None, *, git_bytes_fn=git_bytes, git_blob_fn=git_blob,
                 git_changed_fn=git_changed_paths):
    require(type(commit) is str and re.fullmatch(r"[a-f0-9]{40}", commit) is not None,
            "SOURCE_COMMIT_REQUIRED")
    if base is not None:
        require(type(base) is str and re.fullmatch(r"[a-f0-9]{40}", base) is not None,
                "BASE_COMMIT_REQUIRED")
    changed = git_changed_fn(root, commit, base)
    require(bool(changed), "SOURCE_COMMIT_HAS_NO_PATHS")
    require(all(_path_allowed(path) for path in changed),
            "PACKET_COVERAGE_OUTSIDE_ALLOWED_PREFIX")
    entries = []
    for path in changed:
        raw = git_bytes_fn(root, commit, path)
        require(bool(raw), "EMPTY_GIT_OBJECT:" + path)
        blob = git_blob_fn(root, commit, path).strip()
        require(re.fullmatch(rb"[a-f0-9]{40}", blob) is not None, "PACKET_BLOB_SHAPE:" + path)
        entries.append({"path": path, "bytes": len(raw),
                        "sha256": sha256(raw).hexdigest(),
                        "git_blob": blob.decode("ascii")})
    entries.sort(key=lambda entry: entry["path"])
    packet = {"schema": SCHEMA, "source_commit": commit, "files": entries}
    if base is not None:
        packet["base_commit"] = base
    validate_structure(packet)
    raw = (json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    require(b"\r" not in raw, "PACKET_CRLF_REJECTED")
    return packet, raw


def verify_packet(root, packet_raw, head, *, git_bytes_fn=git_bytes, git_blob_fn=git_blob,
                  git_changed_fn=git_changed_paths, git_ancestor_fn=git_is_ancestor):
    packet = validate_structure(strict_load(packet_raw))
    commit = packet["source_commit"]
    base = packet.get("base_commit")
    require(git_ancestor_fn(root, commit, head), "SOURCE_COMMIT_NOT_ANCESTOR_OF_HEAD")
    if base is not None:
        require(git_ancestor_fn(root, base, commit), "BASE_COMMIT_NOT_ANCESTOR_OF_SOURCE")
    changed = git_changed_fn(root, commit, base)
    require(sorted(changed) == [entry["path"] for entry in packet["files"]],
            "PACKET_COVERAGE_MISMATCH")
    checked = []
    for entry in packet["files"]:
        raw = git_bytes_fn(root, commit, entry["path"])
        require(len(raw) == entry["bytes"], "PACKET_BYTES_MISMATCH:" + entry["path"])
        require(sha256(raw).hexdigest() == entry["sha256"], "PACKET_SHA256_MISMATCH:" + entry["path"])
        blob = git_blob_fn(root, commit, entry["path"]).strip()
        require(blob == entry["git_blob"].encode("ascii"), "PACKET_BLOB_MISMATCH:" + entry["path"])
        checked.append(entry["path"])
    return {"schema": REPORT_SCHEMA, "status": "PACKET_EXACT",
            "source_commit": commit, "head": head,
            "packet_sha256": sha256(packet_raw).hexdigest(),
            "packet_bytes": len(packet_raw), "files": checked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build")
    parser.add_argument("--from")
    parser.add_argument("--output")
    parser.add_argument("--verify")
    parser.add_argument("--head", default="HEAD")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if arguments.build:
        require(arguments.output, "OUTPUT_PATH_REQUIRED")
        packet, raw = build_packet(root, arguments.build, arguments.__dict__.get("from"))
        output = Path(arguments.output).absolute()
        require(not output.exists(), "PACKET_OUTPUT_MUST_BE_FRESH")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(raw)
        print(json.dumps({"schema": REPORT_SCHEMA, "status": "PACKET_BUILT",
                          "source_commit": arguments.build,
                          "packet_sha256": sha256(raw).hexdigest(),
                          "packet_bytes": len(raw), "files": len(packet["files"]),
                          "output": str(output)}, sort_keys=True))
        return 0
    require(arguments.verify, "BUILD_OR_VERIFY_REQUIRED")
    packet_path = Path(arguments.verify).absolute()
    raw = packet_path.read_bytes()
    report = verify_packet(root, raw, arguments.head)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
