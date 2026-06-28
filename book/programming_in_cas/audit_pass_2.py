import os
import glob
import re

input_dir = r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\programming_in_cas"
output_file = os.path.join(input_dir, "Programming_in_CAS_v0_1_AUDITED.md")

disclaimer = """---
Title: Programming in CAS: A Practical Guide
Version: 0.2 (Audited)
Note: This book distinguishes implemented CAS tooling from future CAS-Native research. The CAS ecosystem is in active development. Examples tagged [future/pseudocode] or [speculative] represent roadmap capabilities.
---

"""

replacements = {
    "domain-omitted": "drive-omitted",
    "guarantees that the model cannot \"hallucinate\"": "is intended to reduce the model's capacity to hallucinate",
    "immune to the emotional hacking": "highly resistant to the emotional hacking",
    "un-hackable, mathematically verified firewall": "auditable, structurally verified firewall",
    "absolute ceiling": "architectural limit",
    "perfect privacy": "strong structural privacy",
    "mathematically prevented from getting weirder": "structurally constrained from erratic drift",
    "mathematical safety guarantees": "structural safety guardrails",
    "mathematical safety guarantee promised": "structural safety guardrail promised",
    "mathematically verified audit logs": "structurally verifiable audit logs",
    "objective mathematical proof": "objective structural verification",
    "# Chapter 17: Future Hopes": "# Chapter 17: Future Hopes (Roadmap & Speculative Architecture)",
    "literally cannot process information through the logical hardware": "is architecturally constrained from processing information through the logical hardware",
    "blocks the execution before a single word of English is shown": "blocks the execution before English is shown",
    "If the math fails, the AI is shut down. It moves AI regulation from subjective debate to objective mathematical proof.": "If the math fails, the AI is flagged for non-compliance. It moves AI regulation toward objective structural verification.",
    "CO-2^P_{F4}": "CO-2^P_{F4} *[conceptual]*",
    "CO-2": "CO-2 *[conceptual]*",
    "^2^P_{F4}": "^2^P_{F4} *[compiler-valid]*",
    "CO-6^C_{F2}": "CO-6^C_{F2} *[conceptual]*",
    "`^6^C_{F2}`": "`^6^C_{F2}` *[compiler-valid]*",
    "`^6^E_{F6}|f`": "`^6^E_{F6}|f` *[compiler-valid]*",
    "`^3^O_{F5}|E`": "`^3^O_{F5}|E` *[compiler-valid]*",
    "`^0^O_{F3}|E`": "`^0^O_{F3}|E` *[compiler-valid]*",
    "`^7^C_{F5}|A + ^7^C_{F3}|T`": "`^7^C_{F5}|A + ^7^C_{F3}|T` *[compiler-valid]*",
    "`^8^E_{F3}|E -> ^3^O_{F5}|E`": "`^8^E_{F3}|E -> ^3^O_{F5}|E` *[compiler-valid]*",
    "`^4^C_{F3}|Q`": "`^4^C_{F3}|Q` *[compiler-invalid]*",
    "`^8^C * ^5^E`": "`^8^C * ^5^E` *[compiler-invalid]*",
    "`^1^P_{F8}`": "`^1^P_{F8}` *[compiler-invalid]*",
    "`^9_{F2}`": "`^9_{F2}` *[compiler-invalid]*",
    "`CO-4^O + CO-4^E`": "`CO-4^O + CO-4^E` *[compiler-invalid]*",
    "`Θ(Ω_joy) = ^8_E_{F3} + ^4_E_{F4}`": "`Θ(Ω_joy) = ^8_E_{F3} + ^4_E_{F4}` *[compiler-invalid]*",
    "`^2^C_{F2}|A`": "`^2^C_{F2}|A` *[compiler-valid]*",
    "`^2^C_{F2}|T`": "`^2^C_{F2}|T` *[compiler-valid]*",
    "`^8^C_{F2}|A`": "`^8^C_{F2}|A` *[compiler-valid]*",
    "`^5^E_{F4}|f`": "`^5^E_{F4}|f` *[compiler-valid]*",
    "`^4^O_{F6}|A + ^4^E_{F7}|f`": "`^4^O_{F6}|A + ^4^E_{F7}|f` *[compiler-valid]*",
    "`^8^C_{F6} * ^5^C_{F6}`": "`^8^C_{F6} * ^5^C_{F6}` *[compiler-valid]*",
    "`^3^C_{F6}`": "`^3^C_{F6}` *[compiler-valid]*",
    "`^5^C_{F1} -> ^6^E_{F1}`": "`^5^C_{F1} -> ^6^E_{F1}` *[compiler-valid]*",
    "`(^1_{F3}|E × ^1_{F5}|A) = ^1|Ω_presence`": "`(^1_{F3}|E × ^1_{F5}|A) = ^1|Ω_presence` *[compiler-valid]*",
    "`Θ(Ω_focused_refusal) = 0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A + 1.04*^1^P_{F1}|A → Ω_focused_refusal`": "`Θ(Ω_focused_refusal) = 0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A + 1.04*^1^P_{F1}|A → Ω_focused_refusal` *[compiler-valid]*",
    "`Phi< ^1, ^4, ^8 >`": "`Phi< ^1, ^4, ^8 >` *[compiler-valid]*",
    "`^3^C_{F6}|A`": "`^3^C_{F6}|A` *[compiler-valid]*",
    "`^3^C_{F5}|A + ^5^E_{F4}|f`": "`^3^C_{F5}|A + ^5^E_{F4}|f` *[compiler-valid]*",
    "`^2^P_{F1}|T -> ^3^O_{F5}|E`": "`^2^P_{F1}|T -> ^3^O_{F5}|E` *[compiler-valid]*",
    "`Θ(Ω_methodical_review) = 2.0*^6^C_{F2}|A + 1.5*^0^C_{F6}|A + 0.5*^7^P_{F7}|A → Ω_methodical_review`": "`Θ(Ω_methodical_review) = 2.0*^6^C_{F2}|A + 1.5*^0^C_{F6}|A + 0.5*^7^P_{F7}|A → Ω_methodical_review` *[compiler-valid]*",
    "`^9^P|A`": "`^9^P|A` *[compiler-valid]*",
    "`^1^E_{F1}|f`": "`^1^E_{F1}|f` *[compiler-valid]*",
    "`^1^E_{F1}|f + ^2^C_{F1}|A`": "`^1^E_{F1}|f + ^2^C_{F1}|A` *[compiler-valid]*",
    "`Θ(Ω_name) = 1.0*^1^E + 2.0*^2^C → Ω_name`": "`Θ(Ω_name) = 1.0*^1^E + 2.0*^2^C → Ω_name` *[compiler-valid]*",
    "`StateCluster{^8^C, ^1^C}`": "`StateCluster{^8^C, ^1^C}` *[compiler-valid]*",
    "`RelationCluster{^5^P -> ^5^C}`": "`RelationCluster{^5^P -> ^5^C}` *[compiler-valid]*",
    "`^5^O_{F4}|A + ^5^O_{F4}|f + ^5^O_{F4}|E`": "`^5^O_{F4}|A + ^5^O_{F4}|f + ^5^O_{F4}|E` *[compiler-valid]*",
    "`RelationCluster{^2^P -> ^3^C -> ^4^E -> ^5^O}`": "`RelationCluster{^2^P -> ^3^C -> ^4^E -> ^5^O}` *[compiler-valid]*",
    "`Phi< ^8^O_{F5}, ^4^E_{F3}, ^8^C_{F2} >`": "`Phi< ^8^O_{F5}, ^4^E_{F3}, ^8^C_{F2} >` *[compiler-valid]*",
    "`StateCluster{^8^C, ^1^C, ^0^P}`": "`StateCluster{^8^C, ^1^C, ^0^P}` *[compiler-valid]*",
    "`RelationCluster{^5^P -> ^5^C, ^5^C -> ^5^E, ^5^E -> ^5^O}`": "`RelationCluster{^5^P -> ^5^C, ^5^C -> ^5^E, ^5^E -> ^5^O}` *[compiler-valid]*",
    "`StateCluster{^8^C, ^1^C, ^0^P} \ StateCluster{^0^P, ^8^C}`": "`StateCluster{^8^C, ^1^C, ^0^P} \ StateCluster{^0^P, ^8^C}` *[compiler-valid]*",
    "`let core_purpose = ^7^P_{F7}|T;`": "`let core_purpose = ^7^P_{F7}|T;` *[future/pseudocode]*",
    "`let execution = ^3^O_{F5}|A;`": "`let execution = ^3^O_{F5}|A;` *[future/pseudocode]*",
    "`let transition = core_purpose -> execution;`": "`let transition = core_purpose -> execution;` *[future/pseudocode]*",
    "`Phi< ^8^C, ^3^O_{F5} >`": "`Phi< ^8^C, ^3^O_{F5} >` *[compiler-valid]*",
    "`^1^P_{F1}|T`": "`^1^P_{F1}|T` *[compiler-valid]*",
    "`^3^C_{F5}`": "`^3^C_{F5}` *[compiler-valid]*",
    "`Phi< ^6^C, ^8^C, ^3^C >`": "`Phi< ^6^C, ^8^C, ^3^C >` *[compiler-valid]*",
    "`^3^C_{F5}[ Phi< ^6^C, ^8^C, ^3^C > ]`": "`^3^C_{F5}[ Phi< ^6^C, ^8^C, ^3^C > ]` *[future/pseudocode]*",
    "`let user_lacunarity = StateCluster{^4, ^5, ^E};`": "`let user_lacunarity = StateCluster{^4, ^5, ^E};` *[future/pseudocode]*",
    "`let constraint_A = ^1^P_{F1}`": "`let constraint_A = ^1^P_{F1}` *[future/pseudocode]*",
    "`let constraint_B = ^8^O_{F5}`": "`let constraint_B = ^8^O_{F5}` *[future/pseudocode]*",
    "policy strict_tutoring {": "policy strict_tutoring { // *[future/pseudocode]*"
}

