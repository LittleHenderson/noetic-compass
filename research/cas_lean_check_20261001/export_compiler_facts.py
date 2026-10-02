"""Run real CAS source text through the real compiler and write every answer for Lean to check.

Usage (on the cloud machine, never on the laptop):
    python export_compiler_facts.py --nc <path to noetic-compass-scaffold/noetic-compass> --out lean

Writes:
    lean/CasCheck/Generated.lean   core records + every nested word of 2-4 letters (Lean string constants)
    lean/nest5.txt                 every nested word of 5 letters (read at run time by `lake exe cascheck`)
    lean/facts_summary.json        counts, compiler identity, timing

The record formats are documented in lean/CasCheck/Differential.lean.
By default the compiler is imported WITHOUT the Rust `cas_engine`, so its Python fallback path runs, and the
script refuses to run if `cas_engine` is importable. With `--engine rust` it REQUIRES `cas_engine` and writes
plain answer files (rust_core.txt, rust_nest24.txt, rust_nest5.txt) for `lake exe cascheck core:... nest:...`.
"""
import argparse
import hashlib
import itertools
import json
import pathlib
import sys
import time

EXPECTED_BLOB = "439c4908df2718a3ca1e1ff40bda63020cf71efa"   # compiler.py at commit 8a3555b8
DOMAINS = "PCEO"
REGISTER_CODE = {None: 0, "T": 1, "A": 2, "f": 3, "E": 4}
# Must match `alphabet` in lean/CasCheck/Bounded.lean, in the same order.
LETTERS = ["^2^C", "^3^C", "^2^C|f", "^3^E", "^8^C", "^9^C", "^6^C", "^0^C", "^3^C_{F2}"]
SET_PROGRAMS = ["|Noetics|", "|Domains|", "|Drives|", "|Registers|", "|States|", "|SubFoundations|",
                "|Foundations|", "|Product(Noetics, Domains)|",
                "PartitionOf(SubFoundations, " + ", ".join("Foundation_%d" % i for i in range(1, 8)) + ")",
                "|Product(Drives, Registers)|"]


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nc", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--engine", choices=["python", "rust"], default="python",
                    help="python: refuse if cas_engine is importable (default). rust: REQUIRE cas_engine and write "
                         "plain answer files (rust_core.txt, rust_nest24.txt, rust_nest5.txt) instead of Generated.lean")
    args = ap.parse_args()
    nc = pathlib.Path(args.nc).resolve()
    out = pathlib.Path(args.out).resolve()
    # git stores LF; a Windows checkout may carry CRLF. Python reads either the same way.
    source = (nc / "api" / "notation" / "compiler.py").read_bytes().replace(b"\r\n", b"\n")
    blob = git_blob_sha1(source)
    if blob != EXPECTED_BLOB:
        raise SystemExit("REFUSED: compiler.py blob %s is not the pinned %s" % (blob, EXPECTED_BLOB))
    sys.path.insert(0, str(nc))
    from api.notation import compiler as C   # noqa: E402
    if args.engine == "python" and C.cas_engine is not None:
        raise SystemExit("REFUSED: the Rust cas_engine is importable; the Lean copy describes the Python fallback")
    if args.engine == "rust" and C.cas_engine is None:
        raise SystemExit("REFUSED: --engine rust but cas_engine is not importable")
    compile_expression = C.compile_expression
    started = time.time()

    def run(src):
        art = compile_expression(src)
        return art.result if art.valid else None

    def op_or_99(value, attr):
        if value is None:
            return 99
        return value.composed_operator if attr == "composed" else value.dominant_operator()

    core = []
    for a in range(10):
        for b in range(10):
            times = op_or_99(run("^%d^C * ^%d^C" % (a, b)), "dominant")
            circ = op_or_99(run("^%d^C ∘ ^%d^C" % (a, b)), "composed")
            comp = op_or_99(run("compose(^%d^C, ^%d^C)" % (a, b)), "dominant")
            div = op_or_99(run("^%d^C / ^%d^C" % (a, b)), "dominant")
            core.append("C %d %d %d %d %d %d" % (a, b, times, circ, comp, div))

    def state_src(i):
        return "^%d^%s" % (i % 10, DOMAINS[i // 10])

    for s in range(40):
        for t in range(40):
            rel = run("%s -> %s" % (state_src(s), state_src(t)))
            if rel is None:
                core.append("A %d %d 0 2 2" % (s, t))
            else:
                core.append("A %d %d 1 %d %d" % (s, t, int(rel.admissible), int(rel.domain_descent_ok)))
    # Review round 2: every ordered pair of the 40 states, for <-, <->, *, / and x - y.
    for s in range(40):
        for t in range(40):
            for tag, sym in (("B", "<-"), ("E", "<->")):
                rel = run("%s %s %s" % (state_src(s), sym, state_src(t)))
                if rel is None:
                    core.append("%s %d %d 0 2 2" % (tag, s, t))
                else:
                    core.append("%s %d %d 1 %d %d" % (tag, s, t, int(rel.admissible), int(rel.domain_descent_ok)))
            for tag, sym in (("T", "*"), ("V", "/")):
                v = run("%s %s %s" % (state_src(s), sym, state_src(t)))
                core.append("%s %d %d %d" % (tag, s, t, 99 if v is None else v.dominant_state()))
            v = run("%s - %s" % (state_src(s), state_src(t)))
            if v is None:
                core.append("X %d %d 999 0 0" % (s, t))
            else:
                zeros = sum(1 for w in v.states.values() if w == 0.0)
                core.append("X %d %d %d %d %d" % (s, t, v.dominant_state(), len(v.states), zeros))
    for tag, sym in (("D", "*"), ("Q", "/")):
        for l in range(4):
            for r in range(4):
                v = run("^1^%s %s ^1^%s" % (DOMAINS[l], sym, DOMAINS[r]))
                core.append("%s %d %d %d" % (tag, l, r, 9 if v is None else DOMAINS.index(v.dominant_domain())))
    for a in range(10):
        for b in range(10):
            v = run("^%d^C + ^%d^C" % (a, b))
            core.append("P %d %d %d" % (a, b, 999 if v is None else v.dominant_state()))
    for i in range(40):
        v = run("%s - %s" % (state_src(i), state_src(i)))
        core.append("M %d %d %d" % (i, 999 if v is None else v.dominant_state(), 0 if v is None else len(v.states)))
    for code, prog in enumerate(SET_PROGRAMS):
        art = compile_expression(prog)
        if prog.startswith("PartitionOf"):
            value = 1 if art.valid else 0
        else:
            value = art.result.value if art.valid and hasattr(art.result, "value") else 9999
        core.append("S %d %d" % (code, value))
    for code, letter in enumerate(LETTERS):
        v = run("%s ∘ ^1^C" % letter)
        term = v.to_dict()["nesting"]["terms"][0]
        reg = term.get("register")
        core.append("L %d %d %d %d %d" % (
            code, term["noetic"], 4 if term.get("domain") is None else DOMAINS.index(term["domain"]),
            0 if term.get("drive") is None else int(str(term["drive"]).lstrip("F")),
            9 if isinstance(reg, list) else REGISTER_CODE.get(reg, 9)))

    def nest_record(word):
        art = compile_expression(" ∘ ".join(LETTERS[c] for c in word))
        if not art.valid:
            return "N 0 BAD"
        nest = art.result.to_dict()["nesting"]
        terms = nest["terms"]
        live = [p for p, t in enumerate(terms) if t["noetic"] != 0]

        def survivors(reading):
            gone = {p for pair in nest["canonical_form"][reading]["cancelled"] for p in pair}
            return [p for p in live if p not in gone]

        def counted(xs):
            return [len(xs)] + list(xs)

        def crit(block):
            pairs = [x for pair in block["resolved"] for x in pair]
            return [len(block["resolved"])] + pairs + counted(block["unresolved_surfacing"])

        def met(m):
            return 2 if m is None else int(bool(m))

        dcc = nest["dual_cancellation_criterion"]
        fields = (counted(word) + counted(survivors("surfacing_member_first")) + counted(survivors("either_order"))
                  + crit(dcc) + crit(dcc["by_either_order"]) + crit(dcc["by_any_landing"])
                  + [met(dcc["met"]), met(dcc["by_either_order"]["met"]), met(dcc["by_any_landing"]["met"])])
        return "N " + " ".join(str(x) for x in fields)

    nest = [nest_record(w) for n in (2, 3, 4) for w in itertools.product(range(len(LETTERS)), repeat=n)]
    nest5 = [nest_record(w) for w in itertools.product(range(len(LETTERS)), repeat=5)]

    NL = "\n"
    if args.engine == "rust":
        for name, rows in (("rust_core.txt", core), ("rust_nest24.txt", nest), ("rust_nest5.txt", nest5)):
            (out / name).write_text(NL.join(rows) + NL, encoding="utf-8", newline=NL)
    else:
        gen = out / "CasCheck" / "Generated.lean"
        lean_nl = "\\n"   # the two characters backslash-n: a newline escape INSIDE the Lean string literal
        gen.write_text(
            "/-! Written by export_compiler_facts.py from the REAL compiler. Do not edit by hand. -/" + NL
            + "namespace Cas.Generated" + NL
            + 'def compilerBlob : String := "%s"' % blob + NL
            + 'def engine : String := "python"' + NL
            + 'def coreData : String := "%s"' % lean_nl.join(core) + NL
            + 'def nestData : String := "%s"' % lean_nl.join(nest) + NL
            + "end Cas.Generated" + NL, encoding="utf-8", newline=NL)
        (out / "nest5.txt").write_text(NL.join(nest5) + NL, encoding="utf-8", newline=NL)
    summary = {"compiler_blob": blob, "engine": args.engine,
               "cas_engine_file": getattr(C.cas_engine, "__file__", None), "core_records": len(core), "nest_records_2_4": len(nest),
               "nest_records_5": len(nest5), "bad_nest_programs": sum(r.endswith("BAD") for r in nest + nest5),
               "python": sys.version, "seconds": round(time.time() - started, 1)}
    (out / ("facts_summary.json" if args.engine == "python" else "rust_facts_summary.json")).write_text(json.dumps(summary, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
