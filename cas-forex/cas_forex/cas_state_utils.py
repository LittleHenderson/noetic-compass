"""Lightweight CAS state-literal helpers shared by the CJT/PCBA sidecars.

These helpers parse the *surface* of a CAS state literal (`^k^D_{Fd}|R`) for
diagnostic and static-lint purposes. They are intentionally NOT the CAS
compiler: structural validity, admissibility, and domain descent remain the
compiler's authority (see ``compiler_bridge.CASCompilerBridge``). These helpers
only extract the Noetic index, Domain, Drive, and Register so the evidence-only
sidecars can reason about precedence and involution without re-implementing the
compiler.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# ^k^D_{Fd}|R  e.g. ^8^C_{F2}|A — drive block and register are optional.
_STATE_RE = re.compile(
    r"\^(?P<noetic>\d+)\^(?P<domain>[PCEO])(?:_\{F(?P<drive>\d+)\})?(?:\|(?P<register>[A-Za-z]))?"
)

# Domain precedence (CLAUDE.md): P ≻ C ≻ E ≻ O. Lower rank = higher precedence.
DOMAIN_PRECEDENCE: dict[str, int] = {"P": 0, "C": 1, "E": 2, "O": 3}

# Noetic involution pairs (CLAUDE.md): CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9.
# Self-duals: 0, 1, 4, 7.
_INVOLUTION: dict[int, int] = {2: 3, 3: 2, 5: 6, 6: 5, 8: 9, 9: 8}


@dataclass(frozen=True)
class ParsedState:
    """Surface decomposition of a CAS state literal."""

    raw: str
    noetic: int
    domain: str
    drive: Optional[int] = None
    register: Optional[str] = None


def parse_state_literal(text: str) -> Optional[ParsedState]:
    """Return the first CAS state literal found in ``text``, or None."""

    match = _STATE_RE.search(text or "")
    if not match:
        return None
    return ParsedState(
        raw=match.group(0),
        noetic=int(match.group("noetic")),
        domain=match.group("domain"),
        drive=int(match.group("drive")) if match.group("drive") else None,
        register=match.group("register"),
    )


def domain_of(text: str) -> Optional[str]:
    """Return the Domain letter (P/C/E/O) of the first state literal in text."""

    parsed = parse_state_literal(text)
    return parsed.domain if parsed else None


def noetic_of(text: str) -> Optional[int]:
    """Return the Noetic index of the first state literal in text."""

    parsed = parse_state_literal(text)
    return parsed.noetic if parsed else None


def domain_rank(domain: str) -> Optional[int]:
    """Return precedence rank (0=highest, 3=lowest) for a domain letter."""

    return DOMAIN_PRECEDENCE.get(domain)


def is_involution_pair(noetic_a: int, noetic_b: int) -> bool:
    """True if the two Noetics form a complementary involution pair."""

    return _INVOLUTION.get(noetic_a) == noetic_b
