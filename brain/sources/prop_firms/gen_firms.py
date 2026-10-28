"""Generate draft prop-firm rule JSONs (research workstream R, 2026-10-28)."""
import json, os, sys

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
CHECKED = "2026-10-28"

# ---------- shared route text ----------
TOPSTEP_ROUTE = ("TopstepX (ProjectX) API: REST + websocket, API key auth; $29/month, $14.50 with Topstep promo code; "
                 "orders must originate from personal device (no VPS/VPN/remote server); not available on Live Funded")
NO_FIRM_API = ("No firm API. Candidate routes (all UNVERIFIED for this firm): (1) NinjaTrader 8 on own PC "
               "(NinjaScript strategy, or ATI fed by a local Python process) over the firm's Tradovate/Rithmic login; "
               "(2) Tradovate REST API: community posts say prop accounts have API access disabled; "
               "(3) Rithmic R|Protocol API: needs Rithmic dev kit + conformance approval; "
               "(4) paid third-party webhook bridges (TradersPost, PickMyTrade, CrossTrade)")

def base(**kw):
    d = {
        "firm": None, "plan": None, "account_size_usd": None, "checked": CHECKED, "status": "available",
        "has_evaluation": True,
        "price_usd": None, "billing": None, "reset_usd": None, "activation_usd": 0,
        "platform_fees_usd_per_month": 0, "api_fee_usd_per_month": 0,
        "target_usd": None, "max_loss_usd": None, "drawdown_mode": None, "drawdown_breach_intraday": True,
        "drawdown_lock": None, "drawdown_lock_level_rel_start_usd": None, "drawdown_lock_trigger_rel_start_usd": None,
        "daily_loss_usd": None, "daily_loss_kind": None,
        "eval_consistency_share": None, "eval_consistency_effect": None,
        "min_days": None, "max_micros": None, "flat_by": None,
        "funded_start_balance_usd": None, "funded_max_loss_usd": None, "funded_drawdown_mode": None,
        "funded_lock": None, "funded_lock_level_rel_start_usd": None, "funded_lock_trigger_rel_start_usd": None,
        "funded_daily_loss_usd": None, "funded_daily_loss_kind": None,
        "funded_consistency_share": None, "funded_consistency_effect": None,
        "funded_max_micros": None, "funded_scaling": None,
        "payout_min_winning_days": None, "payout_winning_day_min_usd": None,
        "payout_min_cycle_profit_usd": None, "payout_buffer_rel_start_usd": None,
        "payout_share_of_profit": None, "payout_share_of_balance": None,
        "payout_cap_usd": None, "payout_cap_schedule_usd": None, "payout_min_usd": None,
        "profit_split_trader": None, "after_payout": None, "max_payouts": None, "max_funded_accounts": None,
        "automation_allowed_eval": None, "automation_allowed_funded": None, "automation_conditions": None,
        "python_order_route": None, "python_order_route_verified": False,
        "vps_allowed": None, "hft_banned": True, "min_hold_rule": None,
        "sources": [], "unverified": [],
    }
    d.update(kw)
    return d

files = {}

