"""AST/JSON/hash audit only. Never imports LM-T1 code or data. Writes SOURCE_MANIFEST.json, STATIC_CHECK.json,
STATUS.json. Pattern from sdg_bridge_v2/static_check.py."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

STAGE = Path(__file__).resolve().parent
OWN = ("cce.py", "aliaswide.py", "coverage.py", "scoring.py", "worker.py", "test_lm_t1.py", "test_lm_t1v3.py",
       "static_check.py", "supervisor.ps1", "FROZEN.json", "GRAMMAR_CCE_v0_1.md", "GRAMMAR_CCE_v0_1_v3_ADDENDUM.md",
       "ALIAS_WIDE_LEXICON_v0_1.json", "OWNER_APPROVAL_EVIDENCE.template.md",
       "handset/HAND_SET_v0_1.json", "handset/HAND_SET_FREEZE.json")
BRIDGE = Path(r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011")
LAC = Path(r"C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1\lacunarity_machine")
PATH_D = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-synthetic\data\path_d")
REUSED = [BRIDGE / "sdg_bridge_v2" / n for n in ("__init__.py", "grammar.py", "english.py", "binder.py", "bridge.py", "tables.py")]
REUSED += [BRIDGE / "fair_data_experiment_v2_sdg" / n for n in ("__init__.py", "sdg_source.py")]
REUSED += [LAC / n for n in ("__init__.py", "universe.py", "ledger.py", "readers.py")]
EXTERNAL = [PATH_D / "seeds.jsonl"] + [PATH_D / n for n in (
    "wave3_step2_5_english_descriptions_20260508T203848Z.jsonl",
    "wave3_step2_5_english_descriptions_20260509T002355Z.jsonl",
    "wave3_step2_5_english_descriptions_20260509T002541Z.jsonl")] + [
    Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass\api\notation\compiler.py"),
    Path(r"C:\Python314\python.exe")]
ALLOWED = {"argparse", "collections", "decimal", "fractions", "hashlib", "io", "itertools", "json", "os", "pathlib",
           "random", "re", "socket", "statistics", "sys", "time", "unittest", "ast", "datetime", "cce", "aliaswide",
           "coverage", "scoring", "sdg_bridge_v2", "sdg_bridge_v2.grammar", "fair_data_experiment_v2_sdg",
           "lacunarity_machine.universe", "lacunarity_machine.ledger", "lacunarity_machine.readers",
           "sdg_bridge_v2.english", "cce_v01b", "cce_v01c", "cas_ast"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    files, imports, problems = [], {}, []
    for name in OWN:
        path = STAGE / name
        raw = path.read_bytes()
        if name.endswith(".py"):
            tree = ast.parse(raw.decode("utf-8"))
            mods = sorted({(n.module if isinstance(n, ast.ImportFrom) else a.name) or "."
                           for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names})
            imports[name] = mods
            bad = [m for m in mods if m not in ALLOWED]
            if bad:
                problems.append({"file": name, "unexpected_imports": bad})
        elif name.endswith(".json"):
            json.loads(raw.decode("utf-8"))
        files.append({"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "role": "LM_T1"})
    for p in REUSED:
        files.append({"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size, "role": "REUSED_UNCHANGED"})
    for p in EXTERNAL:
        files.append({"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size, "role": "EXTERNAL_READ_ONLY"})
    manifest = {"version": "lm-t1-v0.1-v3", "created_utc": datetime.now(timezone.utc).isoformat(), "files": files}
    raw = json.dumps(manifest, indent=2).encode("utf-8")
    (STAGE / "SOURCE_MANIFEST.json").write_bytes(raw)
    msha = hashlib.sha256(raw).hexdigest()
    (STAGE / "STATIC_CHECK.json").write_text(json.dumps({"check_type": "STATIC_SOURCE_ONLY", "imports": imports,
                                                         "problems": problems, "source_manifest_sha256": msha,
                                                         "files_hashed": len(files)}, indent=2), "utf-8", newline="\n")
    status = {"status": "STATIC_CHECK_" + ("PASS" if not problems else "FAIL") + "_AWAITING_LOCAL_RUN",
              "source_manifest_sha256": msha,
              "sign_line": "APPROVE lm_t1, source " + msha[:8] + ", LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.",
              "run_id": "LM_T1_MSI_ONCE"}
    (STAGE / "STATUS.json").write_text(json.dumps(status, indent=2), "utf-8", newline="\n")
    print(json.dumps(status))


if __name__ == "__main__":
    main()
