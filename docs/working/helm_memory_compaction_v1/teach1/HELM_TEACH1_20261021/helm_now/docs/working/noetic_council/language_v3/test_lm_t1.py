"""LM-T1 unit tests (builder's own fixtures; no hand-set item and no SDG English row is used here)."""
import random
import unittest

import cce
import aliaswide
import coverage


def frame(n, slots, d=None, r=None, drive=None, pol="ASSERTED"):
    return {"noetic": n, "domain": d, "register": r, "drive": drive, "polarity": pol, "slots": slots}


def content(**kw):
    c = cce.empty_content()
    c.update(kw)
    return c


FIXTURE_TERMS = [
    frame(0, {"I": '"the plan"'}, "P"),
    frame(1, {"M": "I", "I": '"the report"', "ACT": "intakes"}, "C", ["A"]),
    frame(1, {"M": "you", "I": "Ω_x", "ACT": "outputs"}),
    frame(1, {"M": "I", "I": '"x"'}),
    frame(2, {"M": "I", "I": '"the offer"'}, "E", ["f"], "F4"),
    frame(3, {"M": "you", "I": '"the shortcut"'}, "P", ["A", "f", "T"]),
    frame(4, {"I": '"the speech"', "M": "I", "D": "3"}, "E"),
    frame(4, {"I": '"the speech"', "M": "I"}),
    frame(5, {"M": "I", "I": '"ten years of nursing"'}, "C", None, "F2"),
    frame(6, {"I": '"the argument"', "J": '"the premise"'}, "C", ["A"]),
    frame(6, {"M": "I", "I": '"the argument"', "J": '"the premise"'}),
    frame(7, {"M": "I", "I": '"scales"', "R": "1", "U": "day", "P": "daily"}, "O", ["E"]),
    frame(7, {"M": "I", "I": '"scales"'}),
    frame(8, {"I": '"the song"', "J": '"the summer"', "M": "I"}, "O", None, "F7"),
    frame(9, {"J": '"the summer"', "M": "I", "I": '"the song"'}),
    frame(9, {"J": '"the summer"', "M": "you"}),
]


class Frames(unittest.TestCase):
    def test_each_frame_round_trips_fixed_and_drawn(self):
        for t in FIXTURE_TERMS:
            for pol in ("ASSERTED", "DENIED"):
                c = content(terms=[dict(t, polarity=pol)])
                self.assertTrue(cce.round_trip(c)["ok"], (t, pol, cce.round_trip(c)))
                rng = random.Random(5)
                for _ in range(12):
                    self.assertTrue(cce.round_trip(c, rng)["ok"], (t, pol))

    def test_canonical_sentences(self):
        self.assertEqual(cce.render(content(terms=[FIXTURE_TERMS[4]])),
                         'I have an affinity for "the offer", evaluative, affective register, for Connection.')
        self.assertEqual(cce.render(content(terms=[FIXTURE_TERMS[13]])),
                         '"the song" triggers "the summer" to come to me, operational, for Purpose.')

    def test_verb_frame_picks_noetic_not_topic(self):
        c = cce.parse('Ana is a Mind. Ana is attracted toward "the risk".')
        self.assertEqual(c["terms"][0]["noetic"], 2)

    def test_female_male_by_subject_kind(self):
        self.assertEqual(cce.parse('I am composed of "x".')["terms"][0]["noetic"], 5)
        self.assertEqual(cce.parse('"y" is composed of "x".')["terms"][0]["noetic"], 6)

    def test_alias_equals_canon_content(self):
        a = cce.parse('Ana is a Mind. Ana is drawn to "x", cognitive.')
        b = cce.parse('Ana is a Mind. "x" speaks to Ana, cognitive.')
        c = cce.parse('Ana is a Mind. Ana has an affinity for "x", cognitive.')
        self.assertEqual(cce.normalize(a), cce.normalize(b))
        self.assertEqual(cce.normalize(a), cce.normalize(c))

    def test_tail_any_order(self):
        a = cce.parse('I am repelled by "x", principled, affective register, for Unity.')
        b = cce.parse('I am repelled by "x", for Unity, affective register, principled.')
        self.assertEqual(cce.normalize(a), cce.normalize(b))

    def test_number_words(self):
        a = cce.parse('"x" resonates with me to degree three.')
        self.assertEqual(a["terms"][0]["slots"]["D"], "3")


