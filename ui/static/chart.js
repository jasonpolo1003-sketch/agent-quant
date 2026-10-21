/* Chart workspace: a TradingView-style chart you can drive yourself.
   Loaded after app.js and uses its helpers ($, esc, api, send, toast, go, state, RENDER).
   Every server value goes through esc() before it touches innerHTML. */
"use strict";

const LW = LightweightCharts;
const CH_DEFAULT = {
  symbol: "SPY", tf: "D", basis: "split", style: "candles", log: false,
  indicators: [{ id: "i1", kind: "sma", params: { n: 50 } }, { id: "i2", kind: "sma", params: { n: 200 } }, { id: "i3", kind: "rsi", params: { n: 14 } }],
  compare: [], formula: "", panel: "watchlist", drawer: "trades", drawerOpen: true,
};
const CH = (() => { try { return { ...CH_DEFAULT, ...JSON.parse(localStorage.getItem("qb-chart") || "{}") }; } catch (e) { return { ...CH_DEFAULT }; } })();
const CT = { chart: null, main: null, volume: null, overlays: [], markers: null, drawings: [], data: null, ind: [], catalog: null, watch: null,
  tool: "cursor", pending: null, replay: null, trade: null, bar: null, selection: null, reqId: 0 };
const IND_COLORS = ["#f0a93b", "#8cc2e6", "#c9a0e6", "#5cc98f", "#e6c38c", "#e68ca8"];
const TOOLS = [
  ["cursor", "Pointer", "M4 3l12 7-5 1.5L9 17z"],
  ["trend", "Trend line: click two points", "M3 16L17 4"],
  ["hline", "Horizontal level: click a price", "M2 10h16"],
  ["measure", "Measure: click a start day, then an end day", "M3 15h14M3 12v6M17 12v6M6 15l-2-1.5M14 15l2-1.5"],
];

function saveCH() {
  try { const { panel, drawer, drawerOpen, symbol, tf, basis, style, log, indicators, compare, formula } = CH; localStorage.setItem("qb-chart", JSON.stringify({ panel, drawer, drawerOpen, symbol, tf, basis, style, log, indicators, compare, formula })); } catch (e) { /* storage blocked */ }
}
const icon = (d) => `<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><path d="${d}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const f2 = (v, d = 2) => (v == null ? "-" : Number(v).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }));
const sgn = (v, d = 2) => (v == null ? "-" : `${v >= 0 ? "+" : ""}${Number(v).toFixed(d)}%`);
const tone = (v) => (v == null ? "" : v >= 0 ? "good" : "bad");
const dayStr = (t) => {
  if (t == null) return null;
  if (typeof t === "string") return t;
  if (typeof t === "object" && t.year) return `${t.year}-${String(t.month).padStart(2, "0")}-${String(t.day).padStart(2, "0")}`;
  if (typeof t === "number") return new Date(t * 1000).toISOString().slice(0, 10);
  return null;
};

// ---------- page ----------
RENDER.chart = async (main) => {
  CT.catalog = CT.catalog || await api("/api/chart/indicator-catalog");
  main.innerHTML = `
  <div class="ws" id="ws">
    <div class="ws-top">
      <div class="sym-pick"><button class="btn sym-btn" id="sym-btn" type="button"></button>
        <div class="pop" id="sym-pop" hidden><input type="text" id="sym-q" placeholder="Search symbol or name" autocomplete="off"><div id="sym-list" class="pop-list"></div></div></div>
      <div class="seg" id="tf-seg">${["D", "W", "M"].map((t) => `<button type="button" data-tf="${t}" title="${{ D: "Daily", W: "Weekly", M: "Monthly" }[t]} bars">${t}</button>`).join("")}</div>
      <div class="seg" id="style-seg"><button type="button" data-style="candles">Candles</button><button type="button" data-style="line">Line</button></div>
      <select id="basis" title="Which prices to show"><option value="split">As traded</option><option value="total">Total return</option></select>
      <div class="pop-wrap"><button class="btn" id="ind-btn" type="button">+ Indicator</button><div class="pop" id="ind-pop" hidden></div></div>
      <div class="pop-wrap"><button class="btn" id="cmp-btn" type="button">Compare</button>
        <div class="pop" id="cmp-pop" hidden><p class="small muted">Symbols to overlay, each starting at 100 (with dividends).</p><input type="text" id="cmp-in" placeholder="QQQ, TLT, GLD"><div class="row" style="margin-top:8px"><button class="btn primary" id="cmp-go" type="button">Compare</button><button class="link small" id="cmp-clear" type="button">Clear</button></div></div></div>
      <form class="formula" id="fx-form" title="Chart a formula, for example SPY/TLT or (XLK-XLU)*100"><span class="faint">ƒ</span><input type="text" id="fx-in" placeholder="SPY/TLT"><button class="link small" id="fx-clear" type="button" hidden>Clear</button></form>
      <button class="btn" id="replay-btn" type="button" title="Step through history one bar at a time">Replay</button>
      <label class="check small" title="Logarithmic price scale: equal % moves look equal"><input type="checkbox" id="log-cb"> Log</label>
      <span class="grow"></span>
      <span class="badge" id="prov" tabindex="0"></span>
    </div>
    <div class="ws-bar" id="replay-bar" hidden></div>
    <div class="chips-row" id="ind-chips"></div>
    <div class="ws-body">
      <div class="rail" id="rail">${TOOLS.map(([id, label, d]) => `<button type="button" data-tool="${id}" title="${label}" aria-label="${label}">${icon(d)}</button>`).join("")}
        <button type="button" id="clear-draw" title="Remove drawings on this symbol" aria-label="Remove drawings">${icon("M5 6h10M8 6V4h4v2M6 6l1 11h6l1-11")}</button></div>
      <div class="chart-wrap"><div id="ws-chart"></div><div class="tool-hint" id="tool-hint" hidden></div><div class="ws-loading" id="ws-loading" hidden>Loading…</div></div>
      <aside class="side">
        <div class="seg side-tabs"><button type="button" data-panel="watchlist">Watchlist</button><button type="button" data-panel="details">Details</button></div>
        <div id="side-body" class="side-body"></div>
      </aside>
    </div>
    <div class="drawer ${CH.drawerOpen ? "" : "closed"}" id="drawer">
      <div class="drawer-tabs"><div class="seg">${[["trades", "Backtest trades"], ["selection", "Selection"], ["data", "Data"]].map(([k, l]) => `<button type="button" data-drawer="${k}">${l}</button>`).join("")}</div>
        <span class="grow"></span><button class="link small" id="explain-btn" type="button">Explain this chart</button><button class="link small" id="drawer-toggle" type="button"></button></div>
      <div class="drawer-body" id="drawer-body"></div>
    </div>
  </div>`;
  document.body.classList.add("wide");
  wireToolbar();
  buildChart();
  paintControls();
  renderSide();
  renderDrawer();
  await loadAll();
  if (window.pendingReplay) {  // opened from the Lab's "Show on chart"
    const id = window.pendingReplay;
    window.pendingReplay = null;
    CH.drawer = "trades"; CH.drawerOpen = true; saveCH(); $("#drawer").classList.remove("closed"); paintControls();
    await enterTradeReplay(id);
  }
};

function paintControls() {
  document.querySelectorAll("#tf-seg button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.tf === CH.tf));
  document.querySelectorAll("#style-seg button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.style === CH.style));
  document.querySelectorAll("[data-panel]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.panel === CH.panel));
  document.querySelectorAll("[data-drawer]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.drawer === CH.drawer));
  document.querySelectorAll("[data-tool]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.tool === CT.tool));
  $("#basis").value = CH.basis;
  $("#log-cb").checked = CH.log;
  $("#fx-in").value = CH.formula;
  $("#fx-clear").hidden = !CH.formula;
  $("#cmp-btn").textContent = CH.compare.length ? `Compare (${CH.compare.length})` : "Compare";
  $("#drawer-toggle").textContent = CH.drawerOpen ? "Hide panel" : "Show panel";
  const blind = CT.bar?.blind;
  $("#sym-btn").innerHTML = CT.replay ? `${esc(CT.replay.symbol)} <span class="faint">${esc(CT.replay.card_id)} ${esc(CT.replay.phase === "held_out" ? "held-out" : "in-sample")} replay</span>`
    : blind ? "Mystery chart" : CH.formula ? `ƒ ${esc(CH.formula)}` : CH.compare.length ? `${esc(CH.symbol)} vs ${esc(CH.compare.join(", "))}`
    : `${esc(CH.symbol)} <span class="faint">${esc(CT.watch?.symbols.find((s) => s.symbol === CH.symbol)?.name || "")}</span> ▾`;
  chips();
}

function chips() {
  const box = $("#ind-chips");
  if (CT.replay) { box.innerHTML = `<span class="chip-ind">Showing the backtest's own indicators: RSI(2), SMA(200) filter, SMA(5) exit</span>`; return; }
  box.innerHTML = CH.indicators.map((s) => {
    const meta = CT.catalog[s.kind];
    return `<span class="chip-ind" title="${esc(meta.about)}">${esc(meta.label)}(${esc(Object.values(s.params).join(", "))})${meta.engine ? `<span class="eng" title="Same code as the backtest engine">engine</span>` : ""}
      <button type="button" class="link" data-edit-ind="${esc(s.id)}" aria-label="Settings">settings</button><button type="button" class="link" data-del-ind="${esc(s.id)}" aria-label="Remove">✕</button></span>`;
  }).join("") + (CH.indicators.length ? "" : `<span class="faint small">No indicators. Add one with + Indicator.</span>`);
  box.querySelectorAll("[data-del-ind]").forEach((b) => (b.onclick = () => { CH.indicators = CH.indicators.filter((x) => x.id !== b.dataset.delInd); saveCH(); loadAll(); }));
  box.querySelectorAll("[data-edit-ind]").forEach((b) => (b.onclick = () => editIndicator(b.dataset.editInd, b)));
}

