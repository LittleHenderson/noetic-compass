"""Random valid CAS expression generator.

Generates compilable CAS expressions with controlled complexity.
Every generated expression is validated through the compiler before
being accepted. Respects domain descent for ->, same-domain for /,
and admissibility constraints.
"""

from __future__ import annotations

import random
from typing import Any

# Avoid hard import of compiler — passed in at init
OPERATORS = list(range(10))
DOMAINS = ["P", "C", "E", "O"]
DOMAIN_ORDER = {"P": 0, "C": 1, "E": 2, "O": 3}
DRIVES = list(range(1, 8))
INVOLUTION_PAIRS = [(2, 3), (5, 6), (8, 9)]


def _random_state(rng: random.Random) -> str:
    op = rng.choice(OPERATORS)
    dom = rng.choice(DOMAINS)
    drv = rng.choice(DRIVES)
    return f"CO-{op}^{dom}_{{F{drv}}}"


def _random_state_in_domain(dom: str, rng: random.Random) -> str:
    op = rng.choice(OPERATORS)
    drv = rng.choice(DRIVES)
    return f"CO-{op}^{dom}_{{F{drv}}}"


def _descending_domains(rng: random.Random) -> tuple[str, str]:
    """Pick two domains where the first dominates the second."""
    pairs = [("P", "C"), ("P", "E"), ("P", "O"), ("C", "E"), ("C", "O"), ("E", "O")]
    return rng.choice(pairs)


class CASExpressionGenerator:
    """Generates random valid CAS expressions with controlled complexity."""

    def __init__(self, compile_fn: Any, seed: int | None = None):
        self.compile = compile_fn
        self.rng = random.Random(seed)

    def generate_state(self) -> str:
        return _random_state(self.rng)

    def generate_expression(self, complexity: str = "medium") -> str:
        if complexity == "simple":
            return self._gen_simple()
        elif complexity == "complex":
            return self._gen_complex()
        return self._gen_medium()

    def _gen_simple(self) -> str:
        """1-2 states, basic operation."""
        s1 = self.generate_state()
        if self.rng.random() < 0.3:
            return s1

        roll = self.rng.random()
        if roll < 0.25:
            # Multiplication — same domain
            dom = self.rng.choice(DOMAINS)
            s1 = _random_state_in_domain(dom, self.rng)
            s2 = _random_state_in_domain(dom, self.rng)
            return f"{s1} * {s2}"
        elif roll < 0.5:
            # Division — same domain
            dom = self.rng.choice(DOMAINS)
            s1 = _random_state_in_domain(dom, self.rng)
            s2 = _random_state_in_domain(dom, self.rng)
            return f"{s1} / {s2}"
        elif roll < 0.75:
            # Domain descent
            d1, d2 = _descending_domains(self.rng)
            s1 = _random_state_in_domain(d1, self.rng)
            s2 = _random_state_in_domain(d2, self.rng)
            return f"{s1} -> {s2}"
        else:
            # Addition
            s2 = self.generate_state()
            return f"{s1} + {s2}"

    def _gen_medium(self) -> str:
        """2-4 states, maybe RPM or fractal."""
        parts: list[str] = []
        num = self.rng.randint(2, 4)
        dom = self.rng.choice(DOMAINS)

        for _ in range(num):
            if self.rng.random() < 0.15:
                drv = self.rng.choice(DRIVES)
                parts.append(f"RPM(F{drv})")
            else:
                parts.append(_random_state_in_domain(dom, self.rng))

        # Connect with multiplication (same domain)
        expr = " * ".join(parts)

        # Maybe add domain descent
        if self.rng.random() < 0.4:
            lower = [d for d in DOMAINS if DOMAIN_ORDER[d] > DOMAIN_ORDER[dom]]
            if lower:
                d2 = self.rng.choice(lower)
                s2 = _random_state_in_domain(d2, self.rng)
                expr = f"{expr} -> {s2}"

        # Maybe add fractal
        if self.rng.random() < 0.25:
            seq = self.rng.sample(OPERATORS, self.rng.randint(3, 5))
            phi = f"Phi<{':'.join(str(s) for s in seq)}>"
            expr = f"{expr}; {phi}"

        return expr

    def _gen_complex(self) -> str:
        """3-6 states with parentheses, RPM, fractals."""
        d1, d2 = _descending_domains(self.rng)

        # Parenthesized sub-expressions per domain
        n1 = self.rng.randint(1, 3)
        n2 = self.rng.randint(1, 2)
        states1 = [_random_state_in_domain(d1, self.rng) for _ in range(n1)]
        states2 = [_random_state_in_domain(d2, self.rng) for _ in range(n2)]

        g1 = " * ".join(states1) if len(states1) > 1 else states1[0]
        g2 = " * ".join(states2) if len(states2) > 1 else states2[0]

        if len(states1) > 1:
            g1 = f"({g1})"
        if len(states2) > 1:
            g2 = f"({g2})"

        expr = f"{g1} -> {g2}"

        # Add RPM
        if self.rng.random() < 0.4:
            drv = self.rng.choice(DRIVES)
            expr = f"{expr}; RPM(F{drv})"

        # Add fractal
        if self.rng.random() < 0.35:
            seq = self.rng.sample(OPERATORS, self.rng.randint(3, 6))
            phi = f"Phi<{':'.join(str(s) for s in seq)}>"
            expr = f"{expr}; {phi}"

        # Add co-present drives
        if self.rng.random() < 0.3:
            d_a = self.rng.choice(DRIVES)
            d_b = self.rng.choice([d for d in DRIVES if d != d_a])
            expr = f"{expr}; F{d_a} + F{d_b}"

        return expr

    def generate_and_validate(
        self, complexity: str = "medium", max_attempts: int = 20,
    ) -> tuple[str, Any] | None:
        """Generate and validate through compiler. Returns (expr, artifact) or None."""
        for _ in range(max_attempts):
            expr = self.generate_expression(complexity)
            try:
                result = self.compile(expr)
                if result.valid:
                    return expr, result
            except Exception:
                continue
        return None
