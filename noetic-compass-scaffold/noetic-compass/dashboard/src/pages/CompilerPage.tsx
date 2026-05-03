import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { axisColorForNode } from '../lib/casColorPalette';
import { apiFetch } from '../api/client';

// ── Constants ──

// ASCII lines split so the dot formation can be inlined after the S
const ASCII_LINES = [
  ' ██████╗ █████╗ ███████╗',
  '██╔════╝██╔══██╗██╔════╝',
  '██║     ███████║███████╗',
  '██║     ██╔══██║╚════██║',
  '╚██████╗██║  ██║███████║',
  ' ╚═════╝╚═╝  ╚═╝╚══════╝',
  'Cognitive Architecture',
  'Compiler v1.0',
  'Patent Pending',
];

const HELP_TEXT = `Commands:
  :help      Show this message
  :grammar   Print the BNF grammar
  :examples  Show sample expressions
  :natural   Show examples in natural language
  :mirror    Show (CAS expression) natural-language mirror pairs
  :dict      Show the CAS dictionary
  :dict TERM Filter the dictionary
  :learn     Show the guided compiler learning path
  :clear     Clear output
  :history   Show command history

Editing:
  Enter        Submit the expression
  Shift+Enter  Insert a newline
  ↑ / ↓        Recall command history (only when textbox is empty)

Multi-line layout:
  Blank line     → ; (statement separator)
  Single newline → continuation (a long recipe may wrap across lines)
  Or just write ; yourself at line ends — both work.

Type any CAS expression to compile it.`;

interface Example {
  expr: string;
  label: string;
  category: string;
  natural: string;
}

const EXAMPLES: Example[] = [
  // CAS v7.4 — Foundational notation
  { expr: '^2^P_{F2} × ^8^P_{F6}', label: 'Operator Composition (×)', category: 'Foundational', natural: 'Positive/affirming structure in the Principled domain under Vitality integrates with Above/Cause structure in the Principled domain under Purpose.' },
  { expr: '^5^P -> ^5^C', label: 'Domain Descent (P → C)', category: 'Foundational', natural: 'Female/Differentiation moves from a high-level principle into a concrete cognitive interpretation.' },
  { expr: '^2^P / ^3^P', label: 'Involution Division', category: 'Foundational', natural: 'A Positive principled state is compared against its Negative involution pair to expose contrast or missing balance.' },
  { expr: '^5^E + ^2^E', label: 'Co-Presence (+)', category: 'Foundational', natural: 'Female/Differentiation and Positive are both present in the Evaluative domain without forcing them into a single integrated result.' },
  { expr: 'RPM(F5)', label: 'Prerequisite Chain', category: 'Foundational', natural: 'Show the prerequisite ladder for Foundation 5, the Agency drive.' },
  { expr: 'Phi<3:8:5:2>', label: 'Fractal Analysis', category: 'Foundational', natural: 'Read the operator sequence Negative, Above/Cause, Female/Differentiation, Positive as a composed cognitive fractal.' },

  // CAS v7.5 — Phenomenological Registers
  { expr: '^3^P|A', label: 'Analytical-register Negative', category: 'v7.5 Registers', natural: 'Negative/Boundary is operating as a principled analytical judgment.' },
  { expr: '^3^P|f', label: 'Affective-register Negative', category: 'v7.5 Registers', natural: 'Negative/Boundary is operating as a principled felt or affective stance.' },
  { expr: '^2^C_{F2}|T', label: 'Compound state, Transcendent', category: 'v7.5 Registers', natural: 'Positive in the Cognitive domain, under the Vitality drive, is expressed through the Transcendent register.' },

  // CAS v7.6 — Production Semantics
  { expr: 'Θ(Ω_focus) = 0.6·^1^C + 0.4·^7^O → Ω_focus', label: 'Recipe definition', category: 'v7.6 Production', natural: 'Focus is produced from a 60 percent Mind/Cognitive ingredient plus a 40 percent Rhythm/Operational ingredient.' },
  { expr: 'Y_T(Ω_focus)', label: 'Theoretical yield query', category: 'v7.6 Production', natural: 'Ask for the ideal or maximum expected yield of the focus production recipe.' },
  { expr: 'Θ(Ω_book) | κ_deadline = 0.5·^7^P + 0.5·^6^C → Ω_book', label: 'Recipe with catalyst', category: 'v7.6 Production', natural: 'A book-output recipe uses a deadline catalyst while combining Rhythm/Principled and Male/Structure/Cognitive ingredients evenly.' },

  // CAS v7.7 — Register Multiplicity & Operator Discipline
  { expr: '^3^P|⟨A,f,T⟩', label: 'Register-set specification', category: 'v7.7 Operator Discipline', natural: 'The same Negative/Principled operation is explicitly viewed across Analytical, Affective, and Transcendent registers.' },
  { expr: '^3^P|A + ^3^P|f + ^3^P|T', label: 'Register co-presence (defeasible)', category: 'v7.7 Operator Discipline', natural: 'Analytical, affective, and transcendent forms of the same Negative/Principled operation are present together but not yet fused.' },
  { expr: '(^3^P|A × ^3^P|f × ^3^P|T) = Ω_refusal', label: 'Cross-register integration → emergent', category: 'v7.7 Operator Discipline', natural: 'Analytical, affective, and transcendent boundary signals integrate into the named emergent result refusal.' },

  // Meta-logic — Set theory / discrete math layer
  { expr: '^2 ∈ Noetics', label: 'Membership (^N ∈ Noetics)', category: 'Set Theory', natural: 'Positive is one member of the ten Noetic operators.' },
  { expr: 'NoeticCluster{^2, ^7} subseteq Noetics', label: 'Typed Noetic cluster', category: 'Set Theory', natural: 'The cluster containing Positive and Rhythm is a subset of the full Noetics set.' },
  { expr: 'StateVariantCluster{^3^P_{F2}|A, ^2^C|f}', label: 'State variant cluster', category: 'Set Theory', natural: 'Group two richly annotated state variants: an Analytical Negative/Principled/Vitality state and an Affective Positive/Cognitive state.' },
  { expr: 'StateCluster{^2^P, ^7^O} subseteq States', label: 'Typed State cluster', category: 'Set Theory', natural: 'The states Positive/Principled and Rhythm/Operational form a valid subset of the forty-state CAS space.' },
  { expr: 'NoeticCluster{^2, ^7} ∪ NoeticCluster{^7, ^8}', label: 'Set union', category: 'Set Theory', natural: 'Combine the two Noetic clusters into one cluster containing Positive, Rhythm, and Above/Cause.' },
  { expr: 'RelationCluster{^5^P -> ^5^C, ^5^C -> ^5^E}', label: 'Relation cluster', category: 'Set Theory', natural: 'Represent a dependency chain where Female/Differentiation descends from Principled to Cognitive to Evaluative.' },
  { expr: 'Coordinate{^2, P, F2, A}', label: 'CAS coordinate tuple', category: 'Set Theory', natural: 'Name the coordinate Positive, Principled domain, Vitality drive, Analytical register.' },
  { expr: 'Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})', label: 'Finite subobject meet', category: 'Set Theory', natural: 'Find the shared overlap between two Noetic clusters; here the common member is Rhythm.' },
  { expr: 'Product(Noetics, Domains)', label: 'Namespaced product', category: 'Set Theory', natural: 'Construct all pairings of the ten Noetics with the four Domains, producing the forty CAS state positions.' },
  { expr: '^2^P ∈ States', label: 'Compound state ∈ 40-state space', category: 'Set Theory', natural: 'Positive in the Principled domain is one member of the forty-state CAS space.' },
  { expr: 'F2 ∈ Drives', label: 'Drive membership', category: 'Set Theory', natural: 'Vitality is one member of the seven CAS drives.' },
  { expr: 'Foundation_1 ⊂ SubFoundations', label: 'Proper subset (28 sub-foundations)', category: 'Set Theory', natural: 'Foundation 1 names a proper subset inside the complete twenty-eight SubFoundations collection.' },
  { expr: '∅ ⊆ Noetics', label: 'Empty set is subset of every set', category: 'Set Theory', natural: 'The empty set is validly contained inside the Noetics set.' },
  { expr: '|Noetics|', label: 'Cardinality of Noetics (= 10)', category: 'Set Theory', natural: 'Count the Noetics set; it contains ten operators.' },
  { expr: '|States|', label: 'Cardinality of state space (= 40)', category: 'Set Theory', natural: 'Count the CAS state space; ten Noetics times four Domains gives forty states.' },
];

const OPERATOR_NAMES = [
  'Idea', 'Mind', 'Positive', 'Negative',
  'Vibration', 'Female', 'Male', 'Rhythm',
  'Above/Cause', 'Below/Effect',
];

// Quick-insert palette: every Unicode symbol that's hard to type on a US keyboard
const SYMBOL_PALETTE: { sym: string; title: string }[] = [
  // Production semantics (v7.6)
  { sym: 'Θ', title: 'Recipe Θ' },
  { sym: 'Ω_', title: 'Production target Ω_name' },
  { sym: 'Λ_', title: 'Leakage Λ_name' },
  { sym: 'κ_', title: 'Catalyst κ_name' },
  { sym: 'ι_', title: 'Inhibitor ι_name' },
  { sym: 'η', title: 'Efficiency η' },
  { sym: 'Φ', title: 'Fractal Φ' },
  // Operations
  { sym: '×', title: 'Compose / multiply ×' },
  { sym: '·', title: 'Recipe coefficient ·' },
  { sym: '→', title: 'Yields / dependency →' },
  // Set theory
  { sym: '∈', title: 'Member ∈' },
  { sym: '∉', title: 'Not member ∉' },
  { sym: '⊂', title: 'Proper subset ⊂' },
  { sym: '⊆', title: 'Subset ⊆' },
  { sym: '⊃', title: 'Proper superset ⊃' },
  { sym: '⊇', title: 'Superset ⊇' },
  { sym: '∪', title: 'Union ∪' },
  { sym: '∩', title: 'Intersection ∩' },
  { sym: '∖', title: 'Difference ∖' },
  { sym: '∅', title: 'Empty set ∅' },
  // Angle brackets (register-set notation)
  { sym: '⟨', title: 'Open angle ⟨ (register-set)' },
  { sym: '⟩', title: 'Close angle ⟩' },
];

// Frontend pre-processing of input before the compiler sees it. Two passes:
// 1. Multi-line layout normalization. The compiler treats `\n` as ordinary
//    whitespace, so we have to convert visual line breaks to the right thing.
//    Convention:
//      - **Blank line** (one or more `\n` with only whitespace between them)
//        → `;`  — separates statements.
//      - **Single newline** → ` ` — treated as line-continuation, so a long
//        recipe can wrap across multiple lines without breaking.
//    Users may also write `;` explicitly at line ends; in that case the `;` is
//    already the separator and the newline collapses to whitespace harmlessly.
// 2. ASCII fallbacks for users without easy Unicode entry — `in`, `notin`,
//    `subset`, etc. become their Unicode equivalents so the compiler (which
//    only tokenizes Unicode) accepts them.
// Order matters: blank-line collapse before single-newline collapse, and
// longer ASCII aliases before shorter (so `notin` doesn't match as `not`+`in`).
function expandAsciiAliases(text: string): string {
  return text
    .replace(/\n[ \t]*\n+/g, '; ')      // blank line(s) → ; statement separator
    .replace(/[ \t]*\n[ \t]*/g, ' ')    // single newline → space (continuation)
    .replace(/\bnotin\b/g, '∉')
    .replace(/\bsubseteq\b/g, '⊆')
    .replace(/\bsubset\b/g, '⊂')
    .replace(/\bsupseteq\b/g, '⊇')
    .replace(/\bsupset\b/g, '⊃')
    .replace(/\bemptyset\b/g, '∅')
    .replace(/\bin\b/g, '∈');
}

type ExampleView = 'cas' | 'natural' | 'mirror';

function formatExamplesForCommand(view: ExampleView): string {
  return EXAMPLES.map((example, index) => {
    const prefix = `${String(index + 1).padStart(2, ' ')}.`;
    if (view === 'natural') {
      return `${prefix} ${example.natural}\n    CAS: ${example.expr}`;
    }
    if (view === 'mirror') {
      return `${prefix} (${example.expr}) ${example.natural}`;
    }
    return `${prefix} ${example.expr}\n    → ${example.label}\n    NL: ${example.natural}`;
  }).join('\n');
}

const DOMAIN_NAMES: Record<string, string> = { P: 'Principled', C: 'Cognitive', E: 'Evaluative', O: 'Operational' };
const DRIVE_NAMES = ['Unity', 'Wisdom', 'Vitality', 'Connection', 'Agency', 'Structure', 'Purpose'];
const REGISTER_NAMES: Record<string, string> = { T: 'Transcendent', A: 'Analytical', f: 'Affective', E: 'Embodied' };

interface DictionaryEntry {
  term: string;
  category: string;
  notation: string;
  definition: string;
  example: string;
  learn: string;
}

interface LearningStep {
  title: string;
  goal: string;
  terms: string;
  practice: string;
}

