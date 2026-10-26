"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const UIState = require("../../ui/static/state.js");
const QBBots = require("../../ui/static/base_bots.js");

test("strictFiniteNumber accepts only finite numbers and non-blank numeric strings", () => {
  assert.equal(UIState.strictFiniteNumber(0), 0);
  assert.equal(UIState.strictFiniteNumber(-12.5), -12.5);
  assert.equal(UIState.strictFiniteNumber("765.61"), 765.61);

  for (const value of [null, undefined, true, false, "", "   ", "bad", NaN, Infinity, -Infinity]) {
    assert.equal(UIState.strictFiniteNumber(value), null, String(value));
  }
});

test("market formatters preserve zero and expose unavailable values", () => {
  assert.equal(UIState.formatPrice(0), "$0.00");
  assert.equal(UIState.formatPrice(null), "Price unavailable");
  assert.equal(UIState.formatPrice("bad"), "Price unavailable");
  assert.equal(UIState.formatPercentPoints(0, 2), "0.00%");
  assert.equal(UIState.formatPercentPoints(-1.25, 1), "-1.3%");
  assert.equal(UIState.formatPercentPoints(undefined, 2), "Unavailable");
  assert.equal(UIState.directionClass(0), "");
  assert.equal(UIState.directionClass(null), "");
  assert.equal(UIState.directionClass(2), "good");
  assert.equal(UIState.directionClass(-2), "bad");
});

test("provenanceLabel uses row provenance without fixed provider or date fallbacks", () => {
  assert.equal(
    UIState.provenanceLabel({ source: "Tiingo", freshness: "END OF DAY", last_date: "2026-09-28" }),
    "END OF DAY · Tiingo · as of 2026-09-28",
  );
  assert.equal(
    UIState.provenanceLabel({}),
    "Freshness unavailable · Source unavailable · date unavailable",
  );
});

test("market presets normalize the backend list contract by stable id", () => {
  const normalized = UIState.normalizePresets([
    { id: "oversold", title: "Oversold", why: "why", trap: "trap" },
    { id: "momentum", title: "Momentum", why: "why 2", trap: "trap 2" },
  ]);
  assert.deepEqual(Object.keys(normalized), ["oversold", "momentum"]);
  assert.equal(normalized.oversold.title, "Oversold");
  assert.deepEqual(UIState.normalizePresets({ calm: { title: "Calm" } }), {
    calm: { title: "Calm" },
  });
  assert.deepEqual(UIState.normalizePresets(null), {});
});

test("market preset filters match the backend preset identifiers", () => {
  const rows = [
    { symbol: "A", rsi_2: 5, above_sma_200: true, from_52w_high_pct: -2, volatility_20d_pct: 12, drawdown_from_peak_pct: -5 },
    { symbol: "B", rsi_2: 50, above_sma_200: false, from_52w_high_pct: -8, volatility_20d_pct: 22, drawdown_from_peak_pct: -25 },
  ];
  assert.deepEqual(UIState.filterMarketRows(rows, "oversold_uptrend").map((r) => r.symbol), ["A"]);
  assert.deepEqual(UIState.filterMarketRows(rows, "near_high").map((r) => r.symbol), ["A"]);
  assert.deepEqual(UIState.filterMarketRows(rows, "below_200").map((r) => r.symbol), ["B"]);
  assert.deepEqual(UIState.filterMarketRows(rows, "calm").map((r) => r.symbol), ["A"]);
  assert.deepEqual(UIState.filterMarketRows(rows, "deep_drawdown").map((r) => r.symbol), ["B"]);
  assert.equal(UIState.filterMarketRows(rows, "").length, 2);
});

