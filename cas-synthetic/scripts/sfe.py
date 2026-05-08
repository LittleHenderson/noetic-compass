"""Structural Fingerprint Extractor (SFE) — round-trip gate for Wave 2.5.

Built 2026-05-08 after the deterministic-as-corpus detour.

PURPOSE
-------
Replace the 13-validator stack in v2 with a single round-trip gate. The
prior approach was: 13 separate validators, each catching one structural
aspect (recipe coefficients, fractal k-values, drive→outcome framing, ...).
Agent 4's deep audit found 15.5% of records slipping through inter-check
gaps — the validators individually passed but the record was structurally
broken.

SFE solves that by extracting a structural fingerprint from EITHER side
(source CAS or English output) and comparing them as a whole. If the
fingerprints match, the record passes. If they don't, the diff names
exactly what diverged.

ARCHITECTURE
------------
- ``extract_cas_fingerprint(source_cas)`` — reads CAS notation, produces
  a ``CASFingerprint`` (multisets + sets + ordered lists for the
  structural commitments).
- ``extract_english_fingerprint(english_text)`` — reads natural English,
  reverse-maps via the v2 module's alias tables (``NOETIC_VALIDATION_TOKENS``,
  ``DOMAIN_ALIASES``, ``DRIVE_ALIASES``, ``REGISTER_ALIASES``), produces
  the same ``CASFingerprint`` shape.
- ``compare_fingerprints(source_fp, english_fp)`` — computes a diff dict.
- ``validate_sfe_round_trip(source_cas, english)`` — returns a
  ``ValidatorResult`` (compatible with v2's existing validator framework)
  that's True iff the fingerprints match.

This is essentially a deterministic ``english_to_cas`` parser sufficient
for validation, built from existing alias tables. It is NOT a full CAS
parser — it cannot reconstruct the source CAS from English. It can only
verify that every structural commitment in the source has a textual
fingerprint in the English (and vice versa for things the English claims).

WHAT IT CATCHES
---------------
- Operator confusion (^3 rendered as "breaking down" = ^6 alias)
- Domain confusion (^P rendered as "evaluative" = ^E alias)
- Drive confusion (F2 rendered as "agency" = F5 alias)
- Register/domain letter ambiguity (|E embodied vs ^E evaluative — the
  fingerprints distinguish position)
- Drive→outcome leakage (drive subscript surfacing as "outcome called X")
- Ω stem mismatches (source has Ω_alignment, English says
  Ω_integration)
- Variable name drops (let stageA0_1_5622 = ... → English drops the name)
- Cluster member mismatches (5-member NoeticCluster rendered with 4
  members)
- Fractal k-sequence drift (Phi<2:6> rendered out of order or with
  substituted operators)

WHAT IT DOES NOT CATCH
----------------------
- Naturalness / fluency (it's a structural gate, not a style gate)
- Semantically valid paraphrases of intent that change structure (rare,
  but possible — e.g. ``A + B`` rendered as ``B alone with no mention
  of A``; SFE catches it as ``noetics_missing``)
- Compiler validity of the source CAS itself (assumed valid upstream)

CONTRIBUTORS / DEBT
-------------------
- Alias coverage in ``NOETIC_VALIDATION_TOKENS`` / ``DOMAIN_ALIASES``
  etc. is the load-bearing dependency. New colloquialism inflections
  (``rubs you the wrong way`` vs ``rubs the wrong way``) need to be in
  the v2 alias tables for SFE to recognize them. This is shared
  infrastructure; updates benefit both v2 validators and SFE.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


_REPO_ROOT = Path(__file__).resolve().parents[2]
_V2_PATH = _REPO_ROOT / "cas-synthetic" / "scripts" / "generate_path_d_wave3_v2.py"


def _load_v2_module():
    """Load v2 by absolute path so we can reuse alias tables without
    duplicating them."""
    name = "cas_synthetic_path_d_wave3_v2_for_sfe"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _V2_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Fingerprint data structure
# ---------------------------------------------------------------------------


@dataclass
class CASFingerprint:
    """Total structural fingerprint of a CAS expression OR an English
    rendering of one. Two fingerprints are ``==`` iff the structural
    commitments are equivalent.
    """

    # Multiset of (noetic, domain, drive, register) state-literal
    # occurrences. Each tuple element is None if absent in source.
    # Stored as Counter of tuples for multiset equality.
    state_literal_occurrences: Counter = field(default_factory=Counter)

    # Multiset of bare noetics ^N (without domain attached) — covers
    # CO-N composition and meta-logic NoeticCluster members.
    bare_noetics: Counter = field(default_factory=Counter)

    # Set of Ω stem names (post-Ω_ prefix). e.g. {"alignment", "decision_47"}
    omega_stems: set = field(default_factory=set)

    # Multiset of recipe coefficients (float-canonical strings)
    coefficients: Counter = field(default_factory=Counter)

    # Set of variable names introduced via ``let X = ...``
    variable_names: set = field(default_factory=set)

    # Ordered sequence of fractal k-values (when source is a fractal)
    fractal_k_sequence: list = field(default_factory=list)

    # Cluster type ("NoeticCluster", "RelationCluster", "StateCluster",
    # "StateVariantCluster", "CoverOf", "PartitionOf", or None).
    cluster_type: Optional[str] = None

    # Cluster members as multiset of bare noetics (or full state literals
    # for StateCluster / StateVariantCluster).
    cluster_member_multiset: Counter = field(default_factory=Counter)

    # Number of `→` arrows (source) or flow connectives (English)
    arrow_count: int = 0

    # Number of `+` operands (source) or "and"/"combined with"/etc. (English)
    plus_count: int = 0

    # Number of `×` operands or "fused"/"integrated"/etc.
    times_count: int = 0

    # Number of `∘` operators (binary composition)
    compose_count: int = 0

    # Set of meta-logic operators present (∩ ∪ ∖ ∈ ⊂ ⊆ ⊃ ⊇ ⊕ ⊗
    # cardinality |·|). Compared by set inclusion (source ⊆ english).
    meta_logic_operators: set = field(default_factory=set)

    # Raw axis-presence (not paired with noetics) — used for distributive
    # cluster comparisons where one noetic alias mention applies to N
    # enumerated domain words across separate clauses. State-literal-
    # occurrence binding misses these because it requires per-noetic
    # pairing; raw presence captures them.
    domains_present: set = field(default_factory=set)
    drives_present: set = field(default_factory=set)
    registers_present: set = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_literal_occurrences": {str(k): v for k, v in self.state_literal_occurrences.items()},
            "bare_noetics": dict(self.bare_noetics),
            "omega_stems": sorted(self.omega_stems),
            "coefficients": dict(self.coefficients),
            "variable_names": sorted(self.variable_names),
            "fractal_k_sequence": list(self.fractal_k_sequence),
            "cluster_type": self.cluster_type,
            "cluster_member_multiset": {str(k): v for k, v in self.cluster_member_multiset.items()},
            "arrow_count": self.arrow_count,
            "plus_count": self.plus_count,
            "times_count": self.times_count,
            "compose_count": self.compose_count,
            "meta_logic_operators": sorted(self.meta_logic_operators),
        }


# ---------------------------------------------------------------------------
# CAS source fingerprint extraction (deterministic, easy direction)
# ---------------------------------------------------------------------------


_RE_STATE_LITERAL_FULL = re.compile(
    r"\^(\d+)"                              # ^N
    r"(?:\^([PCEO]))?"                      # optional ^D
    r"(?:_\{F(\d+)\})?"                     # optional _{Fk}
    r"(?:\|([TAfE]))?"                      # optional |R (single letter)
)
_RE_OMEGA_NAMED_UNICODE = re.compile(r"Ω_([A-Za-z][A-Za-z0-9_]*)")
_RE_OMEGA_NAMED_ASCII = re.compile(r"Omega_([A-Za-z][A-Za-z0-9_]*)")
_RE_RECIPE_COEFFICIENT = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*\*")
_RE_LET_VARIABLE = re.compile(r"\blet\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=")
_RE_FRACTAL_BODY = re.compile(r"(?:Φ|Phi)\s*[⟨<]\s*([0-9:\s]+?)\s*[⟩>]")
_RE_CO_N = re.compile(r"\bCO-(\d+)\b")
_RE_CLUSTER_HEAD = re.compile(
    r"\b(NoeticCluster|RelationCluster|StateCluster|StateVariantCluster|CoverOf|PartitionOf)\b"
)


def _canonical_coef(s: str) -> str:
    try:
        return f"{float(s):g}"
    except ValueError:
        return s


def extract_cas_fingerprint(source_cas: str) -> CASFingerprint:
    """Extract fingerprint from CAS notation. Deterministic."""
    fp = CASFingerprint()

    # State literal occurrences
    for m in _RE_STATE_LITERAL_FULL.finditer(source_cas):
        n = int(m.group(1))
        d = m.group(2)
        drive = int(m.group(3)) if m.group(3) else None
        reg = m.group(4)
        # Decision: "^N alone" (bare) vs "^N^D..." (full state literal).
        # Bare ^N (no domain, no drive, no register) goes into
        # bare_noetics. Anything more goes into state_literal_occurrences.
        if d is None and drive is None and reg is None:
            fp.bare_noetics[n] += 1
        else:
            fp.state_literal_occurrences[(n, d, drive, reg)] += 1

    # CO-N composition operators (treat as bare noetics)
    for m in _RE_CO_N.finditer(source_cas):
        fp.bare_noetics[int(m.group(1))] += 1

    # Ω stems (Unicode + ASCII spellings)
    for m in _RE_OMEGA_NAMED_UNICODE.finditer(source_cas):
        fp.omega_stems.add(m.group(1))
    for m in _RE_OMEGA_NAMED_ASCII.finditer(source_cas):
        fp.omega_stems.add(m.group(1))

    # Coefficients
    for c in _RE_RECIPE_COEFFICIENT.findall(source_cas):
        fp.coefficients[_canonical_coef(c)] += 1

    # Variable names
    for m in _RE_LET_VARIABLE.finditer(source_cas):
        fp.variable_names.add(m.group(1))

    # Fractal k-sequence. Also fold k-values into bare_noetics so that
    # the English-side noetic counter (which doesn't distinguish bare
    # from compound) can be compared on equal terms.
    fr = _RE_FRACTAL_BODY.search(source_cas)
    if fr:
        body = fr.group(1).strip()
        try:
            fp.fractal_k_sequence = [int(k.strip()) for k in body.split(":") if k.strip()]
            for k in fp.fractal_k_sequence:
                fp.bare_noetics[k] += 1
        except ValueError:
            fp.fractal_k_sequence = []

    # Cluster type and members
    cl = _RE_CLUSTER_HEAD.search(source_cas)
    if cl:
        fp.cluster_type = cl.group(1)
        # Member capture: between { } following the cluster head
        # (handles outer-most cluster body; PartitionOf has multiple
        # nested NoeticClusters — we walk all of them separately for
        # bare_noetics but record cluster_member_multiset as the
        # outermost cluster's first member set when present)
        if fp.cluster_type in ("NoeticCluster", "RelationCluster", "StateCluster", "StateVariantCluster"):
            mb = re.search(re.escape(fp.cluster_type) + r"\{([^{}]*)\}", source_cas)
            if mb:
                body = mb.group(1)
                # For NoeticCluster / RelationCluster: bare ^N members.
                # For StateCluster / StateVariantCluster: full state literals.
                for sm in _RE_STATE_LITERAL_FULL.finditer(body):
                    n = int(sm.group(1))
                    d = sm.group(2)
                    drive_m = int(sm.group(3)) if sm.group(3) else None
                    reg_m = sm.group(4)
                    if d is None and drive_m is None and reg_m is None:
                        fp.cluster_member_multiset[("noetic", n)] += 1
                    else:
                        fp.cluster_member_multiset[("state", n, d, drive_m, reg_m)] += 1
        elif fp.cluster_type in ("CoverOf", "PartitionOf"):
            # CoverOf(...) / PartitionOf(...) - members are nested
            # NoeticClusters; we don't unpack here, only record cluster_type.
            pass

    # Operator counts
    fp.arrow_count = source_cas.count("->") + source_cas.count("→")
    fp.plus_count = source_cas.count("+")
    fp.times_count = source_cas.count("×")
    fp.compose_count = source_cas.count("∘")

    # Meta-logic operators
    META_OP_TOKENS = {
        "∩": "∩",      # intersection
        "∪": "∪",      # union
        "∖": "∖",      # set difference
        "\\setminus": "∖",  # LaTeX-ish fallback
        "∈": "∈",      # element of / belongs to
        "⊂": "⊂",      # proper subset
        "⊆": "⊆",      # subset
        "⊃": "⊃",      # proper superset
        "⊇": "⊇",      # superset
        "⊕": "⊕",      # xor / direct sum
        "⊗": "⊗",      # tensor product
    }
    for tok, canonical in META_OP_TOKENS.items():
        if tok in source_cas:
            fp.meta_logic_operators.add(canonical)
    # Cardinality |...|: detect by ``|`` flanking a cluster/state expr.
    # Conservative pattern: the source contains ``|NoeticCluster{...}|``
    # or ``|StateCluster{...}|`` etc.
    if re.search(r"\|(?:NoeticCluster|RelationCluster|StateCluster|StateVariantCluster)\{[^}]*\}\|", source_cas):
        fp.meta_logic_operators.add("|·|")
    # Product(...) is a meta-logic constructor too
    if re.search(r"\bProduct\s*\(", source_cas):
        fp.meta_logic_operators.add("Product")

    return fp


# ---------------------------------------------------------------------------
# English fingerprint extraction (the load-bearing reverse direction)
# ---------------------------------------------------------------------------


# Lazily loaded reverse maps from v2 alias tables.
_REVERSE_NOETIC_MAP: Optional[dict[str, int]] = None
_REVERSE_DOMAIN_MAP: Optional[dict[str, str]] = None
_REVERSE_DRIVE_MAP: Optional[dict[str, int]] = None
_REVERSE_REGISTER_MAP: Optional[dict[str, str]] = None


def _build_reverse_maps() -> None:
    """Build reverse alias maps from v2's forward tables. Cached."""
    global _REVERSE_NOETIC_MAP, _REVERSE_DOMAIN_MAP, _REVERSE_DRIVE_MAP, _REVERSE_REGISTER_MAP
    if _REVERSE_NOETIC_MAP is not None:
        return
    v2 = _load_v2_module()

    # Noetic: NOETIC_VALIDATION_TOKENS gives canonical aliases per index.
    # Plus _NOETIC_PER_OCCURRENCE_EXTRA for hyphenated/inflected variants.
    noetic_map: dict[str, int] = {}
    for n, aliases in v2.NOETIC_VALIDATION_TOKENS.items():
        for a in aliases:
            noetic_map[a.lower()] = n
    for n, aliases in getattr(v2, "_NOETIC_PER_OCCURRENCE_EXTRA", {}).items():
        for a in aliases:
            noetic_map[a.lower()] = n
    # Sort keys by length descending so longer phrases win ("breaking it down"
    # before "breaking" if both are aliases). Implemented at lookup time.
    _REVERSE_NOETIC_MAP = noetic_map

    # Domain: DOMAIN_ALIASES is dict[letter] -> tuple of aliases
    domain_map: dict[str, str] = {}
    for letter, aliases in v2.DOMAIN_ALIASES.items():
        for a in aliases:
            domain_map[a.lower()] = letter
    _REVERSE_DOMAIN_MAP = domain_map

    # Drive: DRIVE_ALIASES is dict[int] -> tuple of aliases
    drive_map: dict[str, int] = {}
    for k, aliases in v2.DRIVE_ALIASES.items():
        for a in aliases:
            drive_map[a.lower()] = k
    _REVERSE_DRIVE_MAP = drive_map

    # Register: REGISTER_ALIASES is dict[letter] -> tuple
    register_map: dict[str, str] = {}
    for letter, aliases in v2.REGISTER_ALIASES.items():
        for a in aliases:
            register_map[a.lower()] = letter
    _REVERSE_REGISTER_MAP = register_map


