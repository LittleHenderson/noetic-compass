#!/usr/bin/env python3
"""
Post-process pandoc body.tex for The Cognitive Circuit Grimoire build.

Converts pandoc's plain `verbatim` environments (used for CAS/CCDL code blocks
and ASCII schematics) into fvextra `Verbatim` with line-breaking enabled, so
long CCDL statements and block diagrams fit the 6x9 measure instead of running
into the margin. It also makes inline code breakable at syntax delimiters and
turns long Markdown underscore blanks into stretchable rules. No `commandchars`
are set, so literal braces/backslashes in code remain literal.
"""
import re
from pathlib import Path

BODY = Path(__file__).with_name("body.tex")

OPEN_SRC = r"\begin{verbatim}"
OPEN_DST = r"\begin{Verbatim}[breaklines=true,breakanywhere=true,fontsize=\footnotesize]"
CLOSE_SRC = r"\end{verbatim}"
CLOSE_DST = r"\end{Verbatim}"

# Register notation (|T, |A, |f, |E) must be written "\|" in the Markdown so the
# pipe does not split a table cell. Pandoc faithfully renders that escape as a
# literal backslash, so the printed book showed "\|A" instead of "|A" — including
# in the Appendix A quick-reference card that teaches the notation. Strip the
# backslash here, after pandoc, so the Markdown tables stay valid.
PIPE_LEAK = re.compile(r"\\textbackslash\{\}(?=\\textbar\{\})")


# Pandoc emits a printable form blank such as __________ as consecutive \_
# glyphs. A rule is visually equivalent but stretches only through the space
# available in its current line or table cell.
FORM_BLANK = re.compile(r'(?:\\_){8,}')

TEXTTT_OPEN = r'\texttt{'
ALLOW_BREAK = r'\allowbreak{}'
PANDOC_RAGGED_COLUMN = r'\raggedright\arraybackslash'
PANDOC_RAGGED_HEADER = r'\begin{minipage}[b]{\linewidth}\raggedright'
WIDE_TABLE_MIN_COLUMNS = 4
WIDE_TABLE_MARKER = (
    "% grimoire-wide-table: preserve all cells; 8pt type; 2pt tabcolsep\n"
    r"\setlength{\tabcolsep}{2pt}" + "\n"
    + r"\renewcommand{\grimoiretablefont}{\scriptsize}" + "\n"
)
LONGTABLE_ENV = re.compile(
    r"(?P<marker>"
    + re.escape(WIDE_TABLE_MARKER)
    + r")?"
    + r"(?P<begin>\\begin\{longtable\}\[\]\{@\{\}\n)"
    + r"(?P<spec>.*?@\{\}\})"
    + r"(?P<body>.*?)"
    + r"(?P<end>\\end\{longtable\})",
    re.DOTALL,
)
NATURAL_LONGTABLE_START = re.compile(
    r"\\begin\{longtable\}\[\]\{@\{\}(?P<columns>[lcr]{4,})@\{\}\}"
)
NATURAL_ALIGNMENT = {
    "l": r">{\RaggedRight\arraybackslash}",
    "c": r">{\Centering\arraybackslash}",
    "r": r">{\RaggedLeft\arraybackslash}",
}
BREAKABLE_COMMANDS = (
    r'\textbar{}',
    r'\textless{}',
    r'\textgreater{}',
)
BREAK_AFTER_CHARS = frozenset('=/,;:-+×−→')


def _table_topology(table: str) -> tuple[int, int]:
    """Return stable cell-separator and row-terminator counts."""
    return table.count(" & "), table.count(" \\")


def normalize_natural_longtables(text: str) -> tuple[str, int]:
    """Give natural-width 4+ column tables explicit proportional widths."""
    environment_count = text.count(r"\begin{longtable}")

    def replace(match: re.Match[str]) -> str:
        columns = match.group("columns")
        count = len(columns)
        gaps = 2 * (count - 1)
        fraction = 1.0 / count
        specification = "\n".join(
            NATURAL_ALIGNMENT[column]
            + r"p{(\linewidth - "
            + str(gaps)
            + r"\tabcolsep) * \real{"
            + f"{fraction:.4f}"
            + "}}"
            for column in columns
        )
        return r"\begin{longtable}[]{@{}" + "\n" + specification + "@{}}"

    revised, converted = NATURAL_LONGTABLE_START.subn(replace, text)
    if revised.count(r"\begin{longtable}") != environment_count:
        raise ValueError("natural-width normalization changed longtable count")
    return revised, converted


