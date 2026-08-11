"""Read-only professional claims and disclosure posture for CAS Forex.

This module keeps marketing/product language auditable. It does not decide
whether the system may trade; it only reports risky claims, preferred wording,
and whether the local disclosure draft exists.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Pattern


REPO_ROOT = Path(__file__).resolve().parents[1]
DISCLOSURE_DOC_PATH = Path("docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md")
CLAIM_BOUNDARY = (
    "Professional claims posture is a read-only copy and disclosure diagnostic. "
    "It does not authorize trading, block trading, provide legal advice, promise "
    "returns, or decide whether a live-money deployment is compliant. It exists "
    "so owner-facing copy stays accurate, auditable, and professionally bounded."
)


CLAIM_PATTERNS: tuple[tuple[str, str, Pattern[str]], ...] = (
    (
        "guaranteed_profit",
        "Guaranteed profit/return claim",
        re.compile(
            r"\bguarantee[sd]?\s+(profit|profits|return|returns|income|win|wins|winning)\b"
            r"|\bguarantee\s+of\s+profit\b"
            r"|\bprofits?\s+guaranteed\b"
            r"|\bguaranteed\s+\$?\d",
            re.IGNORECASE,
        ),
    ),
    (
        "no_losses",
        "No-loss claim",
        re.compile(r"\bnever\s+lose\b|\bno\s+loss(es)?\b|\bcannot\s+lose\b|\bcan't\s+lose\b", re.IGNORECASE),
    ),
    ("risk_free", "Risk-free claim", re.compile(r"\brisk[- ]free\b", re.IGNORECASE)),
    (
        "money_printer",
        "Money-printer claim",
        re.compile(r"\b(money\s+printer|prints\s+money|bot\s+prints)\b", re.IGNORECASE),
    ),
    (
        "ai_beats_market",
        "AI beats-market claim",
        re.compile(r"\bAI\s+beats?\s+the\s+market\b|\bbeats?\s+the\s+market\s+automatically\b", re.IGNORECASE),
    ),
    ("set_and_forget", "Set-and-forget claim", re.compile(r"\bset\s+and\s+forget\b", re.IGNORECASE)),
    (
        "emotion_proof",
        "Emotion-proof claim",
        re.compile(r"\bemotion[- ]proof\b|\bremoves?\s+psychology\b|\bremove\s+trading\s+psychology\b", re.IGNORECASE),
    ),
    (
        "sure_profit",
        "Sure/assured profit claim",
        re.compile(r"\bassured\s+profit\b|\bsure\s+profit\b", re.IGNORECASE),
    ),
    (
        "capital_safe",
        "Capital-safe claim",
        re.compile(r"\bcapital\s+safe\b|\bsafe\s+capital\b", re.IGNORECASE),
    ),
)

BOUNDARY_CONTEXT_MARKERS = (
    "no guaranteed",
    "not guaranteed",
    "does not guarantee",
    "do not guarantee",
    "never imply",
    "without guaranteeing",
    "not a guarantee",
    "no guarantee",
    "no profit guarantee",
    "disclosure",
    "claims to avoid",
    "forbidden",
    "reject",
    "blocked",
    "misleading",
    "risk disclosure",
)

SCAN_DIRS = (
    Path("ui/src"),
    Path("api/routes"),
    Path("cas_forex"),
)
SCAN_SUFFIXES = {".py", ".ts", ".tsx", ".md"}

REQUIRED_DISCLOSURES: tuple[dict[str, Any], ...] = (
    {
        "key": "no_profit_guarantee",
        "label": "No Profit Guarantee",
        "must_include": ("no guarantee", "profit"),
        "minimum_copy": "CAS Forex does not guarantee profit, income, returns, win rate, or loss avoidance.",
        "recommended_surfaces": ["Settings", "onboarding", "live-mode confirmation", "terms/risk page"],
    },
    {
        "key": "automated_trading_risk",
        "label": "Automated Trading Risk",
        "must_include": ("automated trading", "risk"),
        "minimum_copy": "Automated trading can open, modify, or close positions quickly and can lose money.",
        "recommended_surfaces": ["live-mode confirmation", "risk settings", "terms/risk page"],
    },
    {
        "key": "ai_limitations",
        "label": "AI Limitations",
        "must_include": ("ai", "limitations"),
        "minimum_copy": "AI analysis is probabilistic and can be wrong, stale, incomplete, or blocked by market/broker conditions.",
        "recommended_surfaces": ["assistant", "operator panel", "trade explanation cards"],
    },
    {
        "key": "broker_execution_boundary",
        "label": "Broker Execution Boundary",
        "must_include": ("broker", "execution"),
        "minimum_copy": "Broker execution, pricing, spreads, swaps, margin rules, fills, withdrawals, and account terms are controlled by the broker.",
        "recommended_surfaces": ["broker connection", "order preview", "settings"],
    },
    {
        "key": "paper_demo_live_separation",
        "label": "Paper/Demo/Live Separation",
        "must_include": ("paper", "demo", "live"),
        "minimum_copy": "Paper, demo, and live results are separate operating modes and must not be presented as equivalent proof.",
        "recommended_surfaces": ["dashboard", "history", "performance reports"],
    },
    {
        "key": "not_financial_advice",
        "label": "No Financial Advice",
        "must_include": ("not financial advice",),
        "minimum_copy": "CAS Forex is user-configured automation software and does not provide personal financial, tax, or legal advice.",
        "recommended_surfaces": ["terms/risk page", "onboarding", "assistant"],
    },
)

PREFERRED_LANGUAGE = (
    "automated execution",
    "risk-managed trading",
    "rules-based controls",
    "AI-assisted decisioning",
    "user-defined limits",
    "no guarantee of profit",
    "designed to reduce impulsive trading behavior",
)


def build_professional_claims_report(root: Path | str | None = None) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    disclosure_doc = _disclosure_document(base)
    hits = _scan_claim_hits(base)
    risky_hits = [hit for hit in hits if hit.get("severity") == "needs_review"]
    disclosures = _required_disclosure_status(disclosure_doc)
    missing = [row for row in disclosures if row["status"] != "COVERED"]
    visible_disclosure_doc = {key: value for key, value in disclosure_doc.items() if key != "text"}
    return {
        "report_kind": "cas_forex_professional_claims",
        "status": "ATTENTION" if risky_hits or missing else "OK",
        "risky_claim_count": len(risky_hits),
        "boundary_reference_count": len(hits) - len(risky_hits),
        "claim_hits": hits[:40],
        "disclosure_document": visible_disclosure_doc,
        "required_disclosures": disclosures,
        "missing_disclosures": missing,
        "copy_policy": {
            "forbidden_claim_types": [
                {"key": key, "label": label, "pattern": pattern.pattern}
                for key, label, pattern in CLAIM_PATTERNS
            ],
            "preferred_language": list(PREFERRED_LANGUAGE),
            "claim_boundary": CLAIM_BOUNDARY,
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _disclosure_document(base: Path) -> dict[str, Any]:
    path = base / DISCLOSURE_DOC_PATH
    text = _read_text(path)
    return {
        "path": DISCLOSURE_DOC_PATH.as_posix(),
        "present": bool(text),
        "line_count": len(text.splitlines()) if text else 0,
        "summary": (
            "Disclosure draft present and available for product/legal review."
            if text
            else "Disclosure draft missing."
        ),
        "text": text,
    }


def _required_disclosure_status(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    text = str(document.get("text") or "").lower()
    rows: list[dict[str, Any]] = []
    for disclosure in REQUIRED_DISCLOSURES:
        must_include = tuple(str(item).lower() for item in disclosure["must_include"])
        covered = bool(text) and all(item in text for item in must_include)
        rows.append(
            {
                "key": disclosure["key"],
                "label": disclosure["label"],
                "status": "COVERED" if covered else "MISSING_DRAFT_COPY",
                "minimum_copy": disclosure["minimum_copy"],
                "recommended_surfaces": list(disclosure["recommended_surfaces"]),
            }
        )
    return rows


def _scan_claim_hits(base: Path) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for path in _iter_scan_files(base):
        rel = path.relative_to(base)
        lines = _read_text(path).splitlines()
        for index, line in enumerate(lines):
            line_no = index + 1
            context = " ".join(lines[max(0, index - 1): min(len(lines), index + 2)])
            for key, label, pattern in CLAIM_PATTERNS:
                if not pattern.search(line):
                    continue
                boundary_context = _is_boundary_context(context)
                hits.append(
                    {
                        "path": rel.as_posix(),
                        "line": line_no,
                        "claim_type": key,
                        "label": label,
                        "severity": "boundary_reference" if boundary_context else "needs_review",
                        "excerpt": _excerpt(line),
                    }
                )
    return hits


def _iter_scan_files(base: Path) -> Iterable[Path]:
    for rel_dir in SCAN_DIRS:
        root = base / rel_dir
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SCAN_SUFFIXES and not _is_generated_or_cache_path(path):
                yield path


def _is_generated_or_cache_path(path: Path) -> bool:
    normalized = path.as_posix().lower()
    if normalized.endswith("/cas_forex/professional_claims.py"):
        return True
    return any(part in normalized for part in ("/__pycache__/", "/node_modules/", "/dist/", "/build/"))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _is_boundary_context(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in BOUNDARY_CONTEXT_MARKERS)


def _excerpt(line: str, limit: int = 220) -> str:
    text = " ".join(line.strip().split())
    return text if len(text) <= limit else f"{text[: limit - 3]}..."
