"""CAS lexicon: hand-built dictionary mapping surface forms to CAS signatures."""

from .schema import (
    CASLexicon,
    LexiconEntry,
    LexiconLookup,
    load_seed_lexicon,
    seed_lexicon_path,
)

__all__ = [
    "CASLexicon",
    "LexiconEntry",
    "LexiconLookup",
    "load_seed_lexicon",
    "seed_lexicon_path",
]
