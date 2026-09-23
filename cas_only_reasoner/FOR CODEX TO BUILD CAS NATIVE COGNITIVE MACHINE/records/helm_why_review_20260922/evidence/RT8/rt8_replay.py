"""RT8: scripted-gold replay of the Q4 grammar mask + token codec over every visible G train/dev row.

Pure Python. No torch. Read-only on the repository. Visible files only (via q3_load.load_visible).
Run with:  PYTHONDONTWRITEBYTECODE=1 C:/Python314/python.exe -B rt8_replay.py
"""
import ast as pyast
import collections
import hashlib
import importlib.abc
import json
import pathlib
import sys

# ---------------------------------------------------------------------------------------------
# 0. Torch blocker FIRST, before any lab import.
# ---------------------------------------------------------------------------------------------
BLOCKED = ("torch", "numpy")
blocked_attempts = []


class _Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0]
        if root in BLOCKED:
            blocked_attempts.append(fullname)
            raise ImportError("NOT_RUN_TORCH_DEPENDENCY: import of %s refused by RT8 blocker" % fullname)
        return None


sys.meta_path.insert(0, _Blocker())
assert not any(m.split(".")[0] in BLOCKED for m in sys.modules), "torch/numpy already loaded before start"

ROOT = pathlib.Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
LAB = ROOT / "research/helm_cas_expression_lab"
DATA = LAB / "data/q3_v0_7"
REC = ROOT / "records/q4_authorized_20260922"
R5 = pathlib.Path("C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/helm_review/R5")

out = {}


def say(*parts):
    print(*parts, flush=True)


# ---------------------------------------------------------------------------------------------
# 1. Static import scan of every module this script will import (closure over lab-local modules).
# ---------------------------------------------------------------------------------------------
def scan_file(path):
    tree = pyast.parse(path.read_text(encoding="utf-8"), str(path))
    top, inner = [], []

    def walk(node, in_func):
        for child in pyast.iter_child_nodes(node):
            if isinstance(child, (pyast.Import, pyast.ImportFrom)):
                if isinstance(child, pyast.Import):
                    names = [a.name for a in child.names]
                else:
                    names = [child.module or ""]
                (inner if in_func else top).extend((n, child.lineno) for n in names)
            walk(child, in_func or isinstance(child, (pyast.FunctionDef, pyast.AsyncFunctionDef, pyast.Lambda)))
    walk(tree, False)
    return top, inner


def local_file(name):
    for base in (LAB, R5):
        p = base / (name.split(".")[0] + ".py")
        if p.exists():
            return p
    return None


start = [LAB / "learner_q4_decoder.py", LAB / "learner_q4_representation.py", LAB / "q3_load.py", R5 / "common.py"]
seen, queue, scan = set(), list(start), {}
while queue:
    p = queue.pop(0)
    if p in seen:
        continue
    seen.add(p)
    top, inner = scan_file(p)
    scan[str(p.name) if p.parent == LAB else "R5/" + p.name] = {"import_time": top, "inside_functions": inner}
    for n, _ in top:                       # follow only what executes at import time
        lp = local_file(n)
        if lp and lp not in seen:
            queue.append(lp)
torch_at_import = sorted({(f, n, ln) for f, d in scan.items() for n, ln in d["import_time"] if n.split(".")[0] == "torch"})
torch_in_funcs = sorted({(f, n, ln) for f, d in scan.items() for n, ln in d["inside_functions"] if n.split(".")[0] == "torch"})
say("=== 1. STATIC IMPORT SCAN (closure over lab-local modules executed at import time) ===")
for f, d in scan.items():
    say("  %s" % f)
    say("     import-time: %s" % sorted({n for n, _ in d["import_time"]}))
    say("     inside functions: %s" % sorted({"%s@%d" % (n, ln) for n, ln in d["inside_functions"]}))
say("  torch imported at import time anywhere in closure: %s" % (torch_at_import or "NONE"))
say("  torch imported inside a function anywhere in closure: %s" % (torch_in_funcs or "NONE"))
if torch_at_import:
    say("OUTCOME: NOT_RUN_TORCH_DEPENDENCY")
    sys.exit(2)

# ---------------------------------------------------------------------------------------------
# 2. Imports (blocker active).
# ---------------------------------------------------------------------------------------------
sys.path.insert(0, str(LAB))
import learner_q4_decoder as dec            # noqa: E402
import learner_q4_representation as rep     # noqa: E402
import q3_load                              # noqa: E402
sys.path.insert(0, str(R5))
import common as r5                         # noqa: E402

TOKENS, TOKEN_IDS = dec.TOKENS, dec.TOKEN_IDS


