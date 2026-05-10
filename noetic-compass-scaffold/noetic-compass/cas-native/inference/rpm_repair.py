"""Phase 1 — symbolic structural repair for rendered rpm_chain text.

The v1c+RPM-seed audit (commit b281202) confirmed the decoder seed
fixes the rpm_chain wrong-task collapse (3/3 hijack -> 0/3) but
content drift survives inside the now-correct silhouette. This module
is the **deterministic symbolic** repair pass that lands BEFORE any
semantic-level intervention. Per user directive 2026-05-10:

  - Phase 1 (this module): repair only what is symbolically certain.
    Stage identifiers, malformed/truncated stage suffixes, missing
    ``stage`` prefix, and the final edge are rewritten back to source.
    Semantic drift (Noetic colloquialism, Drive label, Domain word,
    Register) is LOGGED but NOT rewritten — Phase 2 territory.
  - Phase 2 (later): per-stage colloquialism check. Decided based on
    whether Phase 1 alone moves the human-grading needle.
  - Phase 3 (last resort): retry-with-stronger-prompt when Phase 1
    finds drift it can't repair.

Phase 1 is gated to the same shape the seed gates on: the source
CAS must contain at least one ``let <var> = <expr>;`` line. Non-RPM
shapes (state literals, recipes, fractals, meta-logic, CRO) cause
:func:`parse_rpm_chain` to return ``None`` and the repair becomes
a no-op pass-through — same gating discipline as
:mod:`cas_native.inference.identifier_repair`.

Contract mirrors :mod:`identifier_repair`:
  - input ``raw_gen`` is preserved verbatim on the result
  - ``final_text`` reflects the repaired output
  - ``rpm_repair_log`` records every substitution + every flagged
    semantic drift so the audit JSONL can see exactly what changed

User-recommended audit pattern: same as Ω repair / coefficient repair
— "fix the surface, but preserve the trace."
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Source-side parsing
# ---------------------------------------------------------------------------

# Match `let <var> = <expr>;` — captures the var name and the expression
# content up to the next semicolon. Multiline-tolerant.
_LET_BINDING_RX = re.compile(
    r"\blet\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+?)(?:;|$)",
    re.MULTILINE,
)

# Match the final edge `<head> -> <tail>` (or `→`) — captures the two
# stage names. The edge typically appears AFTER all let bindings, so
# we'll search for it AFTER stripping the let-bindings out.
_EDGE_RX = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:->|→)\s*([A-Za-z_][A-Za-z0-9_]*)\b",
)


@dataclass(frozen=True)
class StageBinding:
    """One ``let <var> = <expr>;`` clause from source CAS."""
    var: str
    expr: str


@dataclass(frozen=True)
class FinalEdge:
    """The closing ``<head> -> <tail>`` edge."""
    head: str
    tail: str


@dataclass
class RpmChain:
    """Source-side symbolic structure of an rpm_chain expression.

    ``stages`` preserves source order (first ``let`` first). ``edge``
    is the closing transition; ``None`` when source has only let
    bindings without a trailing edge (still a valid let-binding shape
    for Phase 1 purposes — we just have nothing to verify the edge
    against).
    """
    stages: list[StageBinding]
    edge: Optional[FinalEdge]

    @property
    def stage_vars(self) -> list[str]:
        return [s.var for s in self.stages]


def parse_rpm_chain(source_cas: str) -> Optional[RpmChain]:
    """Extract the let-binding chain + final edge from source CAS.

    Returns ``None`` when the source contains no ``let`` bindings,
    which is the structural gate Phase 1 uses to no-op on non-RPM
    shapes. State literals, recipes, fractals, meta-logic, CRO all
    return ``None`` here.
    """
    bindings = _LET_BINDING_RX.findall(source_cas)
    if not bindings:
        return None
    stages = [StageBinding(var=v, expr=e.strip()) for v, e in bindings]

    # Strip the matched let-bindings from the source so the edge regex
    # doesn't accidentally match a stage var on the LHS of a `=`. The
    # remaining text is everything AFTER the bindings.
    remainder = _LET_BINDING_RX.sub("", source_cas).strip()
    edge_match = _EDGE_RX.search(remainder)
    edge: Optional[FinalEdge] = None
    if edge_match is not None:
        head, tail = edge_match.group(1), edge_match.group(2)
        edge = FinalEdge(head=head, tail=tail)
    return RpmChain(stages=stages, edge=edge)


# ---------------------------------------------------------------------------
# Repair log + result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RpmRepair:
    """One repair operation applied to the rendered text.

    ``kind`` names the operation:
      - ``"stage_identifier"`` — a drifted/malformed stage var was
        substituted back to its source spelling.
      - ``"missing_stage_prefix"`` — bare ``A0_2_0277`` was prefixed
        with ``stage``.
      - ``"final_edge"`` — the closing ``X leads to Y`` (or ``X -> Y``)
        was rewritten so head/tail match the source edge.
    """
    kind: str
    source: str
    found: str


@dataclass(frozen=True)
class StageSemantics:
    """Decomposed semantic content of a ``let stageX = <expr>;`` clause.

    Any field may be ``None`` when the source expression doesn't carry
    that axis. Examples:
      - ``^0^P`` -> noetic=0, domain='P', drive=None, register=None
      - ``^9^P_{F3}`` -> noetic=9, domain='P', drive=3, register=None
      - ``^4^C|A`` -> noetic=4, domain='C', drive=None, register='A'
      - ``^9^P_{F3}|T`` -> noetic=9, domain='P', drive=3, register='T'
    """
    noetic: Optional[int]
    domain: Optional[str]
    drive: Optional[int]
    register: Optional[str]


@dataclass
class SemanticDrift:
    """A flagged-only semantic mismatch between source CAS and rendered
    English for one rpm_chain stage. Phase 2 directive (2026-05-10):
    log only, do NOT rewrite. The audit JSONL surfaces these so the
    next round can decide whether to promote semantic substitution.

    ``drift_kinds`` is a list of short identifiers describing which
    axis drifted. Possible values:
      - ``"noetic_missing"`` — expected ^N indicator absent from clause
      - ``"noetic_wrong"`` — clause carries indicator for a different ^M
      - ``"domain_missing"`` / ``"domain_wrong"``
      - ``"drive_missing"`` / ``"drive_wrong"``
    """
    stage_var: str
    expected_expr: str
    rendered_clause: str
    expected_noetic: Optional[int] = None
    expected_domain: Optional[str] = None
    expected_drive: Optional[int] = None
    drift_kinds: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class RpmRepairLog:
    """Audit-friendly summary of one repair pass."""
    chain_parsed: bool = False
    n_stages_expected: int = 0
    n_stages_found_pre_repair: int = 0
    n_stages_found_post_repair: int = 0
    edge_present_in_source: bool = False
    edge_matched_pre_repair: bool = False
    edge_matched_post_repair: bool = False
    repairs: list[RpmRepair] = field(default_factory=list)
    semantic_drifts: list[SemanticDrift] = field(default_factory=list)

    @property
    def n_repairs(self) -> int:
        return len(self.repairs)

    def to_dict(self) -> dict[str, object]:
        return {
            "chain_parsed": self.chain_parsed,
            "n_stages_expected": self.n_stages_expected,
            "n_stages_found_pre_repair": self.n_stages_found_pre_repair,
            "n_stages_found_post_repair": self.n_stages_found_post_repair,
            "edge_present_in_source": self.edge_present_in_source,
            "edge_matched_pre_repair": self.edge_matched_pre_repair,
            "edge_matched_post_repair": self.edge_matched_post_repair,
            "n_repairs": self.n_repairs,
            "repairs": [
                {"kind": r.kind, "source": r.source, "found": r.found}
                for r in self.repairs
            ],
            "n_semantic_drifts": len(self.semantic_drifts),
            "semantic_drifts": [
                {
                    "stage_var": d.stage_var,
                    "expected_expr": d.expected_expr,
                    "rendered_clause": d.rendered_clause,
                    "expected_noetic": d.expected_noetic,
                    "expected_domain": d.expected_domain,
                    "expected_drive": d.expected_drive,
                    "drift_kinds": list(d.drift_kinds),
                    "notes": list(d.notes),
                }
                for d in self.semantic_drifts
            ],
        }


# ---------------------------------------------------------------------------
# Repair primitives
# ---------------------------------------------------------------------------

# A "stage-shaped" identifier the model might have emitted: starts with
# ``stage`` (or a bare ``A0_``/``D2_``/``W3_``/``P2_`` if the prefix
# was dropped) followed by alphanumerics + underscores.
_STAGE_LIKE_RX = re.compile(
    r"\bstage[A-Za-z0-9_]*\b"
)
# Bare stage suffix: catch dropped-prefix renderings like
# "A0_3_0234 names a foundational thought" — uppercase letter +
# digit/letter + underscore + digits + underscore + digits, with the
# leading word boundary and not preceded by ``stage``.
_BARE_STAGE_SUFFIX_RX = re.compile(
    r"(?<![A-Za-z_])([A-Z][A-Za-z0-9]*_[0-9]+_[0-9]+)\b"
)
# Final-edge phrasings the model uses. We check the LAST such phrase
# in the rendered text — closing edges typically land in the last
# clause. Patterns recognized:
#   "X leads to Y" / "X then leads to Y" / "X flows into Y" /
#   "X -> Y" / "X → Y" / "X feeds into Y" / "X transitions to Y"
_EDGE_PHRASE_RX = re.compile(
    r"\b(stage[A-Za-z0-9_]+)\s+"
    r"(then\s+leads\s+to|leads\s+to|flows\s+into|feeds\s+into|"
    r"transitions\s+to|->|→)\s+"
    r"(stage[A-Za-z0-9_]+)\b"
)


def _norm(s: str) -> str:
    """Lowercase + strip non-alnum for fuzzy comparison."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _best_source_match(found: str, sources: list[str]) -> Optional[str]:
    """Return the source stage_var that the rendered ``found`` token
    most likely refers to. Heuristic: same prefix at length-3, and
    minimum Levenshtein-style mismatch on the suffix. Returns ``None``
    if no source has a sufficiently close prefix.

    Phase 1 stays deterministic — we use a tight prefix gate (first
    3 alnum chars must match) so we don't rewrite a genuinely
    different stage name. Suffix matching is by character difference
    count.
    """
    found_n = _norm(found)
    if not found_n:
        return None
    prefix = found_n[:3]
    candidates: list[tuple[int, str]] = []
    for src in sources:
        src_n = _norm(src)
        if not src_n.startswith(prefix):
            continue
        # Character-level mismatch count over the longer of the two.
        max_len = max(len(found_n), len(src_n))
        diff = sum(
            1 for i in range(max_len)
            if (i >= len(found_n) or i >= len(src_n) or found_n[i] != src_n[i])
        )
        candidates.append((diff, src))
    if not candidates:
        return None
    candidates.sort()
    best_diff, best_src = candidates[0]
    # Cap on how much the suffix may differ. Two characters covers
    # off-by-one-digit (the common "0277" -> "0272" drift) and a
    # single dropped trailing char. More than that is a different
    # stage and we should NOT rewrite it.
    if best_diff > 2:
        return None
    return best_src


