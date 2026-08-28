# Cortex Head-to-Head v0.1

## Route A (native) vs Route B (pretrained open-weight cortex)

**Status:** owner-ordered benchmark informing the Route B ratification
decision (HYBRID_MACHINE_DOCTRINE.md governance note 2). TEST-ONLY: no
foreign model enters production through this board.

## The question

The doctrine proposes Route B (a pretrained open-weight language
cortex under CAS authority) as the MVP route; the standing rule says
no foreign models in production. Instead of ratifying by fiat, the two
routes fight under the RMB identical-conditions law (the SAME nine
conditions crqs/rmb.py enforces for reference-model comparison).

## The contenders

- **Route A**: CCB-L1 v0.1 - hand-built lexicon, deterministic
  grammar, typed located parse errors, the unchanged kernel.
- **Route B**: Qwen/Qwen2.5-0.5B-Instruct from the LOCAL cache,
  offline, CPU, greedy decoding - proposing meaning packets in
  CCB-L1's own schema; the SAME kernel judges its packets. This is
  the FLOOR of the doctrine's 1-3B cortex band.

## The battery (20 scored items, per-dimension, never one number)

1. In-fragment parse (6) - Route A's home ground.
2. Question answering (4) - the same kernel judges both routes'
   packets; gold = kernel status + decoded answer.
3. Unknown-word honesty (4) - signal the unknown, never fabricate.
4. Out-of-fragment breadth (6) - Route B's home ground; Route A is
   expected to refuse with a typed error (honest CANNOT).
5. Determinism - every item run twice per route.

## Fairness

The nine identical conditions are attested one by one in
h2h/grade.py::attestation(), imported from crqs.rmb. Route B's
few-shot prompt examples are disjoint from every scored item.

## Artifacts

- output/h2h_results.json - the sealed run (digest inside).
- output/h2h_report.txt - the per-dimension table.
