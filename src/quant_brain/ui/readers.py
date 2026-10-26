"""Read-only views over the brain: SQLite (opened ``mode=ro``), Markdown, manifests, git.

Nothing in this module writes. Every function tolerates a missing database or
table and returns an empty result, so the terminal renders on a fresh clone.
"""

from __future__ import annotations

import json
import re
import sqlite3
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import frontmatter

from quant_brain.data.market_data import (
    MANIFEST_DIR,
    MarketDataError,
    load_dataset,
    verify_datasets,
)

COUNT_TABLES = (
    "notes", "sources", "chunks", "research_questions", "research_findings",
    "strategy_cards", "price_datasets", "backtests", "reviews", "agent_tasks", "agent_events",
)


@contextmanager
def ro_connect(db_path: str | Path) -> Iterator[sqlite3.Connection | None]:
    path = Path(db_path)
    if not path.is_file():
        yield None
        return
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _rows(db_path: str | Path, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with ro_connect(db_path) as conn:
        if conn is None:
            return []
        try:
            return [dict(r) for r in conn.execute(sql, params)]
        except sqlite3.OperationalError:
            return []


def _json(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


# --- counts and pipeline --------------------------------------------------------------

def brain_counts(db_path: str | Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    with ro_connect(db_path) as conn:
        for table in COUNT_TABLES:
            try:
                counts[table] = int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) \
                    if conn else 0
            except sqlite3.OperationalError:
                counts[table] = 0
    return counts


def pipeline(counts: dict[str, int]) -> list[dict[str, Any]]:
    """The research-to-review chain, each stage lit by what the database actually holds."""
    stages = [
        ("Research", "sources", "curated source notes"),
        ("Market data", "price_datasets", "registered datasets"),
        ("Strategy card", "strategy_cards", "frozen cards"),
        ("Backtest", "backtests", "backtest runs"),
        ("Review", "reviews", "adversarial reviews"),
    ]
    out, blocked = [], False
    for label, table, noun in stages:
        n = counts.get(table, 0)
        state = "done" if n and not blocked else ("next" if not blocked else "waiting")
        if not n:
            blocked = True
        out.append({"label": label, "count": n, "noun": noun, "state": state})
    return out


def plan_checkpoint(project_root: Path, limit: int = 6) -> dict[str, Any]:
    """Headings and the 'next step' line from PLAN.md §10, the handoff checkpoint."""
    path = project_root / "PLAN.md"
    if not path.is_file():
        return {"entries": [], "next": None}
    text = path.read_text(encoding="utf-8")
    start = text.find("## 10.")
    section = text[start:] if start >= 0 else ""
    end = section.find("\n## ", 5)
    section = section[:end] if end > 0 else section
    entries = re.findall(r"^### (.+)$", section, flags=re.M)[:limit]
    nxt = None
    for pattern in (r"\*\*Next bounded step:\*\*\s*(.+)", r"\*\*Next[^*]*:\*\*\s*(.+)"):
        m = re.search(pattern, section)
        if m:
            nxt = m.group(1).strip()
            break
    return {"entries": entries, "next": nxt}


# --- harness events, runs, tasks -------------------------------------------------------

def events(db_path: str | Path, *, after_id: int | None = None, run_id: str | None = None,
           limit: int = 200) -> list[dict[str, Any]]:
    sql = "SELECT * FROM agent_events"
    clauses, params = [], []
    if after_id is not None:
        clauses.append("event_id > ?")
        params.append(after_id)
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    ascending = after_id is not None or run_id is not None
    sql += f" ORDER BY event_id {'ASC' if ascending else 'DESC'} LIMIT ?"
    params.append(limit)
    rows = _rows(db_path, sql, tuple(params))
    for row in rows:
        row["payload"] = _json(row.pop("payload_json", None), {})
    return rows


def max_event_id(db_path: str | Path) -> int:
    rows = _rows(db_path, "SELECT COALESCE(MAX(event_id), 0) AS m FROM agent_events")
    return int(rows[0]["m"]) if rows else 0


def runs(db_path: str | Path, limit: int = 50) -> list[dict[str, Any]]:
    """One row per run, with its final status taken from the run's last event."""
    return _rows(
        db_path,
        """
        SELECT e.run_id, MIN(e.created_at) AS started_at, MAX(e.created_at) AS last_at,
               COUNT(*) AS event_count,
               GROUP_CONCAT(DISTINCT e.agent_role) AS agents,
               (SELECT status FROM agent_events l WHERE l.run_id = e.run_id
                  ORDER BY l.event_id DESC LIMIT 1) AS final_status,
               (SELECT message FROM agent_events l WHERE l.run_id = e.run_id
                  ORDER BY l.event_id DESC LIMIT 1) AS final_message
        FROM agent_events e GROUP BY e.run_id ORDER BY MAX(e.event_id) DESC LIMIT ?
        """,
        (limit,),
    )


def agent_tasks(db_path: str | Path) -> list[dict[str, Any]]:
    return _rows(db_path, "SELECT * FROM agent_tasks ORDER BY COALESCE(created_at, '') DESC")


def research_questions(db_path: str | Path) -> list[dict[str, Any]]:
    return _rows(db_path, "SELECT research_id, question, status, priority, assigned_agent,"
                          " updated_at FROM research_questions ORDER BY updated_at DESC")


# --- market data ----------------------------------------------------------------------

def _manifest_only_reports(project_root: Path, reason: str) -> list[Any]:
    """Fallback when the Gate F verifier itself fails: list manifests, trust none of them."""
    from types import SimpleNamespace

    return [SimpleNamespace(dataset_id=p.stem, state="unverified", problems=[reason])
            for p in sorted((project_root / MANIFEST_DIR).glob("*.json"))]


def datasets(project_root: Path, db_path: str | Path) -> list[dict[str, Any]]:
    try:
        reports = verify_datasets(project_root, db_path)
    except Exception as exc:  # e.g. a corrupt Parquet file; show it, never crash the terminal
        reports = _manifest_only_reports(
            project_root, f"verifier crashed: {type(exc).__name__}: {exc}")
    out = []
    for report in reports:
        manifest = {}
        mpath = project_root / MANIFEST_DIR / f"{report.dataset_id}.json"
        if mpath.is_file():
            manifest = _json(mpath.read_text(encoding="utf-8"), {})
        out.append({
            "dataset_id": report.dataset_id,
            "state": report.state,
            "problems": list(report.problems),
            "symbol": manifest.get("symbol"),
            "rows": manifest.get("rows"),
            "first_date": manifest.get("first_date"),
            "last_date": manifest.get("last_date"),
            "provider": manifest.get("provider"),
            "downloaded_at": manifest.get("downloaded_at"),
            "price_basis": manifest.get("price_basis"),
            "warnings": manifest.get("warnings", []),
            "file_sha256": manifest.get("file_sha256"),
            "cross_check": (manifest.get("cross_check") or {}).get("status"),
        })
    return out


def bars(project_root: Path, db_path: str | Path, dataset_id: str) -> list[dict[str, Any]]:
    """Accepted datasets only (``load_dataset`` refuses anything else)."""
    try:
        frame = load_dataset(project_root, db_path, dataset_id)
    except MarketDataError:
        raise
    except Exception as exc:  # the verifier can crash on a corrupt file; that is not loadable
        raise MarketDataError(f"{dataset_id} could not be verified: "
                              f"{type(exc).__name__}: {exc}") from exc
    cols = ["date", "open", "high", "low", "close", "adj_close", "volume"]
    frame = frame[cols]
    return [
        {"time": str(d)[:10], "open": o, "high": h, "low": low, "close": c, "adj_close": a,
         "volume": v}
        for d, o, h, low, c, a, v in frame.itertuples(index=False, name=None)
    ]


# --- backtest lab ---------------------------------------------------------------------

def _file_backed_cards(project_root: Path) -> list[dict[str, Any]]:
    ledger_path = project_root / "brain/03_Strategy_Cards/freeze_ledger.json"
    if not ledger_path.is_file():
        return []
    ledger = _json(ledger_path.read_text(encoding="utf-8"), {})
    superseded = {s.get("card_id") for s in ledger.get("superseded", []) if isinstance(s, dict)}
    out = []
    for entry in reversed(ledger.get("frozen", [])):
        if not isinstance(entry, dict) or not entry.get("card_id"):
            continue
        cid = entry["card_id"]
        rel = entry.get("card_path") or f"brain/03_Strategy_Cards/{cid}.md"
        cpath = project_root / rel
        title, hypothesis, markets = cid, "", []
        if cpath.is_file():
            try:
                post = frontmatter.load(cpath)
                m = re.search(r"^#\s+(.+)$", post.content, re.M)
                if m:
                    title = m.group(1).strip()
                jm = re.search(r"```json\s*(\{.*?\})\s*```", post.content, re.S)
                if jm:
                    spec = _json(jm.group(1), {})
                    title = spec.get("title") or title
                    hypothesis = spec.get("hypothesis") or ""
                    markets = spec.get("universe") or []
            except Exception:
                pass
        out.append({
            "strategy_id": cid,
            "title": title,
            "status": "superseded" if cid in superseded else "frozen",
            "hypothesis": hypothesis,
            "markets": markets,
            "source_ids": [],
            "backtest_ids": [],
            "review_status": "not_reviewed",
            "note_path": rel,
            "created_at": entry.get("frozen_at") or "",
        })
    return out


def _file_backed_trials(project_root: Path) -> list[dict[str, Any]]:
    out = []
    for tpath in sorted((project_root / "brain/04_Backtest_Reports").glob("*.trials.jsonl")):
        try:
            lines = tpath.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            row = _json(line, None)
            if not isinstance(row, dict) or not row.get("trial_id"):
                continue
            metrics = row.get("metrics") or {}
            out.append({
                "backtest_id": row["trial_id"],
                "strategy_id": row.get("card_id"),
                "created_at": row.get("at") or "",
                "total_return": metrics.get("total_return"),
                "benchmark_return": None,
                "cagr": metrics.get("cagr"),
                "sharpe": metrics.get("sharpe"),
                "sortino": None,
                "max_drawdown": metrics.get("max_drawdown"),
                "volatility": None,
                "exposure": metrics.get("exposure"),
                "win_rate": metrics.get("win_rate"),
                "profit_factor": metrics.get("profit_factor"),
                "number_of_trades": metrics.get("trades"),
                "fees": row.get("cost_bps"),
                "config": {
                    "phase": row.get("phase"),
                    "symbol": row.get("symbol"),
                    "cost_bps": row.get("cost_bps"),
                    "kind": row.get("kind"),
                    "rule": row.get("rule"),
                    "period": row.get("period"),
                },
                "equity_available": False,
            })
    return out


def lab(project_root: Path, db_path: str | Path) -> dict[str, Any]:
    """Whatever PROP-007 steps 4-6 wrote. The terminal adapts; it never defines this schema."""
    cards = _rows(db_path, "SELECT * FROM strategy_cards ORDER BY created_at DESC")
    tests = _rows(
        db_path,
        "SELECT b.*, m.total_return, m.benchmark_return, m.cagr, m.sharpe, m.sortino,"
        " m.max_drawdown, m.volatility, m.exposure, m.win_rate, m.profit_factor,"
        " m.number_of_trades, m.fees"
        " FROM backtests b LEFT JOIN metrics m ON m.backtest_id = b.backtest_id"
        " ORDER BY b.created_at DESC",
    )
    for test in tests:
        test["config"] = _json(test.pop("config_json", None), {})
        test["equity_available"] = equity_path(project_root, test) is not None
    reviews = _rows(db_path, "SELECT * FROM reviews ORDER BY created_at DESC")
    for review in reviews:
        review["reasons"] = _json(review.pop("reasons_json", None), [])
        review["source"] = "database"
    known = {r.get("note_path") for r in reviews}
    reviews += [r for r in review_notes(project_root) if r["note_path"] not in known]
    for card in cards:
        for key in ("markets_json", "source_ids_json", "backtest_ids_json"):
            card[key.removesuffix("_json")] = _json(card.pop(key, None), [])
    if not cards:
        cards = _file_backed_cards(project_root)
    if not tests:
        tests = _file_backed_trials(project_root)
    return {"cards": cards, "backtests": tests, "reviews": reviews}


def equity_path(project_root: Path, backtest: dict[str, Any]) -> Path | None:
    """An equity series next to the report (``<report>.equity.{parquet,csv,json}``) or in config."""
    candidates = []
    declared = (backtest.get("config") or {}).get("equity_path")
    if declared:
        candidates.append(project_root / declared)
    report = backtest.get("report_path")
    if report:
        base = project_root / report
        stem = base.with_suffix("")
        candidates += [stem.with_name(stem.name + f".equity.{ext}") for ext in
                       ("parquet", "csv", "json")]
    root = project_root.resolve()
    for path in candidates:
        resolved = path.resolve()
        if resolved.is_file() and resolved.is_relative_to(root):
            return resolved
    return None


def equity_series(project_root: Path, backtest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    import pandas as pd

    path = equity_path(project_root, backtest)
    if path is None:
        return {}
    if path.suffix == ".parquet":
        frame = pd.read_parquet(path)
    elif path.suffix == ".csv":
        frame = pd.read_csv(path)
    else:
        frame = pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
    date_col = next((c for c in frame.columns if c.lower() in ("date", "time", "timestamp")), None)
    if date_col is None:
        frame = frame.reset_index()
        date_col = frame.columns[0]
    out: dict[str, list[dict[str, Any]]] = {}
    for col in frame.columns:
        if col == date_col or not pd.api.types.is_numeric_dtype(frame[col]):
            continue
        out[str(col)] = [{"time": str(t)[:10], "value": float(v)}
                         for t, v in zip(frame[date_col], frame[col], strict=True) if pd.notna(v)]
    return out


# --- reviews written as notes ------------------------------------------------------------

_VERDICT_RE = re.compile(r"^##\s*Review verdict:\s*\*\*(.+?)\*\*", re.M)


def review_notes(project_root: Path) -> list[dict[str, Any]]:
    """Adversarial reviews saved as Markdown in brain/05_Reviews/.

    The review step can finish with a note and no ``reviews`` row, so the terminal
    reads both. Newest first.
    """
    out = []
    for path in sorted((project_root / "brain/05_Reviews").glob("*.md")):
        try:
            post = frontmatter.load(path)
        except Exception:  # an unreadable note is skipped, not fatal
            continue
        m = _VERDICT_RE.search(post.content)
        verdict_text = m.group(1).strip().replace(" — ", ": ").replace("—", ": ") if m else None
        word = re.match(r"[A-Za-z_-]+", verdict_text or "")
        card = re.search(r"SC-\d+", str(post.get("card") or post.get("review_of") or path.stem))
        out.append({
            "review_id": path.stem, "strategy_id": card.group(0) if card else None,
            "verdict": word.group(0).lower() if word else "unknown", "verdict_text": verdict_text,
            "reviewer": post.get("reviewer"), "date": str(post.get("date") or ""),
            "note_path": path.relative_to(project_root).as_posix(), "source": "note",
            "reasons": [],
        })
    return sorted(out, key=lambda r: r["date"], reverse=True)


def effective_counts(project_root: Path, db_path: str | Path) -> dict[str, int]:
    """Database counts, with reviews and file-backed artifacts included when present."""
    counts = brain_counts(db_path)
    counts["reviews"] = max(counts.get("reviews", 0), len(review_notes(project_root)))
    if not counts.get("sources") and (project_root / "brain/01_Sources").is_dir():
        counts["sources"] = len(list((project_root / "brain/01_Sources").rglob("*.md")))
    if not counts.get("price_datasets") and (project_root / MANIFEST_DIR).is_dir():
        counts["price_datasets"] = len(list((project_root / MANIFEST_DIR).glob("*.json")))
    if not counts.get("strategy_cards"):
        counts["strategy_cards"] = len(_file_backed_cards(project_root))
    if not counts.get("backtests"):
        counts["backtests"] = len(_file_backed_trials(project_root))
    return counts


# --- decisions, proposals, journal ----------------------------------------------------

_PROP_RE = re.compile(r"^### (PROP-\d+) — (.+)$", re.M)


def proposals(project_root: Path) -> list[dict[str, Any]]:
    path = project_root / "brain/_system/plan/plan_change_proposals.md"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    matches = list(_PROP_RE.finditer(text))
    out = []
    for i, m in enumerate(matches):
        body = text[m.end(): matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        body = body.split("\n## ", 1)[0]
        date = re.search(r"\*\*Date:\*\*\s*(\S+)", body)
        status = re.search(r"\*\*Status:\*\*\s*([^\n]+)", body)
        out.append({
            "id": m.group(1), "title": m.group(2).strip(), "kind": "proposal",
            "date": date.group(1) if date else None,
            "status": status.group(1).strip() if status else None,
            "path": "brain/_system/plan/plan_change_proposals.md",
        })
    return out


def decisions(project_root: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted((project_root / "brain/07_Decision_Log").glob("*.md")):
        try:
            post = frontmatter.load(path)
        except Exception:  # a malformed note still shows up, just untitled
            post = frontmatter.Post("")
        m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
        heading = re.search(r"^# (.+)$", post.content, re.M)
        out.append({
            "id": path.stem, "kind": "decision",
            "title": str(post.get("title") or (heading.group(1) if heading else path.stem)),
            "date": m.group(1) if m else None, "status": post.get("status"),
            "path": path.relative_to(project_root).as_posix(),
        })
    return out


def journal(project_root: Path) -> list[dict[str, Any]]:
    items = proposals(project_root) + decisions(project_root)
    return sorted(items, key=lambda i: (i.get("date") or "0000", i["id"]), reverse=True)


# --- git ------------------------------------------------------------------------------

def _git(project_root: Path, *args: str) -> str:
    try:
        done = subprocess.run(["git", *args], cwd=project_root, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout if done.returncode == 0 else ""


def git_activity(project_root: Path, limit: int = 25) -> dict[str, Any]:
    log = _git(project_root, "log", f"-{limit}", "--date=iso-strict",
               "--pretty=format:%H%x1f%h%x1f%ad%x1f%an%x1f%s")
    commits = []
    for line in log.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 5:
            commits.append(dict(zip(("sha", "short", "date", "author", "subject"), parts,
                                    strict=True)))
    status = _git(project_root, "status", "--porcelain=v1", "--untracked-files=normal")
    changes = [{"code": line[:2].strip() or "?", "path": line[3:]}
               for line in status.splitlines() if line.strip()]
    return {
        "branch": _git(project_root, "rev-parse", "--abbrev-ref", "HEAD").strip(),
        "head": _git(project_root, "rev-parse", "--short", "HEAD").strip(),
        "commits": commits,
        "changes": changes,
    }
