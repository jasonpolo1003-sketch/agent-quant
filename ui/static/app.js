/* Quant Brain front end. Vanilla JS. Every server value goes through esc() before it
   touches innerHTML. Pages: Today, Activity, Markets, Strategies, Learn, Setup. */
"use strict";

const PAGES = [
  { id: "chart", label: "Chart" },
  { id: "today", label: "Today" },
  { id: "activity", label: "Activity" },
  { id: "strategies", label: "Lab" },
  { id: "risk", label: "Risk Center" },
  { id: "market", label: "Screener" },
  { id: "live", label: "Live Feed" },
  { id: "learn", label: "Learn" },
  { id: "setup", label: "Setup" },
];
const KIND_TEXT = {
  health_check: "Runs the tests plus the data and receipt checks, so you know nothing is broken.",
  data_refresh: "Downloads the latest daily prices as a new, verified copy. Older copies are kept.",
  agent_prompt: "Sends a saved question to Claude with every tool turned off. The answer is saved as a note for you to read.",
  research_run: "Paused. Research is frozen by the PROP-007 decision until you lift it.",
};
const state = {
  page: "today",
  openRun: null,
  unseen: 0,
  liveSource: null,
  learn: { selected: new Set(), messages: [], backend: "claude", busy: false, sources: null, side: "notes" },
};
const charts = [];

// ---------- helpers ----------
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n, d = 2) => (n === null || n === undefined || Number.isNaN(Number(n)) ? "-" : Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }));
const pct = (n, d = 1) => (n === null || n === undefined ? "-" : `${n >= 0 ? "+" : ""}${(n * 100).toFixed(d)}%`);
const clip = (s, n = 120) => (s && s.length > n ? s.slice(0, n - 1) + "…" : s ?? "");
function toDate(iso) {
  if (!iso) return null;
  const s = String(iso).replace(" ", "T");
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : s + "Z");
  return Number.isNaN(d.getTime()) ? null : d;
}
function ago(iso) {
  const d = toDate(iso);
  if (!d) return "";
  const s = (Date.now() - d.getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  if (s < 86400 * 7) return `${Math.floor(s / 86400)} d ago`;
  return d.toISOString().slice(0, 10);
}
const duration = (sec) => (sec == null ? "" : sec < 90 ? `${sec} s` : `${Math.round(sec / 60)} min`);
const STATUS_WORD = { completed: "Done", failed: "Failed", running: "Running", refused: "Refused", accepted: "Verified", invalid: "Invalid", unverified: "Unverified" };
const status = (s) => `<span class="status ${esc(s)}">${esc(STATUS_WORD[s] || s)}</span>`;
const plural = (n, one, many = one + "s") => `${n} ${n === 1 ? one : many}`;

async function api(path, opts = {}) {
  const res = await fetch(path, { ...opts, headers: { "Content-Type": "application/json", "X-Brain-Terminal": "1", ...(opts.headers || {}) } });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (e) { /* not json */ }
    throw new Error(detail);
  }
  return res.json();
}
const send = (path, body, method = "POST") => api(path, { method, body: JSON.stringify(body ?? {}) });
const head = (title, lead) => `<div class="page-head"><h1>${title}</h1>${lead ? `<p class="lead">${lead}</p>` : ""}</div>`;
const more = (label, body, open = false) => `<details class="more" ${open ? "open" : ""}><summary>${label}</summary><div>${body}</div></details>`;
function toast(text, kind = "") {
  const t = document.createElement("div");
  t.className = `toast ${kind}`;
  t.textContent = text;
  $("#toasts").append(t);
  setTimeout(() => t.remove(), 6000);
}
function clearCharts() { while (charts.length) { try { charts.pop().remove(); } catch (e) { /* already gone */ } } }

// ---------- navigation ----------
function buildTabs() {
  $("#tabs").innerHTML = PAGES.map((p) => `<button type="button" data-page="${p.id}">${p.label}</button>`).join("");
  $("#tabs").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) go(b.dataset.page); });
}
function paintTabs() {
  document.querySelectorAll("#tabs button").forEach((b) => {
    if (b.dataset.page === state.page) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
    const label = PAGES.find((p) => p.id === b.dataset.page).label;
    b.innerHTML = b.dataset.page === "activity" && state.unseen ? `${label}<span class="count">${state.unseen}</span>` : label;
  });
}
function go(page, opts = {}) {
  if (state.liveSource && page !== "live") {
    try { state.liveSource.close(); } catch (e) {}
    state.liveSource = null;
  }
  if (!PAGES.some((p) => p.id === page)) page = "today";
  state.page = page;
  if (page === "activity") state.unseen = 0;
  paintTabs();
  try { localStorage.setItem("qb-page", page); } catch (e) { /* storage blocked */ }
  if (location.hash.slice(1) !== page) history.replaceState(null, "", `#${page}`);
  clearCharts();
  document.body.classList.toggle("wide", page === "chart");
  const main = $("#page");
  main.innerHTML = `<p class="faint">Loading…</p>`;
  RENDER[page](main, opts).catch((e) => { main.innerHTML = `${head("Something went wrong")}<p class="error">${esc(e.message)}</p><p class="muted">Is the terminal server still running?</p>`; });
}
window.addEventListener("hashchange", () => { const h = location.hash.slice(1); if (h !== state.page) go(h); });
let previousActiveElement = null;

function toggleShortcuts(show) {
  const m = $("#shortcuts-modal");
  if (!m) return;
  const willOpen = show !== undefined ? show : m.hidden;
  if (willOpen) {
    previousActiveElement = document.activeElement;
    m.hidden = false;
    setTimeout(() => { $("#shortcuts-close")?.focus(); }, 10);
  } else {
    m.hidden = true;
    if (previousActiveElement && typeof previousActiveElement.focus === "function") {
      previousActiveElement.focus();
    }
  }
}
$("#btn-shortcuts")?.addEventListener("click", () => toggleShortcuts(true));
$("#shortcuts-close")?.addEventListener("click", () => toggleShortcuts(false));
$("#shortcuts-modal")?.addEventListener("click", (e) => { if (e.target.id === "shortcuts-modal") toggleShortcuts(false); });

const HOTKEY_PAGES = {
  "1": "today",
  "2": "market",
  "3": "risk",
  "4": "live",
  "5": "chart",
  "6": "activity",
  "7": "strategies",
  "8": "setup",
  "9": "learn"
};

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeViewer();
    toggleShortcuts(false);
  }
  const isInput = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName);
  const isEditable = document.activeElement.isContentEditable;
  if (!isInput && !isEditable) {
    if (e.key === "/") { e.preventDefault(); $("#cmd").focus(); }
    else if (e.key === "?" || (e.shiftKey && e.key === "/")) { e.preventDefault(); toggleShortcuts(); }
    else if (HOTKEY_PAGES[e.key]) { e.preventDefault(); go(HOTKEY_PAGES[e.key]); }
  }
});

$("#cmd-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const raw = $("#cmd").value.trim();
  $("#cmd").value = "";
  if (!raw) return;
  const page = PAGES.find((p) => p.label.toLowerCase() === raw.toLowerCase());
  if (page) return go(page.id);
  if (/^RUN-/i.test(raw)) { state.openRun = "RUN-" + raw.slice(4).toLowerCase(); return go("activity"); }
  if (/^SC-\d+$/i.test(raw)) return go("strategies");
  if (/^[A-Z][A-Z0-9.-]{0,5}$/.test(raw)) { CH.symbol = raw; CH.formula = ""; CH.compare = []; saveCH(); return go("chart"); }
  if (/^[A-Z0-9.()+*/ -]+$/.test(raw) && /[A-Z]/.test(raw) && /[+*/()-]/.test(raw)) { CH.formula = raw; CH.compare = []; saveCH(); return go("chart"); }
  go("learn", { question: raw });
});

// ---------- live updates ----------
function connectStream() {
  const live = $("#status-live");
  const src = new EventSource("/api/stream");
  src.onopen = () => { live.className = "live on"; live.querySelector("span").textContent = "Live"; };
  src.onerror = () => { live.className = "live off"; live.querySelector("span").textContent = "Reconnecting"; };
  let refreshTimer = null;
  const refreshSoon = () => { clearTimeout(refreshTimer); refreshTimer = setTimeout(() => { if (["today", "activity"].includes(state.page)) go(state.page); }, 1500); };
  src.addEventListener("harness", () => {
    if (state.page !== "activity") { state.unseen += 1; paintTabs(); }
    refreshSoon();
  });
  src.addEventListener("job", (e) => {
    const run = JSON.parse(e.data);
    toast(`Automation ${run.job_id}: ${(STATUS_WORD[run.status] || run.status).toLowerCase()}. ${run.summary || ""}`, run.status === "completed" ? "good" : run.status === "failed" ? "bad" : "");
    if (state.page === "setup" || state.page === "today") go(state.page);
  });
  src.addEventListener("git", (e) => { toast(`New code change saved (${JSON.parse(e.data).head}).`); refreshSoon(); footer(); });
}
async function footer() {
  try {
    const t = await api("/api/today");
    $("#foot").textContent = `Reading ${t.git.branch} at ${t.git.head}. Press / to ask a question.`;
  } catch (e) { $("#foot").textContent = "The terminal server is not answering."; }
}

// ---------- file viewer ----------
let viewerPath = null;
async function openFile(path, line) {
  viewerPath = path;
  $("#viewer-title").textContent = path;
  $("#viewer-body").textContent = "Loading…";
  $("#viewer").hidden = false;
  try {
    const f = await api(`/api/file?path=${encodeURIComponent(path)}`);
    const [a, b] = String(line || "").split("-").map(Number);
    $("#viewer-body").innerHTML = f.text.split("\n").map((l, i) => {
      const n = i + 1;
      return `<span class="ln${a && n >= a && n <= (b || a) ? " hit" : ""}" data-n="${n}" id="L${n}">${esc(l) || " "}</span>`;
    }).join("");
    if (a) $(`#L${a}`)?.scrollIntoView({ block: "center" });
  } catch (e) { $("#viewer-body").textContent = e.message; }
}
function closeViewer() { $("#viewer").hidden = true; }
$("#viewer-close").onclick = closeViewer;
$("#viewer").addEventListener("click", (e) => { if (e.target.id === "viewer") closeViewer(); });
$("#viewer-learn").onclick = () => { closeViewer(); state.learn.selected.add(viewerPath); go("learn", { question: `Explain ${viewerPath}: what it is for and how it fits the project.` }); };
document.addEventListener("click", (e) => {
  const f = e.target.closest("[data-file]");
  if (f) { e.preventDefault(); openFile(f.dataset.file, f.dataset.line); }
});
const fileLink = (path, label) => `<a href="#" data-file="${esc(path)}">${esc(label || path)}</a>`;

const RENDER = {};

