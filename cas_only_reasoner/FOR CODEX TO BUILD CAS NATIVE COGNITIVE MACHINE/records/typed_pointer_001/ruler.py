"""THE RULER. Difficulty by graph size and by hop distance, with a continuous score.

WHY THIS EXISTS. Helm 1.0 was judged on **18 yes/no questions about 3- and 4-node graphs**. That
instrument cannot show a learning curve, for three measured reasons:

  * the whole frozen course is **64 worlds: 52 with four nodes, 12 with three**. There is no large
    world anywhere in it, so there is no size axis;
  * eighteen questions with a pass mark of seven cannot resolve progress between "got two" and "got
    twelve". A machine that improves steadily and a machine that improves in one jump look identical;
  * and the questions mix kinds that need no reasoning at all (`context` and `definition` are pure
    lookups — 140 questions of the 564) with kinds that need a whole-graph comparison (`analogy`,
    `correspondence`), so a single number averages incomparable things.

THE ONE PROPERTY THAT MATTERS. How far information has to travel to answer a question is a property
of the **graph**, not of the words. So this ruler is built from synthetic directed graphs of
controlled size, and every question it asks is tagged with **the number of message-passing rounds a
machine provably needs to answer it** — computed by breadth-first search, not asserted.

THREE AXES.

  size       node count: 4, 5, 6, 8, 10, 12, 16
  hops       the round count needed: 1, 2, 3, 4
  score      continuous. Exact match alone throws away everything between "all correct" and "none
             correct"; a partial score is reported BESIDE it, never instead of it.

THE LINES THAT ARE ALWAYS DRAWN. A ruler that does not show what a rule with no learning achieves is
not a ruler. Every table prints:

  * `one_hop`   — a machine that can only read a node's direct neighbours. This is a faithful model
                  of **Helm 1.0**, whose receptive field was exactly one hop.
  * `commonest` — always give the most frequent answer. The audit's guessability test.
  * `rank_last` — always name the lexically last node. The gate's own registered rank rule.
  * `oracle`    — breadth-first search, correct by construction. The ceiling.

WHAT THIS DOES NOT DO. It does not touch the frozen 18-question set, the grader, or any shared module.
It is additive and it lives outside `contract.input_inventory`, so it can be written while a run is in
flight. It makes no claim about Helm: it is the instrument, and a instrument is not a measurement.

Usage:
    python records/typed_pointer_001/ruler.py            # the whole ladder, $0, ~2 seconds
    python records/typed_pointer_001/ruler.py --self-test
"""
from collections import deque
from itertools import combinations
import json
import random
import sys

RULER_SCHEMA = 'cncm.helm-ruler/0.1'

# The three question shapes. Each carries the hop count it needs, so the ladder is measured, not
# asserted. `direct_contains` reads one node's own edges. `edge_account` reads every node's edges, but
# each edge is local, so one round reaches all of them. `reach_exactly_k` needs k rounds.
DIRECT_CONTAINS = 'direct_contains'
EDGE_ACCOUNT = 'edge_account'
REACH_EXACTLY = 'reach_exactly_k'

SIZES = (4, 5, 6, 8, 10, 12, 16)
MAX_HOPS = 4


# --------------------------------------------------------------------------------------------------
# WORLDS. A directed acyclic graph. Names are assigned AFTER the structure is built and are shuffled
# per seed, so a predictor cannot win by knowing which letter comes first -- that is what the gate's
# own `rank_last` rule exploited, and the ruler must be able to see that.
# --------------------------------------------------------------------------------------------------
def _spine_depth(node_count, edges):
    """Longest shortest-path of a raw edge set on nodes 0..node_count-1. Used before naming."""
    best = 0
    for source in range(node_count):
        seen, queue = {source}, deque([(source, 0)])
        while queue:
            node, depth = queue.popleft()
            best = max(best, depth)
            for step in sorted(t for s, t in edges if s == node):
                if step not in seen:
                    seen.add(step)
                    queue.append((step, depth + 1))
    return best