# ================= TOPSTEP =================
TS_SRC = [
    "https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions (updated over a week ago, read 2026-10-28)",
    "https://help.topstep.com/en/articles/8284197-trading-combine-parameters (2026-09-24)",
    "https://help.topstep.com/en/articles/8284208-consistency-at-topstep (2026-09-17)",
    "https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit (2026-09-18)",
    "https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account (2026-06-30)",
    "https://help.topstep.com/en/articles/8284215-express-funded-account-parameters (2026-08-05)",
    "https://help.topstep.com/en/articles/8284217-express-funded-account-activation (2026-09-24)",
    "https://help.topstep.com/en/articles/8284233-topstep-payout-policy (updated over 2 weeks ago)",
    "https://help.topstep.com/en/articles/11187768-topstepx-api-access (2026-09-17)",
    "https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan (2026-07-16)",
]
ts = {
    50:  dict(std=49, naf=95, mll=2000, tgt=3000, micros=50, dll=1000, cap_std=2000, cap_con=3000, b2f=599, xfa_micros_start=20),
    100: dict(std=99, naf=149, mll=3000, tgt=6000, micros=100, dll=2000, cap_std=3000, cap_con=4000, b2f=699, xfa_micros_start=None),
    150: dict(std=199, naf=229, mll=4500, tgt=9000, micros=150, dll=3000, cap_std=5000, cap_con=6000, b2f=829, xfa_micros_start=None),
}
for k, v in ts.items():
    for plan, price, act in (("standard", v["std"], 149), ("no_activation_fee", v["naf"], 0)):
        unv = [
            "flat_by 15:10 CT carried from topstep_50k.json / 2026-10-27 note; not re-read today",
            "default (DLL not set at purchase) payout caps are payout_cap_usd; doubled caps need the optional DLL set at Combine purchase (limited-time offer, no end date)",
        ]
        if k != 50:
            unv.append("XFA lock level/trigger for 100K/150K not stated in MLL article (only the 50K example); assumed lock at $0 once XFA balance reaches +MLL")
        unv.append("XFA scaling-plan tiers are only in an image; " + ("50K starts on a 2-lot (20 micros)" if k == 50 else "starting lot size unknown"))
        if k == 150:
            unv.append("XFA Parameters page shows caps $5,000/$6,000 without size; Payout Policy size table used")
        d = base(
            firm="Topstep", plan=f"Trading Combine {k}K ({plan} path) -> Express Funded Account", account_size_usd=k * 1000,
            price_usd=price, billing="monthly", reset_usd=price, activation_usd=act,
            platform_fees_usd_per_month=0, api_fee_usd_per_month=29, api_fee_discounted_usd_per_month=14.5,
            data_fee_note="Level 1 included; Level 2 $38/month optional",
            target_usd=v["tgt"], max_loss_usd=v["mll"], drawdown_mode="eod_trailing", drawdown_breach_intraday=True,
            drawdown_lock="trails highest end-of-day balance; locks permanently once it reaches the starting balance",
            drawdown_lock_level_rel_start_usd=0, drawdown_lock_trigger_rel_start_usd=v["mll"],
            daily_loss_usd=v["dll"], daily_loss_kind="soft_pause", daily_loss_optional=True,
            daily_loss_note="optional; set at Combine purchase (fixed, carries into XFA); flattens and stops until 5 PM CT next session; not a violation. Default sim: off",
            eval_consistency_share=0.55, eval_consistency_effect="target rises to best_day / 0.55 (no fail)",
            min_days=2, min_days_note="no explicit minimum; 55% consistency implies >=2 days", max_micros=v["micros"], flat_by="15:10 CT",
            funded_start_balance_usd=0, funded_max_loss_usd=v["mll"], funded_drawdown_mode="eod_trailing",
            funded_lock="XFA starts at $0 with MLL at -MLL; trails EOD; locks at $0 once balance reaches +MLL (50K example); set to $0 after first payout",
            funded_lock_level_rel_start_usd=0, funded_lock_trigger_rel_start_usd=v["mll"],
            funded_daily_loss_usd=v["dll"], funded_daily_loss_kind="soft_pause",
            funded_consistency_share=0.40, funded_consistency_effect="consistency payout path only: blocks payout until largest day <=40% of total net profit, >=3 trading days",
            funded_max_micros=v["xfa_micros_start"], funded_scaling="scaling plan (chart image only)",
            payout_paths=["standard", "consistency"],
            payout_min_winning_days=5, payout_winning_day_min_usd=150,
            payout_consistency_path_min_days=3, payout_consistency_path_share=0.40,
            payout_share_of_balance=0.5, payout_cap_usd=v["cap_std"], payout_cap_consistency_path_usd=v["cap_con"],
            payout_cap_with_dll_usd=2 * v["cap_std"], payout_cap_consistency_path_with_dll_usd=2 * v["cap_con"],
            payout_min_usd=125, profit_split_trader=0.9,
            after_payout="MLL set to $0 permanently; winning-day count restarts (standard path needs profit since last payout)",
            max_funded_accounts=5, back2funded_usd=v["b2f"],
            automation_allowed_eval=True, automation_allowed_funded=True,
            automation_conditions="XFA parameters: automated strategies 'Yes, with conditions'; no Topstep support; HFT prohibited; API not allowed on Live Funded accounts",
            python_order_route=TOPSTEP_ROUTE, python_order_route_verified=True, vps_allowed=False,
            min_hold_rule=None, sources=TS_SRC, unverified=unv,
        )
        files[f"topstep_{k}k_{plan}.json"] = d

