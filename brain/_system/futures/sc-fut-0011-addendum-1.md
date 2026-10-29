# SC-FUT-0011 addendum 1 (2026-10-28, before any result)

The frozen rule enters when |price/P0 - 1| > sigma and puts the stop at P0 x (1 +/- 2 x sigma). If price is already beyond 2 x sigma at a check, the entry would sit beyond its own stop and be stopped out immediately (a cost-only trade, possibly twice an evening). This is a specification error, not a strategy choice.

**Change:** enter only when sigma < |price/P0 - 1| < 2 x sigma (strictly inside the stop). Nothing else changes. Made by the orchestrator after the engineering build and before any run on market data; spec v1 and its hash stay as they are.

Other engineering interpretations accepted as written (conservative): targets fill only on a bar after the entry bar; a marketable target exits at entry (gap_target); a missing flatten bar makes a traded day non-evaluable; 0011's missing-bar skip is applied point-in-time (no whole-evening look-ahead).
