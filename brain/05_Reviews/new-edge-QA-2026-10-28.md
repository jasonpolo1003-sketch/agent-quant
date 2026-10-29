# New-edge build QA: SC-FUT-0009 / 0010 / 0011 (2026-10-28)

Reviewer: quality agent. Scope: commits bece950 (specs), f8160d2 (build), 8b2106f (addendum) on `testing`. No market data read, no workbench run, no exam-period data.

## Verdict

The bracket engine, the three cards, `build_evenings` and the matched control match the frozen specs, with one gap: the shared Sidak split (alpha 0.0170) was not applied anywhere, so the workbench would have judged the cards at p < 0.05. That is now fixed and has a test. Nothing else is a bug. The judgement calls below are conservative or neutral, and the addendum accepts the main ones.

## Findings

### High
1. **Shared Sidak split missing (fixed).** `analysis.honesty` (src/quant_brain/workbench/analysis.py:35-48) used 1 - 0.95^(1/trials) for every family, so the first trial of each card would have been judged at alpha = 0.05. The spec (`gates.beats_luck`) requires 0.0170. **Fix:** `FAMILY_SPLIT = {fade_band: 3, gap_fill: 3, evening_revert: 3}` multiplies the Sidak count, giving 0.0170 for the first trial and 1 - 0.95^(1/(3n)) after that. Other families are unchanged. `analysis.py` is not in `engine.CODE_FILES`, so no fingerprints change. The test is `test_the_three_cards_share_one_sidak_split_of_the_honesty_bar` (tests/test_bracket_fixtures.py). It fails on HEAD and passes with the fix.

### Medium: none.

### Low / judgement calls (behaviour left unchanged)
1. **Run order MNQ, then MES.** Honesty counts distinct (settings, market, roll) rows, so if the MES diagnostic is logged first, the MNQ bar becomes 1 - 0.95^(1/6) = 0.0085. Run MNQ first so the MNQ verdict is judged at 0.0170.
2. **A missing flatten bar drops a traded day** (bracket.py:181, plus `run_bracket` returning None). This drops only traded days, and it depends on a bar after the decision. The strategy and the control are dropped together, so the paired test stays fair, but the per-day mean is computed on fewer traded days. This matters most for 0011, where evening 20:30 bars in thin 2019 MNQ may be missing. Report the `non_evaluable` count with the results. The addendum accepted this rule.
3. **Entry-bar ordering** (bracket.py:86-92). On the entry bar the stop check runs before the marketable-target check. If the bar opens beyond the target and later reaches the stop, the trade is recorded as a stop loss, although the marketable limit would have filled at the open first. This literally follows "both in one bar: stop first". It is conservative and should be very rare.
4. **Target equal to the entry** (bracket.py:91, strict `>`). When the entry open sits exactly at the target, the trade is not treated as marketable. It then needs a later 1-tick trade-through, so its gross is <= 0. Conservative, and follows the spec's trade-through wording.
5. **A target hit after a gap fills at the target, not at the better open.** Conservative. `paths` handles it correctly: adverse = target, favourable = target.
6. **A missing fill bar skips the check** (bracket.py:270, :334, :441). Whether a trade prints in the decision minute is technically known only after the decision. NoiseArea uses the same convention. It is not directional and should be rare at RTH checks.
7. **0010 "not yet filled" means the whole 08:30 bar stayed beyond the previous close** (bracket.py:332). Stricter than "close still gapped". Declared by the engineer.
8. **The 0011 missing-bar skip is point-in-time** (bracket.py:434). After the cap is crossed, an open trade keeps running. Accepted by the addendum.
9. **Control legs can overlap in time** (one-at-a-time is not enforced on the redrawn legs). This is inherent to "same entry minutes, random side". Equity uses `paths.book_*` for both sides, so lows stay comparable.

## What I verified

