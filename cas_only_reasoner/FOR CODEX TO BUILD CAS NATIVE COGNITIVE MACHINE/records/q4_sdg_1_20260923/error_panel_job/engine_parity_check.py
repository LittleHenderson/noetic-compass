"""Engine parity: compile every visible Q3 v0.7 row (all families, train+dev) with the Rust engine and with the
pure-Python engine; compare validity and the lab-spelled AST. Reads visible files only."""
import json, sys, pathlib, hashlib
LAB = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(LAB))
import historical_compiler, q3_behaviour_records as q3
module = historical_compiler.load_historical_compiler()
rust = module.cas_engine
assert rust is not None, "no rust engine here"
def run(engine, text):
    module.cas_engine = engine
    try:
        art = module.compile_expression(text).to_dict()
    finally:
        module.cas_engine = rust
    ast = q3.to_lab_spelling(art["ast"]) if art["valid"] and art["ast"] is not None else None
    return art["valid"], json.dumps(ast, sort_keys=True)
counts, diffs = {}, []
for path in sorted((LAB / "data" / "q3_v0_7").glob("visible_*.jsonl")):
    assert "eval" not in path.name and "sealed" not in path.name
    n = d = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row["observation"], str):
            counts.setdefault("skipped_non_text", 0)
            counts["skipped_non_text"] += 1
            continue
        a, b = run(rust, row["observation"]), run(None, row["observation"])
        n += 1
        if a != b:
            d += 1
            if len(diffs) < 5:
                diffs.append({"file": path.name, "id": row["record_id"], "obs": row["observation"][:120], "rust_valid": a[0], "python_valid": b[0]})
    counts[path.name] = {"rows": n, "differ": d}
print(json.dumps({"counts": counts, "examples": diffs}, indent=1))
