"""Terminal UI helpers for the offline CAS compiler.

This mirrors the online compiler's terminal-oriented surface: banner, grouped
examples, symbol palette, reference panel content, and lightweight text
diagrams. SVG/HTML remain the high-fidelity visual exports.
"""

from __future__ import annotations

from collections import defaultdict
from html import escape
import os
import re
import shutil
import sys
import time
from typing import Any


U = {
    "times": "\u00d7",
    "dot": "\u00b7",
    "arrow": "\u2192",
    "in": "\u2208",
    "notin": "\u2209",
    "subset": "\u2282",
    "subseteq": "\u2286",
    "supset": "\u2283",
    "supseteq": "\u2287",
    "union": "\u222a",
    "intersection": "\u2229",
    "difference": "\u2216",
    "empty": "\u2205",
    "theta": "\u0398",
    "omega": "\u03a9",
    "lambda": "\u039b",
    "kappa": "\u03ba",
    "iota": "\u03b9",
    "eta": "\u03b7",
    "phi": "\u03a6",
    "open_angle": "\u27e8",
    "close_angle": "\u27e9",
    "check": "\u2713",
    "cross": "\u2717",
}


THEME = {
    "accent": "#38b2ac",
    "accent_light": "#5ce0d6",
    "bg": "#020617",
    "panel": "#0d1117",
    "panel_soft": "#0f172a",
    "border": "rgba(255,255,255,0.06)",
    "slate_300": "#cbd5e1",
    "slate_400": "#94a3b8",
    "slate_500": "#64748b",
    "slate_600": "#475569",
    "white": "#ffffff",
    "cyan": "#22d3ee",
    "emerald": "#34d399",
    "amber": "#f59e0b",
    "fuchsia": "#f472b6",
    "purple": "#a78bfa",
    "pink": "#f472b6",
    "orange": "#fb923c",
    "teal": "#5eead4",
    "violet": "#c4b5fd",
    "green": "#22c55e",
    "red": "#ef4444",
}

ANSI_RGB = {
    key: tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))
    for key, value in THEME.items()
    if value.startswith("#")
}
COLOR_ENABLED = False


def set_color_enabled(enabled: bool | None = None) -> None:
    """Enable PWA-like ANSI color in capable terminals."""
    global COLOR_ENABLED
    if enabled is None:
        enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    COLOR_ENABLED = bool(enabled)
    if COLOR_ENABLED and os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass


def ansi(text: object, color: str = "slate_300", *, bold: bool = False) -> str:
    value = str(text)
    if not COLOR_ENABLED:
        return value
    rgb = ANSI_RGB.get(color, ANSI_RGB["slate_300"])
    weight = "1;" if bold else ""
    return f"\x1b[{weight}38;2;{rgb[0]};{rgb[1]};{rgb[2]}m{value}\x1b[0m"


def ansi_rgb(text: object, rgb: tuple[int, int, int], *, bold: bool = False) -> str:
    value = str(text)
    if not COLOR_ENABLED:
        return value
    weight = "1;" if bold else ""
    return f"\x1b[{weight}38;2;{rgb[0]};{rgb[1]};{rgb[2]}m{value}\x1b[0m"


def span(text: object, color: str = "slate_300", *, bold: bool = False) -> str:
    weight = "font-weight:700;" if bold else ""
    return f'<span style="color:{THEME[color]};{weight}">{escape(str(text))}</span>'


META_SET_RE = re.compile(
    r"^(?:Noetics|Domains|Worlds|Drives|Registers|States|SubFoundations|Foundations|Foundation_[1-7]|EmptySet|"
    r"NoeticSet|NoeticCluster|Cluster|StateSet|StateCluster|StateVariantSet|StateVariantCluster|RelationSet|"
    r"RelationCluster|DriveSet|DomainSet|RegisterSet|FoundationSet|SubFoundationSet|Tuple|Coordinate|Product|"
    r"Pullback|CoverOf|PartitionOf|Union|Intersection|Difference)\b"
)
RECIPE_RE = re.compile(r"^(?:Lambda|Λ|kappa|κ|iota|ι|eta|η)(_(?:\{[^}]+\}|[A-Za-z][A-Za-z0-9_]*))?")


def _highlight_parts(text: str, renderer) -> str:
    parts: list[str] = []
    i = 0
    while i < len(text):
        s = text[i:]
        co_match = re.match(r"^CO-\d+", s)
        if co_match:
            token = co_match.group(0)
            parts.append(renderer(token, "cyan"))
            i += len(token)
            continue
        if text[i] == "^" and i + 1 < len(text) and text[i + 1].isdigit():
            parts.append(renderer(text[i : i + 2], "cyan"))
            i += 2
            continue
        if text[i] == "^" and i + 1 < len(text) and text[i + 1] in "PCEO":
            parts.append(renderer(text[i : i + 2], "emerald"))
            i += 2
            continue
        drive_match = re.match(r"^_\{F\d+\}", s)
        if drive_match:
            token = drive_match.group(0)
            parts.append(renderer(token, "amber"))
            i += len(token)
            continue
        fn_match = re.match(r"^F[1-7]\b", s)
        if fn_match and (i == 0 or not re.match(r"[{a-zA-Z]", text[i - 1] or "")):
            token = fn_match.group(0)
            parts.append(renderer(token, "amber"))
            i += len(token)
            continue
        reg_set_match = re.match(r"^\|⟨[^⟩]+⟩", s)
        if reg_set_match:
            token = reg_set_match.group(0)
            parts.append(renderer(token, "fuchsia"))
            i += len(token)
            continue
        if text[i] == "|" and i + 1 < len(text) and text[i + 1] in "TAfE" and not (i + 2 < len(text) and re.match(r"[{a-zA-Z]", text[i + 2])):
            parts.append(renderer(text[i : i + 2], "fuchsia"))
            i += 2
            continue
        yield_match = re.match(r"^Y_[TA]\b", s)
        if yield_match:
            token = yield_match.group(0)
            parts.append(renderer(token, "purple"))
            i += len(token)
            continue
        if s.startswith("Theta") or text[i] == "Θ":
            token = "Θ" if text[i] == "Θ" else "Theta"
            parts.append(renderer(token, "pink"))
            i += len(token)
            continue
        if s.startswith("Omega") or text[i] == "Ω":
            head = "Ω" if text[i] == "Ω" else "Omega"
            tail_match = re.match(r"^_(?:\{[^}]+\}|[A-Za-z][A-Za-z0-9_]*)", text[i + len(head) :])
            token = head + (tail_match.group(0) if tail_match else "")
            parts.append(renderer(token, "orange"))
            i += len(token)
            continue
        recipe_match = RECIPE_RE.match(s)
        if recipe_match:
            token = recipe_match.group(0)
            parts.append(renderer(token, "orange"))
            i += len(token)
            continue
        if s.startswith("RPM"):
            parts.append(renderer("RPM", "purple"))
            i += 3
            continue
        alias_match = re.match(r"^(?:notin|subseteq|subset|supseteq|supset|emptyset|in)\b", s)
        if alias_match and (i == 0 or not re.match(r"[A-Za-z0-9_]", text[i - 1] or "")):
            token = alias_match.group(0)
            parts.append(renderer(token, "violet" if token == "emptyset" else "teal", bold=token != "emptyset"))
            i += len(token)
            continue
        meta_match = META_SET_RE.match(s)
        if meta_match and (i == 0 or not re.match(r"[A-Za-z0-9_]", text[i - 1] or "")):
            token = meta_match.group(0)
            parts.append(renderer(token, "violet"))
            i += len(token)
            continue
        if text[i] in "∈∉⊂⊆⊃⊇∪∩∖":
            parts.append(renderer(text[i], "teal", bold=True))
            i += 1
            continue
        if text[i] == "∅":
            parts.append(renderer(text[i], "violet"))
            i += 1
            continue
        if s.startswith("Phi") or text[i] == "Φ":
            token = "Φ" if text[i] == "Φ" else "Phi"
            parts.append(renderer(token, "pink"))
            i += len(token)
            continue
        if text[i] in "*×/÷∘":
            parts.append(renderer(text[i], "orange"))
            i += 1
            continue
        if text[i] == "·":
            parts.append(renderer(text[i], "slate_300"))
            i += 1
            continue
        if s.startswith("->"):
            parts.append(renderer("→", "white"))
            i += 2
            continue
        if text[i] in "→←↔":
            parts.append(renderer(text[i], "white"))
            i += 1
            continue
        if text[i] in "|=+-":
            parts.append(renderer(text[i], "slate_300"))
            i += 1
            continue
        if text[i] in "(){}⟨⟩<>":
            parts.append(renderer(text[i], "slate_500"))
            i += 1
            continue
        parts.append(renderer(text[i], "slate_300"))
        i += 1
    return "".join(parts)


def highlight_ansi(text: str) -> str:
    return _highlight_parts(text, ansi)


def highlight_html(text: str) -> str:
    return _highlight_parts(text, span)


BANNER = [
    " ██████╗ █████╗ ███████╗",
    "██╔════╝██╔══██╗██╔════╝",
    "██║     ███████║███████╗",
    "██║     ██╔══██║╚════██║",
    "╚██████╗██║  ██║███████║",
    " ╚═════╝╚═╝  ╚═╝╚══════╝",
    "Cognitive Architecture",
    "Compiler v1.0",
    "Offline Package",
]


