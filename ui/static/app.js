/* Quant Brain front end. Vanilla JS. Every server value goes through esc() before it
   touches innerHTML. Pages: Today, Activity, Markets, Strategies, Learn, Setup. */
"use strict";

const PAGES = [
  { id: "chart", label: "Chart" },
  { id: "today", label: "Today" },
  { id: "activity", label: "Activity" },
  { id: "strategies", label: "Lab" },
  { id: "study", label: "Study" },
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
  liveTimer: null,
  learn: { selected: new Set(), messages: [], backend: "claude", busy: false, sources: null, side: "notes" },
};
const charts = [];
const UIState = window.QBState;

function reduceCryptoEvent(tracker, generation, event, now = Date.now()) {
  return UIState.applyNormalizedCryptoEvent(tracker, generation, event, now);
}

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
  if (state.liveTimer && page !== "live") {
    clearInterval(state.liveTimer);
    state.liveTimer = null;
  }
  if (page !== "today") stopBaseReplayTimer();
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
  renderRoamingCompanion();
}
window.addEventListener("hashchange", () => { const h = location.hash.slice(1); if (h !== state.page) go(h); });

const modalStack = [];
const modalOpeners = new WeakMap();
const MODAL_FOCUSABLE = "button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])";

function topModal() {
  return UIState.topVisibleModal(modalStack);
}

function openModal(modal, opener, initialSelector) {
  if (!modal || !modal.hidden) return false;
  modalOpeners.set(modal, opener?.isConnected ? opener : null);
  modal.hidden = false;
  const priorIndex = modalStack.indexOf(modal);
  if (priorIndex >= 0) modalStack.splice(priorIndex, 1);
  modalStack.push(modal);
  const initial = initialSelector ? modal.querySelector(initialSelector) : null;
  (initial || modal.querySelector(MODAL_FOCUSABLE) || modal).focus?.();
  return true;
}

function closeModal(modal) {
  if (!modal || modal.hidden) return false;
  modal.hidden = true;
  const index = modalStack.lastIndexOf(modal);
  if (index >= 0) modalStack.splice(index, 1);
  const opener = modalOpeners.get(modal);
  modalOpeners.delete(modal);
  if (opener?.isConnected) opener.focus();
  return true;
}

function trapModalFocus(event, modal) {
  const focusable = [...modal.querySelectorAll(MODAL_FOCUSABLE)].filter((el) => !el.hidden);
  if (!focusable.length) {
    event.preventDefault();
    modal.focus?.();
    return;
  }
  const current = focusable.indexOf(document.activeElement);
  const next = UIState.nextTrapIndex(current, focusable.length, event.shiftKey);
  event.preventDefault();
  focusable[next].focus();
}

