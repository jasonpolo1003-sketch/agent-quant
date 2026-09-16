---
id: FAIL-RUN-seeded-primary-v1
type: failed_run
research_id: RQ-66078766
run_id: RUN-seeded-primary-v1
created: 2026-09-07
---

# Failed Run — RUN-seeded-primary-v1

## What failed

Local Qwen evidence extraction failed closed after snapshots were saved:

```text
ValueError: local model evidence extraction failed: S1 has no evidence quote; S2 has no evidence quote; S3 has no evidence quote; S4 has no evidence quote
```

## What still exists (audit)

- Snapshots: `brain/00_Inbox/Source_Snapshots/RQ-66078766/S1.md` … `S4.md`
- Events: `uv run python -m quant_brain.ops.events tail --run-id RUN-seeded-primary-v1`
- StockCharts seed returned HTTP 422 (not snapshotted)
- arXiv HTML seed returned near-empty SVG content (S2)

## Follow-up in same Step 3

Human-audited extraction from the four snapshots was written into `brain/00_Inbox/Raw_Research/RQ-66078766.md` with exact quotes and `mvp_testable: false` where the evidence does not support the RSI-ETF door. Curator run expected to reject / promote zero.