# ================= TRADEIFY =================
TF_COMMON = [
    "https://intercom.help/tradeify/en/articles/14369021-tradeify-pricing-reference (updated over a week ago)",
    "https://intercom.help/tradeify/en/articles/12268167-essential-trading-rules-overview (updated over a week ago)",
    "https://intercom.help/tradeify/en/articles/10468318-guidelines-for-traders (updated over a week ago)",
    "https://intercom.help/tradeify/en/articles/10495897-rules-trailing-max-drawdowns (updated over a week ago)",
    "https://intercom.help/tradeify/en/articles/10468321-rules-daily-loss-limit (updated over a week ago)",
    "https://intercom.help/tradeify/en/articles/10468320-rules-consistency-rule (updated over a week ago)",
    "https://intercom.help/tradeify/en/articles/12268494-common-faqs (updated over a week ago)",
    "https://intercom.help/tradeify/en/articles/10468221-supported-platforms (updated over a week ago)",
]
TF_AUTO = dict(
    automation_allowed_eval=True, automation_allowed_funded=True,
    automation_conditions=("bots allowed if: you prove sole ownership; no similar orders on other accounts; "
                           "live video of you enabling the code on your own PC on request; not used at other firms; not HFT"),
    python_order_route=NO_FIRM_API + ". Tradeify brokers: Tradovate (NinjaTrader, TradingView) or Rithmic (Tradesea, Quantower, Sierra Chart, R|Trader) or WealthCharts",
    vps_allowed="login must not be via VPN/VPS; after normal login VPS may be used 'at your own risk'",
    min_hold_rule="funded only: payout needs >50% of trades AND >50% of profit from trades held >10 s (blocks payout, no fail)",
    commission_mnq_round_trip_usd=1.82, flat_by="16:45 ET", max_funded_accounts=5,
)
files["tradeify_growth_50k.json"] = base(
    firm="Tradeify", plan="Growth 50K", account_size_usd=50000,
    price_usd=145, billing="one_time", reset_usd=95, activation_usd=0,
    target_usd=3000, max_loss_usd=2000, drawdown_mode="eod_trailing",
    drawdown_lock="evaluation drawdown never locks", drawdown_lock_level_rel_start_usd=None,
    daily_loss_usd=1250, daily_loss_kind="soft_pause", eval_consistency_share=None, min_days=1, max_micros=40,
    funded_start_balance_usd=50000, funded_max_loss_usd=2000, funded_drawdown_mode="eod_trailing",
    funded_lock="locks at start+$100 when EOD balance reaches start+$2,100 or when a payout is requested, whichever first",
    funded_lock_level_rel_start_usd=100, funded_lock_trigger_rel_start_usd=2100,
    funded_daily_loss_usd=1250, funded_daily_loss_kind="soft_pause",
    funded_daily_loss_rises_to_usd=2000, funded_daily_loss_rise_trigger_rel_start_usd=3000,
    funded_consistency_share=0.35, funded_consistency_effect="blocks payout until largest day <=35% of total profit",
    funded_max_micros=40,
    payout_min_winning_days=5, payout_winning_day_min_usd=150, payout_buffer_rel_start_usd=0,
    payout_min_balance_rel_start_usd=3000, payout_share_of_profit=1.0,
    payout_buffer_note="QA 2026-10-28: $53,000 is the minimum balance to REQUEST, not a buffer; official example: $53,000 balance, $1,500 request leaves $51,500 (accounts bought before 2025-09-12: $52,100)",
    payout_cap_schedule_usd=[1500, 2000, 2500, 3000], payout_min_usd=500, profit_split_trader=0.9,
    after_payout="winning-day count resets to zero; drawdown locked (lock triggered by payout request)",
    sources=TF_COMMON + ["https://intercom.help/tradeify/en/articles/10495915-growth-evaluation-accounts",
                         "https://intercom.help/tradeify/en/articles/11083796-advanced-and-growth-account-payout-policies"],
    unverified=["DLL measured on realized or net-liq not stated", "payout amount as share of profit not stated (only per-request cap)",
                "whether a self-written Python program can reach Tradeify accounts (no firm API documented)"],
    **TF_AUTO)
sel_common = dict(
    firm="Tradeify", account_size_usd=50000, billing="one_time", activation_usd=0,
    target_usd=3000, max_loss_usd=2000, drawdown_mode="eod_trailing", drawdown_lock="evaluation drawdown never locks",
    daily_loss_usd=None, daily_loss_kind=None,
    eval_consistency_share=0.40, eval_consistency_effect="cannot pass until largest day <=40% of total profit (50% with add-on)",
    min_days=3, max_micros=40, funded_start_balance_usd=50000, funded_max_loss_usd=2000, funded_drawdown_mode="eod_trailing",
    funded_lock_level_rel_start_usd=100, funded_lock_trigger_rel_start_usd=2100,
    funded_consistency_share=None, funded_max_micros=40,
    funded_scaling="starts 20 micros; EOD profit $1,500 -> 30; $2,000 -> 40 (next day)",
    payout_min_usd=250, profit_split_trader=0.9,
)
files["tradeify_select_flex_50k.json"] = base(
    plan="Select 50K (40% consistency eval) -> Select Flex funded", price_usd=165, reset_usd=109,
    price_with_50pct_consistency_addon_usd=205, reset_with_addon_usd=135,
    funded_lock="locks at start+$100 when EOD balance reaches start+$2,100 or on payout request",
    funded_daily_loss_usd=None, funded_daily_loss_kind=None,
    payout_min_winning_days=5, payout_winning_day_min_usd=150, payout_share_of_profit=0.5, payout_cap_usd=2500,
    payout_cap_note="$2,500 for accounts bought on/after 2026-09-01 ($3,000 before)",
    after_payout="cycle profit resets; needs positive net profit in each cycle; 50% computed on total profit (balance - start)",
    sources=TF_COMMON + ["https://intercom.help/tradeify/en/articles/12853921-select-evaluation-accounts",
                         "https://intercom.help/tradeify/en/articles/12853966-select-flex-and-select-daily-payout-policies"],
    unverified=["Flex vs Daily chosen after passing (permanent); same eval price"],
    **sel_common, **TF_AUTO)
