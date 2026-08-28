"""CAS ontology primitives for the CAS Reasoning Runtime (CAS-RR v0.1).

Typed, frozen reference tables. No behavior lives here.

Namespaces (kept separate by design - CAS-RR v0.1 spec, Ch. 5):

* ^0..^9     Noetics - authoritative definitions, verbatim canonical.
* P/C/E/O    Domains - structural precedence tiers.
* DF1..DF7   CAS Drive rails (F1 Unity ... F7 Purpose) - why a local
             cognitive operation is moving.
* TF1..TF7   TKS Foundation goal engines - position-matched to the Drive
             rails, but a SEPARATE namespace: they are desired classes
             of outcome, not local drive rails.
* TF1a..TF7d the 28 sub-foundation channels (a Spiritual, b Mental,
             c Emotional, d Physical) = 7 engines x 4 transmission modes.
* A_root + D1-D7 + W1-W7 + P1-P7 = 22 acquisition pathways.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Noetics (authoritative, verbatim canonical definitions)
# --------------------------------------------------------------------------
NOETICS = {
    "^0": ("Idea", "All things in and outside the Mind."),
    "^1": ("Mind", "Various degrees of awareness that processes, stores, outputs, and intakes Ideas."),
    "^2": ("Positive", "An Idea the Mind has an affinity for and is attracted toward."),
    "^3": ("Negative", "An Idea the Mind is adverse to and repelled by."),
    "^4": ("Vibration", "The degree to which an Idea resonates with the Mind, its impression."),
    "^5": ("Female", "A Mind impregnated with an Idea, the Ideas a Mind is composed of."),
    "^6": ("Male", "An Idea impregnated with another Idea, the Ideas an Idea is composed of."),
    "^7": ("Rhythm", "The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it."),
    "^8": ("Above/Cause", "An Idea that triggers a different Idea than itself to come to Mind."),
    "^9": ("Below/Effect", "The Idea brought to Mind by an Above/Cause trigger."),
}

# --------------------------------------------------------------------------
# Domains (structural precedence tiers)
# --------------------------------------------------------------------------
DOMAINS = ("P", "C", "E", "O")
DOMAIN_DESCENT = ("P", "C", "E", "O")  # causation graph; O -> P is feedback only
DOMAIN_PRECEDENCE = {"P": 0, "C": 1, "E": 2, "O": 3}

# --------------------------------------------------------------------------
# CAS Drive rails (DF namespace)
# --------------------------------------------------------------------------
DRIVES = {
    "F1": "Unity",
    "F2": "Wisdom",
    "F3": "Vitality",
    "F4": "Connection",
    "F5": "Agency",
    "F6": "Structure",
    "F7": "Purpose",
}
DRIVE_INVERSIONS = {1: 7, 7: 1, 2: 6, 6: 2, 3: 5, 5: 3}  # F4 self-dual

# --------------------------------------------------------------------------
# Registers (CAS v7.5) and their World correspondence (a/b/c/d)
# --------------------------------------------------------------------------
REGISTERS = ("T", "A", "f", "E")
WORLDS = ("a", "b", "c", "d")
WORLD_NAMES = {
    "a": "Spiritual / ideal",
    "b": "Mental / model",
    "c": "Emotional / value",
    "d": "Physical / execution",
}
# TKS World position <-> CAS Register position (translation key, position-matched).
WORLD_REGISTER = {"a": "T", "b": "A", "c": "f", "d": "E"}
REGISTER_WORLD = {"T": "a", "A": "b", "f": "c", "E": "d"}

# --------------------------------------------------------------------------
# TKS Foundation goal engines (TF namespace)
# --------------------------------------------------------------------------
FOUNDATIONS = {
    "TF1": "Association or Unity",
    "TF2": "Wisdom",
    "TF3": "Life",
    "TF4": "Companionship",
    "TF5": "Power",
    "TF6": "Wealth or Material Resources",
    "TF7": "Continuation or Reproduction",
}
# Position-matched CAS drive rails. Structural cross-validation, NOT identity:
# the Foundations are goal engines; the Drives are local rails.
FOUNDATION_POSITION_DRIVE = {f"TF{m}": f"F{m}" for m in range(1, 8)}

# The 28-channel matrix: 7 engines, each with 4 transmission modes.
CHANNEL_TITLES = {
    "TF1a": "Abstract unification", "TF1b": "Concept grouping",
    "TF1c": "Affective synchrony", "TF1d": "Material continuity",
    "TF2a": "Ideal ordering", "TF2b": "Mental models",
    "TF2c": "Felt coherence", "TF2d": "Physical constraints",
    "TF3a": "Essential vitality", "TF3b": "Motivation",
    "TF3c": "Emotional animation", "TF3d": "Biological or kinetic activation",
    "TF4a": "Relational archetypes", "TF4b": "Social cognition",
    "TF4c": "Bonding and empathy", "TF4d": "Interaction pathways",
    "TF5a": "Abstract intention", "TF5b": "Strategy",
    "TF5c": "Assertion and boundaries", "TF5d": "Force or physical expression",
    "TF6a": "Ideal resource flow", "TF6b": "Resource models",
    "TF6c": "Valuation and attachment", "TF6d": "Physical resources",
    "TF7a": "Pattern perpetuation", "TF7b": "Future projection",
    "TF7c": "Desire momentum", "TF7d": "Reproduction and survival",
}
CHANNELS = tuple(f"TF{m}{w}" for m in range(1, 8) for w in WORLDS)

# --------------------------------------------------------------------------
# Foundation-to-Drive adapter.
#
# Each sub-foundation channel "routes toward" a mixture of CAS drive rails.
# The arrow means routing, not identity (spec Ch. 5.4).
# --------------------------------------------------------------------------
DRIVE_ADAPTER = {
    "TF1a": {"F1": 0.6, "F7": 0.4}, "TF1b": {"F1": 0.6, "F2": 0.4},
    "TF1c": {"F1": 0.6, "F4": 0.4}, "TF1d": {"F1": 0.6, "F6": 0.4},
    "TF2a": {"F2": 0.6, "F7": 0.4}, "TF2b": {"F2": 1.0},
    "TF2c": {"F2": 0.6, "F4": 0.4}, "TF2d": {"F2": 0.6, "F6": 0.4},
    "TF3a": {"F3": 0.6, "F1": 0.4}, "TF3b": {"F3": 0.6, "F5": 0.4},
    "TF3c": {"F3": 0.6, "F4": 0.4}, "TF3d": {"F3": 1.0},
    "TF4a": {"F4": 0.6, "F7": 0.4}, "TF4b": {"F4": 0.6, "F2": 0.4},
    "TF4c": {"F4": 1.0}, "TF4d": {"F4": 0.6, "F5": 0.4},
    "TF5a": {"F5": 0.6, "F7": 0.4},
    "TF5b": {"F2": 0.35, "F5": 0.45, "F6": 0.20},   # strategy: Wisdom + Agency + Structure
    "TF5c": {"F5": 1.0}, "TF5d": {"F5": 0.6, "F3": 0.4},
    "TF6a": {"F6": 0.6, "F7": 0.4}, "TF6b": {"F6": 0.6, "F2": 0.4},
    "TF6c": {"F6": 0.6, "F4": 0.4},
    "TF6d": {"F3": 0.20, "F5": 0.35, "F6": 0.45},   # physical resources: Vitality + Agency + Structure
    "TF7a": {"F7": 1.0},
    "TF7b": {"F2": 0.40, "F7": 0.60},               # future projection: Wisdom + Purpose
    "TF7c": {"F7": 0.6, "F3": 0.4}, "TF7d": {"F7": 0.6, "F6": 0.4},
}

# --------------------------------------------------------------------------
# Acquisitions: the 22 capability pathways.
#
# Source-grounded root label (docs/cas_rr/SOURCE_GROUNDING_NOTES.md,
# claim M): the book (Ch. 8) and TKS v7.4 use "A0"; TKS v6.1 uses "A1".
# "A22" appears NOWHERE in any checked source - 22 is the COUNT
# (A_root + D1-D7 + W1-W7 + P1-P7), not an index label. The runtime
# therefore names the root A_root internally and records the aliases.
# Freezing the canonical label is Gate 0 of the development plan.
# --------------------------------------------------------------------------
ACQUISITION_ROOT = "A_root"
ACQUISITION_ROOT_ALIASES = ("A0", "A22")
DESIRES = tuple(f"D{m}" for m in range(1, 8))
WISDOMS = tuple(f"W{m}" for m in range(1, 8))
POWERS = tuple(f"P{m}" for m in range(1, 8))
ACQUISITIONS = (ACQUISITION_ROOT,) + DESIRES + WISDOMS + POWERS  # 22 total

# Prerequisite sufficiency threshold (authored design quantity, spec Ch. 11).
SUFFICIENCY_THRESHOLD = 0.6

# --------------------------------------------------------------------------
# Gain regimes of the Reasoning Integrity Spine (spec Ch. 9).
#
# Ambition may choose the question. It must not choose the answer.
# --------------------------------------------------------------------------
GAIN_CANDIDATE = 1.5   # ^8 generation: moderate - breadth, not fireworks
GAIN_EVAL = 1.0        # ^6 and ^9 evaluation: unity - the truth firewall
GAIN_COMMIT = 2.0      # commitment: high but bounded, with hysteresis
GAIN_LEARN = 0.05      # learning feedback: weak and filtered

# Terminal statuses of a reasoning episode (spec Ch. 12).
TERMINAL = (
    "CONCLUDED",
    "NEEDS_INFORMATION",
    "NEEDS_CAPABILITY",
    "CONFLICT_UNRESOLVED",
    "INADMISSIBLE",
    "RESOURCE_EXHAUSTED",
    "LOOP_LIMIT_REACHED",
)
