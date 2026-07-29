# Algothon Backtester

This repository contains a deterministic backtester and visualiser data engine
for the UNSW x Susquehanna International Group Algothon.

It runs competitor strategies over the provided official price dataset. It does
not simulate, bootstrap, Monte Carlo sample, randomise, or substitute market
data. Backtest runs export structured JSON for the included web dashboard, and
the repository also includes a lightweight plotting script for saving a few
quick charts.

## Current Status

| Component | Status | Notes |
| --- | --- | --- |
| Deterministic backtester engine | Implemented | Runs strategies with the supplied 2026 eval-style timing and rules. |
| Visualiser data output | Implemented | Outputs structured JSON with summary, series, matrices, trade logs, instrument summaries, warnings, and clipping events. |
| Quick-look plots | Implemented | `scripts/plot_results.py` saves PNG charts from a results JSON file. |
| Web frontend | Implemented | Displays generated backtest results in an interactive browser dashboard. |

## Repository Structure

```text
.
├── data/
│   └── prices.txt
├── docs/
│   ├── backtest_rules.md
│   ├── results_schema.md
│   └── visualiser_contract.md
├── engine/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── simulator.py
│   └── strategy_loader.py
├── examples/
│   ├── broken_strategy.py
│   ├── momentum_strategy.py
│   ├── sample_results.json
│   ├── team_strategy.py
│   └── zero_strategy.py
├── frontend/
│   ├── public/
│   ├── src/
│   ├── testing/
│   └── package.json
├── scripts/
│   ├── plot_results.py
│   └── run_backtest.py
├── README.md
└── requirements.txt
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Price Data Format

The engine uses prices internally as `(n_instruments, n_days)`.

Two file shapes are supported:

- Old numeric fixture format: rows are instruments, columns are days, no header.
- 2026 format: first row is ticker symbols, rows are days, columns are
  instruments. This is transposed after loading.

The current sample file, `data/prices.txt`, contains the prices from days 1-750


This sample has 3 instruments and 5 days.

## Strategy Format

By default, a strategy file must define:

```python
def getMyPosition(prices):
    ...
```

The `prices` argument has shape `(n_instruments, days_so_far)` and contains
only the provided dataset up to and including the current day. The strategy
returns one target position per instrument.

Strategies should be deterministic for the same input price history. They
should not generate or depend on simulated, bootstrapped, Monte Carlo,
randomised, or fake market data.

## Running A Backtest

Standard 2026-style run:

```bash
python3 scripts/run_backtest.py \
  --strategy examples/team_strategy.py \
  --prices frontend/testing/prices_test.txt \
  --out frontend/public/results.json
```

Small fixture run:

```bash
python3 scripts/run_backtest.py \
  --strategy examples/momentum_strategy.py \
  --prices data/prices.txt \
  --out examples/sample_results.json
```

Windowed run:

```bash
python3 scripts/run_backtest.py \
  --strategy examples/momentum_strategy.py \
  --prices data/prices.txt \
  --start-day 1 \
  --end-day 3 \
  --out window_results.json
```

Custom strategy function name:

```bash
python3 scripts/run_backtest.py \
  --strategy examples/momentum_strategy.py \
  --prices data/prices.txt \
  --function-name getMyPosition \
  --out examples/sample_results.json
```

## Using The Web Frontend

The web frontend turns a completed backtest into a dashboard of charts, daily
results, instrument activity, trades, warnings, and position changes. The
backtester performs all calculations; the frontend only displays the generated
results.

You will need Python for the backtester and Node.js 20.19 or newer for the
frontend. Complete the Python setup above before continuing.

### 1. Generate Results For The Dashboard

From the repository root, activate the Python environment and run:

```bash
source .venv/bin/activate

python3 scripts/run_backtest.py \
  --strategy examples/team_strategy.py \
  --prices frontend/testing/prices_test.txt \
  --out frontend/public/results.json
