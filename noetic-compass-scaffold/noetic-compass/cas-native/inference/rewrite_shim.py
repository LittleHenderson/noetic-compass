"""Free-form English -> training-surface CAS prompt shim.

The CAS-Native K=9 baseline was trained on prompts of the form

    "Turn this formal natural-language CAS reading into the exact expression:
     families: state expression; states: Noetic ^3; domain E (evaluative);
     drive F2; register |f (felt)."

When users type plain colloquial English, the model lacks that surface
distribution and collapses to the most-populated prior (``meta_logic``). This
shim does heuristic axis detection -- driven by the canonical Noetic
colloquialism map in ``CLAUDE.md`` -- and rewrites free-form text into the
training surface so the existing predictor sees something it recognises.

Path A (rule-based, stdlib-only) is implemented here. Path B (Claude API
fallback) is intentionally not enabled by default; the rule-based detector
covers the high-traffic colloquialisms that drive most of the v0 chat demo.

Anti-drift guards (per ``CLAUDE.md`` Clarification 6):
- ``^3`` Negative is VISCERAL, not analytical. Audit/scrutinize/critique-style
  phrasing routes to ``^6`` Male, not ``^3``.
- ``^8`` Above/Cause is associative TRIGGERING, not deductive reasoning. Words
  like ``therefore`` / ``deduce`` / ``follows that`` are NOT ``^8``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


NoeticCode = str   # one of "0".."9"
DomainCode = str   # "P" | "C" | "E" | "O"
DriveCode = str    # "F1".."F7"
RegisterCode = str  # "T" | "A" | "f" | "E"


DOMAIN_NAMES: dict[DomainCode, str] = {
    "P": "principled",
    "C": "cognitive",
    "E": "evaluative",
    "O": "operational",
}

REGISTER_NAMES: dict[RegisterCode, str] = {
    "T": "transcendent",
    "A": "analytical",
    "f": "felt",
    "E": "embodied",
}


# Each entry is (compiled_regex, weight). Weights let us combine evidence and
# rank Noetics when several patterns fire on the same input. Patterns are kept
# colloquial-first so they map back to the canonical CLAUDE.md colloquialism map.
_NOETIC_PATTERNS: dict[NoeticCode, list[tuple[re.Pattern[str], float]]] = {
    "0": [  # Idea -- "It's all in your head"
        (re.compile(r"\b(idea|concept|notion|thought)\b", re.I), 0.4),
        (re.compile(r"all in (your|my|their|his|her) head", re.I), 1.0),
    ],
    "1": [  # Mind -- "paying attention", "making up your mind"
        (re.compile(r"paying attention|focus(?:ing|ed)? on|making up (?:my|your|their) mind", re.I), 1.0),
        (re.compile(r"\b(awareness|attention|attending to)\b", re.I), 0.6),
        (re.compile(r"using (?:my|your|their) head", re.I), 0.7),
    ],
    "2": [  # Positive -- attraction, affinity
        (re.compile(r"\bcan'?t resist\b|\bdrawn to\b|moth to (?:a |the )?flame", re.I), 1.2),
        (re.compile(r"\b(love|adore|crave|enjoy|fond of)\b", re.I), 0.9),
        (re.compile(r"speaks to me|right up my alley|attracted to", re.I), 1.0),
    ],
    "3": [  # Negative -- VISCERAL aversion (NOT analytical critique)
        (re.compile(r"can'?t stand|can'?t stomach|rubs? (?:me|us) (?:the )?wrong way", re.I), 1.3),
        (re.compile(r"wouldn'?t touch (?:it|that) with a (?:ten[- ]?foot|10[- ]?foot) pole", re.I), 1.3),
        (re.compile(r"\b(hate|loathe|despise|disgust|repuls|revolt)", re.I), 1.0),
        (re.compile(r"makes? (?:me|us) sick|turn(?:s|ed) (?:my|our) stomach", re.I), 1.1),
        (re.compile(r"\b(?:annoy|irritate|bother)", re.I), 0.7),
    ],
    "4": [  # Vibration -- resonance, impression
        (re.compile(r"struck a chord|hit me hard|resonate[ds]?|made an impression", re.I), 1.2),
        (re.compile(r"\b(vibe|vibration|impression|reverbera)", re.I), 0.7),
        (re.compile(r"left (?:its|an) (?:mark|impression)", re.I), 0.9),
    ],
    "5": [  # Female -- Mind composed of accumulated experience / identity
        (re.compile(r"sum of (?:my|our|your|their) experiences?", re.I), 1.3),
        (re.compile(r"\bwho I am\b|part of what makes (?:me|us) me|makes me who I am", re.I), 1.2),
        (re.compile(r"shaped by years|years of (?:writing|doing|practicing|working)", re.I), 1.0),
        (re.compile(r"\b(identity|expertise|background|upbringing|formation|trauma|cultural)\b", re.I), 0.5),
    ],
    "6": [  # Male -- decomposition / unpacking / break-down
        # "break X down" where X may be 0-3 intervening words (this/that/it/the
        # argument/idea/claim/...). Also matches the bare "break it down" idiom.
        (re.compile(r"break(?:ing)?(?:\s+\w+){1,4}\s+down\b", re.I), 1.2),
        (re.compile(r"\bunpack(?:ing)?\b", re.I), 1.0),
        (re.compile(r"pull(?:ing)? apart|tak(?:e|ing) apart|looking at what'?s underneath", re.I), 1.0),
        (re.compile(r"\b(analy[sz]e|decompose|dissect|scrutiniz|audit|critique|examine carefully)", re.I), 0.9),
        (re.compile(r"\b(deduce|deduction|therefore|it follows that|infer)", re.I), 0.7),
    ],
    "7": [  # Rhythm -- repetition / practice / entrainment
        (re.compile(r"practice makes perfect|muscle memory|in (?:a|the) groove", re.I), 1.2),
        (re.compile(r"keep (?:practicing|doing|repeating)|every day|daily routine", re.I), 1.0),
        (re.compile(r"\b(repeat|repetition|habit|routine|drill|rehears)", re.I), 0.8),
        (re.compile(r"you are what you repeatedly do", re.I), 1.3),
    ],
    "8": [  # Above/Cause -- associative TRIGGERING (NOT deductive)
        (re.compile(r"that reminds me|reminds me of|made me think of", re.I), 1.3),
        (re.compile(r"one thing led to another|triggered (?:a memory|the thought)", re.I), 1.1),
        (re.compile(r"\btrigger(?:ed|s)?\b", re.I), 0.7),
    ],
    "9": [  # Below/Effect -- the idea that lands
        (re.compile(r"popped into (?:my|your|their) head|out of nowhere I thought", re.I), 1.2),
        (re.compile(r"the thought came to me|it just clicked|came to mind", re.I), 1.1),
        (re.compile(r"\b(realiz|epiphan|dawned on)", re.I), 0.7),
    ],
}


_DOMAIN_PATTERNS: dict[DomainCode, list[tuple[re.Pattern[str], float]]] = {
    "P": [
        # "just" the adverb is too noisy as a P signal; require "justice" as noun
        (re.compile(r"\b(should|ought|ethic(?:s|al)?|moral(?:s|ity)?|principle|justice)\b", re.I), 1.0),
        (re.compile(r"\b(duty|obligation|virtue|fair(?:ness)?|right or wrong)\b", re.I), 0.8),
    ],
    "C": [
        (re.compile(r"\b(think|understand|reason|consider|figure out|comprehend|idea|knowledge)\b", re.I), 0.9),
        (re.compile(r"\b(analy[sz]e|deduce|infer|conceptual|cognit)\b", re.I), 0.8),
    ],
    "E": [
        (re.compile(r"\b(feel|feeling|love|hate|like|dislike|prefer)\b", re.I), 1.0),
        (re.compile(r"\b(good|bad|beautiful|ugly|pleasant|awful|nice|gross)\b", re.I), 0.9),
        (re.compile(r"how I feel about|feel about", re.I), 1.1),
    ],
    "O": [
        (re.compile(r"\b(do|make|build|perform|execute|practice|run|act)\b", re.I), 0.8),
        (re.compile(r"\b(action|behaviour|behavior|task|step|workflow)\b", re.I), 0.9),
    ],
}


_REGISTER_PATTERNS: dict[RegisterCode, list[tuple[re.Pattern[str], float]]] = {
    "T": [
        (re.compile(r"\b(vision|calling|meaning|purpose|big picture|spiritual|transcend|holistic)\b", re.I), 1.0),
    ],
    "A": [
        (re.compile(r"\b(think|reason|logic|deduce|analy[sz]e|step by step|chain of thought)\b", re.I), 1.0),
    ],
    "f": [
        (re.compile(r"\b(feel|feeling|emotion|gut|heart|love|hate|visceral|stomach|sick)\b", re.I), 1.0),
        (re.compile(r"\b(can'?t stand|can'?t stomach|rub|moved|touched)\b", re.I), 0.8),
    ],
    "E": [
        (re.compile(r"\b(body|bodily|kinesthetic|sensor|hand|foot|breath|posture|gesture|movement)\b", re.I), 1.0),
        (re.compile(r"\b(practic(?:e|ing)|drill|rehears|muscle memory|train(?:ing)?)\b", re.I), 0.7),
        (re.compile(r"morning light|sound|smell|taste|touch", re.I), 0.6),
    ],
}


_DRIVE_PATTERNS: dict[DriveCode, list[tuple[re.Pattern[str], float]]] = {
    "F1": [  # Unity
        (re.compile(r"\b(togetherness|unity|wholeness|belong|one with|integrated)\b", re.I), 1.0),
    ],
    "F2": [  # Wisdom
        (re.compile(r"\b(wisdom|understand|insight|learn|knowledge|truth)\b", re.I), 0.9),
    ],
    "F3": [  # Vitality
        (re.compile(r"\b(vital|energy|alive|vigor|liveliness|spark)\b", re.I), 1.0),
    ],
    "F4": [  # Connection
        (re.compile(r"\b(connect|relationship|friend|love|bond|attachment|intimacy)\b", re.I), 1.0),
        (re.compile(r"\b(people|interrupt|with me|with us|company)\b", re.I), 0.4),
    ],
    "F5": [  # Agency
        (re.compile(r"\b(agency|control|autonomy|power|do|act|choice|decide)\b", re.I), 0.8),
    ],
    "F6": [  # Structure
        (re.compile(r"\b(structure|order|system|rule|procedure|framework|discipline)\b", re.I), 1.0),
        (re.compile(r"\b(scale|practice|every day|routine)\b", re.I), 0.6),
    ],
    "F7": [  # Purpose
        (re.compile(r"\b(purpose|goal|mission|aim|destiny|why)\b", re.I), 0.9),
    ],
}


# Minimum total weight on the Noetic axis below which we consider the input
# unstructured ("no signal") and pass the original text through.
_NOETIC_SIGNAL_FLOOR = 0.6


@dataclass
class CASSignal:
    """Detected axes plus per-axis confidence scores in [0, 1]."""

    noetic: Optional[NoeticCode] = None
    noetic_confidence: float = 0.0
    domain: Optional[DomainCode] = None
    domain_confidence: float = 0.0
    drive: Optional[DriveCode] = None
    drive_confidence: float = 0.0
    register: Optional[RegisterCode] = None
    register_confidence: float = 0.0
    has_signal: bool = False
    raw_scores: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "noetic": self.noetic,
            "noetic_confidence": round(self.noetic_confidence, 3),
            "domain": self.domain,
            "domain_confidence": round(self.domain_confidence, 3),
            "drive": self.drive,
            "drive_confidence": round(self.drive_confidence, 3),
            "register": self.register,
            "register_confidence": round(self.register_confidence, 3),
            "has_signal": self.has_signal,
        }


def _score_axis(
    text: str,
    patterns: dict[str, list[tuple[re.Pattern[str], float]]],
) -> dict[str, float]:
    raw: dict[str, float] = {}
    for code, items in patterns.items():
        total = 0.0
        for rx, weight in items:
            if rx.search(text):
                total += weight
        if total > 0:
            raw[code] = total
    return raw


def _normalise(scores: dict[str, float]) -> tuple[Optional[str], float, dict[str, float]]:
    if not scores:
        return None, 0.0, {}
    total = sum(scores.values())
    normalised = {k: v / total for k, v in scores.items()}
    best = max(normalised.items(), key=lambda kv: kv[1])
    return best[0], best[1], normalised


def _apply_anti_drift(text: str, noetic_scores: dict[str, float]) -> dict[str, float]:
    """Enforce CLAUDE.md anti-drift annotations.

    1. ``^3`` Negative is visceral, not analytical. If ``^3`` is the leader but
       the language is dominated by audit/scrutinise/critique vocabulary, push
       the weight onto ``^6`` Male.
    2. ``^8`` Above/Cause is associative triggering, not deductive reasoning.
       If ``^8`` is the leader but the language is overtly deductive
       (``therefore``, ``it follows that``, ``deduce``), redirect the weight
       onto ``^6`` Male (decomposition step) -- ``^9`` Below/Effect is the
       landing step but cannot be inferred from the surface form alone.
    """
    adjusted = dict(noetic_scores)

    audit_rx = re.compile(
        r"\b(audit|scrutiniz|critique|fault[- ]find|find flaws?|pick apart"
        r"|tear apart|nitpick|fact[- ]check)\b",
        re.I,
    )
    deductive_rx = re.compile(
        r"\b(therefore|thus|hence|it follows that|deduce|deduction|q\.?e\.?d\.?"
        r"|ergo|consequently)\b",
        re.I,
    )

    if adjusted and max(adjusted, key=adjusted.get) == "3" and audit_rx.search(text):
        moved = adjusted.pop("3", 0.0)
        adjusted["6"] = adjusted.get("6", 0.0) + moved
    if adjusted and max(adjusted, key=adjusted.get) == "8" and deductive_rx.search(text):
        moved = adjusted.pop("8", 0.0)
        adjusted["6"] = adjusted.get("6", 0.0) + moved

    return adjusted


def detect_cas_signal(free_form_text: str) -> dict:
    """Return detected CAS axes + confidence scores for ``free_form_text``.

    The result is a plain ``dict`` (not the dataclass) so callers can use it
    directly without needing to import ``CASSignal``.
    """
    text = (free_form_text or "").strip()
    if not text:
        return CASSignal().to_dict()

    noetic_scores = _score_axis(text, _NOETIC_PATTERNS)
    noetic_total = sum(noetic_scores.values())
    noetic_scores = _apply_anti_drift(text, noetic_scores)

    domain_scores = _score_axis(text, _DOMAIN_PATTERNS)
    drive_scores = _score_axis(text, _DRIVE_PATTERNS)
    register_scores = _score_axis(text, _REGISTER_PATTERNS)

    noetic, noetic_conf, _ = _normalise(noetic_scores)
    domain, domain_conf, _ = _normalise(domain_scores)
    drive, drive_conf, _ = _normalise(drive_scores)
    register, register_conf, _ = _normalise(register_scores)

    has_signal = noetic is not None and noetic_total >= _NOETIC_SIGNAL_FLOOR

    sig = CASSignal(
        noetic=noetic if has_signal else None,
        noetic_confidence=noetic_conf if has_signal else 0.0,
        domain=domain,
        domain_confidence=domain_conf,
        drive=drive,
        drive_confidence=drive_conf,
        register=register,
        register_confidence=register_conf,
        has_signal=has_signal,
        raw_scores={
            "noetic": noetic_scores,
            "domain": domain_scores,
            "drive": drive_scores,
            "register": register_scores,
        },
    )
    return sig.to_dict()


def _format_training_surface(
    noetic: NoeticCode,
    domain: Optional[DomainCode],
    drive: Optional[DriveCode],
    register: Optional[RegisterCode],
) -> str:
    """Render axes in the exact training-surface template.

    Mirrors the ``v75_register`` and ``v74_baseline`` prompts from the K=9
    training corpus (e.g. ``runs/.../samples.jsonl``):

        "Turn this formal natural-language CAS reading into the exact
         expression: families: state expression; states: Noetic ^3;
         domain E (evaluative); drive F2; register |f (felt)."

    Domain, drive, and register are only emitted when present.
    """
    parts: list[str] = [f"Noetic ^{noetic}"]
    if domain is not None:
        parts.append(f"domain {domain} ({DOMAIN_NAMES[domain]})")
    if drive is not None:
        parts.append(f"drive {drive}")
    if register is not None:
        parts.append(f"register |{register} ({REGISTER_NAMES[register]})")

    state_block = "; ".join(parts)
    return (
        "Turn this formal natural-language CAS reading into the exact "
        f"expression: families: state expression; states: {state_block}."
    )


def rewrite_to_training_surface(free_form_text: str) -> str:
    """Rewrite free-form English into the K=9 training-surface CAS template.

    If no clear CAS structure is detected (per ``detect_cas_signal``), returns
    the original text unchanged so the predictor still sees something
    meaningful -- it will collapse to its prior, but we don't fabricate axes.
    """
    signal = detect_cas_signal(free_form_text)
    if not signal["has_signal"]:
        return free_form_text

    return _format_training_surface(
        noetic=signal["noetic"],
        domain=signal["domain"],
        drive=signal["drive"],
        register=signal["register"],
    )


if __name__ == "__main__":
    test_inputs = [
        "I can't stand it when people interrupt me",
        "I love the way the morning light comes through",
        "I keep practicing the same scale every day",
        "That song struck a chord with me",
        "It just popped into my head",
        "My professional expertise is shaped by years of writing code",
        "I think we should break this argument down",
        "lol idk just hi",
    ]
    for t in test_inputs:
        signal = detect_cas_signal(t)
        rewrite = rewrite_to_training_surface(t)
        print(f"INPUT:    {t}")
        print(f"  signal: {signal}")
        print(f"  rewrite:{rewrite}")
        print()