def _repair_stage_identifiers(
    text: str,
    chain: RpmChain,
    log: RpmRepairLog,
) -> str:
    """Substitute drifted/malformed stage tokens back to their source
    spellings. Records each substitution in ``log.repairs``.
    """
    # First pass: stage-prefixed tokens. Rewrite `stage` matches that
    # don't exactly equal one of the source stage_vars but are close.
    sources = chain.stage_vars
    if not sources:
        return text
    source_set = set(sources)

    def _stage_sub(m: re.Match) -> str:
        token = m.group(0)
        if token in source_set:
            return token
        best = _best_source_match(token, sources)
        if best is None or best == token:
            return token
        log.repairs.append(RpmRepair(
            kind="stage_identifier", source=best, found=token,
        ))
        return best

    text = _STAGE_LIKE_RX.sub(_stage_sub, text)

    # Second pass: bare stage suffixes (dropped `stage` prefix). Only
    # rewrite when the suffix has a unique close match in source.
    def _bare_sub(m: re.Match) -> str:
        suffix = m.group(1)
        full_form = "stage" + suffix
        if full_form in source_set:
            log.repairs.append(RpmRepair(
                kind="missing_stage_prefix",
                source=full_form, found=suffix,
            ))
            return full_form
        # Try fuzzy match: maybe the suffix itself drifted too.
        best = _best_source_match(full_form, sources)
        if best is None:
            return suffix
        log.repairs.append(RpmRepair(
            kind="missing_stage_prefix",
            source=best, found=suffix,
        ))
        return best

    text = _BARE_STAGE_SUFFIX_RX.sub(_bare_sub, text)
    return text


