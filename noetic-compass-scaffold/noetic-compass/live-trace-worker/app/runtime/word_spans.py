"""Word-span reconstruction from a stream of TokenEvents.

This module turns the (token-index, token-string) sequence the model emits
into clickable word spans for the cockpit. See ``app.schemas.events.WordSpan``
docstring for the canonical boundary policy.

The function below is the single source of truth for the policy. The runtime
calls it once at end-of-stream; tests exercise it directly.
"""

from __future__ import annotations

from typing import Iterable

from ..schemas.events import WordSpan, WordSpansEvent


def build_word_spans(tokens: Iterable[tuple[int, str]]) -> WordSpansEvent:
    """Build the ``WordSpansEvent`` for a completed generation.

    Args:
        tokens: iterable of ``(token_index, token_text)`` pairs, in emission
            order. ``token_index`` need not start at 0 — whatever indices the
            worker emitted are preserved verbatim in the output.

    Returns:
        A ``WordSpansEvent`` whose spans cover exactly the non-whitespace
        runs of the concatenated text. Whitespace-only tokens are recorded
        in ``structural_token_indices``. Token-backing is lossless: every
        input token_index appears in exactly one span OR in
        ``structural_token_indices``.

    Determinism: identical input → identical output. No RNG, no clock, no
    locale-dependent calls.
    """

    materialised: list[tuple[int, str]] = [(int(i), str(t)) for i, t in tokens]

    # Walk tokens, building char ranges for each token in the running output.
    token_char_ranges: list[tuple[int, int, int, str]] = []  # (token_index, start, end, text)
    cursor = 0
    for token_index, text in materialised:
        start = cursor
        end = cursor + len(text)
        token_char_ranges.append((token_index, start, end, text))
        cursor = end

    output_text = "".join(text for _, _, _, text in token_char_ranges)

    # Identify maximal non-whitespace runs in the output text. These are the
    # raw word candidates. We then merge any run-pair that share a single
    # token, to preserve token atomicity (no span split mid-token).
    raw_runs: list[tuple[int, int]] = []  # half-open [start, end)
    i = 0
    text_len = len(output_text)
    while i < text_len:
        # Skip whitespace.
        if output_text[i].isspace():
            i += 1
            continue
        run_start = i
        while i < text_len and not output_text[i].isspace():
            i += 1
        raw_runs.append((run_start, i))

    # Map each token to the list of raw runs it overlaps. A token "overlaps"
    # a run if [token_start, token_end) ∩ [run_start, run_end) is non-empty.
    structural_token_indices: list[int] = []
    token_to_runs: dict[int, list[int]] = {}
    for token_index, t_start, t_end, t_text in token_char_ranges:
        if t_text == "" or t_text.isspace():
            structural_token_indices.append(token_index)
            continue
        overlapping: list[int] = []
        for run_i, (r_start, r_end) in enumerate(raw_runs):
            if r_end <= t_start:
                continue
            if r_start >= t_end:
                break
            # Half-open intersection non-empty?
            if max(t_start, r_start) < min(t_end, r_end):
                overlapping.append(run_i)
        token_to_runs[token_index] = overlapping

    # If any token straddles multiple raw runs, merge those runs into a
    # single span (atomicity rule). Use union-find over run indices.
    parent = list(range(len(raw_runs)))

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(a: int, b: int) -> None:
        ra, rb = _find(a), _find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for runs in token_to_runs.values():
        for j in range(1, len(runs)):
            _union(runs[0], runs[j])

    # Build merged spans: group raw runs by their union-find root in order.
    root_to_members: dict[int, list[int]] = {}
    for run_i in range(len(raw_runs)):
        root_to_members.setdefault(_find(run_i), []).append(run_i)

    # Ordered roots = first appearance in run order.
    ordered_roots: list[int] = []
    seen_roots: set[int] = set()
    for run_i in range(len(raw_runs)):
        root = _find(run_i)
        if root not in seen_roots:
            seen_roots.add(root)
            ordered_roots.append(root)

    span_for_run: dict[int, int] = {}
    span_specs: list[tuple[str, int, int]] = []  # (word, char_start, char_end)
    for span_i, root in enumerate(ordered_roots):
        members = root_to_members[root]
        span_start = raw_runs[members[0]][0]
        span_end = raw_runs[members[-1]][1]
        word = output_text[span_start:span_end]
        span_specs.append((word, span_start, span_end))
        for run_i in members:
            span_for_run[run_i] = span_i

    # Assign each non-structural token to exactly one span: the FIRST run it
    # overlaps. This is the deterministic tie-breaker — combined with the
    # merge rule above, it guarantees no split.
    span_token_lists: list[list[int]] = [[] for _ in span_specs]
    for token_index, t_start, t_end, t_text in token_char_ranges:
        if t_text == "" or t_text.isspace():
            continue
        runs = token_to_runs.get(token_index, [])
        if not runs:  # defensive: should not happen — non-empty non-space text
            structural_token_indices.append(token_index)
            continue
        target_span = span_for_run[runs[0]]
        span_token_lists[target_span].append(token_index)

    spans: list[WordSpan] = []
    for (word, char_start, char_end), indices in zip(span_specs, span_token_lists):
        if not indices:
            # Defensive: a word with no backing token shouldn't happen given
            # the construction, but skip rather than violate the schema.
            continue
        spans.append(
            WordSpan(
                word=word,
                token_indices=indices,
                char_start=char_start,
                char_end=char_end,
            )
        )

    total_tokens_covered = len(materialised)

    return WordSpansEvent(
        spans=spans,
        structural_token_indices=structural_token_indices,
        total_tokens_covered=total_tokens_covered,
    )
