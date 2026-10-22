"""cube_task/mix.py -- the frozen batch mixing (pre-code §7: SDG cube : AI-written : CAS-record = 6 : 1 : 3). Stdlib.

Each batch takes an exact count from each pool (largest-remainder split of the batch size); within a pool rows are
drawn in shuffled passes (every row once before any repeats), so small pools are covered evenly. Deterministic in
the seed.
"""
from __future__ import annotations

import random
from typing import Dict, List, Tuple


def split_counts(batch: int, ratio: Dict[str, int]) -> Dict[str, int]:
    total = sum(ratio.values())
    out = {k: batch * v // total for k, v in ratio.items()}          # whole numbers: no floating-point remainders
    rem = {k: batch * v % total for k, v in ratio.items()}
    left = batch - sum(out.values())
    for k in sorted(ratio, key=lambda k: (-rem[k], -ratio[k], k))[:left]:   # ties: the larger share
        out[k] += 1
    return out


def batch_plan(steps: int, batch: int, pools: Dict[str, int], ratio: Dict[str, int],
               seed: int) -> List[List[Tuple[str, int]]]:
    rng = random.Random(seed)
    counts = split_counts(batch, ratio)
    queues: Dict[str, List[int]] = {k: [] for k in pools}

    def take(k: str) -> int:
        if not queues[k]:
            order = list(range(pools[k]))
            rng.shuffle(order)
            queues[k] = order
        return queues[k].pop()

    plan = []
    for _ in range(steps):
        b = [(k, take(k)) for k in sorted(counts) for _ in range(counts[k])]
        rng.shuffle(b)
        plan.append(b)
    return plan
