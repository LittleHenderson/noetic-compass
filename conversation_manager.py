"""Conversational core for HELM — dialogue state, follow-up resolution, context-aware replies.

This is the piece HELM never had. Every earlier layer treated a turn in isolation: match intent, print a sentence.
Here a turn is answered against the thread: what was said, what is being discussed, what was just answered, and what
the user is asking *relative to that* ("why?", "and the other one?", "what about March?").

It is deterministic and testable. The mouth model can later render these choices; the state machine is what makes the
exchange coherent.

    python conversation_manager.py       # runs the demo dialogues
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

GREETINGS = ("hello", "hi", "hey", "morning", "good morning", "howdy", "greetings")
FAREWELLS = ("bye", "goodbye", "see you", "talk later", "later", "goodnight", "good night")
THANKS = ("thanks", "thank you", "appreciate", "cheers")
FOLLOWUP_WHY = ("why", "why?", "why that", "how come", "what makes you say that")
FOLLOWUP_MORE = ("and?", "then what", "what else", "go on", "continue", "tell me more")
FOLLOWUP_OTHER = ("the other one", "other one", "not that", "no, the other", "second one")


@dataclass
class Turn:
    user: str
    reply: str
    tag: str


@dataclass
class ConversationState:
    turns: List[Turn] = field(default_factory=list)
    topic: Optional[str] = None
    last_entity: Optional[str] = None
    last_reply: str = ""
    last_tag: str = ""
    user_affect: Optional[str] = None
    pending_question: Optional[str] = None
    named_things: List[str] = field(default_factory=list)

    def remember(self, user: str, reply: str, tag: str) -> None:
        self.turns.append(Turn(user, reply, tag))
        self.last_reply, self.last_tag = reply, tag
        for m in re.findall(r"\b(?:my|the)\s+([a-z]{3,})\b", user.lower()):
            if m not in ("the", "and"):
                self.last_entity = m
                if m not in self.named_things:
                    self.named_things.append(m)


def _pick(rng: random.Random, options: List[str]) -> str:
    return options[rng.randrange(len(options))]


class ConversationManager:
    """Answers a turn against the dialogue state. Returns (tag, reply)."""

    def __init__(self, seed: int = 7):
        self.s = ConversationState()
        self.rng = random.Random(seed)

    # ---------------------------------------------------------------- intent on the thread
    def classify(self, text: str) -> str:
        t = text.lower().strip().rstrip(".!")
        s = self.s
        if any(t.startswith(g) for g in GREETINGS) or t in GREETINGS:
            return "GREETING"
        if any(f in t for f in FAREWELLS):
            return "FAREWELL"
        if any(x in t for x in THANKS):
            return "THANKS"
        if any(t.startswith(x) for x in FOLLOWUP_WHY) or t in FOLLOWUP_WHY:
            return "EXPLAIN_PREVIOUS"
        if t in FOLLOWUP_MORE or any(t.startswith(x) for x in FOLLOWUP_MORE):
            return "CONTINUE"
        if any(x in t for x in FOLLOWUP_OTHER):
            return "CORRECT_OTHER"
        if "what did i" in t or "remember" in t or "remind me" in t:
            return "RECALL"
        if any(w in t for w in ("tired", "exhausted", "rough day", "drained", "worn out", "low")):
            return "EMPATHY"
        if any(w in t for w in ("what can you", "what do you do", "who are you", "your limits", "what are you")):
            return "SELF"
        if any(w in t for w in ("plan", "next", "start", "order", "what should we do")):
            return "PLAN"
        # A short elliptical question after a previous answer is a follow-up; a long one is a new question.
        if t.startswith("what about ") or t.startswith("and what about "):
            return "NEW_TOPIC"
        if t.endswith("?") and s.last_tag and len(t.split()) <= 6:
            return "FOLLOWUP_QUESTION"
        return "UNKNOWN"

    # ---------------------------------------------------------------- replies that use the thread
    def respond(self, text: str) -> Tuple[str, str]:
        tag = self.classify(text)
        s = self.s
        if tag == "GREETING":
            r = _pick(self.rng, ["Hello! Good to see you. What are we working on today?",
                                 "Hey there. I'm here and ready — what's on your mind?",
                                 "Morning! Where should we start?"])
        elif tag == "FAREWELL":
            r = _pick(self.rng, ["Take care — I'll be here when you're back.",
                                 "See you soon. Everything's saved.",
                                 "Later. I'll keep the context."])
        elif tag == "THANKS":
            r = _pick(self.rng, ["You're welcome — glad it landed.", "Any time. Say the word if you want more."])
        elif tag == "EXPLAIN_PREVIOUS":
            if s.last_tag == "EMPATHY":
                r = "Because you told me you were worn out — I was responding to that, not to a task."
            elif s.last_tag == "PLAN":
                r = "Because the cheapest check rules out the biggest failures first, before we spend effort."
            elif s.last_tag == "SELF":
                r = "Because I answer only from checked inputs; anything else I decline rather than invent."
            elif s.topic:
                r = f"Because it follows from {s.topic}: the inputs constrain the answer, so I keep to them."
            elif s.last_reply:
                r = "Because it follows from what we established — I would rather explain the basis than repeat myself."
            else:
                r = "I don't have a previous answer to explain yet."
        elif tag == "CONTINUE":
            topic = s.topic or (s.named_things[-1] if s.named_things else "that")
            r = f"Continuing on {topic}: the next step is to check the smallest piece, then widen."
            s.topic = topic
        elif tag == "CORRECT_OTHER":
            r = "Understood — switching to the other one. I'll use that from here."
        elif tag == "RECALL":
            thing = s.last_entity or (s.named_things[0] if s.named_things else None)
            if thing:
                r = f"You mentioned your {thing} earlier — I've kept it in this session."
            else:
                r = "You haven't told me a personal detail yet in this session."
        elif tag == "EMPATHY":
            s.user_affect = "low"
            r = _pick(self.rng, ["That sounds draining. Do you want to talk it through or keep it light?",
                                 "I'm sorry — that's a lot. What would help most right now?",
                                 "Rough days are real. I'm here either way."])
        elif tag == "SELF":
            r = "I compute, remember and refuse — but I don't invent facts."
        elif tag == "NEW_TOPIC":
            m = re.search(r"what about (?:my |the )?([a-z]{3,})", text.lower())
            thing = m.group(1) if m else "that"
            s.topic = thing
            r = (f"Your {thing} — I don't have it in this session yet. Tell me what you need from it "
                 f"and I'll work from that.")
        elif tag == "FOLLOWUP_QUESTION":
            r = f"On {s.topic or 'that'}: I can answer from what we've established so far, or check it properly."
        elif tag == "PLAN":
            s.topic = s.topic or "the task"
            r = f"For {s.topic}: start with the cheapest check, then one change, then re-measure."
        else:
            r = ("I'm not sure what you're asking for — do you mean the last task, or something new?")
            s.pending_question = text
        s.remember(text, r, tag)
        return tag, r


def demo() -> int:
    scripts = [
        ["Hello.", "What can you actually do?", "Where should we start?", "Why that order?",
         "And?", "Thanks, talk later."],
        ["I'm exhausted today.", "Why do you say that?", "What about my report?", "No, the other one.",
         "Okay, thanks."],
    ]
    ok = 0
    total = 0
    for script in scripts:
        m = ConversationManager(seed=7)
        print("=" * 70)
        for line in script:
            tag, reply = m.respond(line)
            print(f"USER : {line}")
            print(f"HELM : {reply}   [{tag}]")
            total += 1
            ok += int(reply.strip() != "" and "not sure what you're asking" not in reply)
        print()
    print(f"non-fallback replies: {ok}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(demo())
