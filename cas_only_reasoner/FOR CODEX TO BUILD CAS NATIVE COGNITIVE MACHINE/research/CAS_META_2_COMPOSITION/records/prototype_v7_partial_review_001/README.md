# Failed v7 run: complete byte collection

This directory contains a separate byte-only review. The experiment returned 1; this is not a completed learning result. The extractor does not run the success-only reviewer or load model weights, tensors, task generators, or provider clients.

Fixed job: `cas-meta2-20260906094002-39762c47`.
Source: `42f9164754312f12850d9b8789c062fa7fb8069f`.
Packet: `f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799`, 131,895,861 bytes.
Source ZIP: `f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9`, 7,882,289 bytes.

The collection receipt reports all 2,940 original files included and zero omitted files. Its 1,940 omitted entries refer only to the shortened inline index. The extractor rebuilds the complete index from authenticated bytes and checks its stored hash and first 1,000 entries. It also checks the campaign payload index against every campaign member.

The 791,706,578-byte original payload excludes the 228,518-byte collection receipt. The complete 2,941-member archive expands to 791,935,096 bytes.

## Checks and limits

Before extraction, the helper verifies both externally supplied ZIP hashes, all 603 frozen source files against the ZIP, Git and current disk, all 316 protected files, every packet path/type/size/hash, the collection identity, the full original-file index, and the exact campaign payload index. New extraction only; links, encrypted members, path escapes, duplicate names, case aliases, file/directory aliases and unsafe Windows paths are rejected. Every extracted file and input archive is rechecked at the end. Opaque checkpoint files are copied and hashed, never decoded.

The receipt reports byte verification only. It does not establish training correctness, trace semantics, completed native evaluation, correct answers, cleanup or invoice cost. A later partial semantic audit must retain the unfinished case and distinguish recorded completed outcomes from the 72 scheduled tasks.

Pure synthetic checks:

```text
python -B records/prototype_v7_partial_review_001/test_extract.py
```

Actual extraction command, run from the META2 package directory:

```text
python -B records/prototype_v7_partial_review_001/extract.py --packet records/aws_prototype_v7_001/cloud_artifacts.zip --sha256 f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799 --archive records/aws_prototype_v7_source_001 --archive-sha256 f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9 --source-sha 42f9164754312f12850d9b8789c062fa7fb8069f --job cas-meta2-20260906094002-39762c47 --output records/prototype_v7_partial_review_001/extracted_001 --receipt records/prototype_v7_partial_review_001/extraction_receipt.json
```

For a rerun, use a different new extraction directory and receipt filename inside this directory. Never overwrite the original extracted evidence.

## Initial extractor correction

The first byte-only attempt stopped at `COMPLETE_ORIGINAL_INDEX_HASH_MISMATCH` before creating the extraction directory. The new extractor had sorted raw path strings; the frozen Linux collector sorts `pathlib.Path` components. These differ for names such as `a/z.txt` and `a.txt`. The extractor now reproduces that exact Linux ordering with `PurePosixPath`. A synthetic regression covers it. No packet bytes or frozen source were changed, and the original hash check was not removed or weakened.
