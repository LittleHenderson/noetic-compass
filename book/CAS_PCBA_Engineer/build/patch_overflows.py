# -*- coding: utf-8 -*-
"""Second KDP margin pass: texttt threshold 12 + more break chars,
prose arrow breaks, footnotesize natural-width longtables, resize tikz fig."""
from pathlib import Path
import re

BS = chr(92)
ALLOW = BS + 'allowbreak{}'
BREAK_AFTER = ['=', '|', ',', ';', '→', '/', '›', '(', '·']
TT = BS + 'texttt{'

src = Path('body.tex').read_text(encoding='utf-8')

# ---- pass 1: texttt args ----------------------------------------------------
def patch_arg(arg):
    if len(arg) < 12 or ALLOW in arg:
        return arg
    out = []
    i = 0
    while i < len(arg):
        ch = arg[i]
        if ch == BS and i + 1 < len(arg):
            seq = arg[i:i + 2]
            out.append(seq)
            i += 2
            if seq == BS + '_':
                out.append(ALLOW)
            continue
        out.append(ch)
        i += 1
        if ch in BREAK_AFTER:
            out.append(ALLOW)
    return ''.join(out)

res, i, n_tt = [], 0, 0
while True:
    j = src.find(TT, i)
    if j == -1:
        res.append(src[i:])
        break
    res.append(src[i:j])
    k = j + len(TT)
    depth, m = 1, k
    while m < len(src) and depth:
        c = src[m]
        if c == BS:
            m += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        m += 1
    arg = src[k:m - 1]
    new = patch_arg(arg)
    if new != arg:
        n_tt += 1
    res.append(TT + new + '}')
    i = m
src = ''.join(res)

# ---- pass 2: prose arrows (skip Verbatim + tikzpicture) --------------------
lines = src.split('\n')
out_lines = []
in_verb = in_tikz = False
n_arrow = 0
for ln in lines:
    if BS + 'begin{Verbatim}' in ln:
        in_verb = True
    if BS + 'begin{tikzpicture}' in ln:
        in_tikz = True
    if not in_verb and not in_tikz and '→' in ln and ALLOW not in ln:
        new = ln.replace('→', '→' + ALLOW)
        if new != ln:
            n_arrow += 1
            ln = new
    if BS + 'end{Verbatim}' in ln:
        in_verb = False
    if BS + 'end{tikzpicture}' in ln:
        in_tikz = False
    out_lines.append(ln)
src = '\n'.join(out_lines)

# ---- pass 3: natural-width longtables --> footnotesize group ---------------
pat = re.compile(r'\\begin\{longtable\}\[\]\{@\{\}l+@\{\}\}')
n_lt = 0
pos = 0
chunks = []
for m in pat.finditer(src):
    chunks.append(src[pos:m.start()])
    chunks.append(BS + 'begingroup' + BS + 'footnotesize' + m.group(0))
    pos = m.end()
    n_lt += 1
chunks.append(src[pos:])
src = ''.join(chunks)
# close the groups after their matching \end{longtable}
if n_lt:
    parts = src.split(BS + 'end{longtable}')
    rebuilt = parts[0]
    for p in parts[1:]:
        rebuilt += BS + 'end{longtable}'
        # count opens minus closes so far to know if a group is pending
        opens = rebuilt.count(BS + 'begingroup' + BS + 'footnotesize' + BS + 'begin{longtable}')
        closes = rebuilt.count(BS + 'endgroup% lt')
        if opens > closes:
            rebuilt += BS + 'endgroup% lt' + '\n'
        rebuilt += p
    src = rebuilt

# ---- pass 4: resize the domain-layers tikzpicture --------------------------
anchor = '(O9.east) -- ++(3.0,0) |- (P0.east)'
n_tikz = 0
if anchor in src:
    a = src.rfind(BS + 'begin{tikzpicture}', 0, src.find(anchor))
    b = src.find(BS + 'end{tikzpicture}', src.find(anchor))
    b_end = b + len(BS + 'end{tikzpicture}')
    src = (src[:a] + BS + 'resizebox{' + BS + 'linewidth}{!}{%\n'
           + src[a:b_end] + '}%\n' + src[b_end:])
    n_tikz = 1

