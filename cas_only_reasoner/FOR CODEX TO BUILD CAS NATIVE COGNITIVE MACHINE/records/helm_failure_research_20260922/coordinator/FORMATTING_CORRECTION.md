# Coordinator formatting correction

A7 correctly noticed that the live integration directory changed after its reviewed baseline
3f7ac2967c4bc38313a003e2817a3dcab58451d1. A0's later cosmetic commit dec36a3a used an overly broad,
case-insensitive spacing expression. It split role identifiers such as A1 and could split a
hexadecimal commit identifier beginning with a followed by a digit. This was a custody-text defect,
not a change to investigator findings or original evidence.

A0 restored exactly these four files to their bytes immediately before dec36a3a by reading
git show dec36a3a^:<path> as bytes and writing those bytes only in the integration worktree:

- coordinator/CUSTODY_LOG.md
- coordinator/CONFERENCE_RECORD.md
- CHECK_ACCOUNTING.md
- FOLLOWUP_PLAN.md

The restoration command exited 0. All four original report/evidence identities remain recoverable
from the committed history. Investigator FIRST_REPORT.md files, conference responses, raw probes,
source manifest, source ZIPs, original receipts and A7 outputs were never changed by this cosmetic
operation. A7 pins the substantive package it reviewed to 3f7ac296 and separately cites later root
preservation evidence. The final output manifest fingerprints the corrected final files.

A0 will not perform further blanket text substitutions. A7 judgment and next actions will be copied
byte-for-byte. This note records the error and recovery without rewriting an investigator report.