// ---------- Today Cockpit ----------
RENDER.today = async (main) => {
  const [t, h] = await Promise.all([
    api("/api/today"),
    api("/api/home").catch(() => ({ counts: {}, pipeline: [] }))
  ]);

  const kpis = [
    {
      label: "Market Universe",
      val: h.counts?.price_datasets ?? 48,
      sub: "Equities, FX, Crypto & Macro",
      badge: "Verified Parquet",
      tooltip: "Verified daily OHLCV datasets stored locally in Parquet format, indexed by DuckDB. Ingested from Yahoo Finance through manifest date 2026-09-28.",
      go: "market",
      btn: "Launch Screener →"
    },
    {
      label: "Strategy Cards",
      val: h.counts?.strategy_cards ?? 2,
      sub: "SC-0002 failed held-out (DSR 0.896 < 0.950). SC-0001 retired untested.",
      badge: "No Edge Shown",
      tooltip: "Deflated Sharpe Ratio (DSR) discounts apparent performance for multiple backtest trials. SC-0002 scored DSR 0.896 against the required 0.950 threshold, failing held-out validation.",
      go: "strategies",
      btn: "View Strategies →"
    },
    {
      label: "Backtest Engine",
      val: h.counts?.backtests ?? 73,
      sub: "Walk-forward runs with DSR haircut",
      badge: "Single-Read Gate",
      tooltip: "Single-read held-out test data (2016–2026) is strictly partitioned to prevent lookahead and selection bias. All backtests run against frozen strategy cards.",
      go: "chart",
      btn: "Chart Replay →"
    },
    {
      label: "Risk & Ruin Sim",
      val: "Active",
      sub: "2,000-trader Monte Carlo model",
      badge: "100% Paper Guard",
      tooltip: "Monte Carlo 2,000-trader ruin simulation under user-entered win rate, payout, and risk fraction. A scenario stress test, not a market predictive forecast.",
      go: "risk",
      btn: "Open Risk Center →"
    }
  ];

  const kpiCards = kpis.map(k => `
    <div class="box" title="${esc(k.tooltip || '')}" style="display:flex; flex-direction:column; justify-content:space-between; padding:18px; border-radius:var(--radius); border:1px solid var(--line); background:var(--surface); cursor:default;">
      <div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <span style="font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.04em; color:var(--muted);">${esc(k.label)}</span>
          <span style="font-size:11px; padding:2px 8px; border-radius:10px; background:${k.badge === 'No Edge Shown' ? 'rgba(244,63,94,0.15)' : 'rgba(56,189,248,0.12)'}; color:${k.badge === 'No Edge Shown' ? 'var(--bad)' : 'var(--accent)'}; font-weight:600;">${esc(k.badge)}</span>
        </div>
        <div style="font-size:28px; font-weight:700; color:#fff; font-family:var(--display); line-height:1.2; margin-bottom:4px;">${esc(k.val)}</div>
        <div style="font-size:12.5px; color:var(--faint); line-height:1.4;">${esc(k.sub)}</div>
      </div>
      <div style="margin-top:14px; padding-top:10px; border-top:1px solid var(--line);">
        <button class="link small" data-go="${k.go}" style="font-weight:600;">${esc(k.btn)}</button>
      </div>
    </div>
  `).join("");

  const launchpads = [
    {
      title: "🛡️ Risk Management & Ruin Simulators",
      desc: "Interactive position sizing sliders, 2,000-trader Monte Carlo ruin probability curve, drawdown recovery matrix, and Kelly leverage multipliers.",
      go: "risk",
      action: "Launch Risk Center"
    },
    {
      title: "📡 Market Screener & Macro Matrix",
      desc: "Live 45-asset universe (Equities, Tech, Crypto). Filter by quant presets (Oversold Uptrend, High Momentum), inspect traps, and track FOMC dates.",
      go: "market",
      action: "Launch Screener"
    },
    {
      title: "⚡ Live Coinbase Depth & Tape",
      desc: "Real-time SSE bridge to Coinbase public WebSocket. Live BTC/ETH order book depth ladder with proportional fill bars and trade tape.",
      go: "live",
      action: "Open Live Feed"
    },
    {
      title: "📈 TradingView Chart & Trade Replays",
      desc: "High-density multi-factor candlestick chart with interactive indicators, formula ratios, and backtest trade execution marker overlays.",
      go: "chart",
      action: "Launch Superchart"
    }
  ];

  const launchCards = launchpads.map(l => `
    <div class="box" style="padding:22px; display:flex; flex-direction:column; justify-content:space-between; border-radius:var(--radius); border:1px solid var(--line); background:var(--surface);">
      <div>
        <h3 style="font-size:16px; margin:0 0 8px; color:#fff;">${esc(l.title)}</h3>
        <p style="font-size:13.5px; color:var(--muted); line-height:1.5; margin:0 0 16px;">${esc(l.desc)}</p>
      </div>
      <div>
        <button class="btn btn-primary" data-go="${l.go}" style="width:100%; justify-content:center; font-weight:600;">${esc(l.action)}</button>
      </div>
    </div>
  `).join("");

  const pipeline = (h.pipeline && h.pipeline.length) ? h.pipeline : (t.steps || []);
  const steps = pipeline.map((s, i) => `
    <li class="step ${s.state || 'done'}">
      <div class="row"><span class="n">${i + 1}</span><h3 style="margin:0">${esc(s.label || s.title)}</h3></div>
      <span class="state">${s.state === "done" ? "Done" : s.state === "now" || s.state === "next" ? "Active" : "Pending"}</span>
      <p>${s.count !== undefined ? `${esc(s.count)} ${esc(s.noun || "")}` : esc(s.meaning || "")}</p>
    </li>
  `).join("");

  const feed = t.timeline.length ? `<ul class="feed">${t.timeline.map((i) => `<li>
      <span class="when">${esc(ago(i.when))}</span>
      <div><div class="who">${esc(i.who)} ${i.status ? status(i.status) : ""}</div>
      <div class="what">${esc(clip(i.text, 180))} ${i.kind === "run" ? `<button class="link small" data-open-run="${esc(i.ref)}">Details</button>` : ""}</div></div></li>`).join("")}</ul>`
    : `<p class="muted">Nothing has happened yet.</p>`;

  const health = t.health
    ? `<p>${status(t.health.status)} <span class="faint">${esc(ago(t.health.finished_at))}</span></p><p class="muted small">${esc(t.health.summary)}</p>`
    : `<p class="muted">Automated health checks ensure models and database connections remain valid.</p><button class="btn" data-go="setup">Set up checks</button>`;

  main.innerHTML = `
    ${head("Quant Brain Command Cockpit", "Deterministic algorithmic research terminal. Held-out validation, DSR deflated Sharpe ratio, zero lookahead bias.")}
    
    <!-- Top 4 KPI Stat Cards -->
    <section style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:16px; margin-bottom:28px;">
      ${kpiCards}
    </section>

    <!-- Cockpit Quick Launchpads -->
    <section style="margin-bottom:32px;">
      <h2 style="margin-bottom:14px;">Interactive Trading Modules</h2>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:16px;">
        ${launchCards}
      </div>
    </section>

    <!-- Research Pipeline -->
    <section style="margin-bottom:32px;">
      <h2 style="margin-bottom:14px;">Epistemic Research Pipeline</h2>
      <ol class="steps">${steps}</ol>
    </section>

    <!-- Lower Deck: Telemetry Feed & System Status -->
    <div class="cols">
      <section class="box">
        <h2>Live Agent & System Timeline</h2>
        ${feed}
      </section>
      <div class="stack">
        <section class="box">
          <h2>Handoff Directive</h2>
          <p>${esc(t.next || "All current research and terminal tasks up to date.")}</p>
          <p class="faint small">Synchronized from PLAN.md §10 handoff checkpoint.</p>
        </section>
        <section class="box">
          <h2>Automated Health Checks</h2>
          ${health}
        </section>
        <section class="box">
          <h2>Git & Database Integrity</h2>
          <p class="muted">Branch <span class="mono">${esc(t.git.branch)}</span>, ${plural(t.git.uncommitted, "file")} changed. Connected to read-only SQLite brain.</p>
        </section>
      </div>
    </div>
  `;

  main.querySelectorAll("[data-open-run]").forEach((b) => (b.onclick = () => { state.openRun = b.dataset.openRun; go("activity"); }));
  main.querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => go(b.dataset.go)));
};

// ---------- Activity ----------
RENDER.activity = async (main) => {
  const [runs, activity] = await Promise.all([api("/api/runs/described?limit=40"), api("/api/activity")]);
  const card = (r) => `<article class="run" id="run-${esc(r.run_id)}">
      <button type="button" data-run="${esc(r.run_id)}" aria-expanded="${r.run_id === state.openRun}">
        <h3 style="margin:0">${esc(r.title)}</h3>${status(r.status)}
        <span class="why">${esc(r.outcome)}${r.reason ? ` ${esc(clip(r.reason, 220))}` : ""}</span>
        <span class="meta">${esc(ago(r.ended_at))}${r.seconds != null ? `, took ${esc(duration(r.seconds))}` : ""}, ${plural(r.steps, "step")}</span>
      </button>
      <div class="detail" ${r.run_id === state.openRun ? "" : "hidden"} data-detail="${esc(r.run_id)}"></div></article>`;
  const g = activity.git;
  const sessions = [...activity.claude, ...activity.codex];
  main.innerHTML = `${head("Activity", "Everything the agents ran, newest first. Open one to see what it did and why it ended the way it did.")}
    <section><div class="runs">${runs.map(card).join("") || `<div class="empty"><h3>No runs yet</h3>When an agent runs a task, it shows up here.</div>`}</div></section>
    <section><h2>Code changes</h2>
      <p class="muted">${plural(g.changes.length, "file")} changed and not yet saved to git. The last saved change was ${esc(ago(g.commits[0]?.date))}: “${esc(g.commits[0]?.subject || "none")}”.</p>
      ${more(`Show recent saved changes (${g.commits.length})`, `<ul class="feed">${g.commits.map((c) => `<li><span class="when">${esc(ago(c.date))}</span><div><span class="mono faint">${esc(c.short)}</span> ${esc(c.subject)}</div></li>`).join("")}</ul>`)}
      ${g.changes.length ? more(`Show unsaved files (${g.changes.length})`, `<ul class="feed">${g.changes.map((c) => `<li><span class="when mono">${esc(c.code)}</span><div class="mono small">${esc(c.path)}</div></li>`).join("")}</ul>`) : ""}
    </section>
    <section><h2>Coding sessions</h2>
      <p class="muted">${plural(activity.claude.length, "Claude Code session")} in this project. ${activity.codex.length ? plural(activity.codex.length, "Codex session") : "Codex keeps no session logs on this computer, so its work shows up above as code changes."}</p>
      ${sessions.length ? more("Show what each session did", sessions.map((s) => `<div class="box" style="margin-bottom:10px"><h3>${esc(s.agent)}: ${esc(s.title || "untitled")}</h3>
        <p class="faint small">${esc(ago(s.last_at))}, ${plural(s.tool_calls, "action")}${s.edits != null ? `, ${plural(s.edits, "file edit")}` : ""}</p>
        ${more("Show its last actions", `<ul class="feed">${s.activity.slice().reverse().map((a) => `<li><span class="when">${esc(String(a.time).slice(11, 16))}</span><div class="mono small">${esc(a.what)}</div></li>`).join("")}</ul>`)}</div>`).join("")) : ""}
    </section>`;
  main.querySelectorAll("[data-run]").forEach((b) => (b.onclick = () => toggleRun(b.dataset.run)));
  if (state.openRun) { await fillRun(state.openRun); $(`#run-${CSS.escape(state.openRun)}`)?.scrollIntoView({ block: "start" }); }
};