class Negation(unittest.TestCase):
    def test_not_never_makes_negative(self):
        c = cce.parse('Ana is a Mind. Ana is not attracted toward "the offer".')
        self.assertEqual((c["terms"][0]["noetic"], c["terms"][0]["polarity"]), (2, "DENIED"))
        c = cce.parse('I do not have an affinity for "x".')
        self.assertEqual((c["terms"][0]["noetic"], c["terms"][0]["polarity"]), (2, "DENIED"))

    def test_absence_is_not_a_noetic(self):
        c = cce.parse("There is no Ω_flour.")
        self.assertEqual(c["relations"], [["absent", "Ω_flour"]])
        self.assertEqual(c["terms"], [])


class Discipline(unittest.TestCase):
    def test_plus_is_co_presence(self):
        c = cce.parse("To make Ω_t, use 2 of Negative, principled, analytical register; plus 1 of Negative, principled, affective register.")
        self.assertEqual(len(c["recipe"]["terms"]), 2)
        self.assertTrue(all(t["kind"] == "state" for t in c["recipe"]["terms"]))

    def test_times_needs_named_result(self):
        with self.assertRaises(cce.Refusal) as e:
            cce.parse("To make Ω_t, use 1 of (Negative, principled, analytical register combined with Negative, principled, affective register).")
        self.assertEqual(e.exception.code, "OPERATOR_DISCIPLINE")
        with self.assertRaises(cce.Refusal) as e:
            cce.parse('I am repelled by "x", analytical register combined with affective register.')
        self.assertEqual(e.exception.code, "OPERATOR_DISCIPLINE")
        c = cce.parse("To make Ω_t, use 1 of (Negative, principled, analytical register combined with Negative, "
                      "principled, affective register into Negative, principled named Ω_firm).")
        self.assertEqual(c["recipe"]["terms"][0]["result"], "^3^P|Ω_firm")
        self.assertTrue(cce.round_trip(c)["ok"])

    def test_register_set_is_specification(self):
        c = cce.parse('I am repelled by "x", principled, in analytical, affective and transcendent registers.')
        self.assertEqual(c["terms"][0]["register"], ["A", "f", "T"])
        self.assertEqual(cce.canonical(c)["terms"][0]["register"], ["T", "A", "f"])

    def test_and_is_never_times(self):
        with self.assertRaises(cce.Refusal):
            cce.parse('"x" and "y" are drawn to me.')


class Gate(unittest.TestCase):
    def test_undetermined_fixed_and_never_drawn(self):
        c = cce.parse("I cannot tell.")
        self.assertEqual(c["gate"], "UNDETERMINED")
        for seed in (1, 2, 3):
            s = cce.say(c, seed)
            self.assertEqual((s["sentence"], s["drawn"]), ("I cannot tell.", False))

    def test_clarify_names_the_slot(self):
        c = cce.parse("I need the stock of Ω_leaves for Ω_tea. What is it?")
        self.assertEqual((c["turn"], c["topic"], c["lacunae"]), ("CLARIFY", "Ω_tea", ["the stock of Ω_leaves"]))
        self.assertTrue(cce.round_trip(c)["ok"])

    def test_refusals(self):
        cases = {'"x" is bad.': "NOT_CCE", 'I am drawn to "x" because "y".': "NOT_CCE",
                 'I might intake "x".': "HEDGE", 'I intake a lot of "x".': "VAGUE_QUANTITY",
                 '"x" triggers "x" to come to me.': "SAME_IDEA_TRIGGER", 'Bob is composed of "x".': "UNDECLARED_NAME",
                 'She is composed of "x".': "NOT_CCE", 'I am drawn to "x", formal register.': "NOT_CCE",
                 '"x" is a side effect.': "NOT_CCE", '"x" is composed of "x".': "SLOT_TYPE",
                 'I maybe stores "x"': "HEDGE"}
        for text, code in cases.items():
            with self.assertRaises(cce.Refusal, msg=text) as e:
                cce.parse(text)
            self.assertEqual(e.exception.code, code, text)

    def test_renderer_never_fills_a_gap(self):
        c = content(recipe={"omega": "Ω_t", "terms": [{"kind": "state", "noetic": 2, "domain": "P", "register": None,
                                                       "drive": None, "coefficient": None}],
                            "leakage": [], "catalysts": [], "inhibitors": []})
        self.assertFalse(cce.round_trip(c)["ok"])


