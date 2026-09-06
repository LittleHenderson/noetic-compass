# v6 recorded-result review

Prepared for source `acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0` and
job `cas-meta2-20260906064703-c0d74ffa` before its results were available.
The script has not yet passed against a completed v6 packet. `--help` only
checks that its command-line entry point loads.

The review checks the externally supplied result archive hash, frozen source
package, complete collection index, recorded CUDA gates, checkpoint bytes,
saved validation actions, selected checkpoint history, and native summary
counts. It does not load a checkpoint or import a neural framework.

This is not an independent neural rerun or a stored-trace semantic audit.
Those evidence boundaries must remain separate. No result or candidate is
accepted merely because this script exists or its checks pass.

Use `review.py --sha256 <verified downloaded packet SHA-256>` after the
launcher has completed collection. It requires a new extraction directory
and refuses to overwrite an existing review receipt.
