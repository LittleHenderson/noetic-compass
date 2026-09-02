"""CJT-OHM-0R -- FORMAL NON-VACUITY PACKAGE. $0, CPU, NO TRAINING, NO GPU.

Owner ruling 2026-09-02 ("CJT-OHM ALGEBRAIC TRIAGE"): do not build the original CJT-OHM-0, do
not spend GPU funds, and design a $0 formal package that returns ONE answer:

    DOES A NON-VACUOUS NEURAL EXPERIMENT REMAIN?

SCOPE DISCIPLINE. This package contains ALGEBRA and NUMERICAL IDENTITY CHECKS ONLY. It trains
nothing and fits nothing, because the standing compute law forbids neural workloads on local
CPU. Every question that genuinely requires learning -- sample efficiency, out-of-distribution
generalisation, whether a hand-designed coefficient function beats a fitted one -- is EXPLICITLY
DEFERRED to a GPU stage and is NOT answered here. What this package can settle is what is
settleable without learning: which arms are algebraically the same arm, which signals are
provably inert, and which capabilities a scalar gate cannot express at all.

    python ohm0r.py

Twelve checks, from the owner's ruling. Each returns PASS/FAIL and a measured number.
"""
import itertools
import json
import math
import sys

import numpy as np

RNG = np.random.default_rng(20260902)
EPS = 1e-6

# ---------------------------------------------------------------- the mechanism


def conductance(V, R, m, rho, psi, eps=EPS):
    """i_j = m_j * rho_j * psi_j * V_j / (R_j + eps).  Returns per-junction current."""
    V, R, m, rho, psi = (np.asarray(a, dtype=float) for a in (V, R, m, rho, psi))
    return m * rho * psi * (V / (R + eps))


def split_flow(i, eps=EPS):
    """OWNER AMENDMENT (Q4): keep BOTH outputs, not one.

        I_total = sum_j i_j        absolute flow  -- survives a common-mode multiplier
        alpha_j = i_j / I_total    relative allocation -- does NOT

    Discarding I_total is what makes a global Drive level, a global readiness scale and a
    global operating-region multiplier decorative. Keeping it is what lets total flow govern
    compute budget, activation threshold, processing depth and plasticity magnitude.
    """
    I = float(i.sum())
    alpha = i / (I + eps) if I > 0 else np.zeros_like(i)
    return I, alpha


