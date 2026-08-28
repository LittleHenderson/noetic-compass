"use strict";

/* The CAS Cognitive Workbench renderer. Projection only: it reads the
   sealed WORKBENCH_DATA and draws it. It computes no verdicts. */

function el(tag, attrs, children) {
  const node = document.createElement(tag);
  if (attrs) {
    for (const key of Object.keys(attrs)) {
      if (key === "class") node.className = attrs[key];
      else if (key === "text") node.textContent = attrs[key];
      else node.setAttribute(key, attrs[key]);
    }
  }
  for (const child of children || []) {
    if (child === null || child === undefined) continue;
    node.appendChild(typeof child === "string"
      ? document.createTextNode(child) : child);
  }
  return node;
}

function chip(text, cls) {
  return el("span", { class: "chip " + cls, text: String(text) });
}

function verdictChip(verdict) {
  const ok = ["PROMOTED", "CONCLUDED", "VERIFIED"];
  const bad = ["REJECTED", "REJECTED_AS_PROTECTED",
               "REJECTED_EVALUATOR_TAMPERING", "CONTRADICTED",
               "INADMISSIBLE", "BUDGET_EXHAUSTED", "LOOP_LIMIT_REACHED",
               "FAIL", "DISPROVED"];
  const warn = ["QUARANTINED", "NEEDS_INFORMATION", "NEEDS_CAPABILITY",
                "CONFLICT_UNRESOLVED", "UNKNOWN", "UNDERDETERMINED"];
  const cls = ok.indexOf(verdict) >= 0 ? "ok"
    : (bad.indexOf(verdict) >= 0 ? "bad"
       : (warn.indexOf(verdict) >= 0 ? "warn" : "info"));
  return chip(verdict, cls);
}

function pane(id, title, builder) {
  const section = el("section", { class: "pane", id: id });
  section.appendChild(el("h2", { text: title }));
  const body = el("div", { class: "pane-body" });
  builder(body);
  section.appendChild(body);
  return section;
}

function simpleTable(container, headers, rows) {
  const t = el("table");
  const thead = el("tr");
  headers.forEach(function (h) { thead.appendChild(el("th", { text: h })); });
  t.appendChild(thead);
  rows.forEach(function (row) {
    const tr = el("tr");
    row.forEach(function (cell) {
      const td = el("td");
      td.appendChild(typeof cell === "string"
        ? document.createTextNode(cell) : cell);
      tr.appendChild(td);
    });
    t.appendChild(tr);
  });
  container.appendChild(t);
}

function keyValue(container, pairs) {
  const list = el("ul", { class: "clean" });
  pairs.forEach(function (pair) {
    list.appendChild(el("li", { text: pair[0] + ": " + pair[1] }));
  });
  container.appendChild(list);
}

/* ---------------------------------------------------------------- */
function renderDialogue(container, data) {
  data.questions.forEach(function (q) {
    container.appendChild(el("p", {}, [
      el("strong", { text: q.question + "  " }),
      verdictChip(q.kernel_status),
      el("span", { text: "  ->  " + q.answer }),
    ]));
  });
}

function renderGoalMap(container, data) {
  keyValue(container, [
    ["goal", data.goal_id],
    ["foundation channel", data.foundation_ref],
    ["desired outcome", data.desired_outcome],
    ["kind", data.kind],
    ["D/W/P scan", JSON.stringify({
      D: data.scan.D_ok, W: data.scan.W_ok, P: data.scan.P_ok,
      first_unmet: data.scan.first_unmet,
    })],
    ["adapter", JSON.stringify(data.adapter)],
  ]);
}

function renderLiveBoard(container, data) {
  data.ticks.forEach(function (row) {
    container.appendChild(el("p", {}, [
      el("span", { text: "t" + row.tick + "  ", class: "mono" }),
      el("span", { text: row.components.join(", ") }),
    ]));
  });
}

