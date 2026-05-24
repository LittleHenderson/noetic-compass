"""Worker-side word-span reconstruction tests.

These exercise ``app.runtime.word_spans.build_word_spans`` — the single
source of truth for the click-to-inspect token-backing the cockpit relies
on. The policy is documented in ``app.schemas.events.WordSpan``.

Each test below pins one behavioural invariant. If a test breaks, the UI's
click-on-word feature is at risk: tokens may go missing from spans, spans
may be split mid-token, or char ranges may stop pointing at the rendered
substring.
"""

from __future__ import annotations

from app.runtime.word_spans import build_word_spans


def _reconstruct(tokens: list[tuple[int, str]]) -> str:
    return "".join(t for _, t in tokens)


def test_simple_words_each_one_token() -> None:
    """Plain whitespace-separated tokens — one token per word."""
    tokens = [(0, "hello"), (1, " "), (2, "world")]
    out = build_word_spans(tokens)

    assert out.total_tokens_covered == 3
    assert [s.word for s in out.spans] == ["hello", "world"]
    assert out.spans[0].token_indices == [0]
    assert out.spans[1].token_indices == [2]
    assert out.structural_token_indices == [1]
    text = _reconstruct(tokens)
    for span in out.spans:
        assert text[span.char_start : span.char_end] == span.word


def test_bpe_style_leading_space_token_belongs_to_following_word() -> None:
    """Leading-whitespace tokens (e.g. ' hello') attach to the following word."""
    tokens = [(0, "hello"), (1, " world")]
    out = build_word_spans(tokens)

    assert [s.word for s in out.spans] == ["hello", "world"]
    assert out.spans[0].token_indices == [0]
    # Token 1's leading whitespace is part of the inter-word gap at the char
    # level, but the TOKEN itself belongs to "world".
    assert out.spans[1].token_indices == [1]
    assert out.structural_token_indices == []
    assert out.total_tokens_covered == 2

    text = _reconstruct(tokens)
    assert text[out.spans[0].char_start : out.spans[0].char_end] == "hello"
    assert text[out.spans[1].char_start : out.spans[1].char_end] == "world"


def test_multi_token_word_groups_correctly() -> None:
    """A word built from multiple sub-token pieces lands in ONE span."""
    # "tokenisation" split into three sub-tokens, with a leading-space first piece.
    tokens = [(0, " token"), (1, "isa"), (2, "tion"), (3, " is"), (4, " neat")]
    out = build_word_spans(tokens)

    assert [s.word for s in out.spans] == ["tokenisation", "is", "neat"]
    assert out.spans[0].token_indices == [0, 1, 2]
    assert out.spans[1].token_indices == [3]
    assert out.spans[2].token_indices == [4]
    assert out.structural_token_indices == []

    text = _reconstruct(tokens)
    for span in out.spans:
        assert text[span.char_start : span.char_end] == span.word


def test_single_char_tokens_each_one_word() -> None:
    """Single-character non-whitespace tokens with whitespace between."""
    tokens = [(0, "a"), (1, " "), (2, "b"), (3, " "), (4, "c")]
    out = build_word_spans(tokens)
    assert [s.word for s in out.spans] == ["a", "b", "c"]
    assert out.spans[0].token_indices == [0]
    assert out.spans[1].token_indices == [2]
    assert out.spans[2].token_indices == [4]
    assert sorted(out.structural_token_indices) == [1, 3]


def test_punctuation_extends_prior_word_when_no_leading_space() -> None:
    """A punctuation token glued to the prior word stays in that span."""
    tokens = [(0, "hello"), (1, ","), (2, " world"), (3, "!")]
    out = build_word_spans(tokens)

    assert [s.word for s in out.spans] == ["hello,", "world!"]
    assert out.spans[0].token_indices == [0, 1]
    assert out.spans[1].token_indices == [2, 3]
    assert out.structural_token_indices == []


def test_whitespace_only_tokens_are_structural() -> None:
    """Tokens decoding only to whitespace land in structural_token_indices."""
    tokens = [(0, "x"), (1, " "), (2, "\n"), (3, "\t"), (4, "y")]
    out = build_word_spans(tokens)
    assert [s.word for s in out.spans] == ["x", "y"]
    assert out.spans[0].token_indices == [0]
    assert out.spans[1].token_indices == [4]
    assert sorted(out.structural_token_indices) == [1, 2, 3]


def test_lossless_token_backing_invariant() -> None:
    """Every token_index appears in exactly one span OR is structural."""
    tokens = [
        (0, "The"),
        (1, " quick"),
        (2, " brown"),
        (3, " fox"),
        (4, "."),
        (5, " "),
        (6, "End"),
    ]
    out = build_word_spans(tokens)

    all_indices = {i for i, _ in tokens}
    span_union: set[int] = set()
    for span in out.spans:
        # No duplicates inside a span.
        assert len(set(span.token_indices)) == len(span.token_indices)
        # No overlap with prior spans.
        assert span_union.isdisjoint(span.token_indices)
        span_union.update(span.token_indices)

    structural = set(out.structural_token_indices)
    # No token is BOTH structural and in a span.
    assert span_union.isdisjoint(structural)
    # Every token is accounted for.
    assert span_union | structural == all_indices
    # total_tokens_covered matches.
    assert out.total_tokens_covered == len(tokens)


def test_char_ranges_are_contiguous_in_span_order_and_match_text() -> None:
    """Spans are sorted by char_start and the substring matches the word."""
    tokens = [(0, "alpha"), (1, " beta"), (2, " gamma")]
    out = build_word_spans(tokens)
    text = _reconstruct(tokens)

    last_end = -1
    for span in out.spans:
        assert span.char_start >= last_end
        assert span.char_end > span.char_start
        assert text[span.char_start : span.char_end] == span.word
        last_end = span.char_end


def test_empty_token_sequence_produces_empty_event() -> None:
    out = build_word_spans([])
    assert out.spans == []
    assert out.structural_token_indices == []
    assert out.total_tokens_covered == 0


def test_token_atomicity_when_decode_crosses_runs() -> None:
    """If a single token decodes to text containing whitespace, the resulting
    raw runs are MERGED so the token is not split across spans.

    This is a rare edge case (BPE tokens normally don't contain internal
    whitespace runs), but the policy must handle it deterministically.
    """
    # Single token "foo bar" — would normally yield two raw runs ("foo",
    # "bar"), but must be merged because splitting would violate atomicity.
    tokens = [(0, "foo bar"), (1, " baz")]
    out = build_word_spans(tokens)

    assert [s.word for s in out.spans] == ["foo bar", "baz"]
    assert out.spans[0].token_indices == [0]
    assert out.spans[1].token_indices == [1]
    assert out.structural_token_indices == []


def test_token_indices_preserved_as_given() -> None:
    """If the worker emits non-zero-based indices, the event preserves them."""
    tokens = [(7, "hi"), (8, " "), (9, "there")]
    out = build_word_spans(tokens)
    assert out.spans[0].token_indices == [7]
    assert out.spans[1].token_indices == [9]
    assert out.structural_token_indices == [8]
    assert out.total_tokens_covered == 3


def test_deterministic_under_identical_input() -> None:
    """Same input → same output. No RNG, no hash randomisation."""
    tokens = [(0, "hello"), (1, " "), (2, "world"), (3, "!")]
    a = build_word_spans(tokens)
    b = build_word_spans(tokens)
    assert a.model_dump() == b.model_dump()