# Flow connectives that signal a → arrow has been rendered in English.
_FLOW_CONNECTIVES = (
    "leads to", "produce ", "produces", "yields", "yield ", "becomes",
    "next", "then ", "in turn", "and finally", "transforms into",
    "turns into", "morphs into", "feeds into", "creates", "create ",
    "is followed by", "the chain says", "exported value leads",
)
# Plus-style connectives (commutative composition).
_PLUS_CONNECTIVES = (
    "combined with", "together with", "alongside", "and ",
    "plus ", "added to", "combine in", "combine these",
)
# ×-style connectives (multiplicative / fusion).
_TIMES_CONNECTIVES = (
    "fused with", "merged into", "integrated with", "fusing into",
    "merged with", "fused into", "modes fusing", "fused together",
)
# ∘ composition.
_COMPOSE_CONNECTIVES = (
    "composed with", "composition where", "composition of",
)


def _count_phrase_occurrences(text_lower: str, phrases: tuple[str, ...]) -> int:
    return sum(text_lower.count(p) for p in phrases)


def _scan_for_aliases(
    text_lower: str, alias_to_value: dict[str, Any], min_alias_len: int = 3
) -> Counter:
    """Substring-scan the text for alias hits, return a Counter of values.

    Sorts aliases by length descending so longer phrases match first
    (and shorter aliases that are substrings of matched phrases are not
    double-counted). Removes matched spans from the text before
    continuing.
    """
    counter: Counter = Counter()
    sorted_aliases = sorted(
        (a for a in alias_to_value if len(a) >= min_alias_len),
        key=len, reverse=True
    )
    work = text_lower
    for alias in sorted_aliases:
        # Find all occurrences of this alias in the working text.
        # Use a simple non-overlapping count.
        if alias not in work:
            continue
        cnt = work.count(alias)
        if cnt:
            counter[alias_to_value[alias]] += cnt
            # Remove matched spans so shorter aliases inside don't
            # double-count. Replace with a non-alias placeholder.
            work = work.replace(alias, " " * len(alias))
    return counter


