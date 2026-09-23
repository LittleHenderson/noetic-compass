Post-submission custody note

Immutable FIRST_REPORT and evidence first commit: 87266d875207cc1df6df6de1dc89845fae60109f.

The final staged git diff --check emitted whitespace errors, mostly CRLF, but the PowerShell command continued and committed. This is not a passing staged formatting check. An earlier unstaged diff --check returned 0 while these files were untracked and did not validate them. A subsequent CRLF-aware git show --check returned 2: remaining whitespace includes the deliberate numbered blank source excerpts such as '288: '. Exact output is in format_check.txt. No first-report or raw evidence bytes were changed after commit. Research-result checks are unchanged; this note corrects formatting-check custody only.

Correspondence denominator clarification: the report's 0/5 to 5/5 is the five correspondence questions among all 50 held-world questions, not the 18-question label population. The label contains zero correspondence questions. The official frozen test permits answer losses if the exact paired statistic still passes. No retrospective zero-loss interpretation was used.