function editIndicator(id, anchor) {
  const s = CH.indicators.find((x) => x.id === id);
  const pop = document.createElement("div");
  pop.className = "pop inline-pop";
  pop.innerHTML = `${Object.entries(s.params).map(([k, v]) => `<label class="field">${esc(k)}<input type="number" step="any" data-p="${esc(k)}" value="${esc(v)}"></label>`).join("")}
    <div class="row" style="margin-top:8px"><button class="btn primary" type="button">Apply</button><span class="error small"></span></div>`;
  anchor.closest(".chip-ind").append(pop);
  pop.querySelector("input").focus();
  const apply = async () => {
    const params = {};
    pop.querySelectorAll("[data-p]").forEach((i) => (params[i.dataset.p] = Number(i.value)));
    const old = s.params; s.params = params;
    try { await loadIndicators(); saveCH(); chips(); } catch (e) { s.params = old; pop.querySelector(".error").textContent = e.message; }
  };
  pop.querySelector("button").onclick = apply;
  pop.addEventListener("keydown", (e) => { if (e.key === "Enter") apply(); if (e.key === "Escape") pop.remove(); });
}

function wireToolbar() {
  const toggle = (id) => { document.querySelectorAll(".pop:not(.inline-pop)").forEach((p) => { if (p.id !== id) p.hidden = true; }); const p = $(`#${id}`); p.hidden = !p.hidden; return !p.hidden; };
  document.addEventListener("click", closePops);
  $("#sym-btn").onclick = (e) => { e.stopPropagation(); if (CT.replay) return; if (toggle("sym-pop")) { $("#sym-q").value = ""; symList(""); $("#sym-q").focus(); } };
  $("#sym-q").oninput = (e) => symList(e.target.value);
  $("#sym-q").onkeydown = (e) => { if (e.key === "Enter") { const first = $("#sym-list [data-sym]"); if (first) first.click(); } };
  $("#sym-pop").onclick = (e) => e.stopPropagation();
  document.querySelectorAll("[data-tf]").forEach((b) => (b.onclick = () => { CH.tf = b.dataset.tf; saveCH(); loadAll(); }));
  document.querySelectorAll("[data-style]").forEach((b) => (b.onclick = () => { CH.style = b.dataset.style; saveCH(); buildChart(); loadAll(); }));
  $("#basis").onchange = (e) => { CH.basis = e.target.value; saveCH(); loadAll(); };
  $("#log-cb").onchange = (e) => { CH.log = e.target.checked; saveCH(); CT.chart.applyOptions({ rightPriceScale: { mode: CH.log ? LW.PriceScaleMode.Logarithmic : LW.PriceScaleMode.Normal } }); };
  $("#ind-btn").onclick = (e) => {
    e.stopPropagation();
    if (!toggle("ind-pop")) return;
    $("#ind-pop").innerHTML = `<p class="small muted" style="margin:0 0 6px">Click to add. "engine" means it's the same code the backtests use.</p>` + Object.entries(CT.catalog).map(([k, m]) =>
      `<button type="button" class="pop-item" data-add-ind="${k}"><b>${esc(m.label)}</b>${m.engine ? ` <span class="eng">engine</span>` : ""}<br><span class="small muted">${esc(m.about)}</span></button>`).join("");
    $("#ind-pop").onclick = (ev) => ev.stopPropagation();
    $("#ind-pop").querySelectorAll("[data-add-ind]").forEach((b) => (b.onclick = () => {
      const kind = b.dataset.addInd;
      CH.indicators.push({ id: "i" + Date.now().toString(36), kind, params: { ...CT.catalog[kind].params } });
      saveCH(); $("#ind-pop").hidden = true; loadAll();
    }));
  };
  $("#cmp-btn").onclick = (e) => { e.stopPropagation(); if (toggle("cmp-pop")) { $("#cmp-in").value = CH.compare.join(", "); $("#cmp-in").focus(); } };
  $("#cmp-pop").onclick = (e) => e.stopPropagation();
  const doCompare = () => { CH.compare = $("#cmp-in").value.toUpperCase().split(/[\s,]+/).filter((s) => s && s !== CH.symbol).slice(0, 4); CH.formula = ""; saveCH(); $("#cmp-pop").hidden = true; loadAll(); };
  $("#cmp-go").onclick = doCompare;
  $("#cmp-in").onkeydown = (e) => { if (e.key === "Enter") doCompare(); };
  $("#cmp-clear").onclick = () => { CH.compare = []; saveCH(); $("#cmp-pop").hidden = true; loadAll(); };
  $("#fx-form").onsubmit = (e) => { e.preventDefault(); CH.formula = $("#fx-in").value.trim().toUpperCase(); CH.compare = []; saveCH(); loadAll(); };
  $("#fx-clear").onclick = () => { CH.formula = ""; saveCH(); loadAll(); };
  $("#replay-btn").onclick = () => (CT.bar ? stopBarReplay() : startBarReplay());
  document.querySelectorAll("[data-tool]").forEach((b) => (b.onclick = () => setTool(b.dataset.tool)));
  $("#clear-draw").onclick = async () => { await api(`/api/drawings?symbol=${encodeURIComponent(CH.symbol)}`, { method: "DELETE" }); await loadDrawings(); toast("Drawings removed."); };
  document.querySelectorAll("[data-panel]").forEach((b) => (b.onclick = () => { CH.panel = b.dataset.panel; saveCH(); paintControls(); renderSide(); }));
  document.querySelectorAll("[data-drawer]").forEach((b) => (b.onclick = () => { CH.drawer = b.dataset.drawer; CH.drawerOpen = true; saveCH(); $("#drawer").classList.remove("closed"); paintControls(); renderDrawer(); }));
  $("#drawer-toggle").onclick = () => { CH.drawerOpen = !CH.drawerOpen; saveCH(); $("#drawer").classList.toggle("closed", !CH.drawerOpen); paintControls(); };
  $("#explain-btn").onclick = explainChart;
}
function closePops(e) {
  if (!document.body.contains($("#ws"))) { document.removeEventListener("click", closePops); return; }
  if (!e.target.closest(".pop, .sym-pick, .pop-wrap")) document.querySelectorAll(".pop:not(.inline-pop)").forEach((p) => (p.hidden = true));
  if (!e.target.closest(".chip-ind")) document.querySelectorAll(".inline-pop").forEach((p) => p.remove());
}
function symList(q) {
  const ql = q.trim().toLowerCase();
  const rows = (CT.watch?.symbols || []).filter((s) => s.available && (!ql || s.symbol.toLowerCase().includes(ql) || s.name.toLowerCase().includes(ql)));
  $("#sym-list").innerHTML = rows.map((s) => `<button type="button" class="pop-item row-item" data-sym="${esc(s.symbol)}"><b>${esc(s.symbol)}</b><span class="muted small">${esc(s.name)}</span><span class="faint small">${esc(s.group)}</span></button>`).join("") || `<p class="muted small">No match in the starter list.</p>`;
  $("#sym-list").querySelectorAll("[data-sym]").forEach((b) => (b.onclick = () => { $("#sym-pop").hidden = true; setSymbol(b.dataset.sym); }));
}
function setSymbol(sym) {
  CH.symbol = sym; CH.formula = ""; CH.compare = CH.compare.filter((s) => s !== sym); CT.selection = null; saveCH();
  loadAll();
}

