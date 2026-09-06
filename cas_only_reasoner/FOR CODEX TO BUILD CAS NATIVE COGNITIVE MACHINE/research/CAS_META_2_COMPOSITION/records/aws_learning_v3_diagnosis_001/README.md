# v3 retained-result diagnosis — release not accepted

Source: `ec9d161908ab4ed8a4fb300ca31cb089ac0c3b70`.
Job: `cas-meta2-20260906002616-34a51f16`.
Packet SHA-256: `ebb76793a3897d70563be8cd2a857b0e24c82c4e412d3db66d80ac76345acaf2`.

The 60-epoch run reached final evidence collection, where the unchanged campaign
failed with `RuntimeError:V3_OUTPUT_LINK_DETECTED`. The bounded collector omitted
423 original files. The frozen inspector, using a correctly named extraction
directory, returned `CAS_META_2_V3_PACKET_PARTIAL_EVIDENCE`: included bytes and
safe extraction were checked, but complete-run evidence was not verified.
The first inspector attempt rejected the caller's extraction-directory suffix;
that record is retained. Neither inspector was edited.

`recount.py` checks the inspected member hashes and recounts all 72 retained
case receipts, all 360 arm receipts and their separate verification files.
It checks these counts against all three saved group summaries:

| Selector | Correct tasks | Correct bindings | Model rejections |
| --- | ---: | ---: | ---: |
| CAS initial | 0/72 | 0/72 | 72 |
| CAS trained | 0/72 | 19/72 | 53 |
| Generic initial | 0/72 | 0/72 | 72 |
| Generic trained | 12/72 | 33/72 | 39 |
| Rule | 72/72 | 72/72 | 0 |

All reported model rejections are `GENERATION_GRAMMAR_DEAD_END`. CAS's
development score did not translate into correct held-out execution in this
run. Better syntax/binding alone is not a solved task. There is no positive
CAS task-correctness gain eligible for the learned-memory handoff.

This is a consistency recount of retained JSON, not replay of the missing
native databases, independent neural evaluation or complete release acceptance.
The saved checkpoints remain unqualified. Do not amend receipts to claim success.

Next work: finish provider cleanup observation; diagnose the symbolic-link
source without weakening link rejection; investigate the generation failures
and development/held-out gap on a separately versioned candidate. Preserve the
current experiment and failed packet. Any further GPU run needs a fresh bounded
reservation within the existing total $400 cap; do not automatically retrain.

## Follow-up findings

`grammar_receipt_002.json` replays the exact retained rejected prefixes through
the unchanged pure grammar with neural imports blocked. All 53 CAS trained
rejections terminate with `UNREACHABLE_PROCEDURE`. In 21 cases, an earlier prefix
was a valid complete program, but the model selected another declaration; no
closed existing procedure could then call that extra code. This is a candidate
for a language-validity mask correction, not permission to repair saved outputs
or claim those earlier prefixes solved their tasks. All 72 test tasks have four
procedures; the 96 development tasks mix one to four. Future work must measure
performance on comparably structured development cases without relabeling the
now-exposed test set as fresh held-out evidence.

The GPU-test basetemp directory is inside the collected output tree. The locally
inspected pytest helper creates `current` symbolic-link aliases for numbered
temporary directories. This is a plausible source of the link failure, but the
partial packet does not retain the offending path. The exact remote link is
not independently established. Do not weaken the collector's link refusal.

At 2026-09-06 01:57:32 UTC, `cleanup_receipt.json` independently confirmed the
instance terminated, no job-tagged volumes, and removal of the security group,
worker instance profile, both IAM roles and scheduled timer: seven checks passed.
The evidence bucket remains under its separate expiry policy. The launcher's
compute/disk/IP estimate is about $3.80, excluding storage requests, transfer and
taxes; this is not an AWS invoice or an automatic budget refund.
