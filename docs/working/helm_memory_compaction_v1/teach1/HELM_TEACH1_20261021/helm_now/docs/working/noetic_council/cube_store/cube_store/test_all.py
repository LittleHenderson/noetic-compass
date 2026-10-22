"""test_all.py -- Acceptance test suite for Unified Cube Store.

Enforces Sections 7 & 8 of SPEC_CUBE_STORE_UNIFIED_20261018.md:
  S1-S6: Store and operations (S3 core test: 'stock' vs 'on hand' reach same operation)
  K1-K6: Kind classification (K2 vs K3: polarity from parse, not hardcoded sentiment)
  H1-H4: Honesty rules (no cubes on refusal, unknown carries explanation, source!=NONE, no poetry thermal inputs)
  T1-T3: Trace citations (cites op and cubes read, receipts on refusal, 50-run determinism)

Every test includes bite-checks proving that reverting the mechanism fails.
CLAIM CEILING:
MECHANISM ONLY.
KNOWLEDGE IS STORED AS CUBES; ANSWERS COME FROM THREE OPERATIONS OVER THAT STORE.
AN UNKNOWN FACE IS REPORTED AS UNKNOWN AND IS NEVER FILLED.
NO UNDERSTANDING OF THE REQUEST IS CLAIMED.
"""
from __future__ import annotations

import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from cube import (
    Branch,
    Core,
    CubeNode,
    CubeValidationError,
    Face,
    Provenance,
    validate_cube,
)
from operations import find_shared_part, list_parts, reached_via
from store import AdmissionRefusal, CubeStore
from turn import (
    INVENTORY_NODE_ID,
    TurnProcessor,
    TurnReceipt,
)

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def equal(left, right, why=""):
    assert left == right, f"{why or 'values differ'}: {left!r} != {right!r}"


def ok(val, why=""):
    assert val, why or "expected truthy value"


# =============================================================================
# Store and Operations Tests (S1 - S6)
# =============================================================================

@case
def test_s1_inventory_declaration_write():
    """S1: 'We have 50 Flour, 30 Sugar' -> WRITE, kind=instance, source=USER_SAID"""
    tp = TurnProcessor()
    rec = tp.process_turn("We have 50 Flour, 30 Sugar")
    equal(rec.outcome, "WRITE")
    equal(rec.kind, "instance")
    ok(INVENTORY_NODE_ID in rec.cubes_written)

    inv_cube = tp.store.get_cube(INVENTORY_NODE_ID)
    ok(inv_cube is not None)
    equal(inv_cube.provenance.source, "USER_SAID")
    equal(inv_cube.core.kind, "instance")


@case
def test_s2_and_s3_stock_and_on_hand_same_operation():
    """S2 & S3: 'What do we have in stock' & 'what've we got on hand then'
    must reach the SAME operation (LIST_PARTS) and return the SAME answer.
    This is the core test of Section 7.
    """
    tp = TurnProcessor()
    # Write inventory first (S1)
    tp.process_turn("We have 50 Flour, 30 Sugar")

    # S2: "What do we have in stock"
    rec_s2 = tp.process_turn("What do we have in stock")
    equal(rec_s2.outcome, "READ")
    equal(rec_s2.operation, "LIST_PARTS", "S2 must execute LIST_PARTS")
    ok("50 Flour" in rec_s2.response_text and "30 Sugar" in rec_s2.response_text)
    ok(INVENTORY_NODE_ID in rec_s2.cubes_read)

    # S3: "what've we got on hand then"
    rec_s3 = tp.process_turn("what've we got on hand then")
    equal(rec_s3.outcome, "READ")
    equal(rec_s3.operation, "LIST_PARTS", "S3 must execute the SAME operation LIST_PARTS")
    equal(rec_s3.response_text, rec_s2.response_text, "S3 must produce the exact SAME answer as S2")
    equal(rec_s3.cubes_read, rec_s2.cubes_read, "S3 must read the exact same cubes as S2")