test("crypto feed requires upstream live plus a normalized product ticker", () => {
  let tracker = UIState.createCryptoTracker(["BTC-USD", "ETH-USD"]);
  tracker = UIState.beginCryptoConnection(tracker);
  const generation = tracker.generation;

  tracker = UIState.applyCryptoEvent(tracker, { kind: "open", generation }, 1_000);
  assert.equal(UIState.cryptoDisplayState(tracker, "BTC-USD", 1_000), "WAITING");

  tracker = UIState.applyCryptoEvent(
    tracker,
    { kind: "status", generation, state: "live" },
    1_000,
  );
  assert.equal(UIState.cryptoDisplayState(tracker, "BTC-USD", 1_000), "WAITING");

  tracker = UIState.applyCryptoEvent(
    tracker,
    { kind: "ticker", generation, product: "BTC-USD", price: "83439.74" },
    1_000,
  );
  assert.equal(UIState.cryptoDisplayState(tracker, "BTC-USD", 6_000), "LIVE");
  assert.equal(UIState.cryptoDisplayState(tracker, "BTC-USD", 6_001), "DELAYED");
  assert.equal(UIState.cryptoDisplayState(tracker, "BTC-USD", 16_001), "STALE");
});

test("browser adapter consumes backend status.state and normalized product", () => {
  let tracker = UIState.beginCryptoConnection(UIState.createCryptoTracker(["BTC-USD"]));
  const generation = tracker.generation;
  tracker = UIState.applyNormalizedCryptoEvent(
    tracker, generation, { type: "transport", status: "open" }, 1_000,
  );
  tracker = UIState.applyNormalizedCryptoEvent(
    tracker, generation, { type: "status", state: "live" }, 1_000,
  );
  tracker = UIState.applyNormalizedCryptoEvent(
    tracker, generation, { type: "ticker", product: "BTC-USD", price: "100" }, 1_001,
  );
  assert.equal(UIState.cryptoDisplayState(tracker, "BTC-USD", 1_001), "LIVE");
});

test("crypto product caches clear every rendered value after feed invalidation", () => {
  const product = {
    price: 100, bid: 99, ask: 101, change: 2, high: 110, low: 90, volume: 50,
    trades: [{ price: 100 }], bids: [[99, 1]], asks: [[101, 1]],
  };
  const cleared = UIState.clearCryptoProductState(product);
  assert.equal(cleared, product);
  for (const field of ["price", "bid", "ask", "change", "high", "low", "volume"]) {
    assert.equal(cleared[field], null, field);
  }
  assert.deepEqual(cleared.trades, []);
  assert.deepEqual(cleared.bids, []);
  assert.deepEqual(cleared.asks, []);
});

test("upstream pause or transport error invalidates cached live ticks", () => {
  let tracker = UIState.beginCryptoConnection(UIState.createCryptoTracker(["BTC-USD"]));
  const generation = tracker.generation;
  tracker = UIState.applyCryptoEvent(tracker, { kind: "open", generation }, 0);
  tracker = UIState.applyCryptoEvent(tracker, { kind: "status", generation, state: "live" }, 0);
  tracker = UIState.applyCryptoEvent(
    tracker,
    { kind: "ticker", generation, product: "BTC-USD", price: 100 },
    1_000,
  );
  tracker = UIState.applyCryptoEvent(
    tracker,
    { kind: "status", generation, state: "paused" },
    1_001,
  );
  assert.equal(UIState.cryptoDisplayState(tracker, "BTC-USD", 1_002), "DISCONNECTED");
  assert.equal(tracker.lastTickAt["BTC-USD"], null);

  tracker = UIState.applyCryptoEvent(
    tracker,
    { kind: "status", generation, state: "live" },
    1_003,
  );
  assert.equal(UIState.cryptoDisplayState(tracker, "BTC-USD", 1_004), "WAITING");

  tracker = UIState.applyCryptoEvent(tracker, { kind: "error", generation }, 50_001);
  assert.equal(UIState.cryptoDisplayState(tracker, "BTC-USD", 50_002), "DISCONNECTED");
  assert.equal(tracker.lastTickAt["BTC-USD"], null);
});