const BASE_DICTIONARY: DictionaryEntry[] = [
  { term: 'Cognitive Architecture System', category: 'Framework', notation: 'CAS', definition: 'A formal framework for describing how any cognitive system — human, AI, biological, or hypothetical — composes Ideas. Built on 10 Noetic operators × 4 Domains (40 states), 7 Drives, and 4 Registers.', example: 'Product(Noetics, Domains)', learn: 'Universal Applicability: every primitive must apply to humans AND AI AND biological cognition.' },
  { term: 'CAS', category: 'Framework', notation: 'Cognitive Architecture Syntax', definition: 'The compiler notation for CAS — operators, domains, drives, registers, production recipes, and finite meta-logic.', example: 'Product(Noetics, Domains)', learn: 'Start with axes before composing expressions.' },
  { term: 'Noetic', category: 'Axes', notation: '^0..^9', definition: 'A cognitive primitive operator — one of the ten structural dynamics by which a Mind relates to an Idea (Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect).', example: '^2 ∈ Noetics', learn: 'Names are verbatim canonical from the Tootra Math Handbook; do not paraphrase.' },
  { term: 'Domain', category: 'Axes', notation: '^P ^C ^E ^O', definition: 'The operational tier where a Noetic fires: Principled (values, identity), Cognitive (thought), Evaluative (judgment), Operational (action). Total order P ≻ C ≻ E ≻ O.', example: '^5^P -> ^5^C', learn: 'Domain Descent runs P → C → E → O; feedback runs O → P.' },
  { term: 'Drive', category: 'Axes', notation: '_{F1}.._{F7}', definition: 'One of seven core motivational architectures (Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose). Drives pair into involutions: F1↔F7, F2↔F6, F3↔F5; F4 is self-dual.', example: '^2^P_{F2}', learn: 'Each Drive has a structural opposite — its inversion partner.' },
  { term: 'Foundation', category: 'Axes', notation: 'F1..F7', definition: 'Synonym for Drive. The seven foundational motivational primitives that pressure cognition; 7 × 4 Domains = 28 SubFoundations.', example: 'F2 ∈ Drives', learn: 'Drive and Foundation are interchangeable terms in CAS.' },
  { term: 'Register', category: 'Axes', notation: '|T |A |f |E', definition: 'The phenomenological register — operational character of a state: Transcendent (purpose-orienting), Analytical (logical), Affective (felt valence), Embodied (sensorimotor).', example: '^3^P|A', learn: 'Register says HOW a state operates, not WHAT it is. Optional but disambiguates.' },
  { term: 'State', category: 'Axes', notation: '^n^D', definition: 'One cell of the 40-state grid (10 Noetics × 4 Domains). Locates a Noetic operation at a specific operational tier.', example: '^2^P ∈ States', learn: 'State = Noetic × Domain. Add Drive and Register for a State Variant.' },
  { term: 'State Variant', category: 'Axes', notation: '^n^D_{Fk}|R', definition: 'A richer state with optional Drive and Register annotations.', example: '^3^P_{F2}|A', learn: 'Use variants when the state needs context beyond Noetic and Domain.' },
  { term: 'Involution Pair', category: 'Principles', notation: '^n ↔ ^m', definition: 'A pair of Noetics that mirror each other structurally: ^2 Positive ↔ ^3 Negative, ^5 Female ↔ ^6 Male, ^8 Above/Cause ↔ ^9 Below/Effect. ^0, ^1, ^4, ^7 are self-dual.', example: '^2^P / ^3^P', learn: 'Healthy cognition keeps involution pairs in balance; lopsided pairs surface as inversion-axis flags.' },
  { term: 'Inversion', category: 'Principles', notation: 'axis flip', definition: 'The framework operation of flipping an axis to surface its structural opposite. ^2 inverts to ^3; F2 (Wisdom) inverts to F6 (Structure). Inversion reveals what is missing or repressed in a cognitive pattern.', example: '^2^P → (inverted) ^3^P', learn: 'Inversion is a probe, not a prescription — it reveals structure rather than recommending the opposite.' },
  { term: 'Noetics', category: 'Built-in Sets', notation: 'Noetics', definition: 'The built-in finite set of all ten Noetic operators.', example: '|Noetics|', learn: 'Use membership with Noetic symbols: ^2 ∈ Noetics.' },
  { term: 'Domains', category: 'Built-in Sets', notation: 'Domains', definition: 'The built-in finite set {P, C, E, O}.', example: 'Product(Noetics, Domains)', learn: 'Product(Noetics, Domains) builds the 40 state positions.' },
  { term: 'Drives', category: 'Built-in Sets', notation: 'Drives', definition: 'The built-in finite set of F1 through F7.', example: 'F2 ∈ Drives', learn: 'Use Drives for membership claims about F-symbols.' },
  { term: 'Registers', category: 'Built-in Sets', notation: 'Registers', definition: 'The built-in finite set {T, A, f, E}.', example: '|Registers|', learn: 'The affective register is lowercase |f.' },
  { term: 'States', category: 'Built-in Sets', notation: 'States', definition: 'The built-in finite set of 40 Noetic x Domain state positions.', example: '|States|', learn: 'States do not replace variants; variants add Drive/Register detail.' },
  { term: 'Foundations', category: 'Built-in Sets', notation: 'Foundations', definition: 'The built-in finite set of seven foundation families.', example: '|Foundations|', learn: 'Foundations sit above SubFoundations.' },
  { term: 'SubFoundations', category: 'Built-in Sets', notation: 'SubFoundations', definition: 'The built-in finite set of 28 foundation-domain substructures.', example: 'Foundation_1 ⊂ SubFoundations', learn: 'Each foundation family contributes subfoundation members.' },
  { term: 'Empty Set', category: 'Built-in Sets', notation: '∅ / EmptySet', definition: 'The finite empty meta-set.', example: '∅ ⊆ Noetics', learn: 'The empty set is a subset of every finite set.' },
  { term: 'Composition / Integration', category: 'Dynamics', notation: '×', definition: 'Combines compatible CAS structures. Same-Noetic cross-register integration requires a named Ω result.', example: '(^3^P|A × ^3^P|f × ^3^P|T) = Ω_refusal', learn: 'Use × only when the result is integrated, not merely co-present.' },
  { term: 'Co-Presence', category: 'Dynamics', notation: '+', definition: 'Marks simultaneous presence without claiming an integrated emergent result.', example: '^3^P|A + ^3^P|f + ^3^P|T', learn: 'Use + before you can defend a named Ω integration.' },
  { term: 'Division / Contrast', category: 'Dynamics', notation: '/', definition: 'Compares or separates a state against another state, often useful for involution contrast.', example: '^2^P / ^3^P', learn: 'Use division to inspect contrast rather than production.' },
  { term: 'Domain Descent', category: 'Dynamics', notation: '→', definition: 'A directed move from one domain expression toward another.', example: '^5^P -> ^5^C', learn: 'Read arrows as dependency, descent, or yield depending on context.' },
  { term: 'Fractal Sequence', category: 'Dynamics', notation: 'Phi<...>', definition: 'A sequence of Noetic operators read as a composed cognitive pattern.', example: 'Phi<3:8:5:2>', learn: 'Read the numbers in order, then inspect the composed operator.' },
  { term: 'RPM', category: 'Dynamics', notation: 'RPM(Fk)', definition: 'Prerequisite-chain analysis for a foundation or drive.', example: 'RPM(F5)', learn: 'Use RPM when the question is what must be present first.' },
  { term: 'Recipe', category: 'Production', notation: 'Θ(Ω_name)', definition: 'A production expression defining how a named outcome is generated.', example: 'Θ(Ω_focus) = 0.6·^1^C + 0.4·^7^O → Ω_focus', learn: 'Recipe terms are weighted ingredients that yield a target.' },
  { term: 'Production Target', category: 'Production', notation: 'Ω_name', definition: 'A named emergent output or production result.', example: 'Ω_refusal', learn: 'Use meaningful Ω names for integrated results.' },
  { term: 'Coefficient', category: 'Production', notation: '0.6·', definition: 'A recipe weight assigned to a prerequisite ingredient.', example: '0.6·^1^C', learn: 'Weights describe recipe proportions, not absolute truth.' },
  { term: 'Theoretical Yield', category: 'Production', notation: 'Y_T(Ω)', definition: 'The ideal expected yield for a production target.', example: 'Y_T(Ω_focus)', learn: 'Ask Y_T when evaluating expected output.' },
  { term: 'Catalyst', category: 'Production', notation: 'κ_name', definition: 'A factor that helps a recipe proceed without becoming the target itself.', example: 'Θ(Ω_book) | κ_deadline = ...', learn: 'Catalysts change production conditions.' },
  { term: 'Inhibitor', category: 'Production', notation: 'ι_name', definition: 'A factor that suppresses or slows a production recipe.', example: 'Θ(Ω_focus) | ι_noise = ...', learn: 'Use inhibitors for blockers, not missing ingredients.' },
  { term: 'Leakage', category: 'Production', notation: 'Λ_name', definition: 'A side-channel or loss path in production semantics.', example: 'Λ_distraction', learn: 'Use leakage for where production energy goes instead.' },
  { term: 'Membership', category: 'Set Theory', notation: '∈ / ∉', definition: 'Claims that an object is or is not an element of a typed finite set.', example: '^2 ∈ Noetics', learn: 'Left side is an object; right side is a meta-set.' },
  { term: 'Subset', category: 'Set Theory', notation: '⊂ / ⊆', definition: 'Claims one finite meta-set is contained in another.', example: 'NoeticCluster{^2, ^7} ⊆ Noetics', learn: 'Both sides must be meta-sets.' },
  { term: 'Superset', category: 'Set Theory', notation: '⊃ / ⊇', definition: 'The reverse containment relation: the left set contains the right set.', example: 'Noetics ⊇ NoeticCluster{^2, ^7}', learn: 'Superset diagrams reverse the nesting direction.' },
  { term: 'Union', category: 'Set Theory', notation: '∪ / Union(A,B)', definition: 'Combines finite typed sets into their combined membership.', example: 'NoeticCluster{^2, ^7} ∪ NoeticCluster{^7, ^8}', learn: 'Union removes duplicate members.' },
  { term: 'Intersection / Pullback', category: 'Set Theory', notation: '∩ / Pullback(A,B)', definition: 'Finds the common overlap of finite typed sets; Pullback is used here as finite subobject meet.', example: 'Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})', learn: 'This is finite meet behavior, not arbitrary categorical maps.' },
  { term: 'Difference', category: 'Set Theory', notation: '∖ / Difference(A,B)', definition: 'Keeps members of the left set that are not in the right set.', example: 'Difference(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})', learn: 'Read difference left-to-right.' },
  { term: 'Cardinality', category: 'Set Theory', notation: '|X|', definition: 'Counts the number of elements in a finite meta-set.', example: '|States|', learn: 'Cardinality applies to sets, not individual Noetics.' },
  { term: 'Noetic Cluster', category: 'Set Theory', notation: 'NoeticCluster{...}', definition: 'A typed finite cluster whose members are Noetic operators.', example: 'NoeticCluster{^2, ^7}', learn: 'Use this when nesting Noetics inside a set-like structure.' },
  { term: 'State Cluster', category: 'Set Theory', notation: 'StateCluster{...}', definition: 'A typed finite cluster whose members are 40-space states.', example: 'StateCluster{^2^P, ^7^O}', learn: 'Use state clusters when domains matter.' },
  { term: 'State Variant Cluster', category: 'Set Theory', notation: 'StateVariantCluster{...}', definition: 'A typed finite cluster whose members can carry Drive and Register annotations.', example: 'StateVariantCluster{^3^P_{F2}|A, ^2^C|f}', learn: 'Use variant clusters for richer annotated states.' },
  { term: 'Relation Cluster', category: 'Set Theory', notation: 'RelationCluster{a → b}', definition: 'A finite typed cluster of directed relation rows.', example: 'RelationCluster{^5^P → ^5^C, ^5^C → ^5^E}', learn: 'Use relation clusters for dependency rows.' },
  { term: 'Coordinate', category: 'Set Theory', notation: 'Coordinate{n,D,F,R}', definition: 'A coordinate tag naming a Noetic, Domain, Drive, and Register position.', example: 'Coordinate{^2, P, F2, A}', learn: 'Coordinates are compact locator tags.' },
  { term: 'Product', category: 'Set Theory', notation: 'Product(A,B)', definition: 'A namespaced finite Cartesian product that avoids collision with CAS integration ×.', example: 'Product(Noetics, Domains)', learn: 'Use Product for set products; use × for CAS integration.' },
  { term: 'Cover', category: 'Set Theory', notation: 'CoverOf(Base, U1...)', definition: 'A validated family of finite subsets whose members cover the base.', example: 'CoverOf(NoeticCluster{^0, ^1, ^2, ^3}, NoeticCluster{^0, ^1}, NoeticCluster{^1, ^2, ^3})', learn: 'Every cover member must be a subset of the base, and the family must cover the base.' },
  { term: 'Partition', category: 'Set Theory', notation: 'PartitionOf(Base, U1...)', definition: 'A validated disjoint cover of a finite base set.', example: 'PartitionOf(NoeticCluster{^0, ^1, ^2, ^3}, NoeticCluster{^0, ^1}, NoeticCluster{^2, ^3})', learn: 'Partitions must cover and not overlap.' },
  { term: 'Diagram Node', category: 'Diagrams', notation: 'node', definition: 'A visual object emitted in the compiler diagram payload.', example: 'artifact.diagram().nodes', learn: 'Nodes represent individual states, symbols, or operators.' },
  { term: 'Diagram Edge', category: 'Diagrams', notation: 'edge', definition: 'A visual relation between diagram nodes or containers.', example: 'source → target', learn: 'Edges carry dependency, membership, subset, or recipe relations.' },
  { term: 'Containment Box', category: 'Diagrams', notation: 'container', definition: 'A diagram container used for sets, clusters, and nesting.', example: 'NoeticCluster{^2, ^7} ⊆ Noetics', learn: 'Containment boxes teach nesting in real time.' },
  { term: 'Grid Layout', category: 'Diagrams', notation: 'grid', definition: 'A diagram layout for finite products such as Noetics x Domains.', example: 'Product(Noetics, Domains)', learn: 'Grid layout is best for Cartesian combinations.' },
  { term: 'Petals Layout', category: 'Diagrams', notation: 'petals', definition: 'A diagram layout for cover and partition families.', example: 'CoverOf(...)', learn: 'Petals show multiple members arranged around a base.' },
  { term: 'Recipe Layout', category: 'Diagrams', notation: 'recipe', definition: 'A dependency diagram for production ingredients and targets.', example: 'Θ(Ω_focus) = ...', learn: 'Recipe diagrams show what feeds the outcome.' },
  { term: 'Rule 4', category: 'Principles', notation: 'operator admissibility', definition: 'The discipline that prevents invalid operator composition and requires named emergent results for certain integrations.', example: '(^3^P|A × ^3^P|f × ^3^P|T) = Ω_refusal', learn: 'If integration creates a new thing, name the Ω.' },
  { term: 'Object Language', category: 'Principles', notation: 'CAS expressions', definition: 'The core CAS expression layer for states, domains, operators, recipes, and dynamics.', example: '^5^P -> ^5^C', learn: 'Object-language expressions describe cognitive structure.' },
  { term: 'Meta-Logic', category: 'Principles', notation: 'typed finite set layer', definition: 'The compiler layer for set membership, subset, clusters, products, covers, and finite topos-safe constructs.', example: '^2 ∈ Noetics', learn: 'Meta-logic talks about CAS objects without replacing them.' },
  { term: 'Topos-Safe', category: 'Principles', notation: 'finite typed constructs', definition: 'A construct admitted because it preserves finite typing, containment, and compiler-checkable semantics.', example: 'Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})', learn: 'Topos-safe features add structure without breaking the framework.' },
];

const NOETIC_ENTRIES: DictionaryEntry[] = [
  { term: 'Idea', category: 'Noetic Operators', notation: '^0', definition: 'All things in and outside the Mind. The most basic Noetic primitive — anything that can be thought, perceived, or held in awareness.', example: '^0 ∈ Noetics', learn: '"It\'s all in your head." Self-dual; pair with a Domain to form a state.' },
  { term: 'Mind', category: 'Noetic Operators', notation: '^1', definition: 'Various degrees of awareness that processes, stores, outputs, and intakes Ideas.', example: '^1^C', learn: '"Paying attention." / "Making up your mind." Self-dual operator.' },
  { term: 'Positive', category: 'Noetic Operators', notation: '^2', definition: 'An Idea the Mind has an affinity for and is attracted toward.', example: '^2^P', learn: '"Drawn to it like a moth to a flame." Involution-paired with ^3 Negative.' },
  { term: 'Negative', category: 'Noetic Operators', notation: '^3', definition: 'An Idea the Mind is adverse to and repelled by. Visceral aversion, not analytical critique.', example: '^3^P', learn: '"Can\'t stomach it." If you mean audit/scrutinize, that is ^6 Male, not ^3.' },
  { term: 'Vibration', category: 'Noetic Operators', notation: '^4', definition: 'The degree to which an Idea resonates with the Mind, its impression.', example: '^4^E', learn: '"Struck a chord." / "Hit me hard." Self-dual operator.' },
  { term: 'Female', category: 'Noetic Operators', notation: '^5', definition: 'A Mind impregnated with an Idea — the Ideas a Mind is composed of. Encompasses self-image, beliefs, expertise, emotional patterns, trauma and healing — everything we accumulate as experience.', example: '^5^P', learn: '"We are the sum of our experiences." ^5 is a substrate against which other Noetics fire.' },
  { term: 'Male', category: 'Noetic Operators', notation: '^6', definition: 'An Idea impregnated with another Idea — the Ideas an Idea is composed of. Compositional decomposition and structural test.', example: '^6^C', learn: '"Unpacking an idea." / "Breaking it down." Involution-paired with ^5 Female.' },
  { term: 'Rhythm', category: 'Noetic Operators', notation: '^7', definition: 'The rate and pattern a Mind is exposed to an Idea, entraining and conditioning it.', example: '^7^O', learn: '"Practice makes perfect." / "Muscle memory." Self-dual operator.' },
  { term: 'Above/Cause', category: 'Noetic Operators', notation: '^8', definition: 'An Idea that triggers a different Idea than itself to come to Mind. Associative triggering, not deductive reasoning.', example: '^8^C', learn: '"That reminds me..." If you mean deductive analysis, that is ^6 + ^9, not ^8.' },
  { term: 'Below/Effect', category: 'Noetic Operators', notation: '^9', definition: 'The Idea brought to Mind by an Above/Cause trigger.', example: '^9^C', learn: '"It just popped into my head." Involution-paired with ^8 Above/Cause.' },
];

const DOMAIN_ENTRIES: DictionaryEntry[] = [
  { term: 'Principled', category: 'Domains', notation: '^P', definition: 'The highest processing tier in CAS. Felt-sense values, identity, vision — the level where principled commitments live.', example: '^2^P', learn: 'Domain precedence: P ≻ C ≻ E ≻ O. Higher domains anchor lower ones.' },
  { term: 'Cognitive', category: 'Domains', notation: '^C', definition: 'The thought-and-reasoning tier. Where Ideas are entertained, manipulated, and held in working awareness.', example: '^1^C', learn: 'Cognitive sits between Principled values above and Evaluative judgment below.' },
  { term: 'Evaluative', category: 'Domains', notation: '^E', definition: 'The judgment-and-appraisal tier. Where Ideas are weighed, compared, and assessed against criteria.', example: '^3^E', learn: 'Use Register (|A vs |f) to disambiguate analytical assessment from felt response.' },
  { term: 'Operational', category: 'Domains', notation: '^O', definition: 'The action-and-execution tier. The lowest tier in the precedence order; where intention becomes behavior.', example: '^7^O', learn: 'Operational feeds back to Principled (O → P) closing the loop.' },
];

