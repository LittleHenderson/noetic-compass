# CAS Forex UI Visual Baselines

This directory stores source-controlled screenshot fingerprint manifests for the
CAS Forex browser UI. The baseline is generated from the headless zoom smoke
runner and compared with `scripts/run_ui_visual_baseline.py`.

Refresh the baseline after an intentional UI change:

```powershell
npm --prefix ui run build
python scripts\run_ui_browser_zoom_smoke.py --exit-code-on-failure
python scripts\run_ui_visual_baseline.py --source-report runtime\ui_browser_zoom_smoke\<run>\ui_browser_zoom_smoke_report.json --write-baseline
python scripts\run_ui_visual_baseline.py --source-report runtime\ui_browser_zoom_smoke\<run>\ui_browser_zoom_smoke_report.json --exit-code-on-failure
```

The visual baseline is observational only. It compares local screenshots against
a luminance fingerprint manifest; it does not touch broker state, dispatch
orders, change settings, authorize live trading, or make performance claims.
