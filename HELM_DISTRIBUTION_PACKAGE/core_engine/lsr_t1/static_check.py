"""AST/JSON/hash audit only. Never imports engine, data or test code. Writes SOURCE_MANIFEST.json,
STATIC_CHECK.json and STATUS.json (pattern: sdg_bridge_v2/static_check.py)."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

STAGE = Path(__file__).resolve().parent
OWN = ("__init__.py", "engine.py", "families.py", "run_t1.py", "worker.py", "test_lsr.py", "static_check.py",
       "supervisor.ps1", "FROZEN.json", "OWNER_APPROVAL_EVIDENCE.template.md")
CMP = Path(r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011")
LM = Path(r"C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1\lacunarity_machine")
DESIGN = Path(r"C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_oscillator_design_v1")
REUSED = [LM / n for n in ("__init__.py", "universe.py", "ledger.py", "readers.py", "report.py")]
REUSED += [CMP / r for r in (
    "sdg_bridge_v2/__init__.py", "sdg_bridge_v2/grammar.py", "sdg_bridge_v2/english.py", "sdg_bridge_v2/binder.py",
    "sdg_bridge_v2/bridge.py", "sdg_bridge_v2/FROZEN.json", "sdg_bridge/__init__.py", "sdg_bridge/bridge.py",
    "corpus/exchange_adapter.py",
    "fair_data_experiment_v2_sdg/__init__.py", "fair_data_experiment_v2_sdg/data.py",
    "fair_data_experiment_v2_sdg/sdg_source.py", "fair_data_experiment_v2_sdg/binder.py",
    "fair_data_experiment_v2_sdg/FROZEN.json", "scale_benchmark_v1/__init__.py", "scale_benchmark_v1/data.py",
    "fair_data_experiment_v1/__init__.py", "fair_data_experiment_v1/data.py", "fair_data_experiment_v1/FROZEN.json")]
DESIGN_FILES = [DESIGN / n for n in ("ARCHITECTURE.md", "CONVERGENCE.md", "TEST_PLAN.md", "OPEN_QUESTIONS.md",
                                     "lsr_sketch.py", "CAS_MAPPING.md")]
EXTERNAL = [Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-synthetic\data\path_d\seeds.jsonl"),
            Path(r"C:\Python314\python.exe")]
ALLOWED = {"__future__", "itertools", "math", "time", "dataclasses", "fractions", "typing", "json", "random",
           "decimal", "pathlib", "argparse", "hashlib", "io", "os", "socket", "sys", "unittest", "ast", "datetime",
           "scale_benchmark_v1.data", "fair_data_experiment_v2_sdg", "sdg_bridge_v2", "lacunarity_machine.universe",
           "lacunarity_machine.ledger", "lacunarity_machine.readers", "lsr_t1", "engine", "lsr_t1.engine",
           "lsr_t1.families", "lsr_t1.run_t1", "lsr_t1.test_lsr", "."}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    files, imports, problems = [], {}, []
    for name in OWN:
        path = STAGE / name
        raw = path.read_bytes()
        if name.endswith(".py"):
            tree = ast.parse(raw.decode("utf-8"), filename=name)
            mods = sorted({(n.module if isinstance(n, ast.ImportFrom) else a.name) or "."
                           for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names})
            imports[name] = mods
            bad = [m for m in mods if m not in ALLOWED]
            if bad:
                problems.append({"file": name, "unexpected_imports": bad})
        elif name.endswith(".json"):
            json.loads(raw.decode("utf-8"))
        files.append({"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "role": "LSR_T1"})
    for p in REUSED:
        files.append({"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size, "role": "REUSED_UNCHANGED"})
    for p in DESIGN_FILES:
        files.append({"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size, "role": "DESIGN_READ_ONLY"})
    for p in EXTERNAL:
        files.append({"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size, "role": "EXTERNAL_READ_ONLY"})
    manifest = {"version": "lsr-t1", "created_utc": datetime.now(timezone.utc).isoformat(), "files": files}
    raw = json.dumps(manifest, indent=2).encode("utf-8")
    (STAGE / "SOURCE_MANIFEST.json").write_bytes(raw)
    msha = hashlib.sha256(raw).hexdigest()
    check = {"checked_at_utc": manifest["created_utc"], "check_type": "STATIC_SOURCE_ONLY", "ast_parse": "PASS",
             "json_parse": "PASS", "imports": imports, "problems": problems, "source_manifest_sha256": msha,
             "files_hashed": len(files)}
    (STAGE / "STATIC_CHECK.json").write_text(json.dumps(check, indent=2), "utf-8")
    status = {"status": "STATIC_CHECK_" + ("PASS" if not problems else "FAIL") + "_AWAITING_LOCAL_RUN",
              "source_manifest_sha256": msha,
              "sign_line": "APPROVE lsr_t1, source " + msha[:8] + ", LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.",
              "run_id": "LSR_T1_MSI_RUN2"}
    (STAGE / "STATUS.json").write_text(json.dumps(status, indent=2), "utf-8")
    print(json.dumps(status))


if __name__ == "__main__":
    main()