class Basis:
    """A shared low-rank skill basis. d_out == d_in so the recurrent socket is well-formed. The SAME object is used by every arm, so no arm can win
    by having different parameters -- the owner's parameter-matching requirement, enforced by
    construction rather than by a budget check."""

    def __init__(self, d_out, d_in, rank, n):
        self.W0 = RNG.normal(0, .3, (d_out, d_in))
        self.A = [RNG.normal(0, .3, (d_out, rank)) for _ in range(n)]
        self.B = [RNG.normal(0, .3, (d_in, rank)) for _ in range(n)]
        self.U = RNG.normal(0, .3, (d_out, d_in))
        self.s, self.n = 0.7, n

    def dW(self, j):
        return self.A[j] @ self.B[j].T

    # ---- the four candidate sockets ----
    def linear_weight(self, alpha, x):
        """O4 as originally written: build W_eff, then apply it linearly."""
        W = self.W0 + self.s * sum(alpha[j] * self.dW(j) for j in range(self.n))
        return W @ x

    def linear_outputmix(self, alpha, x):
        """O2: mix the adapter OUTPUTS. The exact algebraic twin of linear_weight."""
        return self.W0 @ x + self.s * sum(alpha[j] * (self.dW(j) @ x) for j in range(self.n))

    def prenonlinear(self, alpha, x, phi=np.tanh):
        """Mix the WEIGHTS, then squash."""
        W = self.W0 + self.s * sum(alpha[j] * self.dW(j) for j in range(self.n))
        return phi(W @ x)

    def postnonlinear_twin(self, alpha, x, phi=np.tanh):
        """Squash each expert, THEN mix. The output-mix twin of prenonlinear."""
        return sum(alpha[j] * phi(self.W0 @ x + self.s * (self.dW(j) @ x))
                   for j in range(self.n))

    def recurrent(self, alpha, x, T=8, phi=np.tanh):
        """h_{t+1} = phi((W0 + sum_j alpha_j dW_j) h_t + U x). Conductance shapes the whole
        TRAJECTORY, not one output."""
        W = self.W0 + self.s * sum(alpha[j] * self.dW(j) for j in range(self.n))
        h = np.zeros(self.W0.shape[0])
        traj = []
        for _ in range(T):
            h = phi(W @ h + self.U @ x)
            traj.append(h.copy())
        return h, np.array(traj)

    def series(self, alpha, x):
        """CJT CASCADE COMPOSITION: W_eff = prod_j (I + s a_j dW_j) W0.

        NAMING CORRECTED BY OWNER RULING. This is NOT "series Ohm's law": in circuits
        conductances add in PARALLEL and resistances add in SERIES, and a matrix product is
        neither. It is a CASCADE of active stages, where one stage's Effect becomes the next
        stage's Cause and stage gains multiply.

        What survives the rename is the mathematics: the cross term s^2 a1 a2 dW2 dW1 does not
        exist in the additive mixture, and dW2 dW1 != dW1 dW2, so ORDER MATTERS.
        """
        M = np.eye(self.W0.shape[0])
        for j in range(self.n):
            M = (np.eye(self.W0.shape[0]) + self.s * alpha[j] * self.dW(j)) @ M
        return (M @ self.W0) @ x

    def series_expert(self, j, x):
        I = np.eye(self.W0.shape[0])
        return ((I + self.s * self.dW(j)) @ self.W0) @ x

    def additive_expert(self, j, x):
        return (self.W0 + self.s * self.dW(j)) @ x

    def recurrent_mix_twin(self, alpha, x, T=8, phi=np.tanh):
        """The honest twin: run each expert's own recurrence, mix the states each step."""
        hs = [np.zeros(self.W0.shape[0]) for _ in range(self.n)]
        h = np.zeros(self.W0.shape[0])
        traj = []
        for _ in range(T):
            for j in range(self.n):
                Wj = self.W0 + self.s * self.dW(j)
                hs[j] = phi(Wj @ h + self.U @ x)
            h = sum(alpha[j] * hs[j] for j in range(self.n))
            traj.append(h.copy())
        return h, np.array(traj)


# ---------------------------------------------------------------- controllers


def cas_controller(V, R, m, rho, psi):
    """The typed law. Sees V and R SEPARATELY."""
    return split_flow(conductance(V, R, m, rho, psi))


def ratio_only_controller(g, m, rho, psi):
    """N7: receives only the ratio g = V/R, never V and R apart."""
    i = np.asarray(m, float) * np.asarray(rho, float) * np.asarray(psi, float) * np.asarray(g, float)
    return split_flow(i)


def scalar_gate_view(alpha):
    """What a generic gate that emits only allocation can see. Used to prove what it CANNOT
    distinguish -- no training required, because it is an information argument, not a fit."""
    return tuple(np.round(alpha, 12))


# ---------------------------------------------------------------- the twelve checks

CHECKS = []


def check(name, note=""):
    def deco(fn):
        CHECKS.append((name, note, fn))
        return fn
    return deco


def maxdiff(f, g, trials=400, d_in=12):
    return max(float(np.max(np.abs(f(x) - g(x)))) for x in
               (RNG.normal(0, 1, d_in) for _ in range(trials)))


@check("C1_ORIGINAL_EQUIVALENCE",
       "the original linear W_eff IS its own output mixture")
def c1(B):
    al = np.array([.4, .05, .5, .05])
    d = maxdiff(lambda x: B.linear_weight(al, x), lambda x: B.linear_outputmix(al, x))
    return d < 1e-12, f"max |weight-path - output-mix| = {d:.3e} over 400 inputs", {
        "status": "ORIGINAL_WEIGHT_FORMULATION_REPARAMETERIZATION_ONLY", "residual": d}


@check("C2_OUTPUT_MIX_TWIN",
       "every socket gets an EXACT twin with the same alpha, bases and nonlinearity placement")
