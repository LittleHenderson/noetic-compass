# Corrected HELM 20-pass result

The fresh run completed all 2,940 main updates. The result is mixed: the harder development panel improved, while held-back course accuracy declined from pass 10 to pass 20. These are measured, not certified results from seed 20260918. They do not establish general learning or the registered all-seed relational claim.

| Public measure | Pass 10 | Pass 20 | Change in correct answers |
| --- | ---: | ---: | ---: |
| Course | 502/564 | 487/564 | -15 |
| Held-back course | 115/127 | 111/127 | -4 |
| Trained | 322/358 | 315/358 | -7 |
| Excluded | 65/79 | 61/79 | -4 |
| Harder development | 8/59 | 17/59 | +9 |

Both measurements were fixed in advance. No best checkpoint was selected. The run used AdamW, constant learning rate 0.003, unset planned_main_updates and the frozen model, data, order, holdout and scoring. It made 2,958 total optimizer updates including 16 interference and two replay steps.

The receiver verified all 128 required artifacts; the downloaded inventory contains 839 objects. The mandatory pass-10 checkpoint and metadata match their recorded sizes and SHA256 hashes. No checkpoint was deserialized during this closeout. The worker reports its reload and phase checks complete; this is not an independent numeric reload.

The operator exited 0. All seven independent compute/IAM/security checks passed. The instance was confirmed terminated at 10:55:46 UTC and was absent from EC2 describe at the later closeout check. The private evidence archive is retained with public access blocked; storage remains active and deletion is not authorized.

The USD 19.20 training reservation and all historical reservations remain booked. The canonical ledger is byte-identical to its launch receipt. USD 21.45 was allocated under the USD 21.50 all-services cap. This allocation is not a provider invoice or a claim of actual billed cost.

- Job: `cas-meta2-tpntr-20260926054903-c45f775f-m-20260918`
- Instance: `i-06e9e0febc3881439`; `g7.2xlarge`, `us-west-2`
- Source: `c45f775f225dd06cc20cdf313f0a0398486e0d61`
- Scientific basis: `a5fcf527b5f2c47a3a9b1f170977c55371845af0`
- Admission: `3fee35e9c6da7146f252a29018522709ce78da1f`
- Package SHA256: `38761e9595c321eeab09a368a699a993b7db7616c4f2f15fb716dc78a9066119`
- Launch: `2026-09-26T05:57:31Z`; operator ended `2026-09-26T10:54:44.527596+00:00`
- AWS prelaunch verification: 69 test cases plus six subtests, zero failures/errors/skips.

See [CLOSEOUT.json](CLOSEOUT.json) for exact bindings and [receiver receipt](../receipt_cm2x_rerun_20260918/receiver_receipt.json) for collection evidence. This report is an operator closeout, not a generated acceptance certificate. The old failed attempt remains failed; CAS and 4x/8x work have not been launched.
