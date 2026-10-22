/* Pure Quant Brain UI state helpers. Kept dependency-free for browser and Node tests. */
"use strict";

(function initUIState(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.QBState = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function buildUIState() {
  function strictFiniteNumber(value) {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    if (typeof value !== "string" || value.trim() === "") return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function formatPrice(value, digits = 2) {
    const number = strictFiniteNumber(value);
    return number === null ? "Price unavailable" : `$${number.toFixed(digits)}`;
  }

  function formatPercentPoints(value, digits = 1) {
    const number = strictFiniteNumber(value);
    if (number === null) return "Unavailable";
    return `${number > 0 ? "+" : ""}${number.toFixed(digits)}%`;
  }

  function directionClass(value) {
    const number = strictFiniteNumber(value);
    return number === null || number === 0 ? "" : number > 0 ? "good" : "bad";
  }

  function provenanceLabel(provenance = {}) {
    const freshness = typeof provenance.freshness === "string" && provenance.freshness.trim()
      ? provenance.freshness.trim() : "Freshness unavailable";
    const source = typeof provenance.source === "string" && provenance.source.trim()
      ? provenance.source.trim() : "Source unavailable";
    const date = typeof provenance.last_date === "string" && provenance.last_date.trim()
      ? `as of ${provenance.last_date.trim()}` : "date unavailable";
    return `${freshness} · ${source} · ${date}`;
  }

  function normalizePresets(value) {
    if (Array.isArray(value)) {
      return Object.fromEntries(
        value
          .filter((preset) => preset && typeof preset.id === "string" && preset.id.trim())
          .map((preset) => [preset.id, preset])
      );
    }
    return value && typeof value === "object" ? value : {};
  }

  function filterMarketRows(rows, presetKey) {
    const source = Array.isArray(rows) ? rows : [];
    const numeric = (row, key) => strictFiniteNumber(row?.[key]);
    const filters = {
      oversold_uptrend: (row) => numeric(row, "rsi_2") !== null
        && numeric(row, "rsi_2") < 10 && row.above_sma_200 === true,
      near_high: (row) => numeric(row, "from_52w_high_pct") !== null
        && numeric(row, "from_52w_high_pct") >= -3,
      below_200: (row) => row.above_sma_200 === false,
      calm: (row) => numeric(row, "volatility_20d_pct") !== null
        && numeric(row, "volatility_20d_pct") < 15,
      deep_drawdown: (row) => numeric(row, "drawdown_from_peak_pct") !== null
        && numeric(row, "drawdown_from_peak_pct") <= -20,
    };
    return filters[presetKey] ? source.filter(filters[presetKey]) : source;
  }

  const CRYPTO_LIVE_MAX_MS = 5_000;
  const CRYPTO_DELAYED_MAX_MS = 15_000;

  function createCryptoTracker(products) {
    return {
      generation: 0,
      transport: "connecting",
      upstream: "waiting",
      lastTickAt: Object.fromEntries(products.map((product) => [product, null])),
    };
  }

  function beginCryptoConnection(tracker) {
    return {
      ...tracker,
      generation: tracker.generation + 1,
      transport: "connecting",
      upstream: "waiting",
      lastTickAt: Object.fromEntries(Object.keys(tracker.lastTickAt).map((product) => [product, null])),
    };
  }

  function applyCryptoEvent(tracker, event, now = Date.now()) {
    if (!event || event.generation !== tracker.generation) return tracker;
    if (event.kind === "open") return { ...tracker, transport: "open" };
    if (event.kind === "error") {
      return {
        ...tracker,
        transport: "disconnected",
        upstream: "error",
        lastTickAt: Object.fromEntries(
          Object.keys(tracker.lastTickAt).map((product) => [product, null])
        ),
      };
    }
    if (event.kind === "status") {
      const upstream = ["live", "paused", "gap", "error"].includes(event.state)
        ? event.state : "error";
      if (upstream !== "live") {
        return {
          ...tracker,
          upstream,
          lastTickAt: Object.fromEntries(
            Object.keys(tracker.lastTickAt).map((product) => [product, null])
          ),
        };
      }
      return { ...tracker, upstream };
    }
    if (event.kind === "ticker") {
      if (tracker.transport !== "open" || tracker.upstream !== "live") return tracker;
      if (!(event.product in tracker.lastTickAt) || strictFiniteNumber(event.price) === null) return tracker;
      return { ...tracker, lastTickAt: { ...tracker.lastTickAt, [event.product]: now } };
    }
    return tracker;
  }

  function applyNormalizedCryptoEvent(tracker, generation, event, now = Date.now()) {
    let normalized;
    if (event?.type === "transport") {
      normalized = { kind: event.status === "open" ? "open" : "error", generation };
    } else if (event?.type === "status") {
      normalized = { kind: "status", generation, state: event.state };
    } else if (event?.type === "ticker") {
      normalized = { kind: "ticker", generation, product: event.product, price: event.price };
    } else {
      normalized = { kind: "status", generation, state: "error" };
    }
    return applyCryptoEvent(tracker, normalized, now);
  }

  function cryptoDisplayState(tracker, product, now = Date.now()) {
    if (tracker.transport === "disconnected" || ["paused", "gap", "error"].includes(tracker.upstream)) {
      return "DISCONNECTED";
    }
    const tickAt = tracker.lastTickAt[product];
    if (tracker.transport !== "open" || tracker.upstream !== "live" || tickAt === null) return "WAITING";
    const age = Math.max(0, now - tickAt);
    if (age <= CRYPTO_LIVE_MAX_MS) return "LIVE";
    if (age <= CRYPTO_DELAYED_MAX_MS) return "DELAYED";
    return "STALE";
  }

  function clearCryptoProductState(productState) {
    for (const field of ["price", "bid", "ask", "change", "high", "low", "volume"]) {
      productState[field] = null;
    }
    productState.trades = [];
    productState.bids = [];
    productState.asks = [];
    return productState;
  }

  function isEditableTarget(target) {
    if (!target) return false;
    const element = target.nodeType === 3 ? target.parentElement : target;
    if (!element) return false;
    if (["INPUT", "TEXTAREA", "SELECT"].includes(element.tagName) || element.isContentEditable) {
      return true;
    }
    return typeof element.closest === "function" && Boolean(
      element.closest("input, textarea, select, [contenteditable]:not([contenteditable='false'])")
    );
  }

  function topVisibleModal(modals) {
    for (let index = modals.length - 1; index >= 0; index -= 1) {
      if (modals[index] && !modals[index].hidden) return modals[index];
    }
    return null;
  }

  function nextTrapIndex(current, count, backward = false) {
    if (count <= 0) return -1;
    if (backward) return current <= 0 ? count - 1 : current - 1;
    return current >= count - 1 ? 0 : current + 1;
  }

  return {
    CRYPTO_DELAYED_MAX_MS,
    CRYPTO_LIVE_MAX_MS,
    applyCryptoEvent,
    applyNormalizedCryptoEvent,
    beginCryptoConnection,
    clearCryptoProductState,
    createCryptoTracker,
    cryptoDisplayState,
    directionClass,
    filterMarketRows,
    formatPercentPoints,
    formatPrice,
    isEditableTarget,
    nextTrapIndex,
    normalizePresets,
    provenanceLabel,
    strictFiniteNumber,
    topVisibleModal,
  };
});
