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

Also frozen here: the lab's coordinate convention (domain-major inside; the tokenizer's Noetic-major
ids mapped explicitly), the THREE 28-way namespaces kept apart, and a discrepancy ledger for every
place two sources disagree. Nothing in this file renumbers the engine or migrates historical data.

Usage:  python research/helm_cas_expression_lab/build_operation_contracts.py
Cost:   $0. Pure Python. Writes ONE file beside itself.
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
CONTRACT_VERSION = "helm-cas-expression-lab.operation-contracts/0.1"


HASH_POLICY = "sha256 over LF-normalised bytes (every CRLF -> LF) -- the bytes git stores, so the pin is the same on Windows and Linux"


def canonical_bytes(path):
    """LF-normalised bytes. Git stores LF; Windows checkouts read CRLF. A pin over raw bytes would hold on
    exactly one machine. This is the CRLF trap recorded in memory, closed at the hash."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def _hash(path):
    if not path.is_file():
        raise SystemExit("CONTRACT_REFUSED:PIN_SOURCE_MISSING:%s" % path)
    data = canonical_bytes(path)
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
      * if the origin is not on disk, that is recorded as `origin_on_disk: false`, not silently skipped.
    """
    manifest = json.loads((VENDORED / "PINNED_SOURCES.json").read_text(encoding="utf-8"))
    recorded = {row["origin"]: row for row in manifest["files"]}
    if rel not in recorded:
        raise SystemExit("CONTRACT_REFUSED:NOT_IN_PINNED_SOURCES_MANIFEST:%s" % rel)
    copy = _hash(VENDORED / rel)
    if copy["sha256"] != recorded[rel]["sha256"] or not recorded[rel]["copy_matches_origin"]:
        raise SystemExit("CONTRACT_REFUSED:VENDORED_COPY_DIVERGED_FROM_MANIFEST:%s" % rel)
    origin_path = REPO / rel
    origin_on_disk = origin_path.is_file()
    if origin_on_disk and _hash(origin_path)["sha256"] != copy["sha256"]:
        raise SystemExit("CONTRACT_REFUSED:ORIGIN_DIVERGED_FROM_VENDORED_COPY:%s" % rel)
    return {"path": rel, "vendored_path": "pinned_sources/" + rel, "origin_on_disk_at_build": origin_on_disk, **copy}


