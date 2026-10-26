"""dag_dataset_generator.py -- Generates Paired Everyday English <-> Symbolic CAS DAG Data for Level A1 Scribe Proposer.

Generates:
1. Diverse everyday American English prompts paired with target symbolic CAS DAG structures.
2. Discourse markers covering sequential progression, inversion ('before X, do Y'), priority ('first X, then Y'), and parallel branches.
3. Adversarial prompts with circular dependencies targeting REFUSE (PLAN_CYCLE) and ambiguous prompts targeting CLARIFY.
4. Strictly isolated training and held-out evaluation splits with deterministic random seeds.
"""
from __future__ import annotations

import json
import random
from typing import Dict, List, Any, Tuple

TOOLS = [
    "synthesize_code",
    "git_action",
    "execute_command",
    "systems_design_spec",
    "web_app_scaffold",
    "dispatch_cloud_job",
    "read_file",
    "write_file"
]

TOPOLOGIES = [
    "SEQUENTIAL",
    "INVERSION",
    "PRIORITY",
    "PARALLEL",
    "SINGLE_STEP",
    "CYCLIC_CONTRADICTION",
    "AMBIGUOUS_UNGROUNDED"
]

ENTITIES = [
    "code_file",
    "git_repo",
    "test_suite",
    "web_app",
    "cloud_job",
    "system_arch"
]

FILES = ["auth.py", "math_utils.py", "solver.py", "parser.py", "api.py", "neural_net.py", "db_router.py"]
COMMANDS = ["pytest tests/", "python verify_all.py", "cargo test", "npm test", "python check_invariants.py"]
GIT_ACTIONS = ["status", "diff", "log", "branch", "commit"]
WEB_TYPES = ["dashboard", "landing_page", "control_panel", "admin_portal"]

# Conversational everyday American English templates
SEQUENTIAL_TEMPLATES = [
    "Write the code for {file}, run the verification tests, then commit it to git.",
    "Hey HELM, please generate {file}, verify it with {test_cmd}, and push the commit to our branch.",
    "Draft up {file}, execute the test suite to make sure it passes, then log the git status.",
    "Can you synthesize {file}, run {test_cmd}, and if all looks good create a git commit?",
    "Implement {file}, check that the tests pass with {test_cmd}, then update git."
]

INVERSION_TEMPLATES = [
    "Before writing any code for {file}, run the verification tests on {test_cmd}, then write the code.",
    "Before creating {file}, check the git repo to see what was modified, then write the code.",
    "Prior to synthesizing {file}, run {test_cmd} to see the existing failures, then draft the implementation.",
    "Before designing the system architecture, read through README.md, then create the spec.",
    "Make sure to inspect the existing files before writing {file}."
]

PRIORITY_TEMPLATES = [
    "First check git to see what changed and recover the last known good state, then write the code for {file}.",
    "First inspect {file} using read_file, then update the implementation.",
    "First run {test_cmd} to verify the environment, then start writing {file}.",
    "First check git diff, then write the patch for {file}.",
    "Check git status first before making any edits to {file}."
]

PARALLEL_TEMPLATES = [
    "Inspect README.md and check git status in parallel, then design the system architecture.",
    "Run tests with {test_cmd} and inspect git log concurrently, then scaffold the {web_type}.",
    "Read the configuration and check the git diff side-by-side, then synthesize {file}.",
    "In parallel, check git status and run {test_cmd}, then prepare the cloud deployment.",
    "Concurrently review the existing repo and read the specs, then draft {file}."
]

SINGLE_STEP_TEMPLATES = [
    "Check git log and diff.",
    "Scaffold a responsive web {web_type} for our dashboard.",
    "Dispatch the training package to AWS EC2 g4dn.xlarge GPU.",
    "Run the full verification suite using {test_cmd}.",
    "Generate a systems design specification with bounded memory limits."
]

CYCLIC_TEMPLATES = [
    "Task Alpha requires Task Beta to complete first, and Task Beta requires Task Alpha to complete.",
    "Step 1 depends on Step 2, but Step 2 requires Step 1 before it can begin.",
    "Write the code only after the code is already written.",
    "Run tests that require the build, but build only after the tests pass completely.",
    "Git commit requires verification which requires git commit."
]

AMBIGUOUS_TEMPLATES = [
    "Do something with the code.",
    "Make the system better.",
    "Fix everything.",
    "Can you run that thing from earlier?",
    "Optimize it."
]


