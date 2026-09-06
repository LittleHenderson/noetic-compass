"""Pure diagnostic input/scoring gates; no local CUDA training."""
from copy import deepcopy
import pytest

from cas_meta2 import fit_diagnostic_v5 as fit
from cas_meta2.codec import action_to_ids
from cas_meta2.selection_v3 import target_token_roles


def action(depth=1):
    names = ['main'] + [f'p{i}' for i in range(depth - 1)]
    procedures = {}
    for i, name in enumerate(names):
        step = ({'kind': 'CALL', 'procedure': names[i + 1]} if i + 1 < depth
                else {'kind': 'RUN', 'cjt_id': 'A'})
        procedures[name] = {'input': 'arg', 'allowed_cjts': ['A'],
            'steps': [{**step, 'input': 'arg', 'output': 'v0'}], 'return': 'v0'}
    return {'binding': 0, 'program': {'schema': 'cas-meta2-program/0.1',
                                    'entry': 'main', 'procedures': procedures}}


def tasks():
    return [{'task_id': f'diagnostic-train-{depth}-{i:02d}',
             'provenance': {'depth': depth, 'evaluation_group': 'training'},
             'target': action(depth), 'public': {'problem': 'Synthetic fixture only.',
             'observations': [{'slot': slot, 'tag': tag, 'values': [0.1] * 8}
                              for slot, tag in enumerate(('copper', 'amber', 'jade'))]}}
            for depth in (1, 2, 3) for i in range(9)]


def test_probe_is_deterministic_balanced_and_does_not_mutate():
    source = tasks()
    before = deepcopy(source)
    selected = fit.select_probe(list(reversed(source)))
    assert selected == fit.select_probe(source)
    assert [t['provenance']['depth'] for t in selected] == [1] * 8 + [2] * 8 + [3] * 8
    assert all(not t['task_id'].endswith('08') for t in selected)
    assert source == before


@pytest.mark.parametrize('mutation', ['heldout', 'duplicate', 'depth', 'missing_depth', 'target'])
def test_bad_training_inputs_are_refused(mutation):
    source = tasks()
    if mutation == 'heldout': source[0]['provenance']['evaluation_group'] = 'validation'
    elif mutation == 'duplicate': source[0]['task_id'] = source[1]['task_id']
    elif mutation == 'depth': source[0]['provenance']['depth'] = 3
    elif mutation == 'missing_depth': source = source[:18]
    else: source[0]['target']['binding'] = 99
    with pytest.raises(ValueError): fit.select_probe(source)


def test_unpinned_training_file_is_refused(tmp_path):
    path = tmp_path / 'train.json'
    path.write_text('[]')
    with pytest.raises(ValueError, match='BYTES_CHANGED'): fit.read_training(path)


def test_roles_count_each_known_target_once_and_localize_error():
    target = action(3)
    ids = action_to_ids(target)[1:]
    perfect = fit.role_counts([target], [ids], [ids])
    assert sum(row['total'] for row in perfect.values()) == len(ids)
    assert all(row['correct'] == row['total'] for row in perfect.values())
    roles = target_token_roles(target)[1:]
    wrong = ids.copy()
    wrong[roles.index('call_target')] = 0
    scored = fit.role_counts([target], [wrong], [ids])
    assert scored['call_target']['correct'] == perfect['call_target']['correct'] - 1
    assert {k: v for k, v in scored.items() if k != 'call_target'} == {
        k: v for k, v in perfect.items() if k != 'call_target'}


@pytest.mark.parametrize('mutation', ['length', 'target', 'bool', 'range', 'batch'])
def test_role_scoring_rejects_misalignment(mutation):
    target = action()
    ids = action_to_ids(target)[1:]
    prediction, expected = ids.copy(), ids.copy()
    if mutation == 'length': prediction.pop()
    elif mutation == 'target': expected[0] = 0
    elif mutation == 'bool': prediction[0] = True
    elif mutation == 'range': prediction[0] = 9999
    with pytest.raises(ValueError):
        fit.role_counts([target], [] if mutation == 'batch' else [prediction], [expected])


def context(monkeypatch):
    job = 'cas-meta2-20260906000000-01234567'
    monkeypatch.setattr(fit.sys, 'platform', 'linux')
    monkeypatch.setenv('CAS_META2_RUN_FIT_DIAGNOSTIC', '1')
    monkeypatch.setenv('CAS_META2_AWS_JOB_ID', job)
    return job


@pytest.mark.parametrize('seconds', [True, 0, 59, 2701, 60.0])
def test_time_bounds(monkeypatch, seconds):
    with pytest.raises(ValueError, match='TIME_BOUND'):
        fit.require_request(context(monkeypatch), seconds)


def test_explicit_context_does_not_itself_claim_aws_execution(monkeypatch):
    assert fit.require_request(context(monkeypatch), 60) is None


@pytest.mark.parametrize('mutation', ['platform', 'enable', 'identity', 'job'])
def test_run_refuses_before_training_file_or_neural_import(monkeypatch, mutation):
    job = context(monkeypatch)
    if mutation == 'platform': monkeypatch.setattr(fit.sys, 'platform', 'win32')
    elif mutation == 'enable': monkeypatch.delenv('CAS_META2_RUN_FIT_DIAGNOSTIC')
    elif mutation == 'identity': monkeypatch.setenv('CAS_META2_AWS_JOB_ID', 'wrong')
    else: job = 'wrong'
    with pytest.raises(ValueError, match='FIT_'):
        fit.run('nonexistent', 'nonexistent', job=job, max_seconds=60)
