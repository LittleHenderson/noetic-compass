# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
src = Path('body.tex').read_text(encoding='utf-8')
i = src.find('Introduce new 5.1')
print('ctx:', repr(src[max(0, i - 80):i + 120]))
if i != -1 and src[i - 8:i] != 'sloppy ' + '{'[0:1]:
    src = src[:i - 8] + src[i - 8:].replace('\\textbf{Introduce new 5.1}',
                                            '\\sloppy \\textbf{Introduce new 5.1}', 1)
    Path('body.tex').write_text(src, encoding='utf-8')
    print('patched')
