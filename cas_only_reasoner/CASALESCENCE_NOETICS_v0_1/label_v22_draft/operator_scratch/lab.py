import json, re, os

CHUNK = "C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/label_v21/verdict/team_a/chunk_02.json"
WORK = "C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/label_v21/verdict/labels_team_a.json.chunk_02.work.json"
SCRATCH = os.path.dirname(os.path.abspath(__file__))

with open(CHUNK, encoding="utf-8") as f:
    PASSAGES = {p["id"]: p["text"] for p in json.load(f)}


def sentences(text):
    """Split into sentences: end mark . ? ! optionally followed by closing quote chars, then a space."""
    out = []
    start = 0
    for m in re.finditer(r"[.!?]+['\"\u2019\u201d)]*(?=\s|$)", text):
        end = m.end()
        seg = text[start:end]
        # skip abbreviations such as 'Mrs.' (a period right after a short title word)
        if re.search(r"\b(Mrs|Mr|Ms|Dr)\.$", seg):
            continue
        out.append(seg.strip())
        start = end
        while start < len(text) and text[start] == " ":
            start += 1
    rest = text[start:].strip()
    if rest:
        out.append(rest)
    return out


def sup(pid, *idx):
    """Support = sentences numbered 1.. (adjacent), joined by one space."""
    ss = sentences(PASSAGES[pid])
    nums = list(idx)
    assert nums == list(range(nums[0], nums[-1] + 1)), "support sentences must be adjacent"
    assert len(nums) <= 4
    return " ".join(ss[i - 1] for i in nums)


def E(noetic, label, support, mind, relative_to, certainty, saying, other=None, reached=None):
    d = {
        "noetic": noetic,
        "label": label,
        "support": support,
        "mind": mind,
        "relative_to": relative_to,
        "certainty": certainty,
        "saying": saying,
    }
    if other is not None:
        d["other_candidate"] = other
    if reached is not None:
        d["reached_by"] = reached
    return d


def rec(pid, entries, notes=None, none=False):
    return {
        "passage_id": pid,
        "none_of_these": none,
        "entries": entries,
        "not_enough_information": notes or [],
    }


def check(records):
    """Own pre-check of the form rules stated in the task message. Returns list of problems."""
    probs = []
    for r in records:
        pid = r["passage_id"]
        text = PASSAGES[pid]
        ss = sentences(text)
        ents = r["entries"]
        if r["none_of_these"] and ents:
            probs.append((pid, "none_of_these true but entries present"))
        if not r["none_of_these"] and not ents:
            probs.append((pid, "no entries but none_of_these false"))
        ones = {e["label"] for e in ents if e["noetic"] == "^1"}
        for e in ents:
            tag = (pid, e["noetic"], e["label"][:30])
            keys = {"noetic", "label", "support", "mind", "relative_to", "certainty", "saying"}
            extra = set(e) - keys - {"other_candidate", "reached_by"}
            if extra or not keys <= set(e):
                probs.append((tag, "fields wrong %s" % extra))
            if e["noetic"] not in ["^%d" % i for i in range(1, 10)]:
                probs.append((tag, "bad noetic"))
            if e["certainty"] not in ("clear", "ambiguous"):
                probs.append((tag, "bad certainty"))
            if ("other_candidate" in e) != (e["certainty"] == "ambiguous"):
                probs.append((tag, "other_candidate vs certainty"))
            if "other_candidate" in e and not (re.fullmatch(r"\^[1-9]", e["other_candidate"]) or e["other_candidate"] in ("none", "reasoning")):
                probs.append((tag, "bad other_candidate"))
            if "reached_by" in e and not (e["noetic"] == "^9" and e["relative_to"] == "" and e["reached_by"] == "reasoning"):
                probs.append((tag, "bad reached_by"))
            if e["support"] not in text:
                probs.append((tag, "support not exact text"))
            # support must be whole adjacent sentences
            n = 0
            for i in range(len(ss)):
                for j in range(i, min(i + 4, len(ss))):
                    if " ".join(ss[i:j + 1]) == e["support"]:
                        n = j - i + 1
            if n == 0:
                probs.append((tag, "support not 1-4 whole adjacent sentences"))
            lw = len(e["label"].split())
            if not (1 <= lw <= 12):
                probs.append((tag, "label words %d" % lw))
            if e["label"] not in e["support"]:
                probs.append((tag, "label not in support"))
            if e["noetic"] == "^1":
                if e["saying"] != "":
                    probs.append((tag, "^1 saying must be empty"))
                if e["mind"] != e["label"] or e["relative_to"] != "":
                    probs.append((tag, "^1 mind/relative_to wrong"))
                # support should hold first place of the name
                first = text.find(e["label"])
                if first < 0 or not (text.find(e["support"]) <= first < text.find(e["support"]) + len(e["support"])):
                    probs.append((tag, "^1 support is not the sentence of the first mention"))
            else:
                sw = len(e["saying"].split())
                if not (2 <= sw <= 20):
                    probs.append((tag, "saying words %d" % sw))
                if e["saying"] in text:
                    probs.append((tag, "saying copies passage"))
                if e["noetic"] == "^6":
                    if e["mind"] != "":
                        probs.append((tag, "^6 mind must be empty"))
                else:
                    if e["mind"] == "" or e["mind"] not in ones:
                        probs.append((tag, "mind is not a ^1 label"))
                if e["relative_to"] != "":
                    if e["relative_to"] not in text:
                        probs.append((tag, "relative_to not passage text"))
                    if e["relative_to"] not in e["support"]:
                        probs.append((tag, "SOFT relative_to not in support"))
        # pair symmetry
        by = {(e["noetic"], e["label"]): e for e in ents}
        for e in ents:
            if e["noetic"] in ("^8", "^9") and e["relative_to"]:
                other = "^9" if e["noetic"] == "^8" else "^8"
                if (other, e["relative_to"]) not in by:
                    probs.append(((pid, e["noetic"], e["label"][:30]), "pair partner label not found"))
    return probs


def dump(records, name):
    p = os.path.join(SCRATCH, name)
    with open(p, "w", encoding="ascii") as f:
        json.dump(records, f, indent=1, ensure_ascii=True)
    return p
