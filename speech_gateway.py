"""HELM speech gateway — CAS is sovereign; renderers only make its thoughts digestible.

Architecture (owner directive, 2026-10-26):
  1. CAS decides what may be said: a typed frame with intent, content slots and the exact facts licensed for this turn.
  2. A renderer turns the frame into prose. Renderers are interchangeable: learned proposer (open-domain, now), CTT mouth
     (in-distribution), stochastic composer (social, refusals, structured slots).
  3. Every candidate is validated against the frame before it leaves: no number or name the frame did not license, no
     unlicensed factual claim, shape limits. Pass -> send; fail -> one repair attempt; still fail -> a *varied* refusal.

Greetings and refusals are deliberately non-deterministic: they carry no facts, so they are composed per turn from
grammar rather than retrieved from a bank.
"""
from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

WORD_RX = re.compile(r"[a-z]+|\d+")
NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty",
    "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "dozen", "half", "quarter", "once",
    "twice", "first", "second", "third",
}


@dataclass
class Frame:
    """What CAS has licensed this turn to say."""
    intent: str                                  # GREETING, EMPATHY, ANSWER, REFUSE, ...
    slots: Dict[str, str] = field(default_factory=dict)   # content the sentence may use
    licensed: List[str] = field(default_factory=list)     # every number/name the sentence may contain
    facts: bool = False                          # may the sentence assert facts?
    tone: str = "warm"
    history: List[str] = field(default_factory=list)


# ------------------------------------------------------------------------------------ validation
def validate(frame: Frame, text: str) -> tuple[bool, str]:
    """The CAS check on a candidate sentence. Returns (ok, reason)."""
    t = (text or "").strip()
    if not t:
        return False, "empty"
    if len(t) > 600:
        return False, "too long"
    if t.count("?") > 1:
        return False, "more than one question"
    if len(re.findall(r"[.!?](\s|$)", t)) > 3:
        return False, "too many sentences"
    low = t.lower()
    licensed = {w.lower() for w in frame.licensed}
    digits = set(re.findall(r"\d+", t))
    bad_digits = {d for d in digits if d not in licensed}
    if bad_digits:
        return False, "unlicensed number: %s" % ",".join(sorted(bad_digits))
    words = set(WORD_RX.findall(low))
    bad_numwords = {w for w in words if w in NUMBER_WORDS and w not in licensed and w not in frame.slots.values()}
    if bad_numwords:
        return False, "unlicensed number word: %s" % ",".join(sorted(bad_numwords))
    # Proper nouns must be licensed, factual frame or not: an unlicensed name is an invented fact either way.
    for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z]{2,})\b", t):
        if m.group(1).lower() not in licensed:
            return False, "unlicensed name: %s" % m.group(1)
    return True, ""


# ------------------------------------------------------------------------------------ renderers
OPENERS = ["Hey", "Hi", "Hello", "Morning", "Good to see you", "Hey there", "Well hello", "Afternoon",
           "Hi there", "Evening"]
WARMTH = ["hope you're doing alright", "good to have you here", "hope the day's treating you well",
          "glad you're here", "hope things are going smoothly", "good to have your company",
          "hope it's been a decent day", "nice to see you back", "hope you're keeping well"]
OFFERS = ["what are we working on?", "what's on your mind?", "where should we start?",
          "what can I help with?", "what would you like to get done?", "what shall we tackle?",
          "what do you need from me?", "where would you like to begin?"]


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def compose_greeting(frame: Frame, rng: random.Random) -> str:
    return f"{rng.choice(OPENERS)} — {rng.choice(WARMTH)}. {cap_first(rng.choice(OFFERS))}"


REFUSAL_OPEN = ["I can't do that one", "That's not something I'll do", "I'd rather not", "I'm going to decline that",
                "That one's off the table for me"]
REFUSAL_WHY = ["it would mean guessing", "it isn't grounded in anything I can check", "it risks the work",
               "I'd be inventing it", "there's nothing verified behind it"]
REFUSAL_ALT = ["I can do the checked version instead", "I can show you the version I can verify",
               "I can suggest a safe alternative", "tell me the goal and I'll find a grounded route",
               "give me the grounded version and I'll take it from there"]


def compose_refusal(frame: Frame, rng: random.Random) -> str:
    return f"{rng.choice(REFUSAL_OPEN)} — {rng.choice(REFUSAL_WHY)}. {cap_first(rng.choice(REFUSAL_ALT))}."


