"""helm_talk.py -- HELM's talk layer v1 (A-TALK-2): how HELM answers a line that is not about the kitchen.

WHAT THIS IS, IN PLAIN WORDS
----------------------------
Behind ONE switch, HELM_TALK (default OFF; OFF = today's chat byte for byte):
  SMALL  "hi", "thanks", "how are you", "ok"      -> one short friendly line; nothing saved.
  SELF   "are you a robot?", "do you remember?"   -> one truthful line about what HELM keeps and cannot do.
  OFF    "My sister is moving to Denver."          -> the off-topic rule M10 (A-TALK-1 s3): react in one line, keep the
         person's line word for word (the 20-item user_facts list; no stock, no cube), ask ONE question built from
         the person's own word -- never an opinion, never a fact HELM was not told.
  WORLD  "who won the game?"                       -> "I don't know that. Nobody has told me about it."
Behind a second switch, HELM_TALK_ASK (default OFF; needs HELM_TALK), HELM asks about what it already holds: when an
off-topic or small-talk line names a cube thing it holds, or a stock name, it asks "You told me ... Is that still
right?"; a yes on the next line confirms the cube (provenance CHECKED, the cube oscillation's own `confirm`), a no
writes nothing. Never twice about the same thing in one session.
Every talk reply passes the guards (B3): no CAS token (M1), no recipe-speak (M2), 1-3 sentences (M7), no opinion,
and on OFF exactly one question built only from the person's words, HELM's stored names and the template words. A
reply that fails a guard is replaced by "Thanks for telling me."

HELM has no large language model inside: every reply is a template plus the person's own words or HELM's records.
Design: docs/working/helm_talk_design_v1/ (A-TALK-1, A-TALK-2). CLAIM STATUS: ENGINEERED-NOT-VALIDATED.
"""
from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import helm_voice

# ----------------------------------------------------------------------------------------------- the switches
_ON = {"1", "ON", "TRUE", "YES"}


def talk_on() -> bool:
    return (os.environ.get("HELM_TALK") or "").strip().upper() in _ON


def ask_on() -> bool:
    return talk_on() and (os.environ.get("HELM_TALK_ASK") or "").strip().upper() in _ON


# ----------------------------------------------------------------------------------------------- frozen lists
_TRAIL = r"(?:\s+\w+){0,3}"
SMALL_KINDS = (
    ("greeting", re.compile(r"^(?:hi|hello|hey|hiya|good (?:morning|afternoon|evening))" + _TRAIL + r"$")),
    ("how_are_you", re.compile(r"^(?:how are you|how's it going|hows it going|how are things|what's up|whats up|sup)"
                               + _TRAIL + r"$")),
    ("thanks", re.compile(r"^(?:thanks|thank you|thx|cheers)" + _TRAIL + r"$")),
    ("pause", re.compile(r"^(?:ok|okay|cool|got it|sounds good|one sec|hold on|never mind|nevermind|alright|all right)"
                         + _TRAIL + r"$")),
)
SMALL_REPLIES = {
    "greeting": "Hi there.",
    "how_are_you": "I'm doing fine, thanks for asking.",
    "thanks": "You're welcome.",
    "pause": "Sure.",
}
SELF_RX = re.compile(r"\b(?:are you (?:a |an )?(?:person|human|robot|bot|ai|machine|computer|real)|who are you|"
                     r"what are you|what can you do|how do you work|do you remember|do you forget|can you remember|"
                     r"will you remember)\b")
SELF_REPLIES = {
    "what": "I'm HELM, a program, not a person.",
    "remember": "I keep what you tell me in this chat, including up to twenty things you say about yourself.",
    "can_do": "I can keep track of kitchen amounts you give me and work out what you can make from them.",
}
QUESTION_OPENERS = ("what", "who", "where", "when", "why", "how", "which", "is ", "are ", "do ", "does ", "did ",
                    "can ", "could ", "will ", "would ", "should ")
WORLD_REPLY = "I don't know that. Nobody has told me about it."
OFF_REACT = {
    "strain": "That sounds like a lot.",
    "good": "I'm glad you told me.",
    "neutral": "Thanks for telling me.",
}
STRAIN_RX = re.compile(r"\b(?:tired|exhausted|worried|worry|nervous|anxious|stressed|stress|sad|sick|ill|hard|tough|"
                       r"rough|run down|lonely|scared|upset|hurt|lost|late|bad day|long day)\b", re.I)
