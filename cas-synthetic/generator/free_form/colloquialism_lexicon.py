"""Phrase tables for native free-form English CAS surface generation.

This module is the lexical backbone of Phase 3 SDG. Each phrase is a
verbatim or near-verbatim colloquialism a native English speaker would
use to describe the structural dynamic the corresponding CAS primitive
names. The phrase tables are organised by primitive (Noetic 0-9, Drive
F1-F7, Domain P/C/E/O, Register T/A/f/E) so the surface generator can
compose by axis without reaching back into prose.

Authoritative sources
---------------------
- ``noetic-compass-scaffold/noetic-compass/CLAUDE.md`` — "Colloquialism
  Test" section. The canonical colloquialism map is reproduced verbatim
  per Noetic; the per-Register elaborations below extend the map within
  the same CLAUDE.md anti-drift constraints.
- ``docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`` Clarification 6 — the
  visceral / triggering / etymological-cognate annotations.

Design rules
------------
1.  ``^3`` Negative phrases are VISCERAL, never analytical. No
    "scrutinise", "audit", "find flaws", "tear apart". Analytical
    decomposition belongs to ``^6`` Male.
2.  ``^8`` Above/Cause phrases are ASSOCIATIVE TRIGGERS, never
    deductive. No "therefore", "thus", "it follows that", "q.e.d.",
    "ergo". Deductive reasoning is a compound (``^6`` Male decomposition
    + ``^9`` Below/Effect landing), not ``^8``.
3.  ``^4`` Vibration phrases preserve the etymological cognate ("struck
    a chord", "resonated"). Vibration vocabulary is intentionally
    overlapping with the canonical definition.
4.  Authoritative names (Idea, Mind, Positive, Negative, Vibration,
    Female, Male, Rhythm, Above/Cause, Below/Effect) are reserved for
    structural commentary and never replaced by softening synonyms.

Per-Noetic structure
--------------------
For each Noetic ``^N`` we expose five phrase categories:

- ``base``                    — register-neutral colloquialisms (the
                                 CLAUDE.md verbatim entries).
- ``transcendent_modifier``   — phrases for ``^N|T`` (high-abstraction).
- ``analytical_modifier``     — phrases for ``^N|A`` (sequential/logic).
- ``felt_modifier``           — phrases for ``^N|f`` (value-laden).
- ``embodied_modifier``       — phrases for ``^N|E`` (sensorimotor).

The surface generator MUST always be able to fall back to ``base`` if a
register slot is unspecified or empty.

Domain and Drive flavor tables provide adjective-style markers that the
surface generator weaves into a sentence to colour the underlying
Noetic+Register phrase. Each Domain has 8-15 markers; each Drive has
6-12.

Total: ~50 phrases per Noetic x 10 Noetics + ~50 Drive markers + ~50
Domain markers + ~30 meta-logic / Omega / recipe phrases = ~600-800
total entries. Pure-data, stdlib-only.
"""

from __future__ import annotations

from typing import Final


# ---------------------------------------------------------------------------
# Authoritative Noetic names (per CLAUDE.md "The 10 Noetics")
# ---------------------------------------------------------------------------
#
# These are the CANONICAL names. They appear verbatim in structural
# commentary (e.g. when the surface generator emits a fallback gloss
# such as "the cognitive move here is Above/Cause"). They are NEVER
# softened ("trigger" -> "stimulus", "Female" -> "container", etc).
NOETIC_NAMES: Final[dict[str, str]] = {
    "0": "Idea",
    "1": "Mind",
    "2": "Positive",
    "3": "Negative",
    "4": "Vibration",
    "5": "Female",
    "6": "Male",
    "7": "Rhythm",
    "8": "Above/Cause",
    "9": "Below/Effect",
}


REGISTER_NAMES: Final[dict[str, str]] = {
    "T": "transcendent",
    "A": "analytical",
    "f": "affective",
    "E": "embodied",
}


DOMAIN_NAMES: Final[dict[str, str]] = {
    "P": "principled",
    "C": "cognitive",
    "E": "evaluative",
    "O": "operational",
}


DRIVE_NAMES: Final[dict[str, str]] = {
    "F1": "Unity",
    "F2": "Wisdom",
    "F3": "Vitality",
    "F4": "Connection",
    "F5": "Agency",
    "F6": "Structure",
    "F7": "Purpose",
}