const DRIVE_ENTRIES: DictionaryEntry[] = [
  { term: 'Unity', category: 'Drives', notation: 'F1', definition: 'The drive toward integration, wholeness, belonging — the sense that parts cohere into a larger whole. Inversion-paired with F7 Purpose.', example: 'F1 ∈ Drives', learn: 'F1 ↔ F7 inversion: integration vs directionality.' },
  { term: 'Wisdom', category: 'Drives', notation: 'F2', definition: 'The drive toward understanding, insight, discernment — knowing how things actually are. Inversion-paired with F6 Structure.', example: '^2^P_{F2}', learn: 'F2 ↔ F6 inversion: discerning truth vs imposing form.' },
  { term: 'Vitality', category: 'Drives', notation: 'F3', definition: 'The drive toward life, energy, generativity — being alive and productive. Inversion-paired with F5 Agency.', example: 'F3 ∈ Drives', learn: 'F3 ↔ F5 inversion: aliveness vs willed action.' },
  { term: 'Connection', category: 'Drives', notation: 'F4', definition: 'The drive toward relationship, attachment, communion. Self-dual: F4 inverts to itself.', example: 'F4 ∈ Drives', learn: 'F4 is the only self-dual Drive — connection has no structural opposite.' },
  { term: 'Agency', category: 'Drives', notation: 'F5', definition: 'The drive toward willed action, self-determination, capability. Inversion-paired with F3 Vitality.', example: 'RPM(F5)', learn: 'F5 ↔ F3 inversion: chosen action vs spontaneous aliveness.' },
  { term: 'Structure', category: 'Drives', notation: 'F6', definition: 'The drive toward order, form, predictability — making things hold together reliably. Inversion-paired with F2 Wisdom.', example: 'F6 ∈ Drives', learn: 'F6 ↔ F2 inversion: imposing order vs discerning truth.' },
  { term: 'Purpose', category: 'Drives', notation: 'F7', definition: 'The drive toward meaning, direction, telos — what it is all for. Inversion-paired with F1 Unity.', example: '^8^P_{F7}', learn: 'F7 ↔ F1 inversion: directional aim vs integrative wholeness.' },
];

const REGISTER_ENTRIES: DictionaryEntry[] = [
  { term: 'Transcendent', category: 'Registers', notation: '|T', definition: 'A high-abstraction, purpose-orienting operational character. Felt sense of meaning, vision, calling — integrative across particulars.', example: '^2^P|T', learn: 'Register specifies HOW a state operates, not WHAT it is.' },
  { term: 'Analytical', category: 'Registers', notation: '|A', definition: 'An explicit, sequential, logical, reason-based operational character. Conscious deliberation; chain-of-thought; symbolic reasoning.', example: '^3^P|A', learn: '|A is the register of explicit reasoning.' },
  { term: 'Affective', category: 'Registers', notation: '|f', definition: 'A value-laden, feeling-toned operational character. Emotional response, visceral reaction, RLHF-tuned preference expression.', example: '^3^P|f', learn: 'Lowercase |f. Distinct from |A: same Noetic, different operational character.' },
  { term: 'Embodied', category: 'Registers', notation: '|E', definition: 'A sensorimotor, concrete operational character — direct engagement with material substrate. Bodily knowing, gut response, real-time control loops.', example: '^7^O|E', learn: 'Uppercase |E (embodied register), distinct from ^E (Evaluative domain).' },
];

const DICTIONARY: DictionaryEntry[] = [
  ...BASE_DICTIONARY,
  ...NOETIC_ENTRIES,
  ...DOMAIN_ENTRIES,
  ...DRIVE_ENTRIES,
  ...REGISTER_ENTRIES,
];

const LEARNING_PATH: LearningStep[] = [
  { title: '1. Read The Axes', goal: 'Learn Noetic, Domain, Drive, and Register as the four main coordinates.', terms: 'Noetic, Domain, Drive, Register, State', practice: '^2^C_{F2}|T' },
  { title: '2. Compare Dynamics', goal: 'Distinguish co-presence, domain descent, contrast, and integration.', terms: 'Co-Presence, Domain Descent, Division / Contrast, Composition / Integration', practice: '^3^P|A + ^3^P|f + ^3^P|T' },
  { title: '3. Name Emergence', goal: 'Use Ω when multiple signals integrate into a named result.', terms: 'Rule 4, Production Target, Register', practice: '(^3^P|A × ^3^P|f × ^3^P|T) = Ω_refusal' },
  { title: '4. Read Recipes', goal: 'Understand Θ, coefficients, catalysts, and yield queries.', terms: 'Recipe, Coefficient, Catalyst, Theoretical Yield', practice: 'Θ(Ω_focus) = 0.6·^1^C + 0.4·^7^O → Ω_focus' },
  { title: '5. Use Typed Meta-Logic', goal: 'Separate CAS objects from finite sets that contain or relate them.', terms: 'Meta-Logic, Membership, Subset, Noetic Cluster, State Cluster', practice: 'NoeticCluster{^2, ^7} ⊆ Noetics' },
  { title: '6. Read Diagrams', goal: 'Use compiler diagrams to see nodes, edges, containment, products, and recipes.', terms: 'Diagram Node, Diagram Edge, Containment Box, Grid Layout, Recipe Layout', practice: 'Product(Noetics, Domains)' },
];

function dictionaryMatches(entry: DictionaryEntry, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return [entry.term, entry.category, entry.notation, entry.definition, entry.example, entry.learn]
    .some((value) => value.toLowerCase().includes(needle));
}

function isRunnableDictionaryExample(example: string): boolean {
  return !example.includes('...')
    && !example.includes('artifact.')
    && !example.includes('source → target')
    && !example.includes('Base, U1');
}

function formatDictionaryForCommand(query = ''): string {
  const entries = DICTIONARY.filter((entry) => dictionaryMatches(entry, query));
  if (entries.length === 0) return `No dictionary entries match "${query}".`;
  return entries.map((entry) => (
    `${entry.term} (${entry.notation})\n` +
    `  category: ${entry.category}\n` +
    `  meaning: ${entry.definition}\n` +
    `  example: ${entry.example}\n` +
    `  learn: ${entry.learn}`
  )).join('\n\n');
}

function formatLearningForCommand(): string {
  return LEARNING_PATH.map((step) => (
    `${step.title}\n` +
    `  goal: ${step.goal}\n` +
    `  terms: ${step.terms}\n` +
    `  try: ${step.practice}`
  )).join('\n\n');
}

// ── Types ──

interface CompileResult {
  source: string;
  valid: boolean;
  error?: string | null;
  engine?: string;
  warnings?: string[];
  tokens?: { kind: string; value: string; position: number }[];
  ast?: Record<string, unknown> | null;
  type?: { kind: string; domains: string[]; singular: boolean } | null;
  bytecode?: unknown[];
  result?: Record<string, unknown> | null;
  diagram?: CasDiagram | null;
}

export interface DiagramNode {
  id: string;
  kind: string;
  label: string;
  role?: string;
  step?: number;
  [key: string]: unknown;
}

export interface DiagramEdge {
  id: string;
  source: string;
  target: string;
  kind: string;
  label?: string;
  directed?: boolean;
}

export interface DiagramContainer {
  id: string;
  kind: string;
  label: string;
  contains: string[];
  cardinality?: number;
  element_type?: string;
}

export interface CasDiagram {
  kind: string;
  schema_version: string;
  layouts: string[];
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  containers: DiagramContainer[];
}

interface NlPipelineResult {
  text: string;
  signals: {
    operator_scores: number[];
    domain_scores: number[];
    drive_scores: number[];
    rpm_signal: number;
    word_count: number;
  };
  synthesized_notation: string;
  notation_english: string;
  compilation: {
    valid: boolean;
    error?: string | null;
    engine?: string;
    tokens: number;
    bytecode: number;
    warnings: string[];
    ast?: Record<string, unknown> | null;
    result?: Record<string, unknown> | null;
    diagram?: CasDiagram | null;
  } | null;
  interpretation: string;
}

interface HistoryEntry {
  input: string;
  result: CompileResult | null;
  nlResult?: NlPipelineResult | null;
  isCommand: boolean;
  commandOutput?: string;
  timestamp: number;
}

// ── Syntax highlighting ──

export function highlightSyntax(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let i = 0;
  const s = text;

  while (i < s.length) {
    // CO-N operator (legacy form)
    const coMatch = s.slice(i).match(/^CO-\d+/);
    if (coMatch) {
      parts.push(<span key={i} className="text-cyan-400">{coMatch[0]}</span>);
      i += coMatch[0].length;
      continue;
    }
    // ^N operator (caret form)
    if (s[i] === '^' && /[0-9]/.test(s[i + 1] ?? '')) {
      parts.push(<span key={i} className="text-cyan-400">^{s[i + 1]}</span>);
      i += 2;
      continue;
    }
    // ^Domain
    if (s[i] === '^' && 'PCEO'.includes(s[i + 1] ?? '')) {
      parts.push(<span key={i} className="text-emerald-400">^{s[i + 1]}</span>);
      i += 2;
      continue;
    }
    // _{Fn} drive subscript
    const driveMatch = s.slice(i).match(/^_\{F\d+\}/);
    if (driveMatch) {
      parts.push(<span key={i} className="text-amber-400">{driveMatch[0]}</span>);
      i += driveMatch[0].length;
      continue;
    }
    // Fn drive ref
    const fnMatch = s.slice(i).match(/^F[1-7]\b/);
    if (fnMatch && (i === 0 || !/[{a-zA-Z]/.test(s[i - 1] ?? ''))) {
      parts.push(<span key={i} className="text-amber-400">{fnMatch[0]}</span>);
      i += fnMatch[0].length;
      continue;
    }
    // |⟨R1,R2,...⟩ register-set (CAS v7.7)
    const regSetMatch = s.slice(i).match(/^\|⟨[^⟩]+⟩/);
    if (regSetMatch) {
      parts.push(<span key={i} className="text-fuchsia-400">{regSetMatch[0]}</span>);
      i += regSetMatch[0].length;
      continue;
    }
    // |R single register (CAS v7.5)
    if (s[i] === '|' && /[TAfE]/.test(s[i + 1] ?? '') && !/[{a-zA-Z]/.test(s[i + 2] ?? '')) {
      parts.push(<span key={i} className="text-fuchsia-400">|{s[i + 1]}</span>);
      i += 2;
      continue;
    }
    // Y_T( / Y_A( yield query (CAS v7.6)
    const yieldMatch = s.slice(i).match(/^Y_[TA]\b/);
    if (yieldMatch) {
      parts.push(<span key={i} className="text-purple-400">{yieldMatch[0]}</span>);
      i += yieldMatch[0].length;
      continue;
    }
    // Recipe / production tokens (CAS v7.6)
    if (s.slice(i, i + 5) === 'Theta' || s[i] === 'Θ') {
      const len = s[i] === 'Θ' ? 1 : 5;
      parts.push(<span key={i} className="text-pink-400">{s.slice(i, i + len)}</span>);
      i += len;
      continue;
    }
    // Ω_name production target (with optional _name suffix)
    if (s.slice(i, i + 5) === 'Omega' || s[i] === 'Ω') {
      const headLen = s[i] === 'Ω' ? 1 : 5;
      const tailMatch = s.slice(i + headLen).match(/^_(?:\{[^}]+\}|[A-Za-z][A-Za-z0-9_]*)/);
      const totalLen = headLen + (tailMatch ? tailMatch[0].length : 0);
      parts.push(<span key={i} className="text-orange-400">{s.slice(i, i + totalLen)}</span>);
      i += totalLen;
      continue;
    }
    // Λ leakage / κ catalyst / ι inhibitor (with optional _name)
    const recipeSym = s.slice(i).match(/^(Lambda|Λ|kappa|κ|iota|ι|eta|η)(_(?:\{[^}]+\}|[A-Za-z][A-Za-z0-9_]*))?/);
    if (recipeSym) {
      parts.push(<span key={i} className="text-orange-400">{recipeSym[0]}</span>);
      i += recipeSym[0].length;
      continue;
    }
    // RPM
    if (s.slice(i, i + 3) === 'RPM') {
      parts.push(<span key={i} className="text-purple-400">RPM</span>);
      i += 3;
      continue;
    }
    // ASCII aliases for set-theory operators — colored same as their Unicode
    // equivalents so users see the alias is recognized. Expanded on submit.
    const aliasMatch = s.slice(i).match(/^(notin|subseteq|subset|supseteq|supset|emptyset|in)\b/);
    if (aliasMatch && (i === 0 || !/[A-Za-z0-9_]/.test(s[i - 1] ?? ''))) {
      const word = aliasMatch[0];
      const cls = word === 'emptyset' ? 'text-violet-300' : 'text-teal-300 font-bold';
      parts.push(<span key={i} className={cls}>{word}</span>);
      i += word.length;
      continue;
    }
    // Meta-set names and typed cluster constructors (Set Theory layer).
    const metaSetMatch = s.slice(i).match(
      /^(?:Noetics|Domains|Worlds|Drives|Registers|States|SubFoundations|Foundations|Foundation_[1-7]|EmptySet|NoeticSet|NoeticCluster|Cluster|StateSet|StateCluster|StateVariantSet|StateVariantCluster|RelationSet|RelationCluster|DriveSet|DomainSet|RegisterSet|FoundationSet|SubFoundationSet|Tuple|Coordinate|Product|Pullback|CoverOf|PartitionOf|Union|Intersection|Difference)\b/
    );
    if (metaSetMatch && (i === 0 || !/[A-Za-z0-9_]/.test(s[i - 1] ?? ''))) {
      parts.push(<span key={i} className="text-violet-300">{metaSetMatch[0]}</span>);
      i += metaSetMatch[0].length;
      continue;
    }
    // Set-theory operators (membership, subset, union/intersection/difference)
    if ('∈∉⊂⊆⊃⊇∪∩∖'.includes(s[i])) {
      parts.push(<span key={i} className="text-teal-300 font-bold">{s[i]}</span>);
      i += 1;
      continue;
    }
    // ∅ empty-set literal
    if (s[i] === '∅') {
      parts.push(<span key={i} className="text-violet-300">{s[i]}</span>);
      i += 1;
      continue;
    }
    // Phi / Φ
    if (s.slice(i, i + 3) === 'Phi' || s[i] === 'Φ') {
      const len = s[i] === 'Φ' ? 1 : 3;
      parts.push(<span key={i} className="text-pink-400">{s.slice(i, i + len)}</span>);
      i += len;
      continue;
    }
    // Multiplicative ops × ÷ ∘ (and ASCII aliases * /) — matches Operations key color
    if ('*×/÷∘'.includes(s[i])) {
      parts.push(<span key={i} className="text-orange-400">{s[i]}</span>);
      i += 1;
      continue;
    }
    // Recipe coefficient · — matches Operations key color
    if (s[i] === '·') {
      parts.push(<span key={i} className="text-slate-300">{s[i]}</span>);
      i += 1;
      continue;
    }
    if (s.slice(i, i + 2) === '->') {
      parts.push(<span key={i} className="text-white">→</span>);
      i += 2;
      continue;
    }
    if (s[i] === '→' || s[i] === '←' || s[i] === '↔') {
      parts.push(<span key={i} className="text-white">{s[i]}</span>);
      i += 1;
      continue;
    }
    // Bare pipe — cardinality wrapper |Set| OR recipe-condition separator (key: slate-300)
    if (s[i] === '|') {
      parts.push(<span key={i} className="text-slate-300">{s[i]}</span>);
      i += 1;
      continue;
    }
    // = (recipe definition / emergent assignment)
    if (s[i] === '=') {
      parts.push(<span key={i} className="text-slate-300">{s[i]}</span>);
      i += 1;
      continue;
    }
    if (s[i] === '+' || s[i] === '-') {
      parts.push(<span key={i} className="text-slate-300">{s[i]}</span>);
      i += 1;
      continue;
    }
    // Parens / angle brackets
    if ('(){}⟨⟩<>'.includes(s[i])) {
      parts.push(<span key={i} className="text-slate-500">{s[i]}</span>);
      i += 1;
      continue;
    }
    // Default
    parts.push(<span key={i} className="text-slate-300">{s[i]}</span>);
    i += 1;
  }
  return parts;
}

// ── Result rendering ──

function describeResult(r: CompileResult): string {
  if (!r.result) return '';
  const res = r.result as Record<string, unknown>;
  const kind = res.kind as string | undefined;

  if (kind === 'state') {
    const dom = (res.dominant_domain as string) || '?';
    const op = (res.dominant_operator as string) || '?';
    const opIdx = parseInt(op.replace('CO-', ''));
    const opName = OPERATOR_NAMES[opIdx] ?? op;
    const domName = DOMAIN_NAMES[dom] ?? dom;
    return `${opName} in the ${domName} Domain`;
  }
  if (kind === 'fractal') {
    const seq = (res.sequence as number[]) || [];
    const composed = res.composed_operator as string || '?';
    return `Fractal sequence [${seq.join(':')}] → composed ${composed}`;
  }
  if (kind === 'rpm') {
    const drive = res.drive as string || '?';
    const completeness = res.completeness as number ?? 0;
    return `${drive} prerequisite chain (completeness: ${(completeness * 100).toFixed(0)}%)`;
  }
  if (kind === 'program') {
    const final = res.final_result as Record<string, unknown> | null;
    if (final?.kind === 'state') {
      const dom = (final.dominant_domain as string) || '?';
      const op = (final.dominant_operator as string) || '?';
      const opIdx = parseInt(op.replace('CO-', ''));
      return `Program → ${OPERATOR_NAMES[opIdx] ?? op} in ${DOMAIN_NAMES[dom] ?? dom} Domain`;
    }
    return 'Multi-statement program';
  }
  return JSON.stringify(res).slice(0, 120);
}

