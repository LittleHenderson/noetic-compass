# Contrast v6: failed run, completed training checked

The original run failed during native evaluation. This is not a completed learning result.

Source: acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0
Packet SHA-256: db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def

Training: 200 epochs; {'cas': 8000, 'generic': 8000} optimizer steps.
Dataset: 640 training tasks, 96 validation tasks, 72 held-out task variants in 24 matched triplets.
The original 256-task prototype is excluded from this v6 dataset.

Validation action match (not native task correctness):

| Family | Initial | Selected | Epoch | Depth 1 | Depth 2 | Depth 3 |
| --- | --- | --- | --- | --- | --- | --- |
| cas | 0/96 | 30/96 | 180 | 30/32 | 0/32 | 0/32 |
| generic | 0/96 | 29/96 | 160 | 29/32 | 0/32 | 0/32 |

Preserved native evidence: 12 case directories; 3 complete case receipts, indices [0, 3, 6]. No 72-task success rate is reported.

Failure: RuntimeContractError: repair cannot open without a durable distinct ^6 round trip; case 9, CAS trained arm.

All 72 sealed prediction rows were checked. No predictions were regenerated; no checkpoint was loaded.
All source files and all extracted packet files were checked again at the end.
Recorded GPU: NVIDIA RTX PRO 4500 Blackwell Server Edition. Costs and cleanup are separate provider records.
Earlier familiar 24/24 and earlier held-out CAS 0/72 results remain separate and unchanged.
No accepted baseline, executor, verifier, weights or completed-success review gate was changed.