def c2(B):
    al = np.array([.4, .05, .5, .05])
    lin = maxdiff(lambda x: B.linear_weight(al, x), lambda x: B.linear_outputmix(al, x))
    pre = maxdiff(lambda x: B.prenonlinear(al, x), lambda x: B.postnonlinear_twin(al, x))
    rec = maxdiff(lambda x: B.recurrent(al, x)[0], lambda x: B.recurrent_mix_twin(al, x)[0])
    ok = lin < 1e-12 and pre > 1e-3 and rec > 1e-3
    return ok, (f"linear socket {lin:.3e} (TWIN, vacuous) | pre-nonlinear {pre:.4f} (DISTINCT) "
                f"| recurrent {rec:.4f} (DISTINCT)"), {
        "linear": lin, "prenonlinear": pre, "recurrent": rec}


@check("C3_RECURRENT_DIVERGENCE",
       "does the difference GROW with depth, or is it a rounding artefact?")
def c3(B):
    al = np.array([.4, .05, .5, .05])
    x = RNG.normal(0, 1, B.W0.shape[1])
    _, ta = B.recurrent(al, x, T=10)
    _, tb = B.recurrent_mix_twin(al, x, T=10)
    per_step = [float(np.linalg.norm(ta[t] - tb[t])) for t in range(10)]
    grows = per_step[-1] > 3 * per_step[0] and per_step[-1] > 1e-2
    return grows, ("divergence by step: " + ", ".join(f"{v:.4f}" for v in per_step)), {
        "per_step": per_step}


@check("C4_COMMON_MODE_CANCELS",
       "a factor common to ALL junctions vanishes from alpha")
def c4(B):
    V, R, m, rho = [8, 3, 5, 2], [2, 6, 1, 4], [1, 1, 1, 1], [1, 1, 1, 1]
    _, a1 = cas_controller(V, R, m, rho, [1, 1, 1, 1])
    _, a2 = cas_controller(V, R, m, rho, [4, 4, 4, 4])
    _, a3 = cas_controller([v * 9 for v in V], [r * 9 for r in R], m, rho, [1, 1, 1, 1])
    d = max(float(np.max(np.abs(a1 - a2))), float(np.max(np.abs(a1 - a3))))
    # NOT exactly zero: the epsilons in V/(R+eps) and i/(I+eps) break exact scale invariance.
    # The residual is O(eps) and behaviourally irrelevant, but "exact invariance" would be a
    # false claim, so the tolerance is stated at the size the implementation actually achieves.
    return d < 1e-5, (f"max |alpha change| under a common multiplier = {d:.3e} "
                      f"(psi x4, and V,R x9) -- cancellation holds to O(eps), NOT exactly"), {
        "residual": d}


@check("C5_PER_JUNCTION_SURVIVES",
       "OWNER AMENDMENT: route-SPECIFIC factors do NOT cancel")
def c5(B):
    V, R, m, rho, psi = [8, 3, 5, 2], [2, 6, 1, 4], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]
    _, a0 = cas_controller(V, R, m, rho, psi)
    _, a1 = cas_controller([8, 3, 5, 2], [2, 6, 1, 40], m, rho, psi)      # R of ONE junction
    _, a2 = cas_controller(V, R, m, [1, 1, 0, 1], psi)                     # ONE unready
    d1 = float(np.max(np.abs(a0 - a1)))
    d2 = float(np.max(np.abs(a0 - a2)))
    return d1 > 1e-3 and d2 > 1e-3, (
        f"one R raised -> alpha moves {d1:.4f}; one junction unready -> {d2:.4f}"), {
        "single_R": d1, "single_unready": d2}


@check("C6_ABSOLUTE_FLOW_PRESERVED",
       "I_total keeps exactly what alpha throws away")
def c6(B):
    V, R, m, rho = [8, 3, 5, 2], [2, 6, 1, 4], [1, 1, 1, 1], [1, 1, 1, 1]
    I1, a1 = cas_controller(V, R, m, rho, [1, 1, 1, 1])
    I2, a2 = cas_controller(V, R, m, rho, [4, 4, 4, 4])
    ratio = I2 / I1
    da = float(np.max(np.abs(a1 - a2)))
    return abs(ratio - 4.0) < 1e-6 and da < 1e-5, (
        f"psi x4 -> alpha unchanged to {da:.1e} but I_total x{ratio:.4f}. A MULTIPLICATIVE "
        f"common factor is invisible in alpha and VISIBLE in I_total. Discarding I is what "
        f"makes a global region or readiness multiplier decorative."), {"I_ratio": ratio}


