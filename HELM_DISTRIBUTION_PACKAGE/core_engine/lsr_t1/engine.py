"""LSR-T1 engine: the Lacunarity-SDG-Recipe loop, built from lacunarity_oscillator_design_v1.

Built 2026-10-14 from ARCHITECTURE.md, CONVERGENCE.md and lsr_sketch.py. Standard library only.
Builder decisions where the design was silent or self-inconsistent are listed in FROZEN.json
("builder_decisions"); none of them changes a mark.

Exactness: recipe coefficients, efficiency and capacity are exact Fractions of the stored binary64
data (witnessed ratio). Loop-internal tolerance decisions (|ln(y/yhat)| <= tau) evaluate the exact
coefficients in binary64, as the design's tau itself is a float (math.log). Every REPORTED metric
(explained fractions, held-out accuracy, NMAE) is computed exactly with Fractions.

Clarification 10: several recipes for one Omega are CO-PRESENT (`+`). The readout (EXCLUSIVE max or
POOLED parallel production) is a separate declared rule, never `x`. render_memory() never emits `x`.
The leakage symbol is never used for any row or cell state.
"""
from __future__ import annotations

import itertools
import math
import time
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------- frozen constants (CONVERGENCE.md s.1)
S_MIN = 8
BREAK_ALLOWANCE = 1
HOLDOUT_ALLOWANCE = 1
P_MAX = 6
C_MAX = 8
T_ASSIGN = 4
COEF_BOUNDS = (Fraction(1, 20), Fraction(20))
TAU_LADDER = [math.log(v) for v in (1.5, 1.4, 1.3, 1.2, 1.1, 1.05)]
SHAPED_FLOOR = Fraction(4, 5)
ABS_FLOOR = 0.02

# row / cell states (same vocabulary as lacunarity_machine_v1.universe)
COVERED, NO_EVIDENCE, LACUNA, FADED = "COVERED", "NO_EVIDENCE", "LACUNA", "FADED"
SINGLE, EXCLUSIVE, POOLED = "SINGLE", "EXCLUSIVE", "POOLED"
SDG_ATTESTED_SHAPE, LOOP_EXTENSION = "SDG_ATTESTED_SHAPE", "LOOP_EXTENSION"
K_DROP, K_SUBSET, K_EFF, K_CAP, K_MODE, K_LINES = ("ALT_RECIPE_DROP_CELL", "ALT_RECIPE_SUBSET", "EFFICIENCY_TERM",
                                                  "CAPACITY_TERM", "READOUT_MODE", "POOLED_LINES")
H_COMPLETE = "COVERAGE_COMPLETE"
H_BUDGET = "BUDGET_EXHAUSTED"
H_SHAPED = "RECIPE_SHAPED_RESIDUAL_CARRIED"
H_KNOW = "KNOWLEDGE_MISSING"
H_NOT = "NOT_RECIPE_SHAPED"
H_NOISE = "NOISE_LIMITED_RESIDUAL_CARRIED"


# ---------------------------------------------------------------- data
@dataclass(frozen=True)
class Row:
    row_id: str
    xf: Tuple[float, ...]
    yf: float
    xF: Tuple[Fraction, ...]
    yF: Fraction
    ratio: Optional[Tuple[Fraction, ...]]   # exact x_i / y (None when y == 0)

    @staticmethod
    def make(row_id, x, y):
        xF = tuple(Fraction(v) for v in x)
        yF = Fraction(y)
        ratio = tuple(v / yF for v in xF) if yF > 0 else None
        return Row(row_id, tuple(float(v) for v in x), float(y), xF, yF, ratio)


