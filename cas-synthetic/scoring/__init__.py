"""Content-preservation scoring for Path D corpora.

This subpackage holds offline scorers that check whether a generated
English (or generated CAS) reply preserved the load-bearing structural
content of its source CAS expression. Numerical anti-drift gates (leakage,
rejection, chemistry, level-drift) are NECESSARY but NOT SUFFICIENT —
they catch lexical violations only. Content-preservation scoring catches
the semantic failure modes (coefficient drops in recipes, fractal
k-misreads, domain swaps, parrot pipelines, unrelated corrections).

See `feedback_anti_drift_gates_not_content_preservation.md` in the
project memory for the failure-mode taxonomy.

Pure stdlib + regex only — no ML model dependencies, no embeddings.
"""

from __future__ import annotations

from .content_preservation import score_corpus, score_record

__all__ = ["score_record", "score_corpus"]