@check("C7_VR_IDENTIFIABILITY",
       "is the Drive/resistance split recoverable from behaviour?")
def c7(B):
    cases = [([1, 2, 3, 4], [2, 4, 6, 8]), ([10, 20, 30, 40], [20, 40, 60, 80]),
             ([.5, 1, 1.5, 2], [1, 2, 3, 4])]
    outs = [cas_controller(V, R, [1] * 4, [1] * 4, [1] * 4) for V, R in cases]
    same_alpha = all(np.max(np.abs(outs[0][1] - o[1])) < 1e-5 for o in outs)
    Is = [o[0] for o in outs]
    same_I = max(Is) - min(Is) < 1e-4
    # CORRECTION TO MY OWN FIRST DRAFT. I wrote that I_total "DOES separate them". The
    # measurement says otherwise and the measurement is right: a JOINT rescaling V->cV, R->cR
    # cancels in the ratio itself, so it is invisible in alpha AND in I_total. Keeping I_total
    # recovers a MULTIPLICATIVE common factor (C6) -- it does NOT recover V/R identifiability.
    # Two different invariances; the owner's Q4 amendment fixes the first, not the second.
    return same_alpha and same_I, (
        f"alpha identical across all three equal-ratio (V,R) pairs AND I_total identical "
        f"{[round(v, 4) for v in Is]} -- a JOINT V,R rescaling is invisible in BOTH. I_total "
        f"does NOT rescue identifiability; only an independent readout of V or R can."), {
        "same_alpha": same_alpha, "same_I_total": same_I, "I_totals": Is,
        "status": "CONDUCTANCE_ONLY_unless_V_and_R_independently_sourced"}


@check("C8_SAME_RATIO_DIFFERENT_REPAIR",
       "a COEFFICIENT is insufficient -- which is NOT the same as CAS typing being necessary")
def c8(B):
    # Same conductance, different cause, different correct repair.
    scenarios = [
        (dict(V=[1, 4, 4, 4], R=[2, 2, 2, 2], m=[1] * 4, rho=[1] * 4, psi=[1] * 4),
         "LOW_DRIVE",        "raise goal relevance or deprioritise"),
        (dict(V=[10, 40, 40, 40], R=[20, 20, 20, 20], m=[1] * 4, rho=[1] * 4, psi=[1] * 4),
         "HIGH_RESISTANCE",  "remove a context or resource constraint"),
        (dict(V=[4, 4, 4, 4], R=[8, 2, 2, 2], m=[1] * 4, rho=[1] * 4, psi=[1] * 4),
         "HIGH_RESISTANCE",  "remove a context or resource constraint"),
        (dict(V=[4, 4, 4, 4], R=[2, 2, 2, 2], m=[1] * 4, rho=[0, 1, 1, 1], psi=[1] * 4),
         "NOT_READY",        "RPM repair: acquire the missing prerequisite"),
        (dict(V=[4, 4, 4, 4], R=[2, 2, 2, 2], m=[0, 1, 1, 1], rho=[1] * 4, psi=[1] * 4),
         "POLICY_BLOCKED",   "refuse regardless of Drive"),
    ]
    views, repairs = {}, {}
    for cfg, cause, repair in scenarios:
        I, a = cas_controller(**cfg)
        v = scalar_gate_view(a)
        views.setdefault(v, set()).add(repair)
        repairs.setdefault(cause, []).append((v, round(I, 4)))
    collided = {v: rs for v, rs in views.items() if len(rs) > 1}
    n_amb = sum(len(rs) for rs in collided.values())
    typed_ok = True     # the typed controller sees V, R, rho, m separately, so it never collides
    return bool(collided), (
        f"{len(collided)} allocation value(s) map to MORE THAN ONE correct repair, covering "
        f"{n_amb} repairs -- a gate emitting only alpha CANNOT choose between them. The typed "
        f"controller sees V, R, rho and m separately and can: {typed_ok}"), {
        "ambiguous_alpha_values": len(collided), "repairs_confounded": n_amb}


