"""spans.py -- FROZEN input construction and token-span mapping (architecture
binding: one sequence per passage = clause texts joined by single spaces, then
a newline, then the question; token belongs to a clause iff its character span
overlaps the clause's; a zero-token clause aborts with SPAN_MAPPING_FAILURE).

Pure functions over character offsets -- testable without any tokenizer.
"""
from __future__ import annotations


class SpanMappingFailure(RuntimeError):
    pass


def build_input_text(record: dict) -> str:
    return " ".join(c["text"] for c in record["clauses"]) + "\n" + record["question"]


def clause_char_spans(record: dict):
    """[(start, end) per clause] + (qstart, qend), in build_input_text coordinates."""
    spans, pos = [], 0
    for c in record["clauses"]:
        spans.append((pos, pos + len(c["text"])))
        pos += len(c["text"]) + 1                      # the joining space / newline
    qstart = pos
    return spans, (qstart, qstart + len(record["question"]))


def token_spans(char_spans, question_span, offset_mapping):
    """Map character spans to token index lists via the tokenizer offset_mapping
    [(char_start, char_end) per token]. Overlap rule: token t belongs to span s
    iff max(t_start, s_start) < min(t_end, s_end). Zero-token spans fail closed."""
    def toks(span):
        s0, s1 = span
        out = [i for i, (t0, t1) in enumerate(offset_mapping)
               if max(t0, s0) < min(t1, s1)]
        if not out:
            raise SpanMappingFailure(f"SPAN_MAPPING_FAILURE: span {span} has 0 tokens")
        return out
    return [toks(s) for s in char_spans], toks(question_span)