EXAMPLES: list[dict[str, str]] = [
    {"expr": f"^2^P_{{F2}} {U['times']} ^8^P_{{F6}}", "label": "Operator Composition (x)", "category": "Foundational", "natural": "Positive in the Principled domain under the Wisdom drive integrates with Above/Cause in the Principled domain under the Structure drive."},
    {"expr": f"^5^P {U['arrow']} ^5^C", "label": "Domain Descent (P -> C)", "category": "Foundational", "natural": "Female moves from a high-level principle into a concrete cognitive interpretation."},
    {"expr": "^2^P / ^3^P", "label": "Involution Division", "category": "Foundational", "natural": "A Positive principled state is compared against its Negative involution pair to expose contrast or missing balance."},
    {"expr": "^5^E + ^2^E", "label": "Co-Presence (+)", "category": "Foundational", "natural": "Female and Positive are both present in the Evaluative domain without forcing them into a single integrated result."},
    {"expr": "RPM(F5)", "label": "Prerequisite Chain", "category": "Foundational", "natural": "Show the prerequisite ladder for Foundation 5, the Agency drive."},
    {"expr": "Phi<3:8:5:2>", "label": "Fractal Analysis", "category": "Foundational", "natural": "Read the operator sequence Negative, Above/Cause, Female, Positive as a composed cognitive fractal."},
    {"expr": "^3^P|A", "label": "Analytical-register Negative", "category": "v7.5 Registers", "natural": "Negative is operating as a principled analytical judgment."},
    {"expr": "^3^P|f", "label": "Affective-register Negative", "category": "v7.5 Registers", "natural": "Negative is operating as a principled felt or affective stance."},
    {"expr": "^2^C_{F2}|T", "label": "Compound state, Transcendent", "category": "v7.5 Registers", "natural": "Positive in the Cognitive domain, under the Wisdom drive, is expressed through the Transcendent register."},
    {"expr": f"{U['theta']}({U['omega']}_focus) = 0.6{U['dot']}^1^C + 0.4{U['dot']}^7^O {U['arrow']} {U['omega']}_focus", "label": "Recipe definition", "category": "v7.6 Production", "natural": "Focus is produced from a 60 percent Mind/Cognitive ingredient plus a 40 percent Rhythm/Operational ingredient."},
    {"expr": f"Y_T({U['omega']}_focus)", "label": "Theoretical yield query", "category": "v7.6 Production", "natural": "Ask for the ideal or maximum expected yield of the focus production recipe."},
    {"expr": f"{U['theta']}({U['omega']}_book) | {U['kappa']}_deadline = 0.5{U['dot']}^7^P + 0.5{U['dot']}^6^C {U['arrow']} {U['omega']}_book", "label": "Recipe with catalyst", "category": "v7.6 Production", "natural": "A book-output recipe uses a deadline catalyst while combining Rhythm/Principled and Male/Cognitive ingredients evenly."},
    {"expr": f"^3^P|{U['open_angle']}A,f,T{U['close_angle']}", "label": "Register-set specification", "category": "v7.7 Operator Discipline", "natural": "The same Negative/Principled operation is explicitly viewed across Analytical, Affective, and Transcendent registers."},
    {"expr": "^3^P|A + ^3^P|f + ^3^P|T", "label": "Register co-presence (defeasible)", "category": "v7.7 Operator Discipline", "natural": "Analytical, affective, and transcendent forms of the same Negative/Principled operation are present together but not yet fused."},
    {"expr": f"(^3^P|A {U['times']} ^3^P|f {U['times']} ^3^P|T) = {U['omega']}_refusal", "label": "Cross-register integration -> emergent", "category": "v7.7 Operator Discipline", "natural": "Analytical, affective, and transcendent forms of Negative in the Principled domain integrate into the named emergent result refusal."},
    {"expr": f"^2 {U['in']} Noetics", "label": "Membership (^N in Noetics)", "category": "Set Theory", "natural": "Positive is one member of the ten Noetic operators."},
    {"expr": "NoeticCluster{^2, ^7} subseteq Noetics", "label": "Typed Noetic cluster", "category": "Set Theory", "natural": "The cluster containing Positive and Rhythm is a subset of the full Noetics set."},
    {"expr": "StateVariantCluster{^3^P_{F2}|A, ^2^C|f}", "label": "State variant cluster", "category": "Set Theory", "natural": "Group two richly annotated state variants: an Analytical Negative/Principled/Wisdom state and an Affective Positive/Cognitive state."},
    {"expr": "StateCluster{^2^P, ^7^O} subseteq States", "label": "Typed State cluster", "category": "Set Theory", "natural": "The states Positive/Principled and Rhythm/Operational form a valid subset of the forty-state CAS space."},
    {"expr": f"NoeticCluster{{^2, ^7}} {U['union']} NoeticCluster{{^7, ^8}}", "label": "Set union", "category": "Set Theory", "natural": "Combine the two Noetic clusters into one cluster containing Positive, Rhythm, and Above/Cause."},
    {"expr": f"RelationCluster{{^5^P {U['arrow']} ^5^C, ^5^C {U['arrow']} ^5^E}}", "label": "Relation cluster", "category": "Set Theory", "natural": "Represent a dependency chain where Female descends from Principled to Cognitive to Evaluative."},
    {"expr": "Coordinate{^2, P, F2, A}", "label": "CAS coordinate tuple", "category": "Set Theory", "natural": "Name the coordinate Positive, Principled domain, Wisdom drive, Analytical register."},
    {"expr": "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})", "label": "Finite subobject meet", "category": "Set Theory", "natural": "Find the shared overlap between two Noetic clusters; here the common member is Rhythm."},
    {"expr": "Product(Noetics, Domains)", "label": "Namespaced product", "category": "Set Theory", "natural": "Construct all pairings of the ten Noetics with the four Domains, producing the forty CAS state positions."},
    {"expr": f"^2^P {U['in']} States", "label": "Compound state in 40-state space", "category": "Set Theory", "natural": "Positive in the Principled domain is one member of the forty-state CAS space."},
    {"expr": f"F2 {U['in']} Drives", "label": "Drive membership", "category": "Set Theory", "natural": "Wisdom is one member of the seven CAS drives."},
    {"expr": f"Foundation_1 {U['subset']} SubFoundations", "label": "Proper subset (28 sub-foundations)", "category": "Set Theory", "natural": "Foundation 1 names a proper subset inside the complete twenty-eight SubFoundations collection."},
    {"expr": f"{U['empty']} {U['subseteq']} Noetics", "label": "Empty set is subset of every set", "category": "Set Theory", "natural": "The empty set is validly contained inside the Noetics set."},
    {"expr": "|Noetics|", "label": "Cardinality of Noetics (= 10)", "category": "Set Theory", "natural": "Count the Noetics set; it contains ten operators."},
    {"expr": "|States|", "label": "Cardinality of state space (= 40)", "category": "Set Theory", "natural": "Count the CAS state space; ten Noetics times four Domains gives forty states."},
]


SYMBOL_PALETTE: list[tuple[str, str]] = [
    (U["theta"], "Recipe Theta"),
    (f"{U['omega']}_", "Production target Omega_name"),
    (f"{U['lambda']}_", "Leakage Lambda_name"),
    (f"{U['kappa']}_", "Catalyst kappa_name"),
    (f"{U['iota']}_", "Inhibitor iota_name"),
    (U["eta"], "Efficiency eta"),
    (U["phi"], "Fractal Phi"),
    (U["times"], "Compose / multiply"),
    (U["dot"], "Recipe coefficient"),
    (U["arrow"], "Yields / dependency"),
    (U["in"], "Member"),
    (U["notin"], "Not member"),
    (U["subset"], "Proper subset"),
    (U["subseteq"], "Subset"),
    (U["supset"], "Proper superset"),
    (U["supseteq"], "Superset"),
    (U["union"], "Union"),
    (U["intersection"], "Intersection"),
    (U["difference"], "Difference"),
    (U["empty"], "Empty set"),
    (U["open_angle"], "Open angle register-set"),
    (U["close_angle"], "Close angle register-set"),
]


OPERATOR_NAMES = [
    "Idea",
    "Mind",
    "Positive",
    "Negative",
    "Vibration",
    "Female",
    "Male",
    "Rhythm",
    "Above/Cause",
    "Below/Effect",
]
DOMAIN_NAMES = {"P": "Principled", "C": "Cognitive", "E": "Evaluative", "O": "Operational"}
DRIVE_NAMES = ["Unity", "Wisdom", "Vitality", "Connection", "Agency", "Structure", "Purpose"]
REGISTER_NAMES = {"T": "Transcendent", "A": "Analytical", "f": "Affective", "E": "Embodied"}