def compact_wide_tables(text: str) -> tuple[str, int, int]:
    """Use readable 8pt type and compact gaps for tables with 5+ columns.

    This only inserts local formatting commands. Structural and byte-for-byte
    recovery assertions prove that no authored table cell or row changes.
    """
    tables_seen = 0
    wide_tables_seen = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal tables_seen, wide_tables_seen
        tables_seen += 1
        marker = match.group("marker") or ""
        begin = match.group("begin")
        spec = match.group("spec")
        body = match.group("body")
        end = match.group("end")
        column_count = spec.count("}p{")
        original = begin + spec + body + end

        if column_count < WIDE_TABLE_MIN_COLUMNS:
            if marker:
                raise ValueError(
                    "wide-table marker found below the configured column threshold"
                )
            return original

        wide_tables_seen += 1
        if marker:
            return marker + original

        revised = WIDE_TABLE_MARKER + original
        recovered = revised[len(WIDE_TABLE_MARKER) :]
        if recovered != original:
            raise ValueError("wide-table compaction changed authored table content")
        if _table_topology(revised) != _table_topology(original):
            raise ValueError("wide-table compaction changed table cells or rows")
        return revised

    revised = LONGTABLE_ENV.sub(replace, text)
    marker_count = revised.count(WIDE_TABLE_MARKER)
    if marker_count != wide_tables_seen:
        raise ValueError(
            f"wide-table marker count {marker_count} != {wide_tables_seen} "
            "eligible tables"
        )
    return revised, tables_seen, wide_tables_seen


def _break_texttt_content(content: str) -> tuple[str, int]:
    '''Add invisible breakpoints at top-level syntax boundaries.'''
    out: list[str] = []
    depth = 0
    inserted = 0
    i = 0

    def append_break(end: int) -> None:
        nonlocal inserted
        if not content.startswith(ALLOW_BREAK, end):
            out.append(ALLOW_BREAK)
            inserted += 1

    while i < len(content):
        if depth == 0:
            command = next(
                (token for token in BREAKABLE_COMMANDS if content.startswith(token, i)),
                None,
            )
            if command is not None:
                out.append(command)
                i += len(command)
                append_break(i)
                continue

            if content.startswith(r'\_', i) or content.startswith('\\ ', i):
                out.append(content[i : i + 2])
                i += 2
                append_break(i)
                continue

            if content[i] in BREAK_AFTER_CHARS:
                out.append(content[i])
                i += 1
                append_break(i)
                continue

            # Narrow code cells can be smaller than one identifier segment.
            # Give long alphanumeric runs an invisible breakpoint every four
            # characters; TeX uses these only when the token would overflow.
            if content[i].isalnum() and (i == 0 or not content[i - 1].isalnum()):
                j = i
                while j < len(content) and content[j].isalnum():
                    j += 1
                if j - i > 8:
                    break_at = set(range(i + 4, j, 4))
                    break_at.update(
                        offset
                        for offset in range(i + 1, j)
                        if content[offset].isupper() and content[offset - 1].islower()
                    )
                    for offset in range(i, j):
                        if offset in break_at:
                            out.append(ALLOW_BREAK)
                            inserted += 1
                        out.append(content[offset])
                    i = j
                    continue

            if content[i].isupper() and i > 0 and content[i - 1].islower():
                out.append(ALLOW_BREAK)
                inserted += 1

        char = content[i]
        if char == '\\' and i + 1 < len(content):
            # Copy a complete control word so CamelCase logic cannot split it.
            if content[i + 1].isalpha():
                j = i + 2
                while j < len(content) and content[j].isalpha():
                    j += 1
                out.append(content[i:j])
                i = j
                continue
            out.append(content[i : i + 2])
            i += 2
            continue
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth < 0:
                raise ValueError('unexpected closing brace inside \\texttt')
        out.append(char)
        i += 1

    if depth:
        raise ValueError('unclosed nested group inside \\texttt')
    return ''.join(out), inserted


