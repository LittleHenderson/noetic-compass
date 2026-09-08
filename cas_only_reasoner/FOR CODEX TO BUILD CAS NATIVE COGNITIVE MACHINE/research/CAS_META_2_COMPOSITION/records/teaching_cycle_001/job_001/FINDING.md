# First teaching launch attempt: price-format refusal

Transport source: `874ad687bc77a86c5e9885fbf6b515ec84104a71`.
Job: `cas-meta2-teaching-20260908052008-5b9d7c0b`.

The real read-only AWS preflight succeeded. The parent then rejected the
hourly-price field with `BudgetRefused: INVALID_USD_AMOUNT`, before reservation
or resource creation. AWS supplied `2.5200000000`; the canonical budget parser
accepts at most eight decimal places. The numerical price is exactly $2.52.

The original `launch/001_preflight_result.json`, `launch/failure.json`, and
`launch/result.json` retain the actual responses and failure. No GPU instance,
worker process, training update, or cloud result bucket was created. The ledger
remained at revision 17: $102 reserved, $298 unreserved, inclusive cap $400.
Its unchanged SHA256 is
`83fd87829a34a559ae901b553a851d79ec27359601230561afffb55955df2b92`.

The 208 fake-client/process tests passed before this attempt. They did not cover
this exact live price representation. This finding concerns the provider-to-
budget handoff, not the neural teaching method or the accepted executor.

The correction must preserve the raw quote, remove only insignificant trailing
zeros from the comparison field, and reject prices over the existing ceiling
without rounding them down. The budget parser and cap stay unchanged. This job
is closed, with no reservation refund claimed and no retry of its authority.
Any subsequent attempt requires newly committed source and a fresh bound job.