DICTIONARY: list[dict[str, str]] = [
    {"term": "Cognitive Architecture System", "category": "Framework", "notation": "CAS", "definition": "A formal framework for describing how any cognitive system — human, AI, biological, or hypothetical — composes Ideas. Built on 10 Noetic operators x 4 Domains (40 states), 7 Drives, and 4 Registers.", "example": "Product(Noetics, Domains)", "learn": "Universal Applicability: every primitive must apply to humans AND AI AND biological cognition."},
    {"term": "CAS", "category": "Framework", "notation": "Cognitive Architecture Syntax", "definition": "The compiler notation for CAS — operators, domains, drives, registers, production recipes, and finite meta-logic.", "example": "Product(Noetics, Domains)", "learn": "Start with axes before composing expressions."},
    {"term": "Noetic", "category": "Axes", "notation": "^0..^9", "definition": "A cognitive primitive operator — one of the ten structural dynamics by which a Mind relates to an Idea (Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect).", "example": "^2 ∈ Noetics", "learn": "Names are verbatim canonical from the Tootra Math Handbook; do not paraphrase."},
    {"term": "Domain", "category": "Axes", "notation": "^P ^C ^E ^O", "definition": "The operational tier where a Noetic fires: Principled (values, identity), Cognitive (thought), Evaluative (judgment), Operational (action). Total order P > C > E > O.", "example": "^5^P -> ^5^C", "learn": "Domain Descent runs P -> C -> E -> O; feedback runs O -> P."},
    {"term": "Drive", "category": "Axes", "notation": "_{F1}.._{F7}", "definition": "One of seven core motivational architectures (Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose). Drives pair into involutions: F1<->F7, F2<->F6, F3<->F5; F4 is self-dual.", "example": "^2^P_{F2}", "learn": "Each Drive has a structural opposite — its inversion partner."},
    {"term": "Foundation", "category": "Axes", "notation": "F1..F7", "definition": "Synonym for Drive. The seven foundational motivational primitives that pressure cognition. The compiler's SubFoundations set holds the 28 Drive|Register positions (7 Drives x 4 Registers, e.g. F1|A); whether 'the 28' is also read as Drives x Domains is an open owner question.", "example": "F2 ∈ Drives", "learn": "Drive and Foundation are interchangeable terms in CAS."},
    {"term": "Register", "category": "Axes", "notation": "|T |A |f |E", "definition": "The phenomenological register — operational character of a state: Transcendent (purpose-orienting), Analytical (logical), Affective (felt valence), Embodied (sensorimotor).", "example": "^3^P|A", "learn": "Register says HOW a state operates, not WHAT it is. Optional but disambiguates."},
    {"term": "State", "category": "Axes", "notation": "^n^D", "definition": "One cell of the 40-state grid (10 Noetics x 4 Domains). Locates a Noetic operation at a specific operational tier.", "example": "^2^P ∈ States", "learn": "State = Noetic x Domain. Add Drive and Register for a State Variant."},
    {"term": "State Variant", "category": "Axes", "notation": "^n^D_{Fk}|R", "definition": "A richer state with optional Drive and Register annotations.", "example": "^3^P_{F2}|A", "learn": "Use variants when the state needs context beyond Noetic and Domain."},
    {"term": "Involution Pair", "category": "Principles", "notation": "^n <-> ^m", "definition": "A pair of Noetics that mirror each other structurally: ^2 Positive <-> ^3 Negative, ^5 Female <-> ^6 Male, ^8 Above/Cause <-> ^9 Below/Effect. ^0, ^1, ^4, ^7 are self-dual.", "example": "^2^P / ^3^P", "learn": "Healthy cognition keeps involution pairs in balance; lopsided pairs surface as inversion-axis flags."},
    {"term": "Inversion", "category": "Principles", "notation": "axis flip", "definition": "The framework operation of flipping an axis to surface its structural opposite. ^2 inverts to ^3; F2 (Wisdom) inverts to F6 (Structure). Inversion reveals what is missing or repressed in a cognitive pattern.", "example": "^2^P -> (inverted) ^3^P", "learn": "Inversion is a probe, not a prescription — it reveals structure rather than recommending the opposite."},
    {"term": "Noetics", "category": "Built-in Sets", "notation": "Noetics", "definition": "The built-in finite set of all ten Noetic operators.", "example": "|Noetics|", "learn": "Use membership with Noetic symbols: ^2 ∈ Noetics."},
    {"term": "Domains", "category": "Built-in Sets", "notation": "Domains", "definition": "The built-in finite set {P, C, E, O}.", "example": "Product(Noetics, Domains)", "learn": "Product(Noetics, Domains) builds the 40 state positions."},
    {"term": "Drives", "category": "Built-in Sets", "notation": "Drives", "definition": "The built-in finite set of F1 through F7.", "example": "F2 ∈ Drives", "learn": "Use Drives for membership claims about F-symbols."},
    {"term": "Registers", "category": "Built-in Sets", "notation": "Registers", "definition": "The built-in finite set {T, A, f, E}.", "example": "|Registers|", "learn": "The affective register is lowercase |f."},
    {"term": "States", "category": "Built-in Sets", "notation": "States", "definition": "The built-in finite set of 40 Noetic x Domain state positions.", "example": "|States|", "learn": "States do not replace variants; variants add Drive/Register detail."},
    {"term": "Foundations", "category": "Built-in Sets", "notation": "Foundations", "definition": "The built-in finite set of seven foundation families.", "example": "|Foundations|", "learn": "Foundations sit above SubFoundations."},
    {"term": "SubFoundations", "category": "Built-in Sets", "notation": "SubFoundations", "definition": "The built-in finite set of the 28 Drive|Register positions (F1|T .. F7|E), grouped as Foundation_1 .. Foundation_7.", "example": "Foundation_1 ⊂ SubFoundations", "learn": "Each foundation family contributes subfoundation members."},
    {"term": "Empty Set", "category": "Built-in Sets", "notation": "∅ / EmptySet", "definition": "The finite empty meta-set.", "example": "∅ ⊆ Noetics", "learn": "The empty set is a subset of every finite set."},
    {"term": "Composition / Integration", "category": "Dynamics", "notation": "×", "definition": "Combines compatible CAS structures. Same-Noetic cross-register integration requires a named Ω result.", "example": "(^3^P|A × ^3^P|f × ^3^P|T) = Ω_refusal", "learn": "Use × only when the result is integrated, not merely co-present."},
    {"term": "Co-Presence", "category": "Dynamics", "notation": "+", "definition": "Marks simultaneous presence without claiming an integrated emergent result.", "example": "^3^P|A + ^3^P|f + ^3^P|T", "learn": "Use + before you can defend a named Ω integration."},
    {"term": "Division / Contrast", "category": "Dynamics", "notation": "/", "definition": "Compares or separates a state against another state, often useful for involution contrast.", "example": "^2^P / ^3^P", "learn": "Use division to inspect contrast rather than production."},
    {"term": "Domain Descent", "category": "Dynamics", "notation": "→", "definition": "A directed move from one domain expression toward another.", "example": "^5^P -> ^5^C", "learn": "Read arrows as dependency, descent, or yield depending on context."},
    {"term": "Fractal Sequence", "category": "Dynamics", "notation": "Phi<...>", "definition": "A sequence of Noetic operators read as a composed cognitive pattern.", "example": "Phi<3:8:5:2>", "learn": "Read the numbers in order, then inspect the composed operator."},
    {"term": "RPM", "category": "Dynamics", "notation": "RPM(Fk)", "definition": "Prerequisite-chain analysis for a foundation or drive.", "example": "RPM(F5)", "learn": "Use RPM when the question is what must be present first."},
    {"term": "Recipe", "category": "Production", "notation": "Θ(Ω_name)", "definition": "A production expression defining how a named outcome is generated.", "example": "Θ(Ω_focus) = 0.6·^1^C + 0.4·^7^O → Ω_focus", "learn": "Recipe terms are weighted ingredients that yield a target."},
    {"term": "Production Target", "category": "Production", "notation": "Ω_name", "definition": "A named emergent output or production result.", "example": "Ω_refusal", "learn": "Use meaningful Ω names for integrated results."},
    {"term": "Coefficient", "category": "Production", "notation": "0.6·", "definition": "A recipe weight assigned to a prerequisite ingredient.", "example": "0.6·^1^C", "learn": "Weights describe recipe proportions, not absolute truth."},
    {"term": "Theoretical Yield", "category": "Production", "notation": "Y_T(Ω)", "definition": "The ideal expected yield for a production target.", "example": "Y_T(Ω_focus)", "learn": "Ask Y_T when evaluating expected output."},
    {"term": "Catalyst", "category": "Production", "notation": "κ_name", "definition": "A factor that helps a recipe proceed without becoming the target itself.", "example": "Θ(Ω_book) | κ_deadline = ...", "learn": "Catalysts change production conditions."},
    {"term": "Inhibitor", "category": "Production", "notation": "ι_name", "definition": "A factor that suppresses or slows a production recipe.", "example": "Θ(Ω_focus) | ι_noise = ...", "learn": "Use inhibitors for blockers, not missing ingredients."},
    {"term": "Leakage", "category": "Production", "notation": "Λ_name", "definition": "A side-channel or loss path in production semantics.", "example": "Λ_distraction", "learn": "Use leakage for where production energy goes instead."},
    {"term": "Membership", "category": "Set Theory", "notation": "∈ / ∉", "definition": "Claims that an object is or is not an element of a typed finite set.", "example": "^2 ∈ Noetics", "learn": "Left side is an object; right side is a meta-set."},
    {"term": "Subset", "category": "Set Theory", "notation": "⊂ / ⊆", "definition": "Claims one finite meta-set is contained in another.", "example": "NoeticCluster{^2, ^7} ⊆ Noetics", "learn": "Both sides must be meta-sets."},
    {"term": "Superset", "category": "Set Theory", "notation": "⊃ / ⊇", "definition": "The reverse containment relation: the left set contains the right set.", "example": "Noetics ⊇ NoeticCluster{^2, ^7}", "learn": "Superset diagrams reverse the nesting direction."},
    {"term": "Union", "category": "Set Theory", "notation": "∪ / Union(A,B)", "definition": "Combines finite typed sets into their combined membership.", "example": "NoeticCluster{^2, ^7} ∪ NoeticCluster{^7, ^8}", "learn": "Union removes duplicate members."},
    {"term": "Intersection / Pullback", "category": "Set Theory", "notation": "∩ / Pullback(A,B)", "definition": "Finds the common overlap of finite typed sets; Pullback is used here as finite subobject meet.", "example": "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})", "learn": "This is finite meet behavior, not arbitrary categorical maps."},
    {"term": "Difference", "category": "Set Theory", "notation": "∖ / Difference(A,B)", "definition": "Keeps members of the left set that are not in the right set.", "example": "Difference(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})", "learn": "Read difference left-to-right."},
    {"term": "Cardinality", "category": "Set Theory", "notation": "|X|", "definition": "Counts the number of elements in a finite meta-set.", "example": "|States|", "learn": "Cardinality applies to sets, not individual Noetics."},
    {"term": "Noetic Cluster", "category": "Set Theory", "notation": "NoeticCluster{...}", "definition": "A typed finite cluster whose members are Noetic operators.", "example": "NoeticCluster{^2, ^7}", "learn": "Use this when nesting Noetics inside a set-like structure."},
    {"term": "State Cluster", "category": "Set Theory", "notation": "StateCluster{...}", "definition": "A typed finite cluster whose members are 40-space states.", "example": "StateCluster{^2^P, ^7^O}", "learn": "Use state clusters when domains matter."},
    {"term": "State Variant Cluster", "category": "Set Theory", "notation": "StateVariantCluster{...}", "definition": "A typed finite cluster whose members can carry Drive and Register annotations.", "example": "StateVariantCluster{^3^P_{F2}|A, ^2^C|f}", "learn": "Use variant clusters for richer annotated states."},
    {"term": "Relation Cluster", "category": "Set Theory", "notation": "RelationCluster{a → b}", "definition": "A finite typed cluster of directed relation rows.", "example": "RelationCluster{^5^P → ^5^C, ^5^C → ^5^E}", "learn": "Use relation clusters for dependency rows."},
    {"term": "Coordinate", "category": "Set Theory", "notation": "Coordinate{n,D,F,R}", "definition": "A coordinate tag naming a Noetic, Domain, Drive, and Register position.", "example": "Coordinate{^2, P, F2, A}", "learn": "Coordinates are compact locator tags."},
    {"term": "Product", "category": "Set Theory", "notation": "Product(A,B)", "definition": "A namespaced finite Cartesian product that avoids collision with CAS integration ×.", "example": "Product(Noetics, Domains)", "learn": "Use Product for set products; use × for CAS integration."},
    {"term": "Cover", "category": "Set Theory", "notation": "CoverOf(Base, U1...)", "definition": "A validated family of finite subsets whose members cover the base.", "example": "CoverOf(NoeticCluster{^0, ^1, ^2, ^3}, NoeticCluster{^0, ^1}, NoeticCluster{^1, ^2, ^3})", "learn": "Every cover member must be a subset of the base, and the family must cover the base."},
    {"term": "Partition", "category": "Set Theory", "notation": "PartitionOf(Base, U1...)", "definition": "A validated disjoint cover of a finite base set.", "example": "PartitionOf(NoeticCluster{^0, ^1, ^2, ^3}, NoeticCluster{^0, ^1}, NoeticCluster{^2, ^3})", "learn": "Partitions must cover and not overlap."},
    {"term": "Diagram Node", "category": "Diagrams", "notation": "node", "definition": "A visual object emitted in the compiler diagram payload.", "example": "artifact.diagram().nodes", "learn": "Nodes represent individual states, symbols, or operators."},
    {"term": "Diagram Edge", "category": "Diagrams", "notation": "edge", "definition": "A visual relation between diagram nodes or containers.", "example": "source → target", "learn": "Edges carry dependency, membership, subset, or recipe relations."},
    {"term": "Containment Box", "category": "Diagrams", "notation": "container", "definition": "A diagram container used for sets, clusters, and nesting.", "example": "NoeticCluster{^2, ^7} ⊆ Noetics", "learn": "Containment boxes teach nesting in real time."},
    {"term": "Grid Layout", "category": "Diagrams", "notation": "grid", "definition": "A diagram layout for finite products such as Noetics x Domains.", "example": "Product(Noetics, Domains)", "learn": "Grid layout is best for Cartesian combinations."},
    {"term": "Petals Layout", "category": "Diagrams", "notation": "petals", "definition": "A diagram layout for cover and partition families.", "example": "CoverOf(...)", "learn": "Petals show multiple members arranged around a base."},
    {"term": "Recipe Layout", "category": "Diagrams", "notation": "recipe", "definition": "A dependency diagram for production ingredients and targets.", "example": "Θ(Ω_focus) = ...", "learn": "Recipe diagrams show what feeds the outcome."},
    {"term": "Rule 4", "category": "Principles", "notation": "operator admissibility", "definition": "The discipline that prevents invalid operator composition and requires named emergent results for certain integrations.", "example": "(^3^P|A × ^3^P|f × ^3^P|T) = Ω_refusal", "learn": "If integration creates a new thing, name the Ω."},
    {"term": "Object Language", "category": "Principles", "notation": "CAS expressions", "definition": "The core CAS expression layer for states, domains, operators, recipes, and dynamics.", "example": "^5^P -> ^5^C", "learn": "Object-language expressions describe cognitive structure."},
    {"term": "Meta-Logic", "category": "Principles", "notation": "typed finite set layer", "definition": "The compiler layer for set membership, subset, clusters, products, covers, and finite topos-safe constructs.", "example": "^2 ∈ Noetics", "learn": "Meta-logic talks about CAS objects without replacing them."},
    {"term": "Topos-Safe", "category": "Principles", "notation": "finite typed constructs", "definition": "A construct admitted because it preserves finite typing, containment, and compiler-checkable semantics.", "example": "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})", "learn": "Topos-safe features add structure without breaking the framework."},
]