function diagramColor(kind: string, node?: { noetic?: number | null; domain?: string | null; drive?: number | null }): string {
  // When a node carries specific axis values, delegate to the value-keyed palette
  // (Noetic > Domain > Drive precedence). Falls back to kind-keyed colors below.
  if (node) {
    try {
      const axisColor = axisColorForNode(node);
      if (axisColor !== null) return axisColor;
    } catch {
      // out-of-range axis value — fall through to kind-keyed fallback
    }
  }
  if (kind.includes('cluster') || kind === 'meta_set') return '#14b8a6';
  if (kind === 'state') return '#38bdf8';
  if (kind === 'noetic') return '#22d3ee';
  if (kind === 'drive') return '#f59e0b';
  if (kind === 'domain') return '#34d399';
  if (kind === 'register') return '#f472b6';
  if (kind === 'foundation' || kind === 'subfoundation') return '#fbbf24';
  if (kind === 'call' || kind === 'operator') return '#c084fc';
  if (kind === 'production_target' || kind === 'emergent') return '#a78bfa';
  return '#94a3b8';
}

// Layout strategies. Each returns a LayoutResult with node positions and an
// optional regions map (container id → {cx, cy, rx, ry}) for Venn-style
// containment rendering.
type Pos = { x: number; y: number };
type Region = { cx: number; cy: number; rx: number; ry: number };
type GridSpec = {
  x0: number;
  y0: number;
  cellW: number;
  cellH: number;
  rows: string[];
  cols: string[];
  title: string;
};
type PetalSector = {
  id: string;
  start: number;
  end: number;
  label: string;
  color: string;
};
type PetalSpec = {
  cx: number;
  cy: number;
  innerR: number;
  outerR: number;
  sectors: PetalSector[];
  title: string;
};
type FractalBranch = { x1: number; y1: number; x2: number; y2: number; opacity: number };
type LayoutResult = {
  positions: Map<string, Pos>;
  regions?: Map<string, Region>;
  grid?: GridSpec;
  petals?: PetalSpec;
  fractalBranches?: FractalBranch[];
  // Containers that should be drawn as a single small circle (atom-style)
  // inside their target's region — used for ∈ membership where the LHS is a
  // set being asserted as one element of another set.
  pointMembers?: Set<string>;
};

function radialLayout(items: DiagramNode[], w: number, h: number): LayoutResult {
  // Containers (small labels) sit along the top row; atomic nodes ring around
  // a centre pushed enough below the row that the topmost atom clears the
  // container labels. An angular offset rotates the ring by a half-step so no
  // atom lands directly beneath a container anchor.
  const out = new Map<string, Pos>();
  const containers = items.filter(it => it.id.startsWith('container:'));
  const atoms = items.filter(it => !it.id.startsWith('container:'));

  const containerRowY = 32;
  const containerRowH = 38; // matches the rect height in the renderer
  const atomR = 20;
  // Centre the ring far enough below the container row that even the top atom
  // clears it: top of ring = cy - r must exceed (containerRowY + containerRowH/2 + atomR + padding)
  const r = Math.min(w, h) * 0.34;
  const cy = Math.max(h / 2 + 22, containerRowY + containerRowH / 2 + atomR + 14 + r);

  const cx = w / 2;
  // Half-step angular offset so atoms straddle the vertical, not sit on it
  const angleOffset = atoms.length > 0 ? Math.PI / atoms.length : 0;
  atoms.forEach((item, i) => {
    const angle = (Math.PI * 2 * i) / Math.max(atoms.length, 1) - Math.PI / 2 + angleOffset;
    out.set(item.id, { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r });
  });

  if (containers.length === 1) {
    out.set(containers[0].id, { x: cx, y: containerRowY });
  } else if (containers.length > 1) {
    // Pack containers in the top row using their actual rendered widths so
    // wide labels (e.g. "NoeticCluster{CO-2, CO-7}") get enough horizontal
    // breathing room and don't visually collide with each other.
    const widths = containers.map(c => rectWidthFor(c.label));
    const totalContent = widths.reduce((s, x) => s + x, 0);
    const gap = Math.max(20, (w - 80 - totalContent) / Math.max(containers.length - 1, 1));
    let x = 40 + widths[0] / 2;
    containers.forEach((c, i) => {
      out.set(c.id, { x, y: containerRowY });
      if (i < containers.length - 1) {
        x += widths[i] / 2 + gap + widths[i + 1] / 2;
      }
    });
  }
  return { positions: out };
}

function dependencyLayout(items: DiagramNode[], edges: DiagramEdge[], w: number, h: number): LayoutResult {
  // BFS layering: rank = longest incoming-edge path. Sources on the left.
  const ids = new Set(items.map(i => i.id));
  const inEdges = new Map<string, string[]>();
  const outEdges = new Map<string, string[]>();
  items.forEach(it => { inEdges.set(it.id, []); outEdges.set(it.id, []); });
  edges.forEach(e => {
    if (ids.has(e.source) && ids.has(e.target)) {
      inEdges.get(e.target)!.push(e.source);
      outEdges.get(e.source)!.push(e.target);
    }
  });
  const rank = new Map<string, number>();
  const queue: string[] = [];
  items.forEach(it => {
    if (inEdges.get(it.id)!.length === 0) {
      rank.set(it.id, 0);
      queue.push(it.id);
    }
  });
  while (queue.length) {
    const id = queue.shift()!;
    const r0 = rank.get(id)!;
    for (const tgt of outEdges.get(id) || []) {
      const cur = rank.get(tgt);
      if (cur === undefined || cur < r0 + 1) {
        rank.set(tgt, r0 + 1);
        queue.push(tgt);
      }
    }
  }
  items.forEach(it => { if (!rank.has(it.id)) rank.set(it.id, 0); });
  const byRank = new Map<number, string[]>();
  rank.forEach((r, id) => {
    if (!byRank.has(r)) byRank.set(r, []);
    byRank.get(r)!.push(id);
  });
  const ranks = [...byRank.keys()].sort((a, b) => a - b);
  const out = new Map<string, Pos>();
  const padX = 70;
  const padY = 36;
  const stepX = ranks.length > 1 ? (w - padX * 2) / (ranks.length - 1) : 0;
  ranks.forEach((r, i) => {
    const lane = byRank.get(r)!;
    const stepY = (h - padY * 2) / Math.max(lane.length, 1);
    lane.forEach((id, j) => {
      out.set(id, {
        x: ranks.length > 1 ? padX + i * stepX : w / 2,
        y: padY + (j + 0.5) * stepY,
      });
    });
  });
  return { positions: out };
}

function gridLayout(items: DiagramNode[], containers: DiagramContainer[], w: number, h: number): LayoutResult {
  const out = new Map<string, Pos>();
  const noetics = items
    .filter(it => it.kind === 'noetic')
    .sort((a, b) => parseInt(a.label.replace(/\D/g, '') || '0') - parseInt(b.label.replace(/\D/g, '') || '0'));
  const domains = items
    .filter(it => it.kind === 'domain')
    .sort((a, b) => ['P', 'C', 'E', 'O'].indexOf(a.label) - ['P', 'C', 'E', 'O'].indexOf(b.label));

  const rows = noetics.length ? noetics : items.filter(it => it.role === 'atomic_noetic');
  const cols = domains.length ? domains : items.filter(it => it.role === 'processing_domain');
  const x0 = 150;
  const y0 = 72;
  const gridW = w - x0 - 42;
  const gridH = h - y0 - 38;
  const cellW = gridW / Math.max(cols.length, 1);
  const cellH = gridH / Math.max(rows.length, 1);

  rows.forEach((row, i) => {
    out.set(row.id, { x: x0 - 42, y: y0 + cellH * (i + 0.5) });
  });
  cols.forEach((col, i) => {
    out.set(col.id, { x: x0 + cellW * (i + 0.5), y: y0 - 26 });
  });

  containers.forEach(container => {
    if (container.element_type === 'noetic') {
      out.set(container.id, { x: x0 - 42, y: 30 });
    } else if (container.element_type === 'domain') {
      out.set(container.id, { x: x0 + gridW / 2, y: 30 });
    }
  });

  const call = items.find(it => it.kind === 'call' && it.label === 'Product');
  if (call) out.set(call.id, { x: x0 + gridW - 42, y: h - 24 });

  return {
    positions: out,
    grid: {
      x0,
      y0,
      cellW,
      cellH,
      rows: rows.map(row => row.label),
      cols: cols.map(col => col.label),
      title: `${rows.length || '?'} × ${cols.length || '?'} finite product coordinates`,
    },
  };
}

function wedgePath(cx: number, cy: number, innerR: number, outerR: number, start: number, end: number): string {
  const largeArc = end - start > Math.PI ? 1 : 0;
  const p0 = { x: cx + Math.cos(start) * outerR, y: cy + Math.sin(start) * outerR };
  const p1 = { x: cx + Math.cos(end) * outerR, y: cy + Math.sin(end) * outerR };
  const p2 = { x: cx + Math.cos(end) * innerR, y: cy + Math.sin(end) * innerR };
  const p3 = { x: cx + Math.cos(start) * innerR, y: cy + Math.sin(start) * innerR };
  return [
    `M ${p0.x} ${p0.y}`,
    `A ${outerR} ${outerR} 0 ${largeArc} 1 ${p1.x} ${p1.y}`,
    `L ${p2.x} ${p2.y}`,
    `A ${innerR} ${innerR} 0 ${largeArc} 0 ${p3.x} ${p3.y}`,
    'Z',
  ].join(' ');
}

function petalLayout(items: DiagramNode[], containers: DiagramContainer[], edges: DiagramEdge[], w: number, h: number): LayoutResult {
  const out = new Map<string, Pos>();
  const cx = w / 2;
  const cy = h / 2 + 10;
  const outerR = Math.min(w, h) * 0.38;
  const innerR = 46;
  const call = items.find(it => it.kind === 'call' && (it.label === 'CoverOf' || it.label === 'PartitionOf'));
  const baseEdge = edges.find(edge => edge.kind === 'cover_base' || edge.kind === 'partition_base');
  const baseId = baseEdge?.source;
  const memberIds = edges
    .filter(edge => edge.kind === 'cover_member' || edge.kind === 'partition_member')
    .map(edge => edge.source);
  const memberContainers = memberIds
    .map(id => containers.find(container => container.id === id))
    .filter((container): container is DiagramContainer => !!container);
  const fallbackMembers = containers.filter(container => container.id !== baseId);
  const sectorsSource = memberContainers.length ? memberContainers : fallbackMembers;
  const sectors: PetalSector[] = [];

  if (baseId) out.set(baseId, { x: cx, y: cy });
  if (call) out.set(call.id, { x: cx, y: cy });

  sectorsSource.forEach((container, i) => {
    const start = -Math.PI / 2 + (Math.PI * 2 * i) / Math.max(sectorsSource.length, 1);
    const end = -Math.PI / 2 + (Math.PI * 2 * (i + 1)) / Math.max(sectorsSource.length, 1);
    const mid = (start + end) / 2;
    const color = diagramColor(container.kind);
    sectors.push({ id: container.id, start, end, label: container.label, color });
    out.set(container.id, {
      x: cx + Math.cos(mid) * (outerR + 24),
      y: cy + Math.sin(mid) * (outerR + 24),
    });
    container.contains.forEach((childId, j) => {
      const spread = (j - (container.contains.length - 1) / 2) * ((end - start) * 0.16);
      const radius = innerR + (outerR - innerR) * (0.48 + 0.12 * (j % 2));
      out.set(childId, {
        x: cx + Math.cos(mid + spread) * radius,
        y: cy + Math.sin(mid + spread) * radius,
      });
    });
  });

  items.filter(item => !out.has(item.id)).forEach((item, i) => {
    out.set(item.id, { x: 52 + i * 42, y: h - 26 });
  });

  return {
    positions: out,
    petals: {
      cx,
      cy,
      innerR,
      outerR,
      sectors,
      title: call?.label === 'PartitionOf' ? 'disjoint finite partition' : 'finite cover family',
    },
  };
}

function fractalLayout(items: DiagramNode[], edges: DiagramEdge[], w: number, h: number): LayoutResult {
  const out = new Map<string, Pos>();
  const stepNodes = items
    .filter(item => item.role === 'fractal_step' || edges.some(edge => edge.kind === 'fractal_step' && (edge.source === item.id || edge.target === item.id)))
    .sort((a, b) => Number(a.step ?? 0) - Number(b.step ?? 0));
  const ordered = stepNodes.length ? stepNodes : items;
  const branches: FractalBranch[] = [];
  const startY = 48;
  const stepY = Math.min(72, (h - 96) / Math.max(ordered.length - 1, 1));
  ordered.forEach((item, i) => {
    const amplitude = Math.max(28, 120 / (i + 1));
    const x = i === 0 ? w / 2 : w / 2 + (i % 2 === 0 ? 1 : -1) * amplitude;
    const y = startY + i * stepY;
    out.set(item.id, { x, y });
    if (i < ordered.length - 1) {
      branches.push(
        { x1: x, y1: y + 18, x2: x - amplitude * 0.48, y2: y + stepY * 0.58, opacity: 0.18 },
        { x1: x, y1: y + 18, x2: x + amplitude * 0.48, y2: y + stepY * 0.58, opacity: 0.18 },
      );
    }
  });
  items.filter(item => !out.has(item.id)).forEach((item, i) => {
    out.set(item.id, { x: 46 + i * 46, y: h - 28 });
  });
  return { positions: out, fractalBranches: branches };
}

