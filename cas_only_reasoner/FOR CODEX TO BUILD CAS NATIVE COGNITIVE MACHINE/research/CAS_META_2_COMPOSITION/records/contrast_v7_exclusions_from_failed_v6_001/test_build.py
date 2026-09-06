"""Pure in-memory boundary tests. No current dataset, model or provider access."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('failed_exposure_builder', here/'build.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
helper_path = b.ROOT/'records/contrast_v7_exclusions_001/build.py'
raw = helper_path.read_bytes()
b.verify_bytes(raw, b.HELPER_HASH, 'TEST_HELPER_SOURCE_PIN')
spec = importlib.util.spec_from_file_location('pure_union_helper', helper_path)
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


def prior():
    return {'count': 2, 'graph_signatures': ['a'*64, 'b'*64],
            'origins': {'old': {'count': 2, 'graph_signatures': ['a'*64, 'b'*64]}}}


def receipt():
    value = {'schema': 'cas-meta2-contrast-failure-review/6', 'status': 'FAILED_RUN_TRAINING_RECOUNT_PASSED',
        'source_sha': b.SOURCE, 'source_archive_sha256': b.SOURCE_HASH, 'packet_sha256': b.PACKET_HASH,
        'job': b.JOB, 'source_files_verified': 538, 'protected_files_verified': 316,
        'collection': {'returncode': 1, 'partial_evidence': False, 'omitted_full_file_count': 0},
        'extraction': {'path': str(b.EXTRACTED), 'all_member_bytes_verified_after_write': True, 'files_verified': 1},
        'member_files': 1, 'inventory': [{}]}
    value.update({key: True for key in ('audit_completed', 'training_recount_passed',
                                       'source_and_extraction_rechecked_at_end', 'collection_full_index_verified')})
    value.update({key: False for key in ('campaign_completed', 'native_evaluation_completed', 'neural_execution',
                                        'provider_calls', 'learning_accepted', 'release_accepted')})
    return value


class ExclusionTests(unittest.TestCase):
    def test_union_keeps_prior_and_deduplicates_new(self):
        result = u.combine(prior(), {'failed_train': {'b'*64, 'c'*64}, 'failed_test': {'c'*64, 'd'*64}})
        self.assertEqual(result['schema'], 'cas-meta2-known-exposures/7')
        self.assertEqual(result['count'], 4)
        self.assertEqual(result['graph_signatures'], [c*64 for c in 'abcd'])
        self.assertEqual(result['origins']['old'], prior()['origins']['old'])

    def test_no_prior_removal(self):
        value = prior(); value['origins']['old'] = {'count': 1, 'graph_signatures': ['a'*64]}
        with self.assertRaisesRegex(ValueError, 'PRIOR_EXPOSURE_REMOVED'):
            u.combine(value, {})

    def test_old_origin_cannot_be_replaced(self):
        with self.assertRaisesRegex(ValueError, 'ORIGIN_COLLISION'):
            u.combine(prior(), {'old': {'c'*64}})

    def test_origin_counts_recounted(self):
        value = prior(); value['origins']['old']['count'] = 3
        with self.assertRaisesRegex(ValueError, 'ORIGIN_COUNT_INVALID'):
            u.combine(value, {})

    def test_failed_review_is_allowed_without_native_success(self):
        b.admit(receipt())

    def test_success_review_does_not_enter_failure_route(self):
        for change in [{'status': 'RECORDED_CONTRAST_RECOUNT_PASSED'}, {'campaign_completed': True},
                       {'native_evaluation_completed': True}, {'learning_accepted': True}]:
            with self.subTest(change=change):
                value = receipt(); value.update(change)
                with self.assertRaisesRegex(ValueError, 'PINNED_FAILED'):
                    b.admit(value)

    def test_wrong_source_or_packet_receipt_rejected(self):
        for key in ('source_sha', 'source_archive_sha256', 'packet_sha256', 'job'):
            with self.subTest(key=key):
                value = receipt(); value[key] = 'wrong'
                with self.assertRaisesRegex(ValueError, 'PINNED_FAILED'):
                    b.admit(value)

    def test_missing_recheck_or_omitted_bytes_rejected(self):
        value = receipt(); value['source_and_extraction_rechecked_at_end'] = False
        with self.assertRaises(ValueError):
            b.admit(value)
        value = receipt(); value['collection']['omitted_full_file_count'] = 1
        with self.assertRaisesRegex(ValueError, 'FAILED_COMPLETE'):
            b.admit(value)

    def test_resealed_json_cannot_replace_external_pin(self):
        original = b.canonical({'payload': {'a': 1}, 'inner_sha': 'old'})
        changed = b.canonical({'payload': {'a': 2}, 'inner_sha': sha256(b'new').hexdigest()})
        with self.assertRaisesRegex(ValueError, 'PINNED_JSON_CHANGED'):
            b.verify_bytes(changed, sha256(original).hexdigest(), 'PINNED_JSON_CHANGED')

    def test_committed_source_byte_mismatch_stops_before_import(self):
        with patch.object(b.subprocess, 'check_output', return_value=b'changed helper bytes'):
            with self.assertRaisesRegex(ValueError, 'COMMITTED_HELPER_PIN_CHANGED'):
                b.load_committed('must_not_import', b.ROOT/'file.py', 'a'*64, b.ROOT)

    def test_local_source_mismatch_stops_before_import(self):
        raw = b'known helper bytes'
        with patch.object(b.subprocess, 'check_output', return_value=raw), patch.object(b, 'file_hash', return_value='b'*64):
            with self.assertRaisesRegex(ValueError, 'LOCAL_HELPER_SOURCE_CHANGED'):
                b.load_committed('must_not_import', b.ROOT/'file.py', sha256(raw).hexdigest(), b.ROOT)

    def test_original_256_must_stay_in_prior_and_union(self):
        graphs = {f'{i:064x}' for i in range(256)}
        origin = {'count': 256, 'graph_signatures': sorted(graphs)}
        value = {'graph_signatures': sorted(graphs), 'origins': {'contrast_prototype_seed_926601': origin}}
        b.retained_prototype(value, deepcopy(value), graphs)
        changed = deepcopy(value); changed['graph_signatures'].pop()
        with self.assertRaisesRegex(ValueError, 'KNOWN_EXPOSURE_REMOVED'):
            b.retained_prototype(value, changed, graphs)

    def test_prototype_origin_cannot_be_relabelled(self):
        graphs = {f'{i:064x}' for i in range(256)}
        value = {'graph_signatures': sorted(graphs), 'origins': {
            'contrast_prototype_seed_926601': {'count': 256, 'graph_signatures': sorted(graphs)}}}
        changed = deepcopy(value); changed['origins']['contrast_prototype_seed_926601']['count'] = 255
        with self.assertRaisesRegex(ValueError, 'PROTOTYPE_ORIGIN_CHANGED'):
            b.retained_prototype(value, changed, graphs)

    def test_depth_and_graph_provenance_recount(self):
        tasks = [{'task_id': str(i), 'target': {'program': {'depth': 3, 'signature': 'a'*64}},
                  'provenance': {'depth': 3, 'graph_signature': 'a'*64}} for i in range(3)]
        graph = lambda p: p['signature']
        validate = lambda p: {'max_call_depth': p['depth']}
        graphs, result = b.recount(tasks, {'tasks': 3, 'depths': {'3': 3}}, graph, validate)
        self.assertEqual(graphs, {'a'*64})
        self.assertEqual(result['unique_graphs_by_depth'], {'3': 1})
        tasks[0]['provenance']['graph_signature'] = 'b'*64
        with self.assertRaisesRegex(ValueError, 'TASK_GRAPH_PROVENANCE_CHANGED'):
            b.recount(tasks, {'tasks': 3, 'depths': {'3': 3}}, graph, validate)

    def test_json_duplicate_or_nonfinite_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e400}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                b.decode(raw)

    def test_pure_import_did_not_load_neural_libraries(self):
        import sys
        self.assertFalse({'torch', 'casformer', 'cas_cjt', 'boto3'} & set(sys.modules))


if __name__ == '__main__':
    unittest.main(verbosity=2)

