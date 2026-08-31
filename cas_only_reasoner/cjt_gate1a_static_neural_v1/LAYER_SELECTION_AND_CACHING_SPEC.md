# Layer selection and activation caching — FROZEN law

## Layer selection (one law, all arms)

- Candidate layers: **{6, 12, 18, 24}** of Qwen2.5-0.5B-Instruct (24 layers).
- Selection procedure: train the **S0 head only**, one run per candidate layer at
  seed 11, and pick L* = the layer with the highest **validation** exact-match
  accuracy (ties broken toward the SHALLOWER layer, deterministically).
- The selected L* is then used by **every arm and every seed**. No per-arm layer
  tuning, ever. The four selection runs are part of the Gate 1B budget and are
  recorded in the execution receipt (layer, validation accuracy, tie-break applied).
- The protected split plays no role in selection.

## Idea and question representations

- `h_i` = mean over Idea i's token hidden states at L* (clause token spans computed
  deterministically from the frozen tokenizer over the `clauses` fields).
- `g` = mean over the question's token hidden states at L*.

## Caching law (cache once, reuse everywhere)

- Hidden states at all four candidate layers are extracted **once per passage** on
  AWS GPU (one pass over train + validation; the protected split is extracted only
  in the final protected-evaluation step, after all training is complete).
- The cache is stored to the run's S3 prefix as fp16 tensors keyed by
  `(passage_id, layer)`, with a cache manifest recording the model revision digest,
  tokenizer digest, dataset digests, and per-shard SHA-256.
- Every arm/seed trains its heads FROM THE CACHE. The base model does exactly one
  forward pass per passage per split; no arm re-extracts. This is the registered
  cost-control and the guarantee that arms see literally identical inputs.
- Cache invalidation: any mismatch between the cache manifest's model/tokenizer/
  dataset digests and the job's resolved digests aborts with `CACHE_INTEGRITY_FAILURE`.