def lf_sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# ---------------------------------------------------------------------------------------------
# 3. Token table / index space checks.
# ---------------------------------------------------------------------------------------------
say("\n=== 3. TOKEN TABLE ===")
say("  len(TOKENS) = %d ; distinct = %d ; BOS_ID = %d" % (len(TOKENS), len(set(TOKENS)), dec.BOS_ID))
say("  TOKENS order: %s" % list(enumerate(TOKENS)))
say("  TOKEN_IDS is inverse of TOKENS: %s" % all(TOKENS[i] == n and TOKEN_IDS[n] == i for i, n in enumerate(TOKENS)))
field_union = set().union(*dec._FIELDS.values()) | {"EOS", "STATE", "BINARY"}
say("  _FIELDS union + {EOS,STATE,BINARY} == set(TOKENS): %s ; fields pairwise disjoint: %s" % (
    field_union == set(TOKENS), sum(len(v) for v in dec._FIELDS.values()) + 3 == len(field_union)))
pins = json.loads((REC / "run_001/plan.json").read_text(encoding="utf-8"))["source_pins"]
say("  runtime source pins (run_001/plan.json) vs current LF-normalised sha256:")
pin_match = {}
for name in ("learner_q4_decoder.py", "learner_q4_representation.py", "q3_load.py", "reference_ops.py",
             "learner_q4_neural.py", "q4_smoke_job.py", "q3_behaviour_records.py"):
    cur = lf_sha(LAB / name)
    pin_match[name] = cur == pins.get(name)
    say("    %-32s pinned %s current %s match=%s" % (name, pins.get(name, "-")[:16], cur[:16], pin_match[name]))
res_json = json.loads((REC / "run_001/result.json").read_text(encoding="utf-8"))
P = res_json["learned_parameter_count"]
W = 64
fixed = 257 * W + 2 * (3 * W * W * 2 + 3 * W * 2)            # input embedding + 2 GRUs (weight_ih, weight_hh, 2 biases)
per_v = W + W + 1                                          # output_embedding row (V+1 rows) + head row + head bias
V_from_params = (P - fixed - W) / per_v
say("  result.json learned_parameter_count = %d ; solving 257*64 + 2*GRU + (V+1)*64 + 64*V + V = %d gives V = %s" % (P, P, V_from_params))
out["token_table"] = {"len": len(TOKENS), "bos": dec.BOS_ID, "V_from_param_count": V_from_params, "pins": pin_match}

# ---------------------------------------------------------------------------------------------
# 4. Load visible rows through the learner's door.
# ---------------------------------------------------------------------------------------------
rows = {s: q3_load.load_visible(DATA, "G", s) for s in ("train", "dev")}
say("\n=== 4. VISIBLE ROWS (q3_load.load_visible) === train %d dev %d" % (len(rows["train"]), len(rows["dev"])))


# ---------------------------------------------------------------------------------------------
# 5. Parser fidelity side checks.
# ---------------------------------------------------------------------------------------------
def tree_depth(a):
    return 1 + max(tree_depth(a["left"]), tree_depth(a["right"])) if a["node"] == "BinaryExpr" else 0


insp = json.loads((REC / "inspected_predictions.json").read_text(encoding="utf-8"))["cases"]
p16 = sum(r5.parse(c["input"]) == c["checker_reference_ast"] for c in insp)
say("\n=== 5. PARSER SIDE CHECKS ===")
say("  R5 parse == checker_reference_ast on saved cases: %d/%d" % (p16, len(insp)))
lit_noreg = sum(1 for c in insp for lf in r5.leaves(c["checker_reference_ast"]) if "register" not in lf)
lit_reg = sum(1 for c in insp for lf in r5.leaves(c["checker_reference_ast"]) if "register" in lf)
lit_nodrive = sum(1 for c in insp for lf in r5.leaves(c["checker_reference_ast"]) if lf["drive"] is None)
say("  saved reference literals: register key absent %d, present %d; drive null %d" % (lit_noreg, lit_reg, lit_nodrive))
parsed, parse_fail, render_fail = {}, collections.Counter(), collections.Counter()
for s, rs in rows.items():
    parsed[s] = []
    for r in rs:
        try:
            a = r5.parse(r["observation"])
        except Exception as e:                                  # noqa: BLE001
            parse_fail[s] += 1
            parsed[s].append(None)
            say("  PARSER_FAIL %s %s %r" % (s, r["record_id"], e))
            continue
        if r5.show(a) != r["observation"]:
            render_fail[s] += 1
        parsed[s].append(a)
    say("  %s: parsed %d/%d ; render(parse(obs)) == obs on %d/%d" % (
        s, len(rs) - parse_fail[s], len(rs), len(rs) - parse_fail[s] - render_fail[s], len(rs)))

