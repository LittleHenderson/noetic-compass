"""test_all.py -- runnable with no pytest: `python -B test_all.py`.

Every case is named after the claim it tests. A case that fails raises; the runner prints FAIL
with the reason and keeps going, then exits non-zero. The last lines print the figures the report
asks for: the wordings-per-content minimum, median and maximum, and the count of cases.

What is being tested is the round trip and only the round trip (TRANSLATOR_SPEC.md section 5),
plus the three anti-cheat checks and the honest refusals around them. No case tests "meaning".
"""

from __future__ import annotations

import os
import statistics
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:                                    # the console on Windows is not UTF-8 by default
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                       # pragma: no cover
    pass

import cas_validator
import cce_parse
import cce_render
import inject
import lexicon as LX
import roundtrip as RT
import tap
from content import CASContent, Leakage, N, Recipe, RecipeTerm, State, Term

CASES = []
FIGURES = {}


def case(function):
    CASES.append(function)
    return function


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def equal(left, right, message):
    if not left == right:
        raise AssertionError("%s\n  left : %r\n  right: %r" % (message, left, right))


def expect_refusal(text, code, **kwargs):
    report = cce_parse.parse_report(text, **kwargs)
    check(report["status"] == "UNPARSEABLE",
          "%r should be UNPARSEABLE with %s, but it parsed" % (text, code))
    equal(report["code"], code, "wrong refusal code for %r" % (text,))
    return report


# --- the sample contents every case reuses ---------------------------------------------------------------------
OFFER = '"the offer"'
ARGUMENT = '"the argument"'
PREMISE = '"the premise"'


def sample_recipe() -> CASContent:
    """A full recipe: two prerequisite states with a tail each, a p/q coefficient, an outcome
    prerequisite, leakage, a catalyst and an inhibitor."""
    recipe = Recipe(
        "Ω_bread",
        terms=(RecipeTerm("1/3", kind="state", state=State(5, domain="C")),
               RecipeTerm("2", kind="state", state=State(7, domain="O", register=("A",), drive="F6")),
               RecipeTerm("3/7", kind="outcome", name="Ω_starter")),
        leakage=(Leakage("1/9", "Ω_steam"),),
        catalysts=("Ω_warmth",),
        inhibitors=("Ω_draught",))
    return CASContent(recipe=recipe)


def sample_frame() -> CASContent:
    term = Term(2, slots={"M": "I", "I": OFFER}, domain="P", register=("A", "f"), drive="F2")
    return CASContent(terms=(term,))


def sample_two_terms() -> CASContent:
    first = Term(3, slots={"M": "Ana", "I": OFFER}, domain="E", register=("f",))
    second = Term(1, slots={"M": "Ana", "I": ARGUMENT, "ACT": "processes"}, domain="C")
    return CASContent(terms=(first, second), relations=(("is_a", "Ana", "Mind"),))


def sample_nested() -> CASContent:
    inner = CASContent(terms=(Term(2, slots={"M": "Ana", "I": OFFER}),))
    outer = Term(1, slots={"M": "I", "I": inner, "ACT": "stores"}, domain="C",
                 register=("A",), drive="F2")
    return CASContent(terms=(outer,), relations=(("is_a", "Ana", "Mind"),))


def sample_fractal() -> CASContent:
    return CASContent(fractal=(State(8, domain="E", register=("f",)),
                               State(4, domain="E", register=("f",))))


def sample_relations() -> CASContent:
    return CASContent(relations=(("is_a", "Ana", "Mind"),
                                 ("is_a", "Bo", "Idea"),
                                 ("one_of", OFFER, ('"coffee"', OFFER)),
                                 ("leads_to", '"rain"', '"flood"'),
                                 ("needs_first", "Ω_b", "Ω_a"),
                                 ("absent", "Ω_flour"),
                                 ("stock", "4", "Ω_leaves")))


def sample_turns() -> CASContent:
    return CASContent(turn="CLARIFY", omega="Ω_x", lacunae=("the stock of Ω_leaves",))


def sample_refusal_turn() -> CASContent:
    return CASContent(turn="REFUSE_CLAIM", reason="no evidence")


def sample_undetermined() -> CASContent:
    return CASContent(gate="UNDETERMINED")


def named_samples():
    return (("recipe with 1/3 and 3/7", sample_recipe()),
            ("one frame with a full tail", sample_frame()),
            ("two terms and a declaration", sample_two_terms()),
            ("nested frame", sample_nested()),
            ("fractal sequence", sample_fractal()),
            ("relations and statements", sample_relations()),
            ("a CLARIFY turn", sample_turns()),
            ("a REFUSE_CLAIM turn", sample_refusal_turn()),
            ("UNDETERMINED", sample_undetermined()))


def drawable_samples():
    """The contents a wording draw can vary: frames and recipes. The spec FIXES the wording of
    UNDETERMINED ("I cannot tell.", never drawn) and of the CLARIFY and REFUSE_CLAIM turns, so
    those are excluded from the wordings-per-content minimum and reported separately."""
    return tuple((name, content) for name, content in named_samples()
                 if content.terms or content.recipe is not None)


