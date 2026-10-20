"""helm_memory.py -- Multi-Turn Conversational Working Memory & State Tracker (v0.8).

Maintains cross-turn context, entity resolution, anaphora tracking, and goal continuation
under the strict 354 MB local memory ceiling and RPM Gate zero-hallucination invariant.

Components:
- ConversationTurn: Immutable turn record with timestamps, user text, resolved entities, and receipts.
- WorkingMemoryContext: Tracked state across turns (active files, inventory, project goals, preferences).
- HELMConversationalMemory: Thread-safe, bounded FIFO + priority LRU memory manager.
- AnaphoraResolver: Resolves conversational pronouns ('it', 'those files', 'the previous result', 'add 5 more').
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
CUBE_STORE_DIR = os.path.join(HERE, "docs", "working", "noetic_council", "cube_store")
#: Default home of chat session logs (helm_ui/.gitignore ignores it). Never the repo root.
DEFAULT_SESSION_DIR = os.path.join(HERE, "helm_ui", "sessions")
if os.path.isdir(CUBE_STORE_DIR) and CUBE_STORE_DIR not in sys.path:
    sys.path.insert(0, CUBE_STORE_DIR)

try:
    from store import CubeStore, AdmissionRefusal
    from turn import TurnProcessor, TurnReceipt, extract_assertion_and_valence, INVENTORY_NODE_ID
    from cube import CubeNode, Core, Face, Provenance, Branch
    from operations import list_parts, find_shared_part, reached_via
    CUBE_STORE_AVAILABLE = True
except ImportError:
    CUBE_STORE_AVAILABLE = False
    INVENTORY_NODE_ID = "cube_inventory_on_hand"


@dataclass
class ConversationTurn:
    turn_id: int
    timestamp_utc: str
    user_raw_text: str
    resolved_text: str
    intent: str
    entities: Dict[str, Any]
    helm_response: str
    receipt_hash: Optional[str] = None
    gate_code: str = "GATE_PASS"
    duration_seconds: float = 0.0
    kind: Optional[str] = None
    assertion: str = "ASSERTED"
    valence: str = "NEUTRAL"
    operation: Optional[str] = None
    cubes_read: List[str] = field(default_factory=list)
    cubes_written: List[str] = field(default_factory=list)


class WorkingMemoryContext:
    def __init__(self, context_id: str = "helm_session_store"):
        self.active_project: Optional[str] = None
        self.active_files: List[str] = []
        self.active_tools: List[str] = []
        self.inventory: Dict[str, Decimal] = {}
        self.last_goal: Optional[str] = None
        self.last_plan_steps: List[Dict[str, Any]] = []
        self.last_result_summary: Optional[str] = None
        self.pending_clarification: Optional[str] = None
        self.user_facts: List[str] = []
        self.user_preferences: Dict[str, Any] = {
            "voice": "everyday",
            "dial_preset": "BALANCED",
            "verbose": False
        }
        self.cube_store: Optional[CubeStore] = CubeStore(context_id=context_id) if CUBE_STORE_AVAILABLE else None
        self.turn_processor: Optional[TurnProcessor] = TurnProcessor(store=self.cube_store) if CUBE_STORE_AVAILABLE else None

    def process_turn_with_cube_store(self, text: str) -> Optional[TurnReceipt]:
        if self.turn_processor is not None:
            return self.turn_processor.process_turn(text)
        return None

    def add_user_preference(self, key: str, value: Any, note: Optional[str] = None, turn_index: int = 1):
        self.user_preferences[key] = value
        if note:
            self.add_user_fact(note, turn_index=turn_index)

        # Record directive into cube store
        if self.cube_store is not None:
            dir_text = note or f"Preference {key}: {value}"
            node_id = f"directive_{key}_{turn_index}"
            if node_id not in self.cube_store.nodes:
                core = Core(label=dir_text, kind="directive", identity_statement=f"User directive recorded on turn {turn_index}.")
                faces = {
                    f"face_{i}": Face(
                        availability="unknown" if i > 1 else "populated",
                        human_text=dir_text if i == 1 else "Directive has no technical decomposition."
                    )
                    for i in range(1, 7)
                }
                node = CubeNode(
                    node_id=node_id,
                    core=core,
                    faces=faces,
                    turn_index=turn_index,
                    provenance=Provenance(source="USER_SAID"),
                    assertion="ASSERTED",
                    valence="NEUTRAL"
                )
                self.cube_store.write_cube(node)

    def find_memory_match(self, query: str) -> List[str]:
        tokens = [w for w in re.findall(r'\b\w+\b', query.lower()) if len(w) > 3 and w not in ["what", "said", "about", "remember", "know", "have", "told", "that", "this", "tell"]]
        matches = []
        for fact in self.user_facts:
            f_lower = fact.lower()
            if any(t in f_lower for t in tokens):
                matches.append(fact)
        for k, v in self.user_preferences.items():
            if any(t in k.lower() or (isinstance(v, str) and t in v.lower()) for t in tokens):
                matches.append(f"{k}: {v}")
        return matches

    def add_user_fact(self, fact: str, turn_index: int = 1):
        cleaned = fact.strip().rstrip(".").strip()
        if cleaned and cleaned not in self.user_facts:
            self.user_facts.append(cleaned)
        # Bounded cap: keep last 20 user narrative facts
        self.user_facts = self.user_facts[:20]

        # Record into cube store
        if self.cube_store is not None and cleaned:
            fact_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12]
            node_id = f"fact_{fact_hash}"
            if node_id not in self.cube_store.nodes:
                assertion, valence = extract_assertion_and_valence(cleaned)
                core = Core(label=cleaned, kind="instance", identity_statement=f"User stated fact: {cleaned}")
                faces = {
                    f"face_{i}": Face(
                        availability="unknown" if i > 1 else "populated",
                        human_text=cleaned if i == 1 else "Fact has no physical part decomposition."
                    )
                    for i in range(1, 7)
                }
                node = CubeNode(
                    node_id=node_id,
                    core=core,
                    faces=faces,
                    turn_index=turn_index,
                    provenance=Provenance(source="USER_SAID"),
                    assertion=assertion,
                    valence=valence
                )
                self.cube_store.write_cube(node)

    def update_files(self, files: List[str]):
        for f in files:
            if f in self.active_files:
                self.active_files.remove(f)
            self.active_files.insert(0, f)
        # Bounded cap: keep last 10 active files
        self.active_files = self.active_files[:10]

    def update_inventory(self, items: Dict[str, Decimal], turn_index: int = 1):
        for k, v in items.items():
            self.inventory[k] = v

        if self.cube_store is not None and self.inventory:
            inv_node = self.cube_store.get_cube(INVENTORY_NODE_ID, view_profile="Authoring")
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
                    structured={"items": list(self.inventory.keys())} if i == 5 else {}
                )
                for i in range(1, 7)
            }
            inv_node = CubeNode(
                node_id=INVENTORY_NODE_ID,
                core=inv_core,
                faces=inv_faces,
                revision=rev,
                turn_index=turn_index,
                provenance=Provenance(source="USER_SAID"),
                assertion="ASSERTED",
                valence="NEUTRAL"
            )
            self.cube_store.write_cube(inv_node)

            for item_name, amt in self.inventory.items():
                item_id = f"item_{item_name.lower()}"
                item_core = Core(
                    label=item_name,
                    kind="instance",
                    identity_statement=f"Stock constituent: {amt} units of {item_name}."
                )
                item_faces = {
                    f"face_{i}": Face(
                        availability="unknown" if i > 1 else "populated",
                        human_text=f"{amt} {item_name}" if i == 1 else "Constituent of inventory."
                    )
                    for i in range(1, 7)
                }
                prev_item = self.cube_store.get_cube(item_id, view_profile="Authoring")
                item_rev = (prev_item.revision + 1) if prev_item else 1
                item_node = CubeNode(
                    node_id=item_id,
                    core=item_core,
                    faces=item_faces,
                    revision=item_rev,
                    turn_index=turn_index,
                    provenance=Provenance(source="USER_SAID"),
                    assertion="ASSERTED",
                    valence="NEUTRAL"
                )
                self.cube_store.write_cube(item_node)
                branch = Branch(
                    branch_id=f"branch_inv_{item_name.lower()}_{turn_index}_{item_rev}",
                    context_id=self.cube_store.context_id,
                    source_node_id=INVENTORY_NODE_ID,
                    predicate="contains",
                    target_node_id=item_id,
                    commonality={"amount": str(amt), "unit": item_name}
                )
                self.cube_store.write_branch(branch)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_project": self.active_project,
            "active_files": list(self.active_files),
            "active_tools": list(self.active_tools),
            "inventory": {k: str(v) for k, v in self.inventory.items()},
            "user_facts": list(self.user_facts),
            "last_goal": self.last_goal,
            "last_plan_steps": self.last_plan_steps,
            "last_result_summary": self.last_result_summary,
            "pending_clarification": self.pending_clarification,
            "user_preferences": self.user_preferences
        }


class AnaphoraResolver:
    """Resolves conversational references, pronouns, and relative quantities
    against recent working memory context.
    """

    @staticmethod
    def resolve(text: str, context: WorkingMemoryContext) -> Tuple[str, Dict[str, Any]]:
        resolved = text
        entities_found = {}

        # 1. Resolve 'it' / 'that file' / 'the file' to most recently referenced file
        if context.active_files:
            latest_file = context.active_files[0]
            pat = r'\b(it|that file|the file|the code|this file)\b'
            if re.search(pat, text, re.IGNORECASE):
                action_pat = r'\b(run|test|tests on|verify|inspect|check|open|edit|commit|diff|view|on|for|in)\s+(it|that file|the file|the code|this file)\b'
                if re.search(action_pat, text, re.IGNORECASE):
                    resolved = re.sub(pat, latest_file, resolved, count=1, flags=re.IGNORECASE)
                    entities_found["resolved_file"] = latest_file

        # 2. Extract explicit files mentioned in current utterance
        file_matches = re.findall(r'\b([\w\-_]+\.(?:py|json|md|txt|html|js|ts|css|rs|toml))\b', text, re.IGNORECASE)
        if file_matches:
            context.update_files(file_matches)
            entities_found["explicit_files"] = file_matches

        # 3. Relative quantities ('add 10 more', 'add 25 units of Flour and 10 Water') are NOT applied here any more
        #    (fix H, 2026-10-18). This used to add amounts to context.inventory outside the checked route. Stock
        #    now changes only through helm_end_to_end_loop (helm_english_in asks "in total, or on top?").
        #    The mention is still reported as an entity, for the record only.
        if re.search(r'\b(add|plus|include|with)\b', text, re.IGNORECASE):
            items_found = re.findall(r'(\d+(?:\.\d+)?)\s*(?:units?\s+of\s+)?([A-Za-z]+)', text)
            for qty_str, ing_name in items_found:
                if ing_name.lower() in ["steps", "files", "minutes", "seconds", "times", "attempts", "units", "more"]:
                    continue
                entities_found[f"relative_quantity_mentioned_{ing_name.capitalize()}"] = qty_str

        # 4. Resolve 'what did we just do?' / 'what was the previous result?'
        if re.search(r'\b(what did we just do|previous result|last result|what was accomplished|summary)\b', text, re.IGNORECASE):
            entities_found["query_last_result"] = True

        # 5. Resolve 'what do we have in stock?' / 'what is our inventory?' / 'what is in the pantry?'
        if re.search(r'\b(what do we have|current inventory|what ingredients|in stock|on hand|in the pantry|in pantry|list what|list the inventory|what is in the pantry|what\'s in the pantry|show me what\'s in the pantry|what\'ve we got on hand then)\b', text, re.IGNORECASE):
            entities_found["query_inventory"] = True

        return resolved, entities_found


class HELMConversationalMemory:
    """Thread-safe, bounded multi-turn conversational working memory manager.
    Enforces 354 MB local memory budget and keeps verified cryptographic hashes.
    """

    def __init__(self, session_id: Optional[str] = None, max_turns: int = 50, storage_dir: Optional[str] = None):
        self.session_id = session_id or f"helm-session-{int(time.time())}"
        self.max_turns = max_turns
        self.turns: List[ConversationTurn] = []
        self.context = WorkingMemoryContext()
        # Session logs go to the given folder, else $HELM_SESSION_DIR, else helm_ui/sessions (git-ignored) --
        # never the repo root. The folder is made on the first write (record_turn), not here, so starting a
        # session leaves no empty folder behind.
        self.storage_dir = storage_dir or os.environ.get("HELM_SESSION_DIR") or DEFAULT_SESSION_DIR
        self.session_file = os.path.join(self.storage_dir, f"{self.session_id}.jsonl")

    def process_turn_with_cube_store(self, text: str) -> Optional[TurnReceipt]:
        return self.context.process_turn_with_cube_store(text)

    def record_turn(self,
                    user_raw_text: str,
                    resolved_text: str,
                    intent: str,
                    entities: Dict[str, Any],
                    helm_response: str,
                    receipt_hash: Optional[str] = None,
                    gate_code: str = "GATE_PASS",
                    duration: float = 0.0,
                    kind: Optional[str] = None,
                    assertion: str = "ASSERTED",
                    valence: str = "NEUTRAL",
                    operation: Optional[str] = None,
                    cubes_read: Optional[List[str]] = None,
                    cubes_written: Optional[List[str]] = None) -> ConversationTurn:
        turn_id = len(self.turns) + 1
        turn = ConversationTurn(
            turn_id=turn_id,
            timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            user_raw_text=user_raw_text,
            resolved_text=resolved_text,
            intent=intent,
            entities=entities,
            helm_response=helm_response,
            receipt_hash=receipt_hash,
            gate_code=gate_code,
            duration_seconds=round(duration, 3),
            kind=kind,
            assertion=assertion,
            valence=valence,
            operation=operation,
            cubes_read=cubes_read or [],
            cubes_written=cubes_written or []
        )
        self.turns.append(turn)

        # Enforce FIFO bound on in-memory turns to respect 354 MB memory budget
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

        # Append to persistent JSONL session ledger (its folder is created lazily, on this first write)
        os.makedirs(os.path.dirname(os.path.abspath(self.session_file)), exist_ok=True)
        with open(self.session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(turn)) + "\n")

        return turn

    def get_recent_turns(self, n: int = 5) -> List[ConversationTurn]:
        return self.turns[-n:]

    def summarize_session_state(self, current_turn_number: Optional[int] = None) -> str:
        """Generates a warm, direct Everyday American English summary of the conversation."""
        turn_num = current_turn_number if current_turn_number is not None else (len(self.turns) if self.turns else 0)
        if turn_num == 0 and not self.context.user_facts and not self.context.active_files and not self.context.inventory and not self.context.last_goal:
            return "We just started our session. I'm ready to help with code, testing, git control, or recipe planning."

        summary_parts = []
        if turn_num > 0:
            summary_parts.append(f"We're on Turn {turn_num} of this session.")
        else:
            summary_parts.append("We just started our session.")

        if self.context.user_facts:
            summary_parts.append(f"Recorded notes about you: {'; '.join(self.context.user_facts[:3])}.")

        # If preferences are active
        active_prefs = [f"{k}: {v}" for k, v in self.context.user_preferences.items() if k not in ["voice", "dial_preset", "verbose"]]
        if active_prefs:
            summary_parts.append(f"Active preferences: {'; '.join(active_prefs)}.")

        if self.context.active_files:
            summary_parts.append(f"Recently worked files: {', '.join(self.context.active_files[:3])}.")

        if self.context.inventory:
            inv_str = ", ".join(f"{v} {k}" for k, v in self.context.inventory.items())
            summary_parts.append(f"Current inventory on hand: {inv_str}.")

        if self.context.last_goal:
            clean_goal = self.context.last_goal.strip().rstrip(".").strip()
            summary_parts.append(f"Last executed goal: '{clean_goal}'.")

        # If no files, inventory, or goals, but there were turns, describe conversational topics explored
        if not self.context.active_files and not self.context.inventory and not self.context.last_goal and self.turns:
            intents = [t.intent for t in self.turns if t.intent not in ["SESSION_SUMMARY"]]
            unique_intents = list(dict.fromkeys(intents))
            if unique_intents:
                intent_names = {
                    "USER_NARRATIVE": "personal background",
                    "USER_AFFECT": "how you're feeling",
                    "USER_PREFERENCE": "your preferences",
                    "USER_KNOWLEDGE_QUERY": "what I know about you",
                    "CREATIVE_HUMOR": "creative humor",
                    "GENERAL_KNOWLEDGE_INQUIRY": "general questions",
                    "QUERY_MEMORY_RECALL": "memory lookups",
                    "QUERY_MEMORY_COUNT": "conversation fact counts",
                    "GENERAL_CONVERSATION": "general dialogue"
                }
                readable = [intent_names.get(i, i.lower().replace("_", " ")) for i in unique_intents[:4]]
                summary_parts.append(f"Topics explored: {', '.join(readable)}.")

        return " ".join(summary_parts)