function containmentLayout(items: DiagramNode[], containers: DiagramContainer[], edges: DiagramEdge[], w: number, h: number): LayoutResult {
  // Build a containment graph using both explicit `contains` AND subset/⊆ edges
  // between containers. The compiler exports e.g. `NoeticCluster{^2,^7} ⊆
  // Noetics` as a subset *edge* between two ROOT containers (neither lists the
  // other in its `contains`), so the only way to recover the visual nesting is
  // to read those edges.
  const containedIn = new Map<string, string>();
  containers.forEach(c => c.contains.forEach(member => containedIn.set(member, c.id)));

  const containerIds = new Set(containers.map(c => c.id));
  // Track which container is rendered as a single point INSIDE another (for ∈
  // membership assertions where the LHS is a set being treated as one element).
  const memberOf = new Map<string, string>();
  // Read edge.label (which is reliable across operators) — edge.kind is buggy
  // upstream (the compiler emits kind="subset" for ⊇ too, so we can't trust it).
  edges.forEach(e => {
    if (!containerIds.has(e.source) || !containerIds.has(e.target)) return;
    const lbl = (e.label || '').trim();
    if (lbl === '⊆' || lbl === '⊂') {
      // source ⊆/⊂ target: source nests inside target
      if (!containedIn.has(e.source)) containedIn.set(e.source, e.target);
    } else if (lbl === '⊇' || lbl === '⊃') {
      // source ⊇/⊃ target: REVERSED — target nests inside source
      if (!containedIn.has(e.target)) containedIn.set(e.target, e.source);
    } else if (lbl === '∈') {
      // source ∈ target: source rendered as a single point inside target's region
      memberOf.set(e.source, e.target);
    }
  });

  const roots = containers.filter(c => !containedIn.has(c.id));
  if (roots.length === 0) return radialLayout(items, w, h);

  const out = new Map<string, Pos>();
  const regions = new Map<string, Region>();
  const cx = w / 2;
  const cy = h / 2 + 14; // ring centre — slightly below visual centre

  // Pick the largest root as the outer (Venn-style "universe") region.
  const sortedRoots = [...roots].sort(
    (a, b) =>
      (containers.find(c => c.id === b.id)?.contains.length ?? 0) -
      (containers.find(c => c.id === a.id)?.contains.length ?? 0),
  );
  const outer = sortedRoots[0];
  const outerContainer = containers.find(c => c.id === outer.id)!;

  const childContainersByParent = new Map<string, string[]>();
  containedIn.forEach((parentId, childId) => {
    if (!containerIds.has(childId)) return;
    const children = childContainersByParent.get(parentId) ?? [];
    children.push(childId);
    childContainersByParent.set(parentId, children);
  });
  const atomsForContainer = (containerId: string, seen = new Set<string>()): Set<string> => {
    if (seen.has(containerId)) return new Set();
    seen.add(containerId);
    const container = containers.find(c => c.id === containerId);
    const atomIds = new Set<string>();
    (container?.contains ?? []).forEach(childId => {
      if (containerIds.has(childId)) {
        atomsForContainer(childId, seen).forEach(id => atomIds.add(id));
      } else {
        atomIds.add(childId);
      }
    });
    (childContainersByParent.get(containerId) ?? []).forEach(childId => {
      atomsForContainer(childId, seen).forEach(id => atomIds.add(id));
    });
    return atomIds;
  };

  // Atoms in the outer container and in any nested containers go on the main
  // ring. This prevents reversed superset diagrams from dumping the target
  // universe's atoms as orphans.
  const outerAtomIds = atomsForContainer(outerContainer.id);
  const directAtoms = items.filter(
    it => !it.id.startsWith('container:') && outerAtomIds.has(it.id),
  );
  const r = Math.min(w, h) * 0.32;
  directAtoms.forEach((m, i) => {
    const angle = (Math.PI * 2 * i) / Math.max(directAtoms.length, 1) - Math.PI / 2;
    out.set(m.id, { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r });
  });

  // Outer container is rendered as a big translucent ellipse enclosing the
  // ring. Position it at the ring centre; size enough to wrap around all
  // direct atoms with padding.
  out.set(outer.id, { x: cx, y: cy });
  regions.set(outer.id, {
    cx,
    cy,
    rx: r + 36,
    ry: r + 36,
  });

  // Inner / nested containers: render as smaller translucent ellipses sized
  // to enclose only their own members (subset of the ring).
  const innerContainers = containers.filter(c => c.id !== outer.id);
  innerContainers.forEach(c => {
    const memberPositions = c.contains
      .map(mid => out.get(mid))
      .filter((p): p is Pos => !!p);
    if (memberPositions.length === 0) {
      // No anchored members; place this inner container as a small ellipse off
      // to the side so it doesn't crash into anything else.
      out.set(c.id, { x: cx, y: cy });
      regions.set(c.id, { cx, cy, rx: 60, ry: 30 });
      return;
    }
    const xs = memberPositions.map(p => p.x);
    const ys = memberPositions.map(p => p.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const innerCx = (minX + maxX) / 2;
    const innerCy = (minY + maxY) / 2;
    // Pad enough to enclose the atom circles (radius 20) plus breathing room.
    const padding = 30;
    const rx = Math.max((maxX - minX) / 2 + padding, 70);
    const ry = Math.max((maxY - minY) / 2 + padding, 40);
    out.set(c.id, { x: innerCx, y: innerCy - ry - 6 }); // label perches above the ellipse
    regions.set(c.id, { cx: innerCx, cy: innerCy, rx, ry });
  });

  // Containers asserted as single-point ∈ members: position them inside their
  // target's region as small atom-style circles (rendered as such by the
  // renderer based on the pointMembers set).
  memberOf.forEach((targetId, sourceId) => {
    const targetRegion = regions.get(targetId) ?? regions.get(outer.id)!;
    if (!targetRegion) return;
    // Park the point member just inside the target's right edge so it doesn't
    // overlap whatever is already on the ring.
    out.set(sourceId, {
      x: targetRegion.cx + targetRegion.rx * 0.55,
      y: targetRegion.cy - targetRegion.ry * 0.45,
    });
  });

  // Any remaining unpositioned orphan items: drop them into the lower-right
  // corner area as a fallback.
  const orphans = items.filter(it => !out.has(it.id));
  orphans.forEach((m, i) => {
    out.set(m.id, { x: w - 60 - (i * 50), y: h - 30 });
  });
  return { positions: out, regions, pointMembers: new Set(memberOf.keys()) };
}

// Categorical / commutative-diagram style: containers are nodes in a directed
// graph laid out on a grid, with morphism edges flowing along grid axes. Unlike
// containmentLayout, nothing nests visually — the morphism structure (subset,
// intersection, union, etc.) is read from the directed arrows between nodes.
// Atoms (non-container items) are placed in a fallback row beneath the grid so
// they don't disrupt the categorical reading.
function toposLayout(items: DiagramNode[], containers: DiagramContainer[], edges: DiagramEdge[], w: number, h: number): LayoutResult {
  const out = new Map<string, Pos>();
  const containerIds = new Set(containers.map(c => c.id));
  if (containers.length === 0) return dependencyLayout(items, edges, w, h);

  // Build container-to-container adjacency from edges so we can rank by depth
  // (sources on top row, sinks on bottom). Edges between container and atom
  // are ignored for ranking — they're rendered but don't shape the grid.
  const inEdges = new Map<string, Set<string>>();
  const outEdgesC = new Map<string, Set<string>>();
  containers.forEach(c => { inEdges.set(c.id, new Set()); outEdgesC.set(c.id, new Set()); });
  edges.forEach(e => {
    if (!containerIds.has(e.source) || !containerIds.has(e.target)) return;
    if (e.source === e.target) return;
    outEdgesC.get(e.source)!.add(e.target);
    inEdges.get(e.target)!.add(e.source);
  });

  // BFS rank: longest incoming path. Pure sources land on row 0.
  const rank = new Map<string, number>();
  const queue: string[] = [];
  containers.forEach(c => {
    if (inEdges.get(c.id)!.size === 0) {
      rank.set(c.id, 0);
      queue.push(c.id);
    }
  });
  while (queue.length) {
    const id = queue.shift()!;
    const r0 = rank.get(id)!;
    for (const tgt of outEdgesC.get(id) ?? []) {
      const cur = rank.get(tgt);
      if (cur === undefined || cur < r0 + 1) {
        rank.set(tgt, r0 + 1);
        queue.push(tgt);
      }
    }
  }
  containers.forEach(c => { if (!rank.has(c.id)) rank.set(c.id, 0); });

  // Bucket containers per rank, then lay out as a grid: ranks become rows,
  // position within rank becomes column. We cap rows so very tall diagrams
  // don't push atoms off the canvas.
  const byRank = new Map<number, DiagramContainer[]>();
  containers.forEach(c => {
    const r = rank.get(c.id) ?? 0;
    if (!byRank.has(r)) byRank.set(r, []);
    byRank.get(r)!.push(c);
  });
  const ranks = [...byRank.keys()].sort((a, b) => a - b);
  const rowCount = Math.max(ranks.length, 1);
  const padX = 80;
  const padY = 56;
  const usableH = h - padY * 2 - 40; // reserve bottom strip for atoms
  const rowStep = rowCount > 1 ? usableH / (rowCount - 1) : 0;

  ranks.forEach((r, rowIdx) => {
    const row = byRank.get(r)!;
    const colCount = row.length;
    const colStep = colCount > 1 ? (w - padX * 2) / (colCount - 1) : 0;
    const y = padY + rowIdx * rowStep;
    row.forEach((c, colIdx) => {
      const x = colCount > 1 ? padX + colIdx * colStep : w / 2;
      out.set(c.id, { x, y });
    });
  });

  // Atoms: drop into a single bottom strip so the categorical grid stays clean.
  const atoms = items.filter(it => !it.id.startsWith('container:'));
  if (atoms.length > 0) {
    const stripY = h - 30;
    const stripStep = (w - padX * 2) / Math.max(atoms.length, 1);
    atoms.forEach((a, i) => {
      out.set(a.id, { x: padX + (i + 0.5) * stripStep, y: stripY });
    });
  }

  // Anything still unpositioned (rare): tuck into the corner.
  items.filter(it => !out.has(it.id)).forEach((it, i) => {
    out.set(it.id, { x: w - 60 - i * 50, y: h - 30 });
  });
  return { positions: out };
}

// Cluster nodes by ontological kind (Noetic / Domain / Drive / Register /
// State / Container / other). Each kind gets its own vertical lane, with
// items sorted within the lane. Distinct from radial because there is no
// single ring — buckets sit side-by-side and items of the same kind cluster
// together visually, exposing the kind-composition of the expression.
function semanticLayout(items: DiagramNode[], containers: DiagramContainer[], edges: DiagramEdge[], w: number, h: number): LayoutResult {
  const out = new Map<string, Pos>();

  // Bucket-key extraction. Containers are bucketed by their declared
  // element_type when available so that e.g. NoeticCluster sits in the
  // noetic lane next to its members; otherwise they fall into a "set" lane.
  const bucketOf = (it: DiagramNode): string => {
    if (it.id.startsWith('container:')) {
      const c = containers.find(cc => cc.id === it.id);
      return c?.element_type ? `set:${c.element_type}` : 'set';
    }
    return it.kind || 'other';
  };

  // Preferred lane order — matches CAS axis precedence so a v7.5 register
  // expression reads left-to-right as Noetic → Domain → Drive → Register.
  const laneOrder = [
    'set:noetic', 'set:domain', 'set:drive', 'set:register', 'set:state',
    'set',
    'noetic', 'domain', 'drive', 'register', 'state',
    'foundation', 'subfoundation', 'meta_set',
    'call', 'operator',
    'production_target', 'emergent',
    'other',
  ];

  const buckets = new Map<string, DiagramNode[]>();
  items.forEach(it => {
    const key = bucketOf(it);
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key)!.push(it);
  });

  // Stable lane sequence: known lanes first in canonical order, then any
  // unrecognised lane keys appended in insertion order so we never silently
  // drop content.
  const presentLanes = [
    ...laneOrder.filter(k => buckets.has(k)),
    ...[...buckets.keys()].filter(k => !laneOrder.includes(k)),
  ];

  // Sort each bucket. For atoms, sort by label (e.g. ^0..^9 by leading digit
  // when present). Containers keep arrival order so the user-typed ordering is
  // preserved.
  const numericLead = (s: string): number => {
    const m = s.match(/\d+/);
    return m ? parseInt(m[0], 10) : Number.MAX_SAFE_INTEGER;
  };
  presentLanes.forEach(key => {
    const arr = buckets.get(key)!;
    if (!key.startsWith('set')) {
      arr.sort((a, b) => numericLead(a.label) - numericLead(b.label) || a.label.localeCompare(b.label));
    }
  });

  const padX = 60;
  const padY = 56;
  const headerY = 28;
  const laneCount = Math.max(presentLanes.length, 1);
  const laneW = (w - padX * 2) / laneCount;
  const usableH = h - padY - 30;

  presentLanes.forEach((key, laneIdx) => {
    const arr = buckets.get(key)!;
    const cx = padX + laneW * (laneIdx + 0.5);
    const itemStep = usableH / Math.max(arr.length, 1);
    arr.forEach((it, i) => {
      out.set(it.id, { x: cx, y: padY + (i + 0.5) * itemStep });
    });
  });

  // Mark unused: edges and lane labels are passed through to caller via the
  // standard render path; this layout keeps the LayoutResult shape minimal so
  // edges still draw between buckets, exposing cross-kind relationships.
  void edges;
  void headerY;

  items.filter(it => !out.has(it.id)).forEach((it, i) => {
    out.set(it.id, { x: w - 60 - i * 50, y: h - 30 });
  });
  return { positions: out };
}

// Top-down hierarchical tree. Root is the first edge source (or, failing
// edges, the largest container by `contains` count). Children fan downward.
// Distinct from radial because it's tree-structured, not circular.
function branchLayout(items: DiagramNode[], containers: DiagramContainer[], edges: DiagramEdge[], w: number, h: number): LayoutResult {
  const out = new Map<string, Pos>();
  const ids = new Set(items.map(it => it.id));

  // Build child adjacency from BOTH container.contains AND directed edges,
  // so cross-register fusion `(A × B × C) = Ω` (where Ω is an emergent node
  // with edges from each register state) renders as a fan-in/fan-out tree.
  const children = new Map<string, string[]>();
  const parents = new Map<string, Set<string>>();
  const addEdge = (src: string, tgt: string) => {
    if (!ids.has(src) || !ids.has(tgt) || src === tgt) return;
    if (!children.has(src)) children.set(src, []);
    if (!children.get(src)!.includes(tgt)) children.get(src)!.push(tgt);
    if (!parents.has(tgt)) parents.set(tgt, new Set());
    parents.get(tgt)!.add(src);
  };
  containers.forEach(c => {
    c.contains.forEach(childId => addEdge(c.id, childId));
  });
  edges.forEach(e => addEdge(e.source, e.target));

  // Root selection: prefer a node with outgoing edges and no incoming edges.
  // If none, fall back to the largest container, then to the first item.
  const rootCandidates = items.filter(it => (children.get(it.id)?.length ?? 0) > 0 && !(parents.get(it.id)?.size));
  let rootId: string | undefined = rootCandidates[0]?.id;
  if (!rootId) {
    const biggestContainer = [...containers].sort((a, b) => b.contains.length - a.contains.length)[0];
    rootId = biggestContainer?.id ?? items[0]?.id;
  }
  if (!rootId) return radialLayout(items, w, h);

  // BFS depth assignment. Items unreachable from root get parked at the
  // deepest layer + 1 so they don't visually overlap the tree.
  const depth = new Map<string, number>();
  depth.set(rootId, 0);
  const queue: string[] = [rootId];
  const visited = new Set<string>([rootId]);
  while (queue.length) {
    const id = queue.shift()!;
    const d = depth.get(id)!;
    for (const ch of children.get(id) ?? []) {
      if (!visited.has(ch)) {
        visited.add(ch);
        depth.set(ch, d + 1);
        queue.push(ch);
      } else {
        // Re-visit only if a longer path exists (keeps nodes BELOW their
        // deepest parent so fan-in arrows point downward).
        const cur = depth.get(ch) ?? 0;
        if (d + 1 > cur) depth.set(ch, d + 1);
      }
    }
  }
  const maxDepth = Math.max(0, ...depth.values());
  items.forEach(it => {
    if (!depth.has(it.id)) depth.set(it.id, maxDepth + 1);
  });

  // Bucket by depth, lay out top-down. Within a layer, position by insertion
  // order (which approximates left-to-right pre-order for typical diagrams).
  const byDepth = new Map<number, string[]>();
  items.forEach(it => {
    const d = depth.get(it.id) ?? 0;
    if (!byDepth.has(d)) byDepth.set(d, []);
    byDepth.get(d)!.push(it.id);
  });
  const depthsSorted = [...byDepth.keys()].sort((a, b) => a - b);
  const padX = 60;
  const padY = 50;
  const layerCount = Math.max(depthsSorted.length, 1);
  const layerStep = layerCount > 1 ? (h - padY * 2) / (layerCount - 1) : 0;

  depthsSorted.forEach((d, layerIdx) => {
    const layer = byDepth.get(d)!;
    const cnt = layer.length;
    const colStep = cnt > 1 ? (w - padX * 2) / (cnt - 1) : 0;
    const y = padY + layerIdx * layerStep;
    layer.forEach((id, i) => {
      const x = cnt > 1 ? padX + i * colStep : w / 2;
      out.set(id, { x, y });
    });
  });

  items.filter(it => !out.has(it.id)).forEach((it, i) => {
    out.set(it.id, { x: w - 60 - i * 50, y: h - 30 });
  });
  return { positions: out };
}

// Visual constants used by both layout (for spacing) and rendering (for size)
const ATOM_RADIUS = 20;
const RECT_HEIGHT_FULL = 38;   // radial-mode container box
const RECT_HEIGHT_PILL = 22;   // venn-mode container label pill
const RECT_PAD_X = 16;         // horizontal padding inside container rect
const CHAR_W = 6.5;            // approx width per char at text-[10px] font-mono

function truncateLabel(label: string, max = 22): string {
  return label.length > max ? `${label.slice(0, max - 1)}…` : label;
}

function rectWidthFor(label: string): number {
  return Math.max(truncateLabel(label).length * CHAR_W + RECT_PAD_X * 2, 48);
}

// Walk a ray from `from` toward `to` and return the point where it exits the
// shape centred at `from`. Used to clip edge endpoints to the boundary of the
// source/target node so arrow tips touch the outer edge instead of piercing
// through the middle.
function clipRay(from: Pos, to: Pos, shape: { kind: 'circle'; r: number } | { kind: 'rect'; w: number; h: number }): Pos {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const dist = Math.hypot(dx, dy);
  if (dist === 0) return from;
  const ux = dx / dist;
  const uy = dy / dist;
  if (shape.kind === 'circle') {
    return { x: from.x + ux * shape.r, y: from.y + uy * shape.r };
  }
  const halfW = shape.w / 2;
  const halfH = shape.h / 2;
  const tx = ux === 0 ? Infinity : halfW / Math.abs(ux);
  const ty = uy === 0 ? Infinity : halfH / Math.abs(uy);
  const t = Math.min(tx, ty);
  return { x: from.x + ux * t, y: from.y + uy * t };
}

