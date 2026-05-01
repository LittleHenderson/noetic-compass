"""CAS-Native tokenizer package.

The tokenizer is the first layer of CAS reasoning, not a vocabulary mapping.
Every output token carries:

  - exact ``surface_span`` provenance back to the source character offsets,
  - an explicit ``cas_signature`` over the four CAS axes (Noetic / Domain /
    Drive / Register) plus role tags,
  - a ``source`` flag (LEXICON / LEARNED / CAS_NOTATION / FALLBACK) recording
    how the signature was assigned.

Wave 1 of the build (this module) supplies deterministic, rule-based
components:

  - ``structured_token`` — token + signature schema.
  - ``pretokenizer``     — span-tracking segmentation.
  - ``cas_notation``     — CAS-notation literal recognizer (v7.7 coverage).
  - ``lexicon``          — hand-built surface → signature lexicon.
  - ``assembler``        — end-to-end ``tokenize(text)`` entry point.

A learned CAS-axis tagger (Wave 3) plugs in alongside the lexicon for OOV
coverage. The seed lexicon is the source of truth for the lexicon-anchored
case; lexicon entries always win over the learned tagger.
"""

from .assembler import TokenizeStats, tokenize, tokenize_with_stats
from .cas_notation import CASNotationMatch, find_all_cas_notation, match_cas_notation
from .lexicon import CASLexicon, LexiconEntry, LexiconLookup, load_seed_lexicon, seed_lexicon_path
from .pretokenizer import PretokenSpan, pretokenize, reassemble
from .structured_token import (
    DOMAIN_AXIS_LEN,
    DOMAIN_LABELS,
    DRIVE_AXIS_LEN,
    NOETIC_AXIS_LEN,
    REGISTER_AXIS_LEN,
    REGISTER_LABELS,
    CASSignature,
    StructuredToken,
    TokenSource,
)
from .vocabulary import (
    BOS_ID,
    BOS_TOKEN,
    CAS_LITERAL_ID,
    CAS_LITERAL_TOKEN,
    EOS_ID,
    EOS_TOKEN,
    FALLBACK_NEUTRAL_ID,
    FALLBACK_NEUTRAL_TOKEN,
    LEXICON_HIT_ID,
    LEXICON_HIT_TOKEN,
    MASK_ID,
    MASK_TOKEN,
    PAD_ID,
    PAD_TOKEN,
    RESERVED_TOKENS,
    UNK_ID,
    UNK_TOKEN,
    StructuredTokenVocabulary,
    structured_token_key,
)

__all__ = [
    "DOMAIN_AXIS_LEN",
    "DOMAIN_LABELS",
    "DRIVE_AXIS_LEN",
    "NOETIC_AXIS_LEN",
    "REGISTER_AXIS_LEN",
    "REGISTER_LABELS",
    "CASLexicon",
    "CASNotationMatch",
    "CASSignature",
    "LexiconEntry",
    "LexiconLookup",
    "PretokenSpan",
    "StructuredToken",
    "TokenSource",
    "TokenizeStats",
    "BOS_ID",
    "BOS_TOKEN",
    "CAS_LITERAL_ID",
    "CAS_LITERAL_TOKEN",
    "EOS_ID",
    "EOS_TOKEN",
    "FALLBACK_NEUTRAL_ID",
    "FALLBACK_NEUTRAL_TOKEN",
    "LEXICON_HIT_ID",
    "LEXICON_HIT_TOKEN",
    "MASK_ID",
    "MASK_TOKEN",
    "PAD_ID",
    "PAD_TOKEN",
    "RESERVED_TOKENS",
    "UNK_ID",
    "UNK_TOKEN",
    "StructuredTokenVocabulary",
    "structured_token_key",
    "find_all_cas_notation",
    "load_seed_lexicon",
    "match_cas_notation",
    "pretokenize",
    "reassemble",
    "seed_lexicon_path",
    "tokenize",
    "tokenize_with_stats",
]
