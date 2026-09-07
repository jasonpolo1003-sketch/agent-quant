"""Keep pytest on the seeded discovery backend so CI never opens a socket."""

from __future__ import annotations

import os

# Default live discovery is fail-closed without Agent Reach. Tests that need the
# live path pass backend="live" plus injected search_fn/fetch_fn.
os.environ.setdefault("QUANT_BRAIN_DISCOVERY", "seeded")
