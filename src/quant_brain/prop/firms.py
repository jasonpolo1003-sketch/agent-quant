"""Prop-firm rules schema and loader (plan E1: several firms in one simulator).

One `Firm` = an evaluation phase (None for a direct-to-funded account), a funded
phase and a fee schedule, all in dollars. Balances are tracked from the phase's
start balance; every level (lock, floor after a payout, buffer) is an offset from
that start, so "locks at the starting balance" is lock 0 and "locks at start +
$100" is lock 100.

Drawdown modes (the floor is start - max_loss until it moves):
- eod_trailing: the floor follows the highest end-of-day balance; a breach is
  checked intraday on equity including open P&L (the day low), or on the close
  only if the firm says breaches are not intraday (`breach_intraday`);
- intraday_trailing: the floor follows the highest intraday equity (see firm_sim);
- static: the floor never moves.
A lock caps a trailing floor at start + lock; it never moves after that.

Daily loss: soft_pause flattens the day at -limit (not a failure); hard_fail fails
the account. An optional daily loss (Topstep's DLL) is soft, chosen at purchase,
and may raise the funded payout cap (`Firm.with_optional_daily_loss`).

Funded payouts: eligibility counts days since the last payout (winning days,
trading days, profit goal, consistency share); cap, profit goal and consistency
share may be schedules by payout number (the last entry repeats). The amount is
share x (balance - start - buffer), capped, paid if >= the minimum and the balance
stays above the post-payout floor.

Loader: research drafts in brain/_system/prop/firms/*.json, nested ("funded": {...})
or flat (funded_* and payout_* keys at the top level). Field names are mapped from
several spellings (`_ALIASES`); a value may be wrapped as {"value": x, ...}; null
in one alias yields to a value in another. A missing required field, an unknown
mode, an inconsistent lock, or a share above 1 raises ValueError. "plans" (fee
overrides, dict) and "payout_paths" (funded overrides, dict; or Topstep's list
["standard", "consistency"] with payout_consistency_path_* keys) expand one file
into variants. Assumptions where drafts give only text: after a payout the floor
moves to the lock level (override: floor_after_payout_rel_start_usd); with no
payout share but a buffer, the whole excess over the buffer can be paid; API fees
count as monthly platform fees.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

DRAWDOWN_MODES = ("eod_trailing", "intraday_trailing", "static")
DAILY_KINDS = ("soft_pause", "hard_fail")
BILLING = ("monthly", "one_time")
NEEDS_PROFIT = ("always", "after_first", "never")
CONSISTENCY_SCOPES = ("cycle", "total", "best_ever")


def _check_daily(limit: float | None, kind: str | None, where: str) -> None:
    if (limit is None) != (kind is None):
        raise ValueError(f"{where}: daily_loss_usd and daily_loss_kind must be set together")
    if kind is not None and kind not in DAILY_KINDS:
        raise ValueError(f"{where}: daily_loss_kind {kind!r} not in {DAILY_KINDS}")


def _check_share(x: float | None, name: str) -> None:
    if x is not None and not 0 < x <= 1:
        raise ValueError(f"{name} must be a share in (0, 1], got {x!r}")


@dataclass(frozen=True)
class EvalRules:
    target: float
    max_loss: float
    drawdown: str = "eod_trailing"
    lock: float | None = None  # trailing floor stops at start + lock
    daily_loss: float | None = None
    daily_loss_kind: str | None = None
    consistency: float | None = None  # best day <= share x profit, else the target rises
    min_days: int = 0  # trading days (a day with any P&L) before a pass counts
    start: float = 0.0
    breach_intraday: bool = True  # False: the floor is checked on the close only

    def __post_init__(self):
        if self.drawdown not in DRAWDOWN_MODES:
            raise ValueError(f"evaluation drawdown_mode {self.drawdown!r} not in {DRAWDOWN_MODES}")
        _check_daily(self.daily_loss, self.daily_loss_kind, "evaluation")
        _check_share(self.consistency, "eval_consistency_share")


@dataclass(frozen=True)
class FundedRules:
    max_loss: float
    payout_share: float  # of (balance - start - buffer)
    cap: float | None  # largest single payout; None = no cap
    min_payout: float
    split: float  # trader's share of a payout
    drawdown: str = "eod_trailing"
    lock: float | None = None
    daily_loss: float | None = None
    daily_loss_kind: str | None = None
    floor_after_payout: float | None = None  # floor moves to start + this and stops trailing
    winning_days: int = 0  # since the last payout, days closing >= winning_day_min
    winning_day_min: float = 0.0
    trading_days: int = 0  # since the last payout, days with any P&L
    consistency: float | None = None  # largest day <= share x profit (scope below)
    needs_profit: str = "always"  # profit since the last payout > 0: always / after_first / never
    min_profit: float | None = None  # profit since the last payout needed
    buffer: float = 0.0  # balance kept above start; only the excess can be paid
    max_payouts: int | None = None  # the account ends (not breached) after this many
    start: float = 0.0
    breach_intraday: bool = True
    cap_schedule: tuple[float, ...] | None = None  # by payout number; the last repeats
    min_profit_schedule: tuple[float, ...] | None = None
    consistency_schedule: tuple[float, ...] | None = None
    # cycle: largest day since the last payout vs profit since it; total: largest day ever vs
    # all profit since the start; best_ever: largest day ever vs profit since the last payout
    consistency_scope: str = "cycle"

    def __post_init__(self):
        if self.drawdown not in DRAWDOWN_MODES:
            raise ValueError(f"funded drawdown_mode {self.drawdown!r} not in {DRAWDOWN_MODES}")
        _check_daily(self.daily_loss, self.daily_loss_kind, "funded")
        for x in (self.consistency, *(self.consistency_schedule or ())):
            _check_share(x, "funded consistency_share")
        _check_share(self.payout_share, "payout_share")
        _check_share(self.split, "profit_split")
        if self.needs_profit not in NEEDS_PROFIT:
            raise ValueError(f"payout_needs_profit {self.needs_profit!r} not in {NEEDS_PROFIT}")
        if self.consistency_scope not in CONSISTENCY_SCOPES:
            raise ValueError(
                f"consistency_scope {self.consistency_scope!r} not in {CONSISTENCY_SCOPES}"
            )
        if self.winning_days and not self.winning_day_min:
            raise ValueError("payout_min_winning_days needs payout_winning_day_min_usd")

    def cap_at(self, k: int) -> float | None:
        """Cap of payout number k (0-based)."""
        return _at(self.cap_schedule, k) if self.cap_schedule else self.cap

    def min_profit_at(self, k: int) -> float | None:
        return _at(self.min_profit_schedule, k) if self.min_profit_schedule else self.min_profit

    def consistency_at(self, k: int) -> float | None:
        return _at(self.consistency_schedule, k) if self.consistency_schedule else self.consistency


def _at(schedule: tuple[float, ...], k: int) -> float:
    return schedule[min(k, len(schedule) - 1)]


@dataclass(frozen=True)
class Fees:
    billing: str  # "monthly": price every 21 trading days of an evaluation; "one_time"
    price: float  # evaluation, or the funded account itself when there is no evaluation
    reset: float | None  # None: a failed evaluation buys a new account at `price`
    activation: float = 0.0  # once per passed evaluation
    platform_per_month: float = 0.0  # data/platform/API, every month the bot runs
    days_per_month: int = 21

    def __post_init__(self):
        if self.billing not in BILLING:
            raise ValueError(f"billing {self.billing!r} not in {BILLING}")


@dataclass(frozen=True)
class Firm:
    name: str
    evaluation: EvalRules | None  # None: the account is bought funded (no evaluation)
    funded: FundedRules
    fees: Fees
    optional_daily_loss: float | None = None  # soft, both phases, chosen at purchase
    cap_with_optional_daily_loss: float | None = None
    max_micros: int | None = None  # evaluation; sizes above are cut to it
    funded_max_micros: int | None = None
    automation_eval: bool = True
    automation_funded: bool = True
    notes: tuple[str, ...] = field(default=(), compare=False)

    def __post_init__(self):
        if self.evaluation is None and self.fees.billing != "one_time":
            raise ValueError(f"{self.name}: a direct-to-funded account must be billed one_time")

    @property
    def automation_allowed(self) -> bool:
        return self.automation_eval and self.automation_funded

    def with_optional_daily_loss(self, on: bool) -> Firm:
        """Opt into the firm's optional daily loss limit (if any): soft in a phase that has
        no daily loss of its own, and the funded cap that comes with it."""
        if not on or self.optional_daily_loss is None:
            return self
        x = self.optional_daily_loss

        def add(r):
            if r is None or r.daily_loss is not None:
                return r
            return replace(r, daily_loss=x, daily_loss_kind="soft_pause")

        fu = add(self.funded)
        if self.cap_with_optional_daily_loss is not None:
            fu = replace(fu, cap=self.cap_with_optional_daily_loss)
        return replace(self, evaluation=add(self.evaluation), funded=fu)


# --- loader ---------------------------------------------------------------------------------

_MISSING = object()
_ABSENT = object()  # a default that is not "required"

_ALIASES: dict[str, tuple[str, ...]] = {
    # fees (top level or a plan)
    "price": ("price_usd", "eval_price_usd", "subscription_usd_per_month", "fee_usd"),
    "billing": ("billing", "billing_kind"),
    "reset": ("reset_usd", "reset_fee_usd"),
    "activation": ("activation_usd", "activation_fee_usd", "xfa_activation_usd"),
    "platform": (
        "platform_fees_usd_per_month",
        "platform_fee_usd_per_month",
        "data_fees_usd_per_month",
    ),
    "api": ("api_fee_usd_per_month", "api_fees_usd_per_month"),
    "days_per_month": ("trading_days_per_month",),
    "has_evaluation": ("has_evaluation",),
    # both phases
    "start": ("start_balance_usd", "account_size_usd"),
    "max_loss": ("max_loss_usd", "max_loss_limit_usd", "max_drawdown_usd"),
    "drawdown": ("drawdown_mode", "drawdown_type"),
    "breach_intraday": ("drawdown_breach_intraday", "breach_intraday"),
    "lock": (
        "drawdown_lock_usd",
        "drawdown_lock_floor_offset_usd",
        "drawdown_lock_level_rel_start_usd",
        "lock_level_rel_start_usd",
    ),
    "lock_trigger": (
        "drawdown_lock_trigger_rel_start_usd",
        "lock_trigger_rel_start_usd",
        "drawdown_lock_at_profit_usd",
    ),
    "daily_loss": ("daily_loss_usd", "daily_loss_limit_usd"),
    "daily_loss_kind": ("daily_loss_kind",),
    "daily_loss_optional": ("daily_loss_optional",),
    "max_micros": ("max_micros", "max_micro_contracts"),
    # evaluation
    "target": ("target_usd", "profit_target_usd"),
    "eval_consistency": ("eval_consistency_share", "consistency_best_day_max_share"),
    "min_days": ("min_days", "minimum_trading_days", "min_trading_days"),
    "automation_eval": ("automation_allowed_eval",),
    "automation_funded": ("automation_allowed_funded",),
    # funded
    "consistency": ("consistency_share", "payout_consistency_share"),
    "consistency_schedule": ("consistency_schedule",),
    "consistency_scope": ("consistency_scope",),
    "winning_days": ("payout_min_winning_days", "min_winning_days"),
    "winning_day_min": (
        "payout_winning_day_min_usd",
        "payout_winning_day_usd",
        "payout_winning_day_threshold_usd",
        "winning_day_min_usd",
    ),
    "trading_days": ("payout_min_trading_days", "payout_min_days"),
    "frequency_days": ("payout_frequency_days",),
    "buffer": ("payout_buffer_rel_start_usd", "payout_buffer_usd", "buffer_usd"),
    "payout_share": ("payout_share", "payout_share_of_balance", "payout_share_of_profit"),
    "cap": ("payout_cap_usd", "cap_usd", "max_payout_usd"),
    "cap_schedule": ("payout_cap_schedule_usd",),
    "cap_with_dll": (
        "payout_cap_with_dll_usd",
        "payout_cap_with_daily_loss_usd",
        "cap_with_dll_usd",
    ),
    "min_payout": ("payout_min_usd", "min_payout_usd"),
    "split": ("profit_split_trader", "profit_split", "payout_split"),
    "floor_after_payout": (
        "floor_after_payout_rel_start_usd",
        "floor_after_payout_usd",
        "drawdown_after_payout_usd",
    ),
    "needs_profit": ("payout_needs_profit",),
    "min_profit": ("payout_min_cycle_profit_usd", "payout_min_profit_usd"),
    "min_profit_schedule": ("payout_profit_goal_schedule_usd", "payout_min_profit_schedule_usd"),
    "max_payouts": ("max_payouts",),
}

_MODE_WORDS = {
    "eod_trailing": "eod_trailing",
    "eod": "eod_trailing",
    "end_of_day": "eod_trailing",
    "end_of_day_trailing": "eod_trailing",
    "intraday_trailing": "intraday_trailing",
    "intraday": "intraday_trailing",
    "realtime_trailing": "intraday_trailing",
    "static": "static",
    "fixed": "static",
}
_KIND_WORDS = {
    "soft_pause": "soft_pause",
    "soft": "soft_pause",
    "pause": "soft_pause",
    "hard_fail": "hard_fail",
    "hard": "hard_fail",
    "fail": "hard_fail",
    "hard_breach": "hard_fail",
}
_BILLING_WORDS = {
    "monthly": "monthly",
    "subscription": "monthly",
    "one_time": "one_time",
    "one-time": "one_time",
    "onetime": "one_time",
    "once": "one_time",
}


def _unwrap(v: Any) -> Any:
    return v["value"] if isinstance(v, dict) and "value" in v else v


def _get(c: dict, key: str, where: str, default: Any = _MISSING) -> Any:
    """The value under any alias of `key`. Null counts as a value only if no alias has one.

    Missing and no default: raise. Two aliases with different values: raise.
    """
    found = [a for a in _ALIASES[key] if a in c]
    values = [_unwrap(c[a]) for a in found if _unwrap(c[a]) is not None]
    if len({json.dumps(v) for v in values}) > 1:
        raise ValueError(f"{where}: conflicting values for {found}")
    if values:
        return values[0]
    if found:
        return None
    if default is _MISSING:
        raise ValueError(f"{where}: missing required field {_ALIASES[key][0]!r}")
    return default


def _need(c: dict, key: str, where: str) -> Any:
    """Required and not null."""
    v = _get(c, key, where)
    if v is None:
        raise ValueError(f"{where}: required field {_ALIASES[key][0]!r} is null")
    return v


def _word(v: Any, table: dict[str, str], name: str, where: str) -> str:
    out = table.get(str(v).strip().lower()) if v is not None else None
    if out is None:
        raise ValueError(f"{where}: unknown {name} {v!r}")
    return out


def _schedule(v: Any, where: str) -> tuple[float, ...] | None:
    if v is None:
        return None
    if not isinstance(v, list) or not v:
        raise ValueError(f"{where}: a schedule must be a non-empty list, got {v!r}")
    return tuple(v)


def _lock(c: dict, max_loss: float, mode: str, where: str) -> float | None:
    """Floor offset where trailing stops; null = never locks. Trailing modes must say.

    The trigger (profit at which it locks) must equal level + max loss when both are given.
    """
    named = any(a in c for a in _ALIASES["lock"] + _ALIASES["lock_trigger"])
    if not named:
        if mode == "static":
            return None
        raise ValueError(f"{where}: missing required field 'drawdown_lock_level_rel_start_usd'")
    level = _get(c, "lock", where, None)
    trigger = _get(c, "lock_trigger", where, None)
    if isinstance(level, str):
        if level.strip().lower() not in ("start", "start_balance", "starting_balance"):
            raise ValueError(f"{where}: unknown drawdown lock {level!r}")
        level = 0.0
    if level is None:
        return None if trigger is None else trigger - max_loss
    if trigger is not None and abs(trigger - max_loss - level) > 1e-6:
        raise ValueError(
            f"{where}: lock level {level} and trigger {trigger} disagree with max loss {max_loss}"
        )
    return level


def _daily(c: dict, where: str) -> tuple[float | None, str | None, bool]:
    limit = _get(c, "daily_loss", where)
    optional = bool(_get(c, "daily_loss_optional", where, False))
    kind_raw = _get(c, "daily_loss_kind", where, None)
    if limit is None:
        return None, None, False
    if kind_raw is None:
        raise ValueError(f"{where}: daily_loss_usd is set, so daily_loss_kind is required")
    return limit, _word(kind_raw, _KIND_WORDS, "daily_loss_kind", where), optional


def _evaluation(c: dict, where: str) -> tuple[EvalRules, float | None]:
    max_loss = _need(c, "max_loss", where)
    mode = _word(_get(c, "drawdown", where), _MODE_WORDS, "drawdown_mode", where)
    daily, kind, optional = _daily(c, where)
    min_days = _get(c, "min_days", where)
    ev = EvalRules(
        target=_need(c, "target", where),
        max_loss=max_loss,
        drawdown=mode,
        lock=_lock(c, max_loss, mode, where),
        daily_loss=None if optional else daily,
        daily_loss_kind=None if optional else kind,
        consistency=_get(c, "eval_consistency", where),
        min_days=int(min_days or 0),
        start=_get(c, "start", where, 0.0),
        breach_intraday=bool(_get(c, "breach_intraday", where, True)),
    )
    return ev, daily if optional else None


def _funded(fc: dict, where: str) -> tuple[FundedRules, float | None]:
    max_loss = _need(fc, "max_loss", where)
    mode = _word(_get(fc, "drawdown", where), _MODE_WORDS, "drawdown_mode", where)
    daily, kind, optional = _daily(fc, where)
    lock = _lock(fc, max_loss, mode, where)
    buffer = _get(fc, "buffer", where, None)
    share = _get(fc, "payout_share", where, None)
    if share is None:
        if buffer is None:
            raise ValueError(
                f"{where}: missing required field 'payout_share_of_profit' "
                "(or 'payout_share_of_balance', or a buffer to pay everything above)"
            )
        share = 1.0  # all profit above the buffer
    after = _get(fc, "floor_after_payout", where, _ABSENT)
    trading_days = _get(fc, "trading_days", where, None)
    if trading_days is None:
        trading_days = _get(fc, "frequency_days", where, None)
    fu = FundedRules(
        max_loss=max_loss,
        payout_share=share,
        cap=_get(fc, "cap", where),
        min_payout=_need(fc, "min_payout", where),
        split=_need(fc, "split", where),
        drawdown=mode,
        lock=lock,
        daily_loss=None if optional else daily,
        daily_loss_kind=None if optional else kind,
        floor_after_payout=lock if after is _ABSENT else after,
        winning_days=int(_get(fc, "winning_days", where, 0) or 0),
        winning_day_min=_get(fc, "winning_day_min", where, 0.0) or 0.0,
        trading_days=int(trading_days or 0),
        consistency=_get(fc, "consistency", where),
        needs_profit=_get(fc, "needs_profit", where, "always"),
        min_profit=_get(fc, "min_profit", where, None),
        buffer=buffer or 0.0,
        max_payouts=_get(fc, "max_payouts", where, None),
        start=_get(fc, "start", where, 0.0),
        breach_intraday=bool(_get(fc, "breach_intraday", where, True)),
        cap_schedule=_schedule(_get(fc, "cap_schedule", where, None), where),
        min_profit_schedule=_schedule(_get(fc, "min_profit_schedule", where, None), where),
        consistency_schedule=_schedule(_get(fc, "consistency_schedule", where, None), where),
        consistency_scope=_get(fc, "consistency_scope", where, "cycle"),
    )
    return fu, daily if optional else None


def _parse(c: dict, fc: dict, name: str) -> Firm:
    where = name
    has_eval = _get(c, "has_evaluation", where, True)
    fees = Fees(
        billing=_word(_get(c, "billing", where), _BILLING_WORDS, "billing", where),
        price=_need(c, "price", where),
        reset=_get(c, "reset", where),
        activation=_get(c, "activation", where) or 0,
        platform_per_month=(_get(c, "platform", where) or 0) + (_get(c, "api", where, 0) or 0),
        days_per_month=_get(c, "days_per_month", where, 21),
    )
    ev, e_opt = _evaluation(c, where) if has_eval else (None, None)
    fu, f_opt = _funded(fc, f"{where}.funded")
    max_micros = _get(c, "max_micros", where, None)
    return Firm(
        name=name,
        evaluation=ev,
        funded=fu,
        fees=fees,
        optional_daily_loss=e_opt if e_opt is not None else f_opt,
        cap_with_optional_daily_loss=_get(fc, "cap_with_dll", where, None),
        max_micros=max_micros,
        funded_max_micros=_get(fc, "max_micros", where, None) or max_micros,
        automation_eval=bool(_get(c, "automation_eval", where)),
        automation_funded=bool(_get(c, "automation_funded", where)),
    )


_FUNDED_KEYS = ("funded", "funded_rules", "xfa")
_FLAT_FUNDED_TOP = ("payout_", "profit_split", "max_payouts", "min_payout", "daily_loss_optional")
_CONSISTENCY_PATH = (
    "payout_consistency_path_min_days",
    "payout_consistency_path_share",
    "payout_cap_consistency_path_usd",
)


def _funded_section(c: dict) -> dict:
    """The funded rules: a nested section, or the flat funded_* (prefix dropped) + payout_* keys."""
    nested = next((c[k] for k in _FUNDED_KEYS if k in c), None)
    if nested is not None:
        if not isinstance(nested, dict):
            raise ValueError("'funded' must be an object")
        return dict(nested)
    fc = {k: v for k, v in c.items() if k.startswith(_FLAT_FUNDED_TOP)}
    fc.update({k[len("funded_") :]: v for k, v in c.items() if k.startswith("funded_")})
    return fc


def _path_variants(c: dict, fc: dict, where: str) -> dict[str | None, dict]:
    paths = c.get("payout_paths")
    if not paths:
        return {None: fc}
    if isinstance(paths, dict):
        return {name: {**fc, **over} for name, over in paths.items()}
    if paths != ["standard", "consistency"]:
        raise ValueError(f"{where}: unknown payout_paths layout {paths!r}")
    for k in _CONSISTENCY_PATH:
        if _unwrap(c.get(k)) is None:
            raise ValueError(f"{where}: missing required field {k!r} for the consistency path")
    # Topstep: the standard path counts winning days and needs profit after the first payout;
    # the consistency path counts trading days and the largest-day share, at its own caps.
    std = {**fc, "consistency_share": None, "consistency_schedule": None}
    std["payout_needs_profit"] = "after_first"
    con = {k: v for k, v in fc.items() if k not in _ALIASES["winning_days"]}
    for k in _ALIASES["cap_with_dll"] + _ALIASES["cap"] + _ALIASES["consistency"]:
        con.pop(k, None)
    con.update(
        {
            "payout_min_winning_days": 0,
            "payout_min_trading_days": _unwrap(c["payout_consistency_path_min_days"]),
            "consistency_share": _unwrap(c["payout_consistency_path_share"]),
            "payout_cap_usd": _unwrap(c["payout_cap_consistency_path_usd"]),
            "payout_cap_with_dll_usd": _unwrap(c.get("payout_cap_consistency_path_with_dll_usd")),
            "payout_needs_profit": "always",
        }
    )
    return {"standard": std, "consistency": con}


def parse_firm(c: dict, name: str) -> dict[str, Firm]:
    """Variants of one firm description: "plan/path", "plan", "path" or "default"."""
    plans = c.get("plans") or {None: {}}
    out = {}
    for plan, p_over in plans.items():
        merged = {**c, **p_over}
        for path, fc in _path_variants(merged, _funded_section(merged), name).items():
            key = "/".join(x for x in (plan, path) if x is not None) or "default"
            out[key] = _parse(merged, fc, name)
    return out


def load_firm(path: Path) -> dict[str, Firm]:
    """Variants of the firm in one research JSON file (name = the file stem)."""
    try:
        c = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name}: not valid JSON ({exc})") from exc
    try:
        return parse_firm(c, path.stem)
    except (TypeError, KeyError) as exc:
        raise ValueError(f"{path.stem}: malformed rules ({exc!r})") from exc


# --- Topstep 50K adapter (the existing rules files) ---------------------------------------


def from_legacy(rules, xfa, optional_daily_loss: float | None = None) -> Firm:
    """A `Firm` equal to `account.Rules` + `funded.XfaRules` (cap already chosen)."""
    standard = xfa.path == "standard"
    return Firm(
        name="topstep_50k",
        evaluation=EvalRules(
            target=rules.target,
            max_loss=rules.max_loss,
            drawdown="eod_trailing" if rules.trailing else "static",
            lock=0 if rules.lock_at_start and rules.trailing else None,
            consistency=rules.consistency or None,
            min_days=0,
            start=rules.start,
        ),
        funded=FundedRules(
            max_loss=xfa.max_loss,
            payout_share=xfa.payout_share,
            cap=xfa.cap,
            min_payout=xfa.min_payout,
            split=xfa.split,
            drawdown="eod_trailing",
            lock=0,
            floor_after_payout=0,
            winning_days=xfa.winning_days if standard else 0,
            winning_day_min=xfa.winning_day_min,  # unused when winning_days is 0
            trading_days=0 if standard else xfa.trading_days,
            consistency=None if standard else xfa.largest_day_share,
            needs_profit="after_first" if standard else "always",
        ),
        fees=Fees(
            billing="monthly",
            price=rules.subscription,
            reset=rules.reset,
            activation=xfa.activation,
            days_per_month=rules.days_per_month,
        ),
        optional_daily_loss=optional_daily_loss,
    )


def topstep(combine_json: Path, xfa_json: Path) -> dict[str, Firm]:
    """Topstep 50K variants "plan/path" from topstep_50k.json + topstep_50k_xfa.json.

    The DLL ($1,000, soft) is optional and doubles the payout cap: switch it on with
    `with_optional_daily_loss(True)`. The Combine locks at the start balance (lock 0)
    when the file says so; the XFA floor locks at $0 and is $0 for good after a payout.
    """
    from quant_brain.prop import funded

    c = json.loads(combine_json.read_text(encoding="utf-8"))
    x = json.loads(xfa_json.read_text(encoding="utf-8"))
    out = {}
    for plan in c["plans"]:
        rules, activation = funded.plan_rules(combine_json, plan)
        for path, p in x["paths"].items():
            xr = funded.XfaRules.from_json(xfa_json, path, dll=False, activation=activation)
            f = from_legacy(rules, xr, c.get("daily_loss_limit_usd"))
            out[f"{plan}/{path}"] = replace(
                f,
                cap_with_optional_daily_loss=p["cap_with_dll_usd"],
                max_micros=c["max_micro_contracts"],
                funded_max_micros=x.get("max_micro_contracts_verified"),
                notes=("adapter over topstep_50k.json + topstep_50k_xfa.json",),
            )
    return out


def months(days: int, days_per_month: int = 21) -> int:
    """Calendar months a run of `days` trading days touches (a month starts every 21 days)."""
    return math.ceil(days / days_per_month) if days > 0 else 0