def generate_single_example(rng: random.Random) -> Dict[str, Any]:
    topo = rng.choice(TOPOLOGIES)
    f = rng.choice(FILES)
    test_cmd = rng.choice(COMMANDS)
    git_act = rng.choice(GIT_ACTIONS)
    web_type = rng.choice(WEB_TYPES)

    if topo == "SEQUENTIAL":
        tpl = rng.choice(SEQUENTIAL_TEMPLATES)
        text = tpl.format(file=f, test_cmd=test_cmd)
        return {
            "prompt": text,
            "primary_tool": "synthesize_code",
            "secondary_tool": "execute_command",
            "tertiary_tool": "git_action",
            "topology": "SEQUENTIAL",
            "turn_type": "ANSWER",
            "target_entity": "code_file",
            "prereq_order": ["synthesize_code", "execute_command", "git_action"]
        }

    elif topo == "INVERSION":
        tpl = rng.choice(INVERSION_TEMPLATES)
        text = tpl.format(file=f, test_cmd=test_cmd)
        return {
            "prompt": text,
            "primary_tool": "execute_command",
            "secondary_tool": "synthesize_code",
            "tertiary_tool": "NONE",
            "topology": "INVERSION",
            "turn_type": "ANSWER",
            "target_entity": "test_suite",
            "prereq_order": ["execute_command", "synthesize_code"]
        }

    elif topo == "PRIORITY":
        tpl = rng.choice(PRIORITY_TEMPLATES)
        text = tpl.format(file=f, test_cmd=test_cmd)
        return {
            "prompt": text,
            "primary_tool": "git_action",
            "secondary_tool": "synthesize_code",
            "tertiary_tool": "NONE",
            "topology": "PRIORITY",
            "turn_type": "ANSWER",
            "target_entity": "git_repo",
            "prereq_order": ["git_action", "synthesize_code"]
        }

    elif topo == "PARALLEL":
        tpl = rng.choice(PARALLEL_TEMPLATES)
        text = tpl.format(file=f, test_cmd=test_cmd, web_type=web_type)
        return {
            "prompt": text,
            "primary_tool": "read_file",
            "secondary_tool": "git_action",
            "tertiary_tool": "systems_design_spec",
            "topology": "PARALLEL",
            "turn_type": "ANSWER",
            "target_entity": "system_arch",
            "prereq_order": ["read_file", "git_action", "systems_design_spec"]
        }

    elif topo == "SINGLE_STEP":
        tpl = rng.choice(SINGLE_STEP_TEMPLATES)
        text = tpl.format(file=f, test_cmd=test_cmd, web_type=web_type)
        tool = "git_action" if "git" in text.lower() else ("web_app_scaffold" if "web" in text.lower() else ("dispatch_cloud_job" if "aws" in text.lower() else "execute_command"))
        return {
            "prompt": text,
            "primary_tool": tool,
            "secondary_tool": "NONE",
            "tertiary_tool": "NONE",
            "topology": "SINGLE_STEP",
            "turn_type": "ANSWER",
            "target_entity": "git_repo" if tool == "git_action" else "code_file",
            "prereq_order": [tool]
        }

    elif topo == "CYCLIC_CONTRADICTION":
        tpl = rng.choice(CYCLIC_TEMPLATES)
        return {
            "prompt": tpl,
            "primary_tool": "NONE",
            "secondary_tool": "NONE",
            "tertiary_tool": "NONE",
            "topology": "CYCLIC_CONTRADICTION",
            "turn_type": "REFUSE",
            "target_entity": "code_file",
            "prereq_order": []
        }

    else:  # AMBIGUOUS_UNGROUNDED
        tpl = rng.choice(AMBIGUOUS_TEMPLATES)
        return {
            "prompt": tpl,
            "primary_tool": "NONE",
            "secondary_tool": "NONE",
            "tertiary_tool": "NONE",
            "topology": "AMBIGUOUS_UNGROUNDED",
            "turn_type": "CLARIFY",
            "target_entity": "code_file",
            "prereq_order": []
        }


def generate_dataset(n_samples: int = 2500, seed: int = 42) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rng = random.Random(seed)
    all_data = [generate_single_example(rng) for _ in range(n_samples)]

    # Hold out 500 samples strictly for evaluation
    eval_size = min(500, int(n_samples * 0.2))
    eval_data = all_data[:eval_size]
    train_data = all_data[eval_size:]

    return train_data, eval_data


if __name__ == "__main__":
    tr, ev = generate_dataset(100, seed=123)
    print(f"Generated {len(tr)} train samples, {len(ev)} eval samples.")
    print("Sample 0:", json.dumps(tr[0], indent=2))
