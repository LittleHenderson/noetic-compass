"""Analogy wiring probe v0.3 -- THE METRIC, a pure function of raw score tables.

Standard library only: no torch, no numpy, no GPU, no file writes. Rules: PREREG_ANALOGY_WIRING_PROBE_v0_3.md
(status PROPOSED). Label: CLAUDE_BUILT_CLAUDE_CHECKED; EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT.

WHY v0.3 EXISTS (design v0.4 amendment A2.6). Probe v0.2 re-standardised the candidate scores after every change,
over a candidate set that still contained the changed world. So a change in ONE world's own score moved every
other candidate's z-score even when their raw scores stayed fixed (a false "coupled" signal), and a change that
rescaled every candidate in the same way was invisible. v0.2 also scored its set contrasts by their ABSOLUTE size,
so movement AWAY from the newly matching worlds passed as easily as movement toward them.

WHAT v0.3 DOES, for every counterfactual (one changed world w):
  * the reference set R is the candidate set with w removed;
  * the reference spread sigma0 is the population standard deviation of the UNCHANGED packet's scores over R.
    It is computed once, from the unchanged packet, and never from a counterfactual;
  * the shared shift is the MEDIAN over R of the raw changes (s - s0). w is never in R, so its own movement can
    never enter another candidate's value; one moved candidate cannot move the median of 3 or more;
  * a candidate's residual is (s_c - s0_c) - shift, read in units of sigma0;
  * RC and RC_dom are SIGNED: (mean raw change of the worlds that START matching) minus (mean raw change of the
    worlds that STOP matching), in units of sigma0. A correct comparison makes both positive.
The only permitted score transformation is s -> a*s + b, with a > 0 fixed for one model and b free per packet
(b may depend on the focus and on the counterfactual). Every scored quantity is invariant to it.
"""
import copy
import functools
import hashlib
import itertools
import json
import math
import pathlib
import statistics

HERE = pathlib.Path(__file__).resolve().parent
PREREG_NAME = "PREREG_ANALOGY_WIRING_PROBE_v0_3.md"
SCHEMA_TABLE = "claude.analogy-wiring-probe-score-table/0.3"
SCHEMA_RESULT = "claude.analogy-wiring-probe-result/0.3"
SCHEMA_VALIDATION = "claude.analogy-wiring-probe-validation/0.3"

# Frozen in PREREG_ANALOGY_WIRING_PROBE_v0_3.md section 4. The witness pair (A7) and the counts are v0.2's.
RULES = {
    "tau": 1e-5,                         # z units: "no dependency" tolerance
    "noise_max_z": 1e-6,                 # z units of the record's own reference spread
    "rc_min_signed": 1e-2,               # z units, SIGNED: toward the favoured set must be >= +this
    "share_foci": 22,                    # of the 24 distinct foci
    "foci_expected": 24,
    "records_expected": 70,
    "leak_ratio": 0.1,                   # bystander L(f) <= 0.1 * M3z(f)
    "effect_floor_min": 1e-3,            # z units
    "effect_floor_noise_factor": 100.0,  # effect_floor = max(1e-3, 100 * delta0_z)
    "min_candidates": 4,                 # |X| >= 4, so |X \ {bystander}| >= 3 and the median shift is exact
    "witnesses": ["typed-input-092dc3b89a0480d462945ca7447bac511c81358714e48059922cd9b469f8a53e",
                  "typed-input-0df25be340de7c545d7cdac679233a291d8d134b872c808ff098130afae7171a"],
}
ALTERNATIVES = {  # v0.2's frozen list, unchanged (canonical edge form)
    4: [((0, 1), (0, 2), (0, 3)), ((0, 1), (0, 2), (1, 3), (2, 3)), ((0, 1), (1, 2), (2, 3)),
        ((0, 1), (0, 2), (3, 1)), ((0, 1), (0, 2), (1, 3))],
    3: [((0, 1), (1, 2)), ((0, 1), (0, 2)), ((0, 2), (1, 2)), ((0, 1), (0, 2), (1, 2))],
}
PRESENT_BOTH = "PRESENT_GRAPH_AND_DOMAIN"
VERDICTS = ("INVALID_NONDETERMINISTIC", "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT", PRESENT_BOTH, "PRESENT_GRAPH",
            "COUPLED_NOT_COMPARISON", "MOVES_AWAY_FROM_FAVOURED_SET", "MIXED")