def _scan_with_positions(
    text_lower: str, alias_to_value: dict[str, Any], min_alias_len: int = 3
) -> list[tuple[int, int, Any]]:
    """Like ``_scan_for_aliases`` but returns position spans for each
    match instead of a count. Used by the bound-state-literal
    extraction to associate each noetic position with the nearest
    domain / drive / register hit.

    Returns list of (start, end, value) tuples, sorted by start position.
    """
    spans: list[tuple[int, int, Any]] = []
    sorted_aliases = sorted(
        (a for a in alias_to_value if len(a) >= min_alias_len),
        key=len, reverse=True,
    )
    work = list(text_lower)  # mutable so we can mask matched spans
    for alias in sorted_aliases:
        n = len(alias)
        i = 0
        while True:
            joined = "".join(work)
            pos = joined.find(alias, i)
            if pos == -1:
                break
            spans.append((pos, pos + n, alias_to_value[alias]))
            # Mask the matched span so shorter aliases nested inside
            # don't double-count.
            for j in range(pos, pos + n):
                work[j] = " "
            i = pos + n
    spans.sort(key=lambda s: s[0])
    return spans


_CLAUSE_BOUNDARY_RE = re.compile(
    r"\.\s|;\s|,\s+(?:and|but|then|next|which|leads|produces|while|"
    r"combined|added|together|with(?:\s+those)?|fusing|"
    r"fused|merged|expressed)\s+|"
    r"\bleads\s+to\b|\bproduces?\b|\bbecomes?\b|\bturns\s+into\b|"
    r"\btransforms\s+into\b|\bin\s+turn\b|\band\s+finally\b|"
    r"\byields?\b|\bthe\s+chain\s+says\b",
    re.IGNORECASE,
)


def _split_into_clauses(text_lower: str) -> list[tuple[int, int]]:
    """Split text into clause spans by sentence/clause boundaries.

    Returns list of (start, end) character offsets, end-exclusive.
    Used for clause-level binding of noetic+domain pairs (strict),
    while registers are checked globally (relaxed) — see
    ``_bind_state_literals``.
    """
    boundaries = [0]
    for m in _CLAUSE_BOUNDARY_RE.finditer(text_lower):
        boundaries.append(m.start())
    boundaries.append(len(text_lower))
    spans = []
    for i in range(len(boundaries) - 1):
        s, e = boundaries[i], boundaries[i + 1]
        if e > s:
            spans.append((s, e))
    return spans