def _count_stage_mentions(text: str, chain: RpmChain) -> int:
    """Count how many distinct source stage_vars appear in ``text``
    (exact matches only — used to track pre/post repair coverage)."""
    found = 0
    for var in chain.stage_vars:
        if var and re.search(rf"\b{re.escape(var)}\b", text):
            found += 1
    return found


def _repair_final_edge(
    text: str,
    chain: RpmChain,
    log: RpmRepairLog,
) -> str:
    """If the rendered text has an edge phrase that names the wrong
    head or tail, rewrite the names so they match the source edge.

    We only rewrite identifiers; the connector phrase ("leads to",
    "flows into", arrow, etc.) is preserved so the prose stays natural.
    """
    if chain.edge is None:
        return text
    expected_head = chain.edge.head
    expected_tail = chain.edge.tail
    # Find the LAST edge phrase in the text. Use finditer to enumerate
    # then pick the last; rewriting only the last is conservative.
    matches = list(_EDGE_PHRASE_RX.finditer(text))
    if not matches:
        # No recognized edge phrase. Phase 1 doesn't synthesize one
        # from nothing; that would risk breaking the prose. Just
        # record that we couldn't verify the edge.
        return text
    last = matches[-1]
    head_found = last.group(1)
    connector = last.group(2)
    tail_found = last.group(3)
    if head_found == expected_head and tail_found == expected_tail:
        # Edge already correct.
        return text
    # Rewrite this match in-place: keep the connector verbatim, swap
    # the two identifiers. Record both substitutions.
    if head_found != expected_head:
        log.repairs.append(RpmRepair(
            kind="final_edge", source=expected_head, found=head_found,
        ))
    if tail_found != expected_tail:
        log.repairs.append(RpmRepair(
            kind="final_edge", source=expected_tail, found=tail_found,
        ))
    new_phrase = f"{expected_head} {connector} {expected_tail}"
    return text[: last.start()] + new_phrase + text[last.end() :]