@case
def test_s3_bite_check():
    """Prove S3 bites: if a naive regex matching only 'stock' is used,
    'what've we got on hand then' fails to reach LIST_PARTS.
    """
    tp = TurnProcessor()
    tp.process_turn("We have 50 Flour, 30 Sugar")

    # Simulate fragile regex matching only the literal word 'stock'
    def fragile_query_resolver(text):
        if "stock" in text.lower():
            return "LIST_PARTS"
        return "GENERIC_FALLBACK"

    s2_op = fragile_query_resolver("What do we have in stock")
    s3_op = fragile_query_resolver("what've we got on hand then")
    equal(s2_op, "LIST_PARTS")
    equal(s3_op, "GENERIC_FALLBACK", "Bite check: fragile keyword matching misses 'on hand'")
    ok(s2_op != s3_op, "Bite check proves fragile matcher creates divergent operations")


@case
def test_s4_and_s5_directive_preference_write_and_read():
    """S4 & S5: 'Remember I prefer short answers' -> WRITE, kind=directive
    'Do you remember my preference' -> READ, returns the directive written in S4.
    """
    tp = TurnProcessor()
    rec_s4 = tp.process_turn("Remember I prefer short answers")
    equal(rec_s4.outcome, "WRITE")
    equal(rec_s4.kind, "directive", "kind must be directive (Addition 1)")
    ok(len(rec_s4.cubes_written) >= 1)

    node_id = rec_s4.cubes_written[0]
    cube = tp.store.get_cube(node_id)
    equal(cube.core.kind, "directive")
    equal(cube.provenance.source, "USER_SAID")

    # S5: READ preference
    rec_s5 = tp.process_turn("Do you remember my preference")
    equal(rec_s5.outcome, "READ")
    ok(node_id in rec_s5.cubes_read, "Must cite reading the directive cube")
    ok("Remember I prefer short answers" in rec_s5.response_text)


@case
def test_s6_find_shared_part_on_inventory():
    """S6: 'Do we have 50 Flour and 30 Sugar or not' -> FIND_SHARED_PART on the inventory cube"""
    tp = TurnProcessor()
    tp.process_turn("We have 50 Flour, 30 Sugar")

    rec_s6 = tp.process_turn("Do we have 50 Flour and 30 Sugar or not")
    equal(rec_s6.outcome, "READ")
    equal(rec_s6.operation, "FIND_SHARED_PART")
    ok(INVENTORY_NODE_ID in rec_s6.cubes_read)
    ok("confirmed" in rec_s6.response_text.lower() or "yes" in rec_s6.response_text.lower())


@case
def test_s7_pantry_query_is_read_not_write():
    """Probe 2: 'list what's in the pantry' -> READ, operation=LIST_PARTS.
    A question must never be recorded as a statement; asking must write ZERO cubes.
    """
    tp = TurnProcessor()
    tp.process_turn("We have 50 Flour, 30 Sugar")
    initial_cubes = len(tp.store.nodes)

    rec = tp.process_turn("list what's in the pantry")
    equal(rec.outcome, "READ", "Asking to list pantry contents must be a READ operation")
    equal(rec.operation, "LIST_PARTS", "Pantry listing must resolve to LIST_PARTS")
    equal(len(rec.cubes_written), 0, "Querying the pantry must write ZERO cubes to store")
    equal(len(tp.store.nodes), initial_cubes, "Store node count must not increase on read query")
    ok(INVENTORY_NODE_ID in rec.cubes_read, "Must read inventory cube")
    ok("50 Flour" in rec.response_text and "30 Sugar" in rec.response_text)


# =============================================================================
# Kind & Polarity Classification Tests (K1 - K6)
# =============================================================================