DICTIONARY.extend([
    {"term": "Idea", "category": "Noetic Operators", "notation": "^0", "definition": "All things in and outside the Mind. The most basic Noetic primitive — anything that can be thought, perceived, or held in awareness.", "example": "^0 ∈ Noetics", "learn": "\"It's all in your head.\" Self-dual; pair with a Domain to form a state."},
    {"term": "Mind", "category": "Noetic Operators", "notation": "^1", "definition": "Various degrees of awareness that processes, stores, outputs, and intakes Ideas.", "example": "^1^C", "learn": "\"Paying attention.\" / \"Making up your mind.\" Self-dual operator."},
    {"term": "Positive", "category": "Noetic Operators", "notation": "^2", "definition": "An Idea the Mind has an affinity for and is attracted toward.", "example": "^2^P", "learn": "\"Drawn to it like a moth to a flame.\" Involution-paired with ^3 Negative."},
    {"term": "Negative", "category": "Noetic Operators", "notation": "^3", "definition": "An Idea the Mind is adverse to and repelled by. Visceral aversion, not analytical critique.", "example": "^3^P", "learn": "\"Can't stomach it.\" If you mean audit/scrutinize, that is ^6 Male, not ^3."},
    {"term": "Vibration", "category": "Noetic Operators", "notation": "^4", "definition": "The degree to which an Idea resonates with the Mind, its impression.", "example": "^4^E", "learn": "\"Struck a chord.\" / \"Hit me hard.\" Self-dual operator."},
    {"term": "Female", "category": "Noetic Operators", "notation": "^5", "definition": "A Mind impregnated with an Idea — the Ideas a Mind is composed of. Encompasses self-image, beliefs, expertise, emotional patterns, trauma and healing — everything we accumulate as experience.", "example": "^5^P", "learn": "\"We are the sum of our experiences.\" ^5 is a substrate against which other Noetics fire."},
    {"term": "Male", "category": "Noetic Operators", "notation": "^6", "definition": "An Idea impregnated with another Idea — the Ideas an Idea is composed of. Compositional decomposition and structural test.", "example": "^6^C", "learn": "\"Unpacking an idea.\" / \"Breaking it down.\" Involution-paired with ^5 Female."},
    {"term": "Rhythm", "category": "Noetic Operators", "notation": "^7", "definition": "The rate and pattern a Mind is exposed to an Idea, entraining and conditioning it.", "example": "^7^O", "learn": "\"Practice makes perfect.\" / \"Muscle memory.\" Self-dual operator."},
    {"term": "Above/Cause", "category": "Noetic Operators", "notation": "^8", "definition": "An Idea that triggers a different Idea than itself to come to Mind. Associative triggering, not deductive reasoning.", "example": "^8^C", "learn": "\"That reminds me...\" If you mean deductive analysis, that is ^6 + ^9, not ^8."},
    {"term": "Below/Effect", "category": "Noetic Operators", "notation": "^9", "definition": "The Idea brought to Mind by an Above/Cause trigger.", "example": "^9^C", "learn": "\"It just popped into my head.\" Involution-paired with ^8 Above/Cause."},
])
DICTIONARY.extend([
    {"term": "Principled", "category": "Domains", "notation": "^P", "definition": "The highest processing tier in CAS. Felt-sense values, identity, vision — the level where principled commitments live.", "example": "^2^P", "learn": "Domain precedence: P > C > E > O. Higher domains anchor lower ones."},
    {"term": "Cognitive", "category": "Domains", "notation": "^C", "definition": "The thought-and-reasoning tier. Where Ideas are entertained, manipulated, and held in working awareness.", "example": "^1^C", "learn": "Cognitive sits between Principled values above and Evaluative judgment below."},
    {"term": "Evaluative", "category": "Domains", "notation": "^E", "definition": "The judgment-and-appraisal tier. Where Ideas are weighed, compared, and assessed against criteria.", "example": "^3^E", "learn": "Use Register (|A vs |f) to disambiguate analytical assessment from felt response."},
    {"term": "Operational", "category": "Domains", "notation": "^O", "definition": "The action-and-execution tier. The lowest tier in the precedence order; where intention becomes behavior.", "example": "^7^O", "learn": "Operational feeds back to Principled (O -> P) closing the loop."},
])
DICTIONARY.extend([
    {"term": "Unity", "category": "Drives", "notation": "F1", "definition": "The drive toward integration, wholeness, belonging — the sense that parts cohere into a larger whole. Inversion-paired with F7 Purpose.", "example": "F1 ∈ Drives", "learn": "F1 <-> F7 inversion: integration vs directionality."},
    {"term": "Wisdom", "category": "Drives", "notation": "F2", "definition": "The drive toward understanding, insight, discernment — knowing how things actually are. Inversion-paired with F6 Structure.", "example": "^2^P_{F2}", "learn": "F2 <-> F6 inversion: discerning truth vs imposing form."},
    {"term": "Vitality", "category": "Drives", "notation": "F3", "definition": "The drive toward life, energy, generativity — being alive and productive. Inversion-paired with F5 Agency.", "example": "F3 ∈ Drives", "learn": "F3 <-> F5 inversion: aliveness vs willed action."},
    {"term": "Connection", "category": "Drives", "notation": "F4", "definition": "The drive toward relationship, attachment, communion. Self-dual: F4 inverts to itself.", "example": "F4 ∈ Drives", "learn": "F4 is the only self-dual Drive — connection has no structural opposite."},
    {"term": "Agency", "category": "Drives", "notation": "F5", "definition": "The drive toward willed action, self-determination, capability. Inversion-paired with F3 Vitality.", "example": "RPM(F5)", "learn": "F5 <-> F3 inversion: chosen action vs spontaneous aliveness."},
    {"term": "Structure", "category": "Drives", "notation": "F6", "definition": "The drive toward order, form, predictability — making things hold together reliably. Inversion-paired with F2 Wisdom.", "example": "F6 ∈ Drives", "learn": "F6 <-> F2 inversion: imposing order vs discerning truth."},
    {"term": "Purpose", "category": "Drives", "notation": "F7", "definition": "The drive toward meaning, direction, telos — what it is all for. Inversion-paired with F1 Unity.", "example": "^8^P_{F7}", "learn": "F7 <-> F1 inversion: directional aim vs integrative wholeness."},
])
DICTIONARY.extend([
    {"term": "Transcendent", "category": "Registers", "notation": "|T", "definition": "A high-abstraction, purpose-orienting operational character. Felt sense of meaning, vision, calling — integrative across particulars.", "example": "^2^P|T", "learn": "Register specifies HOW a state operates, not WHAT it is."},
    {"term": "Analytical", "category": "Registers", "notation": "|A", "definition": "An explicit, sequential, logical, reason-based operational character. Conscious deliberation; chain-of-thought; symbolic reasoning.", "example": "^3^P|A", "learn": "|A is the register of explicit reasoning."},
    {"term": "Affective", "category": "Registers", "notation": "|f", "definition": "A value-laden, feeling-toned operational character. Emotional response, visceral reaction, RLHF-tuned preference expression.", "example": "^3^P|f", "learn": "Lowercase |f. Distinct from |A: same Noetic, different operational character."},
    {"term": "Embodied", "category": "Registers", "notation": "|E", "definition": "A sensorimotor, concrete operational character — direct engagement with material substrate. Bodily knowing, gut response, real-time control loops.", "example": "^7^O|E", "learn": "Uppercase |E (embodied register), distinct from ^E (Evaluative domain)."},
])