// Several layout names returned by the compiler currently map to the same
// underlying renderer. We dedupe the chips by family so the user only sees one
// button per genuinely distinct visual.
const LAYOUT_FAMILY: Record<string, string> = {
  containment: 'containment',
  topos: 'topos',
  grid: 'grid',
  petals: 'petals',
  fractal: 'fractal',
  radial: 'radial',
  branch: 'branch',
  semantic: 'semantic',
  dependency: 'dependency',
  recipe: 'dependency',
};

function computeLayout(
  layout: string,
  items: DiagramNode[],
  edges: DiagramEdge[],
  containers: DiagramContainer[],
  w: number,
  h: number,
): LayoutResult {
  const family = LAYOUT_FAMILY[layout] ?? layout;
  switch (family) {
    case 'grid':
      return gridLayout(items, containers, w, h);
    case 'petals':
      return petalLayout(items, containers, edges, w, h);
    case 'fractal':
      return fractalLayout(items, edges, w, h);
    case 'dependency':
      return dependencyLayout(items, edges, w, h);
    case 'containment':
      return containmentLayout(items, containers, edges, w, h);
    case 'topos':
      return toposLayout(items, containers, edges, w, h);
    case 'semantic':
      return semanticLayout(items, containers, edges, w, h);
    case 'branch':
      return branchLayout(items, containers, edges, w, h);
    case 'radial':
    default:
      return radialLayout(items, w, h);
  }
}