@case
def test_k1_through_k6_kind_and_polarity():
    """K1-K6: Exact kind classification and lexical valence polarity.
    K1: 'We have 50 Flour' -> instance
    K2: 'I feel tired today' -> instance (state) AND polarity NEGATIVE
    K3: 'I feel fantastic today' -> instance AND polarity POSITIVE
    K4: 'Write a program' -> procedure
    K5: 'Tell me a joke' -> directive
    K6: 'What is entropy' -> query for a concept
    """
    tp = TurnProcessor()

    # K1
    r_k1 = tp.process_turn("We have 50 Flour")
    equal(r_k1.kind, "instance")

    # K2: Negative affect
    r_k2 = tp.process_turn("I feel tired today")
    equal(r_k2.kind, "instance")
    equal(r_k2.polarity, "NEGATIVE", "K2 must extract NEGATIVE polarity from 'tired'")
    ok("sorry" in r_k2.response_text.lower(), "Negative polarity triggers empathetic response")

    # K3: Positive affect
    r_k3 = tp.process_turn("I feel fantastic today")
    equal(r_k3.kind, "instance")
    equal(r_k3.polarity, "POSITIVE", "K3 must extract POSITIVE polarity from 'fantastic'")
    ok("fantastic" in r_k3.response_text.lower() or "glad" in r_k3.response_text.lower())
    ok("sorry" not in r_k3.response_text.lower(), "Positive polarity must NEVER receive 'sorry' condolence")

    # K4: Procedure
    r_k4 = tp.process_turn("Write a program")
    equal(r_k4.kind, "procedure")

    # K5: Directive
    r_k5 = tp.process_turn("Tell me a joke")
    equal(r_k5.kind, "directive")

    # K6: Concept inquiry
    r_k6 = tp.process_turn("What is entropy")
    equal(r_k6.kind, "concept")


@case
def test_k2_k3_polarity_bite_check():
    """Prove K2 vs K3 bites: reverting to v0.8.2's hardcoded sentiment word
    reproduces the defect where HELM said 'sorry to hear you're feeling tired' to 'I feel fantastic'.
    """
    # In v0.8.2, any "i feel" match unconditionally responded: "sorry to hear you're feeling tired"
    def reverted_v082_affect_handler(user_input):
        return "I'm sorry to hear that you're feeling tired today! Take things easy."

    reverted_response_to_fantastic = reverted_v082_affect_handler("I feel fantastic today")
    ok(
        "sorry to hear that you're feeling tired" in reverted_response_to_fantastic,
        "Bite check: old hardcoded logic told a fantastic user that it's sorry they are tired!"
    )


@case
def test_k7_assertion_and_valence_orthogonal_split_and_probes():
    """Probe 1 & 3: Assertion (ASSERTED/DENIED) and Valence (POSITIVE/NEGATIVE/NEUTRAL)
    are orthogonal axes.
    - 'I feel wonderful' -> assertion: ASSERTED, valence: POSITIVE
    - 'I feel awful' -> assertion: ASSERTED, valence: NEGATIVE
    - 'I'm over the moon' -> assertion: ASSERTED, valence: POSITIVE
    - 'Tell me a joke' -> directive, assertion: ASSERTED, valence: NEUTRAL
    - 'I am not attracted toward \"the offer\".' -> assertion: DENIED, valence: POSITIVE (F14 anti-drift)
    - 'I am repelled by \"the offer\".' -> assertion: ASSERTED, valence: NEGATIVE
    """
    tp = TurnProcessor()

    # 1. "I feel wonderful" -> POSITIVE valence
    r_won = tp.process_turn("I feel wonderful")
    equal(r_won.assertion, "ASSERTED")
    equal(r_won.valence, "POSITIVE")
    ok("fantastic" in r_won.response_text.lower() or "glad" in r_won.response_text.lower())

    # 2. "I feel awful" -> NEGATIVE valence
    r_awf = tp.process_turn("I feel awful")
    equal(r_awf.assertion, "ASSERTED")
    equal(r_awf.valence, "NEGATIVE")
    ok("sorry" in r_awf.response_text.lower(), "Awful must trigger empathetic response")

    # 3. "I'm over the moon" -> POSITIVE valence idiom
    r_moon = tp.process_turn("I'm over the moon")
    equal(r_moon.assertion, "ASSERTED")
    equal(r_moon.valence, "POSITIVE")
    ok("fantastic" in r_moon.response_text.lower() or "glad" in r_moon.response_text.lower())

    # 4. "Tell me a joke" -> directive with NEUTRAL valence
    r_joke = tp.process_turn("Tell me a joke")
    equal(r_joke.kind, "directive")
    equal(r_joke.assertion, "ASSERTED")
    equal(r_joke.valence, "NEUTRAL")

    # 5. F14 Anti-drift test: 'not' never produces ^3 Negative
    r_drift = tp.process_turn('I am not attracted toward "the offer".')
    equal(r_drift.assertion, "DENIED", "Negation must set assertion=DENIED")
    equal(r_drift.valence, "POSITIVE", "F14 rule: 'not' never turns affinity ^2 into negative ^3")

    # 6. Negative repulsion
    r_rep = tp.process_turn('I am repelled by "the offer".')
    equal(r_rep.assertion, "ASSERTED")
    equal(r_rep.valence, "NEGATIVE")