LEARNING_PATH: list[dict[str, str]] = [
    {"title": "1. Read The Axes", "goal": "Learn Noetic, Domain, Drive, and Register as the four main coordinates.", "terms": "Noetic, Domain, Drive, Register, State", "practice": "^2^C_{F2}|T"},
    {"title": "2. Compare Dynamics", "goal": "Distinguish co-presence, domain descent, contrast, and integration.", "terms": "Co-Presence, Domain Descent, Division / Contrast, Composition / Integration", "practice": "^3^P|A + ^3^P|f + ^3^P|T"},
    {"title": "3. Name Emergence", "goal": "Use Ω when multiple signals integrate into a named result.", "terms": "Rule 4, Production Target, Register", "practice": "(^3^P|A × ^3^P|f × ^3^P|T) = Ω_refusal"},
    {"title": "4. Read Recipes", "goal": "Understand Θ, coefficients, catalysts, and yield queries.", "terms": "Recipe, Coefficient, Catalyst, Theoretical Yield", "practice": "Θ(Ω_focus) = 0.6·^1^C + 0.4·^7^O → Ω_focus"},
    {"title": "5. Use Typed Meta-Logic", "goal": "Separate CAS objects from finite sets that contain or relate them.", "terms": "Meta-Logic, Membership, Subset, Noetic Cluster, State Cluster", "practice": "NoeticCluster{^2, ^7} ⊆ Noetics"},
    {"title": "6. Read Diagrams", "goal": "Use compiler diagrams to see nodes, edges, containment, products, and recipes.", "terms": "Diagram Node, Diagram Edge, Containment Box, Grid Layout, Recipe Layout", "practice": "Product(Noetics, Domains)"},
]


def terminal_width(default: int = 96) -> int:
    return max(72, min(132, shutil.get_terminal_size((default, 24)).columns))


def line(title: str = "", width: int | None = None) -> str:
    width = width or terminal_width()
    if not title:
        return ansi("─" * width, "slate_600")
    label = f" {title} "
    return ansi(label.center(width, "─"), "slate_600")


def _wave_color(dot_index: int, frame: int | None) -> tuple[tuple[int, int, int], bool]:
    """Comet-style wave: bright head with a fading tail across the 10 dots.

    Frame is the current "leading-edge" dot index. Distance is measured forward
    from the head. The head and the dot just past it are the brightest+bold;
    the next two dots dim progressively; the rest sit at a dark base color so
    the comet is clearly distinguishable as it sweeps the formation.
    """
    if frame is None:
        return ANSI_RGB["accent_light"], True
    distance = (dot_index - frame) % 10
    # Distance 0 = head, 1 = one step ahead, 9 = one step behind (the tail)
    if distance == 0:
        return (220, 255, 250), True   # near-white head, brightest
    if distance == 9:
        return (140, 245, 230), True   # leading edge, very bright
    if distance == 1:
        return (92, 224, 214), True    # accent_light, bright + bold
    if distance == 8:
        return (56, 178, 172), False   # mid teal, fading
    if distance == 2:
        return (56, 178, 172), False   # mid teal symmetric
    # Far from the comet — keep visible but dim so the wave clearly stands out
    return (38, 92, 92), False


def _terminal_dot(dot_index: int, frame: int | None) -> str:
    """Block-dot layout: two full-block characters edge to edge.

    `\u2588` (U+2588 FULL BLOCK) fills its terminal cell completely with no padding,
    so two adjacent `\u2588`s render as a single solid 2-cell-wide rectangle with
    NO visible gap between them \u2014 visually one bigger glyph, not two side-by-
    side circles like the rejected `\u2b24\u2b24` attempt. Combined with the comet
    animation in _wave_color, the result is a chunky teal block that brightens
    as the wave passes through it.
    """
    rgb, bold = _wave_color(dot_index, frame)
    return ansi_rgb("\u2588\u2588", rgb, bold=bold)


def _terminal_dot_row(indices: list[int], frame: int | None) -> str:
    # Spacing tuned for the 2-char-wide block dot to keep the formation
    # visually centered next to the CAS lettering and to match the original
    # zigzag rhythm.
    if len(indices) == 1:
        return "    " + _terminal_dot(indices[0], frame)
    return _terminal_dot(indices[0], frame) + "      " + _terminal_dot(indices[1], frame)


def banner_text(frame: int | None = None) -> str:
    dot_rows = [[0], [1, 2], [3], [4, 5], [6], [7, 8], [9]]
    rows: list[str] = []
    for i, left in enumerate(BANNER[:7]):
        right = _terminal_dot_row(dot_rows[i], frame)
        rows.append(f"{ansi(left.ljust(31), 'accent_light', bold=True)}{right}")
    rows.extend(ansi(row, "slate_500") for row in BANNER[7:])
    return "\n".join(rows)


def play_banner_wave(cycles: int = 3, frame_delay: float = 0.08) -> None:
    """Animate the banner by redrawing it with an ANSI color wave."""
    if not COLOR_ENABLED or not sys.stdout.isatty():
        print(banner_text())
        return
    line_count = len(banner_text(0).splitlines())
    sys.stdout.write("\x1b[?25l")
    try:
        for frame in range(cycles * 10):
            if frame:
                sys.stdout.write(f"\x1b[{line_count}F")
            sys.stdout.write(banner_text(frame % 10))
            sys.stdout.write("\n")
            sys.stdout.flush()
            time.sleep(frame_delay)
    finally:
        sys.stdout.write("\x1b[?25h")
        sys.stdout.flush()


def _compiling_spinner_frame(frame: int, dot_count: int = 10) -> str:
    """Render one frame of the inline compiling spinner.

    Reuses _wave_color so the comet head/tail palette matches the banner wave.
    Frame is the leading-edge dot index (0..dot_count-1). The frame is a single
    line: dim teal "compiling" prefix + spaced row of small block dots.
    """
    label = ansi_rgb("compiling", ANSI_RGB["accent"], bold=False)
    dots: list[str] = []
    for dot_index in range(dot_count):
        rgb, bold = _wave_color(dot_index, frame % dot_count)
        # Single block char for the inline spinner; the banner uses two for
        # display weight, but inline next to text a single block keeps the
        # row compact and avoids wrapping in narrow terminals.
        dots.append(ansi_rgb("█", rgb, bold=bold))
    return f"{label} {' '.join(dots)}"


def play_compiling_spinner(stop_event: Any, *, delay_before_show: float = 0.25, frame_delay: float = 0.08) -> None:
    """Animate a one-line "compiling..." comet spinner until stop_event is set.

    Designed to run in a daemon thread while the main thread calls
    compile_expression(). The spinner only becomes visible after
    delay_before_show seconds so fast compiles do not flicker. When the
    stop_event is set the spinner clears its line with an ANSI clear-line
    escape and restores the cursor.

    Gating mirrors play_banner_wave: only renders when COLOR_ENABLED is true
    and stdout is a tty. Otherwise it waits silently for stop_event.
    """
    if not COLOR_ENABLED or not sys.stdout.isatty():
        # Still respect the stop_event so the caller's thread.join() returns
        # promptly; just emit nothing.
        stop_event.wait()
        return

    # Hold off on first render so fast compiles don't flicker the terminal.
    if stop_event.wait(delay_before_show):
        return

    sys.stdout.write("\x1b[?25l")
    try:
        frame = 0
        while not stop_event.is_set():
            sys.stdout.write("\r\x1b[2K")
            sys.stdout.write(_compiling_spinner_frame(frame))
            sys.stdout.flush()
            frame += 1
            if stop_event.wait(frame_delay):
                break
    finally:
        # Clear the spinner line and restore the cursor unconditionally so
        # the next print() lands on a clean row even on Ctrl+C.
        sys.stdout.write("\r\x1b[2K")
        sys.stdout.write("\x1b[?25h")
        sys.stdout.flush()


def startup_hint_text() -> str:
    return (
        f"{ansi('Type ', 'slate_500')}"
        f"{ansi(':help', 'slate_300', bold=True)} "
        f"{ansi('for commands, ', 'slate_500')}"
        f"{ansi(':examples', 'slate_300', bold=True)} "
        f"{ansi('for sample expressions, ', 'slate_500')}"
        f"{ansi(':mirror', 'slate_300', bold=True)} "
        f"{ansi('for 1:1 translations, ', 'slate_500')}"
        f"{ansi(':dict', 'slate_300', bold=True)} "
        f"{ansi('for terms, ', 'slate_500')}"
        f"{ansi(':quit', 'slate_300', bold=True)} "
        f"{ansi('to exit.', 'slate_500')}"
    )