# Validation (prereg section 6): five raw cases from the real harness, two derived from them in pure Python.
VALIDATION_RAW_CASES = ("V1_CONTROL_UNWRAPPED", "V2_POSITIVE_COMPARISON", "V3_ANTI_COMPARISON",
                        "V4_NEGATIVE_UNIFORM", "V5_NEGATIVE_COUPLED")
VALIDATION_KAPPA = 0.5
VALIDATION_AFFINE_A = 3.0
VALIDATION_REL_TOL = 1e-9


class TableRefused(ValueError):
    """The score table is not a complete, well-formed v0.3 table. This is NOT a verdict on the model."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _require(ok, code):
    if not ok:
        raise TableRefused(code)


def lf_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def frozen_hashes():
    """The LF-normalised sha256 of the prereg, this metric and the harness, as they sit beside this file."""
    return {"prereg_sha256_lf": lf_sha(HERE / PREREG_NAME),
            "metric_sha256_lf": lf_sha(pathlib.Path(__file__)),
            "harness_sha256_lf": lf_sha(HERE / "probe_v0_3_harness.py")}


# ---------------------------------------------------------------- shapes (v0.2's canonical form, unchanged)
@functools.lru_cache(maxsize=None)
def _canon(n, edges):
    best = None
    for p in itertools.permutations(range(n)):
        key = tuple(sorted((p[a], p[b]) for a, b in edges))
        if best is None or key < best:
            best = key
    return (n, best)


def canon(n, edges):
    """(n, the lexicographically least sorted edge tuple over every relabelling) -- v0.2's `canon`."""
    return _canon(int(n), tuple(sorted((int(a), int(b)) for a, b in edges)))


def shape_json(shape):
    n, edges = shape
    return [int(n), [[int(a), int(b)] for a, b in edges]]


def shape_key(value):
    _require(type(value) is list and len(value) == 2 and type(value[0]) is int and type(value[1]) is list
             and all(type(e) is list and len(e) == 2 for e in value[1]), "TABLE_SHAPE")
    key = (value[0], tuple((int(e[0]), int(e[1])) for e in value[1]))
    _require(canon(key[0], key[1]) == key, "TABLE_SHAPE_NOT_CANONICAL")
    return key


# ---------------------------------------------------------------- the counterfactual plan (v0.2's enumeration)
def plan_focus(focus, meta, candidates):
    """The counterfactuals v0.3 requires for one focus, from the UNCHANGED packet's world facts only.

    Same enumeration as v0.2: every graph alternative of the focus's node count except its own shape; ONE
    bystander, the first (sorted) cross-domain candidate with the focus's node count, rewired to every alternative
    except its own shape; every other declared domain of the bank, in sorted order.
    """
    domain = {w: meta[w]["domain"] for w in meta}
    n = meta[focus]["nodes"]
    fshape = shape_key(meta[focus]["shape"])
    X = sorted(c for c in candidates if c != focus and domain[c] != domain[focus])
    X_all = sorted(c for c in candidates if c != focus)
    graph = [[list(e) for e in edges] for edges in ALTERNATIVES.get(n, []) if canon(n, edges) != fshape]
    same_size = [c for c in X if meta[c]["nodes"] == n]
    bystander = same_size[0] if same_size else None
    runs = []
    if bystander is not None:
        bshape = shape_key(meta[bystander]["shape"])
        runs = [[list(e) for e in edges] for edges in ALTERNATIVES.get(n, []) if canon(n, edges) != bshape]
    domains = sorted(set(domain.values()) - {domain[focus]})
    return {"X": X, "X_all": X_all, "graph": graph, "bystander": bystander, "bystander_runs": runs,
            "domains": domains}


