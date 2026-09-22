"""Q3 v0.7 -- behaviour-paired records with SEALED targets, STRICT structure splits, and baselines that include the attacks.

v0.7 follows final review of identifier boundaries and fully-labelled repeated nesting words.
  The intermediate v0.6 build and its exact compiler snapshot remain preserved.

v0.6 preserves v0.4/v0.5 and binds a fresh build to the recovered and corrected compiler.
  The source, offline directory and ZIP now carry identical compiler bytes. Mechanical
  register-identity, warning, diagnostic and short-pattern fixes do not select book readings.

v0.5 (2026-09-21) is v0.4 rebuilt on the CHANGED compiler text (LF sha256 5c732d95f5862e5e...; v0.4 was bound to 8169188ad73df8fc...).
  The compiler gained the book's meaning for the Nesting Operator (an additive `nesting` block) and eight defect fixes; the
  R and G targets are parse trees, which the change does not touch (checked: every v0.4 observation gives the same tree under
  both texts), but the manifest binds the data to one compiler text, so a new version is the honest form. Nothing else changed.
  The pool is now found by walking up from the worktree (the scaffold being checked out here no longer hides the pool).

v0.4 (2026-09-21) answers the three-attacker review of v0.3, which broke two claims and found the rest sound:
  G   'eval depths are longer than anything in train' was FALSE: train held 485 rows at eval's depths, and 170 of 256 eval
      trees had a bare tree shape already in train -- only a per-leaf suffix pattern was held out (the v0.1 'fingerprint'
      defect again). -> G is now split by BARE TREE SHAPE and by DEPTH: train is depths 1-3, dev is depth-3 trees whose bare
      shape is held out whole, eval is depths 4-5. The builder asserts that no bare shape is shared and that eval is deeper
      than every train row.
  A   'all four rule features are richly present in train' was FALSE for the ^0 diagonal: 4 positive rows in 2,048, and a
      sweep of 120 seeds gave as few as 0. -> every ^0-diagonal row of the train cells is included (a floor of 16 is
      asserted), and the builder now ASSERTS the dev/eval sizes and the exact 50% order-flip share instead of hoping.
      Refusals are drawn by QUOTA per kind (8 per kind in dev and eval) so 'unseen refusal class' accuracy has an n.
      New registered baselines: the train case-family prior, and a learner-side refusal rule that uses NO oracle.
      The manifest now says in plain words that dev and eval are deliberately REBALANCED and gives the admissible rate by
      case family per split, and how many swapped twins of eval rows sit in train.
  ^   R and G targets are the compiler's AST with ONE documented, invertible spelling change: the compiler writes a Noetic
      as 'CO-k'; the lab target writes '^k' (owner ruling OD-2). `to_lab_spelling` / `to_compiler_spelling` are tested.


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
SCHEMA = "helm-cas-expression-lab.q3-behaviour-records/0.7"
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
    # This version generates historical Q3 v0.7. New language extensions must
    # not replace its target oracle or cause an in-place dataset repin.
    from historical_compiler import load_historical_compiler, source_receipt
    return load_historical_compiler().compile_expression, source_receipt()


def _find_pool():
    for root in [REPO, MAIN_CHECKOUT, *REPO.parents]:
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


def tree_shape(ast):
    """The BARE shape of a nested binary expression: 'L' for anything that is not a binary node, else ['B', left, right]."""
    if isinstance(ast, dict) and isinstance(ast.get("left"), dict) and isinstance(ast.get("right"), dict):
        return ["B", tree_shape(ast["left"]), tree_shape(ast["right"])]
    return "L"


def tree_depth(shape):
    return 0 if shape == "L" else 1 + max(tree_depth(shape[1]), tree_depth(shape[2]))


def to_lab_spelling(ast):
    """The compiler spells a Noetic 'CO-k'. The lab target spells it '^k' (owner ruling OD-2). Nothing else changes."""
    if isinstance(ast, dict):
        return {k: to_lab_spelling(v) for k, v in ast.items()}
    if isinstance(ast, list):
        return [to_lab_spelling(v) for v in ast]
    if isinstance(ast, str) and len(ast) == 4 and ast.startswith("CO-") and ast[3].isdigit():
        return "^" + ast[3]
    return ast


def to_compiler_spelling(ast):
    if isinstance(ast, dict):
        return {k: to_compiler_spelling(v) for k, v in ast.items()}
    if isinstance(ast, list):
        return [to_compiler_spelling(v) for v in ast]
    if isinstance(ast, str) and len(ast) == 2 and ast[0] == "^" and ast[1].isdigit():
        return "CO-" + ast[1]
    return ast


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
        lab = to_lab_spelling(row["ast"])
        assert to_compiler_spelling(lab) == row["ast"], "the spelling map must be invertible"
        sealed.append({"record_id": rid, "family": family, "target_canonical_ast": canonical(lab), "target_ast": lab,
                       "ast_size": _ast_size(row["ast"]), "shape_key": row["shape_key"], "depth": row.get("depth"),
                       "tree_shape_key": row.get("tree_shape_key"),
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
    # v0.4: split by BARE tree shape and by DEPTH. train = depths 1-3; dev = depth-3 trees whose bare shape is held out WHOLE;
    # eval = depths 4-5 (deeper than every train row, so every eval shape is new by construction -- asserted below).
    for row in candidates:
        shape = tree_shape(row["ast"])
        row["tree_shape_key"], row["shape_key"] = _sha_json(shape)[:16], _sha_json(strict_shape(row["ast"]))[:16]
        assert tree_depth(shape) == row["depth"], "the generator's depth must be the tree's depth"
    depth3 = collections.defaultdict(list)
    for row in candidates:
        if row["depth"] == 3:
            depth3[row["tree_shape_key"]].append(row)
    shape_order = sorted(depth3)
    rng.shuffle(shape_order)
    dev_shapes, dev_rows = set(), 0
    for key in shape_order:                                   # whole shapes go to dev until it is full
        if dev_rows >= SIZES["dev"]:
            break
        dev_shapes.add(key)
        dev_rows += len(depth3[key])
    out = {s: [] for s in SPLITS}
    for row in candidates:
        if row["depth"] >= 4:
            out["eval"].append(row)
        elif row["tree_shape_key"] in dev_shapes:
            out["dev"].append(row)
        else:
            out["train"].append(row)
    for s in SPLITS:
        rng.shuffle(out[s])
    half = SIZES["eval"] // 2                               # eval: depth 4 and depth 5 in equal parts
    out["eval"] = [r for r in out["eval"] if r["depth"] == 4][:half] + [r for r in out["eval"] if r["depth"] == 5][:SIZES["eval"] - half]
    rng.shuffle(out["eval"])
    for s in ("train", "dev"):
        out[s] = out[s][:SIZES[s]]
    shapes = {s: {r["tree_shape_key"] for r in out[s]} for s in SPLITS}
    if shapes["train"] & shapes["dev"] or shapes["train"] & shapes["eval"] or shapes["dev"] & shapes["eval"]:
        raise SystemExit("Q3_REFUSED:G_TREE_SHAPE_SHARED_ACROSS_SPLITS")
    if not min(r["depth"] for r in out["eval"]) > max(r["depth"] for r in out["train"]):
        raise SystemExit("Q3_REFUSED:G_EVAL_NOT_DEEPER_THAN_TRAIN")
    groups = {r["shape_key"] for r in candidates}
    stats = {"generated_valid": len(candidates), "rejected_by_compiler": dict(rejected), "strict_shape_groups": len(groups),
             "strict_shapes_per_split": {s: len({r["shape_key"] for r in out[s]}) for s in SPLITS},
             "bare_tree_shapes_per_split": {s: len(shapes[s]) for s in SPLITS}, "bare_tree_shapes_shared_across_splits": 0,
             "bare_tree_shapes_of_depth_3_in_pool": len(depth3), "bare_tree_shapes_held_out_for_dev": len(dev_shapes),
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


def _refusal_case(rng, split, kind=None):
    pool, base = REFUSAL_POOLS[split], {"operator": rng.randrange(10), "source": [rng.choice(ref.DOMAINS), rng.randrange(10)],
                                       "target": [rng.choice(ref.DOMAINS), rng.randrange(10)]}
    kind = kind or rng.choice(("bad_operator", "bad_domain", "bad_noetic") + pool["types"])
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
            # v0.4: ^0 is admissible ONLY on the diagonal. Every such row of the train cells is included, so the rule can be learned.
            diagonal = [r for r in rows if r["case_family"] == "op0_same_domain" and r["source"] == r["target"]]
            if len(diagonal) < 16:
                raise SystemExit("Q3_REFUSED:A_TRAIN_HAS_TOO_FEW_OP0_DIAGONAL_POSITIVES:%d" % len(diagonal))
            out[s] = diagonal + [r for r in rows if r not in diagonal][:SIZES[s] - len(diagonal)]
            rng.shuffle(out[s])
        else:                                   # finding A2: at least half of valid rows are order-flip rows
            half = SIZES[s] // 2
            flat, chosen = pools[s]["flat"], []
            diagonal = [r for r in flat if r["case_family"] == "op0_same_domain" and r["source"] == r["target"]]
            chosen += diagonal[:6]                       # ^0 is admissible ONLY on the diagonal: guarantee some positives
            for fam in ("op0_same_domain", "op0_cross_domain", "nonidentity_same_domain"):
                chosen += [r for r in flat if r["case_family"] == fam and r not in chosen][:16]
            chosen += [r for r in flat if r not in chosen][:SIZES[s] - half - len(chosen)]
            out[s] = pools[s]["flip"][:half] + chosen
            if len(pools[s]["flip"][:half]) != half or len(out[s]) != SIZES[s]:
                raise SystemExit("Q3_REFUSED:A_%s_SIZE_OR_FLIP_SHARE_NOT_MET:%d flip, %d rows" % (s.upper(), len(pools[s]["flip"][:half]), len(out[s])))
            rng.shuffle(out[s])
    refusal_strings = {}
    for s in SPLITS:
        kinds = ("bad_operator", "bad_domain", "bad_noetic") + REFUSAL_POOLS[s]["types"]
        per_kind = 25 if s == "train" else 8                 # v0.4: a QUOTA per kind, so every refusal class has an n
        plan = [k for k in kinds for _ in range(per_kind)]
        n_bad, made, seen = len(plan), 0, set()
        while made < n_bad:
            obs, kind = _refusal_case(rng, s, plan[made])
            key = json.dumps(obs, sort_keys=True)
            if key in seen or not _refuses(obs):
                continue
            seen.add(key)
            out[s].insert(rng.randrange(len(out[s]) + 1), {**obs, "refusal_kind": kind})
            made += 1
        refusal_strings[s] = seen
    train_index = collections.defaultdict(list)
    for r in out["train"]:
        if "order_flip" in r:
            train_index[(r["operator"], tuple(r["source"]), tuple(r["target"]))].append(r)
    stats = {"cells": len(cells), "cells_held_eval": 24, "cells_held_dev": 16,
             "held_cells_eval": sorted("%d:%s>%s" % c for c in held["eval"]), "held_cells_dev": sorted("%d:%s>%s" % c for c in held["dev"]),
             "order_flip_valid_rows": {s: sum(1 for r in out[s] if r.get("order_flip")) for s in SPLITS},
             "valid_rows": {s: sum(1 for r in out[s] if "order_flip" in r) for s in SPLITS},
             "refusal_rows": {s: sum(1 for r in out[s] if "refusal_kind" in r) for s in SPLITS},
             "valid_rows_by_case_family": {s: {f: sum(1 for r in out[s] if r.get("case_family") == f) for f in CASE_FAMILIES} for s in SPLITS},
             "op0_diagonal_positive_rows": {s: sum(1 for r in out[s] if r.get("case_family") == "op0_same_domain" and r["source"] == r["target"]) for s in SPLITS},
             "admissible_rows": {s: sum(1 for r in out[s] if "order_flip" in r and ref.is_admissible(r["operator"], tuple(r["source"]), tuple(r["target"]))) for s in SPLITS},
             "admissible_rate_by_case_family": {s: {f: round(sum(1 for r in out[s] if r.get("case_family") == f and ref.is_admissible(r["operator"], tuple(r["source"]), tuple(r["target"])))
                                                          / max(1, sum(1 for r in out[s] if r.get("case_family") == f)), 6) for f in CASE_FAMILIES} for s in SPLITS},
             "refusal_rows_by_kind": {s: dict(sorted(collections.Counter(r["refusal_kind"] for r in out[s] if "refusal_kind" in r).items())) for s in SPLITS},
             "swapped_twin_of_a_heldout_row_is_a_train_row": {s: sum(1 for r in out[s] if "order_flip" in r and any(
                 t["operator"] == r["operator"] and t["source"] == r["target"] and t["target"] == r["source"] for t in train_index.get((r["operator"], tuple(r["target"]), tuple(r["source"])), []))) for s in ("dev", "eval")},
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
    family_prior = collections.defaultdict(collections.Counter)      # what a learner knows from train: the usual answer per case family
    for o, t in train_valid:
        family_prior[case_family(o["operator"], o["source"], o["target"])][t] += 1
    prior = {f: c.most_common(1)[0][0] for f, c in family_prior.items()}
    vocabulary = {"operator": set(), "domain": set(), "noetic": set()}   # every token seen in a VALID train row; no oracle involved
    for o, _ in train_valid:
        vocabulary["operator"].add(repr(o["operator"]))
        for end in ("source", "target"):
            vocabulary["domain"].add(repr(o[end][0]))
            vocabulary["noetic"].add(repr(o[end][1]))

    def learner_side_refuse(o):
        """Refuse when the key set is wrong or any field token never appeared in a valid train row. repr() keeps 2, 2.0, True and '2' apart."""
        try:
            if set(o) != {"operator", "source", "target"} or repr(o["operator"]) not in vocabulary["operator"]:
                return True
            return any(len(o[end]) != 2 or repr(o[end][0]) not in vocabulary["domain"] or repr(o[end][1]) not in vocabulary["noetic"] for end in ("source", "target"))
        except Exception:
            return True

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
        "train_case_family_prior (the usual train answer for this kind of question) + range-check refusal": lambda o: REFUSE if not _valid_fields(o) else prior[case_family(o["operator"], o["source"], o["target"])],
        "R7 lookup + LEARNER-SIDE refusal (train vocabulary only, NO oracle)": lambda o: REFUSE if learner_side_refuse(o) else lookup.get(feats(o), majority),
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
    hit = sum(1 for v in vis_eval if canonical(to_lab_spelling(compile_expression(v["observation"]).to_dict()["ast"])) == ev[v["record_id"]]["target_canonical_ast"])
    return {"compiler_reference (measured, not typed)": {"exact": round(hit / max(1, len(vis_eval)), 6), "n": len(vis_eval), "note": "the oracle; this family measures fidelity"},
            "copy_input_string_as_ast": {"exact": 0.0, "note": "a string is not an AST"},
            "eval_ast_size_distribution": dict(sorted(collections.Counter(ev[v["record_id"]]["ast_size"] for v in vis_eval).items()))}


# ---------------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(HERE / "data" / "q3_v0_7"))
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    out = pathlib.Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit("Q3_REFUSED:OUTPUT_NOT_EMPTY:use a fresh data version directory")
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

    baselines = {"schema": "helm-cas-expression-lab.q3-baselines/0.5", "scored_on": {"A": ["dev", "eval"], "C": "eval", "R": "eval", "G": "eval"},
                 "A": {split: baselines_A(*packets["A"]["train"], *packets["A"][split]) for split in ("dev", "eval")},
                 "C": baselines_C(*packets["C"]["eval"]),
                 "R": baselines_reconstruction(compile_expression, *packets["R"]["eval"]),
                 "G": baselines_reconstruction(compile_expression, *packets["G"]["eval"])}
    baselines_body = json.dumps(baselines, indent=1, sort_keys=True).encode("utf-8")
    (out / "baselines.json").write_bytes(baselines_body)
    files["baselines.json"] = {"records": None, "sha256": _sha_bytes(baselines_body)}      # v0.4: the baselines are hashed too

    manifest = {
        "schema": SCHEMA, "seed": args.seed, "built": "2026-09-21", "generator": pathlib.Path(__file__).name, "supersedes": "data/q3_v0_4 (kept on disk, unchanged: bound to compiler text 8169188ad73df8fc..., which was replaced on 2026-09-21 by 5c732d95f5862e5e... -- book meaning for the Nesting Operator, eight defect fixes; R and G targets are parse trees and are unchanged); v0.4 superseded v0.3 (kept on disk: attacked on 2026-09-21 -- G's 'deeper than train' claim and A's 'richly present' claim were false); v0.3 superseded v0.2 (bound to a contract HEAD no longer holds); v0.2 superseded v0.1 (found leaking)",
        "rebalancing_note": "Family A's dev and eval are DELIBERATELY rebalanced (half order-flip rows, stratified case families). Their answer rates differ from train BY CONSTRUCTION -- see stats.A.admissible_rate_by_case_family. A model's calibration on eval is therefore not comparable with its calibration on train, and a gap between train and eval accuracy is partly this sampling decision.",
        "target_spelling": "R and G targets are the compiler's AST with one documented, invertible change: the compiler writes a Noetic as 'CO-k', the lab target writes '^k' (owner ruling OD-2). q3_behaviour_records.to_compiler_spelling restores the compiler's form exactly.",
        "contract_binding": "operation_contracts_digest MUST equal contract_digest in OPERATION_CONTRACTS.json; a test and the exporter refuse anything else",
        "operation_contracts_digest": contract["contract_digest"], "compiler": compiler_pin, "sdg_pool": pool_pin,
        "sdg_usage": "expression strings only; SDG prompt/response text is never read (the label sits inside it)",
        "sizes_are_ceilings": SIZES, "counts": counts, "files": files, "stats": {"R": statsR, "G": statsG, "A": statsA, "C": statsC},
        "family_labels": {
            "R": "FIDELITY. Expression -> canonical AST for SDG expressions. Ceiling = the compiler (measured). The SDG pool is structurally narrow; strict-shape holdout therefore yields a SMALL eval and dev, reported in stats. Reviewer measurement on v0.1: one regular expression reproduced 204/256 eval targets; 52/256 needed a grammar.",
            "G": "STRUCTURAL GENERALISATION. Grammar-generated nested binary trees, compiled. Split by BARE tree shape and by depth: train is depths 1-3; dev is depth-3 trees whose bare shape is held out whole (new shape, same depth); eval is depths 4-5 (deeper than every train row, so every eval shape is new). Both facts are asserted by the builder and re-checked by the loader.",
            "A": "CONFORMANCE AND TRANSFER, NOT DISCOVERY. The answer depends only on four field equalities (op==0, same_domain, target_noetic==op, source==target). A three-line hand rule (R3) and a 4-feature lookup filled from train (R7) are registered; a learned module is measured on fidelity to them and on transfer to unseen cells, and MUST report the order-flip and swapped-twin metrics, accuracy BY CASE FAMILY (^0 same-domain, ^0 cross-domain, non-identity same-domain, non-identity cross-domain, refusal) and refusal accuracy on unseen refusal classes. Because the lookup R7 already scores 1.0, this family can only show that a model MATCHES THE CODE; it can never show learning beyond lookup. The targets are the engine code's rules (owner decision OD-6), not the book's. Accuracy alone is not a claim.",
            "C": "CONFORMANCE-ONLY. The modular-sum rule scores 1.0 by construction.",
        },
        "visibility": {
            "R": {"mode": "reconstruction", "visible": ["record_id", "family", "mode", "observation"], "withheld": ["target_canonical_ast", "target_ast", "ast_size", "shape_key", "tree_shape_key", "depth", "validity", "oracle"]},
            "G": {"mode": "reconstruction", "visible": ["record_id", "family", "mode", "observation"], "withheld": ["target_canonical_ast", "target_ast", "ast_size", "shape_key", "tree_shape_key", "depth", "validity", "oracle"]},
            "A": {"mode": "neural_operation_execution", "visible": ["record_id", "family", "mode", "operation_id", "observation"], "withheld": ["outcome", "target", "cell", "order_flip", "case_family", "swapped_target", "refusal_kind", "oracle", "trace"]},
            "C": {"mode": "neural_operation_execution", "visible": ["record_id", "family", "mode", "operation_id", "observation"], "withheld": ["outcome", "target", "depth", "oracle", "trace"]},
            "teacher_forcing_note": "a target may be used to compute training LOSS; it is never a model INPUT at evaluated prediction; teacher-forced passes are not free-running reconstruction and are reported apart",
        },
        "split_policy": {"R": "whole STRICT shapes (every scalar leaf abstracted); eval then dev take the rarest first", "G": "train = depths 1-3; dev = whole bare tree shapes of depth 3, held out; eval = depths 4 and 5 in equal parts; no bare shape shared (asserted)",
                         "A": "whole (operator, source_domain, target_domain) cells: 24 eval, 16 dev, 120 train; each of eval and dev is guaranteed one cell of every case family; eval/dev valid rows are 50% order-flip, and the other half is stratified across the case families with ^0 diagonal positives guaranteed; refusals drawn from split-disjoint value pools and type classes",
                         "C": "one seen-set across all splits, train first; depths train 1-3, dev 2-3, eval 4-6"},
        "exposure_report": {
            "R": "strict shapes: none shared across splits by construction (asserted). Atomic literals, names and coefficients recur across splits -- disclosed. Eval and dev are small because the SDG pool has few strict shapes; see stats.R.",
            "G": "bare tree shapes: none shared across splits (asserted by the builder, re-checked by the loader); every eval row is deeper than every train row (asserted); leaf literals and the +/x operators recur across splits -- disclosed.",
            "A": "the rule's four features are present in train in the measured amounts in stats.A (the rarest, ^0-diagonal positives, has a floor of 16 -- every such row of the train cells); holding out cells holds out COMBINATIONS, not rule components; some swapped twins of held-out rows ARE train rows (stats.A.swapped_twin_of_a_heldout_row_is_a_train_row), so the swapped-twin score is partly in-distribution; R7 (a 4-feature lookup from train) reaches its registered score on unseen cells with no hand truth table. Refusal observations are asserted disjoint across splits, and eval refusal TYPE CLASSES (float-equal-to-int, string) are unseen in train -- disclosed.",
            "C": "measured: dev/eval strings verbatim in train = stats.C.verbatim_in_train (must be 0); dev/eval chains that contain a verbatim train chain as a sub-expression = stats.C.contain_a_verbatim_train_chain_as_subexpression -- disclosed, expected high, because every long chain extends a short one. The digit-multiset check used in v0.1 was vacuous and is gone.",
        },
        "record_id_policy": "sha256 of the raw UTF-8 string '<seed>:<family>:<split>:<index>', first 24 hex. Position only.",
        "seal_policy": "a file boundary against a LEARNER, not a secret: the sealed side regenerates from this public code and seed (shown by the v0.1 reviewers).",
        "review_of_v0_1": "three independent attackers, 2026-09-21: leak (refusals recycled), baseline (hand rule 1.0, lookup 1.0, order-flip rows 11.7%), split (R shape was a fingerprint; C dev not deduplicated). All three succeeded; v0.2 answers each by name in the module docstring.",
    }
    with open(out / "manifest.json", "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=1, sort_keys=True))

    print("Q3 v0.7 written to %s" % out)
    print("  counts:", counts)
    print("  R: %d valid SDG expressions, %d strict shapes; per split %s; root mix eval %s" % (statsR["valid_unique"], statsR["strict_shape_groups"], statsR["strict_shapes_per_split"], statsR["root_node_mix"]["eval"]))
    print("  G: %d generated valid, rejected %s; bare tree shapes per split %s (shared: 0, asserted); depths %s" % (statsG["generated_valid"], statsG["rejected_by_compiler"], statsG["bare_tree_shapes_per_split"], statsG["depths_per_split"]))
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