# ---------------------------------------------------------------------------
# Per-Noetic phrase tables
# ---------------------------------------------------------------------------
#
# All phrases below are colloquial English fragments. They are designed
# to drop into a sentence frame supplied by the surface generator. They
# are NOT full sentences — the generator wraps them with appropriate
# pronouns, conjunctions, and Domain/Drive flavor.
#
# Anti-drift commentary lives next to the affected Noetic.

NOETIC_LEXICON: Final[dict[str, dict[str, tuple[str, ...]]]] = {
    # -----------------------------------------------------------------
    # ^0 Idea — content-neutral, "all things in and outside the Mind"
    # -----------------------------------------------------------------
    "0": {
        "base": (
            "the idea",
            "this notion",
            "a concept",
            "the thought itself",
            "what we're calling the idea",
            "the content",
            "the underlying notion",
            "the basic point",
            "an idea I'm holding",
            "the thing in question",
            "the matter at hand",
            "this whole concept",
            "the idea sitting there",
            "the idea on the table",
            "what's all in your head",
        ),
        "transcendent_modifier": (
            "the big-picture idea",
            "the meaning of it",
            "the deep idea",
            "the idea at the highest level",
            "the encompassing notion",
            "the overarching idea",
            "the unifying idea",
            "the idea read from above",
        ),
        "analytical_modifier": (
            "the idea, taken explicitly",
            "the idea written out step by step",
            "the propositional idea",
            "the idea spelled out",
            "the formally stated idea",
            "the precise idea",
            "the idea, broken into premises",
            "the idea on paper",
        ),
        "felt_modifier": (
            "the idea that has a feel to it",
            "the idea that carries weight",
            "the felt idea",
            "the idea I have feelings about",
            "the value-laden idea",
            "the idea you can taste",
            "the idea that comes with a tone",
            "the affectively coloured idea",
        ),
        "embodied_modifier": (
            "the idea I can touch",
            "the concrete idea",
            "the idea you can pick up",
            "the hands-on idea",
            "the idea that lives in the body",
            "the practical idea",
            "the idea grounded in something physical",
            "the lived idea",
        ),
    },
    # -----------------------------------------------------------------
    # ^1 Mind — awareness; "paying attention", "making up your mind"
    # -----------------------------------------------------------------
    "1": {
        "base": (
            "paying attention",
            "making up my mind",
            "using my head",
            "noticing",
            "tracking it",
            "keeping it in mind",
            "minding it",
            "being aware of it",
            "holding it in awareness",
            "staying attentive",
            "watching for it",
            "having it on my mind",
            "keeping watch",
            "keeping tabs",
            "keeping it in the front of my mind",
        ),
        "transcendent_modifier": (
            "holding the whole thing in awareness",
            "minding the big picture",
            "noticing the meaning behind it",
            "attending to what it really points at",
            "keeping the deeper sense of it in mind",
            "paying attention from above",
            "minding the larger arc",
            "letting the meaning stay present",
        ),
        "analytical_modifier": (
            "thinking it through carefully",
            "working through it step by step",
            "deliberating",
            "reasoning about it",
            "minding it analytically",
            "watching the logic",
            "tracking the argument",
            "paying attention to the chain of thought",
        ),
        "felt_modifier": (
            "tuning in to how it feels",
            "noticing the feeling",
            "minding the affective tone",
            "paying attention to the gut response",
            "tracking the felt sense",
            "staying with the feeling",
            "watching for the emotional signal",
            "letting the affect register",
        ),
        "embodied_modifier": (
            "noticing it in my body",
            "minding the bodily signal",
            "feeling it in my chest",
            "paying attention to the breath",
            "tracking what the body is doing",
            "staying with the kinesthetic feel",
            "minding the posture",
            "noticing the somatic cue",
        ),
    },
    # -----------------------------------------------------------------
    # ^2 Positive — affinity, attracted toward
    # -----------------------------------------------------------------
    "2": {
        "base": (
            "drawn to it",
            "speaks to me",
            "can't resist",
            "right up my alley",
            "moth to a flame",
            "hooked on it",
            "love it",
            "leaning into it",
            "pulled toward it",
            "magnetic",
            "I keep coming back to it",
            "it has my attention",
            "I'm a sucker for it",
            "I gravitate toward it",
            "warming to it",
        ),
        "transcendent_modifier": (
            "deeply called to it",
            "drawn to the meaning of it",
            "feels like a calling",
            "feels like a vocation",
            "pulled by the purpose of it",
            "drawn by something larger",
            "the sense of vision pulls me",
            "drawn to the higher arc",
        ),
        "analytical_modifier": (
            "the more I think about it the more I like it",
            "the case for it convinces me",
            "the reasoning lands well",
            "I find the argument attractive",
            "I keep arriving at yes",
            "the more I lay it out the more it appeals",
            "the logic of it pulls me in",
            "I keep talking myself into it",
        ),
        "felt_modifier": (
            "it just feels right",
            "warm feeling about it",
            "good vibes",
            "it sits well",
            "I have a soft spot for it",
            "I'm fond of it",
            "I'm warm on it",
            "the feeling is yes",
        ),
        "embodied_modifier": (
            "my body leans toward it",
            "I can feel myself reaching",
            "physically drawn",
            "I light up around it",
            "my hands want to do it",
            "feet move toward it",
            "shoulders relax around it",
            "chest opens to it",
        ),
    },
    # -----------------------------------------------------------------
    # ^3 Negative — VISCERAL aversion (NOT analytical critique)
    # -----------------------------------------------------------------
    # Anti-drift: ABSOLUTELY NO words like "audit", "scrutinise",
    # "critique", "find flaws", "fact-check", "dissect", "tear apart",
    # "interrogate". Those belong on ^6 Male. ^3 is gut-level
    # repulsion, not analytical decomposition.
    "3": {
        "base": (
            "can't stomach it",
            "rubs me the wrong way",
            "wouldn't touch it with a ten-foot pole",
            "makes my skin crawl",
            "puts my back up",
            "turns my stomach",
            "can't stand it",
            "loathe it",
            "hate it",
            "find it repulsive",
            "find it gross",
            "off-putting",
            "rubs me wrong",
            "skin-crawl response",
            "I bristle at it",
            "I recoil from it",
        ),
        "transcendent_modifier": (
            "violates everything I stand for",
            "deeply wrong at the level of meaning",
            "core principle violation",
            "feels like a betrayal of what matters",
            "cuts against the deepest read I have",
            "stands against the whole point",
            "feels like sacrilege to what I value",
            "is wrong all the way down",
        ),
        "analytical_modifier": (
            "I have to push back",
            "I have to disagree",
            "the answer I land on is no",
            "I keep arriving at no",
            "no, the more I sit with it",
            "I have to say no to that",
            "after working it through, the conclusion is no",
            "the read I land on is unwilling",
        ),
        "felt_modifier": (
            "doesn't sit right",
            "leaves a bad taste",
            "has a sour feel",
            "the feeling is no",
            "the affect is rejection",
            "I feel a no in my chest",
            "the gut says no",
            "feels off",
        ),
        "embodied_modifier": (
            "my body says no",
            "physically pulling back",
            "tightening up",
            "shoulders tense",
            "I feel myself lean away",
            "my hands curl",
            "stomach clenches",
            "jaw locks",
        ),
    },
    # -----------------------------------------------------------------
    # ^4 Vibration — resonance, impression
    # -----------------------------------------------------------------
    # Etymological cognate preserved: "struck a chord" is a literal
    # vibration metaphor; "resonate" carries the same etymology.
    "4": {
        "base": (
            "struck a chord",
            "hit me hard",
            "resonated",
            "resonates with me",
            "made an impression",
            "left an impression",
            "left a mark",
            "rings true",
            "sounded right",
            "echoes for me",
            "lingers with me",
            "still rings in my head",
            "the impression stays",
            "registered",
            "landed",
            "really landed",
        ),
        "transcendent_modifier": (
            "resonates at the deepest level",
            "the meaning of it rings true",
            "rings true for me at the core",
            "echoes the larger picture",
            "the deeper register hums with it",
            "sounds the right note in the bigger picture",
            "vibrates at the level of meaning",
            "the meaning of it lands",
        ),
        "analytical_modifier": (
            "the argument rings true",
            "the logic resonates",
            "every step of the reasoning sounds right",
            "the structure clicks",
            "the case rings out clearly",
            "the chain of thought hums",
            "the explanation registers cleanly",
            "the argument echoes",
        ),
        "felt_modifier": (
            "the feeling resonates",
            "it touched me",
            "moved me",
            "stirred something",
            "the emotion lingers",
            "the feeling stays in the room",
            "felt it in the chest",
            "the affect rings out",
        ),
        "embodied_modifier": (
            "I felt it in my body",
            "vibrated in my chest",
            "felt it in my bones",
            "rang in my bones",
            "physically reverberated",
            "I felt the buzz of it",
            "shook me physically",
            "the body still hums with it",
        ),
    },
    # -----------------------------------------------------------------
    # ^5 Female — Mind composed of accumulated experience
    # -----------------------------------------------------------------
    # Per CLAUDE.md "Expanded scope note": "we are each the sum of
    # our experiences" — covers self-image, expertise, formation,
    # trauma/healing, cultural composition.
    "5": {
        "base": (
            "the sum of my experiences",
            "it's who I am",
            "part of what makes me me",
            "shaped by years of it",
            "years of work made me this",
            "what I am made of",
            "the layers I've accumulated",
            "everything I've been through",
            "the whole arc of how I got here",
            "decades of it built into me",
            "the formation I carry",
            "what I bring with me",
            "the experience that made me",
            "all the practice I've absorbed",
            "the version of me that all of that produced",
        ),
        "transcendent_modifier": (
            "the meaning I've grown into over a lifetime",
            "the calling I've been formed by",
            "the deeper arc of my life shaping me",
            "what feels like my vocation, accumulated",
            "the larger story I've lived into",
            "my whole sense of purpose, layered up over years",
            "the deep self I've become",
            "who I've become at the level of meaning",
        ),
        "analytical_modifier": (
            "the body of knowledge I've built",
            "the framework I've gradually constructed",
            "the analytical machinery I've accumulated",
            "the explicit knowledge I carry",
            "the chain of reasoning patterns I've absorbed",
            "the formal toolkit I've grown",
            "the structured expertise I've assembled",
            "the explicit lessons I've internalised",
        ),
        "felt_modifier": (
            "the emotional patterns I carry",
            "the felt history I bring",
            "the affective grooves life put in me",
            "the layered feelings I've inherited",
            "the way years of feeling have shaped me",
            "the sensitivities I've grown",
            "my emotional formation",
            "the sediment of feeling I'm made of",
        ),
        "embodied_modifier": (
            "the muscle memory I've built up",
            "what my hands have learned",
            "what my body has absorbed",
            "the kinesthetic library I've accumulated",
            "the embodied skill I bring",
            "what my body remembers from doing this",
            "what's been trained into my body",
            "the somatic shape years of practice gave me",
        ),
    },
    # -----------------------------------------------------------------
    # ^6 Male — decomposition; "unpacking", "breaking it down"
    # -----------------------------------------------------------------
    # ^6 IS the home for analytical decomposition vocabulary
    # ("unpack", "scrutinise", "audit", "break down"). It is NOT ^3.
    "6": {
        "base": (
            "unpacking it",
            "breaking it down",
            "looking at what's underneath",
            "pulling it apart",
            "taking it apart",
            "decomposing it",
            "examining the parts",
            "scrutinising it",
            "auditing it",
            "going piece by piece",
            "looking at each component",
            "dissecting it",
            "going through it line by line",
            "going through it bit by bit",
            "stripping it down",
            "peeling it back",
        ),
        "transcendent_modifier": (
            "unpacking what it really means",
            "breaking down the core of it",
            "looking at what the deepest layer is made of",
            "pulling apart the meaning of it",
            "decomposing the larger structure",
            "examining the meaning piece by piece",
            "going through the underlying purpose part by part",
            "dissecting the bigger picture",
        ),
        "analytical_modifier": (
            "going through the argument step by step",
            "auditing the reasoning",
            "checking each premise",
            "scrutinising the logic",
            "looking at the proof structure",
            "breaking down the argument piece by piece",
            "dissecting the chain of inference",
            "unpacking the argument",
        ),
        "felt_modifier": (
            "unpacking the feeling",
            "breaking down what the feeling is doing",
            "looking at what the affect is made of",
            "auditing the emotional tone",
            "examining the feeling piece by piece",
            "decomposing the felt sense",
            "going through the feelings one at a time",
            "pulling apart the emotional content",
        ),
        "embodied_modifier": (
            "looking at each motion",
            "breaking down the gesture",
            "unpacking the technique",
            "going through each step of the movement",
            "auditing my form",
            "going piece by piece through what my hands are doing",
            "decomposing the physical action",
            "scrutinising the practice",
        ),
    },
    # -----------------------------------------------------------------
    # ^7 Rhythm — repetition / practice / entrainment
    # -----------------------------------------------------------------
    "7": {
        "base": (
            "practice makes perfect",
            "muscle memory",
            "in the groove",
            "you are what you repeatedly do",
            "every day, the same",
            "daily routine",
            "every single day",
            "keep doing it",
            "habit",
            "the rhythm of it",
            "the cadence I've built",
            "the drumbeat of doing it",
            "the loop",
            "the cycle",
            "the same thing over and over",
            "the practice I keep returning to",
        ),
        "transcendent_modifier": (
            "the rhythm of meaning I've cultivated",
            "the larger pattern I keep returning to",
            "the practice that shapes who I'm becoming",
            "the daily ritual that holds the meaning",
            "the cadence of vocation",
            "the practice as a form of devotion",
            "the rhythm of the calling",
            "the repeated act that builds purpose",
        ),
        "analytical_modifier": (
            "the analytical drill I keep running",
            "the reasoning I rehearse",
            "the proof I keep walking through",
            "the same argument every day until it sticks",
            "the chain of thought I drill on",
            "the structured practice of the logic",
            "the repeated sequence of reasoning",
            "the methodical loop",
        ),
        "felt_modifier": (
            "the emotional groove I keep falling into",
            "the same feeling, every time",
            "the affective rhythm I've built",
            "the recurring feeling pattern",
            "the cadence of emotion",
            "the same gut response, day after day",
            "the felt loop",
            "the recurring affect",
        ),
        "embodied_modifier": (
            "muscle memory built up over years",
            "the practice my hands know",
            "what my body has been trained to do",
            "the kinesthetic loop I keep running",
            "drilled-in technique",
            "the somatic rhythm",
            "the way my body falls into it",
            "the bodily cadence",
        ),
    },
    # -----------------------------------------------------------------
    # ^8 Above/Cause — ASSOCIATIVE TRIGGERING (NOT deductive)
    # -----------------------------------------------------------------
    # Anti-drift: NO "therefore", "thus", "it follows that", "q.e.d.",
    # "ergo", "hence", "consequently", "deduce", "deduction". Those
    # belong on a compound (^6 decomposition + ^9 landing). ^8 is
    # association: one thing reminds you of another.
    "8": {
        "base": (
            "that reminds me",
            "reminds me of",
            "made me think of",
            "one thing led to another",
            "triggered a memory",
            "set me off thinking about",
            "called to mind",
            "brought to mind",
            "made me remember",
            "got me thinking about",
            "kicked off the thought of",
            "started me on",
            "linked in my head to",
            "summoned up",
            "set off the chain of associations to",
            "conjured up",
        ),
        "transcendent_modifier": (
            "reminded me of the larger picture",
            "called to mind the meaning of",
            "set off a chain of association toward the deeper sense",
            "brought the bigger arc to mind",
            "linked, in my head, to the purpose of it",
            "summoned the wider meaning",
            "made me think about what it all points at",
            "called up the encompassing idea",
        ),
        "analytical_modifier": (
            "made me think of the argument that",
            "reminded me of the proof of",
            "brought to mind the reasoning that",
            "called up the chain of thought about",
            "set off the explicit thinking about",
            "associated, in my head, with the case for",
            "got me thinking through the logic of",
            "linked to the explicit chain of reasoning about",
        ),
        "felt_modifier": (
            "made me feel the way I felt about",
            "reminded me of the feeling of",
            "stirred the same emotion as",
            "brought back the felt sense of",
            "triggered the affect that goes with",
            "set off the same emotional response as",
            "conjured the feeling of",
            "called up the mood of",
        ),
        "embodied_modifier": (
            "reminded my body of",
            "made my hands remember",
            "set off the same bodily reaction as",
            "brought back the kinesthetic memory of",
            "called up the muscle memory of",
            "linked, in my body, to the act of",
            "triggered the same somatic response as",
            "summoned the same physical pattern as",
        ),
    },
    # -----------------------------------------------------------------
    # ^9 Below/Effect — the surfaced thought; "popped into my head"
    # -----------------------------------------------------------------
    "9": {
        "base": (
            "popped into my head",
            "out of nowhere I thought of",
            "the thought came to me",
            "it just clicked",
            "came to mind",
            "a thought surfaced",
            "an idea showed up",
            "the idea arrived",
            "what arrived in my head was",
            "what landed was",
            "an answer came",
            "the conclusion that surfaced was",
            "what came up was",
            "what dropped in was",
            "the thing that arose was",
            "what came forward was",
        ),
        "transcendent_modifier": (
            "what arrived was the deeper sense that",
            "what landed was the meaning that",
            "what surfaced was the bigger picture that",
            "the thought that arose was about the purpose of",
            "what dropped in was the larger arc",
            "what came up was the encompassing idea",
            "the conclusion that arrived was the deeper read",
            "what showed up was the meaning",
        ),
        "analytical_modifier": (
            "the conclusion arrived",
            "the answer surfaced",
            "the proof clicked",
            "the explicit answer came",
            "what landed was the formal answer",
            "what came up was the precise conclusion",
            "what arrived was the analytic resolution",
            "the case finally clicked",
        ),
        "felt_modifier": (
            "the feeling arrived",
            "the affect surfaced",
            "the emotion came forward",
            "what showed up was the feeling that",
            "what landed was a felt sense of",
            "the gut response arrived",
            "what came up was the mood of",
            "the affect dropped in",
        ),
        "embodied_modifier": (
            "the answer came in my body",
            "the gesture arrived",
            "my hands knew what to do",
            "the body landed on it",
            "what showed up was a movement",
            "the kinesthetic answer came",
            "the action surfaced",
            "the body delivered the answer",
        ),
    },
}