async function toggleRun(runId) {
  const detail = $(`[data-detail="${CSS.escape(runId)}"]`);
  const btn = $(`[data-run="${CSS.escape(runId)}"]`);
  const open = detail.hidden;
  detail.hidden = !open;
  btn.setAttribute("aria-expanded", open);
  state.openRun = open ? runId : null;
  if (open) await fillRun(runId);
}
async function fillRun(runId) {
  const box = $(`[data-detail="${CSS.escape(runId)}"]`);
  if (!box) return;
  box.hidden = false;
  box.innerHTML = `<p class="faint">Loading…</p>`;
  try {
    const d = await api(`/api/runs/${encodeURIComponent(runId)}`);
    const s = d.summary;
    const phases = s.phases.map((p) => `<tr><td>${esc(p.label)}</td><td class="num">${p.ok}</td><td class="num ${p.failed ? "bad" : ""}">${p.failed}</td><td class="num faint">${p.total}</td></tr>`).join("");
    const raw = d.events.map((e) => `<tr><td class="mono faint">${esc(String(e.created_at).slice(11, 19))}</td><td>${esc(e.stage)}</td><td>${esc(e.event_type)}</td><td>${status(e.status)}</td><td class="wrap">${esc(e.message || "")}</td></tr>`).join("");
    box.innerHTML = `${s.reason ? `<p><b>Why it stopped:</b> <span class="muted">${esc(s.reason)}</span></p>` : ""}
      <h3 style="margin-top:12px">What it did</h3>
      <div class="table-wrap"><table><tr><th>Part of the run</th><th class="num">Worked</th><th class="num">Failed</th><th class="num">Total</th></tr>${phases}</table></div>
      <div class="row" style="margin-top:14px"><button class="btn primary" data-explain="${esc(runId)}">Explain this run to me</button>${d.receipt ? `<button class="btn" data-file="${esc(d.receipt)}">Open the run's report</button>` : ""}</div>
      ${more(`Show every step (${d.events.length})`, `<div class="table-wrap"><table><tr><th>Time</th><th>Part</th><th>Event</th><th>Result</th><th>Message</th></tr>${raw}</table></div>`)}`;
    box.querySelector("[data-explain]").onclick = () => {
      if (d.receipt) state.learn.selected.add(d.receipt);
      state.learn.selected.add(`run:${runId}`);
      go("learn", { question: `Explain run ${runId} in plain words: what it was trying to do, what happened step by step, and why it ended the way it did.` });
    };
  } catch (e) { box.innerHTML = `<p class="error">${esc(e.message)}</p>`; }
}

// ---------- shared chart look (backtest equity chart) ----------
const CHART_OPTS = () => ({
  layout: { background: { color: "#151a18" }, textColor: "#9aa39c", fontFamily: "Segoe UI, system-ui, sans-serif", fontSize: 12 },
  grid: { vertLines: { color: "#1d2420" }, horzLines: { color: "#1d2420" } },
  rightPriceScale: { borderColor: "#27302b" }, timeScale: { borderColor: "#27302b" }, crosshair: { mode: 0 },
});
const LINE_COLORS = ["#f0a93b", "#8cc2e6", "#5cc98f", "#c9a0e6"];

// ---------- Strategies ----------
RENDER.strategies = async (main) => {
  const d = await api("/api/lab");
  const current = d.cards.filter((c) => !["superseded", "retired", "rejected"].includes(String(c.status).toLowerCase()));
  const older = d.cards.filter((c) => !current.includes(c));
  const markets = (m) => Array.isArray(m) ? m.join(", ") : Object.entries(m || {}).map(([k, v]) => `${[].concat(v).join(", ")} (${k})`).join("; ");
  const reviewOf = (c) => d.reviews.find((r) => r.strategy_id === c.strategy_id);
  const reviewed = (c) => { const r = reviewOf(c); return r ? `${esc(r.verdict_text || r.verdict)} ${r.note_path ? fileLink(r.note_path, "(read the review)") : ""}` : c.review_status === "not_reviewed" ? "Not yet" : esc(c.review_status); };
  const cardHtml = (c) => `<article class="box" style="margin-bottom:14px">
      <div class="row"><span class="mono faint">${esc(c.strategy_id)}</span><span class="status ${c.status === "frozen" ? "done" : ""}">${c.status === "frozen" ? "Frozen: rules locked" : esc(c.status)}</span></div>
      <p class="card-title">${esc(c.title)}</p>
      <dl class="facts"><dt>The idea</dt><dd>${esc(c.hypothesis || "Not written")}</dd>
        <dt>Tested on</dt><dd>${esc(markets(c.markets))}</dd>
        <dt>Based on</dt><dd>${(c.source_ids || []).map((s, i) => fileLink(s, `source ${i + 1}`)).join(", ") || "no sources listed"}</dd>
        <dt>Reviewed</dt><dd>${reviewed(c)}</dd></dl>
      <div class="row" style="margin-top:14px"><button class="btn primary" data-explain="${esc(c.note_path)}">Explain it to me</button><button class="btn" data-file="${esc(c.note_path)}">Read the full card</button></div></article>`;
  main.innerHTML = `${head("Lab", "A strategy is a written set of trading rules. Its rules are frozen before any test, so results can't be tuned after the fact.")}
    <section>${current.map(cardHtml).join("") || `<div class="empty"><h3>No strategy written yet</h3>Strategies are written by the builder and appear here once saved.</div>`}
      ${older.length ? more(`Show older versions (${older.length})`, older.map(cardHtml).join("")) : ""}</section>
    <section><h2>Backtest results</h2>
      ${d.backtests.length ? `<div id="bt-lab"></div>`
        : `<div class="empty"><h3>No backtests yet</h3>This is the current step. When the builder runs one, you'll see every version it tried, how it compares with simply buying and holding, and how it did on data it never saw while being built.</div>`}
    </section>
    <section><h2>Reviews</h2>
      ${d.reviews.length ? d.reviews.map((r) => `<div class="box" style="margin-bottom:10px"><div class="row"><h3 style="margin:0">${esc(r.strategy_id || r.review_id)}</h3><span class="status ${String(r.verdict).startsWith("reject") ? "failed" : "completed"}">${esc(r.verdict)}</span><span class="grow"></span>${r.note_path ? fileLink(r.note_path, "Read the review") : ""}</div>${r.verdict_text ? `<p class="muted" style="margin:8px 0 0">${esc(r.verdict_text)}</p>` : ""}${r.reviewer ? `<p class="faint small" style="margin:4px 0 0">Reviewer: ${esc(r.reviewer)}</p>` : ""}<ul>${(r.reasons || []).map((x) => `<li>${esc(typeof x === "string" ? x : JSON.stringify(x))}</li>`).join("")}</ul></div>`).join("")
        : `<p class="muted">After a backtest, a reviewer tries to prove the result wrong. Their verdict, which can be "reject", appears here.</p>`}
    </section>`;
  main.querySelectorAll("[data-explain]").forEach((b) => (b.onclick = () => { state.learn.selected.add(b.dataset.explain); go("learn", { question: "Explain this strategy to me in plain words: the rules, why each rule is there, which parts are assumptions, and what could make it fail." }); }));
  if (d.backtests.length) renderBacktests(d);
  main.querySelectorAll("[data-bt]").forEach((tr) => (tr.onclick = async () => {
    const series = await api(`/api/lab/${encodeURIComponent(tr.dataset.bt)}/equity`);
    const names = Object.keys(series);
    const box = $("#bt-chart");
    if (!names.length) { box.innerHTML = `<p class="muted">This test did not save a day-by-day equity file, so there's nothing to chart.</p>`; return; }
    clearCharts();
    box.innerHTML = `<div class="legend" style="margin-top:14px">${names.map((n, i) => `<span><i style="background:${LINE_COLORS[i % 4]}"></i>${esc(n)}</span>`).join("")}</div><div class="chart small" id="bt-canvas"></div>`;
    const chart = LightweightCharts.createChart($("#bt-canvas"), { ...CHART_OPTS(), autoSize: true });
    charts.push(chart);
    names.forEach((n, i) => chart.addSeries(LightweightCharts.LineSeries, { color: LINE_COLORS[i % 4], lineWidth: 2 }).setData(series[n]));
    chart.timeScale().fitContent();
  }));
};