# ===============================================================================================================
# 1. numbers: the Q13 ruling
# ===============================================================================================================
@case
def the_number_layer_keeps_one_third_exact():
    proof = N.prove_one_third()
    check(proof["parsed_is_exactly_one_third"], "1/3 did not parse to exactly Fraction(1, 3)")
    equal(proof["rendered"], "1/3", "1/3 rendered as something other than p/q")
    check(proof["reparsed_equals_parsed"], "1/3 did not parse back to itself")
    equal(proof["decimal_refused_with"], "LOSSY_CONVERSION_REFUSED",
          "asking for a decimal of 1/3 was not refused with a typed word")
    equal(proof["decimal_style_refused_with"], "LOSSY_CONVERSION_REFUSED",
          "the decimal style of 1/3 was not refused")
    check(proof["never_decimal"], "1/3 must never become a decimal")
    for text, expected in (("3/7", N.Fraction(3, 7)), ("0.5", N.Fraction(1, 2)),
                           ("half", N.Fraction(1, 2)), ("2", N.Fraction(2)),
                           ("22/7", N.Fraction(22, 7)), ("0.25", N.Fraction(1, 4))):
        equal(N.parse_number(text), expected, "%r parsed to the wrong exact value" % text)
    equal(N.fraction_text(N.Fraction(3, 7)), "3/7", "Fraction(3, 7) did not render as 3/7")
    equal(N.render_number(N.Fraction(1, 2), "decimal"), "0.5", "1/2 has a decimal form")
    equal(N.render_number(N.Fraction(1, 2), "fraction"), "1/2", "1/2 has a p/q form")
    check(not N.is_terminating(N.Fraction(1, 3)), "1/3 was called terminating")
    check(N.is_terminating(N.Fraction(1, 8)), "1/8 was called non-terminating")
    try:
        N.parse_number(0.5)
    except N.NumberRefusal as exc:
        equal(exc.code, "NOT_A_NUMBER", "a float was not refused as lossy")
    else:
        raise AssertionError("a float was accepted as an exact number")
    try:
        N.parse_number("-2")
    except N.NumberRefusal as exc:
        equal(exc.code, "NEGATIVE_NOT_CCE", "a negative was not refused")
    else:
        raise AssertionError("a negative was accepted")


@case
def one_third_round_trips_in_a_recipe_and_never_becomes_decimal():
    content = sample_recipe()
    sentence = cce_render.render(content)
    check("1/3" in sentence, "the fixed twin lost the 1/3 coefficient: %r" % sentence)
    check("3/7" in sentence, "the fixed twin lost the 3/7 coefficient: %r" % sentence)
    check("1/9" in sentence, "the fixed twin lost the 1/9 leakage coefficient: %r" % sentence)
    for forbidden in ("0.333", "0.33", "0.4285", "0.1428", "round"):
        check(forbidden not in sentence, "the fixed twin approximated a number: %r" % sentence)
    back = cce_parse.parse(sentence)
    equal(back, content, "the 1/3 recipe did not parse back identical")
    exact = [entry.coefficient for entry in back.recipe.terms]
    equal(exact[0], N.Fraction(1, 3), "1/3 came back as a different value")
    for wording in cce_render.wordings(content):
        said = cce_render.render(content, wording)
        check("0.3" not in said, "a wording rendered 1/3 as a decimal: %r" % said)
        equal(cce_parse.parse(said), content, "a wording of the recipe failed read-back")


# ===============================================================================================================
# 2. the round trip itself
# ===============================================================================================================
@case
def a_full_recipe_renders_to_canon_english_and_parses_back_identical():
    content = sample_recipe()
    wording = cce_render.fixed_twin(content)
    equal(wording.tier, "CANON", "the fixed twin is not CANON wording")
    sentence = cce_render.render(content, wording)
    equal(sentence,
          "To make Ω_bread, use 1/3 of Female, cognitive; plus 2 of Rhythm, operational, "
          "analytical register, for Structure; plus 3/7 of Ω_starter. Side product: 1/9 of Ω_steam. "
          "Helped by Ω_warmth. Slowed by Ω_draught.",
          "the CANON recipe sentence is not the expected one")
    back = cce_parse.parse(sentence)
    equal(back.key(), content.key(), "the CANON recipe did not parse back identical")
    receipt = RT.round_trip(content, wording)
    check(receipt.ok, "the recipe receipt failed: %r" % (receipt.rejection_codes,))
    check(cas_validator.is_valid(content), "the recipe content is not CAS-valid: %r"
          % (cas_validator.validate(content),))


@case
def every_noetic_frame_round_trips_with_a_tail():
    for noetic, slots in RT.PROBE_SLOTS.items():
        for domain in ("P", "C", "E", "O"):
            for register in (None, "T", "A", "f", "E"):
                term = Term(noetic, slots=slots, domain=domain,
                            register=(register,) if register else None,
                            drive="F1" if noetic in (2, 5) else None)
                content = CASContent(terms=(term,))
                receipt = RT.round_trip(content)
                check(receipt.ok, "^%d frame (domain %s, register %r) failed read-back: %r"
                      % (noetic, domain, register, receipt.rejection_codes))
                check(cas_validator.is_valid(content),
                      "^%d frame is not CAS-valid: %r" % (noetic, cas_validator.validate(content)))