// ---------- chart ----------
const CHART_THEME = () => ({
  layout: { background: { color: "#151a18" }, textColor: "#9aa39c", fontFamily: "Segoe UI, system-ui, sans-serif", fontSize: 12,
    panes: { separatorColor: "#27302b", separatorHoverColor: "#3a463f", enableResize: true } },
  grid: { vertLines: { color: "#1b221e" }, horzLines: { color: "#1b221e" } },
  rightPriceScale: { borderColor: "#27302b", mode: CH.log ? LW.PriceScaleMode.Logarithmic : LW.PriceScaleMode.Normal },
  timeScale: { borderColor: "#27302b", rightOffset: 6 },
  crosshair: { mode: LW.CrosshairMode.Normal },
  autoSize: true,
});

function buildChart() {
  if (CT.chart) { try { CT.chart.remove(); } catch (e) { /* gone */ } }
  const el = $("#ws-chart");
  CT.chart = LW.createChart(el, CHART_THEME());
  charts.push(CT.chart);
  CT.main = null; CT.volume = null; CT.overlays = []; CT.markers = null; CT.drawings = [];
  CT.chart.subscribeCrosshairMove(onCrosshair);
  // Native clicks, converted to chart coordinates: the library drops a second click
  // that lands within its double-click window, which made quick two-point tools flaky.
  el.addEventListener("click", (ev) => {
    if (!CT.chart || !CT.main) return;
    const r = el.getBoundingClientRect();
    const x = ev.clientX - r.left, y = ev.clientY - r.top;
    let top = 0, pane0 = r.height;
    try { pane0 = CT.chart.panes()[0].getHeight(); } catch (e) { /* single pane */ }
    onChartClick({ point: { x, y }, time: CT.chart.timeScale().coordinateToTime(x), inMainPane: y >= top && y <= pane0 });
  });
}

function clearSeries() {
  for (const s of [CT.main, CT.volume, ...CT.overlays, ...CT.drawings.map((d) => d.series).filter(Boolean)]) {
    if (s) { try { CT.chart.removeSeries(s); } catch (e) { /* already removed */ } }
  }
  CT.main = null; CT.volume = null; CT.overlays = []; CT.markers = null; CT.drawings = [];
  // drop empty lower panes left behind by removed indicators
  try { const panes = CT.chart.panes(); for (let i = panes.length - 1; i > 0; i--) CT.chart.removePane(i); } catch (e) { /* older API */ }
}

function mainSeries(kind) {
  if (kind === "candles") return CT.chart.addSeries(LW.CandlestickSeries, { upColor: "#5cc98f", downColor: "#ef6b6b", borderVisible: false, wickUpColor: "#5cc98f", wickDownColor: "#ef6b6b" });
  return CT.chart.addSeries(LW.LineSeries, { color: "#f0a93b", lineWidth: 2 });
}

function loading(on) { const l = $("#ws-loading"); if (l) l.hidden = !on; }

async function loadAll() {
  const req = ++CT.reqId;
  paintControls();
  loading(true);
  try {
    if (!CT.watch) CT.watch = await api("/api/chart/watchlist");
    if (CT.replay) { drawReplay(); return; }
    clearSeries();
    CT.chart.applyOptions({ timeScale: { visible: !CT.bar?.blind }, rightPriceScale: { visible: !CT.bar?.blind } });
    if (CH.formula) await loadFormula(req);
    else if (CH.compare.length) await loadCompare(req);
    else await loadSymbol(req);
    if (req !== CT.reqId) return;
    renderSide();
    renderDrawer();
  } catch (e) {
    toast(e.message, "bad");
    if (CH.formula) { CH.formula = ""; saveCH(); }
  } finally { if (req === CT.reqId) loading(false); paintControls(); }
}

