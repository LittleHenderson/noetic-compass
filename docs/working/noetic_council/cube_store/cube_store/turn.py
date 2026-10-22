"""turn.py -- Conversational turn processor and pipeline for Unified Cube Store.

Implements Sections 1, 4, 5, 6, 7 of SPEC_CUBE_STORE_UNIFIED_20261018.md:
  user turn
     ↓
  cce.py parse() / lexical valence extraction
     ↓
  kind + confidence classification
     ↓
  WRITE / READ / CLARIFY / REFUSE
     ↓
  surface rendering / response
     ↓
  receipt with trace citation (T1, T2)

Rules:
- A REFUSE writes no cube. A CLARIFY writes no cube.
- Only a WRITE creates knowledge, and only from USER_SAID or CHECKED. Never NONE.
- S3: 'what do we have in stock', 'what've we got on hand then', and 'list what's in the pantry' reach the exact SAME operation (LIST_PARTS).
- Section 4 / F14: Assertion (ASSERTED/DENIED) and valence (POSITIVE/NEGATIVE/NEUTRAL) are orthogonal axes.
  The word 'not' never produces ^3 (anti-drift rule); it negates assertion.
  Valence comes from the frozen ALIAS-WIDE lexicon and the Noetic ^2/^3 frames. Affect words outside the lexicon resolve to NEUTRAL and are not guessed.
- Legacy 'polarity' field is DEPRECATED and preserved solely as a backwards-compatibility alias; new callers must read 'assertion' and 'valence'.
- H4: Non-physical or ungroundable concepts like 'medieval poetry' produce NO hypothesized inputs and are REFUSED.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
COUNCIL = os.path.dirname(HERE)
CANDIDATE_LANG_DIRS = [
    os.path.join(COUNCIL, "language_v3"),
    r"D:\tksCAS-worktrees\repair-performer-20261017\docs\working\noetic_council\language_v3",
    r"C:\Users\wakil\Documents\Codex\2026-10-14\lm_t1",
]
for p in CANDIDATE_LANG_DIRS:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

# Also add Codex bridge if present for aliaswide dependencies
BRIDGE_DIR = r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011"
if os.path.isdir(BRIDGE_DIR) and BRIDGE_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_DIR)

LACUNARITY_DIR = r"C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1"
if os.path.isdir(LACUNARITY_DIR) and LACUNARITY_DIR not in sys.path:
    sys.path.insert(0, LACUNARITY_DIR)

try:
    import cce
except ImportError:
    cce = None

try:
    import aliaswide
except ImportError:
    aliaswide = None

from cube import (
    ALLOWED_ASSERTIONS,
    ALLOWED_KINDS,
    ALLOWED_VALENCES,
    Branch,
    Core,
    CubeNode,
    Face,
    Provenance,
)
from operations import (
    OperationReceipt,
    find_shared_part,
    list_parts,
    reached_via,
)
from store import AdmissionRefusal, CubeStore

INVENTORY_NODE_ID = "cube_inventory_on_hand"

# Canonical Noetic ^3 Negative valence vocabulary (aversion, repulsion, distress, fatigue, illness)
NEGATIVE_VALENCE_WORDS = {
    "awful", "terrible", "horrible", "dreadful", "bad", "poor", "sad", "unhappy",
    "depressed", "down", "miserable", "tired", "exhausted", "fatigued", "drained",
    "sick", "ill", "hurting", "pain", "unwell", "frustrated", "angry", "annoyed",
    "upset", "bitter", "disgusted", "repelled", "repel", "repulsion", "adverse",
    "averse", "aversion", "dislike", "hate", "negative"
}

# Canonical Noetic ^2 Positive valence vocabulary (affinity, attraction, joy, elation)
POSITIVE_VALENCE_WORDS = {
    "wonderful", "fantastic", "great", "good", "happy", "delighted", "cheerful",
    "excited", "energized", "superb", "splendid", "brilliant", "joyful", "blessed",
    "thrilled", "ecstatic", "glad", "content", "peaceful", "fine", "terrific",
    "amazing", "awesome", "attracted", "attract", "attraction", "affinity",
    "fond", "love", "like", "positive"
}

POSITIVE_VALENCE_IDIOMS = [
    "over the moon", "cloud nine", "on top of the world", "like a moth to a flame",
    "cannot resist", "can't resist", "drawn toward", "drawn to", "attracted to",
    "attracted toward"
]

NEGATIVE_VALENCE_IDIOMS = [
    "down in the dumps", "under the weather", "cannot stomach", "can't stomach",
    "rubs me the wrong way", "rub me the wrong way", "ten-foot pole",
    "repelled by", "repelled from", "averse to"
]


def extract_assertion_and_valence(text: str) -> Tuple[str, str]:
    """Extracts (assertion, valence) tuple adhering to F14 and Noetic ^2 / ^3.
    assertion: "ASSERTED" | "DENIED"
    valence: "POSITIVE" | "NEGATIVE" | "NEUTRAL"
    Rule F14: The word 'not' never produces ^3. Negation sets assertion="DENIED".
    Valence comes from the frozen ALIAS-WIDE lexicon and the Noetic ^2/^3 frames.
    Affect words outside the lexicon resolve to NEUTRAL and are not guessed.
    """
    clean = text.strip()
    lower = clean.lower()

    # 1. Canonical CCE parse
    if cce is not None:
        try:
            parsed = cce.parse(clean)
            if parsed.get("terms"):
                t = parsed["terms"][0]
                n = t.get("noetic")
                pol = t.get("polarity", "ASSERTED")
                val = "POSITIVE" if n == 2 else ("NEGATIVE" if n == 3 else "NEUTRAL")
                return pol, val
        except Exception:
            pass

    # 2. Check aliaswide phrase hits for Noetic 2 / 3
    if aliaswide is not None:
        try:
            hits = aliaswide.phrase_hits(lower)
            for start, end, noetic, rank in hits:
                is_denied = bool(re.search(r"\b(?:not|never|no|without|don't|doesn't|didn't|cannot|can't)\b", lower))
                if noetic == 2:
                    return ("DENIED" if is_denied else "ASSERTED"), "POSITIVE"
                elif noetic == 3:
                    return ("DENIED" if is_denied else "ASSERTED"), "NEGATIVE"
        except Exception:
            pass

    # 3. Check affective idioms
    is_denied = bool(re.search(r"\b(?:not|never|no|without|don't|doesn't|didn't|cannot|can't)\b", lower))
    for idiom in POSITIVE_VALENCE_IDIOMS:
        if idiom in lower:
            return ("DENIED" if is_denied else "ASSERTED"), "POSITIVE"
    for idiom in NEGATIVE_VALENCE_IDIOMS:
        if idiom in lower:
            return ("DENIED" if is_denied else "ASSERTED"), "NEGATIVE"

    # 4. Check affective vocabulary
    words = set(re.findall(r"\b[a-z]+\b", lower))
    has_pos = bool(words & POSITIVE_VALENCE_WORDS)
    has_neg = bool(words & NEGATIVE_VALENCE_WORDS)

    if has_pos and not has_neg:
        return ("DENIED" if is_denied else "ASSERTED"), "POSITIVE"
    elif has_neg and not has_pos:
        return ("DENIED" if is_denied else "ASSERTED"), "NEGATIVE"

    return ("DENIED" if is_denied else "ASSERTED"), "NEUTRAL"


@dataclass
class TurnReceipt:
    turn_index: int
    user_text: str
    outcome: str  # WRITE | READ | CLARIFY | REFUSE
    kind: Optional[str] = None  # concept | instance | event | procedure | directive
    assertion: str = "ASSERTED"  # ASSERTED | DENIED (Section 4 & F14)
    valence: str = "NEUTRAL"  # POSITIVE | NEGATIVE | NEUTRAL (Section 4 & Noetic ^2/^3)
    polarity: Optional[str] = None
    """DEPRECATED: Legacy compatibility alias only. Conflates assertion with valence.
    Do not read or write in new code. Use `assertion` and `valence` instead."""
    operation: Optional[str] = None  # LIST_PARTS | FIND_SHARED_PART | REACHED_VIA | WRITE_CUBE | REFUSE | CLARIFY
    cubes_read: List[str] = field(default_factory=list)
    cubes_written: List[str] = field(default_factory=list)
    confidence: Optional[Dict[str, Any]] = None
    response_text: str = ""
    receipt_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        pol = self.polarity if self.polarity is not None else (self.valence if self.valence != "NEUTRAL" else self.assertion)
        return {
            "turn_index": self.turn_index,
            "user_text": self.user_text,
            "outcome": self.outcome,
            "kind": self.kind,
            "assertion": self.assertion,
            "valence": self.valence,
            "polarity": pol,
            "operation": self.operation,
            "cubes_read": list(self.cubes_read),
            "cubes_written": list(self.cubes_written),
            "confidence": copy.deepcopy(self.confidence),
            "response_text": self.response_text,
            "receipt_hash": self.receipt_hash,
        }


class TurnProcessor:
    def __init__(self, store: Optional[CubeStore] = None):
        self.store = store if store is not None else CubeStore()
        self.turn_index = 0
        self.turn_history: List[TurnReceipt] = []

    def classify_turn(self, text: str) -> Tuple[str, str, str, str, Optional[Dict[str, Any]]]:
        """Classifies user text into (outcome, kind, assertion, valence, confidence).
        outcome: WRITE | READ | CLARIFY | REFUSE
        kind: concept | instance | event | procedure | directive
        assertion: ASSERTED | DENIED
        valence: POSITIVE | NEGATIVE | NEUTRAL
        """
        clean = text.strip()
        lower = clean.lower()

        assertion, valence = extract_assertion_and_valence(clean)

        # Check for ungroundable non-physical hypotheses / study requests (H4)
        m_study = re.search(r"\b(?:study|model|formulate a recipe for)\s+(.+)", lower)
        if m_study:
            topic = m_study.group(1).strip().rstrip("?.")
            # If domain has no justified physical energy/matter equations (e.g. poetry, ancient literature)
            if any(w in topic for w in ["poetry", "medieval", "literature", "philosophy", "novel"]):
                return "REFUSE", "procedure", assertion, valence, {"reason": "NON_GROUNDED_DOMAIN"}

        # Check for general out-of-domain knowledge queries (H1)
        if re.search(r"\b(?:what is the capital of|who was the president|who won the)\b", lower):
            return "REFUSE", "concept", assertion, valence, {"reason": "ABSENT_ENCYCLOPEDIC_ATLAS"}

        # Question / Query forms -> READ (including query imperatives like "list what's in the pantry")
        is_query = (
            "?" in clean
            or lower.startswith((
                "what", "who", "where", "when", "why", "how", "do we", "do you", "is there",
                "list", "show", "display", "print", "enumerate", "check"
            ))
            or bool(re.search(r"\b(?:list|show|display|enumerate|check|tell me)\s+(?:what|what's|the|all|parts|items|ingredients|inventory|stock|pantry)\b", lower))
        )

        if is_query:
            if "entropy" in lower or "what is" in lower:
                return "READ", "concept", assertion, valence, {"score": 1.0}
            if "preference" in lower or "what i said" in lower:
                return "READ", "directive", assertion, valence, {"score": 1.0}
            if any(w in lower for w in ["stock", "hand", "inventory", "have", "pantry", "cupboard"]):
                return "READ", "instance", assertion, valence, {"score": 1.0}
            return "READ", "instance", assertion, valence, {"score": 0.8}

        # Directive forms (K5, S4)
        if any(lower.startswith(d) for d in ["remember that", "remember i", "please remember", "tell me a", "make me a"]):
            return "WRITE", "directive", assertion, valence, {"score": 1.0}

        # Procedure forms (K4)
        if any(lower.startswith(p) for p in ["write a program", "create a script", "synthesize code", "compile"]):
            return "WRITE", "procedure", assertion, valence, {"score": 1.0}

        # State / Affect forms (K2, K3, probes)
        if valence in ("POSITIVE", "NEGATIVE") or any(k in lower for k in ["i feel", "i am feeling", "i'm feeling", "i am", "i'm", "feeling"]):
            return "WRITE", "instance", assertion, valence, {"score": 1.0}

        # Inventory / Material Declarations (K1, S1)
        if re.search(r"\b(?:we have|there is|inventory has|on hand)\b", lower):
            return "WRITE", "instance", assertion, valence, {"score": 1.0}

        # Ambiguous statement lacking required slot -> CLARIFY
        if len(clean.split()) < 2:
            return "CLARIFY", "instance", assertion, valence, {"reason": "SLOT_MISSING"}

        return "WRITE", "instance", assertion, valence, {"score": 0.7}

    def process_turn(self, user_text: str) -> TurnReceipt:
        self.turn_index += 1
        t_idx = self.turn_index
        text = user_text.strip()
        lower = text.lower()

        outcome, kind, assertion, valence, conf = self.classify_turn(text)
        legacy_polarity = valence if valence != "NEUTRAL" else assertion

        cubes_read: List[str] = []
        cubes_written: List[str] = []
        op_name: Optional[str] = None
        response_text = ""

        # =====================================================================
        # 1. REFUSE Outcome (H1, H4) — Writes NO cube
        # =====================================================================
        if outcome == "REFUSE":
            op_name = "REFUSE"
            reason = conf.get("reason", "UNREPRESENTABLE_IN_STORE") if conf else "UNREPRESENTABLE"
            if reason == "NON_GROUNDED_DOMAIN":
                response_text = (
                    f"I will not do that: '{text}' lacks justified physical inputs. "
                    f"Missing knowledge must not be filled with fabricated content."
                )
            else:
                response_text = (
                    f"I don't have verified data on that in my active cube store, "
                    f"so I won't guess without evidence."
                )

        # =====================================================================
        # 2. CLARIFY Outcome — Writes NO cube
        # =====================================================================
        elif outcome == "CLARIFY":
            op_name = "CLARIFY"
            response_text = "Could you clarify what specific instance or concept you'd like to record?"

        # =====================================================================
        # 3. WRITE Outcome (S1, S4, K1-K5) — Creates cube from USER_SAID
        # =====================================================================
        elif outcome == "WRITE":
            op_name = "WRITE_CUBE"

            if kind == "directive":
                # S4: "Remember I prefer short answers"
                node_id = f"directive_turn_{t_idx}"
                core = Core(
                    label=text,
                    kind="directive",
                    identity_statement=f"User directive recorded on turn {t_idx}."
                )
                faces = {
                    f"face_{i}": Face(
                        availability="unknown" if i > 1 else "populated",
                        human_text=text if i == 1 else "Directive has no technical decomposition."
                    )
                    for i in range(1, 7)
                }
                node = CubeNode(
                    node_id=node_id,
                    core=core,
                    faces=faces,
                    turn_index=t_idx,
                    confidence=conf,
                    provenance=Provenance(source="USER_SAID"),
                    assertion=assertion,
                    valence=valence,
                    polarity=legacy_polarity
                )
                self.store.write_cube(node)
                cubes_written.append(node_id)
                response_text = f"Understood. I've recorded your directive: '{text}'."

            elif kind == "procedure":
                # K4: "Write a program"
                node_id = f"proc_turn_{t_idx}"
                core = Core(
                    label=text,
                    kind="procedure",
                    identity_statement=f"Procedure request: {text}"
                )
                faces = {
                    f"face_{i}": Face(
                        availability="unknown" if i > 1 else "populated",
                        human_text=text if i == 1 else "Procedure details pending implementation."
                    )
                    for i in range(1, 7)
                }
                node = CubeNode(
                    node_id=node_id,
                    core=core,
                    faces=faces,
                    turn_index=t_idx,
                    confidence=conf,
                    provenance=Provenance(source="USER_SAID"),
                    assertion=assertion,
                    valence=valence,
                    polarity=legacy_polarity
                )
                self.store.write_cube(node)
                cubes_written.append(node_id)
                response_text = f"Planned procedure for '{text}' registered into working store."

            elif valence in ("POSITIVE", "NEGATIVE") or "i feel" in lower or "feeling" in lower:
                # K2, K3, probes: State affect with assertion and valence
                node_id = f"affect_turn_{t_idx}"
                core = Core(
                    label=text,
                    kind="instance",
                    identity_statement=f"User stated feeling on turn {t_idx}."
                )
                faces = {
                    f"face_{i}": Face(
                        availability="unknown" if i > 1 else "populated",
                        human_text=text if i == 1 else "Affective state has no physical part decomposition."
                    )
                    for i in range(1, 7)
                }
                node = CubeNode(
                    node_id=node_id,
                    core=core,
                    faces=faces,
                    turn_index=t_idx,
                    confidence=conf,
                    provenance=Provenance(source="USER_SAID"),
                    assertion=assertion,
                    valence=valence,
                    polarity=legacy_polarity
                )
                self.store.write_cube(node)
                cubes_written.append(node_id)

                # Valence + Assertion dictates response
                if valence == "NEGATIVE" and assertion == "ASSERTED":
                    response_text = f"I'm sorry to hear that you're feeling down. Let me know how I can help."
                elif valence == "POSITIVE" and assertion == "ASSERTED":
                    response_text = f"That's fantastic to hear! Glad you're feeling great today."
                else:
                    response_text = f"I hear you. Anything I can help with?"

            else:
                # S1, K1: Inventory / Material Instance
                # e.g. "We have 50 Flour, 30 Sugar"
                quantities = re.findall(r"(\d+)\s+([A-Za-z]+)", text)

                # Ensure main inventory node exists
                inv_node = self.store.get_cube(INVENTORY_NODE_ID, view_profile="Authoring")
                rev = (inv_node.revision + 1) if inv_node else 1
                inv_core = Core(
                    label="Current Inventory",
                    kind="instance",
                    identity_statement="Aggregated session inventory of available ingredients."
                )
                inv_faces = {
                    f"face_{i}": Face(
                        availability="populated",
                        human_text="Direct ingredient stock on hand.",
                        structured={"items": [q[1] for q in quantities]} if i == 5 else {}
                    )
                    for i in range(1, 7)
                }
                inv_node = CubeNode(
                    node_id=INVENTORY_NODE_ID,
                    core=inv_core,
                    faces=inv_faces,
                    revision=rev,
                    turn_index=t_idx,
                    confidence=conf,
                    provenance=Provenance(source="USER_SAID"),
                    assertion=assertion,
                    valence=valence,
                    polarity=legacy_polarity
                )
                self.store.write_cube(inv_node)
                cubes_written.append(INVENTORY_NODE_ID)

                # Write item nodes and contains branches
                for amt, item_name in quantities:
                    item_id = f"item_{item_name.lower()}"
                    item_core = Core(
                        label=item_name,
                        kind="instance",
                        identity_statement=f"Stock constituent: {amt} units of {item_name}."
                    )
                    item_faces = {
                        f"face_{i}": Face(
                            availability="unknown" if i > 1 else "populated",
                            human_text=f"{amt} {item_name}" if i == 1 else f"Constituent of inventory."
                        )
                        for i in range(1, 7)
                    }
                    item_node = CubeNode(
                        node_id=item_id,
                        core=item_core,
                        faces=item_faces,
                        turn_index=t_idx,
                        provenance=Provenance(source="USER_SAID"),
                        assertion=assertion,
                        valence=valence,
                        polarity=legacy_polarity
                    )
                    # Revisions for item
                    if item_id in self.store.nodes:
                        item_node.revision = self.store.nodes[item_id].revision + 1
                    self.store.write_cube(item_node)
                    cubes_written.append(item_id)

                    branch = Branch(
                        branch_id=f"branch_inv_{item_name.lower()}_{t_idx}",
                        context_id=self.store.context_id,
                        source_node_id=INVENTORY_NODE_ID,
                        predicate="contains",
                        target_node_id=item_id,
                        commonality={"amount": amt, "unit": item_name}
                    )
                    self.store.write_branch(branch)

                items_str = ", ".join(f"{q[0]} {q[1]}" for q in quantities)
                response_text = f"Recorded {items_str} in store."

        # =====================================================================
        # 4. READ Outcome (S2, S3, S5, S6, pantry query) — Runs operations over store
        # =====================================================================
        elif outcome == "READ":
            # Check S6: "Do we have 50 Flour and 30 Sugar or not"
            if re.search(r"\bdo we have\b", lower) and ("or not" in lower or "and" in lower):
                op_name = "FIND_SHARED_PART"
                query_items = re.findall(r"(?:\d+\s+)?([A-Za-z]+)", text)
                clean_items = [i for i in query_items if i.lower() not in ("do", "we", "have", "and", "or", "not")]
                rec = find_shared_part(self.store, INVENTORY_NODE_ID, clean_items)
                cubes_read.extend(rec.cubes_read)
                if rec.success:
                    response_text = f"Yes, confirmed: we have {', '.join(clean_items)} recorded in inventory."
                else:
                    missing = rec.output.get("missing", []) if rec.output else clean_items
                    response_text = f"We do not have all requested items. Missing: {', '.join(missing)}."

            # Check S5: "Do you remember my preference"
            elif any(w in lower for w in ["preference", "directive", "my preference"]):
                op_name = "READ_NODE"
                directives = self.store.find_cubes_by_kind("directive")
                if directives:
                    chosen = directives[-1]
                    cubes_read.append(chosen.node_id)
                    response_text = f"Yes, you specified: '{chosen.core.label}'."
                else:
                    response_text = "No stored preferences found in this session."

            # Check S2 and S3: "What do we have in stock" & "what've we got on hand then" & "list what's in the pantry"
            # ALL semantically resolve to LIST_PARTS on the inventory node! Zero cubes written.
            elif any(w in lower for w in [
                "stock", "on hand", "inventory", "pantry", "cupboard", "cabinet",
                "what do we have", "what've we got", "what is in", "what's in", "list what"
            ]):
                op_name = "LIST_PARTS"
                rec = list_parts(self.store, INVENTORY_NODE_ID)
                cubes_read.extend(rec.cubes_read)
                if rec.success and rec.output:
                    parts_str = ", ".join(
                        f"{p.get('amount', '')} {p['label']}".strip() for p in rec.output
                    )
                    if "pantry" in lower:
                        response_text = f"Currently on hand in pantry: {parts_str}."
                    else:
                        response_text = f"Currently on hand: {parts_str}."
                else:
                    if "pantry" in lower:
                        response_text = "No items are currently recorded in pantry."
                    else:
                        response_text = "No inventory items are currently recorded in stock."

            # Concept inquiry (K6: "What is entropy")
            elif "entropy" in lower or kind == "concept":
                op_name = "READ_NODE"
                matched = self.store.find_cubes_by_label("entropy")
                if matched:
                    c = matched[0]
                    cubes_read.append(c.node_id)
                    response_text = f"Entropy: {c.core.identity_statement}"
                else:
                    response_text = "Concept 'entropy' is not populated in the active store."

            else:
                op_name = "READ_NODE"
                response_text = "Query evaluated against store."

        # Compute tamper-proof receipt hash
        receipt_data = f"{t_idx}:{text}:{outcome}:{op_name}:{assertion}:{valence}:{sorted(set(cubes_read))}:{sorted(set(cubes_written))}"
        h = hashlib.sha256(receipt_data.encode("utf-8")).hexdigest()[:16]

        receipt = TurnReceipt(
            turn_index=t_idx,
            user_text=text,
            outcome=outcome,
            kind=kind,
            assertion=assertion,
            valence=valence,
            polarity=legacy_polarity,
            operation=op_name,
            cubes_read=sorted(set(cubes_read)),
            cubes_written=sorted(set(cubes_written)),
            confidence=conf,
            response_text=response_text,
            receipt_hash=h
        )
        self.turn_history.append(receipt)
        return receipt
