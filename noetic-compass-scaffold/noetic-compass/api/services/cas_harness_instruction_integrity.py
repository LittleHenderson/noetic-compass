"""Shadow-mode instruction-integrity findings for CAS Harness.

This module is deterministic and intentionally conservative. It records
possible instruction-integrity risks, but it never produces or mutates final
CAS Harness verdicts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any, Iterable, Literal, Mapping


IntegrityStatus = Literal["present", "FLAG_FOR_HUMAN_REVIEW"]
TruthState = Literal["VALID", "UNDETERMINED"]
Severity = Literal["low", "medium", "high"]

SCHEMA_VERSION = "cas_harness_instruction_integrity.v0.shadow"
SPAN_EXCERPT_LIMIT = 160


@dataclass(frozen=True)
class InstructionIntegrityFinding:
    kind: str
    severity: Severity
    source: str
    span_hash: str
    span_excerpt: str
    authority_level: str
    gate: str
    decision: str
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
class InstructionIntegrityReport:
    schema_version: str
    mode: Literal["shadow"]
    status: IntegrityStatus
    truth_state: TruthState
    verdict_effect: Literal["none_shadow_only"]
    findings: list[InstructionIntegrityFinding]
    claim_grounding: list[ClaimGrounding]
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
        repair="reverse_to_preserve_upstream_instruction_hierarchy",
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
        repair="replace_with_unavailable_and_redact_secret_request",
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
        repair="reverse_to_declared_role_boundary",
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
        repair="remove_from_active_context_and_preserve_original_task",
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

_SECRET_VALUE_RE = re.compile(
    r"\b([A-Za-z0-9_\-]{24,}|sk-[A-Za-z0-9_\-]+|ghp_[A-Za-z0-9_]+)\b"
)
_NEGATED_INSTRUCTION_PREFIX_RE = re.compile(
    r"\b(do not|don't|never|must not|should not|cannot|can't|refus(?:e|ed|es|ing) to)\s*$",
    re.IGNORECASE,
)
_BENIGN_QUOTED_CONTEXT_RE = re.compile(
    r"\b(quoted|quote|phrase|example|sample|transcript|classify|summari[sz]e|"
    r"analy[sz]e|label|refusal|refused|safety policy)\b",
    re.IGNORECASE,
)
_BENIGN_FORMAT_TARGET_RE = re.compile(
    r"\b(json|yaml|xml|csv|schema|fields?|bullets?|markdown|one sentence|"
    r"short answer|audit report)\b",
    re.IGNORECASE,
)
_NEGATED_OR_GOVERNANCE_CLAIM_RE = re.compile(
    r"\b(do not|don't|never|must not|should not|cannot|can't|does not|is not|"
    r"not yet|avoid claiming|do not claim|do not market|do not say)\b"
    r".{0,80}$",
    re.IGNORECASE | re.DOTALL,
)


def build_instruction_integrity_report(
    *,
    prompt_text: str | None = None,
    scenario_text: str | None = None,
    output_text: str | None = None,
    evidence_packet_trace_id: str | None = None,
    evidence_packet: Mapping[str, Any] | None = None,
    proof_chips: Iterable[Mapping[str, Any]] | None = None,
    activation_detection: Mapping[str, Any] | None = None,
) -> InstructionIntegrityReport:
    """Build a shadow-only instruction-integrity report.

    The report can flag risk, but it has no final verdict effect. Enforcement
    and customer-facing `ACCEPT` / `SUPPRESS` remain owned by the evidence-gated
    verdict runner.
    """

    sources = [
        ("prompt", prompt_text),
        ("scenario_text", scenario_text),
        ("model_output", output_text),
    ]
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
    flagged = bool(findings or any(c.support_status == "unavailable" for c in claim_grounding))
    truth_state: TruthState = "UNDETERMINED" if flagged else "VALID"
    status: IntegrityStatus = "FLAG_FOR_HUMAN_REVIEW" if flagged else "present"
    coverage_status = "incomplete" if flagged else "present"
    gluing: dict[str, Any] = {
        "coverage_status": coverage_status,
        "lacunarity_flags": lacunarity_flags,
        "truth_state": truth_state,
        "evidence_packet_trace_id": evidence_packet_trace_id,
    }
    if activation_detection is not None:
        gluing["activation_detection"] = dict(activation_detection)

    return InstructionIntegrityReport(
        schema_version=SCHEMA_VERSION,
        mode="shadow",
        status=status,
        truth_state=truth_state,
        verdict_effect="none_shadow_only",
        findings=findings,
        claim_grounding=claim_grounding,
        gluing=gluing,
    )


def _find_instruction_risks(source_name: str, text: str) -> list[InstructionIntegrityFinding]:
    findings: list[InstructionIntegrityFinding] = []
    seen: set[tuple[str, str]] = set()
    for spec in _FINDING_PATTERNS:
        for match in spec.pattern.finditer(text):
            if _is_benign_instruction_mention(text, match.start(), match.end(), spec.kind):
                continue
            matched = match.group(0)
            key = (spec.kind, _span_hash(source_name, matched))
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                InstructionIntegrityFinding(
                    kind=spec.kind,
                    severity=spec.severity,
                    source=source_name,
                    span_hash=key[1],
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
            if _is_negated_or_governance_claim_mention(text, match.start()):
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


def _lacunarity_flags(
    findings: list[InstructionIntegrityFinding],
    claim_grounding: list[ClaimGrounding],
) -> list[str]:
    flags: set[str] = set()
    for finding in findings:
        if finding.kind == "authority_override":
            flags.add("policy_override")
        elif finding.kind == "secret_exfiltration":
            flags.add("secret_boundary")
        elif finding.kind == "role_confusion":
            flags.add("authority_confusion")
        elif finding.kind == "task_replacement":
            flags.add("task_drift")
    if any(claim.support_status == "unavailable" for claim in claim_grounding):
        flags.add("missing_evidence_span")
    return sorted(flags)


def _evidence_refs(
    evidence_packet_trace_id: str | None,
    evidence_packet: Mapping[str, Any] | None,
) -> list[str]:
    refs: list[str] = []
    trace = evidence_packet_trace_id
    if trace is None and isinstance(evidence_packet, Mapping):
        raw_trace = evidence_packet.get("trace_id")
        trace = raw_trace if isinstance(raw_trace, str) else None
    if trace:
        refs.append(f"evidence_packet:{trace}")
    return refs


def _has_present_packet_proof(proof_chips: Iterable[Mapping[str, Any]] | None) -> bool:
    if proof_chips is None:
        return False
    for chip in proof_chips:
        if chip.get("id") == "packet_proof" and chip.get("status") in {"present", "verified"}:
            return True
    return False


def _is_benign_instruction_mention(text: str, start: int, end: int, kind: str) -> bool:
    prefix = text[max(0, start - 120) : start]
    suffix = text[end : min(len(text), end + 120)]
    local_prefix = text[max(0, start - 40) : start]
    if _NEGATED_INSTRUCTION_PREFIX_RE.search(local_prefix):
        return True
    if _is_inside_double_or_backtick_quote(text, start) and _BENIGN_QUOTED_CONTEXT_RE.search(prefix):
        return True
    if kind == "task_replacement" and _BENIGN_FORMAT_TARGET_RE.search(suffix):
        return True
    return False


def _is_negated_or_governance_claim_mention(text: str, start: int) -> bool:
    prefix = text[max(0, start - 120) : start]
    return bool(_NEGATED_OR_GOVERNANCE_CLAIM_RE.search(prefix))


def _is_inside_double_or_backtick_quote(text: str, index: int) -> bool:
    prefix = text[:index]
    return prefix.count('"') % 2 == 1 or prefix.count("`") % 2 == 1


def _span_hash(source_name: str, span: str) -> str:
    digest = hashlib.sha256(f"{source_name}:{span}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _safe_excerpt(value: str) -> str:
    redacted = _SECRET_VALUE_RE.sub("[REDACTED]", value)
    collapsed = " ".join(redacted.split())
    if len(collapsed) <= SPAN_EXCERPT_LIMIT:
        return collapsed
    return f"{collapsed[: SPAN_EXCERPT_LIMIT - 3]}..."
