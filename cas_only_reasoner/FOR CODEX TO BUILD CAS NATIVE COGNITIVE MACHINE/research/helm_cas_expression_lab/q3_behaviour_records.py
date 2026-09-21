"""Q3 v0.3 -- behaviour-paired records with SEALED targets, STRICT structure splits, and baselines that include the attacks.

v0.3 (2026-09-21) changes three things and nothing else; v0.2 stays on disk as the artifact that was reviewed:
  * BOUND TO THE CURRENT CONTRACT. v0.2's manifest and its 10,376 exported records cite contract digest e97b8aa6..., a
    version HEAD stopped holding when the contract was rebuilt; nothing compared the two. v0.3 is built against
    OPERATION_CONTRACTS.json 0.2, and a test and the exporter now REFUSE a manifest whose digest is not the contract's.
  * EVERY CASE FAMILY IS PRESENT IN DEV AND EVAL. v0.2's dev had ZERO operator-^0 rows and eval had four, so the identity
    operator could not be measured at all. Held-out cells now always include an ^0 same-domain cell, an ^0 cross-domain
    cell, a non-identity same-domain cell and a non-identity cross-domain cell in each of dev and eval, and the non-flip
    half of those splits is stratified across the case families (with ^0 diagonal positives guaranteed).
  * BASELINES ARE SCORED BY CASE FAMILY, ON DEV AND ON EVAL, each with its n. 'Always inadmissible' is named in plain
    words. An outside reviewer measured it at 0.705 on the full uniform grid; on these splits it is whatever the file says.
Notation follows the owner's ruling: ^0 .. ^9.


Directive section 8. An ISOLATED, VERSIONED adapter beside `cas-synthetic`. It never modifies the
generator, its templates or its frozen outputs, and it never reads SDG prompt/response text (a level2
prompt says "Describe a situation in which the emergent register Omega_clarity arises" -- the label sits
inside the prompt and inside the expression). Only compiler-checked `cas_expression` strings are read.

v0.1 (`data/q3_v0_1/`, kept on disk untouched as the reviewed artifact) was attacked by three independent
reviewers on 2026-09-21. All three attacks succeeded. v0.2 is the response, and every change below names
the finding it answers:

  A1  A hand rule -- the registered rule + "^0 needs source == target" + a range check that refuses
      out-of-range fields -- scores 1.000000 on A eval; so does a 4-feature majority lookup filled from
      train. The answer depends only on field EQUALITIES (op==0, same_domain, target_noetic==op,
      source==target), so holding out (op, source_domain, target_domain) cells holds out NO rule component.
      -> A is relabelled a CONFORMANCE-AND-TRANSFER family, never a discovery test. Both rules are
      registered as baselines. The manifest says so in plain words.
  A2  Only 30 of 256 valid eval rows changed answer when source and target were swapped, so the overall
      score was dominated by rows where order does not matter.
      -> eval and dev are REBALANCED so at least half of their valid rows are order-flip rows, and every
      rule is ALSO scored on the flip rows and on the swapped twin of every row (the order-flip metric).
  A3  Refusals were six fixed templates recycled into every split: 16/16 eval refusals were verbatim train
      rows, and the row-memory baseline hid it by skipping refusal rows.
      -> refusals are generated per split from SPLIT-DISJOINT value pools and type classes (out-of-range
      ints, floats that equal ints, booleans, strings, missing and extra keys); the test asserts no refusal
      observation is shared across splits; row memory now includes refusals; "answer False, refuse
      out-of-range" (0.764706 on v0.1) is registered.
  R1  `shape()` kept coefficient values and Omega names as leaves, so it was a FINGERPRINT: every eval
      group was a singleton, and with leaves abstracted 251/256 eval structures were already in train
      (eval was 80% RecipeLiteral against 8% in train).
      -> `strict_shape()` abstracts EVERY scalar leaf to its type. R is split by strict shape (groups are
      disjoint by construction; eval is therefore SMALL and the manifest says how small). R is labelled a
      FIDELITY family with the compiler as its ceiling, and the reviewer's measurement that one regular
      expression reproduces 204/256 of v0.1's eval targets is quoted.
  G   Because the SDG pool is structurally narrow (about 71 strict shapes), a NEW family G generates nested
      binary trees over state literals from the grammar itself, compiles each one, and holds out whole
      TOPOLOGIES and longer depths. G is the structural-generalisation family R could not be.
  C1  C's dev split was not deduplicated against train (102/256 verbatim; depth-1 has only 100 strings).
      -> one seen-set across ALL splits, train first; dev depths (2, 3); the sub-chain exposure
      ("every eval chain contains a verbatim train chain as a sub-expression") is MEASURED and disclosed,
      and the digit-multiset check, which was vacuous, is gone.
  B1  Two ceilings were written as the literal 1.0. -> every reference score is MEASURED.
  I1  `record_id` hashed the JSON-quoted string while the doc said otherwise. -> the raw string is hashed
      and the doc says exactly what.

VISIBILITY IS A FILE BOUNDARY, NOT A SECRET. The reviewers also showed that the whole sealed side
regenerates from this public code and its public seed. That is by design: the seal is a discipline
against a LEARNER (a learner may open `visible_*` only), not a secret against anyone holding the repo.

Determinism: one seed, no wall-clock, no filesystem order. Two builds are byte-identical. Cost `$0`.
"""
import argparse
import collections
import hashlib
import itertools
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reference_ops as ref  # noqa: E402  -- the EVALUATOR's oracle; targets only, never a model input

