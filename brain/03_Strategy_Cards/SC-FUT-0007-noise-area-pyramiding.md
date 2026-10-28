---
card_id: SC-FUT-0007
status: frozen
frozen: true
frozen_at: 2026-10-28
frozen_spec: brain/_system/futures/sc-fut-0007-spec.v1.json
method_family: noise_area_momentum
primary: MNQ
parent: SC-FUT-0005
---

# SC-FUT-0007: noise-area momentum with pyramiding, MNQ

> **FROZEN 2026-10-28** before any result (bigger-edge plan, step A2). Binding rules: brain/_system/futures/sc-fut-0007-spec.v1.json.

**Idea:** SC-FUT-0005's profit is concentrated in a few trend days (best 20 days = 76%). Start every trade at 1 MNQ, so a bad day stays small, and add one more MNQ each time the trade moves one noise-band width further in our favour, up to 4. Trend days get bigger, while the starting risk stays the same.

**Rules:** the SC-FUT-0005 entry, exit, checks and flatten are unchanged. Adds are resting stop orders at +1, +2 and +3 steps from the entry. One step = the noise band's width (sigma × the day's open) at the check that opened the trade. All units exit together.

**Luck gets the same deal:** random-direction trades pyramid on their own open profit by the identical rule. Pyramiding into noise must not count as an edge.

**How it fails honestly:** adds fill near the top and give it back at the trailing stop. Or the bigger best days break Topstep's consistency rules, or the trades still pay out too slowly.

**Gate (cash, 42 days, $1,000 DLL):** mean net cash > $0, beats luck (lower 90% bound > $0), and the chance of a payout between 3% and 30% (stated in advance). Four plan/path cells, each one trial. No variants on this card.
