"""CAS expression structural similarity utilities.

Sprint 1 of the Idea Atlas feature. Public surface:

- :func:`api.similarity.cosine.cas_similarity` -- compile two CAS expressions
  and return a weighted cosine similarity score in ``[0, 1]``.
- :func:`api.similarity.cosine.extract_features` -- decompose a compiled
  artifact dict into the four primitive feature vectors plus the meta-set
  bag-of-names vector.
- :func:`api.similarity.cosine.cosine_similarity` -- pure-stdlib cosine
  between two equal-length numeric vectors.

See :doc:`README` (``api/similarity/README.md``) for the full design,
weighting rationale, and inversion-pair semantics.
"""

from api.similarity.cosine import (
    cas_similarity,
    cosine_similarity,
    extract_features,
)

__all__ = [
    "cas_similarity",
    "cosine_similarity",
    "extract_features",
]
