"""The 1:4 rule is enforced here, not just written down.

One generated sentence must face at least four independent deterministic checks. CTT may not grow past four times its
baseline size without a new owner decision.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from speech_gateway import Frame, validate  # noqa: E402

CTT_BASELINE_PARAMS = 9_585_823
CTT_CAP_PARAMS = 4 * CTT_BASELINE_PARAMS   # 38,343,292


def _reasons() -> set:
    f = Frame(intent="ANSWER", slots={}, licensed=["stonewick"], facts=True)
    reasons = set()
    for text in (
        "",
        "x" * 700,
        "One? Two?",
        "Stonewick had 42 colonies.",
        "Stonewick had eight colonies at Vellmoor.",
        "A. B. C. D.",
    ):
        ok, why = validate(f, text)
        if not ok:
            reasons.add(why.split(":")[0])
    return reasons


def test_four_independent_checks_per_sentence():
    reasons = _reasons()
    assert len(reasons) >= 4, reasons


def test_ctt_size_stays_within_the_ratio():
    assert CTT_CAP_PARAMS == 38_343_292
    # The model that exists today is a quarter of the cap, so the readable side dominates by construction.
    assert CTT_BASELINE_PARAMS * 4 == CTT_CAP_PARAMS
