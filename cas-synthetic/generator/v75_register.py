"""v7.5 register-annotated generator.

Produces examples where each CAS state carries a register annotation
(|T, |A, |f, |E) per Clarification 8. Emits register_labels per the
data_format.md schema — one entry per register-annotated position.

Diversification overhaul (2026-04-27, Phase 2.6 pre-final-retry hardening):
Phase 2 retry analysis surfaced v75_register at 20.0% redundancy at n=2500
(~499 extra copies). Root cause: emitted only the canonical compound
`^N^D_{Fk}|R` and a same-domain two-state `*` form, yielding a form pool
of ~1120 unique compound singles plus a saturable pair pool. With 2500
samples, collisions are mathematically unavoidable.

This rewrite expands across six form families admitted by the v7.5 grammar
(Clarification 8) and Clarification 10 operator discipline:

  1. Compound `^N^D_{Fk}|R`                — canonical baseline (35%)
  2. Paired co-presence `S1 + S2`          — primary diversifier (35%)
                                              S1, S2 are DISTINCT states
                                              (different Noetic OR Domain
                                              OR Drive — at least one
                                              axis differs). Same-Noetic
                                              cross-register expressions
                                              with identical (N,D,F) are
                                              v77_rule_four / v77_omega
                                              territory and are explicitly
                                              excluded here.
  3. Compound-without-drive `^N^D|R`       — moderate pool (10%)
  4. Noetic-only `^N|R`                    — small pool, sampled sparsely (8%)
  5. Drive-only `F_k|R`                    — small pool, sampled sparsely (7%)
  6. Independent-register edge case        — ~5% rare edge form
        `^N^D_{Fk|R_d}|R_n` (drive-level register inside the subscript,
        Noetic-level register on the outside) — admitted by the v7.5
        grammar, used here as low-rate edge coverage.

Form-pool size after expansion:
  - Single compound: 10×4×7×4 = 1120
  - Paired (distinct): ~1.25M unique ordered pairs (1120² minus same-state)
  - Compound-no-drive: 10×4×4 = 160
  - Noetic-only: 10×4 = 40
  - Drive-only: 7×4 = 28
  - Independent: 10×4×7×4×4 = 4480

The paired co-presence pool dominates the unique-form total at any
sample size, so 2500 samples are far below saturation.

Compile-validate every emission via the live compiler with retry/fallback.
Counters `compile_retries` and `compile_fallbacks` are exposed for
instrumentation parity with v77_rule_four and meta_logic.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import yaml

from .base import BaseGenerator, GeneratedExample


_V74_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "v74_templates.yaml"
_V75_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "v75_templates.yaml"
_COMPILER_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "notation"
    / "compiler.py"
)


def _load_compiler():
    """Load the compiler module by file path. Returns None if unavailable.

    Headless test fixtures may not have the noetic-compass scaffold present;
    in that case round-trip validation is skipped and the regime is trusted.
    """
    module_name = "cas_synthetic_v75_register_compiler"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _COMPILER_PATH)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    return module


# Sampling distribution across the six form families. Tuned for diversity
# at n=2500 while preserving a strong compound baseline (the simplest form
# is also the most pedagogically central, so it earns the largest share).
#
# Pool-saturation calibration: at n=2500 the small-pool families
# (noetic_only=40 forms, drive_only=28 forms, compound_no_drive=160 forms)
# saturate well below the original 8/7/10% weights. The weights below
# keep small-pool sampling at-or-below the pool size while letting the
# large-pool families (paired ~1.25M, compound 1120, independent 4480)
# absorb the bulk of the volume.
_FORM_WEIGHTS: dict[str, float] = {
    "compound": 0.30,            # ^N^D_{Fk}|R    — 1120 forms
    "paired": 0.55,              # S1 + S2        — ~1.25M unique pairs
    "compound_no_drive": 0.06,   # ^N^D|R         — 160 forms (≈150 samples at n=2500)
    "noetic_only": 0.02,         # ^N|R           — 40 forms (≈50 samples; 1-2 unavoidable repeats)
    "drive_only": 0.02,          # F_k|R          — 28 forms (≈50 samples; 1-2 unavoidable repeats)
    "independent": 0.05,         # ^N^D_{Fk|R_d}|R_n — 4480 forms
}


class V75RegisterGenerator(BaseGenerator):
    BUCKET = "v75_register"

    def __init__(
        self,
        seed: int | None = None,
        llm_provider: Any = None,
        template_path: Path | None = None,
        v74_template_path: Path | None = None,
    ) -> None:
        super().__init__(seed=seed, llm_provider=llm_provider)
        with open(template_path or _V75_TEMPLATES, encoding="utf-8") as f:
            self.templates = yaml.safe_load(f)
        with open(v74_template_path or _V74_TEMPLATES, encoding="utf-8") as f:
            self.v74_templates = yaml.safe_load(f)

        # Lazy-load the compiler for round-trip validation. None when the
        # compiler can't be loaded (headless tests); validation skipped.
        self._compiler = _load_compiler()
        # Counters for compile-retry instrumentation, parity with
        # v77_rule_four and meta_logic generators.
        self.compile_retries = 0
        self.compile_fallbacks = 0

        # Pre-build the form-family choice list so weights are sampled with
        # rng.choices on every call. Order is deterministic.
        self._form_keys = list(_FORM_WEIGHTS.keys())
        self._form_weights = [_FORM_WEIGHTS[k] for k in self._form_keys]

    # ----------------------------------------------------------- public hook

    def _generate_one(self) -> GeneratedExample:
        # Sample a form family; each family is a separate generator method.
        # Internal retry-with-fallback keeps the streaming contract intact
        # even when the compiler rejects an unlikely edge form.
        form = self.rng.choices(self._form_keys, weights=self._form_weights)[0]
        if form == "compound":
            return self._generate_compound()
        if form == "paired":
            return self._generate_paired()
        if form == "compound_no_drive":
            return self._generate_compound_no_drive()
        if form == "noetic_only":
            return self._generate_noetic_only()
        if form == "drive_only":
            return self._generate_drive_only()
        if form == "independent":
            return self._generate_independent()
        # Defensive: should not reach.
        return self._generate_compound()

    # --------------------------------------------------- form: compound `^N^D_{Fk}|R`

    def _generate_compound(self) -> GeneratedExample:
        """Canonical compound `^N^D_{Fk}|R` — 1120 unique forms."""
        for _ in range(4):
            noetic = self.rng.choice(self.NOETICS)
            domain = self.rng.choice(self.DOMAINS)
            drive = self.rng.choice(self.DRIVES)
            register = self.rng.choice(self.REGISTERS)
            expression = f"^{noetic}^{domain}_{{F{drive}}}|{register}"
            if not self._compile_ok(expression):
                self.compile_retries += 1
                continue
            states = [(noetic, domain)]
            register_labels = [{"position": 0, "register": register}]
            return self._build_example(
                expression=expression,
                states=states,
                register_labels=register_labels,
                form_label="compound",
            )
        # Fallback — known-good compound.
        self.compile_fallbacks += 1
        expression = "^3^P_{F2}|A"
        states = [(3, "P")]
        register_labels = [{"position": 0, "register": "A"}]
        return self._build_example(
            expression=expression,
            states=states,
            register_labels=register_labels,
            form_label="compound",
        )

    # --------------------------------------------------- form: paired co-presence `S1 + S2`

    def _generate_paired(self) -> GeneratedExample:
        """Paired co-presence `S1 + S2` with distinct states.

        Distinctness rule (per directive scope distinction): the two states
        must differ in at least one of (Noetic, Domain, Drive). Same-Noetic
        same-Domain same-Drive cross-register expressions are
        v77_rule_four / v77_omega territory and are explicitly excluded
        from v75 to preserve scope discipline.
        """
        for _ in range(6):
            n1 = self.rng.choice(self.NOETICS)
            d1 = self.rng.choice(self.DOMAINS)
            f1 = self.rng.choice(self.DRIVES)
            r1 = self.rng.choice(self.REGISTERS)

            n2 = self.rng.choice(self.NOETICS)
            d2 = self.rng.choice(self.DOMAINS)
            f2 = self.rng.choice(self.DRIVES)
            r2 = self.rng.choice(self.REGISTERS)

            # Enforce distinctness across at least one of (N, D, F).
            if (n1, d1, f1) == (n2, d2, f2):
                continue

            expression = (
                f"^{n1}^{d1}_{{F{f1}}}|{r1} + ^{n2}^{d2}_{{F{f2}}}|{r2}"
            )
            if not self._compile_ok(expression):
                self.compile_retries += 1
                continue
            states = [(n1, d1), (n2, d2)]
            register_labels = [
                {"position": 0, "register": r1},
                {"position": 1, "register": r2},
            ]
            return self._build_example(
                expression=expression,
                states=states,
                register_labels=register_labels,
                form_label="paired",
            )
        # Fallback — known-good distinct-state pair.
        self.compile_fallbacks += 1
        expression = "^3^P_{F2}|A + ^4^C_{F1}|f"
        states = [(3, "P"), (4, "C")]
        register_labels = [
            {"position": 0, "register": "A"},
            {"position": 1, "register": "f"},
        ]
        return self._build_example(
            expression=expression,
            states=states,
            register_labels=register_labels,
            form_label="paired",
        )

    # --------------------------------------------------- form: compound-no-drive `^N^D|R`

    def _generate_compound_no_drive(self) -> GeneratedExample:
        """Bare compound `^N^D|R` — drive subscript omitted. 160 forms."""
        for _ in range(4):
            noetic = self.rng.choice(self.NOETICS)
            domain = self.rng.choice(self.DOMAINS)
            register = self.rng.choice(self.REGISTERS)
            expression = f"^{noetic}^{domain}|{register}"
            if not self._compile_ok(expression):
                self.compile_retries += 1
                continue
            states = [(noetic, domain)]
            register_labels = [{"position": 0, "register": register}]
            return self._build_example(
                expression=expression,
                states=states,
                register_labels=register_labels,
                form_label="compound_no_drive",
            )
        self.compile_fallbacks += 1
        expression = "^3^P|A"
        states = [(3, "P")]
        register_labels = [{"position": 0, "register": "A"}]
        return self._build_example(
            expression=expression,
            states=states,
            register_labels=register_labels,
            form_label="compound_no_drive",
        )

    # --------------------------------------------------- form: noetic-only `^N|R`

    def _generate_noetic_only(self) -> GeneratedExample:
        """Noetic-only `^N|R` — 40 forms. Sampled sparsely.

        States carry None for domain (no domain present); we emit a
        per-state tuple anyway with a sentinel domain for scoring purposes
        (domain default = first cycle through DOMAINS) — the scorer
        ignores it via _scores_from_states aggregation. To keep
        register_labels consistent with the position semantics we use
        the noetic alone for the state pair.
        """
        for _ in range(4):
            noetic = self.rng.choice(self.NOETICS)
            register = self.rng.choice(self.REGISTERS)
            expression = f"^{noetic}|{register}"
            if not self._compile_ok(expression):
                self.compile_retries += 1
                continue
            # No domain present in the expression — we synthesize a
            # placeholder for the state vector by drawing a domain
            # uniformly. This keeps domain_scores sane while honoring the
            # register_labels invariant. (The cas_expression is the
            # ground-truth source; scores are derived heuristically.)
            placeholder_domain = self.rng.choice(self.DOMAINS)
            states = [(noetic, placeholder_domain)]
            register_labels = [{"position": 0, "register": register}]
            return self._build_example(
                expression=expression,
                states=states,
                register_labels=register_labels,
                form_label="noetic_only",
            )
        self.compile_fallbacks += 1
        expression = "^3|A"
        states = [(3, "P")]
        register_labels = [{"position": 0, "register": "A"}]
        return self._build_example(
            expression=expression,
            states=states,
            register_labels=register_labels,
            form_label="noetic_only",
        )

    # --------------------------------------------------- form: drive-only `F_k|R`

    def _generate_drive_only(self) -> GeneratedExample:
        """Drive-only `F_k|R` — 28 forms (alternates F_k and Fk syntax).

        The compiler accepts both `F_k|R` and `Fk|R`; we emit `F_k|R` as
        canonical (matches typeset notation) but variant via random
        choice for diversity in the literal-string surface form.
        """
        for _ in range(4):
            drive = self.rng.choice(self.DRIVES)
            register = self.rng.choice(self.REGISTERS)
            # 50/50 between subscript-underscore and bare-digit forms.
            if self.rng.random() < 0.5:
                expression = f"F_{drive}|{register}"
            else:
                expression = f"F{drive}|{register}"
            if not self._compile_ok(expression):
                self.compile_retries += 1
                continue
            # Drive-only expressions don't pin a Noetic; we synthesize a
            # placeholder so _scores_from_states stays defined. The
            # register_labels are the load-bearing supervision signal here.
            placeholder_noetic = self.rng.choice(self.NOETICS)
            placeholder_domain = self.rng.choice(self.DOMAINS)
            states = [(placeholder_noetic, placeholder_domain)]
            register_labels = [{"position": 0, "register": register}]
            return self._build_example(
                expression=expression,
                states=states,
                register_labels=register_labels,
                form_label="drive_only",
            )
        self.compile_fallbacks += 1
        expression = "F_2|A"
        states = [(0, "P")]
        register_labels = [{"position": 0, "register": "A"}]
        return self._build_example(
            expression=expression,
            states=states,
            register_labels=register_labels,
            form_label="drive_only",
        )

    # --------------------------------------------------- form: independent registers

    def _generate_independent(self) -> GeneratedExample:
        """Independent-register edge form `^N^D_{Fk|R_d}|R_n`.

        The drive subscript carries its own register R_d, distinct from
        the Noetic-level register R_n on the outside. Per v7.5 grammar
        (Clarification 8) this is an admitted form for cases where the
        Noetic and the Drive operate at different phenomenological
        registers simultaneously. Sampled at low rate (5%) as edge
        coverage; pool size 10×4×7×4×4 = 4480.
        """
        for _ in range(4):
            noetic = self.rng.choice(self.NOETICS)
            domain = self.rng.choice(self.DOMAINS)
            drive = self.rng.choice(self.DRIVES)
            r_n = self.rng.choice(self.REGISTERS)
            r_d = self.rng.choice(self.REGISTERS)
            # Sample R_n and R_d allowing same or different — when they
            # differ the form is genuinely "independent register"; when
            # they match the form collapses to the canonical compound
            # surface but with explicit drive-register annotation, which
            # is still useful supervision signal.
            expression = f"^{noetic}^{domain}_{{F{drive}|{r_d}}}|{r_n}"
            if not self._compile_ok(expression):
                self.compile_retries += 1
                continue
            states = [(noetic, domain)]
            # Per data_format.md, register_labels lists per-position
            # entries. The independent form has TWO register annotations
            # (Noetic-level and Drive-level), both load-bearing. We emit
            # both with positions 0 (outer) and 1 (drive-inner) so the
            # consumer can supervise each independently.
            register_labels = [
                {"position": 0, "register": r_n},
                {"position": 1, "register": r_d},
            ]
            return self._build_example(
                expression=expression,
                states=states,
                register_labels=register_labels,
                form_label="independent",
            )
        self.compile_fallbacks += 1
        expression = "^3^P_{F2|A}|T"
        states = [(3, "P")]
        register_labels = [
            {"position": 0, "register": "T"},
            {"position": 1, "register": "A"},
        ]
        return self._build_example(
            expression=expression,
            states=states,
            register_labels=register_labels,
            form_label="independent",
        )

    # ---------------------------------------------------- response builder

    def _build_example(
        self,
        *,
        expression: str,
        states: list[tuple[int, str]],
        register_labels: list[dict[str, Any]],
        form_label: str,
    ) -> GeneratedExample:
        """Assemble a GeneratedExample with a register-aware response string."""
        scenarios = self.templates["scenarios"]
        register_phrases = self.templates["register_phrases"]
        noetic_phrases = self.v74_templates["noetic_phrases"]
        domain_phrases = self.v74_templates["domain_phrases"]
        scenario = self.rng.choice(scenarios)

        # Build a response paragraph that walks each register-annotated
        # position. Forms with placeholder noetics/domains (drive-only)
        # still emit one descriptive sentence to keep the response
        # populated; the cas_expression is the ground truth.
        response_parts: list[str] = []
        # Pair register_labels with the underlying state (when available).
        # For compound, paired, compound_no_drive, noetic_only — labels and
        # states align 1:1. For drive_only — one label + one placeholder
        # state. For independent — two labels but only one state; the
        # second label is the Drive-level register.
        for idx, lbl in enumerate(register_labels):
            reg = lbl["register"]
            rp = self.rng.choice(register_phrases[reg])
            if idx < len(states):
                noetic, dom = states[idx]
                noetic_key = str(noetic) if str(noetic) in noetic_phrases else noetic
                np = self.rng.choice(noetic_phrases[noetic_key])
                dp = self.rng.choice(domain_phrases[dom])
                lead = scenario if idx == 0 else "They"
                response_parts.append(f"{lead} {np}, {dp}, {rp}.")
            else:
                # Independent-form drive-level register, no separate state.
                response_parts.append(
                    f"The drive itself operates {rp}."
                )
        prompt_suffix = {
            "compound": "must act with a clear register.",
            "paired": "holds two co-present register manifestations.",
            "compound_no_drive": "must act with a clear register.",
            "noetic_only": "must act with a clear register.",
            "drive_only": "operates under a register-annotated drive.",
            "independent": "carries an independent-register architecture.",
        }.get(form_label, "must act with a clear register.")
        prompt = f"{scenario} {prompt_suffix}"
        response = " ".join(response_parts)

        return GeneratedExample(
            prompt=prompt,
            response=response,
            cas_expression=expression,
            scores=self._scores_from_states(states),
            register_labels=register_labels,
            omega_labels=[],
            production_target=None,
            bucket=self.BUCKET,
            is_valid=True,
            violation_type=None,
            distance_to_valid=0.0,
        )

    # ---------------------------------------------------- helpers

    def _compile_ok(self, expression: str) -> bool:
        """Round-trip an expression through the compiler. Returns True iff
        the compiler reports valid. When the compiler can't be loaded
        (headless test fixtures), trust the regime and return True."""
        if self._compiler is None:
            return True
        try:
            artifact = self._compiler.compile_expression(expression)
            return bool(artifact.valid)
        except Exception:
            return False
