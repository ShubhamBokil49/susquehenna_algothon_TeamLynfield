# Visualiser Contract

The frontend should consume the JSON written by `scripts/run_backtest.py`. It
should not need to recalculate P&L, turnover, commission, trades, or warnings.

## Dashboard Cards

Use `summary` for dashboard cards:

- `summary.score`
- `summary.total_pnl`
- `summary.max_drawdown`
- `summary.total_turnover`
- `summary.total_commission`
- `summary.total_trades`
- `summary.clipping_event_count`

If `metadata.tickers` is present, frontend views may use it for instrument
labels. Instrument indexes remain the stable identifiers.

## Charts

Use `series` for charts. `series.days` is the x-axis and all series arrays are
aligned by index.

- Cumulative P&L: `series.cumulative_pnl`
- Daily P&L: `series.daily_pnl`
- Drawdown: `series.drawdown`
- Turnover: `series.daily_turnover`
- Commission: `series.daily_commission`

## Replay And Tables

- Use `daily_records` for replay state and daily result tables.
- Use `trade_logs` for the trade table and buy/sell markers.
- Use `instrument_summary` for per-instrument breakdowns.
- Use `warnings` for user-facing diagnostics.

## Matrices And Heatmaps

- Use `positions` for the position heatmap.
- Use `trades` for the trade matrix.

Rows align with `daily_records` and `series.days`. Columns are zero-based
instrument indexes.

## Trade Markers

Use `trade_logs` to place buy/sell markers on charts. Each row includes day,
instrument, side, previous position, new position, quantity, price, trade value,
and commission.
