from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "run_stage22_5_full_row_proxy_attribution.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("stage22_5", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_stage22_5_uses_full_stage22_4_row_set():
    module = _load_module()
    report = module.build_report()
    assert report["status"] == "STAGE22_5_FULL_ROW_PROXY_ATTRIBUTION_COMPLETE"
    assert report["source_product_status"] == "NULL"
    assert report["source_diagnostic_status"] == "STAGE22_4_DIAGNOSTIC_ROWS_EMITTED"
    assert report["headline"]["total_rows"] == 4704
    assert report["headline"]["lacunarity_proxy_measurable_rows"] == 4704
    assert report["headline"]["inversion_numeric_measured_rows"] == 0


def test_stage22_5_preserves_per_model_row_parity():
    module = _load_module()
    report = module.build_report()
    for model in report["models"].values():
        assert model["row_parity_ok"] is True
        assert model["accepted_rows"] + model["suppressed_rows"] == model["total_rows"]
        assert model["lacunarity_proxy"]["measurable_rate"] == 1.0
        assert model["inversion_scan"]["measured_rate"] == 0.0


def test_stage22_5_counts_lacunarity_from_attribution_status():
    module = _load_module()
    report = module.build_report()
    for model in report["models"].values():
        counts = model["lacunarity_proxy"]["attribution_status_counts"]
        assert counts == {"proxy_measurable": model["total_rows"]}
        assert model["lacunarity_proxy"]["measurable_rows"] == counts["proxy_measurable"]


def test_stage22_5_only_counts_numeric_inversion_statuses_as_measured():
    module = _load_module()
    report = module.build_report()
    for model in report["models"].values():
        counts = model["inversion_scan"]["attribution_status_counts"]
        assert counts == {"not_measurable": model["total_rows"]}
        assert "not_available" not in model["inversion_scan"]["numeric_measured_statuses"]
        assert "not_evaluated" not in model["inversion_scan"]["numeric_measured_statuses"]
        assert "not_measurable" not in model["inversion_scan"]["numeric_measured_statuses"]