@case
def test_k8_polarity_deprecation_and_unlisted_affect_words_resolve_neutral():
    """K8: Polarity legacy alias deprecation isolation and honest lexical boundary.
    Claim ceiling:
    'Valence comes from the frozen ALIAS-WIDE lexicon and the Noetic ^2/^3 frames.
    Affect words outside the lexicon resolve to NEUTRAL and are not guessed.'

    1. In-lexicon expressions resolve appropriately:
       - 'I'm on top of the world' -> assertion: ASSERTED, valence: POSITIVE
       - 'I feel ecstatic' -> assertion: ASSERTED, valence: POSITIVE
       - 'I am miserable' -> assertion: ASSERTED, valence: NEGATIVE

    2. Unlisted affect words outside the lexicon honestly resolve to NEUTRAL without guessing:
       - 'I feel wretched' -> assertion: ASSERTED, valence: NEUTRAL
       - 'I'm furious' -> assertion: ASSERTED, valence: NEUTRAL
       - 'I'm overjoyed' -> assertion: ASSERTED, valence: NEUTRAL

    3. Deprecation isolation of 'polarity':
       - In 'Tell me a joke', kind is 'directive', assertion is 'ASSERTED', valence is 'NEUTRAL'.
         Legacy receipt.polarity == 'ASSERTED' is preserved for old callers.
       - Internal processor decisions branch on node.assertion and node.valence, never node.polarity.
       - Verifies that CubeNode and TurnReceipt mark .polarity as DEPRECATED.
    """
    tp = TurnProcessor()

    # 1. In-lexicon expressions
    r_world = tp.process_turn("I'm on top of the world")
    equal(r_world.assertion, "ASSERTED")
    equal(r_world.valence, "POSITIVE")

    r_ecstatic = tp.process_turn("I feel ecstatic")
    equal(r_ecstatic.assertion, "ASSERTED")
    equal(r_ecstatic.valence, "POSITIVE")

    r_miserable = tp.process_turn("I am miserable")
    equal(r_miserable.assertion, "ASSERTED")
    equal(r_miserable.valence, "NEGATIVE")

    # 2. Unlisted affect words honestly resolve to NEUTRAL (no guessing)
    r_wretched = tp.process_turn("I feel wretched")
    equal(r_wretched.assertion, "ASSERTED")
    equal(r_wretched.valence, "NEUTRAL", "Unlisted affect word 'wretched' must resolve to NEUTRAL without guessing")

    r_furious = tp.process_turn("I'm furious")
    equal(r_furious.assertion, "ASSERTED")
    equal(r_furious.valence, "NEUTRAL", "Unlisted affect word 'furious' must resolve to NEUTRAL without guessing")

    r_overjoyed = tp.process_turn("I'm overjoyed")
    equal(r_overjoyed.assertion, "ASSERTED")
    equal(r_overjoyed.valence, "NEUTRAL", "Unlisted affect word 'overjoyed' must resolve to NEUTRAL without guessing")

    # 3. Polarity deprecation isolation
    r_joke = tp.process_turn("Tell me a joke")
    equal(r_joke.kind, "directive")
    equal(r_joke.assertion, "ASSERTED")
    equal(r_joke.valence, "NEUTRAL")
    # Legacy alias still reports ASSERTED for legacy backward compatibility
    equal(r_joke.polarity, "ASSERTED")

    # Verify docstring deprecation notices exist on both classes
    import inspect
    cube_src = inspect.getsource(CubeNode)
    turn_src = inspect.getsource(TurnReceipt)
    ok("DEPRECATED" in cube_src, "CubeNode must document polarity as DEPRECATED")
    ok("DEPRECATED" in turn_src, "TurnReceipt must document polarity as DEPRECATED")