function toggleShortcuts(show) {
  const modal = $("#shortcuts-modal");
  if (!modal) return;
  const shouldOpen = show !== undefined ? show : modal.hidden;
  if (shouldOpen) openModal(modal, document.activeElement, "#shortcuts-close");
  else closeModal(modal);
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
  const modal = topModal();
  if (e.key === "Tab" && modal) {
    trapModalFocus(e, modal);
    return;
  }
  if (e.key === "Escape" && modal) {
    e.preventDefault();
    closeModal(modal);
    return;
  }
  if (modal || UIState.isEditableTarget(e.target)) return;
  if (e.key === "/") { e.preventDefault(); $("#cmd").focus(); }
  else if (e.key === "?" || (e.shiftKey && e.key === "/")) { e.preventDefault(); toggleShortcuts(); }
  else if (HOTKEY_PAGES[e.key]) { e.preventDefault(); go(HOTKEY_PAGES[e.key]); }
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
async function openFile(path, line, opener = document.activeElement) {
  viewerPath = path;
  $("#viewer-title").textContent = path;
  $("#viewer-body").textContent = "Loading…";
  openModal($("#viewer"), opener, "#viewer-close");
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
function closeViewer() { return closeModal($("#viewer")); }
$("#viewer-close").onclick = closeViewer;
$("#viewer").addEventListener("click", (e) => { if (e.target.id === "viewer") closeViewer(); });
$("#viewer-learn").onclick = () => { closeViewer(); state.learn.selected.add(viewerPath); go("learn", { question: `Explain ${viewerPath}: what it is for and how it fits the project.` }); };
document.addEventListener("click", (e) => {
  const f = e.target.closest("[data-file]");
  if (f) { e.preventDefault(); openFile(f.dataset.file, f.dataset.line, f); }
});
const fileLink = (path, label) => `<a href="#" data-file="${esc(path)}">${esc(label || path)}</a>`;

const RENDER = {};

// ---------- Today Cockpit (Interactive Home Base & Visual Agent UI) ----------
let baseReplayTimer = null;

function stopBaseReplayTimer() {
  if (baseReplayTimer) {
    clearInterval(baseReplayTimer);
    baseReplayTimer = null;
  }
}

RENDER.today = async (main) => {
  stopBaseReplayTimer();

  const [t, h, labData, snapData, calData, descRuns, replaysList, datasetsList] = await Promise.all([
    api("/api/today"),
    api("/api/home").catch(() => ({ counts: {}, pipeline: [], runs: [] })),
    api("/api/lab").catch(() => ({ cards: [], backtests: [], reviews: [] })),
    api("/api/market/snapshot").catch(() => ({ rows: [], missing: [], presets: [] })),
    api("/api/market/calendar").catch(() => ({ events: [] })),
    api("/api/runs/described?limit=8").catch(() => []),
    api("/api/replays").catch(() => []),
    api("/api/datasets").catch(() => []),
  ]);

  const BotEngine = window.QBBots;
  const botStyle = (() => {
    try { return localStorage.getItem("qb-bot-style") || "droid"; } catch (_) { return "droid"; }
  })();
  let currentBotStyle = botStyle;

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

  // Dynamic Backtest & Strategy Summary from /api/lab
  const activeCard = (labData.cards || []).find((c) => c.strategy_id === "SC-0002") || (labData.cards || [])[0] || null;
  const activeReview = (labData.reviews || []).find((r) => r.strategy_id === (activeCard?.strategy_id || "SC-0002")) || (labData.reviews || [])[0] || null;
  const ruleRuns = (labData.backtests || []).filter((b) => b.config && b.config.kind === "rule");
  const bhRuns = (labData.backtests || []).filter((b) => b.config && b.config.kind === "buy_and_hold");

  const pickBt = (phase, rule = "A", sym = "SPY", cost = 5) =>
    ruleRuns.find((b) => b.config.phase === phase && String(b.config.rule) === rule && b.config.symbol === sym && Number(b.config.cost_bps) === cost)
    || ruleRuns.find((b) => b.config.phase === phase)
    || null;
  const pickBh = (phase, sym = "SPY") =>
    bhRuns.find((b) => b.config.phase === phase && b.config.symbol === sym) || null;

  const isBt = pickBt("in_sample", "A", "SPY", 5);
  const hoBt = pickBt("held_out", "A", "SPY", 5);
  const isBh = pickBh("in_sample", "SPY");
  const hoBh = pickBh("held_out", "SPY");

  // Market movers & upcoming macro events for What's New Hub
  const marketRows = Array.isArray(snapData?.rows) ? snapData.rows : [];
  const oversoldRows = UIState.filterMarketRows(marketRows, "oversold_uptrend");
  const topMovers = marketRows
    .filter((r) => UIState.strictFiniteNumber(r.change_1d_pct) !== null)
    .slice()
    .sort((a, b) => Math.abs(Number(b.change_1d_pct)) - Math.abs(Number(a.change_1d_pct)))
    .slice(0, 4);
  const upcomingMacro = (calData?.events || []).slice(0, 4);

  const totalTrials = (labData.backtests || []).length || h.counts?.backtests || 0;
  const totalDatasets = h.counts?.price_datasets || marketRows.length || 0;
  const totalSources = h.counts?.sources || 0;

  main.innerHTML = `
    <!-- Title Row -->
    <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:16px; flex-wrap:wrap; gap:12px;">
      <div>
        <h1>Quant Brain Overview</h1>
        <p class="lead">${esc(t.headline?.title || "SC-0002 finished all 5 steps")}: ${esc(t.headline?.detail || "Held-out DSR 0.896 vs 0.950 required gate. Next: " + (t.next || "backend decision"))}</p>
      </div>
      <div class="row" style="gap:8px;">
        <button id="today-bot-pill" type="button" class="btn small" title="Cycle Quant Agent insights" aria-label="Show the next Quant Agent insight">
          <span class="small"><strong>Agent Insight:</strong> <span id="today-bot-msg">SC-0002 Gate Verified · 101 In-Sample Trades Loaded</span></span>
        </button>
        <div class="seg" role="group" aria-label="Layout view mode">
          <button id="cockpit-btn-split" type="button" aria-pressed="true">Split View</button>
          <button id="cockpit-btn-feed" type="button" aria-pressed="false">Feed Focus</button>
          <button id="cockpit-btn-chart" type="button" aria-pressed="false">Chart Focus</button>
          <button id="cockpit-btn-strategy" type="button" aria-pressed="false">Base Focus</button>
        </div>
      </div>
    </div>

    <!-- Overall Summary KPI Strip (1px divided strip) -->
    <section class="kpi-strip" aria-label="Project Summary Metrics">
      <div class="kpi-cell">
        <span class="kpi-label">Epistemic Stage</span>
        <span class="kpi-val">5 / 5</span>
        <span class="kpi-sub">Research to Review complete</span>
      </div>
      <div class="kpi-cell">
        <span class="kpi-label">Active Strategy Verdict</span>
        <span class="kpi-val bad">${esc((activeReview?.verdict || "Reject").toUpperCase())}</span>
        <span class="kpi-sub">SC-0002 · DSR 0.896 vs 0.950</span>
      </div>
      <div class="kpi-cell">
        <span class="kpi-label">Backtest Trial Ledger</span>
        <span class="kpi-val">${esc(totalTrials)}</span>
        <span class="kpi-sub">101 in-sample · 91 held-out trades</span>
      </div>
      <div class="kpi-cell">
        <span class="kpi-label">Verified Market Data</span>
        <span class="kpi-val">${esc(totalDatasets)}</span>
        <span class="kpi-sub">${esc(totalSources)} curated sources · ${esc(t.git?.branch || "main")}</span>
      </div>
      <div class="kpi-cell">
        <span class="kpi-label">Live Coinbase BTC-USD</span>
        <span class="kpi-val" id="today-btc-val">Price unavailable</span>
        <span class="kpi-sub"><span class="live" id="today-coinbase-status" style="padding:1px 6px; font-size:11px;"><i></i><span>WAITING</span></span></span>
      </div>
    </section>

    <!-- Simplified Obsidian & Plan Summary Hub (6 Plain-English Doors that open inline on this page) -->
    <section id="hub-cards-section" aria-label="Simplified Project Summary Hub">
      <div class="row" style="justify-content:space-between; margin-bottom:10px;">
        <div>
          <h2 style="margin:0;">Executive Summary &amp; Obsidian Brain Map</h2>
          <p class="muted small" style="margin:2px 0 0;">Everything summed up in plain words. Click any button below to open that note or tool right here on the Main Page.</p>
        </div>
        <span class="badge small">Click any card to inspect inline</span>
      </div>

      <div class="hub-cards-grid">
        <article class="hub-card" data-hub-card="plan">
          <div class="hub-card-head">
            <h3 class="hub-card-title">1. Master Plan &amp; Handoff</h3>
            <span class="status done">5 / 5 Stages</span>
          </div>
          <p class="hub-card-summary">We built a 5-stage quant research harness. Phases 0-5, Gate C, Gate F (48 datasets), Strategy Card SC-0002, the 72-trial backtest, and the Adversarial Review are complete. Next: ${esc(clip(t.next || "PROP-010 Learning Terminal", 95))}</p>
          <div class="hub-card-links">
            <button type="button" class="btn small" data-inline-note="PLAN.md">Read PLAN.md</button>
            <button type="button" class="btn small" data-inline-note="SESSION_HANDOFF.md">Read Handoff</button>
            <button type="button" class="btn small" data-inline-note="brain/_system/plan/learning_terminal_plan.md">Learning Plan</button>
          </div>
        </article>

        <article class="hub-card" data-hub-card="strategies">
          <div class="hub-card-head">
            <h3 class="hub-card-title">2. Strategy &amp; Backtest Lab</h3>
            <span class="status failed">SC-0002 Rejected</span>
          </div>
          <p class="hub-card-summary">Connors RSI(2) &lt; 10 above 200-day SMA on SPY/QQQ/IWM. Earned +40.2% in-sample (101 trades) and +36.4% held-out (91 trades), which missed our 0.950 Deflated Sharpe gate (0.896) and Buy &amp; Hold (0.46 vs 0.89).</p>
          <div class="hub-card-links">
            <button type="button" class="btn small primary" data-inline-page="strategies">Open Lab Inline</button>
            <button type="button" class="btn small" data-inline-note="brain/05_Reviews/SC-0002-adversarial-review.md">Review Note</button>
            <button type="button" class="btn small" data-inline-note="brain/04_Backtest_Reports/SC-0002-held-out.md">Held-Out Report</button>
            <button type="button" class="btn small" data-inline-note="brain/03_Strategy_Cards/SC-0002-rsi2-connors-spy.md">SC-0002 Card</button>
          </div>
        </article>

        <article class="hub-card" data-hub-card="vault">
          <div class="hub-card-head">
            <h3 class="hub-card-title">3. Obsidian Vault &amp; Research</h3>
            <span class="status accepted">${esc(totalSources)} Sources</span>
          </div>
          <p class="hub-card-summary">${esc(totalSources)} curated sources in 01_Sources (StockCharts RSI, TA-Lib, QuantConnect Look-Ahead &amp; Survivorship Bias) embedded in RAG. Scout RUN-871299ea31 validated all 5 sources across 15 windows.</p>
          <div class="hub-card-links">
            <button type="button" class="btn small primary" data-inline-note="brain/01_Sources/docs/SRC-1ea110cb46-stockcharts-chartschool-relative-strength-index-rsi.md">Browse Vault Notes</button>
            <button type="button" class="btn small" data-inline-note="brain/01_Sources/docs/SRC-2830f8cd41-quantconnect-glossary-look-ahead-bias.md">Look-Ahead Note</button>
            <button type="button" class="btn small" data-inline-note="brain/00_Inbox/Failed_Runs/RUN-871299ea31.md">RUN-871299ea31</button>
          </div>
        </article>

        <article class="hub-card" data-hub-card="market">
          <div class="hub-card-head">
            <h3 class="hub-card-title">4. Market Screener &amp; Macro</h3>
            <span class="status accepted">${esc(totalDatasets)} Datasets</span>
          </div>
          <p class="hub-card-summary">${esc(totalDatasets)} Gate F daily EOD datasets (2000-2026) with 5 quant screener presets (Oversold Uptrend, Near 52W High, Calm Volatility), official Federal Reserve FOMC dates, and live Coinbase BTC/ETH.</p>
          <div class="hub-card-links">
            <button type="button" class="btn small primary" data-inline-page="market">Open Screener &amp; FOMC Inline</button>
            <button type="button" class="btn small" data-inline-page="live">Live Crypto Inline</button>
            <button type="button" class="btn small" data-go="chart">Full Superchart</button>
          </div>
        </article>

        <article class="hub-card" data-hub-card="risk">
          <div class="hub-card-head">
            <h3 class="hub-card-title">5. Risk Simulators &amp; Decisions</h3>
            <span class="status completed">Paper Guard</span>
          </div>
          <p class="hub-card-summary">Calculate share size from stop-loss distance, compare Full vs Half-Kelly sizing, and run 2,000 Monte Carlo paths to see probability of ruin, plus read all PROP-001..010 and DEC-* decisions.</p>
          <div class="hub-card-links">
            <button type="button" class="btn small primary" data-inline-page="risk">Open Risk Center Inline</button>
            <button type="button" class="btn small" data-inline-note="brain/_system/plan/plan_change_proposals.md">Proposals (PROP-001..010)</button>
          </div>
        </article>

        <article class="hub-card" data-hub-card="learn">
          <div class="hub-card-head">
            <h3 class="hub-card-title">6. Agents, Automations &amp; Tutor</h3>
            <span class="status completed">5 Agents</span>
          </div>
          <p class="hub-card-summary">5 specialist bots enforced by the harness, scheduled health/data jobs, and a NotebookLM-style AI Tutor that reads ticked vault files and cites exact [file:line] numbers.</p>
          <div class="hub-card-links">
            <button type="button" class="btn small primary" data-inline-page="learn">Open AI Tutor Inline</button>
            <button type="button" class="btn small" data-inline-page="activity">Activity Inline</button>
            <button type="button" class="btn small" data-inline-page="setup">Setup Inline</button>
          </div>
        </article>
      </div>
    </section>

    <!-- Inline Main-Page Stage Switcher: Open any page or Obsidian note right here on the Main Page -->
    <section class="box" id="main-inline-stage" style="margin-bottom:20px;">
      <div class="inline-stage-bar">
        <div class="seg" id="inline-stage-tabs" role="group" aria-label="Main page workspace view">
          <button type="button" data-stage-tab="overview" aria-pressed="true">Feed, Base &amp; Replay Chart</button>
          <button type="button" data-stage-tab="vault" aria-pressed="false">Obsidian Vault Reader</button>
          <button type="button" data-stage-tab="strategies" aria-pressed="false">Strategy Lab</button>
          <button type="button" data-stage-tab="market" aria-pressed="false">Screener &amp; FOMC</button>
          <button type="button" data-stage-tab="risk" aria-pressed="false">Risk Center</button>
          <button type="button" data-stage-tab="live" aria-pressed="false">Live Crypto</button>
          <button type="button" data-stage-tab="activity" aria-pressed="false">Activity &amp; Runs</button>
          <button type="button" data-stage-tab="learn" aria-pressed="false">AI Tutor</button>
          <button type="button" data-stage-tab="setup" aria-pressed="false">Setup</button>
        </div>
        <span class="faint small" id="inline-stage-status">Viewing Main Feed, Agent Base &amp; Chart</span>
      </div>

      <!-- Mounted Inline Tool or Obsidian Vault Reader -->
      <div id="inline-stage-mount" hidden></div>

      <!-- Default Overview Workspace: Left = Unified Everything Feed | Right = Interactive Agent Base + Backtest Replay Chart -->
      <div class="overview-grid" id="cockpit-grid" style="margin-bottom:0;">
      <!-- Left Column: Unified Master Feed (One Stream for Everything) -->
      <section class="box" id="master-feed-section">
        <div class="master-feed-controls">
          <div>
            <h2 style="margin:0;">Unified Everything Feed</h2>
            <p class="muted small" style="margin:2px 0 0;">Every backtest, review, strategy card, research source, failed-run receipt, market dataset, FOMC event, decision, and commit in one place.</p>
          </div>
          <div class="row" style="gap:8px;">
            <input type="text" id="master-feed-search" placeholder="Search (SC-0002, SPY, FOMC, Qwen…)" aria-label="Search unified feed" style="width:210px;">
            <div class="seg" role="group" aria-label="Feed sort order">
              <button type="button" id="feed-sort-featured" aria-pressed="true">Featured</button>
              <button type="button" id="feed-sort-newest" aria-pressed="false">Newest</button>
            </div>
          </div>
        </div>

        <div class="row" style="margin-bottom:10px; justify-content:space-between;">
          <div class="seg" id="master-feed-tabs" role="group" aria-label="Filter feed by category"></div>
          <span class="faint small" id="master-feed-count"></span>
        </div>

        <ul class="master-feed-list" id="master-feed-list"></ul>

        <div class="box-foot" id="master-feed-foot" hidden>
          <div class="row" style="justify-content:space-between;">
            <span class="small muted" id="master-feed-foot-label">All project categories merged</span>
            <button type="button" class="btn small" id="master-feed-more-btn">Show all items</button>
          </div>
        </div>
      </section>

      <!-- Right Column: Interactive Visual Agent Base + Embedded Backtest Replay Chart -->
      <div class="stack" id="cockpit-col-right" style="gap:20px;">
        <!-- Interactive Visual Agent Base Map -->
        <section class="box" id="cockpit-col-strategy" style="padding:16px;">
          <div id="base-map-section" style="display:flex; flex-direction:column; height:100%;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">
              <div>
                <h2 style="margin:0;">Interactive Agent Base</h2>
                <p class="muted small" style="margin:2px 0 0;">Click any bot, workstation, or feed row to inspect state, or replay the latest run.</p>
              </div>
              <div class="row" style="gap:6px;">
                <div class="seg" role="group" aria-label="Bot visual style">
                  <button type="button" class="bot-style-btn" data-bot-style="droid" aria-pressed="${currentBotStyle === "droid"}">Droids</button>
                  <button type="button" class="bot-style-btn" data-bot-style="pixel" aria-pressed="${currentBotStyle === "pixel"}">Pixel</button>
                  <button type="button" class="bot-style-btn" data-bot-style="geometric" aria-pressed="${currentBotStyle === "geometric"}">Geo</button>
                </div>
                <button class="btn small primary" id="base-replay-run-btn" type="button">Replay Run</button>
                <button class="btn small" id="base-reset-bots-btn" type="button">Reset</button>
              </div>
            </div>

            <div class="base-stage-wrap">
              <div class="base-floor-canvas" id="base-floor-canvas">
                <svg class="base-paths-svg" viewBox="0 0 100 100" preserveAspectRatio="none" id="base-paths-svg"></svg>
                <div id="base-stations-layer"></div>
                <div id="base-bots-layer"></div>
              </div>
              <div class="base-inspector" id="base-inspector">
                <div class="grow">
                  <div class="row" style="gap:8px;">
                    <span class="badge small" id="insp-badge">BASE</span>
                    <b id="insp-title" style="font-size:13px;">Click any Bot or Workstation</b>
                  </div>
                  <p id="insp-desc" class="muted small" style="margin:3px 0 0;">Each bot represents a verified harness module. Watch them move when tasks run.</p>
                </div>
                <div class="row" id="insp-actions" style="gap:6px;">
                  <button class="btn small" id="insp-ask-tutor" type="button">Ask Tutor</button>
                  <button class="btn small" id="insp-open-page" type="button" data-go="activity">Activity</button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Backtest Replay Chart & Strategy Metrics -->
        <section class="box" id="cockpit-col-chart">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">
            <div class="row" style="gap:8px;">
              <h2 style="margin:0;">SPY · Connors RSI(2) Backtest Replay</h2>
              <span id="today-replay-badge" class="badge small">In-Sample (101 trades)</span>
            </div>
            <div class="row" style="gap:6px;">
              ${replaysList.length > 1 ? `<select id="today-replay-select" aria-label="Select backtest replay" style="padding:4px 8px; font-size:12px;">
                ${replaysList.map((r) => `<option value="${esc(r.id)}">${esc(r.card_id)} Rule ${esc(r.rule_id)} · ${esc(r.symbol)} (${esc(r.phase === "held_out" ? "Held-Out" : "In-Sample")})</option>`).join("")}
              </select>` : ""}
              <button class="btn small" id="today-toggle-replay" type="button">Switch to Held-Out (91)</button>
              <button class="btn small" data-go="chart" type="button">Full Chart</button>
            </div>
          </div>

          <div id="today-chart-wrap" style="height:220px; width:100%; border-radius:var(--radius-sm); overflow:hidden; background:var(--bg); border:1px solid var(--line); position:relative;">
            <div id="today-chart-canvas" style="width:100%; height:100%;"></div>
            <div id="today-chart-loading" style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center; background:var(--surface); font-size:12px; color:var(--muted);">Loading SPY backtest bars…</div>
          </div>

          <div style="margin-top:10px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; font-size:12px;">
            <div class="row" style="gap:6px;">
              <button class="btn small" id="today-prev-trade" type="button">Prev Trade</button>
              <button class="btn small" id="today-next-trade" type="button">Next Trade</button>
              <span id="today-trade-info" class="muted">Viewing Trade 1 of 101</span>
            </div>
            <div class="row small muted" style="gap:12px;">
              <span>Return: <b class="good" id="today-stat-return">${isBt ? esc(pct(isBt.total_return, 1)) : "+40.2%"}</b></span>
              <span>Win Rate: <b id="today-stat-win">${isBt && isBt.win_rate != null ? esc(pct(isBt.win_rate, 1).replace("+", "")) : "71.3%"}</b></span>
              <span>Sharpe: <b id="today-stat-sharpe">${isBt ? esc(fmt(isBt.sharpe, 2)) : "0.41"}</b> (vs ${isBh ? esc(fmt(isBh.sharpe, 2)) : "0.29"} B&amp;H)</span>
              <span>Max DD: <b id="today-stat-dd">${isBt ? esc(pct(isBt.max_drawdown, 1)) : "-15.1%"}</b></span>
            </div>
          </div>

          <div class="box-foot" style="margin-top:10px;">
            <div class="row" style="justify-content:space-between;">
              <span class="small muted"><b>Why rejected:</b> ${esc(activeReview?.verdict_text || "Held-out DSR 0.896 < 0.950 required gate; random-entry 94.9% < 95%.")}</span>
              <div class="row" style="gap:10px;">
                <button class="link small" data-inline-page="strategies">All ${esc(totalTrials)} Trials</button>
                <button class="link small" data-inline-page="risk">Risk Simulators</button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
    </section>

    <!-- 5-Step Epistemic Pipeline -->
    <section>
      <div class="row" style="justify-content:space-between; margin-bottom:10px;">
        <h2 style="margin:0;">5-Stage Epistemic Research Pipeline</h2>
        <span class="faint small">Branch ${esc(t.git?.branch || "main")} (${esc(t.git?.head || "")}) · ${plural(t.git?.uncommitted || 0, "unsaved file")}</span>
      </div>
      <ol class="steps">${steps}</ol>
    </section>
  `;

  main.querySelectorAll("[data-open-run]").forEach((b) => (b.onclick = () => { state.openRun = b.dataset.openRun; go("activity"); }));
  main.querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => go(b.dataset.go)));
  main.querySelectorAll("[data-jump-sym]").forEach((tr) => (tr.onclick = () => {
    if (window.CH) { CH.symbol = tr.dataset.jumpSym; CH.formula = ""; saveCH(); }
    go("chart");
  }));

  // Render Interactive Visual Agent Base Map
  let focusFeedItemOnBase = null;
  if (BotEngine) {
    const stationsLayer = $("#base-stations-layer");
    const botsLayer = $("#base-bots-layer");
    const pathsSvg = $("#base-paths-svg");
    const botStates = BotEngine.deriveInitialBotStates({
      counts: h.counts || {},
      runs: descRuns,
      lab: labData,
    });
    let selectedEntity = null;

    // Draw SVG connecting paths between stations
    if (pathsSvg) {
      pathsSvg.innerHTML = BotEngine.PATH_EDGES.map(([aId, bId]) => {
        const a = BotEngine.stationById(aId);
        const b = BotEngine.stationById(bId);
        return `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="#2e2e32" stroke-width="0.6" stroke-dasharray="1.5 1.5"/>`;
      }).join("");
    }

    // Draw Stations
    if (stationsLayer) {
      stationsLayer.innerHTML = BotEngine.STATIONS.map((st) => `
        <div class="base-station" data-station-id="${esc(st.id)}" style="left:${st.x}%; top:${st.y}%;" role="button" tabindex="0" aria-label="${esc(st.label)} workstation">
          <div class="st-title"><span class="st-dot" style="background:${esc(st.color)};"></span>${esc(st.label)}</div>
          <div class="st-sub">${esc(st.sub)}</div>
        </div>
      `).join("");
    }

    const updateInspector = (badgeText, titleText, descText, targetPage, tutorPrompt) => {
      const badgeEl = $("#insp-badge");
      const titleEl = $("#insp-title");
      const descEl = $("#insp-desc");
      const openBtn = $("#insp-open-page");
      const askBtn = $("#insp-ask-tutor");
      if (badgeEl) badgeEl.textContent = badgeText;
      if (titleEl) titleEl.textContent = titleText;
      if (descEl) descEl.textContent = descText;
      if (openBtn && targetPage) {
        openBtn.dataset.go = targetPage;
        openBtn.textContent = `Open ${PAGES.find((p) => p.id === targetPage)?.label || targetPage} →`;
        openBtn.onclick = () => go(targetPage);
      }
      if (askBtn) {
        askBtn.onclick = () => go("learn", { question: tutorPrompt || `Explain ${titleText} and how it works in Quant Brain.` });
      }
    };

    // Slight positional offsets when multiple bots share a station
    const computeBotCoords = () => {
      const byStation = {};
      Object.values(botStates).forEach((b) => {
        byStation[b.stationId] = byStation[b.stationId] || [];
        byStation[b.stationId].push(b);
      });
      Object.values(byStation).forEach((group) => {
        group.forEach((b, idx) => {
          const st = BotEngine.stationById(b.stationId);
          const spread = (idx - (group.length - 1) / 2) * 7;
          b.x = Math.max(6, Math.min(94, st.x + spread));
          b.y = Math.max(14, Math.min(88, st.y + 13));
        });
      });
    };

    const paintBots = () => {
      if (!botsLayer) return;
      computeBotCoords();
      botsLayer.innerHTML = Object.values(botStates).map((b) => {
        const isSel = selectedEntity === b.id;
        return `<button type="button" class="base-bot-sprite ${b.walking ? "walking" : ""} ${isSel ? "selected" : ""}" data-bot-id="${esc(b.id)}" style="left:${b.x}%; top:${b.y}%;" aria-label="${esc(b.name)} (${esc(b.mood)})">
          ${(isSel || b.walking) ? `<div class="bot-speech-pop">${esc(b.speech)}</div>` : ""}
          <div class="bot-avatar-ring" style="border-color:${esc(b.color)};">
            ${BotEngine.botAvatarSvg(currentBotStyle, b.color, b.mood)}
          </div>
          <span class="bot-name-tag">${esc(b.name)}</span>
        </button>`;
      }).join("");

      botsLayer.querySelectorAll("[data-bot-id]").forEach((btn) => {
        btn.onclick = () => {
          const b = botStates[btn.dataset.botId];
          if (!b) return;
          selectedEntity = b.id;
          const st = BotEngine.stationById(b.stationId);
          updateInspector(
            `${b.badge} · ${b.mood.toUpperCase()}`,
            `${b.name} @ ${st.label}`,
            `${b.speech} — ${b.detail}`,
            st.page,
            `Explain the role of ${b.name} (${b.role}) in this project and what rules it follows.`
          );
          paintBots();
        };
      });
    };

    paintBots();

    stationsLayer?.querySelectorAll("[data-station-id]").forEach((el) => {
      const activateStation = () => {
        const st = BotEngine.stationById(el.dataset.stationId);
        stationsLayer.querySelectorAll(".base-station").forEach((s) => s.classList.toggle("active", s === el));
        updateInspector(
          "WORKSTATION",
          `${st.label} (${st.sub})`,
          st.description,
          st.page,
          `Explain the ${st.label} stage (${st.sub}) in Quant Brain and how it prevents common quant mistakes.`
        );
      };
      el.onclick = activateStation;
      el.onkeydown = (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); activateStation(); } };
    });

    // Style switcher buttons (Sci-Fi Droids / Pixel Arcade / Geometric)
    main.querySelectorAll(".bot-style-btn").forEach((btn) => {
      btn.onclick = () => {
        currentBotStyle = btn.dataset.botStyle || "droid";
        try { localStorage.setItem("qb-bot-style", currentBotStyle); } catch (_) {}
        main.querySelectorAll(".bot-style-btn").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
        paintBots();
        renderRoamingCompanion();
      };
    });

    // Replay Latest Run animation on the Base Map
    const replayBtn = $("#base-replay-run-btn");
    const resetBtn = $("#base-reset-bots-btn");

    if (replayBtn) {
      replayBtn.onclick = async () => {
        stopBaseReplayTimer();
        replayBtn.disabled = true;
        replayBtn.textContent = "Replaying Run…";
        let events = [];
        const latestRunId = descRuns[0]?.run_id || (h.runs && h.runs[0]?.run_id);
        if (latestRunId) {
          try {
            const detail = await api(`/api/runs/${encodeURIComponent(latestRunId)}`);
            events = detail.events || [];
          } catch (_) { events = []; }
        }
        const stepsToPlay = BotEngine.buildReplayStepsFromEvents(events, descRuns[0] || {});
        let idx = 0;

        const runStep = () => {
          if (idx >= stepsToPlay.length) {
            stopBaseReplayTimer();
            Object.values(botStates).forEach((b) => { b.walking = false; });
            if (replayBtn) {
              replayBtn.disabled = false;
              replayBtn.textContent = "▶ Replay Latest Run";
            }
            paintBots();
            return;
          }
          const step = stepsToPlay[idx++];
          Object.values(botStates).forEach((b) => { b.walking = false; });
          const bot = botStates[step.botId] || botStates.scout;
          bot.stationId = step.stationId;
          bot.mood = step.mood;
          bot.speech = step.speech;
          bot.walking = true;
          selectedEntity = bot.id;
          const st = BotEngine.stationById(step.stationId);
          updateInspector(
            `STEP ${idx}/${stepsToPlay.length} · ${step.stage.toUpperCase()}`,
            `${bot.name} moved to ${st.label}`,
            step.speech,
            st.page,
            `Explain what happened during stage ${step.stage} in run ${step.runId || "the latest run"}.`
          );
          paintBots();
        };

        runStep();
        baseReplayTimer = setInterval(runStep, 1400);
      };
    }

    if (resetBtn) {
      resetBtn.onclick = () => {
        stopBaseReplayTimer();
        if (replayBtn) {
          replayBtn.disabled = false;
          replayBtn.textContent = "▶ Replay Latest Run";
        }
        const fresh = BotEngine.deriveInitialBotStates({ counts: h.counts || {}, runs: descRuns, lab: labData });
        Object.keys(fresh).forEach((k) => { botStates[k] = fresh[k]; });
        selectedEntity = null;
        paintBots();
      };
    }

    focusFeedItemOnBase = (item) => {
      stopBaseReplayTimer();
      const bId = item.bot_id || "scout";
      const stId = item.station_id || "scout_desk";
      const bot = botStates[bId] || botStates.scout;
      if (!bot) return;
      Object.values(botStates).forEach((b) => { b.walking = false; });
      bot.stationId = stId;
      bot.mood = BotEngine.mapStatusToMood(item.status || "completed");
      bot.speech = item.title;
      bot.walking = true;
      selectedEntity = bot.id;
      const st = BotEngine.stationById(stId);
      updateInspector(
        item.badge || "FEED EVENT",
        `${bot.name} @ ${st.label}: ${item.title}`,
        item.summary || "",
        st.page,
        `Explain "${item.title}" in plain words: ${item.summary || ""}`
      );
      paintBots();
      $("#cockpit-col-strategy")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    };
  }

  // Interactive Bot Pill
  const botTips = [
    "SC-0002 Gate Verified · 101 In-Sample Trades Loaded",
    "Tip: In-sample strategy was in the market only 9% of days",
    "Deflated Sharpe Ratio (DSR) discounts for all 73 backtest trials",
    "Status: Ready for Strategy Card SC-0003 formulation"
  ];
  let botTipIdx = 0;
  const botPill = $("#today-bot-pill");
  if (botPill) {
    botPill.onclick = () => {
      botTipIdx = (botTipIdx + 1) % botTips.length;
      $("#today-bot-msg").textContent = botTips[botTipIdx];
    };
  }

  // Load and Render Embedded SPY Backtest Chart
  let loadReplayFromFeed = null;
  const chartCanvas = $("#today-chart-canvas");
  if (chartCanvas && window.LightweightCharts) {
    let currentReplayId = "SC-0002-in-sample-A-SPY-5bps";
    let activeReplayData = null;
    let currentTradeIdx = 0;

    const chart = LightweightCharts.createChart(chartCanvas, {
      layout: { background: { color: "#171719" }, textColor: "#b4b4b4", fontSize: 12 },
      grid: { vertLines: { color: "#222224" }, horzLines: { color: "#222224" } },
      rightPriceScale: { borderColor: "#222224" },
      timeScale: { borderColor: "#222224", rightOffset: 6 },
      autoSize: true,
    });
    charts.push(chart);

    const candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
      upColor: "#44a282", downColor: "#e5566f", borderVisible: false,
      wickUpColor: "#44a282", wickDownColor: "#e5566f"
    });
    const smaSeries = chart.addSeries(LightweightCharts.LineSeries, {
      color: "#d9a441", lineWidth: 1.5, title: "SMA 200"
    });

    async function loadReplay(replayId) {
      const loadingEl = $("#today-chart-loading");
      if (loadingEl) loadingEl.hidden = false;
      try {
        const replay = await api(`/api/replays/${encodeURIComponent(replayId)}`);
        activeReplayData = replay;
        currentTradeIdx = 0;

        const bars = replay.bars.map((b) => ({
          time: b.date,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close
        }));
        candleSeries.setData(bars);

        const smaBars = replay.bars
          .filter((b) => b.sma_filter !== null && b.sma_filter !== undefined)
          .map((b) => ({ time: b.date, value: b.sma_filter }));
        smaSeries.setData(smaBars);

        const markers = [];
        replay.trades.forEach((t) => {
          if (t.entry_date) {
            markers.push({
              time: t.entry_date,
              position: "belowBar",
              color: "#44a282",
              shape: "arrowUp",
              text: "#" + t.number
            });
          }
          if (t.exit_date) {
            markers.push({
              time: t.exit_date,
              position: "aboveBar",
              color: "#e5566f",
              shape: "arrowDown",
              text: "Exit"
            });
          }
        });
        markers.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
        if (window.LightweightCharts.createSeriesMarkers) {
          window.LightweightCharts.createSeriesMarkers(candleSeries, markers);
        } else if (typeof candleSeries.setMarkers === "function") {
          candleSeries.setMarkers(markers);
        }

        chart.timeScale().fitContent();
        updateTradeStepUI();
      } catch (e) {
        toast("Failed loading replay: " + e.message, "bad");
      } finally {
        if (loadingEl) loadingEl.hidden = true;
      }
    }

    function updateTradeStepUI() {
      if (!activeReplayData || !activeReplayData.trades.length) return;
      const t = activeReplayData.trades[currentTradeIdx];
      const infoEl = $("#today-trade-info");
      if (infoEl && t) {
        infoEl.innerHTML = `Viewing Trade <strong>${esc(t.number)} of ${activeReplayData.trades.length}</strong> (${esc(t.entry_date)} → ${esc(t.exit_date)}, ${esc(sgn(t.return * 100))}, ${esc(t.holding_days)}d)`;
      }
    }

    function stepTrade(dir) {
      if (!activeReplayData || !activeReplayData.trades.length) return;
      currentTradeIdx = Math.max(0, Math.min(activeReplayData.trades.length - 1, currentTradeIdx + dir));
      const t = activeReplayData.trades[currentTradeIdx];
      if (t) {
        chart.timeScale().setVisibleRange({ from: t.entry_date, to: t.exit_date });
        updateTradeStepUI();
      }
    }

    const prevBtn = $("#today-prev-trade");
    const nextBtn = $("#today-next-trade");
    if (prevBtn) prevBtn.onclick = () => stepTrade(-1);
    if (nextBtn) nextBtn.onclick = () => stepTrade(1);

    const togglePhaseBtn = $("#today-toggle-replay");
    const replaySelect = $("#today-replay-select");
    if (replaySelect) {
      replaySelect.onchange = (e) => {
        currentReplayId = e.target.value;
        loadReplay(currentReplayId);
      };
    }
    if (togglePhaseBtn) {
      togglePhaseBtn.onclick = () => {
        if (currentReplayId === "SC-0002-in-sample-A-SPY-5bps") {
          currentReplayId = "SC-0002-held-out-A-SPY-5bps";
          $("#today-replay-badge").textContent = "Held-Out (91 trades)";
          togglePhaseBtn.textContent = "Switch to In-Sample (101 trades)";
        } else {
          currentReplayId = "SC-0002-in-sample-A-SPY-5bps";
          $("#today-replay-badge").textContent = "In-Sample (101 trades)";
          togglePhaseBtn.textContent = "Switch to Held-Out (91 trades)";
        }
        loadReplay(currentReplayId);
      };
    }

    loadReplay(currentReplayId);
    loadReplayFromFeed = (repId) => {
      currentReplayId = repId;
      if (replaySelect) replaySelect.value = repId;
      if ($("#today-replay-badge")) {
        $("#today-replay-badge").textContent = repId.includes("held-out") ? "Held-Out (91 trades)" : "In-Sample (101 trades)";
      }
      loadReplay(repId);
      $("#cockpit-col-chart")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    };

    // Responsive View Switcher & Element ResizeObserver
    const chartWrap = $("#today-chart-wrap");
    const chartCol = $("#cockpit-col-chart");
    const stratCol = $("#cockpit-col-strategy");
    const viewportPill = $("#cockpit-viewport-pill");
    const gridEl = $("#cockpit-grid");

    const updateSizingTelemetry = () => {
      const w = window.innerWidth;
      const wrapW = chartWrap ? chartWrap.clientWidth : 0;
      if (viewportPill) {
        if (w <= 960) {
          viewportPill.innerHTML = `Half-Screen (${w}px) · <span style="color:var(--accent); font-weight:600;">Adaptive Stack</span>`;
        } else {
          viewportPill.innerHTML = `Full Screen (${w}px) · <span style="color:var(--good); font-weight:600;">Pro Split</span>`;
        }
      }
      if (chart && wrapW > 0) {
        chart.applyOptions({ width: Math.floor(wrapW) });
      }
    };

    if (window.ResizeObserver && chartWrap) {
      const ro = new ResizeObserver(() => {
        updateSizingTelemetry();
      });
      ro.observe(chartWrap);
      if (gridEl) ro.observe(gridEl);
    }
    window.addEventListener("resize", updateSizingTelemetry);
    setTimeout(updateSizingTelemetry, 60);

    // View Switching Controls
    const btnSplit = $("#cockpit-btn-split");
    const btnFeed = $("#cockpit-btn-feed");
    const btnChart = $("#cockpit-btn-chart");
    const btnStrat = $("#cockpit-btn-strategy");
    const feedSectionEl = $("#master-feed-section");
    const rightColEl = $("#cockpit-col-right");

    const setViewMode = (mode) => {
      if (!chartCol || !stratCol) return;
      const selected = ["chart", "strategy", "feed"].includes(mode) ? mode : "split";
      [["split", btnSplit], ["feed", btnFeed], ["chart", btnChart], ["strategy", btnStrat]].forEach(([name, btn]) => {
        if (btn) btn.setAttribute("aria-pressed", String(name === selected));
      });
      if (mode === "feed") {
        if (gridEl) gridEl.style.gridTemplateColumns = "1fr";
        if (feedSectionEl) feedSectionEl.style.display = "flex";
        if (rightColEl) rightColEl.style.display = "none";
      } else if (mode === "chart") {
        if (gridEl) gridEl.style.gridTemplateColumns = "1fr";
        if (feedSectionEl) feedSectionEl.style.display = "none";
        if (rightColEl) rightColEl.style.display = "grid";
        chartCol.style.display = "flex";
        stratCol.style.display = "none";
        if (chartWrap) chartWrap.style.height = "460px";
      } else if (mode === "strategy") {
        if (gridEl) gridEl.style.gridTemplateColumns = "1fr";
        if (feedSectionEl) feedSectionEl.style.display = "none";
        if (rightColEl) rightColEl.style.display = "grid";
        chartCol.style.display = "none";
        stratCol.style.display = "flex";
      } else {
        if (gridEl) gridEl.style.gridTemplateColumns = "";
        if (feedSectionEl) feedSectionEl.style.display = "flex";
        if (rightColEl) rightColEl.style.display = "grid";
        chartCol.style.display = "flex";
        stratCol.style.display = "flex";
        if (chartWrap) chartWrap.style.height = "220px";
      }
      setTimeout(updateSizingTelemetry, 40);
    };

    if (btnSplit) btnSplit.onclick = () => setViewMode("split");
    if (btnFeed) btnFeed.onclick = () => setViewMode("feed");
    if (btnChart) btnChart.onclick = () => setViewMode("chart");
    if (btnStrat) btnStrat.onclick = () => setViewMode("strategy");
  }

  // Unified Master Feed Controller
  const rawFeed = Array.isArray(t.feed) && t.feed.length
    ? t.feed
    : (t.timeline || []).map((i, idx) => ({
        id: `tl-${idx}`,
        when: i.when,
        category: i.kind === "commit" ? "code" : "research",
        badge: (i.kind || "event").toUpperCase(),
        status: i.status || "completed",
        title: i.who,
        summary: i.text,
        metrics: i.ref ? [i.ref] : [],
        run_id: i.kind === "run" ? i.ref : null,
        priority: 70,
      }));

  const FEED_CATEGORIES = [
    { id: "all", label: "All", match: () => true },
    { id: "backtest", label: "Backtests & Reviews", match: (x) => x.category === "backtest" },
    { id: "research", label: "Research & Sources", match: (x) => x.category === "research" },
    { id: "strategy", label: "Strategies & Decisions", match: (x) => x.category === "strategy" || x.category === "decision" },
    { id: "market", label: "Market & Macro", match: (x) => x.category === "market" },
    { id: "code", label: "Runs & Commits", match: (x) => x.category === "code" },
  ];

  let activeFeedCat = "all";
  let activeFeedSort = "featured";
  let feedSearchQuery = "";
  let feedExpanded = false;

  const feedTabsEl = $("#master-feed-tabs");
  const feedListEl = $("#master-feed-list");
  const feedCountEl = $("#master-feed-count");
  const feedFootEl = $("#master-feed-foot");
  const feedMoreBtn = $("#master-feed-more-btn");
  const feedSearchEl = $("#master-feed-search");
  const sortFeaturedBtn = $("#feed-sort-featured");
  const sortNewestBtn = $("#feed-sort-newest");

  const renderMasterFeed = () => {
    if (!feedListEl || !feedTabsEl) return;

    const q = feedSearchQuery.trim().toLowerCase();
    const matchesSearch = (item) => {
      if (!q) return true;
      const hay = `${item.title || ""} ${item.summary || ""} ${item.badge || ""} ${(item.metrics || []).join(" ")} ${item.file_path || ""}`.toLowerCase();
      return hay.includes(q);
    };

    const searchFiltered = rawFeed.filter(matchesSearch);

    feedTabsEl.innerHTML = FEED_CATEGORIES.map((cat) => {
      const cnt = searchFiltered.filter(cat.match).length;
      return `<button type="button" data-feed-cat="${esc(cat.id)}" aria-pressed="${activeFeedCat === cat.id}">${esc(cat.label)} (${cnt})</button>`;
    }).join("");

    feedTabsEl.querySelectorAll("[data-feed-cat]").forEach((btn) => {
      btn.onclick = () => {
        activeFeedCat = btn.dataset.feedCat;
        renderMasterFeed();
      };
    });

    const catObj = FEED_CATEGORIES.find((c) => c.id === activeFeedCat) || FEED_CATEGORIES[0];
    const filtered = searchFiltered.filter(catObj.match).slice();

    if (activeFeedSort === "newest") {
      filtered.sort((a, b) => String(b.when || "").localeCompare(String(a.when || "")));
    } else {
      filtered.sort((a, b) => (Number(b.priority || 0) - Number(a.priority || 0)) || String(b.when || "").localeCompare(String(a.when || "")));
    }

    const limit = feedExpanded ? filtered.length : 6;
    const shown = filtered.slice(0, limit);

    if (feedCountEl) {
      feedCountEl.textContent = `Showing ${shown.length} of ${filtered.length} items`;
    }
    if (feedFootEl && feedMoreBtn) {
      feedFootEl.hidden = filtered.length <= 6;
      feedMoreBtn.textContent = feedExpanded ? "Show fewer items" : `Show all ${filtered.length} items`;
    }

    if (!shown.length) {
      feedListEl.innerHTML = `<li class="empty">No items match this filter or search query.</li>`;
      return;
    }

    feedListEl.innerHTML = shown.map((item, i) => {
      const dateLabel = item.when ? (item.when.length > 10 ? ago(item.when) : item.when) : "";
      const metricsHtml = (item.metrics || []).map((m) => `<span class="badge small">${esc(m)}</span>`).join("");
      return `<li class="master-feed-row" data-feed-idx="${i}">
        <div class="master-feed-meta">
          <span class="badge small">${esc(item.badge || item.category)}</span>
          <span class="master-feed-when">${esc(dateLabel)}</span>
        </div>
        <div class="master-feed-body">
          <div class="master-feed-title">
            <span>${esc(item.title)}</span>
            ${item.status ? status(item.status) : ""}
          </div>
          <p class="master-feed-summary">${esc(item.summary || "")}</p>
          ${metricsHtml ? `<div class="master-feed-metrics">${metricsHtml}</div>` : ""}
        </div>
        <div class="master-feed-actions">
          ${item.replay_id ? `<button type="button" class="btn small" data-feed-replay="${esc(item.replay_id)}">Replay on Chart</button>` : ""}
          ${item.symbol ? `<button type="button" class="btn small" data-feed-sym="${esc(item.symbol)}">Open ${esc(item.symbol)}</button>` : ""}
          ${item.file_path ? `<button type="button" class="btn small" data-feed-note="${esc(item.file_path)}">Read Note</button>` : ""}
          ${item.run_id ? `<button type="button" class="btn small" data-open-run="${esc(item.run_id)}">Inspect Run</button>` : ""}
          <button type="button" class="btn small" data-feed-base="${i}">Show on Base</button>
          <button type="button" class="link small" data-feed-tutor="${i}">Ask Tutor</button>
        </div>
      </li>`;
    }).join("");

    feedListEl.querySelectorAll("[data-feed-replay]").forEach((btn) => {
      btn.onclick = () => {
        if (loadReplayFromFeed) loadReplayFromFeed(btn.dataset.feedReplay);
      };
    });
    feedListEl.querySelectorAll("[data-feed-note]").forEach((btn) => {
      btn.onclick = () => {
        openInlineVaultNote(btn.dataset.feedNote);
      };
    });
    feedListEl.querySelectorAll("[data-feed-sym]").forEach((btn) => {
      btn.onclick = () => {
        if (window.CH) { CH.symbol = btn.dataset.feedSym; CH.formula = ""; saveCH(); }
        go("chart");
      };
    });
    feedListEl.querySelectorAll("[data-open-run]").forEach((btn) => {
      btn.onclick = () => {
        state.openRun = btn.dataset.openRun;
        openInlineStage("activity");
      };
    });
    feedListEl.querySelectorAll("[data-feed-base]").forEach((btn) => {
      btn.onclick = () => {
        const item = shown[Number(btn.dataset.feedBase)];
        if (item && focusFeedItemOnBase) focusFeedItemOnBase(item);
      };
    });
    feedListEl.querySelectorAll("[data-feed-tutor]").forEach((btn) => {
      btn.onclick = () => {
        const item = shown[Number(btn.dataset.feedTutor)];
        if (!item) return;
        if (item.file_path) state.learn.selected.add(item.file_path);
        if (item.run_id) state.learn.selected.add(`run:${item.run_id}`);
        openInlineStage("learn", { question: `Explain "${item.title}" in plain words: what happened, what evidence or numbers it produced, and how it fits into the project.` });
      };
    });
  };

  if (feedSearchEl) {
    feedSearchEl.oninput = (e) => {
      feedSearchQuery = e.target.value;
      renderMasterFeed();
    };
  }
  if (sortFeaturedBtn && sortNewestBtn) {
    sortFeaturedBtn.onclick = () => {
      activeFeedSort = "featured";
      sortFeaturedBtn.setAttribute("aria-pressed", "true");
      sortNewestBtn.setAttribute("aria-pressed", "false");
      renderMasterFeed();
    };
    sortNewestBtn.onclick = () => {
      activeFeedSort = "newest";
      sortNewestBtn.setAttribute("aria-pressed", "true");
      sortFeaturedBtn.setAttribute("aria-pressed", "false");
      renderMasterFeed();
    };
  }
  if (feedMoreBtn) {
    feedMoreBtn.onclick = () => {
      feedExpanded = !feedExpanded;
      renderMasterFeed();
    };
  }

  renderMasterFeed();

  // Inline Main-Page Stage & Obsidian Vault Note Reader
  const stageTabsEl = $("#inline-stage-tabs");
  const stageStatusEl = $("#inline-stage-status");
  const stageMountEl = $("#inline-stage-mount");
  const overviewGridEl = $("#cockpit-grid");
  let currentVaultNote = "PLAN.md";
  let vaultRawMode = false;

  async function renderInlineVaultReader(notePath) {
    if (!stageMountEl) return;
    currentVaultNote = notePath || currentVaultNote || "PLAN.md";
    stageMountEl.hidden = false;
    if (overviewGridEl) overviewGridEl.hidden = true;
    stageMountEl.innerHTML = `<p class="muted">Loading Obsidian vault &amp; ${esc(currentVaultNote)}…</p>`;

    try {
      const [sourcesGroups, fileData] = await Promise.all([
        state.learn.sources ? Promise.resolve(state.learn.sources) : api("/api/learn/sources"),
        api(`/api/file?path=${encodeURIComponent(currentVaultNote)}`),
      ]);
      state.learn.sources = sourcesGroups;

      const navHtml = (sourcesGroups || []).map((g) => `
        <details class="src-group" ${g.items.some((i) => i.path === currentVaultNote) || g.group === "Plan & rules" || g.group === "Strategy & results" ? "open" : ""}>
          <summary>${esc(g.group)} (${g.items.length})</summary>
          <div style="display:grid; gap:2px; margin-top:4px;">
            ${g.items.map((i) => `<button type="button" class="vault-note-btn" data-vault-note="${esc(i.path)}" aria-current="${i.path === currentVaultNote}">
              ${esc(i.path.split("/").pop())}
            </button>`).join("")}
          </div>
        </details>
      `).join("");

      const rawText = String(fileData?.text || "");
      const bodyHtml = vaultRawMode
        ? `<pre class="pre" style="max-height:none; margin:0;">${esc(rawText)}</pre>`
        : `<div class="md">${renderMarkdown(rawText)}</div>`;

      stageMountEl.innerHTML = `
        <div class="inline-vault-grid">
          <aside class="box" style="padding:12px;">
            <div class="row" style="justify-content:space-between; margin-bottom:8px;">
              <b style="font-size:13px;">Obsidian Vault &amp; Plan</b>
              <span class="faint small">${(sourcesGroups || []).reduce((acc, g) => acc + g.items.length, 0)} files</span>
            </div>
            <input type="text" id="inline-vault-filter" placeholder="Filter vault notes…" style="width:100%; margin-bottom:8px;">
            <div class="vault-nav-list" id="inline-vault-nav">${navHtml}</div>
          </aside>

          <div class="box" style="padding:16px;">
            <div class="row" style="justify-content:space-between; margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid var(--line);">
              <div>
                <span class="badge small">OBSIDIAN NOTE</span>
                <b style="margin-left:8px; font-size:14px;">${esc(currentVaultNote)}</b>
              </div>
              <div class="row" style="gap:6px;">
                <button type="button" class="btn small" id="vault-toggle-raw">${vaultRawMode ? "Formatted View" : "Raw Source"}</button>
                <button type="button" class="btn small primary" id="vault-ask-tutor">Ask Tutor About This Note</button>
                <button type="button" class="btn small" id="vault-back-overview">Back to Feed &amp; Base</button>
              </div>
            </div>
            <div class="vault-note-body">${bodyHtml}</div>
          </div>
        </div>
      `;

      stageMountEl.querySelectorAll("[data-vault-note]").forEach((btn) => {
        btn.onclick = () => renderInlineVaultReader(btn.dataset.vaultNote);
      });
      $("#vault-toggle-raw")?.addEventListener("click", () => {
        vaultRawMode = !vaultRawMode;
        renderInlineVaultReader(currentVaultNote);
      });
      $("#vault-ask-tutor")?.addEventListener("click", () => {
        state.learn.selected.add(currentVaultNote);
        openInlineStage("learn", { question: `Summarize ${currentVaultNote} in plain words and explain how it fits into the Quant Brain plan.` });
      });
      $("#vault-back-overview")?.addEventListener("click", () => {
        openInlineStage("overview");
      });
      $("#inline-vault-filter")?.addEventListener("input", (e) => {
        const q = e.target.value.trim().toLowerCase();
        stageMountEl.querySelectorAll("[data-vault-note]").forEach((b) => {
          b.hidden = Boolean(q && !b.dataset.vaultNote.toLowerCase().includes(q));
        });
        if (q) stageMountEl.querySelectorAll(".src-group").forEach((d) => { d.open = true; });
      });
    } catch (err) {
      stageMountEl.innerHTML = `<p class="error">${esc(err.message)}</p>`;
    }
  }

  async function openInlineStage(tabId, opts = {}) {
    if (state.liveSource && tabId !== "live") {
      try { state.liveSource.close(); } catch (_) {}
      state.liveSource = null;
    }
    if (state.liveTimer && tabId !== "live") {
      clearInterval(state.liveTimer);
      state.liveTimer = null;
    }

    stageTabsEl?.querySelectorAll("[data-stage-tab]").forEach((btn) => {
      btn.setAttribute("aria-pressed", String(btn.dataset.stageTab === tabId));
    });

    if (tabId === "overview") {
      if (stageMountEl) { stageMountEl.hidden = true; stageMountEl.innerHTML = ""; }
      if (overviewGridEl) overviewGridEl.hidden = false;
      if (stageStatusEl) stageStatusEl.textContent = "Viewing Main Feed, Agent Base & Chart";
      return;
    }

    if (tabId === "vault") {
      if (stageStatusEl) stageStatusEl.textContent = `Reading Obsidian Note: ${opts.note || currentVaultNote}`;
      await renderInlineVaultReader(opts.note || currentVaultNote);
      $("#main-inline-stage")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
    }

    if (RENDER[tabId] && stageMountEl) {
      if (overviewGridEl) overviewGridEl.hidden = true;
      stageMountEl.hidden = false;
      const pageLabel = PAGES.find((p) => p.id === tabId)?.label || tabId;
      if (stageStatusEl) stageStatusEl.textContent = `Inline Tool: ${pageLabel}`;
      stageMountEl.innerHTML = `<p class="muted">Loading ${esc(pageLabel)}…</p>`;
      await RENDER[tabId](stageMountEl, opts);
      $("#main-inline-stage")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  function openInlineVaultNote(notePath) {
    currentVaultNote = notePath || "PLAN.md";
    openInlineStage("vault", { note: currentVaultNote });
  }

  stageTabsEl?.querySelectorAll("[data-stage-tab]").forEach((btn) => {
    btn.onclick = () => openInlineStage(btn.dataset.stageTab);
  });
  main.querySelectorAll("[data-inline-page]").forEach((btn) => {
    btn.onclick = () => openInlineStage(btn.dataset.inlinePage);
  });
  main.querySelectorAll("[data-inline-note]").forEach((btn) => {
    btn.onclick = () => openInlineVaultNote(btn.dataset.inlineNote);
  });
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

// ---------- Study: SC-FUT-0001 ----------
const OUTCOME = {
  pass_to_execution_calibration: { word: "PASSED", cls: "good", note: "Beat random entries and cleared the $15/day floor. Next would be a small paper-trading fill study, not real money." },
  not_demonstrated: { word: "NOT DEMONSTRATED", cls: "bad", note: "No edge shown: it either didn't beat random entries convincingly, or didn't clear $15/day after costs." },
  inconclusive: { word: "INCONCLUSIVE", cls: "warn", note: "The data can't settle it (too many gaps, too few trades, or the verdict flips under the worst-case check)." },
};
const WINDOW_WORD = { development: "Practice 2019–2023", diagnostics: "2024 check", held_out: "Final exam 2025–2026" };
const money = (n, d = 2) => (n == null ? "-" : `${n < 0 ? "−" : ""}$${fmt(Math.abs(n), d)}`);

// A horizontal meter with a pass line. `good` says which side of the line passes.
function meter({ label, value, text, min, max, line, lineLabel, good }) {
  const at = (v) => Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100));
  const passed = good === "below" ? value < line : value >= line;
  return `<div class="meter"><div class="row"><b>${label}</b><span class="grow"></span><span class="${passed ? "good" : "bad"}">${text}</span></div>
    <div class="meter-track" role="img" aria-label="${esc(`${label}: ${text}; pass line ${lineLabel}`)}">
      <i class="meter-fill ${passed ? "good" : "bad"}" style="left:${Math.min(at(value), at(line))}%;width:${Math.abs(at(value) - at(line))}%"></i>
      <i class="meter-line" style="left:${at(line)}%"></i><i class="meter-dot ${passed ? "good" : "bad"}" style="left:${at(value)}%"></i></div>
    <div class="row faint small"><span>${esc(String(min))}</span><span class="grow"></span><span>pass line: ${esc(lineLabel)}</span><span class="grow"></span><span>${esc(String(max))}</span></div></div>`;
}

