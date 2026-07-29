"""Algothon 2026 submission strategy.

Live engines
------------
1. Optimised nonlinear 100-day cross-sectional reversal.
2. Three rolling fair-value pairs:
   AENO-NWIG, SMAH-ILVX, and EORC-NGTE.
3. One-day market-adjusted CUBO reversal.

The function required by the official evaluator is getMyPosition(prcSoFar).
It returns desired TOTAL positions in integer shares, not trades.
"""



import numpy as np


# -----------------------------------------------------------------------------
# Competition setup and fixed instrument indices
# -----------------------------------------------------------------------------

N_INST = 51

DOLLAR_CAPS = np.full(N_INST, 10_000.0)
DOLLAR_CAPS[0] = 100_000.0

ALGO = 0
AENO = 1
SMAH = 10
EORC = 13
CUBO = 14
NWIG = 20
NGTE = 45
ILVX = 46

# The pair/CUBO names are removed from the broad cross-sectional sleeve so that
# the broad and dedicated engines do not fight for the same capped positions.
DEDICATED = np.array([AENO, NWIG, SMAH, ILVX, EORC, NGTE, CUBO], dtype=int)
CARVE_DEDICATED_FROM_CROSS_SECTION = True


# -----------------------------------------------------------------------------
# Engine parameters frozen from the research
# -----------------------------------------------------------------------------

# Optimised nonlinear cross-sectional reversal
CS_LOOKBACK = 100
CS_THRESHOLD = 0.50
CS_Z_CLIP = 2.50
CS_POWER = 0.50                 # square-root magnitude
CS_REBALANCE = 2
CS_GROSS_TARGET = 600_000.0

# Pair sleeve: (asset A, asset B, window, entry z, exit z, maximum hold)
PAIR_CONFIGS = (
    (AENO, NWIG, 250, 1.50, 0.25, 5),
    (SMAH, ILVX, 300, 1.25, 0.50, 40),
    (EORC, NGTE, 200, 1.00, 0.50, 10),
)
PAIR_GROSS_TARGET = 20_000.0

# CUBO one-observation idiosyncratic reversal
CUBO_REGRESSION_WINDOW = 150
CUBO_REFIT_EVERY = 20
CUBO_VOL_WINDOW = 20
CUBO_ENTRY = 0.75
CUBO_RIDGE_ALPHA = 1.0
CUBO_DOLLAR_CAP = 10_000.0

_EPS = 1e-12

# State is retained across the evaluator's sequential calls.
_CACHE: dict[str, object] = {}


# -----------------------------------------------------------------------------
# General helpers
# -----------------------------------------------------------------------------

def _simple_returns(prices: np.ndarray) -> np.ndarray:
    """Return a days x instruments simple-return matrix; day zero is 0."""
    n_days = prices.shape[1]
    out = np.zeros((n_days, N_INST), dtype=float)
    if n_days > 1:
        out[1:] = (prices[:, 1:] / prices[:, :-1] - 1.0).T
    return out


def _signal_to_dollars(signal: np.ndarray, gross_target: float) -> np.ndarray:
    """Dollar-neutralise active signals, scale gross, then apply asset caps."""
    s = np.nan_to_num(
        np.asarray(signal, dtype=float), nan=0.0, posinf=0.0, neginf=0.0
    ).copy()

    active = np.abs(s) > _EPS
    if not np.any(active):
        return np.zeros(N_INST, dtype=float)

    # Neutralise only among assets carrying a signal. Assets in the dead zone
    # remain exactly flat.
    s[active] -= np.mean(s[active])

    gross = np.sum(np.abs(s))
    if gross <= _EPS:
        return np.zeros(N_INST, dtype=float)

    dollars = gross_target * s / gross
    return np.clip(dollars, -DOLLAR_CAPS, DOLLAR_CAPS)


# -----------------------------------------------------------------------------
# 1. Optimised nonlinear cross-sectional reversal
# -----------------------------------------------------------------------------

def _cross_sectional_dollars_at_day(
    prices: np.ndarray, day_index: int
) -> np.ndarray:
    """Compute the optimised cross-sectional target for one rebalance day."""
    if day_index < CS_LOOKBACK:
        return np.zeros(N_INST, dtype=float)

    performance = (
        prices[:, day_index] / prices[:, day_index - CS_LOOKBACK] - 1.0
    )

    median = np.median(performance)
    mad = np.median(np.abs(performance - median))
    robust_scale = 1.4826 * mad

    if not np.isfinite(robust_scale) or robust_scale <= _EPS:
        return np.zeros(N_INST, dtype=float)

    z = (performance - median) / robust_scale
    abs_z = np.abs(z)

    signal = np.zeros(N_INST, dtype=float)
    active = abs_z >= CS_THRESHOLD
    clipped_magnitude = np.minimum(abs_z[active], CS_Z_CLIP)
    signal[active] = (
        -np.sign(z[active]) * np.power(clipped_magnitude, CS_POWER)
    )

    if CARVE_DEDICATED_FROM_CROSS_SECTION:
        signal[DEDICATED] = 0.0

    return _signal_to_dollars(signal, CS_GROSS_TARGET)


