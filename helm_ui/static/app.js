/* HELM UI v0. Vanilla JS, no build step.
   Live mode talks to helm_ui/server.py. Demo mode (window.HELM_DEMO present) replays a recorded real session. */
(function () {
  "use strict";
  var DEMO = window.HELM_DEMO || null;
  var $ = function (id) { return document.getElementById(id); };
  var FOUND = [["F1", "Unity"], ["F2", "Wisdom"], ["F3", "Vitality"], ["F4", "Connection"], ["F5", "Agency"], ["F6", "Structure"], ["F7", "Purpose"]];
  var JOB_NAMES = { CURIOSITY: "Curiosity", PONDERING: "Pondering", IMAGINATION: "Imagination", VERIFY: "Verify", ASKING: "Asking", INTEGRATION: "Integration", CONSOLIDATE: "Consolidate" };
  var SUGGEST = [
    "We have 12 cups of flour and 9 cups of water.",
    "How much bread can we make?",
    "We made 5 loaves from 10 flour and 8 water and ran out of flour.",
    "My grandfather kept bees.",
    "What do you know about me so far?",
    "Who will win the football game next year?"
  ];
  var state = { world: "clean", busy: false, demoIndex: 0, lastState: null, showRecords: false };

  /* ---------------- theme (per-viewer convenience only) */
  function storeGet(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
  function storeSet(k, v) { try { window.localStorage.setItem(k, v); } catch (e) { /* private window */ } }
  function currentTheme() {
    var t = document.documentElement.getAttribute("data-theme");
    if (t) return t;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  var qTheme = (/[?&]theme=(dark|light)/.exec(window.location.search) || [])[1];
  var saved = qTheme || storeGet("helm-theme");
  if (saved === "dark" || saved === "light") document.documentElement.setAttribute("data-theme", saved);
  $("themeBtn").addEventListener("click", function () {
    var next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    storeSet("helm-theme", next);
  });

  /* ---------------- tiny DOM helpers (all text goes through textContent) */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = String(text);
    return n;
  }
  function svg(tag, attrs) {
    var n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function word(w) { return el("span", "word", w); }
  function fmtPct(a, b) { return b ? (100 * a / b).toFixed(1) + "%" : "-"; }
  function nice(s) { return String(s || "").toLowerCase().replace(/_/g, " "); }

  /* ---------------- tooltip */
  var tip = $("tip");
  function showTip(evt, text) {
    tip.textContent = text; tip.hidden = false;
    var x = Math.min(evt.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
    var y = Math.max(8, evt.clientY - tip.offsetHeight - 12);
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  function hideTip() { tip.hidden = true; }
  function hover(node, text) {
    node.addEventListener("mousemove", function (e) { showTip(e, text); });
    node.addEventListener("mouseleave", hideTip);
    node.setAttribute("aria-label", text);
    node.setAttribute("tabindex", "0");
    node.addEventListener("focus", function () { var r = node.getBoundingClientRect(); showTip({ clientX: r.left, clientY: r.top }, text); });
    node.addEventListener("blur", hideTip);
  }

  /* ---------------- data layer */
  function getJSON(url, opts) {
    return fetch(url, opts).then(function (r) { return r.json(); });
  }
  var api = {
    turn: function (text) {
      if (DEMO) return Promise.resolve(demoTurn(text));
      return getJSON("/turn", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: text }) });
    },
    state: function () { return DEMO ? Promise.resolve(DEMO.state_initial) : getJSON("/state"); },
    history: function () { return DEMO ? Promise.resolve([]) : getJSON("/history"); },
    eye: function (world) { return DEMO ? Promise.resolve(DEMO.eye[world]) : getJSON("/eye/scan?world=" + encodeURIComponent(world)); },
    plan: function (text) {
      if (DEMO) {
        var hit = DEMO.plans.filter(function (p) { return p.request.trim().toLowerCase() === text.trim().toLowerCase(); })[0];
        return Promise.resolve(hit || { ok: false, reason: "This page is a recording, so it can only replay the example plans shown. Run python helm_ui/server.py to plan anything you type." });
      }
      return getJSON("/plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: text }) });
    },
    setDials: function (body) {
      if (DEMO) return Promise.resolve(Object.assign({ ok: false, error: "This page is a recording; the dials only move on the live server." }, DEMO.state_initial.dials));
      return getJSON("/dials", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    }
  };
  function demoTurn(text) {
    var t = (text || "").trim().toLowerCase();
    for (var i = 0; i < DEMO.turns.length; i++) {
      if (DEMO.turns[i].you_said.trim().toLowerCase() === t) return DEMO.turns[i].response;
    }
    return { ok: true, kind: "note", recorded: false,
      reply: "This page is a recording of a real local session, so it can only replay the sentences shown as suggestions. To talk with HELM, run python helm_ui/server.py on the laptop and open http://127.0.0.1:8765." };
  }

  /* ---------------- conversation */
  var log = $("log");
  function scrollDown() { log.scrollTop = log.scrollHeight; }
  function hideIntro() { var i = $("intro"); if (i) i.remove(); }

  function sayInto(node, text) {
    var lines = String(text || "").split("\n");
    var list = null;
    lines.forEach(function (ln) {
      var m = /^\s*(?:-|\d+\.)\s+(.*)$/.exec(ln);
      if (m) {
        if (!list) { list = el("ul"); node.appendChild(list); }
        list.appendChild(el("li", null, m[1]));
      } else if (ln.trim()) {
        list = null;
        node.appendChild(el("p", null, ln));
      }
    });
  }

  function addUser(text, quiet) {
    hideIntro();
    var m = el("div", "msg user");
    if (quiet) m.style.animation = "none";
    m.appendChild(el("div", "bubble", text));
    log.appendChild(m); scrollDown();
  }

  function addThinking() {
    var m = el("div", "msg helm");
    m.appendChild(el("div", "who", "HELM"));
    var t = el("div", "typing"); t.appendChild(el("i")); t.appendChild(el("i")); t.appendChild(el("i"));
    m.appendChild(t);
    log.appendChild(m); scrollDown();
    return m;
  }

  function addHelm(resp, into, quiet) {
    hideIntro();
    var m = into || el("div", "msg helm");
    if (quiet) m.style.animation = "none";
    m.innerHTML = "";
    if (resp.kind === "note") m.className = "msg helm note";
    m.appendChild(el("div", "who", resp.kind === "note" ? "Note" : "HELM"));
    var say = el("div", "say");
    sayInto(say, resp.reply || "");
    m.appendChild(say);
    var meta = el("div", "meta");
    if (resp.record) {
      meta.appendChild(el("span", "what", resp.record.status_plain));
      if (resp.record.tools_off) meta.appendChild(el("span", null, "Tool actions are off in this window"));
      var btn = el("button", "link", "Show the record");
      btn.type = "button";
      btn.setAttribute("aria-expanded", "false");
      var panel = null;
      var setOpen = function (open, deep) {
        if (!open && panel) { panel.remove(); panel = null; btn.textContent = "Show the record"; btn.setAttribute("aria-expanded", "false"); }
        if (open && !panel) {
          panel = recordPanel(resp.record);
          m.appendChild(panel);
          btn.textContent = "Hide the record"; btn.setAttribute("aria-expanded", "true");
        }
        if (open && panel && deep) { var h = panel.querySelector(".hood"); if (h) h.open = true; }
        if (open) scrollDown();
      };
      btn.addEventListener("click", function () { setOpen(!panel, false); });
      togglers.push(setOpen);
      meta.appendChild(btn);
      if (state.showRecords) setTimeout(function () { setOpen(true, true); }, 0);
    } else if (resp.kind === "note") {
      meta.appendChild(el("span", null, "Not a turn: nothing recorded"));
    } else if (!resp.ok) {
      meta.appendChild(el("span", null, resp.detail ? "Not recorded. " + String(resp.detail).slice(0, 160) : "Not recorded"));
    }
    m.appendChild(meta);
    if (!into) log.appendChild(m);
    scrollDown();
  }

  function recordPanel(rec) {
    var box = el("div", "record");
    var dl = el("dl");
    function row(k, v) {
      dl.appendChild(el("dt", null, k));
      var dd = el("dd");
      if (v instanceof Node) dd.appendChild(v); else dd.textContent = v;
      dl.appendChild(dd);
    }
    var st = el("span");
    st.appendChild(document.createTextNode(rec.status_plain + "  "));
    st.appendChild(word(rec.status_word || "none"));
    row("Status", st);
    row("You said", rec.you_said);
    if (rec.resolved_text) row("Read as", rec.resolved_text);
    var saved = (rec.cubes_written || []);
    row("Saved", saved.length ? saved.map(nice).join(", ") : "Nothing saved");
    if ((rec.cubes_read || []).length) row("Looked up", rec.cubes_read.map(nice).join(", "));
    var g = el("span"); g.appendChild(word(rec.gate || "none")); row("Turn gate", g);
    var rg = rec.loop && rec.loop.rpm_gate;
    if (rg) {
      var r2 = el("span");
      r2.appendChild(document.createTextNode((rg.can_proceed ? "Passed: " : "Stopped: ") + (rg.gap ? "missing " + rg.gap + " " : "") ));
      r2.appendChild(word(rg.code || rg.verdict || "none"));
      row("Safety check", r2);
    }
    var vv = rec.loop && rec.loop.valve;
    if (vv) {
      var v2 = el("span");
      v2.appendChild(document.createTextNode("noise in the request " + vv.inflow_entropy + ", let through up to " + vv.aperture_sigma + ", push-back " + vv.backpressure + " "));
      v2.appendChild(word(vv.gate_interlock || vv.status || "none"));
      row("Information valve", v2);
    }
    row("Receipt", el("span", "mono", rec.receipt_hash || "none"));
    row("Turn", "#" + rec.turn_id + " at " + rec.time_utc + " (UTC), " + rec.wall_s + " s");
    if (rec.session_file) row("Logged to", el("span", "mono", "helm_ui/sessions/" + rec.session_file));
    box.appendChild(dl);

    var hood = el("details", "hood");
    hood.appendChild(el("summary", null, "Under the hood"));
    var inner = el("div");
    var p = el("div", "small");
    p.style.marginTop = "8px";
    if (rec.loop) {
      p.textContent = "This reply went through HELM's recipe loop. Station path:";
      inner.appendChild(p);
      var path = el("div", "path");
      (rec.loop.stations || []).forEach(function (s) { path.appendChild(el("span", null, s)); });
      inner.appendChild(path);
      if (rec.loop.checked_form) {
        var cf = el("div", "small"); cf.textContent = "Checked form (what the reader turned your words into):";
        inner.appendChild(cf);
        inner.appendChild(el("pre", null, rec.loop.checked_form));
      }
      if (rec.loop.next) { var nx = el("div", "small"); nx.textContent = "Next step: " + rec.loop.next; inner.appendChild(nx); }
      var raw = el("div", "small"); raw.textContent = "Loop records for this turn (" + (rec.loop.records || []).length + "):";
      inner.appendChild(raw);
      inner.appendChild(el("pre", null, JSON.stringify(rec.loop.records, null, 1)));
    } else {
      p.textContent = "This reply came from HELM's chat routes (route " + rec.route + "), not the recipe loop. There is no checked form or CAS expression for it.";
      inner.appendChild(p);
    }
    hood.appendChild(inner);
    box.appendChild(hood);
    return box;
  }

  function send(text) {
    text = (text || "").trim();
    if (!text || state.busy) return;
    state.busy = true; $("sendBtn").disabled = true;
    addUser(text);
    var pending = addThinking();
    var started = Date.now();
    api.turn(text).then(function (resp) {
      var wait = DEMO ? Math.max(0, 550 - (Date.now() - started)) : 0;
      setTimeout(function () {
        addHelm(resp, pending);
        if (resp.state) renderState(resp.state);
        state.busy = false; $("sendBtn").disabled = false; $("input").focus();
      }, wait);
    }).catch(function () {
      addHelm({ ok: false, kind: "error", reply: "The local server did not answer. Is python helm_ui/server.py still running?" }, pending);
      state.busy = false; $("sendBtn").disabled = false;
    });
  }

  var input = $("input");
  function autosize() { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 160) + "px"; }
  input.addEventListener("input", autosize);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("composer").requestSubmit(); }
  });
  $("composer").addEventListener("submit", function (e) {
    e.preventDefault();
    var t = input.value; input.value = ""; autosize(); send(t);
  });

  function renderChips() {
    var c = $("chips"); c.innerHTML = "";
    var list = DEMO ? DEMO.turns.map(function (t) { return t.you_said; }) : SUGGEST;
    list.forEach(function (s) {
      var b = el("button", "chip", s); b.type = "button";
      b.addEventListener("click", function () { send(s); });
      c.appendChild(b);
    });
    if (DEMO) {
      var all = el("button", "chip", "Play the whole recorded session"); all.type = "button";
      all.addEventListener("click", function () { playAll(0); });
      c.appendChild(all);
    }
  }
  function playAll(i) {
    if (i >= DEMO.turns.length) return;
    if (state.busy) { setTimeout(function () { playAll(i); }, 200); return; }
    send(DEMO.turns[i].you_said);
    setTimeout(function () { playAll(i + 1); }, 1300);
  }

  /* ---------------- card: what HELM knows */
  function renderKnows(k, wiring) {
    var body = $("knowsBody"); body.innerHTML = "";
    if (!k) {
      body.appendChild(el("div", "empty", "Not wired: " + ((wiring && wiring.chat) || "HELM's chat did not load")));
      return;
    }
    $("knowsSub").textContent = k.turns + (k.turns === 1 ? " turn" : " turns") + " in this session";
    var g1 = el("div", "group"); g1.appendChild(el("h3", null, "On hand"));
    if (k.stock.length || k.out_of.length) {
      var ul = el("ul", "rows");
      k.stock.forEach(function (s) {
        var li = el("li"); li.appendChild(el("span", null, s.name));
        li.appendChild(el("span", "v", s.amount + (s.unit ? " " + s.unit : ""))); ul.appendChild(li);
      });
      k.out_of.forEach(function (n) {
        var li = el("li"); li.appendChild(el("span", null, n)); li.appendChild(el("span", "v", "out")); ul.appendChild(li);
      });
      g1.appendChild(ul);
    } else g1.appendChild(el("div", "empty", "Nothing on hand yet. Tell HELM what you have."));
    body.appendChild(g1);

    var g2 = el("div", "group"); g2.appendChild(el("h3", null, "Recipes it knows, per one made"));
    var ul2 = el("ul", "rows");
    k.recipes.forEach(function (r) {
      var li = el("li"); li.appendChild(el("span", null, r.product));
      var learned = r.needs.filter(function (n) { return n.per_unit !== null && n.per_unit !== undefined; });
      var v = el("span", "v");
      if (!r.needs.length) v.textContent = "-";
      else if (!learned.length) { v.className = "v unlearned"; v.textContent = r.needs.map(function (n) { return n.ingredient; }).join(", ") + ": amounts not learned yet"; }
      else v.textContent = r.needs.map(function (n) { return n.ingredient + " " + (n.per_unit === null || n.per_unit === undefined ? "not learned" : n.per_unit); }).join(", ");
      li.appendChild(v); ul2.appendChild(li);
    });
    g2.appendChild(ul2);
    body.appendChild(g2);

    var g3 = el("div", "group"); g3.appendChild(el("h3", null, "About you"));
    if (k.your_facts.length) {
      var ul3 = el("ul", "rows");
      k.your_facts.forEach(function (f) { ul3.appendChild(el("li", null, f)); });
      g3.appendChild(ul3);
    } else g3.appendChild(el("div", "empty", "Nothing yet. HELM only keeps what you tell it."));
    if (k.prefers_short_answers) g3.appendChild(el("div", "small", "You asked for short answers."));
    body.appendChild(g3);
    if (k.brain && k.brain.claim_ceiling) {
      var src = el("div", "small"); src.textContent = "Recipe brain: " + (k.brain.name || "licensed recipe brain") + ". Limit: " + k.brain.claim_ceiling;
      body.appendChild(src);
    }
  }

  /* ---------------- card: self-check */
  document.querySelectorAll(".seg button").forEach(function (b) {
    b.addEventListener("click", function () {
      state.world = b.getAttribute("data-world");
      document.querySelectorAll(".seg button").forEach(function (o) {
        var on = o === b; o.classList.toggle("seg-on", on); o.setAttribute("aria-checked", on ? "true" : "false");
      });
    });
  });
  $("eyeRun").addEventListener("click", function () {
    var b = $("eyeRun"); b.disabled = true; b.textContent = "Checking";
    $("eyeBody").innerHTML = ""; $("eyeBody").appendChild(el("p", "muted", "Reading the test copy. Nothing is written."));
    api.eye(state.world).then(function (rep) { renderEye(rep); })
      .catch(function () { renderEye({ ok: false, reason: "The local server did not answer." }); })
      .then(function () { b.disabled = false; b.textContent = "Run self-check"; });
  });
  function renderEye(rep) {
    var body = $("eyeBody"); body.innerHTML = "";
    if (!rep) { body.appendChild(el("p", "muted", "No self-check yet. Press Run. It only reads.")); return; }
    if (!rep.ok) { body.appendChild(el("p", "muted", (rep.wired === false ? "" : "Self-check did not run: ") + (rep.reason || "unknown"))); return; }
    if (rep.world) {
      state.world = rep.world;
      document.querySelectorAll(".seg button").forEach(function (o) {
        var on = o.getAttribute("data-world") === rep.world; o.classList.toggle("seg-on", on); o.setAttribute("aria-checked", on ? "true" : "false");
      });
    }
    var say = el("div", "eye-say");
    rep.plain.forEach(function (s) {
      var cls = s.kind === "FINDING" ? "finding" : (s.kind === "NEVER_TESTED" || s.kind === "NO_EVIDENCE" ? "unknown" : "");
      var sp = el("span", cls, s.text);
      if (s.cites && s.cites.length) sp.title = "Record: " + s.cites.join(", ");
      say.appendChild(sp); say.appendChild(document.createTextNode(" "));
    });
    body.appendChild(say);
    var facts = el("div", "eye-facts");
    var f = rep.findings.length;
    facts.appendChild(word(f ? f + (f === 1 ? " finding" : " findings") : "0 findings"));
    facts.appendChild(word("Eye writes " + rep.eye_writes_to_brain));
    facts.appendChild(word("whisper writes " + rep.whisper_writes));
    body.appendChild(facts);
    body.appendChild(el("div", "small", rep.what));
    var hood = el("details", "hood");
    hood.appendChild(el("summary", null, "Under the hood"));
    var inner = el("div");
    inner.appendChild(el("div", "small", "Item by item (the owner-asked report):"));
    inner.appendChild(el("pre", null, rep.itemized.map(function (s) { return "[" + s.kind + "] " + s.text + (s.cites.length ? "   <- " + s.cites.join(", ") : ""); }).join("\n")));
    if (rep.technical) { inner.appendChild(el("div", "small", "Technical view (CAS):")); inner.appendChild(el("pre", null, rep.technical)); }
    if (f) { inner.appendChild(el("div", "small", "Findings:")); inner.appendChild(el("pre", null, JSON.stringify(rep.findings, null, 1))); }
    inner.appendChild(el("div", "small", "World " + rep.world_id + " (salt " + rep.salt + "), arm " + rep.arm + ", reads " + rep.reads_total + ", scan digest " + rep.scan_digest + ", own log read-back " + rep.log_read_back_ok + ". Source: " + rep.source));
    hood.appendChild(inner);
    body.appendChild(hood);
  }

  /* ---------------- card: attention */
  function renderAttention(p) {
    var body = $("attnBody"); body.innerHTML = "";
    if (!p || !p.wired) { body.appendChild(el("div", "empty", (p && p.reason) || "Not wired")); return; }
    var wrap = el("div", "attn");
    wrap.appendChild(radial(p.attention));
    wrap.appendChild(el("div", "small", "Each spoke is one of the 7 desires. The shape shows the share of " + p.attention.total.toLocaleString("en-US") + " idle attention steps that landed on it; the dashed ring is an even split. Mirrored desires are opposite pairs."));
    wrap.appendChild(heat(p));
    var lg = el("div", "legend");
    var a = el("span"); a.appendChild(document.createTextNode("worked")); var r = el("span", "ramp"); a.insertBefore(document.createTextNode("rarely "), a.firstChild); a.insertBefore(r, a.lastChild); lg.appendChild(a);
    var b = el("span"); b.appendChild(el("span", "key")); b.appendChild(document.createTextNode("the Eye's best pick")); lg.appendChild(b);
    var c = el("span"); var cv = el("span", "key"); cv.style.borderStyle = "dashed"; cv.style.borderWidth = "1px"; cv.style.borderColor = "var(--line-strong)"; c.appendChild(cv); c.appendChild(document.createTextNode("never tried")); lg.appendChild(c);
    wrap.appendChild(lg);
    var tv = el("details", "hood");
    tv.appendChild(el("summary", null, "Show as a table"));
    var tbl = el("table", "tv"); var thr = el("tr"); thr.appendChild(el("th", null, "Desire"));
    p.faculties.forEach(function (f) { thr.appendChild(el("th", null, JOB_NAMES[f].slice(0, 5))); });
    tbl.appendChild(thr);
    p.grid.forEach(function (row) {
      var tr = el("tr"); tr.appendChild(el("td", null, row.name));
      row.cells.forEach(function (c2) { tr.appendChild(el("td", null, c2.worked + "/" + c2.tries + (c2.eye_best ? "*" : ""))); });
      tbl.appendChild(tr);
    });
    var tw = el("div"); tw.style.overflowX = "auto"; tw.appendChild(tbl); tv.appendChild(tw);
    tv.appendChild(el("div", "small", "Cells: worked / tries. * = the Eye's best pick. It matched the hidden best brain job on " + p.match + " of 7 desires."));
    wrap.appendChild(tv);
    var src = el("div", "source");
    src.textContent = "From a recorded run, not this chat: " + p.source + ". Word " + p.status_word + ", verdict " + p.test_verdict + ", limit " + p.claim_ceiling + ". Attention steps during conversation: " + p.attention.steps_in_conversation + ".";
    wrap.appendChild(src);
    var hood = el("details", "hood");
    hood.appendChild(el("summary", null, "Under the hood"));
    hood.appendChild(el("pre", null, "Drives F1-F7 on the open 7-simplex (Correction 4: every coordinate > 0).\nSmallest coordinate of the live point over the life: " + p.attention.min_coord + " (positive: " + p.attention.open_simplex + ").\nInversion pairs: F1<->F7, F2<->F6, F3<->F5; F4 self-dual.\nShown here: " + p.attention.what + "."));
    wrap.appendChild(hood);
    body.appendChild(wrap);
  }

  function radial(att) {
    // Order puts each inversion pair as mirror images: F4 on top; F5|F3, F6|F2, F7|F1 left-right.
    var order = ["F4", "F5", "F6", "F7", "F1", "F2", "F3"];
    var names = {}; FOUND.forEach(function (f) { names[f[0]] = f[1]; });
    var W = 300, H = 270, cx = W / 2, cy = 138, R = 96;
    var shares = {}; var maxS = 0;
    order.forEach(function (f) { shares[f] = att.steps[f] / att.total; if (shares[f] > maxS) maxS = shares[f]; });
    var scale = Math.max(maxS, 1 / 7) * 1.12;
    var s = svg("svg", { viewBox: "0 0 " + W + " " + H, class: "radial", role: "img", "aria-label": "Share of idle attention steps per desire" });
    function pt(i, r) { var a = -Math.PI / 2 + i * 2 * Math.PI / 7; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; }
    [0.5, 1].forEach(function (f) {
      var pts = order.map(function (_, i) { return pt(i, R * f).join(","); }).join(" ");
      s.appendChild(svg("polygon", { points: pts, class: "ring" }));
    });
    var even = order.map(function (_, i) { return pt(i, R * (1 / 7) / scale).join(","); }).join(" ");
    s.appendChild(svg("polygon", { points: even, class: "even" }));
    order.forEach(function (f, i) { var e = pt(i, R); s.appendChild(svg("line", { x1: cx, y1: cy, x2: e[0], y2: e[1], class: "spoke" })); });
    [[1, 6], [2, 5], [3, 4]].forEach(function (pr) {
      var a = pt(pr[0], R + 6), b = pt(pr[1], R + 6);
      s.appendChild(svg("line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: "pair" }));
    });
    var shape = order.map(function (f, i) { return pt(i, R * shares[f] / scale).join(","); }).join(" ");
    s.appendChild(svg("polygon", { points: shape, class: "shape" }));
    order.forEach(function (f, i) {
      var p = pt(i, R * shares[f] / scale);
      var label = names[f] + ": " + att.steps[f].toLocaleString("en-US") + " of " + att.total.toLocaleString("en-US") + " steps (" + fmtPct(att.steps[f], att.total) + ")";
      s.appendChild(svg("circle", { cx: p[0], cy: p[1], r: 4.5, class: "dot" }));
      var hit = svg("circle", { cx: p[0], cy: p[1], r: 12, class: "hit" });
      hover(hit, label);
      s.appendChild(hit);
      var lp = pt(i, R + 22);
      var t = svg("text", { x: lp[0], y: lp[1] + 4, "text-anchor": Math.abs(lp[0] - cx) < 8 ? "middle" : (lp[0] < cx ? "end" : "start") });
      t.textContent = names[f];
      s.appendChild(t);
    });
    return s;
  }

  function heat(p) {
    var g = el("div", "heat");
    g.setAttribute("role", "img");
    g.setAttribute("aria-label", "Which brain job worked for which desire, as worked out of tries");
    g.appendChild(el("div"));
    p.faculties.forEach(function (f) { g.appendChild(el("div", "col", JOB_NAMES[f] || f)); });
    p.grid.forEach(function (row) {
      g.appendChild(el("div", "row", row.name));
      row.cells.forEach(function (c) {
        var d = el("div", "cell");
        if (!c.tries) d.classList.add("void");
        else {
          var pct = Math.round(8 + 92 * c.worked / c.tries);
          d.style.background = "color-mix(in oklab, var(--seq) " + pct + "%, var(--surface-2))";
        }
        if (c.eye_best) d.classList.add("best");
        var txt = row.name + " with " + (JOB_NAMES[c.faculty] || c.faculty) + ": worked " + c.worked + " of " + c.tries + " tries" + (c.tries ? " (" + fmtPct(c.worked, c.tries) + ")" : "") + (c.eye_best ? ". The Eye's best pick" : "") + (c.true_best ? (c.eye_best ? ", and the hidden best." : ". The hidden best.") : ".");
        hover(d, txt);
        g.appendChild(d);
      });
    });
    return g;
  }

  /* ---------------- status strip */
  function renderClaims(claims) {
    var chips = $("stripChips"); chips.innerHTML = "";
    var body = $("claimsBody"); body.innerHTML = "";
    (claims || []).forEach(function (c) {
      var sc = el("span", "sc");
      sc.appendChild(document.createTextNode(c.mark + " " + c.panel + " "));
      sc.appendChild(el("b", null, c.word));
      chips.appendChild(sc);
      var row = el("div", "claim");
      row.appendChild(el("span", "mk", c.mark));
      var hd = el("div", "hd");
      hd.appendChild(el("strong", null, c.panel));
      hd.appendChild(word(c.word));
      if (c.verdict) hd.appendChild(word(c.verdict));
      if (c.status) hd.appendChild(word(c.status));
      if (c.ceiling) hd.appendChild(word(c.ceiling));
      row.appendChild(hd);
      if (c.plain) row.appendChild(el("div", "tx", c.plain));
      if (c.not_licensed) row.appendChild(el("div", "nl", "Not licensed: " + c.not_licensed));
      if (c.source) row.appendChild(el("div", "nl", "Source: " + c.source));
      body.appendChild(row);
    });
    var ceil = el("span", "sc ceiling", "Synthetic worlds only");
    chips.insertBefore(ceil, chips.firstChild);
    var key = el("div", "small");
    key.textContent = "Markers: ✅ confirmed win, 🟩 strong with a named limit, 🟨 partial, 🟧 weak, 🟥 failed (kept on record), ⬜ not validated or not run, 🔧 method win, 🔒 waiting on the owner. The words are copied from the run records; this page never upgrades them.";
    body.appendChild(key);
  }

  function renderState(s) {
    state.lastState = s;
    renderKnows(s.knows, s.wiring);
    renderAttention(s.pairing);
    if (s.dials) renderDials(s.dials);
    renderClaims(s.claims);
    if (s.eye_last && !$("eyeBody").querySelector(".eye-say")) renderEye(s.eye_last);
    if (!DEMO && s.wiring && s.wiring.tools && s.wiring.tools !== "on") {
      $("composerNote").textContent = "Enter to send. Shift + Enter for a new line. Tool actions (files, commands, git) are off in this window.";
    }
  }

  /* ---------------- view tabs and the records toggle */
  var togglers = [];
  document.querySelectorAll(".tab").forEach(function (t) {
    t.addEventListener("click", function () {
      var v = t.getAttribute("data-view");
      document.querySelectorAll(".tab").forEach(function (o) { var on = o === t; o.classList.toggle("on", on); o.setAttribute("aria-selected", on ? "true" : "false"); });
      $("viewChat").hidden = v !== "chat"; $("viewPlan").hidden = v !== "plan";
      (v === "chat" ? $("input") : $("planInput")).focus();
    });
  });
  $("recToggle").addEventListener("click", function () {
    state.showRecords = !state.showRecords;
    $("recToggle").setAttribute("aria-pressed", state.showRecords ? "true" : "false");
    $("recToggle").textContent = state.showRecords ? "Hide records" : "Show records";
    togglers.forEach(function (f) { f(state.showRecords, true); });
    storeSet("helm-records", state.showRecords ? "1" : "0");
  });

  /* ---------------- plan a task */
  var PLAN_EXAMPLES = [
    "Write the code for auth.py, verify the tests pass, then commit it to git.",
    "Before you commit to git, verify the tests pass. Before you verify the tests, write the code for auth.py.",
    "Ω_a needs Ω_b first. Ω_b needs Ω_a first."
  ];
  var REFUSAL_PLAIN = {
    PLAN_CYCLE: "These steps contradict each other: each one is said to come before the other. HELM will not pick an order for a contradiction.",
    PLAN_EMPTY: "There were no steps to plan in that sentence.",
    PLAN_HORIZON: "The chain of steps is too deep for the planner's limit.",
    PLAN_UNDECLARED_OMEGA: "A step was named as a prerequisite but never declared.",
    PLAN_ORDER_VIOLATION: "The safety gate found a step placed before something it needs.",
    PLAN_EDGE_WITHOUT_SOURCE: "An ordering link had no sentence behind it, so it was refused.",
    PLAN_REPAIR_FAILED: "A step failed and its one repair attempt failed too."
  };
  function renderPlanChips() {
    var c = $("planChips"); c.innerHTML = "";
    var list = DEMO ? DEMO.plans.map(function (p) { return p.request; }) : PLAN_EXAMPLES;
    list.forEach(function (s) {
      var b = el("button", "chip", s); b.type = "button";
      b.addEventListener("click", function () { $("planInput").value = s; doPlan(); });
      c.appendChild(b);
    });
  }
  function doPlan() {
    var text = $("planInput").value.trim();
    if (!text) return;
    var b = $("planBtn"); b.disabled = true; b.textContent = "Planning";
    api.plan(text).then(renderPlan).catch(function () { renderPlan({ ok: false, reason: "The local server did not answer." }); })
      .then(function () { b.disabled = false; b.textContent = "Make the plan"; });
  }
  $("planForm").addEventListener("submit", function (e) { e.preventDefault(); doPlan(); });
  $("planInput").addEventListener("keydown", function (e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); doPlan(); } });

  function renderPlan(res) {
    var out = $("planOut"); out.innerHTML = "";
    if (!res.ok) { var p0 = el("div", "panel"); p0.appendChild(el("p", null, res.reason || "The planner did not run.")); out.appendChild(p0); return; }
    if (res.refused) {
      var pr = el("div", "panel refused");
      pr.appendChild(el("h3", null, res.stage === "gate" ? "The safety gate stopped the plan." : "HELM refused to plan this."));
      pr.appendChild(el("p", null, REFUSAL_PLAIN[res.code] || "The planner refused."));
      var w = el("p"); w.appendChild(word(res.code)); w.appendChild(document.createTextNode(" " + res.detail)); pr.appendChild(w);
      out.appendChild(pr);
    }
    if (res.plan) {
      var pp = el("div", "panel");
      pp.appendChild(el("h3", null, res.plan.order.length === 1 ? "One step." : res.plan.order.length + " steps, in this order."));
      if (res.plan.order_source === "NONE") pp.appendChild(el("p", null, "No ordering words were found, so no step depends on another."));
      pp.appendChild(dag(res.plan));
      var steps = el("ol", "steps");
      var dry = res.dry_run ? res.dry_run.steps : [];
      res.plan.order.forEach(function (name, i) {
        var li = el("li");
        var node = res.plan.nodes.filter(function (n) { return n.omega === name; })[0] || {};
        var txt = el("span"); txt.textContent = name + (node.needs && node.needs.length ? "  (after " + node.needs.join(", ") + ")" : "");
        li.appendChild(txt);
        var st = dry[i];
        var gw = el("span");
        if (st) { gw.appendChild(document.createTextNode(st.gate_verdict === "PROCEED" ? "gate: go " : "gate: ")); gw.appendChild(word(st.gate_code)); }
        else gw.appendChild(word("not checked"));
        li.appendChild(gw);
        steps.appendChild(li);
      });
      pp.appendChild(steps);
      pp.appendChild(el("div", "small", "Nothing was run. The safety gate checked each step in order against what earlier steps had produced."));
      var hood = el("details", "hood");
      hood.appendChild(el("summary", null, "Under the hood"));
      hood.appendChild(el("pre", null,
        "order source: " + res.plan.order_source + "\nplan digest: " + res.plan.digest +
        (res.dry_run ? "\ndry-run bias digest: " + res.dry_run.final_bias_digest + " (version " + res.dry_run.final_bias_version + ")" : "") +
        "\nlimit: " + res.claim_ceiling + "\nsource: " + res.source + "\n\n" + JSON.stringify({ plan: res.plan, dry_run: res.dry_run }, null, 1)));
      pp.appendChild(hood);
      out.appendChild(pp);
    }
  }

  function dag(plan) {
    var byName = {}; plan.nodes.forEach(function (n) { byName[n.omega] = n; });
    var cols = {}; plan.order.forEach(function (n) { var d = (byName[n] || {}).depth || 0; (cols[d] = cols[d] || []).push(n); });
    var depths = Object.keys(cols).map(Number).sort(function (a, b) { return a - b; });
    var NW = 132, NH = 44, GX = 64, GY = 18;
    var maxRows = Math.max.apply(null, depths.map(function (d) { return cols[d].length; }));
    var W = depths.length * NW + (depths.length - 1) * GX + 8, H = maxRows * NH + (maxRows - 1) * GY + 8;
    var pos = {};
    depths.forEach(function (d, ci) { cols[d].forEach(function (n, ri) { var off = (maxRows - cols[d].length) * (NH + GY) / 2; pos[n] = [4 + ci * (NW + GX), 4 + off + ri * (NH + GY)]; }); });
    var s = svg("svg", { viewBox: "0 0 " + W + " " + H, class: "dag", role: "img", "aria-label": "Plan graph: " + plan.order.join(", then ") });
    s.style.maxWidth = W + "px";
    var defs = svg("defs", {}); var mk = svg("marker", { id: "ah", viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" });
    mk.appendChild(svg("path", { d: "M0 0L10 5L0 10z", class: "ah" })); defs.appendChild(mk); s.appendChild(defs);
    plan.edges.forEach(function (e) {
      var a = pos[e.before], b = pos[e.after]; if (!a || !b) return;
      var x1 = a[0] + NW, y1 = a[1] + NH / 2, x2 = b[0] - 2, y2 = b[1] + NH / 2, mx = (x1 + x2) / 2;
      var d = "M" + x1 + " " + y1 + " C" + mx + " " + y1 + " " + mx + " " + y2 + " " + x2 + " " + y2;
      s.appendChild(svg("path", { d: d, class: "edge", "marker-end": "url(#ah)" }));
      var hit = svg("path", { d: d, class: "edge-hit" }); hover(hit, e.before + " comes before " + e.after + ". From: “" + e.source + "”"); s.appendChild(hit);
    });
    plan.order.forEach(function (n, i) {
      var p = pos[n]; var g = svg("g", { class: "node", transform: "translate(" + p[0] + "," + p[1] + ")" });
      g.appendChild(svg("rect", { width: NW, height: NH, rx: 10 }));
      var t = svg("text", { x: 14, y: 20 }); t.textContent = n.length > 16 ? n.slice(0, 15) + "…" : n; g.appendChild(t);
      var t2 = svg("text", { x: 14, y: 35, class: "sub" }); t2.textContent = "step " + (i + 1) + " · depth " + ((byName[n] || {}).depth || 0); g.appendChild(t2);
      hover(g, n + ": step " + (i + 1) + ((byName[n] || {}).needs && byName[n].needs.length ? ", needs " + byName[n].needs.join(", ") : ", needs nothing first"));
      s.appendChild(g);
    });
    return s;
  }

  /* ---------------- search dials */
  var DIAL_TEXT = {
    K: ["How many options to try", "few", "many", "Breadth K"],
    rho: ["Willingness to swap one input for another", "strict", "free", "Substitution curvature ρ (CES)"],
    R: ["How far to look", "near", "far", "Search radius R over the atlas"],
    ponder: ["Idle thinking budget", "none", "most", "Idle pondering budget (ticks)"],
    sigma: ["Openness to new ideas", "closed", "open", "Valve saliency σ"]
  };
  var PRESET_TEXT = { CONSERVATIVE: "Conservative", BALANCED: "Balanced", EXPLORATORY: "Exploratory", OUT_OF_THE_BOX: "Out of the box" };
  function renderDials(d, msg) {
    var body = $("dialBody"); body.innerHTML = "";
    if (!d || !d.wired) { body.appendChild(el("div", "empty", (d && d.reason) || "Not wired")); return; }
    var pr = el("div", "presets"); pr.setAttribute("role", "group"); pr.setAttribute("aria-label", "Presets");
    d.presets.forEach(function (p) {
      var b = el("button", d.mode === p ? "on" : "", PRESET_TEXT[p] || p); b.type = "button";
      b.setAttribute("aria-pressed", d.mode === p ? "true" : "false");
      b.addEventListener("click", function () { sendDials({ preset: p }); });
      pr.appendChild(b);
    });
    body.appendChild(pr);
    var now = el("div", "small"); now.style.margin = "-4px 0 6px";
    now.textContent = "Now: " + (PRESET_TEXT[d.mode] || "custom values that match no preset");
    body.appendChild(now);
    ["K", "rho", "R", "ponder", "sigma"].forEach(function (k) {
      var tx = DIAL_TEXT[k], rg = d.ranges[k], row = el("div", "dial");
      var id = "dial-" + k;
      var lab = el("label", null, tx[0]); lab.htmlFor = id; row.appendChild(lab);
      var val = el("span", "val", d.values[k]); row.appendChild(val);
      var inp = document.createElement("input"); inp.type = "range"; inp.id = id;
      if (rg.options) { inp.min = 0; inp.max = rg.options.length - 1; inp.step = 1; inp.value = Math.max(0, rg.options.indexOf(Number(d.values[k]))); }
      else { inp.min = rg.min; inp.max = rg.max; inp.step = rg.step; inp.value = d.values[k]; }
      var current = function () { return rg.options ? rg.options[Number(inp.value)] : (rg.step < 1 ? Number(inp.value).toFixed(rg.step < 0.1 ? 2 : 1) : inp.value); };
      inp.addEventListener("input", function () { val.textContent = current(); });
      inp.addEventListener("change", function () { var b = {}; b[k] = current(); sendDials(b); });
      row.appendChild(inp);
      var ends = el("div", "ends"); ends.appendChild(el("span", null, tx[1])); ends.appendChild(el("span", null, tx[2])); row.appendChild(ends);
      body.appendChild(row);
    });
    body.appendChild(el("div", "dial-msg", msg || ""));
    body.appendChild(el("div", "small", "In this chat the dials only feed the tool planner, and tool actions are off in this window. Changing them never writes to HELM's recipe brain or memory."));
    var hood = el("details", "hood");
    hood.appendChild(el("summary", null, "Under the hood"));
    hood.appendChild(el("pre", null, ["K", "rho", "R", "ponder", "sigma"].map(function (k) { return DIAL_TEXT[k][3] + " = " + d.values[k]; }).join("\n") + "\nmode: " + d.mode + "\nsource: " + d.source + "\nused by: " + d.used_by));
    body.appendChild(hood);
  }
  function sendDials(b) {
    api.setDials(b).then(function (r) { renderDials(r, r.ok ? "" : (r.error || r.reason)); })
      .catch(function () { $("dialBody").querySelector(".dial-msg").textContent = "The local server did not answer."; });
  }

  /* ---------------- start */
  if (/[?&]records=1/.test(window.location.search) || storeGet("helm-records") === "1") $("recToggle").click();
  renderPlanChips();
  var qPlan = /[?&]plan=([^&]*)/.exec(window.location.search);
  if (/[?&]view=plan/.test(window.location.search)) {
    document.querySelector('.tab[data-view="plan"]').click();
    if (qPlan) { $("planInput").value = decodeURIComponent(qPlan[1].replace(/\+/g, " ")); doPlan(); }
  }
  var pill = $("modePill");
  if (DEMO) {
    pill.textContent = "Recorded demo"; pill.classList.remove("live");
    $("composerNote").textContent = "This page replays a real local session recorded " + DEMO.recorded_utc + " (UTC). Use the suggestions above.";
  }
  renderChips();
  api.state().then(function (s) {
    if (!DEMO) { pill.textContent = s.wiring && s.wiring.chat === "wired" ? "Live on this laptop" : "HELM not wired"; pill.classList.toggle("live", s.wiring && s.wiring.chat === "wired"); }
    renderState(s);
    return api.history();
  }).then(function (rows) {
    (rows || []).forEach(function (r) {
      addUser(r.you_said, true);
      addHelm({ ok: true, kind: "reply", reply: r.reply, record: r.record && r.record.status_plain ? r.record : null }, null, true);
    });
  }).catch(function () {
    pill.textContent = "Server not reachable";
    renderKnows(null, { chat: "the local server did not answer" });
    renderAttention({ wired: false, reason: "The local server did not answer." });
  });
})();
