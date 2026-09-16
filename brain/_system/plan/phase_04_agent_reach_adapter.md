---
id: PHASE-04
type: plan_phase
phase: 4
title: Agent Reach adapter
status: done
created: 2026-08-28
---

# Phase 4 — Agent Reach adapter (thin, testable)

> **COMPLETE (merged 2026-09-07).** The adapter, production discovery handler, source snapshots, raw-note schema, and zero-network fixture tests are present. Registry and dry-run verification route `discovery` to `research_scout`. Next: Phase 5 / roadmap Gate B. This completion does not constitute Qwen-backed Scout or research acceptance.

Parent plan: [../../../PLAN.md](../../../PLAN.md)
Policy: [../research_source_quality_policy.md](../research_source_quality_policy.md)

## Why this phase exists (historical rationale)

Before this phase, Agent Reach was referenced in policy and prompts but no production code called it; the research executor used a hardcoded `STARTER_SOURCES` stub. This section records why the now-complete adapter was required, not the current implementation state.

This phase built the missing bridge: a narrow, read-only, testable subprocess adapter.

## What Agent Reach actually is (read this before coding)

Verified from the local clone at `C:/Users/jason/Projects/Agent-Reach-review` (v1.5.0, MIT):

- It is a **capability layer**: installer + doctor + router. Its own docs say explicitly *"NOT a wrapper — after install, agents call upstream tools directly."*
- Each platform is one file in `agent_reach/channels/`, inheriting `BaseChannel`, implementing `can_handle(url)`, `read(url)`, `search(query)`, `check()`.
- Each platform resolves to an **ordered backend list** (preferred ▸ fallback). `doctor` reports which backend is currently active.
- Credentials live in `~/.agent-reach/config.yaml`, mode 600. **The project must never read that file.**

### Backend routing as of v1.5.0

| Channel | Preferred | Fallback | Config needed |
|---|---|---|---|
| web | Jina Reader (`curl https://r.jina.ai/URL`) | — | none |
| youtube | `yt-dlp` | — | none (needs `--js-runtimes node`) |
| github | `gh` CLI | — | none for public |
| rss | `feedparser` | — | none |
| search | Exa via `mcporter` | — | none (MCP, free) |
| bilibili | `bili-cli` | OpenCLI ▸ search API | none for search |
| twitter | `twitter-cli` | OpenCLI ▸ bird | cookies |
| reddit | OpenCLI | `rdt-cli` | **login required — no zero-config path** |
| facebook / instagram / xiaohongshu | OpenCLI | — | browser session |
| linkedin | `mcp-server-linkedin` | Jina Reader | varies |

### Live doctor result on this machine (2026-08-28)

```
youtube      warn  active_backend=yt-dlp    (needs --js-runtimes node configured)
bilibili     ok    active_backend=B站搜索API
github       warn  active_backend=null      (gh present; doctor won't run auth status)
twitter      warn  active_backend=null      (OpenCLI extension files found, NOT connected)
reddit       warn  active_backend=null      (same)
facebook     warn  active_backend=null      (same)
instagram    warn  active_backend=null      (same)
xiaohongshu  warn  active_backend=null      (same)
```

**Operational note for Jason:** the OpenCLI browser extension is not currently connected. Login-backed platforms are unavailable until Edge is open with the OpenCLI extension enabled. This does not block this phase — every channel this project needs in v1 is zero-config.

**Important subtlety:** `active_backend: null` does not always mean "broken." Per the skill file, doctor deliberately skips live probes that would read browser cookies or write device IDs. For `github` specifically, `gh` is installed and configured; doctor just declines to run `gh auth status`. Treat null as "unverified," not "absent" — and verify with a read-only command only when a run actually needs that channel.

## Scope for v1 — deliberately narrow

**Enabled:** web (Jina), github (gh), youtube (yt-dlp), rss (feedparser), search (Exa/mcporter).

**Disabled by default:** reddit, twitter, facebook, instagram, xiaohongshu, linkedin.

Rationale: the source-quality policy classes social content as **Tier C (discovery leads only)** — it cannot independently support a durable claim anyway. Building login-backed plumbing now would add cookie/session risk for evidence the curator will refuse to promote. Add per-platform later, behind an explicit env flag, once Jason confirms his Edge/OpenCLI session is live.

## Entry gate

Phase 0 complete. Independent of Phases 1-3.

## Exit gate

The adapter can:
1. Run `agent-reach doctor --json` and return parsed per-channel health.
2. Fetch one web URL through the web channel and return structured content + `captured_at` + upstream URL + content hash.
3. Snapshot that fetch to disk for provenance.
4. Do all of the above with **zero network calls in pytest** (recorded fixtures).

## Design

### Module

`src/quant_brain/discovery/agent_reach.py`