function chip(ok, text) { return `<span class="chip ${ok ? "good" : "bad"}">${ok ? "✓" : "!"} ${esc(text)}</span>`; }

function verdictCard(key, entry) {
  const v = entry.verdict, o = OUTCOME[v.outcome] || { word: v.outcome, cls: "", note: "" };
  const [market, window] = key.split("/");
  const p = v.p_value, abs = v.absolute_mean_cents == null ? null : v.absolute_mean_cents / 100;
  const paired = v.observed_paired_cents == null ? null : v.observed_paired_cents / 100;
  const power = entry.power;
  return `<article class="box verdict">
    <div class="row"><span class="mono faint">${esc(market)} · ${esc(WINDOW_WORD[window] || window)}</span><span class="grow"></span><span class="faint small">${fmt(v.evaluable_days, 0)} days · ${fmt(v.trades, 0)} trades</span></div>
    <p class="verdict-word ${o.cls}">${o.word}</p><p class="muted" style="margin-top:0">${esc(o.note)}</p>
    ${p == null ? "" : meter({ label: "Better than random entries?", value: p, text: `p = ${fmt(p, 3)} · ${money(paired)}/day better`, min: 0, max: 1, line: 0.05, lineLabel: "p < 0.05", good: "below" })}
    ${abs == null ? "" : meter({ label: "Profit per day after costs", value: abs, text: `${money(abs)}/day`, min: -30, max: 30, line: 15, lineLabel: "$15/day", good: "above" })}
    <div class="row" style="margin-top:12px">
      ${chip(v.missing_session_share <= 0.01, `data gaps ${fmt(v.missing_session_share * 100, 1)}% (limit 1%)`)}
      ${v.ambiguity_share == null ? "" : chip(v.ambiguity_share <= 0.1, `same-minute stops ${fmt(v.ambiguity_share * 100, 1)}% (limit 10%)`)}
      ${power ? chip(power.joint_power >= 0.8, `power ${fmt(power.joint_power * 100, 0)}% to catch a real $20/day edge (target 80%)`) : ""}
      ${v.stress_outcome ? chip(v.stress_outcome === v.outcome || v.outcome === "inconclusive", `worst-case check: ${v.stress_outcome === v.outcome ? "same verdict" : "different"}`) : ""}
    </div></article>`;
}

