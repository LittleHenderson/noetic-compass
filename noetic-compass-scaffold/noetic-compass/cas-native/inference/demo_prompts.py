"""Curated starter prompts for the CAS-Native v0 chat demo.

Each entry is a dict with bucket / prompt / ground_truth / feature.
All prompts pass canonical-exact prediction on the K=9 baseline checkpoint
(commit 3232f05, run dir
``structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045``).
Hand-curated from ``current_unique_eval_samples.jsonl`` to showcase specific
structural features per bucket. ``user_prompt`` and ``cas_expression`` fields
are copied verbatim from the eval JSONL.

Buckets covered:

- ``v74_baseline``  -- bare 40-state CAS (no register).
- ``v75_register`` -- Register-enriched expressions (|A, |f, |T, |E).
- ``v77_rule_four`` -- Same-state co-presence across multiple registers (``+``).
- ``v77_omega``    -- Cross-register integration into named emergent (``Ω``).
- ``v76_production`` -- Production recipes with weighted ingredients and arrow.
- ``meta_logic``   -- Typed clusters, relations, set ops, products.
"""

from __future__ import annotations

DEMO_PROMPTS: list[dict[str, str]] = [
    # ----- v74 baseline -- bare 40-state CAS (no register) -----
    {
        'bucket': 'v74_baseline',
        'prompt': 'I am learning CAS. The target structure is families: state expression; states: Noetic ^1; domain E (evaluative); drive F1. What is the precise notation?',
        'ground_truth': '^1^E_{F1}',
        'feature': 'simple state expression',
    },
    {
        'bucket': 'v74_baseline',
        'prompt': 'As a notation exercise, map this structure into CAS: families: state expression; states: Noetic ^8; domain C (cognitive); drive F6 / Noetic ^5; domain C (cognitive); drive F6; operators: composition star.',
        'ground_truth': '^8^C_{F6} * ^5^C_{F6}',
        'feature': 'composition of two states',
    },
    {
        'bucket': 'v74_baseline',
        'prompt': 'Given these CAS axes in words, produce the expression and a plain explanation: families: state expression; states: Noetic ^5; domain C (cognitive); drive F1 / Noetic ^6; domain E (evaluative); drive F1; operators: directed arrow.',
        'ground_truth': '^5^C_{F1} -> ^6^E_{F1}',
        'feature': 'directed transition between states',
    },
    {
        'bucket': 'v74_baseline',
        'prompt': 'I need the CAS expression for this recoverable structure: families: state expression; states: Noetic ^4; domain E (evaluative); drive F3 / Noetic ^8; domain O (operational); drive F3; operators: directed arrow. What notation should I use?',
        'ground_truth': '^4^E_{F3} -> ^8^O_{F3}',
        'feature': 'evaluative-to-operational transition',
    },
    # ----- v75 register -- single state or co-presence with registers -----
    {
        'bucket': 'v75_register',
        'prompt': 'I need the CAS expression for this recoverable structure: families: state expression; states: Noetic ^0; domain O (operational); drive F3; register |E (embodied). What notation should I use?',
        'ground_truth': '^0^O_{F3}|E',
        'feature': 'single state with |E embodied register',
    },
    {
        'bucket': 'v75_register',
        'prompt': 'As a notation exercise, map this structure into CAS: families: state expression; states: Noetic ^2; domain C (cognitive); drive F2; register |A (analytical).',
        'ground_truth': '^2^C_{F2}|A',
        'feature': 'single state with |A analytical register',
    },
    {
        'bucket': 'v75_register',
        'prompt': 'As a notation exercise, map this structure into CAS: families: state expression; states: Noetic ^9; domain P (principled); register |A (analytical).',
        'ground_truth': '^9^P|A',
        'feature': 'domain-omitted state with |A register',
    },
    {
        'bucket': 'v75_register',
        'prompt': 'Turn this formal natural-language CAS reading into the exact expression: families: state expression; states: Noetic ^4; domain O (operational); drive F6; register |A (analytical) / Noetic ^4; domain E (evaluative); drive F7; register |f (felt); operators: plus co-presence.',
        'ground_truth': '^4^O_{F6}|A + ^4^E_{F7}|f',
        'feature': 'register co-presence with +',
    },
    # ----- v77 Rule-4 -- same-state co-presence across registers -----
    {
        'bucket': 'v77_rule_four',
        'prompt': 'I am learning CAS. The target structure is families: state expression; states: Noetic ^1; domain E (evaluative); drive F7; register |E (embodied) / Noetic ^1; domain E (evaluative); drive F5; register |f (felt); operators: plus co-presence. What is the precise notation?',
        'ground_truth': '^1^E_{F7}|E + ^1^E_{F5}|f',
        'feature': '2-register Rule-4 co-presence',
    },
    {
        'bucket': 'v77_rule_four',
        'prompt': 'As a notation exercise, map this structure into CAS: families: state expression; states: Noetic ^7; domain C (cognitive); drive F5; register |A (analytical) / Noetic ^7; domain C (cognitive); drive F3; register |T (meaning-level) / Noetic ^7; domain C (cognitive); drive F1; register |f (felt); operators: plus co-presence.',
        'ground_truth': '^7^C_{F5}|A + ^7^C_{F3}|T + ^7^C_{F1}|f',
        'feature': '3-register Rule-4 co-presence (A,T,f)',
    },
    {
        'bucket': 'v77_rule_four',
        'prompt': 'Translate this exact CAS slot description into notation, then explain it briefly: families: state expression; states: Noetic ^5; domain O (operational); drive F4; register |A (analytical) / Noetic ^5; domain O (operational); drive F4; register |f (felt) / Noetic ^5; domain O (operational); drive F4; register |E (embodied) / Noetic ^5; domain O (operational); drive F4; register |T (meaning-level); operators: plus co-presence.',
        'ground_truth': '^5^O_{F4}|A + ^5^O_{F4}|f + ^5^O_{F4}|E + ^5^O_{F4}|T',
        'feature': 'full 4-register Rule-4 (all registers, same state)',
    },
    # ----- v77 omega -- cross-register integration into named emergent -----
    {
        'bucket': 'v77_omega',
        'prompt': 'As a notation exercise, map this structure into CAS: families: named emergent; states: Noetic ^1; drive F3; register |E (embodied) / Noetic ^1; drive F5; register |A (analytical) / Noetic ^1; named emergent target: Ω_presence; operators: cross-register integration, emergent assignment.',
        'ground_truth': '(^1_{F3}|E × ^1_{F5}|A) = ^1|Ω_presence',
        'feature': 'cross-register integration into omega bind',
    },
    {
        'bucket': 'v77_omega',
        'prompt': 'Given these CAS axes in words, produce the expression and a plain explanation: families: named emergent; states: Noetic ^1; domain E (evaluative); drive F3; register |T (meaning-level) / Noetic ^1; domain E (evaluative); drive F7; register |A (analytical) / Noetic ^1; domain E (evaluative); drive F6; register |E (embodied) / Noetic ^1; domain E (evaluative); named emergent target: Ω_witness; operators: cross-register integration, emergent assignment.',
        'ground_truth': '(^1^E_{F3}|T × ^1^E_{F7}|A × ^1^E_{F6}|E) = ^1^E|Ω_witness',
        'feature': '3-register omega with domain (witness)',
    },
    {
        'bucket': 'v77_omega',
        'prompt': 'Given these CAS axes in words, produce the expression and a plain explanation: families: named emergent; states: Noetic ^7; domain O (operational); drive F2; register |E (embodied) / Noetic ^7; domain O (operational); drive F5; register |A (analytical) / Noetic ^7; domain O (operational); drive F6; register |f (felt) / Noetic ^7; domain O (operational); named emergent target: Ω_cadence; operators: cross-register integration, emergent assignment.',
        'ground_truth': '(^7^O_{F2}|E × ^7^O_{F5}|A × ^7^O_{F6}|f) = ^7^O|Ω_cadence',
        'feature': '3-register omega bind (cadence)',
    },
    # ----- v76 production -- weighted recipe with arrow -----
    {
        'bucket': 'v76_production',
        'prompt': 'As a notation exercise, map this structure into CAS: families: production recipe, named emergent; production target Ω_focused_refusal; recipe coefficients: 0.53 times Noetic ^7; domain P (principled); drive F7; register |T (meaning-level) / 2.11 times Noetic ^3; domain P (principled); drive F2; register |A (analytical) / 1.04 times Noetic ^1; domain P (principled); drive F1; register |A (analytical); states: Noetic ^7; domain P (principled); drive F7; register |T (meaning-level) / Noetic ^3; domain P (principled); drive F2; register |A (analytical) / Noetic ^1; domain P (principled); drive F1; register |A (analytical); named emergent target: Ω_focused_refusal; operators: coefficient multiplication, ingredient sum, directed arrow, emergent assignment.',
        'ground_truth': 'Θ(Ω_focused_refusal) = 0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A + 1.04*^1^P_{F1}|A → Ω_focused_refusal',
        'feature': 'production recipe with weighted ingredients',
    },
    {
        'bucket': 'v76_production',
        'prompt': 'Turn this formal natural-language CAS reading into the exact expression: families: production recipe, named emergent; production target Ω_grounded_creative_insight; recipe coefficients: 1.52 times Noetic ^6; domain C (cognitive); drive F2; register |A (analytical) / 0.83 times Noetic ^8; domain C (cognitive); drive F3; register |A (analytical) / 0.98 times Noetic ^4; domain E (evaluative); drive F4; register |f (felt); leakage: 0.1 leakage to Ω_aversion_overflow; states: Noetic ^6; domain C (cognitive); drive F2; register |A (analytical) / Noetic ^8; domain C (cognitive); drive F3; register |A (analytical) / Noetic ^4; domain E (evaluative); drive F4; register |f (felt); named emergent target: Ω_aversion_overflow, Ω_grounded_creative_insight; operators: coefficient multiplication, ingredient sum, directed arrow, emergent assignment.',
        'ground_truth': 'Θ(Ω_grounded_creative_insight) = 1.52*^6^C_{F2}|A + 0.83*^8^C_{F3}|A + 0.98*^4^E_{F4}|f → Ω_grounded_creative_insight + 0.1*Λ·Ω_aversion_overflow',
        'feature': 'recipe with leakage (Lambda) side-product',
    },
    {
        'bucket': 'v76_production',
        'prompt': 'Turn this formal natural-language CAS reading into the exact expression: families: production recipe, named emergent; production target Ω_mentored_skill_transfer; recipe coefficients: 1.26 times Noetic ^5; domain O (operational); drive F5; register |E (embodied) / 1.87 times Noetic ^7; domain P (principled); drive F7; register |T (meaning-level) / 1.06 times Noetic ^5; domain C (cognitive); drive F5; register |A (analytical); leakage: 0.1 leakage to Ω_favoritism; states: Noetic ^5; domain O (operational); drive F5; register |E (embodied) / Noetic ^7; domain P (principled); drive F7; register |T (meaning-level) / Noetic ^5; domain C (cognitive); drive F5; register |A (analytical); named emergent target: Ω_favoritism, Ω_mentored_skill_transfer; operators: coefficient multiplication, ingredient sum, directed arrow, emergent assignment.',
        'ground_truth': 'Θ(Ω_mentored_skill_transfer) = 1.26*^5^O_{F5}|E + 1.87*^7^P_{F7}|T + 1.06*^5^C_{F5}|A → Ω_mentored_skill_transfer + 0.1*Λ·Ω_favoritism',
        'feature': 'cross-domain recipe with favoritism leakage',
    },
    # ----- meta-logic -- typed clusters, relations, set ops, products -----
    {
        'bucket': 'meta_logic',
        'prompt': 'I am learning CAS. The target structure is families: typed cluster; states: Noetic ^4 / Noetic ^1 / Noetic ^3 / Noetic ^2. What is the precise notation?',
        'ground_truth': 'NoeticCluster{^4, ^1, ^3, ^2}',
        'feature': 'typed Noetic cluster (set of Noetics)',
    },
    {
        'bucket': 'meta_logic',
        'prompt': 'Translate this exact CAS slot description into notation, then explain it briefly: families: typed cluster; states: Noetic ^5; domain P (principled) / Noetic ^5; domain C (cognitive) / Noetic ^5; domain E (evaluative) / Noetic ^5; domain O (operational); operators: directed arrow.',
        'ground_truth': 'RelationCluster{^5^P -> ^5^C, ^5^C -> ^5^E, ^5^E -> ^5^O}',
        'feature': 'relation cluster across P-C-E-O domain descent',
    },
    {
        'bucket': 'meta_logic',
        'prompt': 'Translate this exact CAS slot description into notation, then explain it briefly: families: typed cluster; states: Noetic ^8; domain C (cognitive) / Noetic ^1; domain C (cognitive) / Noetic ^0; domain P (principled); operators: difference.',
        'ground_truth': 'StateCluster{^8^C, ^1^C, ^0^P} ∖ StateCluster{^0^P, ^8^C}',
        'feature': 'state cluster set-difference',
    },
    {
        'bucket': 'meta_logic',
        'prompt': 'As a notation exercise, map this structure into CAS: families: Cartesian product; carriers: Noetics, Registers.',
        'ground_truth': 'Product(Noetics, Registers)',
        'feature': 'Cartesian product of carriers',
    },
]
