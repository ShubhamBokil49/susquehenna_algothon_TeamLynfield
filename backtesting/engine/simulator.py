from numbers import Integral
from typing import Optional, Sequence

import numpy as np


DEFAULT_NUM_TEST_DAYS = 250
DEFAULT_COMMISSION_RATE = 0.0001
INSTRUMENT_0_COMMISSION_RATE = 0.00002
DEFAULT_POSITION_LIMIT_DOLLARS = 10000.0
INSTRUMENT_0_POSITION_LIMIT_DOLLARS = 100000.0
SCORE_METHOD = "susquehanna_2026"


def validate_positions(positions, n_instruments: int) -> np.ndarray:
    positions = np.asarray(positions)

    if positions.shape != (n_instruments,):
        raise ValueError(
            f"Strategy returned shape {positions.shape}, "
            f"but expected ({n_instruments},)."
        )

    if np.any(~np.isfinite(positions)):
        raise ValueError("Strategy returned NaN or infinite positions.")

    return positions.astype(int)


def _validate_optional_day(day: Optional[int], name: str) -> Optional[int]:
    if day is None:
        return None

    if isinstance(day, bool) or not isinstance(day, Integral):
        raise TypeError(f"{name} must be an integer day index.")

    return int(day)


def validate_day_window(
    n_days: int,
    start_day: Optional[int],
    end_day: Optional[int],
    num_test_days: int = DEFAULT_NUM_TEST_DAYS,
) -> tuple[int, int]:
    if n_days < 2:
        raise ValueError("Backtest requires at least two days of price data.")

    if isinstance(num_test_days, bool) or not isinstance(num_test_days, Integral):
        raise TypeError("num_test_days must be a positive integer.")

    num_test_days = int(num_test_days)

    if num_test_days < 1:
        raise ValueError("num_test_days must be a positive integer.")

    end_day = _validate_optional_day(end_day, "end_day")
    start_day = _validate_optional_day(start_day, "start_day")

    if end_day is None:
        end_day = n_days - 1

    if end_day >= n_days:
        raise ValueError(
            f"end_day must be less than the number of days ({n_days}); "
            f"got {end_day}."
        )

    if end_day < 1:
        raise ValueError("end_day must be at least 1.")

    if start_day is None:
        start_day = max(1, end_day - num_test_days + 1)

    if start_day < 1:
        raise ValueError(
            "start_day must be at least 1 because day 0 has no previous price."
        )

    if end_day < start_day:
        raise ValueError(
            f"end_day ({end_day}) must be greater than or equal to "
            f"start_day ({start_day})."
        )

    return start_day, end_day


def resolve_function_name(get_position_function, function_name: Optional[str]) -> str:
    if function_name:
        return function_name

    return getattr(get_position_function, "__name__", "getMyPosition")


def build_commission_rates(
    n_instruments: int,
    default_commission_rate: float = DEFAULT_COMMISSION_RATE,
    instrument_0_commission_rate: float = INSTRUMENT_0_COMMISSION_RATE,
) -> np.ndarray:
    rates = np.full(n_instruments, float(default_commission_rate), dtype=float)

    if n_instruments > 0:
        rates[0] = float(instrument_0_commission_rate)

    return rates


def build_position_limits(
    n_instruments: int,
    default_position_limit_dollars: float = DEFAULT_POSITION_LIMIT_DOLLARS,
    instrument_0_position_limit_dollars: float = INSTRUMENT_0_POSITION_LIMIT_DOLLARS,
) -> np.ndarray:
    limits = np.full(n_instruments, float(default_position_limit_dollars), dtype=float)

    if n_instruments > 0:
        limits[0] = float(instrument_0_position_limit_dollars)

    return limits


def _validate_rule_vector(values: np.ndarray, n_instruments: int, name: str) -> np.ndarray:
    values = np.asarray(values, dtype=float)

    if values.shape != (n_instruments,):
        raise ValueError(
            f"{name} must have shape ({n_instruments},); got {values.shape}."
        )

    if np.any(~np.isfinite(values)):
        raise ValueError(f"{name} contains NaN or infinite values.")

    if np.any(values < 0):
        raise ValueError(f"{name} must not contain negative values.")

    return values


