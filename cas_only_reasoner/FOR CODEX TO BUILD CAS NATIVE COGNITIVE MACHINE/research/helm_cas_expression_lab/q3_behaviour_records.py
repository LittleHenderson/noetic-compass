"""Q3 -- behaviour-paired records with SEALED targets, structure-family splits, and registered baselines.

Directive section 8. This is an ISOLATED, VERSIONED adapter beside `cas-synthetic`. It does not modify
the generator, its templates or its frozen outputs. It reads one thing from it -- the compiler-checked
`cas_expression` strings in `level2_full_10k.jsonl` -- and builds three task families around the
operations frozen in `OPERATION_CONTRACTS.json`.

WHAT THE SDG RECORDS ARE, AND ARE NOT, USED FOR. A level2 record's `prompt` says things like "Describe a
situation in which the emergent register Omega_clarity arises" and its `cas_expression` ends in
`Ω_clarity`: the label sits inside both. So the SDG's prompt/response text is NOT used here at all. Its
expressions are used only as a pool of syntactically valid CAS, re-compiled and re-validated here.

THREE FAMILIES.
  R  reconstruction     observation = the expression as text.   target = canonical AST (sealed).
                        Split by AST SHAPE (leaves abstracted), so a held-out shape has never been seen.
                        Its mechanism-free ceiling is the compiler itself: R measures FIDELITY, not
                        reasoning, and the report says so.
  A  admissibility      observation = (operator k, source state, target state) as typed fields.
                        target = bool from the contract's `is_admissible` (sealed). THE ORDER-SENSITIVE
                        FAMILY. Split by whole (k, source_domain, target_domain) CELLS: a held-out cell has
                        never been seen with ANY noetics, so a row-level memoriser cannot pass.
                        Includes INVALID_INPUT cases (out-of-range operands) with the refusal sealed.
  C  compose chains     observation = a bracketed chain over `compose`.  target = the result (sealed).
                        Longer chains are held out. The modular-sum baseline scores 1.0 here by
                        construction, so C is CONFORMANCE-ONLY and never evidence of grouping-sensitivity.

VISIBILITY IS A FILE BOUNDARY, NOT A PROMISE. `visible_<split>.jsonl` holds only the fields a model may
see; `sealed_<split>.jsonl` holds targets, oracle traces and validity. They share `record_id`, which is
sha256(seed, family, index) -- a function of position only, so it carries no answer. `manifest.json`
lists, per family and per mode, exactly which fields are visible and which are withheld.

BASELINES ARE REGISTERED HERE, BEFORE ANY TRAINING. For each family the cheapest mechanism-free rules are
scored on the EVAL split and written into `baselines.json`. A learned result on these files is
uninterpretable until it is read beside them.

Determinism: one seed, no wall-clock, no filesystem order dependence. Two builds must be byte-identical
(`test_q3_behaviour_records.py` asserts it). Cost: `$0`. No torch, no GPU, no model.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reference_ops as ref  # noqa: E402  -- the EVALUATOR's oracle; targets only, never a model input

REPO = HERE.parents[3]
def _main_checkout():
    """The sparse worktree does not hold the scaffold; the main checkout above `_worktrees/` does. Walk up
    until the compiler is found rather than trusting a fixed depth -- the worktree sits five levels below."""
    for cand in [REPO] + list(REPO.parents):
        if (cand / "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py").is_file():
            return cand
    return REPO                                # _find_scaffold will refuse with a clear message


MAIN_CHECKOUT = _main_checkout()
SCHEMA = "helm-cas-expression-lab.q3-behaviour-records/0.1"
SEED = 20260921
FAMILIES = ("R", "A", "C")
SPLITS = ("train", "dev", "eval")
SIZES = {"train": 2048, "dev": 256, "eval": 256}      # directive s11 engineering-smoke ceilings, not targets
SDG_POOL = "cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl"


def _sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _record_id(seed, family, index):
    """A function of POSITION only. Never of content, never of the answer."""
    return _sha("%d:%s:%d" % (seed, family, index))[:24]


# ---------------------------------------------------------------------------------------------
# The compiler: resolved, hashed, and used ONLY to produce sealed targets and validity for family R.
# ---------------------------------------------------------------------------------------------
def _find_scaffold():
    for root in (REPO, MAIN_CHECKOUT):
        cand = root / "noetic-compass-scaffold/noetic-compass"
        if (cand / "api/notation/compiler.py").is_file():
            return cand
    raise SystemExit("Q3_REFUSED:COMPILER_MISSING: neither the worktree nor the main checkout holds api/notation/compiler.py")


def _load_compiler():
    scaffold = _find_scaffold()
    sys.path.insert(0, str(scaffold))
    from api.notation.compiler import compile_expression  # noqa: E402
    source = (scaffold / "api/notation/compiler.py").read_bytes().replace(b"\r\n", b"\n")
    return compile_expression, {"path": "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py",
                                "resolved_from": "worktree" if scaffold.is_relative_to(REPO) else "main_checkout",
                                "sha256": hashlib.sha256(source).hexdigest(), "hash_policy": "lf-normalised"}


def _find_pool():
    for root in (REPO, MAIN_CHECKOUT):
        cand = root / SDG_POOL
        if cand.is_file():
            data = cand.read_bytes().replace(b"\r\n", b"\n")
            return cand, {"path": SDG_POOL, "sha256": hashlib.sha256(data).hexdigest(), "hash_policy": "lf-normalised"}
    raise SystemExit("Q3_REFUSED:SDG_POOL_MISSING:%s" % SDG_POOL)


# ---------------------------------------------------------------------------------------------
# Canonical AST and its SHAPE key (leaves abstracted) -- the split key for family R.
# ---------------------------------------------------------------------------------------------
def canonical(ast):
    """Sorted-key JSON of the compiler's AST. Operand ORDER and nesting are preserved: `left`/`right` stay
    positional. This is the exact-match target; nothing is simplified away (directive s9)."""
    return json.dumps(ast, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def shape(ast):
    """The AST with every leaf value replaced by its FIELD-PRESENCE signature, so `^3^P_{F2}|f` and
    `^7^C_{F5}|A` share a shape but `^3^P|f` (no drive) does not. Structure-family key for splitting."""
    if isinstance(ast, dict):
        node = ast.get("node")
        if node == "StateLiteral":
            return {"node": node, "fields": sorted(k for k, v in ast.items() if k != "node" and v is not None)}
        return {k: (shape(v) if isinstance(v, (dict, list)) else ("<name>" if k == "assigned_name" else v))
                for k, v in ast.items()}
    if isinstance(ast, list):
        return [shape(x) for x in ast]
    return ast


def _ast_size(ast):
    if isinstance(ast, dict):
        return 1 + sum(_ast_size(v) for v in ast.values() if isinstance(v, (dict, list)))
    if isinstance(ast, list):
        return sum(_ast_size(x) for x in ast)
    return 0


# ---------------------------------------------------------------------------------------------
# Family R -- reconstruction
# ---------------------------------------------------------------------------------------------
def build_family_R(rng, compile_expression, pool_path):
    seen, rows = set(), []
    with open(pool_path, encoding="utf-8") as handle:
        for line in handle:
            try:
                expr = json.loads(line).get("cas_expression", "")
            except ValueError:
                continue
            if not expr or expr in seen:
                continue
            seen.add(expr)
            art = compile_expression(expr).to_dict()
            if not art["valid"] or art["ast"] is None:
                continue
            rows.append({"expression": expr, "ast": art["ast"]})
    # group by SHAPE, then assign whole groups to splits: a held-out shape never appears in train.
    groups = collections.defaultdict(list)
    for row in rows:
        groups[_sha(shape(row["ast"]))[:16]].append(row)
    keys = sorted(groups)
    rng.shuffle(keys)
    # groups are uneven; fill eval and dev first with SMALL groups so the held-out shapes are genuinely rare
    keys.sort(key=lambda k: (len(groups[k]), k))
    split_of = {}
    quota = dict(SIZES)
    for split in ("eval", "dev"):
        for k in keys:
            if k in split_of:
                continue
            if quota[split] - len(groups[k]) >= 0:
                split_of[k] = split
                quota[split] -= len(groups[k])
            if quota[split] <= 0:
                break
    for k in keys:
        split_of.setdefault(k, "train")
    out = {s: [] for s in SPLITS}
    for k in keys:
        for row in groups[k]:
            out[split_of[k]].append({**row, "shape_key": k})
    for s in SPLITS:
        rng.shuffle(out[s])
        out[s] = out[s][:SIZES[s]]
    return out, {"pool_expressions": len(seen), "valid_unique": len(rows), "shape_groups": len(groups)}


def emit_R(rows, split, seed):
    visible, sealed = [], []
    for i, row in enumerate(rows):
        rid = _record_id(seed, "R:" + split, i)
        visible.append({"record_id": rid, "family": "R", "mode": "reconstruction", "observation": row["expression"]})
        sealed.append({"record_id": rid, "family": "R", "target_canonical_ast": canonical(row["ast"]),
                       "target_ast": row["ast"], "ast_size": _ast_size(row["ast"]), "shape_key": row["shape_key"],
                       "validity": "VALID", "oracle": "api.notation.compiler.compile_expression"})
    return visible, sealed


# ---------------------------------------------------------------------------------------------
# Family A -- admissibility execution (the order-sensitive family)
# ---------------------------------------------------------------------------------------------
def build_family_A(rng):
    states = [(d, n) for d in ref.DOMAINS for n in range(10)]
    cells = [(k, sd, td) for k in range(10) for sd in ref.DOMAINS for td in ref.DOMAINS]     # 160 cells
    rng.shuffle(cells)
    held = {"eval": set(cells[:24]), "dev": set(cells[24:40])}                                 # 15% + 10% of cells
    split_of_cell = {c: ("eval" if c in held["eval"] else "dev" if c in held["dev"] else "train") for c in cells}
    triples = [(k, s, t) for k in range(10) for s in states for t in states]                   # 16,000
    rng.shuffle(triples)
    out = {s: [] for s in SPLITS}
    for k, s, t in triples:
        split = split_of_cell[(k, s[0], t[0])]
        if len(out[split]) < SIZES[split]:
            out[split].append({"operator": k, "source": list(s), "target": list(t), "kind": "VALID"})
    # invalid-input cases: refusals are targets too. ~6% of each split.
    bad = [{"operator": 10, "source": ["P", 0], "target": ["P", 0]}, {"operator": 3, "source": ["X", 0], "target": ["P", 0]},
           {"operator": 3, "source": ["P", 10], "target": ["P", 0]}, {"operator": -1, "source": ["C", 2], "target": ["E", 2]},
           {"operator": 4, "source": ["P", 1], "target": ["Q", 4]}, {"operator": 2, "source": ["O", 9], "target": ["O", 11]}]
    for s in SPLITS:
        n_bad = max(1, SIZES[s] // 16)
        for j in range(n_bad):
            b = dict(bad[j % len(bad)])
            out[s].insert(rng.randrange(len(out[s]) + 1), {**b, "kind": "INVALID_INPUT"})
    return out, {"cells": len(cells), "cells_held_eval": len(held["eval"]), "cells_held_dev": len(held["dev"]),
                 "held_cells_eval": sorted(["%d:%s>%s" % c for c in held["eval"]]),
                 "held_cells_dev": sorted(["%d:%s>%s" % c for c in held["dev"]])}


def emit_A(rows, split, seed):
    visible, sealed = [], []
    for i, row in enumerate(rows):
        rid = _record_id(seed, "A:" + split, i)
        visible.append({"record_id": rid, "family": "A", "mode": "neural_operation_execution",
                        "operation_id": "cas.op.is_admissible/1.0",
                        "observation": {"operator": row["operator"], "source": row["source"], "target": row["target"]}})
        if row["kind"] == "INVALID_INPUT":
            sealed.append({"record_id": rid, "family": "A", "outcome": "INVALID_INPUT", "target": None,
                           "cell": None, "oracle": "reference_ops.is_admissible", "trace": "InvalidInput raised"})
            continue
        s, t = tuple(row["source"]), tuple(row["target"])
        value = ref.is_admissible(row["operator"], s, t)
        why = ("CO-0 diagonal" if row["operator"] == 0 else "same domain" if s[0] == t[0]
               else "cross-domain, target noetic == operator" if t[1] == row["operator"] else "cross-domain, target noetic != operator")
        sealed.append({"record_id": rid, "family": "A", "outcome": "CORRECT_IF_MATCH", "target": value,
                       "cell": "%d:%s>%s" % (row["operator"], s[0], t[0]), "oracle": "reference_ops.is_admissible",
                       "trace": why})
    return visible, sealed


# ---------------------------------------------------------------------------------------------
# Family C -- compose chains (conformance-only)
# ---------------------------------------------------------------------------------------------
def _chain(rng, depth):
    """A bracketed chain string with EXPLICIT grouping, e.g. 'compose(compose(3, 4), 7)'. The result is
    order- and grouping-independent for this operation (it is a group), which is exactly why C is a
    conformance family: the sealed trace records the grouping anyway, for the day a non-commutative op exists."""
    expr, value = str(rng.randrange(10)), None
    value = int(expr)
    for _ in range(depth):
        k = rng.randrange(10)
        if rng.random() < 0.5:
            expr, value = "compose(%s, %d)" % (expr, k), ref.compose(value, k)
        else:
            expr, value = "compose(%d, %s)" % (k, expr), ref.compose(k, value)
    return expr, value


def build_family_C(rng):
    out = {s: [] for s in SPLITS}
    depth_of = {"train": (1, 2, 3), "dev": (1, 2, 3), "eval": (4, 5, 6)}      # longer chains held out
    for s in SPLITS:
        seen = set()
        while len(out[s]) < SIZES[s]:
            expr, value = _chain(rng, rng.choice(depth_of[s]))
            if expr in seen:
                continue
            seen.add(expr)
            out[s].append({"expression": expr, "value": value, "depth": expr.count("compose(")})
    return out, {"depths": {s: list(depth_of[s]) for s in SPLITS}}


def emit_C(rows, split, seed):
    visible, sealed = [], []
    for i, row in enumerate(rows):
        rid = _record_id(seed, "C:" + split, i)
        visible.append({"record_id": rid, "family": "C", "mode": "neural_operation_execution",
                        "operation_id": "cas.op.compose/1.0", "observation": row["expression"]})
        sealed.append({"record_id": rid, "family": "C", "outcome": "CORRECT_IF_MATCH", "target": row["value"],
                       "depth": row["depth"], "oracle": "reference_ops.compose",
                       "trace": "modular sum; grouping irrelevant for this operation (conformance-only)"})
    return visible, sealed


# ---------------------------------------------------------------------------------------------
# Baselines -- registered on EVAL before anything is trained.
# ---------------------------------------------------------------------------------------------
def baselines_A(vis_train, seal_train, vis_eval, seal_eval):
    tv = {r["record_id"]: r for r in seal_train}
    valid_train = [(v["observation"], tv[v["record_id"]]["target"]) for v in vis_train if tv[v["record_id"]]["target"] is not None]
    majority = collections.Counter(t for _, t in valid_train).most_common(1)[0][0]
    memo = {json.dumps(o, sort_keys=True): t for o, t in valid_train}
    ev = {r["record_id"]: r for r in seal_eval}
    rules = {
        "constant_majority": lambda o: majority,
        "same_domain_only": lambda o: o["source"][0] == o["target"][0],
        "target_noetic_equals_operator": lambda o: o["target"][1] == o["operator"],
        "same_domain_or_target_noetic_equals_operator_ignoring_CO0": lambda o: o["source"][0] == o["target"][0] or o["target"][1] == o["operator"],
        "exact_row_memory_from_train": lambda o: memo.get(json.dumps(o, sort_keys=True)),
        "always_valid_never_refuse": lambda o: True,
    }
    out = {}
    for name, rule in rules.items():
        hit = n = refusals_missed = 0
        for v in vis_eval:
            s = ev[v["record_id"]]
            n += 1
            if s["outcome"] == "INVALID_INPUT":
                refusals_missed += 1            # none of these rules refuse; they all answer
                continue
            try:
                hit += (rule(v["observation"]) is s["target"]) or (rule(v["observation"]) == s["target"] and rule(v["observation"]) is not None)
            except Exception:
                pass
        out[name] = {"exact": round(hit / n, 6), "n": n, "refusals_missed": refusals_missed}
    out["exact_symbolic_reference"] = {"exact": 1.0, "n": len(vis_eval), "note": "the contract oracle; the ceiling, not a competitor"}
    return out


def baselines_C(vis_eval, seal_eval):
    ev = {r["record_id"]: r for r in seal_eval}
    hit = 0
    for v in vis_eval:
        digits = [int(x) for x in v["observation"].replace("compose(", " ").replace(")", " ").replace(",", " ").split()]
        hit += (sum(digits) % 10) == ev[v["record_id"]]["target"]
    return {"modular_sum_ignoring_grouping": {"exact": round(hit / len(vis_eval), 6), "n": len(vis_eval),
                                             "note": "1.0 by construction; C is conformance-only"},
            "constant_majority": {"exact": round(max(collections.Counter(ev[v["record_id"]]["target"] for v in vis_eval).values()) / len(vis_eval), 6)}}


def baselines_R(vis_eval, seal_eval):
    ev = {r["record_id"]: r for r in seal_eval}
    sizes = collections.Counter(ev[v["record_id"]]["ast_size"] for v in vis_eval)
    return {"compiler_reference": {"exact": 1.0, "note": "the oracle; R measures fidelity, not reasoning"},
            "copy_input_string_as_ast": {"exact": 0.0, "note": "a string is not an AST; exact match impossible"},
            "eval_ast_size_distribution": dict(sorted(sizes.items()))}


# ---------------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(HERE / "data" / "q3_v0_1"))
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    compile_expression, compiler_pin = _load_compiler()
    pool_path, pool_pin = _find_pool()
    contract = json.loads((HERE / "OPERATION_CONTRACTS.json").read_text(encoding="utf-8"))

    rng = random.Random(args.seed)
    R, statsR = build_family_R(random.Random(args.seed + 1), compile_expression, pool_path)
    A, statsA = build_family_A(random.Random(args.seed + 2))
    C, statsC = build_family_C(random.Random(args.seed + 3))

    files, counts = {}, {}
    packets = {"R": {}, "A": {}, "C": {}}
    for fam, rows_by_split, emit in (("R", R, emit_R), ("A", A, emit_A), ("C", C, emit_C)):
        for split in SPLITS:
            vis, seal = emit(rows_by_split[split], split, args.seed)
            packets[fam][split] = (vis, seal)
            for kind, rows in (("visible", vis), ("sealed", seal)):
                path = out / ("%s_%s_%s.jsonl" % (kind, fam, split))
                body = "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n"
                path.write_bytes(body.encode("utf-8"))
                files[path.name] = {"records": len(rows), "sha256": _sha(body.encode("utf-8"))}
            counts["%s_%s" % (fam, split)] = len(vis)

    baselines = {"schema": "helm-cas-expression-lab.q3-baselines/0.1", "scored_on": "eval",
                 "A": baselines_A(*packets["A"]["train"], *packets["A"]["eval"]),
                 "C": baselines_C(*packets["C"]["eval"]), "R": baselines_R(*packets["R"]["eval"])}
    (out / "baselines.json").write_text(json.dumps(baselines, indent=1, sort_keys=True), encoding="utf-8")

    manifest = {
        "schema": SCHEMA, "seed": args.seed, "built": "2026-09-21", "generator": pathlib.Path(__file__).name,
        "operation_contracts_digest": contract["contract_digest"], "compiler": compiler_pin, "sdg_pool": pool_pin,
        "sdg_usage": "expression strings only; SDG prompt/response text is never read (the label sits inside it)",
        "sizes": SIZES, "counts": counts, "files": files, "stats": {"R": statsR, "A": statsA, "C": statsC},
        "visibility": {
            "R": {"mode": "reconstruction", "visible": ["record_id", "family", "mode", "observation"],
                  "withheld": ["target_canonical_ast", "target_ast", "ast_size", "shape_key", "validity", "oracle"],
                  "teacher_forcing_note": "a target may be used to compute training LOSS; it is never a model INPUT at evaluated prediction; teacher-forced passes are not free-running reconstruction and must be reported apart"},
            "A": {"mode": "neural_operation_execution", "visible": ["record_id", "family", "mode", "operation_id", "observation"],
                  "withheld": ["outcome", "target", "cell", "oracle", "trace"]},
            "C": {"mode": "neural_operation_execution", "visible": ["record_id", "family", "mode", "operation_id", "observation"],
                  "withheld": ["outcome", "target", "depth", "oracle", "trace"]},
        },
        "split_policy": {"R": "whole AST-shape groups; eval and dev take the rarest shapes first",
                         "A": "whole (operator, source_domain, target_domain) cells: 24 eval, 16 dev, 120 train",
                         "C": "by chain depth: train/dev 1-3, eval 4-6"},
        "exposure_report": {
            "R": "surface form: none shared across splits (deduplicated); AST shape: none shared across splits by construction; atomic literals: SHARED (every family reuses the same 40 states, drives, registers) -- disclosed, not forbidden",
            "A": "operator ids and domains are all seen in training; held-out CELLS are unseen combinations of them; individual (source, target) noetic pairs may recur across cells -- disclosed",
            "C": "the operation and all ten digits are seen; held-out DEPTHS are unseen; the baseline solves every depth",
        },
        "record_id_policy": "sha256(seed, family:split, index)[:24] -- position only; no content, no answer, no source hash",
        "reference_learner_separation": "sealed_* files are the evaluator's; a learner may open visible_* only. Enforced by test_q3_behaviour_records.py.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    print("Q3 v0.1 written to %s" % out)
    print("  counts:", counts)
    print("  R: pool %d unique expressions, %d valid, %d shape groups" % (statsR["pool_expressions"], statsR["valid_unique"], statsR["shape_groups"]))
    print("  A: %d cells, %d held for eval, %d for dev" % (statsA["cells"], statsA["cells_held_eval"], statsA["cells_held_dev"]))
    print("  baselines on eval, family A:")
    for name, row in baselines["A"].items():
        print("    %-58s exact %s" % (name, row["exact"]))
    print("  baselines on eval, family C: modular_sum %s" % baselines["C"]["modular_sum_ignoring_grouping"]["exact"])
    print("  compiler %s @ %s (%s)" % (compiler_pin["path"].split("/")[-1], compiler_pin["sha256"][:12], compiler_pin["resolved_from"]))
    print("Q3_BUILD_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