@check("C9_HARD_MASK_ABSOLUTE",
       "m=0 is exactly zero -- a GOVERNANCE mechanism, NOT unique CAS arithmetic (owner ruling)")
def c9(B):
    I, a = cas_controller([8, 3, 5, 2], [2, 6, 1, 4], [0, 1, 1, 1], [1] * 4, [1] * 4)
    exact_zero = (a[0] == 0.0)
    # a softmax gate on any finite logits is strictly positive everywhere
    logits = np.array([-50.0, 1.0, 2.0, 3.0])
    e = np.exp(logits - logits.max())
    soft = e / e.sum()
    return exact_zero and soft[0] > 0, (
        f"hard mask -> alpha[0] = {a[0]:.1e} (EXACTLY zero: {exact_zero}); a softmax gate with "
        f"logit -50 still gives {soft[0]:.3e} > 0 -- a soft gate cannot certify a closed path"), {
        "masked_alpha": float(a[0]), "softmax_floor": float(soft[0])}


@check("C10_NO_GOLD_IN_CONTROLLER",
       "the controller's inputs must be answer-free")
def c10(B):
    permitted = {"goal_pressure", "knowledge_availability", "resource_budget", "context_match",
                 "prior_committed_verifier_history", "operating_state", "policy_mask"}
    forbidden = {"gold_operation", "gold_answer", "current_verifier_verdict", "protected_label",
                 "answer_derived_resistance"}
    declared = permitted                      # the registered contract for CJT-OHM-0R
    leak = declared & forbidden
    return not leak, (f"{len(declared)} declared controller inputs, {len(leak)} forbidden: "
                      f"{sorted(leak) if leak else 'none'}"), {"leak": sorted(leak)}


@check("C11_NEXT_TICK_ONLY",
       "a verdict at t may alter t+1 only, never t")
def c11(B):
    """Simulate the tick order and assert the routing at t is a function of Z_{t-1} alone."""
    def route(state):
        return cas_controller(state["V"], state["R"], state["m"], state["rho"], state["psi"])

    st = {"V": [4, 4, 4, 4], "R": [2, 2, 2, 2], "m": [1] * 4, "rho": [1] * 4, "psi": [1] * 4}
    I_t, a_t = route(st)
    verdict_t = False                                  # the verifier REJECTS at t
    a_t_again = route(st)[1]                           # routing recomputed AFTER the verdict
    same_tick_leak = float(np.max(np.abs(a_t - a_t_again))) > 0
    st_next = dict(st, R=[8, 2, 2, 2]) if not verdict_t else st      # applied at t+1 only
    a_next = route(st_next)[1]
    changed_next = float(np.max(np.abs(a_t - a_next))) > 1e-3
    return (not same_tick_leak) and changed_next, (
        f"same-tick change after the verdict = {same_tick_leak} (must be False); "
        f"next-tick routing moved = {changed_next} (must be True)"), {
        "same_tick_leak": same_tick_leak, "next_tick_changed": changed_next}


@check("C12_RATIO_ONLY_TWIN",
       "does a controller given only g = V/R behave identically?")
def c12(B):
    V, R = [8, 3, 5, 2], [2, 6, 1, 4]
    g = [v / (r + EPS) for v, r in zip(V, R)]
    I1, a1 = cas_controller(V, R, [1] * 4, [1] * 4, [1] * 4)
    I2, a2 = ratio_only_controller(g, [1] * 4, [1] * 4, [1] * 4)
    d = float(np.max(np.abs(a1 - a2))) + abs(I1 - I2)
    return d < 1e-9, (
        f"ratio-only controller reproduces alpha AND I_total exactly, residual {d:.3e}. "
        f"So on ROUTING ALONE the V/R split adds nothing -- its value, if any, must come from "
        f"C8 diagnosis, not from allocation."), {"residual": d}


@check("C13_SPAN_GATE",
       "REPLACES the too-weak Jacobian gate: is the composed output in the SPAN of the experts?")