def _matching_brace(text: str, open_brace: int) -> int:
    '''Return the closing brace paired with text[open_brace].'''
    depth = 1
    i = open_brace + 1
    while i < len(text):
        if text[i] == '\\' and i + 1 < len(text):
            # A control symbol such as \{ prints a brace; it does not group.
            i += 2
            continue
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError(f'unclosed TeX group beginning at byte {open_brace}')


def make_inline_code_breakable(text: str) -> tuple[str, int, int]:
    '''Rewrite complete texttt groups without touching nested metadata.'''
    out: list[str] = []
    cursor = 0
    search_from = 0
    spans_changed = 0
    breaks_inserted = 0

    while True:
        start = text.find(TEXTTT_OPEN, search_from)
        if start < 0:
            break
        open_brace = start + len(TEXTTT_OPEN) - 1
        close_brace = _matching_brace(text, open_brace)
        content_start = open_brace + 1
        revised, inserted = _break_texttt_content(text[content_start:close_brace])

        out.append(text[cursor:content_start])
        out.append(revised)
        out.append('}')
        cursor = close_brace + 1
        search_from = cursor
        if inserted:
            spans_changed += 1
            breaks_inserted += inserted

    out.append(text[cursor:])
    return ''.join(out), spans_changed, breaks_inserted


def main() -> None:
    text = BODY.read_text(encoding="utf-8")
    n_open = text.count(OPEN_SRC)
    text = text.replace(OPEN_SRC, OPEN_DST).replace(CLOSE_SRC, CLOSE_DST)
    text, n_natural_tables = normalize_natural_longtables(text)
    n_ragged_columns = text.count(PANDOC_RAGGED_COLUMN)
    n_ragged_headers = text.count(PANDOC_RAGGED_HEADER)
    text = text.replace(PANDOC_RAGGED_COLUMN, r'\RaggedRight\arraybackslash')
    text = text.replace(
        PANDOC_RAGGED_HEADER,
        r'\begin{minipage}[b]{\linewidth}\RaggedRight',
    )
    text, n_tables, n_wide_tables = compact_wide_tables(text)
    text, n_blanks = FORM_BLANK.subn(lambda _: r'\hrulefill{}', text)
    text, n_code_spans, n_breaks = make_inline_code_breakable(text)

    text, n_pipes = PIPE_LEAK.subn("", text)

    BODY.write_text(text, encoding="utf-8")
    print(f"postprocess: converted {n_open} verbatim block(s) to breakable Verbatim")
    print(f"postprocess: removed {n_pipes} leaked register-pipe backslash(es)")

    remaining = len(re.findall(r"\\textbackslash\{\}\\textbar\{\}", text))
    print(f'postprocess: converted {n_blanks} printable form blank(s) to rules')
    print(
        f'postprocess: added {n_breaks} inline-code breakpoint(s) '
        f'across {n_code_spans} span(s)'
    )

    print(
        f'postprocess: restored table hyphenation in {n_ragged_columns} column '
        f'declaration(s) and {n_ragged_headers} header cell(s)'
    )
    print(
        f'postprocess: normalized {n_natural_tables} natural-width table(s) '
        'with 4+ columns to proportional widths'
    )
    print(
        f'postprocess: preserved {n_tables} proportional longtable body/bodies; compacted '
        f'{n_wide_tables} table(s) with {WIDE_TABLE_MIN_COLUMNS}+ columns'
    )

    remaining_ragged = text.count(PANDOC_RAGGED_COLUMN) + text.count(PANDOC_RAGGED_HEADER)
    if remaining_ragged:
        raise SystemExit(
            f'postprocess: FAILED - {remaining_ragged} non-hyphenating table cell(s) remain'
        )
    remaining_blanks = len(FORM_BLANK.findall(text))
    if remaining_blanks:
        raise SystemExit(
            f'postprocess: FAILED - {remaining_blanks} fixed-width form blank(s) remain'
        )
    if remaining:
        raise SystemExit(f"postprocess: FAILED — {remaining} leaked '\\|' remain in body.tex")


if __name__ == "__main__":
    main()