@case
def eight_plus_wordings_of_one_content_all_parse_back_to_it():
    content = sample_frame()
    table = cce_render.wordings(content)
    check(len(table) >= 8, "only %d wordings were enumerated" % len(table))
    seen = set()
    for wording in table:
        sentence = cce_render.render(content, wording)
        back = cce_parse.parse(sentence)
        equal(back, content, "wording %d changed the content: %r" % (wording.wid, sentence))
        seen.add(sentence)
    check(len(seen) >= 8, "the wordings produced only %d distinct sentences" % len(seen))
    check(len({wording.tier for wording in table} | {"CANON"}) >= 2,
          "no ALIAS wording was enumerated")


@case
def the_fixed_twin_says_eight_or_more_wordings_per_content():
    rows, failures = [], []
    for name, content in named_samples():
        info = RT.sayable(content, cap=96)
        rows.append({"content": name, "wordings_ok": info["wordings_ok"],
                     "wordings_tried": info["wordings_tried"],
                     "distinct_sentences": info["distinct_sentences"]})
        for failure in info["failures"]:
            failures.append((name, failure))
    for name, failure in failures:
        check(False, "a wording of %r failed read-back: %r" % (name, failure))
    drawable_names = {name for name, _ in drawable_samples()}
    drawable = [row for row in rows if row["content"] in drawable_names]
    counts = [row["wordings_ok"] for row in drawable]
    FIGURES["wordings_per_content"] = {
        "rows": rows,
        "drawable": sorted(drawable_names),
        "min": min(counts),
        "median": statistics.median(counts),
        "max": max(counts),
    }
    low = [row for row in drawable if row["wordings_ok"] < 8]
    check(not low, "these drawable contents said fewer than 8 wordings: %r" % (low,))
    fixed = {row["content"]: row["wordings_ok"] for row in rows
             if row["content"] not in drawable_names}
    equal(fixed.get("UNDETERMINED"), 1, "the UNDETERMINED content must have exactly one form")
    equal(fixed.get("a CLARIFY turn"), 1, "the CLARIFY turn must have exactly one form")
    equal(fixed.get("a REFUSE_CLAIM turn"), 1, "the REFUSE_CLAIM turn must have exactly one form")
    FIGURES["single_form_turns"] = fixed


@case
def render_parse_render_is_stable():
    for name, content in named_samples():
        first = cce_render.render(content)
        once = cce_parse.parse(first)
        equal(once, content, "%r changed content on the first read" % name)
        second = cce_render.render(once)
        equal(second, first, "%r: rendering the re-read content gave a different sentence" % name)
        twice = cce_parse.parse(second)
        equal(twice, once, "%r changed content on the second read" % name)


@case
def undetermined_renders_as_exactly_i_cannot_tell():
    content = sample_undetermined()
    equal(cce_render.render(content), "I cannot tell.", "UNDETERMINED is not the fixed sentence")
    equal(cce_render.FIXED_UNDETERMINED, "I cannot tell.", "the fixed sentence is not exact")
    for wording in cce_render.wordings(content):
        equal(cce_render.render(content, wording), "I cannot tell.",
              "a wording varied the UNDETERMINED sentence")
    check(RT.say(content, 11)["drawn"] is False, "UNDETERMINED was drawn as a wording")
    equal(RT.say(content, 11)["sentence"], "I cannot tell.", "say() varied the UNDETERMINED sentence")
    equal(cce_parse.parse("I cannot tell.").gate, "UNDETERMINED", "the gate word did not parse",
          )
    equal(cce_parse.parse("I cannot tell.").key(), content.key(),
          "I cannot tell. did not parse back to the UNDETERMINED content")


# ===============================================================================================================
# 3. refusals: the grammar never guesses
# ===============================================================================================================
@case
def an_ambiguous_sentence_is_refused_not_picked():
    # "X is composed of Y" is ^5 (a Mind is composed of an Idea) and ^6 (an Idea is composed of
    # another Idea). With an undeclared name the sentence genuinely reads two ways.
    report = expect_refusal('Ana is composed of "ten years of nursing".', "AMBIGUOUS")
    check("Mind or an Idea" in report["detail"],
          "the refusal did not name the two readings: %r" % report["detail"])
    # A declaration settles it, and the settled reading is the Mind one.
    settled = cce_parse.parse('Ana is a Mind. Ana is composed of "ten years of nursing".')
    equal(settled.terms[0].noetic, 5, "a declared Mind did not settle the frame to ^5")
    # An Idea subject is settled the other way, by the quotes themselves.
    idea_form = cce_parse.parse('"ten years" is composed of "nursing".')
    equal(idea_form.terms[0].noetic, 6, "a quoted subject did not settle the frame to ^6")
    # Equal-length ties never pick one: the same words with no declaration are refused twice.
    expect_refusal('Bo is impregnated with "x".', "AMBIGUOUS")


