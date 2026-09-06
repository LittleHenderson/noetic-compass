# Retrospective decoder-comparison inputs

`inputs.zip` is a data-only artifact for a future AWS decoder comparison.
It is not a runnable cloud job or an accepted learning result.

- Archive SHA-256: `bbb538f9a6cad0ecde46106f542edac9dd64e3188568cb96b2ca550ff854ee93`
- Archive bytes: `6444247`
- Source packet SHA-256: `ebb76793a3897d70563be8cd2a857b0e24c82c4e412d3db66d80ac76345acaf2`
- Learning source SHA: `ec9d161908ab4ed8a4fb300ca31cb089ac0c3b70`

The builder checks the fixed partial-inspection receipt, packet bytes and
inspected member index. Each selected member is checked against its recorded
length and SHA-256, copied without alteration, then read back and rehashed.
Checkpoint metadata is checked against the actual copied weight-file hashes.
No torch/model import, tensor operation, provider request or GPU launch occurs.

Contents include CAS and generic initial and selected checkpoints, tokenizer,
original checkpoint/training metadata, sealed original predictions, public and
private 72-task files, and their dataset manifest. Both selected checkpoints
are epoch 60 / 11,520 optimizer steps. All checkpoint bytes remain unchanged.
An added input manifest maps portable locations without editing the original
metadata or claiming the incomplete source run passed its audit.

These tasks have already been exposed during failure diagnosis. The manifest
therefore marks them RETROSPECTIVE_DECODER_DIAGNOSTIC and forbids a fresh-held-out
claim or training. Predictors should receive public observations only; a separate
evaluation stage should open private targets only after new predictions are
sealed. Any improvement from the changed mask is a decoding result, not new
learning. Complete native execution, audit and source-bound AWS budget/cleanup
controls still need to be implemented for the new job.

The budget ledger remains revision 5: $39 reserved and $361 unreserved within
the total $400 cap. Reservations are not an invoice or spend measurement.
