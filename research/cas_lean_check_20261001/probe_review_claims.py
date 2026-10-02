"""Run every example the 2026-10-01 adversarial review derived BY READING the compiler, on the real compiler.

Usage (cloud machine only):  python probe_review_claims.py <noetic-compass dir> <out.json>
Run once with plain python3 (Python fallback) and once with the venv that has cas_engine (Rust route).
Each entry records: did it compile, the error text (it names the stage), and a short form of the result.
"""
import json
import sys

sys.path.insert(0, sys.argv[1])
from api.notation import compiler as C  # noqa: E402

CLAIMS = [
    ("B6a", "plus result as an operand of *: expected refused by the type checker", ["(^2^C + ^3^C) * ^5^C"]),
    ("B6b", "plus result through an any-typed binding: expected ^7^C vs ^8^C",
     ["let x: any = ^2^C + ^3^C; x * ^5^C", "let x: any = ^3^C + ^2^C; x * ^5^C"]),
    ("B6c", "plus result inside fractal(): expected composed 7 vs 8",
     ["fractal(^2^C + ^3^C, ^5^C)", "fractal(^3^C + ^2^C, ^5^C)"]),
    ("B6d", "mixed-Domain plus as an arrow source: expected domain_descent_ok true vs false",
     ["^2^C + ^3^E -> ^5^C", "^3^E + ^2^C -> ^5^C"]),
    ("B6e", "three-term plus: expected dominant ^3^C vs ^1^C", ["^1^C + ^2^C + ^3^C", "^1^C + (^2^C + ^3^C)"]),
    ("B9", "minus leaves a zero weight: expected state 11 with weight 0.0", ["(^1^C + ^2^C) - ^1^C"]),
    ("B7a", "minus drops the Register label", ["^3^C|A - ^3^C|A", "^2^C - ^3^C"]),
    ("TC1", "type checker reads the alphabetically first Domain of a plus: expected refused", ["(^1^P + ^1^E) -> ^1^C"]),
    ("TC2", "expected to compile and report domain_descent_ok false", ["(^1^O + ^1^C) -> ^1^C"]),
    ("TC3", "expected to pass the type checker and fail at run time (cross-Domain division)", ["(^1^P * ^1^C) / ^1^P"]),
    ("TC4", "plus with a drive gives a program value; expected run-time error at the arrow", ["(^2^C + F_1) -> ^3^C"]),
    ("EM", "v7.7 emergent result over three ^3^P terms: expected state P9 carrying the label",
     ["(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω", "(^3^P|A * ^3^P|f) = fused"]),
    ("RG", "co-presence keeps no Register on the result", ["^3^P|A + ^3^P|f"]),
    ("RPM", "RPM completeness is 1 whenever a drive is attached", ["RPM(^2^C_{F2})", "RPM(^2^C)"]),
    ("SET", "membership vs typed set; bare ^n; repeated Register",
     ["^2 ∈ States", "StateSet{^2}", "^2", "^2|T^C_{F2}|A"]),
    ("NA2", "either-order agreed flag compares positions, not labels", ["^3^C ∘ ^2^C ∘ ^3^C"]),
    ("B8b", "bracket dependence of * chains", ["(^1^E * ^1^C) * ^1^O", "^1^E * (^1^C * ^1^O)", "^1^E * ^1^C * ^1^O"]),
    ("B8d", "bracket dependence of the reported drive",
     ["(^1^P_{F1} * ^1^C_{F2}) * ^1^E_{F3}", "^1^P_{F1} * (^1^C_{F2} * ^1^E_{F3})"]),
    ("B3d", "division's reported drive depends on order", ["^2^C_{F2} / ^7^C_{F5}", "^7^C_{F5} / ^2^C_{F2}"]),
    ("CH", "chained arrows", ["^1^P -> ^1^C -> ^1^E"]),
]


def short(value):
    if value is None:
        return None
    d = C.serialize_value(value)
    if isinstance(d, dict) and d.get("kind") == "fractal":
        n = d.pop("nesting")
        d["canonical_form"] = n["canonical_form"]
        d["orbit_class"] = n["orbit_class"]
    if isinstance(d, dict) and d.get("kind") == "relation":
        for side in ("source", "target"):
            d[side] = {k: d[side].get(k) for k in ("dominant_state", "states")}
    return d


out = {"engine": "rust" if C.cas_engine is not None else "python", "claims": []}
for cid, what, programs in CLAIMS:
    runs = []
    for src in programs:
        art = C.compile_expression(src)
        runs.append({"source": src, "valid": art.valid, "error": art.error, "result": short(art.result) if art.valid else None})
    out["claims"].append({"id": cid, "expectation_from_review": what, "runs": runs})
with open(sys.argv[2], "w", encoding="utf-8", newline="\n") as fh:
    json.dump(out, fh, indent=1, ensure_ascii=False, default=str)
print("wrote", sys.argv[2], out["engine"], len(out["claims"]), "claims")
