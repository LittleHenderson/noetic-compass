"""Phase 1 — symbolic structural repair for rendered meta-logic relations.

Per user directive 2026-05-10 (post Phase 3 negative result on
prompt-enrichment): meta-logic first because it has the cleanest
structural anchor and the least ambiguity. PartitionOf, CoverOf,
Product, cluster count, and cluster membership are all explicit in
the source CAS — that makes it the closest analog to rpm_chain
Phase 1.

Phase 1 narrow scope (user-specified):
  - log + repair the relation type WORD only when wrong, because
    that's structurally certain (e.g., source ``CoverOf`` rendered
    as "partition" -> rewrite to "cover", preserving inflection).
  - log but DO NOT rewrite cluster members or cluster cardinality.
    Member-level drift gets a flag-only entry; the audit decides
    whether to promote semantic substitution next round.

Three-layer gating (mirrors rpm_repair):
  1. ``apply_meta_logic_repair`` flag in postprocess() (default
     True; flip off for raw-behavior comparison evals).
  2. ``routing.task_type == "cas_to_english"`` (invalid CAS skipped).
  3. ``parse_meta_logic`` returns None for non-meta-logic sources
     (state literals, rpm_chains, recipes, fractals, CRO all no-op
     via ``relation_parsed=False``).

Grammar parsed (CLAUDE.md §"22 Capability Pathways" + Tootra
diagram layer per project memory):
  - ``PartitionOf(<universe>, <cluster1>, <cluster2>, ...)``
  - ``CoverOf(<universe>, <cluster1>, <cluster2>, ...)``
  - ``Product(<cluster1>, <cluster2>)``
  - cluster syntax: ``NoeticCluster{^N1, ^N2, ...}``

Audit's known failures (commit b281202 + 702a910):
  - Record 16 (``PartitionOf`` with 3 clusters): relation correct,
    cluster content drift. Phase 1 will detect the cluster member
    mismatch but NOT rewrite — log only.
  - Record 18 (``CoverOf``): rendered as "partition" instead of
    "cover". Phase 1 WILL rewrite the relation word.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Source-side parsing
# ---------------------------------------------------------------------------

_NOETIC_CLUSTER_RX = re.compile(
    r"NoeticCluster\s*\{\s*([^}]*)\s*\}"
)
_NOETIC_OP_RX = re.compile(r"\^([0-9])")

_RELATION_NAMES = ("PartitionOf", "CoverOf", "Product")
_TAKES_UNIVERSE = {"PartitionOf", "CoverOf"}


@dataclass(frozen=True)
class NoeticCluster:
    """One ``NoeticCluster{^N1, ^N2, ...}`` literal."""
    noetics: tuple[int, ...]


@dataclass
class MetaLogicRelation:
    """Source-side symbolic structure of a meta-logic relation."""
    relation_type: str  # "PartitionOf" / "CoverOf" / "Product"
    universe: Optional[str]  # "Noetics" or similar; None for Product
    clusters: list[NoeticCluster]

    @property
    def cluster_count(self) -> int:
        return len(self.clusters)


def parse_meta_logic(source_cas: str) -> Optional[MetaLogicRelation]:
    """Extract relation type, universe (if any), and cluster members
    from source CAS. Returns ``None`` for non-meta-logic sources."""
    rel_match: Optional[tuple[str, int]] = None
    for name in _RELATION_NAMES:
        idx = source_cas.find(name + "(")
        if idx >= 0 and (rel_match is None or idx < rel_match[1]):
            rel_match = (name, idx)
    if rel_match is None:
        return None
    relation_type, start = rel_match

    # Walk forward from the opening paren and find the matching close
    # paren so we can carve out only this relation's argument list
    # (defensive against trailing text after the relation).
    open_paren = source_cas.find("(", start)
    if open_paren < 0:
        return None
    depth = 1
    cursor = open_paren + 1
    while cursor < len(source_cas) and depth > 0:
        ch = source_cas[cursor]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        cursor += 1
    if depth != 0:
        return None
    args_text = source_cas[open_paren + 1 : cursor - 1]

    # Universe (PartitionOf / CoverOf): first arg is a bare identifier
    # before the first NoeticCluster{. For Product we skip universe.
    universe: Optional[str] = None
    if relation_type in _TAKES_UNIVERSE:
        first_cluster_at = args_text.find("NoeticCluster")
        if first_cluster_at > 0:
            universe = args_text[:first_cluster_at].rstrip(", \t\n").strip()
        else:
            universe = args_text.strip()

    clusters: list[NoeticCluster] = []
    for cm in _NOETIC_CLUSTER_RX.finditer(args_text):
        body = cm.group(1)
        ops = tuple(int(m.group(1)) for m in _NOETIC_OP_RX.finditer(body))
        clusters.append(NoeticCluster(noetics=ops))

    if not clusters:
        return None
    return MetaLogicRelation(
        relation_type=relation_type,
        universe=universe,
        clusters=clusters,
    )


# ---------------------------------------------------------------------------
# Repair log + dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MetaLogicRepair:
    """One repair operation applied to the rendered text. Phase 1
    only emits ``relation_type`` repairs; cluster-level repairs are
    deferred to a future phase."""
    kind: str  # "relation_type"
    source_relation: str
    found_word: str
    new_word: str


@dataclass
class ClusterMemberDrift:
    """Flag-only cluster-membership mismatch between source and
    rendered text. Phase 1 logs this but does NOT rewrite — the
    audit decides whether to promote semantic substitution next.
    """
    cluster_index: int
    expected_noetics: tuple[int, ...]
    expected_count: int
    notes: list[str] = field(default_factory=list)


@dataclass
class MetaLogicRepairLog:
    """Audit-friendly summary of one meta-logic repair pass."""
    relation_parsed: bool = False
    expected_relation: Optional[str] = None
    found_relation_pre_repair: Optional[str] = None
    found_relation_post_repair: Optional[str] = None
    relation_matched_pre_repair: bool = False
    relation_matched_post_repair: bool = False
    expected_cluster_count: int = 0
    found_cluster_word_count: int = 0
    cluster_count_matches: bool = False
    repairs: list[MetaLogicRepair] = field(default_factory=list)
    member_drifts: list[ClusterMemberDrift] = field(default_factory=list)

    @property
    def n_repairs(self) -> int:
        return len(self.repairs)

    def to_dict(self) -> dict[str, object]:
        return {
            "relation_parsed": self.relation_parsed,
            "expected_relation": self.expected_relation,
            "found_relation_pre_repair": self.found_relation_pre_repair,
            "found_relation_post_repair": self.found_relation_post_repair,
            "relation_matched_pre_repair": self.relation_matched_pre_repair,
            "relation_matched_post_repair": self.relation_matched_post_repair,
            "expected_cluster_count": self.expected_cluster_count,
            "found_cluster_word_count": self.found_cluster_word_count,
            "cluster_count_matches": self.cluster_count_matches,
            "n_repairs": self.n_repairs,
            "repairs": [
                {
                    "kind": r.kind,
                    "source_relation": r.source_relation,
                    "found_word": r.found_word,
                    "new_word": r.new_word,
                }
                for r in self.repairs
            ],
            "n_member_drifts": len(self.member_drifts),
            "member_drifts": [
                {
                    "cluster_index": d.cluster_index,
                    "expected_noetics": list(d.expected_noetics),
                    "expected_count": d.expected_count,
                    "notes": list(d.notes),
                }
                for d in self.member_drifts
            ],
        }


# ---------------------------------------------------------------------------
# Relation-word detection + repair
# ---------------------------------------------------------------------------

# Each relation has a regex that matches its English root + optional
# inflection suffix. We capture the suffix so we can preserve plural/
# verb forms when swapping the root (partitions -> covers, partitioning
# -> covering, partitioned -> covered).
_RELATION_PATTERNS: dict[str, re.Pattern] = {
    "PartitionOf": re.compile(r"\b(partition)(s|ed|ing|)\b", re.IGNORECASE),
    "CoverOf":     re.compile(r"\b(cover)(s|ed|ing|)\b",     re.IGNORECASE),
    "Product":     re.compile(r"\b(product)(s|)\b",          re.IGNORECASE),
}

_RELATION_ROOT: dict[str, str] = {
    "PartitionOf": "partition",
    "CoverOf":     "cover",
    "Product":     "product",
}


# Idiom-pattern rewrites for cross-relation phrase swaps. When the
# rendered text uses a verb-into-group idiom from the WRONG relation
# (e.g., "X partition into Y groups" where source says CoverOf), we
# rewrite the whole idiom rather than just swapping the root word
# (the bare swap "partition" -> "cover" produced grammatically rough
# output like "thinking cover into two groups" — the audit on commit
# d5e0864 flagged this and asked for "are covered by" passive voice).
#
# Patterns are tried IN ORDER; the first matching pattern is applied
# and supersedes the bare word swap. When no idiom pattern matches,
# the bare swap (preserving suffix + case) is used as the fallback.
_IDIOM_REWRITES: dict[tuple[str, str], list[tuple[re.Pattern, str]]] = {
    ("PartitionOf", "CoverOf"): [
        # "X partitions into N groups" -> "X is covered by N groups"
        # (3rd-person singular subject)
        (
            re.compile(
                r"\bpartitions\s+into\s+(\w+\s+(?:groups?|clusters?|sets?))\b",
                re.IGNORECASE,
            ),
            r"is covered by \1",
        ),
        # "X partitioned into N groups" -> "X covered by N groups"
        (
            re.compile(
                r"\bpartitioned\s+into\s+(\w+\s+(?:groups?|clusters?|sets?))\b",
                re.IGNORECASE,
            ),
            r"covered by \1",
        ),
        # "X partition into N groups" -> "X are covered by N groups"
        # (collective/plural subject — matches the audit's record-18
        # case where "ten ways of thinking partition into two groups"
        # should become "are covered by two groups")
        (
            re.compile(
                r"\bpartition\s+into\s+(\w+\s+(?:groups?|clusters?|sets?))\b",
                re.IGNORECASE,
            ),
            r"are covered by \1",
        ),
        # "by partitioning" -> "by covering"
        (
            re.compile(r"\bby\s+partitioning\b", re.IGNORECASE),
            "by covering",
        ),
    ],
    ("CoverOf", "PartitionOf"): [
        # "X are covered by N groups" -> "X partition into N groups"
        (
            re.compile(
                r"\bare\s+covered\s+by\s+(\w+\s+(?:groups?|clusters?|sets?))\b",
                re.IGNORECASE,
            ),
            r"partition into \1",
        ),
        # "X is covered by N groups" -> "X partitions into N groups"
        (
            re.compile(
                r"\bis\s+covered\s+by\s+(\w+\s+(?:groups?|clusters?|sets?))\b",
                re.IGNORECASE,
            ),
            r"partitions into \1",
        ),
        # "by covering" -> "by partitioning"
        (
            re.compile(r"\bby\s+covering\b", re.IGNORECASE),
            "by partitioning",
        ),
    ],
    # Product idioms are less common as drift targets in the audit;
    # fall back to bare-word swap for Product mismatches until we have
    # evidence a phrase-level rewrite would help.
}


def _find_first_relation_word(text: str) -> Optional[tuple[str, re.Match]]:
    """Return (relation_type, match) for the earliest relation word
    found in ``text``, or None if no relation word is present."""
    earliest: Optional[tuple[str, re.Match]] = None
    for rel_type, pat in _RELATION_PATTERNS.items():
        m = pat.search(text)
        if m is None:
            continue
        if earliest is None or m.start() < earliest[1].start():
            earliest = (rel_type, m)
    return earliest


def _try_idiom_rewrite(
    text: str, found_relation: str, expected_relation: str,
) -> Optional[tuple[str, str, str]]:
    """Try to apply an idiom-level rewrite for the (found, expected)
    relation pair. Returns ``(new_text, found_phrase, new_phrase)``
    when a pattern matched; ``None`` when no idiom matched and the
    caller should fall back to the bare word swap.

    Patterns are tried in declaration order; the first match wins.
    Only the first occurrence of the matched pattern is rewritten
    (count=1) so we don't accidentally over-edit a long passage.
    """
    key = (found_relation, expected_relation)
    patterns = _IDIOM_REWRITES.get(key)
    if not patterns:
        return None
    for pat, replacement in patterns:
        m = pat.search(text)
        if m is None:
            continue
        new_text = pat.sub(replacement, text, count=1)
        # Compute the actual replacement string for logging. ``pat.sub``
        # returns the substituted text, but the substitution we want
        # to log is the post-expansion form of ``replacement`` for
        # this match.
        new_phrase = m.expand(replacement) if "\\" in replacement else replacement
        return new_text, m.group(0), new_phrase
    return None


def _swap_relation_root(
    found_match: re.Match, expected_relation: str,
) -> str:
    """Swap the root of a relation word match for the expected
    relation's root, preserving the original suffix and case.
    Product has no -ing/-ed inflection, so when swapping IN to
    Product from a verb form, suffix collapses to '' or 's'."""
    found_root = found_match.group(1)
    found_suffix = found_match.group(2) or ""
    target_root = _RELATION_ROOT[expected_relation]
    target_suffix = found_suffix
    # Product can't take -ing or -ed; coerce those to "" so we don't
    # emit "producting" / "producted".
    if expected_relation == "Product":
        if target_suffix in ("ing", "ed"):
            target_suffix = ""
    # Preserve case of the first character.
    if found_root[0].isupper():
        target_root = target_root.capitalize()
    return target_root + target_suffix


# ---------------------------------------------------------------------------
# Cluster-side verification (flag-only in Phase 1)
# ---------------------------------------------------------------------------

# Indicators for "this rendered text describes some number of groups."
# Numerals + group-noun patterns. We count occurrences as a rough
# cardinality signal — Phase 1 does NOT rewrite cardinality.
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_GROUP_NOUNS = ("group", "groups", "cluster", "clusters", "set", "sets")
_GROUP_COUNT_RX = re.compile(
    r"\b(" + "|".join(_NUMBER_WORDS.keys()) + r"|\d+)\s+("
    + "|".join(_GROUP_NOUNS) + r")\b",
    re.IGNORECASE,
)


def _detect_cluster_word_count(text: str) -> int:
    """Best-effort estimate of how many groups/clusters the rendered
    text claims. Returns 0 when no countable phrase is found.

    Phase 1 only LOGS this; downstream audits compare to source
    cluster_count to surface cardinality drift."""
    m = _GROUP_COUNT_RX.search(text)
    if m is None:
        return 0
    word = m.group(1).lower()
    if word.isdigit():
        return int(word)
    return _NUMBER_WORDS.get(word, 0)


# Canonical Noetic colloquialisms (mirrors rpm_repair Phase 2 map but
# scoped to identification, not enforcement). Used for member-drift
# detection: Phase 1 checks whether each source-cluster Noetic has at
# least one indicator anywhere in the rendered text. Missing indicators
# are FLAGGED, not rewritten.
_NOETIC_INDICATORS: dict[int, tuple[str, ...]] = {
    0: ("foundational thought", "an idea", "a thought", "in your head"),
    1: ("paying attention", "make up your mind", "cognitive attention"),
    2: ("drawn to", "speaks to", "attracted toward"),
    3: ("rubs the wrong way", "averse to", "repelled"),
    4: ("struck a chord", "made an impression", "resonated"),
    5: ("who one is", "who you are", "shaped by experiences"),
    6: ("breaking it down", "unpacking", "pulling apart"),
    7: ("muscle memory", "practice makes perfect", "practiced rhythm"),
    8: ("that reminds", "one thing leads", "triggered a memory"),
    9: ("popped into mind", "just clicked", "popped"),
}


def _check_cluster_members(
    rendered_lower: str, cluster: NoeticCluster, cluster_index: int,
) -> Optional[ClusterMemberDrift]:
    """Return a drift entry when the rendered text is missing any of
    the source cluster's Noetic indicators. ``None`` when every
    expected Noetic has at least one indicator in rendered_lower."""
    missing: list[int] = []
    for n in cluster.noetics:
        indicators = _NOETIC_INDICATORS.get(n, ())
        if not any(ind in rendered_lower for ind in indicators):
            missing.append(n)
    if not missing:
        return None
    notes = [
        f"^{n} indicator missing from rendered text" for n in missing
    ]
    return ClusterMemberDrift(
        cluster_index=cluster_index,
        expected_noetics=cluster.noetics,
        expected_count=len(cluster.noetics),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def repair_meta_logic_rendering(
    *,
    source_cas: str,
    rendered: str,
    relation: Optional[MetaLogicRelation] = None,
) -> tuple[str, MetaLogicRepairLog]:
    """Run Phase 1 meta-logic repair on ``rendered``.

    Returns ``(repaired_text, log)``. When ``relation`` is None we
    parse it from ``source_cas``; pass through to skip re-parsing.
    No-op contract: when the source isn't a meta-logic relation
    (parse_meta_logic returns None) or the rendered text is empty,
    return ``(rendered, log)`` with ``relation_parsed=False`` and
    no repairs.
    """
    log = MetaLogicRepairLog()
    if relation is None:
        relation = parse_meta_logic(source_cas)
    if relation is None or not rendered:
        return rendered, log

    log.relation_parsed = True
    log.expected_relation = relation.relation_type
    log.expected_cluster_count = relation.cluster_count

    # ---- Pre-repair detection ----
    found_pre = _find_first_relation_word(rendered)
    if found_pre is not None:
        log.found_relation_pre_repair = found_pre[0]
        log.relation_matched_pre_repair = (
            found_pre[0] == relation.relation_type
        )
    else:
        log.found_relation_pre_repair = None
        log.relation_matched_pre_repair = False

    # ---- Phase 1 repair: relation-type word/phrase ----
    # Two-stage repair: first try an idiom-pattern rewrite for the
    # (found, expected) relation pair (e.g., "X partition into N
    # groups" -> "X are covered by N groups" for CoverOf source).
    # If no idiom pattern matches, fall back to the bare suffix-
    # preserving word swap (e.g., partitions -> covers).
    text = rendered
    if found_pre is not None and found_pre[0] != relation.relation_type:
        rel_type_found, m = found_pre
        idiom = _try_idiom_rewrite(text, rel_type_found, relation.relation_type)
        if idiom is not None:
            new_text, found_phrase, new_phrase = idiom
            log.repairs.append(MetaLogicRepair(
                kind="relation_phrase",
                source_relation=relation.relation_type,
                found_word=found_phrase,
                new_word=new_phrase,
            ))
            text = new_text
        else:
            new_word = _swap_relation_root(m, relation.relation_type)
            log.repairs.append(MetaLogicRepair(
                kind="relation_type",
                source_relation=relation.relation_type,
                found_word=m.group(0),
                new_word=new_word,
            ))
            text = text[: m.start()] + new_word + text[m.end():]

    # ---- Post-repair detection ----
    found_post = _find_first_relation_word(text)
    if found_post is not None:
        log.found_relation_post_repair = found_post[0]
        log.relation_matched_post_repair = (
            found_post[0] == relation.relation_type
        )

    # ---- Cluster cardinality (flag only) ----
    log.found_cluster_word_count = _detect_cluster_word_count(text)
    log.cluster_count_matches = (
        log.found_cluster_word_count == relation.cluster_count
    )

    # ---- Cluster membership (flag only) ----
    rendered_lower = text.lower()
    for i, cluster in enumerate(relation.clusters):
        drift = _check_cluster_members(rendered_lower, cluster, i)
        if drift is not None:
            log.member_drifts.append(drift)

    return text, log


__all__ = [
    "ClusterMemberDrift",
    "MetaLogicRelation",
    "MetaLogicRepair",
    "MetaLogicRepairLog",
    "NoeticCluster",
    "parse_meta_logic",
    "repair_meta_logic_rendering",
]
