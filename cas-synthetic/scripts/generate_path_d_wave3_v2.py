"""Path D Wave 3 v2 — content-preservation rewrite (2026-05-08).

The phase-1 corpus at ``cas-synthetic/data/path_d/wave3_phase1_aggregate_20260508.jsonl``
passed all four numerical anti-drift gates (leakage 0.13%, rejection 2.0%,
chemistry 0%, level-drift 0.07%) but FAILED content-preservation audit on
two of four slots. See:

  cas-synthetic/data/path_d/wave3_phase1_aggregate_20260508.NEEDS_REWORK.md
  docs/working/wave3_generator_codebase_map_2026_05_08.md
  user memory: feedback_anti_drift_gates_not_content_preservation.md

Defects fixed by this module:

1. ``english_to_cas`` was 100% verbatim copy. The phase-1 prompt embedded
   the source CAS as a "reference target" and asked the model not to paste
   it. Fix: this module's ``english_to_cas`` prompt takes ONLY a
   pre-generated English description (Wave 2.5 artifact) — there is no CAS
   to copy. An anti-copy guard at validation time catches edge cases.

2. ``invalid_to_corrected`` had ~30% unrelated-correction. Fix: the
   corrected-expression prompt asks the model for the SMALLEST POSSIBLE
   EDIT, includes a positive example (single-token fix) and a bad example
   (whole-expression rewrite), and the generator runs a Jaccard guard
   against the invalid input (rejects when <0.6, re-rolls up to 3 attempts).

3. ``cas_to_english`` recipes dropped numeric coefficients. Fix: the
   prompt explicitly requires every coefficient (e.g. ``0.7``, ``1.5``)
   and every named ``Ω_*`` target to be reproduced verbatim in the
   English output. A regex-based validator rejects records that drop them.

4. ``cas_to_english`` fractals misread ``Φ⟨k:k:…⟩`` k-values as counts.
   Fix: the prompt explicitly tells the model that each k is an OPERATOR
   INDEX (0-9 selecting one of the 10 Noetics), not a count. A validator
   requires the canonical operator name or colloquialism to appear for
   each k.

This module is **library + CLI** for the Wave 2.5 step (pre-generate
English descriptions) and the v2 prompt builders + validators for Wave 3
phase 2 (paid generation, run by user as a separate decision).

NO API CALLS HAPPEN INSIDE THIS MODULE WITHOUT A USER-PROVIDED CLIENT.
The validators and prompt builders are dry-run-safe and unit-testable.

Per ``feedback_traceability_is_the_whole_purpose.md`` every record produced
by this pipeline carries: ``seed_id``, ``source_cas``,
``prompt_template_version``, ``validators_run``, ``validators_passed``,
``validators_failed_reasons``, ``generated_at``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE_VERSION = "wave3_v2_2026_05_08"
WAVE_2_5_TEMPLATE_VERSION = "wave3_step2_5_v1_2026_05_08"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPILER_PATH = (
    _REPO_ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "notation"
    / "compiler.py"
)


# ---------------------------------------------------------------------------
# Canonical Noetic operator names + colloquialisms (for fractal validation
# and the cas_to_english prompt). Map matches CLAUDE.md and
# feedback_use_canonical_colloquialisms_as_operator_aliases.md.
# ---------------------------------------------------------------------------

NOETIC_NAMES: dict[int, str] = {
    0: "Idea",
    1: "Mind",
    2: "Positive",
    3: "Negative",
    4: "Vibration",
    5: "Female",
    6: "Male",
    7: "Rhythm",
    8: "Above/Cause",
    9: "Below/Effect",
}

# Lower-cased substrings to look for when validating that a fractal k-index
# was rendered. Matching is case-insensitive and substring-based; we accept
# either the operator name or any of its canonical colloquialisms.
NOETIC_VALIDATION_TOKENS: dict[int, tuple[str, ...]] = {
    0: ("idea", "thought", "in your head", "on your mind"),
    1: ("mind", "paying attention", "using your head", "becoming aware",
        "making up your mind"),
    2: ("positive", "drawn to", "drawn toward", "draw toward",
        "draws toward", "draws you toward", "pull toward",
        "pulls toward", "pulled toward", "speaks to", "can't resist",
        "attraction"),
    3: ("negative", "can't stomach", "rubs the wrong way",
        "wouldn't touch", "pushed away", "aversion", "averse",
        "repulsion",
        "turned away", "repelled", "repulsed", "push away",
        "pushes away", "pushed-away", "pushed-away-from", "push-away"),
    4: ("vibration", "hit hard", "struck a chord", "strike a chord",
        "striking a chord", "strikes a chord", "resonated", "resonate",
        "resonates", "resonance", "resonant", "resonating",
        "made an impression", "make an impression", "makes an impression"),
    5: ("female", "sum of", "experiences", "who one is", "shaped by",
        "what makes someone"),
    6: ("male", "unpacking", "unpack", "break down", "breaks down",
        "breaking down", "breaking it down", "broken down", "pulling apart",
        "looking at what's underneath"),
    7: ("rhythm", "practice makes perfect", "practice", "practiced",
        "repeatedly", "second nature", "habitual", "automatic",
        "muscle memory", "in a groove", "getting used to it"),
    8: ("above", "cause", "that reminds", "reminds", "reminds you",
        "reminds me", "trigger", "triggers", "triggered", "triggering",
        "one thing leads", "made me think", "brought to mind",
        "bring to mind"),
    9: ("below", "effect", "popped into mind", "out of nowhere",
        "it just clicked", "just clicked", "the thought came"),
}


# ---------------------------------------------------------------------------
# Compiler loader (matches generate_path_d_wave3_smoke.py pattern).
# ---------------------------------------------------------------------------


def _load_compiler():
    module_name = "cas_synthetic_path_d_wave3_v2_compiler"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _COMPILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load compiler module from {_COMPILER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Shared anti-drift guidance (subset reused from phase 1 with light editing
# for the v2 prompts).
# ---------------------------------------------------------------------------


_PLAIN_LANGUAGE_GUIDANCE_V2 = (
    "Write a concise, plain-English description aimed at a curious adult "
    "reader. Describe the meaning in everyday language. Keep it under 70 "
    "words.\n"
    "\n"
    "STRICT anti-drift rules:\n"
    "- Do NOT use chemistry / physics / biology / finance metaphors. Domain "
    "  letters (P, C, E, O) are abstract abbreviations, never elements.\n"
    "- Do NOT invent cardinalities or counts. Quantify only what the "
    "  expression itself quantifies.\n"
    "- Do NOT invent intensity, strength, weight, or probability quantities. "
    "  Reproduce coefficients faithfully when the expression has them; "
    "  introduce no others. Numeric coefficients (e.g., 0.7, 1.5) are the "
    "  ONLY numbers that may appear in the English.\n"
    "- Stay neutral on emotional valence unless the expression explicitly "
    "  encodes a Positive or Negative operator.\n"
    "- NEVER describe Noetic operators as 'levels' or 'tiers'. Noetic "
    "  indices 0-9 are operator slots in a formal vocabulary, not a "
    "  hierarchy."
)


# Strong, explicit anti-notation block. Added 2026-05-08 after the first paid
# Wave 2.5 preflight (run 20260508T081835Z) accepted 179 records of which 80
# leaked CAS notation: 14 Ω_<name> leaks, 15 ^N^D state-literal leaks, 32
# F[1-7] drive leaks, 17 P/C/E/O domain-letter leaks, 2 register-letter leaks.
# The earlier _PLAIN_LANGUAGE_GUIDANCE_V2 said "do not echo notation" but did
# not provide explicit replacement rules; the model leaked anyway. This block
# names every forbidden token AND the plain-English replacement.
_NO_NOTATION_GUIDANCE_V2 = (
    "NO-NOTATION RULE (load-bearing — overrides any temptation to copy "
    "tokens from the source):\n"
    "\n"
    "The English output must NEVER contain any of these CAS notation tokens. "
    "For each forbidden token, use the plain-English replacement instead.\n"
    "\n"
    "FORBIDDEN — Ω (Greek capital omega):\n"
    "  - Never write Ω anywhere in the English. Never write 'Ω_'.\n"
    "  - Replace with the name STEM (the part after Ω_).\n"
    "  - Example: Ω_alignment → 'the outcome called alignment' or "
    "'named outcome alignment' or simply 'alignment'. NEVER 'Ω_alignment'.\n"
    "\n"
    "FORBIDDEN — state-literal markers ^0 ^1 ^2 ^3 ^4 ^5 ^6 ^7 ^8 ^9:\n"
    "  - Never write a caret followed by a digit. Never write '^N^D'.\n"
    "  - Replace with the operator name or an approved colloquialism (see "
    "colloquialism map below).\n"
    "\n"
    "FORBIDDEN — drive labels F1 F2 F3 F4 F5 F6 F7:\n"
    "  - Never write F followed by a digit as a label.\n"
    "  - Replace with the drive name:\n"
    "      F1 → unity / cohesion\n"
    "      F2 → wisdom / insight\n"
    "      F3 → vitality / energy\n"
    "      F4 → connection / belonging\n"
    "      F5 → agency / self-determination\n"
    "      F6 → structure / order\n"
    "      F7 → purpose / meaning\n"
    "\n"
    "FORBIDDEN — domain letters as labels (P-Domain, C-Domain, E-Domain, "
    "O-Domain, 'domain C', 'the P domain', 'in the O domain'):\n"
    "  - Never use a single letter to label a domain.\n"
    "  - Replace with the domain word:\n"
    "      P → principled / foundational\n"
    "      C → cognitive / mental\n"
    "      E → evaluative / judging\n"
    "      O → operational / behavioral\n"
    "\n"
    "FORBIDDEN — register labels T A f E (when used as register specifiers, "
    "e.g. 'register T', 'the A register', 'across two registers'):\n"
    "  - Never use a single letter to label a register.\n"
    "  - Replace with the register character:\n"
    "      T → transcendent / strategic / big-picture\n"
    "      A → analytical / reasoned / step-by-step\n"
    "      f → affective / felt / emotional\n"
    "      E (register) → embodied / bodily / sensorimotor\n"
    "\n"
    "FORBIDDEN — bare CAS jargon: 'Noetic', 'Noetics', 'RPM', "
    "'compile-time'. Use plain English (operator names from the "
    "colloquialism map, or the descriptive replacements above) instead.\n"
    "\n"
    "FORBIDDEN — the bare nouns 'domain', 'drive', 'register' anywhere in "
    "your output, in any form, regardless of context. These three nouns are "
    "CAS axis names. The validator rejects any reply containing them "
    "(case-insensitive). They appear elsewhere in this prompt for pedagogy "
    "only — your OUTPUT must use the replacements below.\n"
    "  - 'domain' (and 'X-domain', 'X domain') → 'arena' / 'realm' / 'area' "
    "/ 'frame', OR omit and use the domain word alone:\n"
    "      'in cognitive thinking', 'a principled foundation',\n"
    "      'evaluative judgment', 'operational behavior'\n"
    "  - 'drive' (and 'X-drive', 'X drive') → never use this noun. Replace "
    "with verb constructions:\n"
    "      'driven by a need for X', 'with X as the driving need',\n"
    "      'pulled by X', 'pressured by X'\n"
    "    where X is the drive meaning (unity, wisdom, vitality, connection, "
    "agency, structure, purpose).\n"
    "  - 'register' (and 'X-register', 'X register') → never use this noun. "
    "Replace with:\n"
    "      'mode' / 'way of expressing' / 'expressed through X' /\n"
    "      'in an X way'\n"
    "    where X is the register character (transcendent, analytical, "
    "felt, embodied).\n"
    "\n"
    "PRESERVE STRUCTURE THROUGH ORDINARY LANGUAGE, NOT NOTATION. The English "
    "must capture every load-bearing element of the source: every operator, "
    "every coefficient, every named outcome, every domain, every drive, "
    "every register — but expressed in plain English a curious adult could "
    "read aloud. Test: a careful reader of the English alone (with no source "
    "CAS) should be able to reconstruct the same structural commitments."
)


_COLLOQUIALISM_GUIDANCE_V2 = (
    "Approved everyday English phrasings for each Noetic operator (use only "
    "when one fits naturally — NEVER force):\n"
    "- ^0 Idea: 'a thought', 'something on your mind', 'it's all in your head'\n"
    "- ^1 Mind: 'paying attention', 'using your head', 'becoming aware'\n"
    "- ^2 Positive: 'drawn to it', 'speaks to me', 'pulled toward'\n"
    "- ^3 Negative: \"can't stomach it\", 'rubs the wrong way', "
    "'pushed away from'\n"
    "- ^4 Vibration: 'hit hard', 'struck a chord', 'resonated', "
    "'made an impression'\n"
    "- ^5 Female: 'sum of one's experiences', 'who one is', 'shaped by'\n"
    "- ^6 Male: 'unpacking an idea', 'breaking it down', 'pulling apart "
    "the argument'\n"
    "- ^7 Rhythm: 'practice makes perfect', 'muscle memory', 'in a groove'\n"
    "- ^8 Above/Cause: 'that reminds me', 'triggered a memory', "
    "'one thing leads to another'\n"
    "- ^9 Below/Effect: 'popped into mind', 'out of nowhere', "
    "'it just clicked'\n"
    "\n"
    "Rules:\n"
    "- Preserve the structural relation FIRST, naturalize SECOND.\n"
    "- Use a colloquialism only when it fits the source structure naturally. "
    "Don't force one. Don't pile multiple together.\n"
    "- Aliases for OPERATORS, not decoration. Each phrase makes a structural "
    "claim; using one is a structural commitment, not flavor."
)


# Recipe-specific guidance: explicit coefficient + named-Ω-stem preservation.
# Patched in v2 because phase 1's recipe outputs dropped coefficients in
# ~83% of recipe samples. Patched again on 2026-05-08 so that the named
# outcome STEM (e.g. ``reasoning_02``) is what surfaces in English — not
# the full ``Ω_*`` token. The earlier rule contradicted the no-CAS-jargon
# rule and would have trained the model to leak ``Ω_*`` tokens in plain
# English replies.
_RECIPE_PRESERVATION_GUIDANCE = (
    "RECIPE-SPECIFIC RULES (this expression is a recipe — Θ(Ω_...) = ... → ...):\n"
    "- Every numeric coefficient MUST appear in your English output as a "
    "  digit-form number. Example: '0.7*X' must surface as 'weighted at 0.7' "
    "  or '0.7 of X' or 'a 0.7 contribution from X' — NEVER paraphrased away "
    "  as 'mostly' or 'a small amount' or 'partial'.\n"
    "- If the recipe targets a named outcome (e.g. Ω_decision_47, "
    "  Ω_reasoning_02), you MUST reference the outcome by its NAME STEM "
    "  (the part after the Ω_ prefix — e.g. 'decision_47', 'reasoning_02') "
    "  in your English output. Do NOT echo the 'Ω_' symbol or any other CAS "
    "  notation. Render the name as a plain-English noun phrase: "
    "  '\"the named outcome reasoning_02\"', 'the outcome called "
    "  reasoning_02', 'named outcome reasoning_02', or simply quoting the "
    "  stem 'reasoning_02' all work. The stem itself appears verbatim; the "
    "  Ω_ prefix never does.\n"
    "- The recipe arrow → means 'produces'. State the production explicitly: "
    "  'these inputs produce the outcome called <stem>'.\n"
    "- GOOD example: '0.7*^9^C|A + 1.5*^1^P|A → Ω_reasoning_50' should "
    "  surface as: 'Take 0.7 of an analytical realization in cognitive "
    "thinking and add 1.5 of analytical attention to a foundational "
    "principle — together they produce the outcome called reasoning_50.' "
    "  Both coefficients (0.7, 1.5) appear as digits; the stem "
    "(reasoning_50) appears; the Ω_ prefix does not; the words "
    "'domain' / 'drive' / 'register' do not appear.\n"
    "- BAD example — DO NOT do this: '...produces Ω_reasoning_50.' That "
    "  echoes the Ω_ symbol, which is CAS notation, not English. It is a "
    "  jargon leak and will be rejected.\n"
    "- BAD example — DO NOT do this: 'A 0.7 contribution from the "
    "cognitive domain combined with a 1.5 contribution from the "
    "principled domain produces reasoning_50.' That uses the bare noun "
    "'domain' twice — REJECT under the axis-word leakage gate.\n"
    "- BAD example — DO NOT confuse ^3 and ^6 inside recipes: "
    "'0.5*^3^E_{F6}|f' must NOT be rendered as '0.5 of breaking down "
    "an idea.' ^3 is Negative/aversion ('rubs the wrong way', 'pushed "
    "away'); ^6 is Male/analysis ('breaking it down', 'unpacking'). "
    "If the source says ^3, use aversion language, not analysis language."
)


# Fractal-specific guidance: k-values are operator indices, not counts.
# Patched in v2 because phase 1's fractal outputs misread k-values as
# counts (~60-80% of fractal samples).
_FRACTAL_K_INDEX_GUIDANCE = (
    "FRACTAL-SPECIFIC RULES (this expression is a fractal sequence — "
    "Φ⟨k₁:k₂:…:kₙ⟩ or Phi<k:k:…:k>):\n"
    "- Each k-value is an OPERATOR INDEX (an integer 0-9 selecting one "
    "of the 10 Noetic operators). It is NOT a count of anything.\n"
    "- DO NOT say '9 domains', '4 operations', 'a sequence of 8 stages', "
    "or similar count-language. Each k picks one of: 0=Idea, 1=Mind, "
    "2=Positive, 3=Negative, 4=Vibration, 5=Female, 6=Male, 7=Rhythm, "
    "8=Above/Cause, 9=Below/Effect.\n"
    "- Render each k as the SPECIFIC operator name OR a SPECIFIC "
    "approved colloquialism for THAT operator (see the colloquialism "
    "map above), in the order they appear. Generic 'thought' / 'idea' / "
    "'feeling' wording does NOT count — every operator has its own "
    "specific meaning.\n"
    "- The ':' inside the angle brackets is a step-separator, not an "
    "operator. Treat the sequence as 'first this, then that, then …'.\n"
    "\n"
    "DETERMINISTIC k → English-phrase table. For each k-value in the "
    "source, pick ONE of the listed phrases and use it (verbatim or "
    "lightly inflected). Do not generalize beyond this table:\n"
    "  k=0 (Idea):         'a thought' / 'an idea on the mind'\n"
    "  k=1 (Mind):         'paying attention' / 'becoming aware' / "
    "'using one's head'\n"
    "  k=2 (Positive):     'drawn to' / 'pulled toward' / 'speaks to'\n"
    "  k=3 (Negative):     'an aversion' / 'rubs the wrong way' / "
    "'pushed away'\n"
    "  k=4 (Vibration):    'struck a chord' / 'resonated' / "
    "'made an impression'\n"
    "  k=5 (Female):       'shaped by' / 'the sum of one's experiences'\n"
    "  k=6 (Male):         'breaking it down' / 'unpacking' / "
    "'pulling apart'\n"
    "  k=7 (Rhythm):       'muscle memory' / 'practice makes perfect' "
    "/ 'in a groove'\n"
    "  k=8 (Above/Cause):  'reminded one of' / 'triggered' / "
    "'led one thing to another'\n"
    "  k=9 (Below/Effect): 'popped into mind' / 'just clicked' / "
    "'out of nowhere'\n"
    "Connect them in source order with: 'led to', 'then', 'which "
    "became', 'in turn', 'and finally'.\n"
    "\n"
    "MANDATORY CHECKLIST before submitting your reply:\n"
    "1. Identify each k-value in the source.\n"
    "2. Pick ONE phrase from the deterministic table above for each k. "
    "Generic 'thought' / 'idea' / 'feeling' wording does NOT count "
    "unless it is the specific table entry for that k.\n"
    "3. Verify: the count of phrases drawn from the table equals the "
    "count of k-values in the source.\n"
    "4. GENERICITY TEST: if your reply could describe ANY fractal "
    "sequence (e.g. 'a series of thoughts and feelings'), it is TOO "
    "GENERIC and FAILS. A reader who sees only your English should be "
    "able to infer WHICH operator each step uses by recognizing the "
    "phrase from the table.\n"
    "\n"
    "- Worked example 1: 'Φ⟨9:4:7⟩' → 'A thought that popped into mind "
    "led to something that struck a chord, which then turned into "
    "muscle memory.' Three steps; ^9 → 'popped into mind', ^4 → "
    "'struck a chord', ^7 → 'muscle memory'.\n"
    "- Worked example 2: 'Φ⟨2:6:8⟩' → 'Drawn to something, then "
    "breaking it down, which reminded one of something else.' Three "
    "steps; ^2 → 'drawn to', ^6 → 'breaking it down', ^8 → 'reminded'.\n"
    "- BAD: 'A sequence of three thoughts.' Generic — fails the "
    "Genericity Test (could describe Φ⟨0:0:0⟩, Φ⟨1:1:1⟩, etc.).\n"
    "- BAD: 'A series of cognitive operations leading from one to the "
    "next.' Same problem — does not name which operators.\n"
    "- BAD: 'a sequence of three stages with operations 9, 4, and 7.' "
    "Echoes the k-numbers as numbers and drops the operator-index "
    "meaning.\n"
    "- BAD: any reply containing '^N' notation — REJECT."
)


# Per-slot guidance for the categories that previously had no specific
# preservation rules. Added 2026-05-08 after the global-leakage agent run
# found that recipe + fractal validators alone were too narrow — the other
# 8 cas_to_english categories passed through without category-specific
# guidance and the model leaked CAS notation in 80 of 179 records. Each
# block follows the same pattern: rule + worked example + explicit "NOT"
# counter-examples that mirror the actual leak patterns observed.

_STATE_LITERAL_GUIDANCE_V2 = (
    "STATE-LITERAL RULES (this expression is a single state literal — "
    "^N^D[_{Fk}][|R]):\n"
    "- A state literal names: a Noetic operator (the ^N part), a Domain "
    "(^D), optionally a Drive (_{Fk}), optionally a Register (|R). All "
    "components present in the source MUST surface in the English via "
    "their plain-English replacements — NEVER as the raw notation.\n"
    "\n"
    "CRITICAL DISAMBIGUATION — register vs. named outcome:\n"
    "- The '|R' after a state literal is a REGISTER specifier (one of "
    "T/A/f/E). It describes HOW the state is expressed:\n"
    "    T → transcendent / strategic / big-picture\n"
    "    A → analytical / reasoned / step-by-step\n"
    "    f → affective / felt / emotional\n"
    "    E → embodied / bodily / sensorimotor\n"
    "- '|R' is NOT an outcome name. Outcome names appear ONLY after 'Ω_' "
    "AND ONLY in recipes or cross-register-omega expressions.\n"
    "- WRONG: '^7^C_{F2}|A' rendered as 'the outcome called A' — A is a "
    "register character, not an outcome name. This is a category error.\n"
    "- CORRECT: '^7^C_{F2}|A' → 'Practice and muscle memory in cognitive "
    "thinking, driven by a need for wisdom, expressed through analytical "
    "reasoning.'\n"
    "\n"
    "- Worked example 1 (with all parts): '^7^E_{F3}|A' should surface "
    "as: 'Practice and muscle memory in evaluative judgment, driven by a "
    "need for vitality, expressed through analytical reasoning.' All "
    "four parts (Rhythm, Evaluative, F3 vitality, A analytical) appear "
    "as plain English; no '^', no 'F3', no 'A register'.\n"
    "- Worked example 2 (no register): '^3^P_{F1}' → 'A principled "
    "aversion driven by a need for unity.' Three parts (no register).\n"
    "- BAD: 'Rhythm in E domain with F3 drive at A register.' Echoes "
    "^E, F3, A — three jargon leaks.\n"
    "- BAD: 'Repetition.' Drops domain, drive, and register.\n"
    "- BAD: 'The outcome called A.' Confuses register character with "
    "named outcome — REJECT."
)


_BINARY_COMPOSITION_GUIDANCE_V2 = (
    "BINARY-COMPOSITION RULES (two state literals joined by + or ×):\n"
    "- Each operand MUST surface independently in English with its Noetic "
    "(via colloquialism or operator name) AND its Domain (as the domain "
    "word).\n"
    "- The operator '+' reads as 'and' / 'combined with' / 'together "
    "with'. The operator '×' reads as 'integrated with' / 'merged into' / "
    "'fused with'.\n"
    "- Worked example: '^3^O + ^7^P' should surface as: 'A felt aversion "
    "in the operational arena combined with a practiced rhythm in the "
    "principled arena.' Both operands' noetics and domains appear; no "
    "'^N', no 'O', no 'P' as labels.\n"
    "- DO NOT describe operands as 'operator index 2' or 'operator index "
    "9'. The index number is CAS notation; use the corresponding "
    "operator meaning or colloquialism instead.\n"
    "- BAD: '^3 in O combined with ^7 in P.' Echoes notation.\n"
    "- BAD: 'the first at operator index 2 and the second at operator "
    "index 9.' Echoes index numbers instead of meaning.\n"
    "- BAD: 'Aversion and rhythm.' Drops both domains."
)


_CROSS_REGISTER_OMEGA_GUIDANCE_V2 = (
    "CROSS-REGISTER OMEGA RULES (two or three same-Noetic "
    "register-instantiations fused into a named outcome — "
    "(^N^D|R1 × ^N^D|R2 [× ^N^D|R3]) = ^N^D|Ω_X):\n"
    "- This represents an integrated/emergent state. Render as: the same "
    "noetic + domain expressed across EXACTLY the source registers, then "
    "fusing into a named outcome. Do not invent a third mode when the "
    "source has only two operands.\n"
    "- The emergent outcome's STEM (after Ω_) MUST surface; the Ω_ prefix "
    "NEVER does. Every operand register character before '=' MUST be "
    "described in plain English. The shared noetic + domain MUST surface.\n"
    "- Register disambiguation is load-bearing: |E means embodied / bodily "
    "/ sensorimotor expression, while ^E means evaluative judgment. |T "
    "means transcendent / strategic / big-picture expression. |A means "
    "analytical / reasoned expression. |f means felt / affective / "
    "emotional expression.\n"
    "- Exact-register checklist: before writing, list the source registers "
    "mentally and render ONLY those registers. If the source includes |E, "
    "the English must include embodied / bodily / sensorimotor language. "
    "If the source lacks |A, do not say analytical / reasoned / "
    "step-by-step. If the source lacks |f, do not say felt / emotional. "
    "If the source lacks |T, do not say transcendent / strategic / "
    "big-picture.\n"
    "- Worked example (three registers): "
    "'(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω_alignment' should surface as: "
    "'A principled aversion expressed through analytical reasoning, felt "
    "emotion, and transcendent strategic conviction — all three modes "
    "fusing into the outcome called alignment.' Stem 'alignment' surfaces, "
    "all three source registers (analytical, felt, transcendent) appear, "
    "noetic and domain (aversion, principled) appear; Ω_ never appears.\n"
    "- Worked example (two registers): "
    "'(^6^P|f × ^6^P|A) = ^6^P|Ω_integration' should surface as: "
    "'A principled effort to break down an idea expressed through felt "
    "emotion and analytical reasoning, with those two modes fusing into "
    "the outcome called integration.' Exactly two source registers appear; "
    "no embodied or transcendent mode is invented.\n"
    "- BAD: '^3^P in registers A, f, T.' Echoes every part.\n"
    "- BAD: '...the outcome Ω_alignment.' Ω_ prefix leak.\n"
    "- BAD: a two-register source rendered as 'analytical, felt, and "
    "embodied — all three modes.' Invents a register that is not in the "
    "source.\n"
    "- BAD: '(^4^C|E × ^4^C|f)' rendered as 'analytical reasoning and "
    "felt emotion.' Source has |E and |f, so it must be embodied + felt, "
    "not analytical + felt.\n"
    "- BAD: '(^5^P|f × ^5^P|T)' rendered as 'felt emotion and analytical "
    "reasoning.' Source has |f and |T, so it must be felt + transcendent "
    "or strategic, not analytical."
)


_RPM_CHAIN_GUIDANCE_V2 = (
    "RPM-CHAIN RULES (an arrow chain A → B → C → D ...):\n"
    "- Each → is a step. Order matters. Render as a sequenced flow with "
    "explicit step connectives ('then', 'leads to', 'becomes', 'next', "
    "'in turn', 'and finally', 'produces').\n"
    "- Each operand's Noetic + Domain MUST surface in plain English in "
    "the order they appear.\n"
    "\n"
    "NAMED-STAGE RULE (load-bearing for chains with `let` bindings):\n"
    "- If the chain references named stages (e.g. `stageA0_5 → stageW_5` "
    "after `let stageA0_5 = …; let stageW_5 = …`), each stage variable "
    "name MUST appear VERBATIM in the English in the same order, "
    "INCLUDING any digits and underscores. The reader must be able to "
    "reconstruct which named stage feeds into which.\n"
    "- Truncating the name (e.g. 'stageA' instead of 'stageA0_1_5622') "
    "is a FAIL — the english_to_cas reverse step cannot rebuild the "
    "original variable from a truncated name.\n"
    "\n"
    "- Worked example 1 (literal-only): '^0^P → ^1^C → ^2^E → ^7^O' → "
    "'A foundational thought leads to attention in the cognitive arena, "
    "which in turn becomes a positive draw in the evaluative arena, and "
    "finally becomes muscle memory in the operational arena.' Four "
    "steps, four noetics, four domains; no notation.\n"
    "- Worked example 2 (named stages): "
    "'let stageA0_5 = ^0^P; let stageW_5 = ^7^C; stageA0_5 → stageW_5' → "
    "'Let \"stageA0_5\" name a foundational thought, and \"stageW_5\" "
    "name a practiced rhythm in the cognitive arena. stageA0_5 leads to "
    "stageW_5.' Both stage names appear verbatim; chain order preserved.\n"
    "- BAD: '^0 then ^1 then ^2 then ^7.' Notation echo.\n"
    "- BAD: 'A thought leads to other things.' Drops domains and chain.\n"
    "- BAD (named stages): 'A first stage leads to a second stage.' "
    "Drops the actual variable names — REJECT."
)


_LET_BINDING_GUIDANCE_V2 = (
    "LET-BINDING RULES (let X = ...):\n"
    "- The variable name X MUST appear VERBATIM in the English, "
    "INCLUDING any digits and underscores. Quote it or attribute it as "
    "a name: 'Let \"X\" name …' or 'let X be defined as …'. The "
    "english_to_cas reverse step cannot rebuild the original variable "
    "from a missing or truncated name.\n"
    "- The bound expression's content (Noetic + Domain + any drive / "
    "register) MUST be rendered in plain English.\n"
    "\n"
    "- Worked example 1 (short name): 'let anchor_03 = ^1^P_{F2}|T' → "
    "'Let \"anchor_03\" name attention to a principled foundation, "
    "driven by wisdom, expressed through transcendent strategic "
    "framing.' Variable name surfaces verbatim; all four bound-"
    "expression parts surface.\n"
    "- Worked example 2 (stage-style name): "
    "'let stageA0_1_5622 = ^0^P' → 'Let \"stageA0_1_5622\" name a "
    "foundational thought.' Full name (digits + underscores intact); "
    "Noetic + Domain present.\n"
    "- BAD: 'let anchor_03 = ^1 in P with F2 in T.' Notation echo.\n"
    "- BAD: 'A label is set.' Drops the name AND the binding's "
    "content — REJECT.\n"
    "- BAD: 'Let stageA name a thought.' Truncates 'stageA0_1_5622' to "
    "'stageA' — REJECT, the reverse step cannot rebuild the variable."
)


_INVERSION_GUIDANCE_V2 = (
    "INVERSION RULES (single state literal in inversion-axis context):\n"
    "- Render the same way as a state literal: the Noetic + Domain + "
    "(any drive and/or register) MUST all surface in plain English.\n"
    "- Worked example: '^3^P_{F1}' should surface as: 'A principled "
    "aversion driven by a need for unity.' Aversion, principled, unity "
    "all appear; no '^', no 'F1'.\n"
    "- BAD: '^3 in P with F1.' Notation.\n"
    "- BAD: 'Aversion.' Drops domain and drive."
)


_DIAGRAM_EXPORT_GUIDANCE_V2 = (
    "DIAGRAM-EXPORT RULES (cluster constructs — NoeticCluster{...}, "
    "RelationCluster{...}, CoverOf(...), PartitionOf(...)):\n"
    "- Render as a cluster / grouping / collection of its members. Each "
    "member's Noetic MUST surface (via colloquialism or operator name). "
    "Do not add or drop members. Do not echo the cluster-constructor "
    "name verbatim ('NoeticCluster' is jargon).\n"
    "- Worked example: 'NoeticCluster{^1, ^3, ^4}' should surface as: "
    "'A cluster of three operations: paying attention, an aversion, and "
    "something that struck a chord.' Three members, three operator "
    "renderings, no '^N'.\n"
    "- Compound export example: 'export let upsilon_0206 = "
    "NoeticCluster{^6, ^8}' should surface as: 'Export \"upsilon_0206\" "
    "as a cluster of two operations: breaking down an idea and something "
    "that triggered a memory.' The exported name appears verbatim, and "
    "both cluster members surface. Dropping 'upsilon_0206' is a FAIL "
    "because the reverse step cannot reconstruct the export binding.\n"
    "- BAD: 'A NoeticCluster of ^1, ^3, ^4.' Two notation echoes.\n"
    "- BAD: 'A cluster containing two operations: breaking down an idea "
    "and something that triggered a memory.' Drops the export name from "
    "'export let upsilon_0206 = ...' — REJECT for compound export shapes.\n"
    "- BAD: 'A cluster.' Drops every member."
)


# ---------------------------------------------------------------------------
# v2 prompt builders.
# ---------------------------------------------------------------------------


def build_cas_to_english_prompt_v2(
    seed: dict[str, Any],
) -> tuple[str, str]:
    """Build the v2 cas_to_english prompt.

    The system message is unchanged in spirit. The user message conditionally
    appends recipe / fractal preservation guidance based on the seed's
    grammar category. Keeps the colloquialism guidance from phase 1.
    """
    expr = seed["expression"]
    cat = seed.get("grammar_category", "unknown")
    system = (
        "You are a translator that turns formal CAS (Cognitive Architecture "
        "System) expressions into clear English paraphrases. CAS is a formal "
        "notation describing cognitive states and operations. Your job is to "
        "express what an expression MEANS in plain English while preserving "
        "every load-bearing element: numeric coefficients, named outcome "
        "targets (Ω_*), operator-index sequences inside fractal angle "
        "brackets, and the structural relation between elements."
    )
    parts = [
        f"CAS expression (grammar category: {cat}):\n\n    {expr}\n",
        _PLAIN_LANGUAGE_GUIDANCE_V2,
        _NO_NOTATION_GUIDANCE_V2,
        _COLLOQUIALISM_GUIDANCE_V2,
    ]
    if cat == "recipe" or "Θ" in expr or "Theta" in expr:
        parts.append(_RECIPE_PRESERVATION_GUIDANCE)
    if cat == "fractal_sequence" or "Φ" in expr or re.search(r"\bPhi\s*[<⟨]", expr):
        parts.append(_FRACTAL_K_INDEX_GUIDANCE)
    if cat == "state_literal":
        parts.append(_STATE_LITERAL_GUIDANCE_V2)
    if cat == "binary_composition":
        parts.append(_BINARY_COMPOSITION_GUIDANCE_V2)
    if cat == "cross_register_omega":
        parts.append(_CROSS_REGISTER_OMEGA_GUIDANCE_V2)
    if cat == "rpm_chain":
        parts.append(_RPM_CHAIN_GUIDANCE_V2)
    if cat == "let_binding":
        parts.append(_LET_BINDING_GUIDANCE_V2)
    if cat == "inversion":
        parts.append(_INVERSION_GUIDANCE_V2)
    if cat == "diagram_export":
        parts.append(_DIAGRAM_EXPORT_GUIDANCE_V2)
    parts.append(
        "Reply with ONLY the English paraphrase. No preamble, no list, no "
        "explanation of CAS notation, no quotes around the answer."
    )
    return system, "\n\n".join(parts)


def build_english_to_cas_prompt_v2(
    english_description: str,
    *,
    grammar_category: str,
    prior_attempt: Optional[str] = None,
    prior_error: Optional[str] = None,
) -> tuple[str, str]:
    """Build the v2 english_to_cas prompt.

    KEY CHANGE FROM PHASE 1: there is NO reference target and NO source CAS
    in this prompt. The model must produce a CAS expression based ONLY on
    the English description. The English description is generated by the
    Wave 2.5 step from the source CAS — the model translates English back
    to CAS without ever seeing the source.

    Validation against verbatim-copy is enforced separately by
    ``validate_anti_copy_english_to_cas``.
    """
    system = (
        "You are a translator that produces compiler-valid CAS (Cognitive "
        "Architecture System) expressions from English descriptions. CAS is a "
        "formal notation. Your output must parse and admissibility-check via "
        "the CAS compiler. Surface the structural relations described in the "
        "English: state literals (^N^D|R), operators (+, ×, →, ∘), recipes "
        "(Θ(Ω_*) = ...), fractals (Φ⟨k:k:…⟩), meta-logic (NoeticCluster, "
        "PartitionOf, CoverOf), let-bindings, etc. The grammar category is "
        "given as a hint — match it."
    )
    parts = [
        f"Grammar category target: {grammar_category}\n",
        f"English description to translate to CAS:\n\n    {english_description}\n",
        (
            "Reply with ONLY the CAS expression on a single line. No preamble, "
            "no markdown fences, no commentary. The expression alone."
        ),
    ]
    if prior_attempt is not None and prior_error is not None:
        parts.append(
            f"Your previous attempt was:\n\n    {prior_attempt}\n\n"
            f"It failed compiler validation with:\n\n    {prior_error}\n\n"
            f"Try again. Produce a corrected expression."
        )
    return system, "\n\n".join(parts)


def build_invalid_to_explanation_prompt_v2(
    invalid: dict[str, Any],
) -> tuple[str, str]:
    """Build the v2 invalid_to_explanation prompt.

    The audit rated this slot clean (18/25 FAITHFUL, 0 major drift). Carry
    forward the phase-1 prompt with minor language tightening.
    """
    expr = invalid["expression"]
    err = invalid.get("compiler_error_message", "")
    cls = invalid.get("error_class", "unknown")
    system = (
        "You are an explainer that describes why a CAS (Cognitive "
        "Architecture System) expression is invalid. CAS is a formal notation "
        "with a strict compiler. Your job is to say in plain English what is "
        "wrong with a malformed expression and why a careful reader should "
        "spot it. Stay clinical — clarity beats colloquial smoothing here."
    )
    user = (
        f"Invalid CAS expression (error class: {cls}):\n\n"
        f"    {expr}\n\n"
        f"Compiler error message:\n\n"
        f"    {err}\n\n"
        f"{_PLAIN_LANGUAGE_GUIDANCE_V2}\n\n"
        f"Explain in plain English what is wrong with the expression. Do NOT "
        f"echo the compiler error verbatim — describe it in your own words. "
        f"Reply with ONLY the explanation. No preamble, no markdown."
    )
    return system, user


def build_invalid_to_corrected_repair_prompt_v2(
    invalid: dict[str, Any],
) -> tuple[str, str]:
    """Produce the model-generated corrected expression (CAS, not English).

    KEY CHANGE FROM PHASE 1: the v2 invalid_to_corrected slot has TWO
    outputs: the corrected CAS expression (this prompt) and the English
    narration (the next prompt). The corrected-expression prompt asks for
    the smallest possible edit, with positive and negative worked examples.

    A Jaccard guard is applied at validation time
    (``validate_invalid_to_corrected_jaccard``).
    """
    expr = invalid["expression"]
    err = invalid.get("compiler_error_message", "")
    cls = invalid.get("error_class", "unknown")
    system = (
        "You are a CAS (Cognitive Architecture System) repair assistant. CAS "
        "is a formal notation with a strict compiler. The user shows you a "
        "malformed expression and the compiler error. Your job: produce the "
        "SMALLEST POSSIBLE EDIT that makes the expression compiler-valid. "
        "Replace only what is broken. Preserve every other token."
    )
    user = (
        f"Invalid CAS expression (error class: {cls}):\n\n"
        f"    {expr}\n\n"
        f"Compiler error on the invalid form:\n\n"
        f"    {err}\n\n"
        f"REPAIR RULES:\n"
        f"- Produce the smallest possible edit. The corrected expression "
        f"  MUST share the majority of its tokens with the invalid one.\n"
        f"- Replace, insert, or delete ONLY the broken token(s). Do not "
        f"  rewrite, simplify, or restructure the expression.\n"
        f"- Do not substitute a different valid expression for the broken "
        f"  one. Repair the specific surface error.\n"
        f"- If the error is a typo (wrong domain letter, wrong noetic "
        f"  index, missing closing bracket, missing register, etc.), fix "
        f"  exactly that token.\n"
        f"\n"
        f"GOOD EXAMPLE — minimal edit:\n"
        f"  invalid:    ^13^E|f + ^1^E|E\n"
        f"  error:      typecheck: operator index must be 0-9, got 13\n"
        f"  corrected:  ^1^E|f + ^1^E|E   (changed only `^13` to `^1`)\n"
        f"\n"
        f"BAD EXAMPLE — DO NOT do this:\n"
        f"  invalid:    ^13^E|f + ^1^E|E\n"
        f"  corrected:  ^2^P + ^4^C|T → Ω_demo   (replaced the whole expression "
        f"with a different valid one — wrong)\n"
        f"\n"
        f"Reply with ONLY the corrected CAS expression on a single line. No "
        f"preamble, no markdown fences, no commentary."
    )
    return system, user


def build_invalid_to_corrected_narration_prompt_v2(
    invalid: dict[str, Any],
    *,
    corrected_expression: str,
) -> tuple[str, str]:
    """Produce the English narration of the actual minimal change.

    Takes the model's corrected expression (already validated by Jaccard +
    compiler) and asks for an English description of the specific change.
    """
    expr = invalid["expression"]
    err = invalid.get("compiler_error_message", "")
    cls = invalid.get("error_class", "unknown")
    system = (
        "You are a CAS (Cognitive Architecture System) repair narrator. The "
        "user shows you a malformed expression, the compiler error, and the "
        "specific corrected form. Your job: describe the FIX in plain "
        "English — what was wrong, what specific change makes it valid. "
        "Reference the actual minimal change, not a generic 'replaced with a "
        "self-contained expression' phrasing."
    )
    user = (
        f"Invalid CAS expression (error class: {cls}):\n\n"
        f"    {expr}\n\n"
        f"Corrected expression (the minimal-edit valid form):\n\n"
        f"    {corrected_expression}\n\n"
        f"Compiler error on the invalid form:\n\n"
        f"    {err}\n\n"
        f"{_PLAIN_LANGUAGE_GUIDANCE_V2}\n\n"
        f"Describe the repair in plain English. Be specific about what "
        f"single change was made. Examples of good narration phrasing:\n"
        f"- 'Changed the operator index from 13 to 1 — only single digits "
        f"  0 through 9 are valid.'\n"
        f"- 'Added the missing domain letter after the second caret.'\n"
        f"- 'Replaced the comma with the colon separator the fractal sequence "
        f"  requires.'\n"
        f"\n"
        f"DO NOT use generic language like 'the fix replaces the whole "
        f"construct with a self-contained expression' — that phrasing came "
        f"from the audit's failure cases. Name the specific token or "
        f"surface element that changed.\n"
        f"\n"
        f"Reply with ONLY the description. No preamble, no markdown."
    )
    return system, user


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


# Match `<digit(s)>.<digit(s)> *` or `<digit(s)> *` immediately followed by
# `*` (the recipe coefficient marker). Anchored to the recipe shape:
# `<coeff>*<primitive>` where `<coeff>` is a positive number.
_RE_RECIPE_COEFFICIENT = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*\*")
_RE_OMEGA_NAMED = re.compile(r"Ω_([A-Za-z][A-Za-z0-9_]*)")
_RE_OMEGA_PREFIX_LEAK = re.compile(r"Ω_[A-Za-z]")
_RE_FRACTAL_BODY = re.compile(r"(?:Φ|Phi)\s*[⟨<]\s*([0-9:\s]+?)\s*[⟩>]")


def _tokenize_for_jaccard(s: str) -> set[str]:
    """Tokenize a CAS expression for word-level Jaccard comparison.

    Split on whitespace and a small punctuation set. Preserves operator
    tokens like `+`, `→`, `×`, `=` as their own tokens. Used by tests that
    inspect word-level token overlap; the production Jaccard guard
    (``validate_invalid_to_corrected_jaccard``) uses character n-gram
    Jaccard via ``_char_ngrams`` because word-level Jaccard penalizes
    legitimate single-character fixes (e.g. `^13` → `^1`) too heavily.
    """
    if not s:
        return set()
    # Insert spaces around structural punctuation so `^3^P|A+^4^P|A` becomes
    # `^3^P|A + ^4^P|A` for split.
    spaced = re.sub(r"([+×→=∘\(\)\{\}⟨⟩<>;,])", r" \1 ", s)
    spaced = re.sub(r"->", " → ", spaced)
    parts = [t for t in spaced.split() if t]
    return set(parts)


def _char_ngrams(s: str, n: int = 3) -> set[str]:
    """Character n-gram set for fuzzy minimal-edit Jaccard.

    Whitespace-collapsed; n-grams are over the raw string. Used by
    ``validate_invalid_to_corrected_jaccard`` because single-character
    fixes (operator-index 13 → 1, missing closing bracket, missing domain
    letter) preserve most n-grams while differing on one or two tokens.
    A whole-expression rewrite shares almost no n-grams with the invalid
    one and is correctly flagged.
    """
    if not s:
        return set()
    s = re.sub(r"\s+", " ", s.strip())
    if len(s) < n:
        return {s}
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


@dataclass
class ValidatorResult:
    name: str
    passed: bool
    reason: Optional[str] = None
    detail: dict[str, Any] = field(default_factory=dict)


def validate_cas_to_english_recipe_preservation(
    *,
    source_cas: str,
    english_output: str,
) -> ValidatorResult:
    """Recipe slot only — every numeric coefficient and named-Ω-target STEM
    must surface in the English output, and the ``Ω_`` prefix must NOT
    appear in the English output.

    Stems: ``Ω_reasoning_02`` -> stem ``reasoning_02``. The English output
    must reference the stem (verbatim, possibly within a quoting / naming
    phrase like 'the outcome called reasoning_02') without echoing the
    ``Ω_`` symbol. Echoing ``Ω_`` is CAS notation leakage and is rejected.

    Skipped (returns passed=True) when the source CAS has no recipe shape
    (no coefficients AND no named Ω targets).

    Patched 2026-05-08 to fix the original verbatim-Ω rule, which
    contradicted the no-CAS-jargon rule and would have trained the model
    to leak Ω_* tokens in plain English replies.
    """
    coefficients = _RE_RECIPE_COEFFICIENT.findall(source_cas)
    omega_stems = _RE_OMEGA_NAMED.findall(source_cas)
    if not coefficients and not omega_stems:
        return ValidatorResult(
            name="cas_to_english_recipe_preservation",
            passed=True,
            reason="not a recipe — validator skipped",
            detail={"coefficients_found": [], "omega_stems_found": []},
        )
    missing_coefficients: list[str] = []
    for c in coefficients:
        # Look for the coefficient as a digit-form number, possibly with
        # leading/trailing word boundaries. We accept `0.7`, `0.70`, `.7`
        # all as the same value to be tolerant.
        if c not in english_output:
            # Also try without leading-zero variants.
            try:
                f = float(c)
            except ValueError:
                missing_coefficients.append(c)
                continue
            # Try canonical forms.
            forms = {c, f"{f:g}", f"{f:.1f}", f"{f:.2f}"}
            if not any(form in english_output for form in forms):
                missing_coefficients.append(c)
    missing_stems: list[str] = []
    for stem in omega_stems:
        if stem not in english_output:
            missing_stems.append(stem)
    # Anti-leak guard: the Ω_ prefix must not appear in the English output.
    omega_leak_hits = _RE_OMEGA_PREFIX_LEAK.findall(english_output)
    if missing_coefficients or missing_stems or omega_leak_hits:
        reasons = []
        if missing_coefficients:
            reasons.append(
                f"missing coefficients: {missing_coefficients}"
            )
        if missing_stems:
            reasons.append(
                f"missing named Ω target stems: {missing_stems}"
            )
        if omega_leak_hits:
            reasons.append(
                f"Ω_ prefix leaked into English output: {omega_leak_hits}"
            )
        return ValidatorResult(
            name="cas_to_english_recipe_preservation",
            passed=False,
            reason="; ".join(reasons),
            detail={
                "coefficients_found": coefficients,
                "omega_stems_found": omega_stems,
                "missing_coefficients": missing_coefficients,
                "missing_omega_stems": missing_stems,
                "omega_prefix_leaks": omega_leak_hits,
            },
        )
    return ValidatorResult(
        name="cas_to_english_recipe_preservation",
        passed=True,
        detail={
            "coefficients_found": coefficients,
            "omega_stems_found": omega_stems,
        },
    )


_RE_RECIPE_OPERAND = re.compile(
    r"(?P<coeff>\d+(?:\.\d+)?)\s*\*\s*"
    r"(?P<state>"
    r"\^\d+(?:\^[A-Za-z])?(?:_\{F\d+\})?(?:\|(?:[A-Za-z]|⟨[^⟩]+⟩))?"
    r")"
)


# Extended noetic-alias substrings for the per-occurrence validator only.
# Adds variants observed in run 20260508T110453Z that
# NOETIC_VALIDATION_TOKENS (used by the fractal validator) lacks.
# Scoped to this validator so the fractal validator's behavior is
# unchanged.
#
# Tolerances added: hyphenated forms (``breaking-down`` for
# ``break down``), inserted-pronoun forms (``rubs you the wrong way``
# for ``rubs the wrong way``), small set of canonical synonyms
# (``realization`` for ^9, ``analysis`` for ^6).
_NOETIC_PER_OCCURRENCE_EXTRA: dict[int, tuple[str, ...]] = {
    0: ("realization",),
    1: ("attention",),
    2: ("draw to", "drawn-to"),
    3: ("rubs you the wrong way", "rub the wrong way",
        "rubs the wrong way", "rubbed the wrong way",
        "rubbing the wrong way", "wrong way"),
    4: ("resonant",),
    5: ("who you are", "who-you-are", "shaped by"),
    6: ("breaking-down", "break-down", "broken-down",
        "analysis", "analyse", "analyze", "analyzing", "analysing"),
    7: ("practice makes perfect", "practice-makes-perfect",
        "practice making perfect", "mental practice"),
    8: ("triggered a memory", "trigger a memory"),
    9: ("realization", "realisation",
        "popped into", "the thought came", "came to mind"),
}


def _noetic_aliases_per_occurrence(n: int) -> tuple[str, ...]:
    """Combined alias tuple = NOETIC_VALIDATION_TOKENS[n] + extras."""
    base = NOETIC_VALIDATION_TOKENS.get(n, ())
    extra = _NOETIC_PER_OCCURRENCE_EXTRA.get(n, ())
    return tuple(base) + tuple(extra)


def _parse_recipe_operands(source_cas: str) -> list[dict[str, Any]]:
    """Parse ``<coeff>*<state>`` pairs from a recipe LHS.

    Returns a list of dicts with keys: ``coeff_str`` (raw digit form),
    ``coeff_value`` (canonical float form ``f"{f:g}"``), ``noetic`` (int),
    ``domain`` (str|None), ``drive`` (int|None), ``register`` (str|None),
    ``state_repr`` (the raw state-literal substring).

    Only the LHS of the recipe (everything before the first chain arrow)
    is parsed; the RHS is the production target Omega, not an operand.
    """
    lhs = source_cas
    for arrow in ("→", "->"):
        idx = lhs.find(arrow)
        if idx >= 0:
            lhs = lhs[:idx]
    operands: list[dict[str, Any]] = []
    for m in _RE_RECIPE_OPERAND.finditer(lhs):
        coeff_str = m.group("coeff")
        state = m.group("state")
        sm = _RE_STATE_LITERAL.match(state)
        if not sm:
            continue
        try:
            n = int(sm.group(1))
        except (TypeError, ValueError):
            continue
        d = sm.group(2)
        drive_raw = sm.group(3)
        reg = sm.group(4)
        drive_idx: Optional[int] = None
        if drive_raw and drive_raw.startswith("F"):
            try:
                drive_idx = int(drive_raw[1:])
            except ValueError:
                drive_idx = None
        try:
            coeff_value = f"{float(coeff_str):g}"
        except ValueError:
            coeff_value = coeff_str
        operands.append({
            "coeff_str": coeff_str,
            "coeff_value": coeff_value,
            "noetic": n,
            "domain": d,
            "drive": drive_idx,
            "register": reg,
            "state_repr": state,
        })
    return operands


def _coefficient_anchor_spans(
    coeff_str: str, coeff_value: str, english: str
) -> list[tuple[int, int]]:
    """Find character-span occurrences of a coefficient in the English.

    Tolerates trailing-zero / leading-dot variants by trying multiple
    canonical forms. Each match is anchored on a digit boundary so
    ``0.7`` does not match inside ``0.75`` and ``2`` does not match
    inside ``2026``.
    """
    spans: list[tuple[int, int]] = []
    forms: set[str] = {coeff_str, coeff_value}
    try:
        f = float(coeff_str)
        forms.update({f"{f:g}", f"{f:.1f}", f"{f:.2f}"})
        if f == int(f):
            forms.add(f"{int(f)}")
    except ValueError:
        pass
    seen_starts: set[int] = set()
    for form in sorted(forms, key=len, reverse=True):
        if not form:
            continue
        pat = re.compile(rf"(?<![\w.]){re.escape(form)}(?![\w.])")
        for m in pat.finditer(english):
            if m.start() in seen_starts:
                continue
            overlap = any(
                start <= m.start() < end for (start, end) in spans
            )
            if overlap:
                continue
            spans.append((m.start(), m.end()))
            seen_starts.add(m.start())
    spans.sort()
    return spans


def _phrase_window(
    english: str, start: int, end: int, radius: int = 120
) -> str:
    """Return a phrase-bounded substring around span [start, end).

    Up to ``radius`` characters before ``start`` and after ``end``,
    trimmed at the nearest conjunctive-phrase boundary so a coefficient
    sitting in operand-1's clause does not see operand-2's alias on the
    other side of a strong boundary.

    Boundary set deliberately excludes plain ``and`` / ``plus`` -- those
    are within-clause connectives in many recipe descriptions (``a need
    for cohesion in foundational thinking, expressed in an analytical
    way``) where cutting at ``and`` would orphan the register
    descriptor from its operand. Strong boundaries only: ``, and ``,
    ``, plus ``, ``; ``, em-dash, en-dash, period.
    """
    lo = max(0, start - radius)
    hi = min(len(english), end + radius)
    snippet = english[lo:hi]
    rel_start = start - lo
    rel_end = end - lo
    boundary_tokens = (
        ", and ", ", plus ", "; ", " — ", " – ", "—", "–", ". ",
    )
    left_text = snippet[:rel_start]
    left_cut = 0
    for token in boundary_tokens:
        idx = left_text.rfind(token)
        if idx > left_cut:
            left_cut = idx + len(token)
    right_text = snippet[rel_end:]
    right_cut = len(snippet)
    for token in boundary_tokens:
        idx = right_text.find(token)
        if idx >= 0:
            candidate = rel_end + idx
            if candidate < right_cut:
                right_cut = candidate
    return snippet[left_cut:right_cut]


def validate_cas_to_english_recipe_per_occurrence(
    *,
    source_cas: str,
    english_output: str,
    window_radius: int = 120,
) -> ValidatorResult:
    """Recipe slot -- per-occurrence operator-alias check.

    Sibling validator to ``validate_cas_to_english_recipe_preservation``.
    For each ``<coeff>*<state_literal>`` operand on the recipe LHS:

      * locate the coefficient digit-form in the English with a strict
        digit-boundary anchor (so ``1`` does not match inside
        ``rehearsal_61``);
      * within a phrase-bounded window (~``window_radius`` chars,
        trimmed at strong conjunctive boundaries: ``, and ``,
        ``, plus ``, ``; ``, em-dash, en-dash, period), require the
        operand's noetic alias from ``NOETIC_VALIDATION_TOKENS`` to
        appear;
      * register check is CONFLICT-BASED. If the operand has a register
        ``|R`` and the operand's window contains a DIFFERENT register
        letter's alias (mode confusion such as |E source rendered with
        |A "analytical" alias), fail. Pure absence of the source
        register's alias is allowed (the model often renders register
        positionally outside the window or omits register
        descriptors when fluent context already conveys it).

    Operand resolution is order-tolerant by greedy assignment with
    backtracking-lite: when two operands share the same coefficient
    string, every pairing is tried.

    Skipped (passed=True) when the source CAS has no recipe operands.

    Tone discipline: this is a window-based heuristic, not an AST-level
    semantic check. Some legitimate phrasings may still be reported as
    misrenders when the alias surfaces outside the heuristic window,
    and some genuine misrenders may slip past when the wrong noetic
    happens to share substrings with the right one. False-positive risk
    is nonzero; treat the validator as a catch-most-cases gate, not a
    proof.

    Closes 3 known operator-confusion patterns missed by the original
    recipe validator (see seed_recipe_00407 ^3->^5, seed_recipe_00061
    ^2->^6, seed_recipe_00165 |E->|A; module header has details).
    """
    operands = _parse_recipe_operands(source_cas)
    if not operands:
        return ValidatorResult(
            name="cas_to_english_recipe_per_occurrence",
            passed=True,
            reason="not a recipe — validator skipped",
            detail={"operands_found": 0},
        )

    operand_candidates: list[list[dict[str, Any]]] = []
    missing_anchor: list[str] = []
    for op in operands:
        spans = _coefficient_anchor_spans(
            op["coeff_str"], op["coeff_value"], english_output
        )
        cand: list[dict[str, Any]] = []
        for s, e in spans:
            window = _phrase_window(
                english_output, s, e, radius=window_radius
            )
            cand.append({
                "span": (s, e),
                "window": window,
                "window_lower": window.lower(),
                "window_singular": re.sub(
                    r"(\w+)s\b", r"\1", window.lower()
                ),
            })
        if not cand:
            missing_anchor.append(
                f"coeff_{op['coeff_str']}@{op['state_repr']}"
            )
        operand_candidates.append(cand)

    if missing_anchor:
        return ValidatorResult(
            name="cas_to_english_recipe_per_occurrence",
            passed=False,
            reason=(
                f"recipe coefficient(s) missing from English (anchor not "
                f"found): {missing_anchor}"
            ),
            detail={"missing_anchors": missing_anchor},
        )

    def _try_assignment(
        order: list[int],
        claimed: set[tuple[int, int]],
    ) -> tuple[bool, list[dict[str, Any]], list[dict[str, Any]]]:
        if not order:
            return True, [], []
        idx = order[0]
        rest = order[1:]
        op = operands[idx]
        n = op["noetic"]
        ntoks = _noetic_aliases_per_occurrence(n)
        reg = op["register"]
        reg_letters: list[str] = []
        if reg:
            if reg.startswith("⟨") and reg.endswith("⟩"):
                reg_letters = [
                    x.strip() for x in reg[1:-1].split(",") if x.strip()
                ]
            else:
                reg_letters = [reg]
        last_fail: Optional[dict[str, Any]] = None
        for cand in operand_candidates[idx]:
            if cand["span"] in claimed:
                continue
            wl = cand["window_lower"]
            ws = cand["window_singular"]
            noetic_ok = (
                any(tok in wl or tok in ws for tok in ntoks)
                if ntoks else True
            )
            if not noetic_ok:
                last_fail = {
                    "operand_index": idx,
                    "operand": op["state_repr"],
                    "coefficient": op["coeff_str"],
                    "reason": (
                        f"operator_misrender_at_coeff_"
                        f"{op['coeff_str']}: ^{n} alias not found near "
                        f"coefficient"
                    ),
                    "snippet": cand["window"].strip(),
                }
                continue
            # Conflict-based register check. Only fires when the
            # operand has a source register AND that register's alias
            # is missing from the window AND a DIFFERENT register
            # letter's alias is present in the window. Pure absence is
            # tolerated (register descriptors often surface outside the
            # heuristic window or are dropped in fluent prose). This
            # is the seed_recipe_00165 |E->|A pattern.
            reg_fail: Optional[str] = None
            for letter in reg_letters:
                rtoks = REGISTER_ALIASES.get(letter, ())
                source_reg_present = bool(rtoks) and any(
                    rt in wl for rt in rtoks
                )
                if source_reg_present:
                    continue
                # Source register alias is absent; look for a
                # conflicting register letter's STRICT alias set
                # (CROSS_REGISTER_EXTRA_MODE_ALIASES is narrower than
                # REGISTER_ALIASES so common words like "meaning" do
                # not trigger).
                conflicting: list[str] = []
                for other in ("T", "A", "f", "E"):
                    if other == letter:
                        continue
                    other_strict = CROSS_REGISTER_EXTRA_MODE_ALIASES.get(
                        other, ()
                    )
                    if other_strict and any(
                        rt in wl for rt in other_strict
                    ):
                        conflicting.append(other)
                if conflicting:
                    reg_fail = (
                        f"register_misplaced_at_coeff_"
                        f"{op['coeff_str']}: |{letter} source register "
                        f"missing AND conflicting alias for "
                        f"|{','.join(conflicting)} present near "
                        f"coefficient"
                    )
                    break
            if reg_fail is not None:
                last_fail = {
                    "operand_index": idx,
                    "operand": op["state_repr"],
                    "coefficient": op["coeff_str"],
                    "reason": reg_fail,
                    "snippet": cand["window"].strip(),
                }
                continue
            new_claimed = claimed | {cand["span"]}
            ok, fails, passes = _try_assignment(rest, new_claimed)
            if ok:
                passes.append({
                    "operand_index": idx,
                    "operand": op["state_repr"],
                    "coefficient": op["coeff_str"],
                    "snippet": cand["window"].strip(),
                })
                return True, fails, passes
            if fails and last_fail is None:
                last_fail = fails[0]
        return (
            False,
            [last_fail] if last_fail else [{
                "operand_index": idx,
                "operand": op["state_repr"],
                "coefficient": op["coeff_str"],
                "reason": (
                    f"operator_misrender_at_coeff_"
                    f"{op['coeff_str']}: no candidate window satisfied "
                    f"operand checks"
                ),
                "snippet": "",
            }],
            [],
        )

    success, fail_records, pass_records = _try_assignment(
        list(range(len(operands))), set()
    )
    if success:
        return ValidatorResult(
            name="cas_to_english_recipe_per_occurrence",
            passed=True,
            detail={
                "operands_found": len(operands),
                "operand_passes": pass_records,
            },
        )
    return ValidatorResult(
        name="cas_to_english_recipe_per_occurrence",
        passed=False,
        reason="; ".join(
            f"{f['reason']} — snippet: {f['snippet']!r}"
            for f in fail_records
        ),
        detail={
            "operands_found": len(operands),
            "operand_failures": fail_records,
        },
    )


def validate_cas_to_english_fractal_k_indices(
    *,
    source_cas: str,
    english_output: str,
) -> ValidatorResult:
    """Fractal slot only — for each k-value in `Φ⟨k:k:…⟩`, the corresponding
    operator name OR a canonical colloquialism for that operator must appear
    in the English output.

    Also rejects count-misread phrasings like 'sequence of N stages' /
    'N domains' / 'N operations' where N matches one of the k-values.

    Skipped (passed=True) when the source CAS has no fractal shape.
    """
    body_match = _RE_FRACTAL_BODY.search(source_cas)
    if not body_match:
        return ValidatorResult(
            name="cas_to_english_fractal_k_indices",
            passed=True,
            reason="not a fractal — validator skipped",
        )
    body = body_match.group(1)
    try:
        k_values = [int(s.strip()) for s in body.split(":") if s.strip()]
    except ValueError:
        return ValidatorResult(
            name="cas_to_english_fractal_k_indices",
            passed=False,
            reason=f"could not parse k-values from fractal body: {body!r}",
        )
    if not k_values:
        return ValidatorResult(
            name="cas_to_english_fractal_k_indices",
            passed=False,
            reason="empty k-value list",
        )
    out_lower = english_output.lower()
    # Light morphological normalization — strip 's' suffix on the last
    # word of multi-word tokens to catch "hits hard" matching "hit hard".
    # Keep this conservative; we still prefer a literal substring hit.
    out_normalized_singular = re.sub(r"(\w+)s\b", r"\1", out_lower)
    missing_ks: list[int] = []
    for k in k_values:
        if k not in NOETIC_VALIDATION_TOKENS:
            # Out-of-range k — the source is malformed; flag.
            missing_ks.append(k)
            continue
        tokens = NOETIC_VALIDATION_TOKENS[k]
        matched = any(
            tok in out_lower or tok in out_normalized_singular
            for tok in tokens
        )
        if not matched:
            missing_ks.append(k)
    # Count-misread heuristic — "N domains", "N stages", "N operations",
    # "sequence of N" patterns where N is in the k-values list.
    count_misread_patterns = []
    for k in k_values:
        for noun in ("domains", "stages", "operations", "pathways", "steps", "elements"):
            pat = re.compile(rf"\b{k}\s+{noun}\b", re.IGNORECASE)
            if pat.search(english_output):
                count_misread_patterns.append(f"{k} {noun}")
        seq_pat = re.compile(rf"sequence\s+of\s+{len(k_values)}\b", re.IGNORECASE)
        # only check seq once
    seq_pat = re.compile(rf"sequence\s+of\s+{len(k_values)}\b", re.IGNORECASE)
    if seq_pat.search(english_output):
        count_misread_patterns.append(f"sequence of {len(k_values)}")
    if missing_ks or count_misread_patterns:
        reasons = []
        if missing_ks:
            reasons.append(
                f"k-values not rendered as operators: {missing_ks}"
            )
        if count_misread_patterns:
            reasons.append(
                f"count-misread patterns detected: {count_misread_patterns}"
            )
        return ValidatorResult(
            name="cas_to_english_fractal_k_indices",
            passed=False,
            reason="; ".join(reasons),
            detail={
                "k_values": k_values,
                "missing_ks": missing_ks,
                "count_misread_patterns": count_misread_patterns,
            },
        )
    return ValidatorResult(
        name="cas_to_english_fractal_k_indices",
        passed=True,
        detail={"k_values": k_values},
    )


# ---------------------------------------------------------------------------
# Global Wave 2.5 jargon-leak validator + slot-specific structural-preservation
# validators. Added 2026-05-08 in response to a paid preflight that accepted
# 179 records of which the user reported:
#   * 14 records leaked ``Ω_<name>`` (bare Ω-underscore-name)
#   * 15 records leaked state literals like ``^3^P|A`` or ``^5``
#   * 32 records leaked drive references like ``F7`` standalone
#   * 17 records leaked CAS-jargon-shaped ``domain X`` phrasing
#   * 1-2 records leaked the bare CAS-jargon word ``register`` / ``noetic``
# The phase-1 validators only fired on recipe + fractal slots, so the other
# eight grammar categories had ZERO content-preservation gating. These
# validators close that gap.
# ---------------------------------------------------------------------------


# Domain letter -> approved English alias substrings (lower-cased). The
# generator's prompt uses these aliases; the validator accepts any of them.
DOMAIN_ALIASES: dict[str, tuple[str, ...]] = {
    "P": ("principled", "foundational", "principle", "foundation"),
    "C": ("cognitive", "mental", "thought", "thinking", "mind"),
    "E": ("evaluative", "judging", "judgment", "judgement", "evaluation",
          "evaluat", "assess"),
    "O": ("operational", "behavioral", "behaviour", "behavior", "action",
          "outcome", "act"),
}

# Drive subscript Fk -> approved English alias substrings. From CLAUDE.md
# canonical drive list. Per the colloquialism feedback, also accept the
# raw drive name word.
DRIVE_ALIASES: dict[int, tuple[str, ...]] = {
    1: ("unity", "oneness", "wholeness"),
    2: ("wisdom", "wise", "insight", "understanding"),
    3: ("vitality", "vital", "life-energy", "aliveness"),
    4: ("connection", "connect", "relation", "bond", "tie"),
    5: ("agency", "agent", "choice", "act with intent"),
    6: ("structure", "structural", "form", "shape", "framework"),
    7: ("purpose", "purposeful", "intent", "telos", "meaning"),
}

# Register letter -> approved English alias substrings.
REGISTER_ALIASES: dict[str, tuple[str, ...]] = {
    "T": ("transcendent", "vision", "calling", "purpose-orient", "meaning",
          "strategic", "big-picture", "big picture"),
    "A": ("analytical", "analy", "reason", "logic", "deliberat",
          "explicit", "step-by-step"),
    "f": ("affective", "feeling", "felt", "emotion", "valenc",
          "value-laden", "preference"),
    "E": ("embodied", "bodily", "kinesthetic", "sensorimotor", "physical",
          "concrete", "gut"),
}

# Strong aliases used only to catch invented cross-register modes. Keep this
# narrower than REGISTER_ALIASES so ordinary words like "meaning" do not
# falsely reject a good answer.
CROSS_REGISTER_EXTRA_MODE_ALIASES: dict[str, tuple[str, ...]] = {
    "T": ("transcendent", "strategic", "big-picture", "big picture"),
    "A": ("analytical", "reasoned", "step-by-step", "logic"),
    "f": ("affective", "felt", "emotional"),
    "E": ("embodied", "bodily", "sensorimotor", "physical"),
}


# ---- Global jargon-leak regexes -------------------------------------------

# Bare ``Ω`` symbol anywhere -- catches both ``Ω_alignment`` and rare bare
# ``Ω``. Stricter than ``_RE_OMEGA_PREFIX_LEAK`` (which requires a letter
# after ``_``). Catches ``Ω_4`` (digit stem) which the older pattern missed.
_RE_OMEGA_BARE = re.compile(r"Ω")

# State-literal prefix: ``^`` followed by a digit. Catches ``^3``, ``^3^P``,
# ``^9^P_{F7}``, etc. CAS state literals always start ``^<digit>``.
_RE_STATE_LITERAL_LEAK = re.compile(r"\^[0-9]")

# Drive reference: bare ``F[1-7]`` as a standalone token. Word boundaries
# avoid matching ``F1A2`` or compound identifiers. Note: drive subscripts
# in CAS source are written ``_{F7}`` -- in English leakage they appear
# as ``F7`` standalone or inside parens like ``(F7)``.
_RE_DRIVE_LEAK = re.compile(r"\bF[1-7]\b")

# Bare CAS-jargon words: noetic(s), RPM, compile-time. Conservative —
# these words have no plain-English meaning that would false-positive in
# our corpus.
_RE_NOETIC_KEYWORD = re.compile(r"\bnoetic[s]?\b", re.IGNORECASE)
_RE_RPM_KEYWORD = re.compile(r"\bRPM\b")
_RE_COMPILE_TIME_KEYWORD = re.compile(r"\bcompile-time\b", re.IGNORECASE)

# Bare ``register`` is jargon ONLY when adjacent to a CAS register letter
# (T/A/f/E) or following a CAS-jargon word like ``the lens of domain P,
# register F6``. We flag the word ``register`` only when it co-occurs
# with a CAS letter token; plain-English uses like ``registered nurse`` or
# ``cash register`` would not match.
_RE_REGISTER_LEAK_CONTEXTUAL = re.compile(
    r"\bregister\s+(?:[TAfE]\b|F[1-9]\b|[PCEO]\b)", re.IGNORECASE
)
# Also flag ``transcendent register``, ``analytical register``, etc. — these
# are CAS-jargon-shaped phrasings.
_RE_REGISTER_LEAK_NAMED = re.compile(
    r"\b(?:transcendent|analytical|affective|embodied)\s+register[s]?\b",
    re.IGNORECASE,
)
# Plural ``registers`` is reliably CAS-jargon when the surrounding context
# is enumerative or comparative. Catches phrases like "across two distinct
# registers", "three registers", "different registers", "across the
# registers", which the v7.5 generator template tends to surface verbatim.
# We require an enumerative or comparative cue word before/after to avoid
# false-positive matches on "cash registers" / "voter registers" /
# "musical registers" (none of which co-occur with these cues in plain
# prose).
_RE_REGISTER_LEAK_PLURAL = re.compile(
    r"(?:"
    r"\b(?:two|three|four|five|several|distinct|different|multiple|"
    r"separate|various|many|all|both|each)\s+(?:[a-z]+\s+){0,2}registers\b"
    r"|\bregisters\s+of\s+(?:thought|attention|cognition|experience|mind)\b"
    r"|\bacross\s+(?:[a-z]+\s+){0,3}registers\b"
    r"|\bregisters\s+(?:of|in)\s+(?:CAS|the\s+system)\b"
    r")",
    re.IGNORECASE,
)

# Domain-word leaks: only when ``domain`` is adjacent to a CAS letter
# (P/C/E/O) or drive letter (F[1-9]). Conservative by design — plain
# uses like ``the domain of mathematics`` MUST NOT match.
#
# Patterns flagged:
#   ``domain P``, ``domain C``, ``domain E``, ``domain O``
#   ``P-Domain``, ``C-domain``, ``P Domain``  (any case)
#   ``domain F4``, ``F4 domain``
#   ``domain (P)``, ``domain marked P``, ``domain of E``
#   ``in domain E``, ``through domain P``, ``the domain P``
_RE_DOMAIN_LEAK = re.compile(
    r"(?:"
    r"\bdomain\s+[PCEO]\b"                  # domain P
    r"|\b[PCEO]\s*-\s*[Dd]omain\b"          # P-Domain, C-domain, etc.
    r"|\b[PCEO]\s+[Dd]omain\b"              # P Domain
    r"|\bdomain\s+F[1-9]\b"                 # domain F6
    r"|\bF[1-9]\s+domain\b"                 # F4 domain
    r"|\bdomain\s*\(\s*[PCEO]\s*\)"         # domain (P)
    r"|\bdomain\s+(?:marked|labeled|labelled)\s+[PCEO]\b"  # domain marked P
    r"|\bdomain\s+of\s+[PCEO]\b"            # domain of E
    r")"
)

# Policy B (2026-05-08): the calibration after 17f56d1 still accepted
# CAS-shaped prose such as "operational domain", "structure-and-order drive",
# and "emotional register". For Wave 2.5 training data those words are
# structural labels, not normal conversation, so reject them while preserving
# unrelated English like "the domain of mathematics" and "cash register".
_RE_DOMAIN_AXIS_WORD_LEAK = re.compile(
    r"\b(?:principled|foundational|cognitive|mental|evaluative|judging|"
    r"judgment|judgement|operational|behavioral|behavioural)\s+domain\b"
    r"|\bdomain\s+(?:of\s+)?(?:principles?|foundations?|cognition|"
    r"thinking|thought|evaluation|judg(?:e|ing|ment)|operation|"
    r"behavior|behaviour)\b",
    re.IGNORECASE,
)
_RE_DRIVE_AXIS_WORD_LEAK = re.compile(
    r"\bdrive\b",
    re.IGNORECASE,
)
_RE_REGISTER_AXIS_WORD_LEAK = re.compile(
    r"(?<!\bcash\s)\bregisters?\b",
    re.IGNORECASE,
)


def validate_no_cas_jargon_leakage(
    *,
    english_output: str,
) -> ValidatorResult:
    """Global Wave 2.5 jargon-leak guard.

    Reject when the English output contains CAS-notation or CAS-jargon
    surface-form leakage. Catches every leakage pattern the user reported
    after the 2026-05-08 paid preflight.

    Patterns flagged:

    * ``Ω`` (bare or prefixed, e.g. ``Ω_patience``, ``Ω_4``).
    * ``^[0-9]`` (any state-literal prefix, e.g. ``^3``, ``^9^P_{F7}``).
    * ``F[1-7]`` standalone (drive reference).
    * ``noetic`` / ``noetics`` (bare CAS-jargon word).
    * ``RPM`` (bare CAS-jargon word).
    * ``compile-time`` (bare CAS-jargon word).
    * ``register T`` / ``register F6`` / ``register P`` / ``transcendent
      register`` etc., plus bare ``register``/``registers`` except
      unrelated plain English like ``cash register``.
    * ``domain P`` / ``P-Domain`` / ``F4 domain`` / ``domain (P)`` /
      ``domain marked P`` / ``domain of E`` etc. (CAS-jargon-shaped — NOT
      plain ``the domain of mathematics``).
    * ``operational domain`` / ``cognitive domain`` / similar CAS-shaped
      domain-axis labels.
    * bare ``drive`` as a CAS-axis label.

    Pass when none of those patterns hit. Fail with the list of which
    patterns hit and the captured fragments.

    Applies to every cas_to_english record regardless of grammar
    category. The recipe-slot ``Ω_`` prefix-leak guard is a subset of
    this validator and remains in place for category-specific reporting.
    """
    text = english_output or ""
    hits: dict[str, list[str]] = {}

    def _add(name: str, pat: re.Pattern) -> None:
        matches = pat.findall(text)
        if matches:
            # Some findall patterns return tuples when alternation has
            # groups; flatten consistently to strings.
            flat: list[str] = []
            for m in matches:
                if isinstance(m, tuple):
                    flat.append(next((s for s in m if s), str(m)))
                else:
                    flat.append(m)
            hits[name] = flat

    _add("omega_symbol", _RE_OMEGA_BARE)
    _add("state_literal_prefix", _RE_STATE_LITERAL_LEAK)
    _add("drive_reference", _RE_DRIVE_LEAK)
    _add("noetic_keyword", _RE_NOETIC_KEYWORD)
    _add("rpm_keyword", _RE_RPM_KEYWORD)
    _add("compile_time_keyword", _RE_COMPILE_TIME_KEYWORD)
    _add("register_jargon_contextual", _RE_REGISTER_LEAK_CONTEXTUAL)
    _add("register_jargon_named", _RE_REGISTER_LEAK_NAMED)
    _add("register_jargon_plural", _RE_REGISTER_LEAK_PLURAL)
    _add("domain_jargon", _RE_DOMAIN_LEAK)
    _add("domain_axis_word", _RE_DOMAIN_AXIS_WORD_LEAK)
    _add("drive_axis_word", _RE_DRIVE_AXIS_WORD_LEAK)
    _add("register_axis_word", _RE_REGISTER_AXIS_WORD_LEAK)

    if not hits:
        return ValidatorResult(
            name="no_cas_jargon_leakage",
            passed=True,
        )

    # Build a compact reason string with the pattern names that hit and a
    # sample of the matched fragments.
    parts = []
    for name, frags in hits.items():
        sample = frags[:3]
        parts.append(f"{name}={sample}")
    return ValidatorResult(
        name="no_cas_jargon_leakage",
        passed=False,
        reason="CAS jargon leaked into English output: " + "; ".join(parts),
        detail={"hits": hits},
    )


# ---- Slot-specific structural-preservation validators ---------------------


def _english_contains_any(out_lower: str, tokens: Iterable[str]) -> bool:
    return any(tok.lower() in out_lower for tok in tokens)


# Match the ``CO-N`` operator surface form. CAS notation accepts both ``^N``
# and ``CO-N`` — same operator, different surface form (CLAUDE.md). The
# ``CO-N`` form appears in a small subset of binary_composition seeds (e.g.
# ``CO-9 ∘ CO-7``); the ``^N`` form covers the rest. The state-literal
# regex above does NOT match ``CO-N`` because there's no caret.
_RE_CO_N_OPERATOR = re.compile(r"\bCO-(\d+)\b")


def _extract_co_n_operators(source_cas: str) -> list[int]:
    """Return the list of operator indices that surface as ``CO-N`` in
    source. Order-preserving; duplicates retained (a record can legitimately
    repeat the same operator, e.g. ``CO-3 ∘ CO-3``).
    """
    out: list[int] = []
    for raw in _RE_CO_N_OPERATOR.findall(source_cas):
        try:
            out.append(int(raw))
        except ValueError:  # pragma: no cover — regex restricts to digits
            continue
    return out


def _state_literal_components(source_cas: str) -> list[dict[str, Any]]:
    """Return the list of state literals in source with their parsed
    components. Each entry: ``{noetic: int, domain: str|None, drive: int|None,
    register: str|None}``.
    """
    out: list[dict[str, Any]] = []
    for m in _RE_STATE_LITERAL.finditer(source_cas):
        try:
            n = int(m.group(1))
        except (TypeError, ValueError):
            continue
        d = m.group(2)
        drive_raw = m.group(3)
        reg = m.group(4)
        drive_idx: Optional[int] = None
        if drive_raw and drive_raw.startswith("F"):
            try:
                drive_idx = int(drive_raw[1:])
            except ValueError:
                drive_idx = None
        out.append({
            "noetic": n,
            "domain": d,
            "drive": drive_idx,
            "register": reg,
        })
    return out


def _check_state_literal_preservation(
    *,
    source_cas: str,
    english_output: str,
    require_drive: bool = True,
    require_register: bool = True,
) -> tuple[list[str], list[str]]:
    """Shared helper: returns (missing_components, present_components).

    Each entry of missing_components is a string like
    ``noetic_3@^3^P|A`` describing what didn't surface.
    """
    out_lower = english_output.lower()
    out_singular = re.sub(r"(\w+)s\b", r"\1", out_lower)
    missing: list[str] = []
    present: list[str] = []
    for lit in _state_literal_components(source_cas):
        n = lit["noetic"]
        d = lit["domain"]
        drive = lit["drive"]
        reg = lit["register"]
        tok = f"^{n}"
        if d:
            tok += f"^{d}"
        # Noetic alias check
        ntoks = NOETIC_VALIDATION_TOKENS.get(n, ())
        if ntoks and (
            _english_contains_any(out_lower, ntoks)
            or _english_contains_any(out_singular, ntoks)
        ):
            present.append(f"noetic_{n}@{tok}")
        else:
            missing.append(f"noetic_{n}@{tok}")
        # Domain alias check
        if d and d in DOMAIN_ALIASES:
            if _english_contains_any(out_lower, DOMAIN_ALIASES[d]):
                present.append(f"domain_{d}@{tok}")
            else:
                missing.append(f"domain_{d}@{tok}")
        # Drive alias check
        if drive is not None and require_drive:
            dtoks = DRIVE_ALIASES.get(drive, ())
            if dtoks and _english_contains_any(out_lower, dtoks):
                present.append(f"drive_F{drive}@{tok}")
            else:
                missing.append(f"drive_F{drive}@{tok}")
        # Register alias check
        if reg and require_register:
            # Register may be a single letter or a register-set ``⟨...⟩``;
            # the latter is handled per-letter.
            letters: list[str] = []
            if reg.startswith("⟨") and reg.endswith("⟩"):
                letters = [
                    x.strip() for x in reg[1:-1].split(",") if x.strip()
                ]
            else:
                letters = [reg]
            for letter in letters:
                rtoks = REGISTER_ALIASES.get(letter, ())
                if rtoks and _english_contains_any(out_lower, rtoks):
                    present.append(f"register_{letter}@{tok}")
                else:
                    missing.append(f"register_{letter}@{tok}")
    return missing, present


def validate_cas_to_english_state_literal_preservation(
    *,
    source_cas: str,
    english_output: str,
) -> ValidatorResult:
    """state_literal slot — noetic + domain + drive + register all surface.

    Skipped (passed=True) when the source has no state literals — e.g. a
    pure NoeticCluster diagram with raw ``^N`` operators is delegated to
    the diagram_export validator.
    """
    if not _RE_STATE_LITERAL.search(source_cas):
        return ValidatorResult(
            name="cas_to_english_state_literal_preservation",
            passed=True,
            reason="no state literals in source",
        )
    missing, present = _check_state_literal_preservation(
        source_cas=source_cas,
        english_output=english_output,
    )
    if missing:
        return ValidatorResult(
            name="cas_to_english_state_literal_preservation",
            passed=False,
            reason=f"missing state-literal components: {missing[:6]}",
            detail={"missing": missing, "present": present},
        )
    return ValidatorResult(
        name="cas_to_english_state_literal_preservation",
        passed=True,
        detail={"present": present},
    )


def validate_cas_to_english_binary_composition(
    *,
    source_cas: str,
    english_output: str,
) -> ValidatorResult:
    """binary_composition slot — both operands' noetic + domain surface.

    The operator (``+`` vs ``×``) is left to soft-checking via the prompt;
    we do NOT fail on operator phrasing. Drive + register checks are
    relaxed here (binary compositions tend to be drive-less in the
    preflight corpus).

    Two source surface forms are supported:

    1. ``^N^D + ^M^D`` (state-literal form) — handled by
       ``_check_state_literal_preservation``.
    2. ``CO-N ∘ CO-M`` (operator-only form, no domain) — checked via
       ``_extract_co_n_operators``. For each ``CO-N`` source operator,
       require an alias from ``NOETIC_VALIDATION_TOKENS[N]`` to surface
       in English. When an operator's alias is missing AND an alias for
       a DIFFERENT operator (one not present in the source) is being
       used in its place, flag ``operator_misrender_in_co_n_composition``
       — this catches the audit case ``CO-9 ∘ CO-7`` rendered with two
       ``^4`` aliases ('struck a chord' + 'hit hard').

    Mixed source — both ``^N`` and ``CO-N`` — is handled by running both
    branches; failures from either branch surface together.
    """
    state_lits = _state_literal_components(source_cas)
    co_n_ops = _extract_co_n_operators(source_cas)
    # Treat the source as a binary composition when total operands across
    # both surface forms (``^N^D`` literals + ``CO-N``) is >= 2. Mixed
    # sources like ``^3^P + CO-7`` are valid and should be evaluated on
    # both branches.
    total_operands = len(state_lits) + len(co_n_ops)
    if total_operands < 2:
        return ValidatorResult(
            name="cas_to_english_binary_composition",
            passed=True,
            reason="not a binary composition (fewer than 2 operands)",
        )
    diagnostics: list[str] = []
    detail: dict[str, Any] = {}
    if state_lits:
        missing, present = _check_state_literal_preservation(
            source_cas=source_cas,
            english_output=english_output,
            require_drive=False,
            require_register=False,
        )
        detail["missing"] = missing
        detail["present"] = present
        if missing:
            diagnostics.append(
                f"missing operand components in binary composition: "
                f"{missing[:6]}"
            )
    if co_n_ops:
        out_lower = english_output.lower()
        out_singular = re.sub(r"(\w+)s\b", r"\1", out_lower)
        source_op_set = set(co_n_ops)
        co_n_missing: list[int] = []
        co_n_present: list[int] = []
        for n in co_n_ops:
            ntoks = NOETIC_VALIDATION_TOKENS.get(n, ())
            if ntoks and (
                _english_contains_any(out_lower, ntoks)
                or _english_contains_any(out_singular, ntoks)
            ):
                co_n_present.append(n)
            else:
                co_n_missing.append(n)
        # Misrender detection: for each missing source operator, are aliases
        # for operators NOT in the source present in the English instead?
        # The phenomenon to catch is the audit case where CO-9 ∘ CO-7 was
        # rendered with two ^4 aliases.
        intruder_ops: list[int] = []
        for k in range(10):
            if k in source_op_set:
                continue
            ktoks = NOETIC_VALIDATION_TOKENS.get(k, ())
            if ktoks and (
                _english_contains_any(out_lower, ktoks)
                or _english_contains_any(out_singular, ktoks)
            ):
                intruder_ops.append(k)
        # Deduplicate while preserving order for stable diagnostics.
        co_n_missing_unique = sorted(set(co_n_missing))
        detail["co_n_source_operators"] = co_n_ops
        detail["co_n_missing"] = co_n_missing_unique
        detail["co_n_present"] = sorted(set(co_n_present))
        detail["co_n_intruder_operators"] = intruder_ops
        if co_n_missing_unique and intruder_ops:
            diagnostics.append(
                "operator_misrender_in_co_n_composition: source "
                f"CO-{co_n_missing_unique} aliases missing while aliases "
                f"for non-source operators ^{intruder_ops} surfaced "
                "instead"
            )
        elif co_n_missing_unique:
            diagnostics.append(
                "missing CO-N operator aliases: "
                f"CO-{co_n_missing_unique}"
            )
    if diagnostics:
        return ValidatorResult(
            name="cas_to_english_binary_composition",
            passed=False,
            reason="; ".join(diagnostics),
            detail=detail,
        )
    return ValidatorResult(
        name="cas_to_english_binary_composition",
        passed=True,
        detail=detail,
    )


def validate_cas_to_english_cross_register_omega(
    *,
    source_cas: str,
    english_output: str,
) -> ValidatorResult:
    """cross_register_omega slot — ``(^N^D|R1 × ^N^D|R2 [× ^N^D|R3]) =
    ^N^D|Ω_<stem>``.

    The emergent result name (the stem after ``Ω_``) MUST surface in
    English. Each register letter must surface via its alias. The noetic
    + domain must surface. The Ω anti-leak applies (already covered by
    the global jargon validator; we still report stem-coverage here for
    structured traceability).
    """
    # Match shape: ``(... ) = ^N^D|Ω_stem`` or ``= ^N|Ω_stem`` etc.
    # We accept the loose match: any ``Ω_<stem>`` after ``=``.
    eq_match = re.search(r"=\s*[^=]*?Ω_([A-Za-z][A-Za-z0-9_]*)", source_cas)
    if not eq_match:
        return ValidatorResult(
            name="cas_to_english_cross_register_omega",
            passed=True,
            reason="not a cross-register-omega (no Ω_<stem> after =)",
        )
    stem = eq_match.group(1)
    out_lower = english_output.lower()
    if stem.lower() not in out_lower:
        return ValidatorResult(
            name="cas_to_english_cross_register_omega",
            passed=False,
            reason=f"emergent omega stem missing from English: {stem!r}",
            detail={"stem": stem},
        )
    # Register coverage on operand register letters (the registers BEFORE
    # the ``=``, not on the result).
    pre_eq = source_cas.split("=", 1)[0]
    operand_regs: list[str] = []
    for m in _RE_STATE_LITERAL.finditer(pre_eq):
        reg = m.group(4)
        if not reg:
            continue
        if reg.startswith("⟨") and reg.endswith("⟩"):
            operand_regs.extend(
                x.strip() for x in reg[1:-1].split(",") if x.strip()
            )
        else:
            operand_regs.append(reg)
    missing_regs: list[str] = []
    operand_reg_set = set(operand_regs)
    for letter in operand_reg_set:
        rtoks = REGISTER_ALIASES.get(letter, ())
        if rtoks and not _english_contains_any(out_lower, rtoks):
            missing_regs.append(letter)
    unexpected_regs: list[str] = []
    for letter, rtoks in CROSS_REGISTER_EXTRA_MODE_ALIASES.items():
        if letter in operand_reg_set:
            continue
        if _english_contains_any(out_lower, rtoks):
            unexpected_regs.append(letter)
    register_count_mismatch = False
    if len(operand_reg_set) == 2 and re.search(
        r"\b(?:all\s+three|three\s+(?:modes|ways|registers|forms|"
        r"expressions))\b",
        out_lower,
    ):
        register_count_mismatch = True
    # Noetic + domain on the operands.
    missing, present = _check_state_literal_preservation(
        source_cas=pre_eq,
        english_output=english_output,
        require_drive=False,
        require_register=False,
    )
    diagnostics: list[str] = []
    if missing_regs:
        diagnostics.append(f"missing register descriptions: {missing_regs}")
    if unexpected_regs:
        diagnostics.append(
            f"unexpected register descriptions: {unexpected_regs}"
        )
    if register_count_mismatch:
        diagnostics.append(
            "register count mismatch: source has two operand registers "
            "but English says all three/three modes"
        )
    if missing:
        diagnostics.append(
            f"missing operand components: {missing[:6]}"
        )
    if diagnostics:
        return ValidatorResult(
            name="cas_to_english_cross_register_omega",
            passed=False,
            reason="; ".join(diagnostics),
            detail={
                "stem": stem,
                "missing_register_letters": missing_regs,
                "unexpected_register_letters": unexpected_regs,
                "register_count_mismatch": register_count_mismatch,
                "missing_operand_components": missing,
                "present_operand_components": present,
            },
        )
    return ValidatorResult(
        name="cas_to_english_cross_register_omega",
        passed=True,
        detail={"stem": stem, "present_operand_components": present},
    )


# Anaphor markers that license a stage clause referring back to a previously
# established noetic without restating the alias. The audit case shows that
# stages 2-4 of a 4-stage same-noetic chain commonly drop the noetic; some
# of those are real drops (the audit failure mode) and some legitimately
# refer back via "the same X" / "this same X" / "again" / "continues". The
# anaphor exception keeps the validator from flagging legitimate references.
_RPM_STAGE_ANAPHOR_RE = re.compile(
    r"\b(?:same|this|again|continues?|continuing|likewise|similarly|"
    r"another|repeats?|repeating|repeated|more of)\b",
    re.IGNORECASE,
)


def _stage_clause_window(
    *, english_output: str, stage_name: str
) -> Optional[str]:
    """Return the clause (within the same sentence) that mentions
    ``stage_name``. Sentence boundary = ``.`` or ``;`` or string start/end.
    Clause boundary within a sentence = ``,`` or ``and ``. Returns ``None``
    when ``stage_name`` does not appear.

    The returned window is the substring from the nearest preceding clause
    boundary to the next clause / sentence boundary. Stage-name match is
    case-insensitive. NO lookback into prior clauses — adjacent stages'
    aliases must not bleed in. Anaphor evidence is checked separately
    (``_stage_anaphor_window``) with a controlled lookback.
    """
    lower_output = english_output.lower()
    lower_stage = stage_name.lower()
    pos = lower_output.find(lower_stage)
    if pos < 0:
        return None
    # Find the nearest preceding sentence boundary.
    sent_start = max(
        lower_output.rfind(".", 0, pos),
        lower_output.rfind(";", 0, pos),
        -1,
    ) + 1
    # Find the nearest preceding clause boundary within the sentence. We
    # treat ``,`` and the conjunction `` and `` as clause boundaries —
    # they're how the corpus chains stage descriptions.
    clause_start = sent_start
    last_comma = lower_output.rfind(",", sent_start, pos)
    if last_comma >= 0:
        clause_start = max(clause_start, last_comma + 1)
    last_and = lower_output.rfind(" and ", sent_start, pos)
    if last_and >= 0:
        clause_start = max(clause_start, last_and + len(" and "))
    # Find the nearest following clause boundary.
    next_sent = min(
        (i for i in (
            lower_output.find(".", pos),
            lower_output.find(";", pos),
        ) if i >= 0),
        default=len(lower_output),
    )
    next_comma = lower_output.find(",", pos, next_sent)
    if next_comma < 0:
        next_comma = next_sent
    return english_output[clause_start:next_comma]


def _stage_anaphor_window(
    *, english_output: str, stage_name: str, lookback_chars: int = 60
) -> Optional[str]:
    """Return the anaphor-evidence window for ``stage_name``: the stage's
    own clause PLUS up to ``lookback_chars`` of the immediately preceding
    text within the same sentence. Used only for anaphor detection so a
    stage clause referring back via 'the same X' / 'continues' / etc. can
    inherit the prior stage's alias.

    Critically, this window is consulted ONLY for anaphor presence — never
    for noetic-alias presence — so adjacent stages' aliases do NOT bleed
    into the alias check.
    """
    lower_output = english_output.lower()
    lower_stage = stage_name.lower()
    pos = lower_output.find(lower_stage)
    if pos < 0:
        return None
    sent_start = max(
        lower_output.rfind(".", 0, pos),
        lower_output.rfind(";", 0, pos),
        -1,
    ) + 1
    last_comma = lower_output.rfind(",", sent_start, pos)
    last_and = lower_output.rfind(" and ", sent_start, pos)
    clause_start = sent_start
    if last_comma >= 0:
        clause_start = max(clause_start, last_comma + 1)
    if last_and >= 0:
        clause_start = max(clause_start, last_and + len(" and "))
    next_sent = min(
        (i for i in (
            lower_output.find(".", pos),
            lower_output.find(";", pos),
        ) if i >= 0),
        default=len(lower_output),
    )
    next_comma = lower_output.find(",", pos, next_sent)
    if next_comma < 0:
        next_comma = next_sent
    extended_start = max(sent_start, clause_start - lookback_chars)
    return english_output[extended_start:next_comma]


def _check_per_stage_noetic_preservation(
    *,
    source_cas: str,
    english_output: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """For each ``let stageNAME = ^N^D[...]`` binding in source, verify
    that an alias for ``^N`` surfaces inside the English clause that
    mentions ``stageNAME``. Returns (failed_stages, ok_stages); each entry
    is a dict with ``name``, ``noetic``, ``clause`` (truncated), and
    ``anaphor`` for ok stages.
    """
    failed: list[dict[str, Any]] = []
    ok: list[dict[str, Any]] = []
    for name, expr in _RE_LET_BINDING.findall(source_cas):
        # Only check stages with a state-literal RHS; skip e.g. ``let a =
        # NoeticCluster{...}`` (different shape, not in scope here).
        sl_match = _RE_STATE_LITERAL.search(expr)
        if not sl_match:
            continue
        try:
            n = int(sl_match.group(1))
        except ValueError:
            continue
        ntoks = NOETIC_VALIDATION_TOKENS.get(n, ())
        if not ntoks:
            continue
        clause = _stage_clause_window(
            english_output=english_output, stage_name=name
        )
        if clause is None:
            # Stage name absent from English entirely. The let_binding
            # validator will already flag this; per-stage noetic check
            # cannot evaluate without locating the clause, so skip.
            continue
        clause_lower = clause.lower()
        clause_singular = re.sub(r"(\w+)s\b", r"\1", clause_lower)
        if _english_contains_any(clause_lower, ntoks) or \
                _english_contains_any(clause_singular, ntoks):
            ok.append({"name": name, "noetic": n, "anaphor": False})
            continue
        # Anaphor exception: clause (or a small lookback window into the
        # prior clause within the same sentence) carries an explicit
        # back-reference like ``the same`` / ``continues`` / ``again``.
        anaphor_window = _stage_anaphor_window(
            english_output=english_output, stage_name=name
        )
        if anaphor_window and _RPM_STAGE_ANAPHOR_RE.search(anaphor_window):
            ok.append({"name": name, "noetic": n, "anaphor": True})
            continue
        failed.append({
            "name": name,
            "noetic": n,
            "clause": clause.strip()[:200],
        })
    return failed, ok


def validate_cas_to_english_rpm_chain(
    *,
    source_cas: str,
    english_output: str,
) -> ValidatorResult:
    """rpm_chain slot — ``A → B → C [→ D]`` chain.

    Checks: arrow count <= count of flow connectives in English. Each
    operand's noetic referenced. Operand resolution accommodates
    ``let X = ^N^D; ... X -> Y`` shape used in the preflight corpus.

    Per-stage noetic check (added 2026-05-08): when source contains
    ``let stageX = ^N^D[...]`` bindings, every stage's noetic alias must
    surface inside the clause that mentions ``stageX`` — not merely
    somewhere in the output. Anaphor exception: a clause referring back
    via ``same`` / ``this`` / ``again`` / ``continues`` etc. counts as
    inheriting the alias from the prior clause. Catches the audit case
    where a 4-stage ^8 chain rendered only the first stage with
    ``triggered`` and dropped the alias on stages 2-4.
    """
    if re.search(r"(?:Θ|Theta)\s*\(", source_cas):
        return ValidatorResult(
            name="cas_to_english_rpm_chain",
            passed=True,
            reason="recipe shape — rpm-chain validator skipped",
        )
    arrow_count = source_cas.count("→") + len(re.findall(r"->", source_cas))
    if arrow_count == 0:
        return ValidatorResult(
            name="cas_to_english_rpm_chain",
            passed=True,
            reason="no chain arrows in source",
        )
    out_lower = english_output.lower()
    # Flow connectives — generous list of natural-language flow markers.
    flow_re = re.compile(
        r"\b(?:then|next|leads?\s+to|leading\s+to|becomes?|"
        r"becoming|produces?|producing|yields?|yielding|creates?|creating|"
        r"transforms?\s+into|transforming\s+into|morphs?\s+into|"
        r"morphing\s+into|turns?\s+into|turning\s+into|"
        r"results?\s+in|resulting\s+in|gives?\s+rise|"
        r"feeds?\s+into|flows?\s+into|prompts?|prompting|"
        r"triggers?|triggering|after\s+that|in\s+turn|"
        r"and\s+then|which\s+then)\b",
        re.IGNORECASE,
    )
    flow_count = len(flow_re.findall(english_output))
    diagnostics: list[str] = []
    if flow_count < arrow_count:
        diagnostics.append(
            f"insufficient flow connectives: arrow_count={arrow_count} "
            f"but only {flow_count} flow markers in English"
        )
    # Each state literal in source must have its noetic surface in English.
    state_lits = _state_literal_components(source_cas)
    missing_noetics: list[str] = []
    out_singular = re.sub(r"(\w+)s\b", r"\1", out_lower)
    for lit in state_lits:
        ntoks = NOETIC_VALIDATION_TOKENS.get(lit["noetic"], ())
        if ntoks and not (
            _english_contains_any(out_lower, ntoks)
            or _english_contains_any(out_singular, ntoks)
        ):
            missing_noetics.append(f"^{lit['noetic']}")
    if missing_noetics:
        diagnostics.append(
            f"missing noetic operator descriptions: {missing_noetics}"
        )
    # Per-stage noetic preservation — catches the repeated-noetic stage
    # operator drop where the chain narration uses the alias on the first
    # stage only and then describes later stages by domain alone.
    stage_failed, stage_ok = _check_per_stage_noetic_preservation(
        source_cas=source_cas,
        english_output=english_output,
    )
    if stage_failed:
        names = [s["name"] for s in stage_failed]
        diagnostics.append(
            "stage_noetic_dropped: stage(s) "
            f"{names} mention the stage name but their clause "
            "lacks the bound noetic's alias and no anaphor"
        )
    if diagnostics:
        return ValidatorResult(
            name="cas_to_english_rpm_chain",
            passed=False,
            reason="; ".join(diagnostics),
            detail={
                "arrow_count": arrow_count,
                "flow_connective_count": flow_count,
                "missing_noetics": missing_noetics,
                "stage_noetic_failed": stage_failed,
                "stage_noetic_ok": stage_ok,
            },
        )
    return ValidatorResult(
        name="cas_to_english_rpm_chain",
        passed=True,
        detail={
            "arrow_count": arrow_count,
            "flow_connective_count": flow_count,
            "stage_noetic_ok": stage_ok,
        },
    )


# Match ``let <name> = <expr>`` in source CAS; capture name + expr fragment.
_RE_LET_BINDING = re.compile(
    r"\blet\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;\n]+)"
)


def validate_cas_to_english_let_binding(
    *,
    source_cas: str,
    english_output: str,
) -> ValidatorResult:
    """let_binding slot — variable name stem + bound expression content.

    Pass when at least one variable name appears in English (verbatim or
    quoted) AND the bound expression's noetic/domain at least partially
    surface (re-uses the state-literal preservation helper, drive+register
    optional).
    """
    bindings = _RE_LET_BINDING.findall(source_cas)
    if not bindings:
        return ValidatorResult(
            name="cas_to_english_let_binding",
            passed=True,
            reason="no let-bindings in source",
        )
    out_lower = english_output.lower()
    missing_names: list[str] = []
    for name, _expr in bindings:
        # The variable name itself must surface in English. Lowercase
        # match is sufficient — names are typically alphanumeric.
        if name.lower() not in out_lower:
            missing_names.append(name)
    diagnostics: list[str] = []
    if missing_names:
        diagnostics.append(f"missing let-binding names: {missing_names[:5]}")
    # Noetic coverage — at least one operand from each binding's RHS
    # surfaces. We pool across all bindings rather than per-binding to be
    # tolerant of compact narrations.
    missing, present = _check_state_literal_preservation(
        source_cas=source_cas,
        english_output=english_output,
        require_drive=False,
        require_register=False,
    )
    if missing and not present:
        # No operand surfaces at all -> definitely a fail. Partial misses
        # are allowed (the let-binding narration can be terse).
        diagnostics.append(
            f"no bound-expression operand surfaces in English: "
            f"{missing[:6]}"
        )
    if diagnostics:
        return ValidatorResult(
            name="cas_to_english_let_binding",
            passed=False,
            reason="; ".join(diagnostics),
            detail={
                "missing_names": missing_names,
                "missing_operand_components": missing,
            },
        )
    return ValidatorResult(
        name="cas_to_english_let_binding",
        passed=True,
        detail={
            "let_names": [n for n, _ in bindings],
            "present_operand_components": present,
        },
    )


def validate_cas_to_english_inversion(
    *,
    source_cas: str,
    english_output: str,
) -> ValidatorResult:
    """inversion slot — re-uses state-literal preservation, drive+register
    optional. Inversion sources are typically ``^N^D[|R]`` literals or
    pairs.
    """
    if not _RE_STATE_LITERAL.search(source_cas):
        return ValidatorResult(
            name="cas_to_english_inversion",
            passed=True,
            reason="no state literals in source",
        )
    missing, present = _check_state_literal_preservation(
        source_cas=source_cas,
        english_output=english_output,
        require_drive=False,
        require_register=False,
    )
    if missing:
        return ValidatorResult(
            name="cas_to_english_inversion",
            passed=False,
            reason=f"missing inversion components: {missing[:6]}",
            detail={"missing": missing, "present": present},
        )
    return ValidatorResult(
        name="cas_to_english_inversion",
        passed=True,
        detail={"present": present},
    )


# ---- Phantom-outcome (drive→outcome confusion) gate ----------------------
#
# Wave 2.5 stratified audit (2026-05-08) of the 398-record green run found
# inversion + rpm_chain records where the model rendered DRIVE subscripts
# (``_{F2}``, ``_{F3}``, ``_{F5}``, ``_{F6}``) as if they were named OUTCOME
# targets (``Ω_<stem>``). Concrete failures:
#
#   * ``^2^O_{F2} + ^3^O_{F6}`` rendered as "a positive pull toward the
#     outcome called wisdom, combined with a negative push away from the
#     outcome called structure". F2/F6 are drives (wisdom/structure are
#     the canonical drive aliases). The source has NO ``Ω_`` token.
#   * ``^2^O_{F3} + ^3^O_{F5}`` rendered as "drawn toward the outcome
#     named vitality... pushed away from the outcome named agency".
#   * ``^6^P_{F2}`` rendered as "in the realm of wisdom" — the F2 drive
#     subscript surfaces as if it were a domain/outcome label.
#
# All three slipped past the existing inversion / rpm_chain / state-literal
# validators, which only check that the noetic + domain alias surface in
# English. They do not catch "drive rendered as named outcome", which is a
# structural drift: it teaches a downstream model that drives and outcomes
# are interchangeable, breaking compiler round-trip.
#
# This gate fires on EVERY cas_to_english record (it is a safety check, not
# a category-specific structural check). Two trigger families:
#
#   1. Diagnostic phrases — "outcome called X", "outcome named X", "named
#      outcome X". Natural English rarely uses these constructions; in the
#      Wave 2.5 corpus they are nearly diagnostic of phantom-outcome
#      framing. Flagged whenever the captured stem is NOT one of the
#      source's ``Ω_`` stems.
#
#   2. Axis-word phrases — "the outcome X", "in the realm of X", "realm
#      of X" — flagged only when X is a CAS axis word (drive alias).
#      ``the outcome of the game`` and ``in the realm of mathematics`` are
#      plain English and must NOT match.
#
# Pass conditions: no phantom phrase hits, OR every captured stem appears
# in the source's ``Ω_<stem>`` token set (the framing is justified).

# Diagnostic phrases: "outcome called X", "outcome named X", "named
# outcome X". Capture the immediately following identifier (single word,
# possibly with underscore + alphanumeric suffix like ``reasoning_02``).
# These phrases are nearly diagnostic of phantom-outcome framing; flagged
# regardless of what X is, as long as X is not a source Ω_ stem.
_RE_OUTCOME_CALLED_NAMED = re.compile(
    r"\b(?:outcome\s+called|outcome\s+named|named\s+outcome)\s+"
    r"([A-Za-z][A-Za-z0-9_\-]*)\b",
    re.IGNORECASE,
)

# "the outcome <X>" — only flag when X is a CAS axis word AND not followed
# by a preposition (which would indicate plain-English usage like
# ``the outcome of the game`` or ``the outcome from the meeting``).
# We capture X and additionally require X is followed by sentence-end /
# punctuation / non-preposition continuation so plain English passes.
_RE_THE_OUTCOME_AXIS = re.compile(
    r"\bthe\s+outcome\s+"
    r"([A-Za-z][A-Za-z0-9_\-]*)"
    r"(?!\s+(?:of|for|in|to|from|on|at|by|with|that|which|was|is|"
    r"were|will|would|might|may|seemed|appeared|became|might))"
    r"\b",
    re.IGNORECASE,
)

# "(in the )realm of X" — only flag when X is a CAS axis word. Plain
# English uses like "the realm of mathematics" must pass.
_RE_REALM_OF_AXIS = re.compile(
    r"\b(?:in\s+the\s+realm\s+of|realm\s+of)\s+"
    r"([A-Za-z][A-Za-z0-9_\-]*)\b",
    re.IGNORECASE,
)

# CAS axis words: drive aliases (wisdom/vitality/agency/structure/unity/
# connection/purpose) plus close lexical variants from DRIVE_ALIASES.
# These are the words that, when surfaced as if they were Ω-style outcome
# targets, signal drive→outcome confusion.
#
# Built lazily inside the validator so it stays in sync with DRIVE_ALIASES
# without a separate manual list.


def _cas_axis_outcome_words() -> set[str]:
    """Return the lowercase set of words that, when used as a phantom
    outcome target, signal drive→outcome confusion.

    Drawn from ``DRIVE_ALIASES``. Multi-word aliases (``act with intent``)
    and compound forms (``life-energy``) are included as their first word
    for the single-token captures we extract from the regex.
    """
    words: set[str] = set()
    for aliases in DRIVE_ALIASES.values():
        for a in aliases:
            # Single-token form for matching against captured X.
            head = a.split()[0].lower()
            words.add(head)
            # Also include the full alias as a fallback (used only when
            # building a friendly hit list, not for matching a single-
            # word capture).
            words.add(a.lower())
    return words


def validate_no_phantom_outcome_framing(
    *,
    source_cas: str,
    english: str,
) -> ValidatorResult:
    """Reject English outputs that frame DRIVE subscripts as if they were
    named OUTCOME targets (``Ω_<stem>``).

    Background: in the Wave 2.5 green-run audit (2026-05-08), the model
    rendered ``^2^O_{F2}`` as "the outcome called wisdom" (F2 = wisdom
    drive). The source has no ``Ω_`` token, so the "outcome called X"
    framing is a hallucination. Same failure class as the original
    structural-shape-without-content drift.

    Triggers:

      * ``outcome called X`` / ``outcome named X`` / ``named outcome X``
        (where X is any single-word stem). These constructions are
        nearly diagnostic of named-outcome framing in our corpus.
      * ``the outcome X`` (where X is a single word that is NOT followed
        by a preposition, AND X is a CAS axis word — drive alias). This
        avoids false positives on plain English like "the outcome of the
        game".
      * ``realm of X`` / ``in the realm of X`` (where X is a CAS axis
        word). Plain English uses like "the realm of mathematics" pass
        because "mathematics" is not a CAS axis word.

    Pass conditions:

      * No phantom phrase hits in the English output, OR
      * The source CAS contains at least one ``Ω_<stem>`` token AND
        every captured X matches one of the source's ``Ω_`` stems
        (the framing is justified by an actual named outcome target).

    Returns a ``ValidatorResult`` with ``detail.phantom_phrases`` listing
    the matched fragments and ``detail.source_omega_stems`` for context.
    """
    text = english or ""
    src = source_cas or ""

    # Source Ω_<stem> set. When the source has Ω targets, "outcome
    # called <stem>" is legitimate iff <stem> matches one of them.
    # Accept both the canonical Ω_<stem> spelling and the ASCII fallback
    # ``Omega_<stem>`` that some diagram_export source records use as a
    # pre-compile representation.
    source_omega_stems = {s.lower() for s in _RE_OMEGA_NAMED.findall(src)}
    source_omega_stems |= {
        s.lower()
        for s in re.findall(r"\bOmega_([A-Za-z][A-Za-z0-9_]*)", src)
    }

    axis_words = _cas_axis_outcome_words()

    phantom_phrases: list[str] = []
    triggers: list[str] = []

    # 1. Diagnostic phrases — "outcome called/named X", "named outcome X".
    for m in _RE_OUTCOME_CALLED_NAMED.finditer(text):
        captured_stem = m.group(1).lower()
        if captured_stem in source_omega_stems:
            # Legitimate — references an actual source Ω target.
            continue
        phantom_phrases.append(m.group(0))
        triggers.append("outcome_called_or_named")

    # 2. "the outcome X" — flag only when X is a CAS axis word.
    for m in _RE_THE_OUTCOME_AXIS.finditer(text):
        captured = m.group(1).lower()
        if captured not in axis_words:
            continue
        if captured in source_omega_stems:
            continue
        phantom_phrases.append(m.group(0))
        triggers.append("the_outcome_axis_word")

    # 3. "realm of X" / "in the realm of X" — flag only when X is a CAS
    #    axis word.
    for m in _RE_REALM_OF_AXIS.finditer(text):
        captured = m.group(1).lower()
        if captured not in axis_words:
            continue
        if captured in source_omega_stems:
            continue
        phantom_phrases.append(m.group(0))
        triggers.append("realm_of_axis_word")

    if phantom_phrases:
        return ValidatorResult(
            name="no_phantom_outcome_framing",
            passed=False,
            reason=(
                "phantom outcome framing — drive (or other non-Ω) "
                "subscript rendered as a named outcome target: "
                f"{phantom_phrases[:6]}"
            ),
            detail={
                "phantom_phrases": phantom_phrases,
                "triggers": sorted(set(triggers)),
                "source_omega_stems": sorted(source_omega_stems),
                "source_has_omega": bool(source_omega_stems),
            },
        )
    return ValidatorResult(
        name="no_phantom_outcome_framing",
        passed=True,
        detail={
            "phantom_phrases": [],
            "source_omega_stems": sorted(source_omega_stems),
            "source_has_omega": bool(source_omega_stems),
        },
    )


# Diagram cluster constructor names. The English output must signal cluster /
# group / collection semantics.
_DIAGRAM_CLUSTER_NAMES = (
    "NoeticCluster",
    "RelationCluster",
    "StateCluster",
    "StateSet",
    "StateVariantCluster",
    "CoverOf",
    "PartitionOf",
    "Tuple",
    "Coordinate",
    "Product",
)
_DIAGRAM_GROUP_HINTS = (
    "cluster", "group", "collection", "set", "partition", "cover",
    "grouping", "divides", "divid", "tuple", "pair", "structure",
    "comprising", "consisting", "consists",
)
_COUNT_WORD_TO_INT = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _first_cluster_member_count(source_cas: str) -> int | None:
    m = re.search(
        r"\b(?:NoeticCluster|RelationCluster|StateCluster|StateSet|"
        r"StateVariantCluster)\s*\{([^{}]*)\}",
        source_cas,
    )
    if not m:
        return None
    items = [part.strip() for part in m.group(1).split(",") if part.strip()]
    return len(items) if items else None


def _explicit_cluster_counts(english_output: str) -> list[int]:
    count_word_re = "|".join(_COUNT_WORD_TO_INT)
    pat = re.compile(
        rf"\b({count_word_re}|\d+)\s+(?:distinct\s+|linked\s+|"
        rf"interconnected\s+)?(?:elements|components|operations|operators|"
        rf"states|members|items)\b",
        re.IGNORECASE,
    )
    counts: list[int] = []
    for m in pat.finditer(english_output):
        raw = m.group(1).lower()
        counts.append(_COUNT_WORD_TO_INT.get(raw, int(raw) if raw.isdigit() else -1))
    return [c for c in counts if c > 0]


def validate_cas_to_english_diagram_export(
    *,
    source_cas: str,
    english_output: str,
) -> ValidatorResult:
    """diagram_export slot — cluster type referenced AND member noetics
    surface.

    The "cluster type" is loosely satisfied by any group/collection word
    (cluster / group / collection / set / partition / etc.).
    """
    cluster_present = any(
        name in source_cas for name in _DIAGRAM_CLUSTER_NAMES
    )
    if not cluster_present:
        return ValidatorResult(
            name="cas_to_english_diagram_export",
            passed=True,
            reason="no diagram-cluster constructor in source",
        )
    out_lower = english_output.lower()
    has_group_hint = any(h in out_lower for h in _DIAGRAM_GROUP_HINTS)
    diagnostics: list[str] = []
    if not has_group_hint:
        diagnostics.append(
            "no group/cluster/collection word in English"
        )
    expected_member_count = _first_cluster_member_count(source_cas)
    rendered_counts = _explicit_cluster_counts(english_output)
    wrong_counts = [
        count for count in rendered_counts
        if expected_member_count is not None and count != expected_member_count
    ]
    if wrong_counts:
        diagnostics.append(
            f"wrong explicit cluster cardinality: expected "
            f"{expected_member_count}, saw {wrong_counts}"
        )
    # Member noetics: every ``^N`` in source must have its alias surface.
    member_re = re.compile(r"\^(\d)\b")
    member_ks = sorted({int(m) for m in member_re.findall(source_cas)})
    out_singular = re.sub(r"(\w+)s\b", r"\1", out_lower)
    missing_ks: list[int] = []
    for k in member_ks:
        ntoks = NOETIC_VALIDATION_TOKENS.get(k, ())
        if ntoks and not (
            _english_contains_any(out_lower, ntoks)
            or _english_contains_any(out_singular, ntoks)
        ):
            missing_ks.append(k)
    # We allow up to 25% of members to be unrendered for diagrams with
    # many members — the English narration legitimately abstracts when N
    # is large.
    threshold = max(1, int(len(member_ks) * 0.25 + 0.5)) if member_ks else 0
    if member_ks and len(missing_ks) > threshold:
        diagnostics.append(
            f"too many missing member noetics: {missing_ks} "
            f"(allowed {threshold} of {len(member_ks)})"
        )
    if diagnostics:
        return ValidatorResult(
            name="cas_to_english_diagram_export",
            passed=False,
            reason="; ".join(diagnostics),
            detail={
                "member_ks": member_ks,
                "missing_ks": missing_ks,
                "has_group_hint": has_group_hint,
                "expected_member_count": expected_member_count,
                "rendered_counts": rendered_counts,
            },
        )
    return ValidatorResult(
        name="cas_to_english_diagram_export",
        passed=True,
        detail={
            "member_ks": member_ks,
            "missing_ks": missing_ks,
            "has_group_hint": has_group_hint,
            "expected_member_count": expected_member_count,
            "rendered_counts": rendered_counts,
        },
    )


def validate_anti_copy_english_to_cas(
    *,
    prompt_text: str,
    generated_cas: str,
) -> ValidatorResult:
    """Reject when the generated CAS is byte-equal to any non-trivial
    contiguous substring of the prompt.

    Defense in depth: the v2 prompt redesign already removes the source CAS
    from the english_to_cas prompt. This validator catches edge cases where
    the prompt's English description accidentally contains a verbatim CAS
    fragment that the model could echo.
    """
    if not generated_cas or not generated_cas.strip():
        return ValidatorResult(
            name="anti_copy_english_to_cas",
            passed=False,
            reason="empty generated CAS",
        )
    candidate = generated_cas.strip()
    # Allow short outputs (fewer than 4 characters) without copy check —
    # those are too generic to fingerprint.
    if len(candidate) < 4:
        return ValidatorResult(
            name="anti_copy_english_to_cas",
            passed=True,
            detail={"reason": "candidate too short for copy detection"},
        )
    if candidate in prompt_text:
        return ValidatorResult(
            name="anti_copy_english_to_cas",
            passed=False,
            reason=(
                f"generated CAS is a verbatim substring of the prompt — "
                f"copy detected"
            ),
            detail={"candidate_length": len(candidate)},
        )
    return ValidatorResult(
        name="anti_copy_english_to_cas",
        passed=True,
        detail={"candidate_length": len(candidate)},
    )


# Token regexes used by validate_english_to_cas_structural_match. These are
# token-level extractors over a CAS expression — no AST dependency. They
# capture state literals (with optional ``_{Fk}`` and ``|R``), numeric
# coefficients, ``Ω_<name>`` targets, and the operator surface set.
_RE_STATE_LITERAL = re.compile(
    r"\^(\d+)(?:\^([A-Za-z]))?"      # ^N or ^N^D
    r"(?:_\{(F\d+)\})?"              # optional _{Fk}
    r"(?:\|([A-Za-z]|⟨[^⟩]+⟩))?"     # optional |R or |⟨R1,R2,…⟩
)
_RE_COEFFICIENT_TOKEN = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*\*")
# Operator surface: capture the structural / glue symbols. Each is a single
# token. The set Jaccard over these is the operator-structure check.
_OPERATOR_TOKENS = ("+", "×", "→", "->", "Λ", "Θ", "∘", "=")


def _extract_state_literal_set(s: str) -> Counter:
    """Multiset of state-literal tokens normalized for comparison.

    Each token is rendered as ``^N^D[_{Fk}][|R]`` after capture.
    """
    bag: Counter = Counter()
    for m in _RE_STATE_LITERAL.finditer(s):
        n, d, drive, reg = m.group(1), m.group(2), m.group(3), m.group(4)
        tok = f"^{n}"
        if d:
            tok += f"^{d}"
        if drive:
            tok += f"_{{{drive}}}"
        if reg:
            tok += f"|{reg}"
        bag[tok] += 1
    return bag


def _extract_coefficient_set(s: str) -> Counter:
    bag: Counter = Counter()
    for c in _RE_COEFFICIENT_TOKEN.findall(s):
        # Normalize: float-canonical so "0.7" and "0.70" compare equal.
        try:
            bag[f"{float(c):g}"] += 1
        except ValueError:
            bag[c] += 1
    return bag


def _extract_omega_set(s: str) -> set[str]:
    return set(_RE_OMEGA_NAMED.findall(s))


def _extract_operator_token_set(s: str) -> set[str]:
    present: set[str] = set()
    for op in _OPERATOR_TOKENS:
        if op in s:
            present.add(op)
    # Fold the ASCII '->' alias into '→' for Jaccard purposes — they are
    # the same operator.
    if "->" in present:
        present.discard("->")
        present.add("→")
    return present


def validate_english_to_cas_structural_match(
    *,
    source_cas: str,
    generated_cas: str,
    operator_jaccard_threshold: float = 0.7,
) -> ValidatorResult:
    """Structural-equivalence check between hidden source CAS and the
    model-generated CAS.

    Necessary because the v2 ``english_to_cas`` prompt does NOT show the
    source CAS — the validator must catch outputs that compile cleanly
    while being structurally wrong relative to the hidden source.

    Token-level (no AST dependency). Checks four dimensions:

      * ``state_literal_drift`` — multiset of ``^N^D[_{Fk}][|R]`` tokens
        must be equal between source and generated.
      * ``coefficient_mismatch`` — multiset of recipe coefficients
        (float-canonicalized) must be equal.
      * ``omega_target_mismatch`` — set of ``Ω_<name>`` tokens must be
        equal.
      * ``operator_structure_mismatch`` — Jaccard over the operator-token
        surface (`+`, `×`, `→`, `Λ`, `Θ`, `∘`, `=`) must be ≥
        ``operator_jaccard_threshold``.

    Pass = all four dimensions match. Fail = report the diverged
    dimension(s) in the result reason / detail for traceability.

    Reordering is tolerated by design: the state-literal and coefficient
    checks are MULTISET equality, and Ω is a set, so ``A + B`` and
    ``B + A`` both pass.
    """
    source_states = _extract_state_literal_set(source_cas)
    gen_states = _extract_state_literal_set(generated_cas)
    source_coefs = _extract_coefficient_set(source_cas)
    gen_coefs = _extract_coefficient_set(generated_cas)
    source_omegas = _extract_omega_set(source_cas)
    gen_omegas = _extract_omega_set(generated_cas)
    source_ops = _extract_operator_token_set(source_cas)
    gen_ops = _extract_operator_token_set(generated_cas)
    op_j = jaccard(source_ops, gen_ops)

    diverged: list[str] = []
    detail: dict[str, Any] = {
        "source_state_literals": dict(source_states),
        "generated_state_literals": dict(gen_states),
        "source_coefficients": dict(source_coefs),
        "generated_coefficients": dict(gen_coefs),
        "source_omegas": sorted(source_omegas),
        "generated_omegas": sorted(gen_omegas),
        "source_operators": sorted(source_ops),
        "generated_operators": sorted(gen_ops),
        "operator_jaccard": round(op_j, 4),
        "operator_jaccard_threshold": operator_jaccard_threshold,
    }
    if source_states != gen_states:
        missing = source_states - gen_states
        extra = gen_states - source_states
        diverged.append(
            "state_literal_drift "
            f"(missing={dict(missing)} extra={dict(extra)})"
        )
    if source_coefs != gen_coefs:
        missing_c = source_coefs - gen_coefs
        extra_c = gen_coefs - source_coefs
        diverged.append(
            "coefficient_mismatch "
            f"(missing={dict(missing_c)} extra={dict(extra_c)})"
        )
    if source_omegas != gen_omegas:
        diverged.append(
            "omega_target_mismatch "
            f"(missing={sorted(source_omegas - gen_omegas)} "
            f"extra={sorted(gen_omegas - source_omegas)})"
        )
    if op_j < operator_jaccard_threshold:
        diverged.append(
            f"operator_structure_mismatch (jaccard={op_j:.3f} "
            f"< threshold={operator_jaccard_threshold})"
        )
    if diverged:
        return ValidatorResult(
            name="english_to_cas_structural_match",
            passed=False,
            reason="; ".join(diverged),
            detail=detail,
        )
    return ValidatorResult(
        name="english_to_cas_structural_match",
        passed=True,
        detail=detail,
    )


def validate_invalid_to_corrected_jaccard(
    *,
    invalid_expression: str,
    corrected_expression: str,
    threshold: float = 0.6,
    short_string_edit_distance_floor: int = 4,
) -> ValidatorResult:
    """Reject when the corrected expression diverges too much from the
    invalid one.

    Decision logic (in order):
      1. If both inputs are SHORT (< 12 chars), use character-level
         Levenshtein-style edit distance as the metric: pass when the
         number of differing characters is at most
         ``short_string_edit_distance_floor`` AND the longer string is at
         most 1.5× the shorter (catches insertion of small substring vs
         replacement of whole expression).
      2. Otherwise use char-3gram Jaccard with ``threshold``.

    Why two-mode: a legitimate minimal edit like `Phi<6 2` -> `Phi<6:2>`
    is a single-character insertion on a 7-character string. Char-3gram
    Jaccard on such a short string measures ~0.4 because the local
    context shifts most of its trigrams — well below the 0.6 threshold,
    even though the change is structurally minimal. Edit distance is a
    better metric for short strings.

    Catches the audit's ~30% unrelated-correction failure mode without
    over-rejecting legitimate single-character fixes on short inputs.
    """
    inv_len = len(invalid_expression or "")
    cor_len = len(corrected_expression or "")
    if inv_len < 12 and cor_len < 12:
        # Short-string mode — edit distance + length-ratio sanity.
        edit = _levenshtein(invalid_expression, corrected_expression)
        longer = max(inv_len, cor_len)
        shorter = max(1, min(inv_len, cor_len))
        ratio = longer / shorter
        if edit <= short_string_edit_distance_floor and ratio <= 1.5:
            return ValidatorResult(
                name="invalid_to_corrected_jaccard",
                passed=True,
                detail={
                    "metric": "edit_distance",
                    "edit_distance": edit,
                    "ratio": round(ratio, 3),
                    "edit_floor": short_string_edit_distance_floor,
                },
            )
        return ValidatorResult(
            name="invalid_to_corrected_jaccard",
            passed=False,
            reason=(
                f"short-string edit distance {edit} > floor "
                f"{short_string_edit_distance_floor} or length ratio "
                f"{ratio:.2f} > 1.5 — corrected expression diverges too "
                f"much from invalid"
            ),
            detail={
                "metric": "edit_distance",
                "edit_distance": edit,
                "ratio": round(ratio, 3),
                "edit_floor": short_string_edit_distance_floor,
            },
        )
    a = _char_ngrams(invalid_expression, n=3)
    b = _char_ngrams(corrected_expression, n=3)
    j = jaccard(a, b)
    if j < threshold:
        return ValidatorResult(
            name="invalid_to_corrected_jaccard",
            passed=False,
            reason=(
                f"char-3gram Jaccard {j:.3f} < threshold {threshold} — "
                f"corrected expression diverges too much from invalid"
            ),
            detail={
                "metric": "char3gram_jaccard",
                "jaccard": round(j, 4),
                "threshold": threshold,
                "invalid_ngrams": len(a),
                "corrected_ngrams": len(b),
            },
        )
    return ValidatorResult(
        name="invalid_to_corrected_jaccard",
        passed=True,
        detail={
            "metric": "char3gram_jaccard",
            "jaccard": round(j, 4),
            "threshold": threshold,
        },
    )


def _levenshtein(a: str, b: str) -> int:
    """Standard Levenshtein edit distance (insert/delete/substitute = 1)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    # Two-row DP, len(a)+1 wide.
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr[j] = min(
                curr[j - 1] + 1,        # insertion
                prev[j] + 1,            # deletion
                prev[j - 1] + cost,     # substitution
            )
        prev = curr
    return prev[-1]


