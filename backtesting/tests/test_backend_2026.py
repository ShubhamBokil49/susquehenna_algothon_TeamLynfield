import tempfile
import unittest
from pathlib import Path

import numpy as np

from engine.data_loader import load_price_data, load_prices
from engine.simulator import (
    DEFAULT_COMMISSION_RATE,
    DEFAULT_POSITION_LIMIT_DOLLARS,
    INSTRUMENT_0_COMMISSION_RATE,
    INSTRUMENT_0_POSITION_LIMIT_DOLLARS,
    run_backtest,
    score_susquehanna_2026,
)


class PriceLoaderTests(unittest.TestCase):
    def test_loads_old_numeric_instruments_by_days_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "prices.txt"
            path.write_text("100 101 102\n50 51 52\n")

            price_data = load_price_data(str(path))

        np.testing.assert_array_equal(
            price_data.prices,
            np.array([[100.0, 101.0, 102.0], [50.0, 51.0, 52.0]]),
        )
        self.assertIsNone(price_data.tickers)
        self.assertEqual(price_data.input_format, "numeric_instruments_by_days")

    def test_loads_headered_days_by_instruments_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "prices.txt"
            path.write_text("AAA BBB\n100 50\n101 51\n102 52\n")

            price_data = load_price_data(str(path))

        np.testing.assert_array_equal(
            price_data.prices,
            np.array([[100.0, 101.0, 102.0], [50.0, 51.0, 52.0]]),
        )
        self.assertEqual(price_data.tickers, ["AAA", "BBB"])
        self.assertEqual(price_data.input_format, "headered_days_by_instruments")

    def test_load_prices_keeps_array_only_compatibility(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "prices.txt"
            path.write_text("100 101 102\n")

            prices = load_prices(str(path))

        np.testing.assert_array_equal(prices, np.array([[100.0, 101.0, 102.0]]))


class Simulator2026Tests(unittest.TestCase):
    def test_default_window_and_instrument_zero_rules(self):
        prices = np.vstack(
            [
                np.full(1000, 100.0),
                np.full(1000, 50.0),
                np.full(1000, 20.0),
            ]
        )

        def large_constant_position(prices_so_far):
            return np.array([5000, 5000, 5000])

        results = run_backtest(
            prices=prices,
            get_position_function=large_constant_position,
            function_name="large_constant_position",
            tickers=["AAA", "BBB", "CCC"],
        )

        self.assertEqual(results["metadata"]["start_day"], 750)
        self.assertEqual(results["metadata"]["end_day"], 999)
        self.assertEqual(results["metadata"]["run_days"], 250)
        self.assertEqual(len(results["daily_records"]), 250)
        self.assertEqual(len(results["series"]["days"]), 250)
        self.assertEqual(len(results["positions"]), 250)
        self.assertEqual(len(results["trades"]), 250)
        self.assertEqual(results["metadata"]["tickers"], ["AAA", "BBB", "CCC"])
        self.assertEqual(
            results["metadata"]["commission_rates"],
            [INSTRUMENT_0_COMMISSION_RATE, DEFAULT_COMMISSION_RATE, DEFAULT_COMMISSION_RATE],
        )
        self.assertEqual(
            results["metadata"]["position_limit_dollars_by_instrument"],
            [
                INSTRUMENT_0_POSITION_LIMIT_DOLLARS,
                DEFAULT_POSITION_LIMIT_DOLLARS,
                DEFAULT_POSITION_LIMIT_DOLLARS,
            ],
        )

        self.assertEqual(results["positions"][0], [1000, 200, 500])
        self.assertEqual(results["trade_logs"][0]["day"], 749)
        self.assertEqual(results["trade_logs"][0]["instrument"], 0)
        self.assertEqual(results["trade_logs"][0]["trade_quantity"], 1000)
        self.assertAlmostEqual(results["trade_logs"][0]["commission"], 2.0)
        self.assertAlmostEqual(results["daily_records"][0]["commission"], 4.0)
        self.assertAlmostEqual(results["daily_records"][0]["net_pnl"], -4.0)
        self.assertAlmostEqual(results["summary"]["total_commission"], 4.0)

    def test_score_uses_2026_formula(self):
        mean_daily_pnl = 10.0
        std_daily_pnl = 2.0
        sharpe = np.sqrt(250) * mean_daily_pnl / std_daily_pnl
        expected = mean_daily_pnl * sharpe**2 / (sharpe**2 + 1.0)

        self.assertAlmostEqual(
            score_susquehanna_2026(mean_daily_pnl, std_daily_pnl),
            expected,
        )
        self.assertEqual(score_susquehanna_2026(-5.0, 2.0), -5.0)
        self.assertEqual(score_susquehanna_2026(5.0, 0.0), 5.0)


if __name__ == "__main__":
    unittest.main()