function trailStrip(trail) {
  return `<ol class="trail">${trail.map((s) => `<li class="${s.done ? "done" : "todo"}" title="${esc(s.about)}">
    <b>${s.done ? "✓" : "🔒"} ${esc(s.label)}</b><span class="faint small">${s.at ? esc(s.at.slice(0, 10)) : "not yet"}</span>
    ${s.detail ? `<span class="mono faint small">${esc(String(s.detail).slice(0, 10))}…</span>` : ""}</li>`).join("")}</ol>`;
}

function histogramSvg(h) {
  const W = 640, H = 170, pad = 24, n = h.counts.length, top = Math.max(...h.counts, 1);
  const lo = h.edges[0], hi = h.edges[n], x = (v) => pad + ((v - lo) / (hi - lo || 1)) * (W - 2 * pad);
  const bars = h.counts.map((c, i) => { const x0 = x(h.edges[i]), x1 = x(h.edges[i + 1]); const bh = (c / top) * (H - 2 * pad); return `<rect x="${x0 + 1}" y="${H - pad - bh}" width="${Math.max(1, x1 - x0 - 2)}" height="${bh}" class="hist-bar"/>`; }).join("");
  const ox = Math.max(pad, Math.min(W - pad, x(h.orb_total)));
  return `<svg viewBox="0 0 ${W} ${H}" class="hist" role="img" aria-label="${esc(`Totals of 500 random-entry versions; the strategy's total ${money(h.orb_total, 0)} beat ${Math.round(h.share_of_draws_beaten * 100)}% of them`)}">
    ${bars}<line x1="${ox}" x2="${ox}" y1="${pad / 2}" y2="${H - pad}" class="hist-orb"/>
    <text x="${ox + 4}" y="${pad}" class="hist-label">strategy ${esc(money(h.orb_total, 0))}</text>
    <text x="${pad}" y="${H - 6}" class="hist-axis">${esc(money(lo, 0))}</text><text x="${W - pad}" y="${H - 6}" text-anchor="end" class="hist-axis">${esc(money(hi, 0))}</text></svg>`;
}

function yearTable(diag) {
  if (!diag || !diag.by_year) return "";
  const years = Object.entries(diag.by_year), ladder = Object.entries(diag.cost_ladder || {});
  return `<div class="study-grid">
    <div class="box"><h3>By year</h3><p class="faint small">Does any edge come from one lucky year?</p><div class="table-wrap"><table><tr><th>Year</th><th class="num">Days</th><th class="num">Per day</th><th class="num">vs random</th></tr>
      ${years.map(([y, r]) => `<tr><td>${esc(y)}</td><td class="num">${fmt(r.days, 0)}</td><td class="num ${r.absolute_mean_cents >= 0 ? "good" : "bad"}">${money(r.absolute_mean_cents / 100)}</td><td class="num ${r.paired_mean_cents >= 0 ? "good" : "bad"}">${money(r.paired_mean_cents / 100)}</td></tr>`).join("")}</table></div></div>
    <div class="box"><h3>Cost ladder</h3><p class="faint small">Per-day profit as trading costs rise. L3 is the official level.</p><div class="table-wrap"><table><tr><th>Cost level</th><th class="num">Per day</th><th class="num">vs random</th></tr>
      ${ladder.map(([l, r]) => `<tr${l === "L3" ? ' class="bench"' : ""}><td>${esc(l)}${l === "L3" ? " (official)" : ""}</td><td class="num ${r.absolute_mean_cents >= 0 ? "good" : "bad"}">${money(r.absolute_mean_cents / 100)}</td><td class="num ${r.paired_mean_cents >= 0 ? "good" : "bad"}">${money(r.paired_mean_cents / 100)}</td></tr>`).join("")}</table></div></div></div>`;
}

RENDER.study = async (main) => {
  const d = await api("/api/study");
  const S = (state.study = state.study || { phase: "development", market: "MNQ", window: "development", day: null });
  const report = d.phases[S.phase];
  const lead = "One strategy, tested honestly: rules frozen first, compared with 500 random entries every day, and a locked final exam that can be opened only once.";
  if (!report) {
    main.innerHTML = `${head("Study: SC-FUT-0001", lead)}${trailStrip(d.trail)}<div class="empty"><h3>No results yet</h3>The practice run hasn't finished. This page fills in from its report.</div>`;
    return;
  }
  const keys = Object.keys(report);
  const windows = [...new Set(keys.map((k) => k.split("/")[1]))];
  if (!windows.includes(S.window)) S.window = windows[0];
  const key = `${S.market}/${S.window}`, entry = report[key];
  const seg = (name, values, word) => `<div class="seg" role="group" aria-label="${name}">${values.map((v) => `<button type="button" data-study-${name}="${esc(v)}" aria-pressed="${S[name] === v}">${esc(word(v))}</button>`).join("")}</div>`;
  const phases = Object.keys(d.phases);
  main.innerHTML = `${head("Study: SC-FUT-0001", lead)}
    <section>${trailStrip(d.trail)}</section>
    <div class="row" style="margin:14px 0">${phases.length > 1 ? seg("phase", phases, (v) => (v === "held_out" ? "Final exam" : "Practice")) : ""}${seg("market", ["MNQ", "MES"], (v) => (v === "MNQ" ? "MNQ (main)" : "MES (comparison only)"))}${seg("window", windows, (v) => WINDOW_WORD[v] || v)}</div>
    <section>${entry ? verdictCard(key, entry) : `<p class="muted">No result for ${esc(key)}.</p>`}</section>
    <section><h2>Strategy vs luck</h2>
      <p class="muted">The bold line is the strategy's running profit after costs. The grey band is where 90% of 500 random-entry versions ended up on the same days, with the same stop and costs. Inside the band means you can't tell it from luck.</p>
      <div class="legend"><span><i style="background:#f0a93b"></i>strategy</span><span><i style="background:#94a3b8"></i>random entries: average</span><span><i style="background:#475569"></i>random entries: 5%–95% band</span></div>
      <div class="study-chart" id="study-equity"></div>
      <div id="study-hist"></div></section>
    <section><h2>Where the money goes</h2>${yearTable(entry && entry.diagnostics)}</section>
    <section><h2>Replay a day</h2>
      <p class="muted">Pick a day to see the 1-minute candles, the opening-range box, the breakout, the stop and the exit. Faint dots are where random entries went in that day.</p>
      <div class="row"><label class="small">Day <select id="study-day"></select></label><button class="btn" id="study-best">Best day</button><button class="btn" id="study-worst">Worst day</button></div>
      <div id="study-replay-info" class="small muted" style="margin:8px 0"></div><div class="study-chart tall" id="study-replay"></div></section>`;
  main.querySelectorAll("[data-study-phase],[data-study-market],[data-study-window]").forEach((b) => (b.onclick = () => {
    if (b.dataset.studyPhase) { S.phase = b.dataset.studyPhase; S.window = S.phase === "held_out" ? "held_out" : "development"; }
    if (b.dataset.studyMarket) S.market = b.dataset.studyMarket;
    if (b.dataset.studyWindow) S.window = b.dataset.studyWindow;
    S.day = null;
    go("study");
  }));
  const fileKey = `${S.market}.${S.window}`;
  const sp = `phase=${encodeURIComponent(S.phase)}&key=${encodeURIComponent(fileKey)}`;
  const [series, days] = await Promise.all([api(`/api/study/series?${sp}`), api(`/api/study/days?${sp}`)]);
  drawEquity(series);
  $("#study-hist").innerHTML = series.histogram
    ? `<h3>Where would luck have put you?</h3><p class="muted">Each bar counts random-entry versions by their total profit. The line is the strategy: it beat ${Math.round(series.histogram.share_of_draws_beaten * 100)}% of them. To count as an edge it needs to beat about 95%.</p>${histogramSvg(series.histogram)}`
    : `<p class="faint small">The luck band and histogram need the per-entry file from a newer practice run.</p>`;
  const traded = days.filter((x) => x.trades > 0);
  $("#study-day").innerHTML = traded.map((x) => `<option value="${esc(x.date)}">${esc(x.date)} · ${money(x.orb)} · ${x.trades} trade${x.trades > 1 ? "s" : ""}</option>`).join("");
  const show = (day) => { S.day = day; $("#study-day").value = day; drawReplay(S.market, day); };
  $("#study-day").onchange = (e) => show(e.target.value);
  $("#study-best").onclick = () => show(traded.reduce((a, b) => (b.orb > a.orb ? b : a)).date);
  $("#study-worst").onclick = () => show(traded.reduce((a, b) => (b.orb < a.orb ? b : a)).date);
  if (traded.length && S.window !== "held_out") show(S.day && traded.some((x) => x.date === S.day) ? S.day : traded[0].date);
};

