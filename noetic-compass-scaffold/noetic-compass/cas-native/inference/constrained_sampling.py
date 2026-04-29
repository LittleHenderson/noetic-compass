"""Grammar-constrained CAS expression decoding helpers.

This module is deliberately inference-side only.  It does not change the CAS
compiler; instead, it builds bucket-specific finite-state tries from
compiler-valid candidate expressions and lets the model choose only legal next
tokens from that trie.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
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