# ---------------------------------------------------------------------------
# Domain flavor markers
# ---------------------------------------------------------------------------
#
# Domain flavor is woven into a sentence as background colouring. The
# generator picks one or two markers per surface, ideally in a way
# compatible with the chosen Noetic phrase (e.g. "principle" pairs
# naturally with ^3|T or ^2|T; "doing" pairs naturally with ^7|E).
DOMAIN_FLAVOR: Final[dict[str, tuple[str, ...]]] = {
    "P": (
        "principle",
        "should",
        "ought to",
        "ethics",
        "what's right",
        "what's wrong",
        "the moral of it",
        "duty",
        "obligation",
        "the right thing to do",
        "fairness",
        "justice",
        "the principled answer",
        "what we owe each other",
        "the ethical case",
    ),
    "C": (
        "thinking",
        "the way I understand it",
        "the concept",
        "make sense of",
        "the idea behind it",
        "the way it parses",
        "the reasoning",
        "the way I read it",
        "the cognitive shape",
        "knowledge",
        "the mental model",
        "the framework",
        "what I understand",
        "the conceptual map",
        "the way it fits in my head",
    ),
    "E": (
        "feel",
        "feels",
        "feeling about",
        "react to",
        "respond to",
        "evaluate",
        "good or bad",
        "the way I take it",
        "the affective read",
        "how I feel about it",
        "value-laden",
        "judgment about",
        "the gut take",
        "the verdict",
        "the emotional read",
    ),
    "O": (
        "doing",
        "performing",
        "executing",
        "the practice",
        "running it",
        "carrying it out",
        "the action",
        "the workflow",
        "the procedure",
        "step by step in practice",
        "actually doing it",
        "in the field",
        "in the doing of it",
        "the operational reality",
        "in practice",
    ),
}


