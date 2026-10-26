"""Regression tripwires that connect tested UI helpers to the maintained cockpit code."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = (REPO / "ui/static/app.js").read_text(encoding="utf-8")


def test_market_renderers_do_not_turn_missing_values_into_zero_or_fixed_provenance():
    assert "change_1d_pct ?? 0" not in APP
    assert "change_1m_pct ?? 0" not in APP
    assert "vs_sma_200_pct ?? 0" not in APP
    assert "EOD · Yahoo" not in APP
    assert "?? 48" not in APP
    assert "?? 2" not in APP
    assert "?? 73" not in APP
    assert "UIState.formatPrice" in APP
    assert "UIState.provenanceLabel" in APP


def test_crypto_renderers_use_normalized_events_and_the_tested_state_machine():
    assert "d.product_id" not in APP
    assert "ev.product_id" not in APP
    assert "UIState.applyNormalizedCryptoEvent" in APP
    assert "UIState.cryptoDisplayState" in APP
    assert 'addEventListener("status"' in APP
    assert "event.product" in APP


def test_today_coinbase_widget_starts_unknown_and_is_hydrated_by_the_tracker():
    assert "$67,428.50" not in APP
    assert 'id="today-coinbase-status"' in APP
    assert 'id="today-btc-val"' in APP
    assert '$("#today-coinbase-status")' in APP
    assert '$("#today-btc-val")' in APP


def test_crypto_disconnects_clear_rendered_caches_and_only_accept_fresh_tickers():
    assert "UIState.clearCryptoProductState" in APP
    assert "delete tickerValues[product]" in APP
    assert "liveTracker.lastTickAt[prod] === receivedAt" in APP
    assert "tickerTracker.lastTickAt[event.product] === receivedAt" in APP


def test_cockpit_controls_expose_keyboard_and_selected_state():
    assert '<div id="today-bot-pill"' not in APP
    assert 'id="today-bot-pill"' in APP and 'type="button"' in APP
    assert 'btn.setAttribute("aria-pressed", String(name === selected))' in APP


def test_replay_fields_are_escaped_before_inner_html_rendering():
    assert "${esc(t.number)}" in APP
    assert "${esc(t.holding_days)}" in APP


def test_modal_and_shortcut_handlers_use_focus_stack_and_editable_guards():
    assert "const modalStack = []" in APP
    assert "UIState.topVisibleModal" in APP
    assert "UIState.nextTrapIndex" in APP
    assert "UIState.isEditableTarget(e.target)" in APP
    assert 'e.key === "Tab" && modal' in APP
    assert 'e.key === "Escape" && modal' in APP
    assert "if (!modal || modal.hidden) return false" in APP


def test_interactive_base_and_roaming_companion_are_wired():
    index_html = (REPO / "ui/static/index.html").read_text(encoding="utf-8")
    assert '/static/base_bots.js' in index_html
    assert 'id="roaming-companion-root"' in index_html
    assert 'id="base-floor-canvas"' in APP
    assert 'id="base-replay-run-btn"' in APP
    assert "renderRoamingCompanion" in APP
    assert 'id="master-feed-section"' in APP
    assert 'id="master-feed-list"' in APP
    assert 'id="master-feed-tabs"' in APP