```python
AGENT_REACH_EXE = "C:/Users/jason/.agent-reach-venv/Scripts/agent-reach.exe"  # configurable

ENABLED_CHANNELS = frozenset({"web", "github", "youtube", "rss", "search"})

@dataclass(frozen=True)
class ChannelHealth:
    channel: str
    status: str            # ok | warn | error
    active_backend: str | None
    message: str

@dataclass(frozen=True)
class FetchedSource:
    url: str               # upstream URL — never an Agent Reach URL
    channel: str
    backend: str
    title: str | None
    content: str
    content_hash: str      # sha256 of content
    captured_at: str       # ISO8601 UTC
    snapshot_path: str
```

Functions:
- `check_health(exe=..., timeout=60) -> dict[str, ChannelHealth]`
- `is_channel_usable(health, channel) -> bool` — enabled ∧ (status ok ∨ zero-config-with-tool-present)
- `fetch_web(url, ...) -> FetchedSource` — via Jina Reader
- `snapshot(content, url, root) -> str` — writes to `brain/00_Inbox/Source_Snapshots/YYYY-MM-DD/{sha256[:16]}.md`

### Hard boundaries (enforce in code, not just docs)

```python
FORBIDDEN_SUBCOMMANDS = frozenset({"install", "uninstall", "configure"})
```

Raise immediately if any caller tries these. Also:
- Never read `~/.agent-reach/config.yaml`.
- Never pass cookie values as arguments or env.
- Never write project files into `~/.agent-reach/`.
- Use `%TEMP%/agent-reach/` for scratch, per the vault's CLI note.
- **Never** log a credential-shaped value.

### Subprocess hygiene

- Always pass an **argument list**, never `shell=True`, never string interpolation of a URL into a shell command. URLs come from discovery and are untrusted input — this is a command-injection boundary.
- Set an explicit timeout on every call. Kill on overrun.
- Capture stdout/stderr separately; never let stderr noise corrupt JSON parsing.
- Non-zero exit → raise a typed error carrying channel + backend, so the caller can fall back or fail closed.

### Provenance / snapshotting

Every fetch writes a snapshot **before** any LLM sees it. Rationale: upstream URLs rot, and a curated source note asserting a quote must be checkable months later. Snapshot file carries YAML frontmatter with url, captured_at, channel, backend, content_hash.

The `sources` table already has `raw_path` and `checksum` columns — wire snapshots into them.

### Events

Record via `quant_brain.ops.events` (Phase 0): `stage="discovery"`, event types `health_checked`, `fetch_started`, `fetch_completed`, `fetch_failed`, with payload carrying channel/backend/url-hash.

## Testing strategy

**pytest must never hit the network.**

- Record real `agent-reach doctor --json` output once → `tests/fixtures/agent_reach_doctor.json`.
- Record one real Jina Reader response → `tests/fixtures/jina_web_page.md`.
- Inject a fake runner (`runner=` callable defaulting to `subprocess.run`) so tests substitute a stub. Do not monkeypatch `subprocess` globally.
- Test: health parsing, enabled/disabled channel gating, forbidden-subcommand rejection, snapshot path + hash determinism, timeout handling, non-zero exit handling.

## Files to create/modify

| Path | Action |
|---|---|
| `src/quant_brain/discovery/__init__.py` | create |
| `src/quant_brain/discovery/agent_reach.py` | create |
| `scripts/agent_reach_check.py` | create — CLI health check for humans |
| `tests/test_agent_reach_adapter.py` | create |
| `tests/fixtures/agent_reach_doctor.json` | create (recorded) |
| `tests/fixtures/jina_web_page.md` | create (recorded) |
| `brain/_system/agent_reach_adapter_workflow.md` | create — workflow doc, matching the house pattern |

## Verification steps

```bash
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run python scripts/agent_reach_check.py                 # prints channel health table
uv run python -c "from quant_brain.discovery.agent_reach import fetch_web; print(fetch_web('https://kernc.github.io/backtesting.py/').title)"
uv run pytest tests/test_agent_reach_adapter.py -v
uv run pytest -q
```

## Definition of done

- [x] `check_health()` parses real doctor JSON into `ChannelHealth`
- [x] `fetch_web()` returns content + hash + captured_at + snapshot path
- [x] Snapshots land in `brain/00_Inbox/Source_Snapshots/YYYY-MM-DD/`
- [x] Forbidden subcommands raise
- [x] Login-backed channels are off by default
- [x] Tests pass with no network access
- [x] Events recorded for health check + each fetch
- [x] `PLAN.md` §10 checkpoint updated

## Do not

- Do not wrap Agent Reach's own routing logic. It routes; you call the channel it names.
- Do not write a scraper fallback when a channel is down. Log, fall back to the next backend Agent Reach lists, else fail closed.
- Do not enable social channels "just to see." Tier C evidence cannot be promoted anyway.
- Do not cite Agent Reach in any durable note. Cite the upstream URL.
