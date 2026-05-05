# Phase 1 T8 — SDG Throughput Benchmark

Status: complete. Single-process generation easily clears the "no multiprocessing required" bar.

## Run command

Driver: `cas-synthetic/scripts/bench_t8_throughput.py` (added in this branch). Wraps
`Level3ConversationalGenerator` with cold-cache wall-clock timing, `tracemalloc`
peak-allocation, and a coarse split between full pipeline (generation + JSONL
serialize + file write) and pure generation (consume iterator, no file I/O).

```
python cas-synthetic/scripts/bench_t8_throughput.py \
    --input cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl \
    --output cas-synthetic/data/level2_scaffold/_bench/bench_run_1k.jsonl \
    --max-source-records 1000 \
    --variants-per-source 5 \
    --style-id recoverable_translation \
    --json-summary cas-synthetic/data/level2_scaffold/_bench/bench_summary_1k.json
```

Three independent cold-process runs were executed against the
`level2_full_10k.jsonl` source on Windows 11, Python 3.14.0, single thread.
Outputs were written to `cas-synthetic/data/level2_scaffold/_bench/` and are
git-ignored (see `.gitignore` change in this branch).

## Source slice

- Source file: `cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl` (10,000 records).
- Slice: first 1,000 source records.
- Of those, 31 are flagged invalid in the Level 2 metadata and skipped, leaving 969 source records used.
- `--variants-per-source 5` over a single style id (`recoverable_translation`) yields exactly 5 variants per used source -> **4,845 output records per 1K-source run**.

## Measurements

| Metric                                | Run A   | Run B   | Run C   |
| ------------------------------------- | ------- | ------- | ------- |
| Full pipeline (gen + JSON + write), s | 2.618   | 2.660   | 2.620   |
| Output records written                | 4,845   | 4,845   | 4,845   |
| Full-pipeline records / sec           | 1,850.7 | 1,821.7 | 1,849.4 |
| Pure generation, s                    | 0.520   | 0.543   | 0.542   |
| Pure-generation records / sec         | 9,311.8 | 8,922.6 | 8,932.5 |
| Serialization + write delta, s        | 2.098   | 2.117   | 2.078   |
| Serialization + write share of full   | 80.1%   | 79.6%   | 79.3%   |
| Peak Python heap (tracemalloc), MB    | 0.40    | 0.40    | 0.40    |
| Output JSONL size on disk, MB         | 10.83   | 10.83   | 10.83   |

Headline numbers (median of three runs): **~1,850 records/sec end-to-end**,
**~9,000 records/sec generation-only**, **~0.4 MB peak Python heap**, **~10.8 MB
on disk per 4,845 output records (~2.3 KB/record)**.

### Compiler / validator overhead

Recorded as **N/A**. The Level 3 conversational generator does not invoke the
CAS compiler or live validators in the hot path. It uses
`source.metadata.is_valid` precomputed at Level 2 scaffold build time to skip
invalid sources. Therefore "compiler overhead" is paid once per Level 2 record
during scaffold construction, not during Level 3 conversational expansion. If
later phases route Level 3 expressions back through the compiler (e.g. a
post-hoc compile-validation gate), that cost would have to be measured
separately and is out of scope for T8.

### Where the time goes

The 80% serialization-and-write share of wall-clock time is dominated by:
1. `json.dumps(...)` on each conversational record dict (multi-key dict
   including `pre_state`, `assistant_response`, `provenance`, `tags`, etc.).
2. Per-record `f.write(...)` calls into the output handle (no batching).

Pure templating + RNG-driven variant assembly (the actual "generation" cost) is
~9K rec/s. There is headroom in serialization if it ever becomes the
bottleneck: per-record `dumps` + write is the next lever (e.g. accumulate
chunks, or use `orjson`). It does not need to be pulled now.

## Projection to 100K corpus

Two natural readings of "100K corpus":

| Target                                 | Output records | Single-process projection (at 1,850 rec/s) |
| -------------------------------------- | -------------- | ------------------------------------------ |
| 100K **output records** (smaller read) | 100,000        | ~54 seconds                                |
| 100K **source records** at 5 variants  | ~485,000       | ~262 seconds (~4.4 minutes)                |

Either reading sits well under the 90-minute threshold defined in T8.

Sanity check on the dataset side: `level2_full_10k.jsonl` has 10K source
records. Running variants_per_source=5 across the full file yields ~48,450
output records in ~26 seconds single-process. A 100K-source corpus does not
exist on disk today; it is the Phase 1 SDG-scaling target. When that corpus
materializes, single-process generation finishes in single-digit minutes.

## Recommendation

**Single-process is fine. T8 collapses to a 0.5d task:** wire up the existing
generator into the Phase 1 SDG-scaling flow with no multiprocessing scaffolding.

Deferred work (only if later evidence forces it):
- If serialization becomes the headline bottleneck on a 1M-record build,
  swap `json.dumps` for `orjson` or batch writes; still single-process.
- If a downstream compile-validation pass is added to the Level 3 pipeline
  (post-hoc compiler check on every conversational record), re-benchmark
  with that stage included before declaring the budget.

Multiprocessing is **not** recommended now. The slice-by-slice partitioning
that would be required (`--max-source-records` plus a per-shard offset) is not
currently supported by `Level3ConversationalGenerator.generate_to_jsonl` on
master — the CLI script `generate_level3_conversations.py` declares a
`--start-source-record` flag and a `--max-output-records` flag, but the
underlying method signature does not accept them and any actual invocation
raises `TypeError`. That is an existing latent bug in the script, surfaced
during this benchmark; flagged for follow-up but not blocking and not in
scope for T8.

## T8 effort estimate

**0.5 day** to integrate the existing single-process generator into the SDG
scaling flow. No new code beyond the wiring is required to hit 100K records
inside a few minutes of wall-clock. The bench script
(`cas-synthetic/scripts/bench_t8_throughput.py`) is committed for reuse if any
future change to the generator (e.g. compile-validation gate, NL paraphrase
expansion, register-multiplicity expansion) requires re-running the
measurement.

## Artifacts

- Benchmark script: `cas-synthetic/scripts/bench_t8_throughput.py`
- JSON summaries (gitignored): `cas-synthetic/data/level2_scaffold/_bench/bench_summary_1k.json`, `..._1k_b.json`, `..._1k_c.json`
- Generated JSONL outputs (gitignored, deleted after measurement): `bench_run_1k.jsonl`, `bench_run_1k_b.jsonl`, `bench_run_1k_c.jsonl`, `smoke.jsonl`
