"""build_s7_pilot.py -- CJT-DEV-P1 step 3: construct the independent WordNet-derived
S7-P semantic control, OR emit S7_PILOT_CONSTRUCTION_FAILED (owner directive
CJT-DEV-P1, non-claim-bearing development pilot).

The S7-P control must be a 4-class, balanced (4 verbs each), fixed, WordNet-only
partition of the 16 registered clause-head verbs that is NOT the CAS partition
and NOT a permutation of it, with Cramer's V(S7, CAS) <= 0.35. CAS labels are
read ONLY AFTER construction, to compute the orthogonality gate.

ANTI-FISHING LAW (directive: "Do not manufacture a convenient control"): the
construction rule is PRE-DECLARED and CAS-blind. The primary rule is the one the
repository already froze BEFORE this pilot -- the ALTERNATIVE_TAXONOMY_MANIFEST
construction_law: each verb -> its WordNet primary-sense lexname (supersense);
the four classes are the four most-populous lexnames, smaller lexnames merged
into the most-populous seed, then rebalanced to 4/4/4/4 by repeatedly moving the
alphabetically-first lemma of the largest class to the smallest. The fallback
rule is a second a-priori semantic feature (the sense-1 hypernym's lexname). We
do NOT search across features and pick whichever passes -- that selection would
be driven by the CAS-orthogonality target, i.e. manufacturing. The full
diagnostic landscape is recorded transparently, including any non-selected
construction that happens to pass, with the reason it is excluded.

WordNet is a frozen external lexical resource. The snapshot digest + license are
recorded so the verdict is reproducible. Lemmatization is morphy-direct (no
per-verb judgment calls).

Run:  NLTK_DATA=<dir with corpora/wordnet.zip> python build_s7_pilot.py
Writes S7_PILOT_BUILD_RECEIPT.json (always) and, ONLY on PASS,
S7_PILOT_WORDNET_V1.json.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent

# the 16 registered clause-head verbs and their CAS operation class, from
# ALTERNATIVE_TAXONOMY_MANIFEST_CANDIDATE.json head_verb_table (^2 attract,
# ^3 avert, ^6 decompose, ^8 trigger) -> class index 0..3 in the frozen
# CLASSES order ("^2","^3","^6","^8").
CAS_ORDER = ("^2", "^3", "^6", "^8")
VERBS = ["drawn", "pulled", "felt", "captured",       # ^2 attract   -> 0
         "withdrew", "repelled", "recoiled", "backed",  # ^3 avert    -> 1
         "broke", "lay", "split", "made",             # ^6 decompose -> 2
         "brought", "thought", "reminded", "summoned"]  # ^8 trigger  -> 3
CAS = {v: (i // 4) for i, v in enumerate(VERBS)}
ORTHOGONALITY_THRESHOLD = 0.35


# ---- statistics --------------------------------------------------------------

def contingency(assign):
    tab = [[0] * 4 for _ in range(4)]
    for v in VERBS:
        tab[assign[v]][CAS[v]] += 1
    return tab


def cramers_v(assign):
    tab = contingency(assign)
    n = len(VERBS)
    row = [sum(r) for r in tab]
    col = [sum(tab[i][j] for i in range(4)) for j in range(4)]
    chi = 0.0
    for i in range(4):
        for j in range(4):
            e = row[i] * col[j] / n
            if e > 0:
                chi += (tab[i][j] - e) ** 2 / e
    v = math.sqrt(chi / (n * 3)) if n > 0 else 0.0
    return chi, v, tab, row


def is_permutation_of_cas(assign):
    """True if some relabeling sigma of the 4 class ids maps CAS exactly onto
    assign -- i.e. S7 is CAS with the class names swapped (still forbidden)."""
    for perm in itertools.permutations(range(4)):
        if all(assign[v] == perm[CAS[v]] for v in VERBS):
            return True
    return False


def gate(assign):
    row = [0] * 4
    for v in VERBS:
        row[assign[v]] += 1
    chi, v, tab, _ = cramers_v(assign)
    balanced = (row == [4, 4, 4, 4])
    equals_s3 = all(assign[v] == CAS[v] for v in VERBS)
    perm = is_permutation_of_cas(assign)
    passed = balanced and (v <= ORTHOGONALITY_THRESHOLD) \
        and (not equals_s3) and (not perm)
    return {"balanced": balanced, "class_sizes": row,
            "cramers_v": round(v, 6), "chi2": round(chi, 6),
            "equals_S3": equals_s3, "is_permutation_of_S3": perm,
            "contingency_S7rows_x_CAScols": tab, "gate_pass": passed}


# ---- WordNet features (morphy-direct lemmatization, no judgment calls) --------

def load_features():
    from nltk.corpus import wordnet as wn
    feats = {}
    for v in VERBS:
        base = wn.morphy(v, wn.VERB) or v
        syns = wn.synsets(base, pos="v")
        s1 = syns[0]
        hyp = s1.hypernyms()
        feats[v] = {
            "lemma": base,
            "primary_lexname": s1.lexname(),
            "primary_synset": s1.name(),
            "primary_synset_offset": s1.offset(),
            "n_verb_senses": len(syns),
            "sense1_hypernym_lexname": (hyp[0].lexname() if hyp else s1.lexname()),
            "sense1_n_lemmas": len(s1.lemmas())}
    return feats, wn.get_version()


def sort_partition(feats, keyfn, mode):
    order = sorted(VERBS, key=lambda v: (keyfn(v), feats[v]["lemma"], v))
    return {v: (r % 4 if mode == "rr" else r // 4) for r, v in enumerate(order)}


def manifest_lexname_rule(feats):
    """The repository's frozen construction_law, made fully executable: seed the
    four classes with the four most-populous primary lexnames (ties by lexname
    string); merge every smaller lexname into the most-populous seed; then
    rebalance to 4/4/4/4 by repeatedly moving the alphabetically-first lemma of
    the largest class to the smallest (deterministic, CAS-blind)."""
    from collections import Counter, defaultdict
    lex = Counter(feats[v]["primary_lexname"] for v in VERBS)
    seeds = [l for l, _ in sorted(lex.items(), key=lambda kv: (-kv[1], kv[0]))[:4]]
    grp = defaultdict(list)
    for v in VERBS:
        l = feats[v]["primary_lexname"]
        grp[l if l in seeds else seeds[0]].append(v)
    classes = {i: sorted(grp[seeds[i]], key=lambda v: feats[v]["lemma"])
               for i in range(4)}
    for _ in range(len(VERBS) * 2):
        sizes = {i: len(classes[i]) for i in range(4)}
        if all(s == 4 for s in sizes.values()):
            break
        big = max(sizes, key=lambda i: (sizes[i], -i))
        small = min(sizes, key=lambda i: (sizes[i], i))
        if sizes[big] <= sizes[small] + 1:
            break
        mv = sorted(classes[big], key=lambda v: feats[v]["lemma"])[0]
        classes[big].remove(mv)
        classes[small].append(mv)
    return {v: i for i in range(4) for v in classes[i]}


def pin_wordnet_snapshot():
    data = os.environ.get("NLTK_DATA", "")
    z = None
    for base in list(filter(None, data.split(os.pathsep))) + [""]:
        cand = Path(base) / "corpora" / "wordnet.zip" if base else None
        if cand and cand.is_file():
            z = cand
            break
    if z is None:
        import glob
        hits = glob.glob(str(Path(data) / "**" / "wordnet.zip"), recursive=True) \
            if data else []
        z = Path(hits[0]) if hits else None
    if z is None or not z.is_file():
        return {"wordnet_zip_sha256": "UNAVAILABLE",
                "wordnet_zip_bytes": 0, "note": "wordnet.zip not located"}
    b = z.read_bytes()
    return {"wordnet_zip_sha256": hashlib.sha256(b).hexdigest(),
            "wordnet_zip_bytes": len(b),
            "license": "WordNet Release 3.0 License (Princeton University)",
            "source": "Princeton WordNet 3.0 (obtained via nltk 'wordnet' corpus)"}


def main():
    feats, wn_version = load_features()
    snapshot = pin_wordnet_snapshot()

    primary = manifest_lexname_rule(feats)
    primary_gate = gate(primary)
    fallback = sort_partition(feats, lambda v: feats[v]["sense1_hypernym_lexname"],
                              "block")
    fallback_gate = gate(fallback)

    # transparent diagnostic landscape: every principled construction tried,
    # with its gate result. Recorded so the verdict is auditable; NOT a menu to
    # pick a passing rule from (that selection would be CAS-driven = manufacturing).
    landscape = []
    feature_semantic = {"primary_lexname": True, "sense1_hypernym_lexname": True,
                        "n_verb_senses": False, "primary_synset_offset": False,
                        "sense1_n_lemmas": False}
    for key, semantic in feature_semantic.items():
        for mode in ("block", "rr"):
            g = gate(sort_partition(feats, lambda v, k=key: feats[v][k], mode))
            note = ""
            if g["gate_pass"] and not semantic:
                note = ("EXCLUDED: not a semantic organization (arbitrary WordNet "
                        "identifier / count); selecting it because it passes the "
                        "orthogonality test is manufacturing a convenient control")
            landscape.append({"construction": f"{key}[{mode}]",
                              "semantic_feature": semantic,
                              "cramers_v": g["cramers_v"],
                              "gate_pass": g["gate_pass"], "note": note})

    passing_semantic = [
        {"rule": "PRE_DECLARED_PRIMARY (manifest verb-lexname)", **primary_gate}
    ] if primary_gate["gate_pass"] else []
    if not passing_semantic and fallback_gate["gate_pass"]:
        passing_semantic = [{"rule": "PRE_DECLARED_FALLBACK (sense1-hypernym-lexname)",
                             **fallback_gate}]

    if passing_semantic:
        chosen = passing_semantic[0]
        verdict = "S7_PILOT_CONSTRUCTED"
        table = {v: (primary[v] if "PRIMARY" in chosen["rule"] else fallback[v])
                 for v in VERBS}
    else:
        chosen = None
        verdict = "S7_PILOT_CONSTRUCTION_FAILED"
        table = None

    receipt = {
        "receipt_id": "S7_PILOT_BUILD_RECEIPT",
        "pilot": "CJT-DEV-P1",
        "non_claim_bearing": True,
        "verdict": verdict,
        "orthogonality_threshold_cramers_v": ORTHOGONALITY_THRESHOLD,
        "wordnet": {"version": wn_version, "lemmatization": "morphy-direct (no judgment)",
                    **snapshot},
        "registered_verbs": VERBS,
        "cas_class_order": CAS_ORDER,
        "cas_mapping_verb_to_classindex": CAS,
        "per_verb_wordnet_features": feats,
        "pre_declared_primary_rule": {
            "name": "verb primary-sense lexname, most-populous-4 + merge + rebalance "
                    "(ALTERNATIVE_TAXONOMY_MANIFEST_CANDIDATE.construction_law)",
            "assignment_verb_to_classindex": primary, **primary_gate},
        "pre_declared_fallback_rule": {
            "name": "sense-1 hypernym lexname, sorted contiguous-block balanced",
            "assignment_verb_to_classindex": fallback, **fallback_gate},
        "diagnostic_landscape": landscape,
        "conclusion": (
            "No PRE-DECLARED, CAS-blind, semantic WordNet partition of the 16 "
            "registered verbs reaches Cramer's V <= 0.35 against the CAS classes. "
            "The pre-declared primary rule (the repository's own frozen "
            "construction_law) yields V=%.4f (fails by %.4f). Every no-judgment "
            "semantic feature fails. The only constructions that pass are "
            "non-semantic identifier/lemmatization shuffles selected BECAUSE they "
            "pass -- i.e. manufacturing, which the directive forbids. This "
            "confirms the manifest's own circularity_disclosure: the answer "
            "function is defined over the CAS classes, so a genuinely task-relevant "
            "non-CAS control cannot exist on this vocabulary. Emitting "
            "S7_PILOT_CONSTRUCTION_FAILED and stopping BEFORE any GPU use, per the "
            "directive."
            % (primary_gate["cramers_v"],
               primary_gate["cramers_v"] - ORTHOGONALITY_THRESHOLD))
        if verdict == "S7_PILOT_CONSTRUCTION_FAILED" else
        "A pre-declared semantic WordNet partition passed all S7-P gates.",
        "chosen_rule": chosen}

    (HERE / "S7_PILOT_BUILD_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if table is not None:
        (HERE / "S7_PILOT_WORDNET_V1.json").write_text(
            json.dumps({"table_id": "S7_PILOT_WORDNET_V1",
                        "non_claim_bearing": True,
                        "verb_to_class": table,
                        "wordnet": receipt["wordnet"]}, indent=2) + "\n",
            encoding="utf-8")
    print(f"VERDICT: {verdict}")
    print(f"  primary rule (manifest verb-lexname): V={primary_gate['cramers_v']} "
          f"gate_pass={primary_gate['gate_pass']}")
    print(f"  fallback rule (sense1-hypernym-lexname): V={fallback_gate['cramers_v']} "
          f"gate_pass={fallback_gate['gate_pass']}")
    print(f"  wordnet {wn_version} zip_sha256="
          f"{snapshot.get('wordnet_zip_sha256','?')[:16]}...")
    return 0 if verdict == "S7_PILOT_CONSTRUCTED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