GOOD_RX = re.compile(r"\b(?:happy|excited|glad|great news|good news|proud|thrilled|finally|won|celebrat\w*|engaged|"
                     r"promoted|birthday)\b", re.I)
OFF_QUESTIONS = ("What's going on with {w}?", "What happened with {w}?")      # A-TALK-3 W4
OFF_QUESTION_NONE = "Do you want to tell me more?"
ASK_TAIL = "Is that still right?"
TEMPLATE_WORDS = {w for t in list(OFF_QUESTIONS) + [OFF_QUESTION_NONE, ASK_TAIL, "You told me we have of the"]
                  for w in re.findall(r"[a-z']+", t.lower())}
#: A-TALK-3 W3: feeling, time and filler words are never the topic of the question
NOT_A_TOPIC = {"feeling", "feel", "feels", "tired", "today", "tonight", "week", "weekend", "morning", "night", "lately",
               "day", "days", "long", "down", "run", "strange", "kind", "sort", "pretty", "really", "been", "going"}
MONTH_WORDS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
               "november", "december"}
#: M2 (A-TALK-1 / the talk packet's frozen list): recipe-speak on a non-recipe turn
RECIPE_SPEAK_RX = re.compile(r"\b(?:recipes?|ingredients?|stock|inventory|limiting|yield|batch|receipt|foundation loop|station|"
                             r"gate|RPM|cube|verified facts|flour|water|sugar|butter|eggs?|milk|salt|yeast)\b"
                             r"|how much .* do (?:we|you) have", re.I)
OPINION_RX = re.compile(r"\b(?:i think|i believe|i feel that|i like|i love|i hate|in my opinion|you should|"
                        r"that'?s (?:good|bad|great|terrible|wrong|right|awful|wonderful)|that is (?:good|bad|great|terrible|"
                        r"wrong|right|awful|wonderful))\b", re.I)
YES_RX = re.compile(r"^(?:yes|yeah|yep|yup|right|correct|that's right|thats right|still right|it is|sure is)\b", re.I)
NO_RX = re.compile(r"^(?:no|nope|not anymore|not any more|that's wrong|thats wrong|it changed|wrong)\b", re.I)
SAFE_LINE = "Thanks for telling me."
ASK_YES_CUBE = "Thanks, I'll keep that as checked."
ASK_YES_STOCK = "Good, I'll keep it as it is."
ASK_NO = "Okay. Tell me what it is now and I'll update it."
_WORD_RX = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def _plain(text: str) -> str:
    return re.sub(r"[^\w\s']", " ", (text or "").lower()).strip()


def _words(text: str) -> Set[str]:
    return {w.lower().strip("'-") for w in _WORD_RX.findall(text or "")}


# ----------------------------------------------------------------------------------------------- B2 kinds
def small_kind(text: str) -> Optional[str]:
    p = " ".join(_plain(text).split())
    for kind, rx in SMALL_KINDS:
        if rx.match(p):
            return kind
    return None


def is_question(text: str) -> bool:
    low = (text or "").strip().lower()
    return "?" in low or low.startswith(QUESTION_OPENERS)


def classify(text: str) -> Optional[str]:
    """SMALL / SELF / OFF / WORLD for a line no earlier branch took (B2 order 2-5)."""
    if not (text or "").strip():
        return None
    if small_kind(text):
        return "SMALL"
    if SELF_RX.search(_plain(text)):
        return "SELF"
    if is_question(text):
        return "WORLD"
    return "OFF"


def self_reply(text: str) -> str:
    p = _plain(text)
    if re.search(r"\b(?:remember|forget)\b", p):
        return SELF_REPLIES["remember"]
    if re.search(r"\bwhat can you do|how do you work\b", p):
        return SELF_REPLIES["can_do"]
    return SELF_REPLIES["what"]


# ----------------------------------------------------------------------------------------------- B4 the one word
def _is_name(w: str) -> bool:
    return w[:1].isupper() and w.lower() not in MONTH_WORDS and w != "I" and len(w) >= 2