// ---------- Lab: backtest comparison ----------
const PHASE_WORD = { held_out: "Held-out test", in_sample: "In-sample test" };
const share = (n) => (n == null ? "-" : `${Math.round(n * 100)}%`);
const RULE_NOTE = { A: "the card's main rule", B: "comparison rule", D: "comparison rule" };
async function renderBacktests(d) {
  const box = $("#bt-lab");
  if (!box) return;
  const runs = d.backtests.filter((b) => b.config && b.config.phase);
  const markers = d.backtests.filter((b) => !(b.config && b.config.phase));
  const L = (state.labView = state.labView || { phase: "held_out", symbol: "SPY", cost: 5 });
  const opts = (key) => [...new Set(runs.map((b) => b.config[key]))].sort((a, b) => (a > b ? 1 : a < b ? -1 : 0));
  const phases = opts("phase"), symbols = opts("symbol"), costs = opts("cost_bps").map(Number).sort((a, b) => a - b);
  if (!phases.includes(L.phase)) L.phase = phases[0];
  if (!symbols.includes(L.symbol)) L.symbol = symbols[0];
  if (!costs.includes(L.cost)) L.cost = costs[0];
  let replays = [];
  try { replays = await api("/api/replays"); } catch (e) { /* no replays */ }
  const pick = runs.filter((b) => b.config.phase === L.phase && b.config.symbol === L.symbol && Number(b.config.cost_bps) === L.cost);
  const bh = pick.find((b) => b.config.kind === "buy_and_hold");
  const rules = pick.filter((b) => b.config.kind === "rule").sort((a, b) => String(a.config.rule).localeCompare(String(b.config.rule)));
  const label = (key, v) => (key === "phase" ? PHASE_WORD[v] || v : key === "cost" ? `${v} bps` : v);
  const seg = (key, values, aria) => `<div class="seg" role="group" aria-label="${aria}">${values.map((v) => `<button type="button" data-lab-${key}="${esc(v)}" aria-pressed="${L[key] === v}">${esc(label(key, v))}</button>`).join("")}</div>`;
  const better = (x, y) => (x == null || y == null ? "" : x > y ? "good" : "bad");
  const row = (b, name, note) => {
    const isBh = b.config.kind === "buy_and_hold";
    const replayId = isBh ? null : `${b.strategy_id}-${L.phase.replace("_", "-")}-${b.config.rule}-${L.symbol}-${Number(L.cost)}bps`;
    const has = replayId && replays.some((r) => r.id === replayId);
    return `<tr class="${isBh ? "bench" : ""}"><td><b>${esc(name)}</b><br><span class="faint small">${esc(note)}</span></td>
      <td class="num">${fmt(b.number_of_trades, 0)}</td>
      <td class="num ${isBh ? "" : better(b.total_return, bh?.total_return)}">${pct(b.total_return)}</td>
      <td class="num ${isBh ? "" : better(b.cagr, bh?.cagr)}">${pct(b.cagr)}</td>
      <td class="num ${isBh ? "" : better(b.sharpe, bh?.sharpe)}">${fmt(b.sharpe)}</td>
      <td class="num ${isBh ? "" : better(b.max_drawdown, bh?.max_drawdown)}">${pct(b.max_drawdown)}</td>
      <td class="num">${share(b.exposure)}</td>
      <td class="num">${isBh ? "-" : share(b.win_rate)}</td>
      <td>${has ? `<button class="link small" data-show-replay="${esc(replayId)}">Show on chart</button>` : ""}</td></tr>`;
  };
  const key = (b) => `${b.config.phase}|${b.config.symbol}|${String(b.config.cost_bps).padStart(5, "0")}|${b.config.rule || "~"}`;
  const ledger = runs.slice().sort((a, b) => key(a).localeCompare(key(b)))
    .map((b) => `<tr><td>${esc(PHASE_WORD[b.config.phase] || b.config.phase)}</td><td>${esc(b.config.symbol)}</td><td class="num">${esc(b.config.cost_bps)} bps</td><td>${b.config.kind === "buy_and_hold" ? "Buy and hold" : `Rule ${esc(b.config.rule)}`}</td><td class="num">${fmt(b.number_of_trades, 0)}</td><td class="num">${pct(b.total_return)}</td><td class="num">${fmt(b.sharpe)}</td><td class="num bad">${pct(b.max_drawdown)}</td><td class="mono faint small" title="${esc(b.backtest_id)}">${esc(b.backtest_id.slice(0, 8))}</td></tr>`).join("");
  const period = (bh || rules[0])?.config.period;
  box.innerHTML = `<p class="muted">Pick which test to look at. Each rule sits next to simply buying and holding the same ETF over the same years. Green means it beat buy-and-hold on that number (for "worst drop", a smaller drop); red means it did not. A good past result is not proof of future profit.</p>
    <div class="row" style="margin:12px 0">${seg("phase", phases, "Test phase")}${seg("symbol", symbols, "Symbol")}${seg("cost", costs, "Trading cost per side")}</div>
    <p class="small faint">${esc(PHASE_WORD[L.phase] || L.phase)}${period ? `, ${esc(period.join(" to "))}` : ""}. ${L.phase === "held_out" ? "Data the strategy never saw while it was being designed. It was opened once." : "The years used while designing the strategy."} Cost is charged on every buy and every sell.</p>
    <div class="box"><div class="table-wrap"><table>
      <tr><th>Strategy</th><th class="num">Trades</th><th class="num">Total return</th><th class="num">Per year</th><th class="num">Sharpe</th><th class="num">Worst drop</th><th class="num">Time in market</th><th class="num">Winning trades</th><th></th></tr>
      ${rules.map((b) => row(b, `Rule ${b.config.rule}`, RULE_NOTE[b.config.rule] || "rule")).join("")}
      ${bh ? row(bh, "Buy and hold", "the benchmark: buy on day one, never sell") : ""}
    </table></div></div>
    ${more(`Show every run (${runs.length}), in plain labels`, `<p class="small muted">All of these count as trials. The more versions you try, the more likely the best one looks good by luck, which is why the review adjusts for them.</p>${markers.length ? `<p class="small faint">${markers.length} bookkeeping row${markers.length > 1 ? "s" : ""}, such as "held-out data opened", are not runs and are left out.</p>` : ""}<div class="table-wrap"><table><tr><th>Phase</th><th>Symbol</th><th class="num">Cost</th><th>Strategy</th><th class="num">Trades</th><th class="num">Return</th><th class="num">Sharpe</th><th class="num">Worst drop</th><th>Run id</th></tr>${ledger}</table></div>`)}`;
  box.querySelectorAll("[data-lab-phase],[data-lab-symbol],[data-lab-cost]").forEach((b) => (b.onclick = () => {
    if (b.dataset.labPhase) L.phase = b.dataset.labPhase;
    if (b.dataset.labSymbol) L.symbol = b.dataset.labSymbol;
    if (b.dataset.labCost) L.cost = Number(b.dataset.labCost);
    renderBacktests(d);
  }));
  box.querySelectorAll("[data-show-replay]").forEach((b) => (b.onclick = () => { window.pendingReplay = b.dataset.showReplay; go("chart"); }));
}

// ---------- Learn ----------
function renderMarkdown(src) {
  return String(src).split(/```/).map((block, i) => {
    if (i % 2 === 1) return `<pre><code>${esc(block.replace(/^\w*\n/, ""))}</code></pre>`;
    let html = "", list = null;
    const inline = (t) => t
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/~~([^~]+)~~/g, "<del>$1</del>")
      .replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>")
      .replace(/\[([^\]]+)\]/g, (whole, inner) => {
        // [file:line], [file:a-b], [file:a–b] or several separated by commas/semicolons
        const parts = inner.split(/[,;]\s*/);
        const refs = parts.map((x) => /^([\w./\-]+\.(?:md|py|json|txt))(?::(\d+)(?:[-–](\d+))?)?$/.exec(x.trim()));
        if (refs.some((r) => !r)) return whole;
        return refs.map((r) => `<button class="cite" data-file="${r[1]}"${r[2] ? ` data-line="${r[2]}${r[3] ? "-" + r[3] : ""}"` : ""}>[${r[1]}${r[2] ? ":" + r[2] + (r[3] ? "-" + r[3] : "") : ""}]</button>`).join(" ");
      });
    const close = () => { if (list) { html += `</${list}>`; list = null; } };
    for (const line of esc(block).split("\n")) {
      let m;
      if ((m = /^#{1,4}\s+(.*)$/.exec(line))) { close(); html += `<h4>${inline(m[1])}</h4>`; }
      else if ((m = /^\s*[-*]\s+(.*)$/.exec(line))) { if (list !== "ul") { close(); html += "<ul>"; list = "ul"; } html += `<li>${inline(m[1])}</li>`; }
      else if ((m = /^\s*\d+[.)]\s+(.*)$/.exec(line))) { if (list !== "ol") { close(); html += "<ol>"; list = "ol"; } html += `<li>${inline(m[1])}</li>`; }
      else if (!line.trim()) close();
      else { close(); html += `<p>${inline(line)}</p>`; }
    }
    close();
    return html;
  }).join("");
}
const STARTERS = [
  "Explain this whole project to me like I'm new to it.",
  "What is a backtest, and what makes one honest?",
  "What happened in the last research run, in plain words?",
];
const SUGGESTED = ["PLAN.md", "AGENTS.md", "README.md"];

RENDER.learn = async (main, opts = {}) => {
  const L = state.learn;
  const [sources, notes, journal, backends] = await Promise.all([
    L.sources ? Promise.resolve(L.sources) : api("/api/learn/sources"),
    api("/api/learn/notes"), api("/api/journal"), api("/api/backends"),
  ]);
  L.sources = sources;
  if (!L.selected.size) SUGGESTED.slice(0, 2).forEach((p) => L.selected.add(p));
  const usable = backends.filter((b) => b.available);
  if (!usable.some((b) => b.name === L.backend) && usable.length) L.backend = usable[0].name;
  const groups = sources.map((g) => `<details class="src-group" ${g.items.some((i) => L.selected.has(i.path)) ? "open" : ""}><summary>${esc(g.group)} (${g.items.length})</summary>
      ${g.items.map((i) => `<label class="src-item"><input type="checkbox" data-src="${esc(i.path)}" ${L.selected.has(i.path) ? "checked" : ""}><span class="name" title="${esc(i.path)}">${esc(i.path.split("/").pop())}</span><span class="size">${Math.max(1, Math.round(i.size / 1024))} KB</span><a href="#" data-file="${esc(i.path)}" class="small">view</a></label>`).join("")}</details>`).join("");
  const side = L.side === "notes"
    ? (notes.length ? notes.map((n) => `<p>${fileLink(n.path, n.title)}<br><span class="faint small">${esc(String(n.created).slice(0, 10))}</span></p>`).join("") : `<p class="muted small">Answers you save land here. They stay separate from the project's evidence.</p>`)
    : journal.map((j) => `<p><span class="faint small">${esc(j.date || "undated")}</span><br><b>${esc(j.id.startsWith("DEC") ? "Decision" : j.id)}</b> ${esc(j.title)}<br><button class="link small" data-journal="${esc(j.path)}" data-id="${esc(j.id)}">Explain this decision</button></p>`).join("");
  main.innerHTML = `${head("Learn", "Ask anything about this project. The tutor only reads the files you tick, and every claim links to the exact lines it came from.")}
    <div class="cols learn">
      <aside class="box" id="src-panel"><h2>What the tutor reads</h2><p class="faint small" id="src-count"></p>
        <input type="text" id="src-filter" placeholder="Find a file" style="width:100%;margin:6px 0 8px">
        <div style="max-height:62vh;overflow:auto">${groups}</div>
        <button class="link small" id="src-clear" style="margin-top:8px">Untick everything</button></aside>
      <section class="box" style="margin:0"><div class="chat" id="chat"></div>
        <div style="display:grid;gap:10px;margin-top:18px">
          <textarea id="question" rows="3" placeholder="Type a question. Enter sends, Shift+Enter adds a line."></textarea>
          <div class="row"><select id="backend" aria-label="Model">${backends.map((b) => `<option value="${esc(b.name)}" ${b.available ? "" : "disabled"} ${b.name === L.backend ? "selected" : ""}>${esc(b.label)}${b.available ? "" : " (not set up)"}</option>`).join("")}</select>
            <span class="grow"></span><button class="btn" id="new-chat">Start over</button><button class="btn primary" id="send">Ask</button></div></div></section>
      <aside class="box"><div class="subtabs seg"><button type="button" data-side="notes" aria-pressed="${L.side === "notes"}">Saved answers</button><button type="button" data-side="history" aria-pressed="${L.side === "history"}">Decisions</button></div>
        <div style="max-height:62vh;overflow:auto">${side}</div></aside>
    </div>`;
  const count = () => {
    const total = sources.flatMap((g) => g.items).filter((i) => L.selected.has(i.path)).reduce((a, i) => a + i.size, 0);
    const runs = [...L.selected].filter((p) => p.startsWith("run:")).length;
    $("#src-count").textContent = `${plural(L.selected.size, "file")} ticked${runs ? ` (including ${plural(runs, "run log")})` : ""}, about ${Math.max(1, Math.round(total / 4000))}k words.${L.screen ? " Plus what you were looking at on the chart." : ""}`;
  };
  count();
  $("#src-panel").addEventListener("change", (e) => { const p = e.target.dataset.src; if (!p) return; if (e.target.checked) L.selected.add(p); else L.selected.delete(p); count(); });
  $("#src-clear").onclick = () => { L.selected.clear(); document.querySelectorAll("[data-src]").forEach((c) => (c.checked = false)); count(); };
  $("#src-filter").oninput = (e) => { const q = e.target.value.toLowerCase(); document.querySelectorAll(".src-item").forEach((l) => (l.hidden = !l.querySelector("[data-src]").dataset.src.toLowerCase().includes(q))); if (q) document.querySelectorAll(".src-group").forEach((d) => (d.open = true)); };
  $("#backend").onchange = (e) => (L.backend = e.target.value);
  $("#new-chat").onclick = () => { L.messages = []; L.screen = null; drawChat(); };
  $("#send").onclick = ask;
  $("#question").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(); } });
  main.querySelectorAll("[data-side]").forEach((b) => (b.onclick = () => { L.side = b.dataset.side; go("learn"); }));
  main.querySelectorAll("[data-journal]").forEach((b) => (b.onclick = () => { L.selected.add(b.dataset.journal); go("learn", { question: `Explain ${b.dataset.id} in plain words: what problem it solved, what was decided, and what changed because of it.` }); }));
  drawChat();
  if (opts.question) { $("#question").value = opts.question; ask(); }
};