files["tradeify_select_daily_50k.json"] = base(
    plan="Select 50K (40% consistency eval) -> Select Daily funded", price_usd=165, reset_usd=109,
    price_with_50pct_consistency_addon_usd=205, reset_with_addon_usd=135,
    funded_lock="locks at start+$100 when EOD balance reaches start+$2,100",
    funded_daily_loss_usd=1000, funded_daily_loss_kind="soft_pause",
    payout_min_winning_days=0, payout_buffer_rel_start_usd=2100, payout_max_cycle_profit_multiple=2,
    payout_rule="daily; may request up to 2x profit earned since previous request; cannot withdraw below start+$2,100",
    payout_cap_usd=1250, payout_cap_note="$1,250 for accounts bought on/after 2026-09-01 ($1,000 before)",
    after_payout="profit since last payout resets to zero",
    sources=TF_COMMON + ["https://intercom.help/tradeify/en/articles/12853921-select-evaluation-accounts",
                         "https://intercom.help/tradeify/en/articles/12853966-select-flex-and-select-daily-payout-policies"],
    unverified=["first-payout rule for Daily (2x profit with no prior payout) not explicit"],
    **sel_common, **TF_AUTO)
files["tradeify_lightning_50k.json"] = base(
    firm="Tradeify", plan="Lightning Funded 50K (no evaluation)", account_size_usd=50000, has_evaluation=False,
    price_usd=492, billing="one_time", reset_usd=None, activation_usd=0,
    funded_start_balance_usd=50000, funded_max_loss_usd=2000, funded_drawdown_mode="eod_trailing",
    funded_lock="locks at start+$100 when EOD balance reaches start+$2,100 or on payout request",
    funded_lock_level_rel_start_usd=100, funded_lock_trigger_rel_start_usd=2100,
    funded_daily_loss_usd=1250, funded_daily_loss_kind="soft_pause",
    funded_daily_loss_rises_to_usd=2000, funded_daily_loss_rise_trigger_rel_start_usd=3000,
    funded_consistency_share=0.20, funded_consistency_schedule=[0.20, 0.25, 0.30],
    funded_consistency_effect="payout needs total profit >= largest EOD day / share (payout 1: 20%, 2: 25%, 3+: 30%)",
    funded_max_micros=40, payout_profit_goal_schedule_usd=[3000, 2000],
    payout_min_winning_days=0, payout_cap_schedule_usd=[2000, 2000, 2000, 2500], payout_min_usd=1000, profit_split_trader=0.9,
    after_payout="next payout needs a new profit goal ($2,000); may be moved to live at Tradeify's discretion",
    sources=TF_COMMON + ["https://intercom.help/tradeify/en/articles/10495938-lightning-funded-accounts",
                         "https://intercom.help/tradeify/en/articles/10495932-lightning-funded-account-payout-policy"],
    unverified=["drawdown after payout beyond lock not described", "whether the profit goal is per cycle or cumulative"],
    **TF_AUTO)

