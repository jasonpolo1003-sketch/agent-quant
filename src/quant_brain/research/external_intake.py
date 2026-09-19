"""Isolated retention of external research, never trusted-index promotion."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader
from pypdf import __version__ as PDF_VERSION

from quant_brain.config import PROJECT_ROOT

PROTECTED_ROOTS = (PROJECT_ROOT, PROJECT_ROOT.parent / "memory_vault")
APPLICATION_ID = 0x5142494E
# Checked against the on-disk size before any read, so an oversized or hostile
# artifact cannot be pulled into memory just to be rejected afterwards.
MAX_REPORT_BYTES = 64 * 1024 * 1024


def safe_workspace(path: str | Path) -> Path:
    raw = Path(path).absolute()
    resolved = raw.resolve()
    for protected in PROTECTED_ROOTS:
        protected = protected.resolve()
        if resolved.is_relative_to(protected) or protected.is_relative_to(resolved):
            raise ValueError("workspace must be isolated from production roots and ancestors")
    for part in (raw, *raw.parents):
        if part.is_symlink() or (
            part.exists() and getattr(part.lstat(), "st_file_attributes", 0) & 0x400
        ):
            raise ValueError("workspace alias/reparse point is forbidden")
    return resolved


def safe_target(root: Path, path: Path) -> Path:
    safe_workspace(root)
    if not path.resolve().is_relative_to(root):
        raise ValueError("artifact alias escapes workspace")
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink() or (
            part.exists()
            and (
                getattr(part.lstat(), "st_file_attributes", 0) & 0x400
                or (part.is_file() and part.stat().st_nlink > 1)
            )
        ):
            raise ValueError("artifact/database alias is forbidden")
    return path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.now(UTC).isoformat()


def followup_for(reason: str) -> str:
    """Name the concrete recovery step for a report that yielded no usable text.

    A blocked report stays retained and searchable, so the reason alone is not
    enough: the catalog has to say what would unblock it. Inaccessible is not
    disproven, and it is not a dead end either.
    """
    if not reason:
        return ""
    if reason == "missing native text":
        return (
            "No native text layer (scanned or vector-drawn glyphs). Obtain a "
            "text-bearing export from the provider, or attach the original "
            "source documents; OCR is not implemented in this intake lane."
        )
    return (
        f"Native extraction failed ({reason}). Re-export or re-download the "
        "report from the provider and re-import."
    )


class Intake:
    def __init__(self, workspace: str | Path, *, create: bool = True):
        self.root = safe_workspace(workspace)
        self.db_path = safe_target(self.root, self.root / "external.sqlite")
        if self.db_path.exists():
            with closing(sqlite3.connect(self.db_path.as_uri() + "?mode=ro", uri=True)) as conn:
                if conn.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID:
                    raise ValueError("existing database is not an external intake catalog")
        if not create:
            if not self.db_path.exists():
                raise ValueError("intake workspace does not exist")
            return
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.execute(f"PRAGMA application_id={APPLICATION_ID}")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS observations (report_id TEXT, provider TEXT, origin TEXT, UNIQUE(report_id, provider, origin))"
            )
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS targets (id TEXT PRIMARY KEY, url TEXT NOT NULL, tier TEXT NOT NULL, reason TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS claims (id TEXT PRIMARY KEY, report_id TEXT NOT NULL REFERENCES reports(id), target_id TEXT NOT NULL REFERENCES targets(id), data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS history (seq INTEGER PRIMARY KEY, claim_id TEXT NOT NULL REFERENCES claims(id), state TEXT NOT NULL, reason TEXT NOT NULL, reviewer TEXT NOT NULL, evidence_id INTEGER, recorded_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS fetches (id INTEGER PRIMARY KEY, target_id TEXT NOT NULL REFERENCES targets(id), data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evaluations (id INTEGER PRIMARY KEY, claim_id TEXT NOT NULL REFERENCES claims(id), fetch_id INTEGER NOT NULL REFERENCES fetches(id), data TEXT NOT NULL, UNIQUE(claim_id,fetch_id));
                CREATE INDEX IF NOT EXISTS claim_history ON history(claim_id, seq);
                CREATE TRIGGER IF NOT EXISTS history_no_update BEFORE UPDATE ON history BEGIN SELECT RAISE(ABORT, 'append-only history'); END;
                CREATE TRIGGER IF NOT EXISTS history_no_delete BEFORE DELETE ON history BEGIN SELECT RAISE(ABORT, 'append-only history'); END;
            """)

    @contextmanager
    def connection(self):
        for suffix in ("", "-journal", "-wal", "-shm"):
            safe_target(self.root, Path(str(self.db_path) + suffix))
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def import_report(self, path: str | Path, *, provider: str) -> dict:
        path = Path(path).resolve()
        size = path.stat().st_size
        if size > MAX_REPORT_BYTES:
            raise ValueError(f"report size {size} exceeds the {MAX_REPORT_BYTES}-byte intake cap")
        original = path.read_bytes()
        sha = digest(original)
        report_id = sha
        with self.connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO observations VALUES (?,?,?)",
                (report_id, provider, str(path)),
            )
            row = conn.execute("SELECT data FROM reports WHERE id=?", (report_id,)).fetchone()
            if row:
                result = json.loads(row[0])
                for field, hash_field in [
                    ("original_path", "sha256"),
                    ("text_path", "text_sha256"),
                ]:
                    target = safe_target(self.root, Path(result[field]))
                    if not target.exists() or digest(target.read_bytes()) != result[hash_field]:
                        raise ValueError("retained report integrity failure")
                return result
            artifact = safe_target(self.root, self.root / f"{sha}.pdf")
            artifact.write_bytes(original)
            try:
                pages = [
                    p.extract_text(extraction_mode="layout") or ""
                    for p in PdfReader(artifact).pages
                ]
                reason = "" if all(p.strip() for p in pages) and pages else "missing native text"
            except Exception as exc:
                pages, reason = [], f"{type(exc).__name__}: {exc}"
            extracted = safe_target(self.root, self.root / f"{sha}.text.json")
            extracted.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
            result = dict(
                id=report_id,
                sha256=sha,
                provider=provider,
                origin=str(path),
                original_path=str(artifact),
                text_path=str(extracted),
                extraction_status="extraction_blocked" if reason else "extracted",
                extraction_reason=reason,
                followup_action=followup_for(reason),
                captured_at=now(),
                extractor="pypdf",
                page_count=len(pages),
                extractor_version=PDF_VERSION,
                extraction_mode="layout",
                text_sha256=digest(extracted.read_bytes()),
            )
            conn.execute("INSERT INTO reports VALUES (?,?)", (report_id, json.dumps(result)))
            return result

    def checked_report_text(self, report):
        for field, hash_field in [("original_path", "sha256"), ("text_path", "text_sha256")]:
            target = safe_target(self.root, Path(report[field]))
            if not target.exists() or digest(target.read_bytes()) != report[hash_field]:
                raise ValueError("report integrity failure")
        return Path(report["text_path"]).read_text(encoding="utf-8")

    def add_claim(
        self,
        report_id: str,
        *,
        url: str,
        claim: str,
        quote: str,
        locator: str,
        context: str = "",
        research_id: str = "",
    ) -> dict:
        from quant_brain.discovery.source_quality import classify_source, normalize_candidate_url

        if not claim.strip() or not locator.strip():
            raise ValueError("claim and report locator required")
        canonical = normalize_candidate_url(url) if url else ""
        target_id = digest((canonical or f"bibliographic:{report_id}:{locator}").encode())
        # research_id is part of claim identity: the same passage tracked for two
        # research questions is two claims with independent review histories, not one.
        claim_id = digest(
            json.dumps(
                [report_id, target_id, claim, quote, locator, research_id], ensure_ascii=False
            ).encode()
        )
        tier = classify_source(canonical) if canonical else None
        result = dict(
            id=claim_id,
            report_id=report_id,
            target_id=target_id,
            claim=claim,
            quote=quote,
            locator=locator,
            context=context,
            research_id=research_id,
            empirical_validation="not_assessed",
            origin="external_report_candidate",
        )
        with self.connection() as conn:
            if not conn.execute("SELECT 1 FROM reports WHERE id=?", (report_id,)).fetchone():
                raise ValueError("unknown report")
            old = conn.execute("SELECT data FROM claims WHERE id=?", (claim_id,)).fetchone()
            if old:
                return json.loads(old[0])
            conn.execute(
                "INSERT OR IGNORE INTO targets VALUES (?,?,?,?)",
                (
                    target_id,
                    canonical,
                    tier.tier if tier else "discovery-only",
                    tier.reason if tier else "bibliographic lead; no source URL",
                ),
            )
            conn.execute(
                "INSERT INTO claims VALUES (?,?,?,?)",
                (claim_id, report_id, target_id, json.dumps(result)),
            )
            conn.execute(
                "INSERT INTO history(claim_id,state,reason,reviewer,recorded_at) VALUES (?,?,?,?,?)",
                (
                    claim_id,
                    "unreviewed_lead",
                    "Imported candidate; source and scope not checked",
                    "importer",
                    now(),
                ),
            )
        return result

    def history(self, claim_id: str) -> list[dict]:
        with self.connection() as conn:
            conn.row_factory = sqlite3.Row
            return [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM history WHERE claim_id=? ORDER BY seq", (claim_id,)
                )
            ]

    def record_review(
        self,
        claim_id: str,
        *,
        state: str,
        reason: str,
        reviewer: str,
        evidence_id: int | None = None,
    ) -> int:
        allowed = {
            "unreviewed_lead",
            "unresolved",
            "blocked",
            "partially_supported",
            "supported_in_scope",
            "contradicted",
            "superseded",
        }
        if state not in allowed or not reason.strip() or not reviewer.strip():
            raise ValueError("valid state, reason and reviewer required")
        # Automated checks never assert contradiction. Review conclusions remain attributed.
        if state == "supported_in_scope":
            raise ValueError("support requires a pinned source verification; use scope review")
        with self.connection() as conn:
            if not conn.execute("SELECT 1 FROM claims WHERE id=?", (claim_id,)).fetchone():
                raise ValueError("unknown claim")
            old = conn.execute(
                "SELECT seq,state,reason,reviewer,evidence_id FROM history WHERE claim_id=? ORDER BY seq DESC LIMIT 1",
                (claim_id,),
            ).fetchone()
            if old and tuple(old[1:]) == (state, reason, reviewer, evidence_id):
                return old[0]
            cur = conn.execute(
                "INSERT INTO history(claim_id,state,reason,reviewer,evidence_id,recorded_at) VALUES (?,?,?,?,?,?)",
                (claim_id, state, reason, reviewer, evidence_id, now()),
            )
            return cur.lastrowid

    def verify(self, claim_id, **kwargs):
        from .external_verification import verify_claim

        return verify_claim(self, claim_id, **kwargs)

    def approve_scope(self, claim_id, **kwargs):
        from .external_verification import approve_scope

        return approve_scope(self, claim_id, **kwargs)

    def handoff(self):
        from .external_verification import handoff

        return handoff(self)

    def summary(self) -> dict:
        with self.connection() as conn:
            reports = [
                json.loads(r[0]) for r in conn.execute("SELECT data FROM reports ORDER BY id")
            ]
            claims = [json.loads(r[0]) for r in conn.execute("SELECT data FROM claims ORDER BY id")]
            targets = [
                dict(zip(("id", "url", "tier", "reason"), r))
                for r in conn.execute("SELECT * FROM targets ORDER BY id")
            ]
        for claim in claims:
            claim["history"] = self.history(claim["id"])
            claim["state"] = claim["history"][-1]["state"]
        return dict(
            reports=reports,
            claims=claims,
            targets=targets,
            report_count=len(reports),
            claim_count=len(claims),
            distinct_source_targets=len(targets),
            independent_corroboration="not_assessed",
            production_promotion=False,
        )
