import os
import re

input_file = r'C:\Users\wakil\OneDrive\Desktop\tksCAS\book\programming_in_cas\Programming_in_CAS_v0_2_Draft.md'
output_file = r'C:\Users\wakil\OneDrive\Desktop\tksCAS\book\programming_in_cas\Programming_in_CAS_v0_3_TECH_REVIEW.md'

with open(input_file, 'r', encoding='utf-8-sig') as f:
    text = f.read()

# 1. Clean out all existing tags
text = re.sub(r'\s*\*\[.*?\]\*', '', text)
text = text.replace(' // *[future/pseudocode]*', '')

# 2. Fix front matter and text claims
text = text.replace('Version: 0.2 Draft', 'Version: 0.3 Draft / Technical Review Pending')
text = text.replace('perfectly embodies', 'conceptually maps to')
text = text.replace('blocks the execution before English is shown', 'is architected to block execution before English is shown')
text = text.replace('If the math holds, the AI is certified. If the math fails, the AI is flagged for non-compliance.', 'If the math holds, the AI is certified. If the math fails, the AI is flagged for structural review.')

# 3. Add exact replacements for tagging
tags = {
    '`^2^P_{F4}`': '`^2^P_{F4}` *[compiler-valid via cas notation]*',
    '`CO-6^C_{F2}`': '`CO-6^C_{F2}` *[conceptual]*',
    '`^6^C_{F2}`': '`^6^C_{F2}` *[compiler-valid via cas notation]*',
    '`^6^E_{F6}|f`': '`^6^E_{F6}|f` *[compiler-valid via cas notation]*',
    '`^3^O_{F5}|E`': '`^3^O_{F5}|E` *[compiler-valid via cas notation]*',
    '`^0^O_{F3}|E`': '`^0^O_{F3}|E` *[compiler-valid via cas notation]*',
    '`^7^C_{F5}|A + ^7^C_{F3}|T`': '`^7^C_{F5}|A + ^7^C_{F3}|T` *[compiler-valid via cas notation]*',
    '`^8^E_{F3}|E -> ^3^O_{F5}|E`': '`^8^E_{F3}|E -> ^3^O_{F5}|E` *[compiler-valid via cas notation]*',
    '`^4^C_{F3}|Q`': '`^4^C_{F3}|Q` *[compiler-invalid]*',
    '`^8^C * ^5^E`': '`^8^C * ^5^E` *[compiler-invalid]*',
    '`^1^P_{F8}`': '`^1^P_{F8}` *[compiler-invalid]*',
    '`^9_{F2}`': '`^9_{F2}` *[compiler-invalid]*',
    '`CO-4^O + CO-4^E`': '`CO-4^O + CO-4^E` *[compiler-invalid]*',
    '`Θ(Ω_joy) = ^8_E_{F3} + ^4_E_{F4}`': '`Θ(Ω_joy) = ^8_E_{F3} + ^4_E_{F4}` *[compiler-invalid]*',
    '`^2^C_{F2}|A`': '`^2^C_{F2}|A` *[compiler-valid via cas notation]*',
    '`^2^C_{F2}|T`': '`^2^C_{F2}|T` *[compiler-valid via cas notation]*',
    '`^8^C_{F2}|A`': '`^8^C_{F2}|A` *[compiler-valid via cas notation]*',
    '`^5^E_{F4}|f`': '`^5^E_{F4}|f` *[compiler-valid via cas notation]*',
    '`^4^O_{F6}|A + ^4^E_{F7}|f`': '`^4^O_{F6}|A + ^4^E_{F7}|f` *[compiler-valid via cas notation]*',
    '`^8^C_{F6} * ^5^C_{F6}`': '`^8^C_{F6} * ^5^C_{F6}` *[compiler-valid via cas notation]*',
    '`^3^C_{F6}`': '`^3^C_{F6}` *[compiler-valid via cas notation]*',
    '`^5^C_{F1} -> ^6^E_{F1}`': '`^5^C_{F1} -> ^6^E_{F1}` *[compiler-valid via cas notation]*',
    '`(^1_{F3}|E × ^1_{F5}|A) = ^1|Ω_presence`': '`(^1_{F3}|E × ^1_{F5}|A) = ^1|Ω_presence` *[compiler-valid via cas notation]*',
    '`Θ(Ω_focused_refusal) = 0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A + 1.04*^1^P_{F1}|A → Ω_focused_refusal`': '`Θ(Ω_focused_refusal) = 0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A + 1.04*^1^P_{F1}|A → Ω_focused_refusal` *[compiler-valid via cas notation]*',
    '`Phi< ^1, ^4, ^8 >`': '`Phi< ^1, ^4, ^8 >` *[conceptual]*',
    '`Phi< ^8^O_{F5}, ^4^E_{F3}, ^8^C_{F2} >`': '`Phi< ^8^O_{F5}, ^4^E_{F3}, ^8^C_{F2} >` *[conceptual]*',
    '`Phi< ^8^C, ^3^O_{F5} >`': '`Phi< ^8^C, ^3^O_{F5} >` *[conceptual]*',
    '`Phi< ^6^C, ^8^C, ^3^C >`': '`Phi< ^6^C, ^8^C, ^3^C >` *[conceptual]*',
    '`Phi< ^8^C|A, ^3^O|E, ^6^E|f >`': '`Phi< ^8^C|A, ^3^O|E, ^6^E|f >` *[conceptual]*',
    '`^3^C_{F5}[ Phi< ^6^C, ^8^C, ^3^C > ]`': '`^3^C_{F5}[ Phi< ^6^C, ^8^C, ^3^C > ]` *[future/pseudocode]*',
    '`Θ(Ω_methodical_review) = 2.0*^6^C_{F2}|A + 1.5*^0^C_{F6}|A + 0.5*^7^P_{F7}|A → Ω_methodical_review`': '`Θ(Ω_methodical_review) = 2.0*^6^C_{F2}|A + 1.5*^0^C_{F6}|A + 0.5*^7^P_{F7}|A → Ω_methodical_review` *[compiler-valid via cas notation]*',
    '`^9^P|A`': '`^9^P|A` *[compiler-valid via cas notation]*',
    '`^1^E_{F1}|f`': '`^1^E_{F1}|f` *[compiler-valid via cas notation]*',
    '`^1^E_{F1}|f + ^2^C_{F1}|A`': '`^1^E_{F1}|f + ^2^C_{F1}|A` *[compiler-valid via cas notation]*',
    '`Θ(Ω_name) = 1.0*^1^E + 2.0*^2^C → Ω_name`': '`Θ(Ω_name) = 1.0*^1^E + 2.0*^2^C → Ω_name` *[compiler-valid via cas notation]*',
    '`StateCluster{^8^C, ^1^C}`': '`StateCluster{^8^C, ^1^C}` *[compiler-valid via cas notation]*',
    '`RelationCluster{^5^P -> ^5^C}`': '`RelationCluster{^5^P -> ^5^C}` *[compiler-valid via cas notation]*',
    '`^5^O_{F4}|A + ^5^O_{F4}|f + ^5^O_{F4}|E`': '`^5^O_{F4}|A + ^5^O_{F4}|f + ^5^O_{F4}|E` *[compiler-valid via cas notation]*',
    '`RelationCluster{^2^P -> ^3^C -> ^4^E -> ^5^O}`': '`RelationCluster{^2^P -> ^3^C -> ^4^E -> ^5^O}` *[compiler-valid via cas notation]*',
    '`StateCluster{^8^C, ^1^C, ^0^P}`': '`StateCluster{^8^C, ^1^C, ^0^P}` *[compiler-valid via cas notation]*',
    '`RelationCluster{^5^P -> ^5^C, ^5^C -> ^5^E, ^5^E -> ^5^O}`': '`RelationCluster{^5^P -> ^5^C, ^5^C -> ^5^E, ^5^E -> ^5^O}` *[compiler-valid via cas notation]*',
    '`StateCluster{^8^C, ^1^C, ^0^P} \ StateCluster{^0^P, ^8^C}`': '`StateCluster{^8^C, ^1^C, ^0^P} \ StateCluster{^0^P, ^8^C}` *[compiler-valid via cas notation]*',
    '`let core_purpose = ^7^P_{F7}|T;`': '`let core_purpose = ^7^P_{F7}|T;` *[future/pseudocode]*',
    '`let execution = ^3^O_{F5}|A;`': '`let execution = ^3^O_{F5}|A;` *[future/pseudocode]*',
    '`let transition = core_purpose -> execution;`': '`let transition = core_purpose -> execution;` *[future/pseudocode]*',
    '`let user_lacunarity = StateCluster{^4, ^5, ^E};`': '`let user_lacunarity = StateCluster{^4, ^5, ^E};` *[future/pseudocode]*',
    '`let constraint_A = ^1^P_{F1}`': '`let constraint_A = ^1^P_{F1}` *[future/pseudocode]*',
    '`let constraint_B = ^8^O_{F5}`': '`let constraint_B = ^8^O_{F5}` *[future/pseudocode]*',
    '`policy strict_tutoring {`': '`policy strict_tutoring {` *[future/pseudocode]*',
    '`^1^P_{F1}|T`': '`^1^P_{F1}|T` *[compiler-valid via cas notation]*',
    '`^3^C_{F5}`': '`^3^C_{F5}` *[compiler-valid via cas notation]*',
    '`^3^C_{F5}|A + ^5^E_{F4}|f`': '`^3^C_{F5}|A + ^5^E_{F4}|f` *[compiler-valid via cas notation]*',
    '`CO-n^Domain_{Drive}`': '`CO-n^Domain_{Drive}` *[conceptual]*',
    '`CO-2^P_{F4}`': '`CO-2^P_{F4}` *[conceptual]*',
    '`CO-n`': '`CO-n` *[conceptual]*',
    '`CO-2`': '`CO-2` *[conceptual]*',
    '`CO-3`': '`CO-3` *[conceptual]*',
    '`CO-5`': '`CO-5` *[conceptual]*',
    '`CO-6`': '`CO-6` *[conceptual]*',
    '`CO-3^O`': '`CO-3^O` *[conceptual]*',
    '`CO-8^O`': '`CO-8^O` *[conceptual]*',
    '`CO-1^O`': '`CO-1^O` *[conceptual]*',
    '`CO-5^E`': '`CO-5^E` *[conceptual]*',
    '`CO-6^E`': '`CO-6^E` *[conceptual]*',
    '`(CO-2^P × CO-8^P) + CO-3^O`': '`(CO-2^P × CO-8^P) + CO-3^O` *[conceptual]*',
    '`CO-0^P`': '`CO-0^P` *[conceptual]*',
    '`CO-5^E ÷ CO-6^E`': '`CO-5^E ÷ CO-6^E` *[conceptual]*',
    '`CO-2^C_{F2}`': '`CO-2^C_{F2}` *[conceptual]*',
    '`CO-3^O_{F5}`': '`CO-3^O_{F5}` *[conceptual]*',
    '`CO-5^E_{F4}`': '`CO-5^E_{F4}` *[conceptual]*',
    '`CO-6^C_{F6}`': '`CO-6^C_{F6}` *[conceptual]*',
    '`CO-9^C`': '`CO-9^C` *[conceptual]*',
    '`CO-8^E`': '`CO-8^E` *[conceptual]*',
    '`CO-4^E`': '`CO-4^E` *[conceptual]*',
    '`CO-6^O_{F5}`': '`CO-6^O_{F5}` *[conceptual]*',
    '`CO-8^C_{F2}`': '`CO-8^C_{F2}` *[conceptual]*',
    '`CO-1^P_{F6}`': '`CO-1^P_{F6}` *[conceptual]*',
    '`CO-9^O_{F5}`': '`CO-9^O_{F5}` *[conceptual]*',
    '`CO-6^E_{F1}`': '`CO-6^E_{F1}` *[conceptual]*',
    '`StateCluster{^0^C, ^1^C, ^2^C, ^3^C, ^4^C, ^5^C, ^6^C, ^7^C, ^8^C, ^9^C}`': '`StateCluster{^0^C, ^1^C, ^2^C, ^3^C, ^4^C, ^5^C, ^6^C, ^7^C, ^8^C, ^9^C}` *[compiler-valid via cas notation]*'
}

