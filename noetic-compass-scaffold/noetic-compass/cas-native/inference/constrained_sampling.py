"""Grammar-constrained CAS expression decoding helpers.

This module is deliberately inference-side only.  It does not change the CAS
compiler; instead, it builds bucket-specific finite-state tries from
compiler-valid candidate expressions and lets the model choose only legal next
tokens from that trie.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import re
from typing import Iterable, Protocol

from api.notation import compile_expression


BUCKETS = (
    "v74_baseline",
    "v75_register",
    "v77_rule_four",
    "v77_omega",
    "v76_production",
    "meta_logic",
)

DOMAINS = ("P", "C", "E", "O")
REGISTERS = ("T", "A", "f", "E")
DRIVES = tuple(range(1, 8))
NOETICS = tuple(range(10))
OMEGA_NAMES = (
    "Ω_presence",
    "Ω_refusal",
    "Ω_grounding",
    "Ω_alignment",
    "Ω_clarity",
    "Ω_resolve",
    "Ω_witness",
    "Ω_attunement",
    "Ω_genesis",
    "Ω_cadence",
    "Ω_invocation",
    "Ω_landing",
)
PRODUCTION_NAMES = (
    "Ω_focused_refusal",
    "Ω_pattern_entrainment_learning",
    "Ω_embodied_safety_check",
    "Ω_grounded_creative_insight",
    "Ω_safe_judgment",
)


class TokenizerLike(Protocol):
    EOS_ID: int

    def encode(self, text: str, max_length: int = 512, *, add_special: bool = True) -> list[int]:
        ...

    def decode(self, ids: Iterable[int], *, skip_special: bool = True) -> str:
        ...


@dataclass(frozen=True)
class ConstraintDecision:
    """Allowed next-token decision for a partially generated CAS expression."""

    allowed_token_ids: frozenset[int]
    allow_eos: bool
    state: str
    reason: str
    valid_prefix: bool
    candidate_count: int
    prefix_text: str


@dataclass
class _TrieNode:
    children: dict[int, "_TrieNode"] = field(default_factory=dict)
    terminal: bool = False


def _state(n: int, domain: str, drive: int, register: str | None = None) -> str:
    suffix = f"^{n}^{domain}_{{F{drive}}}"
    return f"{suffix}|{register}" if register else suffix


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _compile_valid(expr: str) -> bool:
    try:
        return bool(compile_expression(expr).valid)
    except Exception:
        return False


def _v74_candidates() -> Iterable[str]:
    for n in NOETICS:
        for domain in DOMAINS:
            for drive in DRIVES:
                yield _state(n, domain, drive)
                yield f"{_state(n, domain, drive)} * {_state((n + 1) % 10, domain, drive)}"
                yield f"{_state(n, domain, drive)} + {_state((n + 2) % 10, domain, ((drive % 7) + 1))}"
    for drive in DRIVES:
        yield f"RPM(F{drive})"
    for parts in ("3:8:5:2", "1:4:7:0", "9:2:6:3", "5:1:8:4"):
        yield f"Φ<{parts}>"


def _v75_candidates() -> Iterable[str]:
    for n in NOETICS:
        for domain in DOMAINS:
            for drive in DRIVES:
                for register in REGISTERS:
                    yield _state(n, domain, drive, register)
                    yield (
                        f"{_state(n, domain, drive, register)} + "
                        f"{_state((n + 1) % 10, domain, ((drive % 7) + 1), REGISTERS[(REGISTERS.index(register) + 1) % len(REGISTERS)])}"
                    )
    for n in NOETICS:
        for domain in DOMAINS:
            yield f"^{n}^{domain}_{{F1}}|⟨T,A,f⟩"
            yield f"^{n}^{domain}_{{F2}}|⟨A,f,E⟩"


def _rule_four_candidates() -> Iterable[str]:
    for n in NOETICS:
        for domain in DOMAINS:
            for drive in (1, 2, 3, 4):
                yield (
                    f"{_state(n, domain, drive, 'T')} + "
                    f"{_state(n, domain, drive, 'A')} + "
                    f"{_state(n, domain, drive, 'f')}"
                )
                omega = OMEGA_NAMES[(n + drive) % len(OMEGA_NAMES)]
                yield (
                    f"({_state(n, domain, drive, 'A')} × "
                    f"{_state(n, domain, drive, 'f')}) = ^{n}^{domain}|{omega}"
                )
                yield (
                    f"({_state(n, domain, drive, 'A')} × "
                    f"{_state(n, domain, drive, 'f')} × "
                    f"{_state(n, domain, drive, 'T')}) = ^{n}^{domain}|{omega}"
                )


def _omega_candidates() -> Iterable[str]:
    for idx, omega in enumerate(OMEGA_NAMES):
        n = idx % 10
        domain = DOMAINS[idx % len(DOMAINS)]
        drive = (idx % 7) + 1
        yield (
            f"({_state(n, domain, drive, 'A')} × "
            f"{_state(n, domain, drive, 'f')}) = ^{n}^{domain}|{omega}"
        )
        yield (
            f"({_state(n, domain, drive, 'A')} × "
            f"{_state(n, domain, drive, 'f')} × "
            f"{_state(n, domain, drive, 'T')}) = ^{n}^{domain}|{omega}"
        )
        yield (
            f"({_state(n, domain, drive, 'T')} × "
            f"{_state(n, domain, drive, 'E')}) = ^{n}^{domain}|{omega}"
        )


def _production_candidates() -> Iterable[str]:
    ingredient_sets = (
        (("1", "P", 1, "A", "0.50"), ("3", "P", 2, "f", "0.30"), ("7", "P", 7, "T", "0.20")),
        (("2", "C", 3, "A", "0.45"), ("5", "C", 1, "f", "0.35"), ("8", "C", 4, "E", "0.20")),
        (("4", "O", 2, "E", "0.60"), ("6", "O", 6, "A", "0.25"), ("9", "O", 3, "T", "0.15")),
        (("0", "E", 5, "f", "0.40"), ("1", "E", 1, "A", "0.40"), ("2", "E", 7, "T", "0.20")),
    )
    for idx, target in enumerate(PRODUCTION_NAMES):
        ingredients = ingredient_sets[idx % len(ingredient_sets)]
        rhs = " + ".join(
            f"{coeff}·{_state(int(n), domain, drive, register)}"
            for n, domain, drive, register, coeff in ingredients
        )
        yield f"Θ({target}) = {rhs} → {target}"


def _meta_logic_candidates() -> Iterable[str]:
    yield "^2 ∈ Noetics"
    yield "^2 ∉ Domains"
    yield "NoeticCluster{^2, ^7} ⊆ Noetics"
    yield "NoeticCluster{^2} ⊂ Noetics"
    yield "Noetics ⊇ NoeticCluster{^2, ^7}"
    yield "∅ ⊆ Noetics"
    yield "|Noetics|"
    yield "Product(Noetics, Domains)"
    yield "Coordinate{^6, P, F2, T}"
    yield "NoeticCluster{^1, ^2} ∪ NoeticCluster{^3, ^4}"
    yield "NoeticCluster{^1, ^2} ∩ NoeticCluster{^2, ^3}"
    yield "NoeticCluster{^1, ^2, ^3} ∖ NoeticCluster{^2}"
    yield "StateCluster{^2^P, ^7^O} ⊆ States"
    yield "CoverOf(SubFoundations, Foundation_1, Foundation_2, Foundation_3, Foundation_4, Foundation_5, Foundation_6, Foundation_7)"


def _raw_candidates(bucket: str) -> Iterable[str]:
    if bucket == "v74_baseline":
        return _v74_candidates()
    if bucket == "v75_register":
        return _v75_candidates()
    if bucket == "v77_rule_four":
        return _rule_four_candidates()
    if bucket == "v77_omega":
        return _omega_candidates()
    if bucket == "v76_production":
        return _production_candidates()
    if bucket == "meta_logic":
        return _meta_logic_candidates()
    return ()


@lru_cache(maxsize=None)
def build_candidate_expressions(bucket: str, max_candidates: int = 5000) -> tuple[str, ...]:
    """Return compiler-valid candidate expressions for a generation bucket."""
    candidates: list[str] = []
    for expr in _unique(_raw_candidates(bucket)):
        if _compile_valid(expr):
            candidates.append(expr)
        if len(candidates) >= max_candidates:
            break
    return tuple(candidates)


def build_dataset_candidate_expressions(
    records: Iterable[dict],
    bucket: str,
    *,
    max_candidates: int = 5000,
    include_builtin: bool = True,
) -> tuple[str, ...]:
    """Build compiler-valid candidates from dataset records for a bucket.

    Dataset candidates are the next step after the small hand-authored grammar
    bank: they preserve the same compiler-validity guarantee while giving the
    model a much broader, dataset-grounded set of expressions to rerank.
    """
    candidates: list[str] = []
    seen: set[str] = set()

    def add(expr: str) -> None:
        expr = str(expr or "").strip()
        if not expr or expr in seen:
            return
        if _compile_valid(expr):
            seen.add(expr)
            candidates.append(expr)

    for record in records:
        if record.get("_meta", {}).get("bucket") != bucket:
            continue
        add(record.get("cas_expression", ""))
        if len(candidates) >= max_candidates:
            break

    if include_builtin and len(candidates) < max_candidates:
        for expr in build_candidate_expressions(bucket, max_candidates):
            add(expr)
            if len(candidates) >= max_candidates:
                break

    return tuple(candidates)


_MEMBER = "\u2208"
_NOT_MEMBER = "\u2209"
_SUBSET = "\u2282"
_SUBSET_EQ = "\u2286"
_SUPERSET = "\u2283"
_SUPERSET_EQ = "\u2287"
_UNION = "\u222a"
_INTERSECTION = "\u2229"
_DIFFERENCE = "\u2216"
_PRODUCT = "\u00d7"
_OMEGA = "\u03a9"
_THETA = "\u0398"
_LEFT_ANGLE = "\u27e8"
_RIGHT_ANGLE = "\u27e9"

_REGISTER_STATE_RE = re.compile(r"\^\d+(?:\^[PCEO])?(?:_\{F_?\d+\})?\|[TAfE]")
_STATE_RE = re.compile(r"\^\d+\^[PCEO](?:_\{F_?\d+\})?")
_FOUNDATION_RE = re.compile(r"\bFoundation[_\s-]?([1-7])\b", re.IGNORECASE)
_DRIVE_RE = re.compile(r"\bF_?([1-7])\b", re.IGNORECASE)
_NOETIC_REF_RE = re.compile(r"\^([0-9])")

_CARRIERS = ("Noetics", "Domains", "Drives", "Registers", "States", "Foundations", "SubFoundations")
_DOMAIN_WORDS = {
    "principled": "P",
    "principle": "P",
    "cognitive": "C",
    "evaluative": "E",
    "operational": "O",
}
_REGISTER_WORDS = {
    "transcendent": "T",
    "analytical": "A",
    "affective": "f",
    "embodied": "E",
}


def _normalize_symbol_text(text: str) -> str:
    normalized = str(text or "").lower()
    return (
        normalized.replace("\u03c9_", "omega_")
        .replace("\u03a9_", "omega_")
        .replace("omega-", "omega_")
        .replace("omega ", "omega_")
        .replace("theta", "\u03b8")
    )


def _has_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle in text for needle in needles)


def _has_word(text: str, word: str) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}\b", text))


def _ordered_unique(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(item) for item in items if str(item)))


def expression_families(expr: str) -> frozenset[str]:
    """Return structural families present in a compiler candidate expression."""
    expr = str(expr or "").strip()
    normalized = _normalize_symbol_text(expr)
    families: set[str] = set()

    if expr.startswith(f"{_THETA}(") or normalized.startswith("\u03b8("):
        families.add("production")
    if _OMEGA in expr or "omega_" in normalized:
        families.add("omega")
    if _PRODUCT in expr:
        families.add("register_integration")
        if "omega_" in normalized or _OMEGA in expr:
            families.add("omega_integration")
    if " + " in expr and "|" in expr:
        families.add("register_copresence")
    if f"|{_LEFT_ANGLE}" in expr or "|<" in expr:
        families.add("register_set")
    if _REGISTER_STATE_RE.search(expr):
        families.add("register_state")

    if expr.startswith("Product("):
        families.add("product")
    if expr.startswith("Coordinate{") or expr.startswith("CASCoordinate{") or (
        expr.startswith(_LEFT_ANGLE) and expr.endswith(_RIGHT_ANGLE)
    ):
        families.add("coordinate")
    if expr.startswith("Pullback("):
        families.add("pullback")
    if expr.startswith("CoverOf("):
        families.add("cover")
    if expr.startswith("PartitionOf("):
        families.add("partition")

    if _UNION in expr or "Union(" in expr:
        families.add("set_union")
        families.add("set_operation")
    if _INTERSECTION in expr or "Intersection(" in expr:
        families.add("set_intersection")
        families.add("set_operation")
    if _DIFFERENCE in expr or "Difference(" in expr:
        families.add("set_difference")
        families.add("set_operation")
    if _has_any(expr, (_MEMBER, _NOT_MEMBER)):
        families.add("membership")
    if _has_any(expr, (_SUBSET, _SUBSET_EQ, _SUPERSET, _SUPERSET_EQ)):
        families.add("subset")
    if expr.startswith("|") and expr.endswith("|") and len(expr) > 2:
        families.add("cardinality")

    contains_set_operator = bool({"set_operation", "membership", "subset", "cardinality"} & families)
    if expr.startswith("RelationCluster{"):
        families.add("relation_cluster")
    if expr.startswith("StateVariantCluster{"):
        families.add("state_variant_cluster")
    if expr.startswith("StateCluster{"):
        families.add("state_cluster")
        if not contains_set_operator:
            families.add("state_cluster_literal")
    if expr.startswith("NoeticCluster{"):
        families.add("noetic_cluster")
        if not contains_set_operator:
            families.add("noetic_cluster_literal")

    if expr.startswith("\u03a6<") or expr.startswith("Phi<"):
        families.add("fractal")
    if expr.startswith("RPM("):
        families.add("rpm")
    if _STATE_RE.search(expr):
        families.add("v74_state")
    if any(op in expr for op in (" * ", " -> ", " \u2192 ")) and _STATE_RE.search(expr):
        families.add("v74_composition")

    if not families:
        families.add("unknown")
    return frozenset(families)


_FAMILY_PRIORITY = (
    "production",
    "omega_integration",
    "register_integration",
    "register_copresence",
    "register_set",
    "register_state",
    "pullback",
    "partition",
    "cover",
    "product",
    "coordinate",
    "set_union",
    "set_intersection",
    "set_difference",
    "set_operation",
    "membership",
    "subset",
    "cardinality",
    "relation_cluster",
    "state_variant_cluster",
    "state_cluster_literal",
    "state_cluster",
    "noetic_cluster_literal",
    "noetic_cluster",
    "fractal",
    "rpm",
    "v74_composition",
    "v74_state",
    "unknown",
)


def classify_expression_family(expr: str) -> str:
    """Return the primary family for diagnostics and tests."""
    families = expression_families(expr)
    for family in _FAMILY_PRIORITY:
        if family in families:
            return family
    return "unknown"


def infer_prompt_families(prompt: str, bucket: str) -> tuple[str, ...]:
    """Infer which structural families a natural-language prompt is asking for."""
    text = _normalize_symbol_text(prompt)
    families: list[str] = []

    def add(*items: str) -> None:
        for item in items:
            if item not in families:
                families.append(item)

    if _has_any(text, ("recipe", "produces", "produce", "production", "ingredient", "yield", "catalyst", "inhibitor", "leakage", "outcome")):
        add("production")
    if _has_any(text, ("emergent register", "omega_", "arises", "unified", "integrat", "cross-register")):
        add("omega_integration", "register_integration")
    if _has_any(text, ("co-present", "copresent", "co presence", "co-presence")):
        add("register_copresence")
    if _has_any(text, ("clear register", "register manifestation", "register state")):
        add("register_state")
    if "register set" in text:
        add("register_set")

    if _has_any(text, ("finite-meet", "pullback")):
        add("pullback")
    if _has_word(text, "partition") or "partitionof" in text:
        add("partition")
    if _has_word(text, "cover") or "coverof" in text:
        add("cover")
    if _has_any(text, ("cartesian product", "typed product", "product(")):
        add("product")
    elif "product" in text and bucket == "meta_logic":
        add("product")
    if _has_any(text, ("coordinate", "angle-bracket", "angle bracket")):
        add("coordinate")
    if "union" in text or "\u222a" in text:
        add("set_union")
    if "intersection" in text or "\u2229" in text:
        add("set_intersection")
    if _has_any(text, ("set-difference", "set difference", "difference operation")) or "\u2216" in text:
        add("set_difference")
    if _has_any(text, ("union", "intersection", "set-difference", "set difference", "difference operation", "combine under")):
        add("set_operation")
    if _has_any(text, ("belongs", "membership", "member of", "element of")):
        add("membership")
    if _has_any(text, ("subset", "contained", "typed-subset", "superset")):
        add("subset")
    if _has_any(text, ("cardinality", "how many", "count of")):
        add("cardinality")
    if "relation cluster" in text:
        add("relation_cluster")
    if "statevariantcluster" in text or "state variant" in text:
        add("state_variant_cluster")
    if "statecluster" in text or "state cluster" in text:
        if "collect" in text or "typed state cluster" in text or "spanning" in text:
            add("state_cluster_literal")
        add("state_cluster")
    if "noeticcluster" in text or "noetic cluster" in text:
        if "containing" in text or "typed noetic cluster" in text or "over noetics" in text:
            add("noetic_cluster_literal")
        add("noetic_cluster")

    if _has_any(text, ("fractal", "phi<", "\u03c6<")):
        add("fractal")
    if "rpm" in text:
        add("rpm")
    if _has_any(text, ("composition", "transition", "pathway")) and bucket == "v74_baseline":
        add("v74_composition")

    if not families:
        if bucket == "v76_production":
            add("production")
        elif bucket == "v77_omega":
            add("omega_integration", "register_integration")
        elif bucket == "v77_rule_four":
            add("register_copresence", "omega_integration", "register_integration")
        elif bucket == "v75_register":
            add("register_state", "register_copresence", "register_set")
        elif bucket == "v74_baseline":
            add("v74_state", "v74_composition", "fractal", "rpm")

    return tuple(families)


_KNOWN_OMEGA_TERMS = {
    _normalize_symbol_text(name)
    for name in (*OMEGA_NAMES, *PRODUCTION_NAMES)
}


def infer_prompt_required_terms(prompt: str) -> tuple[str, ...]:
    """Extract exact semantic anchors, such as Omega_clarity, when present."""
    text = _normalize_symbol_text(prompt)
    terms: list[str] = []
    for match in re.finditer(r"\bomega([_\s-]+)([a-z][a-z0-9_]*)", text):
        separator, stem = match.groups()
        term = f"omega_{stem.strip('_')}"
        # Plain "omega names" should not force a bogus target; exact
        # underscore form or known Omega names are safe enough to filter by.
        if "_" in separator or term in _KNOWN_OMEGA_TERMS:
            if term not in terms:
                terms.append(term)
    return tuple(terms)


def candidate_matches_required_terms(expr: str, required_terms: Iterable[str]) -> bool:
    text = _normalize_symbol_text(expr)
    return all(term in text for term in required_terms)


def _numbers_after_keyword(text: str, keyword_pattern: str) -> tuple[str, ...]:
    numbers: list[str] = []
    for match in re.finditer(rf"{keyword_pattern}\s+([0-9](?:\s*(?:,|and)\s*[0-9])*)", text):
        numbers.extend(re.findall(r"[0-9]", match.group(1)))
    return _ordered_unique(numbers)


def _foundation_range(text: str) -> tuple[str, ...]:
    for match in re.finditer(r"foundation[_\s-]?([1-7])\s*(?:\.\.|-|through|to)\s*foundation?[_\s-]?([1-7])", text):
        start, end = int(match.group(1)), int(match.group(2))
        if start <= end:
            return tuple(f"F{i}" for i in range(start, end + 1))
    return ()


def expression_slots(expr: str) -> dict[str, tuple[str, ...]]:
    """Extract typed slot values from a CAS expression candidate."""
    expr = str(expr or "")
    slots: dict[str, tuple[str, ...]] = {
        "omega_terms": infer_prompt_required_terms(expr),
        "carriers": _ordered_unique(carrier for carrier in _CARRIERS if re.search(rf"\b{carrier}\b", expr)),
        "noetics": _ordered_unique(_NOETIC_REF_RE.findall(expr)),
        "domains": _ordered_unique(re.findall(r"\^\d+\^([PCEO])", expr)),
        "drives": _ordered_unique(f"F{drive}" for drive in _DRIVE_RE.findall(expr)),
        "foundations": _ordered_unique(f"F{n}" for n in _FOUNDATION_RE.findall(expr)),
        "registers": _ordered_unique(re.findall(r"\|([TAfE])", expr)),
    }

    coordinate = re.search(r"(?:Coordinate\{|<)\s*\^\d+\s*,\s*([PCEO])\s*,\s*F_?([1-7])\s*,\s*([TAfE])", expr)
    if coordinate:
        domain, drive, register = coordinate.groups()
        slots["domains"] = _ordered_unique((*slots["domains"], domain))
        slots["drives"] = _ordered_unique((*slots["drives"], f"F{drive}"))
        slots["registers"] = _ordered_unique((*slots["registers"], register))

    return {key: value for key, value in slots.items() if value}


def infer_prompt_slots(prompt: str, bucket: str) -> dict[str, tuple[str, ...]]:
    """Infer concrete typed CAS slots requested by a prompt.

    This is intentionally conservative: it only extracts explicit slot
    evidence. Generic words like "domain" or "register" do not force values.
    """
    text = _normalize_symbol_text(prompt)
    slots: dict[str, tuple[str, ...]] = {}

    omega_terms = infer_prompt_required_terms(prompt)
    if omega_terms:
        slots["omega_terms"] = omega_terms

    explicit_noetics = _ordered_unique(_NOETIC_REF_RE.findall(prompt))
    named_noetics = _numbers_after_keyword(text, r"\bnoetics?\b")

    carriers = _ordered_unique(carrier for carrier in _CARRIERS if re.search(rf"\b{carrier.lower()}\b", text))
    if named_noetics:
        carriers = tuple(carrier for carrier in carriers if carrier != "Noetics")
    if carriers:
        slots["carriers"] = carriers

    if explicit_noetics or named_noetics:
        slots["noetics"] = _ordered_unique((*explicit_noetics, *named_noetics))

    domains = _ordered_unique(
        domain
        for word, domain in _DOMAIN_WORDS.items()
        if _has_word(text, word)
    )
    explicit_domains = _ordered_unique(re.findall(r"\b(?:domain|domains?)\s+([PCEO])\b", prompt))
    if domains or explicit_domains:
        slots["domains"] = _ordered_unique((*domains, *explicit_domains))

    registers = _ordered_unique(
        register
        for word, register in _REGISTER_WORDS.items()
        if _has_word(text, word)
    )
    explicit_register_matches = re.findall(r"(?:\|([TAfE])\b|\bregister\s+([TAfE])\b)", prompt)
    flattened_registers = _ordered_unique(
        item
        for pair in explicit_register_matches
        for item in pair
        if item
    )
    if registers or flattened_registers:
        slots["registers"] = _ordered_unique((*registers, *flattened_registers))

    foundation_values = _ordered_unique((
        *_foundation_range(text),
        *(f"F{n}" for n in _FOUNDATION_RE.findall(prompt)),
        *(f"F{n}" for n in _DRIVE_RE.findall(prompt)),
    ))
    named_foundations = _numbers_after_keyword(text, r"\bfoundations?\b")
    if named_foundations:
        foundation_values = _ordered_unique((*foundation_values, *(f"F{n}" for n in named_foundations)))
    if foundation_values:
        # Foundation_N and F_N occupy the same finite 1..7 slot space in these
        # prompt/candidate filters; the compiler still owns final type checks.
        slots["foundations"] = foundation_values
        if bucket != "meta_logic":
            slots["drives"] = foundation_values

    return slots


def candidate_matches_slots(expr: str, slots: dict[str, Iterable[str]]) -> bool:
    candidate_slots = expression_slots(expr)
    for key, raw_values in slots.items():
        wanted = set(raw_values)
        if not wanted:
            continue
        if not wanted.issubset(set(candidate_slots.get(key, ()))):
            return False
    return True


def filter_candidates_by_slots(
    candidates: Iterable[str],
    slots: dict[str, Iterable[str]],
) -> tuple[str, ...]:
    return tuple(expr for expr in candidates if candidate_matches_slots(expr, slots))


_SPECIFIC_FILTER_FAMILIES = {
    "production",
    "omega_integration",
    "register_copresence",
    "register_set",
    "register_state",
    "pullback",
    "partition",
    "cover",
    "product",
    "coordinate",
    "set_union",
    "set_intersection",
    "set_difference",
    "membership",
    "subset",
    "cardinality",
    "relation_cluster",
    "state_variant_cluster",
    "state_cluster_literal",
    "noetic_cluster_literal",
    "fractal",
    "rpm",
    "v74_composition",
}


def filter_candidates_by_family(candidates: Iterable[str], families: Iterable[str]) -> tuple[str, ...]:
    wanted = set(families)
    if not wanted:
        return tuple(candidates)
    specific_wanted = wanted & _SPECIFIC_FILTER_FAMILIES
    active_wanted = specific_wanted or wanted
    return tuple(expr for expr in candidates if expression_families(expr) & active_wanted)


def filter_candidates_for_prompt(
    candidates: Iterable[str],
    prompt: str,
    bucket: str,
    *,
    min_candidates: int = 1,
) -> tuple[tuple[str, ...], dict]:
    """Apply prompt-inferred family and exact-term filters with safe fallback."""
    original = tuple(candidates)
    prompt_families = infer_prompt_families(prompt, bucket)
    required_terms = infer_prompt_required_terms(prompt)
    prompt_slots = infer_prompt_slots(prompt, bucket)

    by_family = filter_candidates_by_family(original, prompt_families)
    selected = by_family if len(by_family) >= min_candidates else original
    family_fallback = selected is original and bool(prompt_families)

    by_terms = tuple(expr for expr in selected if candidate_matches_required_terms(expr, required_terms))
    term_fallback = False
    if required_terms:
        if len(by_terms) >= min_candidates:
            selected = by_terms
        else:
            term_fallback = True

    slot_fallback = False
    by_slots = tuple()
    if prompt_slots:
        by_slots = filter_candidates_by_slots(selected, prompt_slots)
        if len(by_slots) >= min_candidates:
            selected = by_slots
        else:
            slot_fallback = True

    diagnostics = {
        "family_filter": "prompt",
        "prompt_families": list(prompt_families),
        "prompt_required_terms": list(required_terms),
        "prompt_slots": {key: list(value) for key, value in prompt_slots.items()},
        "pre_filter_candidate_count": len(original),
        "post_family_candidate_count": len(by_family),
        "post_term_candidate_count": len(by_terms) if required_terms else len(selected),
        "post_slot_candidate_count": len(by_slots) if prompt_slots else len(selected),
        "post_filter_candidate_count": len(selected),
        "family_filter_fallback": bool(family_fallback),
        "term_filter_fallback": bool(term_fallback),
        "slot_filter_fallback": bool(slot_fallback),
    }
    return selected, diagnostics


class CandidateTrieConstraint:
    """Token-level finite-state constraint over compiler-valid candidates."""

    def __init__(
        self,
        tokenizer: TokenizerLike,
        bucket: str,
        *,
        candidates: Iterable[str] | None = None,
        max_candidates: int = 5000,
    ) -> None:
        self.tokenizer = tokenizer
        self.bucket = bucket
        self.candidates = tuple(candidates) if candidates is not None else build_candidate_expressions(bucket, max_candidates)
        self.root = _TrieNode()
        self._inserted = 0
        for candidate in self.candidates:
            token_ids = self._encode(candidate)
            if token_ids:
                self._insert(token_ids)
                self._inserted += 1

    @property
    def candidate_count(self) -> int:
        return self._inserted

    def _encode(self, text: str) -> list[int]:
        return self.tokenizer.encode(text, max_length=512, add_special=False)

    def _insert(self, token_ids: list[int]) -> None:
        node = self.root
        for token_id in token_ids:
            node = node.children.setdefault(int(token_id), _TrieNode())
        node.terminal = True

    def _node_for(self, token_ids: Iterable[int]) -> _TrieNode | None:
        node = self.root
        for raw_id in token_ids:
            token_id = int(raw_id)
            if token_id not in node.children:
                return None
            node = node.children[token_id]
        return node

    def decision(self, generated_ids: Iterable[int], *, primer_ids: Iterable[int] = ()) -> ConstraintDecision:
        prefix_ids = [int(i) for i in primer_ids]
        prefix_ids.extend(int(i) for i in generated_ids)
        node = self._node_for(prefix_ids)
        prefix_text = self.tokenizer.decode(prefix_ids)
        if node is None:
            return ConstraintDecision(
                allowed_token_ids=frozenset(),
                allow_eos=False,
                state="dead_end",
                reason="prefix does not match any compiler-valid candidate",
                valid_prefix=False,
                candidate_count=self.candidate_count,
                prefix_text=prefix_text,
            )
        return ConstraintDecision(
            allowed_token_ids=frozenset(node.children.keys()),
            allow_eos=node.terminal,
            state="accepting" if node.terminal else "in_progress",
            reason="ok",
            valid_prefix=True,
            candidate_count=self.candidate_count,
            prefix_text=prefix_text,
        )

    def primer_ids(self, primer: str) -> list[int]:
        return self._encode(primer)

    def is_compatible_primer(self, primer: str) -> bool:
        return self.decision([], primer_ids=self.primer_ids(primer)).valid_prefix