# ---------------------------------------------------------------------------
# Drive flavor markers
# ---------------------------------------------------------------------------
#
# The 7 Core Drives. Each Drive carries a short bag of markers the
# generator can sprinkle into a sentence to evoke the underlying
# motivational architecture without naming it.
DRIVE_FLAVOR: Final[dict[str, tuple[str, ...]]] = {
    "F1": (
        "tying it together",
        "wholeness",
        "unifying",
        "integrating",
        "as one whole",
        "all of a piece",
        "in unity with",
        "as a coherent whole",
        "everything pulling together",
    ),
    "F2": (
        "wisdom",
        "deep understanding",
        "grasping fully",
        "seeing the whole truth of it",
        "with a wise read",
        "knowing the depth of it",
        "the mature read",
        "with insight",
        "wisely",
    ),
    "F3": (
        "alive to it",
        "vital",
        "energy",
        "with vigor",
        "feeling vital around it",
        "with a spark",
        "alive in the doing",
        "lively",
        "with juice",
        "with full life force",
    ),
    "F4": (
        "in connection with",
        "in relationship",
        "tied to other people",
        "bonded with",
        "rooted in connection",
        "with someone close",
        "in the company of",
        "intimately",
        "with attachment",
        "with people I'm bonded to",
    ),
    "F5": (
        "agency",
        "with control",
        "by my own hand",
        "of my own choice",
        "wielding it myself",
        "in command of it",
        "making the call",
        "owning the move",
        "deciding it myself",
        "sovereignly",
    ),
    "F6": (
        "structure",
        "by the rules",
        "with discipline",
        "in good order",
        "framework",
        "system",
        "procedure",
        "orderly",
        "with a clear structure",
        "structured",
    ),
    "F7": (
        "purpose",
        "toward the goal",
        "with a clear why",
        "for a reason",
        "with a mission",
        "aimed at something",
        "with intention",
        "purposefully",
        "with a clear destination",
        "with the aim of",
    ),
}