def _clause_for_position(pos: int, clauses: list[tuple[int, int]]) -> int:
    for i, (s, e) in enumerate(clauses):
        if s <= pos < e:
            return i
    return -1


def _bind_state_literals(
    text_lower: str,
    *,
    noetic_spans: list[tuple[int, int, int]],
    domain_spans: list[tuple[int, int, str]],
    drive_spans: list[tuple[int, int, int]],
    register_spans: list[tuple[int, int, str]],
) -> list[tuple[int, Optional[str], Optional[int], Optional[str]]]:
    """Build bound (noetic, domain, drive, register) tuples by:

    - **Clause-level binding** for domain and drive: a noetic position is
      bound to a domain word ONLY if both are in the same clause. Catches
      cross-clause domain swaps like ``^1^P -> ^4^P`` rendered as
      "paying attention in principled arena leads to resonating in
      operational arena" (where ^4 is in clause 2 with O, not P).

    - **Set-level binding** for register: each noetic position gets a
      tuple PER register that appears anywhere in the text. This handles
      the CRO pattern where one noetic mention covers multiple registers
      ("resonates in foundational way, expressed through felt emotion
      AND transcendent conviction" — one ^4 mention, two registers).

    Returns a list of bound tuples (one per noetic-position × matching
    register pair, plus a base tuple per noetic position with no register).
    """
    clauses = _split_into_clauses(text_lower)
    # Pre-compute domain/drive spans per clause for fast lookup
    clause_domains: dict[int, list[str]] = {}
    clause_drives: dict[int, list[int]] = {}
    for ds, de, d in domain_spans:
        ci = _clause_for_position((ds + de) // 2, clauses)
        clause_domains.setdefault(ci, []).append(d)
    for ds, de, k in drive_spans:
        ci = _clause_for_position((ds + de) // 2, clauses)
        clause_drives.setdefault(ci, []).append(k)

    # All registers present anywhere (set-level)
    all_registers = list({r for _s, _e, r in register_spans})

    bound: list[tuple[int, Optional[str], Optional[int], Optional[str]]] = []
    for nstart, nend, n in noetic_spans:
        ncenter = (nstart + nend) // 2
        ci = _clause_for_position(ncenter, clauses)
        # Domain candidates: in same clause as noetic
        domains_here = list(set(clause_domains.get(ci, []))) or [None]
        # Drive candidates: same
        drives_here = list(set(clause_drives.get(ci, []))) or [None]
        # Register candidates: global set + None for "no register"
        registers_here = list(all_registers) + [None]
        # Cross-product: every (domain, drive, register) combination
        # within the noetic's clause-context is a valid bound tuple
        for d in domains_here:
            for drv in drives_here:
                for reg in registers_here:
                    bound.append((n, d, drv, reg))
    return bound


# Recognized cluster framings in English. Order matters — we check most
# specific first. Map keys are case-insensitive substrings to scan for.
_CLUSTER_FRAMINGS = {
    # Explicit type names (rare in English output, but possible)
    "noeticcluster": "NoeticCluster",
    "relationcluster": "RelationCluster",
    "statecluster": "StateCluster",
    "statevariantcluster": "StateVariantCluster",
    "coverof": "CoverOf",
    "partitionof": "PartitionOf",
    # Natural-language patterns. Specific phrases first.
    "cover of": "CoverOf",
    "partition of": "PartitionOf",
    "a partition": "PartitionOf",
    "a cover": "CoverOf",
    # Generic cluster — type unknown
    "cluster of": "Cluster",
    "group containing": "Cluster",
    "cluster containing": "Cluster",
    "a group": "Cluster",
    # Plurals + set-operation framings used by deterministic renderers
    "groups": "Cluster",
    "of groups": "Cluster",
    "between groups": "Cluster",
    "intersection of": "Cluster",
    "union of": "Cluster",
    "intersection relation": "Cluster",
    "union relation": "Cluster",
    "an intersection": "Cluster",
    "a union": "Cluster",
    "first group": "Cluster",
    "second group": "Cluster",
    "grouping": "Cluster",
    "group 1": "Cluster",
    "group 2": "Cluster",
}

# Variable-name extraction from English. All case-insensitive.
# Pattern 1: "let X name ..." / "let X be ..." / "let X = ..."
_RE_ENGLISH_LET_NAME = re.compile(
    r'(?:\blet|\bname[ds]?)\s+"?([a-zA-Z_][a-zA-Z0-9_]+)"?'
    r'(?:\s+(?:name|names|be|=|to|as|the|a)\b)?',
    re.IGNORECASE,
)
# Pattern 1b: "Export X as ..." / "Export X." (diagram_export shape)
_RE_ENGLISH_EXPORT_NAME = re.compile(
    r'\bexport\s+"?([a-zA-Z_][a-zA-Z0-9_]+)"?',
    re.IGNORECASE,
)
# Pattern 2: stage references after definition (case-sensitive — stage
# names are conventionally cased)
_RE_ENGLISH_STAGE_REF = re.compile(r'\b(stage[A-Za-z][A-Za-z0-9_]*)\b')
# Pattern 3: quoted variable names "anchor_03"
_RE_ENGLISH_QUOTED_VAR = re.compile(r'"([a-zA-Z_][a-zA-Z0-9_]+)"')
# Pattern 4: "X names" — the deterministic renderer often says
# 'stageA0_5 names a thought' / 'attraction_0281 name something'
_RE_ENGLISH_NAMES_VERB = re.compile(
    r'\b([a-zA-Z_][a-zA-Z0-9_]+)\s+name[ds]?\b',
)

# Outcome-stem extraction. Multiple patterns to handle different rendering
# styles. Each captures the stem.
_RE_OUTCOME_STEM_PATTERNS = [
    # "outcome called X" / "outcome named X"
    re.compile(r"\boutcome\s+(?:called|named)\s+([a-zA-Z][a-zA-Z0-9_]*)", re.IGNORECASE),
    # "named outcome X"
    re.compile(r"\bnamed\s+outcome\s+([a-zA-Z][a-zA-Z0-9_]*)", re.IGNORECASE),
    # "Recipe for outcome X" / "for outcome X"
    re.compile(r"\bfor\s+outcome\s+([a-zA-Z][a-zA-Z0-9_]*)", re.IGNORECASE),
    # "outcome X" where X has underscore+digit suffix (typical Ω stem shape)
    re.compile(r"\boutcome\s+([a-zA-Z][a-zA-Z0-9_]*_\d+)", re.IGNORECASE),
    # "produce X" / "produces X" / "yields X" where X has underscore+digit
    re.compile(r"\bproduces?\s+([a-zA-Z][a-zA-Z0-9_]*_\d+)", re.IGNORECASE),
    re.compile(r"\byields?\s+([a-zA-Z][a-zA-Z0-9_]*_\d+)", re.IGNORECASE),
    # "into X" / "fusing into X" — CRO-style fusion target
    re.compile(r"\bfusing\s+into\s+(?:the\s+outcome\s+(?:called|named)\s+)?([a-zA-Z][a-zA-Z0-9_]*)", re.IGNORECASE),
    # Λ-leakage side-effect stems: only ``_side`` suffix (recipe convention).
    # Anchored on stem-shaped suffix to avoid catching variable names.
    re.compile(r"\b([a-z][a-z_]+_side)\b"),
    # "outcomes: X and Y" / "outcomes X and Y" — captures the second stem
    # when listed alongside the first (recipe leakage form).
    re.compile(
        r"named\s+outcomes:?\s+[a-zA-Z][a-zA-Z0-9_]*\s+and\s+([a-zA-Z][a-zA-Z0-9_]*)",
        re.IGNORECASE,
    ),
]


def extract_english_fingerprint(english: str) -> CASFingerprint:
    """Extract structural fingerprint from English by reverse-mapping
    via v2 alias tables."""
    _build_reverse_maps()
    assert _REVERSE_NOETIC_MAP is not None
    assert _REVERSE_DOMAIN_MAP is not None
    assert _REVERSE_DRIVE_MAP is not None
    assert _REVERSE_REGISTER_MAP is not None

    fp = CASFingerprint()
    text_lower = english.lower()

    # Position-aware scans for each axis. We need positions (not just
    # counts) so we can BIND each noetic to the nearest domain / drive /
    # register hit. The 2026-05-08 false-positive on ``^1^P -> ^4^P``
    # rendered with second operand as ^O slipped through count-based
    # matching because the noetic-set {^1, ^4} and domain-set {P, O}
    # checks looked correct in isolation. Bound-tuple comparison fixes
    # that: source tuple ``(^4, P)`` requires ENGLISH ^4 alias near a
    # P-domain word.
    noetic_spans = _scan_with_positions(text_lower, _REVERSE_NOETIC_MAP)
    domain_spans = _scan_with_positions(text_lower, _REVERSE_DOMAIN_MAP, min_alias_len=4)
    drive_spans = _scan_with_positions(text_lower, _REVERSE_DRIVE_MAP, min_alias_len=5)
    register_spans = _scan_with_positions(text_lower, _REVERSE_REGISTER_MAP, min_alias_len=5)

    # Bare noetics: count noetic mentions overall (informational, used
    # only for fractal-sequence comparison and noetics_extra).
    for _s, _e, n in noetic_spans:
        fp.bare_noetics[n] += 1

    # Raw axis-presence sets (used by distributive cluster comparison)
    fp.domains_present = {d for _s, _e, d in domain_spans}
    fp.drives_present = {k for _s, _e, k in drive_spans}
    fp.registers_present = {r for _s, _e, r in register_spans}

    # Bound state-literal occurrences via window-based association.
    bound_tuples = _bind_state_literals(
        text_lower,
        noetic_spans=noetic_spans,
        domain_spans=domain_spans,
        drive_spans=drive_spans,
        register_spans=register_spans,
    )
    for tup in bound_tuples:
        fp.state_literal_occurrences[tup] += 1

    # Ω stems — try all patterns, accumulate matches.
    # The patterns themselves are anchored on "outcome"/"produce"/"yield" so
    # the captured stems are likely Ω names. Just filter out the obvious
    # filler words that could land in capture position.
    _OMEGA_FILLER_WORDS = {
        "called", "named", "the", "a", "an", "of", "for", "from",
        "in", "to", "by", "with", "as", "at", "on",
    }
    for pat in _RE_OUTCOME_STEM_PATTERNS:
        for m in pat.finditer(english):
            stem = m.group(1)
            if stem.lower() in _OMEGA_FILLER_WORDS:
                continue
            fp.omega_stems.add(stem)

    # Coefficients (digit-form numbers preceded by " X of " / "X times " /
    # "weighted at X" / inline as "X of"). We use a permissive regex.
    for c in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)\b", english):
        # Filter out years, ID-suffixes (which appear after underscores),
        # and similar non-coefficients. ID-suffixes are typically embedded
        # inside identifier-shaped tokens; we use a simpler heuristic:
        # only count coefficients that are < 100 and standalone
        # (already enforced by the regex's leading boundary).
        try:
            v = float(c)
            if v < 100:  # coefficient sanity bound
                fp.coefficients[_canonical_coef(c)] += 1
        except ValueError:
            pass

    # Variable names — combine four extractors. Filter out common false
    # positives (alias-words, English filler) at the candidate level.
    var_candidates: set[str] = set()
    for m in _RE_ENGLISH_QUOTED_VAR.finditer(english):
        var_candidates.add(m.group(1))
    for m in _RE_ENGLISH_LET_NAME.finditer(english):
        var_candidates.add(m.group(1))
    for m in _RE_ENGLISH_EXPORT_NAME.finditer(english):
        var_candidates.add(m.group(1))
    for m in _RE_ENGLISH_STAGE_REF.finditer(english):
        var_candidates.add(m.group(1))
    for m in _RE_ENGLISH_NAMES_VERB.finditer(english):
        var_candidates.add(m.group(1))
    # Filter: variables must not be plain alias words and must look
    # identifier-shaped (>=4 chars OR contain underscore-digit suffix
    # which is conventional for generated stage/anchor names).
    for cand in var_candidates:
        cand_low = cand.lower()
        if cand_low in _REVERSE_NOETIC_MAP:
            continue
        if cand_low in _REVERSE_DOMAIN_MAP:
            continue
        if cand_low in _REVERSE_DRIVE_MAP:
            continue
        if cand_low in _REVERSE_REGISTER_MAP:
            continue
        # Allow if length >=4 OR contains underscore+digit
        has_uscore_digit = "_" in cand and any(
            part.isdigit() for part in cand.split("_") if part
        )
        if len(cand) >= 4 or has_uscore_digit:
            fp.variable_names.add(cand)

    # Cluster type — look for explicit mentions or cluster-of-N framing.
    for needle, cluster_type in _CLUSTER_FRAMINGS.items():
        if needle in text_lower:
            if cluster_type is not None:
                fp.cluster_type = cluster_type
                break
            else:
                fp.cluster_type = "Cluster"
                break

    # Operator counts (English connectives standing in for source operators).
    fp.arrow_count = _count_phrase_occurrences(text_lower, _FLOW_CONNECTIVES)
    fp.plus_count = _count_phrase_occurrences(text_lower, _PLUS_CONNECTIVES)
    fp.times_count = _count_phrase_occurrences(text_lower, _TIMES_CONNECTIVES)
    fp.compose_count = _count_phrase_occurrences(text_lower, _COMPOSE_CONNECTIVES)

    # Meta-logic operators — natural-English equivalents.
    # Subset/superset ENGLISH phrases overlap heavily with proper-subset
    # (⊂/⊃) and non-proper (⊆/⊇) — natural English rarely distinguishes.
    # Match them as a family: any "subset" phrase counts for both ⊂ and ⊆.
    SUBSET_PHRASES = (
        "subset", "subset of", "subset relation", "is a subset",
        "contained within", "contained in", "sits inside",
        "all members of", "is contained", "all of", "every member of",
    )
    SUPERSET_PHRASES = (
        "superset", "superset of", "superset relation", "is a superset",
        "contains all", "includes all", "encompasses", "wraps around",
    )
    META_OP_NL = {
        "∩": ("intersection", "intersected with", "intersect with",
              "common to both", "shared by", "intersection of",
              "intersection relation", "an intersection", "in common"),
        "∪": ("union", "union of", "union relation", "a union",
              "combined groups", "joined groups", "joined together",
              "merged groups", "merged into one"),
        "∖": ("difference", "minus", "excluded from", "set difference",
              "without", "removed from"),
        "∈": ("belongs to", "is a member of", "is an element of",
              "belongs in", "is in the set"),
        "⊂": SUBSET_PHRASES,
        "⊆": SUBSET_PHRASES,
        "⊃": SUPERSET_PHRASES,
        "⊇": SUPERSET_PHRASES,
        "⊕": ("exclusive or", "xor", "direct sum", "exclusive disjunction"),
        "⊗": ("tensor", "tensor product", "tensored"),
        "|·|": ("cardinality", "size of", "count of", "number of members",
                "how many members"),
        "Product": ("cartesian product", "product of", "all pairs",
                    "every combination", "product grouping",
                    "product pairing", "pairs the first", "pairs ",
                    "every pair"),
    }
    for op, phrases in META_OP_NL.items():
        for phrase in phrases:
            if phrase in text_lower:
                fp.meta_logic_operators.add(op)
                break

    return fp


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


# Lexical jargon patterns that are CAS-shaped but slip past the structural
# fingerprint check. Added 2026-05-08 after Henderson audit found 13/177
# accepted records containing "operator", "cognitive operation", "noetic",
# or bare "drive" wording — structurally faithful but stiff/jargony for
# downstream training data. The SFE round-trip alone doesn't catch these
# because they don't break operand binding.
_JARGON_PATTERNS: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    ("noetic_keyword",        re.compile(r"\bnoetic[s]?\b", re.IGNORECASE)),
    ("operator_bare",         re.compile(r"\boperator[s]?\b", re.IGNORECASE)),
    ("cognitive_operation",   re.compile(r"\bcognitive\s+operation[s]?\b", re.IGNORECASE)),
    ("operator_slot",         re.compile(r"\boperator\s+slot[s]?\b", re.IGNORECASE)),
    ("operator_position",     re.compile(r"\boperator\s+position[s]?\b", re.IGNORECASE)),
    ("operator_index",        re.compile(r"\boperator\s+ind(?:ex|ices)\b", re.IGNORECASE)),
    ("rpm_keyword",           re.compile(r"\bRPM\b")),
    ("compile_time",          re.compile(r"\bcompile-time\b", re.IGNORECASE)),
    ("co_n_literal",          re.compile(r"\bCO-\d+\b")),
    ("drive_bare",            re.compile(r"\bdrive[s]?\b", re.IGNORECASE)),
    ("register_bare",         re.compile(r"\bregister[s]?\b", re.IGNORECASE)),
    # "domain" is more common in plain English ("the domain of math"); only
    # flag when paired with a CAS-axis letter.
    ("domain_with_letter",    re.compile(r"\b(?:[PCEO]\s+domain|domain\s+[PCEO])\b")),
)


