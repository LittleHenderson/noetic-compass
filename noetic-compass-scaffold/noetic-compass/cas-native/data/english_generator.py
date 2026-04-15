"""Template-based English scenario generator.

Converts CAS expressions into natural English by combining operator-domain
templates, drive context templates, operation transition templates, and
scenario contexts. This is the REVERSE of the signal analyzer.
"""

from __future__ import annotations

import random
import re

# ── Operator × Domain templates (40 combos × 3-5 each) ──

OP_DOM_TEMPLATES: dict[tuple[int, str], list[str]] = {
    # CO-0: Generative Potential
    (0, "P"): ["contemplating fundamental possibilities before any commitment", "sitting with the open-ended nature of the ethical question", "allowing all potential principles to surface before narrowing"],
    (0, "C"): ["brainstorming multiple analytical approaches", "keeping the investigation open before forming a hypothesis", "surveying the full landscape of available data"],
    (0, "E"): ["feeling the full weight of the situation before reacting", "sitting with the emotional ambiguity without forcing resolution", "allowing competing feelings to coexist"],
    (0, "O"): ["pausing before acting to consider all options", "keeping the plan flexible before execution", "maintaining optionality in the action plan"],
    # CO-1: Directed Attention
    (1, "P"): ["carefully examining which values are at stake", "directing focus to the ethical core of the dilemma", "attending closely to the moral implications"],
    (1, "C"): ["analyzing the situation with focused precision", "directing attention to the key analytical question", "examining the evidence with concentrated scrutiny"],
    (1, "E"): ["paying close attention to the emotional dynamics", "noticing subtle shifts in feeling and mood", "focusing on what the situation feels like from the inside"],
    (1, "O"): ["zeroing in on the practical steps needed", "directing attention to what must be done next", "focusing on the operational details that matter"],
    # CO-2: Attraction / Affinity
    (2, "P"): ["being drawn toward what feels ethically right", "gravitating toward the principled path", "feeling a pull toward the morally resonant choice"],
    (2, "C"): ["being drawn to the most elegant explanation", "gravitating toward the theory that fits best", "finding the compelling argument attractive"],
    (2, "E"): ["feeling warmth and care toward the person involved", "being drawn to the empathetic response", "gravitating toward compassion and connection"],
    (2, "O"): ["being drawn toward the practical solution that just works", "gravitating toward the actionable option", "finding the efficient path appealing"],
    # CO-3: Aversion / Critical Evaluation
    (3, "P"): ["examining whether this action violates core ethical principles", "setting a firm moral boundary", "identifying the ethical risks that others overlook", "questioning whether this meets the standard of first do no harm"],
    (3, "C"): ["finding the logical flaw in the argument", "identifying which assumptions do not hold up under scrutiny", "stress-testing the analysis for hidden errors"],
    (3, "E"): ["weighing the emotional dangers of proceeding", "recognizing that this feels wrong even if the logic seems sound", "protecting someone from emotional harm"],
    (3, "O"): ["stopping the process because something is not right", "refusing to proceed until safety checks pass", "blocking an action that poses practical risk"],
    # CO-4: Encoding Intensity
    (4, "P"): ["feeling the absolute weight of the moral stakes", "recognizing this as a pivotal ethical moment", "understanding the profound significance of the choice"],
    (4, "C"): ["registering the critical importance of this finding", "recognizing a breakthrough insight", "feeling the intensity of intellectual discovery"],
    (4, "E"): ["experiencing the overwhelming emotional impact", "feeling the depth of the situation viscerally", "registering the profound personal significance"],
    (4, "O"): ["recognizing the urgency of immediate action", "feeling the critical time pressure", "understanding the high-stakes operational moment"],
    # CO-5: Receptive Integration
    (5, "P"): ["absorbing a perspective that challenges existing values", "genuinely receiving an unfamiliar ethical viewpoint", "integrating a new moral framework into existing beliefs"],
    (5, "C"): ["absorbing complex information from multiple sources", "integrating diverse analytical perspectives", "receiving and synthesizing conflicting data points"],
    (5, "E"): ["genuinely absorbing another person's emotional experience", "taking in the feelings of others while maintaining identity", "empathetically receiving what someone is going through"],
    (5, "O"): ["absorbing practical feedback and adjusting the approach", "receiving operational input and integrating it into the plan", "taking in real-world constraints"],
    # CO-6: Projective Assertion
    (6, "P"): ["asserting a clear ethical stance", "declaring what is right and standing behind it", "projecting moral clarity into an ambiguous situation"],
    (6, "C"): ["articulating a clear analytical conclusion", "asserting the logical implications with confidence", "decomposing a complex problem into clear components"],
    (6, "E"): ["expressing genuine feelings openly", "asserting emotional truth", "communicating the depth of personal feeling"],
    (6, "O"): ["issuing clear operational directives", "asserting what needs to happen next", "communicating the action plan with authority"],
    # CO-7: Pattern Entrainment
    (7, "P"): ["recognizing a recurring ethical pattern", "seeing this dilemma as part of a larger moral tradition", "connecting to established principles through repeated exposure"],
    (7, "C"): ["identifying the analytical pattern across cases", "recognizing a repeating logical structure", "seeing the familiar reasoning template"],
    (7, "E"): ["feeling the emotional rhythm of the situation", "recognizing a pattern in how feelings develop", "noticing the cyclical nature of the emotional response"],
    (7, "O"): ["following established operational procedures", "relying on proven routines and methods", "executing the standard process with practiced rhythm"],
    # CO-8: Causal Initiation
    (8, "P"): ["tracing the ethical origins of the problem", "identifying what caused the moral failure", "searching for the principled root cause"],
    (8, "C"): ["tracing the causal chain of events analytically", "identifying what led to this outcome", "mapping the cause-and-effect reasoning"],
    (8, "E"): ["understanding what triggered the emotional response", "tracing the feeling back to its source", "identifying the emotional catalyst"],
    (8, "O"): ["initiating a concrete plan of action", "starting the practical resolution process", "taking the first operational step", "launching the implementation"],
    # CO-9: Consequential Grounding
    (9, "P"): ["weighing the long-term ethical consequences", "grounding the moral decision in its real-world effects", "considering what this choice means for the future"],
    (9, "C"): ["identifying the concrete outcomes of the analysis", "grounding the theory in observable results", "predicting the consequences of the conclusion"],
    (9, "E"): ["facing the emotional consequences of the decision", "grounding feelings in their real impact", "acknowledging what this will mean emotionally"],
    (9, "O"): ["delivering the concrete outcome", "grounding the plan in tangible results", "executing to completion with measurable effect"],
}