def _edge_in_text(text: str, edge: FinalEdge) -> bool:
    """True iff ``text`` contains an edge phrase whose head and tail
    exactly match ``edge``."""
    for m in _EDGE_PHRASE_RX.finditer(text):
        if m.group(1) == edge.head and m.group(3) == edge.tail:
            return True
    return False


# ---------------------------------------------------------------------------
# Phase 2 — flag-only semantic verifier
# ---------------------------------------------------------------------------
#
# Parses each let-binding's expression into (Noetic, Domain, Drive,
# Register), finds the matching clause in the rendered text, and
# checks whether the canonical colloquialism for each axis appears.
# When the expected indicator is missing, OR a different axis's
# indicator appears in its place, a SemanticDrift is logged. NO
# rewriting in Phase 2 — that decision is deferred per user audit
# 2026-05-10 (post commit 702a910).

_NOETIC_RX = re.compile(r"\^([0-9])")
_DOMAIN_RX = re.compile(r"\^([0-9])\^([PCEO])")
_DRIVE_RX = re.compile(r"_\{F([1-7])\}")
_REGISTER_RX = re.compile(r"\|([TAfE])(?![A-Za-z])")


def parse_stage_semantics(expr: str) -> StageSemantics:
    """Decompose a let-binding RHS like ``^9^P_{F3}|T`` into structured
    fields. Any field is ``None`` when the corresponding axis is
    absent from the expression.

    Robust to optional axes:
      - ``^0^P`` -> noetic=0, domain='P', drive=None, register=None
      - ``^9^P_{F3}`` -> noetic=9, domain='P', drive=3
      - ``^4^C|A`` -> noetic=4, domain='C', register='A'
    """
    noetic_match = _DOMAIN_RX.search(expr)
    if noetic_match is not None:
        noetic = int(noetic_match.group(1))
        domain = noetic_match.group(2)
    else:
        # No domain attached; just look for the bare ^N
        nm = _NOETIC_RX.search(expr)
        noetic = int(nm.group(1)) if nm else None
        domain = None
    drive_match = _DRIVE_RX.search(expr)
    drive = int(drive_match.group(1)) if drive_match else None
    register_match = _REGISTER_RX.search(expr)
    register = register_match.group(1) if register_match else None
    return StageSemantics(
        noetic=noetic, domain=domain, drive=drive, register=register,
    )


