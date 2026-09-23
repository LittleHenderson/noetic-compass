# Evaluation design before implementation — 2026-09-23

This document is committed before changing the analogy model or tuning any model.
It follows the current owner's concrete repair request and docs/OWNER_RUN_AUTHORIZATION_20260922.md.
Source baseline: a6e6f95bcae348775b910438109c9ed3842a5c19; complementary review: 26f1b46515c960a7aed6023f370df95d591ca36a.
Historical artifacts and frozen graders stay immutable. New outputs are dated and source-pinned.

## Three distinct questions
1. Historical certification: reproduce the ORIGINAL paired exact binomial rule at question level, all presentations correct; b > c, p <= 1/100, at least two improved kinds and worlds, all three seeds pass. No zero-loss veto. Helm 1.0 remains certified. Recheck each seed, exact probability and breadth, not just aggregate labels/counts.
2. Analogy repair: establish an explicit learned comparison of focus and candidate structure/domain, and prove by intervention and gradients that the focus can change candidate-relative scores. Keep complete-assignment decoding untouched. This is an effect test, not evidence of trained generalization.
3. Q4 reconstruction: report teaching-set fit, new content on familiar tree structures, and genuinely new tree structures separately. A smoke run's negative accuracy is not a failed historical Helm gate.

## Future evaluation: HELM_TRANSFER_EVALUATION_DRAFT_20260923
Separate from historical certification; not a replacement or approved release claim.
Freeze generation seeds, item IDs, checker version, graph fingerprints, model source and budgets before a learned run. Separate development from unseen final evaluation. Previously investigated items are diagnostics, never fresh hidden evaluation.
Use matched graph sizes for familiar and new directed unlabeled structures, with declared participant/order/flag constraints recorded separately. Stratify reach equally among ABSENT, DIRECT and exact VIA, avoiding unknowable lexical tie breaks. Add multi-hop and counterexample cases. Report all answer kinds separately.
Correspondence includes positive complete bijections and NO_MATCH negatives. Preserve and test the existing exhaustive complete-assignment decoder. Analogy includes chain/star alternatives and incompatible domains: hold candidates fixed, change only focus and compare rankings.
For every panel report exact questions and presentations, numerator/denominator, uncertainty and paired transitions; compiler/graph/degree/lexical baselines in distinct columns. A new release threshold and power/sample-size analysis must be frozen before a claim-bearing training job. No such job is selected here.
Do not use either the historical 11/18 floor or 16/18 rule baseline as a newly invented historical veto.

## Q4 panel protocol — diagnostic evaluation, not tuning
A. Teaching fit: exact examples known to be consumed by the saved model; report sampling/full denominator and evidence for exposure.
B. New content, familiar structure: content-disjoint expressions whose ordered operator/tree skeleton exists in teaching. Check identity and skeleton separately.
C. New structures: ordered operator/tree skeleton absent from the complete teaching corpus, at matched size/depth where possible. Distinguish matched from extrapolation.
Freeze an input manifest before inference, including IDs, source and structural keys, checker, selection rule and all overlap checks. Report exact reconstruction, parse validity and structure-only accuracy separately. A compiler's target is a reference, never a learned prediction.
The old Q4 dev split has no teaching shapes. Its 0/16 cannot distinguish B from C. The eight-row RT7 memorization and 256-row RT2 negative result remain separate diagnostic jobs, not a replacement measurement of the original saved model.
First use saved results. A bounded evaluation-only job on the existing 128-update checkpoint may be selected: zero updates, no optimizer, at most 48 predictions (16 per panel), 120 seconds on CPU, one process/two CPU threads, no GPU/cloud/API, no automatic retries. Its exact input/source/checkpoint identities and consumed-example evidence must be written before launch. If these prerequisites cannot be met, report unavailable panels and a precise next command instead of fabricated scores.
No longer training or larger representation is selected or asserted necessary.

## Late Helm reach experiment — separate, NOT selected for execution
The seed-20260919 reach regression occurred after pass 8 and by pass 10. No pass-8 tensor checkpoint is retained. Smallest valid replay uses the saved pass-1 checkpoint, freezes teaching order and all settings, then compares original learning rate with one changed rate. This tests one cause, not Q4. Register physical device, exact two-arm update budget, wall/thermal limits and checkpoint identity before any future launch. Do not call an unrun arm failed.

## Selected repair checks and limits
- Static evidence verification and historical rescore: CPU only, one process at a time, <= 900 seconds each, no neural inference, no cloud/API; stop on source mismatch or malformed custody.
- Analogy unit/effect checks: CPU only, <= 120 seconds per invocation, two threads, newly initialized small containers only; zero optimizer steps/training, no historical checkpoint rewrite. Show expected legacy failure and repaired effect, plus unchanged non-analogy behavior.
- Q4 implementation helper: one existing-allowance agent, separate worktree, only Q4 evaluation files/tests/records. No new research team or paid allowance.
- Save test collection counts separately from passed/skipped/failed cases and preserve failure receipts.