# ---------------------------------------------------------------- arithmetic
def _spread(scores, R):
    """Population standard deviation over R (exact rational arithmetic inside `statistics`)."""
    return statistics.pstdev([scores[c] for c in R]) if len(R) >= 2 else 0.0


def residuals(s, s0, R):
    """{c: (s_c - s0_c) - median over R of (s - s0)} for c in R, and that median (the shared shift)."""
    change = {c: s[c] - s0[c] for c in R}
    shift = statistics.median(list(change.values()))
    return {c: change[c] - shift for c in R}, shift


def discordant_fraction(a, b, X):
    """v0.2's Kendall discordant-pair fraction, on RAW scores (a monotone rescale cannot change it)."""
    pairs = list(itertools.combinations(sorted(X), 2))
    bad = sum(1 for i, j in pairs if (a[i] - a[j]) * (b[i] - b[j]) < 0)
    return bad / len(pairs) if pairs else 0.0


def standardize(scores, R):
    """Within-record z-scores of an UNCHANGED packet (M1z, M2z only); None when the spread is zero."""
    vals = [scores[c] for c in R]
    sd = statistics.pstdev(vals)
    if sd == 0:
        return None
    mu = statistics.fmean(vals)
    return {c: (scores[c] - mu) / sd for c in R}


def decision(scores):
    """v0.2's slot decision: argmax with NO_MATCH pinned at logit 0; a tie with NO_MATCH counts as NO_MATCH."""
    best = max(sorted(scores), key=scores.get)
    return best if scores[best] > 0.0 else "NO_MATCH"


def _mean_change(s, s0, S):
    return statistics.fmean([s[c] - s0[c] for c in S])


# ---------------------------------------------------------------- table checks
def _scores(value, candidates, where):
    _require(type(value) is dict and set(value) == candidates, "TABLE_CANDIDATES:" + where)
    for v in value.values():
        _require(type(v) is float and math.isfinite(v), "TABLE_SCORE:" + where)
    return value


def _check_meta(meta, candidates, where):
    _require(type(meta) is dict and candidates <= set(meta), "TABLE_WORLDS:" + where)
    for w, m in meta.items():
        _require(type(m) is dict and type(m.get("domain")) is str and type(m.get("nodes")) is int,
                 "TABLE_WORLD_FIELDS:" + where + ":" + w)
        _require(shape_key(m.get("shape"))[0] == m["nodes"], "TABLE_WORLD_NODES:" + where + ":" + w)


