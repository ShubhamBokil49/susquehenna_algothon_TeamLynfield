"""Algothon 2026 submission strategy.

Live engines
------------
1. Optimised nonlinear 100-day cross-sectional reversal.
2. Filtered 13-pair rolling fair-value sleeve.
3. One-day market-adjusted CUBO reversal.
4. Regime-gated 10-day time-series momentum.

The official evaluator calls getMyPosition(prcSoFar).
The function returns desired TOTAL positions in integer shares, not trades.
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
ELLT = 4
HETT = 7
HUXZ = 8
SMAH = 10
EORC = 13
CUBO = 14
RTTH = 18
NWIG = 20
CTGI = 25
ALUT = 26
ACAC = 27
ACIX = 31
CCNS = 32
MTNS = 33
NAYO = 35
FWWG = 36
EELT = 37
HRND = 38
ULXY = 40
BLBT = 41
BENI = 42
ITPA = 43
NGTE = 45
ILVX = 46
FCSG = 47
MHRM = 49
EAFC = 50

# Remove dedicated pair/CUBO assets from the broad cross-sectional sleeve so
# the engines do not fight for the same capped positions.
DEDICATED = np.array(
    [AENO, NWIG, SMAH, ILVX, EORC, NGTE, CUBO],
    dtype=int,
)
CARVE_DEDICATED_FROM_CROSS_SECTION = True

# HRND and ELLT were persistent broad-engine losers in the diagnostic pass.
# They remain available to dedicated pair trading where applicable.
BROAD_EXCLUDED = np.array([ELLT, HRND], dtype=int)


# -----------------------------------------------------------------------------
# Frozen strategy parameters
# -----------------------------------------------------------------------------

# Optimised nonlinear cross-sectional reversal
CS_LOOKBACK = 100
CS_THRESHOLD = 0.50
CS_Z_CLIP = 2.50
CS_POWER = 0.50          # Square-root weighting
CS_REBALANCE = 2
CS_GROSS_TARGET = 600_000.0

# Pair sleeve: (asset A, asset B, window, entry z, exit z, maximum hold)
PAIR_CONFIGS = (
    (SMAH, ILVX, 250, 1.00, 0.00, 40),
    (AENO, NWIG, 250, 1.00, 0.00, 40),
    (EORC, NGTE, 250, 1.00, 0.00, 40),
    (HUXZ, ACAC, 250, 1.00, 0.00, 40),
    (MHRM, EAFC, 250, 1.00, 0.00, 40),
    (HETT, ULXY, 250, 1.00, 0.00, 40),
    (CTGI, EELT, 250, 1.00, 0.00, 40),
    (RTTH, NAYO, 250, 1.00, 0.00, 40),
    (FWWG, BLBT, 250, 1.00, 0.00, 40),
    (ACIX, ITPA, 250, 1.00, 0.00, 40),
    (MTNS, BENI, 250, 1.00, 0.00, 40),
    (ALUT, CCNS, 250, 1.00, 0.00, 40),
    (NAYO, BLBT, 250, 1.00, 0.00, 40),
)
PAIR_GROSS_TARGET = 20_000.0

# CUBO one-day idiosyncratic reversal
CUBO_REGRESSION_WINDOW = 150
CUBO_REFIT_EVERY = 20
CUBO_VOL_WINDOW = 20
CUBO_ENTRY = 0.75
CUBO_RIDGE_ALPHA = 1.0
CUBO_DOLLAR_CAP = 10_000.0

# Regime-gated time-series momentum
MOM_LOOKBACK = 10
MOM_REBALANCE = 10

# Fixed three-state Gaussian Markov model fitted only on days 0-799.
# State order: neutral, bear, bull. Momentum is active only in neutral.
HMM_TRANSITION = np.array([
    [0.892378611, 0.0643955214, 0.0659306739],
    [0.0644705831, 0.935603527, 0.000000685128457],
    [0.0431508056, 0.000000951905668, 0.934068641],
], dtype=float)
HMM_MEANS = np.array([0.00503728789, -0.0411799858, 0.0577908314])
HMM_VARIANCES = np.array([0.000190761901, 0.000382625094, 0.000665301737])
HMM_INITIAL = np.array([0.37655522, 0.37699119, 0.24645359])
HMM_NEUTRAL_STATE = 0
HMM_TREND_LOOKBACK = 20

EPS = 1e-12

# Retained between sequential evaluator calls.
CACHE = {}


# -----------------------------------------------------------------------------
# General helpers
# -----------------------------------------------------------------------------

def _simple_returns(prices):
    """Return a days-by-instruments simple-return matrix."""
    n_days = prices.shape[1]
    returns = np.zeros((n_days, N_INST), dtype=float)

    if n_days > 1:
        returns[1:] = (prices[:, 1:] / prices[:, :-1] - 1.0).T

    return returns


def _signal_to_dollars(signal, gross_target):
    """Neutralise active signals, scale gross exposure, and apply caps."""
    signal = np.nan_to_num(
        np.asarray(signal, dtype=float),
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    ).copy()

    active = np.abs(signal) > EPS
    if not np.any(active):
        return np.zeros(N_INST, dtype=float)

    # Neutralise only assets with a live signal. Dead-zone assets remain flat.
    signal[active] -= np.mean(signal[active])

    gross = np.sum(np.abs(signal))
    if gross <= EPS:
        return np.zeros(N_INST, dtype=float)

    target_dollars = gross_target * signal / gross
    return np.clip(target_dollars, -DOLLAR_CAPS, DOLLAR_CAPS)


# -----------------------------------------------------------------------------
# 1. Optimised nonlinear cross-sectional reversal
# -----------------------------------------------------------------------------

def _cross_sectional_dollars_at_day(prices, day_index):
    """Calculate the cross-sectional target for a rebalance day."""
    if day_index < CS_LOOKBACK:
        return np.zeros(N_INST, dtype=float)

    performance = (
        prices[:, day_index] / prices[:, day_index - CS_LOOKBACK] - 1.0
    )

    median_performance = np.median(performance)
    mad = np.median(np.abs(performance - median_performance))
    robust_scale = 1.4826 * mad

    if not np.isfinite(robust_scale) or robust_scale <= EPS:
        return np.zeros(N_INST, dtype=float)

    z_score = (performance - median_performance) / robust_scale
    abs_z = np.abs(z_score)

    signal = np.zeros(N_INST, dtype=float)
    active = abs_z >= CS_THRESHOLD

    clipped_magnitude = np.minimum(abs_z[active], CS_Z_CLIP)
    signal[active] = (
        -np.sign(z_score[active])
        * np.power(clipped_magnitude, CS_POWER)
    )

    if CARVE_DEDICATED_FROM_CROSS_SECTION:
        signal[DEDICATED] = 0.0

    signal[BROAD_EXCLUDED] = 0.0

    return _signal_to_dollars(signal, CS_GROSS_TARGET)


# -----------------------------------------------------------------------------
# 2. Rolling fair-value pair sleeve
# -----------------------------------------------------------------------------

def _pair_beta_and_z(log_prices, asset_a, asset_b, window, day_index):
    """Calculate rolling OLS beta and the current spread z-score."""
    if day_index + 1 < window:
        return np.nan, np.nan

    start = day_index - window + 1
    y = log_prices[asset_a, start:day_index + 1]
    x = log_prices[asset_b, start:day_index + 1]

    mean_x = np.mean(x)
    mean_y = np.mean(y)

    dx = x - mean_x
    dy = y - mean_y

    sum_xx = np.dot(dx, dx)
    if sum_xx <= EPS:
        return np.nan, np.nan

    beta = np.dot(dx, dy) / sum_xx
    alpha = mean_y - beta * mean_x

    spread = y - alpha - beta * x
    spread_std = np.std(spread, ddof=0)

    if spread_std <= EPS:
        return beta, np.nan

    # The fitted intercept makes the in-window spread mean approximately zero.
    z_score = spread[-1] / spread_std
    return beta, z_score


def _new_pair_state():
    return {
        "direction": 0.0,
        "held": 0.0,
        "beta": np.nan,
    }


def _update_one_pair(state, beta, z_score, entry, exit_z, max_hold):
    """Apply the pair entry, exit, and maximum-holding-period rules."""
    if np.isfinite(beta):
        state["beta"] = beta

    if not np.isfinite(z_score):
        return

    direction = float(state["direction"])

    if direction == 0.0:
        if z_score >= entry:
            # Asset A is rich relative to B: short A and buy B.
            state["direction"] = -1.0
            state["held"] = 0.0

        elif z_score <= -entry:
            # Asset A is cheap relative to B: buy A and short B.
            state["direction"] = 1.0
            state["held"] = 0.0

        return

    state["held"] += 1.0

    reverted = (
        (direction == -1.0 and z_score <= exit_z)
        or
        (direction == 1.0 and z_score >= -exit_z)
    )
    timed_out = state["held"] >= max_hold

    if reverted or timed_out:
        state["direction"] = 0.0
        state["held"] = 0.0


def _replay_pair_states(log_prices):
    """Reconstruct pair states when the first call contains long history."""
    states = [_new_pair_state() for _ in PAIR_CONFIGS]
    n_days = log_prices.shape[1]

    for day_index in range(n_days):
        for state, config in zip(states, PAIR_CONFIGS):
            asset_a, asset_b, window, entry, exit_z, max_hold = config

            beta, z_score = _pair_beta_and_z(
                log_prices,
                asset_a,
                asset_b,
                window,
                day_index,
            )

            _update_one_pair(
                state,
                beta,
                z_score,
                entry,
                exit_z,
                max_hold,
            )

    return states


def _advance_pair_states(log_prices, day_index, states):
    """Advance all pair states by one newly supplied price day."""
    for state, config in zip(states, PAIR_CONFIGS):
        asset_a, asset_b, window, entry, exit_z, max_hold = config

        beta, z_score = _pair_beta_and_z(
            log_prices,
            asset_a,
            asset_b,
            window,
            day_index,
        )

        _update_one_pair(
            state,
            beta,
            z_score,
            entry,
            exit_z,
            max_hold,
        )


def _pair_dollars(states):
    """Convert all active pair states into target dollar positions."""
    target_dollars = np.zeros(N_INST, dtype=float)

    for state, config in zip(states, PAIR_CONFIGS):
        asset_a, asset_b, _, _, _, _ = config
        direction = float(state["direction"])
        beta = float(state["beta"])

        if direction == 0.0 or not np.isfinite(beta):
            continue

        weight_a = direction
        weight_b = -direction * beta

        gross_weight = abs(weight_a) + abs(weight_b)
        if gross_weight <= EPS:
            continue

        target_dollars[asset_a] += (
            PAIR_GROSS_TARGET * weight_a / gross_weight
        )
        target_dollars[asset_b] += (
            PAIR_GROSS_TARGET * weight_b / gross_weight
        )

    return np.clip(target_dollars, -DOLLAR_CAPS, DOLLAR_CAPS)


# -----------------------------------------------------------------------------
# 3. CUBO one-day idiosyncratic reversal
# -----------------------------------------------------------------------------

def _fit_scalar_ridge(x, y, alpha):
    """Fit y = intercept + beta*x with ridge applied only to beta."""
    mean_x = float(np.mean(x))
    mean_y = float(np.mean(y))

    dx = x - mean_x
    dy = y - mean_y

    beta = float(np.dot(dx, dy) / (np.dot(dx, dx) + alpha))
    intercept = mean_y - beta * mean_x

    return intercept, beta


def _cubo_dollars(returns):
    """Trade against an unusually large ALGO-adjusted CUBO return."""
    day_index = returns.shape[0] - 1
    target_dollars = np.zeros(N_INST, dtype=float)

    minimum_day = CUBO_REGRESSION_WINDOW + CUBO_VOL_WINDOW - 1
    if day_index < minimum_day:
        return target_dollars

    residuals = np.empty(CUBO_VOL_WINDOW, dtype=float)
    model_cache = {}
    first_day = day_index - CUBO_VOL_WINDOW + 1

    for residual_index, current_day in enumerate(
        range(first_day, day_index + 1)
    ):
        # Refit anchors are 150, 170, 190, ... . The fitting window excludes
        # the anchor return, ensuring each prediction uses only prior returns.
        anchor = CUBO_REGRESSION_WINDOW + (
            (current_day - CUBO_REGRESSION_WINDOW)
            // CUBO_REFIT_EVERY
        ) * CUBO_REFIT_EVERY

        if anchor not in model_cache:
            fit_start = anchor - CUBO_REGRESSION_WINDOW

            x_fit = returns[fit_start:anchor, ALGO]
            y_fit = returns[fit_start:anchor, CUBO]

            model_cache[anchor] = _fit_scalar_ridge(
                x_fit,
                y_fit,
                CUBO_RIDGE_ALPHA,
            )

        intercept, beta = model_cache[anchor]
        predicted_return = intercept + beta * returns[current_day, ALGO]

        residuals[residual_index] = (
            returns[current_day, CUBO] - predicted_return
        )

    residual_volatility = np.std(residuals, ddof=0)
    if residual_volatility <= EPS:
        return target_dollars

    z_score = residuals[-1] / residual_volatility

    if abs(z_score) >= CUBO_ENTRY:
        # Continuous sizing. Full CUBO capacity is reached at |z| = 2.
        scaled_signal = -np.clip(z_score / 2.0, -1.0, 1.0)
        target_dollars[CUBO] = scaled_signal * CUBO_DOLLAR_CAP

    return target_dollars


# -----------------------------------------------------------------------------
# 4. Regime-gated 10-day time-series momentum
# -----------------------------------------------------------------------------

def _market_trend_feature(prices, day_index):
    """20-day return of an equal-weight index built from daily asset returns."""
    if day_index < HMM_TREND_LOOKBACK:
        return np.nan

    daily_returns = prices[:, 1:day_index + 1] / prices[:, :day_index] - 1.0
    market_returns = np.mean(daily_returns, axis=0)
    market_index = np.cumprod(1.0 + market_returns)

    # market_index[k] corresponds to price day k + 1.
    current = market_index[-1]
    past_position = day_index - HMM_TREND_LOOKBACK - 1
    past = 1.0 if past_position < 0 else market_index[past_position]
    return current / past - 1.0


def _hmm_filter_step(previous_probabilities, observation, first_observation=False):
    """One forward-filter step for the fixed three-state Gaussian HMM."""
    if first_observation:
        predicted = HMM_INITIAL.copy()
    else:
        predicted = HMM_TRANSITION @ previous_probabilities

    densities = np.exp(
        -0.5 * (observation - HMM_MEANS) ** 2 / HMM_VARIANCES
    ) / np.sqrt(2.0 * np.pi * HMM_VARIANCES)

    filtered = predicted * densities
    total = np.sum(filtered)

    if not np.isfinite(total) or total <= EPS:
        return predicted / np.sum(predicted)

    return filtered / total


def _replay_hmm(prices):
    """Filter the market regime through all supplied price history."""
    n_days = prices.shape[1]
    probabilities = HMM_INITIAL.copy()
    first = True

    for day_index in range(HMM_TREND_LOOKBACK, n_days):
        observation = _market_trend_feature(prices, day_index)
        probabilities = _hmm_filter_step(probabilities, observation, first)
        first = False

    return probabilities, first


def _momentum_dollars_at_day(prices, day_index):
    """Full-cap 10-day momentum target, refreshed every ten price days."""
    if day_index < MOM_LOOKBACK:
        return np.zeros(N_INST, dtype=float)

    performance = prices[:, day_index] / prices[:, day_index - MOM_LOOKBACK] - 1.0
    target_dollars = np.sign(performance) * DOLLAR_CAPS
    target_dollars[BROAD_EXCLUDED] = 0.0
    return target_dollars


# -----------------------------------------------------------------------------
# Online state management
# -----------------------------------------------------------------------------

def _initialise_cache(prices):
    """Initialise state from all history supplied on the first call."""
    n_days = prices.shape[1]
    last_day = n_days - 1

    # The cross-sectional engine rebalances on global even-numbered price days.
    rebalance_day = last_day - (last_day % CS_REBALANCE)

    cross_sectional_dollars = _cross_sectional_dollars_at_day(
        prices,
        rebalance_day,
    )

    pair_states = _replay_pair_states(np.log(prices))

    momentum_day = last_day - (last_day % MOM_REBALANCE)
    momentum_dollars = _momentum_dollars_at_day(prices, momentum_day)
    hmm_probabilities, hmm_first = _replay_hmm(prices)

    CACHE.clear()
    CACHE["last_n_days"] = n_days
    CACHE["cross_sectional_dollars"] = cross_sectional_dollars
    CACHE["pair_states"] = pair_states
    CACHE["momentum_dollars"] = momentum_dollars
    CACHE["hmm_probabilities"] = hmm_probabilities
    CACHE["hmm_first"] = hmm_first


def _advance_cache(prices):
    """Process only price days appended since the previous strategy call."""
    previous_n_days = int(CACHE["last_n_days"])
    current_n_days = prices.shape[1]
    log_prices = np.log(prices)

    for day_index in range(previous_n_days, current_n_days):
        if day_index % CS_REBALANCE == 0:
            CACHE["cross_sectional_dollars"] = (
                _cross_sectional_dollars_at_day(prices, day_index)
            )

        if day_index % MOM_REBALANCE == 0:
            CACHE["momentum_dollars"] = _momentum_dollars_at_day(
                prices, day_index
            )

        if day_index >= HMM_TREND_LOOKBACK:
            observation = _market_trend_feature(prices, day_index)
            CACHE["hmm_probabilities"] = _hmm_filter_step(
                np.asarray(CACHE["hmm_probabilities"], dtype=float),
                observation,
                bool(CACHE["hmm_first"]),
            )
            CACHE["hmm_first"] = False

        _advance_pair_states(
            log_prices,
            day_index,
            CACHE["pair_states"],
        )

    CACHE["last_n_days"] = current_n_days


# -----------------------------------------------------------------------------
# Official entry point
# -----------------------------------------------------------------------------

def getMyPosition(prcSoFar):
    """Return desired total positions in integer shares for all 51 assets."""
    prices = np.asarray(prcSoFar, dtype=float)

    if prices.ndim != 2 or prices.shape[0] != N_INST:
        raise ValueError(
            "Expected prices with shape (51, number_of_days), "
            f"but received {prices.shape}."
        )

    if prices.shape[1] == 0:
        return np.zeros(N_INST, dtype=int)

    if not np.all(np.isfinite(prices)) or np.any(prices <= 0.0):
        raise ValueError("All prices must be finite and strictly positive.")

    n_days = prices.shape[1]
    cached_n_days = int(CACHE.get("last_n_days", -1))

    # Rebuild when first called or when a caller repeats/rewinds the history.
    # Otherwise, advance only through newly appended price days.
    if not CACHE or n_days <= cached_n_days:
        _initialise_cache(prices)
    else:
        _advance_cache(prices)

    returns = _simple_returns(prices)

    cross_sectional = np.asarray(
        CACHE["cross_sectional_dollars"],
        dtype=float,
    )
    pairs = _pair_dollars(CACHE["pair_states"])
    cubo = _cubo_dollars(returns)

    regime_state = int(np.argmax(CACHE["hmm_probabilities"]))
    if regime_state == HMM_NEUTRAL_STATE:
        momentum = np.asarray(CACHE["momentum_dollars"], dtype=float)
    else:
        momentum = np.zeros(N_INST, dtype=float)

    target_dollars = cross_sectional + pairs + cubo + momentum
    target_dollars = np.clip(
        target_dollars,
        -DOLLAR_CAPS,
        DOLLAR_CAPS,
    )

    current_prices = prices[:, -1]

    # np.trunc moves toward zero and therefore cannot exceed the dollar limit
    # because of share rounding.
    positions = np.trunc(
        target_dollars / current_prices
    ).astype(np.int64)

    # Final defensive share-level cap. The official backtester clips too.
    share_caps = np.floor(
        DOLLAR_CAPS / current_prices
    ).astype(np.int64)

    positions = np.clip(
        positions,
        -share_caps,
        share_caps,
    )

    return positions.astype(int)