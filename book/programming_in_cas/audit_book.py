import os
import re
import glob

# Configuration
input_dir = r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\programming_in_cas"
output_file = os.path.join(input_dir, "Programming_in_CAS_v0_1_AUDITED.md")

disclaimer = """---
Title: Programming in CAS: A Practical Guide
Version: 0.1 (Audited)
Note: This book distinguishes implemented CAS tooling from future CAS-Native research. The CAS ecosystem is in active development. Examples tagged [future-syntax] or [speculative] represent roadmap capabilities.
---

"""

# Replacements for overstatements and errors
replacements = {
    "domain-omitted": "drive-omitted",
    "guarantees that the model cannot \"hallucinate\"": "is designed to constrain the model from hallucinating",
    "immune to the emotional hacking": "highly resistant to the emotional hacking",
    "un-hackable, mathematically verified firewall": "structurally verifiable firewall",
    "absolute ceiling": "architectural limit",
    "perfect privacy": "strong structural privacy",
    "mathematically prevented from getting weirder": "structurally constrained from erratic drift",
    "mathematical safety guarantees": "structural safety guardrails",
    "mathematical safety guarantee promised": "structural safety guardrail promised",
    "mathematically verified audit logs": "structurally verifiable audit logs",
    "objective mathematical proof": "objective structural verification",
    "# Chapter 17: Future Hopes": "# Chapter 17: Future Hopes (Roadmap & Speculative Architecture)"
}

def tag_examples(text):
    # Tag conceptual
    text = re.sub(r'(`CO-[0-9][^`]*`)', r'\1 *[conceptual]*', text)
    
    # Tag compiler-valid (look for valid state literals ^Noetic^Domain or combinations like Phi, Θ, StateCluster)
    # Be careful not to double-tag if we run multiple times, though this runs once.
    def tag_valid(match):
        code = match.group(1)
        # Check if it looks like a full expression (has Noetic and Domain/Drive, or is a constructor)
        if re.search(r'\^[0-9]\^[PCEO]', code) or "Phi<" in code or "Θ(" in code or "StateCluster" in code or "RelationCluster" in code:
            return f"{code} *[compiler-valid]*"
        return code
        
    text = re.sub(r'(`\^?[^`]+`)', tag_valid, text)
    
    # Clean up any accidental double tags or tags on simple things like `^C`
    # (The regex above already filters for \^[0-9]\^[PCEO], which avoids tagging just `^C`)
    
    # Let's also tag invalid examples like `^1^P_{F8}` explicitly if they are mentioned as invalid
    text = text.replace("`^1^P_{F8}` *[compiler-valid]*", "`^1^P_{F8}` *[compiler-invalid]*")
    text = text.replace("`^9_{F2}` *[compiler-valid]*", "`^9_{F2}` *[compiler-invalid]*")
    
    return text

def main():
    chapters = sorted(glob.glob(os.path.join(input_dir, "Chapter_*.md")))
    
    content = []
    content.append(disclaimer)
    
    for ch_file in chapters:
        with open(ch_file, "r", encoding="utf-8") as f:
            text = f.read()
            
            # Apply replacements
            for old, new in replacements.items():
                text = text.replace(old, new)
                
            # Tag examples
            text = tag_examples(text)
            
            content.append(text)
            content.append("\n\n---\n\n")
            
    # Appendices
    source_appendix = """
## E. Source Mapping

This book was synthesized from the following reference files in the CAS v7.5+ architecture repository:
- **TKS v7.4 Voice Reference**: `docs/reference/tks_v7_4_voice_spec_reference.md`
- **TKS 28 Foundations Translation Key**: `docs/reference/tks_28_foundations_translation_key.md`
- **CAS Foundational Clarifications**: `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`
- **CAS CLI Reference**: `README_CAS_CLI.md`
- **CAS Memory Design**: `docs/architecture/CAS_MEMORY_SUBSTRATE_PDR_AND_DESIGN.md`
- **CABS Simplex MVP Spec**: `docs/working/simplex_mvp_build_spec_2026_05_11.md`
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
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("".join(content))
        
    print(f"Successfully wrote {output_file}")

if __name__ == "__main__":
    main()
