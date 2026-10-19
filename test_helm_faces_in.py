"""Tests for helm_faces_in.py (the faces reader). Standard library only. Run: python -B -m unittest test_helm_faces_in -v"""
import json
import os
import unittest

import helm_faces_in as F

ING = ["Flour", "Water", "Sugar", "Butter", "Milk", "Egg", "Yeast", "Salt"]
PROD = ["Bread", "Frosting", "Starter", "Meringue"]


def faces(text):
    r = F.read(text, ING, PROD)
    return r["status"], [(f["scope"], f["name"], f["face"], f["stage"]) for f in r["faces"]], r["remainder"], r["clarify"]


class TestFacesReader(unittest.TestCase):
    def test_owner_example_wisdom_rising_and_stock_kept(self):
        st, fs, rem, _ = faces("We have 12 cups of flour but I barely know how to use it.")
        self.assertEqual(st, "FACES")
        self.assertEqual(fs, [("ingredient", "Flour", "WISDOM", "RISING")])
        self.assertEqual(rem, "we have 12 cups of flour.")

    def test_power_waning_alone_leaves_no_remainder(self):
        st, fs, rem, _ = faces("The yeast is getting old.")
        self.assertEqual((st, fs, rem), ("FACES", [("ingredient", "Yeast", "POWER", "WANING")], ""))

    def test_recipe_purpose_absent(self):
        self.assertEqual(faces("There's no reason to bake bread today.")[1], [("recipe", "Bread", "PURPOSE", "ABSENT")])
        self.assertEqual(faces("Nobody needs meringue today.")[1], [("recipe", "Meringue", "PURPOSE", "ABSENT")])

    def test_ingredient_purpose_absent(self):
        self.assertEqual(faces("The sugar isn't for the frosting.")[1], [("ingredient", "Sugar", "PURPOSE", "ABSENT")])

    def test_two_faces_two_ingredients(self):
        st, fs, _, _ = faces("The yeast is getting old and I'm still learning how to use the milk.")
        self.assertEqual(fs, [("ingredient", "Yeast", "POWER", "WANING"), ("ingredient", "Milk", "WISDOM", "RISING")])

    def test_stock_list_with_face_keeps_every_stock_clause(self):
        st, fs, rem, _ = faces("We have 8 cups of water, 12 cups of flour, and the yeast is getting old.")
        self.assertEqual(fs, [("ingredient", "Yeast", "POWER", "WANING")])
        self.assertEqual(rem, "we have 8 cups of water and 12 cups of flour.")

    def test_no_face_returns_text_unchanged(self):
        for t in ("We have 12 cups of flour.", "I love baking with flour.", "The flour bag is heavy.",
                  "How much bread can we make?"):
            st, fs, rem, cl = faces(t)
            self.assertEqual((st, fs, rem, cl), ("NONE", [], t, None), t)

    def test_question_is_never_a_face(self):
        self.assertEqual(faces("Is the yeast getting old?")[0], "NONE")

    def test_cue_word_without_a_row_asks(self):
        st, fs, rem, cl = faces("The old flour is fine.")
        self.assertEqual((st, fs, rem, cl["code"]), ("CLARIFY", [], "", "FACE_UNREAD"))

    def test_negation_is_not_taken(self):
        self.assertEqual(faces("I'm not rusty with the butter.")[0], "CLARIFY")
        self.assertEqual(faces("I'm not rusty with the butter.")[3]["code"], "FACE_NEGATED")
        # a row whose own words carry the negation is taken
        self.assertEqual(faces("I'm not sure how to use the salt.")[1], [("ingredient", "Salt", "WISDOM", "RISING")])

    def test_pronoun_needs_exactly_one_named_ingredient(self):
        st, _, _, cl = faces("We have 3 eggs and 2 cups of milk but I barely know how to use it.")
        self.assertEqual((st, cl["code"]), ("CLARIFY", "FACE_WHICH_INGREDIENT"))
        st, _, _, cl = faces("I barely know how to use it.")
        self.assertEqual((st, cl["code"]), ("CLARIFY", "FACE_WHICH_INGREDIENT"))

    def test_only_known_names(self):
        # an ingredient the brain does not have is not read as a face of anything
        self.assertEqual(faces("The cinnamon is getting old.")[0], "NONE")

    def test_every_lexicon_row_fires_on_its_own_example(self):
        examples = {
            "W1": "I barely know how to use the salt.", "W2": "I'm still learning how to use the salt.",
            "W3": "I'm just learning to use the salt.", "W4": "I'm new to using the salt.",
            "W5": "I'm not sure how to use the salt.", "W6": "I'm a bit rusty with the salt.",
            "W7": "I'm out of practice with the salt.", "W8": "I know the salt inside out.",
            "W9": "I know exactly how to use the salt.", "W10": "I've mastered the salt.",
            "W11": "I have no idea how to use the salt.", "W12": "I don't know how to use the salt.",
            "P1": "The salt is getting stale.", "P2": "The salt is losing its strength.", "P3": "The salt is past its best.",
            "P4": "The salt is just starting to work.", "P5": "The salt is still waking up.", "P6": "The salt is dead.",
            "P7": "The salt has gone bad.", "P8": "The salt has spoiled.", "P9": "The salt is fresh.",
            "P10": "The salt is at full strength.", "U1": "The salt isn't for the meringue.",
            "U2": "I'm saving the salt for something else.", "U3": "I might use the salt for the meringue.",
            "U4": "The salt is meant for the meringue.", "R1": "There is no reason to make meringue.",
            "R2": "Nobody wants meringue.", "R3": "We don't need any meringue.", "R4": "We might make some meringue.",
            "R5": "We need meringue for the party.",
        }
        rows = {r["id"]: r for r in F.LEXICON["rows"]}
        self.assertEqual(set(examples), set(rows))
        for rid, text in examples.items():
            r = F.read(text, ING, PROD)
            self.assertEqual(r["status"], "FACES", rid)
            self.assertEqual(r["faces"][0]["row"], rid, (rid, r["faces"]))
            self.assertEqual((r["faces"][0]["face"], r["faces"][0]["stage"]), (rows[rid]["face"], rows[rid]["stage"]))

    def test_lexicon_rows_carry_sources_and_one_scale_stages(self):
        for row in F.LEXICON["rows"]:
            self.assertIn(row["source"], F.LEXICON["sources"])
            self.assertIn(row["stage"], ("RISING", "PEAK", "WANING", "ABSENT"))
            self.assertIn(row["face"], ("PURPOSE", "WISDOM", "POWER"))
            self.assertEqual(row["scope"] == "recipe", row["id"].startswith("R"))

    def test_deterministic_and_pure(self):
        before = F.LEXICON_SHA256
        a = [F.read("We have 12 cups of flour but I barely know how to use it.", ING, PROD) for _ in range(3)]
        self.assertTrue(all(x == a[0] for x in a))
        with open(F.LEXICON_PATH, "rb") as h:
            import hashlib
            self.assertEqual(hashlib.sha256(h.read()).hexdigest(), before)

    def test_say_face_has_no_cas_words(self):
        for row in F.LEXICON["rows"]:
            name = "Bread" if row["scope"] == "recipe" else "Flour"
            text = F.say_face({"scope": row["scope"], "name": name, "face": row["face"], "stage": row["stage"]})
            for bad in ("Ω", "^", "PURPOSE", "WISDOM", "POWER", "RISING", "WANING", "PEAK", "ABSENT"):
                self.assertNotIn(bad, text)


if __name__ == "__main__":
    unittest.main()
