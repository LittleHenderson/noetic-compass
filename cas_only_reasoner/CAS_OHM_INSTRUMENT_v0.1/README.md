# CAS-Ohm Instrumentation Panel v0.1

The last roadmap board: profile-specific measurement of the CAS-Ohm
quantities, under the paper's own restrictions as executable rules.

- `panel/protocol.py`   - manifests; calibration/validation splits
                            enforced DISJOINT (R7); deterministic
                            synthetic source, labeled `synthetic_mock`.
- `panel/calibrate.py`  - R_eff fit on the calibration split only;
                            residuals RANK follow-up probes and
                            identify NO causes (R6).
- `panel/asom.py`       - operating condition (Starved / Aligned /
                            Oversaturated / Misaligned) from response
                            REGION and semantic OUTCOME independently.
- `panel/report.py`     - every restriction R1-R10 printed verbatim.

This panel is OPTIONAL instrumentation: it is not part of the
reasoning loop, makes no causal or predictive claims, measures no
attention, and admits no live calibration. Run `python run_demo.py`.
