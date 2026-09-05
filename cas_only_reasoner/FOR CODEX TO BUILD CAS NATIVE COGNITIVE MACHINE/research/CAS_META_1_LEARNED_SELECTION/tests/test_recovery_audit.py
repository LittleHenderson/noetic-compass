"""Small pure checks for audit containment; no real torch or neural execution."""
import copy
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from tools import audit_recovery_semantics as audit


def fake_guard_dependencies():
    class FakeModule:
        def __init__(self): self.created = True
        def __call__(self): return 'called'
    instances = []
    class FakeDispatch:
        def __enter__(self): instances.append(self); return self
        def __exit__(self, *args): return False
    torch = SimpleNamespace(nn=SimpleNamespace(Module=FakeModule), load=lambda: 'loaded', __version__='synthetic')
    return torch, FakeDispatch, instances


def test_guard_blocks_construction_calls_loads_and_tensor_dispatch_then_restores():
    torch, dispatch, modes = fake_guard_dependencies()
    existing = torch.nn.Module()
    original = (torch.nn.Module.__init__, torch.nn.Module.__call__, torch.load)
    with audit.prohibit_neural_work(torch, dispatch) as state:
        for operation in (torch.nn.Module, existing, torch.load, lambda: modes[0].__torch_dispatch__(None, None)):
            with pytest.raises(audit.AuditInvalid, match='NEURAL_OR_TENSOR_WORK_FORBIDDEN'):
                operation()
        assert state['blocked_attempts'] == ['Module.__init__','Module.__call__','torch.load','tensor_operation']
    assert (torch.nn.Module.__init__, torch.nn.Module.__call__, torch.load) == original
    assert torch.nn.Module().created and existing() == 'called' and torch.load() == 'loaded'


def test_guard_restores_hooks_on_unrelated_failure():
    torch, dispatch, _ = fake_guard_dependencies()
    original = torch.nn.Module.__init__
    with pytest.raises(RuntimeError, match='synthetic failure'):
        with audit.prohibit_neural_work(torch, dispatch):
            raise RuntimeError('synthetic failure')
    assert torch.nn.Module.__init__ is original


@pytest.mark.parametrize('mutation', ['changed','extra'])
def test_extraction_requires_exact_packet_file_set_and_bytes(tmp_path, monkeypatch, mutation):
    monkeypatch.setattr(audit, 'ROOT', tmp_path)
    extracted = tmp_path/'records'/'extracted'; extracted.mkdir(parents=True)
    (extracted/'native.db').write_bytes(b'fake durable bytes')
    archive = tmp_path/'packet.zip'
    with zipfile.ZipFile(archive, 'w') as target:
        target.writestr('native.db', b'fake durable bytes')
    assert audit.verify_extraction(archive, extracted) == {'native.db':audit.file_hash(extracted/'native.db')}
    if mutation == 'changed': (extracted/'native.db').write_bytes(b'changed')
    else: (extracted/'extra.txt').write_text('unlisted')
    with pytest.raises(audit.AuditInvalid, match='FILE_SET_OR_BYTES'):
        audit.verify_extraction(archive, extracted)


def test_audit_paths_cannot_leave_owned_records(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'ROOT', tmp_path)
    for path in (tmp_path, tmp_path/'records', tmp_path/'runs'/'audit', tmp_path/'records'/'..'/'elsewhere'):
        with pytest.raises(audit.AuditInvalid, match='OWNED_RECORDS'):
            audit.owned_records(path)


def case_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'ROOT', tmp_path)
    recovery = tmp_path/'records'/'extracted'/'cloud_job'/'recovery'
    files, tasks = {}, [{'case_index':index} for index in range(72)]
    verdict = {'success':True, 'reasons':[]}
    for arm in audit.ARMS:
        files[recovery/(arm+'_case_results.json')] = [{'case_index':index,'verification':dict(verdict)} for index in range(72)]
    for index in range(72):
        case = recovery/'cases'/f'case_{index:04d}'
        for arm in ('reference', *audit.ARMS):
            files[case/arm/'result.json'] = {'case_index':index,'arm':arm,'output_dir':'/immutable/cloud/path'}
    monkeypatch.setattr(audit, 'read', lambda path:files[Path(path)])
    calls = []
    def verifier(task, result, reference):
        assert result['case_index'] == reference['case_index'] == task['case_index']
        assert Path(result['output_dir']).is_relative_to(recovery)
        assert result['native_database'] == str(Path(result['output_dir'])/'native.db')
        calls.append((task['case_index'], result['arm']))
        return dict(verdict)
    return recovery, files, tasks, verifier, calls


def test_audit_rechecks_72_references_and_360_verdicts_without_mutating_records(tmp_path, monkeypatch):
    recovery, files, tasks, verifier, calls = case_fixture(tmp_path, monkeypatch)
    original = copy.deepcopy(files)
    result = audit.verify_cases(recovery, tasks, verifier)
    assert result['references_reverified'] == 72 and result['arm_executions_reverified'] == 360
    assert len(calls) == 432 and all(value == 72 for value in result['success_counts'].values())
    assert files == original


def test_audit_refuses_a_changed_recorded_verdict(tmp_path, monkeypatch):
    recovery, files, tasks, verifier, _ = case_fixture(tmp_path, monkeypatch)
    files[recovery/'cas_trained_case_results.json'][3]['verification']['success'] = False
    with pytest.raises(audit.AuditInvalid, match='RECORDED_VERDICT_MISMATCH:cas_trained:3'):
        audit.verify_cases(recovery, tasks, verifier)


def test_audit_refuses_missing_cases_before_verifying_anything(tmp_path, monkeypatch):
    recovery, files, tasks, verifier, calls = case_fixture(tmp_path, monkeypatch)
    files[recovery/'rule_case_results.json'].pop()
    with pytest.raises(audit.AuditInvalid, match='MISSING_DUPLICATE_OR_REORDERED'):
        audit.verify_cases(recovery, tasks, verifier)
    assert calls == []