# ================= LUCID =================
LU_COMMON = [
    "https://intercom.help/lucid-trading/en/articles/11404728-other-trading-activities (2026-08-26)",
    "https://intercom.help/lucid-trading/en/articles/11404736-prohibited-high-frequency-trading (2026-08-26)",
    "https://intercom.help/lucid-trading/en/articles/11404742-prohibited-microscalping (2026-08-26)",
    "https://intercom.help/lucid-trading/en/articles/11404614-lucid-trading-supported-platforms",
    "https://intercom.help/lucid-trading/en/articles/11404620-simulated-account-fees",
]
LU_AUTO = dict(
    automation_allowed_eval=True, automation_allowed_funded=True,
    automation_conditions="'Automated trading systems and trade copiers are permitted'; must follow all rules; trader responsible for software errors; HFT prohibited",
    python_order_route=NO_FIRM_API + ". Lucid platforms: CQG (NinjaTrader, Tradovate, TradingView) or Rithmic (Quantower, R|Trader Pro, Sierra Chart, etc.)",
    vps_allowed=None, min_hold_rule="flag if >50% of profits from trades held <=5 s (manual review; eval and funded)",
    billing="one_time", activation_usd=0,
)
LU_PRICE_UNV = "price/reset not on Lucid help centre; lucidtrading.com returns 403. BLOG figures only (inconsistent)"
files["lucid_flex_50k.json"] = base(
    firm="Lucid Trading", plan="LucidFlex 50K", account_size_usd=50000, price_usd=None, reset_usd=None,
    target_usd=3000, max_loss_usd=2000, drawdown_mode="eod_trailing",
    drawdown_lock="article says same EOD system for eval and funded: locks at start+$100 once balance exceeds start+$2,100",
    drawdown_lock_level_rel_start_usd=100, drawdown_lock_trigger_rel_start_usd=2100,
    daily_loss_usd=None, daily_loss_kind="soft_pause", daily_loss_optional=True,
    eval_consistency_share=0.40, eval_consistency_effect="cannot upgrade until largest day <=40% of profit (50% add-on); no fail",
    min_days=3, min_days_note="no explicit minimum; 'pass in as few as 3 days' (2 with 50% add-on)", max_micros=40,
    funded_start_balance_usd=50000, funded_max_loss_usd=2000, funded_drawdown_mode="eod_trailing",
    funded_lock="locks at start+$100 once balance exceeds start+$2,100; on any payout request MLL moves to locked level",
    funded_lock_level_rel_start_usd=100, funded_lock_trigger_rel_start_usd=2100,
    funded_daily_loss_usd=None, funded_daily_loss_kind="soft_pause", funded_consistency_share=None,
    funded_max_micros=40, funded_scaling="profit $0-999: 20 micros; $1,000-1,999: 30; $2,000+: 40 (set at session end)",
    payout_min_winning_days=5, payout_winning_day_min_usd=150, payout_buffer_rel_start_usd=0,
    payout_share_of_profit=0.5, payout_cap_usd=2000, payout_min_usd=500, profit_split_trader=0.9,
    after_payout="winning-day requirement restarts; net profit in cycle must be positive; MLL moves to locked level",
    max_payouts=5, max_payouts_note="after 5 payouts the account is moved live",
    sources=LU_COMMON + ["https://intercom.help/lucid-trading/en/articles/12945790-lucidflex-evaluation-account",
                         "https://intercom.help/lucid-trading/en/articles/12945795-lucidflex-funded-account",
                         "https://intercom.help/lucid-trading/en/articles/12945796-lucidflex-payouts (2026-07-28)",
                         "https://intercom.help/lucid-trading/en/articles/12945805-lucidflex-consistency-percentage",
                         "https://intercom.help/lucid-trading/en/articles/12945808-lucidflex-scaling-plan (2026-05-06)",
                         "https://intercom.help/lucid-trading/en/articles/12945815-lucidflex-drawdown (2026-08-26)",
                         "https://intercom.help/lucid-trading/en/articles/16226050-lucidflex-customization"],
    unverified=[LU_PRICE_UNV + " (LucidFlex 50K ~$146, reset ~$90 per proptradingvibes DE, unverified)",
                "optional DLL amount for LucidFlex not stated officially (BLOG: $1,200)",
                "whether the eval MLL also locks (drawdown article implies yes)",
                "automation on Lucid Live accounts not stated"],
    **LU_AUTO)
