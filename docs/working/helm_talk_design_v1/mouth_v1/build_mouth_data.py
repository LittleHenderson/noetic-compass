"""Builder tool (NOT in the sealed package): the MOUTH TRAIN package's data files (A-TALK-4 W4, W6; A-TALK-5 F2).

    python -X utf8 -B build_mouth_data.py

Writes package_source/data/:
  mouth_train.jsonl, mouth_dev.jsonl   the keyed lessons (mouth_llm assemble), with source / writer labels
  mouth_exam.jsonl                     held-out exam inputs: >= 800 fresh readings + the held-out person lines (never in
                                       the lessons, A-TALK-5 F2); no target -- the mouth writes, the guard checks
  FUNCTION_WORDS.json                  the lock's everyday words: words of the LLM-written TRAIN targets that are NOT in
                                       their own row's input, seen at least twice, minus every subject-pool name, number
                                       word and month (FACT_WORDS) and the generator's subject nouns
  FACT_WORDS.json                      the names, number words and months of the subject pools (the guard's fact list)
  train_cube.jsonl, cas_keep.jsonl, dev_sdg.jsonl, dev_llm.jsonl, cas_val.jsonl   copied byte for byte from the sealed
                                       CUBE TRAIN package (the ear keeps its skill and is re-read after training)
  DATA_MANIFEST_MOUTH.json             counts and sha256 of every file
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mouth_lessons as ML  # noqa: E402
import mouth_llm as MM  # noqa: E402

DATA = HERE / "package_source" / "data"
CUBE_PKG = Path(r"C:\Users\wakil\Documents\Codex\2026-10-22\cube_train\HELM_CUBE_TRAIN_20261022")
CUBE_FILES = ("train_cube.jsonl", "cas_keep.jsonl", "dev_sdg.jsonl", "dev_llm.jsonl", "cas_val.jsonl")
EXAM_FACTS = 800                   # 700 + the person lines fell short of 1,000 once Google had no quota (A-TALK-6 G2)
EXAM_FIRST_INDEX = 40_000
WORD_RX = re.compile(r"[a-z]+")
MIN_SEEN = 2


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_jsonl(p: Path):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_jsonl(p: Path, rows) -> None:
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def subject_nouns() -> set:
    out = set()
    for t in ML.W.TEMPLATE_TEXT.values():
        for v in t.values():
            for s in (v if isinstance(v, tuple) else (v,)):
                out.update(w for w in WORD_RX.findall(s.lower()) if len(w) >= 4)
    return out


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    train = read_jsonl(MM.HERE and Path(MM.OUT) / "rows_mouth_train.jsonl")
    dev = read_jsonl(Path(MM.OUT) / "rows_mouth_dev.jsonl")
    fact_words = sorted(ML.NAMES | ML.NUMBERS | ML.MONTHS)
    nouns = subject_nouns()
    seen = Counter()
    for r in train:
        if r["source"] != "LLM_WRITTEN":
            continue
        have = set(WORD_RX.findall(r["input_text"].lower()))
        seen.update(w for w in set(WORD_RX.findall(r["target"].lower())) if w not in have)
    function = sorted(w for w, c in seen.items() if c >= MIN_SEEN and w not in set(fact_words) and w not in nouns)
    # held-out exam inputs (A-TALK-5 F2): fresh readings + the held-out person lines
    exam = [dict(x, split="EXAM") for x in ML.fact_inputs(EXAM_FACTS, first_index=EXAM_FIRST_INDEX)]
    lesson_lines = {(r.get("person_line") or "").lower() for r in train + dev}
    k = 0
    for fam in MM.FAMILIES:
        doc = MM._load(f"persons_exam_{fam}.json", {"lines": []})
        for ln in doc["lines"]:
            t = ln["text"]
            if t.lower() in lesson_lines or not MM._person_ok(ln["situation"], t):
                continue
            exam.append(dict(ML.line_input(ln["situation"], t, f"exam-person:{fam}:{k}"), split="EXAM", person_family=fam))
            k += 1
    write_jsonl(DATA / "mouth_train.jsonl", train)
    write_jsonl(DATA / "mouth_dev.jsonl", dev)
    write_jsonl(DATA / "mouth_exam.jsonl", exam)
    (DATA / "FUNCTION_WORDS.json").write_text(json.dumps(function, indent=0) + "\n", encoding="utf-8", newline="\n")
    (DATA / "FACT_WORDS.json").write_text(json.dumps(fact_words, indent=0) + "\n", encoding="utf-8", newline="\n")
    for name in CUBE_FILES:
        shutil.copyfile(CUBE_PKG / "data" / name, DATA / name)
    files = sorted(p.name for p in DATA.iterdir() if p.is_file() and p.name != "DATA_MANIFEST_MOUTH.json")
    man = {"schema": "mouth-train.data-manifest/1",
           "counts": {"mouth_train": len(train), "mouth_dev": len(dev), "mouth_exam": len(exam),
                      "mouth_exam_facts": EXAM_FACTS, "mouth_exam_person_lines": k, "function_words": len(function),
                      "fact_words": len(fact_words),
                      "train_by_source": dict(Counter(r["source"] for r in train)),
                      "train_by_situation": dict(Counter(r["situation"] for r in train)),
                      "exam_by_situation": dict(Counter(x["situation"] for x in exam))},
           "sha256": {n: sha(DATA / n) for n in files},
           "cube_train_package": str(CUBE_PKG), "function_rule": "LLM-written TRAIN target words not in their own row's "
           "input, seen >= 2 times, minus FACT_WORDS and the generator's subject nouns"}
    (DATA / "DATA_MANIFEST_MOUTH.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(man["counts"], indent=1))


if __name__ == "__main__":
    main()