def examples_text(view: str = "cas") -> str:
    rows: list[str] = []
    grouped: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for i, ex in enumerate(EXAMPLES, 1):
        grouped[ex["category"]].append((i, ex))
    for category, items in grouped.items():
        rows.append(line(category, 92))
        for i, ex in items:
            if view == "natural":
                rows.append(f"{ansi(f'{i:>2}.', 'slate_500')} {ansi(ex['natural'], 'slate_300')}")
                rows.append(f"    {ansi('CAS:', 'slate_500')} {highlight_ansi(ex['expr'])}")
            elif view == "mirror":
                rows.append(
                    f"{ansi(f'{i:>2}.', 'slate_500')} {ansi('(', 'slate_600')}"
                    f"{highlight_ansi(ex['expr'])}{ansi(')', 'slate_600')} "
                    f"{ansi(ex['natural'], 'slate_300')}"
                )
            else:
                rows.append(f"{ansi(f'{i:>2}.', 'slate_500')} {highlight_ansi(ex['expr'])}")
                rows.append(f"    {ansi('->', 'slate_500')} {ansi(ex['label'], 'slate_400')}")
                rows.append(f"    {ansi('NL:', 'slate_500')} {ansi(ex['natural'], 'slate_300')}")
    return "\n".join(rows)


def palette_text() -> str:
    width = 92
    rows = [line("Symbol Palette", width)]
    for sym, title in SYMBOL_PALETTE:
        rows.append(f"{highlight_ansi(sym):<4} {ansi(title, 'slate_400')}")
    return "\n".join(rows)


def reference_text() -> str:
    rows = [line("Reference", 92)]
    rows.append(ansi("Noetics (^0 - ^9)", "slate_500", bold=True))
    rows.extend(f"  {ansi(f'^{i:<2}', 'cyan')} {ansi(name, 'slate_400')}" for i, name in enumerate(OPERATOR_NAMES))
    rows.append("")
    rows.append(ansi("Domains", "slate_500", bold=True))
    rows.extend(f"  {ansi(f'^{code:<2}', 'emerald')} {ansi(name, 'slate_400')}" for code, name in DOMAIN_NAMES.items())
    rows.append("")
    rows.append(ansi("Drives", "slate_500", bold=True))
    rows.extend(f"  {ansi(f'F{i + 1:<2}', 'amber')} {ansi(name, 'slate_400')}" for i, name in enumerate(DRIVE_NAMES))
    rows.append("")
    rows.append(ansi("Registers", "slate_500", bold=True))
    rows.extend(f"  {ansi(f'|{code:<2}', 'fuchsia')} {ansi(name, 'slate_400')}" for code, name in REGISTER_NAMES.items())
    return "\n".join(rows)


def dictionary_text(query: str = "") -> str:
    needle = query.strip().lower()
    entries = [
        entry
        for entry in DICTIONARY
        if not needle
        or needle in entry["term"].lower()
        or needle in entry["category"].lower()
        or needle in entry["notation"].lower()
        or needle in entry["definition"].lower()
    ]
    if not entries:
        return f"  no dictionary entries match {query!r}"

    rows: list[str] = []
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for entry in entries:
        grouped[entry["category"]].append(entry)

    title = "CAS Dictionary" if not needle else f"CAS Dictionary: {query}"
    rows.append(line(title, 92))
    for category, items in grouped.items():
        rows.append("")
        rows.append(ansi(category, "slate_500", bold=True))
        for entry in items:
            rows.append(f"  {ansi(entry['term'], 'accent_light', bold=True)} {ansi(entry['notation'], 'violet')}")
            rows.append(f"    {ansi(entry['definition'], 'slate_300')}")
            if entry.get("example"):
                rows.append(f"    {ansi('example:', 'slate_500')} {highlight_ansi(entry['example'])}")
            if entry.get("learn"):
                rows.append(f"    {ansi('learn:', 'slate_500')} {ansi(entry['learn'], 'slate_400')}")
    return "\n".join(rows)


def learning_text() -> str:
    rows = [line("CAS Learning Path", 92)]
    for step in LEARNING_PATH:
        rows.append("")
        rows.append(ansi(step["title"], "accent_light", bold=True))
        rows.append(f"  {ansi('goal:', 'slate_500')} {ansi(step['goal'], 'slate_300')}")
        rows.append(f"  {ansi('terms:', 'slate_500')} {ansi(step['terms'], 'slate_400')}")
        rows.append(f"  {ansi('try:', 'slate_500')} {highlight_ansi(step['practice'])}")
    rows.append("")
    rows.append(ansi("Use :dict TERM to look up any term, then paste the try-expression at cas>.", "slate_500"))
    return "\n".join(rows)


def example_by_index(index: int) -> str | None:
    if 1 <= index <= len(EXAMPLES):
        return EXAMPLES[index - 1]["expr"]
    return None