files["lucid_pro_50k.json"] = base(
    firm="Lucid Trading", plan="LucidPro 50K", account_size_usd=50000, price_usd=None, reset_usd=None,
    target_usd=3000, max_loss_usd=2000, drawdown_mode="eod_trailing",
    drawdown_lock="locks at start+$100 once balance exceeds start+$2,100 (eval and funded)",
    drawdown_lock_level_rel_start_usd=100, drawdown_lock_trigger_rel_start_usd=2100,
    daily_loss_usd=1200, daily_loss_kind="soft_pause",
    eval_consistency_share=None, eval_consistency_effect="none stated; 'pass the evaluation in one trading day'",
    min_days=1, max_micros=40,
    funded_start_balance_usd=50000, funded_max_loss_usd=2000, funded_drawdown_mode="eod_trailing",
    funded_lock="locks at start+$100 once balance exceeds start+$2,100",
    funded_lock_level_rel_start_usd=100, funded_lock_trigger_rel_start_usd=2100,
    funded_daily_loss_usd=1200, funded_daily_loss_kind="soft_pause",
    funded_daily_loss_scaling="after closing above start+$2,100: DLL = 60% of highest EOD profit (never decreases)",
    funded_consistency_share=0.40, funded_consistency_effect="per payout cycle; blocks payout until largest day <=40% of cycle profit",
    funded_max_micros=40, funded_scaling="none (max size immediately)",
    payout_min_cycle_profit_usd=500, payout_buffer_rel_start_usd=2100, payout_cap_schedule_usd=[2000, 2500],
    payout_min_usd=500, profit_split_trader=0.9, after_payout="consistency resets each cycle",
    sources=LU_COMMON + ["https://intercom.help/lucid-trading/en/articles/12890029-lucidpro-evaluation-account (2026-08-26)",
                         "https://intercom.help/lucid-trading/en/articles/12890069-lucidpro-funded-account (2026-08-26)",
                         "https://intercom.help/lucid-trading/en/articles/12890092-lucidpro-payouts",
                         "https://intercom.help/lucid-trading/en/articles/12890109-lucidpro-consistency-percentage",
                         "https://intercom.help/lucid-trading/en/articles/12890122-lucidpro-daily-loss-limit (2026-07-26)",
                         "https://intercom.help/lucid-trading/en/articles/12890136-lucidpro-drawdown (2026-08-26)"],
    unverified=[LU_PRICE_UNV + " (LucidPro 50K $129.50-$192, reset ~$115 per blogs)",
                "CONFLICT: funded page says 'No simulated payout caps' but payouts page lists $2,000 / $2,500 caps (caps used)",
                "CONFLICT: funded page says DLL optional/customisable; DLL article lists fixed $1,200",
                "number of payouts before live not stated", "drawdown after payout not stated"],
    **LU_AUTO)
files["lucid_direct_50k.json"] = base(
    firm="Lucid Trading", plan="LucidDirect 50K (straight to funded)", account_size_usd=50000, has_evaluation=False,
    price_usd=None, reset_usd=None,
    funded_start_balance_usd=50000, funded_max_loss_usd=2000, funded_drawdown_mode="eod_trailing",
    funded_lock="locks at start+$100 once balance exceeds start+$2,100",
    funded_lock_level_rel_start_usd=100, funded_lock_trigger_rel_start_usd=2100,
    funded_daily_loss_usd=1200, funded_daily_loss_kind="soft_pause",
    funded_daily_loss_scaling="after closing above start+$2,100: DLL = 60% of highest EOD profit",
    funded_consistency_share=0.20, funded_consistency_effect="per payout cycle; largest day <=20% of cycle profit; blocks payout",
    funded_max_micros=40, funded_scaling="none",
    payout_profit_goal_schedule_usd=[3000, 2500], payout_cap_schedule_usd=[2000, 2000, 2000, 2500, 2500],
    payout_min_usd=500, profit_split_trader=0.9, after_payout="profit goal and 20% consistency reset each cycle",
    max_payouts=5, max_payouts_note="caps listed for payouts 1-5 only; LucidDirect Live (Legacy) article not read",
    sources=LU_COMMON + ["https://intercom.help/lucid-trading/en/articles/12890148-luciddirect-funded-account (2026-08-26)",
                         "https://intercom.help/lucid-trading/en/articles/12890164-luciddirect-payout-objectives (2026-08-26)",
                         "https://intercom.help/lucid-trading/en/articles/12890185-luciddirect-daily-loss-limit",
                         "https://intercom.help/lucid-trading/en/articles/12890192-luciddirect-drawdown (2026-08-26)"],
    unverified=[LU_PRICE_UNV, "CONFLICT: funded page says 'No simulated payout caps' but payout page lists caps",
                "an older BLOG listing claimed no automation on LucidDirect; official Other Trading Activities page allows automation without naming plans"],
    **LU_AUTO)