# ---------------------------------------------------------------------------
# Register-level connective phrasing
# ---------------------------------------------------------------------------
#
# Used by the surface generator to choose a sentence frame consistent
# with the operating Register. These appear at the FRONT of a generated
# sentence, ahead of the Noetic phrase.
REGISTER_FRAMES: Final[dict[str, tuple[str, ...]]] = {
    "T": (
        "At the level of meaning,",
        "Looking at the whole arc,",
        "In the bigger picture,",
        "Where it really matters,",
        "From where I stand on this,",
        "Stepping back to the deepest read,",
        "From the meaning of it,",
        "When I take in the larger sense,",
    ),
    "A": (
        "Working through this carefully,",
        "When I think it through,",
        "Step by step,",
        "Reasoning it out,",
        "Laying out the logic,",
        "Walking the chain of thought,",
        "When I sit and reason about it,",
        "On reflection,",
    ),
    "f": (
        "Feeling into it,",
        "Sitting with how it feels,",
        "Honestly,",
        "On the gut level,",
        "Where the feeling sits,",
        "When I check the feeling,",
        "From the gut,",
        "Where the affect lands,",
    ),
    "E": (
        "In the body,",
        "Where my hands meet it,",
        "When I actually do it,",
        "In the doing,",
        "Where I physically engage with it,",
        "On the floor, in practice,",
        "When my body is on the line,",
        "Out in the actual movement,",
    ),
}