# ---------------------------------------------------------------------------------------------
# 6. Scripted-gold replay.
# ---------------------------------------------------------------------------------------------
def slot_trace(tokens):
    """slot class + node depth for each gold position, same stack discipline as allowed_next."""
    pending, outl = [("expr", 0)], []
    for t in tokens:
        if not pending:
            outl.append(("eos", None))
            continue
        slot, d = pending.pop()
        outl.append((slot, d))
        if slot == "expr":
            if TOKENS[t] == "STATE":
                pending.extend((k, d) for k in ("register", "drive", "domain", "noetic"))
            else:
                pending.extend((("expr", d + 1), ("expr", d + 1), ("op", d)))
    return outl


def canon(a):
    return json.dumps(a, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def replay(split_rows, split_parsed, allowed_fn=None):
    """Returns per-row results. allowed_fn: optional in-memory replacement for dec.allowed_next (control only)."""
    original = dec.allowed_next
    if allowed_fn is not None:
        dec.allowed_next = allowed_fn                         # in memory only; restored below
    try:
        results = []
        for r, a in zip(split_rows, split_parsed):
            if a is None:
                results.append({"record_id": r["record_id"], "status": "PARSER_FAIL"})
                continue
            gold = dec.ast_to_tokens(a)
            calls = []

            def scripted(bottleneck, prefix, gold=gold, calls=calls):
                calls.append(len(prefix))
                k = len(prefix)
                return tuple(100.0 if (k < len(gold) and i == gold[k]) else 0.0 for i in range(len(TOKENS)))

            res = dec.free_decode(rep.Bottleneck((0.0,) * 64), scripted)
            ok = (res.outcome == "GENERATED" and res.tokens == gold and res.ast == a
                  and canon(res.ast) == canon(a) and res.steps == len(gold))
            rec = {"record_id": r["record_id"], "status": "OK" if ok else "FAIL", "outcome": res.outcome,
                   "n_tokens": len(gold), "steps": res.steps, "tokens_equal": res.tokens == gold,
                   "ast_equal": res.ast == a, "depth": tree_depth(a), "gold": gold}
            if not ok:
                trace = slot_trace(gold)
                first = next((i for i in range(min(len(res.tokens), len(gold))) if res.tokens[i] != gold[i]),
                             min(len(res.tokens), len(gold)))
                if first < len(gold):
                    slot, nd = trace[first]
                    allowed_here = dec.allowed_next(gold[:first])
                    rec.update({"fail_step": first, "fail_slot": slot, "fail_node_depth": nd,
                                "refused_token": TOKENS[gold[first]],
                                "chosen_token": TOKENS[res.tokens[first]] if first < len(res.tokens) else None,
                                "mask_allowed": [TOKENS[t] for t in allowed_here]})
            results.append(rec)
        return results
    finally:
        dec.allowed_next = original


say("\n=== 6. SCRIPTED-GOLD REPLAY (real mask, real codec) ===")
all_results = {}
for s in ("train", "dev"):
    rs = replay(rows[s], parsed[s])
    all_results[s] = rs
    st = collections.Counter(x["status"] for x in rs)
    steps_eq = sum(1 for x in rs if x.get("steps") == x.get("n_tokens"))
    tok_eq = sum(1 for x in rs if x.get("tokens_equal"))
    ast_eq = sum(1 for x in rs if x.get("ast_equal"))
    gen = sum(1 for x in rs if x.get("outcome") == "GENERATED")
    say("  %s: rows %d | OK %d FAIL %d PARSER_FAIL %d | GENERATED %d | tokens==gold %d | ast==parsed %d | steps==len(gold) %d" % (
        s, len(rs), st["OK"], st["FAIL"], st["PARSER_FAIL"], gen, tok_eq, ast_eq, steps_eq))
    by_depth = collections.Counter((x.get("depth"), x["status"]) for x in rs)
    say("     by (row depth, status): %s" % sorted(by_depth.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1])))
    fails = [x for x in rs if x["status"] == "FAIL"]
    if fails:
        say("     FAIL by slot: %s" % collections.Counter(x.get("fail_slot") for x in fails))
        say("     FAIL by (slot, refused token): %s" % collections.Counter((x.get("fail_slot"), x.get("refused_token")) for x in fails))
        say("     first fails: %s" % [{k: v for k, v in x.items() if k != "gold"} for x in fails[:5]])

# Independent per-step mask check (does not go through free_decode's argmax).
say("\n=== 7. PER-STEP MASK CHECK (gold[i] in allowed_next(gold[:i]); allowed_next(gold) == ()) ===")
slot_steps, slot_refused = collections.Counter(), collections.Counter()
allowed_sets_by_slot = collections.defaultdict(set)
end_ok, total_steps, token_use = 0, 0, collections.Counter()
max_tokens_seen = 0
for s in ("train", "dev"):
    for x in all_results[s]:
        if "gold" not in x:
            continue
        gold = x["gold"]
        max_tokens_seen = max(max_tokens_seen, len(gold))
        trace = slot_trace(gold)
        for i, t in enumerate(gold):
            allowed = dec.allowed_next(gold[:i])
            slot = trace[i][0]
            slot_steps[slot] += 1
            total_steps += 1
            token_use[TOKENS[t]] += 1
            allowed_sets_by_slot[slot].add(tuple(TOKENS[a] for a in allowed))
            if t not in allowed:
                slot_refused[slot] += 1
        end_ok += dec.allowed_next(gold) == ()
