"""Synthetic token-prefix tests only; no task generator, packet or model reads."""
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import importlib.util
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

class NoModels(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','casformer','cas_cjt','cas_meta','tensorflow','jax','cupy','boto3','botocore'}:
            raise AssertionError('FORBIDDEN_IMPORT:'+fullname)

sys.meta_path.insert(0,NoModels())
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('diagnostic_under_test',HERE/'analyze.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
from cas_meta2 import codec,grammar_v3 as g,grammar_viability_v4 as v

MINIMAL=['[BOS]','BIND0','PROC','main','ALLOW','A','ENDALLOW','RUN','A','arg','v0','RETURN','v0','ENDPROC','[EOS]']
FORWARD=['[BOS]','BIND0','PROC','main','ALLOW','A','ENDALLOW','RUN','A','arg','v0',
    'CALL','p9','arg','v1','RETURN','v1','ENDPROC','PROC','p9','ALLOW','A','ENDALLOW']

def diagnose(tokens,limit=256):
    return a.diagnose_ids([codec.ACTION_TO_ID[token] for token in tokens],limit,g,v,codec)

class ReplayTests(unittest.TestCase):
    def test_complete_valid_sequence(self):
        r=diagnose(MINIMAL)
        self.assertEqual(r['structural_class'],'COMPLETE_VALID_TOKEN_SEQUENCE')
        self.assertIsNone(r['whole_stream_codec_error'])
        self.assertIsNone(r['first_empty_mask'])
        self.assertIsNone(r['first_detected_noncompletable_choice'])

    def test_proc_without_pending_forward_call(self):
        r=diagnose(MINIMAL[:-1]+['PROC'])
        w=r['first_detected_noncompletable_choice']
        self.assertEqual((w['cause'],w['token_index_zero_based']),('PROC_WITH_NO_PENDING_FORWARD_CALL',14))
        self.assertTrue(r['all_saved_tokens_allowed_by_actual_v3'])
        self.assertEqual(r['structural_class'],'INCOMPLETE_PREFIX_WITH_AVAILABLE_CONTINUATION')

    def test_call_with_no_target(self):
        r=diagnose(FORWARD+['CALL'])
        self.assertEqual(r['structural_class'],'GRAMMAR_STATE_DEAD_END')
        self.assertEqual(r['terminal_cause'],'NO_LEGAL_CALL_TARGET')
        self.assertEqual(r['first_detected_noncompletable_choice']['cause'],'CALL_WITH_NO_LEGAL_TARGET')
        self.assertEqual(r['first_empty_mask']['prefix_token_count'],24)
        self.assertIsNone(r['first_invalid_token'])
        self.assertTrue(all(r['callee_exclusions'].values()))
        self.assertIn('WOULD_FORM_CALL_CYCLE',r['callee_exclusions']['main'])
        self.assertIn('UNDECLARED_NAME_PASSED_CANONICAL_ORDER',r['callee_exclusions']['p8'])

    def test_pending_declaration_not_false_positive(self):
        r=diagnose(FORWARD)
        self.assertEqual(r['detected_noncompletable_choices'],[])

    def test_legal_call_not_false_positive(self):
        r=diagnose(MINIMAL[:7]+['CALL'])
        self.assertEqual(r['detected_noncompletable_choices'],[])
        self.assertIsNone(r['first_empty_mask'])

    def test_token_budget_reserves_final_eos(self):
        r=diagnose(MINIMAL[:13],14)
        self.assertEqual(r['structural_class'],'TOKEN_BUDGET_EXHAUSTION_OR_EOS_RESERVATION')
        self.assertEqual(r['terminal_cause'],'LAST_POSITION_REQUIRES_EOS')
        self.assertEqual(r['terminal_raw_allowed_without_token_budget'],['ENDPROC'])
        self.assertIsNone(r['first_invalid_token'])

    def test_exact_complete_budget(self):
        self.assertEqual(diagnose(MINIMAL,15)['structural_class'],'COMPLETE_VALID_TOKEN_SEQUENCE')

    def test_token_after_completion(self):
        r=diagnose(MINIMAL+['PROC'])
        self.assertEqual(r['first_invalid_token']['token_index_zero_based'],15)
        self.assertEqual(r['structural_class'],'MALFORMED_OR_DISALLOWED_TOKEN')

    def test_disallowed_literal_token(self):
        r=diagnose(['[BOS]','RUN'])
        self.assertEqual(r['first_invalid_token']['token_index_zero_based'],1)
        self.assertEqual(r['first_invalid_token']['state_before']['role'],'observation_binding')

    def test_incomplete_does_not_mean_invalid_token(self):
        r=diagnose(MINIMAL[:5])
        self.assertEqual(r['structural_class'],'INCOMPLETE_PREFIX_WITH_AVAILABLE_CONTINUATION')
        self.assertIsNotNone(r['whole_stream_codec_error'])
        self.assertFalse(r['literal_invalid_token_detected'])

    def test_malformed_ids(self):
        for ids in ([True],[-1],[len(codec.ACTION_VOCABULARY)],['1'],None,(1,)):
            with self.subTest(ids=ids):
                self.assertEqual(a.diagnose_ids(ids,256,g,v,codec)['structural_class'],'MALFORMED_TOKEN_IDS')

    def test_invalid_bound_is_not_swallowed(self):
        with self.assertRaises(g.GrammarError):diagnose(MINIMAL,True)

    def test_no_input_mutation(self):
        ids=[codec.ACTION_TO_ID[t] for t in FORWARD+['CALL']];before=deepcopy(ids)
        a.diagnose_ids(ids,256,g,v,codec)
        self.assertEqual(ids,before)

    def test_proc_witness_precedes_later_unreachable_rejection(self):
        tokens=MINIMAL[:-1]+['PROC','p9','ALLOW','A','ENDALLOW','RUN','A','arg','v0','RETURN','v0','ENDPROC']
        r=diagnose(tokens)
        self.assertEqual(r['first_detected_noncompletable_choice']['token_index_zero_based'],14)
        self.assertEqual(r['structural_class'],'GRAMMAR_STATE_DEAD_END')
        self.assertEqual(r['terminal_completion_error'],'UNREACHABLE_PROCEDURE')
        self.assertIsNone(r['first_invalid_token'])

    def test_count_distinguishes_terminal_and_earlier_witness(self):
        row={'saved_generation_reason':'GENERATION_GRAMMAR_DEAD_END',
            'diagnosis':diagnose(FORWARD+['CALL']),'saved_reason_matches_replay':True}
        r=a.counts([row])
        self.assertEqual(r['rejected'],1)
        self.assertEqual(r['terminal_causes'],{'NO_LEGAL_CALL_TARGET':1})
        self.assertEqual(r['first_detected_noncompletable_choices'],{'CALL_WITH_NO_LEGAL_TARGET':1})

    def test_no_task_or_gold_argument(self):
        import inspect
        self.assertEqual(list(inspect.signature(a.diagnose_ids).parameters),['ids','max_length','grammar','viability','codec'])

if __name__=='__main__':unittest.main(verbosity=2)
