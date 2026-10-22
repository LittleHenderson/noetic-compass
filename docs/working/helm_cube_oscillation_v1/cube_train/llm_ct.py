"""llm_ct.py -- the CUBE TRAIN `LLM_WRITTEN` stratum (PREREGISTRATION_CUBE_TRAIN §4.2, A-CUBE-TRAIN-1). Exam side.

WHAT THIS IS, IN PLAIN WORDS
----------------------------
Three AI model families (Anthropic's Claude, OpenAI's Codex, Google's Gemini; their command-line tools, on subscriptions
the owner already pays for: 0 USD) each write teaching lines for their own made-up worlds (TRAIN: 20 worlds = 400
lines; DEV: 5 worlds = 100 lines). Each line is checked by rule (anchor words, its value, no other value, no question,
no digits, short, not copied). Then the OTHER two families each say what value the line states; a line becomes a
training row only when both match the generator's truth AND the copy rule holds (rows_ct.truth_reading). The owner
writes nothing.

Stages:  python llm_ct.py write | key | assemble      (outputs in cube_train/llm/)
CLAIM STATUS: ENGINEERED-NOT-VALIDATED.
"""
from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import rows_ct as R  # noqa: E402  (also puts the repository root and TEACH-1's package on the path)
import helm_cube_osc as hco  # noqa: E402
from teach1 import turns_t1 as T  # noqa: E402
from teach1 import worlds_t1 as W  # noqa: E402

OUT = os.path.join(HERE, "llm")
FAMILIES = ("anthropic", "openai", "google", "deepseek")   # deepseek: A-CUBE-TRAIN-4
WORLDS = {"TRAIN": 20, "DEV": 5}
BANDS = {"TRAIN": R.TRAIN_BAND, "DEV": R.DEV_BAND}
FIRST_INDEX = 10_000                     # the SDG rows use the low world indices of the same bands
SLOTS = {"FIX": 2, "FACT": 11, "TRAP": 3, "UNKNOWN": 2, "SMALL": 2}       # = 20 per world
MAX_WORDS = 60
GEMINI_MODEL = "gemini-3-flash-preview"   # TEACH-1's Gemini writer model
BRIEF = open(os.path.join(HERE, "WRITER_BRIEF_CT.md"), encoding="utf-8").read()
KEY_BRIEF = open(os.path.join(HERE, "KEY_BRIEF_CT.md"), encoding="utf-8").read()
SMALL_CANON = ("Hang on, I lost my place for a moment.", "Thanks, that is useful.")
NAMES = {w.lower() for w in W.PERSONS + W.PLACES}


def _words(text: str) -> set:
    return {w.lower().strip("'-") for w in hco._WORD_RX.findall(text or "")}


# ----------------------------------------------------------------------------------------------- packets
def make_packets() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    packs: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for k, fam in enumerate(FAMILIES):
        packs[fam] = {}
        for split, n in WORLDS.items():
            worlds = []
            for j in range(n):
                index = FIRST_INDEX + 100 * k + j
                worlds.append({"band": BANDS[split], "index": index,
                               "slots": world_slots(split, fam, BANDS[split], index)})
            packs[fam][split] = worlds
    return packs