# ================= FUNDEDNEXT FUTURES =================
FN_COMMON = [
    "https://helpfutures.fundednext.com/en/articles/14298560-is-the-usage-of-automated-trading-systems-eas-and-bots-allowed-in-fundednext-futures (2026-04-09)",
    "https://helpfutures.fundednext.com/en/articles/17230388-does-fundednext-futures-allow-high-frequency-trading-hft (2026-09-30)",
    "https://helpfutures.fundednext.com/en/articles/17230319-what-is-copy-group-trading-policy-at-fundednext-futures (2026-09-30)",
    "https://helpfutures.fundednext.com/en/articles/17225812-how-many-accounts-can-i-hold-with-fundednext-futures-and-what-is-the-maximum-allocation-available (2026-09-30)",
    "https://helpfutures.fundednext.com/en/articles/17228899-what-are-the-available-account-sizes-and-their-prices-in-fundednext-futures (2026-10-13)",
    "https://helpfutures.fundednext.com/en/articles/17228852-what-are-the-reset-conditions-and-fees-at-fundednext-futures (updated over 2 weeks ago)",
    "https://helpfutures.fundednext.com/en/articles/17230292-daily-loss-limit-and-maximum-loss-limit-at-fundednext-futures (2026-10-24)",
    "https://helpfutures.fundednext.com/en/articles/17230245-is-there-any-consistency-rule-to-be-followed-in-the-fundednext-futures-challenge-fundednext-account (2026-10-24)",
]
FN_AUTO = dict(
    automation_allowed_eval=True, automation_allowed_funded=True,
    automation_conditions="EAs and bots allowed in Challenge and FundedNext accounts; no support; latency abuse/order flooding banned; automated systems monitored for HFT-like speed",
    python_order_route=NO_FIRM_API + ". FundedNext futures platforms: Tradovate, NinjaTrader, TradingView",
    vps_allowed=None, max_funded_accounts=5, activation_usd=0, billing="one_time",
    min_hold_rule="micro-scalping: share of cycle profit from trades closed within 10 s; 30% warning, >=40% that profit deducted (funded) / progress paused (challenge)",
)
FN_UNV_COMMON = ["billing one-time not stated explicitly in the price article (no recurring charge mentioned)",
                 "activation fee not stated in help centre (website/blog: $0)",
                 "lock trigger derived: MLL stops trailing when it reaches start+$100, i.e. balance start+MLL+$100"]
files["fundednext_rapid_pro_50k.json"] = base(
    firm="FundedNext Futures", plan="Rapid Pro 50K", account_size_usd=50000,
    price_usd=169.99, price_list_usd=299.98, price_with_dll_addon_usd=129.99, reset_usd=174.99, reset_with_dll_addon_usd=134.99,
    target_usd=3000, max_loss_usd=2000, drawdown_mode="eod_trailing",
    drawdown_lock="stops trailing and locks at start+$100", drawdown_lock_level_rel_start_usd=100, drawdown_lock_trigger_rel_start_usd=2100,
    daily_loss_usd=None, daily_loss_kind=None, daily_loss_addon_usd=1000, daily_loss_addon_kind="soft_pause",
    eval_consistency_share=None, min_days=1, max_micros=40,
    funded_start_balance_usd=50000, funded_max_loss_usd=2000, funded_drawdown_mode="eod_trailing",
    funded_lock="locks at start+$100", funded_lock_level_rel_start_usd=100, funded_lock_trigger_rel_start_usd=2100,
    funded_daily_loss_usd=None, funded_daily_loss_kind=None,
    funded_consistency_share=0.40, funded_consistency_effect="blocks withdrawal until highest day <=40% of total profit; >=3 days",
    funded_max_micros=40, payout_frequency_days=3, payout_min_cycle_profit_usd=500, payout_min_usd=250, payout_cap_usd=1200,
    profit_split_trader=0.9, after_payout="new 3-day cycle; account concluded after 5th reward", max_payouts=5,
    sources=FN_COMMON + ["https://helpfutures.fundednext.com/en/articles/17229677-fundednext-futures-rapid-pro-challenge-all-rules (2026-09-30)",
                         "https://helpfutures.fundednext.com/en/articles/17229713-fundednext-futures-rapid-pro-fundednext-account-all-rules (2026-09-30)"],
    unverified=FN_UNV_COMMON + ["CONFLICT: Rapid Pro + DLL add-on 50K price $129.99 (price article) vs $109.99 (reset article)",
                                "share of profit withdrawable per request not stated (only $1,200 max)"],
    **FN_AUTO)