def validate_invalid_to_corrected_compiles(
    *,
    corrected_expression: str,
    compile_expression: Callable[[str], Any],
) -> ValidatorResult:
    """Reject when the corrected expression does not compile."""
    try:
        artifact = compile_expression(corrected_expression)
        valid = bool(getattr(artifact, "valid", False))
        if valid:
            return ValidatorResult(
                name="invalid_to_corrected_compiles",
                passed=True,
            )
        err = getattr(artifact, "error", None) or "compiler returned valid=False"
        return ValidatorResult(
            name="invalid_to_corrected_compiles",
            passed=False,
            reason=f"compiler rejected: {err}",
        )
    except Exception as exc:  # noqa: BLE001
        return ValidatorResult(
            name="invalid_to_corrected_compiles",
            passed=False,
            reason=f"compiler raised: {type(exc).__name__}: {exc}",
        )


# ---------------------------------------------------------------------------
# Wave 2.5 step — pre-generate English descriptions from seed CAS
# ---------------------------------------------------------------------------


@dataclass
class Wave2_5Record:
    """Per-record schema for the Wave 2.5 artifact.

    This artifact is the bridge between phase-1 cas_to_english and phase-2
    english_to_cas. The english_description here is the input the
    english_to_cas v2 prompt translates back to CAS.
    """

    seed_id: str
    source_cas: str
    grammar_category: str
    english_description: str
    prompt_template_version: str
    validators_run: list[str]
    validators_passed: list[str]
    validators_failed_reasons: dict[str, str]
    model_used: str
    raw_response: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    generated_at: str

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def run_validators_for_cas_to_english(
    *,
    seed: dict[str, Any],
    english_output: str,
) -> list[ValidatorResult]:
    """Run the cas_to_english content-preservation validators on a record.

    Always fires the global ``no_cas_jargon_leakage`` validator. Then fires
    category-specific validators that match the seed's grammar shape:

      * recipe → recipe coefficient + Ω-stem preservation
      * fractal_sequence → fractal k-index rendering
      * cross_register_omega → emergent Ω stem + register coverage
      * binary_composition → both operands' noetic + domain
      * state_literal / inversion → noetic + domain (+ drive + register)
      * rpm_chain → arrow count vs flow connectives + operand noetics
      * let_binding → variable name(s) + bound expression operands
      * diagram_export → cluster word + member noetics

    Multiple validators can fire when the source matches multiple shapes
    (e.g. a ``let X = Θ(...)`` seed runs both let_binding + recipe).
    """
    expr = seed["expression"]
    cat = seed.get("grammar_category", "unknown")
    results: list[ValidatorResult] = []
    # Global jargon-leak guard — always fires.
    results.append(
        validate_no_cas_jargon_leakage(english_output=english_output)
    )
    # Global phantom-outcome (drive→outcome confusion) guard — always
    # fires. Catches the Wave 2.5 audit's drive-subscript-rendered-as-Ω
    # failure class regardless of grammar_category.
    results.append(
        validate_no_phantom_outcome_framing(
            source_cas=expr, english=english_output
        )
    )
    is_recipe_shape = bool(re.search(r"(?:Θ|Theta)\s*\(", expr))
    # Recipe — fires when category matches OR the source has a Θ(...) shape.
    if cat == "recipe" or "Θ" in expr or "Theta" in expr:
        results.append(
            validate_cas_to_english_recipe_preservation(
                source_cas=expr, english_output=english_output
            )
        )
        # Sibling per-occurrence operator-alias check. Catches
        # operand-by-operand misrenders the set-based recipe validator
        # passes (e.g. ^3 rendered as a ^5 alias next to its coefficient).
        results.append(
            validate_cas_to_english_recipe_per_occurrence(
                source_cas=expr, english_output=english_output
            )
        )
    # Fractal — fires when category matches OR the source has Φ⟨...⟩ shape.
    if cat == "fractal_sequence" or "Φ" in expr or re.search(r"\bPhi\s*[<⟨]", expr):
        results.append(
            validate_cas_to_english_fractal_k_indices(
                source_cas=expr, english_output=english_output
            )
        )
    # Cross-register omega — fires on category match OR ``= ^N|Ω_stem``
    # shape. Recipe expressions also contain Ω targets, but they are handled
    # by the recipe validator; routing them here creates false "unexpected
    # register" failures on valid recipe descriptions.
    if cat == "cross_register_omega" or (
        not is_recipe_shape and re.search(r"=\s*[^=]*?Ω_[A-Za-z]", expr)
    ):
        results.append(
            validate_cas_to_english_cross_register_omega(
                source_cas=expr, english_output=english_output
            )
        )
    # RPM chain — fires on category match OR presence of ``->`` / ``→``.
    # Recipe arrows have their own preservation validator; scoring them as
    # RPM chains inflated Wave 2.5 recipe failures with unrelated noetic-flow
    # diagnostics.
    if (cat == "rpm_chain" or "→" in expr or "->" in expr) and not is_recipe_shape:
        results.append(
            validate_cas_to_english_rpm_chain(
                source_cas=expr, english_output=english_output
            )
        )
    # let_binding — fires on category match OR ``let X = ...`` shape.
    if cat == "let_binding" or _RE_LET_BINDING.search(expr):
        results.append(
            validate_cas_to_english_let_binding(
                source_cas=expr, english_output=english_output
            )
        )
    # diagram_export — fires on category match OR cluster constructor shape.
    if cat == "diagram_export" or any(
        name in expr for name in _DIAGRAM_CLUSTER_NAMES
    ):
        results.append(
            validate_cas_to_english_diagram_export(
                source_cas=expr, english_output=english_output
            )
        )
    # Binary composition — fires on category match OR when source contains
    # any ``CO-N`` operator (CO-N notation does not parse as a state literal
    # so it would otherwise slip past the category-only trigger). The
    # validator's own threshold (>= 2 total operands) decides whether the
    # check is actually applicable.
    if cat == "binary_composition" or _RE_CO_N_OPERATOR.search(expr):
        results.append(
            validate_cas_to_english_binary_composition(
                source_cas=expr, english_output=english_output
            )
        )
    # state_literal — fires on category match.
    if cat == "state_literal":
        results.append(
            validate_cas_to_english_state_literal_preservation(
                source_cas=expr, english_output=english_output
            )
        )
    # inversion — fires on category match.
    if cat == "inversion":
        results.append(
            validate_cas_to_english_inversion(
                source_cas=expr, english_output=english_output
            )
        )
    return results


