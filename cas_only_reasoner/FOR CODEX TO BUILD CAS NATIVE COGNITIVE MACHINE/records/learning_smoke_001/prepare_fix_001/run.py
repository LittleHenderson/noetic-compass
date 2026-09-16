"""Exercise the actual launch preparation Git gate in a disposable local repo."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "prepare_launch.py"
HOME = next(p for p in reversed(HERE.parents) if p.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def main():
    raw = SOURCE.read_bytes()
    tree = ast.parse(raw)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "require_clean_source"]
    require(len(nodes) == 1, "MISSING_GATE")
    scope = {"subprocess": subprocess, "launch": SimpleNamespace(require=require)}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), scope)
    gate = scope["require_clean_source"]
    repo = Path(tempfile.mkdtemp(prefix="prepare_git_", dir=HOME / "_tmp"))
    def git(*args):
        return subprocess.check_output(["git", "-c", "core.autocrlf=false", *args], cwd=repo, stderr=subprocess.STDOUT)
    git("init", "--quiet")
    (repo / "source.txt").write_bytes(b"source\n")
    git("add", "source.txt")
    git("-c", "user.name=CNCM local gate test", "-c", "user.email=local-test@invalid", "commit", "--quiet", "-m", "fixture")
    head = git("rev-parse", "HEAD").decode().strip()
    cases = []
    def check(name, expected=None, source=head):
        observed = None
        try:
            gate(repo, source)
        except ValueError as error:
            observed = str(error)
        require(observed == expected, "CASE_FAILED:" + name + ":" + str(observed))
        cases.append({"case": name, "observed": observed, "pass": True})
    check("clean_committed_source")
    check("wrong_source_commit", "PREPARE_SOURCE_HEAD", "0" * 40)
    (repo / "source.txt").write_bytes(b"unstaged\n")
    check("unstaged_source_refused", "PREPARE_TRACKED_MODIFICATIONS")
    git("add", "source.txt")
    require(not git("diff", "--name-only").strip(), "STAGED_CASE_NOT_ISOLATED")
    check("staged_source_refused", "PREPARE_TRACKED_MODIFICATIONS")
    (repo / "source.txt").write_bytes(b"source\n")
    git("add", "source.txt")
    check("restored_source")
    (repo / "evidence.json").write_bytes(b"{}\n")
    check("untracked_evidence_allowed")
    git("add", "evidence.json")
    check("staged_new_file_refused", "PREPARE_TRACKED_MODIFICATIONS")
    require(SOURCE.read_bytes() == raw, "SOURCE_CHANGED")
    report = {"status": "PASS", "tests": len(cases), "cases": cases, "scratch_repository": str(repo),
              "prepare_launch_sha256": sha256(raw).hexdigest(), "inputs_unchanged": True,
              "boundary": "Pure local Git gate checks; no model, provider, network, reservation or launch."}
    with (HERE / "receipt.json").open("xb") as stream:
        stream.write((json.dumps(report, sort_keys=True) + "\n").encode())
    print(json.dumps({"status": report["status"], "tests": len(cases), "prepare_launch_sha256": report["prepare_launch_sha256"]}))


if __name__ == "__main__":
    main()
