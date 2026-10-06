"""Deterministic, shadow-only Instruction Integrity scanner.

The scanner records possible prompt-injection and unsupported-claim risks. It
does not rewrite input, remove spans, block execution, mutate an audit verdict,
or create an ACCEPT decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import base64
import hashlib
import html
import re
from typing import Any, Iterable, Literal, Mapping
from urllib.parse import unquote


IntegrityStatus = Literal["present", "FLAG_FOR_HUMAN_REVIEW"]
TruthState = Literal["VALID", "UNDETERMINED"]
Severity = Literal["low", "medium", "high"]

SCHEMA_VERSION = "cas_harness_instruction_integrity.v0.shadow"
SPAN_EXCERPT_LIMIT = 160
_ZERO_WIDTH_RE = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")
_BASE64_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{24,}={0,2}(?![A-Za-z0-9+/=])")
_SECRET_VALUE_RE = re.compile(
    r"\b([A-Za-z0-9_\-]{24,}|sk-[A-Za-z0-9_\-]+|ghp_[A-Za-z0-9_]+)\b"
)


@dataclass(frozen=True)
class InstructionIntegrityFinding:
    kind: str
    severity: Severity
    source: str
    surface: str
    span_start: int
    span_end: int
    span_hash: str
    span_excerpt: str
    authority_level: str
    gate: str
    decision: Literal["FLAG_FOR_HUMAN_REVIEW"]
    repair: str
    reason: str
    evidence_refs: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClaimGrounding:
    claim_hash: str
    claim_excerpt: str
    support_status: Literal["present", "unavailable"]
    decision: str
    reason: str
    evidence_refs: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewRouting:
    route: Literal["none", "instruction_integrity_review"]
    decision: Literal["none", "FLAG_FOR_HUMAN_REVIEW"]
    reason_codes: list[str]
    automatic_action: Literal["none"]
    live_blocking: Literal[False]
    auto_removal: Literal[False]
    automatic_accept: Literal[False]
    verdict_effect: Literal["none_shadow_only"]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InstructionIntegrityReport:
    schema_version: str
    mode: Literal["shadow"]
    status: IntegrityStatus
    truth_state: TruthState
    verdict_effect: Literal["none_shadow_only"]
    findings: list[InstructionIntegrityFinding]
    claim_grounding: list[ClaimGrounding]
    review_routing: ReviewRouting
    gluing: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "status": self.status,
            "truth_state": self.truth_state,
            "verdict_effect": self.verdict_effect,
            "findings": [finding.to_dict() for finding in self.findings],
            "claim_grounding": [claim.to_dict() for claim in self.claim_grounding],
            "review_routing": self.review_routing.to_dict(),
            "gluing": dict(self.gluing),
        }


@dataclass(frozen=True)
class _PatternSpec:
    kind: str
    severity: Severity
    gate: str
    repair: str
    reason: str
    pattern: re.Pattern[str]


_FINDING_PATTERNS: tuple[_PatternSpec, ...] = (
    _PatternSpec(
        kind="authority_override",
        severity="high",
        gate="domain_precedence",
        repair="preserve_upstream_instruction_hierarchy",
        reason="Untrusted text attempts to override upstream instructions or policy authority.",
        pattern=re.compile(
            r"\b(ignore|disregard|bypass|override|forget)\b.{0,80}"
            r"\b(previous|above|system|developer|instruction|policy|rules?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    _PatternSpec(
        kind="secret_exfiltration",
        severity="high",
        gate="provenance_and_secret_boundary",
        repair="redact_secret_request_for_human_review",
        reason="Text requests hidden prompts, secrets, credentials, keys, or tokens.",
        pattern=re.compile(
            r"\b(reveal|print|show|dump|exfiltrate|leak|return)\b.{0,80}"
            r"\b(system prompt|hidden prompt|developer message|api key|token|secret|credential|password)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    _PatternSpec(
        kind="role_confusion",
        severity="medium",
        gate="authority_boundary",
        repair="preserve_declared_role_boundary",
        reason="Text tries to change role authority instead of staying inside the declared audit task.",
        pattern=re.compile(
            r"\b(you are now|act as|pretend to be|switch to)\b.{0,80}"
            r"\b(system|developer|admin|root|policy engine)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    _PatternSpec(
        kind="task_replacement",
        severity="medium",
        gate="task_gluing",
        repair="preserve_original_task_for_human_review",
        reason="Text attempts to replace the active task with a different output objective.",
        pattern=re.compile(
            r"\b(instead|new task|your real task|only output|reply exactly|final answer must be)\b",
            re.IGNORECASE,
        ),
    ),
)

_UNSUPPORTED_CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(prevents?|detects?|guarantees?|proves?|neutralizes?)\b.{0,100}"
        r"\b(prompt injection|jailbreak|hallucination|hallucinations|hijack)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(prompt[- ]injection[- ]proof|hallucination[- ]proof|jailbreak[- ]proof|immune)\b",
        re.IGNORECASE,
    ),
)

_BENIGN_CONTEXT_MARKERS = (
    "quoted phrase",
    "prompt-injection example",
    "do not execute it",
    "model refused to",
    "write a safety policy",
    "never dump",
    "never leak",
    "does not prevent",
    "without creating a final verdict",
    "only output valid json",
)


def build_instruction_integrity_report(
    *,
    prompt_text: str | None = None,
    scenario_text: str | None = None,
    output_text: str | None = None,
    evidence_packet_trace_id: str | None = None,
    evidence_packet: Mapping[str, Any] | None = None,
    proof_chips: Iterable[Mapping[str, Any]] | None = None,
) -> InstructionIntegrityReport:
    """Build a deterministic report with no enforcement or verdict effect."""

    sources = (
        ("prompt", prompt_text),
        ("scenario_text", scenario_text),
        ("output", output_text),
    )
    findings: list[InstructionIntegrityFinding] = []
    claim_grounding: list[ClaimGrounding] = []

    for source_name, value in sources:
        if not value:
            continue
        findings.extend(_find_instruction_risks(source_name, value))
        claim_grounding.extend(
            _find_unsupported_claims(
                source_name=source_name,
                text=value,
                evidence_packet_trace_id=evidence_packet_trace_id,
                evidence_packet=evidence_packet,
                proof_chips=proof_chips,
            )
        )

    lacunarity_flags = _lacunarity_flags(findings, claim_grounding)
    flagged = bool(
        findings
        or any(claim.support_status == "unavailable" for claim in claim_grounding)
    )
    truth_state: TruthState = "UNDETERMINED" if flagged else "VALID"
    status: IntegrityStatus = "FLAG_FOR_HUMAN_REVIEW" if flagged else "present"
    reason_codes = sorted(
        {
            *(finding.kind for finding in findings),
            *(
                "unsupported_claim"
                for claim in claim_grounding
                if claim.support_status == "unavailable"
            ),
        }
    )
    review_routing = ReviewRouting(
        route="instruction_integrity_review" if flagged else "none",
        decision="FLAG_FOR_HUMAN_REVIEW" if flagged else "none",
        reason_codes=reason_codes,
        automatic_action="none",
        live_blocking=False,
        auto_removal=False,
        automatic_accept=False,
        verdict_effect="none_shadow_only",
    )

    return InstructionIntegrityReport(
        schema_version=SCHEMA_VERSION,
        mode="shadow",
        status=status,
        truth_state=truth_state,
        verdict_effect="none_shadow_only",
        findings=findings,
        claim_grounding=claim_grounding,
        review_routing=review_routing,
        gluing={
            "coverage_status": "incomplete" if flagged else "present",
            "lacunarity_flags": lacunarity_flags,
            "truth_state": truth_state,
            "evidence_packet_trace_id": evidence_packet_trace_id,
        },
    )


def _find_instruction_risks(
    source_name: str, text: str
) -> list[InstructionIntegrityFinding]:
    findings: list[InstructionIntegrityFinding] = []
    seen: set[tuple[str, str, str]] = set()
    for surface_name, surface_text in _scan_surfaces(text):
        for spec in _FINDING_PATTERNS:
            for match in spec.pattern.finditer(surface_text):
                if _is_benign_context(surface_text, match.start(), match.end()):
                    continue
                matched = match.group(0)
                key = (spec.kind, source_name, matched.casefold())
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    InstructionIntegrityFinding(
                        kind=spec.kind,
                        severity=spec.severity,
                        source=source_name,
                        surface=surface_name,
                        span_start=match.start(),
                        span_end=match.end(),
                        span_hash=_span_hash(source_name, matched),
                        span_excerpt=_safe_excerpt(matched),
                        authority_level="untrusted_user_or_context",
                        gate=spec.gate,
                        decision="FLAG_FOR_HUMAN_REVIEW",
                        repair=spec.repair,
                        reason=spec.reason,
                        evidence_refs=[],
                    )
                )
    return findings


def _find_unsupported_claims(
    *,
    source_name: str,
    text: str,
    evidence_packet_trace_id: str | None,
    evidence_packet: Mapping[str, Any] | None,
    proof_chips: Iterable[Mapping[str, Any]] | None,
) -> list[ClaimGrounding]:
    claims: list[ClaimGrounding] = []
    evidence_refs = _evidence_refs(evidence_packet_trace_id, evidence_packet)
    has_support = bool(evidence_refs) and _has_present_packet_proof(proof_chips)

    for pattern in _UNSUPPORTED_CLAIM_PATTERNS:
        for match in pattern.finditer(text):
            if _is_benign_context(text, match.start(), match.end()):
                continue
            matched = match.group(0)
            claims.append(
                ClaimGrounding(
                    claim_hash=_span_hash(source_name, matched),
                    claim_excerpt=_safe_excerpt(matched),
                    support_status="present" if has_support else "unavailable",
                    decision=(
                        "record_as_supported_shadow_claim"
                        if has_support
                        else "replace_with_OPEN_or_unavailable_until_verified"
                    ),
                    reason=(
                        "Claim has packet/proof support in this shadow scan."
                        if has_support
                        else (
                            "Instruction-integrity or prevention claim lacks enough "
                            "Evidence Packet proof for production wording."
                        )
                    ),
                    evidence_refs=evidence_refs,
                )
            )
    return claims


def _scan_surfaces(text: str) -> list[tuple[str, str]]:
    """Return bounded, deterministic text surfaces without mutating input."""

    surfaces: list[tuple[str, str]] = [("raw", text)]
    normalized = html.unescape(unquote(_ZERO_WIDTH_RE.sub("", text)))
    if normalized != text:
        surfaces.append(("normalized", normalized))
    for index, match in enumerate(_BASE64_TOKEN_RE.finditer(normalized)):
        token = match.group(0)
        try:
            decoded = base64.b64decode(token, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        if decoded and len(decoded) <= 4096:
            surfaces.append((f"base64[{index}]", decoded))
    return surfaces


def _is_benign_context(text: str, start: int, end: int) -> bool:
    context = text[max(0, start - 120) : min(len(text), end + 120)].casefold()
    return any(marker in context for marker in _BENIGN_CONTEXT_MARKERS)


def _lacunarity_flags(
    findings: list[InstructionIntegrityFinding],
    claim_grounding: list[ClaimGrounding],
) -> list[str]:
    mapping = {
        "authority_override": "policy_override",
        "secret_exfiltration": "secret_boundary",
        "role_confusion": "authority_confusion",
        "task_replacement": "task_drift",
    }
    flags = {mapping[finding.kind] for finding in findings if finding.kind in mapping}
    if any(claim.support_status == "unavailable" for claim in claim_grounding):
        flags.add("missing_evidence_span")
    return sorted(flags)


def _evidence_refs(
    evidence_packet_trace_id: str | None,
    evidence_packet: Mapping[str, Any] | None,
) -> list[str]:
    trace = evidence_packet_trace_id
    if trace is None and isinstance(evidence_packet, Mapping):
        raw_trace = evidence_packet.get("trace_id")
        trace = raw_trace if isinstance(raw_trace, str) else None
    return [f"evidence_packet:{trace}"] if trace else []


def _has_present_packet_proof(
    proof_chips: Iterable[Mapping[str, Any]] | None,
) -> bool:
    if proof_chips is None:
        return False
    return any(
        chip.get("id") == "packet_proof"
        and chip.get("status") in {"present", "verified"}
        for chip in proof_chips
    )


def _span_hash(source_name: str, span: str) -> str:
    digest = hashlib.sha256(f"{source_name}:{span}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _safe_excerpt(value: str) -> str:
    redacted = _SECRET_VALUE_RE.sub("[REDACTED]", value)
    collapsed = " ".join(redacted.split())
    if len(collapsed) <= SPAN_EXCERPT_LIMIT:
        return collapsed
    return f"{collapsed[: SPAN_EXCERPT_LIMIT - 3]}..."