# ---- pass 5: shorten running heads that would wrap to two lines ------------
# A two-line running head overflows memoir's 13.6pt head slot and raises
# "Overfull \vbox (13.59999pt too high)" on that recto page. memoir's
# \section takes three arguments -- \section[TOC][head mark]{printed heading}
# (memoir.cls \@trplargomm / \M@sect: #7 -> TOC and PDF title, #8 -> \markright,
# #9 -> printed) -- so a shortened mark changes only the running head. The
# printed heading, the TOC entry, the PDF bookmark and every page break are
# untouched, so pass 5 cannot repaginate the book.
HEAD_LIMIT = 50
HEAD_MIN = 22
SEPARATORS = (' — ', ': ', ', ', ' – ')
TEXORPDF = BS + 'texorpdfstring{'


def balanced_arg(s, start):
    """Return (argument, index_after_closing_brace) for the group opening at start."""
    depth, i = 1, start + 1
    while i < len(s) and depth:
        if s[i] == BS:
            i += 2
            continue
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
        i += 1
    return s[start + 1:i - 1], i


TEXT_MACROS = {'texttt', 'emph', 'textbf', 'textit', 'textsc', 'textrm',
               'textsf', 'mbox', 'textsuperscript', 'textsubscript'}
SYMBOL_MACROS = {
    'textless': '<', 'textgreater': '>', 'textbar': '|', 'textbackslash': '/',
    'textasciitilde': '~', 'textasciicircum': '^', 'textquotesingle': "'",
    'textquotedblleft': '"', 'textquotedblright': '"', 'textendash': '-',
    'textemdash': '\u2014', 'ldots': '...', 'textbullet': '-',
    'textregistered': '(R)', 'texttrademark': '(TM)', 'textdegree': 'deg',
}
ESCAPES = {'{': '(', '}': ')', '_': '_', '%': '%', '&': '&', '#': '#',
           ' ': ' ', ',': ' ', ';': ' ', ':': ' ', '~': ' ', '^': '^',
           '$': 'S', '\\': '/'}


PLAIN_ESCAPE = [('\\', BS + 'textbackslash{}'), ('{', BS + '{'), ('}', BS + '}'),
                ('$', BS + '$'), ('&', BS + '&'), ('#', BS + '#'),
                ('^', BS + 'textasciicircum{}'), ('_', BS + '_'),
                ('%', BS + '%'), ('~', BS + 'textasciitilde{}')]


def latex_safe(s):
    """Escape plain text for use as a LaTeX running-head mark.

    A running head is typeset in text mode, so a bare `^`, `_`, `&`, `#`, `$`
    or `%` is a syntax error -- `^` alone raises "Missing $ inserted" and then
    "Double superscript" when the title has two of them.
    """
    for a, b in PLAIN_ESCAPE:
        s = s.replace(a, b)
    return s


def strip_macros(s):
    """Replace known text macros and escapes with plain characters.

    Returns None when an unknown macro or math is met, so the caller can leave
    that heading alone rather than emit a broken running head.
    """
    out, i = [], 0
    while i < len(s):
        if s[i] != BS:
            out.append(s[i])
            i += 1
            continue
        j = i + 1
        m = re.match(r'[A-Za-z]+', s[j:])
        if not m:
            # A one-character escape such as \{ \} \^ \_ \& \ ,
            ch = s[j] if j < len(s) else ''
            if ch not in ESCAPES:
                return None
            out.append(ESCAPES[ch])
            i = j + 1
            if i < len(s) and s[i] == '{':     # \^{} and friends
                _, i = balanced_arg(s, i)
            continue
        name = m.group(0)
        k = j + len(name)
        if name in TEXT_MACROS and k < len(s) and s[k] == '{':
            arg, k2 = balanced_arg(s, k)
            inner = strip_macros(arg)
            if inner is None:
                return None
            out.append(inner)
            i = k2
            continue
        if name in SYMBOL_MACROS:
            if k < len(s) and s[k] == '{':
                _, k = balanced_arg(s, k)
            out.append(SYMBOL_MACROS[name])
            i = k
            continue
        return None
    return ''.join(out)


