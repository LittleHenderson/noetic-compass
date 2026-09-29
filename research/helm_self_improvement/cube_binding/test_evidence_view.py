"""Read-only existing-host projection specifications, NOT real HELM evidence."""
import pytest

from ..conftest import host_for
from ..native_bridge import run_baseline
from ..observation import Capture, retain_observation
from ..diagnostic_configuration import CORE_ROUNDS
from .contracts import digest
from .evidence_view import binding_evidence_view
from .test_public_task_adapter import compiled


def retained(tmp_path):
    host = host_for(tmp_path / "host", baseline=True)
    native, _ = run_baseline(host)
    packet = compiled()["packet"]
    capture = Capture(checkpoint_sha256="a" * 64, input_sha256=digest(packet), kind="parts",
                      rounds=CORE_ROUNDS, mode="OBSERVE_ONLY")
    capture.closed = capture.cleanup_complete = True
    anchor = retain_observation(host, capture.receipt(), native_run_id=native["run_id"])
    return host, packet, anchor["ledger_event_digest"]


def test_missing_capture_stays_missing_and_reload_has_no_write_side_effect(tmp_path):
    host, packet, event = retained(tmp_path)
    before = host.events()
    first = binding_evidence_view(host, event, packet)
    second = binding_evidence_view(host, event, packet)
    assert first == second and before == host.events()
    assert first["measurement"]["complete"] is False
    assert first["readonly"] and first["execute_action"] is None and first["promotion"] is False
    assert all(first[k] is None for k in ("model_inferred_binding", "reconstruction", "counterfactual", "evaluation"))
    assert "events" not in first and "signed_values" not in str(first)


def test_wrong_external_anchor_is_refused(tmp_path):
    host, packet, _ = retained(tmp_path)
    with pytest.raises(ValueError, match="EXTERNAL_OBSERVATION_ANCHOR_REQUIRED"):
        binding_evidence_view(host, "f" * 64, packet)
