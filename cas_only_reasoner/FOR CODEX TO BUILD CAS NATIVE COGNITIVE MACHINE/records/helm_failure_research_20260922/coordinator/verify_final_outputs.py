"""One-time final custody check; no project/model imports or behavioral tests."""
import hashlib, json, os, pathlib, subprocess, threading, time
from datetime import datetime, timezone

started = time.monotonic()
watchdog = threading.Timer(115, lambda: os._exit(124))
watchdog.daemon = True
watchdog.start()
root = pathlib.Path.cwd()
relative = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922"
out = root / relative
commands = []
def git(*args, cwd=root):
    result = subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=cwd,
                            capture_output=True, text=True, encoding="utf-8", timeout=20)
    commands.append({"cwd": str(cwd), "argv": ["git", "-c", "core.quotepath=false", *args],
                     "exit_code": result.returncode, "stderr": result.stderr})
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert root.name == "helm-failure-research"
assert pathlib.Path(git("rev-parse", "--show-toplevel")).resolve() == root.resolve()
assert git("branch", "--show-current") == "codex/helm-failure-research-20260922"
status_before = git("status", "--porcelain", "--untracked-files=normal")
assert status_before == "", status_before
expected = {
"A1": "b5a8aa8223c66344bc7da8dfc8169160b6d8a8ece49f6b7a21e31a14ca274e7c",
"A2": "91de7dc113f564374df6dd287be06760d87c2f75c20e7823e96b86cc106a012f",
"A3": "1457f898fc98e47f7ca34975202adc2a36235b959b53c5ac2449ea926f339a52",
"A4": "7a96838b04441697c3d7edee9d437498af66e0c241c5d992ceaefc2edca015c3",
"A5": "6991dca9b2c34ada684822c04c1ea0ef6a04e910ae2ebece8039aa5523e35a84",
"A6": "d9aa2716de1a1db581d68e5173b7f2fd40dd87531fa7a5894927a2bd0576b45c",
}
actual = {role: sha(out / "agents" / role / "FIRST_REPORT.md") for role in expected}
assert actual == expected, "An immutable first report changed"
source_hash = sha(out / "SOURCE_AND_EVIDENCE_MANIFEST.json")
assert source_hash == "1ddf793e5cd6a77cdcc843b089c26b9a880f268ac556d22d40cdbb45e9874101"
copies = {}
for name in ("FINAL_JUDGMENT.md", "NEXT_ACTIONS.md"):
    original = sha(out / "agents" / "A7" / name)
    copied = sha(out / name)
    assert original == copied, name
    copies[name] = {"a7_sha256": original, "top_level_sha256": copied, "byte_equal": True}
role_scopes = []
for n in range(1, 8):
    role = f"A{n}"
    worktree = root.parent / f"helm-failure-a{n}"
    branch = git("branch", "--show-current", cwd=worktree)
    assert branch == f"codex/helm-failure-a{n}-20260922"
    changed = git("diff", "--name-only", "59b1dd57e57648ab68c1cc26fbae95a957c20cd3", "HEAD", cwd=worktree).splitlines()
    assert all(p.startswith(f"{relative}/agents/{role}/") for p in changed), role
    role_scopes.append({"role": role, "worktree": str(worktree), "branch": branch,
                        "head": git("rev-parse", "HEAD", cwd=worktree),
                        "changed_paths": changed, "scope_passed": True})
changed = git("diff", "--name-only", "4eb98682b983f9ceb22c9e0b5fa127e9d21cda0d", "HEAD").splitlines()
allowed_agents = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/AGENTS.md"
assert all(p.startswith(relative + "/") or p == allowed_agents for p in changed)
paths = git("ls-files", "--", relative).splitlines()
manifest_name = relative + "/RESEARCH_OUTPUT_MANIFEST.json"
rows = [{"path": p, "bytes": (root/p).stat().st_size, "sha256": sha(root/p)}
        for p in paths if p != manifest_name]
receipt = {
 "schema": "helm.research-output-custody/0.1", "observed_utc": datetime.now(timezone.utc).isoformat(),
 "pre_manifest_commit": git("rev-parse", "HEAD"), "root": str(root),
 "branch": "codex/helm-failure-research-20260922", "status_before": status_before,
 "source_manifest_sha256": source_hash, "immutable_first_reports": actual,
 "a7_verbatim_top_level_copies": copies, "role_commit_scopes": role_scopes,
 "integration_changed_path_count": len(changed), "integration_scope_passed": True,
 "integration_scope_exception": allowed_agents,
 "output_file_count": len(rows), "outputs": rows,
 "self_excluded": manifest_name, "commands_and_exits": commands,
 "test_functions": 0, "new_behavioral_input_cases": 0, "execution_count": 1,
 "model_execution": False, "elapsed_seconds": time.monotonic()-started,
 "limits": ["File identity and Git write-scope checks only; not new model behavior or certification.",
            "Manifest excludes its own bytes to avoid a circular hash.",
            "Original-source/workspace preservation is separately attributed to root's saved receipt."]}
(out / "RESEARCH_OUTPUT_MANIFEST.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
watchdog.cancel()
print(json.dumps({"status": "PASS", "files": len(rows), "first_reports_unchanged": 6,
                  "a7_copies_equal": 2, "role_scopes": 7,
                  "elapsed_seconds": receipt["elapsed_seconds"]}))
