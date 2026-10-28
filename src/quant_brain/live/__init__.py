"""Live (paper) runner for SC-FUT-0005, MNQ noise-area momentum. DRY RUN ONLY for now.

Modules: `engine` (the noise.py rule driven bar by bar, plus the sigma table built from past
sessions), `broker` (Broker protocol and FakeBroker), `projectx` (an inert TopstepX / ProjectX
Gateway client skeleton), `runner` (per-minute loop, risk switches, JSONL journal).

Topstep rules that bind any live use (help.topstep.com article 11187768, read 2026-10-28):
- The ProjectX API works on simulated accounts only: Trading Combine and Express Funded
  (XFA). It is not available on Live Funded accounts.
- All trading activity must originate from the trader's personal device. VPS, VPN and remote
  servers are prohibited for anything that can place, modify or cancel orders; a server may
  only watch and record. So this runner must run on Jason's own PC, on his normal connection.
- HFT is banned; API orders are final; there is no sandbox (test on a Practice account).
The code cannot verify where it runs, so `runner.Runner` journals and logs STARTUP_WARNING.

Proof of the rule: scripts/live_replay_check.py replays every practice day through
`engine.NoiseEngine` and compares trades with `workbench.noise.NoiseArea().simulate`.
"""

STARTUP_WARNING = (
    "Topstep: API trading is for Combine/XFA (simulated) accounts only, and orders must "
    "originate from your personal PC: no VPS, VPN or remote server may place orders."
)
