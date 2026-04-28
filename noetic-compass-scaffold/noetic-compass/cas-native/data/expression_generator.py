"""Random valid CAS expression generator.

Generates compilable CAS expressions with controlled complexity.
Every generated expression is validated through the compiler before
being accepted. Respects domain descent for ->, same-domain for /,
and admissibility constraints.
"""

from __future__ import annotations

import random
from typing import Any

try:
    from cas_native.model.meta_logic_constructs import META_LOGIC_EXEMPLARS
except Exception:  # pragma: no cover - script-mode fallback
    META_LOGIC_EXEMPLARS = (
        "NoeticCluster{^2, ^7}",
        "StateCluster{^2^P, ^7^O}",
        "StateVariantCluster{^3^P_{F2}|A, ^2^C|f}",
        "RelationCluster{^5^P -> ^5^C, ^5^C -> ^5^E}",
        "NoeticCluster{^2, ^7} ∩ NoeticCluster{^7}",
        "^2 ∈ Noetics",
        "NoeticCluster{^2, ^7} ⊆ Noetics",
        "Coordinate{^2, P, F2, A}",
        "Product(Noetics, Domains)",
        "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})",
        "CoverOf(SubFoundations, Foundation_1, Foundation_2, Foundation_3, Foundation_4, Foundation_5, Foundation_6, Foundation_7)",
        "PartitionOf(SubFoundations, Foundation_1, Foundation_2, Foundation_3, Foundation_4, Foundation_5, Foundation_6, Foundation_7)",
    )

# Avoid hard import of compiler — passed in at init
OPERATORS = list(range(10))
DOMAINS = ["P", "C", "E", "O"]
DOMAIN_ORDER = {"P": 0, "C": 1, "E": 2, "O": 3}
DRIVES = list(range(1, 8))
REGISTERS = ["T", "A", "f", "E"]
INVOLUTION_PAIRS = [(2, 3), (5, 6), (8, 9)]
REGISTER_SET_OPEN = chr(0x27E8)
REGISTER_SET_CLOSE = chr(0x27E9)
MEMBER = chr(0x2208)
SUBSET_EQ = chr(0x2286)
INTERSECTION = chr(0x2229)

V75_REGISTER_EXEMPLARS = (
    "CO-2|T",
    "F_2|A",
    "CO-2^C_{F2}|A",
    "CO-2|T^C_{F2|A}",
)

V76_RECIPE_EXEMPLARS = (
    "Theta(Omega_refusal) = 1*CO-3^P_{F2}|A + 1*CO-3^P_{F2}|f -> Omega_refusal",
    "Theta(Omega_paper) = 3*F_2^C|A + 2*F_2^C|T -> Omega_paper",
    "Theta(Omega_book) = 2*F_2 + 3*F_3 -> Omega_book",
    "Y_T(Omega_refusal)",
    "eta(Omega_refusal)",
)

V77_REGISTER_INTEGRATION_EXEMPLARS = (
    f"CO-3^P|{REGISTER_SET_OPEN}A,f,T{REGISTER_SET_CLOSE}",
    "CO-3^P|A + CO-3^P|f + CO-3^P|T",
    "(CO-3^P|A * CO-3^P|f) = fused",
    f"CO-3^P_{{F2}}|{REGISTER_SET_OPEN}A,f,T{REGISTER_SET_CLOSE}",
    f"(CO-3^P|{REGISTER_SET_OPEN}A,f{REGISTER_SET_CLOSE} * CO-6^P|T)",
)

TYPED_META_LOGIC_EXEMPLARS = (
    "NoeticCluster{^2, ^7}",
    "StateCluster{^2^P, ^7^O}",
    "StateVariantCluster{^3^P_{F2}|A, ^2^C|f}",
    "RelationCluster{^5^P -> ^5^C, ^5^C -> ^5^E}",
    f"NoeticCluster{{^2, ^7}} {INTERSECTION} NoeticCluster{{^7}}",
    f"^2 {MEMBER} Noetics",
    f"NoeticCluster{{^2, ^7}} {SUBSET_EQ} Noetics",
    "|Noetics| = 10",
    "|States| = 40",
    "Coordinate{^2, P, F2, A}",
    "<^2, P, F2, A>",
    "Product(Noetics, Domains)",
    "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})",
    "CoverOf(SubFoundations, Foundation_1, Foundation_2, Foundation_3, Foundation_4, Foundation_5, Foundation_6, Foundation_7)",
    "PartitionOf(SubFoundations, Foundation_1, Foundation_2, Foundation_3, Foundation_4, Foundation_5, Foundation_6, Foundation_7)",
)