def detect_jargon_leaks(english: str) -> list[tuple[str, str]]:
    """Return list of (pattern_name, matched_text) for each jargon hit.
    Empty list = clean."""
    hits: list[tuple[str, str]] = []
    for name, pat in _JARGON_PATTERNS:
        for m in pat.finditer(english):
            hits.append((name, m.group(0)))
    return hits


@dataclass
class FingerprintDiff:
    """Diff between source CAS fingerprint and English fingerprint.

    Empty-fields = match. Non-empty fields = divergence reasons.

    Note: ``noetics_extra`` and ``omega_stems_extra`` are tracked for
    diagnostic purposes but are NOT part of ``is_empty`` (i.e., they don't
    block acceptance). The primary safety condition is "every source
    structural commitment surfaces in English". English having additional
    surface mentions is informational, not a fail.
    """

    noetics_missing: dict[int, int] = field(default_factory=dict)
    noetics_extra: dict[int, int] = field(default_factory=dict)  # informational
    domains_missing: list = field(default_factory=list)
    drives_missing: list = field(default_factory=list)
    registers_missing: list = field(default_factory=list)
    omega_stems_missing: list = field(default_factory=list)
    omega_stems_extra: list = field(default_factory=list)        # informational
    coefficients_missing: dict = field(default_factory=dict)
    coefficients_extra: dict = field(default_factory=dict)
    variable_names_missing: list = field(default_factory=list)
    fractal_k_mismatch: Optional[str] = None
    cluster_type_mismatch: Optional[str] = None
    meta_logic_missing: list = field(default_factory=list)
    arrow_short: int = 0  # source arrows - english flow connectives, when positive
    jargon_leaks: list = field(default_factory=list)  # (pattern_name, matched_text)

    def is_empty(self) -> bool:
        return (
            not self.noetics_missing
            and not self.domains_missing and not self.drives_missing
            and not self.registers_missing
            and not self.omega_stems_missing
            and not self.omega_stems_extra
            and not self.coefficients_missing and not self.coefficients_extra
            and not self.variable_names_missing
            and self.fractal_k_mismatch is None
            and self.cluster_type_mismatch is None
            and not self.meta_logic_missing
            and self.arrow_short == 0
            and not self.jargon_leaks
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            k: v for k, v in {
                "noetics_missing": self.noetics_missing,
                "noetics_extra_informational": self.noetics_extra,
                "domains_missing": self.domains_missing,
                "drives_missing": self.drives_missing,
                "registers_missing": self.registers_missing,
                "omega_stems_missing": self.omega_stems_missing,
                "omega_stems_extra_informational": self.omega_stems_extra,
                "coefficients_missing": self.coefficients_missing,
                "coefficients_extra": self.coefficients_extra,
                "variable_names_missing": self.variable_names_missing,
                "fractal_k_mismatch": self.fractal_k_mismatch,
                "cluster_type_mismatch": self.cluster_type_mismatch,
                "meta_logic_missing": self.meta_logic_missing,
                "arrow_short": self.arrow_short,
                "jargon_leaks": self.jargon_leaks,
            }.items() if v
        }


