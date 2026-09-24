"""Pure-Python stand-ins for the probe v0.3 unit controls. No torch, no course material, no model, no GPU.

A synthetic bank shaped like the real public one (the probe v0.2 before-reading shows 64 candidate worlds, |X| = 48 for
every focus, 24 distinct foci over 70 analogy records):
  * 4 domains x 16 worlds; in each domain 4 three-node chains and 12 four-node worlds cycling through v0.2's five
    four-node shapes (so, as in the real bank, a three-node focus has no isomorph for any of its graph alternatives);
  * 24 foci: in each domain one chain and one world of each four-node shape;
  * 70 records cycling over the foci; the last two carry the frozen A7 witness ids, so the FROZEN rules apply as-is.
Scores are dyadic rationals (multiples of 1/8 and 1/64), so every sum and difference in these controls is exact.
Every scorer re-reads each world's shape and domain from the packet it is handed, so a counterfactual that fails to
reach the packet cannot pass unnoticed. Scores go through the real `probe_v0_3_harness.build_score_table`.
"""
import copy
import functools

import probe_v0_3_harness as harness
import probe_v0_3_metric as metric

DOMAINS = ("toy-domain-a", "toy-domain-b", "toy-domain-c", "toy-domain-d")
SHAPES3 = (((0, 1), (1, 2)), ((0, 1), (0, 2)), ((0, 2), (1, 2)), ((0, 1), (0, 2), (1, 2)))
SHAPES4 = tuple(metric.ALTERNATIVES[4])
SHAPE_INDEX = {metric.canon(3, e): k for k, e in enumerate(SHAPES3)}
SHAPE_INDEX.update({metric.canon(4, e): 4 + k for k, e in enumerate(SHAPES4)})
BANK_SHAPES = {metric.canon(3, SHAPES3[0])} | {metric.canon(4, e) for e in SHAPES4}
UNUSUAL_SHAPE_WEIGHT = 64.0
HIDDEN_ALPHA, HIDDEN_BETA = 1.5, 0.75


def world_id(i):
    return "w%02d" % i


def _edges_of(i):
    j = i % 16
    return (3, SHAPES3[0]) if j < 4 else (4, SHAPES4[(j - 4) % 5])


