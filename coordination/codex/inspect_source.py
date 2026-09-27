"""Lightweight static inspection only: parse text, count methods, hash files.

Does not import project code, collect or run tests, build, benchmark, or submit.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def codex_scope(path):
    relative = path.relative_to(ROOT).as_posix()
    return not any(relative.startswith(prefix) for prefix in (
        "review/", "semantics/", "helm_quantum/compiler/", "tests/compiler/",
        "coordination/claude/", "coordination/deepseek/", "coordination/manager/"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    python_files = sorted(p for p in ROOT.rglob("*.py") if codex_scope(p))
    test_ids = []
    for path in python_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if path.parent == ROOT / "tests":
            for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
                test_ids.extend(f"{path.stem}.{cls.name}.{node.name}" for node in cls.body
                                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
    json_files = sorted(p for p in ROOT.rglob("*.json") if codex_scope(p))
    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts
                   and "__pycache__" not in p.parts and p.suffix in (".py", ".json", ".md", ".pdf", ".txt")
                   and p != ROOT / "evidence/SOURCE_HASHES.json" and codex_scope(p))
    result = {
        "kind": "STATIC_SOURCE_INSPECTION_NOT_TEST_EXECUTION",
        "scope": "Codex-owned source and immutable input only; other leads excluded",
        "python_files_parsed": len(python_files), "json_files_parsed": len(json_files),
        "authored_test_method_count": len(test_ids), "authored_test_ids": test_ids,
        "tests_collected": 0, "tests_executed": 0,
        "files": {p.relative_to(ROOT).as_posix(): {
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
                  for p in files}}
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in ("files", "authored_test_ids")}))


if __name__ == "__main__":
    main()