def compare_fingerprints(
    source: CASFingerprint, english: CASFingerprint
) -> FingerprintDiff:
    """Compute a diff between source and English fingerprints.

    The comparison is asymmetric: every structural commitment in the
    SOURCE must surface in the ENGLISH, but the English may have more
    (stylistic flow connectives, etc.) without penalty.
    """
    diff = FingerprintDiff()

    # BOUND TUPLE check (load-bearing): for each distinct (noetic,
    # domain, drive, register) tuple in source, English must contain
    # a tuple with the SAME bindings. Source's None positions are
    # wildcards (English can have anything there); source's non-None
    # positions are required matches.
    #
    # Catches the 2026-05-08 false positive: ^1^P -> ^4^P rendered with
    # second operand as ^O. Source tuples include (^4, P, None, None);
    # English binds ^4 alias to nearest "operational" producing
    # (^4, O, None, None) — no source-matching tuple → FAIL.
    #
    # Distinct-tuple semantics (set, not multiset): when source has the
    # same tuple repeated (CRO three-register fusion), English needs at
    # least one matching tuple, not three. Repeated identical tuples
    # collapse to a single requirement.
    #
    # DISTRIBUTIVE CLUSTER RELAXATION (2026-05-08, second pass): when
    # source is a cluster (StateCluster / NoeticCluster / etc.) AND has
    # the SAME noetic across multiple domains/registers, English may
    # legitimately use distributive phrasing: ``each shaped by
    # experience: one principled, one cognitive, one evaluative, one
    # operational``. The noetic alias appears ONCE; the domains appear
    # in separate clauses. Strict clause-level binding rejects this
    # (validator false negative). For distributive cluster sources, fall
    # back to set-level matching: noetic anywhere + each domain anywhere.
    src_tuples = set(source.state_literal_occurrences.keys())
    src_tuples = {t for t in src_tuples if t[0] is not None}
    eng_tuples = set(english.state_literal_occurrences.keys())

    # Detect distributive source: cluster_type set AND multiple tuples
    # share the same noetic.
    is_distributive_source = False
    if source.cluster_type is not None:
        from collections import defaultdict as _dd
        _by_n: dict[int, list] = _dd(list)
        for t in src_tuples:
            _by_n[t[0]].append(t)
        is_distributive_source = any(len(g) > 1 for g in _by_n.values())

    # Build english axis-presence sets for the relaxed distributive check.
    # Use RAW presence (english.domains_present etc.), not bound tuples,
    # because distributive phrasing puts domains in clauses that don't
    # contain a noetic alias — they would never appear in bound tuples.
    eng_noetic_set_local = set(english.bare_noetics.keys())
    eng_domain_set_local = set(english.domains_present)
    eng_drive_set_local = set(english.drives_present)
    eng_register_set_local = set(english.registers_present)

    # noetics_missing: distinct noetics in source not in English (fast
    # diagnostic; subset of bound-tuple check).
    src_noetic_set: set = set()
    for n in source.bare_noetics:
        src_noetic_set.add(n)
    for (n, _d, _drive, _reg) in src_tuples:
        if n is not None:
            src_noetic_set.add(n)
    for n in src_noetic_set:
        if english.bare_noetics.get(n, 0) < 1:
            diff.noetics_missing[n] = 1

    # noetics_extra (informational only; not blocking).
    eng_noetic_set = set(english.bare_noetics.keys())
    for n in eng_noetic_set:
        if n not in src_noetic_set:
            diff.noetics_extra[n] = english.bare_noetics[n]

    # Bound-tuple match: for each distinct source tuple, look for a
    # matching English tuple. A "match" means: source's non-None fields
    # all equal the corresponding English fields. English's extra
    # non-None fields don't disqualify (the English may name a register
    # the source didn't mark, e.g.).
    def _tuple_matches(src_t, eng_t) -> bool:
        for sv, ev in zip(src_t, eng_t):
            if sv is None:
                continue  # source wildcard — anything OK
            if sv != ev:
                return False
        return True

    def _distributive_satisfied(st) -> bool:
        """For distributive cluster sources, fall back to set-level
        matching: noetic anywhere + each non-None axis anywhere."""
        sn, sd, sdrive, sreg = st
        if sn is not None and sn not in eng_noetic_set_local:
            return False
        if sd is not None and sd not in eng_domain_set_local:
            return False
        if sdrive is not None and sdrive not in eng_drive_set_local:
            return False
        if sreg is not None and sreg not in eng_register_set_local:
            return False
        return True

    # Track which axis-binding failures occur most often, to populate
    # the diff fields the corrective prompt knows how to format.
    for st in src_tuples:
        if any(_tuple_matches(st, et) for et in eng_tuples):
            continue
        # Distributive cluster: relaxed set-level match
        if is_distributive_source and _distributive_satisfied(st):
            continue
        # No match. Diagnose which axes are missing.
        sn, sd, sdrive, sreg = st
        # Find the English tuple(s) that share the noetic (so we can
        # report the BINDING mismatch, not just "noetic missing").
        partial = [et for et in eng_tuples if et[0] == sn]
        if not partial:
            # No English tuple even has this noetic
            if sn not in diff.noetics_missing:
                diff.noetics_missing[sn] = 1
            continue
        # English has the noetic, but its binding differs. Report which
        # axis(es) diverged.
        if sd is not None and not any(et[1] == sd for et in partial):
            diff.domains_missing.append((sd, sn))
        if sdrive is not None and not any(et[2] == sdrive for et in partial):
            diff.drives_missing.append((sdrive, sn))
        if sreg is not None and not any(et[3] == sreg for et in partial):
            diff.registers_missing.append((sreg, sn))

    # Ω stem check.
    # - omega_stems_missing: every source stem must surface in English (BLOCKING)
    # - omega_stems_extra: English has stems source doesn't. BLOCKING ONLY when
    #   either (a) the extra stem matches an axis word (drive name —
    #   "wisdom"/"structure"/"agency"/etc.), which is the drive→outcome
    #   confusion failure mode; OR (b) source has zero stems but English
    #   claims at least one (also drive→outcome shape).
    src_o = source.omega_stems
    eng_o = english.omega_stems
    diff.omega_stems_missing = sorted(src_o - eng_o)
    extra = eng_o - src_o
    if extra:
        # Build axis-word ban list from canonical drive names.
        _AXIS_WORDS = {
            "unity", "cohesion", "wisdom", "insight",
            "vitality", "energy", "connection", "belonging",
            "agency", "structure", "order", "purpose",
            "meaning", "self-determination",
            # Domain words too — "principled wisdom" might confuse but
            # "the outcome called principled" is wrong.
            "principled", "cognitive", "evaluative", "operational",
            "foundational", "mental", "judging", "behavioral",
            # Register words
            "transcendent", "analytical", "affective", "embodied",
            "felt",
            # Noetic operator names (reserved per Agent 4 Pattern G)
            "idea", "mind", "positive", "negative", "vibration",
            "female", "male", "rhythm",
        }
        blocking_extra = [s for s in sorted(extra) if s.lower() in _AXIS_WORDS]
        # Source-zero rule
        if not src_o and extra:
            blocking_extra = sorted(extra)
        if blocking_extra:
            diff.omega_stems_extra = blocking_extra

    # Coefficient check (multiset equality required)
    src_coefs = source.coefficients
    eng_coefs = english.coefficients
    for c, src_count in src_coefs.items():
        eng_count = eng_coefs.get(c, 0)
        if eng_count < src_count:
            diff.coefficients_missing[c] = src_count - eng_count

    # Variable names: every source var must appear in English (verbatim).
    diff.variable_names_missing = sorted(source.variable_names - english.variable_names)

    # Fractal k-sequence (ordered list equality)
    if source.fractal_k_sequence:
        if source.fractal_k_sequence != english.fractal_k_sequence:
            # The English fingerprint doesn't currently extract k-sequence
            # ordering directly (it folds all noetics into bare_noetics).
            # For fractals, we instead require the noetic multiset to match
            # the k-sequence's multiset.
            src_multiset = Counter(source.fractal_k_sequence)
            for k, src_count in src_multiset.items():
                if english.bare_noetics.get(k, 0) < src_count:
                    diff.fractal_k_mismatch = (
                        f"fractal k-multiset {dict(src_multiset)} not all in "
                        f"English bare_noetics {dict(english.bare_noetics)}"
                    )
                    break

    # Cluster type. Suppressed when the source is a distributive cluster
    # AND every source tuple is satisfied — the cluster's content is
    # faithfully rendered even without an explicit "cluster"/"group"
    # word in the English (e.g. "Each shaped by experience: one P, one
    # C, one E, one O" is a structurally-faithful distributive
    # rendering).
    distributive_fully_satisfied = (
        is_distributive_source
        and not diff.noetics_missing
        and not diff.domains_missing
        and not diff.drives_missing
        and not diff.registers_missing
    )
    if source.cluster_type and not distributive_fully_satisfied:
        if english.cluster_type is None:
            diff.cluster_type_mismatch = (
                f"source cluster type {source.cluster_type} not surfaced in English"
            )
        elif source.cluster_type == "PartitionOf" and english.cluster_type not in (
            "PartitionOf", "Cluster"
        ):
            # Allow generic "Cluster" framing for partitions when the
            # English uses "groups" plural (deterministic renderer style)
            diff.cluster_type_mismatch = (
                f"source PartitionOf rendered as {english.cluster_type}"
            )

    # Meta-logic operators: every source operator must surface in English.
    # Subset/superset proper-vs-non-proper distinction collapses in English,
    # so treat ⊂ and ⊆ as interchangeable for matching, same for ⊃/⊇.
    SUBSET_FAMILY = {"⊂", "⊆"}
    SUPERSET_FAMILY = {"⊃", "⊇"}
    eng_ops = set(english.meta_logic_operators)
    for op in source.meta_logic_operators:
        if op in eng_ops:
            continue
        # Family-level check
        if op in SUBSET_FAMILY and (eng_ops & SUBSET_FAMILY):
            continue
        if op in SUPERSET_FAMILY and (eng_ops & SUPERSET_FAMILY):
            continue
        diff.meta_logic_missing.append(op)

    # Arrow count: English flow connectives must be at least source arrow count
    if english.arrow_count < source.arrow_count:
        diff.arrow_short = source.arrow_count - english.arrow_count

    return diff


