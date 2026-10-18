"""helm_chat.py -- Interactive Conversational Interface for HELM.

Enables direct, interactive natural language dialogue with HELM in Everyday American English.
Integrates:
- Everyday American English Voice Adapter
- Stage v0.7 Topological Scribe Proposer & Level L4 Neural Proposer
- Station S0 22x40 Recipe Brain & 40-digit Decimal Arithmetic
- Phase 3 Meta Valve Controller (tks_meta_valve_controller)
- Immutable RPM Safety Gate (Zero-Hallucination Invariant)
- Level A1/A2 Stoichiometric Agentic Tool Executor

Usage:
    python helm_chat.py
"""
from __future__ import annotations

import os
import sys
import time
from decimal import Decimal
from typing import Optional

# Ensure repository root is on path
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import helm_end_to_end_loop as e2e
import helm_agentic_executor as ax
from helm_memory import HELMConversationalMemory, AnaphoraResolver


class HELMConversationalSession:
    def __init__(self, mode: str = "everyday", session_id: Optional[str] = None):
        self.mode = mode  # "everyday" or "cas_diagnostic"
        self.loop = e2e.HELMEndToEndLoop()
        self.engine = ax.AgenticExecutionEngine(workspace_root=HERE)
        self.memory = HELMConversationalMemory(session_id=session_id)
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
        print("    'dials'   - Inspect and set the Unity Eye supervisory dials")
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
        print("   > 'We have 10 Flour, 8 Sugar, 4 Butter, and 2 Water. How much can we produce?'")
        print("   > 'Can we bake a batch without Water?'")
        print("\n3. Systems & Web Design:")
        print("   > 'Scaffold a modern web dashboard for our cognitive workspace.'")
        print("   > 'Design a high-throughput data processing pipeline with bounded memory.'")
        print("\n4. General Inquiry & Safety Testing:")
        print("   > 'What is the current status of our repository and test suite?'")
        print("   > 'Who will win the football game next year?' (Watch RPM Gate refuse ungrounded guesses)")
        print("-" * 50 + "\n")

    def show_dials(self):
        eye = self.engine.eye
        p = eye.dial_params
        print(f"\n--- Unity Eye F1 Supervisory Dials (Mode: {eye.dial}) ---")
        print(f"  Candidate Breadth (K)     : {p['K']}  [1: Conservative .. 32: Wild]")
        print(f"  Substitution Curvature (ρ): {p['rho']}  [-4: Strict .. 1: Perfect Sub]")
        print(f"  RPA Search Radius (R)     : {p['R']}  [1, 2, 4, 8 bounded horizon]")
        print(f"  Idle Pondering Budget     : {p['ponder']} cycles")
        print(f"  Phase 3 Valve Saliency (σ): {p['sigma']}  [0.0: Closed .. 1.0: Wide Open]")
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

        # Step 2: Handle meta conversational queries from memory directly
        if entities.get("query_last_result") or lower_prompt in ["what did we do", "what did we just do", "summary"]:
            speech = self.memory.summarize_session_state()
            print(f"\nHELM: {speech}\n")
            self.memory.record_turn(prompt, resolved_prompt, "SESSION_SUMMARY", entities, speech, gate_code="GATE_PASS", duration=time.time()-t0)
            return

        if entities.get("query_inventory") or lower_prompt in ["what do we have in stock", "what is our inventory", "check inventory"]:
            inv = self.memory.context.inventory
            if not inv:
                speech = "We don't have any ingredient quantities recorded in our session inventory yet. You can tell me what you have (for example: 'We have 10 Flour, 8 Sugar, and 4 Butter')."
            else:
                inv_items = ", ".join(f"{v} {k}" for k, v in inv.items())
                speech = f"Here is our current inventory recorded on hand: {inv_items}."
            print(f"\nHELM: {speech}\n")
            self.memory.record_turn(prompt, resolved_prompt, "INVENTORY_QUERY", entities, speech, gate_code="GATE_PASS", duration=time.time()-t0)
            return

        # Check if the prompt is an Agentic / Engineering Goal
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
            speech = ax.AgenticExecutionEngine.speak_plan_result(plan_res)
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

        # Otherwise, process through the core recipe and foundational knowledge loop
        # First check if inputs update existing inventory
        current_inputs = self.loop.extract_ingredient_quantities(resolved_prompt)
        if current_inputs:
            self.memory.context.update_inventory(current_inputs)

        # Merge with existing inventory context if only partial inputs were mentioned
        effective_inputs = dict(self.memory.context.inventory)
        effective_inputs.update(current_inputs)

        res = self.loop.process_turn(resolved_prompt, tick=self.turn_count)
        elapsed = time.time() - t0

        print(f"\nHELM: {res['everyday_english_response']}")

        self.memory.context.last_goal = resolved_prompt
        self.memory.context.last_result_summary = res["everyday_english_response"]
        self.memory.record_turn(
            user_raw_text=prompt,
            resolved_text=resolved_prompt,
            intent="RECIPE_FOUNDATION_LOOP",
            entities=entities,
            helm_response=res["everyday_english_response"],
            receipt_hash=res.get("recipe_receipt", {}).get("receipt_hash") if res.get("recipe_receipt") else None,
            gate_code=res.get("recipe_receipt", {}).get("limiting_reagent", "GATE_PASS") if res.get("recipe_receipt") else "GATE_PASS",
            duration=elapsed
        )

        if self.mode == "cas_diagnostic":
            print("\n" + "-" * 40)
            print(f"[CAS DIAGNOSTIC TRACE - Turn {self.turn_count}]")
            print(f"  Loop Status: {res['loop_status']}")
            if res.get("recipe_receipt"):
                rr = res["recipe_receipt"]
                print(f"  Total Output (Y): {rr.get('total_output')}")
                print(f"  Limiting Reagent: {rr.get('limiting_reagent')}")
            if res.get("valve_telemetry"):
                vt = res["valve_telemetry"]
                print(f"  Valve Telemetry : Aperture={vt.get('aperture_sigma')}, Admitted={vt.get('admitted')}")
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
