"""End-to-end tests for the CAS tokenizer assembler."""

from __future__ import annotations

from cas_native.tokenizer.assembler import tokenize, tokenize_with_stats
from cas_native.tokenizer.structured_token import (
    DOMAIN_LABELS,
    REGISTER_LABELS,
    TokenSource,
)


def _surfaces(tokens) -> list[str]:
    return [t.surface_text for t in tokens]


def test_tokenize_natural_language_demographic_diversity():
    """Each demographic register variant produces F3-vitality-depressing tokens."""
    for prompt in (
        "I am hella tired today",
        "I am super sleepy now",
        "I am profoundly fatigued by this",
        "I am exhausted",
    ):
        tokens = tokenize(prompt)
        kept = [t for t in tokens if t.source == TokenSource.LEXICON]
        # At least one lexicon-anchored token must depress F3 vitality.
        assert any(t.cas_signature.drive[2] < 0.0 for t in kept), (
            f"prompt={prompt!r} produced no F3-depleting token"
        )


def test_tokenize_visceral_aversion_anti_drift():
    """'can't stomach' fires ^3, NOT ^6."""
    tokens = tokenize("I can't stomach this idea")
    sigs = [t.cas_signature for t in tokens if t.source == TokenSource.LEXICON]
    assert any(s.noetic[3] >= 0.9 for s in sigs)
    assert not any(s.noetic[6] >= 0.8 for s in sigs), (
        "visceral aversion must NOT fire ^6 Male decomposition"
    )


def test_tokenize_analytical_critique_anti_drift():
    """'audit' fires ^6, NOT ^3."""
    tokens = tokenize("we will audit this carefully")
    sigs = [t.cas_signature for t in tokens if t.source == TokenSource.LEXICON]
    assert any(s.noetic[6] >= 0.8 for s in sigs)
    assert not any(s.noetic[3] >= 0.5 for s in sigs), (
        "analytical critique must NOT fire ^3 Negative"
    )


def test_tokenize_associative_trigger_anti_drift():
    """'reminds me of' fires ^8, NOT a deductive-reasoning compound."""
    tokens = tokenize("that reminds me of last week")
    sigs = [t.cas_signature for t in tokens if t.source == TokenSource.LEXICON]
    assert any(s.noetic[8] >= 0.85 for s in sigs)


def test_tokenize_etymological_cognate_for_vibration():
    """'struck a chord' fires strong ^4."""
    tokens = tokenize("that really struck a chord with me")
    sigs = [t.cas_signature for t in tokens if t.source == TokenSource.LEXICON]
    assert any(s.noetic[4] >= 0.9 for s in sigs)


def test_tokenize_cas_notation_literal():
    """A literal CAS expression in input should emit CAS_NOTATION tokens."""
    tokens = tokenize("the state ^2^P_{F4}|f matters")
    cas_tokens = [t for t in tokens if t.source == TokenSource.CAS_NOTATION]
    assert len(cas_tokens) >= 1
    # The full compound state must come back as one token, not three pieces.
    assert any(t.surface_text == "^2^P_{F4}|f" for t in cas_tokens)
    # Confidence of CAS-notation literals is always 1.0.
    assert all(t.confidence == 1.0 for t in cas_tokens)


def test_tokenize_recipe_form_finds_omega_and_arrow():
    text = "Θ(Ω_focus) = 0.40*^3^P_{F2}|A → Ω_focus"
    tokens = tokenize(text)
    cas_tokens = [t for t in tokens if t.source == TokenSource.CAS_NOTATION]
    role_tags = {tag for t in cas_tokens for tag in t.cas_signature.role_tags}
    assert "omega_target" in role_tags
    assert "recipe_opener" in role_tags
    assert "arrow" in role_tags
    assert "compound_state" in role_tags


def test_tokenize_preserves_full_character_provenance_for_lexicon_tokens():
    text = "I feel drawn to this idea"
    tokens = tokenize(text)
    drawn_tokens = [t for t in tokens if t.surface_text.lower() == "drawn to"]
    assert len(drawn_tokens) == 1
    start, end = drawn_tokens[0].surface_span
    assert text[start:end].lower() == "drawn to"


def test_tokenize_unknown_words_fall_back_with_neutral_signature():
    tokens = tokenize("xyzzqq is not a real word")
    fallback = [t for t in tokens if t.source == TokenSource.FALLBACK]
    assert any(t.surface_text.lower() == "xyzzqq" for t in fallback)
    for t in fallback:
        assert t.cas_signature.is_neutral()
        assert t.confidence == 0.0


def test_tokenize_with_stats_reports_provenance_breakdown():
    text = "I feel drawn to ^2^P_{F4}|f"
    tokens, stats = tokenize_with_stats(text)
    assert stats.n_tokens == len(tokens)
    assert stats.n_cas_notation >= 1
    assert stats.n_lexicon >= 1
    assert stats.n_lexicon + stats.n_cas_notation + stats.n_fallback == stats.n_tokens


def test_tokenize_canonical_example_produces_expected_axes():
    """Smoke test on the user-shown sentence."""
    text = "I feel kind of nervous about doing this thing."
    tokens = tokenize(text)
    sigs_by_surface = {t.surface_text.lower(): t.cas_signature for t in tokens}
    # 'feel' fires |f register
    assert sigs_by_surface.get("feel", None) is not None
    assert sigs_by_surface["feel"].register[REGISTER_LABELS.index("f")] >= 0.8
    # 'nervous' fires ^3 with affective register
    assert sigs_by_surface.get("nervous", None) is not None
    assert sigs_by_surface["nervous"].noetic[3] >= 0.6
    # 'doing' fires O Domain
    assert sigs_by_surface.get("doing", None) is not None
    assert sigs_by_surface["doing"].domain[DOMAIN_LABELS.index("O")] >= 0.8


def test_tokenize_offsets_are_monotonic_increasing():
    tokens = tokenize("I feel drawn to this idea")
    last_end = -1
    for t in tokens:
        assert t.surface_span[0] >= last_end
        last_end = t.surface_span[1]


def test_tokenize_handles_empty_input():
    assert tokenize("") == []
