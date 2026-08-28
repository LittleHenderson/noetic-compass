"""CAS-SM v0.1: capability claims derived from live probes + artifacts;
typed verdicts; the machine knows what it cannot do."""

from selfmodel.model import CAPABILITIES, SelfModel

import pytest


@pytest.fixture(scope="module")
def model():
    return SelfModel()


def test_every_claim_ran_a_live_probe(model):
    assert len(model.entries) == len(CAPABILITIES)
    for entry in model.entries.values():
        assert "probe_note" in entry and entry["probe_note"]


def test_can_verdicts_carry_evidence_artifacts(model):
    for name, entry in model.entries.items():
        if entry["verdict"] == "CAN":
            assert entry["artifact"], f"{name}: CAN without artifact"
            assert entry["probe_ok"] is True


def test_core_capabilities_are_can(model):
    for name in ("reasoning", "mathematics", "discovery", "language",
                 "tools", "learning", "self_improvement",
                 "long_term_goals"):
        assert model.can(name)["verdict"] == "CAN", name


def test_the_machine_knows_what_it_cannot_do(model):
    assert model.cannot_list() == ["coding", "vision"]
    answer = model.can("vision")
    assert answer["verdict"] == "CANNOT"
    assert "no machinery" in answer["reason"]


def test_unknown_for_capabilities_with_no_evidence(model):
    answer = model.can("telepathy")
    assert answer["verdict"] == "UNKNOWN"
    assert "does not bluff" in answer["reason"]


def test_limits_are_first_class(model):
    language = model.can("language")
    assert "fragment grammar" in language["limits"]
    discovery = model.can("discovery")
    assert "trivial to human mathematics" in discovery["limits"]


def test_probe_failure_downgrades_the_claim(monkeypatch):
    """An artifact with a failing probe must NOT yield CAN."""
    import selfmodel.model as sm

    broken = [dict(spec) for spec in sm.CAPABILITIES]
    for spec in broken:
        if spec["name"] == "mathematics":
            spec["probe"] = lambda: (False, "probe artificially broken")
    monkeypatch.setattr(sm, "CAPABILITIES", broken)
    downgraded = sm.SelfModel()
    assert downgraded.can("mathematics")["verdict"] == "UNKNOWN"


def test_model_is_deterministic():
    assert SelfModel().model_digest == SelfModel().model_digest