def world_slots(split: str, fam: str, band: int, index: int) -> List[Dict[str, Any]]:
    world = W.build_world(band, index, W.TEMPLATES[index % 2])
    rng = random.Random(f"llm-slots:{band}:{index}")
    fixes = [f for f in world["facts"] if f.get("fix")]
    known = [f for f in world["facts"] if not f["unknown"] and not f.get("fix")]
    unknown = [f for f in world["facts"] if f["unknown"]]
    rng.shuffle(known)
    slots: List[Dict[str, Any]] = []

    def base(kind: str, f: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return {"id": f"{split}-{fam}-{index}-{len(slots):02d}", "kind": kind, "fact": f, "world_index": index,
                "band": band, "split": split, "family": fam, "units": world["names"]["units"]}

    for f in fixes:
        s = base("FIX", f)
        s.update(canonical=f["fix"]["correction"], value=f["value"], not_value=f["fix"]["first_value"],
                 anchor_words=list(f["anchor_words"]))
        slots.append(s)
    for f in known[:SLOTS["FACT"]]:
        s = base("FACT", f)
        s.update(canonical=f["statement"], value=f["value"], anchor_words=list(f["anchor_words"]))
        slots.append(s)
    for f in known[SLOTS["FACT"]:SLOTS["FACT"] + SLOTS["TRAP"]]:
        s = base("TRAP", f)
        options = ["not", "month", "place"] + (["number"] if f["kind"] == "count" else [])
        kind = rng.choice(options)
        if kind == "number":
            decoy = rng.choice([n for n in W.NUMBERS if n != f["value"]])
        elif kind == "month":
            decoy = rng.choice([m for m in W.MONTHS if m != f.get("month")]).capitalize()
        elif kind == "place":
            decoy = rng.choice([u for u in world["names"]["units"] if u != f["unit"]])
        else:
            decoy = "not"
        s.update(canonical=f["statement"], value=f["value"], anchor_words=list(f["anchor_words"]), decoy=decoy)
        slots.append(s)
    for f in rng.sample(unknown, SLOTS["UNKNOWN"]):
        s = base("UNKNOWN", f)
        s.update(canonical=f["unknown_statement"], anchor_words=list(f["anchor_words"]))
        slots.append(s)
    for i in range(SLOTS["SMALL"]):
        s = base("SMALL", None)
        s.update(canonical=SMALL_CANON[i])
        slots.append(s)
    return slots


def writer_view(slot: Dict[str, Any]) -> Dict[str, Any]:
    return {k: slot[k] for k in ("id", "kind", "canonical", "value", "anchor_words", "not_value", "decoy") if k in slot}


# ----------------------------------------------------------------------------------------------- the line checker
def check_line(slot: Dict[str, Any], text: str) -> Tuple[bool, str]:
    if not isinstance(text, str) or not text.strip():
        return False, "empty"
    t = text.strip()
    if "?" in t:
        return False, "a question"
    if re.search(r"\d", t):
        return False, "digits"
    if len(t.split()) > MAX_WORDS:
        return False, "too long"
    if t == slot["canonical"].strip():
        return False, "copied word for word"
    for name, rx in T.FORBIDDEN.items():
        if re.search(rx, t, re.I):
            return False, f"forbidden phrase ({name})"
    words = _words(t)
    kind = slot["kind"]
    if kind != "SMALL" and not {a.lower() for a in slot["anchor_words"]} <= words:
        return False, "anchor words missing"
    allowed = {slot.get("value", ""), slot.get("not_value", "") or "", str(slot.get("decoy", "")).lower()}
    allowed = {a.lower() for a in allowed if a}
    if kind in ("FACT", "TRAP", "FIX") and slot["value"].lower() not in words:
        return False, "value missing"
    if kind == "FIX" and slot["not_value"].lower() not in words:
        return False, "old value missing"
    if kind == "TRAP" and str(slot["decoy"]).lower() not in words:
        return False, "decoy missing"
    numbers = words & set(W.NUMBERS)
    if kind in ("UNKNOWN", "SMALL") and numbers:
        return False, "a number where none belongs"
    if numbers - allowed:
        return False, "another number"
    fact = slot.get("fact") or {}
    own = {(fact.get("unit") or "").lower()} | {a.lower() for a in slot.get("anchor_words", [])}
    if (words & NAMES) - own - allowed:
        return False, "another name"
    if kind == "SMALL" and words & NAMES:
        return False, "a name in small talk"
    return True, ""


def example_line(slot: Dict[str, Any]) -> str:
    """A rule-made acceptable line (tests only; never a training row)."""
    kind = slot["kind"]
    anchors = " ".join(slot.get("anchor_words", []))
    if kind == "SMALL":
        return "Give me one moment to look at my notes."
    if kind == "UNKNOWN":
        return f"About {anchors}, it has slipped my mind."
    if kind == "FIX":
        return f"Let me fix that: {anchors} was {slot['value']}, not {slot['not_value']}."
    tail = f" Also {slot['decoy']} came up." if kind == "TRAP" else ""
    return f"Noting it down: {anchors} was {slot['value']}.{tail}"


# ----------------------------------------------------------------------------------------------- assembly
def _truth(slot: Dict[str, Any]) -> Tuple[str, str]:
    if slot["kind"] in ("UNKNOWN", "SMALL"):
        return "NONE", "-"
    return slot["value"].lower(), (slot.get("not_value") or "-").lower()


def assemble_one(slot: Dict[str, Any], line: str, keys: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    ok, _why = check_line(slot, line)
    if not ok or len(keys) < 2:                  # A-CUBE-TRAIN-4: at least two keys, every one right
        return None
    want = _truth(slot)
    for k in keys:
        got = (str(k.get("value", "")).strip().lower() or "none", str(k.get("replaces", "-")).strip().lower() or "-")
        got = ("NONE" if got[0] == "none" else got[0], got[1])
        if got != want:
            return None
    row = {"kind": slot["kind"], "input": line.strip(), "family": slot["family"], "split": slot["split"],
           "world_seed": slot["band"], "world_index": slot["world_index"], "slot_id": slot["id"],
           "fact_id": (slot.get("fact") or {}).get("id")}
    if want[0] == "NONE":
        row["target"] = "NONE"
        return row
    r = R.truth_reading(slot["fact"], line, want[0], None if want[1] == "-" else want[1])
    if r is None:
        return None
    row["target"] = hco.target_string(r)
    row["truth_value"] = want[0]
    return row


def parse_reply(text: str) -> Optional[List[Dict[str, Any]]]:
    i, j = (text or "").find("["), (text or "").rfind("]")
    if i < 0 or j <= i:
        return None
    try:
        out = json.loads(text[i:j + 1])
    except ValueError:
        return None
    return out if isinstance(out, list) else None


# ----------------------------------------------------------------------------------------------- the model tools
CODEX_MODEL = "gpt-5.6-terra"            # A-CUBE-TRAIN-2: TEACH-1's Codex writer model
FILE_FAMILIES = ("anthropic",)           # A-CUBE-TRAIN-2: Claude helper agents through prompt / reply files
BATCH_WORLDS = 5


def run_cli(family: str, prompt: str, tag: str, timeout: int = 1800) -> Tuple[str, Dict[str, Any]]:
    if family == "deepseek":
        return run_deepseek(prompt, tag)
    """One call of a family. Command-line families run in an empty folder with the prompt on stdin. The Anthropic
    family is file mode: the prompt is saved as llm/prompts/<tag>.txt and the reply read from llm/replies/<tag>.txt
    once a Claude helper agent has written it (empty until then)."""
    os.makedirs(os.path.join(OUT, "prompts"), exist_ok=True)
    with open(os.path.join(OUT, "prompts", f"{tag}.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(prompt)
    if family in FILE_FAMILIES:
        reply = os.path.join(OUT, "replies", f"{tag}.txt")
        if os.path.isfile(reply):
            return open(reply, encoding="utf-8").read(), {"family": family, "tag": tag, "mode": "file", "status": "replied"}
        return "", {"family": family, "tag": tag, "mode": "file", "status": "pending"}
    import shutil
    work = tempfile.mkdtemp(prefix="cube_train_llm_")
    t0 = time.time()
    if family == "openai":
        last = os.path.join(work, "last.txt")
        cmd = [shutil.which("codex") or "codex", "exec", "--skip-git-repo-check", "-s", "read-only", "-m", CODEX_MODEL,
               "-c", "model_reasoning_effort=medium", "-o", last, "-"]
    else:
        cmd = [shutil.which("gemini") or "gemini", "-m", GEMINI_MODEL, "-p", "Follow the instructions in the input exactly."]
    try:
        res = subprocess.run(cmd, input=prompt.encode("utf-8"), capture_output=True, cwd=work, timeout=timeout)
        rc = res.returncode
        if family == "openai":
            out = open(last, encoding="utf-8").read() if os.path.isfile(last) else ""
        else:
            out = res.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        out, rc = "", "timeout"
    os.makedirs(os.path.join(OUT, "replies"), exist_ok=True)
    with open(os.path.join(OUT, "replies", f"{tag}.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    model = CODEX_MODEL if family == "openai" else GEMINI_MODEL
    return out, {"family": family, "tag": tag, "model": model, "returncode": rc, "seconds": round(time.time() - t0, 1)}


DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


def _deepseek_key() -> Optional[str]:
    """The key from the environment or the owner's local key file; never printed or recorded."""
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ["DEEPSEEK_API_KEY"]
    path = os.path.expanduser("~/.cas_llm_keys.env")
    if not os.path.isfile(path):
        return None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if line.startswith("DEEPSEEK_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def run_deepseek(prompt: str, tag: str, timeout: int = 600) -> Tuple[str, Dict[str, Any]]:
    """One DeepSeek chat call through Python's standard library (A-CUBE-TRAIN-4); usage tokens recorded."""
    import urllib.request
    os.makedirs(os.path.join(OUT, "prompts"), exist_ok=True)
    with open(os.path.join(OUT, "prompts", f"{tag}.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(prompt)
    t0 = time.time()
    body = json.dumps({"model": DEEPSEEK_MODEL, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.7, "max_tokens": 8192}).encode("utf-8")
    req = urllib.request.Request(DEEPSEEK_URL, data=body, headers={"Authorization": "Bearer " + (_deepseek_key() or ""),
                                                                   "Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=timeout))
        out, usage, served, rc = r["choices"][0]["message"]["content"], r.get("usage", {}), r.get("model"), 0
    except Exception as exc:
        out, usage, served, rc = "", {}, None, type(exc).__name__
    os.makedirs(os.path.join(OUT, "replies"), exist_ok=True)
    with open(os.path.join(OUT, "replies", f"{tag}.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    return out, {"family": "deepseek", "tag": tag, "model": served or DEEPSEEK_MODEL, "returncode": rc,
                 "seconds": round(time.time() - t0, 1), "prompt_tokens": usage.get("prompt_tokens", 0),
                 "completion_tokens": usage.get("completion_tokens", 0)}


def _save(name: str, obj: Any) -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")


def _load(name: str) -> Any:
    with open(os.path.join(OUT, name), encoding="utf-8") as fh:
        return json.load(fh)


def _take(text: str, into: Dict[str, str]) -> None:
    for item in parse_reply(text) or []:
        if isinstance(item, dict) and item.get("id") and isinstance(item.get("text"), str):
            into[item["id"]] = item["text"]


def stage_write(families: Tuple[str, ...] = FAMILIES) -> None:
    """Writes (and one rewrite round). Re-runnable: a file-mode family is completed by re-running after its replies."""
    packs = make_packets()
    for fam in families:
        written: Dict[str, str] = {}
        calls = []
        for split in ("TRAIN", "DEV"):
            worlds = packs[fam][split]
            for b in range(0, len(worlds), BATCH_WORLDS):
                batch = worlds[b:b + BATCH_WORLDS]
                slots = [s for w in batch for s in w["slots"]]
                tag = f"write-{fam}-{split}-{b // BATCH_WORLDS}"
                text, meta = run_cli(fam, BRIEF + "\n\nSLOTS:\n" + json.dumps([writer_view(s) for s in slots],
                                                                           ensure_ascii=False), tag)
                calls.append(meta)
                _take(text, written)
                if meta.get("status") == "pending":
                    continue
                redo = []
                for s in slots:
                    ok, why = check_line(s, written.get(s["id"], ""))
                    if not ok:
                        redo.append(dict(writer_view(s), refused_because=why, your_line=written.get(s["id"], "")))
                if redo:
                    text, meta = run_cli(fam, BRIEF + "\n\nREWRITE these slots (each was refused for the reason given):\n"
                                         + json.dumps(redo, ensure_ascii=False), "re" + tag)
                    calls.append(meta)
                    _take(text, written)
                print(fam, tag, "lines", sum(1 for s in slots if s["id"] in written), "ok",
                      sum(1 for s in slots if check_line(s, written.get(s["id"], ""))[0]), flush=True)
        _save(f"written_{fam}.json", {"family": fam, "lines": written, "calls": calls})


def stage_key(keyers: Tuple[str, ...] = FAMILIES, writers: Optional[Tuple[str, ...]] = None,
              missing_from: Optional[str] = None, tag_prefix: str = "key") -> None:
    """Key the lines of `writers` (default: every other family). `missing_from`: only lines that family has not keyed
    (A-CUBE-TRAIN-4's gap). Keys merge into an existing keys file; a line already keyed by this keyer is skipped."""
    packs = make_packets()
    slots = {s["id"]: s for fam in FAMILIES for split in ("TRAIN", "DEV") for w in packs[fam][split] for s in w["slots"]}
    written = {fam: _load(f"written_{fam}.json")["lines"] for fam in FAMILIES
               if os.path.isfile(os.path.join(OUT, f"written_{fam}.json"))}
    have = {}
    if missing_from and os.path.isfile(os.path.join(OUT, f"keys_{missing_from}.json")):
        have = _load(f"keys_{missing_from}.json")["keys"]
    for keyer in keyers:
        old = _load(f"keys_{keyer}.json") if os.path.isfile(os.path.join(OUT, f"keys_{keyer}.json")) else {}
        keys: Dict[str, Dict[str, Any]] = dict(old.get("keys", {}))
        calls = list(old.get("calls", []))
        items = []
        for fam in (writers or FAMILIES):
            if fam == keyer or fam not in written:
                continue
            for sid in sorted(written[fam]):
                line = written[fam][sid]
                s = slots.get(sid)
                if s is None or not check_line(s, line)[0] or sid in keys:
                    continue
                if missing_from and sid in have:
                    continue
                fact = s.get("fact") or {}
                about = [a for a in s.get("anchor_words", []) if a.lower() != (fact.get("unit") or "").lower()]
                items.append({"id": sid, "line": line, "thing": fact.get("unit") or "(none)", "about": about})
        for i in range(0, len(items), 100):
            text, meta = run_cli(keyer, KEY_BRIEF + "\n\nLINES:\n" + json.dumps(items[i:i + 100], ensure_ascii=False),
                                 f"{tag_prefix}-{keyer}-{i // 100}")
            calls.append(meta)
            for k in parse_reply(text) or []:
                if isinstance(k, dict) and k.get("id"):
                    keys[k["id"]] = k
        print(keyer, "keyed", len(keys), "of", len(items), flush=True)
        _save(f"keys_{keyer}.json", {"keyer": keyer, "keys": keys, "calls": calls})


def stage_assemble() -> Dict[str, Any]:
    packs = make_packets()
    written = {fam: _load(f"written_{fam}.json")["lines"] if os.path.isfile(os.path.join(OUT, f"written_{fam}.json"))
               else {} for fam in FAMILIES}
    keys = {fam: _load(f"keys_{fam}.json")["keys"] for fam in FAMILIES
            if os.path.isfile(os.path.join(OUT, f"keys_{fam}.json"))}
    rows: Dict[str, List[Dict[str, Any]]] = {"TRAIN": [], "DEV": []}
    tally: Dict[str, Dict[str, int]] = {}
    for fam in FAMILIES:
        for split in ("TRAIN", "DEV"):
            t = tally.setdefault(f"{fam}:{split}", {"slots": 0, "written": 0, "checked": 0, "kept": 0})
            for w in packs[fam][split]:
                for s in w["slots"]:
                    t["slots"] += 1
                    line = written[fam].get(s["id"])
                    if line is None:
                        continue
                    t["written"] += 1
                    if not check_line(s, line)[0]:
                        continue
                    t["checked"] += 1
                    ks = [keys[k][s["id"]] for k in keys if k != fam and s["id"] in keys[k]]
                    row = assemble_one(s, line, ks)
                    if row is not None:
                        rows[split].append(row)
                        t["kept"] += 1
    for split in rows:
        with open(os.path.join(OUT, f"rows_llm_{split.lower()}.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
            for r in rows[split]:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    record = {"tally": tally, "rows": {k: len(v) for k, v in rows.items()}, "labels": ["LLM_WRITTEN", "SYNTHETIC_ONLY"],
              "cost_usd": 0, "note": "command-line tools on subscriptions the owner already pays for"}
    _save("LLM_STRATUM_RECORD.json", record)
    return record


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    fams = tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else FAMILIES
    if stage == "write":
        stage_write(fams)
    elif stage == "key":
        writers = tuple(sys.argv[3].split(",")) if len(sys.argv) > 3 and sys.argv[3] != "-" else None
        missing = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "-" else None
        prefix = sys.argv[5] if len(sys.argv) > 5 else "key"
        stage_key(fams, writers, missing, prefix)
    elif stage == "assemble":
        print(json.dumps(stage_assemble(), indent=1))
