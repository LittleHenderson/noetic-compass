"""Synthetic-only exposure-union tests. Does not open experiment data."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('exposure_v7_builder', Path(__file__).with_name('build.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def prior():
    return {'count': 2, 'graph_signatures': ['a'*64, 'b'*64],
            'origins': {'old': {'count': 2, 'graph_signatures': ['a'*64, 'b'*64]}}}


class ExposureTests(unittest.TestCase):
    def test_union_preserves_known_and_deduplicates_shared_test_graphs(self):
        result = builder.combine(prior(), {'train': {'b'*64, 'c'*64},
                                          'test': {'c'*64, 'd'*64}})
        self.assertEqual(result['schema'], 'cas-meta2-known-exposures/7')
        self.assertEqual(result['count'], 4)
        self.assertEqual(result['graph_signatures'], [letter*64 for letter in 'abcd'])
        self.assertEqual(result['origins']['old'], prior()['origins']['old'])

    def test_existing_origin_cannot_be_replaced(self):
        with self.assertRaisesRegex(ValueError, 'ORIGIN_COLLISION'):
            builder.combine(prior(), {'old': {'c'*64}})

    def test_prior_count_mismatch_rejected(self):
        value = prior()
        value['count'] = 3
        with self.assertRaisesRegex(ValueError, 'PRIOR_COUNT_INVALID'):
            builder.combine(value, {})

    def test_prior_member_cannot_disappear(self):
        value = prior()
        value['origins']['old'] = {'count': 1, 'graph_signatures': ['a'*64]}
        with self.assertRaisesRegex(ValueError, 'PRIOR_EXPOSURE_REMOVED'):
            builder.combine(value, {})

    def test_origin_count_mismatch_rejected(self):
        value = prior()
        value['origins']['old']['count'] = 8
        with self.assertRaisesRegex(ValueError, 'ORIGIN_COUNT_INVALID'):
            builder.combine(value, {})

    def test_nonfinite_and_duplicate_json_rejected(self):
        for raw in (b'{"count":1,"count":2}', b'{"x":1e400}', b'{"x":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                builder.decode(raw)

    def test_no_receipt_read_without_external_pins(self):
        with self.assertRaisesRegex(ValueError, 'EXTERNAL_HASH_REQUIRED'):
            builder.build('does-not-exist', review_sha256='', packet_sha256='0'*64,
                          output='does-not-exist')

    def test_malformed_graph_refused(self):
        with self.assertRaisesRegex(ValueError, 'GRAPH_SIGNATURE_SET_INVALID'):
            builder.combine(prior(), {'new': {'not-a-sha'}})


if __name__ == '__main__':
    unittest.main(verbosity=2)