function drawEquity(s) {
  const box = $("#study-equity");
  const chart = LightweightCharts.createChart(box, { ...CHART_OPTS(), autoSize: true });
  charts.push(chart);
  const pts = (arr) => s.dates.map((t, i) => ({ time: t, value: arr[i] }));
  if (s.band_low) {
    chart.addSeries(LightweightCharts.LineSeries, { color: "#475569", lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false }).setData(pts(s.band_low));
    chart.addSeries(LightweightCharts.LineSeries, { color: "#475569", lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false }).setData(pts(s.band_high));
  }
  chart.addSeries(LightweightCharts.LineSeries, { color: "#94a3b8", lineWidth: 1, priceLineVisible: false }).setData(pts(s.control_mean));
  const orb = chart.addSeries(LightweightCharts.LineSeries, { color: "#f0a93b", lineWidth: 3 });
  orb.setData(pts(s.orb));
  orb.createPriceLine({ price: 0, color: "#64748b", lineWidth: 1, lineStyle: 2, axisLabelVisible: false });
  chart.timeScale().fitContent();
}

async function drawReplay(market, day) {
  const info = $("#study-replay-info"), box = $("#study-replay");
  info.textContent = "Loading the day's minute bars…";
  let r;
  try { r = await api(`/api/study/replay?market=${encodeURIComponent(market)}&day=${encodeURIComponent(day)}`); }
  catch (e) { info.innerHTML = `<span class="error">${esc(e.message)}</span>`; return; }
  while (charts.length > 1) { try { charts.pop().remove(); } catch (e) { /* gone */ } }
  box.innerHTML = "";
  const chart = LightweightCharts.createChart(box, { ...CHART_OPTS(), autoSize: true, timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#27302b" } });
  charts.push(chart);
  const candles = chart.addSeries(LightweightCharts.CandlestickSeries, { upColor: "#5cc98f", downColor: "#ef6b6b", borderVisible: false, wickUpColor: "#5cc98f", wickDownColor: "#ef6b6b" });
  candles.setData(r.candles);
  if (r.range.high != null) {
    candles.createPriceLine({ price: r.range.high, color: "#38bdf8", lineWidth: 1, lineStyle: 0, axisLabelVisible: true, title: "range high" });
    candles.createPriceLine({ price: r.range.low, color: "#38bdf8", lineWidth: 1, lineStyle: 0, axisLabelVisible: true, title: "range low" });
  }
  const markers = [];
  r.trades.forEach((t, i) => {
    const long = t.side === "long";
    if (t.signal) markers.push({ time: t.signal, position: long ? "aboveBar" : "belowBar", color: "#38bdf8", shape: "circle", text: "breakout" });
    markers.push({ time: t.entry_time, position: long ? "belowBar" : "aboveBar", color: "#f0a93b", shape: long ? "arrowUp" : "arrowDown", text: `${long ? "buy" : "sell"} ${fmt(t.entry)}` });
    markers.push({ time: t.exit_time, position: long ? "aboveBar" : "belowBar", color: t.net >= 0 ? "#10b981" : "#f43f5e", shape: "square", text: `${t.reason === "flatten" ? "exit" : "stopped"} ${money(t.net)}` });
    candles.createPriceLine({ price: t.stop, color: "#f43f5e", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: `stop ${i + 1}` });
  });
  r.gaps.forEach((g) => markers.push({ time: g, position: "inBar", color: "#f59e0b", shape: "square", text: "gap" }));
  if (r.control) r.control.entries.forEach((c) => markers.push({ time: c.time, position: "inBar", color: "rgba(148,163,184,0.35)", shape: "circle", size: 0.4 }));
  markers.sort((a, b) => a.time - b.time);
  LightweightCharts.createSeriesMarkers(candles, markers);
  chart.timeScale().fitContent();
  const t = r.trades.map((x) => `${x.side} at ${fmt(x.entry)} → ${x.reason === "flatten" ? "closed at the 3:07 exit" : "stopped"} at ${fmt(x.exit)} (${money(x.net)})${x.gap_affected ? ", data gap while open" : ""}`).join("; ");
  info.innerHTML = `${esc(r.date)} · ${esc(market)} · stop distance ${fmt(r.stop_points)} pts · day ${money(r.net)}${r.control ? ` · random entries averaged ${money(r.control.mean)}` : ""}<br>${esc(t)}`;
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
          <h2>Kelly Criterion &amp; Position Scaling</h2>
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
  const presets = UIState.normalizePresets(snapshot?.presets);

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
            ${Object.entries(presets).map(([k, v]) => `<option value="${esc(k)}">${esc(v.title || v.label || k)}</option>`).join("")}
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
    const preset = presets[presetKey];
    $("#preset-why").innerHTML = preset ? `<b>Why a quant looks:</b> ${esc(preset.why)} <br><span class="bad"><b>The trap:</b> ${esc(preset.trap)}</span>` : "Click any symbol row to open the full interactive chart.";

    const filtered = UIState.filterMarketRows(rows, presetKey);

    $("#screener-body").innerHTML = filtered.map((r) => {
      const tone1d = UIState.directionClass(r.change_1d_pct);
      const tone1m = UIState.directionClass(r.change_1m_pct);
      const toneSma = UIState.directionClass(r.vs_sma_200_pct);
      const rsi2Tone = r.rsi_2 < 10 ? "good" : r.rsi_2 > 90 ? "bad" : "";
      return `<tr class="click" data-sym="${esc(r.symbol)}">
        <td><b class="mono" style="color:var(--accent)">${esc(r.symbol)}</b></td>
        <td class="small muted">${esc(clip(r.name, 28))}</td>
        <td class="mono num">${esc(UIState.formatPrice(r.close))}</td>
        <td class="mono num ${tone1d}">${esc(UIState.formatPercentPoints(r.change_1d_pct, 1))}</td>
        <td class="mono num ${tone1m}">${esc(UIState.formatPercentPoints(r.change_1m_pct, 1))}</td>
        <td class="mono num ${rsi2Tone}"><b>${esc(fmt(r.rsi_2, 1))}</b></td>
        <td class="mono num">${esc(fmt(r.rsi_14, 1))}</td>
        <td class="mono num ${toneSma}">${esc(UIState.formatPercentPoints(r.vs_sma_200_pct, 1))}</td>
        <td><span class="badge small" title="${esc(UIState.provenanceLabel(r.provenance))}">${esc(r.provenance?.freshness || "Unavailable")}</span></td>
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
  let liveTracker = UIState.beginCryptoConnection(
    UIState.createCryptoTracker(Object.keys(stateFeed))
  );
  const liveGeneration = liveTracker.generation;
  const clearLiveCaches = () => {
    Object.values(stateFeed).forEach((productState) => {
      UIState.clearCryptoProductState(productState);
    });
  };

  main.innerHTML = `${head("Live Crypto Feed (Public WebSocket)", "Real-time, zero-key streaming from Coinbase Advanced Trade. Watch ticks, spread, and order book depth live.")}
    <div class="row" style="margin-bottom:16px">
      <div class="seg" id="live-prod-seg">
        <button type="button" data-prod="BTC-USD" aria-pressed="true">BTC-USD</button>
        <button type="button" data-prod="ETH-USD">ETH-USD</button>
      </div>
      <span class="grow"></span>
      <div class="live" id="crypto-conn-pill"><i></i><span>WAITING · Coinbase upstream</span></div>
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
    const display = UIState.cryptoDisplayState(liveTracker, activeProduct, Date.now());
    const pill = $("#crypto-conn-pill");
    if (pill) {
      pill.className = `live ${display === "LIVE" ? "on" : display === "WAITING" ? "" : "off"}`;
      pill.querySelector("span").textContent = `${display} · Coinbase upstream`;
    }

    const price = UIState.strictFiniteNumber(data.price);
    const bid = UIState.strictFiniteNumber(data.bid);
    const ask = UIState.strictFiniteNumber(data.ask);
    const change = UIState.strictFiniteNumber(data.change);
    const volume = UIState.strictFiniteNumber(data.volume);
    const spread = bid !== null && ask !== null && ask >= bid ? ask - bid : null;

    $("#live-price").textContent = UIState.formatPrice(price);
    $("#live-change").textContent = UIState.formatPercentPoints(change, 2);
    $("#live-change").className = `mono ${UIState.directionClass(change)}`;
    $("#live-bid").textContent = UIState.formatPrice(bid);
    $("#live-ask").textContent = UIState.formatPrice(ask);
    $("#live-spread").textContent = spread === null ? "Unavailable" : UIState.formatPrice(spread);
    $("#live-spread-detail").textContent = spread === null || price === null || price <= 0
      ? "Spread: Unavailable"
      : `Spread: ${UIState.formatPrice(spread)} (${((spread / price) * 100).toFixed(3)}%)`;
    $("#live-vol").textContent = volume === null ? "Unavailable" : volume.toLocaleString(undefined, { maximumFractionDigits: 2 });

    $("#live-trades-tape").innerHTML = (data.trades || []).slice(0, 15).map((t) => {
      const isBuy = t.side === "buy";
      const tradePrice = UIState.strictFiniteNumber(t.price);
      const tradeSize = UIState.strictFiniteNumber(t.size);
      return `<tr>
        <td class="mono faint small">${esc(String(t.time || "").slice(11, 19) || "Unavailable")}</td>
        <td class="${isBuy ? "good" : "bad"} small"><b>${isBuy ? "BUY" : "SELL"}</b></td>
        <td class="mono num ${isBuy ? "good" : "bad"}">${esc(UIState.formatPrice(tradePrice))}</td>
        <td class="mono num faint">${tradeSize === null ? "Unavailable" : esc(tradeSize.toFixed(4))}</td>
      </tr>`;
    }).join("") || `<tr><td colspan="4" class="empty">No usable trades received.</td></tr>`;

    const bookLevels = (levels) => (levels || []).map(([p, q]) => [
      UIState.strictFiniteNumber(p), UIState.strictFiniteNumber(q)
    ]).filter(([p, q]) => p !== null && q !== null && p > 0 && q >= 0);
    const bids = bookLevels(data.bids);
    const asks = bookLevels(data.asks);
    const maxQty = Math.max(...bids.map((b) => b[1]), ...asks.map((a) => a[1]), 0.01);
    $("#live-book-asks").innerHTML = asks.slice(-7).reverse().map(([p, q]) => {
      const pctWidth = Math.min(100, Math.round((q / maxQty) * 100));
      return `<div class="row mono small" style="position:relative;padding:3px 6px">
        <div style="position:absolute;inset:0;right:${100 - pctWidth}%;background:rgba(239,107,107,0.18);border-radius:2px;pointer-events:none"></div>
        <span class="bad num">${esc(UIState.formatPrice(p))}</span>
        <span class="grow"></span>
        <span class="faint num">${esc(q.toFixed(4))}</span>
      </div>`;
    }).join("") || `<div class="empty small">Asks unavailable</div>`;

    $("#live-book-bids").innerHTML = bids.slice(0, 7).map(([p, q]) => {
      const pctWidth = Math.min(100, Math.round((q / maxQty) * 100));
      return `<div class="row mono small" style="position:relative;padding:3px 6px">
        <div style="position:absolute;inset:0;right:${100 - pctWidth}%;background:rgba(92,201,143,0.18);border-radius:2px;pointer-events:none"></div>
        <span class="good num">${esc(UIState.formatPrice(p))}</span>
        <span class="grow"></span>
        <span class="faint num">${esc(q.toFixed(4))}</span>
      </div>`;
    }).join("") || `<div class="empty small">Bids unavailable</div>`;
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
  if (state.liveTimer) clearInterval(state.liveTimer);
  const sse = new EventSource("/api/live/crypto?products=BTC-USD,ETH-USD");
  state.liveSource = sse;

  sse.onopen = () => {
    liveTracker = reduceCryptoEvent(liveTracker, liveGeneration, { type: "transport", status: "open" });
    renderActive();
  };
  sse.onerror = () => {
    liveTracker = reduceCryptoEvent(liveTracker, liveGeneration, { type: "transport", status: "error" });
    clearLiveCaches();
    renderActive();
  };

  sse.addEventListener("status", (e) => {
    try {
      liveTracker = reduceCryptoEvent(liveTracker, liveGeneration, JSON.parse(e.data));
    } catch (_) {
      liveTracker = reduceCryptoEvent(liveTracker, liveGeneration, { type: "status", state: "error" });
    }
    if (liveTracker.upstream !== "live") clearLiveCaches();
    renderActive();
  });

  sse.addEventListener("ticker", (e) => {
    try {
      const ev = JSON.parse(e.data);
      const receivedAt = Date.now();
      liveTracker = reduceCryptoEvent(liveTracker, liveGeneration, ev, receivedAt);
      const prod = ev.product;
      if (stateFeed[prod] && liveTracker.lastTickAt[prod] === receivedAt) {
        stateFeed[prod].price = UIState.strictFiniteNumber(ev.price);
        stateFeed[prod].bid = UIState.strictFiniteNumber(ev.bid);
        stateFeed[prod].ask = UIState.strictFiniteNumber(ev.ask);
        stateFeed[prod].change = UIState.strictFiniteNumber(ev.change_24h_pct);
        stateFeed[prod].high = UIState.strictFiniteNumber(ev.high_24h);
        stateFeed[prod].low = UIState.strictFiniteNumber(ev.low_24h);
        stateFeed[prod].volume = UIState.strictFiniteNumber(ev.volume_24_h ?? ev.volume_24h);
        if (prod === activeProduct) renderActive();
      }
    } catch (_) {
      liveTracker = reduceCryptoEvent(liveTracker, liveGeneration, { type: "status", state: "error" });
      clearLiveCaches();
      renderActive();
    }
  });

  sse.addEventListener("trade", (e) => {
    const ev = JSON.parse(e.data);
    const prod = ev.product;
    if (stateFeed[prod] && liveTracker.transport === "open" && liveTracker.upstream === "live") {
      stateFeed[prod].trades.unshift(ev);
      if (stateFeed[prod].trades.length > 50) stateFeed[prod].trades.pop();
      if (prod === activeProduct) renderActive();
    }
  });

  sse.addEventListener("book", (e) => {
    const ev = JSON.parse(e.data);
    const prod = ev.product;
    if (stateFeed[prod] && liveTracker.transport === "open" && liveTracker.upstream === "live") {
      stateFeed[prod].bids = ev.bids || [];
      stateFeed[prod].asks = ev.asks || [];
      if (prod === activeProduct) renderActive();
    }
  });
  state.liveTimer = setInterval(() => {
    if (state.page === "live") renderActive();
  }, 1000);
  renderActive();
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
      const item = (snap.rows || []).find((i) => i.symbol === sym);
      const el = $(`#tick-${sym.toLowerCase()}`);
      if (!el) continue;
      if (!item) {
        el.innerHTML = `<b style="color:#fff;">${sym}</b> <span style="color:var(--faint); font-size:10.5px;">Unavailable · no accepted dataset</span>`;
        continue;
      }
      const closeText = UIState.formatPrice(item.close);
      const changeText = UIState.formatPercentPoints(item.change_1d_pct, 2);
      const direction = UIState.directionClass(item.change_1d_pct);
      const changeColor = direction === "good" ? "var(--good)" : direction === "bad" ? "var(--bad)" : "var(--faint)";
      const sourceText = UIState.provenanceLabel(item.provenance);
      el.innerHTML = `<b style="color:#fff;">${esc(item.symbol)}</b> ${esc(closeText)} <span style="color:${changeColor};">${esc(changeText)}</span> <span style="color:var(--faint); font-size:10.5px;">${esc(sourceText)}</span>`;
    }
  } catch (e) {
    ["spy", "qqq", "iwm"].forEach((s) => {
      const el = $(`#tick-${s}`);
      if (el) el.innerHTML = `<b style="color:#fff;">${s.toUpperCase()}</b> <span style="color:var(--faint); font-size:10.5px;">Unavailable</span>`;
    });
  }
}

let tickerSSE = null;
let tickerTracker = UIState.createCryptoTracker(["BTC-USD", "ETH-USD"]);
const tickerValues = Object.create(null);

function clearTickerValues() {
  for (const product of ["BTC-USD", "ETH-USD"]) delete tickerValues[product];
}

function cryptoTone(status) {
  if (status === "LIVE") return "var(--good)";
  if (status === "DELAYED" || status === "WAITING") return "var(--warn)";
  return "var(--bad)";
}

function updateTickerAge() {
  const now = Date.now();
  for (const [product, elId] of [["BTC-USD", "#tick-btc"], ["ETH-USD", "#tick-eth"]]) {
    const display = UIState.cryptoDisplayState(tickerTracker, product, now);
    const el = $(elId);
    if (!el) continue;
    const symbol = product.replace("-USD", "");
    const price = tickerValues[product];
    const priceText = price == null ? "Price unavailable" : UIState.formatPrice(price);
    const tickAt = tickerTracker.lastTickAt[product];
    const ageText = tickAt == null ? "no usable quote" : `updated ${Math.round(Math.max(0, now - tickAt) / 1000)}s ago`;
    el.innerHTML = `<b style="color:#fff;">${symbol}</b> ${esc(priceText)} <span style="color:${cryptoTone(display)}; font-size:10.5px;">${display} · Coinbase · ${ageText}</span>`;
    if (product === "BTC-USD") {
      const todayValue = $("#today-btc-val");
      const todayStatus = $("#today-coinbase-status");
      if (todayValue) {
        todayValue.textContent = priceText;
        todayValue.style.color = cryptoTone(display);
      }
      if (todayStatus) {
        todayStatus.className = `live ${display === "LIVE" ? "on" : display === "WAITING" ? "" : "off"}`;
        todayStatus.querySelector("span").textContent = display;
      }
    }
  }
}
setInterval(updateTickerAge, 1000);

function connectTickerLive() {
  try {
    if (tickerSSE) tickerSSE.close();
    tickerTracker = UIState.beginCryptoConnection(tickerTracker);
    clearTickerValues();
    const generation = tickerTracker.generation;
    tickerSSE = new EventSource("/api/live/crypto");
    tickerSSE.onopen = () => {
      tickerTracker = reduceCryptoEvent(tickerTracker, generation, { type: "transport", status: "open" });
      updateTickerAge();
    };
    tickerSSE.addEventListener("status", (e) => {
      try {
        tickerTracker = reduceCryptoEvent(tickerTracker, generation, JSON.parse(e.data));
      } catch (err) {
        tickerTracker = reduceCryptoEvent(tickerTracker, generation, { type: "status", state: "error" });
      }
      if (tickerTracker.upstream !== "live") clearTickerValues();
      updateTickerAge();
    });
    tickerSSE.addEventListener("ticker", (e) => {
      try {
        const event = JSON.parse(e.data);
        const receivedAt = Date.now();
        tickerTracker = reduceCryptoEvent(tickerTracker, generation, event, receivedAt);
        const price = UIState.strictFiniteNumber(event.price);
        if (event.product && price !== null
            && tickerTracker.lastTickAt[event.product] === receivedAt) {
          tickerValues[event.product] = price;
        }
      } catch (err) {
        tickerTracker = reduceCryptoEvent(tickerTracker, generation, { type: "status", state: "error" });
        clearTickerValues();
      }
      updateTickerAge();
    });
    tickerSSE.onerror = () => {
      tickerTracker = reduceCryptoEvent(tickerTracker, generation, { type: "transport", status: "error" });
      clearTickerValues();
      updateTickerAge();
    };
    updateTickerAge();
  } catch (e) {
    tickerTracker = reduceCryptoEvent(tickerTracker, tickerTracker.generation, { type: "transport", status: "error" });
    updateTickerAge();
  }
}

// ---------- Roaming Screen Companion Co-Pilot ----------
let companionOpen = false;
let companionCustomText = null;
let companionCoords = null;
let patrolIdx = 0;

const PAGE_COMPANION_GUIDE = {
  today: {
    title: "Command Base Co-Pilot",
    text: "You're at the Main Base. Click any bot on the floorplan to see what it does, or press 'Replay Latest Run' to watch them move between stations.",
    question: "Explain how all the agents in the Quant Brain harness work together from Research to Review.",
  },
  chart: {
    title: "Superchart Co-Pilot",
    text: "Use Replay or Blind Mode to step through bars without hindsight bias, or load SC-0002's 101 trades in the bottom drawer.",
    question: "Explain what this chart is showing and how next-bar execution prevents look-ahead bias.",
  },
  activity: {
    title: "Operations Trail Co-Pilot",
    text: "Every agent run, Qwen validation gate, and git commit is recorded here. Click any run to see why it stopped.",
    question: "What happened in the last research run, and why did the fail-closed safeguards trigger?",
  },
  strategies: {
    title: "Strategy & Trial Lab Co-Pilot",
    text: "Every parameter test counts as a trial. We compare against Buy & Hold and discount for multiple testing using DSR.",
    question: "Why was SC-0002 rejected on held-out data despite having a 71% win rate in-sample?",
  },
  risk: {
    title: "Risk & Survival Co-Pilot",
    text: "Test your position sizing and run 2,000 Monte Carlo paths to see how risk per trade impacts probability of ruin.",
    question: "Why does risking 5% or 10% per trade lead to ruin even when a strategy has a positive edge?",
  },
  market: {
    title: "Screener & Macro Co-Pilot",
    text: "Filter the starter universe by RSI(2) and SMA(200), or check upcoming FOMC rate decision dates.",
    question: "Why do quants combine a short-term oversold indicator like RSI(2) with a long-term trend filter like SMA(200)?",
  },
  live: {
    title: "Microstructure Co-Pilot",
    text: "Streaming live Coinbase ticks and 10-level order book depth. Watch how bid-ask spread and depth shift in real time.",
    question: "Explain bid-ask spread, order book depth, and how slippage affects algorithmic trading.",
  },
  learn: {
    title: "Grounded Tutor Co-Pilot",
    text: "Tick any project files on the left and ask a question. Every claim links to the exact source line.",
    question: "Explain this whole project to me like I'm new to it.",
  },
  setup: {
    title: "Automations & Models Co-Pilot",
    text: "Manage scheduled health checks, market data refreshes, and check which AI backends and skills are registered.",
    question: "How do the harness permissions and read-only database rules keep the project safe?",
  },
};

function renderRoamingCompanion() {
  const root = $("#roaming-companion-root");
  if (!root || !window.QBBots) return;
  const styleMode = (() => {
    try { return localStorage.getItem("qb-bot-style") || "droid"; } catch (_) { return "droid"; }
  })();
  const guide = PAGE_COMPANION_GUIDE[state.page] || PAGE_COMPANION_GUIDE.today;
  const bodyText = companionCustomText || guide.text;
  const posStyle = companionCoords
    ? `left:${companionCoords.left}px; top:${companionCoords.top}px; right:auto; bottom:auto;`
    : "";

  root.innerHTML = `
    <div class="roaming-companion" id="roaming-companion" style="${posStyle}">
      ${companionOpen ? `
        <div class="roaming-companion-card" role="region" aria-label="Quant Co-Pilot Assistant">
          <div class="row" style="margin-bottom:6px;">
            <b style="color:var(--accent); font-size:12.5px;">${esc(guide.title)}</b>
            <span class="grow"></span>
            ${companionCoords ? `<button type="button" class="link small" id="comp-dock" style="margin-right:6px;">Dock</button>` : ""}
            <button type="button" class="link small" id="comp-close" aria-label="Minimize Co-Pilot">Close</button>
          </div>
          <p style="margin:0 0 10px; color:var(--text); line-height:1.45;">${esc(bodyText)}</p>
          <div class="row" style="gap:6px;">
            <button type="button" class="btn small primary" id="comp-ask-btn">Explain This Screen</button>
            ${state.page !== "today" ? `<button type="button" class="btn small" id="comp-home-btn">Return to Base</button>` : `<button type="button" class="btn small" id="comp-patrol-btn">Walk to Next Panel</button>`}
          </div>
        </div>
      ` : ""}
      <button type="button" class="roaming-companion-btn" id="comp-toggle-btn" title="Quant Co-Pilot Bot (Click to interact)" aria-expanded="${companionOpen}">
        ${window.QBBots.botAvatarSvg(styleMode, "#4a8ad6", companionOpen ? "happy" : "idle")}
      </button>
    </div>
  `;

  $("#comp-toggle-btn")?.addEventListener("click", () => {
    companionOpen = !companionOpen;
    companionCustomText = null;
    renderRoamingCompanion();
  });
  $("#comp-close")?.addEventListener("click", () => {
    companionOpen = false;
    companionCoords = null;
    document.querySelectorAll(".roam-target-highlight").forEach((el) => el.classList.remove("roam-target-highlight"));
    renderRoamingCompanion();
  });
  $("#comp-dock")?.addEventListener("click", () => {
    companionCoords = null;
    document.querySelectorAll(".roam-target-highlight").forEach((el) => el.classList.remove("roam-target-highlight"));
    renderRoamingCompanion();
  });
  $("#comp-ask-btn")?.addEventListener("click", () => {
    companionOpen = false;
    companionCoords = null;
    go("learn", { question: guide.question });
  });
  $("#comp-home-btn")?.addEventListener("click", () => {
    companionCoords = null;
    go("today");
  });
  $("#comp-patrol-btn")?.addEventListener("click", () => {
    const targets = [
      { sel: ".kpi-strip", msg: "KPI Strip: 5/5 stages complete, 72 trials recorded in the ledger, and 48 verified EOD datasets." },
      { sel: "#cockpit-col-chart", msg: "SPY Backtest Replay: Step through 101 in-sample or 91 held-out trades with next-bar execution." },
      { sel: "#cockpit-col-strategy", msg: "Agent Operations Base: 5 specialist bots mapped to their workstations. Click Replay Run to animate." },
      { sel: "#master-feed-section", msg: "Unified Everything Feed: Every backtest, review, research source, failed-run receipt, market dataset, FOMC event, decision, and commit in one filterable stream." },
    ];
    const pick = targets[patrolIdx % targets.length];
    patrolIdx += 1;
    document.querySelectorAll(".roam-target-highlight").forEach((el) => el.classList.remove("roam-target-highlight"));
    const el = $(pick.sel);
    if (el) {
      el.classList.add("roam-target-highlight");
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      const rect = el.getBoundingClientRect();
      const maxLeft = Math.max(20, window.innerWidth - 380);
      const maxTop = Math.max(20, window.innerHeight - 170);
      companionCoords = {
        left: Math.min(maxLeft, Math.max(20, Math.round(rect.right - 340))),
        top: Math.min(maxTop, Math.max(60, Math.round(rect.top + 16))),
      };
    }
    companionCustomText = pick.msg;
    renderRoamingCompanion();
  });
}

// ---------- boot ----------
function boot() {
  buildTabs();
  let first = "today";
  try { const s = localStorage.getItem("qb-page"); if (PAGES.some((p) => p.id === s)) first = s; } catch (e) { /* storage blocked */ }
  const hash = location.hash.slice(1);
  if (PAGES.some((p) => p.id === hash)) first = hash;
  go(first);
  connectStream();
  hydrateTicker();
  connectTickerLive();
  footer();
  renderRoamingCompanion();
}
document.addEventListener("DOMContentLoaded", boot);
