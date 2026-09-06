# Failed contrast-v6 packet: offline training recount

This is separate from the completed-success review. The original AWS campaign failed during native evaluation. This tool never changes that result into a successful run.

The tool requires the externally supplied packet SHA-256 and the exact frozen source archive/commit. It checks all 538 packaged source inputs and 316 protected files before frozen helper imports. It checks the complete ZIP inventory, collection index and no-omission claim; all GPU gate identities and commands; training process exit; unchanged parent-side training recount; selected checkpoint bytes and validation curves; saved dataset construction and file hashes; all 72 neural/five-arm prediction rows and their seals; and available partial native files.

It extracts every packet member to a new records/aws_contrast_v6_001_failure_extracted directory using the unchanged safe ZIP helper. All source and extracted bytes are checked again at the end.

It does not load checkpoints, import neural libraries, generate tasks, call a provider, rerun CUDA, replay native stored traces, or accept learning. Checkpoint hashes describe saved bytes. Validation scores describe generated action matches, not full native task correctness. Partial native case counts are file counts, never a completed 72-task denominator. The 72 task variants form 24 matched triplets, not 72 independent structures.

The original completed-success review and audit scripts are imported only after checking their exact helper hashes. Their successful acceptance entry points are not called or modified.

## Commands from CAS_META_2_COMPOSITION

    C:/Python314/python.exe -B records/contrast_failure_review_v6_001/run_checks.py

    C:/Python314/python.exe -B records/contrast_failure_review_v6_001/review.py --sha256 db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def --output records/contrast_failure_review_v6_001/run_002

The pure suite has 13 test methods. It checks failure-only admission, no omitted files, full-index requirements, exact 72-row mapping, preserved neural actions, rule/public linkage, and import purity. It reads no current packet.

Run 001 failed before extraction because this new review script initially used omitted_file_count rather than the frozen collector's omitted_full_file_count field. That local review failure is retained as run_001/review_failure.json. The field was corrected and a regression test added. This does not change the original AWS failure.

The checked receipt contract is cas-meta2-contrast-failure-review/6, status FAILED_RUN_TRAINING_RECOUNT_PASSED. It retains campaign_completed=false and native_evaluation_completed=false. Its inventory rows are {path, bytes, sha256}, relative to extraction.path. The training_gate is the unchanged, recomputed parent gate, and binding_checks pins the original five-arm prediction bytes, seal, private opening receipt, dataset and original training-parent-gate bytes. A downstream tool must use an externally supplied hash of the completed receipt and recheck its actual input bytes.