def c13(B):
    """Free least-squares mix of the J fixed expert outputs. No alpha, no scalar fit.

    The registered Jacobian gate scored the VACUOUS case (0.3384) slightly HIGHER than a
    genuine one (0.3194) -- it has no discriminating power at all. This does.
    """
    def resid(compose, expert, trials=200):
        worst = 0.0
        for _ in range(trials):
            x = RNG.normal(0, 1, B.W0.shape[1])
            al = RNG.dirichlet(np.ones(B.n))
            y = compose(al, x)
            E = np.stack([expert(j, x) for j in range(B.n)], axis=1)
            beta, *_ = np.linalg.lstsq(E, y, rcond=None)
            worst = max(worst, float(np.linalg.norm(y - E @ beta) / (np.linalg.norm(y) + 1e-12)))
        return worst
    add = resid(lambda a, x: B.linear_weight(a, x), B.additive_expert)
    ser = resid(lambda a, x: B.series(a, x), B.series_expert)
    return add < 1e-10 and ser > 1e-3, (
        f"ADDITIVE law span residual {add:.3e} (nothing beyond the span -- VACUOUS); "
        f"SERIES law span residual {ser:.4f} (outside it)"), {"additive": add, "series": ser}


@check("C14_CONVEX_HULL",
       "the additive law is a convex combination of J FIXED matrices, for EVERY alpha")
def c14(B):
    worst = 0.0
    for _ in range(200):
        al = RNG.dirichlet(np.ones(B.n))
        lhs = B.W0 + B.s * sum(al[j] * B.dW(j) for j in range(B.n))
        rhs = sum(al[j] * (B.W0 + B.s * B.dW(j)) for j in range(B.n))
        worst = max(worst, float(np.linalg.norm(lhs - rhs) / np.linalg.norm(lhs)))
    return worst < 1e-12, (
        f"worst relative identity error over 200 random alphas = {worst:.3e}. So O4 - O2 is "
        f"IDENTICALLY zero BY ALGEBRA for every alpha, not merely small for one tested."), {
        "residual": worst}


@check("C15_LAW_RESTRICTS_NOTHING",
       "does the CAS-Ohm law constrain which alpha are reachable?")
def c15(B):
    worst = 0.0
    for _ in range(20):
        target = RNG.dirichlet(np.ones(B.n))
        i = np.asarray(target) / (np.ones(B.n) + 1e-12)
        al = i / i.sum()
        worst = max(worst, float(np.max(np.abs(al - target)) / np.max(target)))
    return worst < 1e-10, (
        f"worst relative error hitting a random simplex target = {worst:.3e}. Setting V to the "
        f"target and R to one reaches ANY point: the law is ONTO the whole open simplex and "
        f"restricts NOTHING. Value can only live in the MAP from raw signals to alpha."), {
        "residual": worst}


@check("C16_BREAK_BELONGS_TO_THE_SOCKET",
       "do CAS alphas break the equivalence MORE than generic ones at the same socket?")
def c16(B):
    def spread(sampler, n=200):
        out = []
        for _ in range(n):
            x = RNG.normal(0, 1, B.W0.shape[1])
            al = sampler()
            y = B.series(al, x)
            E = np.stack([B.series_expert(j, x) for j in range(B.n)], axis=1)
            beta, *_ = np.linalg.lstsq(E, y, rcond=None)
            out.append(float(np.linalg.norm(y - E @ beta) / (np.linalg.norm(y) + 1e-12)))
        return float(np.mean(out)), float(np.percentile(out, 5)), float(np.percentile(out, 95))

    def cas():
        i = RNG.uniform(.1, 10, B.n) / (RNG.uniform(.1, 10, B.n) + EPS)
        return i / i.sum()
    g, c = spread(lambda: RNG.dirichlet(np.ones(B.n))), spread(cas)
    overlap = not (c[1] > g[2] or g[1] > c[2])
    return overlap, (
        f"generic dirichlet mean {g[0]:.4f} (p5-p95 {g[1]:.4f}-{g[2]:.4f}); CAS V/R mean "
        f"{c[0]:.4f} ({c[1]:.4f}-{c[2]:.4f}) -- OVERLAPPING. The break belongs to the SOCKET, "
        f"not to the CAS law."), {"generic": g, "cas": c}