def clip_positions_to_limit(
    desired_positions: np.ndarray,
    current_prices: np.ndarray,
    position_limit_dollars_by_instrument: np.ndarray,
) -> tuple[np.ndarray, int, np.ndarray]:
    max_shares = np.floor(
        position_limit_dollars_by_instrument / current_prices
    ).astype(int)

    clipped_positions = np.clip(
        desired_positions,
        -max_shares,
        max_shares,
    ).astype(int)

    clipped_mask = clipped_positions != desired_positions
    num_clipped = int(np.sum(clipped_mask))

    return clipped_positions, num_clipped, clipped_mask


def build_trade_log_entries(
    day: int,
    trades: np.ndarray,
    current_prices: np.ndarray,
    previous_positions: np.ndarray,
    new_positions: np.ndarray,
    commission_rates: np.ndarray,
) -> list[dict]:
    entries = []

    for instrument, signed_quantity in enumerate(trades):
        signed_quantity = int(signed_quantity)

        if signed_quantity == 0:
            continue

        price = float(current_prices[instrument])
        trade_value = float(abs(signed_quantity) * price)

        entries.append(
            {
                "day": int(day),
                "instrument": int(instrument),
                "side": "BUY" if signed_quantity > 0 else "SELL",
                "previous_position": int(previous_positions[instrument]),
                "new_position": int(new_positions[instrument]),
                "trade_quantity": abs(signed_quantity),
                "signed_quantity": signed_quantity,
                "price": price,
                "trade_value": trade_value,
                "commission": float(trade_value * commission_rates[instrument]),
            }
        )

    return entries


def calculate_drawdown(cumulative_pnl: list[float]) -> list[float]:
    drawdowns = []
    peak = float("-inf")

    for value in cumulative_pnl:
        peak = max(peak, value)
        drawdowns.append(value - peak)

    return drawdowns


def score_susquehanna_2026(
    mean_daily_pnl: float,
    std_daily_pnl: float,
    param: float = 1.0,
) -> float:
    if mean_daily_pnl <= 0 or std_daily_pnl < 1e-10:
        return float(mean_daily_pnl)

    sharpe = np.sqrt(250) * mean_daily_pnl / std_daily_pnl
    fraction = sharpe**2 / (sharpe**2 + param**2)
    return float(mean_daily_pnl * fraction)


def build_instrument_summary(
    instrument_pnl: list[list[float]],
    instrument_turnover: list[list[float]],
    instrument_commission: list[list[float]],
    positions: list[list[int]],
    trades: list[list[int]],
) -> list[dict]:
    pnl_matrix = np.asarray(instrument_pnl, dtype=float)
    turnover_matrix = np.asarray(instrument_turnover, dtype=float)
    commission_matrix = np.asarray(instrument_commission, dtype=float)
    position_matrix = np.asarray(positions, dtype=int)
    trade_matrix = np.asarray(trades, dtype=int)

    n_instruments = position_matrix.shape[1] if position_matrix.size else 0
    instrument_summary = []

    for instrument in range(n_instruments):
        instrument_daily_pnl = pnl_matrix[:, instrument]
        instrument_positions = position_matrix[:, instrument]
        instrument_trades = trade_matrix[:, instrument]

        instrument_summary.append(
            {
                "instrument": int(instrument),
                "total_pnl": float(np.sum(instrument_daily_pnl)),
                "total_trades": int(np.count_nonzero(instrument_trades)),
                "total_turnover": float(np.sum(turnover_matrix[:, instrument])),
                "total_commission": float(np.sum(commission_matrix[:, instrument])),
                "average_position": float(np.mean(instrument_positions)),
                "max_abs_position": int(np.max(np.abs(instrument_positions))),
                "best_day_pnl": float(np.max(instrument_daily_pnl)),
                "worst_day_pnl": float(np.min(instrument_daily_pnl)),
            }
        )

    return instrument_summary


