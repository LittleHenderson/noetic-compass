#!/usr/bin/env bash
# X-REAL source fetch, as run on 2026-10-19 (record; re-running is NOT needed: the files are pinned in
# SOURCES_PINNED.json). Only the exact URLs of SOURCES.md. Downloads are untrusted data: never executed.
# The User-Agent is a neutral constant and carries no personal data (D-XR-12: the builder's very first request,
# robots.txt, was sent by an earlier inline curl helper whose User-Agent held the owner's e-mail address; every
# later request used this neutral header). A kit test checks this file holds no e-mail address.
set -euo pipefail
UA="HELM-XREAL-builder/1 (one-time research fetch)"
OUT="${1:?usage: fetch_sources.sh <empty sources dir>}"
get() { curl -sS -L --fail --max-time 280 -A "$UA" -o "$2" "$1"; }
mkdir -p "$OUT"/A0_pg_robots "$OUT"/A1_pg_catalog "$OUT"/A1_pg_ebooks "$OUT"/A2_wikibooks "$OUT"/B1_tatoeba
get https://www.gutenberg.org/robots.txt "$OUT"/A0_pg_robots/robots.txt
get https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv "$OUT"/A1_pg_catalog/pg_catalog.csv
# one request per eBook of the frame (ids from the catalog filter in xreal/frames.py pg_licensed_ids), 1 s apart:
#   get https://www.gutenberg.org/cache/epub/<id>/pg<id>.txt "$OUT"/A1_pg_ebooks/pg<id>.txt
get https://dumps.wikimedia.org/enwikibooks/20261001/enwikibooks-20261001-sha1sums.txt \
    "$OUT"/A2_wikibooks/enwikibooks-20261001-sha1sums.txt
get https://dumps.wikimedia.org/enwikibooks/20261001/enwikibooks-20261001-pages-articles.xml.bz2 \
    "$OUT"/A2_wikibooks/enwikibooks-20261001-pages-articles.xml.bz2
get https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences.tsv.bz2 "$OUT"/B1_tatoeba/eng_sentences.tsv.bz2
git -c core.autocrlf=false clone --depth 1 --filter=blob:none --no-checkout \
    https://github.com/google-research-datasets/Taskmaster "$OUT"/B2_taskmaster
# then a sparse checkout of the 13 files listed in SOURCES_PINNED.json at commit d92cb6af3005f1dc09c39e75e7daf4a04905e00b