COMPILER_SURFACE_EXEMPLARS = (
    *V75_REGISTER_EXEMPLARS,
    *V76_RECIPE_EXEMPLARS,
    *V77_REGISTER_INTEGRATION_EXEMPLARS,
    *TYPED_META_LOGIC_EXEMPLARS,
)


def _random_state(rng: random.Random) -> str:
    op = rng.choice(OPERATORS)
    dom = rng.choice(DOMAINS)
    drv = rng.choice(DRIVES)
    return f"CO-{op}^{dom}_{{F{drv}}}"


def _random_state_in_domain(dom: str, rng: random.Random) -> str:
    op = rng.choice(OPERATORS)
    drv = rng.choice(DRIVES)
    return f"CO-{op}^{dom}_{{F{drv}}}"


def _random_register(rng: random.Random) -> str:
    return rng.choice(REGISTERS)


def _random_registered_state_in_domain(dom: str, rng: random.Random) -> str:
    state = _random_state_in_domain(dom, rng)
    return f"{state}|{_random_register(rng)}"


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
        if complexity == "meta_logic":
            return self.generate_meta_logic_expression()
        if complexity in {"compiler_surface", "surface"}:
            return self.generate_compiler_surface_expression()
        if complexity in {"v75", "v75_register", "register"}:
            return self.generate_v75_register_expression()
        if complexity in {"v76", "v76_recipe", "recipe"}:
            return self.generate_v76_recipe_expression()
        if complexity in {"v77", "v77_register", "register_integration"}:
            return self.generate_v77_register_integration_expression()
        if complexity == "simple":
            return self._gen_simple()
        elif complexity == "complex":
            return self._gen_complex()
        return self._gen_medium()

    def generate_meta_logic_expression(self) -> str:
        """Return an admitted compiler exemplar for meta-logic integration.

        These exemplars are symbolic coverage for native surfaces and should
        not be interpreted as trained model competency.
        """
        return self.rng.choice(META_LOGIC_EXEMPLARS)

    def generate_v75_register_expression(self) -> str:
        """Return a compiler-admitted v7.5 register exemplar."""
        return self.rng.choice(V75_REGISTER_EXEMPLARS)

    def generate_v76_recipe_expression(self) -> str:
        """Return a compiler-admitted v7.6 production recipe/yield exemplar."""
        return self.rng.choice(V76_RECIPE_EXEMPLARS)

    def generate_v77_register_integration_expression(self) -> str:
        """Return a compiler-admitted v7.7 register-set/integration exemplar."""
        return self.rng.choice(V77_REGISTER_INTEGRATION_EXEMPLARS)

    def generate_compiler_surface_expression(self) -> str:
        """Return a curated expression from the compiler-accepted surface."""
        return self.rng.choice(COMPILER_SURFACE_EXEMPLARS)

    def compiler_surface_exemplars(self) -> tuple[str, ...]:
        """Deterministic full corpus used for surface-coverage validation."""
        return COMPILER_SURFACE_EXEMPLARS

    def _gen_simple(self) -> str:
        """1-2 states, basic operation."""
        if self.rng.random() < 0.2:
            return self.generate_v75_register_expression()

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
        if self.rng.random() < 0.15:
            return self.generate_v77_register_integration_expression()

        parts: list[str] = []
        num = self.rng.randint(2, 4)
        dom = self.rng.choice(DOMAINS)

        for _ in range(num):
            if self.rng.random() < 0.15:
                drv = self.rng.choice(DRIVES)
                parts.append(f"RPM(F{drv})")
            elif self.rng.random() < 0.2:
                parts.append(_random_registered_state_in_domain(dom, self.rng))
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
        if self.rng.random() < 0.2:
            return self.rng.choice(
                V76_RECIPE_EXEMPLARS
                + V77_REGISTER_INTEGRATION_EXEMPLARS
                + TYPED_META_LOGIC_EXEMPLARS
            )

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