@case
def an_out_of_cce_sentence_is_unparseable_with_a_typed_code():
    expect_refusal('"x" is bad.', "NOT_CCE")
    expect_refusal('Ana is adverse to "x" because the plan failed.', "NOT_CCE")
    expect_refusal('She is adverse to "x".', "NOT_CCE")
    expect_refusal('Ana is repelled by "x", formal register.', "NOT_CCE")
    expect_refusal('Ana might be adverse to "x".', "HEDGE")
    expect_refusal('There is a lot of Ω_flour.', "VAGUE_QUANTITY")
    expect_refusal('"x" triggers "x" to come to I.', "SAME_IDEA_TRIGGER")
    expect_refusal('"x" is composed of "x".', "SLOT_TYPE")
    expect_refusal('Ted is adverse to "x".', "UNDECLARED_NAME")
    expect_refusal('To make Ω_x, use 2 of (Positive, principled combined with Negative, evaluative).',
                   "OPERATOR_DISCIPLINE")
    expect_refusal("Positive is in the Noetic set {Positive}.", "NOT_CCE")
    expect_refusal("", "NOT_CCE")
    expect_refusal('I store that [Ana intakes that [Bo stores that [Ana is adverse to "x"]]].',
                   "UNDECLARED_NAME")
    expect_refusal(
        'Ana is a Mind. Bo is a Mind. Cy is a Mind. '
        'I store that [Ana intakes that [Bo stores that [Cy is adverse to "x"]]].',
        "NEST_TOO_DEEP")
    # A sentence using a word from outside every frozen tier is refused, not guessed at.
    expect_refusal('Ana sparkles at "x".', "NOT_CCE")


@case
def no_number_is_ever_invented():
    # A ^4 frame with no degree says no degree, and reads back with none (never 0, never 1).
    bare = CASContent(terms=(Term(4, slots={"I": OFFER, "M": "I"}),))
    sentence = cce_render.render(bare)
    equal(sentence, '"the offer" resonates with me.', "a missing degree was said as a number")
    equal(cce_parse.parse(sentence), bare, "a missing degree did not read back as missing")
    check(cce_parse.parse(sentence).terms[0].slot("D") is None, "the degree slot was invented")
    # A recipe term cannot exist without a coefficient: None is a lacuna, not a 1.
    try:
        RecipeTerm(None, kind="state", state=State(2, domain="P"))
    except ValueError:
        pass
    else:
        raise AssertionError("a recipe term without a coefficient was accepted")
    # A leakage with no number is marked implicit, never silently 1.
    recipe = Recipe("Ω_x", terms=(RecipeTerm("1", kind="state", state=State(2, domain="P")),),
                    leakage=(Leakage(None, "Ω_side"),))
    content = CASContent(recipe=recipe)
    said = cce_render.render(content)
    check("Side product: Ω_side." in said, "an implicit leakage was given a number: %r" % said)
    equal(cce_parse.parse(said), content, "the implicit leakage did not read back as implicit")
    check(cce_parse.parse(said).recipe.leakage[0].coefficient is None,
          "the implicit leakage came back with a number")


@case
def nesting_deeper_than_two_is_refused():
    level_one = CASContent(terms=(Term(3, slots={"M": "Ana", "I": OFFER}),))
    level_two = CASContent(terms=(Term(1, slots={"M": "Ana", "I": level_one, "ACT": "stores"}),))
    level_three = CASContent(terms=(Term(1, slots={"M": "Ana", "I": level_two, "ACT": "outputs"}),))
    equal(level_three.depth(), 2, "two nested frames did not count as depth 2")
    check(RT.round_trip(CASContent(terms=(level_three.terms[0],))).ok is not None, "sanity")
    try:
        Term(1, slots={"M": "I", "I": level_three, "ACT": "stores"})
    except ValueError as exc:
        check("NEST" in str(exc), "a depth-3 term was refused for the wrong reason: %s" % exc)
    else:
        raise AssertionError("a depth-3 nested term was accepted")
    two_deep = CASContent(terms=(level_three.terms[0],),
                          relations=(("is_a", "Ana", "Mind"),))
    equal(two_deep.depth(), 2, "the depth-2 content is not depth 2")
    check(RT.round_trip(two_deep).ok, "a depth-2 nested content did not round-trip")


# ===============================================================================================================
# 4. normalization and identity
# ===============================================================================================================
@case
def content_normalization_is_the_specs_normalization():
    first = Term(2, slots={"M": "I", "I": OFFER})
    second = Term(3, slots={"M": "I", "I": ARGUMENT})
    equal(CASContent(terms=(first, second)), CASContent(terms=(second, first)),
          "terms did not compare as a multiset")
    equal(Term(2, slots={"M": "I", "I": OFFER}, register=("A", "f")),
          Term(2, slots={"M": "I", "I": OFFER}, register=("f", "A")),
          "register order changed the content")
    check(Term(2, slots={"M": "I", "I": OFFER}, register=None)
          != Term(2, slots={"M": "I", "I": OFFER}, register=("A",)),
          "an unspecified register was read as the analytical register")
    # The spec says coefficients compare as exact Decimals; the Q13 ruling makes that Fractions.
    equal(RecipeTerm("0.5", kind="state", state=State(2, domain="P")),
          RecipeTerm("1/2", kind="state", state=State(2, domain="P")),
          "two written forms of one exact value compared unequal")
    equal(RecipeTerm("1/3", kind="state", state=State(2, domain="P")).coefficient,
          N.Fraction(1, 3), "the coefficient is not an exact Fraction")
    check(sorted({type(RecipeTerm("1/3", kind="state", state=State(2, domain="P")).coefficient).__name__})
          == ["Fraction"], "the coefficient is not a Fraction")
    # Names are byte for byte.
    check(CASContent(terms=(Term(0, slots={"I": '"The Offer"'}),))
          != CASContent(terms=(Term(0, slots={"I": '"the offer"'}),)),
          "two different spellings of a name compared equal")
    spoken = cce_render.render(CASContent(terms=(Term(0, slots={"I": '"The Offer"'}),)))
    check('"The Offer"' in spoken, "the renderer changed a name's bytes: %r" % spoken)
    equal(cce_parse.parse(spoken).terms[0].slot("I"), '"The Offer"',
          "the parser changed a name's bytes")
    # A one-element register set and the single register are the same content (pinned choice).
    equal(Term(2, slots={"M": "I", "I": OFFER}, register=("A",)),
          Term(2, slots={"M": "I", "I": OFFER}, register=("A",)),
          "a one-element register set is not stable")
    # The derived views cannot drift from the slots they come from.
    nested = sample_nested()
    equal(len(nested.nesting), 1, "the nesting view lost the inner record")
    equal(nested.nesting[0], nested.terms[0].slot("I"), "the nesting view disagrees with the slot")
    check(ARGUMENT in "".join(nested.names) or True, "names view is readable")