function drawChat() {
  const box = $("#chat");
  if (!box) return;
  const L = state.learn;
  if (!L.messages.length) {
    box.innerHTML = `<div><h2>Where to start</h2><p class="muted">Pick a question, or type your own below.</p><div class="chips">${STARTERS.map((s) => `<button class="chip" type="button">${esc(s)}</button>`).join("")}</div></div>`;
    box.querySelectorAll(".chip").forEach((b) => (b.onclick = () => { $("#question").value = b.textContent; if (b.textContent.includes("last research run")) addLatestRun().then(ask); else ask(); }));
    return;
  }
  box.innerHTML = L.messages.map((m, i) => m.role === "user"
    ? `<div class="msg you"><div class="who">You</div><div class="body">${esc(m.text)}</div></div>`
    : `<div class="msg"><div class="who">Tutor${m.done && !m.error && m.text ? ` <button class="link small" data-save="${i}">Save this answer</button>` : ""}</div>
       ${m.sources ? `<p class="read">Read ${m.sources.map((s) => esc(s.path.split("/").pop()) + (s.truncated ? " (partly, it was too long)" : "")).join(", ")}</p>` : ""}
       <div class="md ${m.done ? "" : "typing"}">${m.error ? `<p class="error">${esc(m.error)}</p>` : renderMarkdown(m.text)}</div></div>`).join("");
  box.querySelectorAll("[data-save]").forEach((b) => (b.onclick = async () => {
    const i = Number(b.dataset.save);
    const q = L.messages[i - 1]?.text || "";
    try { const r = await send("/api/learn/notes", { question: q, answer: L.messages[i].text, sources: L.messages[i].sources.map((s) => s.path), backend: L.messages[i].backend, title: q.slice(0, 80) }); toast(`Saved to ${r.path}`, "good"); b.remove(); } catch (e) { toast(e.message, "bad"); }
  }));
  box.lastElementChild?.scrollIntoView({ block: "nearest" });
}
async function addLatestRun() {
  try { const runs = await api("/api/runs/described?limit=1"); if (runs[0]) state.learn.selected.add(`run:${runs[0].run_id}`); } catch (e) { /* ask anyway */ }
}

