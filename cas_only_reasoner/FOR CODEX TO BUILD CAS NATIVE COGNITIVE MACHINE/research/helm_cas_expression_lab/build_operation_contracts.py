"""Q2 -- freeze `OPERATION_CONTRACTS.json`: the small set of CAS operations a learned module may be trained against.

An operation is admitted only when it has (directive section 7): a versioned identifier, an
authoritative definition, a PINNED implementation, input/output types, a valid domain, invalid-input
behaviour, a mutation policy, a numerical policy, and INDEPENDENT expected-output cases.

Two disciplines this builder enforces rather than describes:

  * PINS ARE MEASURED, NOT TYPED. Every implementation this contract points at is hashed from the
    bytes on disk at build time and the hash is written into the contract. `test_operation_contracts.py`
    re-hashes at test time; a moved or edited source fails the test. A contract that names a file
    without a hash is a hope.
  * EXPECTED CASES ARE HAND-PINNED HERE, NOT GENERATED FROM `reference_ops.py`. If the reference were
    used to write its own answer key, a bug in the reference would certify itself. The cases below were
    written from the Rust source by reading it, and the test checks the reference against them.

VERSION 0.2 (2026-09-21), what changed from 0.1 and why:
  * Notation: the ten Noetics are written ^0 .. ^9 (owner ruling OD-2). The engine's own spelling (CO-0,
    `CO2`) appears only where the engine's text is quoted, with the ^ form beside it.
  * The canonical 28 is settled (owner ruling OD-3: 28 Foundations 1.0). DR-4 is RESOLVED.
  * A measured witness that two admissible steps do NOT make an admissible collapsed step
    (`is_admissible.witnesses.no_composition_law`): 238,572 of 556,960 chains. No generator may assume it.
  * Three places where the canonical book and the engine code disagree are recorded (DR-5..DR-7) with the
    owner's decision OD-6: the first experiment stays on the engine code's rules.
  * `states.rs`, the authority for the 40-state index, is now pinned like the other sources.
  * The digest is PORTABLE: everything that depends on the machine that ran the build (raw-byte digests,
    whether an origin file is checked out, the validator's version, Windows path separators) moved to a
    non-digested `environment` block. The same sources give the same `contract_digest` on any machine.

VERSION 0.3 (2026-09-21, same day): a reviewer showed that 0.2 compared the WRONG book passages with the engine.
  * The book has TWO combining operations. `x` (Monoid Composition, lines 1727/1729/2782/5572) is ^((a+b) mod 10): the
    engine's compose MATCHES it on the Noetic index and lacks only its domain rule. The non-commutative one is the Nesting
    Operator (Definition 26.1), which the engine does not have at all. 0.2's DR-7 called that a disagreement; it is not.
  * The book's closure claim is about composable morphisms giving SOME morphism. Tested fairly it fails for 9,720 of
    556,960 chains (1.75%), not 238,572 (42.8%); the larger number is a fact about the engine's index-sum collapse.
  * DR-5: nothing pinned enforces 'no single step across intermediate domains' -- the mask enforces direction only.
  * The book itself is now pinned by hash and every quoted phrase is tested against its cited line.

Usage:  python research/helm_cas_expression_lab/build_operation_contracts.py
Cost:   $0. Pure Python. Writes OPERATION_CONTRACTS.json and contracts_package_schema/*.json beside itself.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[1]                       # .../FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE
REPO = HERE.parents[3]                          # the worktree root
VENDORED = HERE / "pinned_sources"                # byte copies taken 2026-09-21, see PINNED_SOURCES.json
ENGINE_REL = "noetic-compass-scaffold/noetic-compass/cas-engine/src"
NATIVE_REL = "noetic-compass-scaffold/noetic-compass/cas-native"
TOKENIZER_REL = "cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json"
CONTRACT_VERSION = "helm-cas-expression-lab.operation-contracts/0.3"
BOOK = "book/manuscript/FULL_MANUSCRIPT_v2.md"

HASH_POLICY = {
    "policy_id": "cncm.hash-policy/1.0", "algorithm": "sha256",
    "compared": "the digest of the LF-normalised bytes (every CRLF -> LF, nothing else touched) -- the bytes git stores, so a pin is the same on Windows and Linux",
    "informational": "environment.raw_observed_pins: the digest of the exact bytes on the building machine; never compared, not part of contract_digest",
    "meaning_of_a_match": "the same text under the declared newline rule -- not a claim that the raw bytes are identical",
}
ENVIRONMENT = {"note": "NOT part of contract_digest: facts about the machine that ran the build", "raw_observed_pins": {}, "origin_on_disk_at_build": {}}


def canonical_bytes(path):
    """LF-normalised bytes. Git stores LF; Windows checkouts read CRLF. A pin over raw bytes would hold on
    exactly one machine. This is the CRLF trap recorded in memory, closed at the hash."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def _hash(path, label):
    if not path.is_file():
        raise SystemExit("CONTRACT_REFUSED:PIN_SOURCE_MISSING:%s" % path)
    raw = path.read_bytes()
    data = raw.replace(b"\r\n", b"\n")
    ENVIRONMENT["raw_observed_pins"][label] = {"bytes_raw_observed": len(raw), "sha256_raw_observed": hashlib.sha256(raw).hexdigest()}
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "hash_policy": "lf-normalised"}