# ── Drive context templates ──

DRIVE_TEMPLATES: dict[int, list[str]] = {
    1: ["driven by a need for unity and wholeness", "motivated by integration and coherence", "seeking harmony and completeness"],
    2: ["driven by a deep need to understand", "motivated by wisdom and insight", "seeking knowledge and clarity"],
    3: ["driven by physical vitality and energy", "motivated by health and resilience", "seeking strength and endurance"],
    4: ["driven by connection and empathy", "motivated by love and belonging", "seeking deep interpersonal bonds"],
    5: ["driven by personal agency and choice", "motivated by autonomy and self-determination", "seeking control and independence"],
    6: ["driven by structure and order", "motivated by systematic organization", "seeking clarity through frameworks"],
    7: ["driven by purpose and direction", "motivated by meaning and mission", "seeking fulfillment through goal pursuit"],
}

# ── Operation transition templates ──

OP_TEMPLATES: dict[str, list[str]] = {
    "*": ["which composes into", "merging with", "combining forces with", "building upon"],
    "+": ["while simultaneously", "alongside", "at the same time as", "together with"],
    "-": ["but held back by", "in tension with", "undermined by", "counterbalanced by"],
    "/": ["in proportion to", "relative to", "measured against", "compared with"],
    "->": ["then descending to", "which leads down to", "flowing into", "transitioning to"],
}

# ── Scenario contexts (50+) ──