# -----------------------------------------------------------------------------
# 2. Rolling fair-value pair sleeve
# -----------------------------------------------------------------------------

def _pair_beta_and_z(
    log_prices: np.ndarray,
    asset_a: int,
    asset_b: int,
    window: int,
    day_index: int,
) -> tuple[float, float]:
    """Rolling OLS beta and current spread z-score for log(A) on log(B)."""
    if day_index + 1 < window:
        return np.nan, np.nan

    start = day_index - window + 1
    y = log_prices[asset_a, start : day_index + 1]
    x = log_prices[asset_b, start : day_index + 1]

    mean_x = np.mean(x)
    mean_y = np.mean(y)
    dx = x - mean_x
    dy = y - mean_y

    sum_xx = np.dot(dx, dx)
    if sum_xx <= _EPS:
        return np.nan, np.nan

    beta = np.dot(dx, dy) / sum_xx
    alpha = mean_y - beta * mean_x

    spread = y - alpha - beta * x
    spread_std = np.std(spread, ddof=0)
    if spread_std <= _EPS:
        return beta, np.nan

    return beta, spread[-1] / spread_std


def _new_pair_state() -> dict[str, float]:
    return {"direction": 0.0, "held": 0.0, "beta": np.nan}


def _update_one_pair(
    state: dict[str, float],
    beta: float,
    z_score: float,
    entry: float,
    exit_z: float,
    max_hold: int,
) -> None:
    """Apply the pair's stateful entry, exit, and maximum-hold rules."""
    if np.isfinite(beta):
        state["beta"] = beta

    if not np.isfinite(z_score):
        return

    direction = float(state["direction"])

    if direction == 0.0:
        if z_score >= entry:
            # A is rich relative to B: short A and buy beta units of B.
            state["direction"] = -1.0
            state["held"] = 0.0
        elif z_score <= -entry:
            # A is cheap relative to B: buy A and short beta units of B.
            state["direction"] = 1.0
            state["held"] = 0.0
        return

    state["held"] += 1.0

    reverted = (
        (direction == -1.0 and z_score <= exit_z)
        or (direction == 1.0 and z_score >= -exit_z)
    )
    timed_out = state["held"] >= max_hold

    if reverted or timed_out:
        state["direction"] = 0.0
        state["held"] = 0.0


def _replay_pair_states(log_prices: np.ndarray) -> list[dict[str, float]]:
    """Recover open pair states when the evaluator first supplies long history."""
    states = [_new_pair_state() for _ in PAIR_CONFIGS]
    n_days = log_prices.shape[1]

    for day_index in range(n_days):
        for state, config in zip(states, PAIR_CONFIGS):
            a, b, window, entry, exit_z, max_hold = config
            beta, z_score = _pair_beta_and_z(
                log_prices, a, b, window, day_index
            )
            _update_one_pair(
                state, beta, z_score, entry, exit_z, max_hold
            )

    return states


def _advance_pair_states(
    log_prices: np.ndarray,
    day_index: int,
    states: list[dict[str, float]],
) -> None:
    for state, config in zip(states, PAIR_CONFIGS):
        a, b, window, entry, exit_z, max_hold = config
        beta, z_score = _pair_beta_and_z(
            log_prices, a, b, window, day_index
        )
        _update_one_pair(state, beta, z_score, entry, exit_z, max_hold)


def _pair_dollars(states: list[dict[str, float]]) -> np.ndarray:
    dollars = np.zeros(N_INST, dtype=float)

    for state, config in zip(states, PAIR_CONFIGS):
        a, b, _window, _entry, _exit_z, _max_hold = config
        direction = float(state["direction"])
        beta = float(state["beta"])

        if direction == 0.0 or not np.isfinite(beta):
            continue

        weight_a = direction
        weight_b = -direction * beta
        gross_weight = abs(weight_a) + abs(weight_b)
        if gross_weight <= _EPS:
            continue

        dollars[a] += PAIR_GROSS_TARGET * weight_a / gross_weight
        dollars[b] += PAIR_GROSS_TARGET * weight_b / gross_weight

    return np.clip(dollars, -DOLLAR_CAPS, DOLLAR_CAPS)


# -----------------------------------------------------------------------------
# 3. CUBO one-day idiosyncratic reversal
# -----------------------------------------------------------------------------

def _fit_scalar_ridge(
    x: np.ndarray, y: np.ndarray, alpha: float
) -> tuple[float, float]:
    """Ridge y = intercept + beta*x, without penalising the intercept."""
    mean_x = float(np.mean(x))
    mean_y = float(np.mean(y))
    dx = x - mean_x
    dy = y - mean_y

    beta = float(np.dot(dx, dy) / (np.dot(dx, dx) + alpha))
    intercept = mean_y - beta * mean_x
    return intercept, beta