def pin(rel):
    """Pin a source by its VENDORED byte copy, with the tracked ORIGIN recorded as provenance.

    The engine and CAS-Native trees are tracked in this repository but are NOT checked out in this
    worktree (sparse / skip-worktree), so the checkable artifact is the copy under `pinned_sources/`,
    taken 2026-09-21 and hashed against the main checkout at copy time (`PINNED_SOURCES.json`,
    `copy_matches_origin`). Rules, enforced here and re-checked by the test:
      * the vendored copy MUST exist and MUST match the manifest's hash (the manifest is the record of
        what the origin was when copied);
      * if the origin IS on disk, it MUST match too -- drift detection when someone checks it out;
      * whether the origin was on disk is a fact about THIS machine: it goes to `environment`, not the digest.
    """
    manifest = json.loads((VENDORED / "PINNED_SOURCES.json").read_text(encoding="utf-8"))
    recorded = {row["origin"]: row for row in manifest["files"]}
    if rel not in recorded:
        raise SystemExit("CONTRACT_REFUSED:NOT_IN_PINNED_SOURCES_MANIFEST:%s" % rel)
    copy = _hash(VENDORED / rel, "pinned_sources/" + rel)
    if copy["sha256"] != recorded[rel]["sha256"] or not recorded[rel]["copy_matches_origin"]:
        raise SystemExit("CONTRACT_REFUSED:VENDORED_COPY_DIVERGED_FROM_MANIFEST:%s" % rel)
    origin_path = REPO / rel
    origin_on_disk = origin_path.is_file()
    if origin_on_disk and hashlib.sha256(canonical_bytes(origin_path)).hexdigest() != copy["sha256"]:
        raise SystemExit("CONTRACT_REFUSED:ORIGIN_DIVERGED_FROM_VENDORED_COPY:%s" % rel)
    ENVIRONMENT["origin_on_disk_at_build"][rel] = origin_on_disk
    return {"path": rel, "vendored_path": "pinned_sources/" + rel, **copy}


def measure_no_composition_law(ref):
    """Count two-step chains s -a-> t -b-> u with both steps admissible, and how many of them are NOT
    admissible as ONE step under the collapsed operator compose(a, b). Exhaustive over the finite grid."""
    states = [(d, n) for d in ref.DOMAINS for n in range(10)]
    reach = {(k, s): [t for t in states if ref.is_admissible(k, s, t)] for k in range(10) for s in states}
    reach_set = {key: set(value) for key, value in reach.items()}
    chains = broken = 0
    for a in range(10):
        for b in range(10):
            ab = ref.compose(a, b)
            for s in states:
                allowed = reach_set[(ab, s)]
                for t in reach[(a, s)]:
                    outs = reach[(b, t)]
                    chains += len(outs)
                    broken += sum(1 for u in outs if u not in allowed)
    return chains, broken


def measure_fair_closure(ref):
    """The book's closure claim read fairly: composable admissible arrows s->t, t->u give SOME admissible arrow s->u."""
    states = [(d, n) for d in ref.DOMAINS for n in range(10)]
    reach = {(k, s): [t for t in states if ref.is_admissible(k, s, t)] for k in range(10) for s in states}
    arrow = {(s, t) for s in states for t in states if any(ref.is_admissible(k, s, t) for k in range(10))}
    chains_without_any_arrow = sum(1 for a in range(10) for b in range(10) for s in states for t in reach[(a, s)] for u in reach[(b, t)] if (s, u) not in arrow)
    paths = [(s, t, u) for (s, t) in sorted(arrow) for u in states if (t, u) in arrow]
    failing = sorted({(s, u) for s, t, u in paths if (s, u) not in arrow})
    return {"state_pairs_with_some_admissible_operator": len(arrow), "of_state_pairs": 1600,
            "operator_labelled_chains_with_no_admissible_operator_end_to_end": chains_without_any_arrow,
            "state_pair_paths": len(paths), "state_pair_paths_with_no_arrow_end_to_end": sum(1 for s, t, u in paths if (s, u) not in arrow),
            "failing_end_to_end_pairs": len(failing),
            "every_failure_ends_at_a_cross_domain_state_with_noetic_0": all(u[1] == 0 and s[0] != u[0] for s, u in failing),
            "example": [list(failing[0][0]), list(failing[0][1])]}