```

The important part is the final line:

```text
--out frontend/public/results.json
```

This places the result where the frontend expects to find it. A successful run
prints a short summary and confirms that the file was saved.

To test your own strategy, replace `examples/team_strategy.py` with the path to
your strategy file. You can also replace the price path when an official
dataset is provided.

### 2. Start The Dashboard

Open a second terminal in the repository root. Install the frontend packages
the first time you use it, then start the development server:

```bash
cd frontend
npm install
npm run dev
```

The terminal will print a local address, usually:

```text
http://localhost:5173/
```

Open that address in your browser. If port 5173 is already occupied, the
terminal will show a different address; use the address it prints.

### 3. Test Strategy Changes

Keep the frontend running while you work. Each time you change your strategy:

1. Return to the first terminal and run the backtest command again.
2. Wait for the new `results.json` file to be written.
3. Refresh the dashboard in your browser.

The dashboard should show a **Live results** banner when it has loaded your
generated file. It shows **Mock fallback** when no readable
`frontend/public/results.json` is available. Mock data is only provided so the
frontend can still be previewed and its not the output of your strategy.

### What The Dashboard Shows

- Summary figures for score, P&L, drawdown, turnover, commission, trades, and
  position clipping.
- Charts showing how P&L, drawdown, turnover, and commission change over time.
- Daily records for checking what happened on a particular scored day.
- An instrument inspector for viewing positions, trades, and buy or sell
  activity for one instrument at a time.
- Position and trade matrices for comparing activity across instruments and
  days.
- Warnings that highlight unusual turnover, commission, clipping, volatility,
  or concentration.

All figures come from the generated result file. The frontend does not
recalculate your score or trading metrics.

### Common Problems

- **The page shows Mock fallback:** generate the result file using
  `--out frontend/public/results.json`, then refresh the page.
- **The page still shows an older run:** confirm the backtest completed, then
  refresh the browser. Restarting `npm run dev` is usually unnecessary.
- **`npm` is not found:** install a current Node.js release, which includes
  npm, then reopen the terminal.
- **The usual address does not open:** use the exact local address printed by
  `npm run dev`; another program may already be using port 5173.
- **The frontend reports invalid or missing information:** rerun the backtest
  with the current `scripts/run_backtest.py` so the result matches the expected
  format.

## CLI Options

| Flag | Required | Default | Description |
| --- | --- | --- | --- |
| `--strategy` | Yes | None | Path to a Python strategy file. |
| `--prices` | Yes | None | Path to the official price dataset. |
| `--out` | No | `results.json` | Path where the results JSON will be written. |
| `--commission` | No | `0.0001` | Default commission rate charged on traded notional. |
| `--position-limit` | No | `10000.0` | Default dollar position limit applied per instrument. |
| `--instrument-0-commission` | No | `0.00002` | Special commission rate for instrument 0. |
| `--instrument-0-position-limit` | No | `100000.0` | Special dollar position limit for instrument 0. |
| `--num-test-days` | No | `250` | Default scored window length when `--start-day` is omitted. |
| `--start-day` | No | Final 250-day window | First zero-based scored day. Must be at least `1`. |
| `--end-day` | No | Last available day | Last zero-based day index to run, inclusive. |
| `--function-name` | No | `getMyPosition` | Strategy function name to load from the strategy file. |

## Backtest Logic

The engine follows the supplied 2026 eval timing:

1. The default scored window is the final 250 days.
2. One unscored warm-up trade is performed before the first scored day.
3. Each strategy call receives `prices[:, :t]`, matching the official eval
   script's slicing.
4. Positions are clipped to per-instrument dollar limits.
5. Instrument 0 receives the special commission and limit.
6. The final loop marks positions without opening new trades.
7. Results are deterministic for the same strategy, configuration, and dataset.

## Output JSON

`scripts/run_backtest.py` writes a structured JSON object with these top-level
fields:

| Field | Description |
| --- | --- |
| `metadata` | Dataset dimensions, run window, cost settings, strategy function name, and determinism flags. |
| `summary` | Score, total P&L, gross P&L, drawdown, turnover, commission, and trade counts. |
| `daily_records` | One record per backtested day for replay and daily result tables. |
| `series` | Chart-ready arrays for days, P&L, drawdown, turnover, and commission. |
| `positions` | End-of-day position matrix by day and instrument. |
| `trades` | Signed trade matrix by day and instrument. |
| `trade_logs` | Readable one-row-per-trade records for tables and buy/sell markers. |
| `instrument_summary` | Per-instrument P&L, turnover, commission, position, and trade metrics. |
| `warnings` | Deterministic rule-based diagnostics for commission drag, turnover, clipping, volatility, and P&L concentration. |
| `clipping_events` | Days where requested positions were clipped by position limits. |

See `docs/results_schema.md` and `docs/visualiser_contract.md` for more detail.

## Quick-Look Plots

The quick-look plotting script reads a results JSON file and saves PNG charts:

```bash
PYTHONPATH=. python3 scripts/plot_results.py \
  --results examples/sample_results.json \
  --out-dir examples/plots
```

It writes:

- `cumulative_pnl.png`
- `daily_pnl.png`
- `drawdown.png`
- `turnover_commission.png`

This script is a lightweight alternative when you only need a few saved chart
images instead of the interactive web dashboard.

## Examples

- `examples/zero_strategy.py`: returns zero positions for every instrument.
- `examples/momentum_strategy.py`: simple deterministic momentum example.
- `examples/team_strategy.py`: cleaned version of the supplied test strategy.
- `examples/broken_strategy.py`: intentionally returns the wrong number of
  positions to demonstrate validation errors.

## What This Project Does Not Do

- No live trading.
- No brokerage integration.
- No real-time market data.
- No strategy generation.
- No simulated, bootstrapped, or Monte Carlo market paths.
- No hosted execution of arbitrary uploaded Python code.
