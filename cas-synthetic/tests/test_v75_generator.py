"""Tests for V75RegisterGenerator.

Updated 2026-04-27 (Phase 2.6 v75 diversification): the generator now
emits six form families (compound, paired co-presence, compound-no-drive,
noetic-only, drive-only, independent-register) per the v7.5 grammar.
Tests that previously asserted the canonical-compound surface form on
every emission are relaxed to test compile-validity and label invariants
across the full form pool.
"""

from __future__ import annotations

import re

from cas_synthetic.generator import V75RegisterGenerator


# Operand regex covering all six v7.5 form families. Captures any
# `^N` prefix optionally followed by `^D` and/or `_{F<k>...}`, terminating
# at a `|R` annotation, OR a `F_k|R` / `Fk|R` drive-only form.
_NOETIC_OPERAND_RE = re.compile(r"\^(\d+)(?:\^([PCEO]))?(?:_\{F(\d)(?:\|[TAfE])?\})?\|([TAfE])")
_DRIVE_ONLY_RE = re.compile(r"(?<!\^)F_?(\d)\|([TAfE])")


class TestV75Register:
    def test_bucket_tag(self):
        gen = V75RegisterGenerator(seed=1)
        ex = next(gen.iter_examples(1))
        assert ex.bucket == "v75_register"

    def test_has_register_labels(self):
        gen = V75RegisterGenerator(seed=1)
        for ex in gen.iter_examples(40):
            assert ex.register_labels, "expected register labels populated"
            for lbl in ex.register_labels:
                assert lbl["register"] in ("T", "A", "f", "E")

    def test_register_in_expression(self):
        """Every emission contains at least one register annotation, and
        the registers extracted from the expression match those in
        register_labels (modulo the independent-form drive-register)."""
        gen = V75RegisterGenerator(seed=1)
        for ex in gen.iter_examples(80):
            noetic_matches = _NOETIC_OPERAND_RE.findall(ex.cas_expression)
            drive_matches = _DRIVE_ONLY_RE.findall(ex.cas_expression)
            # At least one register-annotated operand must be present.
            assert noetic_matches or drive_matches, (
                f"no register-annotated operand found in {ex.cas_expression!r}"
            )
            # Every label register must occur somewhere in the expression.
            label_regs = {lbl["register"] for lbl in ex.register_labels}
            expr_regs: set[str] = set()
            for m in noetic_matches:
                # m = (noetic, domain_or_empty, drive_or_empty, register)
                if m[3]:
                    expr_regs.add(m[3])
                # If the {F<k>|R_d} form was matched, the inner R_d
                # appears in the expression too — extract it directly.
            for m in drive_matches:
                if m[1]:
                    expr_regs.add(m[1])
            # Drive-level registers inside `_{Fk|R}` aren't captured by
            # _NOETIC_OPERAND_RE's terminal group; pick them up directly.
            for m in re.findall(r"_\{F\d\|([TAfE])\}", ex.cas_expression):
                expr_regs.add(m)
            assert label_regs <= expr_regs, (
                f"label registers {label_regs} not all present in expression "
                f"{ex.cas_expression!r} (extracted {expr_regs})"
            )

    def test_no_omega_or_production(self):
        gen = V75RegisterGenerator(seed=1)
        for ex in gen.iter_examples(40):
            assert ex.omega_labels == []
            assert ex.production_target is None

    def test_affective_is_lowercase(self):
        """Clarification 8 mandates lowercase f for Affective."""
        gen = V75RegisterGenerator(seed=1)
        for ex in gen.iter_examples(80):
            # The wrong form would be `|F_<digit>` or `|F` as register.
            # Lowercase f is canonical; uppercase F as a register letter is
            # the failure mode this test guards against.
            assert "|F_" not in ex.cas_expression
            for lbl in ex.register_labels:
                assert lbl["register"] != "F"

    def test_seed_reproducibility(self):
        g1 = V75RegisterGenerator(seed=11)
        g2 = V75RegisterGenerator(seed=11)
        a = list(g1.iter_examples(5))
        b = list(g2.iter_examples(5))
        assert [x.cas_expression for x in a] == [x.cas_expression for x in b]

    def test_is_valid_true(self):
        gen = V75RegisterGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.is_valid is True

    def test_form_diversity(self):
        """The diversification rewrite must surface multiple form families
        across a moderate sample, not collapse to a single shape."""
        gen = V75RegisterGenerator(seed=7)
        exprs = [ex.cas_expression for ex in gen.iter_examples(200)]
        # Heuristic: we should see paired (`+`), bare-noetic (`^N|R` not
        # followed by `^D`), and compound forms in 200 emissions.
        has_paired = any(" + " in e for e in exprs)
        has_compound = any(re.search(r"\^\d\^[PCEO]_\{F\d\}\|[TAfE]", e) for e in exprs)
        # Bare noetic-only: `^N|R` not preceded by anything and not followed by `^[PCEO]` or `_`.
        has_noetic_only = any(
            re.fullmatch(r"\^\d\|[TAfE]", e) for e in exprs
        )
        assert has_paired, "expected at least one paired co-presence form in 200 samples"
        assert has_compound, "expected at least one canonical compound form in 200 samples"
        assert has_noetic_only, "expected at least one noetic-only form in 200 samples"

    def test_paired_states_distinct(self):
        """Paired co-presence (`S1 + S2`) must use distinct (N, D, F)
        states — same-(N,D,F) cross-register expressions belong to
        v77_rule_four / v77_omega, not v75."""
        gen = V75RegisterGenerator(seed=13)
        for ex in gen.iter_examples(300):
            if " + " not in ex.cas_expression:
                continue
            # Extract the two operand triples (N, D, F) from each side.
            ops = re.findall(
                r"\^(\d+)(?:\^([PCEO]))?(?:_\{F(\d)\})?\|[TAfE]",
                ex.cas_expression,
            )
            if len(ops) >= 2:
                a, b = ops[0], ops[1]
                assert a != b, (
                    f"paired co-presence with identical (N,D,F): {ex.cas_expression!r}"
                )

    def test_unique_form_pool_grows(self):
        """At n=300 the generator should yield > 250 distinct expressions
        (ensures the diversification took — pre-fix, n=300 saturated near
        ~120 distinct forms)."""
        gen = V75RegisterGenerator(seed=21)
        exprs = {ex.cas_expression for ex in gen.iter_examples(300)}
        assert len(exprs) > 250, (
            f"expected >250 distinct exprs at n=300, got {len(exprs)}"
        )
