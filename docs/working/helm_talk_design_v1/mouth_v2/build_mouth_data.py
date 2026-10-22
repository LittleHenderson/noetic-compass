"""Builder tool (NOT in the sealed package): MOUTH TRAIN v2's data files (A-TALK-7, A-TALK-8).

    python -X utf8 -B build_mouth_data.py

Writes package_source/data/:
  mouth_train.jsonl, mouth_dev.jsonl   the keyed lessons (corpus_v2 assemble), each with its style part; a lesson the
                                       lock cannot write is dropped (A-TALK-7 H1 F1), after the 95 % gate below
  mouth_exam.jsonl                     held-out exam inputs: 800 fresh styled readings (worlds from index 70000), the v2
                                       held-out person lines (every style and level) and v1's held-out person lines;
                                       never in the lessons
  ear_m.jsonl                          the ear's new lessons: the mouth's own TRAIN fact sentences read back in the ear's
                                       [B] form (H2), and every TRAIN person line with the answer NONE (A-TALK-8 I1)
  FUNCTION_WORDS.json                  the lock's everyday words (mouth_lessons.function_words: seen in >= 2 checked
                                       lessons, minus fact words and WORLD_NOUNS)
  FACT_WORDS.json, WORLD_NOUNS.json    the guard's fact list; the generator's own nouns
  train_cube.jsonl, cas_keep.jsonl, dev_sdg.jsonl, dev_llm.jsonl, cas_val.jsonl   copied byte for byte from the sealed
                                       CUBE TRAIN package
  DATA_MANIFEST_MOUTH.json             counts, the writable shares and sha256 of every file
Refuses (SystemExit) when any situation's lessons are less than 95 % writable under the lock (A-TALK-7 H1 F1).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "package_source"))
import mouth_lessons as ML  # noqa: E402
import corpus_v2 as C  # noqa: E402
from mouth_task import ear_lessons, lock, vocab_m  # noqa: E402

DATA = HERE / "package_source" / "data"
CUBE_PKG = Path(r"C:\Users\wakil\Documents\Codex\2026-10-22\cube_train\HELM_CUBE_TRAIN_20261022")
CUBE_FILES = ("train_cube.jsonl", "cas_keep.jsonl", "dev_sdg.jsonl", "dev_llm.jsonl", "cas_val.jsonl")
EXAM_FACTS = 800
EXAM_FIRST_INDEX = 70_000
WRITABLE_MIN = 0.95


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_jsonl(p: Path):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_jsonl(p: Path, rows) -> None:
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def writable(vm, function, r) -> bool:
    a = lock.MouthAutomaton(vm, lock.allowed_words(function, r["input_text"]))
    for i in vm.encode_mouth_target(r["target"])[:-1]:
        tok = vm.tokens[i]
        if tok not in a.allowed():
            return False
        a.step(tok)
    return "[EOS]" in a.allowed()


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    vm = vocab_m.load(str(DATA / "vocab.json"))
    train = read_jsonl(Path(C.OUT) / "rows_mouth_train.jsonl")
    dev = read_jsonl(Path(C.OUT) / "rows_mouth_dev.jsonl")
    vocab = sorted({w for ws in C.vocab_lists().values() for w in ws})
    function = ML.function_words(train, vocab=vocab)                  # A-TALK-9 J1
    fact_words = sorted(ML.NAMES | ML.NUMBERS | ML.MONTHS)
    # the 95 % gate (before dropping), per situation, on every lesson row
    shares, keep_train, keep_dev = {}, [], []
    for name, rows, keep in (("train", train, keep_train), ("dev", dev, keep_dev)):
        for r in rows:
            ok = writable(vm, function, r)
            s = shares.setdefault(r["situation"], [0, 0])
            s[0] += ok
            s[1] += 1
            if ok:
                keep.append(r)
    share = {k: round(v[0] / v[1], 4) for k, v in shares.items()}
    print("writable share by situation:", json.dumps(share), flush=True)
    low = {k: v for k, v in share.items() if v < WRITABLE_MIN}
    if low:
        raise SystemExit("refused: lessons less than 95 %% writable under the lock in %s (A-TALK-7 H1 F1)" % low)
    # exam: fresh styled readings + held-out person lines (v2 grid and v1), never in the lessons
    exam = [dict(x, split="EXAM") for x in C.new_fact_inputs(EXAM_FACTS, EXAM_FIRST_INDEX, "e")]
    lesson_lines = {(r.get("person_line") or "").lower() for r in train + dev}
    k = 0
    for x in C.person_inputs("persons_exam_v2.json"):
        if x["person_line"].lower() not in lesson_lines:
            exam.append(dict(x, split="EXAM", input_key=x["input_key"].replace("v2:", "exam-v2:")))
            k += 1
    for fam in ("anthropic", "openai", "deepseek", "google"):
        doc = json.load(open(os.path.join(C.V1, f"persons_exam_{fam}.json"), encoding="utf-8")) \
            if os.path.exists(os.path.join(C.V1, f"persons_exam_{fam}.json")) else {"lines": []}
        for j, ln in enumerate(doc["lines"]):
            t = ln["text"]
            if t.lower() in lesson_lines or not C.MM._person_ok(ln["situation"], t):
                continue
            x = ML.line_input(ln["situation"], t, f"exam-person:{fam}:{j}")
            exam.append(dict(ML.styled(x, "warm" if x["tone"][1] == "|f" else "plain", "grade10"), split="EXAM"))
            k += 1
    # the ear's new lessons (TRAIN only): the mouth's fact sentences, and the person lines as NONE
    ear, seen = [], set()
    for r in keep_train:
        if r["source"] != "LLM_WRITTEN":
            continue
        if r["situation"] in ML.FACT_SITUATIONS:
            row = ear_lessons.ear_row(r["target"], r["reading"])
            if row:
                ear.append(row)
        elif r.get("person_line") and r["person_line"].lower() not in seen:
            seen.add(r["person_line"].lower())
            ear.append({"direction": "B", "family": "corpus", "kind": "SMALL", "stratum": "EAR_M", "text": r["person_line"],
                        "truth": "NONE", "target": ["NONE"]})
    write_jsonl(DATA / "mouth_train.jsonl", keep_train)
    write_jsonl(DATA / "mouth_dev.jsonl", keep_dev)
    write_jsonl(DATA / "mouth_exam.jsonl", exam)
    write_jsonl(DATA / "ear_m.jsonl", ear)
    for name, obj in (("FUNCTION_WORDS.json", function), ("FACT_WORDS.json", fact_words),
                      ("WORLD_NOUNS.json", list(ML.WORLD_NOUNS))):
        (DATA / name).write_text(json.dumps(obj, indent=0) + "\n", encoding="utf-8", newline="\n")
    for name in CUBE_FILES:
        shutil.copyfile(CUBE_PKG / "data" / name, DATA / name)
    files = sorted(p.name for p in DATA.iterdir() if p.is_file() and p.name != "DATA_MANIFEST_MOUTH.json")
    man = {"schema": "mouth-train.data-manifest/2",
           "counts": {"mouth_train": len(keep_train), "mouth_dev": len(keep_dev), "dropped_not_writable":
                      len(train) + len(dev) - len(keep_train) - len(keep_dev), "mouth_exam": len(exam),
                      "mouth_exam_facts": EXAM_FACTS, "mouth_exam_person_lines": k, "ear_m": len(ear),
                      "ear_m_facts": sum(1 for e in ear if e["truth"] != "NONE"),
                      "ear_m_none": sum(1 for e in ear if e["truth"] == "NONE"), "function_words": len(function),
                      "train_by_source": dict(Counter(r["source"] for r in keep_train)),
                      "train_by_situation": dict(Counter(r["situation"] for r in keep_train)),
                      "train_by_style": dict(Counter(r["style"][0] for r in keep_train)),
                      "exam_by_situation": dict(Counter(x["situation"] for x in exam)),
                      "exam_by_style": dict(Counter(x["style"][0] for x in exam))},
           "writable_share": share, "sha256": {n: sha(DATA / n) for n in files}, "cube_train_package": str(CUBE_PKG)}
    (DATA / "DATA_MANIFEST_MOUTH.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n", encoding="utf-8",
                                                  newline="\n")
    print(json.dumps(man["counts"], indent=1))


if __name__ == "__main__":
    main()