# Canonical colloquialism map (CLAUDE.md Clarification 6). Each entry
# is a list of lower-case substrings; presence of ANY indicator in a
# rendered clause counts as "this axis is verbalized." Indicators
# stay narrow on purpose — overly generic words like "thought" alone
# would create false positives across all 10 Noetics.
_NOETIC_INDICATORS: dict[int, tuple[str, ...]] = {
    0: ("foundational thought", "in your head", "all in",
        "an idea", "an thought", "a thought"),
    1: ("paying attention", "make up your mind",
        "using your head", "cognitive attention",
        "pay attention", "pays attention", "paid attention",
        "give attention", "gives attention", "given attention"),
    2: ("drawn to", "speaks to", "can't resist",
        "drawn toward", "attracted toward"),
    3: ("rubs the wrong way", "can't stomach", "wouldn't touch",
        "averse to", "repelled", "an aversion", "the aversion",
        "aversion", "averse", "pushed away"),
    4: ("struck a chord", "hit me", "resonated",
        "made an impression", "strikes a chord",
        "resonates", "resonates with", "strike a chord", "hits me",
        "resonance"),
    5: ("who one is", "who you are", "shaped by",
        "sum of experiences", "part of what makes",
        "shaped by experiences", "shaped by experience",
        "sense of self", "one's sense of self", "one's experiences"),
    6: ("breaking it down", "unpacking",
        "what's underneath", "pulling apart", "decomposition"),
    7: ("muscle memory", "practice makes perfect",
        "into a groove", "repeatedly do",
        "practiced rhythm", "practice-based"),
    8: ("that reminds", "one thing leads",
        "triggered a memory", "made me think",
        "triggers", "trigger", "memory trigger", "memory triggers"),
    9: ("popped into", "popped to mind",
        "out of nowhere", "came to me",
        "just clicked", "popped into mind",
        "popped"),
}

_DOMAIN_INDICATORS: dict[str, tuple[str, ...]] = {
    "P": ("principled", "foundational", "principled foundation"),
    "C": ("cognitive thinking", "cognitive attention",
          "cognitive judgment", "cognitive"),
    "E": ("evaluative judgment", "evaluative arena", "evaluative"),
    "O": ("operational behavior", "operational"),
}

_DRIVE_INDICATORS: dict[int, tuple[str, ...]] = {
    1: ("unity", "togetherness", "union"),
    2: ("wisdom", "insight"),
    3: ("vitality", "energy and vitality", "life force"),
    4: ("connection", "attachment"),
    5: ("agency", "self-determination"),
    6: ("structure", "order", "organization"),
    7: ("purpose", "meaning"),
}


def find_stage_clauses(
    text: str, stage_vars: list[str],
) -> dict[str, str]:
    """Map each stage_var to the substring of ``text`` that describes
    it. The clause for stage_var N runs from the FIRST occurrence of
    that var to the FIRST occurrence of stage_var N+1 (in source
    order), or to end of text for the last stage.

    Stage vars not found in the text map to an empty string. The
    caller can use that to distinguish "stage missing" from "stage
    present with semantic drift."
    """
    positions: list[tuple[int, str]] = []
    for var in stage_vars:
        m = re.search(rf"\b{re.escape(var)}\b", text)
        if m is not None:
            positions.append((m.start(), var))
    positions.sort()

    clauses: dict[str, str] = {var: "" for var in stage_vars}
    for i, (start, var) in enumerate(positions):
        if i + 1 < len(positions):
            end = positions[i + 1][0]
        else:
            end = len(text)
        clauses[var] = text[start:end].strip().rstrip(",.")
    return clauses


def _check_axis(
    clause_lower: str,
    expected_value: object,
    indicator_map: dict,
    axis_name: str,
) -> tuple[list[str], list[str]]:
    """Return (drift_kinds, notes) for one axis. Empty when no drift."""
    drift_kinds: list[str] = []
    notes: list[str] = []
    if expected_value is None:
        return drift_kinds, notes
    expected_indicators = indicator_map.get(expected_value, ())
    has_expected = any(ind in clause_lower for ind in expected_indicators)
    if not has_expected:
        drift_kinds.append(f"{axis_name}_missing")
        label = f"^{expected_value}" if axis_name == "noetic" else (
            f"F{expected_value}" if axis_name == "drive"
            else f"^{expected_value}"
        )
        notes.append(
            f"expected {label} indicator missing from clause"
        )
        # Look for a different axis-value's indicator to identify a
        # plausible "wrong" substitute.
        for value, indicators in indicator_map.items():
            if value == expected_value:
                continue
            if any(ind in clause_lower for ind in indicators):
                drift_kinds.append(f"{axis_name}_wrong")
                wrong_label = f"^{value}" if axis_name == "noetic" else (
                    f"F{value}" if axis_name == "drive"
                    else f"^{value}"
                )
                notes.append(
                    f"clause carries {wrong_label} indicator instead"
                )
                break
    return drift_kinds, notes


