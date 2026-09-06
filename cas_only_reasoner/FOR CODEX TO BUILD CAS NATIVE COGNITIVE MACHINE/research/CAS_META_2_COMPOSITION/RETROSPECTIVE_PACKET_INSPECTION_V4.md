# Inspecting the first decoder-comparison packet

`tools/inspect_ablation_packet_v4.py` is pinned to the first comparison
job and source archive. It must not be used as if it covered a later job.
It checks the external packet hash, safe archive membership, every included
file hash, collection-index consistency, and optional safe extraction.
It blocks neural and provider imports. It never loads model weights.

For the first AWS attempt it reports
`RETROSPECTIVE_FAILED_OR_PARTIAL_RUN`: all 90 included member files were
checked and no inspection issues were found, but the experiment failed before
prediction. The collection reports zero omissions.

The inspector also contains receipt-consistency checks for complete comparison
packets. Those checks did not run on this failed packet. The three local tests
cover a synthetic failed packet, a wrong external hash, and an unsafe archive
path. They are not evidence that complete-run checks or stored semantic
verification succeeded.

No inspector status grants learning acceptance. A future completed comparison
requires source/job-specific binding and an independent check of actual stored
execution outcomes. A valid trace or a consistent summary alone is not a
correct answer, new learning, or proof of CAS-specific advantage.