# ---------------------------------------------------------------- one focus
def _focus_metrics(f, F, records, rules):
    _require(type(F) is dict, "TABLE_FOCUS:" + f)
    rid = F.get("record")
    _require(rid in records, "TABLE_FOCUS_RECORD:" + f)
    base = records[rid]["base"]
    candidates = set(base)
    meta = F.get("worlds")
    _check_meta(meta, candidates, f)
    for c in candidates:
        _require(meta[c]["domain"] == records[rid]["candidate_domains"][c], "TABLE_DOMAIN_DISAGREES:" + f + ":" + c)
    _require(f in candidates, "TABLE_FOCUS_NOT_CANDIDATE:" + f)
    plan = plan_focus(f, meta, candidates)
    _require(len(plan["X"]) >= rules["min_candidates"], "TABLE_CANDIDATE_SET_TOO_SMALL:" + f)

    graph, bys, doms = F.get("graph"), F.get("bystander"), F.get("domain")
    _require(type(graph) is list and [g.get("edges") for g in graph] == plan["graph"], "TABLE_GRAPH_RUNS:" + f)
    if plan["bystander"] is None:
        _require(bys is None, "TABLE_BYSTANDER_UNEXPECTED:" + f)
    else:
        _require(type(bys) is dict and bys.get("world") == plan["bystander"] and type(bys.get("runs")) is list
                 and [r.get("edges") for r in bys["runs"]] == plan["bystander_runs"], "TABLE_BYSTANDER_RUNS:" + f)
    _require(type(doms) is list and [d.get("domain") for d in doms] == plan["domains"], "TABLE_DOMAIN_RUNS:" + f)
    for k, g in enumerate(graph):
        _scores(g.get("scores"), candidates, "%s:graph%d" % (f, k))
    for k, r in enumerate(bys["runs"] if bys else []):
        _scores(r.get("scores"), candidates, "%s:bystander%d" % (f, k))
    for k, d in enumerate(doms):
        _scores(d.get("scores"), candidates, "%s:domain%d" % (f, k))

    domain = {w: meta[w]["domain"] for w in meta}
    shape = {w: shape_key(meta[w]["shape"]) for w in meta}
    n = meta[f]["nodes"]
    X, X_all = plan["X"], plan["X_all"]
    A = [c for c in X if shape[c] == shape[f]]
    undefined = []

    # graph counterfactuals: M3z, K, signed RC, M5, top-1 changes
    sigma_x = _spread(base, X)
    m3, kf, rc_rows, m5, top1, shifts = 0.0, 0.0, [], [], 0, []
    for g in graph:
        s = g["scores"]
        new_shape = canon(n, g["edges"])
        res, shift = residuals(s, base, X)
        shifts.append(shift)
        kf = max(kf, discordant_fraction(base, s, X))
        A2 = [c for c in X if shape[c] == new_shape]
        if sigma_x > 0:
            m3 = max(m3, max(abs(v) for v in res.values()) / sigma_x)
            if A and A2:
                rc_rows.append((_mean_change(s, base, A2) - _mean_change(s, base, A)) / sigma_x)
        margin = max(s[c] for c in X) - max(base[c] for c in X)
        m5.append({"new_accepted_empty": not A2, "margin_change_logits": margin,
                   "margin_change_z": margin / sigma_x if sigma_x > 0 else None})
        if decision(s) != decision(base):
            top1 += 1
    if sigma_x == 0:
        undefined.append("REFERENCE_SPREAD_ZERO_X")
    M3z = m3 if sigma_x > 0 else None
    RC = statistics.fmean(rc_rows) if rc_rows else None

    # bystander counterfactuals: L, over X without the bystander, in units of that set's own reference spread
    L, L_rows, sigma_b = None, [], None
    if plan["bystander"] is not None:
        b = plan["bystander"]
        R = [c for c in X if c != b]
        sigma_b = _spread(base, R)
        if sigma_b > 0:
            for r in bys["runs"]:
                res, _shift = residuals(r["scores"], base, R)
                L_rows.append(max(abs(v) for v in res.values()) / sigma_b)
            L = max(L_rows) if L_rows else None
        else:
            undefined.append("REFERENCE_SPREAD_ZERO_X_MINUS_BYSTANDER")
    else:
        undefined.append("NO_BYSTANDER")

    # domain counterfactuals: signed RC_dom over every non-focus world (the cross-domain set itself changes)
    sigma_all = _spread(base, X_all)
    rcd_rows = []
    for d in doms:
        s, other = d["scores"], d["domain"]
        start = [c for c in X_all if shape[c] == shape[f] and domain[c] == domain[f]]
        stop = [c for c in X_all if shape[c] == shape[f] and domain[c] == other]
        if start and stop and sigma_all > 0:
            rcd_rows.append((_mean_change(s, base, start) - _mean_change(s, base, stop)) / sigma_all)
        else:
            rcd_rows.append(None)
    if sigma_all == 0:
        undefined.append("REFERENCE_SPREAD_ZERO_X_ALL")
    defined = [v for v in rcd_rows if v is not None]
    RC_dom = statistics.fmean(defined) if defined else None

    return {"record": rid, "nodes": n, "X": len(X), "A": len(A), "bystander": plan["bystander"],
            "sigma0_X": sigma_x, "sigma0_X_minus_bystander": sigma_b, "sigma0_X_all": sigma_all,
            "M3z": M3z, "K": kf, "RC": RC, "RC_per_alternative": rc_rows, "L": L, "L_per_alternative": L_rows,
            "RC_dom": RC_dom, "RC_dom_per_domain": rcd_rows, "graph_shared_shift_logits": shifts, "M5": m5,
            "top1_changes": top1, "undefined": undefined}