def build_warnings(
    summary: dict,
    instrument_summary: list[dict],
    daily_pnl: list[float],
    clipping_events: list[dict],
    run_days: int,
    position_limit_dollars_by_instrument: np.ndarray,
) -> list[dict]:
    warnings = []
    total_commission = summary["total_commission"]
    total_gross_pnl = summary["total_gross_pnl"]
    total_turnover = summary["total_turnover"]

    commission_base = max(abs(total_gross_pnl), total_commission, 1.0)
    commission_drag = total_commission / commission_base
    if commission_drag >= 0.25:
        warnings.append(
            {
                "code": "HIGH_COMMISSION_DRAG",
                "severity": "warning",
                "message": "Commission is high relative to gross P&L.",
                "metric": "total_commission / max(abs(total_gross_pnl), total_commission, 1)",
                "value": float(commission_drag),
                "threshold": 0.25,
            }
        )

    daily_capacity = max(float(np.sum(position_limit_dollars_by_instrument)), 1.0)
    average_daily_turnover = total_turnover / max(run_days, 1)
    turnover_ratio = average_daily_turnover / daily_capacity
    if turnover_ratio >= 0.5:
        warnings.append(
            {
                "code": "HIGH_TURNOVER",
                "severity": "warning",
                "message": "Average daily turnover is high relative to available exposure.",
                "metric": "average_daily_turnover / sum(position_limits)",
                "value": float(turnover_ratio),
                "threshold": 0.5,
            }
        )

    clipping_rate = len(clipping_events) / max(run_days, 1)
    if clipping_rate >= 0.25:
        warnings.append(
            {
                "code": "FREQUENT_CLIPPING",
                "severity": "warning",
                "message": "Requested positions are frequently clipped by limits.",
                "metric": "clipping_event_days / run_days",
                "value": float(clipping_rate),
                "threshold": 0.25,
            }
        )

    mean_daily_pnl = summary["mean_daily_pnl"]
    std_daily_pnl = summary["std_daily_pnl"]
    volatility_ratio = std_daily_pnl / max(abs(mean_daily_pnl), 1.0)
    if len(daily_pnl) > 1 and volatility_ratio >= 2.0:
        warnings.append(
            {
                "code": "HIGH_DAILY_PNL_VOLATILITY",
                "severity": "warning",
                "message": "Daily P&L volatility is high relative to average daily P&L.",
                "metric": "std_daily_pnl / max(abs(mean_daily_pnl), 1)",
                "value": float(volatility_ratio),
                "threshold": 2.0,
            }
        )

    pnl_denominator = sum(abs(item["total_pnl"]) for item in instrument_summary)
    if pnl_denominator > 0:
        max_pnl_share = max(
            abs(item["total_pnl"]) / pnl_denominator for item in instrument_summary
        )
        if max_pnl_share >= 0.6:
            warnings.append(
                {
                    "code": "PNL_CONCENTRATION",
                    "severity": "warning",
                    "message": "P&L is concentrated in a small number of instruments.",
                    "metric": "max_abs_instrument_pnl / sum_abs_instrument_pnl",
                    "value": float(max_pnl_share),
                    "threshold": 0.6,
                }
            )

    return warnings


def _normalise_tickers(
    tickers: Optional[Sequence[str]],
    n_instruments: int,
) -> list[str] | None:
    if tickers is None:
        return None

    tickers = list(tickers)

    if len(tickers) != n_instruments:
        raise ValueError(
            f"tickers must have length {n_instruments}; got {len(tickers)}."
        )

    return [str(ticker) for ticker in tickers]


