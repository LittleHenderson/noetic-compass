"""Historical dataset/state-oracle isolation from active language extensions."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import historical_compiler as historical
import q3_behaviour_records as q3
import pcba_check


def test_q3_and_pcba_retain_the_reviewed_pre_ohm_oracle():
    compiler, receipt = q3._load_compiler()
    assert receipt["sha256"] == pcba_check.COMPILER_SHA256_LF == historical.SHA256_LF
    assert receipt["resolved_from"] == "pinned_historical_snapshot"
    assert compiler('ohm_scale("s", "drive-units", "attention-units")').valid is False
    state = compiler("^8^C_{F2}|A")
    assert state.valid
    assert pcba_check.check_pcba_document("board example { node x: ^8^C_{F2}|A; }")["valid"]


def test_changed_historical_snapshot_cannot_hide_behind_module_cache(tmp_path, monkeypatch):
    historical.load_historical_compiler()
    changed = tmp_path / "compiler.py"
    changed.write_bytes(historical.SNAPSHOT.read_bytes() + b"\n# edited\n")
    monkeypatch.setattr(historical, "SNAPSHOT", changed)
    with pytest.raises(ValueError, match="HISTORICAL_COMPILER_PIN_MISMATCH"):
        historical.load_historical_compiler()


def test_missing_snapshot_does_not_fall_back_to_current_compiler(tmp_path, monkeypatch):
    monkeypatch.setattr(historical, "SNAPSHOT", tmp_path / "absent.py")
    with pytest.raises(FileNotFoundError):
        historical.load_historical_compiler()