def measure_cross_domain_moves(ref):
    states = [(d, n) for d in ref.DOMAINS for n in range(10)]
    order = {d: i for i, d in enumerate(ref.DOMAINS)}
    cross = [(s, t) for k in range(10) for s in states for t in states if s[0] != t[0] and ref.is_admissible(k, s, t)]
    mask = ref.domain_descent_mask()
    return {"cross_domain_admissible_triples": len(cross),
            "one_step_descents": sum(1 for s, t in cross if order[t[0]] - order[s[0]] == 1),
            "descents_that_skip_a_domain": sum(1 for s, t in cross if order[t[0]] - order[s[0]] > 1),
            "upward_moves": sum(1 for s, t in cross if order[t[0]] < order[s[0]]),
            "mask_true_cells": sum(map(sum, mask)), "mask_true_cells_that_skip_a_domain": sum(1 for i in range(40) for j in range(40) if mask[i][j] and i // 10 - j // 10 > 1)}


BOOK_QUOTES = {   # line number -> a phrase that must be found on that line of the pinned book
    1142: "28 Domain-Specific Drives", 1729: "^a × ^b = ^((a+b) mod 10)", 2782: "^(min(Domain-x, Domain-y))",
    5548: "the admissibility structure enforces this descent", 5572: "Multiplication is only defined where the target domain satisfies the descent constraint",
    5721: "admissibility is preserved under iterated composition", 6021: "The Nesting Operator",
    6038: "admissibility is closed under composition", 6040: "commutativity is not", 8454: "7 Drives × 4 Registers = 28 SubFoundations",
}


def pin_book():
    """The canon book lives in the main checkout (the lab worktree is sparse). Pin it by LF hash and check every quoted phrase."""
    for root in [REPO] + list(REPO.parents):
        path = root / BOOK
        if path.is_file():
            data = canonical_bytes(path)
            lines = data.decode("utf-8").split(chr(10))
            for number, phrase in BOOK_QUOTES.items():
                if phrase not in lines[number - 1]:
                    raise SystemExit("CONTRACT_REFUSED:BOOK_QUOTE_NOT_ON_ITS_LINE:%d:%s" % (number, phrase))
            ENVIRONMENT["book_found_at_build"] = True
            return {"path": BOOK, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "hash_policy": "lf-normalised",
                    "quoted_lines": {str(n): p for n, p in sorted(BOOK_QUOTES.items())}}
    raise SystemExit("CONTRACT_REFUSED:CANON_BOOK_NOT_FOUND:%s -- build from a checkout that holds the book" % BOOK)


def build():
    ops = {}

    ops["involute"] = {
        "id": "cas.op.involute/1.0", "arity": "unary",
        "authoritative_definition": "project instructions, 'Structural invariants': involution pairs ^2<->^3, ^5<->^6, ^8<->^9; self-duals ^0, ^1, ^4, ^7 (the engine spells the ten CO-0 .. CO-9)",
        "pinned_implementation": pin(ENGINE_REL + "/ontology/operators.rs"),
        "implementation_locator": "impl CognitiveOperator :: fn involute(self) -> Self",
        "input_types": {"noetic": "int in 0..9"}, "output_type": "int in 0..9",
        "valid_domain": "every noetic 0..9", "invalid_input": "INVALID_INPUT for anything else",
        "mutation_policy": "pure", "numerical_policy": "exact integer",
        "algebraic_properties": ["self-inverse: involute(involute(x)) == x", "fixed points exactly {0,1,4,7}"],
        "expected_cases": [{"in": [2], "out": 3}, {"in": [3], "out": 2}, {"in": [5], "out": 6}, {"in": [6], "out": 5},
                           {"in": [8], "out": 9}, {"in": [9], "out": 8}, {"in": [0], "out": 0}, {"in": [1], "out": 1},
                           {"in": [4], "out": 4}, {"in": [7], "out": 7}],
        "invalid_cases": [[10], [-1], ["2"], [None]],
        "role_in_the_lab": "a fixed operator the model must NOT learn; used as a conformance check on any learned unary module",
    }

    ops["compose"] = {
        "id": "cas.op.compose/1.0", "arity": "binary",
        "authoritative_definition": ("operators.rs doc comment, quoted: 'Monoid composition. CO-0 is the identity element. ... composition maps "
                                     "(CO-a, CO-b) -> CO-((a+b) mod 10)' -- CO-k is the engine's spelling of ^k. The canon book defines the SAME rule as its "
                                     "Monoid Composition `x`: '^a x ^b = ^((a+b) mod 10)' (lines 1727, 1729, 5572), with a domain rule the engine lacks (DR-7)"),
        "pinned_implementation": pin(ENGINE_REL + "/ontology/operators.rs"),
        "corroborating_implementation": pin(NATIVE_REL + "/model/composition.py"),
        "implementation_locator": "impl CognitiveOperator :: fn compose(self, other) ; cas-native COMPOSE_TABLE[i][j] = (i + j) % 10",
        "input_types": {"a": "int in 0..9", "b": "int in 0..9"}, "output_type": "int in 0..9",
        "valid_domain": "all 100 ordered pairs", "invalid_input": "INVALID_INPUT for anything else",
        "mutation_policy": "pure", "numerical_policy": "exact integer",
        "algebraic_properties": ["identity: compose(0, k) == k", "COMMUTATIVE", "ASSOCIATIVE",
                                 "every element invertible: compose(k, (10-k)%10) == 0 -- this is a GROUP (Z/10), not merely a monoid"],
        "WARNING": ("Commutative and associative. A modular sum solves any nested repetition WITHOUT preserving grouping or "
                    "operand order, so success here is NOT evidence of order-sensitive expression reasoning (directive s9). "
                    "Use as a conformance test and as a strong baseline only."),
        "NOT_A_STATEMENT_ABOUT_ADMISSIBILITY": ("compose is arithmetic on operator indices only. It implies NOTHING about whether the collapsed "
                                                "operator is admissible between the first source and the last target: see "
                                                "is_admissible.witnesses.no_composition_law. It is the book's `x`, NOT the book's Nesting Operator "
                                                "(Definition 26.1), which is not commutative and which the engine does not implement (DR-7)."),
        "expected_cases": [{"in": [0, 7], "out": 7}, {"in": [7, 0], "out": 7}, {"in": [3, 4], "out": 7}, {"in": [7, 5], "out": 2},
                           {"in": [9, 9], "out": 8}, {"in": [5, 5], "out": 0}, {"in": [1, 9], "out": 0}, {"in": [6, 8], "out": 4}],
        "invalid_cases": [[10, 0], [0, -1], [2.0, 3], ["1", 1]],
        "role_in_the_lab": "fixed; conformance and baseline",
    }

    ops["is_admissible"] = {
        "id": "cas.op.is_admissible/1.0", "arity": "ternary",
        "authoritative_definition": "project instructions, CORRECTION 1: each operator ^k has an admissibility relation D_k over states; D_0 is the diagonal only",
        "pinned_implementation": pin(ENGINE_REL + "/ontology/operators.rs"),
        "implementation_locator": "impl CognitiveOperator :: fn is_admissible(self, source: CognitiveStateId, target: CognitiveStateId) -> bool",
        "semantics_as_read_from_code": ["^0: source == target", "^k (k != 0): true if source.domain == target.domain",
                                        "^k (k != 0), different domains: true iff target.operator == k"],
        "input_types": {"operator": "int in 0..9", "source": "(domain in P/C/E/O, noetic in 0..9)", "target": "same"},
        "output_type": "bool", "valid_domain": "all 10 x 40 x 40 = 16,000 triples",
        "invalid_input": "INVALID_INPUT for anything else", "mutation_policy": "pure", "numerical_policy": "exact boolean",
        "algebraic_properties": ["NOT symmetric in (source, target) in general", "depends on operator, both domains and the target noetic",
                                 "for ^0 exactly 40 of 1,600 pairs are admissible", "for ^k (k != 0): 400 intra-domain pairs + cross-domain pairs whose target noetic == k",
                                 "has NO domain-order term: ^9 from ^0^P to ^9^O is admissible in one step, and cross-domain moves go upward as readily as downward (DR-5, witnesses.cross_domain_moves)"],
        "expected_cases": [
            {"in": [0, ["P", 3], ["P", 3]], "out": True}, {"in": [0, ["P", 3], ["P", 4]], "out": False},
            {"in": [0, ["P", 3], ["C", 3]], "out": False},
            {"in": [2, ["P", 3], ["P", 4]], "out": True}, {"in": [2, ["P", 3], ["C", 2]], "out": True},
            {"in": [2, ["P", 3], ["C", 5]], "out": False}, {"in": [2, ["C", 2], ["P", 3]], "out": False},
            {"in": [9, ["O", 1], ["P", 9]], "out": True}, {"in": [9, ["O", 1], ["P", 1]], "out": False},
            {"in": [9, ["O", 1], ["O", 1]], "out": True}, {"in": [7, ["E", 7], ["O", 7]], "out": True},
            {"in": [7, ["E", 7], ["O", 6]], "out": False},
            {"in": [9, ["P", 0], ["O", 9]], "out": True, "reading": "the book says this single step is impossible; the engine allows it (DR-5)"},
            {"in": [2, ["P", 1], ["P", 3]], "out": True}, {"in": [8, ["P", 3], ["P", 2]], "out": True},
            {"in": [0, ["P", 1], ["P", 2]], "out": False, "reading": "^2 then ^8 are each admissible, compose(2,8) = 0, and ^0 from P1 to P2 is not"}],
        "invalid_cases": [[10, ["P", 0], ["P", 0]], [1, ["X", 0], ["P", 0]], [1, ["P", 10], ["P", 0]], [1, "P0", ["P", 0]]],
        "role_in_the_lab": "THE order-sensitive operation: source and target are not interchangeable and the answer depends on context",
    }

    ops["domain_descent_mask"] = {
        "id": "cas.op.domain_descent_mask/1.0", "arity": "nullary (a constant 40x40 relation)",
        "authoritative_definition": "project instructions: domain descent P -> C -> E -> O; cas-native build_domain_descent_mask: rows of domain d attend to columns of domains <= d",
        "pinned_implementation": pin(NATIVE_REL + "/model/domain_descent.py"),
        "implementation_locator": "def build_domain_descent_mask(num_states=40): mask[0:10,0:10]; mask[10:20,0:20]; mask[20:30,0:30]; mask[30:40,0:40]",
        "input_types": {}, "output_type": "40x40 bool, indexed DOMAIN-MAJOR (P0=0 .. O9=39)",
        "valid_domain": "n/a", "invalid_input": "n/a", "mutation_policy": "pure constant", "numerical_policy": "exact boolean",
        "algebraic_properties": ["reflexive", "transitive", "NOT symmetric", "exactly 1,000 true cells: 100 + 200 + 300 + 400"],
        "expected_cases": [
            {"in": [["P", 3], ["C", 1]], "out": False, "reading": "P may not attend to C"},
            {"in": [["C", 1], ["P", 3]], "out": True, "reading": "C may attend to P"},
            {"in": [["O", 9], ["E", 5]], "out": True}, {"in": [["E", 0], ["O", 0]], "out": False},
            {"in": [["P", 0], ["P", 9]], "out": True}, {"in": [["O", 0], ["O", 9]], "out": True}],
        "invalid_cases": [],
        "role_in_the_lab": "fixed structural constraint; a learned module must not be able to violate it",
    }

    ops["rpm_embed_realize"] = {
        "id": "cas.op.rpm_embed_realize/1.0", "arity": "unary pair",
        "authoritative_definition": "project instructions, CORRECTION 2: RPM is a section-retraction, NOT an adjunction: eps o eta = id, but eta o eps != id",
        "pinned_implementation": pin(ENGINE_REL + "/rpm/mod.rs"),
        "implementation_locator": "pub fn embed(score: f64) -> (s, s*s, sqrt s) ; pub fn realize(&EmbeddedScore) -> components[0] ; verify_section_law tolerance f64::EPSILON * 2.0",
        "input_types": {"score": "float in [0, 1], not NaN"}, "output_type": "embed: (float, float, float); realize: float",
        "valid_domain": "[0.0, 1.0]", "invalid_input": "INVALID_INPUT (engine: ScoreOutOfRange) for NaN or outside [0, 1]",
        "mutation_policy": "pure",
        "numerical_policy": ("floating point. embed and realize are exact operations; the SECTION LAW is asserted at "
                             "|realize(embed(s)) - s| <= 2 * f64::EPSILON = 4.440892098500626e-16, exactly the engine's tolerance. "
                             "This is the only admitted operation with a tolerance, and the tolerance is the engine's, not the lab's."),
        "algebraic_properties": ["section law eps o eta = id on [0,1]", "retraction FAILS in general: eta(eps(e)) != e -- asserted, not tolerated",
                                 "one-directional: prerequisite satisfaction is cached, never re-derived by round trip"],
        "WHAT_THE_SECTION_LAW_DOES_NOT_SHOW": ("realize returns the first coordinate of (s, s*s, sqrt s), so the section law holds by construction. "
                                               "It is a regression test for exact recovery. It is not evidence that a learned encoder found a meaningful representation."),
        "KNOWN_LIMIT_OF_THE_FROZEN_ENGINE": ("rpm/mod.rs RpmState and ontology/states.rs CognitiveStateVector derive serde Deserialize without re-running their "
                                             "constructors' checks, and CognitiveStateVector's PartialEq zips without a length check. Nothing in the repository loads "
                                             "those types from outside data today. A `satisfied` flag or a state vector is trustworthy only when built through the constructor."),
        "expected_cases": [{"in": [0.25], "embed": [0.25, 0.0625, 0.5], "realize": 0.25},
                           {"in": [0.0], "embed": [0.0, 0.0, 0.0], "realize": 0.0},
                           {"in": [1.0], "embed": [1.0, 1.0, 1.0], "realize": 1.0},
                           {"in": [0.5625], "embed": [0.5625, 0.31640625, 0.75], "realize": 0.5625}],   # every value exact in binary; embed outputs are compared with ==
        "retraction_failure_cases": [{"embedded": [0.5, 0.9, 0.1], "reason": "components inconsistent; re-embedding 0.5 gives (0.5, 0.25, 0.7071...)"}],
        "invalid_cases": [[1.5], [-0.1], ["nan"], [None], [True]],
        "NOTE_NOT_THE_SAME_AS": ("cas-native/model/rpm_gate.py PrerequisiteGateLayer, whose docstring says 'the section law epsilon o eta = id "
                                 "is not hard-constrained'. That layer is a TRAINABLE mechanism and is NOT an admitted operation (directive s7). "
                                 "Recorded as discrepancy DR-2."),
        "role_in_the_lab": "fixed; the one op with a numerical policy; the retraction-failure direction is a required negative case",
    }

    coordinates = {
        "lab_internal_convention": "DOMAIN-MAJOR: index = 10 * domain + noetic, domain order P=0, C=1, E=2, O=3; P0=0 ... O9=39",
        "authority": [(ENGINE_REL + "/ontology/states.rs") + " :: fn linear_index", "api/notation/compiler.py :: _state_index (same formula)"],
        "engine_index_pin": pin(ENGINE_REL + "/ontology/states.rs"),
        "tokenizer_convention": "NOETIC-MAJOR: id = 213 + 4 * noetic + domain, ^0^P=213 ... ^9^O=252 -- verified for all 40 on 2026-09-21, and again by an outside reviewer's script",
        "tokenizer_pin": pin(TOKENIZER_REL),
        "explicit_map_engine_index_to_tokenizer_id": {str(10 * d + n): 213 + 4 * n + d for d in range(4) for n in range(10)},
        "what_the_canon_books_do": ("Thinking in Cognitive Architecture lists the 40 Noetic-first in Appendix A and Domain-first in Appendix J; CAS PCBA Engineer "
                                    "lists Domain-first. All agree on the Domain order P, C, E, O and that ^0 is Idea. Listing order is presentation, not meaning."),
        "rule": "these are two orderings of the SAME 40 Elements; the lab converts with this map and never renumbers either source, and never passes a raw index between them",
    }

    namespaces_28 = {
        "rule": ("OWNER RULING 2026-09-21 (OD-3): the canonical 28 is '28 Foundations 1.0' -- scheme C below. When the lab needs a 28-way Foundation "
                 "coordinate it uses foundations28.py (symbols 1a..7d, numbered 1..28 as the document numbers them, definitions verbatim). The other "
                 "two grids stay named and separate; conversions are explicit or absent."),
        "canonical": "C_tks_foundation_x_world_aspect", "lab_module": "research/helm_cas_expression_lab/foundations28.py",
        "A_drive_x_domain": {"definition": "7 Drives x 4 Domains, display F{n}-{D}", "authority": "cas-engine/src/ontology/drives.rs :: DomainDrive::linear_index = drive*4 + domain; project instructions; the book, line 1142 ('28 Domain-Specific Drives')",
                             "relation_to_canon": "a DIFFERENT grid: Domains (P, C, E, O) are not Worlds or Registers"},
        "B_drive_x_register": {"definition": "7 Drives x 4 Registers, display F{n}|{R}", "authority": "docs/reference/tks_28_foundations_translation_key.md; cas-native/belief/tks28_foundations.py; the book, line 8454 ('7 Drives x 4 Registers = 28 SubFoundations')",
                               "relation_to_canon": "the POSITION-BY-POSITION mirror of C ('3b' <-> 'F3|A'); positions only -- a CAS drive label is never the meaning of a Foundation"},
        "C_tks_foundation_x_world_aspect": {"definition": "7 Foundations x 4 Worlds (a=Spiritual b=Mental c=Emotional d=Physical), own symbol namespace 1a..7d",
                                            "authority": "28 Foundations 1.0 (owner-supplied PDF, sha256 2c27443f447bd69901372edb1316be56a92490afc6f88055ce0c84ce7a871017)"},
        "label_policy": "every label carries {ontology_version, namespace, definition}; conversions are explicit or absent",
    }

    discrepancies = [
        {"id": "DR-1", "between": ["cas-native/model/domain_descent.py build_domain_descent_mask (domain-major 40 slots)",
                                    "cas_hybrid_tokenizer_v2 compound-state ids (Noetic-major, 213-252)"],
         "issue": "the mask hard-codes domain-major blocks; the tokenizer orders the same 40 states Noetic-major. Any model that feeds tokenizer ids into a mask-indexed slot without the explicit map above is silently wrong.",
         "resolution_in_this_lab": "domain-major inside; the explicit map is frozen in this contract and round-tripped by the test.",
         "status": "OPEN for CAS-Native itself: which order CognitiveStateEmbedding's 40 outputs use has NOT been verified here."},
        {"id": "DR-2", "between": ["cas-engine/src/rpm/mod.rs embed/realize (exact, section law enforced)",
                                    "cas-native/model/rpm_gate.py PrerequisiteGateLayer (trainable; 'section law not hard-constrained')"],
         "issue": "same name, different objects: one is an exact operation, the other a learned gate.",
         "resolution_in_this_lab": "only the engine pair is admitted as an operation; the layer is a mechanism and may be a learned MODULE later, never an oracle.",
         "status": "RESOLVED for this contract"},
        {"id": "DR-3", "between": ["operators.rs doc comment 'Monoid composition'", "the code (a+b) mod 10"],
         "issue": "(a+b) mod 10 is a GROUP (every element invertible), which is stronger than the comment claims. Not a bug; recorded so nobody 'fixes' the comment into the code.",
         "status": "RECORDED"},
        {"id": "DR-4", "between": ["the three 28-way namespaces"], "issue": "see namespaces_28",
         "status": "RESOLVED by owner ruling OD-3, 2026-09-21: the canonical 28 is 28 Foundations 1.0"},
        {"id": "DR-5", "between": [BOOK + " lines 5548-5550: one cannot go from ^0^P directly to ^9^O in a single step without passing through the intermediate domains; 'the admissibility structure enforces this descent'",
                                    "operators.rs is_admissible: ^9 from ^0^P to ^9^O is admissible (the target's Noetic equals the operator)"],
         "issue": ("is_admissible has no domain-order term: see witnesses.cross_domain_moves (one-step descents, descents that skip a domain, and upward moves). "
                   "domain_descent_mask is CAS-Native code, not the engine, and enforces DIRECTION only -- O may attend P in one hop. "
                   "The book's 'no single step across intermediate domains' is enforced by NO pinned source."),
         "status": "FLAG_FOR_HUMAN_REVIEW; owner decision OD-6: the first experiment stays on the engine code's rules; a book-faithful rule is a separate task"},
        {"id": "DR-6", "between": [BOOK + " lines 6038 and 5721: composable admissible morphisms compose to a morphism of Noetica ('admissibility is closed under composition')",
                                    "measured on the engine rule, read FAIRLY as 'some operator is admissible from the first source to the last target': witnesses.fair_closure"],
         "issue": ("the fair reading fails for a SMALL share of chains, every one ending at a cross-domain state whose Noetic is ^0 (only ^0 could reach it, and ^0 admits the diagonal only). "
                   "The much larger count in witnesses.no_composition_law is about collapsing with the index-sum operator -- a fact about the engine's two functions, NOT a claim the book makes. "
                   "Contract 0.2 presented that larger count as the book-vs-engine conflict; that was an overstatement and is withdrawn."),
         "status": "FLAG_FOR_HUMAN_REVIEW; OD-6 as above"},
        {"id": "DR-7", "between": [BOOK + " defines TWO operations: `x` Monoid Composition (lines 1727, 1729, 2782, 5572) and the Nesting Operator of the Fractal Monoid (Definition 26.1, lines 6019-6040)",
                                    "operators.rs compose: (a + b) mod 10 on operator indices only"],
         "issue": ("compose AGREES with the book's `x` on the Noetic index. Two real gaps: (1) the book's `x` also fixes the result's domain (min(Domain-x, Domain-y)) and requires same-domain or "
                   "valid descent -- the engine's compose takes no domains; (2) the Nesting Operator, which the book proves non-commutative (line 6040), has NO engine counterpart. "
                   "Contract 0.2 set line 6040 against compose as if they were the same operation; that was wrong and is withdrawn."),
         "status": "agreement RECORDED for `x` on the index; FLAG_FOR_HUMAN_REVIEW for the two gaps; OD-6 as above"},
        {"id": "DR-8", "between": [BOOK + " line 1142: '28 Domain-Specific Drives' (7 Drives x 4 Domains)", BOOK + " line 8454: '7 Drives x 4 Registers = 28 SubFoundations'"],
         "issue": "the canon book uses '28' for two different grids.", "status": "RECORDED; the owner's ruling OD-3 matches the second; see namespaces_28"},
    ]

    sys.path.insert(0, str(HERE))
    import reference_ops as _ref

    contract = {
        "schema": CONTRACT_VERSION, "built": "2026-09-21", "hash_policy": HASH_POLICY, "builder": pathlib.Path(__file__).name, "pinned_sources_manifest": "pinned_sources/PINNED_SOURCES.json",
        "canon": {"owner_ruling": "OD-2, 2026-09-21: three books are canonical for CAS; Noetics are written ^0 .. ^9",
                  "books": {"Thinking in Cognitive Architecture": BOOK, "CAS PCBA Engineer": "book/CAS_PCBA_Engineer/*.md", "Reality Engineering": "book/superiority_of_tks/MANUSCRIPT.md (built from SOURCE_ORIGINAL.md)"},
                  "canonical_28": "28 Foundations 1.0 -- foundations28.py", "owner_decisions_record": "OWNER_DECISIONS_20260921.json",
                  "book_pin": pin_book()},
        "scope": ("Nothing in CAS is excluded from Helm's expression space (owner ruling OD-4): the 40 Elements, the 28 Foundations, Registers, operators, recipes "
                  "and every expression built from them. THIS file freezes only the first five OPERATIONS a learned module may be trained against."),
        "reference_module": {"path": (HERE / "reference_ops.py").relative_to(REPO).as_posix(), **_hash(HERE / "reference_ops.py", "reference_ops.py")},
        "reference_learner_separation": ("reference_ops.py is the EVALUATOR's oracle. A learned arm receives operands and an operation ID, never "
                                         "reference outputs, answer-derived masks, or a solver callback. An arm that calls the reference is "
                                         "HYBRID_FIXED_OPERATOR and is labelled so. Enforced by test_operation_contracts.py (import scan)."),
        "outcome_vocabulary": ["CORRECT", "WRONG", "INVALID_INPUT", "UNSUPPORTED_OPERATION", "NUMERICAL_FAILURE", "BUDGET_EXHAUSTED"],
        "equality_policy": {"symbolic_or_boolean": "exact", "typed_record": "structural", "continuous": "only rpm_embed_realize, at the engine's own tolerance"},
        "operations": ops, "coordinates": coordinates, "namespaces_28": namespaces_28, "discrepancies": discrepancies,
        "admitted_for_learning_pilot": {"order_sensitive_target": "is_admissible", "conformance_only": ["compose", "involute"],
                                        "structural_constraint": "domain_descent_mask", "numerical": "rpm_embed_realize",
                                        "targets_are": "the ENGINE CODE's rules as pinned (owner decision OD-6); results on them are labelled 'matches the code', never discovery"},
        "not_admitted": ["Decomposition", "Comparison", "Candidate routing", "any CCDL board operation -- no parser on disk, 17 of 39 statement leaders have no semantics",
                         "OmegaRegistry (a registry is not an operation)", "RegisterFiLM (parameterised; a mechanism, not an oracle)",
                         "any rule of the form 'two admissible steps imply an admissible collapsed step' -- measured false, see no_composition_law"],
    }
    # ---- WITNESSES: asymmetry, context-sensitivity and the missing composition law are MEASURED, not inferred from a name.
    states = [(d, n) for d in _ref.DOMAINS for n in range(10)]
    asym = [(k, s, t) for k in range(10) for s in states for t in states
            if _ref.is_admissible(k, s, t) != _ref.is_admissible(k, t, s)]
    ctx = [(s, t) for s in states for t in states if len({_ref.is_admissible(k, s, t) for k in range(10)}) > 1]
    admissible_total = sum(1 for k in range(10) for s in states for t in states if _ref.is_admissible(k, s, t))
    chains, broken = measure_no_composition_law(_ref)
    ops["is_admissible"]["witnesses"] = {
        "admissible_triples": admissible_total, "asymmetric_triples": len(asym), "of_triples": 16000,
        "asymmetric_triples_reading": "ordered triples where f(k,s,t) != f(k,t,s); each unordered pair is counted in both directions, so %d pairs" % (len(asym) // 2),
        "fair_closure": measure_fair_closure(_ref), "cross_domain_moves": measure_cross_domain_moves(_ref),
        "always_inadmissible_accuracy_on_the_full_uniform_grid": (16000 - admissible_total) / 16000,
        "example_asymmetric": {"triple": list(asym[0][:1]) + [list(asym[0][1]), list(asym[0][2])],
                               "f(k,s,t)": _ref.is_admissible(*asym[0]), "f(k,t,s)": _ref.is_admissible(asym[0][0], asym[0][2], asym[0][1])},
        "context_sensitive_pairs": len(ctx), "of_pairs": 1600,
        "note": "a (source, target) pair is context-sensitive when the answer depends on WHICH operator is applied",
        "no_composition_law": {
            "admissible_two_step_chains": chains, "collapsed_operator_not_admissible": broken,
            "example": {"first": [2, ["P", 1], ["P", 3]], "second": [8, ["P", 3], ["P", 2]], "compose": _ref.compose(2, 8),
                        "collapsed": [0, ["P", 1], ["P", 2]], "collapsed_admissible": _ref.is_admissible(0, ("P", 1), ("P", 2))},
            "reading": ("two admissible steps do NOT make the INDEX-SUM-collapsed operator admissible. A fact about the engine's compose and is_admissible together; the code promises no such law "
                        "and the book does not claim it (the book's claim, read fairly, is witnesses.fair_closure). A generator or a learner that assumes it is wrong.")},
    }
    mask = _ref.domain_descent_mask()
    ops["domain_descent_mask"]["witnesses"] = {"asymmetric_cells": sum(1 for i in range(40) for j in range(40) if mask[i][j] != mask[j][i]), "of_cells": 1600}
    ops["compose"]["witnesses"] = {"asymmetric_pairs": sum(1 for a in range(10) for b in range(10) if _ref.compose(a, b) != _ref.compose(b, a)), "of_pairs": 100,
                                   "note": "zero: compose is commutative, which is why it is conformance-only"}

    # ---- PACKAGE-SCHEMA EXPORT: one file per operation conforming to the delivered
    # `_handoffs/FABLE_HELM_CAS_v1/schemas/operation_contract.schema.json`, so the package's own tests can read it.
    schema_path = PACKAGE / "_handoffs/FABLE_HELM_CAS_v1/schemas/operation_contract.schema.json"
    export_dir = HERE / "contracts_package_schema"
    export_dir.mkdir(exist_ok=True)
    io_types = {
        "involute": ({"noetic": "int 0..9"}, {"noetic": "int 0..9"}),
        "compose": ({"a": "int 0..9", "b": "int 0..9"}, {"noetic": "int 0..9"}),
        "is_admissible": ({"operator": "int 0..9", "source": "[domain P|C|E|O, noetic 0..9]", "target": "[domain, noetic]"}, {"admissible": "bool"}),
        "domain_descent_mask": ({}, {"mask": "40x40 bool, domain-major"}),
        "rpm_embed_realize": ({"score": "float in [0,1]"}, {"embed": "[float, float, float]", "realize": "float"}),
    }
    exports = {}
    for name, op in ops.items():
        exp = {
            "schema_version": "fable.operation-contract/1.0", "operation_id": op["id"], "semantics_version": "cas-v7.7 / engine as pinned",
            "reference": {"source_path": op["pinned_implementation"]["path"], "source_sha256": op["pinned_implementation"]["sha256"],
                          "symbol": op["implementation_locator"], "semantic_source": op["authoritative_definition"],
                          "independent_test_reference": "research/helm_cas_expression_lab/test_operation_contracts.py"},
            "input_schema": io_types[name][0], "output_schema": io_types[name][1], "valid_domain": op["valid_domain"],
            "error_cases": [{"condition": "input outside valid_domain (wrong type, range, key set)", "typed_result": "INVALID_INPUT"}]
                           + ([{"condition": "eta(eps(e)) != e for a non-image e", "typed_result": "RETRACTION_FAILURE_EXPECTED"}] if name == "rpm_embed_realize" else []),
            "stateful": False, "parameter_policy": "NONE",   # schema enum: NONE | FIXED_VERSIONED_PARAMETERS | FROZEN_MEASURED_TRANSFORM | UNRESOLVED_EXCLUDE
            "comparison": {"mode": "DECLARED_NUMERIC_TOLERANCE" if name == "rpm_embed_realize" else "EXACT_TYPED",
                           "rule": op["numerical_policy"]},
            "allowed_for_neural_target": name in ("is_admissible", "compose", "involute"),
        }
        with open(export_dir / (name + ".json"), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(exp, indent=1, sort_keys=True))
        exports[name] = "contracts_package_schema/" + name + ".json"
    validation = {"schema": schema_path.relative_to(PACKAGE).as_posix() if schema_path.exists() else None, "validator": None, "results": {}}
    if schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            import jsonschema
        except ImportError:
            raise SystemExit("CONTRACT_REFUSED:VALIDATOR_MISSING: install jsonschema -- the package-schema export is not written unvalidated")
        for name in ops:
            doc = json.loads((export_dir / (name + ".json")).read_text(encoding="utf-8"))
            try:
                jsonschema.validate(doc, schema)
                validation["results"][name] = "VALID"
            except jsonschema.ValidationError as error:
                validation["results"][name] = "INVALID: " + error.message[:160]
        validation["validator"] = "jsonschema"
        ENVIRONMENT["validator_version"] = "jsonschema " + __import__("importlib.metadata").metadata.version("jsonschema")
    contract["package_schema_export"] = {"files": exports, "validation": validation}

    # the digest covers everything EXCEPT `environment`, so the same sources give the same digest on any machine
    body = json.dumps(contract, indent=1, sort_keys=True)
    contract["contract_digest"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    contract["environment"] = ENVIRONMENT
    with open(HERE / "OPERATION_CONTRACTS.json", "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(contract, indent=1, sort_keys=True))
    print("OPERATION_CONTRACTS.json written: %d operations, %d discrepancies, contract_digest %s"
          % (len(ops), len(discrepancies), contract["contract_digest"][:16]))
    print("  no_composition_law: %d admissible two-step chains, %d with a non-admissible collapsed operator" % (chains, broken))
    for name, op in ops.items():
        print("  %-22s %s  pinned %s @ %s" % (name, op["id"], op["pinned_implementation"]["path"], op["pinned_implementation"]["sha256"][:12]))
    return 0


if __name__ == "__main__":
    sys.exit(build())
