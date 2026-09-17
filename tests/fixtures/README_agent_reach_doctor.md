# Agent Reach doctor fixtures — why there are two

JSON cannot carry comments, so the provenance of these two files lives here.
**They must not be merged into one file.**

An unrealistic fixture is what concealed a real defect for an entire gate: the
previous single `agent_reach_doctor.json` invented the channel keys `search` and
`exa`, which do not exist in any Agent Reach install. The adapter looked for those
same invented names, so the code and the fixture agreed with each other and
disagreed with reality — and the suite stayed green while the Exa lane could never
be selected. Splitting observed state from constructed state is what stops that
from recurring.

## `agent_reach_doctor_live.json` — verbatim capture

Captured 2026-09-17 on Jason's Windows machine:

```
C:/Users/jason/.agent-reach-venv/Scripts/agent-reach.exe doctor --json
```

Agent Reach v1.5.0. Nothing in this file is invented. The only edit is scrubbing a
local user path out of one `message` field (one field changed).

Two properties are load-bearing and are pinned by
`test_the_live_doctor_fixture_is_not_edited_into_a_healthy_one`:

- **`exa_search` really is `"status": "off"`** on this machine — mcporter is
  installed, Exa is not configured. This is the true Gate D blocker state.
- **Non-ASCII `name`/`message` values are literal UTF-8**, not `\uXXXX` escapes.
  An escaped file is pure ASCII and would decode cleanly under cp1252, which
  would silently delete the coverage that the encoding fix depends on.

Do not "fix" this file to make a test pass. If reality changes, re-capture it and
say so here.

## `agent_reach_doctor_healthy.json` — synthetic

**Constructed, not observed.** Derived from the live capture with `exa_search`
flipped to `"ok"`, so the dispatch happy-path tests exercise dispatch rather than
silently becoming "no usable channel" tests. Its `exa_search.message` says
SYNTHETIC in the payload itself.

It deliberately keeps the *real* channel keys, so it cannot drift back into naming
channels that do not exist — the original failure.

Used by: the search/dispatch tests in `test_agent_reach_adapter.py` and
`test_discovery_handler.py`.