function renderBranchTree(container, data) {
  const winner = data.winner;
  data.candidates.forEach(function (cand) {
    const card = el("div", { class: "candidate" });
    const inf = cand.inference || {};
    const isWinner = String(inf.conclusion) === String(winner);
    card.appendChild(el("div", {}, [
      el("strong", { text: cand.candidate_id + "  " + cand.target }),
      isWinner ? chip("WINNER", "ok") : chip("ELIMINATED", "bad"),
      el("span", { text: "  " + (data.eliminated[cand.candidate_id] || "") }),
    ]));
    const detail = el("div", { class: "detail" });
    keyValue(detail, [
      ["why generated", cand.trigger_state || "-"],
      ["associated rules", JSON.stringify(cand.associated_rules || [])],
      ["memories contributed", JSON.stringify(cand.retrieved_memories || [])],
      ["amplification", String(cand.amplification) + " (" + (cand.region || "") + ")"],
      ["conclusion proven", String(inf.success)],
      ["rules used", JSON.stringify(inf.rules_used || [])],
      ["premises used", JSON.stringify(inf.premises_used || [])],
      ["contradiction status", inf.contradiction_status || "-"],
    ]);
    card.appendChild(detail);
    card.addEventListener("click", function () {
      card.classList.toggle("open");
    });
    container.appendChild(card);
  });
  container.appendChild(el("p", { text: "Click a candidate to inspect it." }));
  const gates = data.gates || [];
  if (gates.length) {
    container.appendChild(el("h3", { text: "Commitment gates" }));
    simpleTable(container, ["gate", "passed", "detail"],
      gates.map(function (g) {
        return [g.gate, g.passed ? chip("PASS", "ok") : chip("FAIL", "bad"),
                g.detail];
      }));
  }
}

function renderRPM(container, data) {
  data.transitions.forEach(function (t) {
    const label = t.kind === "push_rpm"
      ? "push " + t.goal + " (parent " + t.parent + ")"
      : "return " + t.goal;
    container.appendChild(el("p", {}, [
      el("span", { text: "t" + t.tick + "  ", class: "mono" }),
      el("span", { text: label }),
    ]));
  });
}

function renderMemory(container, data) {
  simpleTable(container, ["content", "source", "layer"],
    data.records.map(function (r) { return [r.content, r.source, r.layer]; }));
  const lacs = data.lacunae || [];
  if (lacs.length) {
    container.appendChild(el("p", { text: "Lacunae (typed missing knowledge):" }));
    lacs.forEach(function (l) {
      container.appendChild(el("span", { class: "chip warn",
        text: l.kind + ": " + l.query }));
      container.appendChild(el("span", { text: " " }));
    });
  }
}

function renderTruth(container, data) {
  simpleTable(container, ["idea", "truth", "provenance"],
    data.semantic_claims.map(function (c) {
      return [JSON.stringify(c.idea), verdictChip(c.truth),
              (c.provenance || {}).source || "-"];
    }));
  container.appendChild(el("p", {}, [
    el("span", { text: "Coherence of the good story: " }),
    data.coherence.good ? chip("COHERENT", "ok") : chip("INCOHERENT", "bad"),
  ]));
  if (data.coherence.broken_violations.length) {
    container.appendChild(el("p", { text: "Broken story violations:" }));
    data.coherence.broken_violations.forEach(function (v) {
      container.appendChild(el("p", { class: "mono",
        text: v.law + " - " + v.detail }));
    });
  }
  const m = data.math;
  container.appendChild(el("h3", { text: "Mathematical verdicts (CCB-M1)" }));
  keyValue(container, [
    ["false-identity attempt", m.attempt.verdict + " at step "
     + m.attempt.first_invalid_step],
    ["guilty procedure", (m.fault || {}).guilty_rule || "-"],
    ["corrected proof", m.corrected_verdict + " ("
     + m.corrected_steps + " step(s))"],
  ]);
}