test("stale EventSource generations cannot change a newer connection", () => {
  let tracker = UIState.beginCryptoConnection(UIState.createCryptoTracker(["BTC-USD"]));
  const oldGeneration = tracker.generation;
  tracker = UIState.beginCryptoConnection(tracker);
  const currentGeneration = tracker.generation;

  tracker = UIState.applyCryptoEvent(
    tracker,
    { kind: "status", generation: oldGeneration, state: "live" },
    1_000,
  );
  tracker = UIState.applyCryptoEvent(
    tracker,
    { kind: "ticker", generation: oldGeneration, product: "BTC-USD", price: 100 },
    1_000,
  );
  assert.equal(tracker.generation, currentGeneration);
  assert.equal(UIState.cryptoDisplayState(tracker, "BTC-USD", 1_000), "WAITING");
});

test("editable targets include descendants of editable hosts", () => {
  assert.equal(UIState.isEditableTarget({ tagName: "INPUT", isContentEditable: false }), true);
  assert.equal(UIState.isEditableTarget({ tagName: "BUTTON", isContentEditable: false }), false);
  assert.equal(UIState.isEditableTarget({
    tagName: "SPAN",
    isContentEditable: false,
    closest: () => ({ tagName: "DIV" }),
  }), true);
});

test("modal helpers select the topmost visible dialog and wrap focus", () => {
  const first = { hidden: false };
  const second = { hidden: true };
  const third = { hidden: false };
  assert.equal(UIState.topVisibleModal([first, second, third]), third);
  assert.equal(UIState.nextTrapIndex(0, 3, true), 2);
  assert.equal(UIState.nextTrapIndex(2, 3, false), 0);
  assert.equal(UIState.nextTrapIndex(1, 3, false), 2);
});

test("visual bot engine maps stages to stations and derives honest bot states", () => {
  assert.equal(QBBots.mapStageToStation("qwen_validation", "research_scout"), "validator_gate");
  assert.equal(QBBots.mapStageToStation("curation", "knowledge_curator"), "library_rag");
  assert.equal(QBBots.mapStageToStation("backtest", "runner"), "backtest_pit");
  assert.equal(QBBots.mapStageToStation("review", "reviewer"), "review_tribunal");

  const states = QBBots.deriveInitialBotStates({
    counts: { sources: 7, price_datasets: 3, strategy_cards: 2, backtests: 73 },
    runs: [{ run_id: "RUN-1", title: "Research run", status: "failed", outcome: "Stopped.", reason: "validation", phases: [{ stage: "qwen_validation", ok: 1, failed: 2 }] }],
    lab: {
      cards: [{ strategy_id: "SC-0002", status: "frozen" }],
      backtests: [{ config: { phase: "held_out", kind: "rule" } }],
      reviews: [{ strategy_id: "SC-0002", verdict: "reject", verdict_text: "reject: no edge" }],
    },
  });

  assert.equal(states.scout.mood, "alert");
  assert.equal(states.validator.mood, "alert");
  assert.equal(states.backtester.mood, "happy");
  assert.equal(states.reviewer.mood, "alert");

  const steps = QBBots.buildReplayStepsFromEvents([
    { event_id: 1, run_id: "RUN-1", agent_role: "research_scout", stage: "discovery", status: "running", event_type: "start", message: "Starting discovery" },
    { event_id: 2, run_id: "RUN-1", agent_role: "research_scout", stage: "qwen_validation", status: "failed", event_type: "fail", message: "Validation failed" },
  ]);
  assert.equal(steps.length, 2);
  assert.equal(steps[0].botId, "scout");
  assert.equal(steps[1].botId, "validator");
  assert.equal(steps[1].stationId, "validator_gate");

  for (const style of ["droid", "pixel", "geometric"]) {
    const svg = QBBots.botAvatarSvg(style, "#38bdf8", "happy");
    assert.ok(svg.includes("<svg"), style);
  }
});