for k, v in tags.items():
    text = text.replace(k, v)

# Update Appendix E
appendix_e_old = """## E. Source Mapping

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
- **Evaluations**: `docs/working/broader_b3_eval_at192/broader_b3_eval_findings.md`"""

appendix_e_new = """## E. Source Mapping

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
- **Python Model Implementations**: `noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_encoder.py`, `noetic-compass-scaffold/noetic-compass/cas-native/model/typed_fiber_decoder.py`, and `noetic-compass-scaffold/noetic-compass/cas-native/model/ssm_typed_fiber_decoder.py`
- **Loss Functions**: `noetic-compass-scaffold/noetic-compass/cas-native/training/fisher_rao_loss.py`
- **Runtime Execution**: `noetic-compass-scaffold/noetic-compass/cas-native/runtime/runtime_frame.py` and `noetic-compass-scaffold/noetic-compass/cas-native/runtime/turn_execution.py`
- **Generation Traces**: `noetic-compass-scaffold/noetic-compass/cas-native/trace/generation_trace.py`
- **Memory Systems**: `noetic-compass-scaffold/noetic-compass/cas-native/belief/geodesic_memory.py`
- **Evaluations**: `docs/working/broader_b3_eval_at192/broader_b3_eval_findings.md` and `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/broader_b3_eval_runner.py`"""

text = text.replace(appendix_e_old, appendix_e_new)

with open(output_file, 'w', encoding='utf-8-sig') as f:
    f.write(text)

print('Success')
