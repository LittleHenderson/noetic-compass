# A5 first-report scope and command-log addendum

This note preserves FIRST_REPORT.md unchanged at commit f253754c21ccc5b2ae8a2c0f381fc4882540b7cc, SHA256 6991dca9b2c34ada684822c04c1ea0ef6a04e910ae2ebece8039aa5523e35a84.

Saved decoder reconstruction covered **analogy and correspondence only**. It covered NO_MATCH versus world choice for analogy, and NO_MATCH versus whole bijection for correspondence. It did **not** reconstruct reach mode, DIRECT/ABSENT/VIA choices, or VIA node scoring. Rows from other families were read as part of complete prediction/scoring JSON files but not analyzed for this role. No claim about reach decoding follows from A5's checks.

After the first report was written, the precommit `git diff --cached --check` emitted whitespace findings on CRLF lines, producing heavily truncated output (tool chunk dd0d8e). The shell continued to the explicit commit; its final process exit was 0. The individual default whitespace-check exit was not captured. This was a formatting check finding, not a probe assertion or data mismatch. A subsequent `git -c core.whitespace=cr-at-eol diff HEAD^ HEAD --check` passed with exit 0, showing the findings were Windows CR line endings. Source and output bytes were left intact to preserve the report's stated SHA256 values. No research calculation was rerun.

The saved records remain research-only. Exact graph results are a new stdlib comparison derived from public data, never presented as saved learned predictions. The first report remains immutable; any later conference revision belongs in a separate file.