export function DiagramPreview({ diagram, result }: { diagram?: CasDiagram | null; result?: Record<string, unknown> | null }) {
  // Truth-value of a set-theory assertion (only present for kind=meta_assertion).
  // Used to colour edges green for holds, red for not-holds.
  const assertionHolds: boolean | undefined =
    result && (result as { kind?: string }).kind === 'meta_assertion'
      ? ((result as { holds?: boolean }).holds ?? undefined)
      : undefined;
  // Dedupe the API-supplied layouts by family so we only show one chip per
  // distinct underlying renderer (e.g. containment+topos collapse to one).
  // When the expression has containers (e.g. cluster intersection/union/subset),
  // hoist `containment` to the front so the Venn renderer is the default —
  // otherwise the compiler often prefers `branch` and the Venn semantics get
  // hidden behind a less-informative ring layout.
  const availableLayouts = useMemo(() => {
    const seen = new Set<string>();
    const list = (diagram?.layouts ?? []).filter(layout => {
      const family = LAYOUT_FAMILY[layout] ?? layout;
      if (seen.has(family)) return false;
      seen.add(family);
      return true;
    });
    if (list.includes('grid')) {
      return ['grid', ...list.filter(l => l !== 'grid')];
    }
    if (list.includes('petals')) {
      return ['petals', ...list.filter(l => l !== 'petals')];
    }
    if (list.includes('fractal')) {
      return ['fractal', ...list.filter(l => l !== 'fractal')];
    }
    if ((diagram?.containers.length ?? 0) > 0 && list.includes('containment')) {
      return ['containment', ...list.filter(l => l !== 'containment')];
    }
    return list;
  }, [diagram]);

  const [activeLayout, setActiveLayout] = useState<string>(availableLayouts[0] ?? 'radial');

  // When a brand-new diagram comes in, reset to its first available layout
  useEffect(() => {
    if (availableLayouts.length && !availableLayouts.includes(activeLayout)) {
      setActiveLayout(availableLayouts[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [diagram]);

  if (!diagram || (diagram.nodes.length === 0 && diagram.containers.length === 0)) return null;

  const displayItems: DiagramNode[] = [
    ...diagram.containers.map(c => ({
      id: c.id,
      kind: c.kind,
      label: `${c.label}${typeof c.cardinality === 'number' ? ` (${c.cardinality})` : ''}`,
      role: c.element_type,
    })),
    ...diagram.nodes,
  ].slice(0, 48);

  const VIEW_W = 620;
  const VIEW_H = 360;
  const layoutResult = computeLayout(activeLayout, displayItems, diagram.edges, diagram.containers, VIEW_W, VIEW_H);
  const positions = layoutResult.positions;
  const regions = layoutResult.regions;
  const grid = layoutResult.grid;
  const petals = layoutResult.petals;
  const fractalBranches = layoutResult.fractalBranches ?? [];
  const pointMembers = layoutResult.pointMembers ?? new Set<string>();
  const useVenn = !!regions && regions.size > 0;
  // Edge stroke colour: green/red only for truth-valued assertions; neutral
  // cyan for structural edges so ordinary diagrams do not look like errors.
  const edgeStroke = assertionHolds === true ? '#22c55e' : assertionHolds === false ? '#ef4444' : '#38bdf8';
  const edgeAccent = assertionHolds === true ? 'fill-emerald-300' : assertionHolds === false ? 'fill-red-300' : 'fill-cyan-300';
  const truthBadge = assertionHolds === true ? '✓' : assertionHolds === false ? '✗' : '';
  const visibleIds = new Set(displayItems.map(item => item.id));
  const visibleEdges = diagram.edges.filter(edge => visibleIds.has(edge.source) && visibleIds.has(edge.target)).slice(0, 32);

  return (
    <div className="mt-3 rounded border border-cyan-500/20 bg-cyan-500/[0.035] p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">CAS Diagram</p>
        {availableLayouts.slice(0, 6).map(layout => {
          const isActive = layout === activeLayout;
          return (
            <button
              key={layout}
              type="button"
              onClick={() => setActiveLayout(layout)}
              className={`rounded-full border px-2 py-0.5 text-[9px] transition-colors ${
                isActive
                  ? 'border-cyan-400/60 bg-cyan-500/15 text-cyan-300'
                  : 'border-white/[0.08] bg-white/[0.04] text-slate-400 hover:border-white/[0.16] hover:text-slate-200'
              }`}
            >
              {layout}
            </button>
          );
        })}
      </div>

      <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="h-72 w-full rounded bg-slate-950/50">
        <defs>
          <marker id="cas-arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
            <path d="M0,0 L9,4.5 L0,9 Z" fill={edgeStroke} />
          </marker>
        </defs>
        {grid && (
          <g>
            <rect
              x={grid.x0}
              y={grid.y0}
              width={grid.cellW * Math.max(grid.cols.length, 1)}
              height={grid.cellH * Math.max(grid.rows.length, 1)}
              rx="12"
              fill="#0f172a"
              stroke="#14b8a6"
              strokeOpacity="0.45"
            />
            {Array.from({ length: grid.cols.length + 1 }, (_, i) => (
              <line
                key={`grid-v-${i}`}
                x1={grid.x0 + i * grid.cellW}
                y1={grid.y0}
                x2={grid.x0 + i * grid.cellW}
                y2={grid.y0 + grid.cellH * grid.rows.length}
                stroke="#14b8a6"
                strokeOpacity="0.18"
              />
            ))}
            {Array.from({ length: grid.rows.length + 1 }, (_, i) => (
              <line
                key={`grid-h-${i}`}
                x1={grid.x0}
                y1={grid.y0 + i * grid.cellH}
                x2={grid.x0 + grid.cellW * grid.cols.length}
                y2={grid.y0 + i * grid.cellH}
                stroke="#14b8a6"
                strokeOpacity="0.18"
              />
            ))}
            {grid.rows.flatMap((_, row) =>
              grid.cols.map((_, col) => (
                <circle
                  key={`grid-cell-${row}-${col}`}
                  cx={grid.x0 + grid.cellW * (col + 0.5)}
                  cy={grid.y0 + grid.cellH * (row + 0.5)}
                  r="2.2"
                  fill="#67e8f9"
                  opacity="0.34"
                />
              )),
            )}
            <text x={grid.x0} y={grid.y0 - 48} className="fill-cyan-200 text-[10px] font-semibold">
              {grid.title}
            </text>
          </g>
        )}
        {petals && (
          <g>
            {petals.sectors.map(sector => (
              <path
                key={`petal-${sector.id}`}
                d={wedgePath(petals.cx, petals.cy, petals.innerR, petals.outerR, sector.start + 0.015, sector.end - 0.015)}
                fill={`${sector.color}24`}
                stroke={sector.color}
                strokeOpacity="0.75"
                strokeWidth="1.2"
              />
            ))}
            <circle cx={petals.cx} cy={petals.cy} r={petals.innerR - 6} fill="#020617" stroke="#38bdf8" strokeOpacity="0.5" />
            <text x={petals.cx} y={petals.cy - 4} textAnchor="middle" className="fill-cyan-200 text-[10px] font-semibold">
              {petals.title}
            </text>
            <text x={petals.cx} y={petals.cy + 10} textAnchor="middle" className="fill-slate-400 text-[8px]">
              {petals.sectors.length} pieces
            </text>
          </g>
        )}
        {fractalBranches.map((branch, i) => (
          <line
            key={`fractal-branch-${i}`}
            x1={branch.x1}
            y1={branch.y1}
            x2={branch.x2}
            y2={branch.y2}
            stroke="#38bdf8"
            strokeWidth="1"
            strokeOpacity={branch.opacity}
          />
        ))}
        {/* Venn-style background regions for containment layout — drawn first so
            atoms and edges sit on top */}
        {useVenn && [...regions!.entries()].map(([id, region]) => {
          const container = diagram.containers.find(c => c.id === id);
          if (!container) return null;
          const color = diagramColor(container.kind);
          return (
            <ellipse
              key={`region-${id}`}
              cx={region.cx}
              cy={region.cy}
              rx={region.rx}
              ry={region.ry}
              fill={`${color}15`}
              stroke={color}
              strokeWidth="1.4"
              strokeDasharray="4 3"
            />
          );
        })}
        {visibleEdges.map(edge => {
          const a = positions.get(edge.source);
          const b = positions.get(edge.target);
          if (!a || !b) return null;
          const sourceItem = displayItems.find(it => it.id === edge.source);
          const targetItem = displayItems.find(it => it.id === edge.target);
          const sourceShape = edge.source.startsWith('container:')
            ? { kind: 'rect' as const, w: rectWidthFor(sourceItem?.label ?? ''), h: useVenn ? RECT_HEIGHT_PILL : RECT_HEIGHT_FULL }
            : { kind: 'circle' as const, r: ATOM_RADIUS };
          const targetShape = edge.target.startsWith('container:')
            ? { kind: 'rect' as const, w: rectWidthFor(targetItem?.label ?? ''), h: useVenn ? RECT_HEIGHT_PILL : RECT_HEIGHT_FULL }
            : { kind: 'circle' as const, r: ATOM_RADIUS };
          // Clip the line endpoints to each shape's outer boundary so the
          // arrow tip kisses the edge of the target rather than piercing the
          // node.
          const start = clipRay(a, b, sourceShape);
          const end = clipRay(b, a, targetShape);
          const labelText = edge.label ? `${edge.label}${truthBadge ? ' ' + truthBadge : ''}` : '';
          return (
            <g key={edge.id}>
              <line
                x1={start.x}
                y1={start.y}
                x2={end.x}
                y2={end.y}
                stroke={edgeStroke}
                strokeWidth="1.8"
                strokeOpacity="0.95"
                markerEnd={edge.directed === false ? undefined : 'url(#cas-arrow)'}
              />
              {labelText && (
                <text x={(start.x + end.x) / 2} y={(start.y + end.y) / 2 - 4} textAnchor="middle" className={`${edgeAccent} text-[10px] font-semibold`}>
                  {labelText}
                </text>
              )}
            </g>
          );
        })}
        {displayItems.map(item => {
          const pos = positions.get(item.id);
          if (!pos) return null;
          const color = diagramColor(item.kind, {
            noetic: typeof item.noetic === 'number' ? item.noetic : null,
            domain: typeof item.domain === 'string' ? item.domain : null,
            drive: typeof item.drive === 'number' ? item.drive : null,
          });
          const isContainer = item.id.startsWith('container:');
          const label = truncateLabel(item.label);
          if (isContainer) {
            // Containers asserted as ∈ members render as a small atom-style
            // circle inside their target's region, with a label tag below.
            if (pointMembers.has(item.id)) {
              return (
                <g key={item.id} transform={`translate(${pos.x}, ${pos.y})`}>
                  <circle r={ATOM_RADIUS - 4} fill={`${color}26`} stroke={color} strokeWidth="1.4" />
                  <text y="3" textAnchor="middle" className="fill-slate-100 text-[9px] font-semibold">
                    {label.replace('NoeticCluster', 'NC').replace('StateCluster', 'SC').replace(/\(\d+\)/, '').slice(0, 6)}
                  </text>
                  <text y={ATOM_RADIUS + 8} textAnchor="middle" className="fill-slate-300 text-[8px]">
                    {label}
                  </text>
                </g>
              );
            }
            const w = rectWidthFor(item.label);
            const useVennPill = useVenn;
            const h = useVennPill ? RECT_HEIGHT_PILL : RECT_HEIGHT_FULL;
            return (
              <g key={item.id} transform={`translate(${pos.x}, ${pos.y})`}>
                <rect
                  x={-w / 2}
                  y={-h / 2}
                  width={w}
                  height={h}
                  rx={useVennPill ? 6 : 10}
                  fill={useVennPill ? '#0d1117' : `${color}22`}
                  stroke={color}
                  strokeWidth={useVennPill ? 1.2 : 1.4}
                />
                <text y="3" textAnchor="middle" className="fill-slate-100 text-[10px] font-semibold">
                  {label}
                </text>
              </g>
            );
          }
          return (
            <g key={item.id} transform={`translate(${pos.x}, ${pos.y})`}>
              <circle r={ATOM_RADIUS} fill={`${color}26`} stroke={color} strokeWidth="1.4" />
              <text y="3" textAnchor="middle" className="fill-slate-100 text-[10px] font-semibold">
                {label}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="mt-2 grid gap-1 text-[10px] text-slate-400 sm:grid-cols-3">
        <span>{diagram.nodes.length} nodes</span>
        <span>{diagram.edges.length} edges</span>
        <span>{diagram.containers.length} containment boxes</span>
      </div>
    </div>
  );
}

function ResultCard({ entry }: { entry: HistoryEntry }) {
  if (entry.isCommand) {
    return (
      <div className="animate-[fadeSlideIn_0.2s_ease-out]">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-accent-teal font-mono text-sm">cas&gt;</span>
          <span className="text-slate-300 font-mono text-sm">{entry.input}</span>
        </div>
        <pre className="text-slate-400 text-xs font-mono whitespace-pre-wrap pl-6">{entry.commandOutput}</pre>
      </div>
    );
  }

  // Natural language pipeline result
  if (entry.nlResult) {
    const nl = entry.nlResult;
    const valid = nl.compilation?.valid ?? false;
    return (
      <div className={`animate-[fadeSlideIn_0.3s_ease-out] rounded-lg border p-4 font-mono text-xs ${valid ? 'border-emerald-500/20 bg-emerald-500/[0.03]' : 'border-white/[0.08] bg-white/[0.02]'}`}>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-purple-400">nl&gt;</span>
          <span className="text-sm text-slate-300 font-sans">{entry.input}</span>
        </div>

        {/* Signal extraction */}
        <div className="mb-3 rounded border border-white/[0.06] bg-white/[0.02] p-3">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Signal Extraction</p>
          <div className="space-y-1">
            {nl.signals.operator_scores.map((score, i) => score > 0 ? (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <span className="text-cyan-400 w-32 shrink-0">CO-{i} {OPERATOR_NAMES[i]}</span>
                <div className="flex-1 h-2 rounded-full bg-white/[0.04] overflow-hidden">
                  <div className="h-full rounded-full bg-cyan-500/60" style={{ width: `${score * 10}%` }} />
                </div>
                <span className="text-slate-500 w-8 text-right">{score.toFixed(1)}</span>
              </div>
            ) : null)}
          </div>
          <div className="flex gap-4 mt-2 text-[10px]">
            {(['P', 'C', 'E', 'O'] as const).map((d, i) => (
              <span key={d} className="text-emerald-400">
                {d}={nl.signals.domain_scores[i]?.toFixed(2)}
              </span>
            ))}
            <span className="text-amber-400">RPM={nl.signals.rpm_signal.toFixed(2)}</span>
          </div>
        </div>

        {/* Synthesized notation */}
        {nl.synthesized_notation && (
          <div className="mb-3 rounded border border-accent-teal/20 bg-accent-teal/[0.03] p-3">
            <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Synthesized Notation</p>
            <p className="text-accent-teal text-[12px]">{highlightSyntax(nl.synthesized_notation)}</p>
            {nl.notation_english && (
              <p className="text-[10px] text-slate-400 mt-1 font-sans">{nl.notation_english}</p>
            )}
          </div>
        )}

        {/* Compilation */}
        {nl.compilation && (
          <div className="mb-3 flex items-center gap-2 text-[10px]">
            {nl.compilation.valid ? <span className="text-emerald-400">Compiled</span> : <span className="text-red-400">Compilation failed</span>}
            {nl.compilation.engine && <span className="text-slate-600">engine: {nl.compilation.engine}</span>}
            <span className="text-slate-600">tokens: {nl.compilation.tokens}</span>
            <span className="text-slate-600">bytecode: {nl.compilation.bytecode}</span>
          </div>
        )}

        {nl.compilation?.diagram && <DiagramPreview diagram={nl.compilation.diagram} />}

        {/* Interpretation */}
        <div className="rounded border border-purple-500/20 bg-purple-500/[0.03] p-3">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Interpretation</p>
          <p className="text-[11px] text-slate-300 font-sans leading-relaxed">{nl.interpretation}</p>
        </div>
      </div>
    );
  }

  const r = entry.result;
  if (!r) return null;

  return (
    <div className={`animate-[fadeSlideIn_0.3s_ease-out] rounded-lg border p-4 font-mono text-xs ${
      r.valid
        ? 'border-emerald-500/20 bg-emerald-500/[0.03]'
        : 'border-red-500/20 bg-red-500/[0.03]'
    }`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        <span className="text-accent-teal">cas&gt;</span>
        <span className="text-sm">{highlightSyntax(r.source)}</span>
      </div>
      <div className="flex items-center gap-2 mt-2 text-[10px]">
        {r.valid ? (
          <span className="text-emerald-400">✅ Valid</span>
        ) : (
          <span className="text-red-400">❌ Invalid</span>
        )}
        {r.engine && <span className="text-slate-600">engine: {r.engine}</span>}
        {r.tokens && <span className="text-slate-600">tokens: {r.tokens.length}</span>}
        {r.bytecode && r.bytecode.length > 0 && <span className="text-slate-600">bytecode: {r.bytecode.length}</span>}
      </div>

      {/* Error */}
      {r.error && (
        <div className="mt-3 rounded border border-red-500/20 bg-red-500/[0.05] p-3">
          <p className="text-red-400 text-[11px]">{r.error}</p>
          {r.tokens && r.tokens.length > 0 && (
            <div className="mt-2 text-slate-500 text-[10px]">
              <p className="text-slate-400 mb-1">Tokens parsed before failure:</p>
              <div className="flex flex-wrap gap-1">
                {r.tokens.map((t, i) => (
                  <span key={i} className="px-1.5 py-0.5 rounded bg-white/[0.04] text-slate-400">
                    {t.kind}={t.value}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* AST */}
      {r.ast && (
        <div className="mt-3 rounded border border-white/[0.06] bg-white/[0.02] p-3">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-1">AST</p>
          <pre className="text-[10px] text-slate-400 whitespace-pre-wrap overflow-x-auto">
            {JSON.stringify(r.ast, null, 2).slice(0, 500)}
          </pre>
        </div>
      )}

      {/* Type */}
      {r.type && (
        <div className="mt-2 flex items-center gap-2 text-[10px]">
          <span className="text-slate-500">Type:</span>
          <span className="text-blue-400">{r.type.kind}</span>
          {r.type.domains.length > 0 && (
            <span className="text-emerald-400">[{r.type.domains.join(', ')}]</span>
          )}
          {r.type.singular && <span className="text-amber-400">singular</span>}
        </div>
      )}

      {/* Result */}
      {r.result && (
        <div className="mt-3 rounded border border-accent-teal/20 bg-accent-teal/[0.03] p-3">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Result</p>
          <p className="text-accent-teal text-[12px]">{describeResult(r)}</p>
        </div>
      )}

      {r.diagram && <DiagramPreview diagram={r.diagram} result={r.result} />}

      {r.warnings && r.warnings.length > 0 && (
        <div className="mt-2">
          {r.warnings.map((w, i) => (
            <p key={i} className="text-[10px] text-amber-400">⚠ {w}</p>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Reference panel content (shared by desktop side panel + mobile overlay) ──

function RefPanelContent({ onPickExample }: { onPickExample: (expr: string) => void }) {
  const [exampleView, setExampleView] = useState<ExampleView>('cas');
  const [dictQuery, setDictQuery] = useState('');
  const grouped = EXAMPLES.reduce<Record<string, Example[]>>((acc, ex) => {
    (acc[ex.category] ||= []).push(ex);
    return acc;
  }, {});
  const dictionaryGrouped = DICTIONARY
    .filter((entry) => dictionaryMatches(entry, dictQuery))
    .reduce<Record<string, DictionaryEntry[]>>((acc, entry) => {
      (acc[entry.category] ||= []).push(entry);
      return acc;
    }, {});

  return (
    <>
      {/* Examples — grouped by framework version */}
      <div>
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">Examples</p>
          <div className="flex gap-1 rounded border border-white/[0.06] p-0.5">
            {(['cas', 'natural', 'mirror'] as const).map((view) => (
              <button
                key={view}
                type="button"
                onClick={() => setExampleView(view)}
                className={`rounded px-1.5 py-0.5 text-[8px] font-mono uppercase tracking-wide transition-colors ${
                  exampleView === view
                    ? 'bg-accent-teal/15 text-accent-teal'
                    : 'text-slate-600 hover:text-slate-300'
                }`}
              >
                {view === 'cas' ? 'CAS' : view === 'natural' ? 'Natural' : 'Mirror'}
              </button>
            ))}
          </div>
        </div>
        <p className="mb-2 text-[9px] text-slate-600 leading-relaxed">
          {exampleView === 'mirror'
            ? 'Mirror view shows each exact CAS expression beside its natural-language meaning.'
            : exampleView === 'natural'
              ? 'Natural view teaches what each example says before users read the symbols.'
              : 'CAS view keeps the original compiler examples with a natural-language line beneath each one.'}
        </p>
        <div className="space-y-3">
          {Object.entries(grouped).map(([category, items]) => (
            <div key={category}>
              <p className="text-[9px] font-mono uppercase tracking-wider text-fuchsia-400/70 mb-1">{category}</p>
              <div className="space-y-1">
                {items.map((ex) => (
                  <button
                    key={ex.expr}
                    onClick={() => onPickExample(ex.expr)}
                    className="w-full text-left rounded px-2 py-1.5 text-[10px] font-mono hover:bg-white/[0.04] transition-colors"
                  >
                    <span className="text-slate-500 block text-[9px] font-sans mb-0.5">{ex.label}</span>
                    {exampleView === 'cas' && (
                      <>
                        <span className="block">{highlightSyntax(ex.expr)}</span>
                        <span className="mt-1 block font-sans text-[10px] leading-relaxed text-slate-500">{ex.natural}</span>
                      </>
                    )}
                    {exampleView === 'natural' && (
                      <>
                        <span className="block font-sans text-[10px] leading-relaxed text-slate-300">{ex.natural}</span>
                        <span className="mt-1 block text-slate-600">{highlightSyntax(ex.expr)}</span>
                      </>
                    )}
                    {exampleView === 'mirror' && (
                      <span className="block leading-relaxed">
                        <span className="text-slate-600">(</span>{highlightSyntax(ex.expr)}<span className="text-slate-600">)</span>
                        <span className="font-sans text-slate-300"> {ex.natural}</span>
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Dictionary — all compiler terms, dynamics, and principles */}
      <div>
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">Dictionary</p>
          <span className="text-[8px] font-mono text-slate-600">{DICTIONARY.length} terms</span>
        </div>
        <input
          value={dictQuery}
          onChange={(event) => setDictQuery(event.target.value)}
          placeholder="Filter: noetic, recipe, subset..."
          className="mb-2 w-full rounded border border-white/[0.06] bg-white/[0.02] px-2 py-1.5 text-[10px] text-slate-300 placeholder-slate-700 outline-none focus:border-accent-teal/40"
        />
        <div className="space-y-3">
          {Object.entries(dictionaryGrouped).map(([category, items]) => (
            <div key={category}>
              <p className="text-[9px] font-mono uppercase tracking-wider text-fuchsia-400/70 mb-1">{category}</p>
              <div className="space-y-1">
                {items.map((entry) => {
                  const runnable = isRunnableDictionaryExample(entry.example);
                  return (
                    <button
                      key={`${entry.category}:${entry.term}`}
                      type="button"
                      onClick={() => { if (runnable) onPickExample(entry.example); }}
                      className={`w-full rounded px-2 py-1.5 text-left transition-colors ${
                        runnable ? 'hover:bg-white/[0.04]' : 'cursor-default'
                      }`}
                      title={runnable ? 'Load example' : 'Reference-only entry'}
                    >
                      <span className="flex items-center justify-between gap-2">
                        <span className="text-[10px] font-semibold text-accent-teal">{entry.term}</span>
                        <span className="shrink-0 font-mono text-[9px] text-violet-300">{highlightSyntax(entry.notation)}</span>
                      </span>
                      <span className="mt-1 block font-sans text-[10px] leading-relaxed text-slate-400">{entry.definition}</span>
                      <span className="mt-1 block font-mono text-[9px] text-slate-600">example: {highlightSyntax(entry.example)}</span>
                      <span className="mt-1 block font-sans text-[9px] leading-relaxed text-slate-600">learn: {entry.learn}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
          {Object.keys(dictionaryGrouped).length === 0 && (
            <p className="text-[10px] text-slate-600">No dictionary terms match that filter.</p>
          )}
        </div>
      </div>

      {/* Learning path */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Learning Path</p>
        <div className="space-y-2">
          {LEARNING_PATH.map((step) => (
            <button
              key={step.title}
              type="button"
              onClick={() => onPickExample(step.practice)}
              className="w-full rounded border border-white/[0.06] bg-white/[0.02] px-2 py-2 text-left hover:border-accent-teal/30 hover:bg-accent-teal/[0.03] transition-colors"
            >
              <span className="block text-[10px] font-semibold text-accent-teal">{step.title}</span>
              <span className="mt-1 block font-sans text-[10px] leading-relaxed text-slate-400">{step.goal}</span>
              <span className="mt-1 block font-sans text-[9px] leading-relaxed text-slate-600">terms: {step.terms}</span>
              <span className="mt-1 block font-mono text-[9px] text-slate-500">try: {highlightSyntax(step.practice)}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Noetics (10 cognitive operators — authoritative names) */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Noetics (^0 – ^9)</p>
        <div className="space-y-0.5">
          {OPERATOR_NAMES.map((name, i) => (
            <div key={i} className="flex items-center gap-2 text-[10px]">
              <span className="text-cyan-400 font-mono w-8">^{i}</span>
              <span className="text-slate-500">{name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Domains */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Domains (P ≻ C ≻ E ≻ O)</p>
        {Object.entries(DOMAIN_NAMES).map(([code, name]) => (
          <div key={code} className="flex items-center gap-2 text-[10px]">
            <span className="text-emerald-400 font-mono w-6">^{code}</span>
            <span className="text-slate-500">{name}</span>
          </div>
        ))}
      </div>

      {/* Drives */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Drives (F1 – F7)</p>
        {DRIVE_NAMES.map((name, i) => (
          <div key={i} className="flex items-center gap-2 text-[10px]">
            <span className="text-amber-400 font-mono w-6">F{i + 1}</span>
            <span className="text-slate-500">{name}</span>
          </div>
        ))}
      </div>

      {/* Phenomenological Registers — CAS v7.5 */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Registers (v7.5)</p>
        {Object.entries(REGISTER_NAMES).map(([code, name]) => (
          <div key={code} className="flex items-center gap-2 text-[10px]">
            <span className="text-fuchsia-400 font-mono w-6">|{code}</span>
            <span className="text-slate-500">{name}</span>
          </div>
        ))}
        <p className="text-[9px] text-slate-600 mt-1.5 leading-relaxed">
          Specifies operational character. Optional — omit for register-neutral.
        </p>
      </div>

      {/* Production Semantics — CAS v7.6 */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Production (v7.6)</p>
        <div className="space-y-0.5 text-[10px]">
          <div><span className="text-pink-400 font-mono">Θ(Ω)</span> <span className="text-slate-500">Recipe for target Ω</span></div>
          <div><span className="text-orange-400 font-mono">Ω_name</span> <span className="text-slate-500">Production target</span></div>
          <div><span className="text-purple-400 font-mono">Y_T / Y_A</span> <span className="text-slate-500">Theoretical / actual yield</span></div>
          <div><span className="text-orange-400 font-mono">Λ_n</span> <span className="text-slate-500">Leakage / side-reaction</span></div>
          <div><span className="text-orange-400 font-mono">κ_n</span> <span className="text-slate-500">Catalyst</span></div>
          <div><span className="text-orange-400 font-mono">ι_n</span> <span className="text-slate-500">Inhibitor</span></div>
        </div>
      </div>

      {/* Operator Discipline — CAS v7.7 */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Operator Discipline (v7.7)</p>
        <div className="space-y-1 text-[10px]">
          <div><span className="text-fuchsia-400 font-mono">|⟨…⟩</span> <span className="text-slate-500">Register-set specification</span></div>
          <div><span className="text-slate-300 font-mono">+</span> <span className="text-slate-500">Co-presence (defeasible)</span></div>
          <div><span className="text-orange-400 font-mono">×</span> <span className="text-slate-500">Integration → emergent Ω</span></div>
        </div>
        <p className="text-[9px] text-slate-600 mt-1.5 leading-relaxed">
          Same-Noetic <span className="font-mono">×</span> requires named <span className="font-mono">Ω</span> result.
        </p>
      </div>

      {/* Set Theory / discrete-math layer */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Set Theory</p>
        <div className="space-y-0.5 text-[10px]">
          <div><span className="text-teal-300 font-mono">∈ ∉</span> <span className="text-slate-500">Member / not member</span></div>
          <div><span className="text-teal-300 font-mono">⊂ ⊆</span> <span className="text-slate-500">Proper subset / subset</span></div>
          <div><span className="text-teal-300 font-mono">⊃ ⊇</span> <span className="text-slate-500">Proper superset / superset</span></div>
          <div><span className="text-violet-300 font-mono">∅</span> <span className="text-slate-500">Empty set</span></div>
          <div><span className="text-slate-300 font-mono">|S|</span> <span className="text-slate-500">Cardinality of S</span></div>
          <div><span className="text-violet-300 font-mono">NoeticCluster{'{^2,^7}'}</span> <span className="text-slate-500">Typed Noetic collection</span></div>
          <div><span className="text-violet-300 font-mono">StateCluster{'{^2^P,C7}'}</span> <span className="text-slate-500">Typed State collection</span></div>
          <div><span className="text-violet-300 font-mono">StateVariantCluster{'{^3^P_{F2}|A}'}</span> <span className="text-slate-500">Drive/Register variants</span></div>
        </div>
        <p className="text-[9px] text-slate-600 mt-2 mb-1 uppercase tracking-wider">Topos-safe reference</p>
        <div className="space-y-0.5 text-[10px]">
          <div><span className="text-slate-400 font-mono">A ∪ B / A ∩ B / A ∖ B</span> <span className="text-slate-500">Set union, meet, difference</span></div>
          <div><span className="text-slate-400 font-mono">RelationCluster{'{^5^P -> ^5^C}'}</span> <span className="text-slate-500">Typed dependency rows</span></div>
          <div><span className="text-slate-400 font-mono">Tuple{'{^2,P,F2,A}'}</span> <span className="text-slate-500">Ordered product element</span></div>
          <div><span className="text-slate-400 font-mono">Coordinate{'{^2,P,F2,A}'}</span> <span className="text-slate-500">CAS coordinate tag</span></div>
          <div><span className="text-slate-400 font-mono">Product(Noetics, Domains)</span> <span className="text-slate-500">Namespaced Cartesian product</span></div>
          <div><span className="text-slate-400 font-mono">Pullback(A, B)</span> <span className="text-slate-500">Finite subobject meet</span></div>
          <div><span className="text-slate-400 font-mono">CoverOf(Base, U1...)</span> <span className="text-slate-500">Validated cover of base</span></div>
          <div><span className="text-slate-400 font-mono">PartitionOf(Base, U1...)</span> <span className="text-slate-500">Validated disjoint cover</span></div>
        </div>
        <p className="text-[9px] text-slate-600 mt-2 leading-relaxed">
          These are compiler-backed finite meta-logic constructs. Pullback here means finite meet/intersection, not a general categorical pullback with maps.
        </p>
        <p className="text-[9px] text-slate-600 mt-2 mb-1 uppercase tracking-wider">Built-in sets</p>
        <div className="space-y-0.5 text-[10px]">
          <div><span className="text-violet-300 font-mono">Noetics</span> <span className="text-slate-500">{'{^0…^9}, |·|=10'}</span></div>
          <div><span className="text-violet-300 font-mono">Domains</span> <span className="text-slate-500">{'{P,C,E,O}, |·|=4'}</span></div>
          <div><span className="text-violet-300 font-mono">Drives</span> <span className="text-slate-500">{'{F1…F7}, |·|=7'}</span></div>
          <div><span className="text-violet-300 font-mono">Registers</span> <span className="text-slate-500">{'{T,A,f,E}, |·|=4'}</span></div>
          <div><span className="text-violet-300 font-mono">States</span> <span className="text-slate-500">{'10×4 = 40 cog. states'}</span></div>
          <div><span className="text-violet-300 font-mono">Foundations</span> <span className="text-slate-500">{'7 named foundations'}</span></div>
          <div><span className="text-violet-300 font-mono">SubFoundations</span> <span className="text-slate-500">{'7×4 = 28 sub-foundations'}</span></div>
          <div><span className="text-violet-300 font-mono">Foundation_1…7</span> <span className="text-slate-500">{'individual foundation set'}</span></div>
          <div><span className="text-violet-300 font-mono">EmptySet</span> <span className="text-slate-500">{'≡ ∅'}</span></div>
        </div>
        <p className="text-[9px] text-slate-600 mt-2 leading-relaxed">
          ASCII fallbacks accepted (auto-expanded on submit):{' '}
          <span className="font-mono text-teal-300">in</span>,{' '}
          <span className="font-mono text-teal-300">notin</span>,{' '}
          <span className="font-mono text-teal-300">subset</span>,{' '}
          <span className="font-mono text-teal-300">subseteq</span>,{' '}
          <span className="font-mono text-teal-300">supset</span>,{' '}
          <span className="font-mono text-teal-300">supseteq</span>,{' '}
          <span className="font-mono text-violet-300">emptyset</span>.
        </p>
      </div>

      {/* Operations */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Operations</p>
        <div className="space-y-0.5 text-[10px]">
          <div><span className="text-orange-400 font-mono">×</span> <span className="text-slate-500">Composition / integration</span></div>
          <div><span className="text-orange-400 font-mono">÷</span> <span className="text-slate-500">Division (algebraic)</span></div>
          <div><span className="text-orange-400 font-mono">∘</span> <span className="text-slate-500">Fractal (algebraic)</span></div>
          <div><span className="text-slate-300 font-mono">+</span> <span className="text-slate-500">Co-presence (syntactic)</span></div>
          <div><span className="text-slate-300 font-mono">·</span> <span className="text-slate-500">Recipe coefficient</span></div>
          <div><span className="text-white font-mono">→</span> <span className="text-slate-500">Dependency / yields</span></div>
        </div>
      </div>
    </>
  );
}

// ── Main Page ──

export function CompilerPage() {
  const [mode, setMode] = useState<'cas' | 'nl'>('cas');
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [cmdHistory, setCmdHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const [loading, setLoading] = useState(false);
  const [showRef, setShowRef] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const mirrorRef = useRef<HTMLDivElement>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight, behavior: 'smooth' });
  }, [history]);

  // Auto-resize the textarea to fit its contents (capped to keep input area sane)
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 240) + 'px';
  }, [input]);

  const addEntry = useCallback((entry: HistoryEntry) => {
    setHistory((prev) => [...prev, entry]);
  }, []);

  // Insert a symbol from the palette at the input cursor position
  function insertSymbol(sym: string) {
    const el = inputRef.current;
    if (!el) {
      setInput((cur) => cur + sym);
      return;
    }
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? el.value.length;
    const newValue = el.value.slice(0, start) + sym + el.value.slice(end);
    setInput(newValue);
    setTimeout(() => {
      el.focus();
      const pos = start + sym.length;
      try { el.setSelectionRange(pos, pos); } catch { /* selection range may be unsupported on some inputs */ }
    }, 0);
  }

  async function handleSubmit() {
    const trimmed = input.trim();
    if (!trimmed) return;

    setCmdHistory((prev) => [trimmed, ...prev].slice(0, 50));
    setHistoryIdx(-1);
    setInput('');

    const ts = Date.now();

    // Special commands
    if (trimmed === ':help') {
      addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: HELP_TEXT, timestamp: ts });
      return;
    }
    if (trimmed === ':clear') {
      setHistory([]);
      return;
    }
    if (trimmed === ':examples') {
      addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: formatExamplesForCommand('cas'), timestamp: ts });
      return;
    }
    if (trimmed === ':natural') {
      addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: formatExamplesForCommand('natural'), timestamp: ts });
      return;
    }
    if (trimmed === ':mirror') {
      addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: formatExamplesForCommand('mirror'), timestamp: ts });
      return;
    }
    if (trimmed === ':dict' || trimmed.startsWith(':dict ')) {
      const query = trimmed.startsWith(':dict ') ? trimmed.slice(':dict '.length).trim() : '';
      addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: formatDictionaryForCommand(query), timestamp: ts });
      return;
    }
    if (trimmed === ':learn') {
      addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: formatLearningForCommand(), timestamp: ts });
      return;
    }
    if (trimmed === ':history') {
      const text = cmdHistory.slice(0, 20).map((c, i) => `  ${i + 1}. ${c}`).join('\n');
      addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: text || '  (empty)', timestamp: ts });
      return;
    }
    if (trimmed === ':grammar') {
      try {
        const data = await apiFetch<{ grammar: string }>('/notation/grammar');
        addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: data.grammar, timestamp: ts });
      } catch {
        addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: 'Failed to fetch grammar', timestamp: ts });
      }
      return;
    }

    // Route based on mode
    setLoading(true);
    if (mode === 'nl') {
      try {
        const nlResult = await apiFetch<NlPipelineResult>('/notation/natural-language', {
          method: 'POST',
          body: JSON.stringify({ text: trimmed, compile: true }),
        });
        addEntry({ input: trimmed, result: null, nlResult, isCommand: false, timestamp: ts });
      } catch (err) {
        const detail = err instanceof Error ? err.message : String(err);
        const isNotFound = detail.includes('Not Found') || detail.includes('404');
        const errorMsg = isNotFound
          ? 'Natural Language endpoint not available. The backend needs to be redeployed with the latest code. Try deploying the API to Railway.'
          : detail;
        addEntry({ input: trimmed, result: { source: '', valid: false, error: errorMsg }, isCommand: false, timestamp: ts });
      } finally {
        setLoading(false);
      }
      return;
    }

    // CAS notation mode — compile expression. Expand ASCII aliases (in, notin,
    // subset, etc.) to canonical Unicode before the compiler sees them.
    const compileSource = expandAsciiAliases(trimmed);
    try {
      const result = await apiFetch<CompileResult>('/notation/compile', {
        method: 'POST',
        body: JSON.stringify({ expression: compileSource }),
      });
      addEntry({ input: compileSource, result, isCommand: false, timestamp: ts });
    } catch (err) {
      // If compile returns 422, the error detail has the compilation error
      const detail = err instanceof Error ? err.message : String(err);
      // Try to get the full artifact even on error
      try {
        const raw = await fetch(`${import.meta.env.PROD ? '/api' : (import.meta.env.VITE_API_URL ?? '/api')}/notation/compile`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ expression: compileSource }),
        });
        if (raw.status === 422) {
          const body = await raw.json();
          addEntry({
            input: compileSource,
            result: { source: compileSource, valid: false, error: body.detail ?? detail, engine: 'rust+python' },
            isCommand: false,
            timestamp: ts,
          });
        } else {
          addEntry({
            input: compileSource,
            result: { source: compileSource, valid: false, error: detail },
            isCommand: false,
            timestamp: ts,
          });
        }
      } catch {
        addEntry({
          input: compileSource,
          result: { source: compileSource, valid: false, error: detail },
          isCommand: false,
          timestamp: ts,
        });
      }
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      // Plain Enter submits; Shift+Enter inserts a newline (textarea default)
      e.preventDefault();
      handleSubmit();
      return;
    }
    // History recall: only when the textarea is empty, so multi-line editing
    // can use arrows naturally once any text is present.
    if (e.key === 'ArrowUp' && input.length === 0) {
      e.preventDefault();
      const next = Math.min(historyIdx + 1, cmdHistory.length - 1);
      setHistoryIdx(next);
      if (cmdHistory[next]) setInput(cmdHistory[next]);
    }
    if (e.key === 'ArrowDown' && input.length === 0) {
      e.preventDefault();
      const next = historyIdx - 1;
      if (next < 0) {
        setHistoryIdx(-1);
        setInput('');
      } else {
        setHistoryIdx(next);
        if (cmdHistory[next]) setInput(cmdHistory[next]);
      }
    }
  }

  return (
    <div className="flex h-full max-h-[calc(100vh-5rem)]">
      {/* Main terminal */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Output area */}
        <div
          ref={outputRef}
          className="flex-1 overflow-y-auto p-4 space-y-4 font-mono"
          style={{ backgroundColor: '#0d1117' }}
          onClick={() => inputRef.current?.focus()}
        >
          {/* Logo: ASCII CAS with 10-dot formation fused to the end of the S */}
          {history.length === 0 && (
            <div className="space-y-3">
              <div className="select-none flex items-start gap-4">
                <pre className="text-accent-teal text-[10px] leading-tight whitespace-pre m-0 shrink-0">{ASCII_LINES.join('\n')}</pre>
                {/* TKS 10-dot formation — 3D spheres with shadow matching ASCII depth */}
                <svg viewBox="0 0 800 1100" className="shrink-0" style={{ height: '100px', width: '58px' }}>
                  <defs>
                    <radialGradient id="dotGrad" cx="35%" cy="35%" r="65%">
                      <stop offset="0%" stopColor="#5ce0d6" />
                      <stop offset="70%" stopColor="#38b2ac" />
                      <stop offset="100%" stopColor="#2a9d8f" />
                    </radialGradient>
                    <filter id="dotShadow" x="-20%" y="-20%" width="150%" height="150%">
                      <feDropShadow dx="8" dy="8" stdDeviation="0" floodColor="rgba(56,178,172,0.3)" />
                      <feDropShadow dx="0" dy="0" stdDeviation="12" floodColor="rgba(56,178,172,0.2)" />
                    </filter>
                  </defs>
                  <circle cx="400" cy="55"   r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 0s infinite alternate' }} />
                  <circle cx="110" cy="190"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 0.25s infinite alternate' }} />
                  <circle cx="690" cy="190"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 0.5s infinite alternate' }} />
                  <circle cx="400" cy="400"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 0.75s infinite alternate' }} />
                  <circle cx="110" cy="545"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 1.0s infinite alternate' }} />
                  <circle cx="690" cy="545"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 1.25s infinite alternate' }} />
                  <circle cx="400" cy="690"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 1.5s infinite alternate' }} />
                  <circle cx="110" cy="870"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 1.75s infinite alternate' }} />
                  <circle cx="690" cy="870"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 2.0s infinite alternate' }} />
                  <circle cx="400" cy="1020" r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 2.25s infinite alternate' }} />
                </svg>
              </div>
              <p className="text-slate-500 text-xs">
                Type <span className="text-slate-300">:help</span> for commands,{' '}
                <span className="text-slate-300">:grammar</span> for the BNF,{' '}
                <span className="text-slate-300">:examples</span> for sample expressions,{' '}
                <span className="text-slate-300">:mirror</span> for 1:1 translations,{' '}
                <span className="text-slate-300">:dict</span> for terms
              </p>
            </div>
          )}

          {/* History */}
          {history.map((entry, i) => (
            <ResultCard key={i} entry={entry} />
          ))}

          {loading && (
            <div className="flex items-center gap-2 text-slate-500 text-xs font-mono animate-pulse">
              <span className="text-accent-teal">cas&gt;</span>
              <span>Compiling...</span>
            </div>
          )}
        </div>

        {/* Mode toggle + Input area */}
        <div className="border-t border-white/[0.06]" style={{ backgroundColor: '#0d1117' }}>
          <div className="flex gap-1 px-3 pt-2">
            <button
              onClick={() => setMode('cas')}
              className={`rounded px-2 py-1 text-[10px] font-mono transition-colors ${mode === 'cas' ? 'bg-accent-teal/15 text-accent-teal' : 'text-slate-600 hover:text-slate-400'}`}
            >
              CAS Notation
            </button>
            <button
              onClick={() => setMode('nl')}
              className={`rounded px-2 py-1 text-[10px] font-mono transition-colors ${mode === 'nl' ? 'bg-purple-500/15 text-purple-400' : 'text-slate-600 hover:text-slate-400'}`}
            >
              Natural Language
            </button>
          </div>
          {/* Quick-insert symbol palette — Unicode chars hard to type on a US keyboard */}
          {mode === 'cas' && (
            <div className="px-3 pt-2 pb-0 flex items-center gap-1 overflow-x-auto whitespace-nowrap scrollbar-thin">
              {SYMBOL_PALETTE.map((item) => (
                <button
                  key={item.sym}
                  onClick={() => insertSymbol(item.sym)}
                  title={item.title}
                  type="button"
                  className="shrink-0 px-2 py-1 rounded text-xs font-mono border border-white/[0.06] hover:border-accent-teal/50 hover:bg-white/[0.04] transition-colors leading-none min-h-[28px]"
                >
                  {highlightSyntax(item.sym)}
                </button>
              ))}
            </div>
          )}
          <div className="p-3 pt-1 flex items-start gap-2">
          <span className={`font-mono text-sm font-bold shrink-0 pt-2 ${mode === 'nl' ? 'text-purple-400' : 'text-accent-teal'}`}>
            {mode === 'nl' ? 'nl>' : 'cas>'}
          </span>
          <div className="flex-1 relative min-h-[44px]">
            {mode === 'cas' && input && (
              <div
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 font-mono text-sm overflow-hidden"
              >
                <div ref={mirrorRef} className="whitespace-pre-wrap break-words py-2">
                  {highlightSyntax(input)}
                </div>
              </div>
            )}
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onScroll={(e) => {
                // Keep the colored mirror in lockstep with the textarea's scroll
                if (mirrorRef.current) {
                  mirrorRef.current.style.transform =
                    `translateY(${-e.currentTarget.scrollTop}px)`;
                }
              }}
              placeholder={mode === 'nl'
                ? 'Type any sentence or paragraph...'
                : 'Θ(Ω_focus)|κ_n = 0.6·^2^P_{F2}|A + 0.4·^5^C → Ω_focus;  ^2 ∈ Noetics'}
              rows={1}
              className={`block w-full bg-transparent border-none outline-none text-sm placeholder-slate-700 resize-none whitespace-pre-wrap break-words py-2 px-0 leading-normal ${mode === 'nl' ? 'font-sans caret-purple-400 text-slate-200' : 'font-mono caret-accent-teal text-transparent selection:bg-accent-teal/30'}`}
              style={{ maxHeight: '240px', overflowY: 'auto' }}
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <button
            onClick={() => setShowRef(!showRef)}
            className="shrink-0 px-2 py-1 rounded text-[10px] font-mono text-slate-500 hover:text-slate-300 border border-white/[0.06] hover:border-white/[0.12] transition-colors min-h-[36px] mt-1"
          >
            {showRef ? 'Hide Ref' : 'Ref'}
          </button>
          </div>
        </div>
      </div>

      {/* Desktop side panel — only renders at sm and up */}
      {showRef && (
        <div className="hidden sm:block w-72 border-l border-white/[0.06] overflow-y-auto p-4 space-y-5 shrink-0" style={{ backgroundColor: '#0d1117' }}>
          <RefPanelContent onPickExample={(expr) => { setInput(expr); inputRef.current?.focus(); }} />
        </div>
      )}

      {/* Mobile full-screen overlay — only renders below sm. No slide-out side panel. */}
      {showRef && (
        <div className="sm:hidden fixed inset-0 z-50 flex flex-col" style={{ backgroundColor: '#0d1117' }}>
          <div className="flex items-center justify-between border-b border-white/[0.06] p-3 shrink-0">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-300">Reference</span>
            <button
              onClick={() => setShowRef(false)}
              className="px-3 py-1.5 rounded text-[11px] font-mono text-slate-200 border border-white/[0.12] hover:border-white/[0.24] active:bg-white/[0.04]"
            >
              Close
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-5">
            <RefPanelContent
              onPickExample={(expr) => {
                setInput(expr);
                setShowRef(false);
                inputRef.current?.focus();
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
