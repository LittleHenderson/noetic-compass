#!/usr/bin/env python3
"""
Post-process pandoc-generated body.tex to fix LaTeX-invalid math constructs
inherited from the manuscript's informal math notation. These are mechanical
replacements that preserve author intent while rendering correctly.

Includes Unicode glyph remediation: certain math-symbol Unicode codepoints
(U+2208 ∈, U+2209 ∉, U+2282 ⊂, U+2286 ⊆, U+2283 ⊃, U+2287 ⊇, U+2205 ∅,
U+27E8 ⟨, U+27E9 ⟩, U+2218 ∘) lack glyphs in the system mono fonts (Consolas,
Cascadia, Courier) AND in the Palatino body. They render correctly in Latin
Modern Math via \\ensuremath{}, but inside `\\texttt` and `verbatim` blocks the
substitution doesn't fire (verbatim disables active chars). This pass:

1. Replaces `\\begin{verbatim}...\\end{verbatim}` blocks containing any of
   these characters with `\\begin{Verbatim}[commandchars=\\\\\\{\\}]...\\end{Verbatim}`
   (fancyvrb, with command-char escaping enabled), substituting each problem
   character with `\\unimath{<latex-name>}`.

2. Replaces `\\texttt{...}` content where the argument contains problem chars
   with the same `\\unimath{...}` substitution.

The `\\unimath` macro is defined in preamble.tex; it switches to math mode
briefly (which uses Latin Modern Math) for one symbol.
"""

import re
from pathlib import Path

BODY = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\publishing\latex\body.tex")

# Codepoint -> LaTeX math name (without backslash, used by \unimath{name})
PROBLEM_CHARS = {
    "∈": "in",        # ∈
    "∉": "notin",     # ∉
    "⊂": "subset",    # ⊂
    "⊆": "subseteq",  # ⊆
    "⊃": "supset",    # ⊃
    "⊇": "supseteq",  # ⊇
    "∅": "varnothing", # ∅
    "⟨": "langle",    # ⟨
    "⟩": "rangle",    # ⟩
    "∘": "circ",      # ∘
}

# Subscript / superscript codepoints that need conversion to TeX subscript
# (in math mode). Mono fonts lack glyphs for the LATIN SUBSCRIPT letters but
# every TeX math font has ordinary letters in subscript-size positions.
SUBSCRIPTS = {
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "ₐ": "a", "ₑ": "e", "ₕ": "h", "ᵢ": "i", "ⱼ": "j",
    "ₖ": "k", "ₗ": "l", "ₘ": "m", "ₙ": "n", "ₒ": "o",
    "ₚ": "p", "ᵣ": "r", "ₛ": "s", "ₜ": "t", "ᵤ": "u",
    "ᵥ": "v", "ₓ": "x",
}
SUPERSCRIPTS = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
}


def substitute_subscripts(s: str) -> str:
    """Replace each subscript Unicode char with $_{plain}$ math-subscript."""
    for ch, ascii_ch in SUBSCRIPTS.items():
        s = s.replace(ch, f"\\textsubscript{{{ascii_ch}}}")
    for ch, ascii_ch in SUPERSCRIPTS.items():
        s = s.replace(ch, f"\\textsuperscript{{{ascii_ch}}}")
    return s


def substitute_chars(s: str) -> str:
    """Replace each problem character with \\unimath{name}."""
    for ch, name in PROBLEM_CHARS.items():
        s = s.replace(ch, f"\\unimath{{{name}}}")
    return s


def transform_verbatim_blocks(text: str) -> str:
    """Convert verbatim blocks containing problem chars to fancyvrb Verbatim."""

    def repl(match):
        body = match.group(1)
        if not any(ch in body for ch in PROBLEM_CHARS):
            return match.group(0)  # leave unchanged

        # Substitute the problem chars in the body
        new_body = substitute_chars(body)

        # Use fancyvrb Verbatim with command-char escaping so the \unimath
        # commands are interpreted. \ { } become the escape characters.
        return ("\\begin{Verbatim}[commandchars=\\\\\\{\\}]" + new_body
                + "\\end{Verbatim}")

    pattern = re.compile(r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}", re.DOTALL)
    return pattern.sub(repl, text)


