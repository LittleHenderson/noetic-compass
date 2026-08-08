#!/bin/sh
# Build all five Project Coherence monographs (run from docs/whitepapers/monograph).
# Three pdflatex passes each for TOC and cross-references.
set -u
for d in noetic_topos2 tks_v8 cas_core8 cas_pcba8 cas_ohm1; do
  ( cd "$d" && mkdir -p build && \
    pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex >/dev/null 2>&1; \
    pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex >/dev/null 2>&1; \
    pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/pass3.log 2>&1; \
    if [ -f build/main.pdf ]; then echo "OK   $d"; else echo "FAIL $d"; grep -A3 '^!' build/pass3.log | head -12; fi )
done
