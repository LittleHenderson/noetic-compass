"""Fast text-to-CAS-signal analyzer for real-time notation synthesis.

Scans raw input text for linguistic patterns that map to CAS ontology
components (operators, domains, drives) and produces scores without
needing an LLM call.  Designed to run in <50ms so it can keep up with
typing in the UI.

The output feeds directly into ``notation_synthesizer.synthesize_notation``
to produce a compiler-validated CAS expression.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Operator signal patterns (CO-0 through CO-9)
#
# Each list contains lowercased keywords/phrases that indicate the text
# is exercising that cognitive operator.
# ---------------------------------------------------------------------------

OPERATOR_SIGNALS: list[list[str]] = [
    # CO-0: Generative Potential / Identity
    [
        "identit", "self", "who am i", "fundament", "core", "essenc",
        "authenti", "genuine", "inherent", "innate", "origin", "nature",
        "trust", "character", "person", "being", "soul", "individ",
        "worth", "dignit", "reput", "credib", "reliab", "depend",
        "integrit", "honest", "sincer", "transparen", "true self",
    ],
    # CO-1: Directed Attention / Reflection
    [
        "reflect", "consider", "examin", "analy", "attention", "focus",
        "contemplat", "introspect", "deliberat", "think about", "ponder",
        "careful", "scrutin", "assess", "evaluat", "review",
        "question", "wonder", "how do", "whether", "weigh",
        "look back", "reconsider", "re-evaluat", "think through",
        "mindful", "aware", "notic", "observ", "recogniz",
    ],
    # CO-2: Attraction / Affinity
    [
        "prefer", "attract", "drawn to", "affinity", "favor",
        "inclin", "gravitat", "appreciat", "valu", "resonat", "benefit",
        "love", "care", "cherish", "treasure", "fond", "dear",
        "friend", "companion", "close", "bond", "connect",
        "reconcil", "restore", "reunite", "repair", "rebuild",
        "forgiv", "accept", "embrac", "welcome", "warmth",
        "loyal", "devot", "commit", "dedic",
    ],
    # CO-3: Aversion / Critical Evaluation
    [
        "reject", "wrong", "harm", "unethic", "immoral", "danger",
        "risk", "concern", "problem", "inappropriat", "violat",
        "refus", "cannot", "shouldn't", "must not", "forbidden",
        "illegal", "consent", "boundar", "exploit", "ethic",
        "privat", "privac", "safe", "protect", "abus",
        "betray", "deceiv", "manipulat", "toxic", "distrust",
        "suspicio", "skeptic", "doubt", "wary", "cautio",
        "wound", "hurt", "damag", "break", "destruct",
        "negat", "avoid", "withdraw", "separat", "distanc",
        "vulnerab", "threat", "fear", "anxiet",
    ],
    # CO-4: Encoding Intensity
    [
        "must", "critical", "essential", "paramount", "vital", "urgent",
        "imperat", "absolut", "intens", "crucial", "non-negotiable",
        "important", "serious", "significant", "profound", "deep",
        "drastic", "overwhelm", "extraordinar", "remarkab",
        "tremendou", "immens", "pivotal", "monumental",
        "drastical", "fundament", "life-chang", "transform",
    ],
    # CO-5: Receptive Integration / Framing
    [
        "perspectiv", "understand", "context", "frame", "interpret",
        "integrat", "nuanc", "complex", "viewpoint", "lens",
        "holistic", "comprehen", "grasp", "discern", "consider",
        "empathi", "see their", "put yourself", "walk in",
        "both sides", "on the other hand", "however", "although",
        "balanc", "reconcil", "bridg", "synthesi", "merg",
        "appreciat", "acknowledg", "recogniz", "accept",
    ],
    # CO-6: Projective Assertion
    [
        "assert", "claim", "declar", "project", "state", "believ",
        "convinc", "argu", "advocat", "insist", "maintain", "contend",
        "say", "opinion", "justif", "propos", "suggest",
        "recommend", "advis", "urge", "express", "communicat",
        "tell", "explain", "articulat", "voice", "speak",
        "demand", "expect", "requir",
    ],
    # CO-7: Pattern Entrainment
    [
        "pattern", "always", "never", "tradition", "norm", "custom",
        "routine", "habitual", "consistent", "expect", "precedent",
        "convention", "standard", "typical", "usual",
        "history", "past", "before", "previous", "last time",
        "track record", "tend to", "habit", "cycle", "repeat",
        "over time", "years", "months", "long term", "duration",
    ],
    # CO-8: Causal Initiation
    [
        "caus", "creat", "initiat", "start", "begin", "launch",
        "trigger", "produc", "generat", "implement", "act",
        "take action", "execut", "build", "develop", "write",
        "make", "do", "help", "chang", "transform", "reform",
        "seek", "pursu", "attempt", "strive", "endeavor",
        "restor", "renew", "reviv", "reestablish",
        "decid", "choos", "resolv", "determin",
    ],
    # CO-9: Consequential Grounding
    [
        "consequen", "result", "outcome", "effect", "impact",
        "implicat", "ramificat", "repercuss", "therefore",
        "thus", "hence", "follow", "lead to", "outweigh",
        "what happen", "what if", "long-term", "aftermath",
        "price", "cost", "worth it", "trade-off", "sacrifice",
        "lesson", "learn from", "grow from", "experienc",
        "moving forward", "going forward", "future",
    ],
]

# ---------------------------------------------------------------------------
# Domain signal patterns
# ---------------------------------------------------------------------------

DOMAIN_SIGNALS: dict[str, list[str]] = {
    "P": [  # Principled
        "ethic", "moral", "right", "principl", "justice", "duty",
        "obligat", "virtue", "dignit", "fair", "integrit",
        "law", "legal", "regulat", "rights", "consent", "honest",
        "privac", "privat", "permiss", "acceptable",
        "trust", "loyal", "betray", "forgiv", "redempt",
        "accountab", "responsib", "honor", "respect", "decen",
        "conscienc", "guilt", "shame", "remorse", "atone",
        "sincer", "genuine", "authenti", "transparen",
        "should", "ought", "wrong", "vow", "promis", "oath",
    ],
    "C": [  # Cognitive
        "think", "reason", "logic", "analy", "knowledge", "understand",
        "cognitive", "rational", "evidence", "hypothes", "theory",
        "deduc", "induc", "infer", "argument", "premis",
        "research", "study", "paper", "data",
        "evaluat", "assess", "question", "whether", "how",
        "recogniz", "discern", "distinguis", "identif", "diagnos",
        "reflect", "consider", "ponder", "deliberat",
        "learn", "realiz", "discover", "observ",
    ],
    "E": [  # Evaluative
        "judg", "assess", "evaluat", "worth", "quality", "merit",
        "weigh", "compar", "rank", "priorit", "trade-off", "tradeoff",
        "cost-benefit", "pros and cons", "better", "worse",
        "outweigh", "justif", "benefit",
        "whether", "decid", "choos", "dilemma", "torn",
        "significan", "import", "matter", "meaningful",
        "deserv", "earn", "warran", "measur", "gaug",
        "trustworth", "credib", "reliab", "genuine",
    ],
    "O": [  # Operational
        "plan", "procedure", "step", "implement", "execut", "process",
        "workflow", "method", "protocol", "practical", "operational",
        "action", "task", "deploy", "schedul", "write", "help", "share",
        "restor", "rebuild", "repair", "reconcil", "heal",
        "approach", "strateg", "tactic", "path", "way forward",
        "gradual", "slow", "careful", "incrementa",
        "boundar", "condition", "rule", "guidelin",
    ],
}

# ---------------------------------------------------------------------------
# Drive signal patterns (F1–F7)
# ---------------------------------------------------------------------------

DRIVE_SIGNALS: list[list[str]] = [
    # F1: Unity
    [
        "unity", "whole", "integrat", "coher", "harmon", "unifi", "oneness", "complete",
        "reconcil", "heal", "mend", "togeth", "peac", "resolv", "restor",
        "intact", "undivid", "consolidat",
    ],
    # F2: Wisdom
    [
        "wisdom", "knowledge", "insight", "learning", "discern", "enlighten", "underst",
        "lesson", "experienc", "matur", "grow", "perspectiv", "reflect",
        "judg", "prudent", "thoughtful", "wise",
    ],
    # F3: Vitality
    [
        "vital", "energy", "health", "wellbeing", "life", "vigor", "flourish", "thrive",
        "emoti", "feel", "passion", "alive", "resilient", "strength",
        "recover", "surviv", "endur", "persist",
    ],
    # F4: Connection
    [
        "connect", "relationship", "empathy", "bond", "community", "together", "social", "collaborat",
        "friend", "companion", "trust", "loyal", "intimac", "closeness",
        "belong", "attach", "care", "love", "affection", "mutual",
        "reconcil", "reunion", "kinship",
    ],
    # F5: Agency
    [
        "agency", "autonomy", "choice", "freedom", "control", "self-determin", "independen", "power",
        "decid", "choos", "boundar", "assert", "stand", "voice",
        "refus", "allow", "permit", "own terms", "empower",
    ],
    # F6: Structure
    [
        "structure", "order", "organiz", "system", "framework", "hierarch", "classif", "categor",
        "boundar", "rule", "condition", "criteria", "process", "method",
        "clear", "defin", "establish", "protocol", "guidelin",
    ],
    # F7: Purpose
    [
        "purpose", "meaning", "goal", "mission", "direction", "intent", "aspir", "vision",
        "why", "reason", "motiv", "aim", "object", "calling",
        "worth", "significan", "matter", "fulfil",
    ],
]

# RPM chain language
RPM_SIGNALS = [
    "prerequisite", "before", "foundation", "build upon", "require",
    "depend", "chain", "sequence", "step by step", "progression",
    "first", "then", "after", "once", "in order to",
    "gradual", "incremental", "phase", "stage",
]


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class TextSignals:
    """Raw CAS signal strengths extracted from text."""
    operator_scores: list[float] = field(default_factory=lambda: [0.0] * 10)
    domain_scores: list[float] = field(default_factory=lambda: [0.0] * 4)
    drive_scores: list[float] = field(default_factory=lambda: [0.0] * 7)
    rpm_signal: float = 0.0
    word_count: int = 0


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------

def _count_signal_hits(text_lower: str, patterns: list[str]) -> int:
    """Count how many pattern strings appear in the text."""
    return sum(1 for p in patterns if p in text_lower)


def analyze_text_signals(text: str) -> TextSignals:
    """Extract CAS signal strengths from raw text.

    Runs in O(n * p) where n=text length, p=total patterns.
    Designed for <50ms on typical prompt-length text.
    """
    if not text or not text.strip():
        return TextSignals()

    lower = text.lower()
    word_count = len(text.split())

    # Scale factor: normalize signal density by text length
    # Short text (< 20 words) gets boosted, long text (> 200 words) gets damped
    length_factor = min(2.0, max(0.5, 50.0 / max(word_count, 1)))

    # Operator scores (0-10 scale for compatibility with synthesizer)
    op_scores = []
    for patterns in OPERATOR_SIGNALS:
        hits = _count_signal_hits(lower, patterns)
        # Scale: each hit adds ~3.0 points, cap at 10
        score = min(10.0, hits * 3.0 * length_factor)
        op_scores.append(round(score, 2))

    # Domain scores (0-1 scale)
    domain_codes = ["P", "C", "E", "O"]
    dom_scores = []
    for code in domain_codes:
        hits = _count_signal_hits(lower, DOMAIN_SIGNALS[code])
        score = min(1.0, hits * 0.2 * length_factor)
        dom_scores.append(round(score, 4))

    # Drive scores (0-1 scale, as chain [D, W, P] format for synthesizer)
    drv_scores = []
    for patterns in DRIVE_SIGNALS:
        hits = _count_signal_hits(lower, patterns)
        score = min(1.0, hits * 0.25 * length_factor)
        drv_scores.append(round(score, 4))

    # RPM signal
    rpm_hits = _count_signal_hits(lower, RPM_SIGNALS)
    rpm_signal = min(1.0, rpm_hits * 0.25 * length_factor)

    return TextSignals(
        operator_scores=op_scores,
        domain_scores=dom_scores,
        drive_scores=drv_scores,
        rpm_signal=round(rpm_signal, 4),
        word_count=word_count,
    )
