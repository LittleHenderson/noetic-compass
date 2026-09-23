"""Independent isomorphism oracle for D-1 acceptance test A3 (Claude). Pure Python; imports nothing from the answer
path. Two methods that share no code beyond the graph representation, and must agree:

  M1  brute force: the lexicographically smallest relabelled edge list over all n! node orders (canonical form)
  M2  degree-refined backtracking: nodes are coloured by (in, out) degree, colours are refined by the multiset of
      neighbour colours until stable, and a mapping is built node by node, only between equal colours, checking
      every edge as it goes. It enumerates ALL isomorphisms (needed for correspondence mapping sets).

A graph is (n, frozenset of (a, b) directed edges over nodes 0..n-1).

    python -B oracle_isomorphism.py --selftest [--frozen-crosscheck]
"""
import argparse
import collections
import itertools
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent


# ----------------------------------------------------------------------------- M1
def canonical_form(n, edges):
    best = None
    for p in itertools.permutations(range(n)):
        key = tuple(sorted((p[a], p[b]) for a, b in edges))
        if best is None or key < best:
            best = key
    return (n, best)


def iso_m1(g, h):
    return g[0] == h[0] and len(g[1]) == len(h[1]) and canonical_form(*g) == canonical_form(*h)


# ----------------------------------------------------------------------------- M2
def _refined_colours(n, edges):
    out_n = collections.defaultdict(list)
    in_n = collections.defaultdict(list)
    for a, b in edges:
        out_n[a].append(b)
        in_n[b].append(a)
    colour = {v: (len(in_n[v]), len(out_n[v])) for v in range(n)}
    for _ in range(n):
        new = {v: (colour[v], tuple(sorted(colour[u] for u in out_n[v])), tuple(sorted(colour[u] for u in in_n[v])))
               for v in range(n)}
        if len(set(new.values())) == len(set(colour.values())):
            colour = new
            break
        colour = new
    return colour


def all_isomorphisms_m2(g, h):
    """Every bijection f: V(g) -> V(h) with (a,b) in E(g)  <=>  (f(a),f(b)) in E(h)."""
    (n, eg), (m, eh) = g, h
    if n != m or len(eg) != len(eh):
        return []
    cg, ch = _refined_colours(n, eg), _refined_colours(m, eh)
    if sorted(map(repr, cg.values())) != sorted(map(repr, ch.values())):
        return []
    eg, eh = set(eg), set(eh)
    order = sorted(range(n), key=lambda v: repr(cg[v]))
    found = []

    def extend(k, mapping, used):
        if k == n:
            found.append(dict(mapping))
            return
        v = order[k]
        for w in range(m):
            if w in used or repr(ch[w]) != repr(cg[v]):
                continue
            ok = True
            for u, x in mapping.items():
                if ((u, v) in eg) != ((x, w) in eh) or ((v, u) in eg) != ((w, x) in eh):
                    ok = False
                    break
            if ok and (((v, v) in eg) == ((w, w) in eh)):
                mapping[v] = w
                used.add(w)
                extend(k + 1, mapping, used)
                del mapping[v]
                used.discard(w)
    extend(0, {}, set())
    return found


def iso_m2(g, h):
    return bool(all_isomorphisms_m2(g, h))


def is_isomorphic(g, h):
    a, b = iso_m1(g, h), iso_m2(g, h)
    if a != b:
        raise AssertionError("ORACLE_METHODS_DISAGREE %r %r" % (g, h))
    return a


# ----------------------------------------------------------------------------- shapes
def _weakly_connected(n, edges):
    adj = collections.defaultdict(set)
    for a, b in edges:
        adj[a].add(b); adj[b].add(a)
    seen, stack = {0}, [0]
    while stack:
        x = stack.pop()
        for y in adj[x]:
            if y not in seen:
                seen.add(y); stack.append(y)
    return len(seen) == n


def _acyclic(n, edges):
    indeg = [0] * n
    out = collections.defaultdict(list)
    for a, b in edges:
        indeg[b] += 1; out[a].append(b)
    queue = [v for v in range(n) if indeg[v] == 0]
    seen = 0
    while queue:
        v = queue.pop(); seen += 1
        for w in out[v]:
            indeg[w] -= 1
            if indeg[w] == 0:
                queue.append(w)
    return seen == n