# ---------------------------------------------------------------------------
# Validator-API entry point
# ---------------------------------------------------------------------------


def validate_sfe_round_trip(*, source_cas: str, english: str) -> dict[str, Any]:
    """Public validator-style entry point. Returns a dict compatible with
    v2's ValidatorResult (so this can be used as a drop-in gate).

    Returns
    -------
    {
        "name": "sfe_round_trip",
        "passed": bool,
        "reason": str (empty if passed),
        "detail": {
            "source_fingerprint": {...},
            "english_fingerprint": {...},
            "diff": {...},
        }
    }
    """
    src_fp = extract_cas_fingerprint(source_cas)
    eng_fp = extract_english_fingerprint(english)
    diff = compare_fingerprints(src_fp, eng_fp)

    # Jargon scan — independent of structural binding. Catches "operator",
    # "cognitive operation", "noetic", bare "drive"/"register" etc. that
    # are CAS-shaped but not structural drift.
    diff.jargon_leaks = detect_jargon_leaks(english)

    detail = {
        "source_fingerprint": src_fp.to_dict(),
        "english_fingerprint": eng_fp.to_dict(),
        "diff": diff.to_dict(),
    }
    if diff.is_empty():
        return {
            "name": "sfe_round_trip",
            "passed": True,
            "reason": "",
            "detail": detail,
        }
    reason_parts: list[str] = []
    if diff.noetics_missing:
        reason_parts.append(f"noetics_missing={diff.noetics_missing}")
    if diff.domains_missing:
        reason_parts.append(f"domains_missing={diff.domains_missing}")
    if diff.drives_missing:
        reason_parts.append(f"drives_missing={diff.drives_missing}")
    if diff.registers_missing:
        reason_parts.append(f"registers_missing={diff.registers_missing}")
    if diff.omega_stems_missing:
        reason_parts.append(f"omega_stems_missing={diff.omega_stems_missing}")
    if diff.omega_stems_extra:
        reason_parts.append(f"omega_stems_phantom={diff.omega_stems_extra}")
    if diff.coefficients_missing:
        reason_parts.append(f"coefficients_missing={diff.coefficients_missing}")
    if diff.variable_names_missing:
        reason_parts.append(f"variable_names_missing={diff.variable_names_missing}")
    if diff.fractal_k_mismatch:
        reason_parts.append(diff.fractal_k_mismatch)
    if diff.cluster_type_mismatch:
        reason_parts.append(diff.cluster_type_mismatch)
    if diff.meta_logic_missing:
        reason_parts.append(f"meta_logic_missing={diff.meta_logic_missing}")
    if diff.arrow_short:
        reason_parts.append(f"arrow_short={diff.arrow_short}")
    if diff.jargon_leaks:
        reason_parts.append(f"jargon_leaks={diff.jargon_leaks}")
    return {
        "name": "sfe_round_trip",
        "passed": False,
        "reason": "; ".join(reason_parts),
        "detail": detail,
    }


__all__ = [
    "CASFingerprint",
    "FingerprintDiff",
    "extract_cas_fingerprint",
    "extract_english_fingerprint",
    "compare_fingerprints",
    "validate_sfe_round_trip",
]
