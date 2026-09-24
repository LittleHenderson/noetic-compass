"""Census: can directed colour refinement tell apart every same-degree pair of 5- and 6-node shapes?

PLAIN SUMMARY. Helm's rounds pass messages from parents and children (`pointer_learner.py:1137-1202`). A learner of
that family can tell two shapes apart from structure alone only if directed colour refinement (1-WL, started from
each node's in-degree and out-degree) tells them apart. That is a NECESSARY condition, not a sufficient one: Helm
also RMS-normalises each summed message, which hides how many identical neighbours were summed.

This script lists every weakly connected directed acyclic shape with n nodes and every degree at most 4 (the
reader's exact range), groups the shapes by their sorted (in-degree, out-degree) list, and counts the
non-isomorphic pairs inside a group that colour refinement cannot separate. It also reports the most self-maps any
such shape has, which bounds how many valid answers a correspondence question can have (checker v2 refuses above
64). Shapes with isolated nodes are allowed by the source validator but are NOT counted here. Pure Python; about
10 seconds.

    python -B colour_refinement_census.py      # prints one JSON line per node count (5 and 6)
"""
import collections
import itertools
import json


def shapes(n):
    """Every weakly connected DAG on n nodes, as edges (a, b) with a < b. Every class has such a labelling."""
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    for mask in range(1, 1 << len(pairs)):
        edges = tuple(pair for index, pair in enumerate(pairs) if mask >> index & 1)
        neighbours = collections.defaultdict(set)
        for a, b in edges:
            neighbours[a].add(b)
            neighbours[b].add(a)
        seen, stack = {0}, [0]
        while stack:
            for other in neighbours[stack.pop()]:
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        if len(seen) == n:
            yield edges


def stable_colours(n, edges):
    """Directed colour refinement from (in-degree, out-degree). Colours are nested tuples, comparable across graphs."""
    parents, children = collections.defaultdict(list), collections.defaultdict(list)
    for a, b in edges:
        children[a].append(b)
        parents[b].append(a)
    colour = {v: (len(parents[v]), len(children[v])) for v in range(n)}
    for _ in range(n):
        refined = {v: (colour[v], tuple(sorted(colour[p] for p in parents[v])),
                       tuple(sorted(colour[c] for c in children[v]))) for v in range(n)}
        stop = len(set(refined.values())) == len(set(colour.values()))
        colour = refined
        if stop:
            break
    return colour


def canonical(n, edges):
    """(colour-refinement signature, smallest edge list over colour-respecting relabellings): an exact class key."""
    colour = stable_colours(n, edges)
    order = sorted(range(n), key=lambda v: colour[v])
    groups = [list(group) for _, group in itertools.groupby(order, key=lambda v: colour[v])]
    best = None
    for choice in itertools.product(*[itertools.permutations(group) for group in groups]):
        position = {v: index for index, v in enumerate(v for part in choice for v in part)}
        form = tuple(sorted((position[a], position[b]) for a, b in edges))
        best = form if best is None or form < best else best
    return tuple(sorted(colour.values())), best


def census(n):
    classes = {}
    for edges in shapes(n):
        classes.setdefault(canonical(n, edges), edges)
    kept = {}
    for key, edges in classes.items():
        in_degree, out_degree = [0] * n, [0] * n
        for a, b in edges:
            out_degree[a] += 1
            in_degree[b] += 1
        if max(in_degree + out_degree) <= 4:
            kept[key] = tuple(sorted(zip(in_degree, out_degree)))
    by_degree, by_colour = collections.defaultdict(list), collections.defaultdict(list)
    for key, degrees in kept.items():
        by_degree[degrees].append(key)
        by_colour[key[0]].append(key)
    unseparated = [group for group in by_colour.values() if len(group) > 1]
    # The most self-maps any kept shape has = the most valid answers a correspondence between two copies of it can
    # have. Checker v2 refuses above 64 (`MAX_ADMISSIBLE_ANSWERS`), so this says whether that cap can bind here.
    most_self_maps = max(sum(1 for order in itertools.permutations(range(n))
                             if {(order[a], order[b]) for a, b in classes[key]} == set(classes[key]))
                         for key in kept)
    return {"nodes": n, "weakly_connected_classes": len(classes), "classes_with_every_degree_at_most_4": len(kept),
            "most_self_maps_of_any_kept_shape": most_self_maps,
            "degree_colliding_classes": sum(len(group) for group in by_degree.values() if len(group) > 1),
            "same_degree_non_isomorphic_pairs": sum(len(g) * (len(g) - 1) // 2 for g in by_degree.values()),
            "pairs_colour_refinement_cannot_separate": sum(len(g) * (len(g) - 1) // 2 for g in unseparated),
            "boundary": "necessary condition for structure reading; not sufficient; no model involved"}


if __name__ == "__main__":
    for count in (5, 6):
        print(json.dumps(census(count), sort_keys=True))
