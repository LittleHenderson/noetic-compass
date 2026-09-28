"""Focused AWS-only capture checks; real-parent parity is diagnostic_worker.witness."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from .observation import Capture, capture_helm, canonical, sha, retain_observation, reload_observation, reload_configuration_inputs
from .harness_capture_vendor.probe_runner import CaptureState


def capture(**changes):
    return Capture(**{**dict(checkpoint_sha256="a"*64, input_sha256="b"*64,
                            kind="parts", rounds=2, mode="OBSERVE_ONLY"), **changes})


def test_off_is_default_and_does_not_capture():
    c = capture(mode="OFF")
    x = torch.tensor([-2., 1.])
    assert c.emit("head.reach", x) is x
    assert c.receipt()["status"] == "DISABLED" and not c.events


def test_missing_site_never_reports_success():
    c = capture(); c.closed = c.cleanup_complete = True
    assert not c.receipt()["complete"]
    assert c.receipt()["coverage"]["graph.node_state"]["stored_calls"] == 0


def test_signed_detached_snapshot_does_not_retain_graph():
    c = capture(); x = torch.ones(2, 64, requires_grad=True) * -2
    before = x.clone()
    assert c.emit("graph.node_state", x) is x
    assert torch.equal(x, before)
    assert c.events[0]["signed_values"] == [-2.] * 128
    assert c.events[0]["coordinate_preview"][0]["signed_value"] == -2.
    with torch.no_grad(): x.add_(4)
    assert c.events[0]["signed_values"][0] == -2.
    json.dumps(c.receipt(), allow_nan=False)


def test_noop_and_observe_have_identical_capture_payloads():
    a,b = capture(),capture(mode="NO_OP_CONTROL")
    x = torch.arange(128, dtype=torch.float32).reshape(2,64)
    assert a.emit("graph.node_state",x) is b.emit("graph.node_state",x)
    assert a.events == b.events


def test_wrong_shape_is_incomplete_and_original_object_returns():
    c=capture(); x=torch.zeros(1,63)
    assert c.emit("graph.node_state",x) is x
    assert c.errors == ["graph.node_state:WRONG_SHAPE"] and not c.events


def test_wrong_round_is_refused_in_receipt():
    c=capture(); c.emit("graph.round_input",torch.zeros(1,64),1)
    assert "graph.round_input:WRONG_ROUND" in c.errors


def test_unknown_site_is_not_accepted():
    c=capture(); c.emit("fabricated.neuron",torch.zeros(1))
    assert c.errors == ["fabricated.neuron:UNKNOWN_SITE"]


def test_extra_call_is_not_accepted():
    c=capture(); x=torch.zeros(1,64)
    c.emit("graph.node_state",x);c.emit("graph.node_state",x)
    assert c.stored["graph.node_state"] == 1 and c.observed["graph.node_state"] == 2
    assert "graph.node_state:EXTRA_SITE_CALL" in c.errors


def test_byte_limit_precedes_tensor_conversion():
    c=capture(max_bytes=20);x=torch.zeros(1,64)
    assert c.emit("graph.node_state",x) is x
    assert c.bytes == 0 and c.errors == ["graph.node_state:CAPTURE_BYTE_LIMIT"]


def test_elapsed_capture_limit_is_enforced():
    c=capture();c.started-=61
    c.emit("graph.node_state",torch.zeros(1,64))
    assert c.errors == ["graph.node_state:CAPTURE_TIME_LIMIT"]


def test_nonfinite_capture_is_incomplete():
    c=capture();x=torch.full((1,64),float("nan"))
    assert c.emit("graph.node_state",x) is x
    assert c.errors == ["graph.node_state:NONFINITE_CAPTURE"]


def test_wrong_parent_refused_before_forward(tmp_path):
    parent=tmp_path/'copy.pt';parent.write_bytes(b'wrong')
    with pytest.raises(ValueError,match='WRONG_CHECKPOINT_BYTES'):
        with capture_helm(SimpleNamespace(),{},checkpoint_path=parent,
                          expected_checkpoint_sha256='a'*64,kind='parts'): pass


def test_nested_or_incumbent_observer_refused(tmp_path):
    with pytest.raises(ValueError,match='INCUMBENT_OR_NESTED_OBSERVER'):
        with capture_helm(SimpleNamespace(_graph=object()),{},checkpoint_path=tmp_path/'missing',
                          expected_checkpoint_sha256='a'*64,kind='parts'): pass


def test_unsupported_active_mode_refused():
    with pytest.raises(ValueError,match='UNSUPPORTED_CAPTURE_MODE'):
        capture(mode='SUPPRESS')


def test_non_parts_reach_refused():
    with pytest.raises(ValueError,match='UNSUPPORTED_CAPTURE_MODE_OR_KIND'):
        capture(kind='world_head')


def test_pythia_container_is_reused_without_probe_coefficients():
    c=capture();x=torch.zeros(1,64);c.emit('graph.node_state',x)
    assert CaptureState.__module__.endswith('harness_capture_vendor.probe_runner')
    assert c.events[0]['cas_label'] == 'UNKNOWN_NOT_FITTED'
    assert c.events[0]['basis'] == 'WITHIN_CHECKPOINT_ONLY'


def test_host_retains_incomplete_and_detects_tampering(admitted_case):
    host,_,baseline,_=admitted_case
    c=capture();c.closed=c.cleanup_complete=True
    anchor=retain_observation(host,c.receipt(),native_run_id=baseline['run_id'])
    result=reload_observation(host,anchor['ledger_event_digest'])
    assert not result['observation']['complete'] and not result['promotion']
    path=host.evidence_root/anchor['path'];original=path.read_bytes()
    try:
        path.write_bytes(original[:-2])
        with pytest.raises(ValueError,match='CAPTURE_RELOAD_INTEGRITY'):
            reload_observation(host,anchor['ledger_event_digest'])
    finally:path.write_bytes(original)


def test_forged_host_refused():
    with pytest.raises(ValueError,match='EXISTING_HOST_REQUIRED'):
        retain_observation(SimpleNamespace(),capture().receipt(),native_run_id='forged')


def _synthetic_complete_parts_receipt():
    # This fixture exercises conversion only. It is not a real HELM forward.
    c=capture(rounds=8)
    for site,expected in c.expected.items():
        for call in range(expected):
            if site.startswith('graph.'):
                value=torch.full((1,64),-2.)
            elif site=='head.node':
                value=torch.tensor([[-1.,2.]])
            elif site=='input.mapping':
                value={'query':{'kind_name':'parts'},'synthetic_fixture':True}
            else:
                value={'synthetic_fixture':True}
            c.emit(site,value,call if site.startswith('graph.round_') else None)
    c.closed=c.cleanup_complete=True
    receipt=c.receipt()
    assert receipt['complete']
    return receipt


def test_anchored_configuration_conversion_preserves_coordinates(admitted_case):
    host,_,baseline,_=admitted_case
    receipt=_synthetic_complete_parts_receipt()
    anchor=retain_observation(host,receipt,native_run_id=baseline['run_id'])
    result=reload_configuration_inputs(host,anchor['ledger_event_digest'])
    assert result['complete'] and result['named_configurations']==[] and not result['promotion']
    raw=result['capture_series']['graph.node_state'][0]
    assert raw.dtype=='float32' and raw.signed_values==(-2.,)*64
    assert raw.checkpoint_sha256==receipt['checkpoint_sha256']
    assert len(result['capture_series']['head.reach'])==0
    assert result['rpa_projection']['execute_action'] is None


def test_configuration_readout_keeps_missing_capture_incomplete(admitted_case):
    host,_,baseline,_=admitted_case
    c=capture(rounds=8);c.closed=c.cleanup_complete=True
    anchor=retain_observation(host,c.receipt(),native_run_id=baseline['run_id'])
    result=reload_configuration_inputs(host,anchor['ledger_event_digest'])
    assert result['status']=='INCOMPLETE_CAPTURE_INPUTS' and not result['complete']
    assert result['named_configurations']==[]
    assert all(not series for series in result['capture_series'].values())
    with pytest.raises(ValueError,match='EXTERNAL_OBSERVATION_ANCHOR_REQUIRED'):
        reload_configuration_inputs(host,'f'*64)


def test_configuration_readout_refuses_mixed_event_parent(admitted_case):
    host,_,baseline,_=admitted_case
    receipt=_synthetic_complete_parts_receipt()
    receipt['events'][0]['checkpoint_sha256']='c'*64
    receipt['receipt_sha256']=sha(canonical({k:v for k,v in receipt.items() if k!='receipt_sha256'}))
    anchor=retain_observation(host,receipt,native_run_id=baseline['run_id'])
    with pytest.raises(ValueError,match='CONFIGURATION_EVENT_IDENTITY'):
        reload_configuration_inputs(host,anchor['ledger_event_digest'])