async function loadSymbol(req) {
  const d = await api(`/api/chart/bars?symbol=${encodeURIComponent(CH.symbol)}&tf=${CH.tf}&basis=${CH.basis}`);
  if (req !== CT.reqId) return;
  CT.data = d;
  CT.main = mainSeries(CH.style);
  const bars = CT.bar ? replayWindow(d.bars) : d.bars;
  CT.main.setData(CH.style === "candles" ? bars : bars.map((b) => ({ time: b.time, value: b.close })));
  CT.volume = CT.chart.addSeries(LW.HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "vol", lastValueVisible: false, priceLineVisible: false });
  CT.chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
  CT.volume.setData(bars.map((b) => ({ time: b.time, value: b.volume, color: b.close >= b.open ? "rgba(92,201,143,0.25)" : "rgba(239,107,107,0.25)" })));
  prov(d.provenance, d.basis_label);
  await loadIndicators(req);
  if (!CT.bar) await loadDrawings();
  if (!CT.bar) CT.chart.timeScale().fitContent();
  if (CT.bar) { if (CT.bar.blind) CT.chart.timeScale().fitContent(); else CT.chart.timeScale().scrollToRealTime(); }
}

async function loadIndicators(req = CT.reqId) {
  if (!CT.main || !CT.data) return;
  for (const s of CT.overlays) { try { CT.chart.removeSeries(s); } catch (e) { /* gone */ } }
  CT.overlays = [];
  try { const panes = CT.chart.panes(); for (let i = panes.length - 1; i > 0; i--) CT.chart.removePane(i); } catch (e) { /* older API */ }
  if (!CH.indicators.length) { CT.ind = []; return; }
  const res = await send("/api/chart/indicators", { symbol: CH.symbol, tf: CH.tf, basis: CH.basis, specs: CH.indicators });
  if (req !== CT.reqId) return;
  CT.ind = res;
  let pane = 0, color = 0;
  const cut = CT.bar ? CT.data.bars[CT.bar.index].time : null;
  const first = CT.bar ? replayWindow(CT.data.bars)[0]?.time : null;
  for (const r of res) {
    const own = r.pane === "own";
    const p = own ? ++pane : 0;
    for (const [name, pts] of Object.entries(r.lines)) {
      const data = cut ? pts.filter((x) => x.time <= cut && (!first || x.time >= first)) : pts;
      const c = IND_COLORS[color++ % IND_COLORS.length];
      const s = name === "histogram"
        ? CT.chart.addSeries(LW.HistogramSeries, { color: "rgba(140,194,230,0.45)", priceLineVisible: false, lastValueVisible: false }, p)
        : CT.chart.addSeries(LW.LineSeries, { color: c, lineWidth: name === "middle" || name === "signal" ? 1 : 2, lineStyle: name === "upper" || name === "lower" ? 2 : 0, priceLineVisible: false, lastValueVisible: own, title: own ? r.name : "" }, p);
      s.setData(data);
      s._qb = { ind: r.id, line: name, label: r.name, multi: Object.keys(r.lines).length > 1 };
      for (const lvl of r.levels || []) s.createPriceLine({ price: lvl, color: "#3a463f", lineWidth: 1, lineStyle: 2, axisLabelVisible: false });
      CT.overlays.push(s);
    }
  }
  try { CT.chart.panes().forEach((pn, i) => pn.setStretchFactor(i === 0 ? 3 : 1)); } catch (e) { /* older API */ }
}

async function loadCompare(req) {
  const syms = [CH.symbol, ...CH.compare];
  const d = await api(`/api/chart/compare?symbols=${encodeURIComponent(syms.join(","))}&tf=${CH.tf}`);
  if (req !== CT.reqId) return;
  const start = d.series.map((s) => s.points[0]?.time).filter(Boolean).sort().pop();
  const again = start ? await api(`/api/chart/compare?symbols=${encodeURIComponent(syms.join(","))}&tf=${CH.tf}&start=${start}`) : d;
  if (req !== CT.reqId) return;
  CT.data = { compare: again, bars: [] };
  again.series.forEach((s, i) => {
    const line = CT.chart.addSeries(LW.LineSeries, { color: IND_COLORS[i % IND_COLORS.length], lineWidth: 2, title: s.symbol });
    line.setData(s.points);
    if (i === 0) CT.main = line; else CT.overlays.push(line);
  });
  prov(null, `Each line starts at 100 on ${start}, dividends included`);
  CT.chart.timeScale().fitContent();
}

async function loadFormula(req) {
  const d = await api(`/api/chart/formula?f=${encodeURIComponent(CH.formula)}&tf=${CH.tf}&basis=${CH.basis}`);
  if (req !== CT.reqId) return;
  CT.data = { formula: d, bars: [] };
  CT.main = CT.chart.addSeries(LW.LineSeries, { color: "#f0a93b", lineWidth: 2, title: d.formula });
  CT.main.setData(d.points);
  prov(d.provenance[0], `Formula on ${d.provenance.length} datasets, ${d.first} to ${d.last}`);
  CT.chart.timeScale().fitContent();
}

function prov(p, extra) {
  const el = $("#prov");
  if (!el) return;
  if (CT.bar?.blind) { el.innerHTML = "<span>Source hidden in blind mode</span>"; el.title = ""; return; }
  if (!p) { el.innerHTML = `<span>${esc(extra || "")}</span>`; el.title = ""; return; }
  const age = Math.round((Date.now() - new Date(p.last_date).getTime()) / 86400000);
  el.innerHTML = `<span class="dot-src"></span>${esc(p.source === "yfinance" ? "Yahoo Finance" : p.source)} · ${esc(p.freshness)} · ${esc(p.last_date)}${age > 5 ? ` <span class="warn">(${age} days old)</span>` : ""}`;
  el.title = `${extra ? extra + "\n" : ""}Dataset ${p.dataset_id}\nDownloaded ${p.downloaded_at}\n${p.terms}`;
}