say("  total gold steps checked %d ; refused %d ; complete-after-EOS %d/%d" % (
    total_steps, sum(slot_refused.values()), end_ok, sum(len(all_results[s]) for s in all_results)))
say("  steps by slot: %s" % dict(sorted(slot_steps.items())))
say("  refused by slot: %s" % (dict(slot_refused) or "NONE"))
for slot, sets in sorted(allowed_sets_by_slot.items()):
    say("  distinct allowed sets at slot %-8s: %d -> %s" % (slot, len(sets), sorted(sets)[:3]))
say("  max gold length seen %d (limit %d)" % (max_tokens_seen, dec.DecodeLimits().max_tokens))
never = [n for n in TOKENS if token_use[n] == 0]
say("  tokens never used by any visible gold sequence: %s" % never)
say("  token use counts: %s" % dict(token_use))

# ---------------------------------------------------------------------------------------------
# 8. Planted-bug control (in memory): a mask that drops REG_T must fail exactly the rows with a |T literal.
# ---------------------------------------------------------------------------------------------
say("\n=== 8. PLANTED-BUG CONTROL (in-memory mask without REG_T) ===")
real_allowed = dec.allowed_next
REG_T = TOKEN_IDS["REG_T"]


def broken_allowed(prefix, limits=dec.DecodeLimits()):
    return tuple(t for t in real_allowed(prefix, limits) if t != REG_T)


ctrl_ok = True
for s in ("train", "dev"):
    expect = {r["record_id"] for r, a in zip(rows[s], parsed[s]) if a and any(lf.get("register") == "T" for lf in r5.leaves(a))}
    rs = replay(rows[s], parsed[s], broken_allowed)
    got = {x["record_id"] for x in rs if x["status"] == "FAIL"}
    slots = collections.Counter((x.get("fail_slot"), x.get("refused_token")) for x in rs if x["status"] == "FAIL")
    same = expect == got
    ctrl_ok &= same and len(expect) > 0
    say("  %s: rows with a |T literal %d ; replay FAILs %d ; sets identical %s ; fail (slot, token): %s" % (
        s, len(expect), len(got), same, dict(slots)))
assert dec.allowed_next is real_allowed
say("  control detects the planted bug: %s" % ctrl_ok)

# ---------------------------------------------------------------------------------------------
# 9. Final torch check + verdict under the pre-registered rules.
# ---------------------------------------------------------------------------------------------
loaded = sorted(m for m in sys.modules if m.split(".")[0] in BLOCKED)
say("\n=== 9. FINAL ===")
say("  torch/numpy in sys.modules: %s ; blocked import attempts: %s" % (loaded or "NONE", blocked_attempts or "NONE"))
n_all = sum(len(all_results[s]) for s in all_results)
n_ok = sum(1 for s in all_results for x in all_results[s] if x["status"] == "OK")
n_fail = sum(1 for s in all_results for x in all_results[s] if x["status"] == "FAIL")
n_pf = sum(1 for s in all_results for x in all_results[s] if x["status"] == "PARSER_FAIL")
say("  rows %d OK %d FAIL %d PARSER_FAIL %d" % (n_all, n_ok, n_fail, n_pf))
if loaded or blocked_attempts:
    verdict = "NOT_RUN_TORCH_DEPENDENCY"
elif not ctrl_ok:
    verdict = "VACUOUS (planted-bug control did not fail as required; no outcome claimed)"
elif n_pf:
    verdict = "FITS_NO_RULE (parser failures on %d rows)" % n_pf
elif n_fail:
    verdict = "MASK_OR_CODEC_BUG on %d rows" % n_fail
elif n_ok == 2304:
    verdict = "ALL_2304_REPLAY_EXACTLY -> mask and codec cleared for every visible row"
else:
    verdict = "FITS_NO_RULE (row count %d != 2304)" % n_all
say("  VERDICT (pre-registered rule): %s" % verdict)
json.dump({"verdict": verdict, "counts": {"rows": n_all, "ok": n_ok, "fail": n_fail, "parser_fail": n_pf},
           "per_row": {s: [{k: v for k, v in x.items() if k != "gold"} for x in all_results[s]] for s in all_results},
           "token_table": out["token_table"], "slot_steps": dict(slot_steps), "refused_by_slot": dict(slot_refused),
           "tokens_never_used": never},
          open(pathlib.Path(__file__).with_name("rt8_results.json"), "w", encoding="utf-8"), indent=1)