REPO = HERE.parents[3]


def _main_checkout():
    """The sparse worktree does not hold the scaffold; the main checkout above `_worktrees/` does. Walk up."""
    for cand in [REPO] + list(REPO.parents):
        if (cand / "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py").is_file():
            return cand
    return REPO


MAIN_CHECKOUT = _main_checkout()
SCHEMA = "helm-cas-expression-lab.q3-behaviour-records/0.3"
SEED = 20260921
FAMILIES = ("R", "G", "A", "C")
SPLITS = ("train", "dev", "eval")
SIZES = {"train": 2048, "dev": 256, "eval": 256}      # directive s11 engineering-smoke CEILINGS, not targets
SDG_POOL = "cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl"


def _sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _sha_json(value):
    return _sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _record_id(seed, family_split, index):
    """sha256 of the RAW string "<seed>:<family>:<split>:<index>", first 24 hex. Position only."""
    return _sha_bytes(("%d:%s:%d" % (seed, family_split, index)).encode("utf-8"))[:24]


# ---------------------------------------------------------------------------------------------
# External inputs: the compiler (targets for R and G) and the SDG expression pool (R only), both hashed.
# ---------------------------------------------------------------------------------------------
def _find_scaffold():
    for root in (REPO, MAIN_CHECKOUT):
        cand = root / "noetic-compass-scaffold/noetic-compass"
        if (cand / "api/notation/compiler.py").is_file():
            return cand
    raise SystemExit("Q3_REFUSED:COMPILER_MISSING")


def _load_compiler():
    scaffold = _find_scaffold()
    sys.path.insert(0, str(scaffold))
    from api.notation.compiler import compile_expression  # noqa: E402
    source = (scaffold / "api/notation/compiler.py").read_bytes().replace(b"\r\n", b"\n")
    return compile_expression, {"path": "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py",
                                "resolved_from": "worktree" if scaffold.is_relative_to(REPO) else "main_checkout",
                                "sha256": _sha_bytes(source), "hash_policy": "lf-normalised"}


def _find_pool():
    for root in (REPO, MAIN_CHECKOUT):
        cand = root / SDG_POOL
        if cand.is_file():
            return cand, {"path": SDG_POOL, "sha256": _sha_bytes(cand.read_bytes().replace(b"\r\n", b"\n")), "hash_policy": "lf-normalised"}
    raise SystemExit("Q3_REFUSED:SDG_POOL_MISSING:%s" % SDG_POOL)


