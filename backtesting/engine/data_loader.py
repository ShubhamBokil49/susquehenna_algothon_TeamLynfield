from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class PriceData:
    prices: np.ndarray
    tickers: list[str] | None
    input_format: str


def _is_float_token(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False

    return True


def _first_non_empty_line(path: Path) -> tuple[int, str]:
    for line_number, line in enumerate(path.read_text().splitlines()):
        stripped = line.strip()

        if stripped:
            return line_number, stripped

    raise ValueError(f"Price data file is empty: {path}")


def _validate_prices(prices: np.ndarray) -> np.ndarray:
    if prices.ndim != 2:
        raise ValueError(
            "Price data must be a 2D array with shape "
            f"(instruments, days); got {prices.ndim}D data."
        )

    n_instruments, n_days = prices.shape

    if n_instruments < 1:
        raise ValueError("Price data must contain at least one instrument.")

    if n_days < 2:
        raise ValueError("Price data must contain at least two days.")

    if np.any(~np.isfinite(prices)):
        raise ValueError("Price data contains NaN or infinite values.")

    if np.any(prices <= 0):
        raise ValueError("Price data must contain only positive prices.")

    return prices.astype(float)


def load_price_data(path: str) -> PriceData:
    price_path = Path(path)
    first_line_number, first_line = _first_non_empty_line(price_path)
    first_tokens = first_line.split()
    has_header = not all(_is_float_token(token) for token in first_tokens)

    if has_header:
        tickers = first_tokens
        raw_prices = np.loadtxt(price_path, skiprows=first_line_number + 1)

        if raw_prices.ndim == 1:
            raw_prices = raw_prices.reshape(1, -1)

        if raw_prices.shape[1] != len(tickers):
            raise ValueError(
                "Ticker header count does not match price column count: "
                f"{len(tickers)} tickers, {raw_prices.shape[1]} price columns."
            )

        return PriceData(
            prices=_validate_prices(raw_prices.T),
            tickers=tickers,
            input_format="headered_days_by_instruments",
        )

    raw_prices = np.loadtxt(price_path)

    if raw_prices.ndim == 1:
        raw_prices = raw_prices.reshape(1, -1)

    return PriceData(
        prices=_validate_prices(raw_prices),
        tickers=None,
        input_format="numeric_instruments_by_days",
    )


def load_prices(path: str) -> np.ndarray:
    return load_price_data(path).prices
