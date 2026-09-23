# Post-write verification

The first report remains unchanged. Its raw SHA256 is 91de7dc113f564374df6dd287be06760d87c2f75c20e7823e96b86cc106a012f.

The first staging command ran `git diff --cached --check` before committing. It reported CR-at-EOL whitespace throughout Windows-formatted files and the two historical learners' existing blank final lines. The surrounding PowerShell command continued to commit; its overall exit was 0 and must not be confused with a passing whitespace check. Output was truncated because the preserved source copies contain many CRLF lines.

A separate `git -c core.whitespace=cr-at-eol show --check --format=oneline HEAD` returned exit 2, with only the two original learner blank-at-EOF findings remaining. Its three output lines are in `commit_whitespace_check.txt`. These exact source-copy bytes were preserved intentionally because changing them would invalidate the manifest fingerprints. No code behavior or source evidence was modified to clear formatting warnings.

The research suite itself passed on its sole execution. Formatting verification is separate from that test result. The report and source-copy fingerprints remain checkable. The commit was then amended only to include this verification record and whitespace output; `FIRST_REPORT.md` was not edited.
