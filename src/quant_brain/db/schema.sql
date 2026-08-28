-- SQLite schema for the Quant Agent Brain.
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

CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id TEXT NOT NULL,
    model TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    vector_json TEXT NOT NULL,
    vector_norm REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (chunk_id, model),
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS research_questions (
    research_id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    method_family TEXT,
    priority INTEGER NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'queued',
    assigned_agent TEXT DEFAULT 'research_scout',
    raw_note_path TEXT,
    source_note_path TEXT,
    curator_note_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS research_findings (
    finding_id TEXT PRIMARY KEY,
    research_id TEXT NOT NULL,
    source_id TEXT,
    claim TEXT NOT NULL,
    evidence TEXT,
    confidence TEXT DEFAULT 'low',
    status TEXT DEFAULT 'raw',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (research_id) REFERENCES research_questions(research_id) ON DELETE CASCADE,
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

-- Ordered event log for harness dispatches and multi-stage agent runs.
-- No foreign key on task_id: events must be recordable for runs whose task rows
-- do not exist yet (and for ad-hoc task ids), even with foreign_keys = ON.
CREATE TABLE IF NOT EXISTS agent_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    task_id TEXT,
    agent_role TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT,
    payload_json TEXT DEFAULT '{}',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_events_run ON agent_events(run_id, event_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_task ON agent_events(task_id);

CREATE INDEX IF NOT EXISTS idx_research_status_priority ON research_questions(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_research_family ON research_questions(method_family);
CREATE INDEX IF NOT EXISTS idx_findings_research_id ON research_findings(research_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model);
CREATE INDEX IF NOT EXISTS idx_chunks_note_id ON chunks(note_id);
CREATE INDEX IF NOT EXISTS idx_strategy_family ON strategy_cards(method_family);
CREATE INDEX IF NOT EXISTS idx_strategy_status ON strategy_cards(status);
CREATE INDEX IF NOT EXISTS idx_backtests_strategy_id ON backtests(strategy_id);
