# NinjaTrader 8 practice bot: setup (Jason)

The bot trades only **Sim** accounts. It refuses any other account, and there is no override. Setup costs $0.

## 1. Install NinjaTrader 8 and make a free account
- Download it from https://ninjatrader.com/trading-platform/trading-simulator/. No deposit is needed.
- Install it, then log in with your new NinjaTrader account. A 14-day trial of live market data starts now, so save this step for when you're ready to run practice sessions.

## 2. Keep the NinjaTrader folder out of OneDrive
NinjaTrader keeps its files in `Documents\NinjaTrader 8`. Its order files reportedly stop working inside a OneDrive-synced folder, and the bot refuses to run there.
- **Check:** open File Explorer, right-click Documents, choose Properties, then the Location tab. If the path contains `OneDrive`, it's synced.
- **Fix:** OneDrive settings > Sync and backup > Manage back up > turn off **Documents**. This moves Documents back to `C:\Users\jason\Documents`. Then restart NinjaTrader.

## 3. Connect to market data
- Go to Control Center > Connections > **Simulation**. Do **not** pick "Simulated Data Feed"; its prices are fake.
- After 14 days the free data runs about 10 minutes late. The bot detects this and stops trading, which is correct behaviour.

## 4. Turn on the Automated Trading Interface
- Tools > Options > **Automated trading interface** > tick **AT Interface** > OK.
- **Restart NinjaTrader**, then reconnect.

## 5. Install the price exporter
- Copy `ninjatrader\QuantBarExporter.cs` from this repo to `Documents\NinjaTrader 8\bin\Custom\Indicators\`.
- Control Center > New > **NinjaScript Editor**. Open QuantBarExporter and press **F5** to compile.
- **If it shows errors, send me the error text.** The file has never been compiled in real NinjaTrader before, so this is the first test.

## 6. Open a chart
- Control Center > New > Chart > instrument **MNQ** (front month, e.g. `MNQ 12-26`) > type Minute, value **1**.
- Load at least 20 days of history (the "Days to load" setting).
- Right-click the chart > Indicators > **QuantBarExporter** > Add > OK.
- Bar files will appear in `Documents\NinjaTrader 8\quant_bars\`.

## 7. Run it
From the repo folder, in PowerShell:

```powershell
$env:PYTHONPATH="src"
# Dry run first: reads the bars, sends nothing.
.venv\Scripts\python.exe scripts\live_nt.py --instrument "MNQ 12-26"
# Practice orders to the Sim101 account:
.venv\Scripts\python.exe scripts\live_nt.py --instrument "MNQ 12-26" --sim Sim101
```

- **When to start it:** before 8:25 AM Central on a trading day. It trades until the 3:00 PM close and then exits.
- **Activity log:** `reports\generated\live_nt\<date>_<mode>.jsonl`.
- **Emergency stop:** create a file called `STOP` in the repo folder. The bot closes its position and stops.

## If it stops itself (a "halt")
A halt lasts the rest of that day, even if you restart the bot.
- **"broker_state" halt:** the bot lost track of an order. It leaves the position alone, so close the MNQ position yourself in the Sim101 account.
- **Restart after fixing the cause:**
  ```powershell
  .venv\Scripts\python.exe scripts\live_nt.py --instrument "MNQ 12-26" --sim Sim101 --clear-halt "what you fixed"
  ```
- **Stray order files:** any it finds are moved to a quarantine folder and are never executed.

## Things to tell me after the first session
- Whether QuantBarExporter compiled cleanly.
- What the files in `Documents\NinjaTrader 8\outgoing\` look like: the order-state and position file names, and their contents. A few formats are unconfirmed (see `src/quant_brain/live/ninjatrader.py`).
- Whether the Sim fills matched the activity log.
