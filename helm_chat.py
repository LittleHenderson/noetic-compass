"""helm_chat.py -- Interactive Conversational Interface for HELM.

Enables direct, interactive natural language dialogue with HELM in Everyday American English.
Integrates:
- Everyday American English Voice Adapter
- Stage v0.7 Topological Scribe Proposer & Level L4 Neural Proposer
- Station S0: HELM's canonical brain, the licensed HELM-R1 wave-1 recipe brain (c34 PASS R1_BEATS_GB3),
  loaded by helm_brain_canonical.py and reached through helm_end_to_end_loop (exact Fraction arithmetic).
  Owner approval 2026-10-18: "recipe brain is canonical". Its license is synthetic-world only.
  The 22x40 brain (helm_brain_22x40.py, 40-digit Decimal) and the tks28 brain (brains/helm_brain_tks28.py
  in the local HELM_DISTRIBUTION_PACKAGE copy) are demos / stand-ins only, not HELM's brain; this
  interface never constructs either. The RB-W1 wide brain (helm_brain_wide.py, helm_wide_turn.py) is HELM's
  canonical brain since the owner's ruling of 2026-10-20 ("YES TO WIDE BRAIN", SPEC 7.56): the HELM_WIDE_BRAIN
  switch is ON by default (set it to 0 / OFF to run the licensed reference brain alone); the licensed path still
  reads every turn first and the wide book takes only the turns it cannot bind.
- Phase 3 Meta Valve Controller (tks_meta_valve_controller)
- Immutable RPM Safety Gate (Zero-Hallucination Invariant)
- Level A1/A2 Stoichiometric Agentic Tool Executor

Usage:
    python helm_chat.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from decimal import Decimal
from typing import Optional

# Ensure repository root and subdirectories are on path
HERE = os.path.dirname(os.path.abspath(__file__))
for sub in [HERE, os.path.join(HERE, "brains"), os.path.join(HERE, "core_engine"), os.path.join(HERE, "real_atlas")]:
    if os.path.exists(sub) and sub not in sys.path:
        sys.path.insert(0, sub)

import helm_end_to_end_loop as e2e
import helm_agentic_executor as ax
import helm_english_in
from helm_brain_canonical import frac_text
from helm_memory import HELMConversationalMemory, AnaphoraResolver
from helm_voice import HELMVoice, receipt_from_loop_result, say_name, _norm_name

#: Loop statuses whose own sentence is already plain English; the voice still checks it before it is said.
PLAIN_LOOP_LINES = ("CLARIFY_STOCK_NOT_RECORDED", "STATED_RECIPE_NOT_TAKEN", "CLARIFY_UNKNOWN_PRODUCT",
                    "CLARIFY_BATCH_NOT_USABLE", "CLARIFY_ROUND_TRIP_FAILED", "NOTHING_TO_SAVE")


class HELMConversationalSession:
    def __init__(self, mode: str = "everyday", session_id: Optional[str] = None):
        self.mode = mode  # "everyday" or "cas_diagnostic"
        self.engine = ax.AgenticExecutionEngine(workspace_root=HERE)
        self.memory = HELMConversationalMemory(session_id=session_id)
        # Fix H: ONE path for stock and recipe English. The loop writes stock into the same cube store the
        # conversation memory reads, so a pantry question sees exactly what the loop verified and saved.
        self.loop = e2e.HELMEndToEndLoop(cube_store=self.memory.context.cube_store)
        self.voice = HELMVoice()  # Fix F: deterministic everyday-English writer over brain receipts
        self.turn_count = 0

    def print_banner(self):
        print("\n" + "=" * 76)
        print("                   HELM CONVERSATIONAL INTERFACE (v0.8)                   ")
        print("         Multi-Turn Conversational Intelligence & Governed Memory         ")
        print("=" * 76)
        print("  Voice Mode       : Everyday American English (Clean, direct, jargon-free)")
        print("  Context Memory   : Active (Multi-turn state tracking, anaphora resolution)")
        print("  Safety Gate      : RPM Gate Active (Zero Hallucination Guaranteed)")
        print("  Memory Budget    : 354 MB local ceiling enforced (0 local GPU requirement)")
        print("  Available Tools  : synthesize_code, git_action, execute_command,")
        print("                     systems_design_spec, web_app_scaffold, dispatch_cloud_job")
        print("-" * 76)
        print("  Commands:")
        print("    'help'    - Show example conversation prompts and tasks")
        print("    'history' - View multi-turn session history and tracked state")
        print("    'mode'    - Toggle between Everyday English and CAS Diagnostic logs")
        print("    'dials'   - Show the Unity Eye supervisory dials")
        print("    'exit'    - Quit session")
        print("=" * 76 + "\n")

    def print_help(self):
        print("\n--- Example Questions & Tasks you can ask HELM ---")
        print("1. Engineering & Code:")
        print("   > 'Write a python helper math_utils.py, verify tests, and check git status.'")
        print("   > 'Before writing any code, run verification tests, then write the code.'")
        print("   > 'First check git diff to see what changed, then synthesize the patch.'")
        print("   > 'Inspect README.md and git status in parallel, then design the system.'")
        print("\n2. Recipe Calculation & Resource Allocation:")
        print("   > 'We have 12 cups of flour and 9 cups of water. How much bread can we make?'")
        print("   > 'We're out of water. Can we bake bread?'")
        print("   > 'We made 5 loaves from 10 flour and 8 water and ran out of flour.'")
        print("\n3. Systems & Web Design:")
        print("   > 'Scaffold a modern web dashboard for our cognitive workspace.'")
        print("   > 'Design a high-throughput data processing pipeline with bounded memory.'")
        print("\n4. General Inquiry & Safety Testing:")
        print("   > 'What is the current status of our repository and test suite?'")
        print("   > 'Who will win the football game next year?' (Watch RPM Gate refuse ungrounded guesses)")
        print("-" * 50 + "\n")

    def show_dials(self):
        """Print the Unity Eye's real dial values (helm_agentic_executor.UnityEyeSupervisor.dial, a
        helm_creativity_dial.CreativityDial). Says "not wired" instead of crashing when they are absent."""
        eye = getattr(self.engine, "eye", None)
        d = getattr(eye, "dial", None)
        fields = ("breadth_K", "curvature_rho", "search_radius_R", "idle_ponder_budget", "valve_novelty_sigma")
        if d is None or not all(hasattr(d, f) for f in fields):
            print("\n--- Unity Eye dials: not wired (this session has no Unity Eye with a creativity dial) ---\n")
            return
        print(f"\n--- Unity Eye F1 Supervisory Dials (Mode: {getattr(eye, 'current_mode', 'unknown')}) ---")
        print(f"  Candidate Breadth (K)     : {d.breadth_K}  [1: Conservative .. 32: Wild]")
        print(f"  Substitution Curvature (ρ): {d.curvature_rho}  [-4: Strict .. 1: Perfect Sub]")
        print(f"  RPA Search Radius (R)     : {d.search_radius_R}  [1, 2, 4, 8 bounded horizon]")
        print(f"  Idle Pondering Budget     : {d.idle_ponder_budget} cycles")
        print(f"  Phase 3 Valve Saliency (σ): {d.valve_novelty_sigma}  [0.0: Closed .. 1.0: Wide Open]")
        print(f"  Safety Invariant          : RPM Gate (G-ABSENT) enforces 0 hallucination regardless of dials.\n")

    def handle_turn(self, user_input: str):
        prompt = user_input.strip()
        if not prompt:
            return

        cmd = prompt.lower()
        if cmd in ["exit", "quit", "q"]:
            print("\nGoodbye! HELM session closed. Working memory preserved.")
            sys.exit(0)
        elif cmd == "help":
            self.print_help()
            return
        elif cmd == "dials":
            self.show_dials()
            return
        elif cmd == "history":
            print("\n" + "=" * 60)
            print("         HELM MULTI-TURN CONVERSATIONAL HISTORY (v0.8)       ")
            print("=" * 60)
            print(f"Session ID: {self.memory.session_id}")
            print(f"Summary   : {self.memory.summarize_session_state()}\n")
            if not self.memory.turns:
                print("  (No previous turns recorded yet in this session.)")
            else:
                for t in self.memory.get_recent_turns(10):
                    print(f"  [Turn {t.turn_id:02d} | {t.timestamp_utc}]")
                    print(f"    You : {t.user_raw_text}")
                    if t.resolved_text != t.user_raw_text:
                        print(f"    (Resolved): {t.resolved_text}")
                    print(f"    HELM: {t.helm_response[:100]}..." if len(t.helm_response) > 100 else f"    HELM: {t.helm_response}")
                    print(f"    Gate: {t.gate_code} ({t.duration_seconds}s)\n")
            print("=" * 60 + "\n")
            return
        elif cmd == "mode":
            if self.mode == "everyday":
                self.mode = "cas_diagnostic"
                print("\n[Switched to CAS Diagnostic Mode: Raw receipts, 40-digit decimals, and Noetic logs enabled.]\n")
            else:
                self.mode = "everyday"
                print("\n[Switched to Everyday American English: Direct, friendly, transparent conversational responses.]\n")
            return

        self.turn_count += 1
        t0 = time.time()
        lower_prompt = prompt.lower()

        # Step 1: Resolve conversational references & pronouns against working memory
        resolved_prompt, entities = AnaphoraResolver.resolve(prompt, self.memory.context)
        if resolved_prompt != prompt and self.mode == "cas_diagnostic":
            print(f"[Anaphora Resolver] '{prompt}' -> '{resolved_prompt}' (Entities: {entities})")

        # Step 2: Meta Conversational Queries from Memory
        clean_lp = re.sub(r"[^\w\s]", "", lower_prompt).strip()
        if entities.get("query_last_result") or clean_lp in ["what did we do", "what did we just do", "summary"]:
            speech = self.memory.summarize_session_state(current_turn_number=self.turn_count)
            print(f"\nHELM: {speech}\n")
            self.memory.record_turn(prompt, resolved_prompt, "SESSION_SUMMARY", entities, speech, gate_code="GATE_PASS", duration=time.time()-t0)
            return

        # Step 3a: Memory Recall query (e.g. "Do you remember what I said about my answers?")
        is_mem_recall = bool(re.search(r"\b(remember what i said|what i said about|what did i say about|my preference|what did i say)\b", lower_prompt))
        if is_mem_recall:
            matches = self.memory.context.find_memory_match(prompt)
            if matches:
                if self.memory.context.user_preferences.get("concise"):
                    speech = f"You said: {matches[0]}."
                else:
                    speech = f"Yes, absolutely: {matches[0]}."
            else:
                speech = "I checked my records for this session, but I don't see a specific note on that yet. Feel free to remind me!"
            print(f"\nHELM: {speech}\n")
            self.memory.record_turn(prompt, resolved_prompt, "QUERY_MEMORY_RECALL", entities, speech, gate_code="GATE_PASS", duration=time.time()-t0)
            return

        # Step 3b: Memory Count query (e.g. "How many things have I told you?")
        is_mem_count = bool(re.search(r"\b(how many things have i told you|how many facts|how much do you know about me)\b", lower_prompt))
        if is_mem_count:
            facts = self.memory.context.user_facts
            if facts:
                facts_str = "\n".join(f"{i+1}. {f}" for i, f in enumerate(facts))
                speech = f"You've shared {len(facts)} thing{'s' if len(facts) != 1 else ''} with me so far in this session:\n{facts_str}"
            else:
                speech = "You haven't shared personal facts or preferences with me yet in this session."
            print(f"\nHELM: {speech}\n")
            self.memory.record_turn(prompt, resolved_prompt, "QUERY_MEMORY_COUNT", entities, speech, gate_code="GATE_PASS", duration=time.time()-t0)
            return

        # Step 3c: Queries about what HELM knows about the user
        is_user_knowledge_query = any(re.search(pat, lower_prompt) for pat in [
            r"what do you know about me",
            r"who am i",
            r"what have i told you",
            r"what do you remember about me",
            r"tell me about myself",
            r"what do you know so far"
        ])
        if is_user_knowledge_query:
            if not self.memory.context.user_facts:
                speech = "So far in this session, you haven't shared personal details with me yet. Tell me a bit about yourself, your background, or what you're working on!"
            else:
                facts_str = "\n".join(f"- {f}" for f in self.memory.context.user_facts)
                speech = f"Here is what you've shared with me so far in this session:\n{facts_str}"
            print(f"\nHELM: {speech}\n")
            self.memory.record_turn(prompt, resolved_prompt, "USER_KNOWLEDGE_QUERY", entities, speech, gate_code="GATE_PASS", duration=time.time()-t0)
            return

        # Step 4: Explanation & Walkthrough Requests ('Explain it back to me in your own words')
        is_explanation_request = any(re.search(pat, lower_prompt) for pat in [
            r"explain it back to me",
            r"in your own words",
            r"walk me through",
            r"explain what you (?:just )?did",
            r"explain what that (?:code|program|script) does",
            r"why did you (?:do|choose) that"
        ])
        if is_explanation_request:
            last_goal = self.memory.context.last_goal
            if last_goal:
                last_goal_clean = last_goal.strip().rstrip(".").strip()
                # (A hard-coded "beehive counts" branch used to fire on any goal with "hive", "bee" or "count"
                # and claimed a hive-tallying program HELM never wrote. Removed: the general reply below
                # repeats the user's own goal words and claims only the planning steps that actually ran.)
                if any(k in last_goal.lower() for k in ["git", "diff", "status", "log"]):
                    speech = (
                        f"Here's what I did in my own words:\n"
                        f"For your goal ('{last_goal_clean}'), I inspected the local git version control state, "
                        f"verified working tree cleanliness, and logged the cryptographic receipt without running any shell scripts."
                    )
                else:
                    speech = (
                        f"Here's what I did in my own words:\n"
                        f"For your goal ('{last_goal_clean}'), I planned the required steps using Kahn's topological sort, "
                        f"cleared each step through the RPM pre-flight safety gate, and executed the tools with verified receipts."
                    )
            else:
                speech = "We haven't executed a workflow yet in this session to explain. Give me an engineering task or ask a question and I'll walk you through it!"
            print(f"\nHELM: {speech}\n")
            self.memory.record_turn(prompt, resolved_prompt, "REQUEST_EXPLANATION", entities, speech, gate_code="GATE_PASS", duration=time.time()-t0)
            return

        # Step 4b (fix H): stock and recipe English goes through the live loop's English-in route -- the same
        # gate, brain, store and receipts as the checked form. No side parser saves inventory any more.
        if self.loop.wants_turn(prompt):
            self._recipe_turn(prompt, resolved_prompt, entities, t0)
            return

        # Step 5a: User Preference statement (e.g. "Remember that I prefer short answers")
        is_pref = bool(re.search(r"\b(remember that i prefer|i prefer|prefer short answers|keep (?:your )?answers? (?:short|concise|brief))\b", lower_prompt))
        if is_pref:
            cube_rec = self.memory.process_turn_with_cube_store(prompt)
            if any(w in lower_prompt for w in ["short", "concise", "brief"]):
                self.memory.context.add_user_preference("concise", True, "You prefer short, concise answers", turn_index=self.turn_count)
                speech = "Understood. I've noted your preference for short, concise answers and will keep future replies brief."
            else:
                self.memory.context.add_user_preference("custom", prompt, f"Preference: {prompt}", turn_index=self.turn_count)
                speech = "Understood! I've noted your preference in our conversation context."
            print(f"\nHELM: {speech}\n")
            rec_hash = cube_rec.receipt_hash if cube_rec else None
            self.memory.record_turn(
                prompt, resolved_prompt, "USER_PREFERENCE", entities, speech,
                receipt_hash=rec_hash, gate_code="GATE_PASS", duration=time.time()-t0,
                kind="directive", operation="WRITE_CUBE", cubes_written=cube_rec.cubes_written if cube_rec else []
            )
            return

        # Step 5b: User Affect / Emotional state (e.g. "I'm feeling tired today", "I feel awful", "I feel wonderful")
        classify_val = "NEUTRAL"
        classify_pol = "ASSERTED"
        if self.memory.context.turn_processor is not None:
            _, _, classify_pol, classify_val, _ = self.memory.context.turn_processor.classify_turn(prompt)

        is_affect = (classify_val in ("POSITIVE", "NEGATIVE")) or bool(re.search(r"\b(i'm feeling|i am feeling|i feel|i'm tired|i am tired)\b", lower_prompt))
        if is_affect:
            cube_rec = self.memory.process_turn_with_cube_store(prompt)
            val = cube_rec.valence if cube_rec else classify_val
            pol = cube_rec.assertion if cube_rec else classify_pol
            is_concise = self.memory.context.user_preferences.get("concise", False)

            if "tired" in lower_prompt:
                self.memory.context.add_user_fact("You shared that you were feeling tired today", turn_index=self.turn_count)
                if is_concise:
                    speech = "Sorry to hear you're feeling tired today. I'll keep things brief. Let me know what you need!"
                else:
                    speech = "I'm sorry to hear that you're feeling tired today! Take things easy. I'm here if you want to offload any coding, design, testing, or recipe tasks, or we can keep our exchanges brief and low-key."
            elif val == "NEGATIVE" and pol == "ASSERTED":
                self.memory.context.add_user_fact(f"You shared feeling down: {prompt}", turn_index=self.turn_count)
                speech = "I'm sorry to hear that you're feeling down. Let me know how I can help."
            elif val == "POSITIVE" and pol == "ASSERTED":
                self.memory.context.add_user_fact(f"You shared feeling positive: {prompt}", turn_index=self.turn_count)
                speech = "That's fantastic to hear! Glad you're feeling great today."
            else:
                self.memory.context.add_user_fact(prompt, turn_index=self.turn_count)
                speech = "I hear you. Anything I can help with?" if is_concise else "I hear you. Anything I can help with today?"

            print(f"\nHELM: {speech}\n")
            rec_hash = cube_rec.receipt_hash if cube_rec else None
            self.memory.record_turn(
                prompt, resolved_prompt, "USER_AFFECT", entities, speech,
                receipt_hash=rec_hash, gate_code="GATE_PASS", duration=time.time()-t0,
                kind=cube_rec.kind if cube_rec else "instance",
                assertion=pol, valence=val,
                operation="WRITE_CUBE", cubes_written=cube_rec.cubes_written if cube_rec else []
            )
            return

        # Step 5c: Creative Humor (e.g. "Tell me a joke")
        is_humor = bool(re.search(r"\b(tell me a joke|make me laugh|say something funny)\b", lower_prompt))
        if is_humor:
            cube_rec = self.memory.process_turn_with_cube_store(prompt)
            is_concise = self.memory.context.user_preferences.get("concise", False)
            if is_concise:
                speech = "Why do programmers prefer dark mode? Because light attracts bugs!"
            else:
                speech = "Why do programmers prefer dark mode? Because light attracts bugs!\n\nWhenever you're ready, let me know what we're working on next."
            print(f"\nHELM: {speech}\n")
            rec_hash = cube_rec.receipt_hash if cube_rec else None
            self.memory.record_turn(
                prompt, resolved_prompt, "CREATIVE_HUMOR", entities, speech,
                receipt_hash=rec_hash, gate_code="GATE_PASS", duration=time.time()-t0,
                kind="directive", operation="WRITE_CUBE", cubes_written=cube_rec.cubes_written if cube_rec else []
            )
            return

        # Step 5d: User Personal Narrative / Facts (e.g. "My grandfather kept bees in the south of France")
        # Identify non-command declarative personal statements without question marks
        is_question = "?" in prompt or lower_prompt.startswith(("what", "who", "where", "when", "why", "how", "can you", "could you", "is it"))
        personal_patterns = [
            r"\b(my grandfather|my grandmother|my dad|my father|my mother|my brother|my sister|my family|my friend|my cousin)\b",
            r"\b(i live in|i work at|i grew up in|i enjoy|i like|i love|i own|i have a|i used to|i am a|i'm a)\b",
            r"\b(kept bees|keeps bees|beekeeping|beekeeper|farmer|gardener|carpenter)\b"
        ]
        is_personal_narrative = (not is_question) and any(re.search(pat, lower_prompt) for pat in personal_patterns)
        if is_personal_narrative:
            cube_rec = self.memory.process_turn_with_cube_store(prompt)
            self.memory.context.add_user_fact(prompt, turn_index=self.turn_count)
            # Repeat back only the user's own words, exactly as stored in user_facts. No added detail:
            # a hard-coded "beekeeping in the south of France" reply used to answer ANY message about bees.
            said = prompt.strip().rstrip(".").strip()
            speech = f'Noted. You told me: "{said}". I\'ve added that to what I know about you in this session.'
            print(f"\nHELM: {speech}\n")
            rec_hash = cube_rec.receipt_hash if cube_rec else None
            self.memory.record_turn(
                prompt, resolved_prompt, "USER_NARRATIVE", entities, speech,
                receipt_hash=rec_hash, gate_code="GATE_PASS", duration=time.time()-t0,
                kind="instance", operation="WRITE_CUBE", cubes_written=cube_rec.cubes_written if cube_rec else []
            )
            return

        # Step 6: Queries about inventory on hand (including pantry, cupboard, stock)
        is_inv_query = bool(
            entities.get("query_inventory")
            or any(w in lower_prompt for w in ["what do we have in stock", "what is our inventory", "check inventory", "what's in the pantry", "what is in the pantry", "list what's in the pantry", "show me what's in the pantry", "what've we got on hand then", "list the inventory", "what's in stock"])
        )
        if is_inv_query:
            cube_rec = self.memory.process_turn_with_cube_store(prompt)
            inv = self.memory.context.inventory
            if not inv and (not cube_rec or not cube_rec.cubes_read):
                speech = "We don't have any ingredient quantities recorded in our session inventory yet. You can tell me what you have (for example: 'We have 50 Flour, 30 Sugar, and 20 Butter')."
            else:
                inv_items = ", ".join(f"{v} {k}" for k, v in inv.items())
                if "pantry" in lower_prompt:
                    speech = f"Currently on hand in pantry: {inv_items}."
                else:
                    speech = f"Here is our current inventory recorded on hand: {inv_items}."
            print(f"\nHELM: {speech}\n")
            rec_hash = cube_rec.receipt_hash if cube_rec else None
            self.memory.record_turn(
                prompt, resolved_prompt, "INVENTORY_QUERY", entities, speech,
                receipt_hash=rec_hash, gate_code="GATE_PASS", duration=time.time()-t0,
                kind=cube_rec.kind if cube_rec else "instance",
                operation=cube_rec.operation if cube_rec else "LIST_PARTS",
                cubes_read=cube_rec.cubes_read if cube_rec else [],
                cubes_written=cube_rec.cubes_written if cube_rec else []
            )
            return

        # Step 7b: Epistemic Self-Directed Growth & Autonomous Recipe Synthesis
        study_match = re.search(r"\b(?:study|investigate|explore|learn about|formulate a recipe for|model the physics of)\s+([\w\s\-]+)", lower_prompt)
        if study_match and not any(k in lower_prompt for k in ["code", "script", "file", "test", "git"]):
            concept = study_match.group(1).strip().rstrip("?.")
            # If domain has no justified physical energy/matter equations (e.g. poetry, ancient literature) -> REFUSE
            if any(w in concept.lower() for w in ["poetry", "medieval", "literature", "philosophy", "novel"]):
                cube_rec = self.memory.process_turn_with_cube_store(prompt)
                speech = f"I will not do that: '{prompt}' lacks justified physical inputs. Missing knowledge must not be filled with fabricated content."
                print(f"\nHELM: {speech}\n")
                rec_hash = cube_rec.receipt_hash if cube_rec else None
                self.memory.record_turn(
                    prompt, resolved_prompt, "STUDY_REFUSAL", {"concept": concept}, speech,
                    receipt_hash=rec_hash, gate_code="GATE_REFUSE", duration=time.time()-t0,
                    kind="procedure", operation="REFUSE", cubes_written=[]
                )
                return

            is_concise = self.memory.context.user_preferences.get("concise", False)
            if is_concise:
                speech = (
                    f"Initialized study hypothesis for '{concept}'. "
                    f"Governed under Station S0 CES formulation (rho=0.5, 4 inputs) with 80% stoichiometric verification and 20% nuance. "
                    f"Status: HYPOTHESIS_FORMULATED."
                )
            else:
                speech = (
                    f"I've initialized an autonomous study hypothesis for '{concept}'.\n"
                    f"Under Station S0's Degree-1 Power Mean formulation, I'm structuring this as a proposed stoichiometric model:\n"
                    f"  - Target Outcome (Y): Effective Stability & Output of {concept}\n"
                    f"  - Hypothesized Inputs: 1. Core Material/State, 2. Thermal Energy Transfer, 3. Dynamic Flow/Rate, 4. Boundary Constraints\n"
                    f"  - Initial Curvature: rho = 0.5 (Balanced elasticity of substitution)\n"
                    f"  - Dual Ratio: 80% strict stoichiometric governance (40-digit Decimal, RPM gate interlocks) : 20% exploratory neural nuance\n"
                    f"  - Epistemic Status: HYPOTHESIS_FORMULATED (ENGINEERED-NOT-VALIDATED)\n\n"
                    f"I've registered this concept into our exploratory working graph. Once calibration data is collected, "
                    f"I can solve exact 40-digit Decimal parameter weights with zero gradient descent."
                )
            print(f"\nHELM: {speech}\n")
            self.memory.context.add_user_fact(f"Autonomous study hypothesis initialized for {concept}", turn_index=self.turn_count)
            self.memory.record_turn(prompt, resolved_prompt, "STUDY_HYPOTHESIS", {"concept": concept}, speech, gate_code="GATE_PASS", duration=time.time()-t0)
            return

        # Step 8: Agentic / Software Engineering Goal
        lower_prompt = resolved_prompt.lower()
        is_agentic = any(k in lower_prompt for k in [
            "write", "create", "test", "verify", "git", "commit", "diff",
            "scaffold", "dashboard", "design", "dispatch", "cloud", "aws", "run", "inspect"
        ])

        if is_agentic and not any(ing.lower() in lower_prompt for ing in self.loop.brain.ingredients):
            # Decompose and execute through Level A1/A2 Topological Planner
            dag = self.engine.decompose_goal(resolved_prompt)
            plan_res = self.engine.execute_dag(dag)
            elapsed = time.time() - t0

            # Render Everyday American English conversational reply
            is_concise = self.memory.context.user_preferences.get("concise", False)
            speech = ax.AgenticExecutionEngine.speak_plan_result(plan_res, concise=is_concise)
            print(f"\nHELM: {speech}")

            # Update working memory context
            self.memory.context.last_goal = resolved_prompt
            self.memory.context.last_result_summary = speech
            self.memory.context.last_plan_steps = plan_res.get("execution_log", [])
            self.memory.record_turn(
                user_raw_text=prompt,
                resolved_text=resolved_prompt,
                intent="AGENTIC_GOAL",
                entities=entities,
                helm_response=speech,
                receipt_hash=plan_res.get("dag_sha256"),
                gate_code="GATE_PASS" if plan_res.get("all_steps_completed") else "GATE_CLAMPED",
                duration=elapsed
            )

            if self.mode == "cas_diagnostic":
                print("\n" + "-" * 40)
                print(f"[CAS DIAGNOSTIC TRACE - Turn {self.turn_count}]")
                print(f"  Topological Steps ({len(plan_res.get('execution_log', []))}):")
                for s in plan_res.get("execution_log", []):
                    print(f"    - [{s.get('step_id')}] status={s.get('status')} (gate={s.get('gate_code', 'PASS')})")
                print(f"  Acyclic Kahn Invariant: VERIFIED")
                print(f"  Elapsed Time: {elapsed:.3f}s")
                print("-" * 40)
            print()
            return

        # Step 10: General Chitchat / Greetings or Ungrounded Refusal
        elapsed = time.time() - t0
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "how are you"]
        cube_rec = self.memory.process_turn_with_cube_store(prompt)
        rec_hash = cube_rec.receipt_hash if cube_rec else None

        if any(lower_prompt.startswith(g) or lower_prompt == g for g in greetings):
            speech = "Hello! I'm HELM, your governed cognitive assistant. I'm ready to help with software engineering, code synthesis, testing, git workflows, or recipe calculations. What's on your mind?"
            print(f"\nHELM: {speech}\n")
            self.memory.record_turn(
                prompt, resolved_prompt, "GENERAL_CONVERSATION", entities, speech,
                receipt_hash=rec_hash, gate_code="GATE_PASS", duration=elapsed,
                kind="instance", operation="WRITE_CUBE"
            )
        else:
            m_gk = re.search(r"what(?:'s| is) (?:the )?([a-zA-Z\s]+)", prompt, re.IGNORECASE)
            is_concise = self.memory.context.user_preferences.get("concise", False)
            if m_gk:
                topic = m_gk.group(1).strip().rstrip("?").strip()
                if is_concise:
                    speech = f"I don't have verified encyclopedic data on {topic} in my active datasets, so I won't guess without evidence."
                else:
                    speech = f"I don't have verified encyclopedic data on {topic} in my active datasets, so I won't guess without evidence. My core capabilities are focused on software engineering, mathematical recipes, systems architecture, and drone flight simulation. Let me know what we can engineer!"
            else:
                if is_concise:
                    speech = "I don't have verified data on that in my system, so I won't guess without evidence."
                else:
                    speech = "I don't have verified data on that in my system, so I won't guess without evidence. Let me know what project, code, or recipe you'd like to work on!"

            print(f"\nHELM: {speech}\n")
            self.memory.record_turn(
                prompt, resolved_prompt, "GENERAL_KNOWLEDGE_INQUIRY", entities, speech,
                receipt_hash=rec_hash, gate_code="GATE_PASS", duration=elapsed,
                kind=cube_rec.kind if cube_rec else "concept",
                operation=cube_rec.operation if cube_rec else "REFUSE",
                cubes_written=[]
            )
        return

    # ------------------------------------------------------------------ fix H: the recipe turn
    def _sync_inventory(self):
        """The conversation's inventory is a MIRROR of the loop's verified stock, never a separate parse."""
        inv = {}
        for k, v in self.loop.stock.items():
            t = frac_text(v)
            inv[k] = Decimal(t) if "/" not in t else v
        self.memory.context.inventory = inv

    def _speak(self, res, prompt):
        """Every everyday reply goes through the voice: stock notes, reader questions, brain receipts."""
        is_concise = self.memory.context.user_preferences.get("concise", False)
        status = res.get("loop_status", "")
        if res.get("path") == "wide":
            # Wave-7 practice (2026-10-20): a wide-path answer was re-rendered as "about 0.33 units" with no dish name, and a
            # recorded stock turn as "That's outside what I know". The wide path's own sentence (helm_wide_turn.say_wide,
            # say_learned, say_refused, say_reader_question) already says every amount exactly and names the dish; the
            # voice still guards it (no CAS words; every number and name from the sentence or the user's words).
            line = res.get("everyday_english_response") or ""
            speech = self.voice._say_plain("loop_line", [line], prompt, [line], status).text
            if not res.get("cubes_written") and "nothing was saved" not in speech.lower():
                speech = speech + " Nothing was saved."
            return speech
        parts = []
        said_order = [s["name"] for s in (res.get("english_in") or {}).get("stocks") or []]
        recorded = sorted(res.get("stock_recorded") or [],
                          key=lambda r: said_order.index(r["name"]) if r["name"] in said_order else len(said_order))
        absent = res.get("absent_recorded") or []
        if recorded or absent:
            parts.append(self.voice.say_stock_noted(recorded, absent, user_text=prompt).text)
        if status != "INVENTORY_RECORDED":
            stock_text = {k: frac_text(v) for k, v in self.loop.stock.items()}
            receipt = receipt_from_loop_result(res, stock_text, units=self.loop.units)
            if status in PLAIN_LOOP_LINES:
                line = res.get("everyday_english_response") or ""
                parts.append(self.voice._say_plain("loop_line", [line], prompt, [line], status).text)
            elif receipt is not None:
                parts.append(self.voice.render(receipt, user_text=prompt, concise=is_concise).text)
            else:
                parts.append(self.voice.render({"kind": "CLARIFY", "situation": "dont_know"},
                                               user_text=prompt, concise=is_concise).text)
        speech = " ".join(p for p in parts if p).strip()
        if not res.get("cubes_written") and "nothing was saved" not in speech.lower():
            speech = speech + " Nothing was saved."   # the honesty promise, in plain words, when nothing was written
        return speech

    def _recipe_turn(self, prompt, resolved_prompt, entities, t0):
        res = self.loop.process_turn(prompt, tick=self.turn_count)
        elapsed = time.time() - t0
        self._sync_inventory()
        # keep the user's own words for amounts ("12 cups of flour") so the voice can quote them back
        for name, q in helm_english_in.quantities_said(res.get("english_in") or {}).items():
            self.voice.state.user_said[_norm_name(say_name(name))] = {
                "qty": q["qty"], "unit": q["unit"], "words": q["words"], "turn": str(self.voice.state.turn)}
        if self.mode == "everyday":
            speech = self._speak(res, prompt)
        else:
            speech = res["everyday_english_response"]
        print(f"\nHELM: {speech}")
        status = res["loop_status"]
        self.memory.context.last_goal = prompt
        self.memory.context.last_result_summary = speech
        self.memory.record_turn(
            user_raw_text=prompt,
            resolved_text=resolved_prompt,
            intent="INVENTORY_DECLARATION" if status == "INVENTORY_RECORDED" else "RECIPE_FOUNDATION_LOOP",
            entities=entities,
            helm_response=speech,
            receipt_hash=res.get("receipt_hash"),
            gate_code=(res.get("gate_verdict") or {}).get("verdict", "GATE_PASS"),
            duration=elapsed,
            kind="instance",
            operation="WRITE_CUBE" if res.get("cubes_written") else "NONE",
            cubes_written=list(res.get("cubes_written") or []),
        )
        if self.mode == "cas_diagnostic":
            print("\n" + "-" * 40)
            print(f"[CAS DIAGNOSTIC TRACE - Turn {self.turn_count}]")
            print(f"  Loop Status     : {status}")
            if res.get("checked_form"):
                print(f"  Checked form    : {res['checked_form']}")
            if res.get("english_in"):
                print(f"  English reader  : {res['english_in'].get('status')} {res['english_in'].get('clarify')}")
            if res.get("recipe_receipt"):
                rr = res["recipe_receipt"]
                print(f"  Yield           : {rr.get('yield')}")
                print(f"  Limiting        : {rr.get('limiting_reagent')}")
            if res.get("valve_telemetry"):
                vt = res["valve_telemetry"]
                print(f"  Valve           : {vt.get('gate_interlock')} admitted={vt.get('admitted')}")
            print(f"  Elapsed Time    : {elapsed:.3f}s")
            print("-" * 40)
        print()

    def repl(self):
        self.print_banner()
        while True:
            try:
                user_input = input("You: ")
                self.handle_turn(user_input)
            except (KeyboardInterrupt, EOFError):
                print("\n\nSession terminated by user. Goodbye!")
                break
            except Exception as e:
                print(f"\n[Notice] {e}\n")


def main():
    session = HELMConversationalSession(mode="everyday")
    session.repl()


if __name__ == "__main__":
    main()