# ---------------------------------------------------------------- the whole table
def evaluate(table, rules=None):
    """The v0.3 reading of ONE model's raw score table. Raises TableRefused if the table is not complete."""
    rules = RULES if rules is None else rules
    _require(type(table) is dict and table.get("schema") == SCHEMA_TABLE, "TABLE_SCHEMA")
    records, foci = table.get("records"), table.get("foci")
    _require(type(records) is dict and len(records) == rules["records_expected"], "TABLE_RECORD_COUNT")
    _require(type(foci) is dict and len(foci) == rules["foci_expected"], "TABLE_FOCUS_COUNT")
    _require(table.get("witnesses") == rules["witnesses"], "TABLE_WITNESSES")

    # records: the noise gate (M0), in each record's own reference units, and the representative per focus
    focus_of, rep, delta0_raw, delta0_z = {}, {}, 0.0, 0.0
    for rid in sorted(records):
        r = records[rid]
        _require(type(r) is dict and type(r.get("focus")) is str, "TABLE_RECORD:" + rid)
        base = r.get("base")
        _require(type(base) is dict and base, "TABLE_RECORD_BASE:" + rid)
        candidates = set(base)
        _scores(base, candidates, rid + ":base")
        _scores(r.get("base_repeat"), candidates, rid + ":base_repeat")
        dom = r.get("candidate_domains")
        _require(type(dom) is dict and set(dom) == candidates and all(type(v) is str for v in dom.values()),
                 "TABLE_RECORD_DOMAINS:" + rid)
        f = r["focus"]
        _require(f in candidates, "TABLE_FOCUS_NOT_CANDIDATE:" + rid)
        focus_of[rid] = f
        rep.setdefault(f, rid)
        diff = max(abs(base[c] - r["base_repeat"][c]) for c in candidates)
        delta0_raw = max(delta0_raw, diff)
        X = [c for c in candidates if c != f and dom[c] != dom[f]]
        sd = _spread(base, X)
        delta0_z = max(delta0_z, 0.0 if diff == 0 else (diff / sd if sd > 0 else math.inf))
    _require(set(foci) == set(rep), "TABLE_FOCI_DISAGREE_WITH_RECORDS")
    for f, F in foci.items():
        _require(type(F) is dict and F.get("record") == rep[f], "TABLE_FOCUS_NOT_FIRST_RECORD:" + f)

    per_focus = {f: _focus_metrics(f, foci[f], records, rules) for f in sorted(foci)}

    # M1z: the A7 witness pair, each standardised over the shared cross-domain set of its own unchanged packet
    ra, rb = rules["witnesses"]
    _require(ra in records and rb in records, "TABLE_WITNESS_RECORDS")
    fa, fb = focus_of[ra], focus_of[rb]
    wa, wb = records[ra]["base"], records[rb]["base"]
    dom_a = records[ra]["candidate_domains"]
    _require(set(wa) == set(wb), "TABLE_WITNESS_CANDIDATES")
    Xw = sorted(c for c in wa if c not in (fa, fb) and dom_a[c] != dom_a[fa] and dom_a[c] != dom_a[fb])
    za, zb = standardize(wa, Xw), standardize(wb, Xw)
    m1z = max(abs(za[c] - zb[c]) for c in Xw) if (za is not None and zb is not None and Xw) else None
    m1k = discordant_fraction(wa, wb, Xw)

    # M2z: within each focus-DOMAIN group X is one set of worlds; the spread of each candidate's z across records
    received, m2_defined = {}, True
    for rid in sorted(records):
        r = records[rid]
        f, dom = r["focus"], r["candidate_domains"]
        X = sorted(c for c in r["base"] if c != f and dom[c] != dom[f])
        z = standardize(r["base"], X)
        if z is None:
            m2_defined = False
            continue
        for c, v in z.items():
            received.setdefault((dom[f], c), []).append(v)
    m2z = max(max(v) - min(v) for v in received.values()) if (m2_defined and received) else None

    floor = max(rules["effect_floor_min"], rules["effect_floor_noise_factor"] * delta0_z)
    items = list(per_focus.values())
    count = lambda pred: sum(1 for p in items if pred(p))  # noqa: E731
    rc_vals = [p["RC"] for p in items if p["RC"] is not None]
    rc_min, share = rules["rc_min_signed"], rules["share_foci"]
    summary = {
        "foci": len(items),
        "K_positive": count(lambda p: p["K"] > 0),
        "M3z_above_floor": count(lambda p: p["M3z"] is not None and p["M3z"] >= floor),
        "RC_defined": len(rc_vals),
        "median_RC_signed": statistics.median(rc_vals) if rc_vals else None,
        "RC_positive": count(lambda p: p["RC"] is not None and p["RC"] > 0),
        "RC_negative": count(lambda p: p["RC"] is not None and p["RC"] < 0),
        "bystander_ok": count(lambda p: p["L"] is not None and p["M3z"] is not None
                              and p["L"] <= rules["leak_ratio"] * p["M3z"]),
        "RC_dom_ok": count(lambda p: p["RC_dom"] is not None and p["RC_dom"] >= rc_min),
        "RC_dom_wrong_direction": count(lambda p: p["RC_dom"] is not None and p["RC_dom"] <= -rc_min),
        "max_M3z": max((p["M3z"] for p in items if p["M3z"] is not None), default=None),
        "max_K": max(p["K"] for p in items),
        "max_L": max((p["L"] for p in items if p["L"] is not None), default=None),
        "effect_floor": floor,
        "top1_changes_reported_not_scored": sum(p["top1_changes"] for p in items),
    }
    graph_moves = summary["K_positive"] >= share and summary["M3z_above_floor"] >= share
    med = summary["median_RC_signed"]
    toward = med is not None and med >= rc_min
    away = med is not None and med <= -rc_min
    if delta0_z > rules["noise_max_z"]:
        verdict = "INVALID_NONDETERMINISTIC"
    elif (m1z is not None and m1z <= rules["tau"] and m2z is not None and m2z <= rules["tau"]
          and all(p["M3z"] is not None and p["M3z"] <= rules["tau"] and p["K"] == 0 for p in items)):
        verdict = "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT"
    elif graph_moves and toward and summary["bystander_ok"] >= share:
        verdict = PRESENT_BOTH if summary["RC_dom_ok"] >= share else "PRESENT_GRAPH"
    elif graph_moves and toward:
        verdict = "COUPLED_NOT_COMPARISON"
    elif graph_moves and away:
        verdict = "MOVES_AWAY_FROM_FAVOURED_SET"
    else:
        verdict = "MIXED"
    return {"schema": SCHEMA_RESULT, "verdict": verdict, "rules": rules, "rules_are_frozen": rules == RULES,
            "model": table.get("model"), "M0_delta0_logits": delta0_raw, "M0_delta0_z": delta0_z,
            "M1z": m1z, "M1_kendall_discordant": m1k, "M1_cross_domain_shared": len(Xw), "M2z": m2z,
            "summary": summary, "per_focus": per_focus, "analogy_records": len(records)}


