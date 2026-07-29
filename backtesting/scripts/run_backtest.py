import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.data_loader import load_price_data
from engine.result_export import write_results_csv
from engine.strategy_loader import load_strategy
from engine.simulator import (
    DEFAULT_COMMISSION_RATE,
    DEFAULT_NUM_TEST_DAYS,
    DEFAULT_POSITION_LIMIT_DOLLARS,
    INSTRUMENT_0_COMMISSION_RATE,
    INSTRUMENT_0_POSITION_LIMIT_DOLLARS,
    run_backtest,
)


def main():
    parser = argparse.ArgumentParser(description="Run Algothon deterministic backtest.")

    parser.add_argument(
        "--strategy",
        required=True,
        help="Path to strategy file containing the strategy function.",
    )

    parser.add_argument(
        "--prices",
        required=True,
        help="Path to official price dataset.",
    )

    parser.add_argument(
        "--out",
        default="results.json",
        help="Output path for results JSON.",
    )

    parser.add_argument(
        "--csv-out",
        default=None,
        help="Optional path for a complete long-form CSV copy of the results.",
    )

    parser.add_argument(
        "--test-id",
        default=None,
        help="Optional stored test identifier to include in result metadata.",
    )

    parser.add_argument(
        "--original-strategy-filename",
        default=None,
        help="Optional original upload filename to include in result metadata.",
    )

    parser.add_argument(
        "--created-at",
        default=None,
        help="Optional stored test creation timestamp to include in result metadata.",
    )

    parser.add_argument(
        "--commission",
        type=float,
        default=DEFAULT_COMMISSION_RATE,
        help="Default commission rate. Example: 0.0001 = 1 bp.",
    )

    parser.add_argument(
        "--position-limit",
        type=float,
        default=DEFAULT_POSITION_LIMIT_DOLLARS,
        help="Default dollar position limit per instrument.",
    )

    parser.add_argument(
        "--instrument-0-commission",
        type=float,
        default=INSTRUMENT_0_COMMISSION_RATE,
        help="Special commission rate for instrument 0.",
    )

    parser.add_argument(
        "--instrument-0-position-limit",
        type=float,
        default=INSTRUMENT_0_POSITION_LIMIT_DOLLARS,
        help="Special dollar position limit for instrument 0.",
    )

    parser.add_argument(
        "--num-test-days",
        type=int,
        default=DEFAULT_NUM_TEST_DAYS,
        help="Default scored window length when --start-day is omitted.",
    )

    parser.add_argument(
        "--start-day",
        type=int,
        default=None,
        help="First zero-based day index to run. Must be at least 1.",
    )

    parser.add_argument(
        "--end-day",
        type=int,
        default=None,
        help="Last zero-based day index to run, inclusive.",
    )

    parser.add_argument(
        "--function-name",
        default="getMyPosition",
        help="Strategy function name to load from the strategy file.",
    )

    args = parser.parse_args()

    price_data = load_price_data(args.prices)
    strategy = load_strategy(args.strategy, function_name=args.function_name)

    results = run_backtest(
        prices=price_data.prices,
        get_position_function=strategy,
        commission_rate=args.commission,
        position_limit_dollars=args.position_limit,
        instrument_0_commission_rate=args.instrument_0_commission,
        instrument_0_position_limit_dollars=args.instrument_0_position_limit,
        start_day=args.start_day,
        end_day=args.end_day,
        function_name=args.function_name,
        num_test_days=args.num_test_days,
        tickers=price_data.tickers,
    )
    results["metadata"]["price_input_format"] = price_data.input_format
    if args.test_id:
        results["metadata"]["test_id"] = args.test_id
    if args.original_strategy_filename:
        results["metadata"]["original_strategy_filename"] = (
            args.original_strategy_filename
        )
    if args.created_at:
        results["metadata"]["created_at"] = args.created_at

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2))

    csv_output_path = None
    if args.csv_out:
        csv_output_path = write_results_csv(results, args.csv_out)

    print("Backtest complete.")
    print(
        f"Loaded {results['metadata']['n_instruments']} instruments "
        f"for {results['metadata']['n_days']} days."
    )
    print(
        f"Scored days: {results['metadata']['start_day']} "
        f"to {results['metadata']['end_day']}."
    )
    print(f"Score: {results['summary']['score']:.4f}")
    print(f"Total P&L: {results['summary']['total_pnl']:.2f}")
    print(f"Max drawdown: {results['summary']['max_drawdown']:.2f}")
    print(f"Total commission: {results['summary']['total_commission']:.2f}")
    print(f"Total turnover: {results['summary']['total_turnover']:.2f}")
    print(f"Results saved to: {output_path}")
    if csv_output_path is not None:
        print(f"CSV results saved to: {csv_output_path}")


if __name__ == "__main__":
    main()
