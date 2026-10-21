"""tests_r1w7/test_multi_qty_w7.py -- A-R1W7-7: a book line with two amounts is not representable (SPEC 7.109 D6).
The lines are the author's own, in the SHAPE of the c54 items; never an exam line. Runs with the frozen grammar
(xreal.grammar) exactly as the custodian loads it (common_w7.setup(helm=False)) -- no HELM, no network."""
import unittest

from r1w7 import common_w7 as C
from r1w7 import multi_qty_w7 as MQ


class A_TwoAmountLineIsNotRepresentable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = C.setup(helm=False)
        cls.G = cls.ns.XG
        cls.K = cls.ns.rb.keys_rbw1t

    def _key(self, raw, pantry=None):
        pantry = pantry or [x for x in raw]
        return self.K.key_item({"id": "author:test", "raw_lines": raw, "pantry_lines": pantry})

    def test_comma_joined_second_amount(self):
        raw = ["2 cups flour", "6 cloves, 12 peppercorns", "1 cup milk"]
        key = self._key(raw)
        before = dict(key["representable"])
        self.assertTrue(before["representable"], before)                         # the frozen key alone: representable
        MQ.apply(key, raw, self.G)
        self.assertEqual(key["representable"]["why_not"], ["line1:MULTI_QTY"])
        self.assertFalse(key["representable"]["representable"])
        self.assertEqual(key["representable"]["amendment"], "A-R1W7-7")
        self.assertEqual(key["representable"]["units"], before["units"])     # nothing else in the key moved
        self.assertEqual(key["representable"]["forms"], before["forms"])

    def test_and_joined_second_amount(self):
        raw = ["1 cup milk or cream and 1/2 cup water", "3 eggs"]
        key = MQ.apply(self._key(raw), raw, self.G)
        self.assertEqual(key["representable"]["why_not"], ["line0:MULTI_QTY"])
        self.assertFalse(key["representable"]["representable"])

    def test_plain_lines_are_untouched(self):
        raw = ["2 cups flour", "1 cup milk", "3 eggs", "2 1/2 teaspoons baking powder", "1/2 cup sugar"]
        key = self._key(raw)
        before = {k: (list(v) if isinstance(v, list) else v) for k, v in key["representable"].items()}
        MQ.apply(key, raw, self.G)
        self.assertTrue(key["representable"]["representable"])
        self.assertEqual(key["representable"]["why_not"], before["why_not"])
        self.assertEqual(MQ.multi_qty_lines(raw, self.G), [])

    def test_one_amount_is_one_amount(self):
        self.assertEqual(MQ.multi_qty_lines(["2 1/2 cups flour", "1-1/2 cups milk", "1/3 cup sugar",
                                             "one and a half cups flour", "1 cup milk (about 240 ml)",
                                             "1/2 to 1 cup sugar"], self.G), [])

    def test_two_amounts_after_a_separator(self):
        self.assertEqual(MQ.multi_qty_lines(["2 eggs and 1 cup milk", "2 cups flour, 1 cup sugar", "1 cup milk",
                                             "6 cloves; 12 peppercorns", "2 cups flour or 1 cup rice flour"], self.G),
                         [0, 1, 3, 4])

    def test_an_already_unrepresentable_key_stays_so_and_keeps_its_reasons(self):
        raw = ["2 or 3 cups flour", "6 cloves, 12 peppercorns"]
        key = self._key(raw)
        why_before = list(key["representable"]["why_not"])
        self.assertTrue(why_before)
        MQ.apply(key, raw, self.G)
        self.assertEqual(key["representable"]["why_not"], why_before + ["line1:MULTI_QTY"])
        self.assertFalse(key["representable"]["representable"])

    def test_idempotent(self):
        raw = ["6 cloves, 12 peppercorns"]
        key = MQ.apply(MQ.apply(self._key(raw), raw, self.G), raw, self.G)
        self.assertEqual(key["representable"]["why_not"], ["line0:MULTI_QTY"])


if __name__ == "__main__":
    unittest.main()