# ---------------------------------------------------------------- derived controls (pure; used by validation)
def default_offset(key):
    """A deterministic per-packet offset in [-4, 4], different for every packet key."""
    digest = hashlib.sha256(json.dumps(key, sort_keys=True).encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) % 8001 - 4000) / 1000.0


def affine(table, a, offset=default_offset):
    """Every score s -> a*s + b(packet): a > 0 for the whole table, b per packet (the repeat shares its packet's b)."""
    if not (type(a) is float and a > 0 and math.isfinite(a)):
        raise ValueError("AFFINE_SCALE_MUST_BE_POSITIVE_FLOAT")
    t = copy.deepcopy(table)

    def apply(scores, key):
        b = offset(key)
        return {c: a * v + b for c, v in scores.items()}

    for rid, r in t["records"].items():
        r["base"] = apply(r["base"], ["record", rid])
        r["base_repeat"] = apply(r["base_repeat"], ["record", rid])
    for f, F in t["foci"].items():
        for k, g in enumerate(F["graph"]):
            g["scores"] = apply(g["scores"], ["graph", f, k])
        for k, run in enumerate(F["bystander"]["runs"] if F["bystander"] else []):
            run["scores"] = apply(run["scores"], ["bystander", f, k])
        for k, d in enumerate(F["domain"]):
            d["scores"] = apply(d["scores"], ["domain", f, k])
    t["provenance"] = dict(t.get("provenance") or {}, derived={"transform": "affine", "a": a})
    return t