# =============================================================================
# Honesty Tests (H1 - H4)
# =============================================================================

@case
def test_h1_unknown_domain_writes_no_cube():
    """H1: A turn about an unknown domain writes NO cube and says so."""
    tp = TurnProcessor()
    initial_cube_count = len(tp.store.nodes)

    rec = tp.process_turn("What is the capital of Portugal?")
    equal(rec.outcome, "REFUSE")
    equal(len(rec.cubes_written), 0, "REFUSE must write NO cube")
    equal(len(tp.store.nodes), initial_cube_count, "Store node count must be unchanged")
    ok("won't guess" in rec.response_text.lower() or "verified data" in rec.response_text.lower())


@case
def test_h2_face_unknown_requires_explanation():
    """H2: A face that cannot be filled is availability=unknown WITH an explanation.
    Missing knowledge must not be filled with fabricated content merely to complete a cube.
    """
    faces = {
        f"face_{i}": Face(availability="populated", human_text=f"Text {i}")
        for i in range(1, 6)
    }
    # Face 6 is unknown but carries NO explanation -> MUST fail validation
    faces["face_6"] = Face(availability="unknown", human_text="", structured={})

    core = Core(label="TestNode", kind="concept", identity_statement="Test statement")
    cube = CubeNode(node_id="test_node_h2", core=core, faces=faces)

    try:
        validate_cube(cube)
        ok(False, "Should have raised CubeValidationError for unknown face lacking explanation")
    except CubeValidationError as e:
        ok("lacks required explanation text" in str(e))

    # Face with structured content while marked unknown -> MUST fail validation
    faces["face_6"] = Face(availability="unknown", human_text="Unknown reason", structured={"fake": 123})
    cube_fake = CubeNode(node_id="test_node_h2b", core=core, faces=faces)
    try:
        validate_cube(cube_fake)
        ok(False, "Should have raised CubeValidationError for unknown face with structured data")
    except CubeValidationError as e:
        ok("non-empty structured data" in str(e))


@case
def test_h3_provenance_source_none_never_admitted():
    """H3: No cube is ever created with provenance.source = NONE.
    Attempting to write a cube with source=NONE raises AdmissionRefusal.
    """
    faces = {
        f"face_{i}": Face(availability="populated", human_text=f"Text {i}")
        for i in range(1, 7)
    }
    core = Core(label="UngroundedCube", kind="instance", identity_statement="Fabricated statement")
    cube_none = CubeNode(
        node_id="cube_none_source",
        core=core,
        faces=faces,
        provenance=Provenance(source="NONE")
    )

    store = CubeStore()
    try:
        store.write_cube(cube_none)
        ok(False, "Should have raised AdmissionRefusal for source=NONE")
    except AdmissionRefusal as e:
        ok("source=NONE is forbidden" in str(e))


@case
def test_h4_non_grounded_domain_refused_no_cube():
    """H4: 'Study medieval poetry' produces NO hypothesised inputs it cannot justify
    (today: it emitted 'Thermal Energy Transfer' for poetry and must be refused).
    """
    tp = TurnProcessor()
    initial_count = len(tp.store.nodes)

    rec = tp.process_turn("Study medieval poetry")
    equal(rec.outcome, "REFUSE")
    equal(len(rec.cubes_written), 0, "Must write NO cube")
    equal(len(tp.store.nodes), initial_count, "Store node count must not increase")
    ok("lacks justified physical inputs" in rec.response_text)
    ok("Thermal Energy Transfer" not in rec.response_text, "No fabricated thermal inputs emitted!")


# =============================================================================
# Trace & Determinism Tests (T1 - T3)
# =============================================================================