def plain_title(title):
    """Plain-text form of a section title, or None.

    pandoc emits `\\section{\\texorpdfstring{<printed>}{<plain>}}` whenever the
    heading contains markup, so the printed form is full of macros that cannot
    be truncated at an arbitrary character. Its second argument is already the
    plain text, which is exactly what a running head wants.
    """
    if not title.startswith(TEXORPDF):
        return None
    _, i = balanced_arg(title, len(TEXORPDF) - 1)
    if i >= len(title) or title[i] != '{':
        return None
    second, j = balanced_arg(title, i)
    if title[j:].strip():
        return None
    plain = strip_macros(second)
    if plain is None or '$' in plain or BS in plain:
        return None
    return plain


def head_mark(flat):
    """A safe, shorter running-head mark for an over-long section title.

    Cuts at a separator or word boundary, then escapes the result for text
    mode. Without the escape step a title containing `^` or `_` produces a
    compiling book with two silent LaTeX errors in the running head.
    """
    for sep in SEPARATORS:
        idx = flat.rfind(sep, 0, HEAD_LIMIT)
        if idx >= HEAD_MIN:
            cand = flat[:idx].rstrip()
            if cand:
                return latex_safe(cand)
    for i in range(min(HEAD_LIMIT, len(flat)), 0, -1):
        if i < len(flat) and flat[i] != ' ':
            continue
        cand = flat[:i].rstrip(' ,;:-')
        if cand:
            return latex_safe(cand)
    return None


SEC = BS + 'section{'
res5, i, n_head, n_skip = [], 0, 0, []
while True:
    j = src.find(SEC, i)
    if j == -1:
        res5.append(src[i:])
        break
    if j and src[j - 1] == '*':
        res5.append(src[i:j + len(SEC)])
        i = j + len(SEC)
        continue
    res5.append(src[i:j])
    k = j + len(SEC)
    title, m = balanced_arg(src, k - 1)
    base = plain_title(title)
    if base is None:
        base = title
    flat = ' '.join(base.split())
    if len(flat) <= HEAD_LIMIT:
        res5.append(src[j:m])
    else:
        cut = head_mark(flat)
        if cut is None:
            n_skip.append(flat[:70])
            res5.append(src[j:m])
        else:
            n_head += 1
            res5.append(BS + 'section[' + title + '][' + cut + ']{' + title + '}')
    i = m
src = ''.join(res5)

# ---- pass 6: give wide longtables wrapping p-columns ----------------------
# pandoc emits `@{}llll@{}` for a pipe table. An `l` column never wraps, so a
# table whose cells are sentences is simply wider than the measure: LaTeX
# reports "Overfull \hbox ... in alignment" and the table's right edge pushes
# into the gutter. Measured on the 809-page build, that ink came within
# 0.513 in of the spine where the layout promises 0.9375 in.
LT_RE = re.compile(r'\\begin\{longtable\}\[\]\{@\{\}([l|]+)@\{\}\}')
MINIPAGE_RE = re.compile(
    r'\\begin\{minipage\}\[[btc]\]\{[^}]*\}(?:\\raggedright)?\s*(.*?)\s*\\end\{minipage\}',
    re.S)
NOISE_RE = re.compile(r'\\(?:toprule|midrule|bottomrule)\b(?:\\noalign\{\})?'
                      r'|\\end(?:head|lastfoot|firsthead)\b|\\def\\LTcaptype\{[^}]*\}')