def _pick(text: str) -> Tuple[Optional[str], bool]:
    """(word, is_name). A name: the first run of consecutive capitalised words after the line's first word, not a
    month, not "I" (A-TALK-3 W1). Else the longest content word (the compactor's rule) that is not in NOT_A_TOPIC
    (W3), first appearance breaking ties."""
    toks = [w.strip("'-") for w in _WORD_RX.findall(text or "")]
    for i in range(1, len(toks)):
        if _is_name(toks[i]):
            run = [toks[i]]
            for w in toks[i + 1:]:
                if not _is_name(w):
                    break
                run.append(w)
            return " ".join(run), True
    import helm_memory_compact as hmc
    best = None
    for w in hmc.content_words(text or ""):
        if w in NOT_A_TOPIC:
            continue
        if best is None or len(w) > len(best):
            best = w
    return best, False


def pick_word(text: str) -> Optional[str]:
    return _pick(text)[0]


def off_question(text: str) -> str:
    w, name = _pick(text)
    if not w:
        return OFF_QUESTION_NONE
    w = w if name else "the " + w                                   # A-TALK-3 W2
    return OFF_QUESTIONS[len((text or "").split()) % len(OFF_QUESTIONS)].format(w=w)


def off_react(text: str) -> str:
    if STRAIN_RX.search(text or ""):
        return OFF_REACT["strain"]
    if GOOD_RX.search(text or ""):
        return OFF_REACT["good"]
    return OFF_REACT["neutral"]


# ----------------------------------------------------------------------------------------------- B3 the guards
def guard(reply: str, kind: str, person_words: Set[str], held: Set[str]) -> Tuple[bool, str]:
    if helm_voice.cas_tokens(reply):
        return False, "M1 CAS token"
    typed = {w.lower() for w in person_words}
    for m in RECIPE_SPEAK_RX.finditer(reply):
        if m.group(0).lower() not in typed and m.group(0).lower() not in held:
            return False, "M2 recipe-speak"
    n = helm_voice.sentence_count(reply)
    if not 1 <= n <= 3 or re.search(r"(?m)^\s*(?:-|Status)", reply):
        return False, "M7 sentences"
    if OPINION_RX.search(reply):
        return False, "opinion"
    if kind == "OFF":
        if reply.count("?") != 1:
            return False, "OFF needs exactly one question"
        q = reply[: reply.index("?") + 1]
        q = re.split(r"(?<=[.!])\s+", q)[-1]
        allowed = typed | {h.lower() for h in held} | TEMPLATE_WORDS
        extra = [w for w in _words(q) if w not in allowed and not w.isdigit()]
        if extra:
            return False, "question word not the person's: " + ", ".join(sorted(extra)[:3])
    return True, ""


def safe_reply(parts: List[str], kind: str, person_words: Set[str], held: Set[str]) -> Tuple[str, Optional[str]]:
    reply = " ".join(p for p in parts if p)
    ok, why = guard(reply, kind, person_words, held)
    return (reply, None) if ok else (SAFE_LINE, why)


