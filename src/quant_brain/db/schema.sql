-- SQLite schema for the Quant Agent Brain.
-- This database stores structured metadata and workflow state.
-- Markdown files remain the human-readable source of truth.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS notes (
    note_id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    title TEXT,
    type TEXT,
    status TEXT DEFAULT 'active',
    content_hash TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    indexed_at TEXT
);

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT UNIQUE,
    source_type TEXT NOT NULL,
    author TEXT,
    published_at TEXT,
    captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
    raw_path TEXT,
    checksum TEXT,
    trust_level TEXT DEFAULT 'unknown',
    note_id TEXT,
    FOREIGN KEY (note_id) REFERENCES notes(note_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    note_id TEXT NOT NULL,
    source_id TEXT,
    heading_path TEXT,
    text_hash TEXT NOT NULL,
    text TEXT NOT NULL,
    token_count INTEGER,
    start_line INTEGER,
    end_line INTEGER,
    embedding_status TEXT DEFAULT 'pending',
    embedding_model TEXT,
    vector_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (note_id) REFERENCES notes(note_id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(source_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS strategy_cards (
    strategy_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    method_family TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'idea',
    stage TEXT NOT NULL DEFAULT 'idea',
    confidence TEXT NOT NULL DEFAULT 'low',
    note_path TEXT NOT NULL UNIQUE,
    hypothesis TEXT,
    markets_json TEXT DEFAULT '[]',
    timeframe TEXT,
    source_ids_json TEXT DEFAULT '[]',
    backtest_ids_json TEXT DEFAULT '[]',
    review_status TEXT DEFAULT 'not_reviewed',
    paper_trade_status TEXT DEFAULT 'not_started',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_datasets (
    dataset_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    source TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    adjusted INTEGER DEFAULT 1,
    path TEXT NOT NULL,
    checksum TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backtests (
    backtest_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    dataset_id TEXT,
    code_commit TEXT,
    config_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'created',
    report_path TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategy_cards(strategy_id) ON DELETE CASCADE,
    FOREIGN KEY (dataset_id) REFERENCES price_datasets(dataset_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_id TEXT NOT NULL,
    total_return REAL,
    benchmark_return REAL,
    cagr REAL,
    sharpe REAL,
    sortino REAL,
    max_drawdown REAL,
    volatility REAL,
    calmar REAL,
    exposure REAL,
    turnover REAL,
    win_rate REAL,
    profit_factor REAL,
    number_of_trades INTEGER,
    fees REAL,
    slippage REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (backtest_id) REFERENCES backtests(backtest_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    backtest_id TEXT,
    reviewer TEXT,
    verdict TEXT NOT NULL DEFAULT 'needs_more_work',
    reasons_json TEXT DEFAULT '[]',
    note_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategy_cards(strategy_id) ON DELETE CASCADE,
    FOREIGN KEY (backtest_id) REFERENCES backtests(backtest_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS agent_tasks (
    task_id TEXT PRIMARY KEY,
    agent_role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    input_path TEXT,
    output_path TEXT,
    model TEXT,
    cost_estimate REAL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    completed_at TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS retrieval_log (
    query_id TEXT PRIMARY KEY,
    agent_id TEXT,
    task_id TEXT,
    query_text TEXT NOT NULL,
    filters_json TEXT DEFAULT '{}',
    retrieved_chunk_ids_json TEXT DEFAULT '[]',
    final_chunk_ids_json TEXT DEFAULT '[]',
    answer_hash TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES agent_tasks(task_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_notes_type ON notes(type);
CREATE INDEX IF NOT EXISTS idx_notes_status ON notes(status);
CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url);
CREATE INDEX IF NOT EXISTS idx_chunks_note_id ON chunks(note_id);
CREATE INDEX IF NOT EXISTS idx_chunks_source_id ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_strategy_family ON strategy_cards(method_family);
CREATE INDEX IF NOT EXISTS idx_strategy_status ON strategy_cards(status);
CREATE INDEX IF NOT EXISTS idx_backtests_strategy_id ON backtests(strategy_id);
CREATE INDEX IF NOT EXISTS idx_metrics_backtest_id ON metrics(backtest_id);
CREATE INDEX IF NOT EXISTS idx_reviews_strategy_id ON reviews(strategy_id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks(status);
