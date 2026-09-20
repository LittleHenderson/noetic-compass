"""Pure lexical occurrence spans over the unchanged v2 lossless encoding.

No instruction parsing, binding selection, gold program, evaluator, task ID or
graph enters these features. Every input token remains present. An occurrence
is an exact whole lexical unit in public.problem, never an observation tag.
Text fidelity does not establish downstream numeric-tensor fidelity.
"""
from __future__ import annotations

import re

from .codec import (ACTION_TO_ID, CJT_NAMES, PROCEDURE_NAMES, VARIABLE_NAMES,
                    PolicyContractError, validate_public)
from .features_v2 import BYTE_START, LosslessPublicTokenizer, UNIT_RULE, _word_token

SCHEMA = "cas-meta2-lexical-copy-spans/3"
COPY_SYMBOLS = PROCEDURE_NAMES + VARIABLE_NAMES + CJT_NAMES
COPY_ACTION_IDS = tuple(ACTION_TO_ID[symbol] for symbol in COPY_SYMBOLS)
_SYMBOLS = frozenset(COPY_SYMBOLS)
_UNITS = re.compile(UNIT_RULE, flags=re.UNICODE)


def encode_public_with_spans(public: dict, tokenizer: LosslessPublicTokenizer) -> dict:
    """Return exact frozen encoding plus half-open lexical/encoded spans.

    Unsupported identifier spellings remain fully encoded; they produce no
    partial match. The fixed generation vocabulary remains independently
    available. Encoded indices include the initial CLS row. Byte-fallback
    occurrences cover every UTF-8 byte, whereas fitted words cover one row.
    """
    if type(tokenizer) is not LosslessPublicTokenizer:
        raise PolicyContractError("V3_COPY_REQUIRES_FROZEN_LOSSLESS_TOKENIZER")
    try:
        validate_public(public)
    except PolicyContractError:
        raise
    except (TypeError, ValueError, OverflowError) as error:
        raise PolicyContractError("PUBLIC_VALUES_INVALID") from error
    encoded = tokenizer.encode_public(public)
    lookup = {token: index for index, token in enumerate(tokenizer.vocabulary)}
    occurrences, cursor = [], 1
    for match in _UNITS.finditer(public["problem"]):
        unit = match.group()
        # Match the frozen lexical-word/UTF-8 rules once per unit without
        # rebuilding the whole vocabulary lookup for every occurrence.
        fitted_id = lookup.get(_word_token(unit))
        unit_ids = ([fitted_id] if fitted_id is not None
                    else [BYTE_START + byte for byte in unit.encode("utf-8", errors="strict")])
        end = cursor + len(unit_ids)
        if encoded["ids"][cursor:end] != unit_ids:
            raise PolicyContractError("V3_COPY_SPAN_ENCODING_MISMATCH")
        if unit in _SYMBOLS:
            if tokenizer.decode_text(unit_ids) != unit:
                raise PolicyContractError("V3_COPY_SPAN_TEXT_MISMATCH")
            occurrences.append({"symbol": unit, "action_id": ACTION_TO_ID[unit],
                "token_start": cursor, "token_end": end,
                "char_start": match.start(), "char_end": match.end()})
        cursor = end
    if encoded["kinds"][cursor] != 1:
        raise PolicyContractError("V3_COPY_PROBLEM_BOUNDARY_MISMATCH")
    return {"encoded": encoded, "occurrences": occurrences}


def symbol_occurrences(public: dict, tokenizer: LosslessPublicTokenizer) -> list[dict]:
    return encode_public_with_spans(public, tokenizer)["occurrences"]