def run_validators_for_english_to_cas(
    *,
    prompt_text: str,
    generated_cas: str,
    source_cas: Optional[str] = None,
    compile_expression: Optional[Callable[[str], Any]] = None,
    operator_jaccard_threshold: float = 0.7,
) -> list[ValidatorResult]:
    """Run the english_to_cas content-preservation + compile validators.

    When ``source_cas`` is provided (the hidden source CAS that was used
    to produce the English description in the Wave 2.5 step), the
    structural-match validator runs in addition to the verbatim-copy
    guard. This catches outputs that compile cleanly but are structurally
    wrong relative to the hidden source — the failure mode the
    verbatim-copy guard alone cannot catch.
    """
    results: list[ValidatorResult] = [
        validate_anti_copy_english_to_cas(
            prompt_text=prompt_text, generated_cas=generated_cas
        )
    ]
    if source_cas is not None:
        results.append(
            validate_english_to_cas_structural_match(
                source_cas=source_cas,
                generated_cas=generated_cas,
                operator_jaccard_threshold=operator_jaccard_threshold,
            )
        )
    if compile_expression is not None:
        results.append(
            validate_invalid_to_corrected_compiles(
                corrected_expression=generated_cas,
                compile_expression=compile_expression,
            )
        )
    return results


def run_validators_for_invalid_to_corrected(
    *,
    invalid_expression: str,
    corrected_expression: str,
    compile_expression: Optional[Callable[[str], Any]] = None,
    jaccard_threshold: float = 0.6,
) -> list[ValidatorResult]:
    """Run the invalid_to_corrected content-preservation + compile validators."""
    results: list[ValidatorResult] = [
        validate_invalid_to_corrected_jaccard(
            invalid_expression=invalid_expression,
            corrected_expression=corrected_expression,
            threshold=jaccard_threshold,
        )
    ]
    if compile_expression is not None:
        results.append(
            validate_invalid_to_corrected_compiles(
                corrected_expression=corrected_expression,
                compile_expression=compile_expression,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Helpers shared with phase-1 pipeline (re-imported when used as a module)
# ---------------------------------------------------------------------------


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_cas_from_response(text: str) -> str:
    """Strip markdown fences / preambles around a CAS expression.

    Re-implemented locally to keep the v2 module self-contained.
    """
    if not text:
        return ""
    s = text.strip()
    fence_re = re.compile(r"```[a-zA-Z0-9_-]*\n?(.*?)```", re.DOTALL)
    m = fence_re.search(s)
    if m:
        s = m.group(1).strip()
    s = re.sub(r"^(?:CAS|Expression|Output|Answer)\s*:\s*", "", s, flags=re.IGNORECASE)
    for line in s.splitlines():
        line = line.strip()
        if line:
            return line
    return s


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def render_fractal_sequence_deterministic(source_cas: str) -> str:
    """Render ``Phi<k:k:...>`` / ``Φ⟨k:k:...⟩`` without an LLM call.

    The paid Wave 2.5 calibrations showed Haiku repeatedly hallucinating
    different k-sequences even under an explicit deterministic table. Fractal
    expressions are already fully explicit index lists, so render them
    locally and let the regular validators verify the result.
    """
    m = _RE_FRACTAL_BODY.search(source_cas)
    if not m:
        raise ValueError(f"not a fractal sequence: {source_cas!r}")
    values = [int(v.strip()) for v in m.group(1).split(":") if v.strip()]
    if not values:
        raise ValueError(f"empty fractal sequence: {source_cas!r}")
    phrase_by_k = {
        0: "a thought",
        1: "paying attention",
        2: "being drawn to something",
        3: "an aversion",
        4: "something that struck a chord",
        5: "what is shaped by experience",
        6: "breaking it down",
        7: "muscle memory",
        8: "something that triggered a memory",
        9: "something that just clicked",
    }
    try:
        phrases = [phrase_by_k[v] for v in values]
    except KeyError as exc:
        raise ValueError(f"fractal k-value out of range: {exc.args[0]}") from exc
    if len(phrases) == 1:
        return f"A fractal sequence with one step: {phrases[0]}."
    if len(phrases) == 2:
        return f"A fractal sequence where {phrases[0]} leads to {phrases[1]}."
    head = ", then ".join(phrases[:-1])
    return f"A fractal sequence where {head}, and finally {phrases[-1]}."


def _join_natural(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def render_cross_register_omega_deterministic(source_cas: str) -> str:
    """Render cross-register Ω expressions without an LLM call.

    Paid Wave 2.5 calibrations showed Haiku repeatedly substituting
    analytical/felt/embodied/transcendent modes that were not present in
    the source. Cross-register Ω is a regular compiler shape, so we render
    its noetic/domain/register/outcome content directly and let validators
    verify the result.
    """
    eq_match = re.search(r"=\s*[^=]*?Ω_([A-Za-z][A-Za-z0-9_]*)", source_cas)
    if not eq_match:
        raise ValueError(f"not a cross-register omega expression: {source_cas!r}")
    stem = eq_match.group(1)
    pre_eq = source_cas.split("=", 1)[0]
    lits = _state_literal_components(pre_eq)
    if len(lits) < 2:
        raise ValueError(f"cross-register omega needs at least two operands: {source_cas!r}")
    noetic = lits[0]["noetic"]
    domain = lits[0]["domain"]
    registers: list[str] = []
    for lit in lits:
        reg = lit.get("register")
        if not reg:
            continue
        if isinstance(reg, str) and reg.startswith("⟨") and reg.endswith("⟩"):
            for part in reg[1:-1].split(","):
                part = part.strip()
                if part and part not in registers:
                    registers.append(part)
        elif reg not in registers:
            registers.append(reg)
    if not registers:
        raise ValueError(f"cross-register omega has no operand registers: {source_cas!r}")
    noetic_phrase = {
        0: "a thought",
        1: "paying attention",
        2: "being drawn toward something",
        3: "an aversion",
        4: "something that strikes a chord",
        5: "who you are, shaped by lived experience",
        6: "breaking down an idea",
        7: "practice becoming second nature",
        8: "something that triggers a memory",
        9: "something that just clicked",
    }.get(noetic, f"state {noetic}")
    domain_phrase = {
        "P": "in a principled foundational frame",
        "C": "in cognitive thinking",
        "E": "in evaluative judgment",
        "O": "in operational behavior",
    }.get(domain, "")
    register_phrase = {
        "T": "transcendent strategic perspective",
        "A": "analytical reasoning",
        "f": "felt emotion",
        "E": "embodied sensorimotor awareness",
    }
    rendered_registers = [
        register_phrase.get(reg, f"{reg} expression") for reg in registers
    ]
    base = noetic_phrase
    if domain_phrase:
        base = f"{base} {domain_phrase}"
    mode_word = "mode" if len(rendered_registers) == 1 else "modes"
    return (
        f"{base.capitalize()} expressed through "
        f"{_join_natural(rendered_registers)}, with those "
        f"{len(rendered_registers)} {mode_word} fusing into the outcome "
        f"called {stem}."
    )


# ---------------------------------------------------------------------------
# Wave 2.5 dry-run scaffold (no API calls).
#
# The full Wave 2.5 step (with API calls) will live in
# ``cas-synthetic/scripts/generate_wave3_step2_5_english_descriptions.py``
# which imports from this module. This function is the dry-run-safe core
# loop: caller supplies a ``model_callable`` that takes ``(system, user)``
# and returns ``(text, input_tokens, output_tokens)``. For dry runs the
# caller passes a function that returns deterministic fixture text.
# ---------------------------------------------------------------------------


def wave2_5_iterate(
    seeds: Iterable[dict[str, Any]],
    *,
    model_callable: Callable[[str, str], tuple[str, int, int]],
    model_name: str,
    cost_per_in_token: float,
    cost_per_out_token: float,
    accept_writer: Callable[[Wave2_5Record], None],
    reject_writer: Callable[[dict[str, Any]], None],
) -> dict[str, int]:
    """Generate English descriptions for a sequence of seeds.

    Pure function modulo the writer callbacks. No API calls happen here —
    the caller supplies ``model_callable``. Validators are applied to each
    output; rejected records go to ``reject_writer`` with the failure
    reason. Returns aggregate counts.
    """
    counts = {"accepted": 0, "rejected": 0, "errored": 0}
    for seed in seeds:
        try:
            if seed.get("grammar_category") == "fractal_sequence":
                text = render_fractal_sequence_deterministic(seed["expression"])
                in_tok = 0
                out_tok = 0
                record_model_name = "deterministic_fractal_renderer"
            elif seed.get("grammar_category") == "cross_register_omega":
                text = render_cross_register_omega_deterministic(seed["expression"])
                in_tok = 0
                out_tok = 0
                record_model_name = "deterministic_cross_register_omega_renderer"
            else:
                system, user = build_cas_to_english_prompt_v2(seed)
                text, in_tok, out_tok = model_callable(system, user)
                record_model_name = model_name
            if not text:
                counts["errored"] += 1
                reject_writer({
                    "seed_id": seed.get("seed_id", "unknown"),
                    "source_cas": seed["expression"],
                    "reason": "empty model response",
                    "validators_run": [],
                    "validators_failed_reasons": {},
                })
                continue
            results = run_validators_for_cas_to_english(
                seed=seed, english_output=text
            )
            failed = [r for r in results if not r.passed]
            if failed:
                counts["rejected"] += 1
                reject_writer({
                    "seed_id": seed.get("seed_id", "unknown"),
                    "source_cas": seed["expression"],
                    "reason": "; ".join(r.reason or "unknown" for r in failed),
                    "validators_run": [r.name for r in results],
                    "validators_failed_reasons": {
                        r.name: (r.reason or "unspecified") for r in failed
                    },
                    "english_output": text,
                })
                continue
            cost = (in_tok * cost_per_in_token) + (out_tok * cost_per_out_token)
            rec = Wave2_5Record(
                seed_id=seed.get("seed_id", f"unknown_{uuid.uuid4().hex[:8]}"),
                source_cas=seed["expression"],
                grammar_category=seed.get("grammar_category", "unknown"),
                english_description=text,
                prompt_template_version=WAVE_2_5_TEMPLATE_VERSION,
                validators_run=[r.name for r in results],
                validators_passed=[r.name for r in results if r.passed],
                validators_failed_reasons={},
                model_used=record_model_name,
                raw_response=text,
                input_tokens=in_tok,
                output_tokens=out_tok,
                estimated_cost_usd=round(cost, 6),
                generated_at=_now_utc_iso(),
            )
            accept_writer(rec)
            counts["accepted"] += 1
        except Exception as exc:  # noqa: BLE001
            counts["errored"] += 1
            reject_writer({
                "seed_id": seed.get("seed_id", "unknown"),
                "source_cas": seed.get("expression", ""),
                "reason": f"exception: {type(exc).__name__}: {exc}",
                "validators_run": [],
                "validators_failed_reasons": {},
            })
    return counts


# ---------------------------------------------------------------------------
# CLI entrypoint (dry-run only — paid generation is launched separately).
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Path D Wave 3 v2 — content-preservation rewrite. "
            "Library + CLI for Wave 2.5 (pre-generate English) and the "
            "v2 prompt builders / validators. Dry-run only by default."
        )
    )
    p.add_argument(
        "--demo-validators",
        action="store_true",
        help=(
            "Run the validators on hand-constructed example outputs and "
            "print accept/reject results. No API calls. Good for unit-style "
            "smoke."
        ),
    )
    return p.parse_args(argv)


def _demo_validators() -> int:
    """Print validator behavior on hand-constructed examples."""
    print("=== validate_cas_to_english_recipe_preservation ===")
    cases = [
        # (label, source_cas, english_output, expected_pass)
        (
            "good — coefficients + Ω stem present",
            "Θ(Ω_reasoning_02) = 1.5*^6^E + 1.5*^6^P|T → Ω_reasoning_02",
            "When 1.5 of unpacking in evaluative judgment combines with "
            "1.5 of unpacking principled foundations, the production yields "
            "the outcome called reasoning_02.",
            True,
        ),
        (
            "bad — coefficients dropped",
            "Θ(Ω_reasoning_02) = 1.5*^6^E + 1.5*^6^P|T → Ω_reasoning_02",
            "Breaking down evaluative judgment combines with breaking down "
            "principled foundations to produce reasoning.",
            False,
        ),
        (
            "bad — Ω_ prefix leaked into English",
            "Θ(Ω_reasoning_02) = 1.5*^6^E + 1.5*^6^P|T → Ω_reasoning_02",
            "1.5 of evaluative unpacking and 1.5 of principled unpacking "
            "produce Ω_reasoning_02.",
            False,
        ),
        (
            "skip — not a recipe",
            "^3^P|A + ^4^E|f",
            "Principled aversion mixes with evaluative resonance.",
            True,
        ),
    ]
    for label, src, eng, exp in cases:
        r = validate_cas_to_english_recipe_preservation(
            source_cas=src, english_output=eng
        )
        ok = (r.passed == exp)
        print(f"  [{'OK' if ok else 'FAIL'}] {label} -> passed={r.passed}, reason={r.reason}")
    print()
    print("=== validate_cas_to_english_fractal_k_indices ===")
    cases = [
        (
            "good — operator names present",
            "Φ⟨9:4:7⟩",
            "A thought popped into mind, then struck a chord, then became "
            "muscle memory.",
            True,
        ),
        (
            "bad — count misread",
            "Φ⟨2:9:6:7:8:9:2:5⟩",
            "A sequence of 8 stages moving through the operations 2, 9, 6, "
            "7, 8, 9, 2, 5.",
            False,
        ),
    ]
    for label, src, eng, exp in cases:
        r = validate_cas_to_english_fractal_k_indices(
            source_cas=src, english_output=eng
        )
        ok = (r.passed == exp)
        print(f"  [{'OK' if ok else 'FAIL'}] {label} -> passed={r.passed}, reason={r.reason}")
    print()
    print("=== validate_invalid_to_corrected_jaccard ===")
    cases = [
        (
            "good — minimal edit",
            "^13^E|f + ^1^E|E",
            "^1^E|f + ^1^E|E",
            True,
        ),
        (
            "bad — whole-expression rewrite",
            "^13^E|f + ^1^E|E",
            "^2^P + ^4^C|T → Ω_demo",
            False,
        ),
    ]
    for label, inv, cor, exp in cases:
        r = validate_invalid_to_corrected_jaccard(
            invalid_expression=inv, corrected_expression=cor
        )
        ok = (r.passed == exp)
        print(f"  [{'OK' if ok else 'FAIL'}] {label} -> passed={r.passed}, reason={r.reason}")
    print()
    print("=== validate_anti_copy_english_to_cas ===")
    cases = [
        (
            "good — independent generation",
            "Translate to CAS: a thought drawn toward foundations.",
            "^0 ∘ ^2^P",
            True,
        ),
        (
            "bad — verbatim copy of prompt fragment",
            "reference target: ^0^P|A + ^0^P|T (do not paste verbatim)",
            "^0^P|A + ^0^P|T",
            False,
        ),
    ]
    for label, prompt, gen, exp in cases:
        r = validate_anti_copy_english_to_cas(
            prompt_text=prompt, generated_cas=gen
        )
        ok = (r.passed == exp)
        print(f"  [{'OK' if ok else 'FAIL'}] {label} -> passed={r.passed}, reason={r.reason}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.demo_validators:
        return _demo_validators()
    print(
        "Path D Wave 3 v2 — library + CLI. Use --demo-validators to "
        "exercise the validators on hand-constructed examples. Paid "
        "generation is launched separately by the user."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