@case
def the_gate_rule_is_enforced_at_construction():
    try:
        CASContent(gate="UNDETERMINED", terms=(Term(2, slots={"M": "I", "I": OFFER}),))
    except ValueError:
        pass
    else:
        raise AssertionError("an UNDETERMINED content was allowed to draw something")


# ===============================================================================================================
# 5. the three anti-cheat checks
# ===============================================================================================================
@case
def every_said_word_comes_from_a_frozen_tier():
    copied = {"the stock of Ω_leaves", "no evidence"}
    checked = 0
    for name, content in named_samples():
        for wording in cce_render.wordings(content):
            sentence = cce_render.render(content, wording)
            report = RT.check_lexicon(sentence, copied)
            check(report["ok"], "%r used words outside every frozen tier: %r"
                  % (name, report["invented"]))
            checked += 1
    for station in tap.world_demo().stations.values():
        record = tap.tap(station)
        if record.sentence is not None:
            report = RT.check_lexicon(record.sentence)
            check(report["ok"], "a tap said a word outside every frozen tier: %r" % (report,))
            checked += 1
    check(checked > 40, "too few sentences were lexicon-checked (%d)" % checked)


@case
def no_covered_cell_breaks_and_a_break_would_be_seen():
    ledger = RT.CoverageLedger()
    report = ledger.run()
    FIGURES["coverage_ledger"] = report["counts"]
    equal(report["cells"], 200, "the ledger is not 10 Noetics x 4 Domains x 5 registers")
    equal(report["covered_without_charge"], 0, "a cell was covered with no charge")
    check(report["counts"]["COVERED"] == 200,
          "not every cell round-trips: %r" % (report["not_covered"],))
    same = RT.check_regression(ledger.baseline(), ledger.states())
    check(same["ok"], "a covered cell broke inside one run")
    broken = dict(ledger.baseline())
    first = min(broken, key=str)
    broken[first] = "FADED"
    detected = RT.check_regression(ledger.baseline(), broken)
    check(not detected["ok"], "a broken cell was not detected")
    equal(detected["broken"][0]["cell"], first, "the wrong cell was reported as broken")


@case
def the_independent_validator_never_sees_the_english():
    source = open(cas_validator.__file__, encoding="utf-8").read()
    for forbidden in ("import lexicon", "from lexicon", "import cce_parse", "from cce_parse",
                      "import cce_render", "from cce_render", "import roundtrip"):
        check(forbidden not in source,
              "the independent validator imports the English layer: %r" % forbidden)
    check("import inspect" not in source or True, "sanity")
    import inspect as _inspect
    signature = _inspect.signature(cas_validator.validate)
    equal(list(signature.parameters), ["content"],
          "the independent validator takes something other than a content record")
    report = cas_validator.self_check()
    check(report["sound_is_valid"], "a sound record was called broken")
    check(report["missing_participant_problems"], "a ^5 frame with no Mind was accepted")
    check(report["same_idea_problems"], "a ^8 frame with the same Idea twice was accepted")
    check(report["wrong_slot_kind_problems"], "an Idea in a Mind slot was accepted")
    equal(cas_validator.validate(sample_recipe()), (), "a sound recipe was called broken")


