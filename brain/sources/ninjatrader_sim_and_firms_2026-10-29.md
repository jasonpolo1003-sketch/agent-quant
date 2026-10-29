# NinjaTrader 8 sim, data and prop-firm bot rules (research, 2026-10-29)

This was gathered by a research sub-agent. Several official pages blocked fetching. Third-party or snippet-only items are marked.

## Data for NinjaTrader's Sim101 account ($0)

- **Free NT account, "Simulation" connection:** live CME data for 14 days. After that the data is delayed, reportedly by 10 minutes (forum snippet only). Automated strategies are supported in the simulator.
  - Source: https://ninjatrader.com/trading-platform/trading-simulator/
- **"Simulated Data Feed":** synthetic prices. Use it to test the order pipeline only, never to judge a strategy.
  - Source: https://ninjatrader.com/support/helpGuides/nt8/simulated_data_feed_connection.htm
- **Tradovate demo:** 2 weeks of real-time data. It is unconfirmed whether that login feeds NT8.
  - Source: https://www.tradovate.com/trial/
- **Rithmic demo:** unreliable in NT8, according to support.
- **Kinetick:** end-of-day only.
- **Market Replay / Playback:** free in limited amounts. Unconfirmed whether ATI orders route to Playback101.
- **Bottom line:** the only free, unlimited options are delayed data or replay. Free real-time data runs for about 14 days per provider.

## ATI / OIF (Automated Trading Interface / Order Instruction Files)

- **License:** the free license includes all features, in simulation only (forum).
- **To enable:** Tools > Options > Automated trading interface > AT Interface, then restart NT8.
  - Source: https://static.ninjatrader.com/support/helpGuides/nt8/automated_trading_interface_at.htm
- **Files:** `Documents\NinjaTrader 8\incoming\oif*.txt`, semicolon-separated, processed the instant they are written.
  - Format: `PLACE;<ACCOUNT>;<INSTRUMENT>;<ACTION>;<QTY>;<ORDER TYPE>;[LIMIT];[STOP];<TIF>;[OCO];[ORDER ID];[STRATEGY];[STRATEGY ID]`
  - Source: https://static.ninjatrader.com/support/helpGuides/nt8/order_instruction_files_oif.htm
- **Gotcha: OneDrive-synced Documents folders break OIF processing.** Move the NinjaTrader 8 folder to a local drive.
  - Source: https://forum.ninjatrader.com/forum/ninjatrader-8/add-on-development/1301639-oif-files-not-processed

## Prop firms through NT8

**Tradeify**
- **Connection:** Tradovate only, under Tradeify's company license.
  - Source: https://intercom.help/tradeify/en/articles/12268716-ninjatrader-8-setup-guide
- **Bot rules** (source: https://intercom.help/tradeify/en/articles/10468318-guidelines-for-traders):
  - Personal, non-HFT bots are allowed.
  - You need proof that you are the sole owner, and they may ask for a live video of you enabling the bot.
  - They scan for similar orders on other accounts.
  - **Using the same bot at other firms is against policy.**

**Lucid**
- **Connection:** NinjaTrader via CQG/Tradovate.
  - Source: https://intercom.help/lucid-trading/en/articles/11404614-lucid-trading-supported-platforms
- **Bot rules** (source: https://support.lucidtrading.com/en/articles/11404728-other-trading-activities):
  - Automated systems and trade copiers are permitted, with no approval process described.
  - HFT, microscalping and hedging are banned.
  - No ban on using the same bot at another firm was found.

**Before running a bot at either firm:** ask support in writing whether their company NT8 license allows ATI/OIF.

## Implication for the plan

- **Tradeify vs Lucid:** if we use Tradeify, the bot cannot also run at Topstep or Lucid. Lucid is the more bot-friendly firm.
- **Practice runs:** use the 14-day live trial for the first real practice sessions. After that, use replay data, or accept that the delayed feed only tests the order plumbing.
