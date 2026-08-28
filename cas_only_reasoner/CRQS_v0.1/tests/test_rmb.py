"""RMB reference bands: per-dimension verdicts, identical-conditions
gate, refusal of single-number equivalence."""

import pytest

from crqs.rmb import (BAND_NAMES, IDENTICAL_CONDITIONS, OUTCOMES,
                      RMBError, band_summary, format_rmb, validate_rmb)


def _conditions(**overrides):
    conditions = {c: True for c in IDENTICAL_CONDITIONS}
    conditions.update(overrides)
    return conditions


def _example():
    return {
        "status": "RUN",
        "identical_conditions": _conditions(),
        "bands": [
            {"band": "GPT-1",
             "domains": [
                 {"domain": "question answering", "outcome": "PASS",
                  "evidence": "artifacts/rmb/g1_qa.json"},
                 {"domain": "entailment", "outcome": "PASS",
                  "evidence": "artifacts/rmb/g1_nli.json"}]},
            {"band": "GPT-3",
             "domains": [
                 {"domain": "instruction following", "outcome": "PASS",
                  "evidence": "artifacts/rmb/g3_instr.json"},
                 {"domain": "broad factual coverage", "outcome": "BELOW",
                  "evidence": "artifacts/rmb/g3_facts.json"},
                 {"domain": "mathematical verification", "outcome": "ABOVE",
                  "evidence": "artifacts/rmb/g3_math.json"},
                 {"domain": "long-term memory", "outcome": "CAS_SPECIFIC",
                  "evidence": "artifacts/rmb/g3_mem.json"}]},
        ],
    }


def test_bands_are_the_historical_references():
    assert BAND_NAMES == ["GPT-1", "GPT-2", "GPT-3"]
    assert "PASS" in OUTCOMES and "CAS_SPECIFIC" in OUTCOMES


def test_not_run_is_the_honest_default():
    assert validate_rmb({}) == {"status": "NOT RUN"}
    assert validate_rmb({"status": "NOT RUN"}) == {"status": "NOT RUN"}
    assert format_rmb({}) == ["    NOT RUN"]


def test_band_results_without_run_status_refused():
    with pytest.raises(RMBError):
        validate_rmb({"status": "NOT RUN", "bands": [{"band": "GPT-1"}]})


def test_single_number_equivalence_refused():
    rmb = _example()
    rmb["equivalence_claim"] = "GPT-3 equivalent"
    with pytest.raises(RMBError, match="per "):
        validate_rmb(rmb)


def test_identical_conditions_gate():
    rmb = _example()
    rmb["identical_conditions"] = _conditions(held_out_split=False)
    with pytest.raises(RMBError, match="held_out_split"):
        validate_rmb(rmb)


def test_every_domain_needs_an_evidence_artifact():
    rmb = _example()
    del rmb["bands"][0]["domains"][0]["evidence"]
    with pytest.raises(RMBError, match="no evidence artifact"):
        validate_rmb(rmb)


def test_band_summary_pass_partial():
    rmb = _example()
    assert band_summary(rmb["bands"][0]) == "GPT-1 band: PASS"
    assert band_summary(rmb["bands"][1]) == "GPT-3 band: PARTIAL"


def test_report_renders_per_dimension():
    lines = format_rmb(_example())
    text = "\n".join(lines)
    assert "GPT-1 band: PASS" in text
    assert "GPT-3 band: PARTIAL" in text
    assert "instruction following: PASS" in text
    assert "broad factual coverage: BELOW" in text
    assert "mathematical verification: ABOVE" in text
    assert "long-term memory: CAS-specific capability" in text


def test_cncm_manifest_stays_not_run():
    from conftest import load_manifest
    manifest = load_manifest("manifest_cncm.json")
    assert format_rmb(manifest.get("rmb", {})) == ["    NOT RUN"]


def test_equivalence_claim_refused_even_under_not_run():
    with pytest.raises(RMBError, match="refused"):
        validate_rmb({"status": "NOT RUN", "equivalence_claim": "GPT-3"})


def test_truthy_placeholder_attestation_refused():
    rmb = _example()
    rmb["identical_conditions"] = {c: "TODO" for c in IDENTICAL_CONDITIONS}
    with pytest.raises(RMBError, match="explicit true"):
        validate_rmb(rmb)


def test_band_summary_refuses_empty_domains():
    with pytest.raises(RMBError, match="no domain"):
        band_summary({"band": "GPT-1", "domains": []})