// ---------- drawings, measure ----------
function setTool(t) {
  CT.tool = t; CT.pending = null;
  const hint = { trend: "Click the first point of the line.", hline: "Click a price to mark a level.", measure: "Click the start day." }[t];
  const h = $("#tool-hint"); h.hidden = !hint; h.textContent = hint || "";
  paintControls();
}
async function loadDrawings() {
  for (const d of CT.drawings) { try { if (d.series) CT.chart.removeSeries(d.series); if (d.line) CT.main.removePriceLine(d.line); } catch (e) { /* gone */ } }
  CT.drawings = [];
  if (!CT.main || CH.formula || CH.compare.length || CT.replay) return;
  const list = await api(`/api/drawings?symbol=${encodeURIComponent(CH.symbol)}`);
  for (const d of list) drawOne(d);
}
function drawOne(d) {
  if (d.kind === "hline") {
    CT.drawings.push({ id: d.id, line: CT.main.createPriceLine({ price: d.price, color: "#8cc2e6", lineWidth: 1, lineStyle: 0, axisLabelVisible: true, title: "level" }) });
  } else if (d.kind === "trend" && d.points?.length === 2) {
    const pts = [...d.points].sort((a, b) => (a.time < b.time ? -1 : 1));
    if (pts[0].time === pts[1].time) return;
    const s = CT.chart.addSeries(LW.LineSeries, { color: "#8cc2e6", lineWidth: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    s.setData(pts);
    CT.drawings.push({ id: d.id, series: s });
  }
}
async function onChartClick(param) {
  if (CT.tool === "cursor" || !param.point || !CT.main) return;
  const price = param.inMainPane === false ? null : CT.main.coordinateToPrice(param.point.y);
  const time = dayStr(param.time);
  const hint = $("#tool-hint");
  if (CT.tool === "hline" && price != null) {
    if (CH.formula || CH.compare.length || CT.replay) { toast("Drawings work on a single symbol chart."); return; }
    const r = await send("/api/drawings", { symbol: CH.symbol, kind: "hline", price });
    drawOne({ id: r.id, kind: "hline", price }); setTool("cursor");
  } else if (CT.tool === "trend" && time && price != null) {
    if (CH.formula || CH.compare.length || CT.replay) { toast("Drawings work on a single symbol chart."); return; }
    if (!CT.pending) { CT.pending = { time, value: price }; hint.textContent = "Now click the second point."; return; }
    const pts = [CT.pending, { time, value: price }];
    const r = await send("/api/drawings", { symbol: CH.symbol, kind: "trend", points: pts });
    drawOne({ id: r.id, kind: "trend", points: pts }); setTool("cursor");
  } else if (CT.tool === "measure" && time) {
    if (!CT.pending) { CT.pending = { time }; hint.textContent = "Now click the end day."; return; }
    const sym = CT.replay ? CT.replay.symbol : CH.symbol;
    const [a, b] = [CT.pending.time, time].sort();
    setTool("cursor");
    try {
      CT.selection = await api(`/api/chart/stats?symbol=${encodeURIComponent(sym)}&start=${a}&end=${b}`);
      CH.drawer = "selection"; CH.drawerOpen = true; $("#drawer").classList.remove("closed"); saveCH(); paintControls(); renderDrawer();
    } catch (e) { toast(e.message, "bad"); }
  }
}

// ---------- crosshair data window ----------
let lastCross = null;
function onCrosshair(param) {
  lastCross = param;
  if (CH.panel === "details") renderDetails(param);
}
function renderDetails(param = lastCross) {
  const body = $("#side-body");
  if (!body || CH.panel !== "details") return;
  const blind = CT.bar?.blind;
  let rows = "";
  let time = dayStr(param?.time);
  if (CT.main && param?.seriesData) {
    const m = param.seriesData.get(CT.main);
    if (m) {
      if (m.open != null) rows += [["Open", m.open], ["High", m.high], ["Low", m.low], ["Close", m.close]].map(([k, v]) => `<tr><td>${k}</td><td class="num">${blind ? "hidden" : f2(v)}</td></tr>`).join("");
      else rows += `<tr><td>Value</td><td class="num">${f2(m.value, 4)}</td></tr>`;
    }
    if (CT.volume) { const v = param.seriesData.get(CT.volume); if (v) rows += `<tr><td>Volume</td><td class="num">${Number(v.value).toLocaleString()}</td></tr>`; }
    for (const s of CT.overlays) { const v = param.seriesData.get(s); if (v && v.value != null) rows += `<tr><td>${esc(s._qb?.label || "")}${s._qb?.multi ? " " + esc(s._qb.line) : ""}</td><td class="num">${f2(v.value)}</td></tr>`; }
  }
  const p = CT.data?.provenance;
  body.innerHTML = `<p class="faint small" style="margin:0 0 6px">Move over the chart to read exact values.</p>
    <h3 style="margin:0 0 6px">${blind ? "Date hidden (blind replay)" : esc(time || "Hover a bar")}</h3>
    <table class="dw">${rows || `<tr><td class="muted">No bar under the cursor.</td></tr>`}</table>
    ${p && !blind ? `<h3 style="margin:16px 0 4px">Where this data comes from</h3><p class="small muted" style="margin:0">${esc(p.source === "yfinance" ? "Yahoo Finance" : p.source)}, end of day, last bar ${esc(p.last_date)}. Price basis: ${esc(CT.data.basis_label || "")}.</p><p class="small faint">${esc(p.terms)}<br>Dataset ${esc(p.dataset_id)}</p>` : ""}`;
}

// ---------- side panel ----------
function renderSide() {
  const body = $("#side-body");
  if (!body) return;
  if (CH.panel === "details") return renderDetails();
  if (CT.bar?.blind) { body.innerHTML = `<p class="muted small">The watchlist is hidden during blind replay, so it can't give the answer away.</p>`; return; }
  const w = CT.watch;
  if (!w) { body.innerHTML = `<p class="faint">Loading…</p>`; return; }
  const groups = {};
  w.symbols.filter((s) => s.available).forEach((s) => (groups[s.group] = groups[s.group] || []).push(s));
  body.innerHTML = Object.entries(groups).map(([g, rows]) => `<div class="wl-group">${esc(g)}</div>` + rows.map((s) =>
    `<button type="button" class="wl-row ${s.symbol === CH.symbol && !CH.formula && !CT.replay ? "on" : ""}" data-wl="${esc(s.symbol)}" title="${esc(s.name)}"><span class="wl-sym">${esc(s.symbol)}</span><span class="num">${f2(s.last)}</span><span class="num ${tone(s.change_pct)}">${sgn(s.change_pct)}</span></button>`).join("")).join("")
    + `<p class="faint small" style="margin-top:10px">End-of-day prices from Yahoo Finance, personal use. ${esc(w.note || "")}</p>`;
  body.querySelectorAll("[data-wl]").forEach((b) => (b.onclick = () => { if (CT.replay) leaveTradeReplay(); setSymbol(b.dataset.wl); }));
}

// ---------- drawer ----------
function renderDrawer() {
  const body = $("#drawer-body");
  if (!body) return Promise.resolve();
  if (CH.drawer === "trades") return renderTrades(body);
  if (CH.drawer === "selection") return renderSelection(body);
  return renderData(body);
}

function renderSelection(body) {
  const s = CT.selection;
  if (!s) { body.innerHTML = `<p class="muted">Pick the <b>Measure</b> tool on the left, then click a start day and an end day on the chart. You'll see what happened in between, next to the S&P 500.</p>`; return; }
  const col = (x) => x ? `<div class="sel-col"><h3>${esc(x.symbol)}</h3><div class="stats compact">
      <div><b class="${tone(x.return_pct)}">${sgn(x.return_pct)}</b><span>total return</span></div>
      <div><b class="bad">${sgn(x.max_drawdown_pct)}</b><span>worst drop inside</span></div>
      <div><b>${f2(x.volatility_pct, 1)}%</b><span>volatility (yearly)</span></div>
      <div><b>${f2(x.up_days_pct, 0)}%</b><span>of days were up</span></div></div>
      <p class="small muted">Best day ${esc(x.best_day.date)} ${sgn(x.best_day.pct)}; worst day ${esc(x.worst_day.date)} ${sgn(x.worst_day.pct)}.</p></div>` : "";
  body.innerHTML = `<p class="small muted" style="margin:0 0 8px">${esc(s.selection.from)} to ${esc(s.selection.to)}, ${esc(s.selection.days)} trading days. ${esc(s.note)}</p>
    <div class="sel-grid">${col(s.selection)}${col(s.benchmark)}</div>
    <div class="row"><button class="link small" id="sel-explain" type="button">Explain what happened in this period</button><button class="link small" id="sel-clear" type="button">Clear</button></div>`;
  $("#sel-clear").onclick = () => { CT.selection = null; renderDrawer(); };
  $("#sel-explain").onclick = () => explainChart(`What happened to ${s.selection.symbol} between ${s.selection.from} and ${s.selection.to}? Explain the numbers in plain words and what a quant would take from them.`);
}

function visibleBars() {
  const bars = CT.replay ? CT.replay.bars.map((b) => ({ time: b.date, open: b.open, high: b.high, low: b.low, close: b.close, volume: b.volume, ...(b.rsi != null ? { rsi: b.rsi } : {}) })) : (CT.data?.bars || []);
  const r = CT.chart?.timeScale().getVisibleRange();
  const inRange = r ? bars.filter((b) => b.time >= r.from && b.time <= r.to) : bars;
  const extra = {};
  if (!CT.replay) for (const ind of CT.ind || []) for (const [line, pts] of Object.entries(ind.lines)) { const key = `${ind.name}${line !== ind.kind ? " " + line : ""}`; extra[key] = new Map(pts.map((p) => [p.time, p.value])); }
  return { rows: inRange, extra };
}

function renderData(body) {
  if (CH.formula || CH.compare.length) { body.innerHTML = `<p class="muted">The data table shows one symbol's bars. Clear the formula or comparison to see it.</p>`; return; }
  const { rows, extra } = visibleBars();
  const cols = Object.keys(extra);
  const last = rows.slice(-150).reverse();
  body.innerHTML = `<div class="row" style="margin-bottom:8px"><span class="small muted">${rows.length} bars in view (showing the latest ${last.length}). Zoom or scroll the chart to change what's included.</span><span class="grow"></span><button class="btn" id="csv-btn" type="button">Download CSV</button><button class="link small" id="data-refresh" type="button">Refresh</button></div>
    <div class="table-wrap drawer-table"><table><tr><th>Date</th><th class="num">Open</th><th class="num">High</th><th class="num">Low</th><th class="num">Close</th><th class="num">Volume</th>${cols.map((c) => `<th class="num">${esc(c)}</th>`).join("")}</tr>
    ${last.map((b) => `<tr><td>${esc(b.time)}</td><td class="num">${f2(b.open)}</td><td class="num">${f2(b.high)}</td><td class="num">${f2(b.low)}</td><td class="num">${f2(b.close)}</td><td class="num">${Number(b.volume || 0).toLocaleString()}</td>${cols.map((c) => `<td class="num">${f2(extra[c].get(b.time))}</td>`).join("")}</tr>`).join("")}</table></div>`;
  $("#data-refresh").onclick = () => renderDrawer();
  $("#csv-btn").onclick = () => {
    const p = CT.replay ? { dataset_id: CT.replay.dataset_id, source: "backtest replay", last_date: "" } : CT.data?.provenance || {};
    const head = [`# ${CT.replay ? CT.replay.symbol : CH.symbol} ${CH.tf} bars, ${CT.replay ? "replay prices (dividend-adjusted)" : CT.data?.basis_label || ""}`,
      `# source: ${p.source || ""}; dataset: ${p.dataset_id || ""}; exported ${new Date().toISOString()}`, "# personal use only; not investment advice"];
    const lines = [["date", "open", "high", "low", "close", "volume", ...cols].join(",")].concat(rows.map((b) => [b.time, b.open, b.high, b.low, b.close, b.volume, ...cols.map((c) => extra[c].get(b.time) ?? "")].join(",")));
    const blob = new Blob([head.join("\n") + "\n" + lines.join("\n") + "\n"], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${CT.replay ? CT.replay.symbol : CH.symbol}-${CH.tf}-${rows[0]?.time || ""}-${rows[rows.length - 1]?.time || ""}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  };
}

// ---------- trade replay (a backtest's trades on the chart) ----------
async function renderTrades(body) {
  if (!CT.replayList) CT.replayList = await api("/api/replays");
  const list = CT.replayList;
  if (!CT.replay) {
    body.innerHTML = list.length ? `<p class="muted" style="margin:0 0 8px">Put a backtest's trades on the chart. You'll see every entry and exit, and click any trade to see exactly why it fired.</p>
      <div class="replay-list">${list.map((r) => `<button type="button" class="pop-item" data-replay="${esc(r.id)}"><b>${esc(r.card_id)} rule ${esc(r.rule_id)} on ${esc(r.symbol)}</b>, ${esc(r.phase === "held_out" ? "held-out test" : "in-sample test")}<br><span class="small muted">${esc(r.trades)} trades, ${esc(r.period?.[0] || "")} to ${esc(r.period?.[1] || "")}, ${esc(r.cost_bps_per_side)} bps cost per side. ${esc(r.reference_check || "")}</span></button>`).join("")}</div>`
      : `<p class="muted">No backtest replays exported yet.</p>`;
    body.querySelectorAll("[data-replay]").forEach((b) => (b.onclick = () => enterTradeReplay(b.dataset.replay)));
    return;
  }
  const R = CT.replay;
  const sel = CT.trade;
  const rows = R.trades.map((t) => `<tr class="click ${sel && sel.number === t.number ? "sel" : ""}" data-trade="${t.number}"><td class="num">${t.number}</td><td>${esc(t.entry_date)}</td><td>${esc(t.exit_date)}</td><td class="num">${t.holding_days}</td><td class="num ${tone(t.return)}">${sgn(t.return * 100)}</td><td class="wrap small muted">${esc(t.why_entry || "")}</td></tr>`).join("");
  body.innerHTML = `<div class="row" style="margin-bottom:8px"><b>${esc(R.card_id)} rule ${esc(R.rule_id)} on ${esc(R.symbol)}, ${esc(R.phase === "held_out" ? "held-out" : "in-sample")}</b>
      <span class="small muted">${R.trades.length} trades. ${esc(R.execution || "")}. ${esc(R.note || "")}</span><span class="grow"></span><button class="btn" id="leave-replay" type="button">Close replay</button></div>
    <div class="trade-split"><div class="table-wrap drawer-table"><table><tr><th class="num">#</th><th>Entry</th><th>Exit</th><th class="num">Days</th><th class="num">Return</th><th>Why it entered</th></tr>${rows}</table></div>
    <div id="trade-card" class="trade-card">${sel ? tradeCard(sel) : `<p class="muted small">Click a trade to jump to it and see the numbers that made the rule fire.</p>`}</div></div>`;
  $("#leave-replay").onclick = leaveTradeReplay;
  body.querySelectorAll("[data-trade]").forEach((tr) => (tr.onclick = () => selectTrade(Number(tr.dataset.trade))));
  const selRow = body.querySelector("tr.sel");
  if (selRow) selRow.scrollIntoView({ block: "nearest" });
}

function tradeCard(t) {
  const R = CT.replay;
  const at = (d) => R.bars.find((b) => b.date === d) || {};
  const sig = at(t.signal_date), xs = at(t.exit_signal_date);
  const keys = Array.isArray(R.indicators) ? R.indicators : Object.keys(R.indicators || {});
  const label = (k) => (Array.isArray(R.indicators) ? k : R.indicators[k] || k);
  const ind = (b) => keys.map((k) => `<tr><td>${esc(label(k))}</td><td class="num">${f2(b[k], 4)}</td></tr>`).join("");
  return `<h3 style="margin:0 0 4px">Trade #${t.number} <span class="${tone(t.return)}">${sgn(t.return * 100)}</span></h3>
    <p class="small"><b>Signal</b> at the close of ${esc(t.signal_date)}. ${esc(t.why_entry || "")}<br><b>Bought</b> at the next open, ${esc(t.entry_date)}, at ${f2(t.entry_price, 4)}.</p>
    <table class="dw"><tr><th colspan="2" class="small">Values on the signal day</th></tr><tr><td>close</td><td class="num">${f2(sig.close, 4)}</td></tr>${ind(sig)}</table>
    <p class="small"><b>Exit signal</b> on ${esc(t.exit_signal_date)}. ${esc(t.why_exit || "")}<br><b>Sold</b> at the next open, ${esc(t.exit_date)}, at ${f2(t.exit_price, 4)}. Held ${t.holding_days} days${t.forced_close ? ", closed by the end of the test" : ""}.</p>
    <table class="dw"><tr><th colspan="2" class="small">Values on the exit-signal day</th></tr><tr><td>close</td><td class="num">${f2(xs.close, 4)}</td></tr>${ind(xs)}</table>
    <button class="link small" id="trade-explain" type="button">Explain this trade to me</button>`;
}

async function enterTradeReplay(id) {
  loading(true);
  try {
    CT.replay = await api(`/api/replays/${encodeURIComponent(id)}`);
    if (CT.bar) stopBarReplay(true);
    CT.trade = null; CT.selection = null;
    drawReplay();
    renderDrawer(); renderSide();
  } catch (e) { toast(e.message, "bad"); } finally { loading(false); paintControls(); }
}

function drawReplay() {
  const R = CT.replay;
  clearSeries();
  CT.chart.applyOptions({ timeScale: { visible: true }, rightPriceScale: { visible: true } });
  CT.main = mainSeries("candles");
  CT.main.setData(R.bars.map((b) => ({ time: b.date, open: b.open, high: b.high, low: b.low, close: b.close })));
  const addLine = (key, color, pane, title) => {
    const s = CT.chart.addSeries(LW.LineSeries, { color, lineWidth: pane ? 2 : 1, priceLineVisible: false, lastValueVisible: !!pane, title }, pane);
    s.setData(R.bars.filter((b) => b[key] != null).map((b) => ({ time: b.date, value: b[key] })));
    s._qb = { ind: key, line: key, label: title };
    CT.overlays.push(s);
    return s;
  };
  if (R.bars.some((b) => b.sma_filter != null)) addLine("sma_filter", "#8cc2e6", 0, "trend filter SMA");
  if (R.bars.some((b) => b.sma_exit != null)) addLine("sma_exit", "#c9a0e6", 0, "exit SMA");
  if (R.bars.some((b) => b.rsi != null)) { const r = addLine("rsi", "#f0a93b", 1, "RSI"); r.createPriceLine({ price: 10, color: "#3a463f", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "" }); }
  try { CT.chart.panes().forEach((pn, i) => pn.setStretchFactor(i === 0 ? 3 : 1)); } catch (e) { /* older API */ }
  const markers = [];
  for (const t of R.trades) {
    markers.push({ time: t.entry_date, position: "belowBar", color: "#5cc98f", shape: "arrowUp", text: `#${t.number}` });
    markers.push({ time: t.exit_date, position: "aboveBar", color: t.return >= 0 ? "#5cc98f" : "#ef6b6b", shape: "arrowDown", text: "" });
  }
  markers.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
  CT.markers = LW.createSeriesMarkers(CT.main, markers);
  prov({ source: "backtest replay", freshness: "FROZEN", last_date: R.period?.[1] || "", dataset_id: R.dataset_id, downloaded_at: R.generated_at, terms: R.price_note || "", price_basis: "" }, `${R.card_id} ${R.phase}: the exact data the backtest used`);
  CT.chart.timeScale().fitContent();
  CT.data = { bars: [], provenance: null };
}

async function selectTrade(n) {
  const R = CT.replay;
  const t = R.trades.find((x) => x.number === n);
  if (!t) return;
  CT.trade = t;
  const idx = R.bars.findIndex((b) => b.date === t.signal_date);
  const end = R.bars.findIndex((b) => b.date === t.exit_date);
  const from = R.bars[Math.max(0, idx - 25)]?.date, to = R.bars[Math.min(R.bars.length - 1, (end < 0 ? idx : end) + 15)]?.date;
  if (from && to) CT.chart.timeScale().setVisibleRange({ from, to });
  await renderDrawer();
  const ex = $("#trade-explain");
  if (ex) ex.onclick = () => explainChart(`Explain trade #${t.number} of ${R.card_id} to me: why the rule bought, why it sold, and whether this trade tells us anything on its own.`);
}

function leaveTradeReplay() {
  CT.replay = null; CT.trade = null;
  loadAll();
}

// ---------- bar replay ----------
const BLIND_CONTEXT = 120;
function replayWindow(bars) {
  const B = CT.bar;
  const from = B.blind ? Math.max(0, B.start - BLIND_CONTEXT) : 0;
  return bars.slice(from, B.index + 1);
}
function startBarReplay() {
  if (CT.replay) leaveTradeReplay();
  if (CH.formula || CH.compare.length) { CH.formula = ""; CH.compare = []; saveCH(); }
  const bars = CT.data?.bars || [];
  if (!bars.length) { toast("Load a symbol first."); return; }
  const startIdx = Math.max(60, bars.length - 260);
  CT.bar = { index: startIdx, playing: false, timer: null, blind: false, speed: 400, start: startIdx };
  renderBarControls();
  loadAll();
}
function stopBarReplay(silent) {
  if (!CT.bar) return;
  clearInterval(CT.bar.timer);
  CT.bar = null;
  $("#replay-bar").hidden = true;
  $("#replay-btn").textContent = "Replay";
  if (!silent) loadAll();
}
function renderBarControls() {
  const B = CT.bar, bars = CT.data.bars;
  const el = $("#replay-bar");
  el.hidden = false;
  $("#replay-btn").textContent = "Stop replay";
  el.innerHTML = `<b>Replay</b>
    ${B.blind ? `<span class="small muted">Start date hidden</span>` : `<label class="small">Start <input type="date" id="rp-start" value="${esc(bars[B.start].time)}" min="${esc(bars[20].time)}" max="${esc(bars[bars.length - 2].time)}"></label>`}
    <button class="btn" id="rp-back" type="button" title="One bar back">◀</button>
    <button class="btn primary" id="rp-play" type="button">${B.playing ? "Pause" : "Play"}</button>
    <button class="btn" id="rp-step" type="button" title="One bar forward">▶</button>
    <select id="rp-speed">${[[800, "Slow"], [400, "Normal"], [120, "Fast"]].map(([v, l]) => `<option value="${v}" ${B.speed === v ? "selected" : ""}>${l}</option>`).join("")}</select>
    <label class="check small" title="Hides the ticker, dates and prices so hindsight can't help you"><input type="checkbox" id="rp-blind" ${B.blind ? "checked" : ""}> Blind mode</label>
    <span class="small muted" id="rp-pos"></span><span class="grow"></span>
    ${B.blind ? `<button class="btn" id="rp-reveal" type="button">Reveal</button>` : ""}`;
  const pos = () => { $("#rp-pos").textContent = B.blind ? `Bar ${B.index - B.start + 1}` : `${bars[B.index].time} (bar ${B.index - B.start + 1})`; };
  pos();
  const step = (d) => { B.index = Math.min(bars.length - 1, Math.max(B.start, B.index + d)); advance(); pos(); if (B.index >= bars.length - 1) pause(); };
  const pause = () => { B.playing = false; clearInterval(B.timer); $("#rp-play").textContent = "Play"; };
  $("#rp-step").onclick = () => step(1);
  $("#rp-back").onclick = () => step(-1);
  $("#rp-play").onclick = () => { if (B.playing) return pause(); B.playing = true; $("#rp-play").textContent = "Pause"; B.timer = setInterval(() => step(1), B.speed); };
  $("#rp-speed").onchange = (e) => { B.speed = Number(e.target.value); if (B.playing) { clearInterval(B.timer); B.timer = setInterval(() => step(1), B.speed); } };
  if ($("#rp-start")) $("#rp-start").onchange = (e) => { const i = bars.findIndex((b) => b.time >= e.target.value); if (i > 0) { B.start = i; B.index = i; pause(); loadAll(); pos(); } };
  $("#rp-blind").onchange = (e) => { B.blind = e.target.checked; renderBarControls(); loadAll(); renderSide(); };
  const rv = $("#rp-reveal");
  if (rv) rv.onclick = () => { toast(`It was ${CH.symbol}, starting ${bars[B.start].time}.`, "good"); B.blind = false; renderBarControls(); loadAll(); renderSide(); };
}
function advance() {
  // Update series in place (no full reload) so playback stays smooth and never shows a future bar.
  const B = CT.bar, bars = CT.data.bars, b = bars[B.index];
  if (!CT.main) return;
  const shown = replayWindow(bars);
  CT.main.setData(CH.style === "candles" ? shown : shown.map((x) => ({ time: x.time, value: x.close })));
  if (CT.volume) CT.volume.setData(shown.map((x) => ({ time: x.time, value: x.volume, color: x.close >= x.open ? "rgba(92,201,143,0.25)" : "rgba(239,107,107,0.25)" })));
  for (const s of CT.overlays) {
    const ind = CT.ind.find((r) => r.id === s._qb?.ind);
    const first = shown[0]?.time;
    if (ind) s.setData(ind.lines[s._qb.line].filter((p) => p.time <= b.time && p.time >= first));
  }
  if (B.blind) CT.chart.timeScale().fitContent(); else CT.chart.timeScale().scrollToRealTime();
}

// ---------- explain ----------
function explainChart(question) {
  const lines = [];
  if (CT.replay) {
    const R = CT.replay;
    lines.push(`Backtest trade replay: ${R.card_id} rule ${R.rule_id} on ${R.symbol}, ${R.phase}, ${R.trades.length} trades, ${R.cost_bps_per_side} bps per side.`, `Execution: ${R.execution}.`, `Summary: ${JSON.stringify(R.summary)}`);
    if (CT.trade) lines.push(`Selected trade: ${JSON.stringify(CT.trade)}`, `Signal-day bar: ${JSON.stringify(R.bars.find((b) => b.date === CT.trade.signal_date) || {})}`);
  } else if (CH.formula) {
    const pts = CT.data?.formula?.points || [];
    lines.push(`Formula chart ${CH.formula} (${CH.tf}), ${pts.length} points, first ${JSON.stringify(pts[0])}, last ${JSON.stringify(pts[pts.length - 1])}.`);
  } else if (CH.compare.length) {
    lines.push(`Comparison of ${[CH.symbol, ...CH.compare].join(", ")} rebased to 100: ${JSON.stringify((CT.data?.compare?.series || []).map((s) => ({ symbol: s.symbol, change_pct: s.change_pct })))}`);
  } else {
    const bars = CT.data?.bars || [];
    const last = bars[bars.length - 1];
    lines.push(`Chart of ${CH.symbol}, ${{ D: "daily", W: "weekly", M: "monthly" }[CH.tf]} bars, ${CT.data?.basis_label}.`, `Last bar: ${JSON.stringify(last)}.`,
      `Indicators on screen: ${(CT.ind || []).map((i) => { const l = Object.values(i.lines)[0]; return `${i.name} last=${l[l.length - 1]?.value}`; }).join("; ") || "none"}.`,
      `Data: ${JSON.stringify(CT.data?.provenance || {})}`);
    const r = CT.chart?.timeScale().getVisibleRange();
    if (r) { const vis = bars.filter((b) => b.time >= r.from && b.time <= r.to); if (vis.length > 1) lines.push(`Visible range ${r.from} to ${r.to}: close went from ${vis[0].close} to ${vis[vis.length - 1].close}.`); }
  }
  if (CT.selection) lines.push(`Measured selection: ${JSON.stringify(CT.selection)}`);
  state.learn.screen = lines.join("\n");
  go("learn", { question: question || "Explain what this chart is showing me in plain words, what each indicator on it means, and what a beginner should notice." });
}