def build():
    ops = {}

    ops["involute"] = {
        "id": "cas.op.involute/1.0", "arity": "unary",
        "authoritative_definition": "CLAUDE.md: involution pairs CO-2<->CO-3, CO-5<->CO-6, CO-8<->CO-9; self-duals CO-0, CO-1, CO-4, CO-7",
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
        "authoritative_definition": "operators.rs doc comment: 'Monoid composition. CO-0 is the identity element. composition maps (CO-a, CO-b) -> CO-((a+b) mod 10)'",
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
        "expected_cases": [{"in": [0, 7], "out": 7}, {"in": [7, 0], "out": 7}, {"in": [3, 4], "out": 7}, {"in": [7, 5], "out": 2},
                           {"in": [9, 9], "out": 8}, {"in": [5, 5], "out": 0}, {"in": [1, 9], "out": 0}, {"in": [6, 8], "out": 4}],
        "invalid_cases": [[10, 0], [0, -1], [2.0, 3], ["1", 1]],
        "role_in_the_lab": "fixed; conformance and baseline",
    }

    ops["is_admissible"] = {
        "id": "cas.op.is_admissible/1.0", "arity": "ternary",
        "authoritative_definition": "CLAUDE.md CORRECTION 1: each CO-k has an admissibility relation D_k over states; D_0 is the diagonal only",
        "pinned_implementation": pin(ENGINE_REL + "/ontology/operators.rs"),
        "implementation_locator": "impl CognitiveOperator :: fn is_admissible(self, source: CognitiveStateId, target: CognitiveStateId) -> bool",
        "semantics_as_read_from_code": ["CO-0: source == target", "CO-k (k != 0): true if source.domain == target.domain",
                                        "CO-k (k != 0), different domains: true iff target.operator == k"],
        "input_types": {"operator": "int in 0..9", "source": "(domain in P/C/E/O, noetic in 0..9)", "target": "same"},
        "output_type": "bool", "valid_domain": "all 10 x 40 x 40 = 16,000 triples",
        "invalid_input": "INVALID_INPUT for anything else", "mutation_policy": "pure", "numerical_policy": "exact boolean",
        "algebraic_properties": ["NOT symmetric in (source, target) in general", "depends on operator, both domains and the target noetic",
                                 "for CO-0 exactly 40 of 1,600 pairs are admissible", "for CO-k (k != 0): 400 intra-domain pairs + cross-domain pairs whose target noetic == k"],
        "expected_cases": [
            {"in": [0, ["P", 3], ["P", 3]], "out": True}, {"in": [0, ["P", 3], ["P", 4]], "out": False},
            {"in": [0, ["P", 3], ["C", 3]], "out": False},
            {"in": [2, ["P", 3], ["P", 4]], "out": True}, {"in": [2, ["P", 3], ["C", 2]], "out": True},
            {"in": [2, ["P", 3], ["C", 5]], "out": False}, {"in": [2, ["C", 2], ["P", 3]], "out": False},
            {"in": [9, ["O", 1], ["P", 9]], "out": True}, {"in": [9, ["O", 1], ["P", 1]], "out": False},
            {"in": [9, ["O", 1], ["O", 1]], "out": True}, {"in": [7, ["E", 7], ["O", 7]], "out": True},
            {"in": [7, ["E", 7], ["O", 6]], "out": False}],
        "invalid_cases": [[10, ["P", 0], ["P", 0]], [1, ["X", 0], ["P", 0]], [1, ["P", 10], ["P", 0]], [1, "P0", ["P", 0]]],
        "role_in_the_lab": "THE order-sensitive operation: source and target are not interchangeable and the answer depends on context",
    }

    ops["domain_descent_mask"] = {
        "id": "cas.op.domain_descent_mask/1.0", "arity": "nullary (a constant 40x40 relation)",
        "authoritative_definition": "CLAUDE.md: domain descent P -> C -> E -> O; cas-native build_domain_descent_mask: rows of domain d attend to columns of domains <= d",
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
        "authoritative_definition": "CLAUDE.md CORRECTION 2: RPM is a section-retraction, NOT an adjunction: eps o eta = id, but eta o eps != id",
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
        "expected_cases": [{"in": [0.25], "embed": [0.25, 0.0625, 0.5], "realize": 0.25},
                           {"in": [0.0], "embed": [0.0, 0.0, 0.0], "realize": 0.0},
                           {"in": [1.0], "embed": [1.0, 1.0, 1.0], "realize": 1.0},
                           {"in": [0.81], "embed": [0.81, 0.6561, 0.9], "realize": 0.81}],
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
        "tokenizer_convention": "NOETIC-MAJOR: id = 213 + 4 * noetic + domain, ^0^P=213 ... ^9^O=252 -- verified for all 40 on 2026-09-21",
        "tokenizer_pin": pin(TOKENIZER_REL),
        "explicit_map_engine_index_to_tokenizer_id": {str(10 * d + n): 213 + 4 * n + d for d in range(4) for n in range(10)},
        "rule": "these are two coordinate systems for the SAME 40 objects; the lab converts with this map and never renumbers either source",
    }

    namespaces_28 = {
        "rule": "THREE distinct 28-way schemes exist in the repository. They are kept apart. No unified 28-way head is trained in this pilot; the 40-Element expression work does not depend on choosing one (directive s7).",
        "A_drive_x_domain": {"definition": "7 Drives x 4 Domains, display F{n}-{D}", "authority": "cas-engine/src/ontology/drives.rs :: DomainDrive::linear_index = drive*4 + domain; CLAUDE.md"},
        "B_drive_x_register": {"definition": "7 Drives x 4 Registers, display F{n}|{R}", "authority": "docs/reference/tks_28_foundations_translation_key.md; cas-native/belief/tks28_foundations.py"},
        "C_tks_foundation_x_world_aspect": {"definition": "7 Foundations x 4 World aspects (a=Spiritual b=Mental c=Emotional d=Physical), the TKS 28 Sub-Foundations, own symbol namespace", "authority": "28 Foundations 1.0 (canon, per memory); TKS clean-definitions manual"},
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
        {"id": "DR-4", "between": ["the three 28-way namespaces"], "issue": "see namespaces_28", "status": "QUARANTINED, owner decision pending, does not block the 40-Element work"},
    ]

    contract = {
        "schema": CONTRACT_VERSION, "built": "2026-09-21", "hash_policy": HASH_POLICY, "builder": pathlib.Path(__file__).name, "pinned_sources_manifest": "pinned_sources/PINNED_SOURCES.json",
        "reference_module": {"path": (HERE / "reference_ops.py").relative_to(REPO).as_posix(), **_hash(HERE / "reference_ops.py")},
        "reference_learner_separation": ("reference_ops.py is the EVALUATOR's oracle. A learned arm receives operands and an operation ID, never "
                                         "reference outputs, answer-derived masks, or a solver callback. An arm that calls the reference is "
                                         "HYBRID_FIXED_OPERATOR and is labelled so. Enforced by test_operation_contracts.py (import scan)."),
        "outcome_vocabulary": ["CORRECT", "WRONG", "INVALID_INPUT", "UNSUPPORTED_OPERATION", "NUMERICAL_FAILURE", "BUDGET_EXHAUSTED"],
        "equality_policy": {"symbolic_or_boolean": "exact", "typed_record": "structural", "continuous": "only rpm_embed_realize, at the engine's own tolerance"},
        "operations": ops, "coordinates": coordinates, "namespaces_28": namespaces_28, "discrepancies": discrepancies,
        "admitted_for_learning_pilot": {"order_sensitive_target": "is_admissible", "conformance_only": ["compose", "involute"],
                                        "structural_constraint": "domain_descent_mask", "numerical": "rpm_embed_realize"},
        "not_admitted": ["Decomposition", "Comparison", "Candidate routing", "any CCDL board operation -- no parser on disk, 17 of 39 statement leaders have no semantics",
                         "OmegaRegistry (a registry is not an operation)", "RegisterFiLM (parameterised; a mechanism, not an oracle)"],
    }
    body = json.dumps(contract, indent=1, sort_keys=True)
    contract["contract_digest"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    out = HERE / "OPERATION_CONTRACTS.json"
    out.write_text(json.dumps(contract, indent=1, sort_keys=True), encoding="utf-8")
    print("OPERATION_CONTRACTS.json written: %d operations, %d discrepancies, contract_digest %s"
          % (len(ops), len(discrepancies), contract["contract_digest"][:16]))
    for name, op in ops.items():
        print("  %-22s %s  pinned %s @ %s" % (name, op["id"], op["pinned_implementation"]["path"], op["pinned_implementation"]["sha256"][:12]))
    return 0


if __name__ == "__main__":
    sys.exit(build())