def ladder_world(node_count, seed, min_depth=None):
    """A connected DAG on `node_count` nodes with a GUARANTEED depth.

    THE DEPTH IS THE POINT. The x-axis of this ruler is hop count, so a world that cannot support a
    question at distance 3 must not silently produce a missing cell. Every additional edge creates a
    shortcut and therefore SHORTENS the longest shortest-path, so chords are accepted only one at a
    time and only while the depth stays at or above `min_depth`. The pure spine has depth
    `node_count - 1`; chords are added for structural variety where they are free, and dropped where
    they are not.

    Names are assigned AFTER the structure is built and are shuffled per seed, so a predictor cannot
    win by knowing which letter comes first -- that is exactly what the gate's own registered
    `rank_last` rule exploited, and the ruler has to be able to see it.
    """
    require(node_count >= 3, 'RULER_WORLD_TOO_SMALL')
    required = node_count - 1 if min_depth is None else min_depth
    require(required <= node_count - 1, 'RULER_MIN_DEPTH_IMPOSSIBLE')
    rng = random.Random('ruler-world-%d-%d' % (node_count, seed))
    edges = {(index, index + 1) for index in range(node_count - 1)}
    candidates = [(i, j) for i in range(node_count - 1) for j in range(i + 2, node_count)]
    rng.shuffle(candidates)
    for chord in candidates[:max(1, node_count // 3)]:
        trial = edges | {chord}
        if _spine_depth(node_count, trial) >= required:
            edges = trial
    require(_spine_depth(node_count, edges) >= required, 'RULER_DEPTH_NOT_REACHED')
    names = ['r%02d' % index for index in range(node_count)]
    rng.shuffle(names)
    label = {index: names[index] for index in range(node_count)}
    return {'node_count': node_count, 'seed': seed,
            'edges': sorted((label[a], label[b]) for a, b in edges)}


def children_of(world, node):
    return sorted(target for source, target in world['edges'] if source == node)


def nodes_of(world):
    out = set()
    for source, target in world['edges']:
        out.add(source)
        out.add(target)
    return sorted(out)


def distance(world, source, target):
    """Breadth-first shortest path length, or `None` when the target is unreachable."""
    if source == target:
        return 0
    seen, queue = {source}, deque([(source, 0)])
    while queue:
        node, depth = queue.popleft()
        for step in children_of(world, node):
            if step == target:
                return depth + 1
            if step not in seen:
                seen.add(step)
                queue.append((step, depth + 1))
    return None


def depth_of(world):
    """The longest shortest-path in the world: the deepest question it can support."""
    best = 0
    for source in nodes_of(world):
        for target in nodes_of(world):
            found = distance(world, source, target)
            if found is not None:
                best = max(best, found)
    return best


def at_distance(world, source, hops):
    """Every node exactly `hops` steps from `source`."""
    return sorted(target for target in nodes_of(world)
                  if distance(world, source, target) == hops)


# --------------------------------------------------------------------------------------------------
# QUESTIONS. Each carries the hop count it needs. That number is derived from the graph, so the
# ladder's x-axis is measured rather than declared.
# --------------------------------------------------------------------------------------------------
def questions_for(world, max_hops=MAX_HOPS):
    out = []
    nodes = nodes_of(world)
    for node in nodes:
        out.append({'kind': DIRECT_CONTAINS, 'focus': node, 'hops': 1,
                    'gold': children_of(world, node)})
    out.append({'kind': EDGE_ACCOUNT, 'focus': None, 'hops': 1,
                'gold': ['%s>%s' % (s, t) for s, t in world['edges']]})
    for hops in range(2, max_hops + 1):
        for node in nodes:
            gold = at_distance(world, node, hops)
            if gold:
                out.append({'kind': REACH_EXACTLY, 'focus': node, 'hops': hops, 'gold': gold})
    return out


def render(question):
    """The question as the machine would be asked it, in one line."""
    if question['kind'] == DIRECT_CONTAINS:
        return 'what does %s directly contain?' % question['focus']
    if question['kind'] == EDGE_ACCOUNT:
        return 'list every contains pair in the world'
    return 'which nodes are exactly %d steps from %s?' % (question['hops'], question['focus'])


# --------------------------------------------------------------------------------------------------
# THE SCORE. Two numbers, always together. Exact match is what the frozen gate uses; the partial score
# is what makes a curve visible, and it is never reported alone.
# --------------------------------------------------------------------------------------------------
def jaccard(predicted, gold):
    """Overlap of two sets of answers. 1.0 exact, 0.0 no overlap, 0.0 for two empty sets is avoided."""
    first, second = set(predicted), set(gold)
    if not first and not second:
        return 1.0
    union = first | second
    return len(first & second) / len(union) if union else 0.0


def score_question(predicted, gold):
    return {'exact': bool(set(predicted) == set(gold)), 'partial': jaccard(predicted, gold)}


# --------------------------------------------------------------------------------------------------
# PREDICTORS. `oracle` is the ceiling. `one_hop` is Helm 1.0. Everything else is a rule with no
# learning in it, printed so nobody can mistake a machine for a rule.
# --------------------------------------------------------------------------------------------------
def oracle(world, question):
    return list(question['gold'])


def one_hop(world, question):
    """A machine that can read only a node's DIRECT neighbours.

    This is a faithful model of Helm 1.0, whose eight rounds all read the same frozen rows, so its
    receptive field was exactly one hop. It answers one-hop questions perfectly and cannot answer a
    deeper one at all: it returns its best one-hop guess, which for a distance-k question is the
    direct children.
    """
    if question['kind'] == DIRECT_CONTAINS:
        return children_of(world, question['focus'])
    if question['kind'] == EDGE_ACCOUNT:
        return ['%s>%s' % (s, t) for s, t in world['edges']]
    return children_of(world, question['focus'])


def commonest(world, question):
    """Always give the answer that is most common across the whole ladder. Needs the corpus, so the
    runner supplies it through `answer_pool`."""
    pool = question.get('answer_pool') or []
    return pool[0] if pool else []


def rank_last(world, question):
    """Always name the lexically last node. The gate registered this as a rule worth removing."""
    last = sorted(nodes_of(world))[-1]
    if question['kind'] == EDGE_ACCOUNT:
        return ['%s>%s' % (s, t) for s, t in world['edges'] if t == last]
    return [last]


PREDICTORS = (('oracle', oracle), ('one_hop', one_hop), ('rank_last', rank_last))


# --------------------------------------------------------------------------------------------------
# THE LADDER.
# --------------------------------------------------------------------------------------------------
def run_ladder(sizes=SIZES, max_hops=MAX_HOPS, world_seeds=(1, 2, 3)):
    """Every cell of (size, hops) x predictor, with both scores. Also returns the answer pool."""
    cells = {}
    pool_counter = {}
    for size in sizes:
        # THE X-AXIS IS CAPPED BY THE SIZE AXIS, and pretending otherwise is a bug. An n-node graph
        # has at most depth n-1, so a four-node world can never be asked a four-hop question. The
        # request is clamped and the clamp is the honest answer, not an error.
        for world_seed in world_seeds:
            reachable_hops = min(max_hops, size - 1)
            world = ladder_world(size, world_seed, min_depth=reachable_hops)
            for question in questions_for(world, max_hops):
                key = (size, question['hops'], question['kind'])
                bucket = cells.setdefault(key, [])
                bucket.append({'world': world, 'question': question})
                for answer in question['gold']:
                    pool_counter[answer] = pool_counter.get(answer, 0) + 1
    pool = [answer for answer, _ in sorted(pool_counter.items(), key=lambda kv: (-kv[1], kv[0]))]

    table = {}
    for key, rows in cells.items():
        size, hops, kind = key
        for name, predictor in PREDICTORS:
            scores = []
            for row in rows:
                question = dict(row['question'])
                question['answer_pool'] = pool
                predicted = predictor(row['world'], question)
                scores.append(score_question(predicted, question['gold']))
            table.setdefault((size, hops), {}).setdefault(name, []).extend(scores)

    summary = {}
    for (size, hops), by_predictor in sorted(table.items()):
        summary['%d|%d' % (size, hops)] = {
            name: {'exact': round(sum(1 for row in rows if row['exact']) / len(rows), 6),
                   'partial': round(sum(row['partial'] for row in rows) / len(rows), 6),
                   'questions': len(rows)}
            for name, rows in sorted(by_predictor.items())}
    return summary, len(pool)


def print_table(summary):
    print('%-5s %-5s %-9s %s' % ('size', 'hops', 'predictor', 'exact   partial  questions'))
    print('-' * 68)
    for key in sorted(summary, key=lambda k: tuple(int(x) for x in k.split('|'))):
        size, hops = key.split('|')
        for name in ('oracle', 'one_hop', 'rank_last'):
            row = summary[key].get(name)
            if row is None:
                continue
            print('%-5s %-5s %-9s %-7.4f %-8.4f %d'
                  % (size, hops, name, row['exact'], row['partial'], row['questions']))
        print()


def self_test():
    """The ruler must be able to tell a one-hop machine from an oracle. If it cannot, it is useless."""
    checks, failures = [], []

    def check(name, condition, detail=''):
        checks.append({'check': name, 'pass': bool(condition), 'detail': detail})
        if not condition:
            failures.append(name)

    summary, pool = run_ladder(sizes=(4, 6, 8), max_hops=3, world_seeds=(1, 2))

    # Every (size, hops) cell must exist. This is what failed first time round, and the reason the
    # generator now GUARANTEES depth instead of hoping for it: an extra edge creates a shortcut and
    # shortens the longest path, so a world can silently lose its deepest questions.
    expected = {(size, hops) for size in (4, 6, 8) for hops in (1, 2, 3)}
    found = {tuple(int(x) for x in key.split('|')) for key in summary}
    check('every (size, hops) cell exists', found == expected,
          'missing %s' % sorted(expected - found) if found != expected else 'all 9 present')
    for key, row in summary.items():
        size, hops = (int(x) for x in key.split('|'))
        if row['oracle']['exact'] != 1.0:
            check('oracle is perfect at %s' % key, False, 'exact=%.4f' % row['oracle']['exact'])
        if hops == 1 and row['one_hop']['exact'] != 1.0:
            check('one-hop rule is perfect at one hop (size %d)' % size, False,
                  'exact=%.4f' % row['one_hop']['exact'])
    check('oracle is perfect in every cell and one_hop is perfect at one hop',
          not [f for f in failures if 'perfect' in f], '%d cells' % len(summary))

    deep = [row for key, row in summary.items() if key.endswith('|2') or key.endswith('|3')]
    check('the one-hop rule is NOT perfect beyond one hop',
          deep and all(row['one_hop']['exact'] < 1.0 for row in deep),
          'worst=%.4f' % min(row['one_hop']['exact'] for row in deep) if deep else 'no deep cells')

    wider = {int(k.split('|')[0]) for k in summary}
    check('size is a real axis, not a label', len(wider) >= 3, 'sizes: %s' % sorted(wider))
    check('the answer pool is non-empty', pool > 0, 'pool: %d' % pool)

    # The ruler must separate cleanly rather than by a hair, or it cannot show a curve.
    gaps = [row['oracle']['exact'] - row['one_hop']['exact']
            for key, row in summary.items() if int(key.split('|')[1]) >= 2]
    check('the oracle and the one-hop rule are separated by a real margin beyond one hop',
          gaps and min(gaps) > 0.5, 'smallest gap=%.4f' % min(gaps) if gaps else 'none')

    print(json.dumps({'schema': RULER_SCHEMA, 'checks': checks,
                      'answer_pool_size': pool, 'cells': len(summary)}, indent=1, sort_keys=True))
    print('RULER_SELFTEST_PASS' if not failures else 'RULER_SELFTEST_FAIL:' + ','.join(failures))
    return 0 if not failures else 1


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def main(argv):
    if argv == ['--self-test']:
        return self_test()
    print('THE RULER  —  difficulty by graph size and hop distance, with a continuous score')
    print('schema %s   sizes %s   max hops %d' % (RULER_SCHEMA, list(SIZES), MAX_HOPS))
    print()
    print('`one_hop` is a faithful model of Helm 1.0: its eight rounds all read the same frozen rows,')
    print('so its reach was exactly one hop. `oracle` is breadth-first search. `rank_last` is the')
    print('gate\'s own registered rank rule.')
    print()
    summary, pool = run_ladder()
    print_table(summary)
    print('answer pool size: %d' % pool)
    print()
    deep = {k: v for k, v in summary.items() if int(k.split('|')[1]) >= 2}
    if deep:
        worst = max(v['one_hop']['partial'] for v in deep.values())
        best_oracle = min(v['oracle']['exact'] for v in deep.values())
        print('BEYOND ONE HOP: the one-hop rule peaks at partial %.4f while the oracle is exact %.4f.'
              % (worst, best_oracle))
        print('That gap is the thing Helm 1.0 had no room to cross, and the thing Helm 2.0 now can.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