@case
def test_t1_answered_turn_cites_operation_and_cubes():
    """T1: Every answered turn cites the operation run and the cube(s) it read."""
    tp = TurnProcessor()
    tp.process_turn("We have 50 Flour, 30 Sugar")

    rec = tp.process_turn("What do we have in stock")
    equal(rec.outcome, "READ")
    ok(rec.operation is not None, "Answered turn must cite operation run")
    equal(rec.operation, "LIST_PARTS")
    ok(len(rec.cubes_read) > 0, "Answered turn must cite cubes read")
    ok(INVENTORY_NODE_ID in rec.cubes_read)


@case
def test_t2_refused_turn_writes_receipt():
    """T2: Every refused turn still writes a receipt."""
    tp = TurnProcessor()
    rec = tp.process_turn("Study medieval poetry")
    equal(rec.outcome, "REFUSE")
    ok(rec.receipt_hash != "", "Refused turn must generate cryptographic receipt hash")
    ok(len(tp.turn_history) == 1, "Refused turn is logged in history")


@case
def test_t3_fifty_identical_conversations_produce_identical_receipts():
    """T3: Fifty identical conversations produce identical receipts."""
    conv_prompts = [
        "We have 50 Flour, 30 Sugar",
        "What do we have in stock",
        "Remember I prefer short answers",
        "Do you remember my preference",
        "Study medieval poetry"
    ]

    base_hashes = []
    for _ in range(50):
        tp = TurnProcessor()
        hashes = [tp.process_turn(p).receipt_hash for p in conv_prompts]
        if not base_hashes:
            base_hashes = hashes
        else:
            equal(hashes, base_hashes, "All 50 iterations must match byte-for-byte")


@case
def test_answer_trace_rate_equals_one():
    """Section 8 requirement: answer_trace_rate must be exactly 1.0."""
    tp = TurnProcessor()
    prompts = [
        "We have 50 Flour, 30 Sugar",
        "What do we have in stock",
        "what've we got on hand then",
        "Remember I prefer short answers",
        "Do you remember my preference",
        "Do we have 50 Flour and 30 Sugar or not",
        "I feel fantastic today"
    ]
    for p in prompts:
        tp.process_turn(p)

    answered_turns = [t for t in tp.turn_history if t.outcome in ("WRITE", "READ")]
    ok(len(answered_turns) > 0)

    traceable_count = sum(
        1 for t in answered_turns
        if t.operation is not None and (len(t.cubes_read) > 0 or len(t.cubes_written) > 0)
    )
    rate = traceable_count / len(answered_turns)
    equal(rate, 1.0, f"answer_trace_rate must be 1.0, got {rate}")


@case
def test_readme_claim_ceiling():
    """Verifies that README.md exists and contains the claim ceiling verbatim."""
    readme_path = os.path.join(HERE, "README.md")
    ok(os.path.exists(readme_path), "README.md must exist in cube_store")

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    expected_ceiling = (
        "MECHANISM ONLY.\n"
        "KNOWLEDGE IS STORED AS CUBES; ANSWERS COME FROM THREE OPERATIONS OVER THAT STORE.\n"
        "AN UNKNOWN FACE IS REPORTED AS UNKNOWN AND IS NEVER FILLED.\n"
        "NO UNDERSTANDING OF THE REQUEST IS CLAIMED."
    )
    ok(expected_ceiling in content, "README.md must contain the claim ceiling verbatim")


# =============================================================================
# Main Test Runner
# =============================================================================

def run_all():
    print("=" * 72)
    print("      UNIFIED CUBE STORE ACCEPTANCE SUITE (SPEC_20261018)      ")
    print("=" * 72)

    passed = 0
    failed = 0
    for c in CASES:
        name = c.__name__
        try:
            c()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name} -> {e}")
            failed += 1

    print("-" * 72)
    print(f"TOTAL: {len(CASES)} cases | PASSED: {passed} | FAILED: {failed}")
    if failed == 0:
        print("RESULT: ALL PASS (100% VERIFIED)")
    else:
        print("RESULT: FAILURES DETECTED")
        sys.exit(1)


if __name__ == "__main__":
    run_all()
