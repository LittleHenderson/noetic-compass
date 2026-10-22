"""CAS-side token list of the CAS-token translator (CTT-1). Standard library only.

What it is, in plain words
--------------------------
The translator writes CAS records as a sequence of tokens. This file is the closed list of those tokens. It holds:

  1. state literals    Noetics ^0..^9, Domains ^P ^C ^E ^O (one spelling: shorthand C2 and CO-2 are normalized to
                       ^2 ^C before training), Drives F1..F7 with `_{` `}`, Registers |T |A |f |E
  2. register sets     |⟨ , ⟩ and the emergent label |Ω  (CAS v7.7, Clarification 10)
  3. operators         + - × * · / ÷ ∘ → ← ↔ = ( ) ; and the rest of the compiler's punctuation
  4. recipes (v7.6)    Θ Ω Ω_ Λ κ ι η S Y_T Y_A and the bare condition bar |
  5. META-LOGIC        let fn use export, the 19 type names, every typed meta-set constructor, every tuple
                       constructor, every builtin, the set operators ∪ ∩ ∖ ∈ ∉ ⊂ ⊆ ⊃ ⊇ ∅, the meta sets
                       (Noetics ... Foundation_1..7, EmptySet, Worlds alias), RPM
  6. COGNITIVE FRACTALS and NESTING   Φ⟨ with the digits 0..9 and `:` and ⟩, ∘ composition; INPUT-ONLY nesting tags
                       as the newest compiler computes them (schema cas.nesting/0.2): orbit classes, term roles and
                       the named open questions N1..N13 (never settled by the model)
  7. CAS-Ohm           ohm_scale ohm_drive ohm_attention ohm_constraint ohm_flow ohm_required_drive
                       ohm_effective_constraint (INPUT-ONLY)
  8. HELM's records    turn forms, the reader's question codes, record words (STOCK ABSENT TOPIC WITNESS MADE
                       RAN_OUT ADD ASKED), Lacunarity states, provenance, valence, cube kinds and faces, the faces
                       triad, ASOM, stations, acts, the 10 voice situations (reserved for the parked mouth)
  9. slot pointers     ⟦q1⟧..⟦q16⟧ amounts, ⟦n1⟧..⟦n32⟧ words, ⟦c1⟧..⟦c8⟧ dialogue records

There are NO digits for amounts and NO ingredient or product names on the output side: the translator points at the
user's own words and a deterministic filler outside this module copies them.

The memory note "token enum must include meta-logic + fractals" (forgotten twice before) is enforced by
tests_ctt/test_cas_vocab.py, which reads BOTH compilers' source text and fails if any token kind, type name,
constructor, builtin, meta set or nesting class is missing here.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

VOCAB_VERSION = "ctt-cas-vocab-v1 (2026-10-19)"

NOETICS = ["^%d" % i for i in range(10)]
DOMAINS = ["^P", "^C", "^E", "^O"]
DOMAIN_LETTERS = ["P", "C", "E", "O"]                 # bare meta symbols (e.g. inside Tuple{...})
DRIVES = ["F%d" % i for i in range(1, 8)]
DRIVE_BRACES = ["_{", "}"]
REGISTERS = ["|T", "|A", "|f", "|E"]
REGISTER_LETTERS = ["T", "A", "f"]                    # bare meta symbols; "E" is shared with the Domain letter
REGISTER_SET = ["|⟨", ",", "⟩", "|Ω"]

OPERATORS = ["+", "-", "×", "*", "·", "/", "÷", "∘", "→", "←", "↔", "=", "(", ")", ";", "{", "[", "]", ":",
             "⟨", "^", "_", '"']
RECIPE = ["Θ", "Ω", "Ω_", "Λ", "κ", "ι", "η", "S", "Y_T", "Y_A", "|"]

META_KEYWORDS = ["let", "fn", "use", "export", "RPM"]
TYPE_NAMES = ["any", "state", "drive", "string", "void", "function", "fractal", "rpm", "relation", "program",
              "number", "tuple", "meta_set", "meta_symbol", "meta_assertion", "ohm_scale", "ohm_drive",
              "ohm_attention", "ohm_constraint"]
TYPED_META_SET_CONSTRUCTORS = ["Set", "MetaSet", "NoeticSet", "NoeticCluster", "Cluster", "StateSet",
                               "StateCluster", "StateVariantSet", "StateVariantCluster", "RelationSet",
                               "RelationCluster", "DriveSet", "DomainSet", "RegisterSet", "FoundationSet",
                               "SubFoundationSet"]
TUPLE_CONSTRUCTORS = ["Tuple", "Coordinate", "CASTuple", "CASCoordinate"]
BUILTINS = ["dominant_state", "dominant_domain", "dominant_operator", "compose", "rpm_of", "fractal", "Pullback",
            "Product", "Union", "Intersection", "Difference", "CoverOf", "PartitionOf"]
META_SETS = ["Noetics", "Domains", "Drives", "Registers", "States", "Foundations", "SubFoundations", "EmptySet",
             "Worlds", "DriveRegisterPositions", "SubFoundationPositions"] + ["Foundation_%d" % i for i in range(1, 8)]
SET_OPERATORS = ["∪", "∩", "∖", "∈", "∉", "⊂", "⊆", "⊃", "⊇", "∅"]

FRACTAL = ["Φ⟨"] + [str(d) for d in range(10)]       # Φ⟨1:2:3⟩ = "Φ⟨" "1" ":" "2" ":" "3" "⟩"
NESTING_TAGS = (["NEST:stabilizing", "NEST:amplifying", "NEST:oscillatory", "NEST:NOT_DECIDED_BY_THE_BOOK",
                 "NEST:role:only_term", "NEST:role:innermost", "NEST:role:governing", "NEST:role:middle",
                 "NEST:cross_domain"] + ["NEST:N%d" % i for i in range(1, 14)])
CAS_OHM = ["ohm_flow", "ohm_required_drive", "ohm_effective_constraint"]   # ohm_scale/drive/... are TYPE_NAMES too

TURN_FORMS = ["ANSWER", "ACK", "CLARIFY", "REFUSE_CLAIM", "REFUSE", "CLOSE", "NOT_MINE"]
RECORD_WORDS = ["STOCK", "ABSENT", "TOPIC", "WITNESS", "MADE", "RAN_OUT", "ADD", "ASKED", "UNIT"]
#: the reader's own question codes (helm_english_in.py, read 2026-10-19); test_cas_vocab checks the reader for more
CLARIFY_CODES = ["APPROXIMATE", "BATCH_NEEDS_MADE", "BATCH_NEEDS_PRODUCT", "BATCH_NEEDS_RAN_OUT",
                 "BATCH_NEEDS_STOCK", "BATCH_TWO_RAN_OUT", "CONTRADICTION", "CONVERSION_REFUSED", "MULTIPLE_PRODUCTS",
                 "NEGATED_AMOUNT", "NO_INGREDIENT_NAMED", "NO_NUMBER", "PRODUCT_AS_STOCK", "RELATIVE_AMOUNT",
                 "ROUND_TRIP_FAILED", "STATED_RECIPE", "UNIT_MISMATCH", "UNKNOWN_INGREDIENT", "UNKNOWN_PRODUCT",
                 "WHAT_IF", "WHAT_IF_ABSENT", "WHICH_PRODUCT"]
HELM_MISC = (["COVERED", "LACUNA", "FADED", "UNKNOWN", "USER_SAID", "AUTHORED", "CHECKED", "NONE", "ASSERTED",
              "DENIED", "POSITIVE", "NEGATIVE", "NEUTRAL", "concept", "instance", "event", "procedure", "directive"]
             + ["face_%d" % i for i in range(1, 7)]
             + ["Purpose", "Wisdom", "Power", "Rising", "Peak", "Waning", "Absent"]
             + ["Starved", "Aligned", "Oversaturated", "Misaligned"]
             + ["S%d" % i for i in range(7)]
             + ["statement", "question", "offer"]
             + ["SIT:success", "SIT:blocked_missing", "SIT:cant_determine", "SIT:dont_know", "SIT:clarify",
                "SIT:refused", "SIT:learned", "SIT:repaired", "SIT:never_learned", "SIT:faded"])

SLOTS_Q = ["⟦q%d⟧" % i for i in range(1, 17)]
SLOTS_N = ["⟦n%d⟧" % i for i in range(1, 33)]
SLOTS_C = ["⟦c%d⟧" % i for i in range(1, 9)]

#: tokens the translator may READ but never WRITE (masked out of every output)
INPUT_ONLY = set(NESTING_TAGS) | set(CAS_OHM) | {"ohm_scale", "ohm_drive", "ohm_attention", "ohm_constraint"}

CATEGORIES: List[Tuple[str, List[str]]] = [
    ("1_state_literals", NOETICS + DOMAINS + DOMAIN_LETTERS + DRIVES + DRIVE_BRACES + REGISTERS + REGISTER_LETTERS),
    ("2_register_multiplicity", REGISTER_SET),
    ("3_operators", OPERATORS),
    ("4_recipes", RECIPE),
    ("5_meta_logic", META_KEYWORDS + TYPE_NAMES + TYPED_META_SET_CONSTRUCTORS + TUPLE_CONSTRUCTORS + BUILTINS
     + META_SETS + SET_OPERATORS),
    ("6_cognitive_fractals_and_nesting", FRACTAL + NESTING_TAGS),
    ("7_cas_ohm", CAS_OHM),
    ("8_helm_records", TURN_FORMS + RECORD_WORDS + CLARIFY_CODES + HELM_MISC),
    ("9_slot_pointers", SLOTS_Q + SLOTS_N + SLOTS_C),
]


def cas_tokens() -> List[str]:
    """The ordered, de-duplicated CAS-side token list (first category wins for a shared surface)."""
    out: List[str] = []
    seen = set()
    for _name, toks in CATEGORIES:
        for t in toks:
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out


def category_of() -> Dict[str, str]:
    out: Dict[str, str] = {}
    for name, toks in CATEGORIES:
        for t in toks:
            out.setdefault(t, name)
    return out


#: compiler TokenKind -> the CTT tokens that carry it (EOF is the end-of-sequence special)
TOKENKIND_MAP: Dict[str, List[str]] = {
    "EXPORT": ["export"], "LET": ["let"], "FN": ["fn"], "USE": ["use"], "CO": NOETICS, "NOETIC": NOETICS,
    "STATE_REF": NOETICS + DOMAINS, "DOMAIN": DOMAINS + DOMAIN_LETTERS, "DRIVE": DRIVES, "REGISTER": REGISTERS,
    "RPM": ["RPM"], "PHI": ["Φ⟨"], "IDENT": TYPE_NAMES + TYPED_META_SET_CONSTRUCTORS + TUPLE_CONSTRUCTORS + BUILTINS
    + META_SETS + REGISTER_LETTERS + SLOTS_N, "STRING": ['"'] + SLOTS_N, "NUMBER": SLOTS_Q + FRACTAL[1:],
    "PLUS": ["+"], "MINUS": ["-"], "TIMES": ["×", "*", "·"], "DIVIDE": ["/", "÷"], "CIRC": ["∘"], "ARROW": ["→"],
    "LARROW": ["←"], "BIARROW": ["↔"], "MEMBER": ["∈"], "NOT_MEMBER": ["∉"], "SUBSET": ["⊂"], "SUBSET_EQ": ["⊆"],
    "SUPERSET": ["⊃"], "SUPERSET_EQ": ["⊇"], "UNION": ["∪"], "INTERSECTION": ["∩"], "SET_DIFF": ["∖"],
    "EMPTY_SET": ["∅"], "CARET": DOMAINS + ["^"], "UNDERSCORE": ["_", "_{", "Ω_"], "LBRACE": ["{", "_{"],
    "RBRACE": ["}"], "LPAREN": ["("], "RPAREN": [")"], "LANGLE": ["⟨", "Φ⟨", "|⟨"], "RANGLE": ["⟩"], "COLON": [":"],
    "COMMA": [","], "EQUALS": ["="], "LBRACKET": ["["], "RBRACKET": ["]"], "SEMI": [";"], "THETA": ["Θ"],
    "OMEGA": ["Ω", "Ω_", "|Ω"], "LAMBDA_TOK": ["Λ"], "KAPPA_TOK": ["κ"], "IOTA_TOK": ["ι"], "ETA_TOK": ["η"],
    "CDOT": ["·"], "STATE_VECTOR": ["S"], "YIELD_T": ["Y_T"], "YIELD_A": ["Y_A"], "PIPE": ["|", "|⟨"],
    "EOF": ["[EOS]"],
}

#: compiler keyword IDENTs that are vocabulary, not pointers
KEYWORD_IDENTS = set(TYPE_NAMES + TYPED_META_SET_CONSTRUCTORS + TUPLE_CONSTRUCTORS + BUILTINS + META_SETS
                     + CAS_OHM)