def verify_rpm_semantics(
    rendered: str, chain: RpmChain,
) -> list[SemanticDrift]:
    """Phase 2 entry point. Returns one SemanticDrift per stage that
    has a detectable axis mismatch. Stages with all axes verbalized
    correctly produce NO drift entry — the absence is the signal.
    """
    drifts: list[SemanticDrift] = []
    if not chain.stages:
        return drifts
    clauses = find_stage_clauses(
        rendered, [s.var for s in chain.stages],
    )
    for stage in chain.stages:
        clause = clauses.get(stage.var, "")
        if not clause:
            # Stage missing entirely from rendered text. Phase 1's
            # n_stages_found_post_repair already surfaces this; we
            # don't double-flag at the semantic layer.
            continue
        expected = parse_stage_semantics(stage.expr)
        clause_lower = clause.lower()

        all_kinds: list[str] = []
        all_notes: list[str] = []

        n_kinds, n_notes = _check_axis(
            clause_lower, expected.noetic, _NOETIC_INDICATORS, "noetic",
        )
        all_kinds.extend(n_kinds)
        all_notes.extend(n_notes)

        d_kinds, d_notes = _check_axis(
            clause_lower, expected.domain, _DOMAIN_INDICATORS, "domain",
        )
        all_kinds.extend(d_kinds)
        all_notes.extend(d_notes)

        dr_kinds, dr_notes = _check_axis(
            clause_lower, expected.drive, _DRIVE_INDICATORS, "drive",
        )
        all_kinds.extend(dr_kinds)
        all_notes.extend(dr_notes)

        if all_kinds:
            drifts.append(SemanticDrift(
                stage_var=stage.var,
                expected_expr=stage.expr,
                rendered_clause=clause,
                expected_noetic=expected.noetic,
                expected_domain=expected.domain,
                expected_drive=expected.drive,
                drift_kinds=all_kinds,
                notes=all_notes,
            ))
    return drifts


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def repair_rpm_rendering(
    *,
    source_cas: str,
    rendered: str,
    chain: Optional[RpmChain] = None,
) -> tuple[str, RpmRepairLog]:
    """Run Phase 1 symbolic repair on ``rendered``.

    Returns ``(repaired_text, log)``. When ``chain`` is None we parse
    it from ``source_cas``; callers that already have a chain can pass
    it through to skip re-parsing.

    No-op contract: when ``parse_rpm_chain`` returns None (non-RPM
    shape), or when ``rendered`` is empty, we return ``(rendered, log)``
    with ``log.chain_parsed == False`` and no repairs.
    """
    if chain is None:
        chain = parse_rpm_chain(source_cas)
    log = RpmRepairLog()
    if chain is None or not rendered:
        return rendered, log

    log.chain_parsed = True
    log.n_stages_expected = len(chain.stages)
    log.n_stages_found_pre_repair = _count_stage_mentions(rendered, chain)
    log.edge_present_in_source = chain.edge is not None
    if chain.edge is not None:
        log.edge_matched_pre_repair = _edge_in_text(rendered, chain.edge)

    text = _repair_stage_identifiers(rendered, chain, log)
    text = _repair_final_edge(text, chain, log)

    log.n_stages_found_post_repair = _count_stage_mentions(text, chain)
    if chain.edge is not None:
        log.edge_matched_post_repair = _edge_in_text(text, chain.edge)

    # Phase 2 semantic verifier (flag-only). Runs on the post-repair
    # text so it sees the canonical stage names, then checks each
    # stage's clause against the expected Noetic/Domain/Drive. Drifts
    # are LOGGED only — no rewrite of ``text``.
    log.semantic_drifts = verify_rpm_semantics(text, chain)

    return text, log


__all__ = [
    "FinalEdge",
    "RpmChain",
    "RpmRepair",
    "RpmRepairLog",
    "SemanticDrift",
    "StageBinding",
    "StageSemantics",
    "find_stage_clauses",
    "parse_rpm_chain",
    "parse_stage_semantics",
    "repair_rpm_rendering",
    "verify_rpm_semantics",
]
