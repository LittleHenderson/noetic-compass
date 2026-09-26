[OWNER/SUPERVISOR EXECUTION PRIORITY — HELM FIRST]
Proceed now with the corrected HELM critical-mass 2x attempt.

Scientific question: does the same HELM configuration improve harder transfer when training reaches 20 passes instead of 10?

Use current corrected source commit a5fcf527 ("Route pointer training helpers through the frozen pointer deadline") as the rerun source basis. Preserve failed job cas-meta2-tpntr-20260925151836-b981625f-m-20260918 and all its receipts unchanged.

Create a NEW prospectively frozen attempt/job/receipt. Do not mutate or reuse the old job identity, reservation, receipt directory, or failed admission. Same model seed 20260918, same data, same batch order, same optimizer, constant LR 0.003, same held-back/development scoring, pass 10 and pass 20 evaluations, pass-10 checkpoint evidence mandatory, one g7.2xlarge, one job, automatic_retries=0, cleanup required. The only scientific-source change from b981625f should be the deadline-routing correction already committed at a5fcf527 plus whatever record/package identity changes are mechanically required for a new attempt. Keep finite all-services cap <= USD 20 for this new attempt unless the current measured runtime proves that impossible; if impossible, stop before spend and return the exact required finite cap.

Before launch: run the focused deadline-routing + critical-mass + admission tests, build source.zip from the exact rerun source commit, freeze a new owner/request/authority/study record, verify canonical ledger path, verify no conflicting active EC2 job. Then launch the single bounded AWS job immediately if all gates pass. No new broad review, no CAS delay, no automatic retry loop.

Return: new source/admission commit, test counts, job id, instance id, reservation/cap, and RUNNING evidence.
