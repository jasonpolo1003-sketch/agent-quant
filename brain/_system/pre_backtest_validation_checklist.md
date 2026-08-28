---
id: SYS-pre-backtest-validation
type: system_checklist
status: active
title: Pre-Backtest Validation Checklist
source_work_packet: WP-3818c6a760
---

# Pre-Backtest Validation Checklist

Use this gate before running any strategy backtest.

## Required Gate — Information Timing

- [ ] Confirm every signal input was available at the simulated decision time.
- [ ] If a signal uses a bar's closing value, execute no earlier than the next bar unless the data and execution timing prove that an earlier fill was genuinely available.

## Decision

- **Pass:** Both boxes are supported by the strategy rules, dataset fields, and execution assumptions.
- **Fail:** Stop the backtest setup and correct the signal or execution timing. Do not report performance from a failing configuration.

## Evidence

- Path: `brain/01_Sources/docs/SRC-2830f8cd41-quantconnect-glossary-look-ahead-bias.md`
- Heading: `Source — QuantConnect glossary — Look-Ahead Bias > Risks / Caveats`
- Reason: Future information can make a strategy appear profitable only because the backtest is cheating.

## Current Scope

This first checklist version covers lookahead bias only. Add other validation gates through separately reviewed evidence rather than expanding this checklist speculatively.