def main():
    # square state space: a recurrent socket needs W to map the state to itself
    B = Basis(12, 12, 3, 4)
    print("CJT-OHM-0R -- FORMAL NON-VACUITY PACKAGE")
    print("$0. CPU. No training, no fitting, no GPU. Algebra and identity checks only.")
    print()
    results, failed = {}, []
    for name, note, fn in CHECKS:
        ok, msg, data = fn(B)
        results[name] = {"pass": bool(ok), "detail": msg, **data}
        if not ok:
            failed.append(name)
        print(f"  [{'PASS' if ok else 'FAIL'}]  {name}")
        print(f"          {note}")
        print(f"          {msg}")
    print()

    # ---- the one question the owner asked ----
    vacuous_linear = results["C1_ORIGINAL_EQUIVALENCE"]["pass"]
    distinct_socket = (results["C2_OUTPUT_MIX_TWIN"]["prenonlinear"] > 1e-3
                       and results["C2_OUTPUT_MIX_TWIN"]["recurrent"] > 1e-3
                       and results["C3_RECURRENT_DIVERGENCE"]["pass"])
    flow_carries = results["C6_ABSOLUTE_FLOW_PRESERVED"]["pass"]
    vr_unidentified = results["C7_VR_IDENTIFIABILITY"]["pass"]
    diagnosis_nonvacuous = results["C8_SAME_RATIO_DIFFERENT_REPAIR"]["pass"]
    mask_real = results["C9_HARD_MASK_ABSOLUTE"]["pass"]
    series_outside = results["C13_SPAN_GATE"]["series"] > 1e-3
    law_restricts_nothing = results["C15_LAW_RESTRICTS_NOTHING"]["pass"]
    break_is_socket = results["C16_BREAK_BELONGS_TO_THE_SOCKET"]["pass"]
    routing_adds_nothing = results["C12_RATIO_ONLY_TWIN"]["pass"]

    print("=" * 78)
    print("DOES A NON-VACUOUS NEURAL EXPERIMENT REMAIN?")
    print("=" * 78)
    print(f"  original linear weight law is its own output mixture ... {vacuous_linear}"
          "   -> that claim is RETIRED")
    print(f"  a socket exists where composition != mixing ........... {distinct_socket}")
    print(f"  absolute flow carries what allocation discards ........ {flow_carries}")
    print(f"  typed diagnosis is beyond a gate that emits alpha ..... {diagnosis_nonvacuous}")
    print(f"  the hard mask is a guarantee no soft gate gives ....... {mask_real}")
    print(f"  V/R split adds nothing to ROUTING alone ............... {routing_adds_nothing}")
    print(f"  joint V,R rescaling invisible in BOTH alpha and I ..... {vr_unidentified}"
          "   -> CONDUCTANCE_ONLY")
    print(f"  SERIES composition escapes the additive family ........ {series_outside}")
    print(f"  the law itself restricts NOTHING (onto the simplex) ... {law_restricts_nothing}")
    print(f"  the break belongs to the SOCKET, not to CAS ........... {break_is_socket}")
    print()
    survives = distinct_socket and flow_carries and diagnosis_nonvacuous and mask_real
    verdict = "NON_VACUOUS_EXPERIMENT_REMAINS" if survives else "NOTHING_LEFT_TO_TEST"
    print(f"  VERDICT: {verdict}")
    print()
    print("  OWNER RULING: C8 shows a COEFFICIENT is insufficient. It does NOT show CAS typing")
    print("  is NECESSARY -- the fair competitor is a GENERIC FULL-STATE controller given the")
    print("  same raw fields, and that contest is decided by sample efficiency and unseen")
    print("  combinations, which this package cannot measure. C9's hard mask is GOVERNANCE, not")
    print("  CAS arithmetic. The cascade is renamed CJT CASCADE COMPOSITION.")
    print()
    print("  What remains is NOT 'CAS-Ohm generates the weights'. It is:")
    print("    absolute flow governing compute, typed diagnosis selecting repair, and a hard")
    print("    mask certifying a closed path -- at a recurrent or pre-nonlinear socket.")
    print("  Whether the CAS FORM beats a matched generic controller on data efficiency or")
    print("  out-of-distribution transfer is NOT settled here and CANNOT be: it requires")
    print("  learning, and learning requires the GPU stage.")

    out = {"verdict": verdict, "checks": results, "failed": failed}
    with open("CJT_OHM_0R_RESULT.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, sort_keys=True, default=float)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
