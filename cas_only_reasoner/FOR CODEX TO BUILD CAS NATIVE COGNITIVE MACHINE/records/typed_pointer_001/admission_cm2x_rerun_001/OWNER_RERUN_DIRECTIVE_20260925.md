# Owner directive: corrected HELM critical-mass 2x rerun

Proceed now with one fresh 20-pass rerun of the same HELM system for model seed 20260918.

Keep the model, data, batch order, optimizer, scoring, constant learning rate 0.003, pass-10 evaluation,
pass-20 evaluation, mandatory pass-10 checkpoint evidence, and no-best-checkpoint rule unchanged from the
`b981625f` experiment. Use one `g7.2xlarge`, one job, `automatic_retries=0`, required cleanup, the canonical
ledger only, and a finite prospective all-services cap no greater than USD 20. Stop before spend if the honest
bound does not fit. Verify there is no conflicting active EC2 job before launch.

Do not reuse or alter job `cas-meta2-tpntr-20260925151836-b981625f-m-20260918`, its reservation, receipt
directory, admission records, or retry mechanism. Historical R18 and failed-attempt receipts remain untouched.

This file is a Codex transcription of the owner message received on 2026-09-25. It is not a signature.
