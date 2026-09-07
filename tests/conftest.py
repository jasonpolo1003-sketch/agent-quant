"""Keep pytest on the seeded discovery backend so CI never opens a socket."""

from __future__ import annotations

import os

# Default production discovery is live Agent Reach. Tests that need the live
# path pass backend="live" plus an injected adapter runner or search_fn/fetch_fn.
os.environ.setdefault("QUANT_BRAIN_DISCOVERY", "seeded")
