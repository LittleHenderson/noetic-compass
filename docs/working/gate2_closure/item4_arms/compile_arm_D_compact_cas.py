#!/usr/bin/env python3
"""
Gate 2 item 4 / build item B4 — compile the Arm D payload.

Arm D is COMPARATOR-ONLY. Spec 8.1, verbatim:
    "Arm D: shortened CAS translation summaries, explicitly comparator-only."
Registry future_agent_rule 1, verbatim:
    "Do not use compact CAS summaries as substitutes for original TKS definitions
     in a claim-bearing probe unless the compact form is an explicitly named
     comparator arm."

This script is mechanical. It performs NO paraphrase, NO summarisation and NO
authoring of definition prose. Every definition string it emits is the
concatenation of two byte-strings lifted verbatim from
docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md (sha256 cda85c03...), joined by a single
ASCII space, per the compile rule frozen in
GATE2_ITEM4_PREREGISTRATION.md section 2.4.

Run:  python compile_arm_D_compact_cas.py
Writes: arm_D_compact_cas.json  (next to this script)

Nothing is committed to git and no experiment is run.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS")
OUT_DIR = REPO / "docs" / "working" / "gate2_closure" / "item4_arms"
OUT_PATH = OUT_DIR / "arm_D_compact_cas.json"

CAS_SRC = REPO / "docs" / "CAS_FOUNDATIONAL_CLARIFICATIONS.md"
ARM_A_SRC = REPO / "docs" / "working" / "tks_owner_locked_definitions_20260603.json"
BANK_BLOB = "165df0f6ff08c80fe1c42cd4412478527aabc934"  # branch experiment/cas-probe-pythia

CREATED_AT = "2026-07-25T00:00:00Z"


# --------------------------------------------------------------------------
# 1. VERBATIM EXTRACTION FROM THE PINNED SOURCE
# --------------------------------------------------------------------------
# Every string below is extracted from CAS_FOUNDATIONAL_CLARIFICATIONS.md by
# regex against the file on disk, not typed from memory. extract_*() asserts
# the extracted text is present byte-for-byte in the file, so a source edit
# breaks the build loudly instead of silently producing stale text.


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def extract_noetic_definitions(text: str) -> dict[str, dict[str, str]]:
    """Clarification 1 -> the 10 authoritative Noetic definitions, verbatim.

    Line form:
      - **^0 (CO-0): Idea** - All things in and outside the Mind.
    (the dash is U+2014 EM DASH)
    """
    pat = re.compile(
        r"^- \*\*\^(?P<idx>\d) \(CO-(?P=idx)\): (?P<name>[^*]+)\*\* \u2014 (?P<body>.+)$",
        re.MULTILINE,
    )
    out: dict[str, dict[str, str]] = {}
    for m in pat.finditer(text):
        out["^" + m.group("idx")] = {
            "noetic": "^" + m.group("idx"),
            "name": m.group("name").strip(),
            "definition_verbatim": m.group("body").strip(),
        }
    if len(out) != 10:
        raise SystemExit(f"expected 10 Noetic definitions, extracted {len(out)}")
    for v in out.values():
        if v["definition_verbatim"] not in text:
            raise SystemExit("noetic verbatim check failed: " + v["definition_verbatim"])
    return out


def extract_register_definitions(text: str) -> dict[str, dict[str, str]]:
    """Clarification 8 section 2 ("The four Registers - definitions") -> the 4
    Register definition lines, verbatim.

    Block form:
      **`|T` - Transcendent Register**
      High-abstraction, purpose-orienting, integrative-across-particulars.
      - Human: ...
    The definition line is the single line between the bold header and the first
    instantiation bullet. The three Human/AI/Biological bullets are
    INSTANTIATIONS, not the definition, and are excluded; see
    `register_definition_scope_note` in the emitted payload.
    """
    pat = re.compile(
        r"^\*\*`\|(?P<sym>[TAfE])` \u2014 (?P<name>\w+) Register\*\*\n(?P<body>[^\n]+)\n- Human:",
        re.MULTILINE,
    )
    out: dict[str, dict[str, str]] = {}
    for m in pat.finditer(text):
        out["|" + m.group("sym")] = {
            "register": "|" + m.group("sym"),
            "name": m.group("name").strip(),
            "definition_verbatim": m.group("body").strip(),
        }
    if len(out) != 4:
        raise SystemExit(f"expected 4 Register definitions, extracted {len(out)}")
    for v in out.values():
        if v["definition_verbatim"] not in text:
            raise SystemExit("register verbatim check failed")
    return out


def extract_domain_axis_sentence(text: str) -> str:
    """Clarification 8 section 4 -> the ONLY sentence in the pinned source that
    says anything about what the Domain axis IS. There are no per-domain
    definitions anywhere in the file; see `domain_definition_gap` in the payload.
    """
    frag = (
        "The Domain axis (Principled / Cognitive / Evaluative / Operational) "
        "specifies the **ontological-substrate level** of a cognitive operation."
    )
    if frag not in text:
        raise SystemExit("domain axis sentence not found verbatim in source")
    return frag


DOMAIN_PREDICATE_VERBATIM = "specifies the ontological-substrate level of a cognitive operation"
DOMAIN_NAMES = {"P": "Principled", "C": "Cognitive", "E": "Evaluative", "O": "Operational"}


# --------------------------------------------------------------------------
# 2. THE CROSSWALK  (PROVISIONAL - OWNER-ACTION BLOCKER B5)
# --------------------------------------------------------------------------
# TKS Noetic position 1..10 -> CAS Noetic ^1..^9, ^0.
NOETIC_CROSSWALK = {1: "^1", 2: "^2", 3: "^3", 4: "^4", 5: "^5",
                    6: "^6", 7: "^7", 8: "^8", 9: "^9", 10: "^0"}

# TKS World A/B/C/D -> CAS *Register*  (the source's own section 8 cross-product)
WORLD_TO_REGISTER = {"A": "|T", "B": "|A", "C": "|f", "D": "|E"}

# TKS World A/B/C/D -> CAS *Domain*  (the pre-registration's literal rule wording)
WORLD_TO_DOMAIN = {"A": "P", "B": "C", "C": "E", "D": "O"}

WORLD_TKS_NAME = {"A": "Spiritual", "B": "Mental", "C": "Emotional", "D": "Physical"}

CODES = [f"{w}{n}" for w in "ABCD" for n in range(1, 11)]


# --------------------------------------------------------------------------
# 3. LENGTH / OVERLAP MEASUREMENT
# --------------------------------------------------------------------------
STOPWORDS = {
    "a", "an", "and", "or", "the", "of", "to", "in", "on", "at", "by", "for",
    "with", "is", "are", "was", "were", "be", "been", "being", "it", "its",
    "that", "this", "these", "those", "as", "from", "into", "than", "then",
    "which", "what", "who", "whom", "all", "any", "both", "each", "other",
    "such", "no", "not", "only", "own", "same", "so", "too", "very", "can",
    "will", "just", "has", "have", "had", "does", "do", "did", "but", "if",
    "one", "s", "t",
}


def content_words(s: str) -> set[str]:
    toks = re.findall(r"[a-z0-9]+", s.lower())
    return {t for t in toks if t not in STOPWORDS and len(t) > 1}


def jaccard(a: str, b: str) -> float:
    A, B = content_words(a), content_words(b)
    if not A and not B:
        return 0.0
    return len(A & B) / len(A | B)


def max_shared_ngram(a: str, b: str, cap: int = 12) -> int:
    ta = re.findall(r"[a-z0-9]+", a.lower())
    tb = set()
    tokens_b = re.findall(r"[a-z0-9]+", b.lower())
    best = 0
    for n in range(1, cap + 1):
        gb = {tuple(tokens_b[i:i + n]) for i in range(len(tokens_b) - n + 1)}
        ga = {tuple(ta[i:i + n]) for i in range(len(ta) - n + 1)}
        if ga & gb:
            best = n
        else:
            break
    del tb
    return best


def stats_block(lengths: list[int]) -> dict:
    return {
        "n": len(lengths),
        "min": min(lengths),
        "max": max(lengths),
        "mean": round(statistics.fmean(lengths), 4),
        "sd_sample": round(statistics.stdev(lengths), 4) if len(lengths) > 1 else 0.0,
    }


# --------------------------------------------------------------------------
# 4. BUILD
# --------------------------------------------------------------------------

def load_bank_glosses() -> dict[str, dict]:
    raw = subprocess.run(
        ["git", "cat-file", "-p", BANK_BLOB],
        cwd=str(REPO), capture_output=True, check=True,
    ).stdout.decode("utf-8")
    out: dict[str, dict] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        out.setdefault(r["element_label"], {
            "gloss": r["element_gloss"],
            "element_domain": r["element_domain"],
            "element_register": r["element_register"],
            "element_noetic_tks": r["element_noetic_tks"],
            "element_cas_noetic": r["element_cas_noetic"],
        })
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cas_text = CAS_SRC.read_text(encoding="utf-8")
    cas_sha = sha256_file(CAS_SRC)
    arm_a_sha = sha256_file(ARM_A_SRC)

    noetics = extract_noetic_definitions(cas_text)
    registers = extract_register_definitions(cas_text)
    domain_axis_sentence = extract_domain_axis_sentence(cas_text)
    if DOMAIN_PREDICATE_VERBATIM not in cas_text.replace("**", ""):
        raise SystemExit("domain predicate fragment not verbatim in source")

    arm_a = {e["code"]: e for e in json.loads(ARM_A_SRC.read_text(encoding="utf-8"))["tks_40_elements"]}
    if sorted(arm_a) != sorted(CODES):
        raise SystemExit("Arm A code set != A1..D10")

    bank = load_bank_glosses()
    if sorted(bank) != sorted(CODES):
        raise SystemExit("bank code set != A1..D10")

    # crosswalk corroboration against the bank fixture (tier 8, corroboration only)
    corroboration = {"noetic_agreements": 0, "register_agreements": 0, "disagreements": []}
    for code in CODES:
        world, npos = code[0], int(code[1:])
        b = bank[code]
        if b["element_cas_noetic"] == NOETIC_CROSSWALK[npos] and b["element_noetic_tks"] == npos:
            corroboration["noetic_agreements"] += 1
        else:
            corroboration["disagreements"].append(f"{code}:noetic")
        if "|" + b["element_register"] == WORLD_TO_REGISTER[world]:
            corroboration["register_agreements"] += 1
        else:
            corroboration["disagreements"].append(f"{code}:register")

    # ---- variant D_REG_V1  (recommended primary) -------------------------
    defs_reg: dict[str, str] = {}
    titles_reg: dict[str, str] = {}
    # ---- variant D_DOM_LITERAL_V1 (recorded, not recommended) ------------
    defs_dom: dict[str, str] = {}
    titles_dom: dict[str, str] = {}

    for code in CODES:
        world, npos = code[0], int(code[1:])
        nk = NOETIC_CROSSWALK[npos]
        nd = noetics[nk]

        rk = WORLD_TO_REGISTER[world]
        rd = registers[rk]
        defs_reg[code] = nd["definition_verbatim"] + " " + rd["definition_verbatim"]
        titles_reg[code] = f"{rd['name']} {nd['name']}"

        dk = WORLD_TO_DOMAIN[world]
        dom_sentence = f"The {DOMAIN_NAMES[dk]} domain {DOMAIN_PREDICATE_VERBATIM}."
        defs_dom[code] = nd["definition_verbatim"] + " " + dom_sentence
        titles_dom[code] = f"{DOMAIN_NAMES[dk]} {nd['name']}"

    def measure(defs: dict[str, str]) -> dict:
        per_code = {}
        for code in CODES:
            d = defs[code]
            a = arm_a[code]["definition"]
            per_code[code] = {
                "chars": len(d),
                "words_whitespace": len(d.split()),
                "arm_a_chars": len(a),
                "delta_chars_vs_arm_a": len(d) - len(a),
                "ratio_vs_arm_a": round(len(d) / len(a), 4),
                "bank_gloss_content_word_jaccard": round(jaccard(d, bank[code]["gloss"]), 4),
                "bank_gloss_max_shared_ngram_tokens": max_shared_ngram(d, bank[code]["gloss"]),
                "arm_a_content_word_jaccard": round(jaccard(d, a), 4),
                "arm_a_max_shared_ngram_tokens": max_shared_ngram(d, a),
            }
        lens = [per_code[c]["chars"] for c in CODES]
        alens = [per_code[c]["arm_a_chars"] for c in CODES]
        deltas = [per_code[c]["delta_chars_vs_arm_a"] for c in CODES]
        ratios = [per_code[c]["ratio_vs_arm_a"] for c in CODES]
        worst = min(per_code, key=lambda c: per_code[c]["delta_chars_vs_arm_a"])
        best = max(per_code, key=lambda c: per_code[c]["delta_chars_vs_arm_a"])
        return {
            "unit": "characters (python len() on the UTF-8 string)",
            "token_counts": "unavailable_until_tokenizer_pinned (required_run_bindings[10]; build item B8)",
            "per_code": per_code,
            "arm_D": stats_block(lens),
            "arm_A_reference": stats_block(alens),
            "delta_vs_arm_A": {
                "mean": round(statistics.fmean(deltas), 4),
                "sd_sample": round(statistics.stdev(deltas), 4),
                "min_most_negative": min(deltas),
                "max_least_negative": max(deltas),
                "worst_case_code": worst,
                "worst_case_delta": per_code[worst]["delta_chars_vs_arm_a"],
                "least_mismatched_code": best,
                "least_mismatched_delta": per_code[best]["delta_chars_vs_arm_a"],
                "codes_within_plus_minus_10_pct_of_arm_A": sum(1 for r in ratios if 0.9 <= r <= 1.1),
                "codes_where_D_longer_than_A": sum(1 for d in deltas if d > 0),
            },
            "ratio_vs_arm_A": {
                "min": min(ratios), "max": max(ratios),
                "mean": round(statistics.fmean(ratios), 4),
                "sd_sample": round(statistics.stdev(ratios), 4),
            },
            "bank_gloss_overlap_S13": {
                "jaccard": stats_block([per_code[c]["bank_gloss_content_word_jaccard"] for c in CODES])
                | {"mean": round(statistics.fmean(per_code[c]["bank_gloss_content_word_jaccard"] for c in CODES), 4)},
                "max_shared_ngram_tokens_max": max(per_code[c]["bank_gloss_max_shared_ngram_tokens"] for c in CODES),
            },
            "arm_a_text_overlap": {
                "jaccard_mean": round(statistics.fmean(per_code[c]["arm_a_content_word_jaccard"] for c in CODES), 4),
                "jaccard_max": max(per_code[c]["arm_a_content_word_jaccard"] for c in CODES),
                "max_shared_ngram_tokens_max": max(per_code[c]["arm_a_max_shared_ngram_tokens"] for c in CODES),
            },
        }

    payload = build_payload(
        cas_sha, arm_a_sha, noetics, registers, domain_axis_sentence,
        defs_reg, titles_reg, defs_dom, titles_dom,
        measure(defs_reg), measure(defs_dom), corroboration,
    )

    body = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    # Write BYTES with LF endings explicitly. Path.write_text() on Windows
    # translates \n -> \r\n, which makes the on-disk sha256 differ from the
    # sha256 of the string that was hashed. That divergence is the CRLF defect
    # that froze a previous run of this project; it is not repeated here.
    blob = body.encode("utf-8")
    OUT_PATH.write_bytes(blob)
    digest = hashlib.sha256(blob).hexdigest()
    print(f"wrote {OUT_PATH}")
    print("payload sha256 (on-disk bytes, LF):", digest)
    if hashlib.sha256(OUT_PATH.read_bytes()).hexdigest() != digest:
        raise SystemExit("on-disk sha256 does not match computed sha256")


def build_payload(cas_sha, arm_a_sha, noetics, registers, domain_axis_sentence,
                  defs_reg, titles_reg, defs_dom, titles_dom,
                  stats_reg, stats_dom, corroboration) -> dict:
    return {
        "schema_version": "gate2_item4_arm_payload_v1",
        "arm_id": "CAS_COMPACT_COMPILED_40E_V1",
        "arm_letter": "D",
        "design_id": "TKS-DEFCTX-40E-PRIMARY-v1",
        "build_item": "B4",
        "provenance": "ASSISTANT_COMPILED",
        "authorship": "ASSISTANT_COMPILED_TIER_7",
        "claim_bearing_precedence": "tier 7 (pedagogical summary) - second-lowest of eight",
        "created_at": CREATED_AT,
        "created_by": "assistant (Claude, Gate 2 item 4 build subagent)",
        "git_committed": False,
        "experiment_run": False,

        "comparator_only_declaration": {
            "status": "COMPARATOR_ONLY",
            "spec_8_1_verbatim": "Arm D: shortened CAS translation summaries, explicitly comparator-only.",
            "registry_future_agent_rule_1_verbatim": (
                "Do not use compact CAS summaries as substitutes for original TKS definitions in a "
                "claim-bearing probe unless the compact form is an explicitly named comparator arm."
            ),
            "prereg_2_4_verbatim": "Arm D is never a candidate for the licensed claim.",
            "converse_also_binding_prereg_10_1_verbatim": (
                "Arm D's comparator-only status governs what Arm D may be claimed FOR. It does NOT make "
                "\"Arm D beats Arm A\" uninformative. If Arm D >= Arm A, the reported finding is that compact "
                "CAS restatements preserve as much of the readable semantic content as the original owner "
                "wording, and the canonical-wording claim is refuted."
            ),
        },

        "source_refs": [
            {
                "role": "definition_source (the ONLY source of definition prose in this payload)",
                "path": "C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md",
                "sha256": cas_sha,
                "matches_prereg_2_4_expected_sha256": cas_sha == "cda85c03273c47f7df9ac53258920b95ba7b3b2007b0e760856a67497f661880",
                "extracted": "Clarification 1 (10 Noetic definitions); Clarification 8 s2 (4 Register definitions); Clarification 8 s4 (the single Domain-axis sentence); Clarification 8 s8 (the 10x4 cross-product statement)",
            },
            {
                "role": "length reference and crosswalk index corroboration ONLY - NO text from this file appears in any Arm D definition",
                "path": "C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/tks_owner_locked_definitions_20260603.json",
                "sha256": arm_a_sha,
                "matches_prereg_2_1_expected_sha256": arm_a_sha == "d3dac0ef5c94ccd768da0f18987846d8d0c0fa0b366e13dccc49c82252d2fc12",
                "used_for": [
                    "per-code character counts for the length_stats delta table",
                    "confirming the code set is exactly A1..D10",
                    "corroborating TKS noetic position -> CAS noetic via the owner's own element TITLES (e.g. A1 'Spiritual Mind' <-> ^1 Mind, A10 'Spiritual Idea' <-> ^0 Idea)",
                ],
                "not_used_for": "any definition text - Arm A prose is never copied, paraphrased, or summarised here",
            },
            {
                "role": "holdout bank - code spelling, and the S13 lexical-overlap covariate",
                "path": "noetic-compass-scaffold/noetic-compass/research/cas_probe/stage9_elements_pilot_20260517.jsonl",
                "git_blob_id": BANK_BLOB,
                "branch": "experiment/cas-probe-pythia",
                "sha256": "2f8637eedff0fb4d9e6191bd5c051ddc21cea699e33621896469a2e522306889",
                "matches_prereg_4_1_expected_sha256": True,
                "claim_bearing_precedence": "tier 8 (generated fixture) - corroboration only, never authority",
            },
        ],

        "compile_rule": {
            "prereg_2_4_frozen_rule_verbatim": (
                "definition(domain d, noetic n) = \"<verbatim Noetic ^n definition from Clarification 1>\" "
                "+ \" \" + \"<verbatim Domain-d definition>\""
            ),
            "template_as_executed": (
                "definition(code) = NOETIC_DEF[ crosswalk_noetic(code) ] + \" \" + "
                "SECOND_FACTOR_DEF[ crosswalk_world(code) ]"
            ),
            "template_applied_uniformly": True,
            "join": "exactly one ASCII space (U+0020); no added punctuation, no code, no title, no domain word, no register word beyond what the verbatim source strings contain",
            "authorial_discretion_in_definition_prose": "none in variant D_REG_V1 - both halves are byte-verbatim from the pinned source",
            "determinism": "pure function of (pinned source bytes, crosswalk); rerunning the script reproduces byte-identical output",
            "script": "docs/working/gate2_closure/item4_arms/compile_arm_D_compact_cas.py",
        },

        # -----------------------------------------------------------------
        "BLOCKER_domain_definition_gap": {
            "severity": "MUST BE RESOLVED BEFORE CAPTURE - new build item, propose id B4a",
            "finding": (
                "The pre-registration section 2.4 states the pinned source 'defines the 10 Noetics, 4 Domains, "
                "7 Drives and 4 Registers'. Measured this session: the file contains ZERO per-domain "
                "definitions. It defines the 10 Noetics (Clarification 1) and the 4 Registers (Clarification 8 "
                "section 2) with a definition line each, but for the Domain axis it contains exactly one "
                "sentence, which names the four domains and says what the AXIS specifies - it does not define "
                "P, C, E or O individually."
            ),
            "the_only_domain_text_in_the_pinned_source_verbatim": domain_axis_sentence,
            "consequence": (
                "The frozen rule's slot '<verbatim Domain-d definition>' has no referent. Executed with maximal "
                "literalness - substituting the one available sentence for all four domains - it emits only 10 "
                "distinct strings for 40 codes, four-way tied under a cosine-argmax readout, capping macro-F1 at "
                "roughly 0.25 by construction. That is a broken arm, not a comparator. The rule as written is "
                "therefore NOT EXECUTABLE from the pinned source without an authorship step, which contradicts "
                "its own 'zero authorial discretion' clause."
            ),
            "what_the_pinned_source_says_instead_verbatim": (
                "TKS encoded both cross-products with the same 4-Worlds axis. Reframed in secular universal "
                "terms as 4 Registers (T, A, f, E), this axis applies consistently across all CAS primitives - "
                "both Noetic-level (10 x 4 = 40 Cognitive-State-by-Register combinations) and Drive-level "
                "(7 x 4 = 28 Drive-by-Register combinations)."
            ),
            "reading": (
                "The pinned source's own account of the 40-Element cross-product makes the second factor the "
                "REGISTER axis, not the Domain axis. This is precisely known_conflict "
                "'tks_world_to_cas_domain_and_register_collision' (P0_SEMANTIC_AXIS), which the pre-registration "
                "already flags as blocking Arm D at B5. Two variants are therefore emitted below and the choice "
                "between them is an owner decision, not an assistant decision."
            ),
            "resolution_required_from_owner": (
                "At B5 ratification, state which variant Arm D is: D_REG_V1 or D_DOM_LITERAL_V1. The selection "
                "MUST be recorded and hashed BEFORE capture. Promoting a variant after any number exists would "
                "be exactly the post-hoc selection the pre-registration forbids."
            ),
        },

        "BLOCKER_crosswalk_unratified": {
            "binding_stamp": "CONDITIONAL_ON_UNRATIFIED_CROSSWALK",
            "build_item": "B5 (OWNER-ACTION BLOCKER)",
            "prereg_2_4_verbatim": (
                "Every A-vs-D number is stamped CONDITIONAL_ON_UNRATIFIED_CROSSWALK unless B5 is completed. "
                "8.4's \"beat the compact arm\" criterion cannot be licensed until the owner ratifies the "
                "crosswalk, and the ratification must be hashed into required_run_bindings[6] before capture, "
                "not after."
            ),
            "required_run_bindings_6_tks_to_cas_crosswalk_sha256": "EMPTY - no ratified artifact exists on disk",
            "noetic_crosswalk_used": NOETIC_CROSSWALK,
            "noetic_crosswalk_basis": (
                "Name identity. The owner's own Arm A element titles carry the Noetic name at each position "
                "(A1 'Spiritual Mind' <-> ^1 Mind; A8 'Spiritual Above' <-> ^8 Above/Cause; A9 'Spiritual Below' "
                "<-> ^9 Below/Effect; A10 'Spiritual Idea' <-> ^0 Idea). This is corroboration from an owner "
                "source, and it is the strong half of the crosswalk - but it is still not a ratified artifact."
            ),
            "world_to_register_used": WORLD_TO_REGISTER,
            "world_to_register_basis": "Clarification 8 section 8 of the pinned source (the 10 x 4 = 40 cross-product statement), plus TKS world names Spiritual/Mental/Emotional/Physical.",
            "world_to_domain_used": WORLD_TO_DOMAIN,
            "world_to_domain_basis": (
                "ASSISTANT-ASSERTED BY ANALOGY ONLY (Spiritual->Principled, Mental->Cognitive, "
                "Emotional->Evaluative, Physical->Operational). Nothing in the pinned source states this "
                "mapping. It is the weakest link in the payload and is the reason D_DOM_LITERAL_V1 is not "
                "recommended as primary."
            ),
            "bank_fixture_corroboration": corroboration
            | {"note": "The bank asserts element_domain (the TKS world letter A/B/C/D) and element_register "
                       "(T/A/f/E). It carries NO CAS-domain field at all. That is independent corroboration that "
                       "the second factor of the 40-Element cross-product was understood as Register. The bank is "
                       "precedence tier 8 and cannot supply authority for a tier-1 claim."},
        },

        "variant_binding": {
            "primary_variant_recommendation": "D_REG_V1",
            "primary_variant_binding_status": "UNRESOLVED_PENDING_B5 - owner selects",
            "recommendation_reason": (
                "D_REG_V1 is the only variant whose definition prose is 100% byte-verbatim from the pinned "
                "source, the only one supported by the source's own cross-product statement, and the only one "
                "that is not near-degenerate on its second factor. D_DOM_LITERAL_V1 conforms to the literal "
                "wording of the frozen rule but requires an assistant-assembled domain sentence and an "
                "assistant-asserted world->domain mapping, and its second factor is discriminated by one "
                "substituted word."
            ),
            "top_level_definitions_field_contains": "D_REG_V1",
            "how_to_switch": "replace `definitions` and `titles` with variants.D_DOM_LITERAL_V1.*, record the decision, rehash, and only then capture",
        },

        "extracted_source_primitives": {
            "noetics_verbatim_clarification_1": noetics,
            "registers_verbatim_clarification_8_section_2": registers,
            "register_definition_scope_note": (
                "The Register definition taken is the single definition line under each bold register header. "
                "The three 'Human:/AI:/Biological:' bullets that follow are INSTANTIATIONS of that definition "
                "across architectures, not the definition. Including them would roughly triple Arm D's length "
                "and would push Arm D from ~40% shorter than Arm A to ~70% longer, i.e. it would trade one "
                "length confound for a larger one in the opposite direction. The narrower reading is also what "
                "the spec's word 'shortened' requires and what pre-registration section 3.2 anticipates "
                "('compiled; will be short'). This is the single scope judgement in the build and it is "
                "disclosed here rather than buried."
            ),
            "domain_axis_sentence_verbatim_clarification_8_section_4": domain_axis_sentence,
        },

        "element_codes": CODES,
        "code_spelling_source": "bank element_label, verified identical to Arm A codes: A1..A10, B1..B10, C1..C10, D1..D10 (one-based, no zero padding)",

        "titles": titles_reg,
        "titles_note": "Titles are CAS-derived (second-factor name + Noetic name). They are NOT the owner's Arm A titles. Per pre-registration section 2.0 Step 1, `code` and `title` are DISCARDED before the anchor pass for every arm; they are carried here only for schema completeness and human audit.",

        "definitions": defs_reg,

        "variants": {
            "D_REG_V1": {
                "second_factor": "CAS Register (Clarification 8 section 2), per the pinned source's own 10 x 4 cross-product",
                "definition_prose_provenance": "100% byte-verbatim from the pinned source; join is one ASCII space",
                "titles": titles_reg,
                "definitions": defs_reg,
                "length_stats": stats_reg,
            },
            "D_DOM_LITERAL_V1": {
                "second_factor": "CAS Domain (the literal wording of the frozen rule)",
                "definition_prose_provenance": (
                    "Noetic half byte-verbatim. Domain half ASSISTANT-ASSEMBLED: the template "
                    "\"The <DomainName> domain <verbatim predicate>.\" where <verbatim predicate> = "
                    "\"" + DOMAIN_PREDICATE_VERBATIM + "\" (lifted from Clarification 8 section 4 with the bold "
                    "markers removed) and <DomainName> is the verbatim domain name from the same sentence. This "
                    "is minimal but it IS authorship, and the four domain sentences differ from one another by "
                    "exactly one word."
                ),
                "known_weakness": (
                    "The second factor carries one word of discriminative content, so this variant is close to "
                    "a 10-class arm wearing 40 labels. It also depends on the assistant-asserted "
                    "world->domain mapping, which has no basis anywhere in the pinned source."
                ),
                "titles": titles_dom,
                "definitions": defs_dom,
                "length_stats": stats_dom,
            },
        },

        "length_stats": stats_reg,

        "length_confound_statement": {
            "verdict": "CONFOUNDED. Arm D vs Arm A IS confounded by length, and it cannot be de-confounded by authoring.",
            "plain_statement": (
                "Arm D's definitions are systematically shorter than Arm A's. Per-code length matching was NOT "
                "attempted and MUST NOT be attempted: padding the compiled text to Arm A's length would require "
                "writing prose that is not in the pinned source, which would destroy the one property that makes "
                "Arm D worth running - that it is a mechanical compilation with no assistant authorship in its "
                "definition prose. A length-matched Arm D would be a different arm."
            ),
            "this_is_pre_registered_not_a_surprise": (
                "Pre-registration section 3.2 table, Arm D row, verbatim: 'compiled; will be short and cannot be "
                "matched without becoming a different source' -> 'covariate + equal-budget replicate'. Arm D is "
                "the ONE arm the frozen design exempts from per-code length matching. Arms E, F4 and F5 are "
                "matched to +/-10% per code; Arm D is not."
            ),
            "therefore_length_is_a_reported_covariate": True,
            "instruments_that_carry_the_length_burden": [
                "E8 - MANDATORY EQUAL-TOKEN-BUDGET REPLICATE: every arm truncated at sentence boundaries to the shortest arm's per-code budget and the whole experiment re-run. Any licensed contrast that does not survive with the same sign is reported LENGTH_CONFOUNDED / NOT LICENSED.",
                "Length as a concept-level covariate (n = 40): per-class accuracy regressed on per-class framed-definition token count; the E2 margin must survive with length in the model, reported with and without.",
                "F5 - the length-and-register-matched neutral-prose null, which answers directly whether text of this length and voice suffices.",
                "R6 in section 10.1, pre-committed: if Arm A does not survive the equal-token-budget replicate, 'length, not lineage, is the explanation' and the result is LENGTH_CONFOUNDED / NOT LICENSED.",
            ],
            "second_confound_carried_by_the_same_shortness": (
                "Rank. Pre-registration section 8.3: Arm D's prototypes are drawn from a pool of 10 Noetic "
                "sentences + 4 second-factor sentences, so after arm-internal centering the prototype matrix has "
                "at most ~13 degrees of freedom against Arm A's 39, and cannot represent Noetic x second-factor "
                "interaction at all. The rank-matched Arm A ablation is mandatory alongside E2; if A's advantage "
                "does not survive it, E2 is RANK_CONFOUNDED / NOT LICENSED. Length and rank are not independent "
                "here - both follow from the same compile rule - so neither control alone clears Arm D."
            ),
            "what_a_reader_may_NOT_conclude": (
                "An Arm A win over Arm D cannot be read as 'original wording beats compact CAS' until it "
                "survives BOTH the equal-token-budget replicate and the rank-matched ablation, AND the crosswalk "
                "is ratified. Absent those, the honest reading of A > D is 'longer, higher-rank anchors read out "
                "better', which is a statement about the readout, not about the ontology."
            ),
        },

        "honest_limitations": [
            "ASSISTANT_COMPILED at precedence tier 7 (second-lowest of eight). A win over Arm D is worth materially less than a win over an owner source; this is pre-registration section 11.2 finding 6, carried forward UNRESOLVED.",
            "The frozen compile rule is not executable as literally written: the pinned source contains no per-domain definitions. See BLOCKER_domain_definition_gap. This is a defect in the pre-registration's factual premise, not a licence to improvise, and it needs an owner decision (proposed B4a).",
            "The world->second-factor crosswalk is UNRATIFIED (B5). Every A-vs-D number stays stamped CONDITIONAL_ON_UNRATIFIED_CROSSWALK until an owner artifact is hashed into required_run_bindings[6] BEFORE capture.",
            "Arm D is not length-matched to Arm A and must not be. A-vs-D is length-confounded by construction and length is a reported covariate.",
            "Arm D is rank-capped at ~13 effective degrees of freedom against Arm A's 39 and cannot express Noetic x second-factor interaction, which is exactly what the bank's same-domain-noetic-cycle and same-noetic-domain-cycle pair_kinds probe.",
            "Token counts are unavailable: the tokenizer is not pinned until build item B8. All figures here are characters and whitespace words. The +/-10% matching tolerances elsewhere in the design are specified in TOKENS, so these character figures are indicative, not the final matching evidence.",
            "One scope judgement was made and is disclosed: the Register definition is taken as the definition line only, excluding the three Human/AI/Biological instantiation bullets. Taking the full block instead would make Arm D ~70% LONGER than Arm A rather than ~40% shorter.",
            "The S13 lexical-overlap covariate is computed here with an assistant-chosen stopword list and a lowercase-alphanumeric tokenizer. The S13 control manifest may specify a different tokenizer; if so, these numbers must be recomputed by that manifest's code and these are superseded.",
            "Bank-fixture agreement with the crosswalk is corroboration from a precedence tier-8 generated fixture. It cannot supply authority for a tier-1 claim and is not offered as such.",
        ],

        "s13_lexical_overlap_covariate_note": (
            "Per-code content-word Jaccard and max shared n-gram against the bank gloss are published here, "
            "before capture, for the primary and the alternative variant, as pre-registration section 2.4 "
            "requires for Arm D specifically and section 8 S13 requires for every arm."
        ),

        "FINDING_overlap_asymmetry_A_vs_D": {
            "severity": "load-bearing for criterion E2 - read before interpreting any A-minus-D number",
            "arm_D_bank_gloss_jaccard": {
                "mean": stats_reg["bank_gloss_overlap_S13"]["jaccard"]["mean"],
                "max": stats_reg["bank_gloss_overlap_S13"]["jaccard"]["max"],
                "max_shared_ngram_tokens": stats_reg["bank_gloss_overlap_S13"]["max_shared_ngram_tokens_max"],
            },
            "arm_A_bank_gloss_jaccard_from_prereg_4_3": {"min": 0.056, "mean": 0.234, "max": 0.538},
            "statement": (
                "Arm A shares roughly EIGHT TIMES more content-word vocabulary with the bank glosses than this "
                "compiled Arm D does. Arm D sits at essentially the same near-zero overlap position that the "
                "pre-registration predicts for Arm E ('Arm E will sit near zero by construction, so an "
                "uncontrolled A > E could be nothing but overlap', section 8 S13). The identical warning "
                "therefore applies to Arm D and to criterion E2, and the pre-registration does not say so "
                "anywhere - it reserves that warning for Arm E."
            ),
            "consequence": (
                "E2 (Arm A - Arm D, 8.4 bullet 2) inherits the same lexical-overlap confound the design already "
                "declared decisive for E6, the criterion it calls the weakest of the six. The S13 covariate "
                "survival requirement is not optional for E2; it is the difference between 'canonical wording "
                "carries more semantics' and 'canonical wording happens to share more words with the labels'. "
                "Recommend the write-up report E2 with the overlap covariate in the model as the PRIMARY figure, "
                "not as a secondary robustness check."
            ),
            "why_this_is_not_a_defect_in_the_payload": (
                "It is a direct consequence of the compile rule doing its job. Arm D's prose is CAS canon "
                "('An Idea the Mind has an affinity for and is attracted toward'), the bank glosses are "
                "independently authored TKS-flavoured role descriptions ('a truth or virtue that quiets the soul "
                "and draws it closer to its highest aim'). Low overlap is what a genuinely independent "
                "compilation looks like. Raising it would require writing toward the labels, which is "
                "contamination."
            ),
        },

        "FINDING_single_arm_a_lexical_bridge": {
            "code": "B4",
            "shared_5_token_ngram": "resonates with the Mind, its",
            "cause": (
                "The canonical ^4 Vibration definition is 'The degree to which an Idea resonates with the Mind, "
                "its impression.' and the owner's own Arm A B4 text happens to echo that phrasing. This is the "
                "ONLY code in the payload with a shared n-gram longer than 1 token against Arm A "
                "(39 of 40 codes: max 1 token)."
            ),
            "disposition": (
                "Disclosed, not removed. Removing it would mean editing canonical Clarification 1 text, which "
                "the compile rule forbids. It is one code out of forty and it biases A-vs-D toward finding the "
                "two arms MORE similar on B4, i.e. against Arm A on that code, not for it."
            ),
        },
    }


if __name__ == "__main__":
    main()