# ---------------------------------------------------------------------------
# Compound / structural commentary
# ---------------------------------------------------------------------------
#
# Templates the generator uses to glue multiple primitives together.
# Each phrase contains zero or more ``{slot}`` placeholders the
# generator will fill in.

COPRESENCE_CONJUNCTIONS: Final[tuple[str, ...]] = (
    "and at the same time",
    "and alongside that",
    "and also",
    "while at the same time",
    "and on top of that",
    "and there's another track running where",
    "and concurrently",
    "and right next to that",
    "and in parallel",
    "and side by side with that",
)


INTEGRATION_OPENERS: Final[tuple[str, ...]] = (
    "When I bring all of it together,",
    "Pulling it into a single shape,",
    "When all of these come together at once,",
    "Where all those tracks fuse,",
    "When I let everything merge,",
    "When the whole thing crystallises,",
    "When I let those layers settle into one thing,",
    "Where it all integrates,",
)


INTEGRATION_RESULT_PHRASES: Final[tuple[str, ...]] = (
    "I find myself arriving at {result}",
    "what emerges is {result}",
    "what comes out the other side is {result}",
    "the integrated state is {result}",
    "I land on {result}",
    "the unified read is {result}",
    "the fused state is {result}",
    "what crystallises is {result}",
)


OMEGA_NAMES: Final[dict[str, str]] = {
    "Omega_refusal": "a clear, principled refusal",
    "Omega_aversion": "a settled, integrated aversion",
    "Omega_aversion_overflow": "a kind of aversion that has spilled past its target",
    "Omega_clarity": "a sense of clarity",
    "Omega_presence": "a sense of being truly present",
    "Omega_grounded_creative_insight": "a grounded creative insight",
    "Omega_creative_insight": "a creative insight",
    "Omega_resolve": "a settled resolve",
    "Omega_grace_under_pressure": "a kind of grace under pressure",
    "Omega_acceptance": "a deep acceptance",
    "Omega_default": "a unified emergent state",
}