@dataclass(frozen=True)
class Recipe:
    cells: FrozenSet[int]
    a: Tuple[Tuple[int, Fraction], ...]      # sorted (cell, exact requirement)

    @property
    def amap(self):
        return dict(self.a)

    @property
    def af(self):
        return tuple((i, float(v)) for i, v in self.a)

    def yield_f(self, x):
        return min(x[i] / v for i, v in self.af)

    def yield_x(self, x):
        return min(x[i] / v for i, v in self.a)

    def limiting(self, x):
        return min(self.af, key=lambda iv: (x[iv[0]] / iv[1], iv[0]))[0]


def make_recipe(cells, amap):
    return Recipe(frozenset(cells), tuple(sorted((i, Fraction(amap[i])) for i in cells)))


@dataclass
class Memory:
    omega: str
    recipes: List[Recipe]
    readout: str = SINGLE
    eta: Fraction = Fraction(1)
    capacity: Optional[Fraction] = None
    revision: int = 0

    def copy(self, **kw):
        d = dict(omega=self.omega, recipes=list(self.recipes), readout=self.readout, eta=self.eta,
                 capacity=self.capacity, revision=self.revision + 1)
        d.update(kw)
        return Memory(**d)


# ---------------------------------------------------------------- readouts
def _solve(matrix, rhs):
    n = len(rhs)
    m = [list(row) + [b] for row, b in zip(matrix, rhs)]
    for c in range(n):
        p = None
        for r in range(c, n):
            if m[r][c] != 0:
                p = r
                break
        if p is None:
            return None
        m[c], m[p] = m[p], m[c]
        for r in range(n):
            if r != c and m[r][c] != 0:
                f = m[r][c] / m[c][c]
                m[r] = [u - f * v for u, v in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def pooled_lp(recipes, x, exact):
    """max sum_k y_k s.t. sum_k a_ki y_k <= x_i, y >= 0. Vertex enumeration (sketch). Fast path:
    single-cell lines on disjoint cells -> sum of x_i / a_i (the LP optimum, ARCHITECTURE s.8 claim 3)."""
    zero = Fraction(0) if exact else 0.0
    if not recipes:
        return zero
    maps = [r.amap if exact else dict(r.af) for r in recipes]
    if all(len(r.cells) == 1 for r in recipes) and len({next(iter(r.cells)) for r in recipes}) == len(recipes):
        return sum(x[next(iter(r.cells))] / maps[k][next(iter(r.cells))] for k, r in enumerate(recipes))
    tol = 0 if exact else 1e-12
    cells = sorted(set().union(*[r.cells for r in recipes]))
    best = zero
    for k in range(1, len(recipes) + 1):
        for support in itertools.combinations(range(len(recipes)), k):
            for binding in itertools.combinations(cells, k):
                matrix = [[maps[j].get(i, zero) for j in support] for i in binding]
                sol = _solve(matrix, [x[i] for i in binding])
                if sol is None or any(v < -tol for v in sol):
                    continue
                ok = True
                for i in cells:
                    used = sum(maps[j].get(i, zero) * v for j, v in zip(support, sol))
                    if used > x[i] + tol * (1 + abs(x[i])):
                        ok = False
                        break
                if ok:
                    s = sum(sol)
                    if s > best:
                        best = s
    return best


def predict(mem, row, exact=False):
    x = row.xF if exact else row.xf
    if not mem.recipes:
        return Fraction(0) if exact else 0.0
    if mem.readout == POOLED:
        y = pooled_lp(mem.recipes, x, exact)
    elif exact:
        y = max(r.yield_x(x) for r in mem.recipes)
    else:
        y = max(r.yield_f(x) for r in mem.recipes)
    y = y * (mem.eta if exact else float(mem.eta))
    if mem.capacity is not None:
        cap = mem.capacity if exact else float(mem.capacity)
        y = min(y, cap)
    return y


def explained(y, yhat, tau):
    if y == 0 or yhat <= 0:
        return abs(y - yhat) <= ABS_FLOOR
    return abs(math.log(y / yhat)) <= tau


# ---------------------------------------------------------------- READ
def tau_index_for(mem, rows, previous):
    logs = []
    for r in rows:
        p = predict(mem, r)
        if r.yf > 0 and p > 0:
            logs.append(abs(math.log(r.yf / p)))
    if not logs:
        return previous
    logs.sort()
    med = logs[len(logs) // 2]
    mad = sorted(abs(v - med) for v in logs)[len(logs) // 2]
    want = max(TAU_LADDER[-1], 3 * 1.4826 * mad)
    idx = 0
    for i, t in enumerate(TAU_LADDER):
        if t >= want:
            idx = i
    return max(idx, previous)


@dataclass(frozen=True)
class Deficit:
    row_id: str
    sign: int
    limiting: Optional[int]
    pressure: Tuple[bool, ...]     # m_i > 0 per cell ("how much of what is missing" is m_i = a_i*y - x_i)


@dataclass
class ReadReceipt:
    omega: str
    tau_index: int
    row_states: Dict[str, str]
    cell_states: Dict[int, str]
    residual: Tuple[str, ...]
    deficits: Tuple[Deficit, ...]
    lacuna_pressure: Dict[int, int]
    structured: bool
    explained_fraction: Fraction


def deficit(mem, row, tau):
    yhat = predict(mem, row)
    n = len(row.xf)
    if explained(row.yf, yhat, tau):
        lim = max(mem.recipes, key=lambda q: q.yield_f(row.xf)).limiting(row.xf) if mem.recipes else None
        return Deficit(row.row_id, 0, lim, tuple(False for _ in range(n)))
    base = max(mem.recipes, key=lambda q: q.yield_f(row.xf)) if mem.recipes else None
    if base is None:
        return Deficit(row.row_id, 1 if row.yf > yhat else -1, None, tuple(False for _ in range(n)))
    am = dict(base.af)
    m = tuple((i in am) and (am[i] * row.yf - row.xf[i] > 0) for i in range(n))
    return Deficit(row.row_id, 1 if row.yf > yhat else -1, base.limiting(row.xf), m)


def structured(deficits):
    by_cell = {}
    for d in deficits:
        if d.sign != 0 and d.limiting is not None:
            by_cell.setdefault(d.limiting, []).append(d.sign)
    for signs in by_cell.values():
        for s in (1, -1):
            same = signs.count(s)
            if same >= S_MIN and Fraction(same, len(signs)) >= Fraction(4, 5):
                return True
    return False


def read(mem, rows, charged, tau_index):
    tau = TAU_LADDER[tau_index]
    deficits = tuple(deficit(mem, r, tau) for r in rows)
    states = {}
    for d in deficits:
        states[d.row_id] = COVERED if d.sign == 0 else (FADED if charged.get(d.row_id) else LACUNA)
    residual = tuple(d.row_id for d in deficits if d.sign != 0)
    n_cells = len(rows[0].xf) if rows else 0
    pressure = {i: sum(1 for d in deficits if d.sign != 0 and d.pressure[i]) for i in range(n_cells)}
    used = set().union(*[r.cells for r in mem.recipes]) if mem.recipes else set()
    witnessed = {d.limiting for d in deficits if d.sign == 0 and d.limiting is not None}
    cells = {}
    for i in range(n_cells):
        if i in used and i in witnessed:
            cells[i] = COVERED
        elif pressure[i] > 0 and i not in used:
            cells[i] = LACUNA
        else:
            cells[i] = NO_EVIDENCE
    frac = Fraction(len(rows) - len(residual), len(rows)) if rows else Fraction(0)
    return ReadReceipt(mem.omega, tau_index, states, cells, residual, deficits, pressure, structured(deficits), frac)


# ---------------------------------------------------------------- PROPOSE
@dataclass(frozen=True)
class Proposal:
    kind: str
    cells: FrozenSet[int]
    readout: str
    source: str
    claimed_rows: Tuple[str, ...]
    reason: str
    library_receipt: str = ""

    def key(self):
        return (self.kind, tuple(sorted(self.cells)), self.readout, self.claimed_rows)


class ShapeLibrary:
    """Attested SDG shapes, read from the seed file through bridge v2's parser (see families.py).
    shape_counts: {n_prerequisites: number of accepted recipe seeds with that many core terms}."""

    def __init__(self, shape_counts, seed_sha256):
        self.shape_counts = dict(shape_counts)
        self.seed_sha256 = seed_sha256
        self.attested_sizes = tuple(sorted(k for k, v in self.shape_counts.items() if v > 0))

    def lookup_order(self, n_cells):
        ext = [k for k in (1, n_cells) if k not in self.attested_sizes]
        ext += [k for k in range(1, n_cells + 1) if k not in self.attested_sizes and k not in ext]
        return [k for k in self.attested_sizes if k <= n_cells] + ext

    def tag(self, cells, kind):
        if kind in (K_DROP, K_SUBSET) and len(cells) in self.attested_sizes:
            return SDG_ATTESTED_SHAPE
        return LOOP_EXTENSION

    def receipt(self, size):
        return "seeds_with_%d_prerequisites=%d;seed_sha256=%s" % (size, self.shape_counts.get(size, 0),
                                                                    self.seed_sha256[:12])


def _mode(mem, allow_pooled):
    return POOLED if (mem.readout == POOLED and allow_pooled) else EXCLUSIVE


def propose(mem, rr, tried, allow_pooled, n_cells, lib):
    """Part 1 (diagnosis, ^6) chooses the kind; part 2 (library lookup, ^8 -> ^9) lists attested shapes."""
    out = []
    under = [d for d in rr.deficits if d.sign > 0]
    over = [d for d in rr.deficits if d.sign < 0]
    current = frozenset().union(*[r.cells for r in mem.recipes]) if mem.recipes else frozenset(range(n_cells))
    if under:
        top = max(rr.lacuna_pressure, key=lambda i: rr.lacuna_pressure[i])
        if Fraction(rr.lacuna_pressure[top], len(under)) >= Fraction(4, 5):
            cells = frozenset(current - {top})
            if cells:
                out.append(Proposal(K_DROP, cells, _mode(mem, allow_pooled), lib.tag(cells, K_DROP),
                                    tuple(d.row_id for d in under), "deficit pressure on cell %d" % top,
                                    lib.receipt(len(cells))))
        elif allow_pooled:
            out.append(Proposal(K_LINES, frozenset(range(n_cells)), POOLED, LOOP_EXTENSION, rr.residual,
                                "spread deficit: parallel production, one single-input line per cell + capacity",
                                lib.receipt(1)))
        for size in lib.lookup_order(n_cells):
            for subset in itertools.combinations(range(n_cells), size):
                cells = frozenset(subset)
                out.append(Proposal(K_SUBSET, cells, _mode(mem, allow_pooled), lib.tag(cells, K_SUBSET),
                                    tuple(d.row_id for d in under), "spread deficit", lib.receipt(size)))
    if over:
        out.append(Proposal(K_EFF, frozenset(), mem.readout, LOOP_EXTENSION, tuple(d.row_id for d in over),
                            "over-predicted; eta <= 1 (side product unobserved)"))
        out.append(Proposal(K_CAP, frozenset(), mem.readout, LOOP_EXTENSION, tuple(d.row_id for d in over),
                            "repeated y values"))
    if allow_pooled and len(mem.recipes) >= 2:
        flip = EXCLUSIVE if mem.readout == POOLED else POOLED
        out.append(Proposal(K_MODE, frozenset(), flip, LOOP_EXTENSION, rr.residual, "readout switch"))
    fresh = [p for p in out if p.key() not in tried]
    fresh.sort(key=lambda p: -len(p.claimed_rows))
    return fresh[:P_MAX]


def random_space(n_cells):
    return [frozenset(s) for k in range(1, n_cells + 1) for s in itertools.combinations(range(n_cells), k)]


def propose_random(rng, mem, rr, tried, n_cells, lib):
    """Dumb baseline B2: same template space, drawn uniformly, ignoring the deficit receipt."""
    space = random_space(n_cells)
    picks = [rng.choice(space) for _ in range(P_MAX)]
    out = []
    for c in picks:
        p = Proposal(K_SUBSET, c, EXCLUSIVE, lib.tag(c, K_SUBSET), rr.residual, "random", lib.receipt(len(c)))
        if p.key() not in tried:
            out.append(p)
    return out


# ---------------------------------------------------------------- FIT (non-gradient, exact)
def witnessed_ratio_min(cells, rows, bounds=True):
    """witnessed_ratio_min_v1: a_i = min over rows with y > 0 of x_i / y, exact Fractions."""
    rows = [r for r in rows if r.ratio is not None]
    if not rows or not cells:
        return None
    a = {i: min(r.ratio[i] for r in rows) for i in cells}
    if any(v <= 0 for v in a.values()):
        return None
    if bounds and any(not (COEF_BOUNDS[0] <= v <= COEF_BOUNDS[1]) for v in a.values()):
        return None
    return make_recipe(cells, a)


@dataclass(frozen=True)
class FitReceipt:
    proposal: Proposal
    candidate: Optional[Memory]
    refusal: Optional[str]
    detail: str = ""


def _median(values):
    s = sorted(values)
    return s[len(s) // 2]


def witnessed_pool_solve_v0(mem, p, rows):
    """ARCHITECTURE s.5.3 (named separately; not the witnessed ratio). Capacity C = the most repeated exact
    y among claimed rows (needs >= S_MIN repeats, else no capacity stage). On the other claimed rows,
    y = sum_i b_i x_i is solved exactly from the first n linearly independent rows; lines a_i = 1/b_i."""
    n = len(rows[0].xF)
    by_id = {r.row_id: r for r in rows}
    claimed = [by_id[i] for i in p.claimed_rows]
    counts = {}
    for r in claimed:
        counts[r.yF] = counts.get(r.yF, 0) + 1
    cap = None
    if counts:
        top = max(sorted(counts), key=lambda v: counts[v])
        if counts[top] >= S_MIN:
            cap = top
    linear = [r for r in claimed if cap is None or r.yF != cap]
    chosen = []
    for r in linear:
        trial = chosen + [r]
        if len(trial) <= n:
            # keep r if the rows chosen so far stay linearly independent
            if _rank([list(q.xF) for q in trial]) == len(trial):
                chosen = trial
        if len(chosen) == n:
            break
    if len(chosen) < n:
        return None, "NOT_IDENTIFIABLE", ""
    b = _solve([list(q.xF) for q in chosen], [q.yF for q in chosen])
    if b is None or any(v <= 0 for v in b):
        return None, "NONPOSITIVE_LINE", ""
    a = [1 / v for v in b]
    if any(not (COEF_BOUNDS[0] <= v <= COEF_BOUNDS[1]) for v in a):
        return None, "COEFFICIENT_OUT_OF_BOUNDS", ""
    lines = [make_recipe([i], {i: a[i]}) for i in range(n)]
    cand = mem.copy(recipes=lines, readout=POOLED, capacity=cap)
    detail = "capacity=%s;solve_rows=%s" % ("none" if cap is None else str(cap), ",".join(q.row_id for q in chosen))
    return cand, None, detail


def _rank(matrix):
    m = [list(r) for r in matrix]
    rank, cols = 0, len(m[0]) if m else 0
    for c in range(cols):
        piv = next((r for r in range(rank, len(m)) if m[r][c] != 0), None)
        if piv is None:
            continue
        m[rank], m[piv] = m[piv], m[rank]
        for r in range(len(m)):
            if r != rank and m[r][c] != 0:
                f = m[r][c] / m[rank][c]
                m[r] = [u - f * v for u, v in zip(m[r], m[rank])]
        rank += 1
    return rank


def fit(mem, p, rows):
    by_id = {r.row_id: r for r in rows}
    if p.kind == K_MODE:
        return FitReceipt(p, mem.copy(readout=p.readout), None)
    if p.kind == K_EFF:
        ratios = []
        for i in p.claimed_rows:
            yhat = predict(mem, by_id[i], exact=True)
            if yhat > 0:
                ratios.append(by_id[i].yF / yhat)
        if not ratios:
            return FitReceipt(p, None, "NOT_IDENTIFIABLE")
        eta = min(Fraction(1), _median(ratios) * mem.eta)
        if eta <= 0:
            return FitReceipt(p, None, "NOT_IDENTIFIABLE")
        return FitReceipt(p, mem.copy(eta=eta), None)
    if p.kind == K_CAP:
        values = [by_id[i].yF for i in p.claimed_rows]
        if not values:
            return FitReceipt(p, None, "NO_REPEATED_VALUE")
        top = max(sorted(set(values)), key=values.count)
        if values.count(top) < S_MIN:
            return FitReceipt(p, None, "NO_REPEATED_VALUE")
        return FitReceipt(p, mem.copy(capacity=top), None)
    if p.kind == K_LINES:
        cand, refusal, detail = witnessed_pool_solve_v0(mem, p, rows)
        return FitReceipt(p, cand, refusal, detail)
    seed = witnessed_ratio_min(p.cells, [by_id[i] for i in p.claimed_rows])
    if seed is None:
        return FitReceipt(p, None, "COEFFICIENT_OUT_OF_BOUNDS")
    recipes = list(mem.recipes) + [seed]
    for _ in range(T_ASSIGN):
        groups = {k: [] for k in range(len(recipes))}
        for r in rows:
            if r.yf <= 0:
                continue
            k = min(range(len(recipes)),
                    key=lambda j: (abs(math.log(r.yf / max(recipes[j].yield_f(r.xf), 1e-9))), j))
            groups[k].append(r)
        refit = [witnessed_ratio_min(rec.cells, groups[k]) or rec for k, rec in enumerate(recipes)]
        if refit == recipes:
            break
        recipes = refit
    return FitReceipt(p, mem.copy(recipes=recipes, readout=p.readout), None)


# ---------------------------------------------------------------- VERIFY
@dataclass(frozen=True)
class VerifyReceipt:
    fit: FitReceipt
    newly_explained: int
    broken: int
    holdout_init: int
    holdout_after: int
    decision: str


def _median_log(mem, rows):
    vals = []
    for r in rows:
        p = predict(mem, r)
        if r.yf > 0 and p > 0:
            vals.append(abs(math.log(r.yf / p)))
    return _median(vals) if vals else 0.0


def verify(mem, fr, train, valid, tau, holdout_init, a_max):
    if fr.candidate is None:
        return VerifyReceipt(fr, 0, 0, holdout_init, 0, "REFUSE:" + str(fr.refusal))
    new = fr.candidate
    before = [explained(r.yf, predict(mem, r), tau) for r in train]
    after = [explained(r.yf, predict(new, r), tau) for r in train]
    gained = sum(1 for b, a in zip(before, after) if a and not b)
    broken = sum(1 for b, a in zip(before, after) if b and not a)
    hold = sum(1 for r in valid if explained(r.yf, predict(new, r), tau))
    if len(new.recipes) > a_max:
        decision = "REFUSE:CAP"
    elif gained < S_MIN:
        decision = "REFUSE:SUPPORT"
    elif broken > BREAK_ALLOWANCE:
        decision = "REFUSE:MEMORY_CHECK"
    elif hold < holdout_init - HOLDOUT_ALLOWANCE:
        decision = "REFUSE:HOLDOUT"
    elif _median_log(new, valid) > _median_log(mem, valid):
        decision = "REFUSE:HOLDOUT_MEDIAN"
    else:
        decision = "ADMIT"
    return VerifyReceipt(fr, gained, broken, holdout_init, hold, decision)


# ---------------------------------------------------------------- HALT
@dataclass(frozen=True)
class HaltReceipt:
    omega: str
    status: str
    lacunae: Tuple[str, ...]
    diagnostics: Dict[str, str]


def halt(omega, rr, budget):
    """CNCM kernel rule: only COVERAGE_COMPLETE may carry an empty lacunae list."""
    diag = {"explained_fraction": "%d/%d" % (rr.explained_fraction.numerator, rr.explained_fraction.denominator),
            "tau_index": str(rr.tau_index), "structured": str(rr.structured)}
    if not rr.residual:
        return HaltReceipt(omega, H_COMPLETE, (), diag)
    if budget:
        status = H_BUDGET
    elif rr.explained_fraction >= SHAPED_FLOOR:
        status = H_SHAPED
    elif not rr.structured:
        status = H_NOISE
    elif all(d.sign < 0 for d in rr.deficits if d.sign != 0) and not any(
            st == LACUNA for st in rr.cell_states.values()):
        status = H_KNOW
        diag["acquisition_request"] = "a prerequisite outside this universe limits the carried rows"
    else:
        status = H_NOT
    receipt = HaltReceipt(omega, status, rr.residual, diag)
    assert receipt.lacunae, "a non-complete HALT must carry its lacunae"
    return receipt


# ---------------------------------------------------------------- the loop
@dataclass
class OmegaRun:
    memory: Memory
    halt: HaltReceipt
    events: List[Tuple[int, str, str]] = field(default_factory=list)   # (t, kind, detail)
    admissions: int = 0
    proposals_tried: int = 0
    refusals: Dict[str, int] = field(default_factory=dict)
    cycles: int = 0
    final_read: Optional[ReadReceipt] = None
    machine_ledger: object = None
    reads: int = 0
    admitted_sources: List[str] = field(default_factory=list)


class RowLedger:
    """Bridge to lacunarity_machine_v1: one Universe cell per training row; one PROBE per row per READ
    (hits 1 if explained, else 0); CHARGE when a row is first explained. Built by the caller with the
    machine's own Universe/Ledger classes (passed in) so the machine's deterministic_read decides
    COVERED / LACUNA / FADED for the carried gaps at the HALT."""

    def __init__(self, universe_cls, cell_cls, ledger_cls, omega, rows):
        self.universe = universe_cls("lsr_rows_" + omega, [cell_cls("row:" + r.row_id) for r in rows],
                                     has_write_history=True)
        self.ledger = ledger_cls(self.universe)
        self.t = 0
        self.charged = set()

    def record(self, rr):
        self.t += 1
        for rid, st in rr.row_states.items():
            self.ledger.probe("row:" + rid, self.t, 1 if st == COVERED else 0, 1, tag="read")
        for rid, st in rr.row_states.items():
            if st == COVERED and rid not in self.charged:
                self.ledger.charge("row:" + rid, self.t, tag="explained")
                self.charged.add(rid)


def run_omega(omega, train, valid, seed_recipe, a_max, allow_pooled, lib, rng=None, deadline=None,
              row_ledger=None):
    n_cells = len(train[0].xf)
    mem = Memory(omega, [seed_recipe] if seed_recipe else [])
    tau_i = tau_index_for(mem, train, 0)
    holdout_init = sum(1 for r in valid if explained(r.yf, predict(mem, r), TAU_LADDER[tau_i]))
    charged = {}
    tried = set()
    run = OmegaRun(mem, None)
    rr = read(mem, train, charged, tau_i)
    run.reads += 1
    if row_ledger:
        row_ledger.record(rr)
    t = 0
    budget = False
    for cycle in range(C_MAX):
        run.cycles = cycle
        for rid, st in rr.row_states.items():
            if st == COVERED:
                charged[rid] = True
        if not rr.residual:
            run.memory, run.final_read = mem, rr
            run.halt = halt(omega, rr, budget=False)
            return run
        if deadline is not None and time.time() > deadline:
            budget = True
            break
        props = (propose_random(rng, mem, rr, tried, n_cells, lib) if rng is not None
                 else propose(mem, rr, tried, allow_pooled, n_cells, lib))
        if not props:
            break
        admitted = False
        for p in props:
            if deadline is not None and time.time() > deadline:
                budget = True
                break
            tried.add(p.key())
            run.proposals_tried += 1
            vr = verify(mem, fit(mem, p, train), train, valid, TAU_LADDER[tau_i], holdout_init, a_max)
            t += 1
            if vr.decision == "ADMIT":
                mem = vr.fit.candidate                          # the ONLY write to recipe memory
                run.admissions += 1
                run.admitted_sources.append(p.source)
                run.events.append((t, "CHARGE", "%s:%s:%s:%s" % (p.kind, sorted(p.cells), p.source, vr.fit.detail)))
                admitted = True
                break
            run.refusals[vr.decision] = run.refusals.get(vr.decision, 0) + 1
            run.events.append((t, "REFUSED", "%s:%s:%s" % (p.kind, sorted(p.cells), vr.decision)))
        tau_i = tau_index_for(mem, train, tau_i)
        rr = read(mem, train, charged, tau_i)
        run.reads += 1
        if row_ledger:
            row_ledger.record(rr)
        if budget:
            break
        if not admitted:
            more = (propose_random(rng, mem, rr, tried, n_cells, lib) if rng is not None
                    else propose(mem, rr, tried, allow_pooled, n_cells, lib))
            if not more:
                break
    else:
        budget = True
    run.memory, run.final_read = mem, rr
    run.halt = halt(omega, rr, budget=budget)
    return run


def static_read(mem, train, row_ledger=None):
    """A0 / B1: one READ and a HALT, no loop (budget=False)."""
    tau_i = tau_index_for(mem, train, 0)
    rr = read(mem, train, {}, tau_i)
    if row_ledger:
        row_ledger.record(rr)
    run = OmegaRun(mem, halt(mem.omega, rr, budget=False))
    run.final_read = rr
    run.reads = 1
    return run


# ---------------------------------------------------------------- rendering (Clarification 10)
def _dec(fr, places=12):
    """Exact Fraction -> decimal text with at most 12 fraction digits (bridge v2 NUMBER grammar)."""
    q = round(Fraction(fr) * 10 ** places)
    if q <= 0:
        q = 1
    s = "%d.%0*d" % (q // 10 ** places, places, q % 10 ** places)
    return s.rstrip("0").rstrip(".")


def render_recipe(rec, omega, cell_names):
    return ("Θ(Ω_" + omega + ") = " + " + ".join(_dec(v) + "*" + cell_names[i] for i, v in rec.a)
            + " → Ω_" + omega)


def render_memory(mem, cell_names):
    """Each recipe is rendered alone (bridge-v2 parsable). Alternatives for the same Omega are joined by
    `+` (co-presence, Clarification 10); the readout is a separate declaration, never `x`."""
    parts = [render_recipe(r, mem.omega, cell_names) for r in mem.recipes]
    joined = " + ".join("Θ%d(Ω_%s)" % (k + 1, mem.omega) for k in range(len(mem.recipes)))
    decl = "readout=%s" % mem.readout
    if mem.eta != 1:
        decl += "; eta=%s" % mem.eta
    if mem.capacity is not None:
        decl += "; capacity_stage: Θ_cap(Ω_%s) = 1*Ω_%s_pool + 1*K → Ω_%s, K=%s" % (
            mem.omega, mem.omega, mem.omega, _dec(mem.capacity))
    return {"recipes": parts, "co_presence": joined, "declaration": decl}