def find_balanced(text: str, start: int) -> int:
    """Given start = position of opening '{', return position of matching '}'.
    Returns -1 if not balanced. Handles \\{ and \\} as escaped braces."""
    depth = 0
    i = start
    while i < len(text):
        c = text[i]
        if c == "\\" and i + 1 < len(text) and text[i+1] in "{}":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def transform_texttt(text: str) -> str:
    """In \\texttt{...} arguments, replace problem chars with \\unimath escapes.
    Handles nested braces via balanced-brace finder."""
    out = []
    i = 0
    needle = "\\texttt{"
    while i < len(text):
        idx = text.find(needle, i)
        if idx < 0:
            out.append(text[i:])
            break
        out.append(text[i:idx])
        brace_start = idx + len(needle) - 1  # position of opening {
        brace_end = find_balanced(text, brace_start)
        if brace_end < 0:
            out.append(text[idx:])
            break
        arg = text[brace_start+1:brace_end]
        if any(ch in arg for ch in PROBLEM_CHARS):
            out.append("\\texttt{" + substitute_chars(arg) + "}")
        else:
            out.append(text[idx:brace_end+1])
        i = brace_end + 1
    return "".join(out)


def transform_highlighting_blocks(text: str) -> str:
    """pandoc's syntax-highlighting wraps content in \\begin{Shaded}\\begin{Highlighting}.
    Inside, content uses \\NormalTok{...}, \\StringTok{...}, etc. Highlighting is a
    Verbatim-like env where \\newunicodechar substitutions don't fire.

    Substitute problem chars inside \\NormalTok{...}, \\StringTok{...},
    \\KeywordTok{...} arguments. The argument may include escaped braces.
    """
    tok_macros = ("NormalTok", "StringTok", "KeywordTok", "DataTypeTok",
                  "OperatorTok", "OtherTok", "CommentTok", "ErrorTok",
                  "FunctionTok", "ConstantTok", "BuiltInTok", "CharTok",
                  "DecValTok", "FloatTok", "VariableTok", "ControlFlowTok",
                  "AttributeTok", "InformationTok", "WarningTok", "AlertTok",
                  "ImportTok", "BaseNTok", "PreprocessorTok", "VerbatimStringTok",
                  "SpecialStringTok", "SpecialCharTok", "DocumentationTok")

    def make_repl(macro):
        def repl(match):
            arg = match.group(1)
            if not any(ch in arg for ch in PROBLEM_CHARS):
                return match.group(0)
            return "\\" + macro + "{" + substitute_chars(arg) + "}"
        return repl

    for macro in tok_macros:
        # Match the argument up to the matching close brace; allow escaped \{ \}
        # but pandoc doesn't nest braces inside Tok args, so a simple match is OK
        pattern = re.compile(
            r"\\" + macro + r"\{((?:[^{}\\]|\\[^{}]|\\\{|\\\})*)\}"
        )
        text = pattern.sub(make_repl(macro), text)

    return text


def main() -> None:
    text = BODY.read_text(encoding="utf-8")
    original_len = len(text)

    # Fix \text{^N} and \text{^} inside math — caret is math-active.
    # Replace with \text{\textasciicircum N} which renders literally.
    text = re.sub(r"\\text\{\^(\d+)\}", r"\\text{\\textasciicircum\1}", text)
    text = re.sub(r"\\text\{\^\}", r"\\text{\\textasciicircum{}}", text)

    # Unicode glyph remediation
    text = transform_verbatim_blocks(text)
    text = transform_texttt(text)
    text = transform_highlighting_blocks(text)

    # Final pass: any remaining bare problem chars in text mode get replaced
    # globally with \unimath{name} since \newunicodechar substitution proves
    # unreliable for these codepoints (likely because unicode-math claims them
    # for math mode and the text-mode shadow has weaker glyph fallback).
    text = substitute_chars(text)
    # Subscript/superscript Unicode chars also lack glyphs in mono fonts;
    # \textsubscript / \textsuperscript handle them in any context.
    text = substitute_subscripts(text)

    # Also fix bare problem chars in regular paragraph text by relying on the
    # \newunicodechar declarations in preamble (these already work for normal
    # text-mode). No action needed here for non-verbatim non-texttt prose.

    BODY.write_text(text, encoding="utf-8")
    print(f"Post-processed body.tex (was {original_len} -> {len(text)} chars)")


if __name__ == "__main__":
    main()
