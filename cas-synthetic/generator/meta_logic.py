"""CAS meta-logic / cluster / diagram-capable construct generator.

This bucket emits only compiler-admitted finite typed set, cluster,
coordinate, product, cover, partition, and finite-meet pullback examples.
`Pullback(...)` is represented honestly as the admitted finite
meet/intersection constructor over finite clusters, not as a general
categorical pullback.

Operand randomization (CAS SDG Day 2): each construct's
``expression_template`` declares its randomizable slots in
``meta_logic_templates.yaml``. At emission time the generator samples
fresh operands per slot, renders the expression, and compile-validates
it against ``api.notation.compile_expression``. On compile failure the
generator retries (capped at ``_MAX_RENDER_RETRIES``) and falls back to
the literal ``expression`` field if all retries fail. The construct
family is preserved across randomization (NoeticCluster stays
NoeticCluster, Pullback stays Pullback, etc.); only operand-level
details vary.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml

from .base import BaseGenerator, GeneratedExample


_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "meta_logic_templates.yaml"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPILER_PATH = (
    _REPO_ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "notation"
    / "compiler.py"
)

_MAX_RENDER_RETRIES = 10

_DOMAIN_ORDER = ["P", "C", "E", "O"]
_BUILTIN_CARRIERS = ("Noetics", "Domains", "Drives", "Registers", "States", "Foundations")
_FOUNDATION_NAMES = tuple(f"Foundation_{i}" for i in range(1, 8))


def _load_compile_expression():
    """Load ``api.notation.compile_expression`` by absolute path.

    The hyphenated parent directory ``noetic-compass-scaffold`` is not
    a valid Python package name, so we load the compiler module by file
    path. Cached in ``sys.modules`` after first use.
    """
    module_name = "cas_notation_compiler_meta_logic"
    if module_name in sys.modules:
        return sys.modules[module_name].compile_expression
    spec = importlib.util.spec_from_file_location(module_name, _COMPILER_PATH)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:  # pragma: no cover - environment-dependent
        return None
    return getattr(module, "compile_expression", None)


_COMPILE_EXPRESSION = None


def _get_compiler():
    global _COMPILE_EXPRESSION
    if _COMPILE_EXPRESSION is None:
        _COMPILE_EXPRESSION = _load_compile_expression()
    return _COMPILE_EXPRESSION


# ---------------------------------------------------------------------------
# Coverage extraction (used by the metrics bookkeeping in the validator;
# duplicated locally here so the generator can populate `states` honestly
# from whatever it actually emitted).
# ---------------------------------------------------------------------------

_NOETIC_RE = re.compile(r"\^(\d)")
_DOMAIN_RE = re.compile(r"\^\d\^([PCEO])")
_REGISTER_RE = re.compile(r"\|([TAfE])(?![a-zA-Z])")


def _extract_states_from_expr(expr: str) -> list[tuple[int, str]]:
    """Return a deduplicated list of (noetic, domain) state pairs.

    State pairs are pulled from the ``^N^D`` substrings; bare ``^N``
    occurrences without a domain are mapped to a default domain so the
    score vector still receives signal. We default missing domains to
    ``"P"`` (the highest precedence) since the generator emits Noetic-
    only clusters as Noetic-level carriers.
    """
    pairs: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()
    # Find all ^N^D first, mark those positions
    for m in _DOMAIN_RE.finditer(expr):
        n = int(m.group(0)[1])
        d = m.group(1)
        if (n, d) not in seen:
            seen.add((n, d))
            pairs.append((n, d))
    # Find bare ^N not followed by ^D
    bare_re = re.compile(r"\^(\d)(?!\^[PCEO])")
    for m in bare_re.finditer(expr):
        n = int(m.group(1))
        # Skip if any (n, d) already recorded (avoid double-counting)
        if any(p == n for p, _ in pairs):
            continue
        key = (n, "P")
        if key not in seen:
            seen.add(key)
            pairs.append(key)
    if not pairs:
        # Nothing extracted (e.g. coordinates with carriers only) — use a
        # neutral fallback so the score vector stays well-formed.
        pairs.append((0, "P"))
    return pairs


def _extract_registers(expr: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in _REGISTER_RE.finditer(expr):
        r = m.group(1)
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# MetaLogicGenerator
# ---------------------------------------------------------------------------


class MetaLogicGenerator(BaseGenerator):
    BUCKET = "meta_logic"

    def __init__(
        self,
        seed: int | None = None,
        llm_provider: Any = None,
        template_path: Path | None = None,
    ) -> None:
        super().__init__(seed=seed, llm_provider=llm_provider)
        with open(template_path or _TEMPLATE_PATH, encoding="utf-8") as f:
            self.templates = yaml.safe_load(f)
        self.constructs = self.templates["constructs"]
        if not self.constructs:
            raise RuntimeError("meta-logic templates contain no constructs")

    # ----------------------------------------------------------------- emit

    def _generate_one(self) -> GeneratedExample:
        construct = self.rng.choice(self.constructs)
        family = construct["family"]

        rendered: dict[str, Any] | None = None
        if "expression_template" in construct and "slots" in construct:
            rendered = self._render_with_retries(construct)

        if rendered is None:
            # Fall back to the literal example expression preserved on the
            # construct. Always available; always compiles by invariant.
            literal_states = [
                (int(n), str(d)) for n, d in construct.get("states", [])
            ]
            literal_registers = list(construct.get("registers", []))
            rendered = {
                "expression": construct["expression"],
                "context": {},
                "states": literal_states or _extract_states_from_expr(construct["expression"]),
                "registers": literal_registers or _extract_registers(construct["expression"]),
            }

        expression = rendered["expression"]
        context = rendered["context"]
        states = rendered["states"]
        registers = rendered["registers"]

        prompt = self._render_text(
            construct.get("prompt_templates"),
            fallback=construct.get("prompt"),
            context=context,
            expression=expression,
        )
        response_body = self._render_text(
            construct.get("response_templates"),
            fallback=construct.get("response"),
            context=context,
            expression=expression,
        )
        response = f"{response_body} Construct family: {family}."

        register_labels = [
            {"position": i, "register": reg} for i, reg in enumerate(registers)
        ]

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

    # ------------------------------------------------------- text rendering

    def _render_text(
        self,
        templates: list[str] | None,
        *,
        fallback: str | None,
        context: dict[str, Any],
        expression: str,
    ) -> str:
        if templates:
            template = self.rng.choice(templates)
        elif fallback is not None:
            template = fallback
        else:
            template = ""
        ctx = dict(context)
        ctx.setdefault("expression", expression)
        try:
            return _safe_substitute(template, ctx)
        except KeyError:
            # Unknown placeholder: hand back the raw template rather than crash.
            return template

    # -------------------------------------------------- expression rendering

    def _render_with_retries(self, construct: dict[str, Any]) -> dict[str, Any] | None:
        compile_expression = _get_compiler()
        for _ in range(_MAX_RENDER_RETRIES):
            try:
                rendered = self._render_construct(construct)
            except _RenderConstraintError:
                continue
            if compile_expression is None:
                # No compiler available (test environment without scaffold):
                # accept the rendered expression as long as rendering succeeded.
                return rendered
            try:
                artifact = compile_expression(rendered["expression"])
            except Exception:  # pragma: no cover - defensive
                continue
            if getattr(artifact, "valid", False):
                return rendered
        return None

    def _render_construct(self, construct: dict[str, Any]) -> dict[str, Any]:
        slots: dict[str, dict[str, Any]] = construct.get("slots", {}) or {}
        # Order slots so that slots with `share_with` / `subset_of` are
        # rendered after the slot they depend on.
        slot_names = self._order_slots(slots)
        slot_values: dict[str, dict[str, Any]] = {}
        for name in slot_names:
            spec = slots[name]
            slot_values[name] = self._sample_slot(spec, slot_values)

        expression = _safe_substitute(
            construct["expression_template"],
            {k: v["text"] for k, v in slot_values.items()},
        )

        # Build context for prompt/response substitution
        context: dict[str, Any] = {}
        for name, info in slot_values.items():
            context[name] = info["text"]
            for k, v in info.get("derived", {}).items():
                context[f"{name}_{k}"] = v
                # Also expose under bare derived name for the first slot.
                # (e.g. ${noetic_list} from a `noetics` slot.)
                context.setdefault(k, v)

        # Aggregate state pairs and registers from all slot infos.
        state_pairs: list[tuple[int, str]] = []
        registers: list[str] = []
        for info in slot_values.values():
            for sp in info.get("states", []):
                if sp not in state_pairs:
                    state_pairs.append(sp)
            for reg in info.get("registers", []):
                if reg not in registers:
                    registers.append(reg)
        if not state_pairs:
            state_pairs = _extract_states_from_expr(expression)
        if not registers:
            registers = _extract_registers(expression)

        return {
            "expression": expression,
            "context": context,
            "states": state_pairs,
            "registers": registers,
        }

    @staticmethod
    def _order_slots(slots: dict[str, dict[str, Any]]) -> list[str]:
        # Two-pass topological ordering: dependents declare share_with/subset_of.
        deferred: list[str] = []
        ordered: list[str] = []
        for name, spec in slots.items():
            if "share_with" in spec or "subset_of" in spec:
                deferred.append(name)
            else:
                ordered.append(name)
        ordered.extend(deferred)
        return ordered

    # ------------------------------------------------- per-slot samplers

    def _sample_slot(
        self,
        spec: dict[str, Any],
        prior: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        kind = spec["kind"]
        if kind == "single_noetic":
            n = self.rng.choice(self.NOETICS)
            return {"text": str(n), "states": [(n, "P")], "derived": {"value": str(n)}}
        if kind == "single_domain":
            d = self.rng.choice(self.DOMAINS)
            return {"text": d, "states": [], "derived": {"value": d}}
        if kind == "single_drive":
            f = self.rng.choice(self.DRIVES)
            return {"text": str(f), "states": [], "derived": {"value": str(f)}}
        if kind == "single_register":
            # Bare register letter (e.g. inside Coordinate{^2, P, F2, A});
            # not a |R suffix, so do NOT propagate to register_labels.
            r = self.rng.choice(self.REGISTERS)
            return {"text": r, "states": [], "derived": {"value": r}}
        if kind == "builtin_carrier":
            c = self.rng.choice(_BUILTIN_CARRIERS)
            return {"text": c, "states": [], "derived": {"value": c}}
        if kind == "foundation_permutation":
            indices = list(range(1, 8))
            self.rng.shuffle(indices)
            names = [f"Foundation_{i}" for i in indices]
            return {
                "text": ", ".join(names),
                "states": [],
                "derived": {"order": ", ".join(str(i) for i in indices)},
            }
        if kind == "noetic_subset":
            return self._sample_noetic_subset(spec)
        if kind == "state_subset":
            return self._sample_state_subset(spec)
        if kind == "state_variant_subset":
            return self._sample_state_variant_subset(spec)
        if kind == "relation_chain":
            return self._sample_relation_chain(spec)
        if kind == "noetic_cluster":
            return self._sample_noetic_cluster(spec, prior)
        if kind == "state_cluster":
            return self._sample_state_cluster(spec, prior)
        raise _RenderConstraintError(f"unknown slot kind {kind!r}")

    # -- subset-style samplers ---------------------------------------------

    def _sample_noetic_subset(self, spec: dict[str, Any]) -> dict[str, Any]:
        lo, hi = int(spec.get("min", 1)), int(spec.get("max", 5))
        size = self.rng.randint(lo, min(hi, len(self.NOETICS)))
        chosen = self.rng.sample(self.NOETICS, size)
        text = ", ".join(f"^{n}" for n in chosen)
        list_text = ", ".join(str(n) for n in chosen)
        return {
            "text": text,
            "states": [(n, "P") for n in chosen],
            "derived": {
                "noetic_list": list_text,
                "noetic_count": str(size),
                "count": str(size),
            },
        }

    def _sample_state_subset(self, spec: dict[str, Any]) -> dict[str, Any]:
        lo, hi = int(spec.get("min", 1)), int(spec.get("max", 5))
        size = self.rng.randint(lo, min(hi, 40))
        # Construct (noetic, domain) pairs with no duplicates.
        chosen: list[tuple[int, str]] = []
        attempts = 0
        max_attempts = size * 8
        used: set[tuple[int, str]] = set()
        while len(chosen) < size and attempts < max_attempts:
            attempts += 1
            n = self.rng.choice(self.NOETICS)
            d = self.rng.choice(self.DOMAINS)
            if (n, d) in used:
                continue
            used.add((n, d))
            chosen.append((n, d))
        if not chosen:
            raise _RenderConstraintError("could not sample non-empty state subset")
        text = ", ".join(f"^{n}^{d}" for n, d in chosen)
        domain_list = ", ".join(sorted({d for _, d in chosen}, key=_DOMAIN_ORDER.index))
        state_list = ", ".join(f"noetic {n} in {d}" for n, d in chosen)
        return {
            "text": text,
            "states": list(chosen),
            "derived": {
                "state_count": str(len(chosen)),
                "count": str(len(chosen)),
                "domain_list": domain_list,
                "state_list": state_list,
            },
        }

    def _sample_state_variant_subset(self, spec: dict[str, Any]) -> dict[str, Any]:
        lo, hi = int(spec.get("min", 1)), int(spec.get("max", 4))
        size = self.rng.randint(lo, hi)
        # Variants: ^N^D[_{Fk}]|R or ^N^D|R or ^N|R or ^N^D_{Fk}
        # The simplest universally-admissible form is ^N^D|R.
        # Mix in some with drive: ^N^D_{Fk}|R.
        chosen_atoms: list[tuple[int, str, int | None, str]] = []
        used: set[tuple[int, str, int | None, str]] = set()
        attempts = 0
        max_attempts = size * 8
        while len(chosen_atoms) < size and attempts < max_attempts:
            attempts += 1
            n = self.rng.choice(self.NOETICS)
            d = self.rng.choice(self.DOMAINS)
            include_drive = self.rng.random() < 0.6
            f = self.rng.choice(self.DRIVES) if include_drive else None
            r = self.rng.choice(self.REGISTERS)
            tup = (n, d, f, r)
            if tup in used:
                continue
            used.add(tup)
            chosen_atoms.append(tup)
        if not chosen_atoms:
            raise _RenderConstraintError("could not sample non-empty state-variant subset")

        def _atom_text(t: tuple[int, str, int | None, str]) -> str:
            n, d, f, r = t
            if f is not None:
                return f"^{n}^{d}_{{F{f}}}|{r}"
            return f"^{n}^{d}|{r}"

        text = ", ".join(_atom_text(t) for t in chosen_atoms)
        state_pairs = [(n, d) for n, d, _, _ in chosen_atoms]
        registers = [r for *_, r in chosen_atoms]
        return {
            "text": text,
            "states": state_pairs,
            "registers": registers,
            "derived": {
                "variant_count": str(len(chosen_atoms)),
                "count": str(len(chosen_atoms)),
            },
        }

    def _sample_relation_chain(self, spec: dict[str, Any]) -> dict[str, Any]:
        lo, hi = int(spec.get("min", 2)), int(spec.get("max", 4))
        # Domain descent: pick a chain of domains in P > C > E > O order
        # of length count+1, then form arrows (state_i -> state_{i+1}).
        max_chain_len = min(hi + 1, len(_DOMAIN_ORDER))
        min_chain_len = max(lo + 1, 2)
        if min_chain_len > max_chain_len:
            min_chain_len = max_chain_len
        chain_len = self.rng.randint(min_chain_len, max_chain_len)
        # Sample chain_len ascending domain indices
        domain_indices = sorted(self.rng.sample(range(len(_DOMAIN_ORDER)), chain_len))
        domains = [_DOMAIN_ORDER[i] for i in domain_indices]
        # Pick noetic per node — typically one noetic across the chain
        if self.rng.random() < 0.7:
            base_n = self.rng.choice(self.NOETICS)
            noetics_chain = [base_n] * chain_len
        else:
            noetics_chain = [self.rng.choice(self.NOETICS) for _ in range(chain_len)]
        relations: list[str] = []
        state_pairs: list[tuple[int, str]] = []
        for i in range(chain_len - 1):
            src = (noetics_chain[i], domains[i])
            tgt = (noetics_chain[i + 1], domains[i + 1])
            relations.append(f"^{src[0]}^{src[1]} -> ^{tgt[0]}^{tgt[1]}")
            if src not in state_pairs:
                state_pairs.append(src)
            if tgt not in state_pairs:
                state_pairs.append(tgt)
        text = ", ".join(relations)
        return {
            "text": text,
            "states": state_pairs,
            "derived": {
                "relation_count": str(len(relations)),
                "count": str(len(relations)),
                "domain_chain": " -> ".join(domains),
            },
        }

    # -- cluster-typed samplers (full bracketed form) ----------------------

    def _sample_noetic_cluster(
        self,
        spec: dict[str, Any],
        prior: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        lo, hi = int(spec.get("min", 1)), int(spec.get("max", 5))
        share_with = spec.get("share_with")
        share_min = int(spec.get("share_min", 0))
        if share_with is not None and share_with in prior:
            other_states = prior[share_with].get("states", [])
            other_noetics = sorted({n for n, _ in other_states})
            if not other_noetics:
                raise _RenderConstraintError("share_with has no noetics")
            shared_count = max(share_min, 1)
            shared_count = min(shared_count, len(other_noetics))
            shared = self.rng.sample(other_noetics, shared_count)
            remaining = [n for n in self.NOETICS if n not in shared]
            extra_lo = max(0, lo - len(shared))
            extra_hi = max(0, hi - len(shared))
            extra_count = self.rng.randint(extra_lo, max(extra_hi, extra_lo))
            extra_count = min(extra_count, len(remaining))
            extra = self.rng.sample(remaining, extra_count) if extra_count > 0 else []
            chosen = sorted(set(shared + extra))
        else:
            size = self.rng.randint(lo, min(hi, len(self.NOETICS)))
            chosen = sorted(self.rng.sample(self.NOETICS, size))
        if not chosen:
            raise _RenderConstraintError("noetic_cluster sample produced empty set")
        inner = ", ".join(f"^{n}" for n in chosen)
        text = f"NoeticCluster{{{inner}}}"
        return {
            "text": text,
            "states": [(n, "P") for n in chosen],
            "derived": {"count": str(len(chosen))},
        }

    def _sample_state_cluster(
        self,
        spec: dict[str, Any],
        prior: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        lo, hi = int(spec.get("min", 1)), int(spec.get("max", 4))
        share_with = spec.get("share_with")
        share_min = int(spec.get("share_min", 0))
        subset_of = spec.get("subset_of")

        if subset_of is not None and subset_of in prior:
            parent = prior[subset_of].get("states", [])
            if not parent:
                raise _RenderConstraintError("subset_of has no states")
            size = self.rng.randint(min(lo, len(parent)), min(hi, len(parent)))
            size = max(1, size)
            chosen = self.rng.sample(parent, size)
        elif share_with is not None and share_with in prior:
            other = prior[share_with].get("states", [])
            if not other:
                raise _RenderConstraintError("share_with has no states")
            shared_count = max(share_min, 1)
            shared_count = min(shared_count, len(other))
            shared = self.rng.sample(other, shared_count)
            remaining_pool: list[tuple[int, str]] = []
            for n in self.NOETICS:
                for d in self.DOMAINS:
                    if (n, d) not in shared:
                        remaining_pool.append((n, d))
            extra_lo = max(0, lo - len(shared))
            extra_hi = max(0, hi - len(shared))
            extra_count = self.rng.randint(extra_lo, max(extra_hi, extra_lo))
            extra_count = min(extra_count, len(remaining_pool))
            extra = self.rng.sample(remaining_pool, extra_count) if extra_count > 0 else []
            # Deduplicate while preserving order
            chosen: list[tuple[int, str]] = []
            for sp in shared + extra:
                if sp not in chosen:
                    chosen.append(sp)
        else:
            size = self.rng.randint(lo, min(hi, 40))
            pool: list[tuple[int, str]] = [(n, d) for n in self.NOETICS for d in self.DOMAINS]
            chosen = self.rng.sample(pool, size)

        if not chosen:
            raise _RenderConstraintError("state_cluster sample produced empty set")
        inner = ", ".join(f"^{n}^{d}" for n, d in chosen)
        text = f"StateCluster{{{inner}}}"
        return {
            "text": text,
            "states": list(chosen),
            "derived": {"count": str(len(chosen))},
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _RenderConstraintError(RuntimeError):
    """Raised when an internal sampling constraint cannot be satisfied.

    The ``_render_with_retries`` loop catches this and retries with fresh
    operands (up to ``_MAX_RENDER_RETRIES`` attempts) before falling back
    to the literal example expression.
    """


_PLACEHOLDER_RE = re.compile(r"\$\{(\w+)\}")


def _safe_substitute(template: str, mapping: dict[str, Any]) -> str:
    """Substitute ``${name}`` placeholders.

    Unknown placeholders raise ``KeyError``. We use a hand-rolled regex
    rather than ``string.Template`` to avoid issues with dollar-signs in
    expressions or YAML-style literals.
    """
    def _resolve(match: re.Match) -> str:
        name = match.group(1)
        if name not in mapping:
            raise KeyError(name)
        return str(mapping[name])
    return _PLACEHOLDER_RE.sub(_resolve, template)