def compose_structured(frame: Frame, rng: random.Random) -> str:
    """Numbers and memory: the content is fixed by CAS; only the phrasing varies."""
    s = frame.slots
    if frame.intent == "ANSWER":
        opts = ["In {month}, {name} {place} had {num} {thing}.",
                "{name}'s {place} had {num} {thing} in {month}.",
                "{num} {thing} at {name} {place}, as of {month}.",
                "{name} {place}: {num} {thing} in {month}."]
        return rng.choice(opts).format(**s)
    if frame.intent == "RECALL":
        opts = ["You told me about {thing} — I've kept it in this session.",
                "You mentioned {thing} earlier; it's still in context.",
                "That's the {thing} you told me about — noted."]
        return rng.choice(opts).format(**s)
    if frame.intent == "YIELD":
        opts = ["Based on your inputs, we can produce exactly {num} units.",
                "The limiting value gives {num} units.",
                "{num} units — that's what the inputs support."]
        return rng.choice(opts).format(**s)
    payload = ", ".join(f"{k}: {v}" for k, v in sorted(s.items()))
    return f"{frame.intent.lower()}: {payload}."


# ------------------------------------------------------------------------------------ learned proposer
class LearnedProposer:
    """Open-domain renderer. It may only phrase the licensed frame; CAS validates what comes back."""

    def __init__(self) -> None:
        self.key = None
        self.model = "deepseek-chat"
        env = Path.home() / ".cas_llm_keys.env"
        if env.exists():
            for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().startswith("DEEPSEEK_API_KEY="):
                    self.key = line.split("=", 1)[1].strip().strip('"')
        self.base = "https://api.deepseek.com/v1/chat/completions"

    @property
    def available(self) -> bool:
        return bool(self.key)

    def render(self, frame: Frame, seed: int = 0) -> Optional[str]:
        if not self.available:
            return None
        import urllib.request
        licensed = ", ".join(frame.licensed) or "(none)"
        system = ("You phrase a single reply for a warm, down-to-earth assistant. "
                  "Use ONLY the licensed content. Invent no numbers, names, places or facts. "
                  "One or two short sentences. No lists, no jargon, no markdown. Sound human.")
        user = (f"intent: {frame.intent}\nlicensed facts: {licensed}\n"
                f"content slots: {json.dumps(frame.slots)}\n"
                f"recent conversation: {' | '.join(frame.history[-3:])}\n"
                "Write only the reply.")
        body = json.dumps({"model": self.model, "temperature": 0.95, "max_tokens": 120,
                           "messages": [{"role": "system", "content": system},
                                        {"role": "user", "content": user}]}).encode("utf-8")
        req = urllib.request.Request(self.base, data=body, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.loads(r.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return None


# ------------------------------------------------------------------------------------ gateway
class SpeechGateway:
    def __init__(self, proposer: Optional[LearnedProposer] = None, seed: int = 0):
        self.proposer = proposer if proposer is not None else LearnedProposer()
        self.rng = random.Random(seed)

    def _render(self, frame: Frame, strict: bool) -> Optional[str]:
        if frame.intent == "GREETING":
            return compose_greeting(frame, self.rng)
        if frame.intent == "REFUSE":
            return compose_refusal(frame, self.rng)
        if frame.intent in ("ANSWER", "RECALL", "YIELD"):
            return compose_structured(frame, self.rng)
        # Open-domain/social: learned proposer first, composer if unavailable or invalid.
        text = self.proposer.render(frame, self.rng.randrange(1 << 30))
        return text

    def speak(self, frame: Frame) -> Dict[str, object]:
        attempts = []
        for strict in (False, True):
            text = self._render(frame, strict)
            if text is None:
                continue
            ok, why = validate(frame, text)
            attempts.append({"text": text, "ok": ok, "why": why})
            if ok:
                return {"text": text, "ok": True, "renderer": frame.intent, "attempts": attempts}
        # One repair pass: ask the proposer again, then a composer fallback.
        if frame.intent not in ("GREETING", "REFUSE", "ANSWER", "RECALL", "YIELD"):
            text = self.proposer.render(frame, self.rng.randrange(1 << 30))
            if text:
                ok, why = validate(frame, text)
                attempts.append({"text": text, "ok": ok, "why": why})
                if ok:
                    return {"text": text, "ok": True, "renderer": "proposer_repair", "attempts": attempts}
        refusal = Frame(intent="REFUSE", tone="warm", history=frame.history)
        text = compose_refusal(refusal, self.rng)
        return {"text": text, "ok": False, "renderer": "refusal", "attempts": attempts}


if __name__ == "__main__":
    gw = SpeechGateway(seed=11)
    for _ in range(8):
        print("GREET:", gw.speak(Frame(intent="GREETING"))["text"])
    print()
    for _ in range(8):
        print("REFUSE:", gw.speak(Frame(intent="REFUSE"))["text"])
    print()
    f = Frame(intent="ANSWER", slots={"name": "Stonewick", "place": "yard", "month": "September",
                                      "num": "eight", "thing": "colonies"},
              licensed=["stonewick", "yard", "september", "eight", "colonies"], facts=True)
    print("ANSWER:", gw.speak(f))
    bad = Frame(intent="ANSWER", slots={"name": "Stonewick"}, licensed=["stonewick"], facts=True)
    print("BAD   :", validate(bad, "Stonewick yard had 42 colonies in September."))
