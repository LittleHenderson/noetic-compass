from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "stage22_6_inversion_scanner.py"
RUNNER = ROOT / "run_stage22_6_inversion_proxy_attribution.py"


def _load(path: Path, name: str):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_scanner_measures_clean_row_as_numeric_allow():
    scanner = _load(SCANNER, "scanner")
    row = {
        "rpm_satisfaction": 1.0,
        "gap_map_summary": {
            "foundation": {"vote_count": 3, "conflict_count": 0},
            "drive": {"vote_count": 3, "conflict_count": 0},
            "register": {"vote_count": 3, "conflict_count": 0},
            "trace_states": {"focus": "stable", "final": "stable", "mean": "stable"},
        },
    }
    scan = scanner.scan_inversion_from_diagnostic_row(row)
    assert scan["attribution_status"] == "numeric_measured"
    assert scan["decision"] == "allow"
    assert scan["flag_count"] == 0
    assert scan["axis_scores"] == [0.0] * 7


def test_scanner_flags_conflicted_factor_row():
    scanner = _load(SCANNER, "scanner_conflict")
    row = {
        "rpm_satisfaction": 0.0,
        "gap_map_summary": {
            "foundation": {"vote_count": 3, "conflict_count": 2},
            "drive": {"vote_count": 3, "conflict_count": 1},
            "register": {"vote_count": 3, "conflict_count": 1},
            "trace_states": {"focus": "conflicted", "final": "uncertain", "mean": "stable"},
        },
    }
    scan = scanner.scan_inversion_from_diagnostic_row(row)
    assert scan["attribution_status"] == "numeric_measured"
    assert scan["decision"] == "suppress"
    assert scan["flag_count"] >= 4
    assert len(scan["axis_scores"]) == 7


def test_scanner_marks_missing_gap_map_not_available():
    scanner = _load(SCANNER, "scanner_missing_gap")
    scan = scanner.scan_inversion_from_diagnostic_row({"rpm_satisfaction": 1.0})
    assert scan["attribution_status"] == "not_available"
    assert scan["decision"] == "not_available"
    assert scan["reason"] == "missing_gap_map_summary"
    assert scan["axis_scores"] == [None] * 7


def test_scanner_marks_partial_vote_profile_not_available():
    scanner = _load(SCANNER, "scanner_partial_votes")
    scan = scanner.scan_inversion_from_diagnostic_row(
        {
            "rpm_satisfaction": 1.0,
            "gap_map_summary": {
                "foundation": {"vote_count": 3, "conflict_count": 0},
                "register": {"vote_count": 3, "conflict_count": 0},
                "trace_states": {"focus": "stable"},
            },
        }
    )
    assert scan["attribution_status"] == "not_available"
    assert scan["reason"] == "missing_drive_profile"


def test_scanner_marks_empty_present_profile_not_available():
    scanner = _load(SCANNER, "scanner_empty_profile")
    scan = scanner.scan_inversion_from_diagnostic_row(
        {
            "rpm_satisfaction": 1.0,
            "gap_map_summary": {
                "foundation": {"vote_count": 3, "conflict_count": 0},
                "drive": {},
                "register": {"vote_count": 3, "conflict_count": 0},
                "trace_states": {"focus": "stable"},
            },
        }
    )
    assert scan["attribution_status"] == "not_available"
    assert scan["reason"] == "malformed_drive_profile"


def test_scanner_marks_nonnumeric_profile_fields_not_available():
    scanner = _load(SCANNER, "scanner_nonnumeric_profile")
    scan = scanner.scan_inversion_from_diagnostic_row(
        {
            "rpm_satisfaction": 1.0,
            "gap_map_summary": {
                "foundation": {"vote_count": "bad", "conflict_count": 0},
                "drive": {"vote_count": 3, "conflict_count": 0},
                "register": {"vote_count": 3, "conflict_count": 0},
                "trace_states": {"focus": "stable"},
            },
        }
    )
    assert scan["attribution_status"] == "not_available"
    assert scan["reason"] == "malformed_foundation_profile"