# ----------------------------------------------------------------------------------------------- the layer
class TalkLayer:
    """One per chat session; created only when HELM_TALK is on."""

    def __init__(self, session: Any) -> None:
        self.session = session
        self.pending: Optional[Dict[str, Any]] = None       # the question HELM just asked (B6)
        self.asked: Set[str] = set()                        # things already asked about this session
        self.guard_log: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------- what the person typed this session
    def person_words(self, prompt: str) -> Set[str]:
        words = _words(prompt)
        for t in self.session.memory.turns:
            words |= _words(t.user_raw_text)
        return words

    def keep_verbatim(self, prompt: str) -> None:
        """M10 step 2: the person's line, kept word for word in the 20-item user_facts list (the memory's own cleaning
        and cap); no stock, no cube."""
        ctx = self.session.memory.context
        cleaned = prompt.strip().rstrip(".").strip()
        if cleaned and cleaned not in ctx.user_facts:
            ctx.user_facts.append(cleaned)
        ctx.user_facts = ctx.user_facts[-20:]

    # ---------------------------------------------------------------- B6 what HELM holds
    def _current_branches(self) -> List[Any]:
        osc = getattr(self.session.memory, "cube_osc", None)
        store = getattr(self.session.memory.context, "cube_store", None)
        if osc is None or store is None:
            return []
        latest: Dict[Tuple[str, str, str], Any] = {}
        for b in store.branches:
            com = b.commonality or {}
            if "kind" in com and b.source_node_id.startswith("thing_"):
                latest[(b.source_node_id, b.target_node_id, com["kind"])] = b
        return list(latest.values())

    def held_names(self) -> Set[str]:
        names = {b.source_node_id[len("thing_"):] for b in self._current_branches()}
        names |= {b.target_node_id[len("thing_"):] for b in self._current_branches()}
        loop = getattr(self.session, "loop", None)
        names |= {str(k).lower() for k in (getattr(loop, "stock", {}) or {})}
        return names

    def held_question(self, prompt: str) -> Optional[Dict[str, Any]]:
        words = _words(prompt)
        for b in self._current_branches():
            thing = b.source_node_id[len("thing_"):]
            if thing in words and ("cube:" + thing) not in self.asked:
                com = b.commonality
                tgt = b.target_node_id[len("thing_"):]
                phrase = f"{thing.capitalize()}, {com['kind']}, {tgt.capitalize()}" + (f": {com['amount']}" if "amount" in com else "")
                return {"what": "cube", "key": "cube:" + thing, "thing": thing,
                        "text": f"You told me {phrase}. {ASK_TAIL}"}
        loop = getattr(self.session, "loop", None)
        for name, value in sorted((getattr(loop, "stock", {}) or {}).items()):
            if str(name).lower() in words and ("stock:" + str(name).lower()) not in self.asked:
                amount = helm_voice.say_amount(value, "f").replace("exactly ", "")
                unit = (getattr(loop, "units", {}) or {}).get(name)          # A-TALK-3 W5: the person's own unit
                said = f"{amount} {unit}" if unit else amount
                return {"what": "stock", "key": "stock:" + str(name).lower(), "name": name,
                        "text": f"You told me we have {said} of {str(name).lower()}. {ASK_TAIL}"}
        return None

    # ---------------------------------------------------------------- recording
    def _say(self, prompt: str, resolved: str, entities: Dict[str, Any], kind: str, intent: str, speech: str,
             t0: float, why: Optional[str]) -> None:
        print(f"\nHELM: {speech}\n")
        ents = dict(entities or {})
        ents["talk"] = kind
        if why:
            ents["talk_guard_fallback"] = why
            self.guard_log.append({"kind": kind, "why": why, "prompt": prompt})
        self.session.memory.record_turn(prompt, resolved, intent, ents, speech, gate_code="GATE_PASS",
                                        duration=time.time() - t0)

    # ---------------------------------------------------------------- B6 the answer to HELM's own question
    def take_answer(self, prompt: str, resolved: str, entities: Dict[str, Any], t0: float) -> bool:
        q, self.pending = self.pending, None
        if q is None:
            return False
        text = (prompt or "").strip()
        if YES_RX.match(text):
            if q["what"] == "cube":
                self.session.memory.cube_osc.confirm(q["thing"])
                speech = ASK_YES_CUBE
            else:
                speech = ASK_YES_STOCK
        elif NO_RX.match(text):
            speech = ASK_NO
        else:
            return False
        self._say(prompt, resolved, entities, "ASK_ANSWER", "GENERAL_CONVERSATION", speech, t0, None)
        return True

    # ---------------------------------------------------------------- B2 the turn
    def take(self, prompt: str, resolved: str, entities: Dict[str, Any], t0: float, kind: Optional[str] = None) -> bool:
        kind = kind or classify(prompt)
        if kind is None:
            return False
        words, held = self.person_words(prompt), self.held_names()
        ask = self.held_question(prompt) if ask_on() and kind in ("OFF", "SMALL") else None
        if kind == "SMALL":
            parts = [SMALL_REPLIES[small_kind(prompt) or "pause"]] + ([ask["text"]] if ask else [])
            intent = "GENERAL_CONVERSATION"
        elif kind == "SELF":
            parts, intent = [self_reply(prompt)], "GENERAL_KNOWLEDGE_INQUIRY"
        elif kind == "WORLD":
            parts, intent = [WORLD_REPLY], "GENERAL_KNOWLEDGE_INQUIRY"
        else:
            self.keep_verbatim(prompt)
            parts = [off_react(prompt), ask["text"] if ask else off_question(prompt)]
            intent = "GENERAL_CONVERSATION"
        speech, why = safe_reply(parts, kind, words, held)
        if ask and why is None:
            self.pending = ask
            self.asked.add(ask["key"])
        self._say(prompt, resolved, entities, kind, intent, speech, t0, why)
        return True
