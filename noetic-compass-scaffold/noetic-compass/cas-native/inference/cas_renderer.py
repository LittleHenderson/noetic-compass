"""Pure-Python renderer for CAS structured predictions.

Takes a dict of axis values produced by the CAS-Native structured-prediction
head and produces a short, natural-language explanation suitable for echoing
back to the user (confirmation prompt style).

Authoritative Noetic names and definitions follow
``noetic-compass-scaffold/noetic-compass/CLAUDE.md`` Project Identity section.
The 10 Noetic names ("Idea", "Mind", "Positive", "Negative", "Vibration",
"Female", "Male", "Rhythm", "Above/Cause", "Below/Effect") are verbatim
canonical and are not softened.

Anti-drift constraints honored:
  - ^3 Negative is VISCERAL (aversion / repelled), not analytical.
  - ^8 Above/Cause is associative TRIGGERING, not deductive reasoning.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any


def _load_structured_prediction_labels() -> Any:
    """Load only the label tuples from ``structured_prediction.py``.

    The model package ``__init__.py`` imports torch-backed submodules eagerly,
    so importing it pulls in PyTorch. This renderer is pure-Python and only
    needs the label tuples, so we load ``structured_prediction.py`` by file
    path via ``importlib.util`` and stub out ``torch.nn``/``torch`` if
    necessary so the module-level imports in that file do not fail.

    Returns the loaded module object.
    """
    # First try a normal import; this works in environments where the
    # ``cas_native`` package shim is already in place AND torch is installed.
    try:
        return importlib.import_module("cas_native.model.structured_prediction")
    except Exception:
        pass

    # Fallback: load the .py file directly. We don't need anything that the
    # torch-backed code paths produce, only the label tuples, so we install
    # minimal torch stubs if torch is unavailable.
    here = Path(__file__).resolve()
    sp_path = here.parent.parent / "model" / "structured_prediction.py"
    if not sp_path.exists():
        raise RuntimeError(
            f"cannot locate structured_prediction.py at {sp_path}"
        )

    # Probe for a working torch.nn; if it's missing or broken (e.g. the local
    # environment has only a torch namespace package without nn), install
    # minimal stubs so module-level ``import torch.nn`` succeeds.
    nn_works = False
    try:
        import torch.nn  # noqa: F401
        nn_works = True
    except Exception:
        nn_works = False

    if not nn_works:
        import types as _types

        existing_torch = sys.modules.get("torch")
        if existing_torch is None:
            existing_torch = _types.ModuleType("torch")
            sys.modules["torch"] = existing_torch
        if not hasattr(existing_torch, "Tensor"):
            existing_torch.Tensor = object  # type: ignore[attr-defined]

        nn_stub = _types.ModuleType("torch.nn")

        class _Module:  # minimal nn.Module stub
            def __init__(self, *_a: Any, **_kw: Any) -> None:
                pass

        class _Linear(_Module):
            pass

        class _Sequential(_Module):
            pass

        class _GELU(_Module):
            pass

        class _LayerNorm(_Module):
            pass

        nn_stub.Module = _Module  # type: ignore[attr-defined]
        nn_stub.Linear = _Linear  # type: ignore[attr-defined]
        nn_stub.Sequential = _Sequential  # type: ignore[attr-defined]
        nn_stub.GELU = _GELU  # type: ignore[attr-defined]
        nn_stub.LayerNorm = _LayerNorm  # type: ignore[attr-defined]

        functional_stub = _types.ModuleType("torch.nn.functional")
        functional_stub.cross_entropy = lambda *a, **kw: None  # type: ignore[attr-defined]
        functional_stub.binary_cross_entropy_with_logits = (  # type: ignore[attr-defined]
            lambda *a, **kw: None
        )

        existing_torch.nn = nn_stub  # type: ignore[attr-defined]
        sys.modules["torch.nn"] = nn_stub
        sys.modules["torch.nn.functional"] = functional_stub

    mod_name = "_cas_renderer_structured_prediction_labels"
    spec = importlib.util.spec_from_file_location(mod_name, sp_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not build import spec for {sp_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


_sp = _load_structured_prediction_labels()
AUTHORITY_LABELS: tuple[str, ...] = _sp.AUTHORITY_LABELS
DOMAIN_LABELS: tuple[str, ...] = _sp.DOMAIN_LABELS
DRIVE_LABELS: tuple[str, ...] = _sp.DRIVE_LABELS
EXPRESSION_FAMILY_LABELS: tuple[str, ...] = _sp.EXPRESSION_FAMILY_LABELS
META_RELATION_LABELS: tuple[str, ...] = _sp.META_RELATION_LABELS
REGISTER_LABELS: tuple[str, ...] = _sp.REGISTER_LABELS
REGISTER_MODE_LABELS: tuple[str, ...] = _sp.REGISTER_MODE_LABELS
TRANSITION_KIND_LABELS: tuple[str, ...] = _sp.TRANSITION_KIND_LABELS
TURN_TYPE_LABELS: tuple[str, ...] = _sp.TURN_TYPE_LABELS


# ---------------------------------------------------------------------------
# Authoritative lookups
# ---------------------------------------------------------------------------

NOETIC_NAMES: dict[int, str] = {
    0: "Idea",
    1: "Mind",
    2: "Positive",
    3: "Negative",
    4: "Vibration",
    5: "Female",
    6: "Male",
    7: "Rhythm",
    8: "Above/Cause",
    9: "Below/Effect",
}

# Short English gloss preserving authoritative verbs. ^3 stays visceral, ^8 stays
# associative-triggering. Used for the one-sentence unpacking after the CAS
# expression. Plain-English noun phrases, not metaphors.
NOETIC_GLOSS: dict[int, str] = {
    0: "an Idea (the bare object in or outside the Mind)",
    1: "Mind awareness operating on an Idea",
    2: "an attraction (the Mind has an affinity for and is attracted toward the Idea)",
    3: "an aversion (the Mind is adverse to and repelled by the Idea)",
    4: "a resonance (the degree to which the Idea resonates with the Mind, its impression)",
    5: "an experiential composition (a Mind impregnated with the Idea, the Ideas a Mind is composed of)",
    6: "a compositional decomposition (an Idea impregnated with another Idea, the Ideas an Idea is composed of)",
    7: "a Rhythm exposure (the rate and pattern the Mind is exposed to the Idea, entraining it)",
    8: "an associative trigger (an Idea that triggers a different Idea to come to Mind)",
    9: "an Idea brought to Mind by an Above/Cause trigger",
}

DOMAIN_NAMES: dict[str, str] = {
    "P": "Principled",
    "C": "Cognitive",
    "E": "Evaluative",
    "O": "Operational",
}

DRIVE_NAMES: dict[str, str] = {
    "F1": "Unity",
    "F2": "Wisdom",
    "F3": "Vitality",
    "F4": "Connection",
    "F5": "Agency",
    "F6": "Structure",
    "F7": "Purpose",
}

REGISTER_NAMES: dict[str, str] = {
    "T": "Transcendent",
    "A": "Analytical",
    "f": "Affective",
    "E": "Embodied",
}

# Adjective form for the lead phrase ("an analytical aversion", "a felt attraction").
REGISTER_ADJECTIVE: dict[str, str] = {
    "T": "transcendent",
    "A": "analytical",
    "f": "felt",
    "E": "embodied",
}

# Short English noun phrase used as the head of the lead sentence per Noetic.
# Picks a register-compatible word: ^3 stays visceral ("aversion"), not analytical.
NOETIC_HEAD_NOUN: dict[int, str] = {
    0: "Idea reference",
    1: "Mind operation",
    2: "attraction",
    3: "aversion",
    4: "resonance",
    5: "experiential composition",
    6: "compositional decomposition",
    7: "Rhythm exposure",
    8: "associative trigger",
    9: "triggered Idea",
}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate(prediction: dict[str, Any]) -> None:
    """Lightly validate a prediction dict; raise ValueError on bad input."""
    noetic = prediction.get("noetic")
    if not isinstance(noetic, int) or not 0 <= noetic <= 9:
        raise ValueError(f"noetic must be int 0..9, got {noetic!r}")

    domain = prediction.get("domain")
    if domain not in DOMAIN_LABELS:
        raise ValueError(f"domain must be in {DOMAIN_LABELS}, got {domain!r}")

    drive = prediction.get("drive")
    if drive not in DRIVE_LABELS:
        raise ValueError(f"drive must be in {DRIVE_LABELS}, got {drive!r}")

    register_mode = prediction.get("register_mode", "none")
    if register_mode not in REGISTER_MODE_LABELS:
        raise ValueError(
            f"register_mode must be in {REGISTER_MODE_LABELS}, got {register_mode!r}"
        )

    registers = prediction.get("registers", ()) or ()
    for r in registers:
        if r not in REGISTER_LABELS:
            raise ValueError(f"register {r!r} not in {REGISTER_LABELS}")

    authority = prediction.get("authority", "none")
    if authority not in AUTHORITY_LABELS:
        raise ValueError(f"authority must be in {AUTHORITY_LABELS}, got {authority!r}")

    family = prediction.get("expression_family")
    if family is not None and family not in EXPRESSION_FAMILY_LABELS:
        raise ValueError(
            f"expression_family must be in {EXPRESSION_FAMILY_LABELS}, got {family!r}"
        )

    turn = prediction.get("turn_type")
    if turn is not None and turn not in TURN_TYPE_LABELS:
        raise ValueError(f"turn_type must be in {TURN_TYPE_LABELS}, got {turn!r}")

    transition = prediction.get("transition_kind")
    if transition is not None and transition not in TRANSITION_KIND_LABELS:
        raise ValueError(
            f"transition_kind must be in {TRANSITION_KIND_LABELS}, got {transition!r}"
        )

    metas = prediction.get("meta_relations", ()) or ()
    for m in metas:
        if m not in META_RELATION_LABELS:
            raise ValueError(f"meta_relation {m!r} not in {META_RELATION_LABELS}")


# ---------------------------------------------------------------------------
# Expression-string rendering
# ---------------------------------------------------------------------------

def _render_register_suffix(register_mode: str, registers: tuple[str, ...] | list[str]) -> str:
    """Return the |... portion of the expression (or empty string)."""
    regs = tuple(registers) if registers else ()

    if register_mode == "none" or not regs:
        return ""

    if register_mode == "single":
        return f"|{regs[0]}"

    if register_mode == "set_spec":
        joined = ",".join(regs)
        return f"|⟨{joined}⟩"  # angle brackets ⟨ ⟩

    if register_mode == "co_presence":
        # Handled at the full-expression level (terms joined by +); no
        # standalone suffix here.
        return f"|{regs[0]}" if len(regs) == 1 else ""

    if register_mode == "integration":
        # Handled at the full-expression level (× with =Ω); no suffix here.
        return f"|{regs[0]}" if len(regs) == 1 else ""

    return ""


def render_cas_expression_string(prediction: dict[str, Any]) -> str:
    """Render the canonical CAS expression notation, e.g. '^3^E_{F2}|A'.

    For multi-register ``co_presence``: ``^3^P|A + ^3^P|f + ^3^P|T``.
    For multi-register ``integration``: ``(^3^P|A × ^3^P|f × ^3^P|T) = Ω``.
    For ``set_spec``: ``^3^P|⟨A,f,T⟩``.
    For ``omega`` family with has_omega: appends ``=Ω``.
    For ``meta_logic`` family: prefixes ``meta:`` for clarity.
    """
    _validate(prediction)

    noetic = prediction["noetic"]
    domain = prediction["domain"]
    drive = prediction["drive"]
    register_mode = prediction.get("register_mode", "none")
    registers = tuple(prediction.get("registers") or ())
    family = prediction.get("expression_family")
    has_omega = bool(prediction.get("has_omega", False))
    has_meta = bool(prediction.get("has_meta_logic", False))
    authority = prediction.get("authority", "none")

    base = f"^{noetic}^{domain}_{{{drive}}}"

    # Multi-register co-presence: write the additive form explicitly.
    if register_mode == "co_presence" and len(registers) >= 2:
        terms = [f"^{noetic}^{domain}|{r}" for r in registers]
        expr = " + ".join(terms)
        if authority == "blocked":
            expr = f"[blocked] {expr}"
        elif authority == "admitted":
            expr = f"[admitted] {expr}"
        return f"meta: {expr}" if has_meta else expr

    # Multi-register integration: parenthesized × form with named result.
    if register_mode == "integration" and len(registers) >= 2:
        terms = [f"^{noetic}^{domain}|{r}" for r in registers]
        body = " × ".join(terms)  # ×
        result = f"^{noetic}^{domain}|Ω" if has_omega else f"^{noetic}^{domain}|R*"
        expr = f"({body}) = {result}"
        if authority == "blocked":
            expr = f"[blocked] {expr}"
        elif authority == "admitted":
            expr = f"[admitted] {expr}"
        return f"meta: {expr}" if has_meta else expr

    # Default: single base expression with optional register suffix.
    suffix = _render_register_suffix(register_mode, registers)
    expr = base + suffix

    if family == "omega" or has_omega:
        expr = f"{expr} = Ω"

    if authority == "blocked":
        expr = f"[blocked] {expr}"
    elif authority == "admitted":
        expr = f"[admitted] {expr}"

    if family == "meta_logic" or has_meta:
        expr = f"meta: {expr}"

    return expr


# ---------------------------------------------------------------------------
# Natural-language rendering
# ---------------------------------------------------------------------------

def _article(word: str) -> str:
    """Pick 'a' or 'an' for the given word."""
    return "an" if word and word[0].lower() in "aeiou" else "a"


def _lead_phrase(noetic: int, domain: str, registers: tuple[str, ...], register_mode: str) -> str:
    """Return the head English phrase: e.g., 'an analytical aversion'."""
    head_noun = NOETIC_HEAD_NOUN[noetic]

    # Single register: prepend the adjective form ("an analytical aversion").
    if register_mode == "single" and len(registers) == 1:
        adj = REGISTER_ADJECTIVE[registers[0]]
        phrase = f"{adj} {head_noun}"
        return f"{_article(adj)} {phrase}"

    # Set-spec / co-presence / integration: use plural / structured phrasing.
    if register_mode == "set_spec" and registers:
        adj_list = ", ".join(REGISTER_ADJECTIVE[r] for r in registers)
        phrase = f"{head_noun} present in {adj_list} registers"
        return f"{_article(head_noun)} {phrase}"

    if register_mode == "co_presence" and len(registers) >= 2:
        adj_list = ", ".join(REGISTER_ADJECTIVE[r] for r in registers)
        phrase = f"{head_noun} co-present in {adj_list} registers"
        return f"{_article(head_noun)} {phrase}"

    if register_mode == "integration" and len(registers) >= 2:
        adj_list = ", ".join(REGISTER_ADJECTIVE[r] for r in registers)
        phrase = f"cross-register integration of {head_noun} across {adj_list} registers"
        return f"{_article('cross')} {phrase}"

    # No register specified.
    return f"{_article(head_noun)} {head_noun}"


def _domain_phrase(domain: str, noetic: int) -> str:
    """Render the 'on the X domain' / 'at the X level' phrase."""
    name = DOMAIN_NAMES[domain]
    if noetic in (0, 1, 2, 3, 4):
        return f"on the {name} domain"
    return f"at the {name} level"


def _structural_addendum(prediction: dict[str, Any]) -> str:
    """Optional second-line context if structurally relevant. May be ''."""
    parts: list[str] = []

    family = prediction.get("expression_family")
    has_omega = bool(prediction.get("has_omega", False))
    has_meta = bool(prediction.get("has_meta_logic", False))
    authority = prediction.get("authority", "none")
    register_mode = prediction.get("register_mode", "none")
    meta_rels = tuple(prediction.get("meta_relations") or ())

    if authority == "blocked":
        parts.append(
            "this represents a blocked move (refusal authority) "
            "rather than an admitted one"
        )
    elif authority == "admitted":
        parts.append(
            "this is an explicitly admitted move (admission authority)"
        )

    if family == "omega":
        parts.append(
            "the head expression is an integrated cross-axis commitment "
            "('omega bind')"
        )
    elif has_omega:
        parts.append("with an integrated emergent state (Omega) on top")

    if family == "meta_logic" or has_meta:
        rels = ", ".join(meta_rels) if meta_rels else ""
        if rels:
            parts.append(
                f"this is a meta-logical statement about CAS structure "
                f"(relations: {rels})"
            )
        else:
            parts.append("this is a meta-logical statement about CAS structure")

    if register_mode == "integration":
        parts.append(
            "the registers enter a genuine cross-register integration "
            "yielding an emergent fused state"
        )
    elif register_mode == "co_presence":
        parts.append(
            "the registers are co-present but remain structurally distinct"
        )
    elif register_mode == "set_spec":
        parts.append(
            "this is an architectural register-set specification, "
            "not a behavioral integration claim"
        )

    if not parts:
        return ""

    # Capitalize first sentence; join with semicolons; end with period.
    first, *rest = parts
    sentence = first[0].upper() + first[1:]
    if rest:
        sentence = sentence + "; " + "; ".join(rest)
    return sentence + "."


def render_cas_prediction(prediction: dict[str, Any]) -> str:
    """Render a CAS prediction as a short natural-language explanation.

    Returns a 2-4 sentence string suitable for echoing back to a user.
    """
    _validate(prediction)

    expr = render_cas_expression_string(prediction)

    noetic = prediction["noetic"]
    domain = prediction["domain"]
    drive = prediction["drive"]
    registers = tuple(prediction.get("registers") or ())
    register_mode = prediction.get("register_mode", "none")
    family = prediction.get("expression_family")
    has_omega = bool(prediction.get("has_omega", False))
    has_meta = bool(prediction.get("has_meta_logic", False))

    noetic_name = NOETIC_NAMES[noetic]
    domain_name = DOMAIN_NAMES[domain]
    drive_name = DRIVE_NAMES[drive]

    # Special families take precedence over the generic head-noun phrasing.
    if family == "omega":
        lead = (
            f"Reading this as `{expr}` — an integrated cross-axis "
            f"commitment ('omega bind') anchored in ^{noetic} {noetic_name} "
            f"{_domain_phrase(domain, noetic)}, driven by {drive} {drive_name}."
        )
    elif family == "meta_logic":
        lead = (
            f"Reading this as `{expr}` — a meta-logical statement about "
            f"CAS structure (^{noetic} {noetic_name} "
            f"{_domain_phrase(domain, noetic)}, drive {drive} {drive_name})."
        )
    else:
        head = _lead_phrase(noetic, domain, registers, register_mode)
        # Inline parenthetical: ^N Noetic in <register-name> register
        if register_mode == "single" and len(registers) == 1:
            r = registers[0]
            inline = (
                f"^{noetic} {noetic_name} {_domain_phrase(domain, noetic)}, "
                f"expressed in {REGISTER_NAMES[r]} register"
            )
        elif register_mode in ("set_spec", "co_presence", "integration") and registers:
            reg_list = ", ".join(REGISTER_NAMES[r] for r in registers)
            inline = (
                f"^{noetic} {noetic_name} {_domain_phrase(domain, noetic)}, "
                f"registers: {reg_list}"
            )
        else:
            inline = (
                f"^{noetic} {noetic_name} {_domain_phrase(domain, noetic)}, "
                f"register unspecified"
            )

        lead = (
            f"Reading this as `{expr}` — {head} ({inline}), "
            f"driven by {drive} {drive_name}."
        )

    addendum = _structural_addendum(prediction)
    closing = "Did I get that right?" if not (has_omega or has_meta) else "Want to confirm or correct?"

    if addendum:
        return f"{lead} {addendum} {closing}"
    return f"{lead} {closing}"


# ---------------------------------------------------------------------------
# __main__ examples
# ---------------------------------------------------------------------------

def _example_simple_negative_analytical() -> dict[str, Any]:
    return {
        "turn_type": "ANSWER",
        "expression_family": "register_state",
        "transition_kind": "state",
        "noetic": 3,
        "domain": "E",
        "drive": "F2",
        "register_mode": "single",
        "registers": ["A"],
        "authority": "none",
        "has_omega": False,
        "has_meta_logic": False,
        "meta_relations": [],
    }


def _example_simple_positive_affective() -> dict[str, Any]:
    return {
        "turn_type": "ANSWER",
        "expression_family": "register_state",
        "transition_kind": "state",
        "noetic": 2,
        "domain": "P",
        "drive": "F4",
        "register_mode": "single",
        "registers": ["f"],
        "authority": "none",
        "has_omega": False,
        "has_meta_logic": False,
        "meta_relations": [],
    }


def _example_compound_omega() -> dict[str, Any]:
    return {
        "turn_type": "REFUSE",
        "expression_family": "omega",
        "transition_kind": "omega_bind",
        "noetic": 3,
        "domain": "P",
        "drive": "F6",
        "register_mode": "integration",
        "registers": ["A", "f", "T"],
        "authority": "none",
        "has_omega": True,
        "has_meta_logic": False,
        "meta_relations": [],
    }


def _example_meta_logic() -> dict[str, Any]:
    return {
        "turn_type": "CLARIFY",
        "expression_family": "meta_logic",
        "transition_kind": "meta_logic_move",
        "noetic": 6,
        "domain": "C",
        "drive": "F2",
        "register_mode": "single",
        "registers": ["A"],
        "authority": "none",
        "has_omega": False,
        "has_meta_logic": True,
        "meta_relations": ["membership", "authority"],
    }


def _example_refusal_blocked() -> dict[str, Any]:
    return {
        "turn_type": "REFUSE",
        "expression_family": "register_state",
        "transition_kind": "state",
        "noetic": 3,
        "domain": "P",
        "drive": "F7",
        "register_mode": "single",
        "registers": ["A"],
        "authority": "blocked",
        "has_omega": False,
        "has_meta_logic": False,
        "meta_relations": [],
    }


def _example_unspecified_register() -> dict[str, Any]:
    return {
        "turn_type": "ANSWER",
        "expression_family": "state",
        "transition_kind": "state",
        "noetic": 4,
        "domain": "C",
        "drive": "F3",
        "register_mode": "none",
        "registers": [],
        "authority": "none",
        "has_omega": False,
        "has_meta_logic": False,
        "meta_relations": [],
    }


_EXAMPLES = (
    ("Simple ^3^E|A (analytical aversion)", _example_simple_negative_analytical()),
    ("Simple ^2^P|f (felt principled attraction)", _example_simple_positive_affective()),
    (
        "Compound integration with has_omega=True (^3^P|A x f x T = Omega)",
        _example_compound_omega(),
    ),
    ("Meta-logic case (^6^C|A with membership/authority)", _example_meta_logic()),
    ("Refusal case (^3^P|A, authority=blocked)", _example_refusal_blocked()),
    ("Unspecified-register case (^4^C, register_mode=none)", _example_unspecified_register()),
)


if __name__ == "__main__":
    # Force UTF-8 stdout so unicode glyphs (Ω, ×, ⟨⟩, em-dash) round-trip on
    # Windows consoles that otherwise default to cp1252.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    for label, pred in _EXAMPLES:
        print(f"=== {label} ===")
        print(f"  expr: {render_cas_expression_string(pred)}")
        print(f"  text: {render_cas_prediction(pred)}")
        print()