CONTEXTS = [
    "A doctor in an emergency room", "A teacher facing a struggling student",
    "A manager delivering difficult feedback", "A parent watching their teenager make a mistake",
    "A judge weighing conflicting testimony", "An engineer discovering a safety flaw",
    "A therapist in a difficult session", "A negotiator at a critical point",
    "A coach deciding whether to bench a star player", "A researcher facing an ethical dilemma",
    "A CEO considering layoffs to save the company", "A social worker visiting a troubled home",
    "A firefighter entering a burning building", "A diplomat mediating between hostile nations",
    "A journalist protecting a confidential source", "A nurse advocating for a patient",
    "A pilot making an emergency landing decision", "A teacher discovering plagiarism",
    "A lawyer defending someone they believe is guilty", "A startup founder choosing between profit and ethics",
    "An investor discovering fraud in a portfolio company", "A scientist whose data contradicts the hypothesis",
    "A principal addressing a bullying situation", "A chef handling a food safety scare",
    "A police officer facing a use-of-force decision", "A surgeon deciding whether to operate",
    "A counselor helping someone through grief", "An architect discovering a structural weakness",
    "A musician choosing artistic integrity over commercial success", "A minister counseling a congregation member",
    "A veteran transitioning to civilian life", "A caregiver managing burnout",
    "A student confronting academic dishonesty", "A farmer facing a drought",
    "A small business owner dealing with a lawsuit", "An athlete weighing a career-ending injury risk",
    "A grandmother mediating a family dispute", "A librarian facing a book ban challenge",
    "A mechanic discovering a dangerous defect", "A programmer finding a security vulnerability",
    "A foster parent navigating a difficult placement", "A coach witnessing unfair officiating",
    "A professor receiving a failing student's personal plea", "A volunteer coordinator managing burnout",
    "A community organizer facing opposition", "A mentor whose protege makes a serious mistake",
    "A doctor refusing a patient's harmful request", "A financial advisor giving unwelcome news",
    "A mediator in a bitter divorce", "A zookeeper making an end-of-life decision for an animal",
]


def _parse_states(expression: str) -> list[dict]:
    """Extract operator, domain, drive from each state in the expression."""
    states = []
    for m in re.finditer(r"CO-(\d+)\^([PCEO])(?:_\{F(\d)\})?", expression):
        states.append({
            "operator": int(m.group(1)),
            "domain": m.group(2),
            "drive": int(m.group(3)) if m.group(3) else random.randint(1, 7),
        })
    return states


def _pick_operation(expression: str) -> str | None:
    """Detect the primary operation in the expression."""
    if "->" in expression:
        return "->"
    if " * " in expression:
        return "*"
    if " / " in expression:
        return "/"
    if " + " in expression:
        return "+"
    if " - " in expression and "->" not in expression:
        return "-"
    return None


def generate_english(expression: str, rng: random.Random | None = None) -> str:
    """Convert a CAS expression into a natural English scenario."""
    if rng is None:
        rng = random.Random()

    states = _parse_states(expression)
    if not states:
        return "A person faces a complex decision requiring careful reasoning."

    context = rng.choice(CONTEXTS)
    op = _pick_operation(expression)
    has_rpm = "RPM" in expression
    has_fractal = "Phi<" in expression

    parts: list[str] = [f"{context} is"]

    # First state
    s = states[0]
    key = (s["operator"], s["domain"])
    templates = OP_DOM_TEMPLATES.get(key, [f"engaging CO-{s['operator']} in the {s['domain']} domain"])
    parts.append(rng.choice(templates))

    drive_ctx = rng.choice(DRIVE_TEMPLATES.get(s["drive"], ["motivated by inner conviction"]))
    parts.append(f"({drive_ctx})")

    # Operation + subsequent states
    if op and len(states) > 1:
        transition = rng.choice(OP_TEMPLATES.get(op, ["then"]))
        parts.append(transition)
        s2 = states[1]
        key2 = (s2["operator"], s2["domain"])
        templates2 = OP_DOM_TEMPLATES.get(key2, [f"engaging CO-{s2['operator']} in the {s2['domain']} domain"])
        parts.append(rng.choice(templates2))

    # Additional states as co-present
    for s_extra in states[2:]:
        key_e = (s_extra["operator"], s_extra["domain"])
        templates_e = OP_DOM_TEMPLATES.get(key_e, ["considering further dimensions"])
        parts.append(f"while also {rng.choice(templates_e)}")

    # RPM
    if has_rpm:
        drv_match = re.search(r"RPM\(F(\d)\)", expression)
        if drv_match:
            d = int(drv_match.group(1))
            d_name = DRIVE_TEMPLATES.get(d, ["meeting prerequisites"])[0].replace("driven by ", "")
            parts.append(f", ensuring all prerequisites for {d_name} are met")

    # Fractal
    if has_fractal:
        parts.append(", cycling through a stabilizing pattern of reasoning")

    scenario = " ".join(parts).replace("  ", " ").strip()
    if not scenario.endswith("."):
        scenario += "."

    return scenario