def make_world(i):
    wid = world_id(i)
    n, edges = _edges_of(i)
    nodes = [{"ref": "%s/n%d" % (wid, k)} for k in range(n)]
    return {"world_id": wid, "nodes": nodes, "declared_whole": nodes[0]["ref"],
            "contains": [{"ref": "%s/e%d" % (wid, k), "source": nodes[a]["ref"], "target": nodes[b]["ref"]}
                         for k, (a, b) in enumerate(edges)],
            "declarations": {"domain": DOMAINS[i // 16]}}


WORLDS = [make_world(i) for i in range(64)]
FOCI = [world_id(d * 16 + j) for d in range(4) for j in (0, 4, 5, 6, 7, 8)]
RECORD_IDS = ["toy-record-%02d" % k for k in range(68)] + list(metric.RULES["witnesses"])
FOCUS_OF = {rid: FOCI[k % 24] for k, rid in enumerate(RECORD_IDS)}


def node_index(world):
    """Stand-in for `pointer_inputs._node_index`: rank = position among the world's sorted refs."""
    refs = sorted(node["ref"] for node in world["nodes"])
    return {ref: k for k, ref in enumerate(refs)}


def packets():
    """70 analogy packets. The world dicts are SHARED (never copied) so any in-place mutation would show."""
    return {rid: {"record": {"query": {"kind": "analogy"}},
                  "source": {"focus_world_id": FOCUS_OF[rid], "worlds": list(WORLDS)}} for rid in RECORD_IDS}


def meta_of(packet):
    return {w["world_id"]: {"domain": w["declarations"]["domain"], "nodes": len(w["nodes"]),
                            "shape": harness.world_shape(w, node_index), "index": int(w["world_id"][1:])}
            for w in packet["source"]["worlds"]}


BANK_META = meta_of({"source": {"worlds": WORLDS}})


@functools.lru_cache(maxsize=None)
def hist(shape):
    n, edges = shape
    ind, outd = [0] * n, [0] * n
    for a, b in edges:
        outd[a] += 1
        ind[b] += 1
    out = {}
    for k in range(n):
        out[(ind[k], outd[k])] = out.get((ind[k], outd[k]), 0) + 1
    return tuple(sorted(out.items()))


def l1(h1, h2):
    a, b = dict(h1), dict(h2)
    return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in set(a) | set(b))


def own(m, c):
    """A candidate's own score: depends only on that candidate's CURRENT shape, its domain and its index."""
    return (SHAPE_INDEX[m[c]["shape"]] * 3 + DOMAINS.index(m[c]["domain"]) * 5 + m[c]["index"] % 7) / 8.0


def compare(m, f, c):
    """Graph mismatch (degree-histogram L1) plus a same-domain mark: the v0.2 self-test's comparison, in integers."""
    return l1(hist(m[f]["shape"]), hist(m[c]["shape"])) + (1 if m[c]["domain"] == m[f]["domain"] else 0)


def _hidden_affine(m, f):
    """POSITIVE, except that rewiring any non-focus world leaves that world's own terms as in the bank and instead
    maps EVERY candidate's score by s -> 1.5*s + 0.75: a global coupling that per-change re-standardisation hides."""
    eff = {w: (m[w] if w == f else BANK_META[w]) for w in m}
    s = SCORERS["POSITIVE"](eff, f)
    if any(m[w]["shape"] != BANK_META[w]["shape"] for w in m if w != f):
        s = {c: HIDDEN_ALPHA * v + HIDDEN_BETA for c, v in s.items()}
    return s


def _pool_dot(m, c):
    pool = {}
    for w in m:
        for k, v in hist(m[w]["shape"]):
            pool[k] = pool.get(k, 0) + v
    return sum(pool.get(k, 0) * v for k, v in hist(m[c]["shape"])) / 64.0


SCORERS = {
    # candidate-only: no focus dependence at all (the unchanged Helm 2.0 analogue)
    "HELM_LIKE": lambda m, f: {c: own(m, c) for c in m},
    # a genuine focus-to-candidate comparison of graph and domain (v0.2 self-test POSITIVE_COMPARISON)
    "POSITIVE": lambda m, f: {c: own(m, c) - 2.0 * compare(m, f, c) for c in m},
    # the same comparison with its sign flipped: favours the WRONG worlds
    "ANTI": lambda m, f: {c: own(m, c) + 2.0 * compare(m, f, c) for c in m},
    # graph comparison right, domain rule wrong (favours the same domain)
    "DOMAIN_ANTI": lambda m, f: {c: own(m, c) - 2.0 * l1(hist(m[f]["shape"]), hist(m[c]["shape"]))
                                 + (2.0 if m[c]["domain"] == m[f]["domain"] else 0.0) for c in m},
    # a shift that depends on the focus but is the same for every candidate (v0.2 self-test NEGATIVE_UNIFORM)
    "UNIFORM": lambda m, f: {c: own(m, c) + 3.0 * (len(m[f]["shape"][1]) + m[f]["nodes"]) for c in m},
    # depends on the focus only through a pool over EVERY world (v0.2 self-test NEGATIVE_COUPLED)
    "COUPLED": lambda m, f: {c: own(m, c) + 0.5 * _pool_dot(m, c) for c in m},
    # a genuine comparison in which a candidate's OWN score jumps by 64 when its own graph takes a shape the bank
    # never shows (as in the real bank, that happens only to three-node bystanders): the v0.2 confound case
    "STRONG_OWN": lambda m, f: {c: own(m, c) + (0.0 if m[c]["shape"] in BANK_SHAPES else UNUSUAL_SHAPE_WEIGHT)
                                - 2.0 * compare(m, f, c) for c in m},
    "HIDDEN_AFFINE": _hidden_affine,
}


def score_fn_for(kind):
    scorer = SCORERS[kind]

    def score(rid, packet, changed_world):
        m = meta_of(packet)
        return {c: float(v) for c, v in scorer(m, packet["source"]["focus_world_id"]).items()}
    return score


def build_table(kind, *, checkpoint_sha256=None, switch=True):
    pk = packets()
    return harness.build_score_table(pk, harness.analogy_ids_of(pk), score_fn_for(kind), node_index,
                                     model={"label": "toy-" + kind, "switch": switch,
                                            "checkpoint_sha256": checkpoint_sha256},
                                     provenance=dict(metric.frozen_hashes(), toy_bank=True),
                                     witnesses=metric.RULES["witnesses"])