def normalise_omega_name(raw: str) -> str:
    """Normalise the assorted Omega-token spellings into a lookup key.

    Accepts ``Ω_clarity``, ``Omega_clarity``, ``omega_clarity`` and
    related variants and returns the canonical ``Omega_clarity`` form
    used by ``OMEGA_NAMES``. Returns the input untouched if no rule
    fires.
    """
    if not raw:
        return raw
    s = raw.strip()
    # Replace the Greek capital omega with the Latin spelling.
    s = s.replace("Ω", "Omega")
    # Collapse a leading underscore introduced by the regex match.
    if s.startswith("_"):
        s = "Omega" + s
    # Title-case the first character so we hit ``Omega_*`` keys.
    if s.lower().startswith("omega"):
        s = "Omega" + s[5:]
    return s


# Recipe / production semantics — used when an expression contains
# ``Theta(Omega_*) = ... -> Omega_*`` or any production-target marker.
RECIPE_OPENERS: Final[tuple[str, ...]] = (
    "What goes into producing {target} is",
    "The recipe for {target} reads roughly:",
    "To get to {target}, what's mixing in is",
    "The way {target} comes about is by combining",
    "The ingredients for {target} are",
    "What it takes to land on {target} is",
)


RECIPE_INGREDIENT_CONJUNCTIONS: Final[tuple[str, ...]] = (
    "plus",
    "and",
    "together with",
    "alongside",
    "combined with",
    "mixed with",
)


