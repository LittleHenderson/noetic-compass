"""The eight authority invariants, as executable constraints."""

from conftest import load_fixture
from cas_math.acceptance import decide_math
from cas_math.lessons import propose_repairs
from cas_math.m1 import CCB_M1


def test_no_verified_without_checker():
    # The false identity must never be marked VERIFIED by the machine,
    # even when the incorrect procedure is in the ruleset.
    package = load_fixture("mistake_package.json")
    m1 = CCB_M1(package)
    result = m1.verify_identity(package["mistake_task"], package)
    assert result["outcome"]["verdict"] == "REJECTED"


def test_repairs_never_target_the_checker():
    package = load_fixture("mistake_package.json")
    m1 = CCB_M1(package)
    cycle = m1.mistake_cycle(package["mistake_task"])
    repairs = []
    for decision in cycle["decisions"]:
        repairs.append(decision["repair"])
    assert repairs
    for repair in repairs:
        assert repair.get("kind") == "replace_rule"
        assert repair.get("target") not in ("checker", "benchmarks")
        assert repair.get("rule_id") != "checker"


def test_checker_targeted_repair_rejected_as_protected():
    package = load_fixture("mistake_package.json")
    child = dict(package)
    child["revision"] = 2
    decision = decide_math(
        package, child,
        {"kind": "modify_checker", "target": "checker"},
        {}, {})
    assert decision["verdict"] == "REJECTED_AS_PROTECTED"
    checks = {c["check"]: c["passed"] for c in decision["checks"]}
    assert checks["checker_untouched"] is False


def test_definitions_versioned_not_silent():
    package = load_fixture("mistake_package.json")
    m1 = CCB_M1(package)
    m1.mistake_cycle(package["mistake_task"])
    # History records both rulesets with digests: no silent change.
    assert len(m1.history) == 2
    assert m1.history[1]["revision"] == 2
    assert m1.history[1]["package_digest"] != m1.history[0]["package_digest"]
    assert "square_sum" not in m1.history[1]["ruleset"]["procedures"]
