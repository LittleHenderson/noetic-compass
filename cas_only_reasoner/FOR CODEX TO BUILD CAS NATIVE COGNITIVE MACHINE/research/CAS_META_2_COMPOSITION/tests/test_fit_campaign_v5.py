"""Simulated stored fit checks; no model training or native execution."""
from copy import deepcopy
from pathlib import Path
import pytest

from cas_meta2 import fit_campaign_v5 as campaign
from cas_meta2.fit_diagnostic_v5 import select_probe
from cas_meta2.selection_v3 import depth_generated_metrics
from test_fit_diagnostic_v5 import tasks as synthetic_tasks


@pytest.fixture
def evidence(monkeypatch, tmp_path):
    tasks = select_probe(synthetic_tasks())
    ids = [t['task_id'] for t in tasks]
    job = 'cas-meta2-20260906000000-01234567'
    table = {}
    process = {'completed': True, 'returncode': 0, 'timed_out': False, 'pid': 123}
    table['processes/training/process_receipt.json'] = process
    history = []
    for epoch in (0, 1, *range(10, 201, 10)):
        families = {}
        for family in ('cas', 'generic'):
            actions = [deepcopy(task['target']) for task in tasks]
            families[family] = {'actions': actions, 'generation': depth_generated_metrics(actions, tasks),
                                'teacher_forced_roles': {}}
        row = {'epoch': epoch, 'optimizer_steps': {'cas': epoch * 3, 'generic': epoch * 3}, 'families': families}
        table[f'fit/measurement_{epoch:04d}.json'] = row
        history.append({'epoch': epoch, 'optimizer_steps': dict(row['optimizer_steps']),
            'families': {f: {k: deepcopy(v) for k, v in values.items() if k != 'actions'}
                         for f, values in families.items()}})
    receipt = {'schema': campaign.SCHEMA, 'completed': True, 'job': job,
        'training_sha256': campaign.TRAIN_SHA, 'task_ids': ids, 'training_examples': 24,
        'epochs_requested': 200, 'batch_size': 8, 'seed': 7, 'vocabulary_training_examples': 3072,
        'optimizer_steps': {'cas': 600, 'generic': 600}, 'held_out_evaluation': False,
        'native_execution': False, 'learning_accepted': False, 'history': history}
    for field, epoch in (('initial_checkpoints', 0), ('final_checkpoints', 200)):
        receipt[field] = {f: {'path': f'{f}_epoch_{epoch:04d}.pt', 'sha256': 'a' * 64}
                          for f in ('cas', 'generic')}
    table['fit/fit_receipt.json'] = receipt
    monkeypatch.setattr(campaign, 'checked_json', lambda p: table[Path(p).relative_to(tmp_path).as_posix()])
    monkeypatch.setattr(campaign, 'file_hash', lambda p: 'a' * 64)
    monkeypatch.setattr(campaign, 'read_training', lambda p: (tasks, tasks))
    return tmp_path, job, ids, table


def test_complete_simulated_recount_covers_both_families_and_every_epoch(evidence):
    output, job, ids, table = evidence
    result = campaign.check_fit(output, job, ids)
    assert len(result['measurement_sha256']) == 22
    assert set(result['final_generation']) == {'cas', 'generic'}
    assert all(v['overall']['joint_correct'] == 24 for v in result['final_generation'].values())


@pytest.mark.parametrize('mutation', ['child_exit', 'child_bool', 'missing_epoch', 'wrong_action',
    'wrong_steps', 'wrong_job', 'heldout_claim', 'accepted_claim', 'checkpoint_path', 'checkpoint_hash'])
def test_incomplete_or_forged_fit_evidence_is_refused(evidence, mutation):
    output, job, ids, table = evidence
    receipt = table['fit/fit_receipt.json']
    if mutation == 'child_exit': table['processes/training/process_receipt.json']['returncode'] = 1
    elif mutation == 'child_bool': table['processes/training/process_receipt.json']['returncode'] = False
    elif mutation == 'missing_epoch': receipt['history'].pop()
    elif mutation == 'wrong_action': table['fit/measurement_0200.json']['families']['cas']['actions'][0]['binding'] = 1
    elif mutation == 'wrong_steps': table['fit/measurement_0010.json']['optimizer_steps']['cas'] = 29
    elif mutation == 'wrong_job': receipt['job'] = 'wrong'
    elif mutation == 'heldout_claim': receipt['held_out_evaluation'] = True
    elif mutation == 'accepted_claim': receipt['learning_accepted'] = True
    elif mutation == 'checkpoint_path': receipt['final_checkpoints']['cas']['path'] = '../other.pt'
    else: receipt['final_checkpoints']['cas']['sha256'] = 'b' * 64
    with pytest.raises(RuntimeError, match='FIT_'):
        campaign.check_fit(output, job, ids)