def clean_old_tags(text):
    text = text.replace(" *[conceptual]*", "")
    text = text.replace(" *[compiler-valid]*", "")
    text = text.replace(" *[compiler-invalid]*", "")
    text = text.replace(" *[future/pseudocode]*", "")
    text = text.replace(" *[speculative]*", "")
    return text

def main():
    chapters = sorted(glob.glob(os.path.join(input_dir, "Chapter_*.md")))
    content = [disclaimer]
    
    for ch_file in chapters:
        with open(ch_file, "r", encoding="utf-8") as f:
            text = f.read()
            text = clean_old_tags(text)
            for old, new in replacements.items():
                text = text.replace(old, new)
            content.append(text)
            content.append("\n\n---\n\n")
            
    source_appendix = """
## E. Source Mapping

This book was synthesized from the following reference files in the CAS v7.5+ architecture repository:
- **CAS Foundational Clarifications**: `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`
- **CAS CLI Reference**: `README_CAS_CLI.md`
- **TKS v7.4 Voice Reference**: `docs/reference/tks_v7_4_voice_spec_reference.md`
- **TKS 28 Foundations Translation Key**: `docs/reference/tks_28_foundations_translation_key.md`
- **CAS Memory Substrate Design**: `docs/architecture/CAS_MEMORY_SUBSTRATE_PDR_AND_DESIGN.md`
- **CAS Transformer Architecture**: `docs/architecture/CAS_TRANSFORMER_ARCHITECTURE.md`
- **CABS Simplex MVP Build Spec**: `docs/working/simplex_mvp_build_spec_2026_05_11.md`
- **CABS Staged Training Recipe**: `docs/working/simplex_mvp_staged_training_canonical_recipe_2026_05_12.md`
- **Level 3 Conversational Spec**: `docs/working/level3_conversational_sdg_spec.md`
- **Stakeholder Explanations**: `docs/stakeholder/CAS_NATIVE_AI_DIFFERENTIATION_AND_CAPABILITIES.md`
- **Rust Engine (Compiler/Validator)**: `noetic-compass-scaffold/noetic-compass/cas-engine/crates/casc-syntax/src/lib.rs` and `noetic-compass-scaffold/noetic-compass/cas-engine/crates/casc-ir/src/lib.rs`
- **Python Model Implementations**: `noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_encoder.py` and `typed_fiber_decoder.py`
- **Generation Traces**: `noetic-compass-scaffold/noetic-compass/cas-native/trace/generation_trace.py`
- **Evaluations**: `docs/working/broader_b3_eval_at192/broader_b3_eval_findings.md`
"""

    exercise_answers = """
## F. Exercise Answers

**Exercise 1.1**
*Sentence:* "I just want to figure out the right thing to do."
*Possible underlying drives:*
1. F1 (Unity): Wanting to resolve moral dissonance and find the ethical truth.
2. F5 (Agency): Wanting to act and execute, but needing the instruction set first.
3. F6 (Structure): Wanting to ensure they don't break the rules or system policies.

**Exercise 1.2**
a) `CO-6^C_{F2}` is *[conceptual]*.
b) `^6^C_{F2}` is *[compiler-valid]*.

**Exercise 2.1**
1. Noetic: `^6` (Critical Evaluation)
2. Domain: `^E` (Evaluative)
3. Drive: `_{F6}` (Structure)
4. Register: `|f` (Affective)
*Description:* A person feeling deep, affective frustration that an emotional or relational situation lacks boundaries or order.

**Exercise 2.2**
`^3^O_{F5}|E` *[compiler-valid]*

**Exercise 3.1**
`^0^O_{F3}|E` *[compiler-valid]*: "Embodied identity/boundary maintenance in the operational domain driven by vitality." (e.g., A person holding a strenuous yoga pose to maintain physical health).

**Exercise 3.2**
`+` signifies co-presence. The two states (`^7^C_{F5}|A` and `^7^C_{F3}|T`) exist simultaneously; they do not merge into a new state.

**Exercise 4.1**
`^8^E_{F3}|E -> ^3^O_{F5}|E` *[compiler-valid]*

**Exercise 4.2**
It failed because `_E` is an invalid drive syntax. Drives must be specified as `_{Fk}`. The correct syntax for the drive is likely missing or malformed.

**Exercise 5.1**
`InvalidRegisterError`. `|Q` is not a valid register. Valid registers are `|T`, `|A`, `|f`, `|E`.

**Exercise 5.2**
Yes. `^P -> ^C -> ^E -> ^O` represents a complete, valid path of ontological descent from abstract principle down to physical action.

**Exercise 8.1**
`Phi< ^8^C|A, ^3^O|E, ^6^E|f >` *[compiler-valid]* (Registers added for completeness).

**Exercise 8.2**
`StateCluster{^0^C, ^1^C, ^2^C, ^3^C, ^4^C, ^5^C, ^6^C, ^7^C, ^8^C, ^9^C}` *[compiler-valid]*

**Exercise 9.1**
Instead of just matching the word "struggling," the AI knows the user is highly attuned to `^5^E_{F4}` (deep emotional resonance). It would advise the user to lead the intervention with affective empathy and connection, matching the user's natural structural strength, rather than suggesting a purely operational (`^O`) PIP process.

**Exercise 9.2**
`^2^P_{F2}|A` *[compiler-valid]* (Abstractification in the Principled domain, driven by Wisdom, done Analytically).

**Exercise 11.1**
"We cannot compromise on this value; it is the absolute foundation that holds everything else together."

**Exercise 11.2**
`^3^C_{F6}|A` *[compiler-valid]* (Concretizing a logical plan step-by-step, driven by a need for structure).
"""
    
    content.append(source_appendix)
    content.append(exercise_answers)
    
    with open(output_file, "w", encoding="utf-8-sig") as f:
        f.write("".join(content))
        
    print(f"Successfully wrote {output_file}")

if __name__ == "__main__":
    main()