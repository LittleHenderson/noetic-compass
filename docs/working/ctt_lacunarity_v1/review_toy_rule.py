"""Review of the companion ChatGPT code draft: run it, measure it, compare with the bounded rule.

The draft's rule, verbatim in effect:
    window of recent FULL gradient vectors
    gradient_variance = np.var(recent_gradients)          # one scalar over all entries
    factor = 1 + lambda * gradient_variance               # no clip, no units
    lr_t = lr0 * factor
    w = w - lr_t * g

Measured here:
  1. the factor is a function of the LOSS SCALE, not of the problem's shape. Variance has units of
     gradient squared, so a 10x steeper loss multiplies the factor by about 100. A universal
     equation cannot depend on the units of the loss it is applied to.
  2. where the rule crosses the stability bound as the loss gets steeper.
  3. the memory the "window of full gradients" costs at CTT-1's 9,585,566 parameters.

Run: python -X utf8 review_toy_rule.py
"""
from __future__ import annotations

import math
import random
import sys

PARAMS_CTT = 9_585_566
WINDOW = 50
LR0 = 0.01
LAMBDA = 0.5
STEPS = 200
DIM = 64
NOISE = 1.0


def gliding_box(values, box):
    n = len(values)
    if box < 1 or n < box or sum(values) <= 0:
        return None
    window = float(sum(values[:box]))
    windows = [window]
    for i in range(box, n):
        window += values[i] - values[i - box]
        windows.append(window)
    mean = sum(windows) / len(windows)
    var = sum((w - mean) ** 2 for w in windows) / len(windows)
    return 1.0 + var / (mean * mean)


def run(rule: str, curvature: float, seed: int = 7):
    rng = random.Random(seed)
    w = [1.0] * DIM
    history = []
    slow = None
    peak, factors = 0.0, []
    for t in range(STEPS):
        g = [curvature * x + NOISE * rng.gauss(0.0, 1.0) for x in w]
        gnorm = math.sqrt(sum(v * v for v in g))
        if rule == "draft":
            history.append(g[:])
            if len(history) > WINDOW:
                history.pop(0)
            if t > 0 and len(history) > 1:
                flat = [v for vec in history for v in vec]
                mean = sum(flat) / len(flat)
                var = sum((v - mean) ** 2 for v in flat) / len(flat)
                factor = 1.0 + LAMBDA * var
            else:
                factor = 1.0
            factors.append(factor)
            lr_t = LR0 * factor
        elif rule == "bounded":
            history.append(gnorm)
            if len(history) > WINDOW:
                history.pop(0)
            l_b = gliding_box(history, 8) if len(history) >= 8 else None
            if l_b is None:
                factor = 1.0
            else:
                l_tilde = min(1.0, max(0.0, (l_b - 1.0) / (2.0 - 1.0)))
                if slow is None:
                    slow = l_tilde
                deviation = l_tilde - slow
                slow = slow + (1.0 - 0.5 ** (1.0 / 500.0)) * (l_tilde - slow)
                factor = min(2.0, max(0.5, math.exp(LAMBDA * deviation)))
            factors.append(factor)
            lr_t = LR0 * factor
        else:
            raise SystemExit("unknown rule")
        w = [x - lr_t * gv for x, gv in zip(w, g)]
        biggest = max(abs(x) for x in w)
        peak = max(peak, biggest)
        if not math.isfinite(biggest) or biggest > 1e6:
            return {"rule": rule, "curvature": curvature, "diverged": True,
                    "peak": biggest, "steps": t + 1,
                    "median_factor": sorted(factors)[len(factors) // 2] if factors else 1.0}
    return {"rule": rule, "curvature": curvature, "diverged": False,
            "peak": peak, "steps": STEPS,
            "median_factor": sorted(factors)[len(factors) // 2] if factors else 1.0}


def main() -> int:
    print("quadratic f(w)=0.5*k*|w|^2, dim %d, %d steps, lr0 %g, lambda %g, noise %g"
          % (DIM, STEPS, LR0, LAMBDA, NOISE))
    print()
    print("median multiplier by loss curvature (the same problem, only the loss scale changes):")
    print("%-10s %-10s %-10s" % ("curvature", "draft", "bounded"))
    for k in (1.0, 3.0, 10.0, 30.0, 100.0):
        d = run("draft", k)
        b = run("bounded", k)
        print("%-10g %-10.3f %-10.3f" % (k, d["median_factor"], b["median_factor"]))
    print()
    print("stability sweep (lr0 fixed at %g; diverged = |w| > 1e6 or non-finite):" % LR0)
    print("%-10s %-10s %-10s" % ("curvature", "draft", "bounded"))
    for k in (1.0, 3.0, 10.0, 30.0, 100.0, 300.0):
        d = run("draft", k)
        b = run("bounded", k)
        print("%-10g %-10s %-10s" % (k, "DIVERGED" if d["diverged"] else "ok",
                                     "DIVERGED" if b["diverged"] else "ok"))
    print()
    per_copy = PARAMS_CTT * 4
    print("CTT-1 parameter count: %d" % PARAMS_CTT)
    print("one fp32 gradient copy: %.1f MB" % (per_copy / 1024 / 1024))
    print("window of 100 full copies: %.2f GB (the draft stores full vectors)"
          % (per_copy * 100 / 1024 / 1024 / 1024))
    print("window of 100 scalar norms: %d bytes" % (100 * 4))
    return 0


if __name__ == "__main__":
    sys.exit(main())