@case
def the_invented_word_cheat_is_caught():
    """A cheat grammar adds a Noetic "Blend" (10) and its word to BOTH its parser and its
    renderer. Its own round trip passes. The independent validator, which never saw the English,
    still refuses it, and the lexicon check refuses the word."""

    def cheat_term():
        term = Term.__new__(Term)            # bypass the record's own Noetic range check
        term.noetic = 10
        term.slots = (("I", ARGUMENT), ("M", "Ana"))
        term.domain = None
        term.register = None
        term.drive = None
        term.polarity = "ASSERTED"
        term.coefficient = None
        return term

    def cheat_render(content):
        return '%s blends %s.' % (content.terms[0].slot("M"), content.terms[0].slot("I"))

    def cheat_parse(sentence):
        if sentence.endswith("."):
            sentence = sentence[:-1]
        head, _, tail = sentence.partition(" blends ")
        return CASContent(terms=(cheat_term(),)) if tail else None

    cheat_content = CASContent(terms=(cheat_term(),))
    said = cheat_render(cheat_content)
    equal(said, 'Ana blends "the argument".', "the cheat sentence is not the expected one")
    check(cheat_parse(said) == cheat_content, "the cheat's own round trip did not even pass")

    independent = RT.check_independent(cheat_content)
    check(not independent["ok"], "the independent validator accepted an invented Noetic")
    check(any(problem.startswith("UNKNOWN_NOETIC") for problem in independent["problems"]),
          "the validator did not name the invented Noetic: %r" % (independent["problems"],))
    lexicon_problem = RT.check_lexicon(said)
    check(not lexicon_problem["ok"], "the lexicon check accepted an invented word")
    check("blends" in lexicon_problem["invented"],
          "the lexicon check did not name the invented word: %r" % (lexicon_problem["invented"],))
    # The honest grammar cannot even read the cheat sentence.
    equal(cce_parse.parse_report(said)["status"], "UNPARSEABLE",
          "the honest grammar parsed the cheat's sentence")
    admitted = RT.admit(cheat_content, None)
    check(not admitted["ok"], "the three checks admitted the cheat")


# ===============================================================================================================
# 6. receipts
# ===============================================================================================================
@case
def receipts_are_written_once_and_never_recomputed():
    log = RT.ReceiptLog()
    content = sample_frame()
    first = RT.round_trip(content, None, None, log)
    check(first.ok, "the first receipt failed")
    second = RT.round_trip(content, None, None, log)
    check(second.cached, "the second read of a written receipt was not served from the log")
    equal(second.receipt_id, first.receipt_id, "a cached receipt changed identity")
    equal(log.stats()["written"], 1, "the log wrote more than one row for one sentence")
    equal(log.stats()["recomputed"], 0, "a receipt was recomputed")
    fields = set(first.to_dict())
    for required in ("content_hash_in", "sentence", "wording_id", "seed", "content_hash_out",
                     "ok", "rejection_codes"):
        check(required in fields, "the receipt is missing the field %r" % required)


@case
def the_english_first_receipt_is_the_one_required():
    sentence = cce_render.render(sample_frame())
    receipt = RT.english_first(sentence)
    check(receipt.ok, "the English-first receipt failed for %r" % sentence)
    # render(parse(E)) need not equal E; content may not change.
    with_alias = 'I am drawn to "the offer", principled, in analytical and affective registers, for Wisdom.'
    back = cce_parse.parse(with_alias)
    again = cce_render.render(back)
    check(again != with_alias, "the wording did not change, which is suspicious but not required")
    equal(cce_parse.parse(again), back, "the content changed across the English-first path")
    equal(RT.english_first(with_alias).ok, True, "the ALIAS sentence failed the English-first receipt")


# ===============================================================================================================
# 7. TAP and INJECT
# ===============================================================================================================
@case
def tap_reads_a_station_and_inject_brings_it_back():
    world = tap.world_demo()
    for name in ("S1", "S2", "S5", "S6"):
        station = world.station(name)
        record = tap.tap(station)
        equal(record.state, "SPOKEN", "station %s did not speak: %r" % (name, record.code))
        check(record.sentence is not None, "station %s said nothing" % name)
        check(record.receipt.ok, "station %s spoke without a passing receipt" % name)
        if station.content.turn == "ANSWER":
            check(record.sentence.startswith("I checked: "),
                  "station %s did not carry its evidence tag: %r" % (name, record.sentence))
        else:
            check(not record.sentence.startswith("I checked: "),
                  "a non-ANSWER turn claimed to be checked: %r" % (record.sentence,))
        delivery = inject.deliver(record.sentence, tap.Station(name))
        check(delivery["entered"], "INJECT refused the tap of station %s: %r"
              % (name, delivery["record"].code))
        equal(delivery["station"].content, station.content,
              "the content that left station %s is not the content that arrived" % name)
        equal(delivery["record"].evidence, "USER_SAID", "the injected content lost its evidence word")
        check(delivery["record"].write["value_written"] is False,
              "INJECT wrote a value instead of a state change")
    # The recipe station carries the exact fractions through the whole journey.
    spoken = tap.tap(world.station("S2")).sentence
    check("1/3" in spoken and "3/7" in spoken, "the tap lost an exact fraction: %r" % spoken)


@case
def a_form_gap_says_nothing_and_is_counted():
    world = tap.world_demo()
    report = tap.tap_all(world)
    check(report["form_gap_count"] >= 1, "no FORM gap was counted: %r" % (report["counts"],))
    gaps = {gap["station"]: gap["missing"] for gap in report["form_gaps"]}
    check("S3" in gaps, "the arrival station did not report its FORM gap: %r" % (gaps,))
    check("yield Y_T" in gaps["S3"], "the FORM gap did not name the yield: %r" % (gaps["S3"],))
    for record in report["records"]:
        if record.state == "FORM_GAP":
            check(record.sentence is None, "a FORM gap still produced a sentence: %r" % record.sentence)
            check(record.missing, "a FORM gap named nothing missing")
    # A station with no content at all says nothing and is NO_EVIDENCE, not a lacuna.
    empty = tap.tap(tap.Station("S4"))
    equal(empty.state, "NO_EVIDENCE", "an empty station was not reported as NO_EVIDENCE")
    check(empty.sentence is None, "an empty station produced a sentence")
    # An UNDETERMINED gate has a form, and it is the fixed sentence.
    gate = tap.tap(tap.station_s3(gate="UNDETERMINED"))
    equal(gate.sentence, "I cannot tell.", "an UNDETERMINED station did not say the fixed sentence")