function renderTrace(container, data) {
  simpleTable(container,
    ["tick", "scheduled", "auth", "rej", "pre hash", "post hash", "terminal"],
    data.rows.map(function (r) {
      return [
        String(r.tick),
        String(r.scheduled.length),
        String(r.authorized),
        String(r.rejected),
        el("span", { class: "hash mono", text: r.pre_state_hash }),
        el("span", { class: "hash mono", text: r.post_state_hash }),
        r.terminal_status ? verdictChip(r.terminal_status) : "-",
      ];
    }));
  keyValue(container, [
    ["final state hash", data.final_state_hash],
    ["trace digest", data.trace_digest],
  ]);
}

function renderLearning(container, data) {
  simpleTable(container, ["mutation", "verdict"],
    data.rule_decisions.map(function (d) {
      return [d.mutation.mutation_id, verdictChip(d.verdict)];
    }));
  keyValue(container, [
    ["experience entries", String(data.experience_count)],
    ["current revision", String(data.current_revision)],
  ]);
}

function renderEvolution(container, data) {
  data.strategies.forEach(function (s) {
    const card = el("div", { class: "candidate" });
    card.appendChild(el("div", {}, [
      el("strong", { text: s.strategy.strategy_id + "  " }),
      verdictChip(s.verdict),
      el("span", { text: "  " + s.strategy.note }),
    ]));
    const checks = el("ul", { class: "clean" });
    s.checks.forEach(function (c) {
      checks.appendChild(el("li", {}, [
        c.passed ? chip("PASS", "ok") : chip("FAIL", "bad"),
        el("span", { text: " " + c.check }),
      ]));
    });
    card.appendChild(checks);
    container.appendChild(card);
  });
  keyValue(container, [
    ["repair budget", String(data.budget) + " sandbox evaluation(s)"],
    ["promoted strategy", data.promoted_strategy || "-"],
    ["unbudgeted regression", String(data.regression_ok)],
  ]);
}

function renderOrgans(container, organs, programTests) {
  simpleTable(container, ["board", "role", "tests"],
    organs.map(function (o) {
      return [o.board, o.role, String(o.tests)];
    }));
  container.appendChild(el("p", { text: "Program total: " + programTests
    + " conformance tests across " + organs.length + " boards." }));
}

/* ---------------------------------------------------------------- */
function render() {
  const data = WORKBENCH_DATA;
  const app = document.getElementById("app");
  const p = data.panes;

  app.appendChild(pane("pane-dialogue", "1. Task and Dialogue",
    function (c) { renderDialogue(c, p.dialogue); }));
  app.appendChild(pane("pane-goal", "2. Goal Map",
    function (c) { renderGoalMap(c, p.goal_map); }));
  app.appendChild(pane("pane-board", "3. Live Board",
    function (c) { renderLiveBoard(c, p.live_board); }));
  app.appendChild(pane("pane-branch", "4. Branch Tree",
    function (c) { renderBranchTree(c, p.branch_tree); }));
  app.appendChild(pane("pane-rpm", "5. RPM Stack",
    function (c) { renderRPM(c, p.rpm_stack); }));
  app.appendChild(pane("pane-memory", "6. Memory Explorer",
    function (c) { renderMemory(c, p.memory); }));
  app.appendChild(pane("pane-truth", "7. Truth and Evidence",
    function (c) { renderTruth(c, p.truth); }));
  app.appendChild(pane("pane-trace", "8. Trace Timeline",
    function (c) { renderTrace(c, p.trace); }));
  app.appendChild(pane("pane-learning", "9. Learning Dashboard",
    function (c) { renderLearning(c, p.learning); }));
  app.appendChild(pane("pane-evolution", "10. Evolution Lab",
    function (c) { renderEvolution(c, p.evolution); }));
  app.appendChild(pane("pane-organs", "The Organ Stack",
    function (c) { renderOrgans(c, data.organs, data.program_tests); }));
}

document.addEventListener("DOMContentLoaded", render);
