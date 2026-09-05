# Independent stored memory-demo audit

The unchanged frozen auditor passed in the isolated `8b5d8ac9e4f469b4cd89bbe917560678d2f52cb7` checkout on 2026-09-05 at 23:09:56 UTC. The saved audit receipt is a byte-identical copy of the isolated checkout's fresh `aws_native_demo_001_stored_audit_clean_003` receipt.

The active checkout's earlier audit encountered new, untracked learning-v3 modules through its source glob. Two isolated-checkout attempts then correctly rejected three protected metadata files whose checkout bytes had CRLF line endings. The Git source blobs, pinned source ZIP, original active checkout, and existing protected byte manifest all agreed on LF bytes. Only those three isolated-checkout metadata files were mechanically normalized to LF. All 316 protected hashes matched before the retry and remained unchanged afterward. No source content, audit code, manifest, original packet, or original extracted evidence was changed.

Evidence files:

- `alignment_receipt.json`: exact three paths, before/after byte hashes and original bytes in hexadecimal, source comparisons, and all 316 verified hashes.
- `process_receipt.json`: exact command, working directory, UTC start/end, exit code, and raw-output hashes.
- `stored_audit_receipt.json`: the unchanged auditor's completed semantic result.
- `prior_*_stored_audit_receipt.json`: byte-identical copies of all three prior failures; their original files were preserved.
- `stdout.txt` and `stderr.txt`: the retry's raw outputs.
- `align_and_retry.py`: the narrowly scoped, fail-closed correction/recording helper used once. It refuses to overwrite its records or reuse the audit output directory.

Verified scope: successful writer exit followed by a separate reader process; unchanged registry retrieval; five reproduced rejection checks; six native traces across three databases; candidate's three native outputs matching the reference; and return of the first B call's identity after two calls to the same stored procedure.

This was a read-only stored-evidence audit, not a new neural execution or an AWS provider check. It does not claim learned retrieval, skill qualification, package promotion, suspended-caller restart, or general memory. `learning_performed=false` and `qualification_status=UNQUALIFIED` remain in force. The separately recorded outer packet inspection and provider cleanup verification provide the other evidence layers. No budget ledger was included in the isolated audit checkout or read by this helper.

Receipt SHA256: `9af2bb1ed781c1e10550c21821cd4f01b9476494258b3379cdce2d39bf1e4fd7`.

Process receipt SHA256: `4fc360c43c382c3309009d591a9d7fd7d24aadbe83352222ce5eda93a58b0e92`.

Alignment receipt SHA256: `e3ecf2a3fab8e709d3b06de6848100911de694a19f46e63370a12677e8edf66a`.