files["fundednext_rapid_daily_50k.json"] = base(
    firm="FundedNext Futures", plan="Rapid Daily 50K", account_size_usd=50000,
    price_usd=169.99, price_list_usd=299.98, reset_usd=189.99,
    target_usd=3000, max_loss_usd=2000, drawdown_mode="eod_trailing",
    drawdown_lock="locks at start+$100", drawdown_lock_level_rel_start_usd=100, drawdown_lock_trigger_rel_start_usd=2100,
    daily_loss_usd=1000, daily_loss_kind="soft_pause", eval_consistency_share=None, min_days=1, max_micros=40,
    funded_start_balance_usd=50000, funded_max_loss_usd=2000, funded_drawdown_mode="eod_trailing",
    funded_lock="locks at start+$100", funded_lock_level_rel_start_usd=100, funded_lock_trigger_rel_start_usd=2100,
    funded_daily_loss_usd=1000, funded_daily_loss_kind="soft_pause", funded_consistency_share=None, funded_max_micros=40,
    payout_min_winning_days=0, payout_buffer_rel_start_usd=2100, payout_min_cycle_profit_usd=500,
    payout_rule="any day: withdraw EOD profit above $52,100 buffer, cycle profit >= $500", payout_min_usd=250, payout_cap_usd=1200,
    profit_split_trader=0.9, after_payout="buffer stays; account concluded after 5th reward", max_payouts=5,
    sources=FN_COMMON + ["https://helpfutures.fundednext.com/en/articles/17229762-fundednext-futures-rapid-daily-challenge-all-rules (2026-09-30)",
                         "https://helpfutures.fundednext.com/en/articles/17229779-fundednext-futures-rapid-daily-fundednext-account-all-rules (2026-09-30)"],
    unverified=FN_UNV_COMMON + ["price article gives one combined Rapid Pro/Daily price table"],
    **FN_AUTO)
files["fundednext_flex_50k.json"] = base(
    firm="FundedNext Futures", plan="Flex 50K", account_size_usd=50000,
    price_usd=74.99, price_note="coupon price for first 2 purchases; $84.99 from 3rd; list $141.99", price_list_usd=141.99, reset_usd=82.99,
    target_usd=2500, max_loss_usd=1500, drawdown_mode="eod_trailing",
    drawdown_lock="locks at start+$100", drawdown_lock_level_rel_start_usd=100, drawdown_lock_trigger_rel_start_usd=1600,
    daily_loss_usd=None, daily_loss_kind=None,
    eval_consistency_share=0.40, eval_consistency_effect="no single day > 40% of the target ($1,000); otherwise target = best_day / 0.40",
    min_days=3, min_days_note="no explicit minimum; implied by 40%-of-target day cap", max_micros=30,
    funded_start_balance_usd=50000, funded_max_loss_usd=1500, funded_drawdown_mode="eod_trailing",
    funded_lock="locks at start+$100; first withdrawal moves MLL to start+$100",
    funded_lock_level_rel_start_usd=100, funded_lock_trigger_rel_start_usd=1600,
    funded_daily_loss_usd=None, funded_daily_loss_kind=None, funded_consistency_share=None, funded_max_micros=30,
    payout_min_winning_days=5, payout_winning_day_min_usd=200, payout_min_cycle_profit_usd=500,
    payout_share_of_profit=0.5, payout_base="cycle", payout_cap_usd=1500, payout_min_usd=250, profit_split_trader=0.95,
    after_payout="MLL moves to start+$100 after first withdrawal; account concluded after 5th reward", max_payouts=5,
    sources=FN_COMMON + ["https://helpfutures.fundednext.com/en/articles/17229829-fundednext-futures-flex-challenge-all-rules (2026-10-13)",
                         "https://helpfutures.fundednext.com/en/articles/17229848-fundednext-futures-flex-fundednext-account-all-rules (2026-10-25)"],
    unverified=FN_UNV_COMMON,
    **FN_AUTO)
files["fundednext_direct_50k.json"] = base(
    firm="FundedNext Futures", plan="Direct 50K (no challenge)", account_size_usd=50000, has_evaluation=False,
    price_usd=169.99, price_list_usd=283.99, reset_usd=None,
    funded_start_balance_usd=50000, funded_max_loss_usd=2000, funded_drawdown_mode="eod_trailing",
    funded_lock="locks at start+$100", funded_lock_level_rel_start_usd=100, funded_lock_trigger_rel_start_usd=2100,
    funded_daily_loss_usd=1000, funded_daily_loss_kind="soft_pause",
    funded_consistency_share=0.20, funded_consistency_scope="best_ever", funded_consistency_effect="perpetual: best day ever <=20% of current cycle profit; blocks payout",
    funded_max_micros=30, payout_buffer_rel_start_usd=2100, payout_buffer_note="must clear $2,100 buffer in current cycle; no profit goal",
    payout_min_usd=800, payout_cap_usd=1200, profit_split_trader=0.9,
    after_payout="account concluded after 5th reward", max_payouts=5,
    sources=FN_COMMON + ["https://helpfutures.fundednext.com/en/articles/17430065-fundednext-futures-direct-account-all-rules (2026-10-07)"],
    unverified=FN_UNV_COMMON + ["buffer semantics (cycle profit >= $2,100 vs balance >= start+$2,100) ambiguous"],
    **FN_AUTO)

for name, d in files.items():
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
        f.write("\n")
print(len(files), "files")