- **Spec fidelity.**
  - 0009: the band is exactly NoiseArea's (`prepare_all` reused; sigma from the previous 14 sessions, at least 10 values; upper/lower from max/min(open, prev close)). Strict "above the open" and "< upper", half-way rule `>=`. Stop at the band edge, target at the 08:30 open. Checks 09:00..14:30, or 11:30 when calendar exit_minute < 15:00 (early days exit at 12:12, so the 12:00 flatten bar exists). At most 3 entries; re-entry only at a check after the exit minute.
  - 0010: |gap| in [0.2, 1.0] x atr_tr_sum/14, checked exactly in integers; both ends inclusive. Entry at the 08:31 open. Target = prev_close, stop = entry ± |gap|. Flatten at 11:00 on all days.
  - 0011: P0 = 17:00 open. Checks 17:30..20:00 every 15 minutes. sigma comes from the previous 14 usable evenings (at least 10 values), with the current evening excluded. Entry band sigma < |move| < 2 sigma (addendum). Stop = P0(1 ± 2 sigma), flatten at 20:30, at most 2 entries.
  - Rounding: `to_tick` floors for longs and ceils for shorts, which puts targets toward the entry and stops away from it.
- **Look-ahead.**
  - Decisions read only the close of bar n-1. Sigma for both 0009 and 0011 uses past days only.
  - 0010's prev_close and ATR come from `build_days`' 15 prior sessions on the same contract.
  - `build_evenings` assigns trade date = CT + 7h: 17:00 on D-1 maps to D, and Sunday maps to Monday. DST is safe because the change happens at 02:00 Sunday. NYSE-closed trade dates (MLK, Thanksgiving, holidays) are dropped through the calendar.
  - It uses the instrument `build_days` selects for D, so the roll is shared. Bars are filtered by that instrument id, and practice end 2024-12-31 means the last evening read is 2024-12-30.
  - The engineer's random-future scramble test also passes.
- **Fill realism.**
  - Stop is checked before target in the same bar. A gap through the stop fills at the open. A target needs a later bar trading 1 tick through it. Flatten at the flatten bar's open.
  - `paths._minute_points` for `target` counts the exit bar's adverse extreme, and `gap_target` counts as out at the open. Only the bracket cards emit these two reasons, so other families are unaffected.
- **Luck control.**
  - One fair coin per leg via `integers(0,2)`, independent of the strategy's side. The seed is (BRACKET_SEED, root, date, card), so draws are deterministic.
  - Distances are kept, including negative ones for gap_target and gap_stop legs, which exit at entry in either direction. Fill rules are the same.
  - Trade counts are equal, so costs are applied identically through `analysis._nets`. Strategy and control lows are both gross book paths.
  - Unflipped legs reproduce the strategy: 878 / 878 legs matched on 600 random days across all three cards, with all control lows <= min(0, gross).
- **Existing results unchanged.** `noise.py`, `orb.py` and `controls.py` are untouched since d0ba1e1. `bars.py` has additions only, and `build_days` is byte-identical.

## Independent recount (SC-FUT-0010)

A from-scratch gap-fill simulator written from the spec text only (Fraction ATR band, own bar loop, own fill rules; scratch script, not in the repo) was compared trade by trade with `GapFill.simulate` on **2,000 random synthetic days**. The days were random walks with gaps of 0-1.5 ATR, missing-bar rates of 0-30%, randomly removed 08:30/08:31/11:00 bars, and missing prev_close/ATR.

**Result: 2,000 / 2,000 agree, 0 disagree** on side, entry, exit minute, exit price, reason and net. That covers 666 traded days (237 target, 242 stop, 151 flatten, 34 gap_stop, 2 gap_target) and 63 non-evaluable days.

## Tests

- Before the fix, test_bracket_fixtures had 84 tests; it now has 85, all passing.
- Full suite: 1304 passed, 4 skipped (203 s). This includes the pinned noise, pyramid, live, firm-grid, prop-simulator, multi-market and bars tests.
- ruff check and ruff format are clean on the touched files (analysis.py, test_bracket_fixtures.py).