def test_scanner_does_not_exempt_empty_foundation_profile():
    scanner = _load(SCANNER, "scanner_empty_foundation_profile")
    scan = scanner.scan_inversion_from_diagnostic_row(
        {
            "stage": "foundation_ensemble",
            "reason": "foundation_ensemble_all_disagree",
            "rpm_satisfaction": 0.5,
            "gap_map_summary": {
                "foundation": {"vote_count": 0, "conflict_count": 0},
                "drive": {"vote_count": 0, "conflict_count": 0},
                "register": {"vote_count": 0, "conflict_count": 0},
                "trace_states": {},
            },
        }
    )
    assert scan["attribution_status"] == "not_available"
    assert scan["reason"] == "empty_foundation_profile"


def test_scanner_marks_empty_trace_states_not_available():
    scanner = _load(SCANNER, "scanner_empty_trace")
    scan = scanner.scan_inversion_from_diagnostic_row(
        {
            "rpm_satisfaction": 1.0,
            "gap_map_summary": {
                "foundation": {"vote_count": 3, "conflict_count": 0},
                "drive": {"vote_count": 3, "conflict_count": 0},
                "register": {"vote_count": 3, "conflict_count": 0},
                "trace_states": {},
            },
        }
    )
    assert scan["attribution_status"] == "not_available"
    assert scan["reason"] == "empty_trace_states"


def test_scanner_keeps_explicit_unreached_stage_numeric():
    scanner = _load(SCANNER, "scanner_unreached")
    scan = scanner.scan_inversion_from_diagnostic_row(
        {
            "stage": "foundation_ensemble",
            "reason": "foundation_ensemble_all_disagree",
            "rpm_satisfaction": 0.5,
            "gap_map_summary": {
                "foundation": {"vote_count": 3, "conflict_count": 2},
                "drive": {"vote_count": 0, "conflict_count": 0},
                "register": {"vote_count": 0, "conflict_count": 0},
                "trace_states": {},
            },
        }
    )
    assert scan["attribution_status"] == "numeric_measured"
    assert len(scan["axis_scores"]) == 7


def test_scanner_marks_missing_rpm_not_available():
    scanner = _load(SCANNER, "scanner_missing_rpm")
    scan = scanner.scan_inversion_from_diagnostic_row(
        {
            "gap_map_summary": {
                "foundation": {"vote_count": 3, "conflict_count": 0},
                "drive": {"vote_count": 3, "conflict_count": 0},
                "register": {"vote_count": 3, "conflict_count": 0},
                "trace_states": {"focus": "stable"},
            },
        }
    )
    assert scan["attribution_status"] == "not_available"
    assert scan["reason"] == "missing_rpm_satisfaction"


def test_scanner_marks_unknown_trace_state_not_available():
    scanner = _load(SCANNER, "scanner_unknown_trace")
    scan = scanner.scan_inversion_from_diagnostic_row(
        {
            "rpm_satisfaction": 1.0,
            "gap_map_summary": {
                "foundation": {"vote_count": 3, "conflict_count": 0},
                "drive": {"vote_count": 3, "conflict_count": 0},
                "register": {"vote_count": 3, "conflict_count": 0},
                "trace_states": {"focus": "mystery"},
            },
        }
    )
    assert scan["attribution_status"] == "not_available"
    assert scan["reason"] == "unknown_trace_state"


def test_stage22_6_report_closes_numeric_inversion_proxy_rows():
    runner = _load(RUNNER, "stage22_6")
    report = runner.build_report()
    assert report["status"] == "STAGE22_6_INVERSION_PROXY_ATTRIBUTION_COMPLETE"
    assert report["headline"]["total_rows"] == 4704
    assert report["headline"]["inversion_numeric_measured_rows"] == 4704
    assert report["headline"]["inversion_numeric_measured_rate"] == 1.0
    for model in report["models"].values():
        assert set(model["axis_mean_scores"]) == {"N", "W", "F", "E", "S", "A", "P"}
        assert model["numeric_measured_rows"] == model["total_rows"]
