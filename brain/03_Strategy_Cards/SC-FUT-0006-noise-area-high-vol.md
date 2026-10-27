---
card_id: SC-FUT-0006
status: frozen
frozen: true
frozen_at: 2026-10-27
frozen_spec: brain/_system/futures/sc-fut-0006-spec.v1.json
method_family: noise_area_momentum
primary: MNQ
parent: SC-FUT-0005
---

# SC-FUT-0006: noise-area momentum, high-volatility days only, 3 MNQ

> **FROZEN 2026-10-27** by Jason before any result. Binding rules: brain/_system/futures/sc-fut-0006-spec.v1.json.

**Idea (Jason):** don't trade every day. Wait for the days where the edge should be biggest, and take more risk then. The SC-FUT-0005 rule is unchanged. It trades only when Nasdaq's recent volatility (20-day, known before the open) is above its own one-year median, and then at 3 MNQ instead of 1.

**Why it might work:** SC-FUT-0005's profit is concentrated (best 20 days = 76%), its higher-volatility years were 2-3x better, and the source research says intraday momentum is strongest in high volatility. A prop account caps the downside at the fee, so concentrating size where the edge is larger could pass faster.

**How it fails honestly:** the filter adds nothing beyond the volatility itself, or 3 MNQ blows the $2,000 limit too often.

**Gate:**
- beats the matched random-direction control and luck in the prop simulator (Combine limit with no lock, the conservative reading);
- **and** the median time to pass is at most 3 months.