RECIPE_LEAKAGE_PHRASES: Final[tuple[str, ...]] = (
    "with a small amount of {leakage} spilling out the side",
    "with a little bit of {leakage} as a side effect",
    "and a trickle of {leakage} as a side reaction",
    "with some {leakage} as a side product",
    "and a bit of {leakage} bleeding out",
)


# Meta-logic / typed cluster phrasing — used for ``NoeticCluster{...}``,
# ``StateCluster{...}``, ``Product(...)``, ``CoverOf(...)``, etc.
META_LOGIC_OPENERS: Final[tuple[str, ...]] = (
    "Looking at the whole family of moves here,",
    "Considering the cluster of cognitive moves at play,",
    "Thinking about the set of moves involved,",
    "Stepping back to the structural level,",
    "From a structural standpoint,",
    "Reading this as a cluster of moves,",
)


META_LOGIC_RELATION_PHRASES: Final[dict[str, tuple[str, ...]]] = {
    "intersection": (
        "what they have in common is",
        "the overlap is",
        "where they meet is",
        "what's shared is",
    ),
    "union": (
        "the combined set is",
        "what you get when you take them all together is",
        "the union of those moves is",
        "rolled up into one set,",
    ),
    "difference": (
        "what's in the first but not the second is",
        "the residual after subtracting is",
        "what one has and the other doesn't is",
        "the asymmetric remainder is",
    ),
    "product": (
        "the cross-combination is",
        "every pairing of those is",
        "the full grid you get from crossing them is",
        "the product set is",
    ),
    "cover": (
        "what covers all of those is",
        "the covering family is",
        "the umbrella over all of them is",
        "the structure that spans them all is",
    ),
    "partition": (
        "the way they split into separate buckets is",
        "the partition of that set is",
        "they break into these mutually-exclusive buckets",
        "the partition reads",
    ),
}


# Lightweight reusable connective tissue.
SENTENCE_CONNECTIVES: Final[tuple[str, ...]] = (
    "—",
    "—",
    ":",
    ".",
    ",",
    ";",
)


__all__ = [
    "NOETIC_NAMES",
    "REGISTER_NAMES",
    "DOMAIN_NAMES",
    "DRIVE_NAMES",
    "NOETIC_LEXICON",
    "DOMAIN_FLAVOR",
    "DRIVE_FLAVOR",
    "REGISTER_FRAMES",
    "COPRESENCE_CONJUNCTIONS",
    "INTEGRATION_OPENERS",
    "INTEGRATION_RESULT_PHRASES",
    "OMEGA_NAMES",
    "normalise_omega_name",
    "RECIPE_OPENERS",
    "RECIPE_INGREDIENT_CONJUNCTIONS",
    "RECIPE_LEAKAGE_PHRASES",
    "META_LOGIC_OPENERS",
    "META_LOGIC_RELATION_PHRASES",
    "SENTENCE_CONNECTIVES",
]
