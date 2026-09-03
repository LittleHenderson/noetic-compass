"""FRW-1 -- the FAULT-RECOVERY WORLD family for CJT-MECH-0 (design v0.2 section 3).

Plain English: a task is stuck because one to three hidden faults are active. The controller
cannot see which. Each tick it may PROBE one fault class (pay to look), FIX one class (pay to
repair; it only works if that class's prerequisites are already clear), EXECUTE (attempt the task;
a verifier answers with a coarse verdict), or ABSTAIN. Budget is limited so probing everything is
unaffordable. Order matters: fixing before the prerequisite is clear wastes the fix and returns
only a prerequisite code.

Everything in this file is deterministic given seeds. No model, no learning, no GPU. Every arm
of the bench receives the identical observation vector produced by Env.obs().

Authorization: OWNER_AUTHORIZATION_20260903_BUILD_AND_RUN.md.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass, field, asdict

import numpy as np

REGISTRY = ["GOAL_UNCLEAR", "KNOWLEDGE_MISSING", "RESOURCE_SHORT", "POLICY_CLOSED",
            "MEMORY_STALE", "TOOL_BROKEN", "CONTEXT_MISMATCH", "PREREQ_UNMET"]
POLICY_REGISTRY_ID = REGISTRY.index("POLICY_CLOSED")
K = 6                                   # active classes per world instance
N_ACTIONS = 2 * K + 2                   # probe(k) = k, fix(k) = K + k, execute = 2K, abstain = 2K + 1
A_EXECUTE, A_ABSTAIN = 2 * K, 2 * K + 1
FAULT_SIZES = (1, 2, 3)
T_MAX = 24                              # safety cap on ticks per episode
RECOVERY_WINDOW = 3                     # "next-tick recovery": success within this many ticks of first feedback

# observation codes
OBS_UNKNOWN, OBS_CLEAR, OBS_FAULT = 0, 1, 2
CODE_NONE, CODE_PREREQ, CODE_NOT_A_FAULT, CODE_VIOLATION = 0, 1, 2, 3
V_NONE, V_INTENDED, V_OFF_AXIS, V_OPPOSITE, V_UNASSESSED = 0, 1, 2, 3, 4
SLOT_DIM = 3 + 1 + 1 + 1 + 1 + 4 + K    # o(3) c d m n e(4) named-prereq(K)
GLOBAL_DIM = 1 + 1 + 5 + 1               # budget_frac, tick_frac, last verdict(5), a0
OBS_DIM = K * SLOT_DIM + GLOBAL_DIM


def a_probe(k: int) -> int:
    return k


def a_fix(k: int) -> int:
    return K + k


@dataclass
class WorldInstance:
    world_id: int
    classes: list                      # registry ids of the 6 active classes (local index -> registry id)
    probe_cost: list                   # c_k, ints
    fix_cost: list                     # d_k, ints
    parents: list                      # parents[k] = sorted list of local indices that must be clear before fix(k) works
    structureless: bool = False        # the negative-control twin: no DAG, free probes, faults visible at reset

    @property
    def policy_local(self):
        return self.classes.index(POLICY_REGISTRY_ID) if POLICY_REGISTRY_ID in self.classes else None

    @property
    def budget(self) -> int:
        # depends on the instance only, never on the fault set (must not leak |F|)
        if self.structureless:
            return int(sum(self.fix_cost)) + 1
        return int(round(0.6 * sum(self.probe_cost))) + 3 * int(np.median(self.fix_cost))

    @property
    def n_edges(self) -> int:
        return sum(len(p) for p in self.parents)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "WorldInstance":
        return WorldInstance(**d)


def draw_instance(rng: np.random.Generator, world_id: int, structureless: bool = False) -> WorldInstance:
    """Draw one world instance from the registry. Same rng stream -> same instance."""
    classes = sorted(int(x) for x in rng.choice(len(REGISTRY), K, replace=False))
    probe_cost = [int(x) for x in rng.integers(1, 5, K)]        # 1..4
    fix_cost = [int(x) for x in rng.integers(2, 7, K)]          # 2..6
    if structureless:
        return WorldInstance(world_id, classes, [0] * K, fix_cost, [[] for _ in range(K)], True)
    while True:                                                 # DAG: 3..6 edges, <= 2 parents per node, acyclic
        order = [int(x) for x in rng.permutation(K)]
        parents = [[] for _ in range(K)]
        for pos in range(1, K):
            node = order[pos]
            n_par = int(rng.choice([0, 1, 1, 2], p=[0.3, 0.3, 0.2, 0.2]))
            if n_par:
                cands = order[:pos]
                pick = rng.choice(len(cands), min(n_par, len(cands)), replace=False)
                parents[node] = sorted(int(cands[i]) for i in pick)
        # the policy class must be fixable first (its mask blocks every other fix), so it has no prerequisites
        if POLICY_REGISTRY_ID in classes:
            parents[classes.index(POLICY_REGISTRY_ID)] = []
        n_edges = sum(len(p) for p in parents)
        if 3 <= n_edges <= 6:
            return WorldInstance(world_id, classes, probe_cost, fix_cost, parents, False)


def all_fault_sets(sizes=FAULT_SIZES):
    out = []
    for s in sizes:
        out.extend(frozenset(c) for c in itertools.combinations(range(K), s))
    return out


def split_fault_sets(rng: np.random.Generator):
    """Train: all singletons + half of the pairs. Held-out: the other pairs + all triples."""
    singles = [f for f in all_fault_sets((1,))]
    pairs = [f for f in all_fault_sets((2,))]
    triples = [f for f in all_fault_sets((3,))]
    perm = rng.permutation(len(pairs))
    half = len(pairs) // 2
    train_pairs = [pairs[i] for i in perm[:half]]
    held_pairs = [pairs[i] for i in perm[half:]]
    return {"train": singles + train_pairs, "heldout": held_pairs + triples}


class Env:
    """Deterministic environment. One instance, one episode at a time."""

    def __init__(self, inst: WorldInstance):
        self.inst = inst

    def reset(self, F):
        self.F = set(int(k) for k in F)
        self.size0 = len(self.F)
        self.o = [OBS_UNKNOWN] * K
        self.n = [0] * K
        self.e = [CODE_NONE] * K
        self.e_named = [-1] * K
        self.b = self.inst.budget
        self.t = 0
        self.last_v = V_NONE
        self.done = False
        self.success = False
        self.violations = 0
        self.wrong_actions = 0
        self.probes = 0
        self.fixes = 0
        self.first_feedback_tick = None
        self.success_tick = None
        self.trace = []
        if self.inst.structureless:                      # twin: faults visible, nothing hidden
            self.o = [OBS_FAULT if k in self.F else OBS_CLEAR for k in range(K)]
        return self.obs()

    # ---- what every arm sees
    def mask(self):
        p = self.inst.policy_local
        if p is not None and p in self.F:
            m = [0] * K
            m[p] = 1
            return m
        return [1] * K

    def a0(self) -> float:
        """Tick-0 activation: a function of the NUMBER of active faults only. Equal-size fault sets
        collide exactly (bit-identical). Visible to every arm."""
        return float(self.size0) / 3.0

    def obs(self) -> np.ndarray:
        m = self.mask()
        v = np.zeros(OBS_DIM, dtype=np.float32)
        for k in range(K):
            base = k * SLOT_DIM
            v[base + self.o[k]] = 1.0
            v[base + 3] = self.inst.probe_cost[k] / 4.0
            v[base + 4] = self.inst.fix_cost[k] / 6.0
            v[base + 5] = float(m[k])
            v[base + 6] = min(self.n[k], 3) / 3.0
            v[base + 7 + self.e[k]] = 1.0
            if self.e_named[k] >= 0:
                v[base + 11 + self.e_named[k]] = 1.0
        g = K * SLOT_DIM
        v[g] = self.b / max(1, self.inst.budget)
        v[g + 1] = self.t / T_MAX
        v[g + 2 + self.last_v] = 1.0
        v[g + 7] = self.a0()
        return v

    # ---- dynamics
    def _end(self, verdict, success=False):
        self.done = True
        self.success = success
        self.last_v = verdict
        if success:
            self.success_tick = self.t

    def _note_feedback(self):
        if self.first_feedback_tick is None:
            self.first_feedback_tick = self.t

    def step(self, a: int):
        """Returns (obs, reward, done, info). Reward is 1.0 on verified success, else 0.0."""
        assert not self.done, "episode is over"
        assert 0 <= a < N_ACTIONS
        self.t += 1
        info = {"action": int(a), "code": CODE_NONE, "verdict": V_NONE, "cost": 0}
        if a == A_ABSTAIN:
            self._end(V_UNASSESSED)
            info["verdict"] = V_UNASSESSED
        elif a == A_EXECUTE:
            cost = 1
            if cost > self.b:
                self._end(V_UNASSESSED)
            else:
                self.b -= cost
                info["cost"] = cost
                if not self.F:
                    self._end(V_INTENDED, success=True)
                    info["verdict"] = V_INTENDED
                else:
                    self.wrong_actions += 1
                    p = self.inst.policy_local
                    verdict = V_OPPOSITE if (p is not None and p in self.F) else V_OFF_AXIS
                    if verdict == V_OPPOSITE:
                        self.violations += 1
                    self.last_v = verdict
                    info["verdict"] = verdict
                    self._note_feedback()
        elif a < K:                                      # probe(k)
            k = a
            cost = self.inst.probe_cost[k]
            if cost > self.b:
                self._end(V_UNASSESSED)
            else:
                self.b -= cost
                self.probes += 1
                info["cost"] = cost
                info["probe_fault"] = bool(k in self.F)
                self.o[k] = OBS_FAULT if k in self.F else OBS_CLEAR
        else:                                            # fix(k)
            k = a - K
            cost = self.inst.fix_cost[k]
            if cost > self.b:
                self._end(V_UNASSESSED)
            else:
                self.b -= cost
                self.fixes += 1
                info["cost"] = cost
                m = self.mask()
                if m[k] == 0:                            # policy closed: fixing anything else is a violation
                    self.violations += 1
                    self.wrong_actions += 1
                    self.n[k] += 1
                    self.e[k] = CODE_VIOLATION
                    self.e_named[k] = -1
                    info["code"] = CODE_VIOLATION
                    self._note_feedback()
                elif k not in self.F:
                    self.wrong_actions += 1
                    self.n[k] += 1
                    self.e[k] = CODE_NOT_A_FAULT
                    self.e_named[k] = -1
                    self.o[k] = OBS_CLEAR
                    info["code"] = CODE_NOT_A_FAULT
                    self._note_feedback()
                else:
                    unmet = [p for p in self.inst.parents[k] if p in self.F]
                    if unmet:
                        self.wrong_actions += 1
                        self.n[k] += 1
                        self.e[k] = CODE_PREREQ
                        self.e_named[k] = min(unmet)
                        info["code"] = CODE_PREREQ
                        info["named"] = min(unmet)
                        self._note_feedback()
                    else:
                        self.F.discard(k)
                        self.o[k] = OBS_CLEAR
                        self.e[k] = CODE_NONE
                        self.e_named[k] = -1
        if not self.done and (self.t >= T_MAX or self.b <= 0):
            self._end(V_UNASSESSED)
        self.trace.append(info)
        reward = 1.0 if (self.done and self.success) else 0.0
        return self.obs(), reward, self.done, info

    # ---- outcome record for the status program
    def outcome(self) -> dict:
        rec_next = bool(self.success and self.first_feedback_tick is not None
                        and self.success_tick - self.first_feedback_tick <= RECOVERY_WINDOW)
        return {"success": bool(self.success), "next_tick_recovery": rec_next,
                "had_feedback": self.first_feedback_tick is not None, "ticks": self.t,
                "budget_left": self.b, "probes": self.probes, "fixes": self.fixes,
                "wrong_actions": self.wrong_actions, "violations": self.violations, "size0": self.size0}


# ---- dataset: worlds + episodes with separate seed streams and an identity assertion
def build_dataset(registry_seed: int, n_train_worlds: int, n_heldout_worlds: int, split_seed: int) -> dict:
    """Train worlds carry train fault sets AND held-out fault sets (the latter never trained on);
    held-out worlds are new DAGs never seen in training. Separate seed streams for each part."""
    rng_w = np.random.default_rng(registry_seed)
    rng_h = np.random.default_rng(registry_seed + 7_000_000)
    rng_s = np.random.default_rng(split_seed)
    train_worlds = [draw_instance(rng_w, i) for i in range(n_train_worlds)]
    held_worlds = [draw_instance(rng_h, 1000 + i) for i in range(n_heldout_worlds)]
    twin_worlds = [draw_instance(np.random.default_rng(registry_seed + 9_000_000 + i), 2000 + i, structureless=True)
                   for i in range(max(2, n_train_worlds // 4))]
    split = split_fault_sets(rng_s)
    train_eps = [(w.world_id, sorted(F)) for w in train_worlds for F in split["train"]]
    held_eps = [(w.world_id, sorted(F)) for w in train_worlds for F in split["heldout"]]
    held_eps += [(w.world_id, sorted(F)) for w in held_worlds for F in all_fault_sets()]
    twin_eps = [(w.world_id, sorted(F)) for w in twin_worlds for F in all_fault_sets()]
    key = lambda e: (e[0], tuple(e[1]))
    assert not (set(map(key, train_eps)) & set(map(key, held_eps))), "HELD-OUT IDENTITY: overlap with training"
    ds = {"registry_seed": registry_seed, "split_seed": split_seed,
          "worlds": {str(w.world_id): w.to_dict() for w in train_worlds + held_worlds + twin_worlds},
          "train_episodes": train_eps, "heldout_episodes": held_eps, "twin_episodes": twin_eps}
    ds["digests"] = {"train": _digest(train_eps), "heldout": _digest(held_eps), "twin": _digest(twin_eps),
                     "worlds": _digest(ds["worlds"])}
    return ds


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def instance_from(ds: dict, world_id: int) -> WorldInstance:
    return WorldInstance.from_dict(ds["worlds"][str(world_id)])


if __name__ == "__main__":
    ds = build_dataset(20260903, 20, 2, 424242)
    print("worlds", len(ds["worlds"]), "train eps", len(ds["train_episodes"]),
          "heldout eps", len(ds["heldout_episodes"]), "twin eps", len(ds["twin_episodes"]))
    print("digests", ds["digests"])
    w = instance_from(ds, 0)
    print("world 0:", w.to_dict(), "budget", w.budget)