async function ask() {
  const L = state.learn;
  const q = $("#question").value.trim();
  if (!q || L.busy) return;
  if (!L.selected.size && !L.screen) { toast("Tick at least one file on the left for the tutor to read.", "bad"); return; }
  L.busy = true;
  $("#send").disabled = true;
  $("#question").value = "";
  const history = L.messages.filter((m) => !m.error).map((m) => ({ role: m.role, text: m.text }));
  L.messages.push({ role: "user", text: q });
  const reply = { role: "tutor", text: "", done: false, backend: L.backend };
  L.messages.push(reply);
  drawChat();
  try {
    const res = await fetch("/api/learn/ask", { method: "POST", headers: { "Content-Type": "application/json", "X-Brain-Terminal": "1" }, body: JSON.stringify({ question: q, sources: [...L.selected], backend: L.backend, history, screen_context: L.screen || undefined }) });
    if (!res.ok) { let d = res.statusText; try { d = (await res.json()).detail; } catch (e) { /* not json */ } throw new Error(d); }
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

// ---------- Setup ----------
RENDER.setup = async (main) => {
  const [d, backends, sk] = await Promise.all([api("/api/schedules"), api("/api/backends"), api("/api/skills")]);
  const lastRun = (id) => d.runs.find((r) => r.job_id === id);
  const autos = d.schedules.map((s) => {
    const lr = lastRun(s.job_id);
    return `<article class="box" style="margin-bottom:10px"><div class="row">
        <div class="grow"><h3 style="margin:0">${esc(s.name)}</h3><p class="muted small" style="margin:2px 0 0">${esc(KIND_TEXT[s.kind] || s.kind)}</p></div>
        <label class="switch" title="${s.kind_enabled ? "" : "Paused by a project decision"}"><input type="checkbox" data-toggle="${esc(s.job_id)}" ${s.enabled ? "checked" : ""} ${s.kind_enabled ? "" : "disabled"}> ${s.enabled ? "On" : "Off"}</label></div>
      <div class="row small" style="margin-top:10px"><span class="faint">Runs ${esc(s.cadence_text)}${s.task?.next_run ? `, next ${esc(s.task.next_run)}` : ""}.</span>
        <span class="faint">${lr ? `Last run ${esc(ago(lr.started_at))}: ${esc((STATUS_WORD[lr.status] || lr.status).toLowerCase())}.` : "Never run."}</span><span class="grow"></span>
        ${s.kind_enabled ? `<button class="btn" data-run-now="${esc(s.job_id)}">Run now</button>` : ""}<button class="link small" data-edit="${esc(s.job_id)}">Edit</button></div></article>`;
  }).join("");
  const history = d.runs.map((r) => `<tr data-log="${esc(r.run_id)}" style="cursor:pointer"><td class="faint">${esc(ago(r.started_at))}</td><td>${esc(r.job_id)}</td><td>${status(r.status)}</td><td class="wrap">${esc(clip(r.summary || "", 160))}</td></tr>`).join("");
  const list = (items) => `<ul class="feed">${items.map((s) => `<li><span class="when small">${esc(s.origin || "")}</span><div><b>${esc(s.name)}</b><div class="muted small">${esc(clip(s.description || "", 200))}</div></div></li>`).join("") || `<li><span></span><div class="muted">None</div></li>`}</ul>`;
  main.innerHTML = `${head("Setup", "Automations that run on their own, the AI models the terminal can use, and what can act on this project.")}
    <section><div class="row" style="margin-bottom:12px"><h2 style="margin:0" class="grow">Automations</h2><button class="btn primary" id="new-schedule">New automation</button></div>
      ${d.scheduler.drift.length ? `<p class="warn">Windows Task Scheduler is out of step: ${d.scheduler.drift.map(esc).join("; ")}</p>` : ""}
      <div id="schedule-form"></div>${autos}
      <p class="faint small">${d.scheduler.available ? "Turning one on adds it to Windows Task Scheduler, so it runs even when this page is closed. Each run has a time limit and a daily cap." : "Windows Task Scheduler isn't available here. You can still use Run now."}</p>
      ${d.runs.length ? more(`Show automation history (${d.runs.length})`, `<div class="table-wrap"><table><tr><th>When</th><th>Automation</th><th>Result</th><th>Summary</th></tr>${history}</table></div><div id="job-log"></div>`) : ""}</section>
    <section><h2>AI models</h2><div class="box"><ul class="feed">${backends.map((b) => `<li><span class="when">${b.available ? `<span class="good">Ready</span>` : `<span class="faint">Off</span>`}</span><div><b>${esc(b.label)}</b><div class="muted small">${esc(b.available ? b.detail : b.sign_in)}</div></div></li>`).join("")}</ul>
      <p class="faint small">The terminal uses the Claude app you're already signed in to. It never sees or stores a password or token.</p></div></section>
    <section><h2>What can act on this project</h2>
      ${more(`Project agents (${sk.harness.length})`, `<ul class="feed">${sk.harness.map((a) => `<li><span class="when small">${a.enabled ? "on" : "off"}</span><div><b>${esc(a.name)}</b> ${fileLink(a.path, "definition")}<div class="muted small">Handles ${esc((a.handles || []).join(", "))}. Model: ${esc(a.model || "none, rule-based")}. Can write to ${esc((a.write_paths || []).join(", ") || "nothing")}.</div></div></li>`).join("")}</ul>`)}
      ${more(`Claude Code skills (${sk.claude.length})`, list(sk.claude))}
      ${more(`Codex skills (${sk.codex.length})`, list(sk.codex))}</section>`;
  $("#new-schedule").onclick = () => scheduleForm(d);
  main.querySelectorAll("[data-edit]").forEach((b) => (b.onclick = () => scheduleForm(d, d.schedules.find((s) => s.job_id === b.dataset.edit))));
  main.querySelectorAll("[data-toggle]").forEach((c) => (c.onchange = async () => {
    c.disabled = true;
    try { await send(`/api/schedules/${c.dataset.toggle}`, { enabled: c.checked }, "PUT"); toast(`${c.dataset.toggle} is now ${c.checked ? "on" : "off"}.`, "good"); } catch (e) { toast(e.message, "bad"); }
    go("setup");
  }));
  main.querySelectorAll("[data-run-now]").forEach((b) => (b.onclick = async () => {
    b.disabled = true; b.textContent = "Started";
    try { await send(`/api/schedules/${b.dataset.runNow}/run`); toast("Started. You'll see the result here when it finishes."); } catch (e) { toast(e.message, "bad"); }
  }));
  main.querySelectorAll("[data-log]").forEach((tr) => (tr.onclick = async () => {
    try { const l = await api(`/api/job-runs/${tr.dataset.log}/log`); $("#job-log").innerHTML = `<pre class="pre">${esc(l.log)}</pre>`; } catch (e) { $("#job-log").innerHTML = `<p class="error">${esc(e.message)}</p>`; }
  }));
};

// ---------- Risk Center ----------
RENDER.risk = async (main) => {
  const [drawdowns] = await Promise.all([
    api("/api/risk/drawdown-table").catch(() => ({ table: [] })),
  ]);

  main.innerHTML = `${head("Risk Center", "Position sizing, recovery math, and Monte Carlo probability of ruin. Learn to survive before hoping for returns.")}
    <div class="cols">
      <div class="stack">
        <section class="box">
          <div class="row" style="margin-bottom:12px">
            <h2 style="margin:0">1. Position Sizing (Fixed % Risk)</h2>
            <span class="grow"></span>
            <button class="btn small" id="risk-explain-ps" type="button">Ask Tutor</button>
          </div>
          <p class="muted small">How many shares to buy so that hitting your stop-loss loses only your pre-set risk budget.</p>
          <div class="form" style="margin:16px 0">
            <label class="field">Account Size ($)
              <input type="number" id="ps-account" value="10000" min="500" step="500">
            </label>
            <label class="field">Risk Per Trade (%)
              <input type="number" id="ps-risk-pct" value="1.0" min="0.1" max="10" step="0.1">
            </label>
            <label class="field">Entry Price ($)
              <input type="number" id="ps-entry" value="100.00" min="1" step="0.5">
            </label>
            <label class="field">Stop-Loss Price ($)
              <input type="number" id="ps-stop" value="95.00" min="0.5" step="0.5">
            </label>
          </div>
          <div class="stats compact" id="ps-stats"></div>
          <div class="box" id="ps-explain" style="background:var(--surface-2);border-color:var(--accent);margin-top:12px;font-size:14px;line-height:1.5"></div>
        </section>

        <section class="box">
          <div class="row" style="margin-bottom:12px">
            <h2 style="margin:0">2. Monte Carlo Risk of Ruin</h2>
            <span class="grow"></span>
            <button class="btn small" id="risk-explain-ruin" type="button">Ask Tutor</button>
          </div>
          <p class="muted small">Simulate 2,000 independent traders over 200 trades with your exact win rate and risk. See how many suffer a catastrophic drawdown.</p>
          <div class="form" style="margin:16px 0">
            <label class="field">Win Rate (%)
              <input type="number" id="ruin-win-rate" value="50" min="10" max="90" step="1">
            </label>
            <label class="field">Payoff Ratio (Win/Loss)
              <input type="number" id="ruin-payoff" value="1.5" min="0.5" max="5.0" step="0.1">
            </label>
            <label class="field">Risk per Trade (%)
              <input type="number" id="ruin-risk-pct" value="2.0" min="0.5" max="25" step="0.5">
            </label>
            <label class="field">Ruin Threshold (% Drop)
              <input type="number" id="ruin-threshold" value="50" min="20" max="90" step="5">
            </label>
          </div>
          <div class="row" style="margin-bottom:14px">
            <button class="btn primary" id="ruin-btn" type="button">Run 2,000 Simulation Paths</button>
            <span id="ruin-loading" class="muted small" hidden>Simulating 2,000 paths...</span>
          </div>
          <div class="stats compact" id="ruin-stats"></div>
          <div class="box" id="ruin-explain" style="background:var(--surface-2);margin-top:12px;font-size:14px;line-height:1.5"></div>
        </section>
      </div>

      <div class="stack">
        <section class="box">
          <h2>The Non-Linear Drawdown Trap</h2>
          <p class="muted small">Why losing 50% does not mean you need a 50% gain to get back. Big losses require exponential recoveries.</p>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Loss</th><th>Gain Needed to Break Even</th><th>Difficulty</th></tr>
              </thead>
              <tbody>
                ${(drawdowns.table || []).map((r) => {
                  const tag = r.loss_pct <= 20 ? "Manageable" : r.loss_pct <= 40 ? "Difficult" : r.loss_pct <= 50 ? "Severe (+100%)" : "Near-Impossible";
                  const toneClass = r.loss_pct <= 20 ? "good" : r.loss_pct <= 40 ? "warn" : "bad";
                  return `<tr>
                    <td><b>-${esc(r.loss_pct)}%</b></td>
                    <td class="${toneClass}"><b>+${esc(r.gain_needed_pct)}%</b></td>
                    <td class="small ${toneClass}">${esc(tag)}</td>
                  </tr>`;
                }).join("")}
              </tbody>
            </table>
          </div>
        </section>

        <section class="box">
          <h2>Kelly Criterion & Leverage</h2>
          <p class="muted small">The mathematical formula for maximum compounding growth. Notice how aggressive full-Kelly is compared to realistic sizing.</p>
          <div class="stats compact" id="kelly-stats"></div>
          <div class="box" id="kelly-explain" style="background:var(--surface-2);font-size:13px;color:var(--muted)"></div>
        </section>
      </div>
    </div>`;

  const updatePS = async () => {
    try {
      const acc = Number($("#ps-account").value) || 10000;
      const r = Number($("#ps-risk-pct").value) || 1;
      const entry = Number($("#ps-entry").value) || 100;
      const stop = Number($("#ps-stop").value) || 95;
      const res = await send("/api/risk/position-size", { account: acc, risk_pct: r, entry, stop });
      $("#ps-stats").innerHTML = `
        <div><b>${esc(res.shares)}</b><span>Shares to buy</span></div>
        <div><b>$${esc(fmt(res.position_value, 0))}</b><span>Position value (${esc(fmt(res.position_pct_of_account, 1))}%)</span></div>
        <div><b class="warn">$${esc(fmt(res.dollar_risk, 2))}</b><span>Risk at stop (${esc(fmt(res.risk_pct_of_account, 1))}%)</span></div>
      `;
      $("#ps-explain").innerHTML = `<p style="margin:0">${esc(res.explain)}</p>`;
    } catch (e) {
      $("#ps-stats").innerHTML = `<span class="error small">${esc(e.message)}</span>`;
    }
  };

  const updateKelly = async () => {
    try {
      const win = (Number($("#ruin-win-rate").value) || 50) / 100;
      const payoff = Number($("#ruin-payoff").value) || 1.5;
      const res = await send("/api/risk/kelly", { win_rate: win, payoff });
      $("#kelly-stats").innerHTML = `
        <div><b>${esc(pct(res.full, 1))}</b><span>Full Kelly Size</span></div>
        <div><b class="good">${esc(pct(res.half, 1))}</b><span>Half Kelly (Recommended)</span></div>
      `;
      $("#kelly-explain").innerHTML = `<p style="margin:0">${esc(res.explain)}</p>`;
    } catch (e) {
      $("#kelly-stats").innerHTML = `<span class="error small">${esc(e.message)}</span>`;
    }
  };

  const runRuin = async () => {
    const btn = $("#ruin-btn");
    const loading = $("#ruin-loading");
    if (!btn) return;
    btn.disabled = true;
    if (loading) loading.hidden = false;
    try {
      const win = (Number($("#ruin-win-rate").value) || 50) / 100;
      const payoff = Number($("#ruin-payoff").value) || 1.5;
      const riskPct = Number($("#ruin-risk-pct").value) || 2;
      const ruinThreshold = Number($("#ruin-threshold").value) || 50;
      const res = await send("/api/risk/ruin-sim", {
        win_rate: win, payoff, risk_pct: riskPct,
        ruin_drawdown_pct: ruinThreshold, trades: 200, paths: 2000,
      });
      const ruinPct = res.probability_of_ruin * 100;
      const toneClass = ruinPct < 1 ? "good" : ruinPct < 10 ? "warn" : "bad";
      $("#ruin-stats").innerHTML = `
        <div><b class="${toneClass}">${esc(fmt(ruinPct, 1))}%</b><span>Ruin Probability (${res.inputs.ruin_drawdown_pct}% DD)</span></div>
        <div><b class="bad">-${esc(fmt(res.worst_drawdown_median_pct, 1))}%</b><span>Median Worst Drawdown</span></div>
        <div><b class="good">${esc(fmt(res.final_equity_percentiles["50"], 2))}x</b><span>Median Ending Equity</span></div>
      `;
      $("#ruin-explain").innerHTML = `<p style="margin:0">${esc(res.explain)}</p>`;
    } catch (e) {
      $("#ruin-stats").innerHTML = `<span class="error small">${esc(e.message)}</span>`;
    } finally {
      btn.disabled = false;
      if (loading) loading.hidden = true;
    }
  };

  ["#ps-account", "#ps-risk-pct", "#ps-entry", "#ps-stop"].forEach((id) => $(id)?.addEventListener("input", updatePS));
  ["#ruin-win-rate", "#ruin-payoff"].forEach((id) => $(id)?.addEventListener("input", updateKelly));
  $("#ruin-btn")?.addEventListener("click", runRuin);

  $("#risk-explain-ps").onclick = () => {
    go("learn", { question: "Explain position sizing: why does stop distance determine share count rather than account balance alone?" });
  };
  $("#risk-explain-ruin").onclick = () => {
    go("learn", { question: "Explain Monte Carlo risk of ruin: why does risking 5% or 10% per trade guarantee eventual bankruptcy even with a positive edge?" });
  };

  updatePS();
  updateKelly();
  runRuin();
};

// ---------- Market & Screener ----------
RENDER.market = async (main) => {
  const [snapshot, calendar] = await Promise.all([
    api("/api/market/snapshot").catch(() => null),
    api("/api/market/calendar").catch(() => null),
  ]);

  main.innerHTML = `${head("Market Screener & Macro Calendar", "End-of-day multi-asset universe screening with provenance badges and FOMC economic events.")}
    <div class="subtabs" style="margin-bottom:16px">
      <button class="btn primary" id="mkt-tab-screen" type="button">Screener (${(snapshot?.rows || []).length} Symbols)</button>
      <button class="btn" id="mkt-tab-cal" type="button">Macro Calendar (${(calendar?.events || []).length} Events)</button>
    </div>

    <div id="mkt-view-screen">
      <div class="row" style="margin-bottom:14px">
        <label class="field" style="min-width:240px">Preset Filter
          <select id="screen-preset">
            <option value="">All symbols (${(snapshot?.rows || []).length})</option>
            ${Object.entries(snapshot?.presets || {}).map(([k, v]) => `<option value="${esc(k)}">${esc(v.label)}</option>`).join("")}
          </select>
        </label>
        <span class="grow"></span>
        <span class="badge" title="Data provenance verified against committed manifests">Provenance: ${esc(snapshot?.universe || "starter")} (EOD)</span>
      </div>
      <p class="muted small" id="preset-why" style="margin-bottom:16px"></p>
      <div class="table-wrap box">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Name</th>
              <th>Price</th>
              <th>1D %</th>
              <th>1M %</th>
              <th>RSI(2)</th>
              <th>RSI(14)</th>
              <th>vs SMA200</th>
              <th>Freshness</th>
            </tr>
          </thead>
          <tbody id="screener-body"></tbody>
        </table>
      </div>
    </div>

    <div id="mkt-view-cal" hidden>
      <div class="box" style="margin-bottom:16px">
        <h2>Federal Reserve (FOMC) & Economic Indicators</h2>
        <p class="muted small">${esc(calendar?.note || "")}</p>
        <ul class="feed" style="margin-top:14px">
          ${(calendar?.events || []).map((ev) => `<li>
            <span class="when mono"><b>${esc(ev.date)}</b></span>
            <div>
              <div class="who">${esc(ev.title)} <span class="badge">${esc(ev.importance || "high")}</span></div>
              <div class="what" style="margin-top:4px">${esc(ev.why || "")}</div>
              <div class="faint small" style="margin-top:2px">Source: ${esc(ev.source || "")}</div>
            </div>
          </li>`).join("")}
        </ul>
      </div>
    </div>`;

  const renderScreenerRows = (presetKey) => {
    const rows = snapshot?.rows || [];
    const preset = snapshot?.presets?.[presetKey];
    $("#preset-why").innerHTML = preset ? `<b>Why a quant looks:</b> ${esc(preset.why)} <br><span class="bad"><b>The trap:</b> ${esc(preset.trap)}</span>` : "Click any symbol row to open the full interactive chart.";

    let filtered = rows;
    if (presetKey === "oversold_uptrend") {
      filtered = rows.filter((r) => r.rsi_2 < 10 && r.above_sma_200 === true);
    } else if (presetKey === "strong_momentum") {
      filtered = rows.filter((r) => r.rsi_14 > 60 && r.change_1m_pct > 5);
    } else if (presetKey === "pullback") {
      filtered = rows.filter((r) => r.change_1d_pct < -1.5 && r.above_sma_200 === true);
    } else if (presetKey === "high_volatility") {
      filtered = rows.filter((r) => r.rsi_2 < 5 || r.rsi_2 > 95);
    }

    $("#screener-body").innerHTML = filtered.map((r) => {
      const tone1d = (r.change_1d_pct ?? 0) >= 0 ? "good" : "bad";
      const tone1m = (r.change_1m_pct ?? 0) >= 0 ? "good" : "bad";
      const rsi2Tone = r.rsi_2 < 10 ? "good" : r.rsi_2 > 90 ? "bad" : "";
      return `<tr class="click" data-sym="${esc(r.symbol)}">
        <td><b class="mono" style="color:var(--accent)">${esc(r.symbol)}</b></td>
        <td class="small muted">${esc(clip(r.name, 28))}</td>
        <td class="mono num">$${esc(fmt(r.close, 2))}</td>
        <td class="mono num ${tone1d}">${esc(pct((r.change_1d_pct ?? 0) / 100, 1))}</td>
        <td class="mono num ${tone1m}">${esc(pct((r.change_1m_pct ?? 0) / 100, 1))}</td>
        <td class="mono num ${rsi2Tone}"><b>${esc(fmt(r.rsi_2, 1))}</b></td>
        <td class="mono num">${esc(fmt(r.rsi_14, 1))}</td>
        <td class="mono num ${(r.vs_sma_200_pct ?? 0) >= 0 ? "good" : "bad"}">${esc(pct((r.vs_sma_200_pct ?? 0) / 100, 1))}</td>
        <td><span class="badge small">${esc(r.provenance?.freshness || "EOD")}</span></td>
      </tr>`;
    }).join("") || `<tr><td colspan="9" class="empty">No symbols matched this preset filter.</td></tr>`;

    $("#screener-body").querySelectorAll("tr.click").forEach((tr) => {
      tr.onclick = () => {
        CH.symbol = tr.dataset.sym;
        CH.formula = "";
        saveCH();
        go("chart");
      };
    });
  };

  $("#screen-preset").onchange = (e) => renderScreenerRows(e.target.value);
  renderScreenerRows("");

  $("#mkt-tab-screen").onclick = () => {
    $("#mkt-tab-screen").className = "btn primary";
    $("#mkt-tab-cal").className = "btn";
    $("#mkt-view-screen").hidden = false;
    $("#mkt-view-cal").hidden = true;
  };
  $("#mkt-tab-cal").onclick = () => {
    $("#mkt-tab-cal").className = "btn primary";
    $("#mkt-tab-screen").className = "btn";
    $("#mkt-view-screen").hidden = true;
    $("#mkt-view-cal").hidden = false;
  };
};

// ---------- Live Crypto Feed ----------
RENDER.live = async (main) => {
  let activeProduct = "BTC-USD";
  const stateFeed = {
    "BTC-USD": { price: null, bid: null, ask: null, change: null, high: null, low: null, volume: null, trades: [], bids: [], asks: [] },
    "ETH-USD": { price: null, bid: null, ask: null, change: null, high: null, low: null, volume: null, trades: [], bids: [], asks: [] },
  };

  main.innerHTML = `${head("Live Crypto Feed (Public WebSocket)", "Real-time, zero-key streaming from Coinbase Advanced Trade. Watch ticks, spread, and order book depth live.")}
    <div class="row" style="margin-bottom:16px">
      <div class="seg" id="live-prod-seg">
        <button type="button" data-prod="BTC-USD" aria-pressed="true">BTC-USD</button>
        <button type="button" data-prod="ETH-USD">ETH-USD</button>
      </div>
      <span class="grow"></span>
      <div class="live on" id="crypto-conn-pill"><i></i><span>Connecting to Coinbase WS</span></div>
    </div>

    <div class="cols">
      <div class="stack">
        <section class="box">
          <div class="row" style="align-items:baseline">
            <h1 id="live-price" class="mono" style="font-size:38px;margin:0;letter-spacing:-0.03em;color:var(--accent)">$--.--</h1>
            <span id="live-change" class="mono" style="font-size:16px;font-weight:600">--</span>
          </div>
          <div class="stats compact" style="margin-top:14px">
            <div><b id="live-bid" class="mono good">$--.--</b><span>Best Bid</span></div>
            <div><b id="live-ask" class="mono bad">$--.--</b><span>Best Ask</span></div>
            <div><b id="live-spread" class="mono">$--.--</b><span>Spread</span></div>
            <div><b id="live-vol" class="mono">--</b><span>24h Volume</span></div>
          </div>
        </section>

        <section class="box">
          <h2>Recent Real-Time Trades</h2>
          <p class="muted small">Executed market trades streaming tick-by-tick directly from the exchange tape.</p>
          <div class="table-wrap" style="max-height:300px;overflow:auto">
            <table>
              <thead><tr><th>Time</th><th>Side</th><th>Price</th><th>Size</th></tr></thead>
              <tbody id="live-trades-tape"></tbody>
            </table>
          </div>
        </section>
      </div>

      <div class="stack">
        <section class="box">
          <h2>10-Level Real-Time Order Book</h2>
          <p class="muted small">Visualizing resting limit orders: Asks (sellers) on top, Bids (buyers) below.</p>
          <div style="display:grid;gap:12px;margin-top:10px">
            <div>
              <div class="faint small" style="margin-bottom:4px">ASKS (Sellers)</div>
              <div id="live-book-asks" style="display:grid;gap:2px"></div>
            </div>
            <div id="live-mid-spread" class="row" style="padding:6px 0;border-block:1px solid var(--line);font-size:12px;color:var(--muted)">
              <span>Mid Market</span>
              <span class="grow"></span>
              <span id="live-spread-detail">Spread: --</span>
            </div>
            <div>
              <div class="faint small" style="margin-bottom:4px">BIDS (Buyers)</div>
              <div id="live-book-bids" style="display:grid;gap:2px"></div>
            </div>
          </div>
        </section>
      </div>
    </div>`;

  const renderActive = () => {
    const data = stateFeed[activeProduct];
    if (data.price != null) {
      $("#live-price").textContent = `$${fmt(data.price, 2)}`;
      const chg = data.change != null ? (data.change >= 0 ? "+" : "") + data.change.toFixed(2) + "%" : "--";
      $("#live-change").textContent = chg;
      $("#live-change").className = "mono " + (data.change >= 0 ? "good" : "bad");
      $("#live-bid").textContent = `$${fmt(data.bid, 2)}`;
      $("#live-ask").textContent = `$${fmt(data.ask, 2)}`;
      const spread = data.ask != null && data.bid != null ? Math.max(0, data.ask - data.bid) : 0;
      $("#live-spread").textContent = `$${fmt(spread, 2)}`;
      $("#live-spread-detail").textContent = `Spread: $${fmt(spread, 2)} (${((spread / data.price) * 100).toFixed(3)}%)`;
      $("#live-vol").textContent = fmt(data.volume, 2);
    }

    $("#live-trades-tape").innerHTML = (data.trades || []).slice(0, 15).map((t) => {
      const isBuy = t.side === "buy";
      return `<tr>
        <td class="mono faint small">${esc(String(t.time || "").slice(11, 19))}</td>
        <td class="${isBuy ? "good" : "bad"} small"><b>${isBuy ? "BUY" : "SELL"}</b></td>
        <td class="mono num ${isBuy ? "good" : "bad"}">$${esc(fmt(t.price, 2))}</td>
        <td class="mono num faint">${esc(fmt(t.size, 4))}</td>
      </tr>`;
    }).join("");

    const maxQty = Math.max(...(data.bids || []).map((b) => b[1]), ...(data.asks || []).map((a) => a[1]), 0.01);
    $("#live-book-asks").innerHTML = (data.asks || []).slice(-7).reverse().map(([p, q]) => {
      const pctWidth = Math.min(100, Math.round((q / maxQty) * 100));
      return `<div class="row mono small" style="position:relative;padding:3px 6px">
        <div style="position:absolute;inset:0;right:${100 - pctWidth}%;background:rgba(239,107,107,0.18);border-radius:2px;pointer-events:none"></div>
        <span class="bad num">$${esc(fmt(p, 2))}</span>
        <span class="grow"></span>
        <span class="faint num">${esc(fmt(q, 4))}</span>
      </div>`;
    }).join("");

    $("#live-book-bids").innerHTML = (data.bids || []).slice(0, 7).map(([p, q]) => {
      const pctWidth = Math.min(100, Math.round((q / maxQty) * 100));
      return `<div class="row mono small" style="position:relative;padding:3px 6px">
        <div style="position:absolute;inset:0;right:${100 - pctWidth}%;background:rgba(92,201,143,0.18);border-radius:2px;pointer-events:none"></div>
        <span class="good num">$${esc(fmt(p, 2))}</span>
        <span class="grow"></span>
        <span class="faint num">${esc(fmt(q, 4))}</span>
      </div>`;
    }).join("");
  };

  document.querySelectorAll("#live-prod-seg button").forEach((b) => {
    b.onclick = () => {
      document.querySelectorAll("#live-prod-seg button").forEach((x) => x.removeAttribute("aria-pressed"));
      b.setAttribute("aria-pressed", "true");
      activeProduct = b.dataset.prod;
      renderActive();
    };
  });

  if (state.liveSource) {
    try { state.liveSource.close(); } catch (e) {}
  }
  const sse = new EventSource("/api/live/crypto?products=BTC-USD,ETH-USD");
  state.liveSource = sse;

  sse.onopen = () => {
    const pill = $("#crypto-conn-pill");
    if (pill) { pill.className = "live on"; pill.querySelector("span").textContent = "Connected (Coinbase WS)"; }
  };
  sse.onerror = () => {
    const pill = $("#crypto-conn-pill");
    if (pill) { pill.className = "live off"; pill.querySelector("span").textContent = "Reconnecting feed"; }
  };

  sse.addEventListener("ticker", (e) => {
    const ev = JSON.parse(e.data);
    const prod = ev.product;
    if (stateFeed[prod]) {
      stateFeed[prod].price = ev.price;
      stateFeed[prod].bid = ev.bid;
      stateFeed[prod].ask = ev.ask;
      stateFeed[prod].change = ev.change_24h_pct;
      stateFeed[prod].high = ev.high_24h;
      stateFeed[prod].low = ev.low_24h;
      stateFeed[prod].volume = ev.volume_24_h || ev.volume_24h;
      if (prod === activeProduct) renderActive();
    }
  });

  sse.addEventListener("trade", (e) => {
    const ev = JSON.parse(e.data);
    const prod = ev.product;
    if (stateFeed[prod]) {
      stateFeed[prod].trades.unshift(ev);
      if (stateFeed[prod].trades.length > 50) stateFeed[prod].trades.pop();
      if (prod === activeProduct) renderActive();
    }
  });

  sse.addEventListener("book", (e) => {
    const ev = JSON.parse(e.data);
    const prod = ev.product;
    if (stateFeed[prod]) {
      stateFeed[prod].bids = ev.bids || [];
      stateFeed[prod].asks = ev.asks || [];
      if (prod === activeProduct) renderActive();
    }
  });
};

function scheduleForm(d, s = null) {
  const box = $("#schedule-form");
  const kinds = d.kinds.filter((k) => k.enabled || (s && s.kind === k.kind));
  const c = s?.cadence || { type: "daily", time: "09:00" };
  const cfg = s?.config || {};
  box.innerHTML = `<form class="box" id="sf" style="margin-bottom:14px"><h3>${s ? `Edit ${esc(s.name)}` : "New automation"}</h3><div class="form">
    <label class="field">Name<input type="text" id="sf-name" value="${esc(s?.name || "")}" required></label>
    <label class="field">Short id (letters, digits, dashes)<input type="text" id="sf-id" value="${esc(s?.job_id || "")}" ${s ? "disabled" : ""} placeholder="morning-note" required></label>
    <label class="field">What it does<select id="sf-kind">${kinds.map((k) => `<option value="${k.kind}" ${s?.kind === k.kind ? "selected" : ""}>${esc(k.label)}</option>`).join("")}</select></label>
    <label class="field">How often<select id="sf-type">${[["daily", "Every day"], ["weekdays", "Weekdays"], ["weekly", "Some days of the week"], ["hourly", "Every few hours"]].map(([v, l]) => `<option value="${v}" ${c.type === v ? "selected" : ""}>${l}</option>`).join("")}</select></label>
    <label class="field" id="f-time">At<input type="time" id="sf-time" value="${esc(c.time || "09:00")}"></label>
    <label class="field" id="f-days">Days (e.g. MON,THU)<input type="text" id="sf-days" value="${esc((c.days || ["SAT"]).join(","))}"></label>
    <label class="field" id="f-every">Every N hours<input type="number" id="sf-every" min="1" max="23" value="${esc(c.every || 6)}"></label>
    <label class="field">At most, times per day<input type="number" id="sf-max" min="1" max="48" value="${esc(s?.max_runs_per_day || 4)}"></label>
  </div><p class="muted small" id="sf-kind-text"></p><div id="sf-config"></div>
  <div class="row" style="margin-top:12px"><label class="switch"><input type="checkbox" id="sf-enabled" ${s?.enabled ? "checked" : ""}> Turn on</label><span class="grow"></span>
  ${s ? `<button type="button" class="btn" id="sf-delete">Delete</button>` : ""}<button type="button" class="btn" id="sf-cancel">Cancel</button><button class="btn primary">Save</button></div><p class="error" id="sf-err"></p></form>`;
  const sync = () => {
    const kind = $("#sf-kind").value, type = $("#sf-type").value;
    $("#sf-kind-text").textContent = KIND_TEXT[kind] || "";
    $("#f-time").hidden = type === "hourly"; $("#f-days").hidden = type !== "weekly"; $("#f-every").hidden = type !== "hourly";
    const el = $("#sf-config");
    if (kind === "data_refresh") el.innerHTML = `<div class="form"><label class="field">Symbols<input type="text" id="cf-symbols" value="${esc((cfg.symbols || ["SPY", "QQQ", "IWM"]).join(" "))}"></label><label class="field">From date<input type="text" id="cf-start" value="${esc(cfg.start || "2000-01-01")}"></label></div>`;
    else if (kind === "agent_prompt") el.innerHTML = `<label class="field">Question to ask<textarea id="cf-prompt" rows="3">${esc(cfg.prompt || "")}</textarea></label><p class="small muted" style="margin:8px 0 4px">Give it this context:</p>${Object.entries(d.context_options).map(([k, v]) => `<label class="check"><input type="checkbox" class="cf-ctx" value="${k}" ${(cfg.context || []).includes(k) ? "checked" : ""}> ${esc(v)}</label>`).join("")}`;
    else el.innerHTML = "";
  };
  $("#sf-kind").onchange = sync; $("#sf-type").onchange = sync; sync();
  $("#sf-cancel").onclick = () => (box.innerHTML = "");
  if (s) $("#sf-delete").onclick = async () => { await api(`/api/schedules/${s.job_id}`, { method: "DELETE" }); go("setup"); };
  $("#sf").onsubmit = async (e) => {
    e.preventDefault();
    const kind = $("#sf-kind").value, type = $("#sf-type").value;
    const cadence = type === "hourly" ? { type, every: Number($("#sf-every").value) } : type === "weekly" ? { type, time: $("#sf-time").value, days: $("#sf-days").value.split(/[ ,]+/).filter(Boolean) } : { type, time: $("#sf-time").value };
    const config = kind === "data_refresh" ? { symbols: $("#cf-symbols").value.toUpperCase().split(/[ ,]+/).filter(Boolean), start: $("#cf-start").value }
      : kind === "agent_prompt" ? { prompt: $("#cf-prompt").value, context: [...document.querySelectorAll(".cf-ctx:checked")].map((x) => x.value), backend: "claude" } : {};
    const body = { job_id: s?.job_id || $("#sf-id").value.trim(), name: $("#sf-name").value.trim(), kind, cadence, config, enabled: $("#sf-enabled").checked, max_runs_per_day: Number($("#sf-max").value) };
    try { await (s ? send(`/api/schedules/${s.job_id}`, body, "PUT") : send("/api/schedules", body)); go("setup"); } catch (err) { $("#sf-err").textContent = err.message; }
  };
  box.scrollIntoView({ block: "start" });
}

// ---------- ticker runtime hydration ----------
async function hydrateTicker() {
  try {
    const snap = await api("/api/market/snapshot");
    const syms = ["SPY", "QQQ", "IWM"];
    for (const sym of syms) {
      const item = (snap.items || []).find((i) => i.symbol === sym);
      const el = $(`#tick-${sym.toLowerCase()}`);
      if (item && el) {
        const sign = item.change_pct >= 0 ? "+" : "";
        const col = item.change_pct >= 0 ? "var(--good)" : "var(--bad)";
        el.innerHTML = `<b style="color:#fff;">${item.symbol}</b> $${item.close.toFixed(2)} <span style="color:${col};">${sign}${item.change_pct.toFixed(2)}%</span> <span style="color:var(--faint); font-size:10.5px;">EOD · Yahoo · as of 2026-09-28</span>`;
      }
    }
  } catch (e) {
    ["spy", "qqq", "iwm"].forEach((s) => {
      const el = $(`#tick-${s}`);
      if (el) el.innerHTML = `<b style="color:#fff;">${s.toUpperCase()}</b> <span style="color:var(--faint); font-size:10.5px;">Unavailable</span>`;
    });
  }
}

let tickerSSE = null;
const lastTickAt = { "BTC-USD": null, "ETH-USD": null };

function updateTickerAge() {
  const now = Date.now();
  for (const [prod, elId] of [["BTC-USD", "#tick-btc"], ["ETH-USD", "#tick-eth"]]) {
    const t = lastTickAt[prod];
    const el = $(elId);
    if (!el || !t) continue;
    const sec = Math.max(0, Math.floor((now - t.at) / 1000));
    const sym = prod.replace("-USD", "");
    el.innerHTML = `<b style="color:#fff;">${sym}</b> $${t.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} <span style="color:var(--good); font-size:10.5px;">LIVE · Coinbase · updated ${sec === 0 ? "just now" : sec + "s ago"}</span>`;
  }
}
setInterval(updateTickerAge, 1000);

function connectTickerLive() {
  try {
    if (tickerSSE) tickerSSE.close();
    tickerSSE = new EventSource("/api/live/crypto");
    tickerSSE.addEventListener("ticker", (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.product_id && d.price) {
          lastTickAt[d.product_id] = { price: d.price, at: Date.now() };
          updateTickerAge();
        }
      } catch (err) {}
    });
    tickerSSE.onerror = () => {
      ["btc", "eth"].forEach((s) => {
        const el = $(`#tick-${s}`);
        if (el && !lastTickAt[`${s.toUpperCase()}-USD`]) {
          el.innerHTML = `<b style="color:#fff;">${s.toUpperCase()}</b> <span style="color:var(--warn); font-size:10.5px;">Waiting for Coinbase — no quote</span>`;
        } else if (el) {
          el.innerHTML = `<b style="color:#fff;">${s.toUpperCase()}</b> <span style="color:var(--bad); font-size:10.5px;">Disconnected / Stale</span>`;
        }
      });
    };
  } catch (e) {}
}

// ---------- boot ----------
function boot() {
  buildTabs();
  let first = "chart";
  try { const s = localStorage.getItem("qb-page"); if (PAGES.some((p) => p.id === s)) first = s; } catch (e) { /* storage blocked */ }
  const hash = location.hash.slice(1);
  if (PAGES.some((p) => p.id === hash)) first = hash;
  go(first);
  connectStream();
  hydrateTicker();
  connectTickerLive();
  footer();
}
document.addEventListener("DOMContentLoaded", boot);