def inject_interaction(table, kappa):
    """Add kappa to ONE fixed other candidate (the first of X without the bystander) in every bystander run."""
    t = copy.deepcopy(table)
    targets = {}
    for f, F in t["foci"].items():
        if not F.get("bystander"):
            continue
        plan = plan_focus(f, F["worlds"], set(t["records"][F["record"]]["base"]))
        target = [c for c in plan["X"] if c != plan["bystander"]][0]
        targets[f] = target
        for run in F["bystander"]["runs"]:
            run["scores"][target] = run["scores"][target] + kappa
    t["provenance"] = dict(t.get("provenance") or {}, derived={"transform": "inject_interaction",
                                                                "kappa": kappa, "targets": targets})
    return t


def _close(x, y, tol=VALIDATION_REL_TOL):
    if x is None or y is None:
        return x is None and y is None
    return abs(x - y) <= tol * max(1.0, abs(x), abs(y))


def scored_quantities(result):
    """Every number a verdict depends on, flattened, for invariance comparisons."""
    out = {"M0_delta0_z": result["M0_delta0_z"], "M1z": result["M1z"], "M2z": result["M2z"],
           "median_RC_signed": result["summary"]["median_RC_signed"], "effect_floor": result["summary"]["effect_floor"]}
    for f, p in result["per_focus"].items():
        for name in ("M3z", "K", "RC", "L", "RC_dom"):
            out["%s:%s" % (name, f)] = p[name]
    return out


