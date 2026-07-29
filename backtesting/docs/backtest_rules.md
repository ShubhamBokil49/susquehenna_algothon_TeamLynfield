# Backtest Rules

The Algothon backtester is deterministic and official-dataset-only.

## Data

- The engine only uses the provided price dataset.
- It does not generate fake, simulated, bootstrapped, Monte Carlo, or randomised
  data.
- Price data is used internally as a matrix with shape
  `(n_instruments, n_days)`.
- Numeric files without a header are treated as already being
  `(n_instruments, n_days)`.
- Headered files are treated as `(n_days, n_instruments)` and transposed after
  loading. The header tokens are preserved as ticker symbols.

## Daily Loop

- By default, the engine scores the final `250` days to match the supplied 2026
  evaluation script.
- The loop performs one unscored warm-up trade immediately before the first
  scored day.
- Each strategy call receives `prices[:, :t]`, matching the official eval
  script's price history slicing.
- The final loop marks the final position value without opening a new trade.
- `start_day` and `end_day` select the scored window from the provided dataset.

## Positions, Trades, And Costs

- The strategy returns target positions for each instrument.
- Position limits are applied per instrument.
- Trades are target position minus previous position.
- Commission is charged on traded notional.
- Instrument `0` uses a commission rate of `0.00002` and dollar position limit
  of `$100,000`.
- All other instruments use a commission rate of `0.0001` and dollar position
  limit of `$10,000`.
- P&L follows the supplied 2026 eval script's cash/value timing.

## Score

- If mean daily P&L is non-positive, or daily P&L standard deviation is too
  close to zero, score is mean daily P&L.
- Otherwise score is:

```text
sharpe = sqrt(250) * mean_daily_pnl / std_daily_pnl
score = mean_daily_pnl * sharpe^2 / (sharpe^2 + 1)
```

## Determinism

Same strategy plus same data and same configuration produces the same result.