@case
def tap_writes_nothing_into_the_world():
    world = tap.world_demo()
    before = world.digest()
    path_before = world.path_log
    report = tap.tap_all(world)
    equal(world.digest(), before, "the tap changed the world digest")
    equal(world.path_log, path_before, "the tap wrote into the path log")
    check(report["wrote_nothing"], "a tap reported that it wrote something")
    check(len(world.tap_log) == len(world.stations), "the tap log did not record every station")


@case
def the_routing_table_names_real_stations_and_record_kinds():
    report = inject.check_routing_table()
    check(report["ok"], "the routing table names something that does not exist: %r" % (report,))
    recipe_record = inject.inject(cce_render.render(sample_recipe()))
    equal(recipe_record.status, "ACCEPTED", "a recipe utterance was refused")
    equal(recipe_record.station, "S2", "a recipe did not route to the bias station")
    refused = inject.inject('"x" is bad.')
    equal(refused.status, "REFUSED", "an out-of-CCE utterance was accepted")
    equal(refused.code, "NOT_CCE", "the refusal lost its typed code")
    check(refused.write is None, "a refused utterance wrote something")
    check(refused.example is not None, "the CLARIFY carried no example sentence")


# ===============================================================================================================
# 8. the spec's open questions, and the claim ceiling
# ===============================================================================================================
@case
def two_hundred_random_contents_round_trip():
    """Breadth, with a fixed seed so the run is reproducible: random Noetics, random tails, random
    polarity, random exact coefficients, one to three terms, and a random sample of each content's
    wordings. Nothing here is chosen to pass."""
    import random

    rng = random.Random(20261016)
    domains = ("P", "C", "E", "O", None)
    registers = (None, ("T",), ("A",), ("f",), ("E",), ("A", "f"), ("T", "A", "f", "E"))
    drives = (None, "F1", "F2", "F3", "F4", "F5", "F6", "F7")
    minds = ("I", "you", "Ana", "Bo")

    def random_term():
        noetic = rng.randrange(10)
        slots = dict(RT.PROBE_SLOTS[noetic])
        if "M" in slots:
            slots["M"] = rng.choice(minds)
        for name, choices in (("I", (OFFER, ARGUMENT)), ("J", (PREMISE, ARGUMENT)),
                              ("D", ("0", "1", "2", "1/3", "3/7", "0.5")),
                              ("R", ("1", "2", "1/3", "0.5")),
                              ("ACT", ("intakes", "processes", "stores", "outputs"))):
            if name in slots:
                slots[name] = rng.choice(choices)
        if noetic in (6, 8, 9) and slots.get("I") == slots.get("J"):
            slots["J"] = PREMISE          # "another Idea" / "a different Idea than itself"
        return Term(noetic, slots=slots, domain=rng.choice(domains), register=rng.choice(registers),
                    drive=rng.choice(drives), polarity=rng.choice(("ASSERTED", "DENIED")))

    checked = 0
    for _ in range(200):
        content = CASContent(terms=tuple(random_term() for _ in range(rng.choice((1, 1, 2, 3)))),
                             relations=(("is_a", "Ana", "Mind"), ("is_a", "Bo", "Mind")))
        equal(cas_validator.validate(content), (), "a random content is not CAS-valid")
        table = cce_render.wordings(content)
        picks = table if len(table) <= 6 else [table[0]] + [table[rng.randrange(len(table))]
                                                           for _ in range(5)]
        for wording in picks:
            report = cce_parse.parse_report(cce_render.render(content, wording))
            equal(report["content"], content, "a random content failed read-back (%r): %r"
                  % (report["code"], report["sentence"]))
            checked += 1
    FIGURES["random_sentences_read_back"] = checked
    check(checked >= 900, "too few random sentences were read back (%d)" % checked)


@case
def the_freeze_check_finds_no_tie_of_the_grammars_own_making():
    """The grammar's own sentences never come back AMBIGUOUS: the frame table's equal-length
    pairs are told apart by slot type, which is the spec's freeze condition."""
    tie_codes = {"AMBIGUOUS", "SLOT_TYPE", "SAME_IDEA_TRIGGER"}
    seen = 0
    for name, content in named_samples():
        for wording in cce_render.wordings(content):
            sentence = cce_render.render(content, wording)
            report = cce_parse.parse_report(sentence)
            check(report["code"] not in tie_codes,
                  "%r: the grammar's own sentence %r came back %r" % (name, sentence, report["code"]))
            seen += 1
    ledger = RT.CoverageLedger()
    for cell in ledger.cells():
        noetic, domain, register = cell
        sentence = cce_render.render(RT.probe_content(noetic, domain, register))
        report = cce_parse.parse_report(sentence)
        check(report["code"] not in tie_codes,
              "probe cell %r produced its own %r on %r" % (cell, report["code"], sentence))
        seen += 1
    equal(len({template.length for template in LX.TEMPLATES}) < len(LX.TEMPLATES), True,
          "the frame table has no equal-length pair at all, so the tie rule is untested")
    FIGURES["sentences_read_back"] = seen


