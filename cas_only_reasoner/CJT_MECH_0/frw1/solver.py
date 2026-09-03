"""Exact belief-state search for FRW-1 -- the M8 ceiling and the engine of kill gate K1.

The world is deterministic given the true fault set F, so a belief is the SET of fault sets still
consistent with everything observed. Every action partitions that set. The value of a belief is
the maximum, over actions, of the expected probability of a verified success within the budget,
with the prior uniform over the fault sets the solver is told to consider. Memoised over
(belief, budget).

Control-plane work: pure python enumeration, no model, no GPU.
"""
from __future__ import annotations

from functools import lru_cache

from .world import (K, A_ABSTAIN, A_EXECUTE, CODE_NOT_A_FAULT, CODE_PREREQ, CODE_VIOLATION, V_OFF_AXIS,
                    V_OPPOSITE, WorldInstance, a_fix, a_probe, all_fault_sets)


class ExactSolver:
    def __init__(self, inst: WorldInstance, prior_sets=None):
        self.inst = inst
        self.prior = tuple(frozenset(f) for f in (prior_sets if prior_sets is not None else all_fault_sets()))
        self.parents = [tuple(p) for p in inst.parents]
        self.p = inst.policy_local
        self._value = lru_cache(maxsize=None)(self._value_impl)

    # ---- initial belief from what tick 0 reveals: the mask (policy state) and a0 (|F|)
    def initial_belief(self, F_true=None, size=None, policy_closed=None):
        if F_true is not None:
            size = len(F_true)
            policy_closed = (self.p is not None and self.p in F_true)
        S = [f for f in self.prior if len(f) == size and ((self.p is not None and self.p in f) == bool(policy_closed))]
        return frozenset(S)

    # ---- transitions: each returns a list of (probability, next_belief, terminal_success)
    def _probe(self, S, k):
        yes = frozenset(f for f in S if k in f)
        no = frozenset(f for f in S if k not in f)
        out = []
        n = len(S)
        if yes:
            out.append((len(yes) / n, yes, False))
        if no:
            out.append((len(no) / n, no, False))
        return out

    def _fix(self, S, k):
        n = len(S)
        groups = {}
        for f in S:
            if k not in f:
                key = ("nf",)
                nxt = f
            else:
                unmet = [q for q in self.parents[k] if q in f]
                if unmet:
                    key = ("pre", min(unmet))
                    nxt = f
                else:
                    key = ("ok",)
                    nxt = f - {k}
            groups.setdefault(key, []).append(nxt)
        return [(len(v) / n, frozenset(v), False) for v in groups.values()]

    def _execute(self, S):
        n = len(S)
        empty = [f for f in S if not f]
        rest = [f for f in S if f]
        out = []
        if empty:
            out.append((len(empty) / n, frozenset(), True))
        if rest:
            out.append((len(rest) / n, frozenset(rest), False))     # verdict adds nothing new: policy state already known
        return out

    def _value_impl(self, S: frozenset, b: int) -> float:
        if not S:
            return 0.0
        best = 0.0
        for a, outcomes, cost in self._options(S, b):
            v = 0.0
            for prob, S2, term in outcomes:
                v += prob * (1.0 if term else self._value(S2, b - cost))
            if v > best:
                best = v
        return best

    def _options(self, S, b):
        """Affordable actions with their outcome distributions. Violations and no-information moves are
        never optimal and are skipped; abstain has value 0 and is implicit."""
        policy_closed = any(self.p is not None and self.p in f for f in S) and all(self.p in f for f in S if f)
        opts = []
        if b >= 1:
            opts.append((A_EXECUTE, self._execute(S), 1))
        for k in range(K):
            c = self.inst.probe_cost[k]
            if c <= b:
                o = self._probe(S, k)
                if len(o) > 1:
                    opts.append((a_probe(k), o, c))
            d = self.inst.fix_cost[k]
            if d <= b and not (policy_closed and self.p is not None and k != self.p):
                o = self._fix(S, k)
                if not (len(o) == 1 and o[0][1] == S):
                    opts.append((a_fix(k), o, d))
        return opts

    def value(self, S, b) -> float:
        return self._value(frozenset(S), int(b))

    def best_action(self, S, b) -> int:
        S = frozenset(S)
        best_a, best_v = A_ABSTAIN, 0.0
        for a, outcomes, cost in self._options(S, b):
            v = sum(prob * (1.0 if term else self._value(S2, b - cost)) for prob, S2, term in outcomes)
            if v > best_v + 1e-12 or (abs(v - best_v) <= 1e-12 and a < best_a and best_v > 0):
                best_a, best_v = a, v
        return best_a


class BeliefTracker:
    """Runtime belief update from the environment's step info, used by the M8 arm."""

    def __init__(self, solver: ExactSolver):
        self.s = solver

    def reset(self, F_true):
        self.S = self.s.initial_belief(F_true=F_true)
        return self.S

    def update(self, action: int, info: dict):
        S = self.S
        if action == A_ABSTAIN:
            return self.S
        if action == A_EXECUTE:
            v = info.get("verdict")
            if v in (V_OFF_AXIS, V_OPPOSITE):
                self.S = frozenset(f for f in S if f)
        elif action < K:
            k = action
            fault = info.get("probe_fault")
            self.S = frozenset(f for f in S if (k in f) == bool(fault))
        else:
            k = action - K
            code = info.get("code")
            if code == CODE_NOT_A_FAULT:
                self.S = frozenset(f for f in S if k not in f)
            elif code == CODE_PREREQ:
                named = info.get("named")
                self.S = frozenset(f for f in S if k in f and [q for q in self.s.parents[k] if q in f]
                                   and min(q for q in self.s.parents[k] if q in f) == named)
            elif code == CODE_VIOLATION:
                pass
            else:                                                 # success
                self.S = frozenset(f - {k} for f in S if k in f and not [q for q in self.s.parents[k] if q in f])
        return self.S