def _cubo_dollars(returns: np.ndarray) -> np.ndarray:
    """Trade against today's unusually large ALGO-adjusted CUBO return."""
    day_index = returns.shape[0] - 1
    dollars = np.zeros(N_INST, dtype=float)

    minimum_day = CUBO_REGRESSION_WINDOW + CUBO_VOL_WINDOW - 1
    if day_index < minimum_day:
        return dollars

    residuals = np.empty(CUBO_VOL_WINDOW, dtype=float)
    model_cache: dict[int, tuple[float, float]] = {}
    first_day = day_index - CUBO_VOL_WINDOW + 1

    for j, current_day in enumerate(range(first_day, day_index + 1)):
        # Refit anchors are 150, 170, 190, ... . The fit ending at an anchor
        # excludes that anchor's return, so only prior information is used.
        anchor = CUBO_REGRESSION_WINDOW + (
            (current_day - CUBO_REGRESSION_WINDOW) // CUBO_REFIT_EVERY
        ) * CUBO_REFIT_EVERY

        if anchor not in model_cache:
            fit_start = anchor - CUBO_REGRESSION_WINDOW
            x_fit = returns[fit_start:anchor, ALGO]
            y_fit = returns[fit_start:anchor, CUBO]
            model_cache[anchor] = _fit_scalar_ridge(
                x_fit, y_fit, CUBO_RIDGE_ALPHA
            )

        intercept, beta = model_cache[anchor]
        predicted = intercept + beta * returns[current_day, ALGO]
        residuals[j] = returns[current_day, CUBO] - predicted

    residual_vol = np.std(residuals, ddof=0)
    if residual_vol <= _EPS:
        return dollars

    z_score = residuals[-1] / residual_vol
    if abs(z_score) >= CUBO_ENTRY:
        # Continuous magnitude, capped at full CUBO capacity by |z| = 2.
        scaled_signal = -np.clip(z_score / 2.0, -1.0, 1.0)
        dollars[CUBO] = scaled_signal * CUBO_DOLLAR_CAP

    return dollars


# -----------------------------------------------------------------------------
# Online state management and official entry point
# -----------------------------------------------------------------------------

def _initialise_cache(prices: np.ndarray) -> None:
    n_days = prices.shape[1]
    last_day = n_days - 1

    # Recover the most recent cross-sectional rebalance target. The first valid
    # rebalance is day 100, so global even-day parity is the natural schedule.
    rebalance_day = last_day - (last_day % CS_REBALANCE)
    cs_dollars = _cross_sectional_dollars_at_day(prices, rebalance_day)

    log_prices = np.log(prices)
    pair_states = _replay_pair_states(log_prices)

    _CACHE.clear()
    _CACHE["last_n_days"] = n_days
    _CACHE["cs_dollars"] = cs_dollars
    _CACHE["pair_states"] = pair_states


def _advance_cache(prices: np.ndarray) -> None:
    previous_n_days = int(_CACHE["last_n_days"])
    current_n_days = prices.shape[1]
    log_prices = np.log(prices)

    for day_index in range(previous_n_days, current_n_days):
        if day_index % CS_REBALANCE == 0:
            _CACHE["cs_dollars"] = _cross_sectional_dollars_at_day(
                prices, day_index
            )

        _advance_pair_states(
            log_prices, day_index, _CACHE["pair_states"]
        )

    _CACHE["last_n_days"] = current_n_days


def getMyPosition(prcSoFar):
    """Return the desired total position in integer shares for all 51 assets."""
    prices = np.asarray(prcSoFar, dtype=float)

    if prices.ndim != 2 or prices.shape[0] != N_INST:
        raise ValueError(
            f"Expected prcSoFar with shape (51, numDays), got {prices.shape}"
        )
    if prices.shape[1] == 0:
        return np.zeros(N_INST, dtype=int)
    if not np.all(np.isfinite(prices)) or np.any(prices <= 0.0):
        raise ValueError("Prices must be finite and strictly positive.")

    n_days = prices.shape[1]

    # Reinitialise if this is the first call or if a caller rewinds/repeats the
    # history. Otherwise process only newly appended days.
    cached_n_days = int(_CACHE.get("last_n_days", -1))
    if not _CACHE or n_days <= cached_n_days:
        _initialise_cache(prices)
    else:
        _advance_cache(prices)

    returns = _simple_returns(prices)

    cross_sectional = np.asarray(_CACHE["cs_dollars"], dtype=float)
    pairs = _pair_dollars(_CACHE["pair_states"])
    cubo = _cubo_dollars(returns)

    target_dollars = cross_sectional + pairs + cubo
    target_dollars = np.clip(target_dollars, -DOLLAR_CAPS, DOLLAR_CAPS)

    current_prices = prices[:, -1]
    positions = np.trunc(target_dollars / current_prices).astype(np.int64)

    # Defensive share-level cap. The official evaluator also enforces this.
    share_caps = np.floor(DOLLAR_CAPS / current_prices).astype(np.int64)
    positions = np.clip(positions, -share_caps, share_caps)

    return positions.astype(int)
