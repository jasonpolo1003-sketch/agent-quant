# SC-FUT-0001 — hand-worked rule fixtures (synthetic, written before the engine)

Implements the frozen spec `sc-fut-0001-spec.v1.json`. Encoded in `tests/test_futures_orb_fixtures.py`; the engine (`futures/orb.py`) and the independent reference (`futures/orb_reference.py`) must both pass. **Synthetic prices only.**

## Conventions
- Prices are integer **ticks** (0.25 point). MNQ tick = 50¢, L3 = 322¢ per round trip; MES tick = 125¢, L3 = 622¢.
- Bars are `(open, high, low, close)` labelled by minute start, CT. Range bar 08:30 = (105, 110, 100, 105) and 08:31–08:44 flat at 105, so **range high 110, low 100**.
- Any minute not listed (08:30 through the exit minute) is a **flat bar at the previous bar's close**. "Missing" means no bar.
- Stop distance **4 ticks** unless stated. Normal flatten 15:07; entry fill cutoff 14:30.

## Interpretations (confirmed by Jason 2026-10-26, with the Step 3 authorization)
- **Missing entry minute consumes that side.** The rule trades the *first* close beyond the range; if its next-minute open is missing, that side is skipped for the day (logged `entry_missing`), and a later close beyond the same side does not re-arm it. This follows "first close" literally and never chases.
- **Primary P&L with a missing minute while a stop is live** continues on the visible bars (a gap carries no information). The trade is flagged, and its stress exit is the worse of the stop and the next visible bar's adverse extreme.

## Rule fixtures (MNQ unless noted)

| ID | Bars (CT) | Expected |
|---|---|---|
| F1 long winner | 08:50 (105,112,105,111) signal; 08:51 (111,113,111,112) entry; 08:52 (112,130,112,130), then flat | Long entry 111 @08:51, stop 107; flatten 130 @15:07: +19 ticks = 950 − 322 = **+628¢** |
| F2 short winner | 08:50 (105,105,98,99); 08:51 (99,99,95,96); 08:52 (96,96,80,80) | Short entry 99, stop 103; flatten 80: +19 ticks = **+628¢** |
| F3 no breakout | all default | 0 trades, **$0**, status `no_trade` |
| F4 void range | 08:40 missing; breakout 08:50 (105,112,105,111) | status `void_range`, 0 trades, **$0** |
| F5 long stopped, then short | 08:50 (105,112,105,111); 08:51 (111,112,111,112); 08:55 (108,108,106,106); 09:00 (106,106,99,99) | Long 111, stop 107 hit @08:55 (open 108 > stop → fill at stop 107): −4 ticks = −522; short signal @09:00, entry 99 @09:01, stop 103, flatten 99: −322. Total **−844¢**, 2 trades |
| F6 stop on entry bar | 08:50 (105,112,105,111); 08:51 (111,111,106,108) | Entry 111, low 106 ≤ 107 on entry bar → exit 107 @08:51: **−522¢**; `entry_bar_stop` = true |
| F7 gap through stop | 08:50 signal; 08:51 (111,112,111,112); 08:52 (105,106,104,105) | Open 105 ≤ stop 107 → fill at open 105: −6 ticks = **−622¢** |
| F8 missing entry minute | 08:50 (105,112,105,111); 08:51 missing; 08:52 (106,106,105,105); 08:55 (105,112,105,112) | `entry_missing` logged @08:51; long side consumed, 08:55 does not trigger; 0 trades, **$0** |
| F9 gap while stop live | 08:50 signal; 08:51 (111,112,111,112); 09:00 missing; 09:01 (112,112,108,110) | Primary: not stopped (108 > 107), flatten 110: −1 tick = **−372¢**; `gap_affected`; stress exit = min(107, 108) = 107 → **stress −522¢** |
| F10 missing flatten | F1 bars with 15:07 missing | status `non_evaluable` (never a fabricated fill, never $0). Trades completed earlier that day stay on the record; statistics exclude the day by status. |
| F11 early close | F1 bars; exit minute 12:12 | Flatten @12:12 open 130: **+628¢** |
| F12a cutoff edge | first breakout 14:29 (105,112,105,111) | Entry @14:30 at 111 (allowed); flatten 111: **−322¢** |
| F12b after cutoff | first breakout 14:30 (105,112,105,111) | Fill would be 14:31 > 14:30: 0 trades, **$0** |
| F13 exit bar can't signal | 08:50 signal; 08:51 (111,112,111,112); 08:55 (108,108,98,99), then flat 99 | Long stopped @08:55 at 107 (−522); 08:55 close 99 is ignored; 08:56 close 99 signals short, entry 99 @08:57; flatten 99 (−322). Total **−844¢** |
| F14 one entry per side | F5 bars to 08:55 (long stopped); 09:10 (106,112,106,112), then flat 112 | Second long ignored; 1 trade, **−522¢** |
| F15 MES costs | F1 bars, root MES | +19 ticks × 125 = 2,375 − 622 = **+1,753¢** |
| F16 ineligible | stop distance unavailable (ATR history incomplete) | status `ineligible` |
| F17 gap to flatten (added after independent review) | F1 long entry; every bar 09:00–15:06 missing | no visible bar between the gap and the flatten → `non_evaluable` |
| F18 no cash-window bars (review) | no bars at all, valid stop | `ineligible` (data only), never a $0 day |
| F19 stress never kinder (review) | F9 bars, then 09:30 (100,101,99,100) | primary gap-stop at open 100 (−11 ticks = −872¢); stress bound = min(107, 100) = 100, so stress −872¢ = primary |
| Control pairing (review) | F6 stop on entry bar, 15:07 missing | ORB evaluable, but some control draws cannot flatten → the whole day is non-evaluable (no averaging over surviving draws) |

## ATR fixtures (`stop_distance_ticks`, 15 prior sessions `(high, low, close)` oldest first)
- **A1:** every session (110, 100, 105) → each TR = 10 ticks; 0.10 × 10 = 1.0 → **1 tick**.
- **A2:** TR mean 25 ticks (sessions (125, 100, 110) with prior close 110 → TR = max(25, 15, 10) = 25) → 2.5 → half-up → **3 ticks**.
- **A3:** TR mean 24 ticks → 2.4 → **2 ticks**.
- **A4:** TR mean 3 ticks → 0.3 → minimum **1 tick**.
- **A5:** gap uses prior close: (110, 100, 100) then fourteen × (420, 410, 415). First TR = max(10, 320, 310) = 320, the rest 10 → mean 32.14 → 3.2 → **3 ticks** (ignoring the prior close would give 1).
- **A6:** any of the 15 sessions missing → **None** (ineligible).

## Control fixtures (`controls.daily_control`)
- **C1:** ORB took 0 trades → control **$0**, no draws used.
- **C2:** all post-range bars flat at 105, ORB took 1 trade → every control trade has gross 0 → net −322 → control daily mean **−322¢**.
- **C3:** same as C2 with k = 2 → the first control trade runs to the flatten, so the second cannot be taken (logged) → mean **−322¢**.
- **C4:** determinism: same day and seed → identical draws; a different trade date → different draws.
- **C5:** all legal fill minutes missing except 10:00 → every draw enters at 10:00; rejections are counted.
