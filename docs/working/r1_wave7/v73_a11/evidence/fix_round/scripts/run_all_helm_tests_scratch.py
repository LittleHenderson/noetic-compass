"""run_all_helm_tests_scratch.py <fix2 dir> <helm copy label> -- every HELM test file the reader builder ran, but from a SCRATCH
copy (reviewer G-10), never from the worktree: each test_helm_*.py as its own unittest process (python -X utf8 -B -m
unittest <module>, cwd = the copy, HELM_SESSION_DIR inside fix2), then the four pytest-style files with pytest. Every
process goes through gate.py (the 500 MB rule). Records the files each test process creates inside the copy and whether
the worktree's stray math_utils.py changed. Writes <fix2>/run/all_helm_<label>/SUMMARY.json and SUMMARY.txt."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

WT = Path(r"C:\tmp\helm-ctt2r-c49-read")
PYTEST_FILES = ("test_helm_agentic_planner.py", "test_helm_chat_nuance.py", "test_helm_memory.py", "test_helm_memory_compact.py")


def files(d):
    return {p.relative_to(d).as_posix(): p.stat().st_mtime_ns for p in d.rglob("*") if p.is_file()
            and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts}


def stray():
    p = WT / "math_utils.py"
    return (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) if p.is_file() else None


def main(fix2, label):
    fix2 = Path(fix2)
    helm = fix2 / label
    logd = fix2 / "run" / f"all_helm_{label}"
    logd.mkdir(parents=True, exist_ok=True)
    sess = fix2 / f"sessions_all_{label}"
    gate = [sys.executable, "-X", "utf8", "-B", "-I", str(fix2 / "scripts" / "gate.py")]
    rows = []
    stray0 = stray()
    jobs = [("unittest", f.stem, [sys.executable, "-X", "utf8", "-B", "-m", "unittest", f.stem])
            for f in sorted(helm.glob("test_helm_*.py"))]
    jobs += [("pytest", Path(f).stem, [sys.executable, "-X", "utf8", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", f])
             for f in PYTEST_FILES if (helm / f).is_file()]
    for kind, mod, argv in jobs:
        before = files(helm)
        out = logd / f"{kind}_{mod}.log"
        r = subprocess.run(gate + ["--label", f"all_helm_{label}_{kind}_{mod}", "--memlog", str(fix2 / "run" / "memory_log.jsonl"),
                                   "--out", str(out), "--cwd", str(helm), "--unset-helm-env",
                                   "--env", f"HELM_SESSION_DIR={sess / mod}", "--"] + argv, capture_output=True, text=True)
        if r.returncode == 3 and "GATE STOP" in r.stdout:
            raise SystemExit(r.stdout)
        after = files(helm)
        text = out.read_text(encoding="utf-8")
        if kind == "unittest":
            ran = ([x for x in text.splitlines() if re.match(r"^Ran \d+ tests? in", x)] or [""])[-1]
            res = ([x for x in text.splitlines() if re.match(r"^(OK|FAILED|NO TESTS RAN)", x)] or [""])[-1]
            line = f"unittest {mod} | {ran} | {res} | rc={r.returncode}"
        else:
            last = ([x for x in text.splitlines() if re.search(r"(passed|failed|error|skipped|no tests ran)", x)] or [""])[-1]
            line = f"pytest {mod}.py | {last} | rc={r.returncode}"
        rows.append({"line": line, "rc": r.returncode, "created_in_copy": sorted(set(after) - set(before)),
                     "changed_in_copy": sorted(k for k in before if k in after and before[k] != after[k])})
        print(line, flush=True)
    stray1 = stray()
    summary = {"helm_copy": str(helm), "rows": rows, "worktree_math_utils_before": stray0,
               "worktree_math_utils_after": stray1, "worktree_math_utils_unchanged": stray0 == stray1}
    (logd / "SUMMARY.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (logd / "SUMMARY.txt").write_text("\n".join(r["line"] for r in rows) + "\n", encoding="utf-8")
    print(json.dumps({"worktree_math_utils_unchanged": stray0 == stray1,
                      "created_in_copy": {r["line"].split(" | ")[0]: r["created_in_copy"] for r in rows if r["created_in_copy"]}},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