LATEX_WORD_RE = re.compile(r'\\[A-Za-z]+\s*|\\.')


def plain_len(text):
    t = MINIPAGE_RE.sub(r'\1', text)
    t = re.sub(r'\\index\{[^{}]*\}', '', t)
    t = LATEX_WORD_RE.sub('', t)
    t = re.sub(r'[{}$]', '', t)
    return len(' '.join(t.split()))


def split_cells(row):
    cells, depth, cur = [], 0, []
    i = 0
    while i < len(row):
        c = row[i]
        if c == BS:
            cur.append(row[i:i + 2])
            i += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        if c == '&' and depth == 0:
            cells.append(''.join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    cells.append(''.join(cur))
    return cells


n_tbl = 0
chunks6, pos6 = [], 0
for m in LT_RE.finditer(src):
    spec = m.group(1)
    ncols = len([c for c in spec if c == 'l'])
    if ncols < 2 or ncols > 12:
        continue
    end = src.find(BS + 'end{longtable}', m.end())
    if end == -1:
        continue
    body = src[m.end():end]
    body = NOISE_RE.sub('', body)
    rows = [r for r in re.split(r'\\\\', body) if r.strip()]
    widths = [3] * ncols
    for row in rows:
        for idx, cell in enumerate(split_cells(row)[:ncols]):
            widths[idx] = max(widths[idx], plain_len(cell))
    if max(widths) < 18:
        continue                      # a genuinely narrow table; leave it alone
    total = float(sum(widths))
    fracs = [w / total for w in widths]
    # No column below 8% of the measure, else renormalise the rest.
    floor = 0.08
    if any(f < floor for f in fracs):
        locked = [i for i, f in enumerate(fracs) if f < floor]
        rest = total - sum(widths[i] for i in locked)
        for i in locked:
            fracs[i] = floor
        scale = (1.0 - floor * len(locked)) / (rest / total)
        for i in range(ncols):
            if i not in locked:
                fracs[i] = (widths[i] / rest) * (1.0 - floor * len(locked))
    colspec = ''.join(
        '>{\\raggedright\\arraybackslash}p{\\dimexpr %.4f\\linewidth-2\\tabcolsep\\relax}'
        % f for f in fracs)
    new_body = MINIPAGE_RE.sub(r'\1', body)
    chunks6.append(src[pos6:m.start()])
    chunks6.append(BS + 'begin{longtable}[]' + '{@{}' + colspec + '@{}}')
    chunks6.append(new_body)
    chunks6.append(BS + 'end{longtable}')
    pos6 = end + len(BS + 'end{longtable}')
    n_tbl += 1
chunks6.append(src[pos6:])
src = ''.join(chunks6) if n_tbl else src

# ---- pass 7: unwrap pandoc's full-width table cells -----------------------
# For grid tables pandoc wraps each cell in
#     \begin{minipage}[b]{\linewidth}\raggedright ... \end{minipage}
# Inside a longtable, \linewidth is the *table* width, not the column width,
# so every such cell demands the whole measure and the table overflows by tens
# of points -- visible as ink reaching into the gutter. A p-column already
# wraps text, so the wrapper is redundant: drop it. (\columnwidth would also
# work, but unwrapping cannot be wrong about which length is in force.)
n_unwrap = len(MINIPAGE_RE.findall(src))
if n_unwrap:
    src = MINIPAGE_RE.sub(lambda m: m.group(1), src)

Path('body.tex').write_text(src, encoding='utf-8')
print(f'texttt patched: {n_tt}, arrow lines: {n_arrow}, longtables: {n_lt}, '
      f'tikz: {n_tikz}, shortened running heads: {n_head}, '
      f'wrapping tables: {n_tbl}, unwrapped table cells: {n_unwrap}')
if n_skip:
    print(f'WARNING {len(n_skip)} over-long section titles could not be shortened '
          f'and may wrap a running head:')
    for s in n_skip:
        print('   ' + s)