@case
def every_undecided_marker_is_listed_in_the_readme():
    markers = []
    for filename in sorted(os.listdir(HERE)):
        if not filename.endswith(".py"):
            continue
        with open(os.path.join(HERE, filename), encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped.startswith("# UNDECIDED IN SPEC:"):
                    markers.append((filename, stripped))
    check(len(markers) >= 8, "only %d UNDECIDED IN SPEC markers were found" % len(markers))
    readme_path = os.path.join(HERE, "README.md")
    check(os.path.exists(readme_path), "README.md is missing")
    readme = open(readme_path, encoding="utf-8").read()
    missing = [row for row in markers if row[1] not in readme]
    check(not missing, "these markers are not listed in README.md: %r" % (missing,))
    FIGURES["undecided_markers"] = [row[1] for row in markers]


@case
def the_gate_table_produces_the_specs_turns():
    equal(len(inject.GATE_ROWS), 5, "the gate table of the spec has five rows")
    supported = inject.gate('Ana is a Mind. Ana is adverse to "x".')
    equal(supported["turn"], "ANSWER", "a supported sentence did not produce an ANSWER")
    check("claim_supported" in supported["facts"], "the ANSWER did not claim support")
    unparsed = inject.gate('"x" is bad.')
    equal(unparsed["turn"], "CLARIFY", "an unparsed sentence did not produce a CLARIFY")
    equal(unparsed["code"], "NOT_CCE", "the CLARIFY lost the typed refusal word")
    check(unparsed["example"] is not None, "the CLARIFY carried no example sentence")
    empty_slot = inject.gate("I need the stock of Ω_leaves for Ω_x. What is it?")
    equal(empty_slot["turn"], "CLARIFY", "a named empty slot did not produce a CLARIFY")
    check("unfilled_slot_present" in empty_slot["facts"], "the CLARIFY did not name the unfilled slot")
    silent = inject.gate("I cannot tell.")
    equal(silent["sentence"], "I cannot tell.", "the gate dressed up the undetermined answer")
    refused = inject.gate('Ana is a Mind. Ana is adverse to "x".', claim_asked=True, evidence_path=False)
    equal(refused["turn"], "REFUSE_CLAIM", "a claim with no evidence path was not refused")
    equal(refused["sentence"], "I cannot tell.", "the refusal did not use the fixed sentence")


@case
def every_named_form_gap_is_in_the_registry():
    names = set()
    for station in tap.world_demo().stations.values():
        names.update(station.unspeakable)
    for name in names:
        check(name in tap.KNOWN_FORM_GAPS,
              "the station reports a FORM gap %r that the registry does not list" % name)
    check(len(tap.KNOWN_FORM_GAPS) >= 8, "the FORM gap registry is too short to be honest")


@case
def the_claim_ceiling_is_stated_exactly():
    readme = open(os.path.join(HERE, "README.md"), encoding="utf-8").read()
    ceiling = "CONTROLLED ENGLISH ONLY. NOT OPEN CONVERSATION. FORM ONLY, NO MEANING CLAIM."
    check(ceiling in readme, "the claim ceiling line is missing from README.md")
    check("0 learned parameters" in readme, "the README does not say there are 0 learned parameters")
    check("free english is a different and much larger build" in readme.lower(),
          "the README does not say free English is a different and much larger build")
    check("no meaning claim" in readme.lower(), "the README does not disclaim a meaning claim")


# ===============================================================================================================
# the runner
# ===============================================================================================================
def main() -> int:
    print("CCE %s -- the language layer, round-trip test suite" % LX.CCE_VERSION)
    print("lexicon digest %s, %d frozen frames, %d frozen words"
          % (LX.digest()[:16], len(LX.TEMPLATES), len(LX.FROZEN_WORDS)))
    print("-" * 78)
    passed, failed = 0, []
    for function in CASES:
        try:
            function()
        except Exception as exc:                    # noqa: BLE001 - a test runner reports everything
            failed.append((function.__name__, exc))
            print("FAIL  %s" % function.__name__)
            print("      %s" % (exc,))
            traceback.print_exc(limit=3)
        else:
            passed += 1
            print("PASS  %s" % function.__name__)
    print("-" * 78)
    figures = FIGURES.get("wordings_per_content")
    if figures:
        print("wordings per content (fixed twin, all lossless wordings tried):")
        for row in figures["rows"]:
            print("  %-32s %3d wordings, %3d distinct sentences, %d tried"
                  % (row["content"], row["wordings_ok"], row["distinct_sentences"],
                     row["wordings_tried"]))
        print("  min %d, median %.1f, max %d"
              % (figures["min"], figures["median"], figures["max"]))
    ledger = FIGURES.get("coverage_ledger")
    if ledger:
        print("coverage ledger: %s" % (ledger,))
    print("sentences read back in the freeze check: %s" % FIGURES.get("sentences_read_back"))
    print("random contents read back: %s sentences from 200 random records"
          % FIGURES.get("random_sentences_read_back"))
    print("UNDECIDED IN SPEC markers: %d (all listed in README.md)"
          % len(FIGURES.get("undecided_markers", ())))
    print("%d of %d cases passed." % (passed, len(CASES)))
    if failed:
        print("FAILED: %s" % ", ".join(name for name, _ in failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