def dag_classes(n):
    """Every weakly connected DAG on n nodes, up to isomorphism, as canonical forms."""
    pairs = [(a, b) for a in range(n) for b in range(n) if a != b]
    classes = set()
    for k in range(n - 1, n * (n - 1) // 2 + 1):
        for es in itertools.combinations(pairs, k):
            s = set(es)
            if any((b, a) in s for a, b in es):
                continue
            if _weakly_connected(n, es) and _acyclic(n, es):
                classes.add(canonical_form(n, es))
    return sorted(classes)


def degree_multiset(n, edges):
    ind, outd = [0] * n, [0] * n
    for a, b in edges:
        outd[a] += 1; ind[b] += 1
    return tuple(sorted(zip(ind, outd)))


def degree_collisions(classes):
    by = collections.defaultdict(list)
    for n, e in classes:
        by[degree_multiset(n, e)].append((n, e))
    return {k: v for k, v in by.items() if len(v) > 1}


# ----------------------------------------------------------------------------- self-test
def selftest(frozen_crosscheck):
    t0 = time.monotonic()
    report = {"schema": "claude.d1-oracle-selftest/0.1"}
    counts = {n: dag_classes(n) for n in (3, 4, 5)}
    report["class_counts"] = {str(n): len(c) for n, c in counts.items()}
    small = counts[3] + counts[4]
    report["collisions_3_4"] = sum(len(v) for v in degree_collisions(small).values())
    coll5 = degree_collisions(counts[5])
    report["classes_5_in_a_collision"] = sum(len(v) for v in coll5.values())
    report["collision_groups_5"] = len(coll5)
    # M1 vs M2 on every ordered pair of classes of equal size at n = 3, 4, and on every colliding group at n = 5,
    # plus every class against a random relabelling of itself (must be isomorphic).
    import random
    rng = random.Random(20260923)
    pairs_checked = disagreements = 0
    for n in (3, 4):
        for g in counts[n]:
            for h in counts[n]:
                pairs_checked += 1
                a, b = iso_m1((n, g[1]), (n, h[1])), iso_m2((n, g[1]), (n, h[1]))
                disagreements += a != b
                if (g == h) != a:
                    disagreements += 1
    for group in coll5.values():
        for g in group:
            for h in group:
                pairs_checked += 1
                a, b = iso_m1(g, h), iso_m2(g, h)
                disagreements += a != b
                disagreements += (g == h) != a
    relabel_ok = 0
    for n in (3, 4, 5):
        for g in counts[n]:
            p = list(range(n)); rng.shuffle(p)
            h = (n, frozenset((p[a], p[b]) for a, b in g[1]))
            maps = all_isomorphisms_m2((n, frozenset(g[1])), h)
            relabel_ok += bool(maps) and all(
                frozenset((m[a], m[b]) for a, b in g[1]) == h[1] for m in maps)
    report.update(pairs_checked=pairs_checked, method_disagreements=disagreements,
                  relabelled_self_isomorphic=relabel_ok,
                  relabelled_total=sum(len(c) for c in counts.values()))
    if frozen_crosscheck:
        report["frozen_crosscheck"] = crosscheck_frozen()
    report["seconds"] = time.monotonic() - t0
    ok = (report["class_counts"] == {"3": 4, "4": 24, "5": 267} and disagreements == 0
          and relabel_ok == report["relabelled_total"]
          and (not frozen_crosscheck or report["frozen_crosscheck"]["disagreements"] == 0))
    report["verdict"] = "ORACLE_SELFTEST_PASS" if ok else "ORACLE_SELFTEST_FAIL"
    return report


def crosscheck_frozen():
    """Compare the oracle with the FROZEN checker's own `_isomorphisms` on every ordered pair of the 64 bank worlds
    (all <= 4 nodes, where the frozen checker is trusted): same yes/no AND same number of bijections."""
    package = HERE.parents[2]
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(package / "research" / "CAS_META_2_COMPOSITION"))
    from cas_meta2.typed_teaching import checker  # read-only use of the frozen module
    bank = json.loads((package / "records/typed_course_001/checks_002/public_course.json").read_text(encoding="utf-8"))["bank"]["worlds"]

    def graph(w):
        refs = sorted(x["ref"] for x in w["nodes"])
        idx = {r: i for i, r in enumerate(refs)}
        return (len(refs), frozenset((idx[e["source"]], idx[e["target"]]) for e in w["contains"]))
    pairs = disagreements = 0
    for a in bank:
        for b in bank:
            pairs += 1
            frozen_maps, _ = checker._isomorphisms(a, b)
            ours = all_isomorphisms_m2(graph(a), graph(b))
            if len(frozen_maps) != len(ours) or (bool(ours) != is_isomorphic(graph(a), graph(b))):
                disagreements += 1
    return {"pairs": pairs, "disagreements": disagreements}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--frozen-crosscheck", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.selftest:
        r = selftest(args.frozen_crosscheck)
        print(json.dumps(r, indent=1))
        if args.out:
            with open(args.out, "w", encoding="utf-8", newline="") as handle:
                handle.write(json.dumps(r, indent=1, sort_keys=True))
        sys.exit(0 if r["verdict"] == "ORACLE_SELFTEST_PASS" else 1)