def _items_by_id(diagram: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for node in diagram.get("nodes", []):
        items[node.get("id", "")] = node
    for container in diagram.get("containers", []):
        items[container.get("id", "")] = container
    return items


def _label(item: dict[str, Any] | None, fallback: str = "?") -> str:
    if not item:
        return fallback
    label = str(item.get("label") or item.get("id") or fallback)
    if isinstance(item.get("cardinality"), int):
        label = f"{label} ({item['cardinality']})"
    return label


def _label_ansi(item: dict[str, Any] | None, fallback: str = "?") -> str:
    if not item:
        return ansi(fallback, "slate_400")
    return ansi(_label(item, fallback), _color_name(item.get("kind", "")), bold=True)


def _color_name(kind: str) -> str:
    if "cluster" in kind or kind == "meta_set":
        return "teal"
    if kind == "state":
        return "cyan"
    if kind == "noetic":
        return "cyan"
    if kind == "drive":
        return "amber"
    if kind == "domain":
        return "emerald"
    if kind == "register":
        return "fuchsia"
    if kind in {"foundation", "subfoundation"}:
        return "amber"
    if kind in {"call", "operator"}:
        return "purple"
    if kind in {"production_target", "emergent"}:
        return "purple"
    return "slate_400"


def _family(diagram: dict[str, Any]) -> str:
    layouts = diagram.get("layouts", [])
    if "grid" in layouts:
        return "grid"
    if "petals" in layouts:
        return "petals"
    if "fractal" in layouts:
        return "fractal"
    if "recipe" in layouts or "dependency" in layouts:
        return "recipe"
    if diagram.get("containers") and ("containment" in layouts or "topos" in layouts):
        return "containment"
    return "semantic"


def terminal_diagram(diagram: dict[str, Any], result: dict[str, Any] | None = None, title: str = "CAS Diagram") -> str:
    if not diagram or (not diagram.get("nodes") and not diagram.get("containers")):
        return ""
    result = result if isinstance(result, dict) else {}
    family = _family(diagram)
    lines = [line(f"CAS Diagram: {family}", 92), f"{ansi('expr:', 'slate_500')} {highlight_ansi(title)}"]
    if family == "grid":
        lines.extend(_grid_diagram(diagram))
    elif family == "petals":
        lines.extend(_petal_diagram(diagram))
    elif family == "fractal":
        lines.extend(_fractal_diagram(diagram))
    elif family == "recipe":
        lines.extend(_recipe_diagram(diagram))
    elif family == "containment":
        lines.extend(_containment_diagram(diagram, result))
    else:
        lines.extend(_semantic_diagram(diagram, result))
    lines.append(line("", 92))
    return "\n".join(lines)


def _grid_diagram(diagram: dict[str, Any]) -> list[str]:
    items = _items_by_id(diagram)
    noetics = sorted(
        [n for n in diagram.get("nodes", []) if n.get("kind") == "noetic"],
        key=lambda n: int(str(n.get("label", "CO-0")).split("-")[-1]),
    )
    domains = sorted(
        [n for n in diagram.get("nodes", []) if n.get("kind") == "domain"],
        key=lambda n: "PCEO".find(str(n.get("label", ""))) if str(n.get("label", "")) in "PCEO" else 99,
    )
    rows = ["", ansi("Cartesian product grid", "slate_500", bold=True)]
    rows.append("        " + "  ".join(_label_ansi(d) for d in domains))
    for n in noetics:
        rows.append(f"  {_label_ansi(n):<5} " + "  ".join(ansi("•", "cyan") for _ in domains))
    rows.append("")
    for edge in diagram.get("edges", []):
        rows.append(f"  {_label_ansi(items.get(edge.get('source')), str(edge.get('source')))} {ansi('->', 'white')} {_label_ansi(items.get(edge.get('target')), str(edge.get('target')))} {ansi(f'[{edge.get('label', edge.get('kind', 'edge'))}]', 'slate_500')}")
    return rows


def _petal_diagram(diagram: dict[str, Any]) -> list[str]:
    items = _items_by_id(diagram)
    base_edges = [e for e in diagram.get("edges", []) if e.get("kind") in {"cover_base", "partition_base"}]
    member_edges = [e for e in diagram.get("edges", []) if e.get("kind") in {"cover_member", "partition_member"}]
    rows = ["", ansi("Cover / partition petals", "slate_500", bold=True)]
    if base_edges:
        base = items.get(base_edges[0].get("source"))
        rows.append(f"  {ansi('base:', 'slate_500')} {_label_ansi(base, str(base_edges[0].get('source')))}")
    for edge in member_edges:
        member = items.get(edge.get("source"))
        children = member.get("contains", []) if member else []
        child_labels = [_label_ansi(items.get(child), child) for child in children[:8]]
        suffix = " ..." if len(children) > 8 else ""
        rows.append(f"  {ansi('petal:', 'slate_500')} {_label_ansi(member, str(edge.get('source')))} {ansi('->', 'white')} {', '.join(child_labels)}{ansi(suffix, 'slate_500')}")
    return rows


def _fractal_diagram(diagram: dict[str, Any]) -> list[str]:
    nodes = [n for n in diagram.get("nodes", []) if n.get("role") == "fractal_step"]
    nodes.sort(key=lambda n: int(n.get("step") or 0))
    rows = ["", ansi("Self-similar composition chain", "slate_500", bold=True)]
    for i, node in enumerate(nodes):
        connector = "└─" if i == len(nodes) - 1 else "├─"
        indent = "  " * i
        rows.append(f"{ansi(indent + connector, 'slate_500')} {_label_ansi(node)}")
    return rows


def _recipe_diagram(diagram: dict[str, Any]) -> list[str]:
    items = _items_by_id(diagram)
    recipe_edges = [e for e in diagram.get("edges", []) if e.get("kind") == "recipe_prerequisite"]
    target_ids = {e.get("target") for e in recipe_edges}
    rows = ["", ansi("Production recipe graph", "slate_500", bold=True)]
    for target_id in target_ids:
        rows.append(f"  {ansi('target:', 'slate_500')} {_label_ansi(items.get(str(target_id)), str(target_id))}")
        for edge in recipe_edges:
            if edge.get("target") != target_id:
                continue
            coeff = edge.get("label") or edge.get("coefficient") or "input"
            rows.append(f"    {_label_ansi(items.get(edge.get('source')), str(edge.get('source'))):<12} {ansi(f'--{coeff}-->', 'orange')} {_label_ansi(items.get(str(target_id)), str(target_id))}")
    if not recipe_edges:
        rows.extend(_semantic_diagram(diagram, {}).copy())
    return rows


def _containment_diagram(diagram: dict[str, Any], result: dict[str, Any]) -> list[str]:
    items = _items_by_id(diagram)
    rows = ["", ansi("Containment / topos view", "slate_500", bold=True)]
    for container in diagram.get("containers", []):
        rows.append(f"  {ansi('╭─', 'teal')} {_label_ansi(container)}")
        children = container.get("contains", [])
        for child in children[:16]:
            rows.append(f"  {ansi('│  ├─', 'slate_500')} {_label_ansi(items.get(child), child)}")
        if len(children) > 16:
            rows.append(f"  {ansi('│  └─', 'slate_500')} {ansi(f'... {len(children) - 16} more', 'slate_500')}")
        rows.append(f"  {ansi('╰', 'teal')}")
    if result.get("kind") == "meta_assertion":
        mark = U["check"] if result.get("holds") is True else U["cross"] if result.get("holds") is False else "?"
        rows.append(f"  {ansi('assertion:', 'slate_500')} {ansi(result.get('message', result.get('operator')), 'green' if result.get('holds') is True else 'red')} {ansi(mark, 'green' if result.get('holds') is True else 'red')}")
    for edge in diagram.get("edges", [])[:12]:
        rows.append(f"  {ansi('edge:', 'slate_500')} {_label_ansi(items.get(edge.get('source')), str(edge.get('source')))} {ansi(edge.get('label', edge.get('kind', '->')), 'teal')} {_label_ansi(items.get(edge.get('target')), str(edge.get('target')))}")
    return rows


def _semantic_diagram(diagram: dict[str, Any], result: dict[str, Any]) -> list[str]:
    items = _items_by_id(diagram)
    rows = ["", ansi("Semantic graph", "slate_500", bold=True)]
    for node in diagram.get("nodes", [])[:24]:
        rows.append(f"  {ansi('node:', 'slate_500')} {_label_ansi(node):<24} {ansi(f'[{node.get('kind', 'node')}]', 'slate_500')}")
    for container in diagram.get("containers", [])[:12]:
        rows.append(f"  {ansi('box:', 'slate_500')}  {_label_ansi(container):<24} {ansi(f'[{container.get('kind', 'container')}]', 'slate_500')}")
    for edge in diagram.get("edges", [])[:24]:
        rows.append(f"  {ansi('edge:', 'slate_500')} {_label_ansi(items.get(edge.get('source')), str(edge.get('source')))} {ansi('->', 'white')} {_label_ansi(items.get(edge.get('target')), str(edge.get('target')))} {ansi(f'[{edge.get('label', edge.get('kind', 'edge'))}]', 'slate_500')}")
    if result.get("kind") == "meta_assertion":
        mark = U["check"] if result.get("holds") is True else U["cross"] if result.get("holds") is False else "?"
        rows.append(f"  {ansi('assertion:', 'slate_500')} {ansi(result.get('message', result.get('operator')), 'green' if result.get('holds') is True else 'red')} {ansi(mark, 'green' if result.get('holds') is True else 'red')}")
    return rows


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def logo_html() -> str:
    ascii_logo = "\n".join(escape(line) for line in BANNER)
    return f"""
<div class="logo-row">
  <pre class="cas-logo">{ascii_logo}</pre>
  <svg viewBox="0 0 1100 1800" class="dot-logo" aria-label="10-dot noetic formation">
    <defs>
      <radialGradient id="dotGrad" cx="35%" cy="35%" r="65%">
        <stop offset="0%" stop-color="{THEME['accent_light']}" />
        <stop offset="70%" stop-color="{THEME['accent']}" />
        <stop offset="100%" stop-color="#2a9d8f" />
      </radialGradient>
      <filter id="dotShadow" x="-20%" y="-20%" width="150%" height="150%">
        <feDropShadow dx="8" dy="8" stdDeviation="0" flood-color="rgba(56,178,172,0.3)" />
        <feDropShadow dx="0" dy="0" stdDeviation="12" flood-color="rgba(56,178,172,0.2)" />
      </filter>
    </defs>
    <circle class="dot" cx="550" cy="210"  r="180" fill="url(#dotGrad)" filter="url(#dotShadow)" style="--i:0" />
    <circle class="dot" cx="185" cy="430"  r="180" fill="url(#dotGrad)" filter="url(#dotShadow)" style="--i:1" />
    <circle class="dot" cx="915" cy="430"  r="180" fill="url(#dotGrad)" filter="url(#dotShadow)" style="--i:2" />
    <circle class="dot" cx="550" cy="680"  r="180" fill="url(#dotGrad)" filter="url(#dotShadow)" style="--i:3" />
    <circle class="dot" cx="185" cy="930"  r="180" fill="url(#dotGrad)" filter="url(#dotShadow)" style="--i:4" />
    <circle class="dot" cx="915" cy="930"  r="180" fill="url(#dotGrad)" filter="url(#dotShadow)" style="--i:5" />
    <circle class="dot" cx="550" cy="1170" r="180" fill="url(#dotGrad)" filter="url(#dotShadow)" style="--i:6" />
    <circle class="dot" cx="185" cy="1410" r="180" fill="url(#dotGrad)" filter="url(#dotShadow)" style="--i:7" />
    <circle class="dot" cx="915" cy="1410" r="180" fill="url(#dotGrad)" filter="url(#dotShadow)" style="--i:8" />
    <circle class="dot" cx="550" cy="1620" r="180" fill="url(#dotGrad)" filter="url(#dotShadow)" style="--i:9" />
  </svg>
</div>
"""


def _examples_html() -> str:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for ex in EXAMPLES:
        grouped[ex["category"]].append(ex)
    chunks = []
    for category, items in grouped.items():
        rows = "".join(
            f'<div class="example"><div class="example-label">{escape(ex["label"])}</div>'
            f'<code>{highlight_html(ex["expr"])}</code>'
            f'<p>{escape(ex["natural"])}</p>'
            f'<div class="example-mirror">({highlight_html(ex["expr"])}) {escape(ex["natural"])}</div></div>'
            for ex in items
        )
        chunks.append(f'<section><h3>{escape(category)}</h3>{rows}</section>')
    return "".join(chunks)


def _palette_html() -> str:
    return "".join(
        f'<span class="symbol-chip" title="{escape(title)}">{highlight_html(sym)}</span>'
        for sym, title in SYMBOL_PALETTE
    )


def _reference_html() -> str:
    noetics = "".join(f"<div><code>{span('^' + str(i), 'cyan')}</code> {escape(name)}</div>" for i, name in enumerate(OPERATOR_NAMES))
    domains = "".join(f"<div><code>{span('^' + code, 'emerald')}</code> {escape(name)}</div>" for code, name in DOMAIN_NAMES.items())
    drives = "".join(f"<div><code>{span('F' + str(i + 1), 'amber')}</code> {escape(name)}</div>" for i, name in enumerate(DRIVE_NAMES))
    registers = "".join(f"<div><code>{span('|' + code, 'fuchsia')}</code> {escape(name)}</div>" for code, name in REGISTER_NAMES.items())
    return f"""
<section><h3>Noetics (^0 - ^9)</h3>{noetics}</section>
<section><h3>Domains</h3>{domains}</section>
<section><h3>Drives</h3>{drives}</section>
<section><h3>Registers</h3>{registers}</section>
"""


def _dictionary_html() -> str:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for entry in DICTIONARY:
        grouped[entry["category"]].append(entry)
    sections: list[str] = []
    for category, entries in grouped.items():
        rows = "".join(
            f'<div class="dict-entry"><div><strong>{escape(entry["term"])}</strong> '
            f'<code>{highlight_html(entry["notation"])}</code></div>'
            f'<p>{escape(entry["definition"])}</p>'
            f'<div class="dict-example">example: {highlight_html(entry["example"])}</div>'
            f'<div class="dict-learn">learn: {escape(entry["learn"])}</div></div>'
            for entry in entries
        )
        sections.append(f'<section><h3>{escape(category)}</h3>{rows}</section>')
    return "".join(sections)


def _learning_html() -> str:
    rows = "".join(
        f'<div class="learn-step"><strong>{escape(step["title"])}</strong>'
        f'<p>{escape(step["goal"])}</p>'
        f'<div>terms: {escape(step["terms"])}</div>'
        f'<div>try: <code>{highlight_html(step["practice"])}</code></div></div>'
        for step in LEARNING_PATH
    )
    return f"<section><h3>Learning Path</h3>{rows}</section>"


def result_summary_html(data: dict[str, Any]) -> str:
    if not data.get("valid"):
        return f'<div class="result invalid">INVALID: {escape(str(data.get("error")))}</div>'
    type_info = data.get("type") or {}
    result = data.get("result") or {}
    kind = type_info.get("kind", "?")
    tokens = len(data.get("tokens") or [])
    bytecode = len(data.get("bytecode") or [])
    meaning = ""
    if isinstance(result, dict):
        if result.get("kind") == "meta_assertion":
            ok = result.get("holds")
            mark = U["check"] if ok is True else U["cross"] if ok is False else "?"
            cls = "ok" if ok is True else "bad" if ok is False else ""
            meaning = f'<p class="{cls}">{escape(str(result.get("message", result.get("operator"))))} {mark}</p>'
        elif result.get("kind") == "meta_set":
            meaning = f'<p>{escape(str(result.get("name", "set")))} ({escape(str(result.get("cardinality", "?")))} elements)</p>'
        elif result.get("kind") == "fractal":
            meaning = f'<p>Fractal [{escape(":".join(str(x) for x in result.get("sequence", [])))}] -> {escape(str(result.get("composed_operator", "?")))}</p>'
        elif result.get("kind") == "state":
            meaning = f'<p>{escape(str(result.get("dominant_operator", "?")))} in {escape(str(result.get("dominant_domain", "?")))} domain</p>'
        elif result.get("kind") == "recipe":
            meaning = f'<p>Recipe -> Ω_{escape(str(result.get("target", "?")))} from {len(result.get("prerequisites") or [])} prerequisite(s)</p>'
    return f"""
<div class="result valid">
  <div class="result-top">
    <span class="badge">valid</span>
    <span>engine: {escape(str(data.get("engine", "rust+python")))}</span>
    <span>type: {escape(str(kind))}</span>
    <span>tokens: {tokens}</span>
    <span>bytecode: {bytecode}</span>
  </div>
  {meaning}
</div>
"""


def compiler_shell_html(
    *,
    source: str,
    artifact_data: dict[str, Any],
    svg: str,
    terminal_preview: str,
    title: str = "CAS Offline Compiler",
) -> str:
    """Standalone offline HTML that visually mirrors the PWA compiler page."""
    diagram = artifact_data.get("diagram") or {}
    layouts = diagram.get("layouts") or []
    layout_chips = "".join(f'<span class="layout-chip">{escape(str(layout))}</span>' for layout in layouts[:6])
    preview = escape(strip_ansi(terminal_preview))
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
  :root {{
    --bg: {THEME['bg']};
    --panel: {THEME['panel']};
    --panel-soft: {THEME['panel_soft']};
    --border: {THEME['border']};
    --accent: {THEME['accent']};
    --accent-light: {THEME['accent_light']};
    --slate-300: {THEME['slate_300']};
    --slate-400: {THEME['slate_400']};
    --slate-500: {THEME['slate_500']};
    --slate-600: {THEME['slate_600']};
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    min-height: 100vh;
    background:
      radial-gradient(circle at 12% 8%, rgba(56,178,172,.16), transparent 32rem),
      radial-gradient(circle at 88% 80%, rgba(99,102,241,.13), transparent 34rem),
      var(--bg);
    color: var(--slate-300);
    font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  .shell {{
    width: min(1200px, calc(100vw - 32px));
    min-height: calc(100vh - 32px);
    margin: 16px auto;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 320px;
    border: 1px solid var(--border);
    border-radius: 18px;
    overflow: hidden;
    background: rgba(13,17,23,.95);
    box-shadow: 0 24px 100px rgba(0,0,0,.48);
  }}
  .main {{ min-width: 0; display: flex; flex-direction: column; }}
  .terminal {{ flex: 1; padding: 22px; overflow: auto; }}
  .input-bar {{
    border-top: 1px solid var(--border);
    background: var(--panel);
    padding: 10px 14px 14px;
  }}
  .mode-row {{ display: flex; gap: 8px; margin-bottom: 9px; }}
  .mode {{ border-radius: 7px; padding: 5px 9px; font: 11px ui-monospace, Consolas, monospace; color: var(--slate-600); border: 1px solid transparent; }}
  .mode.active {{ color: var(--accent-light); background: rgba(56,178,172,.14); border-color: rgba(56,178,172,.22); }}
  .palette {{ display: flex; gap: 6px; overflow-x: auto; padding-bottom: 8px; }}
  .symbol-chip {{
    min-height: 28px;
    display: inline-grid;
    place-items: center;
    padding: 5px 9px;
    border-radius: 7px;
    border: 1px solid var(--border);
    background: rgba(255,255,255,.025);
    font: 13px ui-monospace, Consolas, monospace;
  }}
  .prompt-line {{ display: flex; align-items: flex-start; gap: 10px; font: 14px ui-monospace, Consolas, monospace; }}
  .prompt {{ color: var(--accent-light); font-weight: 800; padding-top: 2px; }}
  .expr-box {{ flex: 1; min-height: 38px; border-radius: 8px; padding: 7px 0; white-space: pre-wrap; word-break: break-word; }}
  .logo-row {{ display: flex; align-items: flex-start; gap: 16px; margin-bottom: 14px; }}
  .cas-logo {{ margin: 0; color: var(--accent-light); font: 700 10px/1.08 ui-monospace, Consolas, monospace; white-space: pre; }}
  .dot-logo {{ height: 190px; width: 118px; flex: 0 0 auto; }}
  .dot-logo .dot {{
    opacity: .28;
    animation: tks-wave 2.8s ease-in-out infinite;
    animation-delay: calc(var(--i) * .13s);
  }}
  @keyframes tks-wave {{
    0%, 100% {{ opacity: .28; }}
    18% {{ opacity: 1; }}
    42% {{ opacity: .58; }}
    62% {{ opacity: .34; }}
  }}
  .hint {{ color: var(--slate-500); font-size: 12px; margin: 0 0 16px; }}
  .card {{
    border: 1px solid rgba(56,178,172,.18);
    background: rgba(56,178,172,.035);
    border-radius: 12px;
    padding: 13px;
    margin-top: 14px;
  }}
  .result-top {{ display: flex; flex-wrap: wrap; gap: 8px; color: var(--slate-500); font: 11px ui-monospace, Consolas, monospace; }}
  .badge {{ color: #86efac; background: rgba(34,197,94,.12); border: 1px solid rgba(34,197,94,.22); border-radius: 999px; padding: 2px 8px; }}
  .result p {{ margin: 9px 0 0; color: var(--slate-300); }}
  .result .ok {{ color: #86efac; }}
  .result .bad {{ color: #fca5a5; }}
  .diagram-head {{ display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin: 16px 0 8px; }}
  .diagram-title {{ color: var(--slate-500); font-size: 9px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }}
  .layout-chip {{ border: 1px solid rgba(56,178,172,.38); color: #67e8f9; background: rgba(56,178,172,.11); border-radius: 999px; padding: 2px 8px; font-size: 9px; }}
  .diagram-wrap {{ border-radius: 12px; overflow: hidden; background: rgba(2,6,23,.5); }}
  .diagram-wrap svg {{ display: block; width: 100%; height: auto; }}
  .terminal-preview {{ margin: 12px 0 0; padding: 12px; border: 1px solid var(--border); border-radius: 10px; background: rgba(2,6,23,.55); color: var(--slate-400); font: 10px/1.45 ui-monospace, Consolas, monospace; overflow-x: auto; }}
  .side {{ border-left: 1px solid var(--border); background: #0d1117; padding: 18px; overflow: auto; }}
  .side h2 {{ margin: 0 0 14px; color: var(--slate-300); font-size: 12px; letter-spacing: .12em; text-transform: uppercase; }}
  .side h3 {{ margin: 18px 0 8px; color: {THEME['fuchsia']}; opacity: .85; font: 10px ui-monospace, Consolas, monospace; text-transform: uppercase; letter-spacing: .08em; }}
  .example {{ border-radius: 8px; padding: 7px 8px; margin: 3px 0; background: rgba(255,255,255,.018); }}
  .example-label {{ color: var(--slate-500); font-size: 9px; margin-bottom: 3px; }}
  .example p {{ color: var(--slate-400); font-size: 10px; line-height: 1.4; margin: 5px 0 0; }}
  .example-mirror {{ color: var(--slate-500); font-size: 9px; line-height: 1.45; margin-top: 5px; }}
  .dict-entry, .learn-step {{ border-radius: 8px; padding: 7px 8px; margin: 3px 0; background: rgba(255,255,255,.018); }}
  .dict-entry strong, .learn-step strong {{ color: var(--accent-light); font-size: 10px; }}
  .dict-entry p, .learn-step p {{ color: var(--slate-400); font-size: 10px; line-height: 1.4; margin: 4px 0; }}
  .dict-example, .dict-learn, .learn-step div {{ color: var(--slate-500); font-size: 9px; line-height: 1.45; margin-top: 3px; }}
  code {{ font-family: ui-monospace, Consolas, monospace; }}
  .side section div {{ color: var(--slate-500); font-size: 11px; margin: 3px 0; }}
  @media (max-width: 900px) {{ .shell {{ grid-template-columns: 1fr; }} .side {{ border-left: 0; border-top: 1px solid var(--border); }} }}
</style>
<main class="shell">
  <section class="main">
    <div class="terminal">
      {logo_html()}
      <p class="hint">Type <code>:help</code> for commands, <code>:grammar</code> for the BNF, <code>:examples</code> for sample expressions, <code>:dict</code> for terms.</p>
      <div class="card">
        <div class="prompt-line">
          <span class="prompt">cas&gt;</span>
          <code class="expr-box">{highlight_html(source)}</code>
        </div>
        {result_summary_html(artifact_data)}
        <div class="diagram-head"><span class="diagram-title">CAS Diagram</span>{layout_chips}</div>
        <div class="diagram-wrap">{svg}</div>
        <pre class="terminal-preview">{preview}</pre>
      </div>
    </div>
    <div class="input-bar">
      <div class="mode-row"><span class="mode active">CAS Notation</span><span class="mode">Natural Language</span></div>
      <div class="palette">{_palette_html()}</div>
      <div class="prompt-line"><span class="prompt">cas&gt;</span><code class="expr-box">{highlight_html(source)}</code></div>
    </div>
  </section>
  <aside class="side">
    <h2>Reference</h2>
    <section><h3>Examples</h3>{_examples_html()}</section>
    <section><h3>Dictionary</h3>{_dictionary_html()}</section>
    {_learning_html()}
    {_reference_html()}
  </aside>
</main>
</html>
"""
