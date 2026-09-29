/* Brain Terminal front end. Vanilla JS; every value from the server is escaped with esc(). */
"use strict";

const SCREENS = ["HOME", "RUNS", "TASKS", "SKILLS", "MARKETS", "LAB", "LEARN", "SETTINGS"];
const state = {
  screen: "HOME",
  liveEvents: [],
  selectedRun: null,
  marketSymbol: "SPY",
  marketRange: "5Y",
  marketMode: "candles",
  selectedBacktest: null,
  learn: { selected: new Set(), messages: [], backend: "claude", busy: false, sources: null },
  unseenEvents: 0,
};
const charts = [];

// ---------- helpers ----------
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n, d = 2) => (n === null || n === undefined || Number.isNaN(n) ? "—" : Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }));
const pct = (n, d = 1) => (n === null || n === undefined ? "—" : `${n >= 0 ? "+" : ""}${(n * 100).toFixed(d)}%`);
const short = (s, n = 12) => (s && s.length > n ? s.slice(0, n) + "…" : s ?? "");
const when = (iso) => {
  if (!iso) return "—";
  const d = new Date(String(iso).replace(" ", "T") + (/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? "" : "Z"));
  if (Number.isNaN(d.getTime())) return esc(iso);
  const s = (Date.now() - d.getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return d.toISOString().slice(0, 10);
};
const statusClass = (s) => ({ completed: "ok", passed: "ok", accepted: "ok", done: "ok", ready: "warn", running: "inf", started: "inf", queued: "dim", refused: "warn", failed: "bad", invalid: "bad", incomplete: "warn", unregistered: "warn" }[String(s).toLowerCase()] || "dim");
const pill = (s) => `<span class="pill ${statusClass(s)}">${esc(s)}</span>`;

async function api(path, opts = {}) {
  const res = await fetch(path, { ...opts, headers: { "Content-Type": "application/json", "X-Brain-Terminal": "1", ...(opts.headers || {}) } });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (e) { /* not json */ }
    throw new Error(detail);
  }
  return res.json();
}
const post = (path, body, method = "POST") => api(path, { method, body: JSON.stringify(body ?? {}) });

function pane(title, body, { small = "", cls = "" } = {}) {
  return `<section class="pane ${cls}"><h3>${title}${small ? `<small>${small}</small>` : ""}</h3><div class="body">${body}</div></section>`;
}
const empty = (title, text) => `<div class="empty"><b>${esc(title)}</b><span>${text}</span></div>`;
const errBox = (e) => `<p class="error">${esc(e.message || e)}</p>`;

function clearCharts() { while (charts.length) { try { charts.pop().remove(); } catch (e) { /* gone */ } } }

// ---------- navigation ----------
function buildKeys() {
  const nav = $("#keys");
  nav.innerHTML = SCREENS.map((s, i) => `<button role="tab" id="key-${s}" data-screen="${s}"><span>F${i + 1}</span>${s}</button>`).join("");
  nav.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) show(b.dataset.screen); });
}
function show(screen, opts = {}) {
  if (!SCREENS.includes(screen)) return;
  state.screen = screen;
  if (screen === "RUNS") state.unseenEvents = 0;
  SCREENS.forEach((s) => $(`#key-${s}`).setAttribute("aria-selected", s === screen));
  updateBadges();
  try { localStorage.setItem("bt-screen", screen); } catch (e) { /* storage blocked */ }
  history.replaceState(null, "", `#${screen.toLowerCase()}`);
  clearCharts();
  const main = $("#screen");
  main.innerHTML = `<p class="dim">Loading ${esc(screen)}…</p>`;
  RENDER[screen](main, opts).catch((e) => { main.innerHTML = errBox(e); });
}
function updateBadges() {
  const k = $("#key-RUNS");
  if (k) k.innerHTML = `<span>F2</span>RUNS${state.unseenEvents ? `<em class="badge">${state.unseenEvents}</em>` : ""}`;
}

document.addEventListener("keydown", (e) => {
  const m = /^F([1-8])$/.exec(e.key);
  if (m) { e.preventDefault(); show(SCREENS[Number(m[1]) - 1]); return; }
  if (e.key === "Escape") closeViewer();
  if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") { e.preventDefault(); $("#cmd").focus(); }
});

$("#cmd-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const raw = $("#cmd").value.trim();
  $("#cmd").value = "";
  if (!raw) return;
  const up = raw.toUpperCase();
  const f = /^F([1-8])$/.exec(up);
  if (f) return show(SCREENS[Number(f[1]) - 1]);
  if (SCREENS.includes(up)) return show(up);
  if (raw.startsWith("?") || /^(LEARN|ASK|EXPLAIN|WHY|HOW|WHAT)\b/i.test(raw)) {
    const q = raw.replace(/^\?\s*/, "").replace(/^learn\s+/i, "");
    return show("LEARN", { question: q });
  }
  if (/^RUN-/i.test(raw)) { state.selectedRun = "RUN-" + raw.slice(4).toLowerCase(); return show("RUNS"); }
  if (/^(SC-|BT-)/i.test(raw)) return show("LAB");
  if (/^[A-Z]{1,5}$/.test(up)) { state.marketSymbol = up; return show("MARKETS"); }
  show("LEARN", { question: raw });
});

// ---------- live stream ----------
function connectStream() {
  const status = $("#status-live");
  const src = new EventSource("/api/stream");
  src.onopen = () => { status.className = "status live"; status.querySelector("span").textContent = "live"; };
  src.onerror = () => { status.className = "status down"; status.querySelector("span").textContent = "reconnecting"; };
  src.addEventListener("harness", (e) => {
    const ev = JSON.parse(e.data);
    state.liveEvents.unshift(ev);
    state.liveEvents = state.liveEvents.slice(0, 100);
    if (state.screen !== "RUNS") { state.unseenEvents += 1; updateBadges(); }
    const feed = $("#live-feed");
    if (feed) { feed.insertAdjacentHTML("afterbegin", eventRow(ev, true)); }
    const hf = $("#home-live");
    if (hf) hf.insertAdjacentHTML("afterbegin", eventRow(ev, true, true));
  });
  src.addEventListener("job", (e) => {
    const run = JSON.parse(e.data);
    toast(`${run.job_id}: ${run.status}${run.summary ? " — " + run.summary : ""}`, statusClass(run.status));
    if (state.screen === "TASKS" || state.screen === "HOME") show(state.screen);
  });
  src.addEventListener("git", (e) => {
    const g = JSON.parse(e.data);
    toast(`New commit ${g.head}`, "inf");
    refreshFooter();
  });
}

function toast(text, cls = "") {
  let box = $("#toasts");
  if (!box) {
    box = document.createElement("div");
    box.id = "toasts";
    box.style.cssText = "position:fixed;right:16px;bottom:40px;display:grid;gap:6px;z-index:60;max-width:min(460px,90vw)";
    document.body.append(box);
  }
  const t = document.createElement("div");
  t.className = `pane ${cls}`;
  t.style.cssText = "padding:8px 12px;border-color:currentColor";
  t.textContent = text;
  box.append(t);
  setTimeout(() => t.remove(), 7000);
}