# ---------------------------------------------------------------------------------------------
# Canonical AST and STRICT shape (finding R1).
# ---------------------------------------------------------------------------------------------
def canonical(ast):
    """Sorted-key JSON of the compiler's AST. `left`/`right` stay positional; nothing is simplified away."""
    return json.dumps(ast, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def strict_shape(ast):
    """The AST with EVERY scalar leaf replaced by its type tag. Node types and structural keys survive;
    coefficients, names, operators, domains, drives and registers do not. Two expressions share a strict
    shape iff their trees have the same topology and the same kinds of leaf in the same places."""
    if isinstance(ast, dict):
        out = {}
        for k, v in ast.items():
            if k == "node":
                out[k] = v
            elif isinstance(v, (dict, list)):
                out[k] = strict_shape(v)
            elif v is None:
                out[k] = "<null>"
            elif isinstance(v, bool):
                out[k] = "<bool>"
            elif isinstance(v, (int, float)):
                out[k] = "<num>"
            else:
                out[k] = "<str>"
        return out
    if isinstance(ast, list):
        return [strict_shape(x) for x in ast]
    return "<leaf>"


def _ast_size(ast):
    if isinstance(ast, dict):
        return 1 + sum(_ast_size(v) for v in ast.values() if isinstance(v, (dict, list)))
    if isinstance(ast, list):
        return sum(_ast_size(x) for x in ast)
    return 0


def _assign_groups_rarest_first(rng, groups, sizes):
    """Whole groups go to one split. eval, then dev, take the SMALLEST groups first, so held-out structure
    is genuinely rare; the rest is train. Returns {group_key: split}."""
    keys = sorted(groups, key=lambda k: (len(groups[k]), k))
    rng.shuffle(keys)
    keys.sort(key=lambda k: len(groups[k]))          # stable: rarest first, ties in shuffled order
    split_of, quota = {}, dict(sizes)
    for split in ("eval", "dev"):
        for k in keys:
            if k in split_of or quota[split] <= 0:
                continue
            if len(groups[k]) <= quota[split]:
                split_of[k] = split
                quota[split] -= len(groups[k])
    for k in keys:
        split_of.setdefault(k, "train")
    return split_of


# ---------------------------------------------------------------------------------------------
# Family R -- SDG expressions, reconstruction, STRICT-shape split. A FIDELITY family.
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
            if art["valid"] and art["ast"] is not None:
                rows.append({"expression": expr, "ast": art["ast"]})
    groups = collections.defaultdict(list)
    for row in rows:
        groups[_sha_json(strict_shape(row["ast"]))[:16]].append(row)
    split_of = _assign_groups_rarest_first(rng, groups, SIZES)
    out = {s: [] for s in SPLITS}
    for k, members in groups.items():
        for row in members:
            out[split_of[k]].append({**row, "shape_key": k})
    for s in SPLITS:
        rng.shuffle(out[s])
        out[s] = out[s][:SIZES[s]]
    stats = {"pool_expressions": len(seen), "valid_unique": len(rows), "strict_shape_groups": len(groups),
             "strict_shapes_per_split": {s: len({r["shape_key"] for r in out[s]}) for s in SPLITS},
             "root_node_mix": {s: dict(collections.Counter(r["ast"].get("node") for r in out[s])) for s in SPLITS}}
    return out, stats


def emit_R(rows, split, seed, family="R"):
    visible, sealed = [], []
    for i, row in enumerate(rows):
        rid = _record_id(seed, "%s:%s" % (family, split), i)
        visible.append({"record_id": rid, "family": family, "mode": "reconstruction", "observation": row["expression"]})
        sealed.append({"record_id": rid, "family": family, "target_canonical_ast": canonical(row["ast"]), "target_ast": row["ast"],
                       "ast_size": _ast_size(row["ast"]), "shape_key": row["shape_key"], "depth": row.get("depth"),
                       "validity": "VALID", "oracle": "api.notation.compiler.compile_expression"})
    return visible, sealed


# ---------------------------------------------------------------------------------------------
# Family G -- GENERATED nested binary trees from the grammar; whole topologies and longer depths held out.
# ---------------------------------------------------------------------------------------------
def _random_literal(rng):
    n, d = rng.randrange(10), rng.choice(ref.DOMAINS)
    lit = "^%d^%s" % (n, d)
    if rng.random() < 0.5:
        lit += "_{F%d}" % rng.randrange(1, 8)
    if rng.random() < 0.5:
        lit += "|" + rng.choice(("T", "A", "f", "E"))
    return lit


def _random_tree(rng, depth):
    """A binary tree of `depth` operator levels with EXPLICIT parentheses, so grouping is visible."""
    if depth == 0:
        return _random_literal(rng)
    left_depth = rng.randrange(depth)
    right_depth = depth - 1 if left_depth < depth - 1 else rng.randrange(depth)
    left, right = _random_tree(rng, left_depth), _random_tree(rng, right_depth)
    if max(left_depth, right_depth) < depth - 1:
        right = _random_tree(rng, depth - 1)
    return "(%s %s %s)" % (left, rng.choice(("+", "×")), right)


def build_family_G(rng, compile_expression):
    candidates, seen, rejected = [], set(), collections.Counter()
    per_depth = {1: 900, 2: 900, 3: 900, 4: 700, 5: 500}
    for depth, n in per_depth.items():
        made = 0
        while made < n:
            expr = _random_tree(rng, depth)
            if expr in seen:
                continue
            seen.add(expr)
            art = compile_expression(expr).to_dict()
            if not art["valid"] or art["ast"] is None:
                rejected[depth] += 1
                continue
            candidates.append({"expression": expr, "ast": art["ast"], "depth": depth})
            made += 1
    groups = collections.defaultdict(list)
    for row in candidates:
        groups[_sha_json(strict_shape(row["ast"]))[:16]].append(row)
    # eval takes whole topologies of depth >= 4 first (unseen and longer), then rarest; dev takes rarest of the rest.
    deep = {k for k, m in groups.items() if min(r["depth"] for r in m) >= 4}
    split_of, quota = {}, dict(SIZES)
    for k in sorted(deep, key=lambda k: (len(groups[k]), k)):
        if len(groups[k]) <= quota["eval"]:
            split_of[k] = "eval"
            quota["eval"] -= len(groups[k])
    rest = {k: m for k, m in groups.items() if k not in split_of}
    split_of.update(_assign_groups_rarest_first(rng, rest, {"eval": quota["eval"], "dev": quota["dev"], "train": SIZES["train"]}))
    out = {s: [] for s in SPLITS}
    for k, members in groups.items():
        for row in members:
            out[split_of[k]].append({**row, "shape_key": k})
    for s in SPLITS:
        rng.shuffle(out[s])
        out[s] = out[s][:SIZES[s]]
    stats = {"generated_valid": len(candidates), "rejected_by_compiler": dict(rejected), "strict_shape_groups": len(groups),
             "strict_shapes_per_split": {s: len({r["shape_key"] for r in out[s]}) for s in SPLITS},
             "depths_per_split": {s: dict(sorted(collections.Counter(r["depth"] for r in out[s]).items())) for s in SPLITS}}
    return out, stats


# ---------------------------------------------------------------------------------------------
# Family A -- admissibility. CONFORMANCE-AND-TRANSFER, order-flip balanced, split-disjoint refusals.
# ---------------------------------------------------------------------------------------------
REFUSAL_POOLS = {   # split-disjoint VALUES and TYPE CLASSES (finding A3). Every one is refused by reference_ops.
    "train": {"bad_ints": (10, 11, 12, -1, -2), "bad_domains": ("X", "Y"), "types": ("float", "missing_key")},
    "dev":   {"bad_ints": (13, 14, 15, -3, -4), "bad_domains": ("Q", "Z"), "types": ("bool", "extra_key")},
    "eval":  {"bad_ints": (16, 17, 18, -5, -6), "bad_domains": ("W", "V"), "types": ("float_equal_to_int", "string")},
}


def _refusal_case(rng, split):
    pool, base = REFUSAL_POOLS[split], {"operator": rng.randrange(10), "source": [rng.choice(ref.DOMAINS), rng.randrange(10)],
                                       "target": [rng.choice(ref.DOMAINS), rng.randrange(10)]}
    kind = rng.choice(("bad_operator", "bad_domain", "bad_noetic") + pool["types"])
    if kind == "bad_operator":
        base["operator"] = rng.choice(pool["bad_ints"])
    elif kind == "bad_domain":
        base[rng.choice(("source", "target"))][0] = rng.choice(pool["bad_domains"])
    elif kind == "bad_noetic":
        base[rng.choice(("source", "target"))][1] = rng.choice(pool["bad_ints"])
    elif kind == "float":
        base["operator"] = rng.randrange(10) + 0.5
    elif kind == "float_equal_to_int":
        base[rng.choice(("source", "target"))][1] = float(rng.randrange(10))
    elif kind == "bool":
        base["operator"] = bool(rng.randrange(2))
    elif kind == "string":
        base["operator"] = str(rng.randrange(10))
    elif kind == "missing_key":
        del base[rng.choice(("source", "target"))]
    elif kind == "extra_key":
        base["via"] = [rng.choice(ref.DOMAINS), rng.randrange(10)]
    return base, kind


def _refuses(observation):
    """The evaluator's range check: does `reference_ops.is_admissible` refuse this observation?"""
    try:
        if set(observation) != {"operator", "source", "target"}:
            return True
        ref.is_admissible(observation["operator"], tuple(observation["source"]), tuple(observation["target"]))
        return False
    except (ref.InvalidInput, TypeError, ValueError):
        return True


CASE_FAMILIES = ("op0_same_domain", "op0_cross_domain", "nonidentity_same_domain", "nonidentity_cross_domain")


def case_family(operator, source, target):
    """The four kinds of valid question. ^0 is the identity operator; 'same domain' compares the two domain letters."""
    same = source[0] == target[0]
    if operator == 0:
        return "op0_same_domain" if same else "op0_cross_domain"
    return "nonidentity_same_domain" if same else "nonidentity_cross_domain"


def build_family_A(rng):
    states = [(d, n) for d in ref.DOMAINS for n in range(10)]
    cells = [(k, sd, td) for k in range(10) for sd in ref.DOMAINS for td in ref.DOMAINS]
    rng.shuffle(cells)
    # v0.3: each of eval and dev is GUARANTEED one cell of every case family, then filled at random to 24 and 16
    by_family = {f: [c for c in cells if case_family(c[0], (c[1], 0), (c[2], 0)) == f] for f in CASE_FAMILIES}
    held = {"eval": {by_family[f][0] for f in CASE_FAMILIES}, "dev": {by_family[f][1] for f in CASE_FAMILIES}}
    rest = [c for c in cells if c not in held["eval"] and c not in held["dev"]]
    held["eval"] |= set(rest[:24 - len(held["eval"])])
    held["dev"] |= set(rest[20:20 + 16 - len(held["dev"])])
    split_of_cell = {c: ("eval" if c in held["eval"] else "dev" if c in held["dev"] else "train") for c in cells}
    triples = [(k, s, t) for k in range(10) for s in states for t in states]
    rng.shuffle(triples)
    pools = {s: {"flip": [], "flat": []} for s in SPLITS}
    for k, s, t in triples:
        split = split_of_cell[(k, s[0], t[0])]
        flip = ref.is_admissible(k, s, t) != ref.is_admissible(k, t, s)
        pools[split]["flip" if flip else "flat"].append({"operator": k, "source": list(s), "target": list(t), "order_flip": flip,
                                                        "case_family": case_family(k, s, t)})
    out = {s: [] for s in SPLITS}
    for s in SPLITS:
        if s == "train":
            rows = (pools[s]["flip"] + pools[s]["flat"])
            rng.shuffle(rows)
            out[s] = rows[:SIZES[s]]
        else:                                   # finding A2: at least half of valid rows are order-flip rows
            half = SIZES[s] // 2
            flat, chosen = pools[s]["flat"], []
            diagonal = [r for r in flat if r["case_family"] == "op0_same_domain" and r["source"] == r["target"]]
            chosen += diagonal[:6]                       # ^0 is admissible ONLY on the diagonal: guarantee some positives
            for fam in ("op0_same_domain", "op0_cross_domain", "nonidentity_same_domain"):
                chosen += [r for r in flat if r["case_family"] == fam and r not in chosen][:16]
            chosen += [r for r in flat if r not in chosen][:SIZES[s] - half - len(chosen)]
            out[s] = pools[s]["flip"][:half] + chosen
            rng.shuffle(out[s])
    refusal_strings = {}
    for s in SPLITS:
        n_bad, made, seen = max(1, SIZES[s] // 16), 0, set()
        while made < n_bad:
            obs, kind = _refusal_case(rng, s)
            key = json.dumps(obs, sort_keys=True)
            if key in seen or not _refuses(obs):
                continue
            seen.add(key)
            out[s].insert(rng.randrange(len(out[s]) + 1), {**obs, "refusal_kind": kind})
            made += 1
        refusal_strings[s] = seen
    stats = {"cells": len(cells), "cells_held_eval": 24, "cells_held_dev": 16,
             "held_cells_eval": sorted("%d:%s>%s" % c for c in held["eval"]), "held_cells_dev": sorted("%d:%s>%s" % c for c in held["dev"]),
             "order_flip_valid_rows": {s: sum(1 for r in out[s] if r.get("order_flip")) for s in SPLITS},
             "valid_rows": {s: sum(1 for r in out[s] if "order_flip" in r) for s in SPLITS},
             "refusal_rows": {s: sum(1 for r in out[s] if "refusal_kind" in r) for s in SPLITS},
             "valid_rows_by_case_family": {s: {f: sum(1 for r in out[s] if r.get("case_family") == f) for f in CASE_FAMILIES} for s in SPLITS},
             "op0_diagonal_positive_rows": {s: sum(1 for r in out[s] if r.get("case_family") == "op0_same_domain" and r["source"] == r["target"]) for s in SPLITS},
             "admissible_rows": {s: sum(1 for r in out[s] if "order_flip" in r and ref.is_admissible(r["operator"], tuple(r["source"]), tuple(r["target"]))) for s in SPLITS},
             "refusal_observations_shared_across_splits": len(refusal_strings["train"] & refusal_strings["dev"])
             + len(refusal_strings["train"] & refusal_strings["eval"]) + len(refusal_strings["dev"] & refusal_strings["eval"])}
    return out, stats


def emit_A(rows, split, seed):
    visible, sealed = [], []
    for i, row in enumerate(rows):
        rid = _record_id(seed, "A:%s" % split, i)
        obs = {k: v for k, v in row.items() if k in ("operator", "source", "target", "via")}
        visible.append({"record_id": rid, "family": "A", "mode": "neural_operation_execution",
                        "operation_id": "cas.op.is_admissible/1.0", "observation": obs})
        if "refusal_kind" in row:
            sealed.append({"record_id": rid, "family": "A", "outcome": "INVALID_INPUT", "target": None, "cell": None, "order_flip": None,
                           "refusal_kind": row["refusal_kind"], "oracle": "reference_ops.is_admissible", "trace": "InvalidInput raised"})
            continue
        s, t = tuple(row["source"]), tuple(row["target"])
        value = ref.is_admissible(row["operator"], s, t)
        why = (("^0 diagonal" if s == t else "^0 off the diagonal") if row["operator"] == 0 else "same domain" if s[0] == t[0]
               else "cross-domain, target noetic == operator" if t[1] == row["operator"] else "cross-domain, target noetic != operator")
        sealed.append({"record_id": rid, "family": "A", "outcome": "CORRECT_IF_MATCH", "target": value,
                       "cell": "%d:%s>%s" % (row["operator"], s[0], t[0]), "order_flip": row["order_flip"], "case_family": row["case_family"],
                       "swapped_target": ref.is_admissible(row["operator"], t, s),
                       "oracle": "reference_ops.is_admissible", "trace": why})
    return visible, sealed


# ---------------------------------------------------------------------------------------------
# Family C -- compose chains, conformance-only, deduplicated ACROSS splits (finding C1).
# ---------------------------------------------------------------------------------------------
def _chain(rng, depth):
    expr = str(rng.randrange(10))
    value = int(expr)
    for _ in range(depth):
        k = rng.randrange(10)
        if rng.random() < 0.5:
            expr, value = "compose(%s, %d)" % (expr, k), ref.compose(value, k)
        else:
            expr, value = "compose(%d, %s)" % (k, expr), ref.compose(k, value)
    return expr, value


def build_family_C(rng):
    out, seen = {s: [] for s in SPLITS}, set()
    depth_of = {"train": (1, 2, 3), "dev": (2, 3), "eval": (4, 5, 6)}
    for s in SPLITS:                                     # train first, so dev/eval can never repeat a train string
        while len(out[s]) < SIZES[s]:
            expr, value = _chain(rng, rng.choice(depth_of[s]))
            if expr in seen:
                continue
            seen.add(expr)
            out[s].append({"expression": expr, "value": value, "depth": expr.count("compose(")})
    train_strings = [r["expression"] for r in out["train"]]
    subchain = {s: sum(1 for r in out[s] if any(t in r["expression"] for t in train_strings)) for s in ("dev", "eval")}
    return out, {"depths": {s: list(depth_of[s]) for s in SPLITS},
                 "verbatim_in_train": {s: sum(1 for r in out[s] if r["expression"] in set(train_strings)) for s in ("dev", "eval")},
                 "contain_a_verbatim_train_chain_as_subexpression": subchain}


def emit_C(rows, split, seed):
    visible, sealed = [], []
    for i, row in enumerate(rows):
        rid = _record_id(seed, "C:%s" % split, i)
        visible.append({"record_id": rid, "family": "C", "mode": "neural_operation_execution",
                        "operation_id": "cas.op.compose/1.0", "observation": row["expression"]})
        sealed.append({"record_id": rid, "family": "C", "outcome": "CORRECT_IF_MATCH", "target": row["value"], "depth": row["depth"],
                       "oracle": "reference_ops.compose", "trace": "modular sum; grouping irrelevant for this operation (conformance-only)"})
    return visible, sealed


# ---------------------------------------------------------------------------------------------
# Baselines -- registered on EVAL before anything trains, INCLUDING the reviewers' attacks (A1, A2, A3).
# ---------------------------------------------------------------------------------------------
def _valid_fields(o):
    return set(o) == {"operator", "source", "target"} and not _refuses(o)


def baselines_A(vis_train, seal_train, vis_eval, seal_eval):
    """Score every registered rule on ONE split (called for dev and for eval), overall and by case family."""
    tv, ev = {r["record_id"]: r for r in seal_train}, {r["record_id"]: r for r in seal_eval}
    train_valid = [(v["observation"], tv[v["record_id"]]["target"]) for v in vis_train if tv[v["record_id"]]["target"] is not None]
    majority = collections.Counter(t for _, t in train_valid).most_common(1)[0][0]
    assert majority is False, "the majority answer in train is expected to be 'inadmissible'"
    memo_all = {json.dumps(v["observation"], sort_keys=True): tv[v["record_id"]]["target"] for v in vis_train}   # refusals included (A3)
    memo_all_has = {json.dumps(v["observation"], sort_keys=True) for v in vis_train}

    def feats(o):
        return (o["operator"] == 0, o["source"][0] == o["target"][0], o["target"][1] == o["operator"], o["source"] == o["target"])
    table = collections.defaultdict(collections.Counter)
    for o, t in train_valid:
        table[feats(o)][t] += 1
    lookup = {k: c.most_common(1)[0][0] for k, c in table.items()}

    REFUSE = "INVALID_INPUT"
    rules = {
        "always_inadmissible (the constant majority answer)": lambda o: majority,
        "same_domain_only": lambda o: o["source"][0] == o["target"][0],
        "target_noetic_equals_operator": lambda o: o["target"][1] == o["operator"],
        "v0_1_registered_rule (same_domain or target_noetic==op)": lambda o: o["source"][0] == o["target"][0] or o["target"][1] == o["operator"],
        "R1 = registered + ^0 diagonal": lambda o: (o["source"] == o["target"]) if o["operator"] == 0 else (o["source"][0] == o["target"][0] or o["target"][1] == o["operator"]),
        "R3 = registered + ^0 + range-check refusal (reviewer's hand rule)": lambda o: REFUSE if not _valid_fields(o) else ((o["source"] == o["target"]) if o["operator"] == 0 else (o["source"][0] == o["target"][0] or o["target"][1] == o["operator"])),
        "R7 = 4-feature majority lookup from train + range-check refusal": lambda o: REFUSE if not _valid_fields(o) else lookup.get(feats(o), majority),
        "exact_row_memory_from_train_INCLUDING_refusals": lambda o: (memo_all[json.dumps(o, sort_keys=True)] if json.dumps(o, sort_keys=True) in memo_all_has else None),
        "answer_False_refuse_out_of_range": lambda o: REFUSE if not _valid_fields(o) else False,
        "ORDER_BLIND: same_domain or tn==k or sn==k (+^0, +refusal)": lambda o: REFUSE if not _valid_fields(o) else ((o["source"] == o["target"]) if o["operator"] == 0 else (o["source"][0] == o["target"][0] or o["target"][1] == o["operator"] or o["source"][1] == o["operator"])),
        "WRONG_DIRECTION: same_domain or sn==k (+^0, +refusal)": lambda o: REFUSE if not _valid_fields(o) else ((o["source"] == o["target"]) if o["operator"] == 0 else (o["source"][0] == o["target"][0] or o["source"][1] == o["operator"])),
        "exact_symbolic_reference (measured, not typed)": lambda o: REFUSE if not _valid_fields(o) else ref.is_admissible(o["operator"], tuple(o["source"]), tuple(o["target"])),
    }

    def score(rule):
        hit = n = flip_hit = flip_n = swap_consistent = swap_n = 0
        by = collections.OrderedDict((f, [0, 0]) for f in CASE_FAMILIES + ("refusal",))
        for v in vis_eval:
            s, o = ev[v["record_id"]], v["observation"]
            n += 1
            try:
                pred = rule(o)
            except Exception:
                pred = None
            want = REFUSE if s["outcome"] == "INVALID_INPUT" else s["target"]
            if pred == want and (pred is not None):
                hit += 1
            fam = "refusal" if s["outcome"] == "INVALID_INPUT" else s["case_family"]
            by[fam][0] += int(pred == want and pred is not None)
            by[fam][1] += 1
            if s.get("order_flip"):
                flip_n += 1
                flip_hit += (pred == want)
            if s["outcome"] != "INVALID_INPUT":
                swapped = {"operator": o["operator"], "source": o["target"], "target": o["source"]}
                try:
                    pred_sw = rule(swapped)
                except Exception:
                    pred_sw = None
                swap_n += 1
                swap_consistent += (pred_sw == s["swapped_target"])
        return {"exact": round(hit / n, 6), "n": n, "order_flip_exact": round(flip_hit / flip_n, 6) if flip_n else None,
                "order_flip_n": flip_n, "swapped_twin_exact": round(swap_consistent / swap_n, 6) if swap_n else None,
                "by_case_family": {f: {"exact": round(h / k, 6) if k else None, "n": k} for f, (h, k) in by.items()}}
    return {name: score(rule) for name, rule in rules.items()}


def baselines_C(vis_eval, seal_eval):
    ev = {r["record_id"]: r for r in seal_eval}
    hit = sum(1 for v in vis_eval if sum(int(x) for x in v["observation"].replace("compose(", " ").replace(")", " ").replace(",", " ").split()) % 10 == ev[v["record_id"]]["target"])
    return {"modular_sum_ignoring_grouping": {"exact": round(hit / len(vis_eval), 6), "n": len(vis_eval), "note": "conformance-only by construction"},
            "constant_majority": {"exact": round(max(collections.Counter(ev[v["record_id"]]["target"] for v in vis_eval).values()) / len(vis_eval), 6)}}


def baselines_reconstruction(compile_expression, vis_eval, seal_eval):
    ev = {r["record_id"]: r for r in seal_eval}
    hit = sum(1 for v in vis_eval if canonical(compile_expression(v["observation"]).to_dict()["ast"]) == ev[v["record_id"]]["target_canonical_ast"])
    return {"compiler_reference (measured, not typed)": {"exact": round(hit / max(1, len(vis_eval)), 6), "n": len(vis_eval), "note": "the oracle; this family measures fidelity"},
            "copy_input_string_as_ast": {"exact": 0.0, "note": "a string is not an AST"},
            "eval_ast_size_distribution": dict(sorted(collections.Counter(ev[v["record_id"]]["ast_size"] for v in vis_eval).items()))}


# ---------------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(HERE / "data" / "q3_v0_3"))
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    compile_expression, compiler_pin = _load_compiler()
    pool_path, pool_pin = _find_pool()
    contract = json.loads((HERE / "OPERATION_CONTRACTS.json").read_text(encoding="utf-8"))

    R, statsR = build_family_R(random.Random(args.seed + 1), compile_expression, pool_path)
    G, statsG = build_family_G(random.Random(args.seed + 4), compile_expression)
    A, statsA = build_family_A(random.Random(args.seed + 2))
    C, statsC = build_family_C(random.Random(args.seed + 3))

    files, counts, packets = {}, {}, {f: {} for f in FAMILIES}
    plan = (("R", R, lambda rows, s, seed: emit_R(rows, s, seed, "R")), ("G", G, lambda rows, s, seed: emit_R(rows, s, seed, "G")),
            ("A", A, emit_A), ("C", C, emit_C))
    for fam, rows_by_split, emit in plan:
        for split in SPLITS:
            vis, seal = emit(rows_by_split[split], split, args.seed)
            packets[fam][split] = (vis, seal)
            for kind, rows in (("visible", vis), ("sealed", seal)):
                path = out / ("%s_%s_%s.jsonl" % (kind, fam, split))
                body = ("\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n").encode("utf-8")
                path.write_bytes(body)
                files[path.name] = {"records": len(rows), "sha256": _sha_bytes(body)}
            counts["%s_%s" % (fam, split)] = len(vis)

    baselines = {"schema": "helm-cas-expression-lab.q3-baselines/0.3", "scored_on": {"A": ["dev", "eval"], "C": "eval", "R": "eval", "G": "eval"},
                 "A": {split: baselines_A(*packets["A"]["train"], *packets["A"][split]) for split in ("dev", "eval")},
                 "C": baselines_C(*packets["C"]["eval"]),
                 "R": baselines_reconstruction(compile_expression, *packets["R"]["eval"]),
                 "G": baselines_reconstruction(compile_expression, *packets["G"]["eval"])}
    with open(out / "baselines.json", "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(baselines, indent=1, sort_keys=True))

    manifest = {
        "schema": SCHEMA, "seed": args.seed, "built": "2026-09-21", "generator": pathlib.Path(__file__).name, "supersedes": "data/q3_v0_2 (kept on disk: the reviewed artifact, bound to contract e97b8aa6..., with no operator-^0 rows in dev); v0.2 superseded data/q3_v0_1 (kept; found leaking)",
        "contract_binding": "operation_contracts_digest MUST equal contract_digest in OPERATION_CONTRACTS.json; a test and the exporter refuse anything else",
        "operation_contracts_digest": contract["contract_digest"], "compiler": compiler_pin, "sdg_pool": pool_pin,
        "sdg_usage": "expression strings only; SDG prompt/response text is never read (the label sits inside it)",
        "sizes_are_ceilings": SIZES, "counts": counts, "files": files, "stats": {"R": statsR, "G": statsG, "A": statsA, "C": statsC},
        "family_labels": {
            "R": "FIDELITY. Expression -> canonical AST for SDG expressions. Ceiling = the compiler (measured). The SDG pool is structurally narrow; strict-shape holdout therefore yields a SMALL eval and dev, reported in stats. Reviewer measurement on v0.1: one regular expression reproduced 204/256 eval targets; 52/256 needed a grammar.",
            "G": "STRUCTURAL GENERALISATION. Grammar-generated nested binary trees, compiled, held out by whole strict TOPOLOGY and by depth (eval prefers depth >= 4). This is the structural test R cannot be.",
            "A": "CONFORMANCE AND TRANSFER, NOT DISCOVERY. The answer depends only on four field equalities (op==0, same_domain, target_noetic==op, source==target). A three-line hand rule (R3) and a 4-feature lookup filled from train (R7) are registered; a learned module is measured on fidelity to them and on transfer to unseen cells, and MUST report the order-flip and swapped-twin metrics, accuracy BY CASE FAMILY (^0 same-domain, ^0 cross-domain, non-identity same-domain, non-identity cross-domain, refusal) and refusal accuracy on unseen refusal classes. Because the lookup R7 already scores 1.0, this family can only show that a model MATCHES THE CODE; it can never show learning beyond lookup. The targets are the engine code's rules (owner decision OD-6), not the book's. Accuracy alone is not a claim.",
            "C": "CONFORMANCE-ONLY. The modular-sum rule scores 1.0 by construction.",
        },
        "visibility": {
            "R": {"mode": "reconstruction", "visible": ["record_id", "family", "mode", "observation"], "withheld": ["target_canonical_ast", "target_ast", "ast_size", "shape_key", "depth", "validity", "oracle"]},
            "G": {"mode": "reconstruction", "visible": ["record_id", "family", "mode", "observation"], "withheld": ["target_canonical_ast", "target_ast", "ast_size", "shape_key", "depth", "validity", "oracle"]},
            "A": {"mode": "neural_operation_execution", "visible": ["record_id", "family", "mode", "operation_id", "observation"], "withheld": ["outcome", "target", "cell", "order_flip", "case_family", "swapped_target", "refusal_kind", "oracle", "trace"]},
            "C": {"mode": "neural_operation_execution", "visible": ["record_id", "family", "mode", "operation_id", "observation"], "withheld": ["outcome", "target", "depth", "oracle", "trace"]},
            "teacher_forcing_note": "a target may be used to compute training LOSS; it is never a model INPUT at evaluated prediction; teacher-forced passes are not free-running reconstruction and are reported apart",
        },
        "split_policy": {"R": "whole STRICT shapes (every scalar leaf abstracted); eval then dev take the rarest first", "G": "whole strict topologies; eval takes depth>=4 topologies first, then rarest; dev the rarest of the rest",
                         "A": "whole (operator, source_domain, target_domain) cells: 24 eval, 16 dev, 120 train; each of eval and dev is guaranteed one cell of every case family; eval/dev valid rows are 50% order-flip, and the other half is stratified across the case families with ^0 diagonal positives guaranteed; refusals drawn from split-disjoint value pools and type classes",
                         "C": "one seen-set across all splits, train first; depths train 1-3, dev 2-3, eval 4-6"},
        "exposure_report": {
            "R": "strict shapes: none shared across splits by construction (asserted). Atomic literals, names and coefficients recur across splits -- disclosed. Eval and dev are small because the SDG pool has few strict shapes; see stats.R.",
            "G": "strict topologies: none shared across splits by construction (asserted); all leaf literals recur -- disclosed; eval depths >= 4 are longer than anything in train.",
            "A": "the rule's four features are all richly present in train; holding out cells holds out COMBINATIONS, not rule components; R7 (a 4-feature lookup from train) reaches its registered score on unseen cells with no hand truth table. Refusal observations are asserted disjoint across splits, and eval refusal TYPE CLASSES (float-equal-to-int, string) are unseen in train -- disclosed.",
            "C": "measured: dev/eval strings verbatim in train = stats.C.verbatim_in_train (must be 0); dev/eval chains that contain a verbatim train chain as a sub-expression = stats.C.contain_a_verbatim_train_chain_as_subexpression -- disclosed, expected high, because every long chain extends a short one. The digit-multiset check used in v0.1 was vacuous and is gone.",
        },
        "record_id_policy": "sha256 of the raw UTF-8 string '<seed>:<family>:<split>:<index>', first 24 hex. Position only.",
        "seal_policy": "a file boundary against a LEARNER, not a secret: the sealed side regenerates from this public code and seed (shown by the v0.1 reviewers).",
        "review_of_v0_1": "three independent attackers, 2026-09-21: leak (refusals recycled), baseline (hand rule 1.0, lookup 1.0, order-flip rows 11.7%), split (R shape was a fingerprint; C dev not deduplicated). All three succeeded; v0.2 answers each by name in the module docstring.",
    }
    with open(out / "manifest.json", "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=1, sort_keys=True))

    print("Q3 v0.3 written to %s" % out)
    print("  counts:", counts)
    print("  R: %d valid SDG expressions, %d strict shapes; per split %s; root mix eval %s" % (statsR["valid_unique"], statsR["strict_shape_groups"], statsR["strict_shapes_per_split"], statsR["root_node_mix"]["eval"]))
    print("  G: %d generated valid, rejected %s; strict shapes %d; per split %s; depths %s" % (statsG["generated_valid"], statsG["rejected_by_compiler"], statsG["strict_shape_groups"], statsG["strict_shapes_per_split"], statsG["depths_per_split"]))
    print("  A: order-flip valid rows %s of valid %s; refusals %s; refusal observations shared across splits: %d" % (statsA["order_flip_valid_rows"], statsA["valid_rows"], statsA["refusal_rows"], statsA["refusal_observations_shared_across_splits"]))
    print("  C: verbatim in train %s; contain a train sub-chain %s" % (statsC["verbatim_in_train"], statsC["contain_a_verbatim_train_chain_as_subexpression"]))
    print("  A rows by case family: %s ; ^0 diagonal positives %s ; admissible rows %s" % (statsA["valid_rows_by_case_family"], statsA["op0_diagonal_positive_rows"], statsA["admissible_rows"]))
    print("  baselines on A eval (exact | order-flip exact | swapped-twin exact):")
    for name, row in baselines["A"]["eval"].items():
        print("    %-70s %s | %s | %s" % (name[:70], row["exact"], row["order_flip_exact"], row["swapped_twin_exact"]))
    print("  R compiler %s; G compiler %s; C modular_sum %s" % (baselines["R"]["compiler_reference (measured, not typed)"]["exact"], baselines["G"]["compiler_reference (measured, not typed)"]["exact"], baselines["C"]["modular_sum_ignoring_grouping"]["exact"]))
    print("Q3_BUILD_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
