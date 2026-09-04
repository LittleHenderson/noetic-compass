from __future__ import annotations

import pytest
import torch

from cas_cjt.readiness import DWPProfile
from cas_cjt.state import make_readiness
from cas_cjt.types import ReadinessAxisName, ReadinessStatus


@pytest.mark.parametrize(
    ("axis", "gate_name"),
    (
        (ReadinessAxisName.DESIRE, "desire_gate"),
        (ReadinessAxisName.WISDOM, "wisdom_gate"),
        (ReadinessAxisName.POWER, "power_gate"),
    ),
)
def test_each_readiness_axis_independently_closes_flow_and_keeps_its_reason(
    axis: ReadinessAxisName, gate_name: str
) -> None:
    state = make_readiness(insufficient_axes=(axis,))
    profile = DWPProfile.from_state(state, torch.ones(2, 3))
    assert state.first_unmet is axis
    assert getattr(state, axis.value.lower()).status is ReadinessStatus.INSUFFICIENT
    assert getattr(state, axis.value.lower()).reason_codes == (
        f"{axis.value}_INSUFFICIENT",
    )
    assert torch.count_nonzero(getattr(profile, gate_name)).item() == 0
    assert torch.count_nonzero(profile.effective_readiness).item() == 0
    assert not state.hard_open