def evaluate_validation(raw_tables, source_sha_before, source_sha_after, rules=None):
    """The frozen validation table (prereg section 6), read from the five raw control tables."""
    rules = RULES if rules is None else rules
    cases, failed = {}, []

    def note(case, ok, **facts):
        cases[case] = dict(facts, ok=bool(ok))
        if not ok:
            failed.append(case)

    results = {}
    for case in VALIDATION_RAW_CASES:
        if case not in raw_tables:
            note(case, False, reason="MISSING")
            continue
        try:
            results[case] = evaluate(raw_tables[case], rules)
        except TableRefused as err:
            note(case, False, reason="TABLE_REFUSED:" + err.code)
    tau, rc_min, share = rules["tau"], rules["rc_min_signed"], rules["share_foci"]

    def all_L_within_tau(r):
        return all(p["L"] is not None and p["L"] <= tau for p in r["per_focus"].values())

    r = results.get("V1_CONTROL_UNWRAPPED")
    if r:
        note("V1_CONTROL_UNWRAPPED", r["verdict"] == "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT" and all_L_within_tau(r),
             verdict=r["verdict"], max_L=r["summary"]["max_L"])
    r = results.get("V2_POSITIVE_COMPARISON")
    if r:
        med = r["summary"]["median_RC_signed"]
        note("V2_POSITIVE_COMPARISON", r["verdict"] == PRESENT_BOTH and all_L_within_tau(r)
             and med is not None and med >= rc_min, verdict=r["verdict"], max_L=r["summary"]["max_L"],
             median_RC_signed=med)
    r = results.get("V3_ANTI_COMPARISON")
    if r:
        med = r["summary"]["median_RC_signed"]
        note("V3_ANTI_COMPARISON", r["verdict"] == "MOVES_AWAY_FROM_FAVOURED_SET" and med is not None
             and med <= -rc_min and r["summary"]["RC_dom_wrong_direction"] >= share,
             verdict=r["verdict"], median_RC_signed=med,
             RC_dom_wrong_direction=r["summary"]["RC_dom_wrong_direction"])
    r = results.get("V4_NEGATIVE_UNIFORM")
    if r:
        note("V4_NEGATIVE_UNIFORM", r["verdict"] == "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT", verdict=r["verdict"])
    r = results.get("V5_NEGATIVE_COUPLED")
    if r:
        note("V5_NEGATIVE_COUPLED", r["verdict"] not in ("PRESENT_GRAPH", PRESENT_BOTH), verdict=r["verdict"])

    base = results.get("V1_CONTROL_UNWRAPPED")
    if base:  # V6: a known injected interaction reads |kappa| / sigma0, and nothing else moves
        r6 = evaluate(inject_interaction(raw_tables["V1_CONTROL_UNWRAPPED"], VALIDATION_KAPPA), rules)
        misses = []
        for f, p in r6["per_focus"].items():
            p1 = base["per_focus"][f]
            if p1["bystander"] is None:
                continue
            sigma0 = p1["sigma0_X_minus_bystander"]
            if not sigma0 or p["L"] is None or abs(p["L"] - abs(VALIDATION_KAPPA) / sigma0) > tau:
                misses.append(f)
        q1, q6 = scored_quantities(base), scored_quantities(r6)
        moved = sorted(k for k in q1 if not k.startswith("L:") and q1[k] != q6[k])
        note("V6_INJECTED_INTERACTION", not misses and not moved, kappa=VALIDATION_KAPPA, foci_off_target=misses,
             other_quantities_moved=moved)
    else:
        note("V6_INJECTED_INTERACTION", False, reason="V1_UNAVAILABLE")
    pos = results.get("V2_POSITIVE_COMPARISON")
    if pos:  # V7: s -> a*s + b(packet) leaves the verdict and every scored quantity unchanged
        r7 = evaluate(affine(raw_tables["V2_POSITIVE_COMPARISON"], VALIDATION_AFFINE_A), rules)
        q2, q7 = scored_quantities(pos), scored_quantities(r7)
        moved = sorted(k for k in q2 if not _close(q2[k], q7[k]))
        note("V7_AFFINE_INVARIANCE", r7["verdict"] == pos["verdict"] and not moved, a=VALIDATION_AFFINE_A,
             verdict=r7["verdict"], quantities_moved=moved)
    else:
        note("V7_AFFINE_INVARIANCE", False, reason="V2_UNAVAILABLE")
    note("SOURCE_UNCHANGED", source_sha_before is not None and source_sha_before == source_sha_after,
         before=source_sha_before, after=source_sha_after)
    return {"schema": SCHEMA_VALIDATION, "validation": "VALIDATION_PASS" if not failed else "VALIDATION_FAIL",
            "failed": failed, "cases": cases, "rules_are_frozen": rules == RULES}