async function refreshFooter() {
  try {
    const home = await api("/api/home");
    $("#foot-root").textContent = `brain: ${home.project_root}`;
    $("#foot-git").textContent = `git: ${home.git.branch} @ ${home.git.head} · ${home.git.changes.length} uncommitted`;
  } catch (e) { $("#foot-git").textContent = "server unreachable"; }
}
setInterval(() => { $("#clock").textContent = new Date().toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit", second: "2-digit" }); }, 1000);

// ---------- file viewer ----------
let viewerPath = null;
async function openFile(path, line) {
  viewerPath = path;
  $("#viewer-title").textContent = path;
  $("#viewer-body").innerHTML = "Loading…";
  $("#viewer").hidden = false;
  try {
    const f = await api(`/api/file?path=${encodeURIComponent(path)}`);
    const [a, b] = String(line || "").split("-").map(Number);
    $("#viewer-body").innerHTML = f.text.split("\n").map((l, i) => {
      const n = i + 1;
      const hit = a && n >= a && n <= (b || a);
      return `<span class="ln${hit ? " hit" : ""}" data-n="${n}" id="L${n}">${esc(l) || " "}</span>`;
    }).join("");
    if (a) $(`#L${a}`)?.scrollIntoView({ block: "center" });
  } catch (e) { $("#viewer-body").innerHTML = errBox(e); }
}
function closeViewer() { $("#viewer").hidden = true; }
$("#viewer-close").onclick = closeViewer;
$("#viewer").addEventListener("click", (e) => { if (e.target.id === "viewer") closeViewer(); });
$("#viewer-learn").onclick = () => { closeViewer(); state.learn.selected.add(viewerPath); show("LEARN", { question: `Explain ${viewerPath} to me: what it is for and how it fits the project.` }); };
document.addEventListener("click", (e) => {
  const f = e.target.closest("[data-file]");
  if (f) { e.preventDefault(); openFile(f.dataset.file, f.dataset.line); }
});
const fileLink = (path, label) => `<a href="#" data-file="${esc(path)}">${esc(label || path)}</a>`;

// ---------- screens ----------
const RENDER = {};

function eventRow(ev, flash = false, compact = false) {
  const cls = flash ? "flash" : "";
  if (compact) return `<tr class="${cls}"><td class="dim">${esc(when(ev.created_at))}</td><td>${esc(ev.agent_role)}</td><td class="${statusClass(ev.status)}">${esc(ev.status)}</td><td class="wrap">${esc(short(ev.message || ev.event_type, 90))}</td></tr>`;
  return `<tr class="${cls}"><td class="dim">${esc(ev.event_id)}</td><td class="dim">${esc(String(ev.created_at || "").slice(5, 19))}</td><td>${esc(ev.run_id)}</td><td>${esc(ev.agent_role)}</td><td>${esc(ev.stage)}</td><td class="${statusClass(ev.status)}">${esc(ev.status)}</td><td class="wrap">${esc(short(ev.message || ev.event_type, 140))}</td></tr>`;
}

RENDER.HOME = async (main) => {
  const d = await api("/api/home");
  const c = d.counts;
  const chain = d.pipeline.map((s) => `<div class="stage ${s.state}"><b>${esc(s.label)}</b><span>${esc(s.count)} ${esc(s.noun)}</span></div>`).join("");
  const health = d.last_health
    ? `<p>${pill(d.last_health.status)} <span class="dim">${esc(when(d.last_health.finished_at))}</span></p><p class="wrap">${esc(d.last_health.summary)}</p>`
    : `<p class="dim">No health check has run yet. Run one from TASKS (F3).</p>`;
  const runs = d.runs.length ? `<table><tr><th>Run</th><th>Agent</th><th>Status</th><th>Last</th></tr>${d.runs.map((r) => `<tr class="click" data-run="${esc(r.run_id)}"><td>${esc(r.run_id)}</td><td title="${esc(r.agents)}">${esc(short(r.agents, 18))}</td><td>${pill(r.final_status)}</td><td class="dim">${esc(when(r.last_at))}</td></tr>`).join("")}</table>` : `<p class="dim">No harness runs recorded.</p>`;
  const jobsTable = d.recent_jobs.length ? `<table>${d.recent_jobs.map((r) => `<tr><td>${esc(r.job_id)}</td><td>${pill(r.status)}</td><td class="dim">${esc(when(r.started_at))}</td></tr>`).join("")}</table>` : `<p class="dim">No terminal jobs yet.</p>`;
  const commits = d.git.commits.slice(0, 6).map((g) => `<tr><td class="warn">${esc(g.short)}</td><td class="dim">${esc(when(g.date))}</td><td class="wrap">${esc(g.subject)}</td></tr>`).join("");
  main.innerHTML = `<div class="grid">
    ${pane("Pipeline", `<div class="chain">${chain}</div><p class="note">Each stage lights up from what the database actually holds, not from a plan.</p>`, { small: "research → data → card → backtest → review", cls: "full" })}
    ${pane("Next step", `<p>${esc(d.checkpoint.next || "Not stated in PLAN.md §10")}</p><table>${d.checkpoint.entries.map((e) => `<tr><td class="dim">§10</td><td class="wrap">${esc(e)}</td></tr>`).join("")}</table>`, { small: "PLAN.md §10" })}
    ${pane("Brain", `<div class="stats">${[["sources", c.sources], ["chunks", c.chunks], ["datasets", c.price_datasets], ["cards", c.strategy_cards], ["backtests", c.backtests], ["reviews", c.reviews], ["events", c.agent_events]].map(([k, v]) => `<div><b>${esc(v)}</b><span>${k}</span></div>`).join("")}</div>`, { small: "brain.sqlite, read-only" })}
    ${pane("Health", health, { small: "last health_check job" })}
    ${pane("Live events", `<table id="home-live">${state.liveEvents.slice(0, 8).map((e) => eventRow(e, false, true)).join("") || ""}</table><p class="dim">${state.liveEvents.length ? "" : "Waiting for new harness events…"}</p>`, { small: "streams as agents run" })}
    ${pane("Recent harness runs", runs)}
    ${pane("Terminal jobs", jobsTable)}
    ${pane("Commits", `<table>${commits}</table>`, { small: `${esc(d.git.branch)} · ${d.git.changes.length} uncommitted` })}
  </div>`;
  main.querySelectorAll("[data-run]").forEach((tr) => tr.addEventListener("click", () => { state.selectedRun = tr.dataset.run; show("RUNS"); }));
};

RENDER.RUNS = async (main) => {
  const [runs, activity] = await Promise.all([api("/api/runs?limit=80"), api("/api/activity")]);
  if (!state.selectedRun && runs.length) state.selectedRun = runs[0].run_id;
  const list = runs.map((r) => `<tr class="click ${r.run_id === state.selectedRun ? "sel" : ""}" data-run="${esc(r.run_id)}" title="last event ${esc(r.last_at)}"><td>${esc(r.run_id)}<br><span class="dim">${esc(when(r.last_at))}</span></td><td>${pill(r.final_status)}</td><td class="num dim">${esc(r.event_count)}</td></tr>`).join("");
  const sessionBlock = (s) => `<details><summary><b>${esc(s.agent)}</b> · ${esc(s.title || "untitled")} <span class="dim">· ${esc(when(s.last_at))} · ${esc(s.tool_calls)} tool calls${s.edits != null ? ` · ${esc(s.edits)} edits` : ""}</span></summary>
      ${s.prompt ? `<p class="note">${esc(short(s.prompt, 300))}</p>` : ""}
      <table>${s.activity.slice().reverse().map((a) => `<tr><td class="dim">${esc(String(a.time).slice(11, 19))}</td><td class="wrap">${esc(a.what)}</td></tr>`).join("")}</table></details>`;
  const codex = activity.codex.length ? activity.codex.map(sessionBlock).join("") : `<p class="dim">No Codex session logs for this repo in ~/.codex/sessions. If Codex runs in the cloud or on another machine, its work still shows up here as commits and uncommitted changes.</p>`;
  const claude = activity.claude.length ? activity.claude.map(sessionBlock).join("") : `<p class="dim">No Claude Code sessions for this repo.</p>`;
  const g = activity.git;
  main.innerHTML = `<div class="grid side">
    ${pane("Harness runs", `<div class="scroll tall"><table><tr><th>Run</th><th>Status</th><th class="num">Events</th></tr>${list}</table></div>`, { small: `${runs.length} runs` })}
    <div class="grid" style="grid-template-columns:1fr">
      <div id="run-detail"></div>
      ${pane("Live feed", `<div class="scroll"><table id="live-feed">${state.liveEvents.map((e) => eventRow(e)).join("")}</table></div><p class="dim">${state.liveEvents.length ? "" : "New harness events appear here the moment they are recorded."}</p>`, { small: "agent_events, streaming" })}
      <div class="grid two">
        ${pane("Working tree", `<p class="dim">${esc(g.branch)} @ ${esc(g.head)}</p><div class="scroll"><table>${g.changes.map((c) => `<tr><td class="warn">${esc(c.code)}</td><td class="wrap">${esc(c.path)}</td></tr>`).join("") || `<tr><td class="dim">clean</td></tr>`}</table></div>`, { small: "what agents are changing now" })}
        ${pane("Commits", `<div class="scroll"><table>${g.commits.map((c) => `<tr><td class="warn">${esc(c.short)}</td><td class="dim">${esc(when(c.date))}</td><td class="wrap">${esc(c.subject)}</td></tr>`).join("")}</table></div>`)}
      </div>
      ${pane("Claude Code sessions", `<div class="scroll">${claude}</div>`, { small: "~/.claude/projects" })}
      ${pane("Codex sessions", codex, { small: "~/.codex/sessions" })}
    </div></div>`;
  main.querySelectorAll("[data-run]").forEach((tr) => tr.addEventListener("click", () => { state.selectedRun = tr.dataset.run; show("RUNS"); }));
  if (state.selectedRun) renderRunDetail(state.selectedRun);
};

async function renderRunDetail(runId) {
  const box = $("#run-detail");
  try {
    const d = await api(`/api/runs/${encodeURIComponent(runId)}`);
    const rows = d.events.map((e) => `<tr class="click" data-ev="${esc(e.event_id)}"><td class="dim">${esc(String(e.created_at).slice(11, 19))}</td><td>${esc(e.stage)}</td><td>${esc(e.event_type)}</td><td class="${statusClass(e.status)}">${esc(e.status)}</td><td class="wrap">${esc(short(e.message || "", 160))}</td></tr><tr hidden id="ev-${esc(e.event_id)}"><td colspan="5"><pre class="mono-block">${esc(JSON.stringify(e.payload, null, 2))}</pre></td></tr>`).join("");
    box.innerHTML = pane(`Run ${esc(runId)}`, `<div class="row">${d.receipt ? `<button class="btn" data-file="${esc(d.receipt)}">Open receipt</button>` : ""}<button class="btn primary" id="explain-run">Explain this run</button><span class="dim">Click an event to see its payload.</span></div><div class="scroll"><table><tr><th>Time</th><th>Stage</th><th>Event</th><th>Status</th><th>Message</th></tr>${rows}</table></div>`, { small: `${d.events.length} events` });
    box.querySelectorAll("[data-ev]").forEach((tr) => tr.addEventListener("click", () => { const p = $(`#ev-${tr.dataset.ev}`); p.hidden = !p.hidden; }));
    $("#explain-run").onclick = () => {
      if (d.receipt) state.learn.selected.add(d.receipt);
      state.learn.selected.add(`run:${runId}`);
      show("LEARN", { question: `Explain run ${runId} step by step: what it tried, where it failed or succeeded, and why.` });
    };
  } catch (e) { box.innerHTML = pane(`Run ${esc(runId)}`, errBox(e)); }
}

RENDER.TASKS = async (main) => {
  const [d, t] = await Promise.all([api("/api/schedules"), api("/api/tasks")]);
  const lastRun = (id) => d.runs.find((r) => r.job_id === id);
  const rows = d.schedules.map((s) => {
    const lr = lastRun(s.job_id);
    const toggle = s.kind_enabled
      ? `<button class="btn small" data-toggle="${esc(s.job_id)}">${s.enabled ? "Turn off" : "Turn on"}</button>`
      : `<span class="pill warn" title="${esc(d.kinds.find((k) => k.kind === s.kind)?.description)}">frozen by PROP-007</span>`;
    return `<tr><td><b>${esc(s.name)}</b><br><span class="dim">${esc(s.job_id)}</span></td><td>${esc(s.kind)}</td><td>${esc(s.cadence_text)}</td>
      <td>${s.enabled ? pill("on") : `<span class="pill dim">off</span>`}</td>
      <td class="dim">${s.task ? esc(s.task.next_run) : "—"}</td>
      <td>${lr ? `${pill(lr.status)} <span class="dim">${esc(when(lr.started_at))}</span>` : `<span class="dim">never</span>`}</td>
      <td><div class="row">${toggle}${s.kind_enabled ? `<button class="btn small" data-run-now="${esc(s.job_id)}">Run now</button>` : ""}<button class="btn small" data-edit="${esc(s.job_id)}">Edit</button></div></td></tr>`;
  }).join("");
  const runsTable = d.runs.map((r) => `<tr class="click" data-log="${esc(r.run_id)}"><td class="dim">${esc(String(r.started_at).slice(0, 19).replace("T", " "))}</td><td>${esc(r.job_id)}</td><td>${esc(r.trigger)}</td><td>${pill(r.status)}</td><td class="wrap">${esc(short(r.summary || "", 180))}</td><td>${r.output_path ? fileLinkMaybe(r.output_path) : ""}</td></tr>`).join("");
  const drift = d.scheduler.drift.length ? `<p class="warn">Task Scheduler drift: ${d.scheduler.drift.map(esc).join("; ")}</p>` : "";
  const sched = d.scheduler.available ? `<p class="note">Turning a schedule on registers it in Windows Task Scheduler under \\QuantBrain\\, so it runs even when this terminal is closed. Every run is capped, logged, and recorded as a harness event.</p>` : `<p class="warn">Windows Task Scheduler is not available here. Jobs can still run with “Run now”.</p>`;
  main.innerHTML = `<div class="grid">
    ${pane("Schedules", `${drift}<div class="row"><button class="btn primary" id="new-schedule">New schedule</button><span class="grow"></span></div><div id="schedule-form"></div><table><tr><th>Job</th><th>Kind</th><th>When</th><th>State</th><th>Next run</th><th>Last run</th><th></th></tr>${rows}</table>${sched}`, { small: "db/terminal.sqlite → Task Scheduler", cls: "full" })}
    ${pane("Job runs", `<div class="scroll"><table><tr><th>Started (UTC)</th><th>Job</th><th>Trigger</th><th>Status</th><th>Summary</th><th>Output</th></tr>${runsTable || `<tr><td class="dim" colspan="6">No runs yet.</td></tr>`}</table></div><div id="job-log"></div>`, { small: "click a run for its log", cls: "full" })}
    ${pane("Harness task queue", `<div class="scroll"><table><tr><th>Task</th><th>Agent</th><th>Status</th><th>Model</th><th>Error</th></tr>${t.agent_tasks.map((x) => `<tr><td>${esc(x.task_id)}</td><td>${esc(x.agent_role)}</td><td>${pill(x.status)}</td><td class="dim">${esc(x.model || "—")}</td><td class="dim" title="${esc(x.error || "")}">${esc(short(x.error || "", 40))}</td></tr>`).join("")}</table></div>`, { small: "agent_tasks" })}
    ${pane("Research questions", `<div class="scroll"><table><tr><th>ID</th><th>Status</th><th>Question</th></tr>${t.research_questions.map((q) => `<tr><td>${esc(q.research_id)}</td><td>${pill(q.status)}</td><td class="wrap">${esc(short(q.question, 160))}</td></tr>`).join("")}</table></div>`, { small: "research_questions" })}
  </div>`;
  $("#new-schedule").onclick = () => scheduleForm(d);
  main.querySelectorAll("[data-edit]").forEach((b) => (b.onclick = () => scheduleForm(d, d.schedules.find((s) => s.job_id === b.dataset.edit))));
  main.querySelectorAll("[data-toggle]").forEach((b) => (b.onclick = async () => {
    const s = d.schedules.find((x) => x.job_id === b.dataset.toggle);
    b.disabled = true;
    try { await post(`/api/schedules/${s.job_id}`, { enabled: !s.enabled }, "PUT"); toast(`${s.job_id} turned ${s.enabled ? "off" : "on"}`, "ok"); } catch (e) { toast(e.message, "bad"); }
    show("TASKS");
  }));
  main.querySelectorAll("[data-run-now]").forEach((b) => (b.onclick = async () => {
    b.disabled = true; b.textContent = "Starting…";
    try { await post(`/api/schedules/${b.dataset.runNow}/run`); toast(`${b.dataset.runNow} started. The result appears here when it finishes.`, "inf"); } catch (e) { toast(e.message, "bad"); }
    setTimeout(() => show("TASKS"), 1200);
  }));
  main.querySelectorAll("[data-log]").forEach((tr) => tr.addEventListener("click", async () => {
    try { const l = await api(`/api/job-runs/${tr.dataset.log}/log`); $("#job-log").innerHTML = `<pre class="mono-block">${esc(l.log)}</pre>`; } catch (e) { $("#job-log").innerHTML = errBox(e); }
  }));
};
const fileLinkMaybe = (p) => (String(p).startsWith("terminal/") ? `<span class="dim">${esc(p)}</span>` : fileLink(p));

function scheduleForm(d, s = null) {
  const box = $("#schedule-form");
  const kinds = d.kinds.filter((k) => k.enabled || (s && s.kind === k.kind));
  const c = s?.cadence || { type: "daily", time: "09:00" };
  const cfg = s?.config || {};
  box.innerHTML = `<form class="pane" id="sf" style="margin:8px 0;padding:10px"><div class="form">
    <label class="field">ID<input type="text" id="sf-id" value="${esc(s?.job_id || "")}" ${s ? "disabled" : ""} placeholder="e.g. morning-digest" required></label>
    <label class="field">Name<input type="text" id="sf-name" value="${esc(s?.name || "")}" required></label>
    <label class="field">Kind<select id="sf-kind">${kinds.map((k) => `<option value="${k.kind}" ${s?.kind === k.kind ? "selected" : ""}>${esc(k.label)}</option>`).join("")}</select></label>
    <label class="field">Repeats<select id="sf-type">${["daily", "weekdays", "weekly", "hourly"].map((t) => `<option ${c.type === t ? "selected" : ""}>${t}</option>`).join("")}</select></label>
    <label class="field">Time<input type="time" id="sf-time" value="${esc(c.time || "09:00")}"></label>
    <label class="field">Days (weekly)<input type="text" id="sf-days" value="${esc((c.days || ["SAT"]).join(","))}"></label>
    <label class="field">Every N hours<input type="number" id="sf-every" min="1" max="23" value="${esc(c.every || 6)}"></label>
    <label class="field">Max runs / 24h<input type="number" id="sf-max" min="1" max="48" value="${esc(s?.max_runs_per_day || 4)}"></label>
  </div>
  <div id="sf-config" style="margin-top:10px"></div>
  <div class="row" style="margin-top:10px"><label class="check"><input type="checkbox" id="sf-enabled" ${s?.enabled ? "checked" : ""}> On (registers with Task Scheduler)</label><span class="grow"></span>
  ${s ? `<button type="button" class="btn" id="sf-delete">Delete</button>` : ""}<button type="button" class="btn" id="sf-cancel">Cancel</button><button class="btn primary">Save</button></div><p class="error" id="sf-err"></p></form>`;
  const renderCfg = () => {
    const kind = $("#sf-kind").value;
    const el = $("#sf-config");
    if (kind === "data_refresh") el.innerHTML = `<div class="form"><label class="field">Symbols<input type="text" id="cf-symbols" value="${esc((cfg.symbols || ["SPY", "QQQ", "IWM"]).join(" "))}"></label><label class="field">Start date<input type="text" id="cf-start" value="${esc(cfg.start || "2000-01-01")}"></label></div><p class="note">Each refresh writes new immutable datasets (Gate F rules). Old ones are never overwritten.</p>`;
    else if (kind === "agent_prompt") el.innerHTML = `<label class="field">Prompt<textarea id="cf-prompt" rows="3">${esc(cfg.prompt || "")}</textarea></label><div class="row" style="margin-top:6px">${Object.entries(d.context_options).map(([k, v]) => `<label class="check" title="${esc(v)}"><input type="checkbox" class="cf-ctx" value="${k}" ${(cfg.context || []).includes(k) ? "checked" : ""}> ${esc(k)}</label>`).join("")}</div><p class="note">Runs through your Claude login with tools disabled. Output is saved under terminal/scheduled/ and is never promoted to evidence.</p>`;
    else el.innerHTML = `<p class="note">${esc(d.kinds.find((k) => k.kind === kind)?.description)}</p>`;
  };
  $("#sf-kind").onchange = renderCfg;
  renderCfg();
  $("#sf-cancel").onclick = () => (box.innerHTML = "");
  if (s) $("#sf-delete").onclick = async () => { await api(`/api/schedules/${s.job_id}`, { method: "DELETE" }); show("TASKS"); };
  $("#sf").onsubmit = async (e) => {
    e.preventDefault();
    const kind = $("#sf-kind").value;
    const type = $("#sf-type").value;
    const cadence = type === "hourly" ? { type, every: Number($("#sf-every").value) } : type === "weekly" ? { type, time: $("#sf-time").value, days: $("#sf-days").value.split(/[ ,]+/).filter(Boolean) } : { type, time: $("#sf-time").value };
    const config = kind === "data_refresh" ? { symbols: $("#cf-symbols").value.toUpperCase().split(/[ ,]+/).filter(Boolean), start: $("#cf-start").value }
      : kind === "agent_prompt" ? { prompt: $("#cf-prompt").value, context: [...document.querySelectorAll(".cf-ctx:checked")].map((x) => x.value), backend: "claude" } : {};
    const body = { job_id: s?.job_id || $("#sf-id").value.trim(), name: $("#sf-name").value.trim(), kind, cadence, config, enabled: $("#sf-enabled").checked, max_runs_per_day: Number($("#sf-max").value) };
    try { await (s ? post(`/api/schedules/${s.job_id}`, body, "PUT") : post("/api/schedules", body)); show("TASKS"); } catch (err) { $("#sf-err").textContent = err.message; }
  };
}

RENDER.SKILLS = async (main) => {
  const d = await api("/api/skills");
  const list = (items, origin = true) => `<input type="text" class="skill-filter" placeholder="Filter" style="width:100%;margin-bottom:6px"><div class="scroll tall"><table>${items.map((s) => `<tr data-name="${esc((s.name + " " + (s.description || "")).toLowerCase())}"><td><b>${esc(s.name)}</b>${origin ? ` <span class="pill dim">${esc(s.origin)}</span>` : ""}<br><span class="dim wrap" style="white-space:normal">${esc(s.description || "")}</span></td></tr>`).join("") || `<tr><td class="dim">None found.</td></tr>`}</table></div>`;
  const harness = d.harness.map((a) => a.error ? `<p class="error">${esc(a.error)}</p>` : `<div style="margin-bottom:10px"><div class="row"><b class="warn">${esc(a.name)}</b>${a.enabled ? pill("enabled") : `<span class="pill dim">disabled</span>`}<span class="grow"></span>${fileLink(a.path, "definition")}</div>
     <table><tr><td class="dim">handles</td><td>${esc(a.handles.join(", "))}</td></tr><tr><td class="dim">model</td><td>${esc(a.model || "deterministic")}</td></tr>
     <tr><td class="dim">reads</td><td class="wrap">${esc(a.read_paths.join(", "))}</td></tr><tr><td class="dim">writes</td><td class="wrap">${esc(a.write_paths.join(", ") || "nothing")}</td></tr></table></div>`).join("");
  main.innerHTML = `<div class="grid">
    ${pane("Harness agents", `${harness}<p class="note">Registered in agents/*.md. The dispatcher matches a task's type to what an agent handles and enforces its read and write paths.</p>`, { small: `${d.harness.length} registered` })}
    ${pane("Claude Code skills", list(d.claude), { small: `${d.claude.length} · ~/.claude/skills` })}
    ${pane("Codex skills", list(d.codex), { small: `${d.codex.length} · ~/.codex/skills` })}
  </div>`;
  main.querySelectorAll(".skill-filter").forEach((inp) => inp.addEventListener("input", () => {
    const q = inp.value.toLowerCase();
    inp.nextElementSibling.querySelectorAll("tr[data-name]").forEach((tr) => (tr.hidden = !tr.dataset.name.includes(q)));
  }));
};

// ---------- markets ----------
const CHART_OPTS = () => ({
  layout: { background: { color: "#111513" }, textColor: "#8a948d", fontFamily: "Cascadia Mono, Consolas, monospace", fontSize: 11 },
  grid: { vertLines: { color: "#1b221e" }, horzLines: { color: "#1b221e" } },
  rightPriceScale: { borderColor: "#26302b" },
  timeScale: { borderColor: "#26302b" },
  crosshair: { mode: 0 },
});
const RANGES = { "1Y": 365, "5Y": 1826, "10Y": 3652, MAX: null };
const SERIES_COLORS = ["#ffb238", "#6cc3ff", "#4fd18b", "#d58cff", "#ff8a65"];
const barsCache = {};
async function getBars(id) { if (!barsCache[id]) barsCache[id] = await api(`/api/datasets/${encodeURIComponent(id)}/bars`); return barsCache[id]; }
const cutRange = (bars, key) => {
  if (!RANGES[key]) return bars;
  const last = new Date(bars[bars.length - 1].time);
  const from = new Date(last.getTime() - RANGES[key] * 86400000).toISOString().slice(0, 10);
  return bars.filter((b) => b.time >= from);
};

RENDER.MARKETS = async (main) => {
  const ds = await api("/api/datasets");
  const accepted = ds.filter((d) => d.state === "accepted");
  const latest = {};
  accepted.forEach((d) => { if (!latest[d.symbol] || d.downloaded_at > latest[d.symbol].downloaded_at) latest[d.symbol] = d; });
  const symbols = Object.keys(latest).sort();
  if (!symbols.includes(state.marketSymbol)) state.marketSymbol = symbols[0];
  const prov = ds.map((d) => `<tr><td><b>${esc(d.symbol || "?")}</b></td><td>${esc(d.dataset_id)}</td><td>${esc(d.first_date)} → ${esc(d.last_date)}</td><td class="num">${fmt(d.rows, 0)}</td><td>${esc(d.provider)}</td><td>${esc(d.price_basis)}</td><td>${pill(d.state)}</td><td class="dim">${esc(short(d.file_sha256, 12))}</td><td class="${d.warnings.length ? "warn" : "dim"}">${d.warnings.length}</td><td class="dim">${esc(d.cross_check || "—")}</td></tr>${d.problems.length ? `<tr><td></td><td colspan="9" class="bad wrap">${esc(d.problems.join("; "))}</td></tr>` : ""}`).join("");
  if (!symbols.length) {
    main.innerHTML = `<div class="grid">${pane("Markets", empty("No accepted datasets", "Fetch data with a data_refresh job in TASKS (F3), or run scripts/fetch_market_data.py."), { cls: "full" })}${pane("Datasets", `<table>${prov}</table>`, { cls: "full" })}</div>`;
    return;
  }
  const mode = (m, label) => `<button class="btn" aria-pressed="${state.marketMode === m}" data-mode="${m}">${label}</button>`;
  main.innerHTML = `<div class="grid">
    ${pane(`<span id="mk-title">${esc(state.marketSymbol)}</span>`, `<div class="row">
        <div class="seg">${symbols.map((s) => `<button class="btn" aria-pressed="${s === state.marketSymbol}" data-sym="${esc(s)}">${esc(s)}</button>`).join("")}</div>
        <div class="seg">${mode("candles", "Candles")}${mode("compare", "Compare")}${mode("drawdown", "Drawdown")}</div>
        <div class="seg">${Object.keys(RANGES).map((r) => `<button class="btn" aria-pressed="${r === state.marketRange}" data-range="${r}">${r}</button>`).join("")}</div>
        <span class="grow"></span><span class="dim" id="mk-note"></span></div>
      <div class="stats" id="mk-stats" style="margin:10px 0"></div>
      <div class="legend" id="mk-legend"></div>
      <div id="mk-chart" class="chart"></div>
      <p class="note">Candles use Yahoo's split-adjusted OHLC. Compare and drawdown use the dividend-adjusted close (total return). Display only: nothing here trades.</p>`, { small: `dataset ${esc(latest[state.marketSymbol].dataset_id)}`, cls: "full" })}
    ${pane("Datasets & provenance", `<table><tr><th>Sym</th><th>Dataset</th><th>Range</th><th class="num">Rows</th><th>Source</th><th>Basis</th><th>State</th><th>sha256</th><th>Warn</th><th>Cross-check</th></tr>${prov}</table><p class="note">Only datasets whose file, manifest and database row agree are "accepted", and only those can be charted or backtested.</p>`, { cls: "full" })}
  </div>`;
  main.querySelectorAll("[data-sym]").forEach((b) => (b.onclick = () => { state.marketSymbol = b.dataset.sym; show("MARKETS"); }));
  main.querySelectorAll("[data-mode]").forEach((b) => (b.onclick = () => { state.marketMode = b.dataset.mode; show("MARKETS"); }));
  main.querySelectorAll("[data-range]").forEach((b) => (b.onclick = () => { state.marketRange = b.dataset.range; show("MARKETS"); }));
  await drawMarket(latest, symbols);
};

async function drawMarket(latest, symbols) {
  const el = $("#mk-chart");
  const chart = LightweightCharts.createChart(el, { ...CHART_OPTS(), autoSize: true });
  charts.push(chart);
  const main = await getBars(latest[state.marketSymbol].dataset_id);
  const bars = cutRange(main, state.marketRange);
  const first = bars[0], last = bars[bars.length - 1];
  let peak = -Infinity, mdd = 0;
  bars.forEach((b) => { peak = Math.max(peak, b.adj_close); mdd = Math.min(mdd, b.adj_close / peak - 1); });
  const ageDays = Math.round((Date.now() - new Date(last.time).getTime()) / 86400000);
  $("#mk-stats").innerHTML = [
    ["last close", fmt(last.close)], ["date", last.time], [`${state.marketRange} total return`, pct(last.adj_close / first.adj_close - 1)],
    ["max drawdown", pct(mdd)], ["bars", fmt(bars.length, 0)], ["data age", `${ageDays}d`],
  ].map(([k, v]) => `<div><b class="${k.includes("return") ? (v.startsWith("+") ? "ok" : "bad") : k === "max drawdown" ? "bad" : k === "data age" && ageDays > 7 ? "warn" : ""}">${esc(v)}</b><span>${esc(k)}</span></div>`).join("");
  if (state.marketMode === "candles") {
    const candles = chart.addCandlestickSeries({ upColor: "#4fd18b", downColor: "#ff5d5d", borderVisible: false, wickUpColor: "#4fd18b", wickDownColor: "#ff5d5d" });
    candles.setData(bars.map((b) => ({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close })));
    const vol = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "vol", color: "#26302b" });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    vol.setData(bars.map((b) => ({ time: b.time, value: b.volume, color: b.close >= b.open ? "#1f4a33" : "#4a2323" })));
    $("#mk-legend").innerHTML = `<span><i style="background:#4fd18b"></i>up day</span><span><i style="background:#ff5d5d"></i>down day</span><span class="dim">volume at the bottom</span>`;
  } else if (state.marketMode === "compare") {
    const all = await Promise.all(symbols.map((s) => getBars(latest[s].dataset_id)));
    const start = cutRange(main, state.marketRange)[0].time;
    const legend = [];
    all.forEach((series, i) => {
      const cut = series.filter((b) => b.time >= start);
      if (!cut.length) return;
      const base = cut[0].adj_close;
      const line = chart.addLineSeries({ color: SERIES_COLORS[i % SERIES_COLORS.length], lineWidth: 2, priceFormat: { type: "custom", formatter: (v) => v.toFixed(0) } });
      line.setData(cut.map((b) => ({ time: b.time, value: (b.adj_close / base) * 100 })));
      legend.push(`<span><i style="background:${SERIES_COLORS[i % SERIES_COLORS.length]}"></i>${esc(symbols[i])} ${pct(cut[cut.length - 1].adj_close / base - 1)}</span>`);
    });
    $("#mk-legend").innerHTML = legend.join("") + `<span class="dim">rebased to 100 at ${esc(start)}</span>`;
    $("#mk-title").textContent = symbols.join(" · ");
  } else {
    let pk = -Infinity;
    const dd = chart.addAreaSeries({ lineColor: "#ff5d5d", topColor: "rgba(255,93,93,0.05)", bottomColor: "rgba(255,93,93,0.35)", lineWidth: 1, priceFormat: { type: "percent" } });
    dd.setData(bars.map((b) => { pk = Math.max(pk, b.adj_close); return { time: b.time, value: (b.adj_close / pk - 1) * 100 }; }));
    $("#mk-legend").innerHTML = `<span><i style="background:#ff5d5d"></i>distance below the running high, %</span>`;
  }
  chart.timeScale().fitContent();
}

// ---------- lab ----------
RENDER.LAB = async (main) => {
  const d = await api("/api/lab");
  const cards = d.cards.map((c) => `<div style="margin-bottom:12px"><div class="row"><b class="warn">${esc(c.strategy_id)}</b>${pill(c.status)}<span class="pill dim">${esc(c.stage)}</span><span class="pill dim">confidence ${esc(c.confidence)}</span><span class="grow"></span>
      <button class="btn small" data-file="${esc(c.note_path)}">Open card</button><button class="btn small" data-explain-card="${esc(c.note_path)}">Explain</button></div>
      <p><b>${esc(c.title)}</b></p><p class="wrap">${esc(c.hypothesis || "")}</p>
      <table><tr><td class="dim">markets</td><td class="wrap">${esc(Array.isArray(c.markets) ? c.markets.join(", ") : Object.entries(c.markets || {}).map(([k, v]) => `${k}: ${[].concat(v).join(", ")}`).join(" · "))}</td></tr><tr><td class="dim">timeframe</td><td>${esc(c.timeframe)}</td></tr><tr><td class="dim">sources</td><td class="wrap">${(c.source_ids || []).map((s) => fileLink(s, s.split("/").pop())).join(", ")}</td></tr><tr><td class="dim">review</td><td>${esc(c.review_status)}</td></tr><tr><td class="dim">created</td><td>${esc(c.created_at)}</td></tr></table></div>`).join("");
  const bts = d.backtests.map((b) => `<tr class="click ${b.backtest_id === state.selectedBacktest ? "sel" : ""}" data-bt="${esc(b.backtest_id)}"><td>${esc(b.backtest_id)}</td><td>${esc(b.strategy_id)}</td><td>${pill(b.status)}</td><td class="num">${pct(b.total_return)}</td><td class="num">${pct(b.benchmark_return)}</td><td class="num">${fmt(b.sharpe)}</td><td class="num bad">${pct(b.max_drawdown)}</td><td class="num">${fmt(b.number_of_trades, 0)}</td><td class="num">${fmt(b.fees)}</td><td class="dim">${esc(short(b.code_commit, 8))}</td><td>${b.equity_available ? "chart" : ""}</td></tr>`).join("");
  const reviews = d.reviews.map((r) => `<div style="margin-bottom:8px"><div class="row"><b>${esc(r.review_id)}</b>${pill(r.verdict)}<span class="dim">${esc(r.reviewer || "")} · ${esc(r.backtest_id || "")}</span>${r.note_path ? fileLink(r.note_path, "open") : ""}</div><ul>${(r.reasons || []).map((x) => `<li>${esc(typeof x === "string" ? x : JSON.stringify(x))}</li>`).join("")}</ul></div>`).join("");
  main.innerHTML = `<div class="grid">
    ${pane("Strategy cards", cards || empty("No strategy cards", "Cards are written and frozen by the builder (PROP-007 step 4)."), { small: `${d.cards.length} · frozen before any result is seen`, cls: "full" })}
    ${pane("Adversarial reviews", reviews || empty("No reviews yet", "The review (PROP-007 step 6) can say reject. Its verdict appears here."), { small: "verdict can be reject", cls: "full" })}
    ${pane("Trial ledger", d.backtests.length ? `<div class="scroll"><table><tr><th>Backtest</th><th>Card</th><th>Status</th><th class="num">Return</th><th class="num">Benchmark</th><th class="num">Sharpe</th><th class="num">Max DD</th><th class="num">Trades</th><th class="num">Fees</th><th>Commit</th><th></th></tr>${bts}</table></div><p class="note">Every trial is listed, not only the best. A backtest is evidence about the past, never proof of future profit.</p><div id="bt-chart"></div>` : empty("No backtests yet", "This fills in when PROP-007 step 5 runs: every grid combination, equity against buy-and-hold and random entry, and the held-out period."), { small: "all trials, sorted newest first", cls: "full" })}
  </div>`;
  main.querySelectorAll("[data-explain-card]").forEach((b) => (b.onclick = () => { state.learn.selected.add(b.dataset.explainCard); show("LEARN", { question: "Explain this strategy card to me: the rules, why each is there, what the assumptions are, and what would make it fail." }); }));
  main.querySelectorAll("[data-bt]").forEach((tr) => tr.addEventListener("click", async () => {
    state.selectedBacktest = tr.dataset.bt;
    main.querySelectorAll("[data-bt]").forEach((x) => x.classList.toggle("sel", x === tr));
    const box = $("#bt-chart");
    const series = await api(`/api/lab/${encodeURIComponent(tr.dataset.bt)}/equity`);
    const names = Object.keys(series);
    if (!names.length) { box.innerHTML = `<p class="dim">No equity series saved for this backtest (expected next to its report as &lt;report&gt;.equity.parquet|csv|json).</p>`; return; }
    clearCharts();
    box.innerHTML = `<div class="legend">${names.map((n, i) => `<span><i style="background:${SERIES_COLORS[i % 5]}"></i>${esc(n)}</span>`).join("")}</div><div class="chart small" id="bt-canvas"></div>`;
    const chart = LightweightCharts.createChart($("#bt-canvas"), { ...CHART_OPTS(), autoSize: true });
    charts.push(chart);
    names.forEach((n, i) => chart.addLineSeries({ color: SERIES_COLORS[i % 5], lineWidth: 2 }).setData(series[n]));
    chart.timeScale().fitContent();
  }));
};

// ---------- learn ----------
function renderMarkdown(src) {
  const blocks = String(src).split(/```/);
  return blocks.map((block, i) => {
    if (i % 2 === 1) return `<pre><code>${esc(block.replace(/^\w*\n/, ""))}</code></pre>`;
    const lines = esc(block).split("\n");
    let html = "", list = null;
    const inline = (t) => t
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/~~([^~]+)~~/g, "<del>$1</del>")
      .replace(/\[([\w./\-]+\.(?:md|py|json|txt)):(\d+(?:-\d+)?)\]/g, (m, p, l) => `<button class="cite" data-file="${p}" data-line="${l}">[${p}:${l}]</button>`)
      .replace(/\[([\w./\-]+\.(?:md|py|json|txt))\]/g, (m, p) => `<button class="cite" data-file="${p}">[${p}]</button>`);
    const close = () => { if (list) { html += `</${list}>`; list = null; } };
    for (const line of lines) {
      let m;
      if ((m = /^(#{1,4})\s+(.*)$/.exec(line))) { close(); html += `<h4>${inline(m[2])}</h4>`; }
      else if ((m = /^\s*[-*]\s+(.*)$/.exec(line))) { if (list !== "ul") { close(); html += "<ul>"; list = "ul"; } html += `<li>${inline(m[1])}</li>`; }
      else if ((m = /^\s*\d+[.)]\s+(.*)$/.exec(line))) { if (list !== "ol") { close(); html += "<ol>"; list = "ol"; } html += `<li>${inline(m[1])}</li>`; }
      else if (!line.trim()) { close(); }
      else { close(); html += `<p>${inline(line)}</p>`; }
    }
    close();
    return html;
  }).join("");
}

const STARTERS = [
  "Explain this project to me like I'm new: what it does, and the order things happen in.",
  "What is look-ahead bias, and how does this repo prevent it?",
  "Walk me through how the dispatcher picks an agent for a task, file by file, so I could rebuild it.",
  "Why was the research harness frozen, and what happens next?",
];

RENDER.LEARN = async (main, opts = {}) => {
  const L = state.learn;
  const [sources, notes, journal, backends] = await Promise.all([
    L.sources ? Promise.resolve(L.sources) : api("/api/learn/sources"),
    api("/api/learn/notes"), api("/api/journal"), api("/api/backends"),
  ]);
  L.sources = sources;
  if (!L.selected.size) ["PLAN.md", "AGENTS.md"].forEach((p) => L.selected.add(p));
  const srcHtml = sources.map((g) => `<details class="src-group" ${g.items.some((i) => L.selected.has(i.path)) || g.group === "Plan & rules" ? "open" : ""}><summary>${esc(g.group)} <span class="dim">(${g.items.length})</span></summary>
    ${g.items.map((i) => `<label class="src-item"><input type="checkbox" data-src="${esc(i.path)}" ${L.selected.has(i.path) ? "checked" : ""}><span>${esc(i.path.split("/").pop())}</span><span class="size">${Math.max(1, Math.round(i.size / 1024))}k</span><button type="button" data-file="${esc(i.path)}" title="View">👁</button></label>`).join("")}</details>`).join("");
  const usable = backends.filter((b) => b.available);
  if (!usable.some((b) => b.name === L.backend) && usable.length) L.backend = usable[0].name;
  main.innerHTML = `<div class="grid learn">
    ${pane("Sources", `<input type="text" id="src-filter" placeholder="Filter sources" style="width:100%;margin-bottom:6px"><div class="row" style="margin-bottom:6px"><span class="dim" id="src-count"></span><span class="grow"></span><button class="btn small" id="src-clear">Clear</button></div><div class="scroll tall" id="src-list">${srcHtml}</div>`, { small: "the tutor reads only these" })}
    ${pane("Tutor", `<div class="chat" id="chat"></div>
      <div class="ask" style="margin-top:12px">
        <div class="chips" id="starters">${STARTERS.map((s) => `<button class="chip" type="button">${esc(s)}</button>`).join("")}</div>
        <textarea id="question" rows="3" placeholder="Ask about the selected sources. Enter sends, Shift+Enter adds a line."></textarea>
        <div class="row"><select id="backend">${backends.map((b) => `<option value="${esc(b.name)}" ${b.available ? "" : "disabled"} ${b.name === L.backend ? "selected" : ""}>${esc(b.label)}${b.available ? "" : " (unavailable)"}</option>`).join("")}</select>
        <span class="dim">no tools · cites [file:line]</span><span class="grow"></span><button class="btn" id="new-chat">New chat</button><button class="btn primary" id="send">Ask</button></div>
      </div>`, { small: "a teacher, not an agent" })}
    <div class="grid" style="grid-template-columns:1fr">
      ${pane("Notebook", notes.length ? `<div class="scroll">${notes.map((n) => `<p>${fileLink(n.path, n.title)}<br><span class="dim">${esc(n.created.slice(0, 10))} · ${esc((n.sources || []).length)} sources</span></p>`).join("")}</div>` : `<p class="dim">Saved answers land here as study notes in terminal/learning/. They are never indexed as evidence.</p>`, { small: `${notes.length} study notes` })}
      ${pane("Decision journal", `<div class="scroll">${journal.map((j) => `<p><span class="dim">${esc(j.date || "undated")}</span> ${j.kind === "proposal" ? `<b class="warn">${esc(j.id)}</b>` : `<b class="inf">DEC</b>`} ${esc(j.title)}<br><span class="dim">${esc(short(String(j.status || "").replace(/\*\*/g, ""), 80))}</span> <button class="btn small" data-journal="${esc(j.path)}" data-id="${esc(j.id)}">Explain</button></p>`).join("")}</div>`, { small: "how the project got here" })}
    </div></div>`;

  const updateCount = () => {
    const total = sources.flatMap((g) => g.items).filter((i) => L.selected.has(i.path)).reduce((a, i) => a + i.size, 0);
    $("#src-count").textContent = `${L.selected.size} selected · ~${Math.round(total / 4 / 1000)}k tokens`;
  };
  updateCount();
  $("#src-list").addEventListener("change", (e) => { const p = e.target.dataset.src; if (!p) return; e.target.checked ? L.selected.add(p) : L.selected.delete(p); updateCount(); });
  $("#src-clear").onclick = () => { L.selected.clear(); document.querySelectorAll("[data-src]").forEach((c) => (c.checked = false)); updateCount(); };
  $("#src-filter").oninput = (e) => { const q = e.target.value.toLowerCase(); document.querySelectorAll(".src-item").forEach((l) => (l.hidden = !l.querySelector("[data-src]").dataset.src.toLowerCase().includes(q))); if (q) document.querySelectorAll(".src-group").forEach((d) => (d.open = true)); };
  $("#backend").onchange = (e) => (L.backend = e.target.value);
  $("#new-chat").onclick = () => { L.messages = []; drawChat(); };
  $("#starters").onclick = (e) => { const b = e.target.closest(".chip"); if (b) { $("#question").value = b.textContent; ask(); } };
  $("#send").onclick = ask;
  $("#question").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(); } });
  main.querySelectorAll("[data-journal]").forEach((b) => (b.onclick = () => { L.selected.add(b.dataset.journal); $("#question").value = `Explain ${b.dataset.id}: what problem it addressed, what was decided, and what it changed.`; show("LEARN", { question: $("#question").value }); }));
  drawChat();
  if (opts.question) { $("#question").value = opts.question; if (opts.autoAsk !== false) ask(); }
};

function drawChat() {
  const box = $("#chat");
  if (!box) return;
  const L = state.learn;
  box.innerHTML = L.messages.length ? L.messages.map((m, i) => m.role === "user"
    ? `<div class="msg you"><div class="who">You</div><div class="md">${esc(m.text)}</div></div>`
    : `<div class="msg tutor"><div class="who">Tutor · ${esc(m.backend || "")}${m.done && !m.error ? ` <button class="btn small" data-save="${i}">Save to notebook</button>` : ""}</div>
       ${m.sources ? `<p class="dim" style="font-size:11px">read: ${m.sources.map((s) => `${esc(s.path)}${s.truncated ? ` <span class="warn">(first ${s.included_lines} of ${s.lines} lines)</span>` : ""}`).join(" · ")}</p>` : ""}
       <div class="md ${m.done ? "" : "typing"}">${m.error ? `<p class="error">${esc(m.error)}</p>` : renderMarkdown(m.text)}</div></div>`).join("")
    : `<div class="empty"><b>Ask anything about this project</b><span>Pick sources on the left: plans, decisions, code, run receipts. The tutor answers only from them and cites the exact lines, so you can check every claim.</span></div>`;
  box.querySelectorAll("[data-save]").forEach((b) => (b.onclick = async () => {
    const i = Number(b.dataset.save);
    const q = L.messages[i - 1]?.text || "";
    try { const r = await post("/api/learn/notes", { question: q, answer: L.messages[i].text, sources: L.messages[i].sources.map((s) => s.path), backend: L.messages[i].backend, title: q.slice(0, 80) }); toast(`Saved ${r.path}`, "ok"); b.disabled = true; b.textContent = "Saved"; } catch (e) { toast(e.message, "bad"); }
  }));
  box.lastElementChild?.scrollIntoView({ block: "end" });
}

async function ask() {
  const L = state.learn;
  const q = $("#question").value.trim();
  if (!q || L.busy) return;
  if (!L.selected.size) { toast("Pick at least one source on the left.", "warn"); return; }
  L.busy = true;
  $("#send").disabled = true;
  $("#question").value = "";
  const history = L.messages.filter((m) => !m.error).map((m) => ({ role: m.role, text: m.text }));
  L.messages.push({ role: "user", text: q });
  const reply = { role: "tutor", text: "", done: false, backend: L.backend };
  L.messages.push(reply);
  drawChat();
  try {
    const res = await fetch("/api/learn/ask", { method: "POST", headers: { "Content-Type": "application/json", "X-Brain-Terminal": "1" }, body: JSON.stringify({ question: q, sources: [...L.selected], backend: L.backend, history }) });
    if (!res.ok) { let d = res.statusText; try { d = (await res.json()).detail; } catch (e) { /* */ } throw new Error(d); }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "", last = 0;
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl); buf = buf.slice(nl + 1);
        if (!line.trim()) continue;
        const msg = JSON.parse(line);
        if (msg.type === "sources") reply.sources = msg.sources;
        else if (msg.type === "text") reply.text += msg.text;
        else if (msg.type === "error") reply.error = msg.error;
      }
      if (Date.now() - last > 120) { last = Date.now(); drawChat(); }
    }
  } catch (e) { reply.error = e.message; }
  reply.done = true;
  L.busy = false;
  if ($("#send")) $("#send").disabled = false;
  drawChat();
}

RENDER.SETTINGS = async (main) => {
  const [b, home] = await Promise.all([api("/api/backends"), api("/api/home")]);
  main.innerHTML = `<div class="grid">
    ${pane("Model backends", `<table><tr><th>Backend</th><th>Status</th><th>Detail</th><th>How it signs in</th></tr>${b.map((x) => `<tr><td><b>${esc(x.label)}</b></td><td>${x.available ? pill("ready") : `<span class="pill warn">unavailable</span>`}</td><td class="wrap">${esc(x.detail)}</td><td class="wrap">${esc(x.sign_in)}</td></tr>`).join("")}</table>
      <p class="note">The terminal calls the official CLIs, which are already logged in to your subscriptions. It never reads, stores or forwards a token. Tutor calls run with every tool disabled, no MCP servers, and an empty working folder.</p>`, { small: "PROP-008 §4", cls: "full" })}
    ${pane("Where things live", `<table>
      <tr><td class="dim">brain (read-only)</td><td class="wrap">${esc(home.project_root)}\\db\\brain.sqlite</td></tr>
      <tr><td class="dim">terminal state</td><td class="wrap">${esc(home.project_root)}\\db\\terminal.sqlite</td></tr>
      <tr><td class="dim">study notes</td><td class="wrap">${esc(home.project_root)}\\terminal\\learning\\</td></tr>
      <tr><td class="dim">scheduled output</td><td class="wrap">${esc(home.project_root)}\\terminal\\scheduled\\</td></tr>
      <tr><td class="dim">job logs</td><td class="wrap">${esc(home.project_root)}\\terminal\\logs\\</td></tr></table>`)}
    ${pane("Guardrails", `<ul class="md"><li>Local only: the server answers on 127.0.0.1 and refuses other host names and cross-site requests.</li><li>The brain database is opened read-only. The only brain writes are job events via ops.events.</li><li>Jobs come from a fixed allowlist, with no arbitrary shell. Research runs stay frozen while PROP-007 holds.</li><li>No trading, no brokers, no market feeds.</li><li>Tutor and scheduled output is marked untrusted and lives outside brain/, so it can never become evidence.</li></ul>`)}
  </div>`;
};

// ---------- boot ----------
buildKeys();
let start = "HOME";
try { const s = localStorage.getItem("bt-screen"); if (SCREENS.includes(s)) start = s; } catch (e) { /* storage blocked */ }
const hash = location.hash.slice(1).toUpperCase();
if (SCREENS.includes(hash)) start = hash;
show(start);
connectStream();
refreshFooter();
window.addEventListener("hashchange", () => {
  const h = location.hash.slice(1).toUpperCase();
  if (SCREENS.includes(h) && h !== state.screen) show(h);
});