def run_backtest(
    prices: np.ndarray,
    get_position_function,
    commission_rate: float = DEFAULT_COMMISSION_RATE,
    position_limit_dollars: float = DEFAULT_POSITION_LIMIT_DOLLARS,
    instrument_0_commission_rate: float = INSTRUMENT_0_COMMISSION_RATE,
    instrument_0_position_limit_dollars: float = INSTRUMENT_0_POSITION_LIMIT_DOLLARS,
    start_day: Optional[int] = None,
    end_day: Optional[int] = None,
    function_name: Optional[str] = None,
    num_test_days: int = DEFAULT_NUM_TEST_DAYS,
    tickers: Optional[Sequence[str]] = None,
) -> dict:
    """
    Backtest on provided data using the 2026 Susquehanna eval timing.

    The first loop opens an unscored warm-up position. Scored daily P&L starts
    on start_day and the final loop marks positions without opening new trades.
    """
    n_instruments, n_days = prices.shape
    start_day, end_day = validate_day_window(
        n_days=n_days,
        start_day=start_day,
        end_day=end_day,
        num_test_days=num_test_days,
    )
    function_name = resolve_function_name(get_position_function, function_name)
    tickers = _normalise_tickers(tickers, n_instruments)

    commission_rates = _validate_rule_vector(
        build_commission_rates(
            n_instruments=n_instruments,
            default_commission_rate=commission_rate,
            instrument_0_commission_rate=instrument_0_commission_rate,
        ),
        n_instruments=n_instruments,
        name="commission_rates",
    )
    position_limits = _validate_rule_vector(
        build_position_limits(
            n_instruments=n_instruments,
            default_position_limit_dollars=position_limit_dollars,
            instrument_0_position_limit_dollars=instrument_0_position_limit_dollars,
        ),
        n_instruments=n_instruments,
        name="position_limit_dollars_by_instrument",
    )

    current_positions = np.zeros(n_instruments, dtype=int)

    daily_records = []
    daily_pnl = []
    gross_daily_pnl = []
    cumulative_pnl = []
    position_history = []
    trade_history = []
    daily_turnover = []
    daily_commission = []
    instrument_pnl_history = []
    instrument_turnover_history = []
    instrument_commission_history = []
    trade_logs = []
    clipping_events = []

    cash = 0.0
    portfolio_value = 0.0
    running_pnl = 0.0
    running_gross_pnl = 0.0
    pending_commission_by_instrument = np.zeros(n_instruments, dtype=float)
    pending_turnover_by_instrument = np.zeros(n_instruments, dtype=float)
    pending_trade_count = 0
    pending_num_clipped = 0

    for eval_day in range(start_day, end_day + 2):
        price_day = eval_day - 1
        prices_so_far = prices[:, :eval_day]
        current_prices = prices_so_far[:, -1]
        previous_prices = prices[:, price_day - 1]
        previous_positions = current_positions.copy()

        charged_commission_by_instrument = pending_commission_by_instrument.copy()
        charged_turnover_by_instrument = pending_turnover_by_instrument.copy()
        charged_commission = float(np.sum(charged_commission_by_instrument))
        charged_turnover = float(np.sum(charged_turnover_by_instrument))
        charged_trade_count = pending_trade_count
        charged_num_clipped = pending_num_clipped

        if eval_day <= end_day:
            try:
                desired_positions = get_position_function(prices_so_far)
            except Exception as exc:
                raise RuntimeError(
                    f"Strategy function {function_name} crashed on day {price_day} "
                    f"with prices_so_far shape {prices_so_far.shape}: {exc}"
                ) from exc

            try:
                desired_positions = validate_positions(desired_positions, n_instruments)
            except ValueError as exc:
                raise ValueError(
                    f"Strategy function {function_name} returned invalid positions "
                    f"on day {price_day} with prices_so_far shape "
                    f"{prices_so_far.shape}: {exc}"
                ) from exc

            clipped_positions, num_clipped, clipped_mask = clip_positions_to_limit(
                desired_positions=desired_positions,
                current_prices=current_prices,
                position_limit_dollars_by_instrument=position_limits,
            )
        else:
            clipped_positions = current_positions.copy()
            num_clipped = 0
            clipped_mask = np.zeros(n_instruments, dtype=bool)

        trades = clipped_positions - previous_positions
        trade_values = trades * current_prices
        current_turnover_by_instrument = np.abs(trade_values).astype(float)
        current_commission_by_instrument = (
            current_turnover_by_instrument * commission_rates
        )
        current_trade_count = int(np.count_nonzero(trades))

        day_trade_logs = build_trade_log_entries(
            day=price_day,
            trades=trades,
            current_prices=current_prices,
            previous_positions=previous_positions,
            new_positions=clipped_positions,
            commission_rates=commission_rates,
        )
        trade_logs.extend(day_trade_logs)

        if num_clipped > 0:
            clipping_events.append(
                {
                    "day": int(price_day),
                    "num_clipped_instruments": int(num_clipped),
                    "instruments": [
                        int(instrument)
                        for instrument in np.flatnonzero(clipped_mask)
                    ],
                }
            )

        cash -= float(current_prices.dot(trades)) + charged_commission
        current_positions = clipped_positions
        position_value = float(current_positions.dot(current_prices))
        net_pnl = cash + position_value - portfolio_value
        portfolio_value = cash + position_value

        instrument_gross_pnl = previous_positions * (current_prices - previous_prices)
        instrument_net_pnl = (
            instrument_gross_pnl - charged_commission_by_instrument
        )
        gross_pnl = float(np.sum(instrument_gross_pnl))

        if eval_day > start_day:
            running_gross_pnl += gross_pnl
            running_pnl += net_pnl

            daily_pnl.append(float(net_pnl))
            gross_daily_pnl.append(gross_pnl)
            cumulative_pnl.append(running_pnl)
            position_history.append(current_positions.tolist())
            trade_history.append(trades.tolist())
            daily_turnover.append(charged_turnover)
            daily_commission.append(charged_commission)
            instrument_pnl_history.append(instrument_net_pnl.astype(float).tolist())
            instrument_turnover_history.append(
                charged_turnover_by_instrument.astype(float).tolist()
            )
            instrument_commission_history.append(
                charged_commission_by_instrument.astype(float).tolist()
            )

            daily_records.append(
                {
                    "day": int(price_day),
                    "gross_pnl": gross_pnl,
                    "net_pnl": float(net_pnl),
                    "cumulative_pnl": running_pnl,
                    "turnover": charged_turnover,
                    "commission": charged_commission,
                    "num_traded_instruments": int(charged_trade_count),
                    "num_clipped_instruments": int(charged_num_clipped),
                }
            )

        pending_commission_by_instrument = current_commission_by_instrument
        pending_turnover_by_instrument = current_turnover_by_instrument
        pending_trade_count = current_trade_count
        pending_num_clipped = int(num_clipped)

    drawdown = calculate_drawdown(cumulative_pnl)

    mean_daily_pnl = float(np.mean(daily_pnl)) if daily_pnl else 0.0
    std_daily_pnl = float(np.std(daily_pnl)) if daily_pnl else 0.0
    score = score_susquehanna_2026(mean_daily_pnl, std_daily_pnl)
    max_drawdown = float(min(drawdown)) if drawdown else 0.0
    run_days = int(end_day - start_day + 1)

    instrument_summary = build_instrument_summary(
        instrument_pnl=instrument_pnl_history,
        instrument_turnover=instrument_turnover_history,
        instrument_commission=instrument_commission_history,
        positions=position_history,
        trades=trade_history,
    )

    summary = {
        "score": float(score),
        "total_pnl": float(running_pnl),
        "total_gross_pnl": float(running_gross_pnl),
        "mean_daily_pnl": mean_daily_pnl,
        "std_daily_pnl": std_daily_pnl,
        "max_drawdown": max_drawdown,
        "total_commission": float(np.sum(daily_commission)),
        "total_turnover": float(np.sum(daily_turnover)),
        "total_trades": len(trade_logs),
        "clipping_event_count": len(clipping_events),
    }

    warnings = build_warnings(
        summary=summary,
        instrument_summary=instrument_summary,
        daily_pnl=daily_pnl,
        clipping_events=clipping_events,
        run_days=run_days,
        position_limit_dollars_by_instrument=position_limits,
    )

    metadata = {
        "n_instruments": int(n_instruments),
        "n_days": int(n_days),
        "start_day": int(start_day),
        "end_day": int(end_day),
        "run_days": run_days,
        "commission_rate": float(commission_rate),
        "position_limit_dollars": float(position_limit_dollars),
        "strategy_function_name": function_name,
        "deterministic": True,
        "uses_simulated_price_data": False,
        "num_test_days": int(num_test_days),
        "score_method": SCORE_METHOD,
        "commission_rates": commission_rates.astype(float).tolist(),
        "position_limit_dollars_by_instrument": position_limits.astype(float).tolist(),
    }

    if tickers is not None:
        metadata["tickers"] = tickers

    return {
        "metadata": metadata,
        "summary": summary,
        "daily_records": daily_records,
        "series": {
            "days": [record["day"] for record in daily_records],
            "daily_pnl": daily_pnl,
            "gross_daily_pnl": gross_daily_pnl,
            "cumulative_pnl": cumulative_pnl,
            "drawdown": drawdown,
            "daily_turnover": daily_turnover,
            "daily_commission": daily_commission,
        },
        "positions": position_history,
        "trades": trade_history,
        "trade_logs": trade_logs,
        "instrument_summary": instrument_summary,
        "warnings": warnings,
        "clipping_events": clipping_events,
    }