class Nesting(unittest.TestCase):
    def test_depth_limit_two(self):
        self.assertTrue(cce.round_trip(cce.parse('I store that [I intake that ["x" is an Idea]].'))["ok"])
        with self.assertRaises(cce.Refusal) as e:
            cce.parse('I store that [I intake that [I output that ["x" is an Idea]]].')
        self.assertEqual(e.exception.code, "NEST_TOO_DEEP")

    def test_machinery_to_depth_five_with_raised_limit(self):
        text = '"x" is an Idea'
        for act in ("intake", "store", "process", "output", "intake"):
            text = "I %s that [%s]" % (act, text)
        c = cce.parse(text + ".", max_depth=5)
        depth, t = 0, c["terms"][0]
        while isinstance(t["slots"].get("I"), dict):
            depth += 1
            t = t["slots"]["I"]["that"]
        self.assertEqual(depth, 5)
        self.assertEqual(cce.render(c), text + ".")


class RoundTripProperty(unittest.TestCase):
    def test_random_recipes(self):
        rng = random.Random(123)
        for _ in range(300):
            terms = []
            for _ in range(rng.randint(1, 4)):
                k = rng.random()
                if k < 0.7:
                    terms.append({"kind": "state", "noetic": rng.randrange(10), "domain": rng.choice("PCEO"),
                                  "register": rng.choice([None, ["T"], ["A"], ["f"], ["E"], ["A", "f"]]),
                                  "drive": rng.choice([None, "F1", "F5", "F7"]),
                                  "coefficient": rng.choice(["1", "2", "0.5", "1.25", "10", "3"])})
                elif k < 0.85:
                    terms.append({"kind": "outcome", "coefficient": "1", "name": "Ω_o%d" % rng.randrange(99)})
                else:
                    terms.append({"kind": "emergent", "coefficient": "2", "result": "Ω_r",
                                  "components": [{"noetic": 2, "domain": "P", "register": None, "drive": None},
                                                 {"noetic": 4, "domain": "E", "register": ["f"], "drive": None}]})
            c = content(recipe={"omega": "Ω_t", "terms": terms, "catalysts": [], "inhibitors": [],
                                "leakage": [{"coefficient": "0.1", "side": "Ω_t_side", "implicit": False}]})
            self.assertTrue(cce.round_trip(c)["ok"])
            self.assertTrue(cce.round_trip(c, rng)["ok"])


class AliasWide(unittest.TestCase):
    """Builder-written English only (never an SDG row)."""
    def parsed(self, cas):
        from sdg_bridge_v2.grammar import parse_recipe
        return parse_recipe(cas)

    def test_verb_frame_first(self):
        p = self.parsed("Θ(Ω_a_1) = 2*^6^C + 1*^9^O → Ω_a_1")
        e = "To make a_1, take 2 of breaking down an idea in cognitive work and 1 of what popped into mind in operational work."
        self.assertEqual(aliaswide.check(p, e)["verdict"], "MATCH")

    def test_swap_is_mismatch(self):
        p = self.parsed("Θ(Ω_a_1) = 2*^9^O + 1*^8^O → Ω_a_1")
        e = "Combine 2 of what one thing leads to another in operational thinking with 1 of what popped into mind in operational thinking."
        self.assertEqual(aliaswide.check(p, e)["verdict"], "MISMATCH")

    def test_number_words_and_one_thing(self):
        p = self.parsed("Θ(Ω_a_1) = 2*^8^O → Ω_a_1")
        self.assertEqual(aliaswide.check(p, "Use two of one thing leads to another, in operational form.")["verdict"], "MATCH")

    def test_bare_cause_not_a_marker(self):
        p = self.parsed("Θ(Ω_a_1) = 2*^8^O → Ω_a_1")
        self.assertEqual(aliaswide.check(p, "Use 2 of the cause in operational form.")["verdict"], "UNPARSEABLE_ENGLISH")

    def test_lexicon_no_shared_exact_phrase(self):
        seen = {}
        for name in ("frame_tier", "name_tier", "noun_tier"):
            for n, ps in aliaswide.LEX[name].items():
                for p in ps:
                    self.assertNotIn(p, seen, p)
                    seen[p] = n


class Ledger(unittest.TestCase):
    def test_universe_size(self):
        self.assertEqual(len(coverage.pairs()), 130)
        self.assertEqual(len(coverage.pairs()) * 4 * 5, 2600)


if __name__ == "__main__":
    unittest.main()
