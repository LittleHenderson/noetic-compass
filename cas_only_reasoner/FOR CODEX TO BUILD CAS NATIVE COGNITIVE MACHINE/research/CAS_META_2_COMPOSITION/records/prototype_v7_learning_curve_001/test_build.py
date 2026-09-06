"""Small synthetic score records; no task generation or neural imports."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_learning_curve_tested',HERE/'build.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def synthetic():
    def metrics(total):
        return {'total':total, 'joint_correct':0, 'program_correct':0, 'binding_correct':0,
            'valid_programs':0, 'native_execution_performed':False, 'all_cases_in_denominator':True}
    def group(total):
        return {'expected_depths':[1,2,3], 'by_depth':{d:metrics(total) for d in m.DEPTHS}, 'overall':metrics(total*3)}
    curves = [{'epoch':epoch,'family':family,'selected':epoch==1,
        'validation':group(32),'training_probe':group(8)} for epoch in (0,1,*range(10,201,10)) for family in m.FAMILIES]
    checkpoints = {family:{stage:{'epoch':epoch,'family':family,'optimizer_steps':epoch*56,'bytes':100,
        'path':family+'_'+stage+'.pt','sha256':'a'*64,'validation':{'generation':group(32)}}
        for stage,epoch in (('initial',0),('selected',1),('final',200))} for family in m.FAMILIES}
    return {'status':'V7_SAVED_TRAINING_RECOUNT_PASSED','completed':True,'campaign_completed':False,
        'native_evaluation_completed':False,'learning_accepted':False,'neural_execution':False,
        'source_sha':m.SOURCE_SHA,'source_archive_sha256':m.ARCHIVE_SHA,'packet_sha256':m.PACKET_SHA,'job':m.JOB,
        'source_files_checked':603,'protected_files_checked':316,'completed_epochs':200,
        'optimizer_steps':{'cas':11200,'generic':11200},'curves':curves,
        'training_gate':{'checkpoints':checkpoints,'boundary':'Recorded actions only; no neural replay.'},
        'dataset':{'splits':{'train':{'tasks':896,'depths':{'1':128,'2':384,'3':384}},
            'validation':{'tasks':96,'depths':{'1':32,'2':32,'3':32}},'test':{'tasks':72,'depths':{'3':48,'4':24}}},
            'base':{'config':{'test_triplets':24}},'prototype':{'tasks':256,'allowed_split':'train'}},
        'processes':{'training':{'command':['python','--output','/opt/example/runs/cloud_job/campaign/training']}},
        'boundary':'Recorded actions, not native task correctness.'}


class Curves(unittest.TestCase):
    def texts(self, r):
        return (m.csv_text(m.CURVE_FIELDS,m.curve_rows(r)),m.csv_text(m.CHECKPOINT_FIELDS,m.checkpoint_rows(r)),m.markdown(r))

    def test_full_synthetic_coverage_and_render(self):
        r = synthetic(); self.assertEqual(len(m.validate(r)),44)
        checked = m.verify_rendered(r,*self.texts(r))
        self.assertEqual(checked['curve_csv_rows'],132)
        self.assertEqual(checked['checkpoint_csv_rows'],6)
        self.assertEqual(checked['markdown_data_cells_checked'],708)

    def test_actual_pinned_receipt_and_render(self):
        self.assertEqual(m.file_hash(m.EXPECTED_RECEIPT),m.RECEIPT_SHA)
        r = m.decode(m.EXPECTED_RECEIPT.read_bytes()); m.validate(r)
        checked = m.verify_rendered(r,*self.texts(r))
        self.assertTrue(checked['all_rendered_tables_and_csv_fields_match_receipt'])

    def test_missing_epoch_refused(self):
        r = synthetic(); r['curves'].pop()
        with self.assertRaisesRegex(ValueError,'ALL_MEASURED'):m.validate(r)

    def test_duplicate_epoch_refused(self):
        r = synthetic(); r['curves'].append(deepcopy(r['curves'][0]))
        with self.assertRaisesRegex(ValueError,'DUPLICATE_CURVE'):m.validate(r)

    def test_unrecorded_interpolation_refused(self):
        r = synthetic(); r['curves'][2]['epoch'] = 2
        with self.assertRaisesRegex(ValueError,'ALL_MEASURED'):m.validate(r)

    def test_wrong_validation_denominator_refused(self):
        r = synthetic(); r['curves'][0]['validation']['by_depth']['2']['total'] = 31
        with self.assertRaisesRegex(ValueError,'DENOMINATOR'):m.validate(r)

    def test_wrong_probe_denominator_refused(self):
        r = synthetic(); r['curves'][0]['training_probe']['by_depth']['2']['total'] = 7
        with self.assertRaisesRegex(ValueError,'DENOMINATOR'):m.validate(r)

    def test_native_metric_claim_refused(self):
        r = synthetic(); r['curves'][0]['validation']['by_depth']['1']['native_execution_performed'] = True
        with self.assertRaisesRegex(ValueError,'BOUNDARY'):m.validate(r)

    def test_boolean_numerator_refused(self):
        r = synthetic(); r['curves'][0]['validation']['by_depth']['1']['joint_correct'] = False
        with self.assertRaisesRegex(ValueError,'INTEGER'):m.validate(r)

    def test_joint_score_cannot_exceed_components(self):
        r = synthetic(); r['curves'][0]['validation']['by_depth']['1']['joint_correct'] = 1
        with self.assertRaisesRegex(ValueError,'JOINT_SCORE'):m.validate(r)

    def test_overall_recount_refused(self):
        r = synthetic(); r['curves'][0]['validation']['overall']['joint_correct'] = 1
        with self.assertRaisesRegex(ValueError,'OVERALL'):m.validate(r)

    def test_selected_is_not_final_epoch(self):
        r = synthetic(); m.validate(r)
        rows = m.curve_rows(r)
        self.assertTrue(all(x['final_selected_checkpoint'] for x in rows if x['epoch']==1))
        self.assertFalse(any(x['final_selected_checkpoint'] for x in rows if x['epoch']==200))

    def test_final_selection_history_mismatch_refused(self):
        r = synthetic(); r['training_gate']['checkpoints']['cas']['selected']['epoch'] = 200
        with self.assertRaisesRegex(ValueError,'SELECTED_HISTORY'):m.validate(r)

    def test_checkpoint_metric_copy_refused(self):
        r = synthetic(); r['training_gate']['checkpoints']['cas']['initial']['validation']['generation']['overall']['joint_correct'] = 1
        with self.assertRaisesRegex(ValueError,'CHECKPOINT_CURVE'):m.validate(r)

    def test_csv_numeric_mutation_refused(self):
        r = synthetic(); curve,cp,report = self.texts(r)
        changed = curve.replace('cas,0,1,0,32,0,8','cas,0,1,1,32,0,8',1)
        self.assertNotEqual(curve,changed)
        with self.assertRaisesRegex(ValueError,'CSV_VALUE'):m.verify_rendered(r,changed,cp,report)

    def test_csv_missing_row_refused(self):
        r = synthetic(); curve,cp,report = self.texts(r)
        with self.assertRaisesRegex(ValueError,'CSV_MISSING'):m.verify_rendered(r,'\n'.join(curve.splitlines()[:-1])+'\n',cp,report)

    def test_markdown_numeric_cell_mutation_refused(self):
        r = synthetic(); curve,cp,report = self.texts(r)
        with self.assertRaisesRegex(ValueError,'MARKDOWN_CELL'):m.verify_rendered(r,curve,cp,report.replace('0/32','1/32',1))

    def test_checkpoint_hash_mutation_refused(self):
        r = synthetic(); curve,cp,report = self.texts(r)
        with self.assertRaisesRegex(ValueError,'CHECKPOINT_CSV'):m.verify_rendered(r,curve,cp.replace('a'*64,'b'*64,1),report)

    def test_no_test_depth_two_invented(self):
        r = synthetic(); r['dataset']['splits']['test']['depths']['2'] = 1
        with self.assertRaisesRegex(ValueError,'ASSEMBLED_SPLITS'):m.validate(r)


if __name__ == '__main__': unittest.main(verbosity=2)
