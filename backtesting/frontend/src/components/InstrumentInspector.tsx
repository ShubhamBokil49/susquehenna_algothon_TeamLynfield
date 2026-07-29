import type { BacktestResults, TradeLog } from "../data/resultTypes";
import { formatCompactCurrency, formatCurrency, formatNumber } from "../lib/formatters";
import { LineChart } from "./Charts";

type InstrumentInspectorProps = {
  results: BacktestResults;
  selectedInstrument: number;
  onSelectedInstrumentChange: (instrument: number) => void;
};

const markerChartWidth = 720;
const markerChartHeight = 190;
const markerPadding = {
  top: 18,
  right: 24,
  bottom: 28,
  left: 58,
};

function getMarkerRange(trades: TradeLog[]): { minDay: number; maxDay: number; minPrice: number; maxPrice: number } {
  if (trades.length === 0) {
    return { minDay: 0, maxDay: 1, minPrice: 0, maxPrice: 1 };
  }

  const days = trades.map((trade) => trade.day);
  const prices = trades.map((trade) => trade.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const pricePadding = minPrice === maxPrice ? 1 : (maxPrice - minPrice) * 0.08;

  return {
    minDay: Math.min(...days),
    maxDay: Math.max(...days),
    minPrice: minPrice - pricePadding,
    maxPrice: maxPrice + pricePadding,
  };
}

function TradeMarkerChart({ trades }: { trades: TradeLog[] }) {
  const { minDay, maxDay, minPrice, maxPrice } = getMarkerRange(trades);
  const innerWidth = markerChartWidth - markerPadding.left - markerPadding.right;
  const innerHeight = markerChartHeight - markerPadding.top - markerPadding.bottom;
  const xFor = (day: number) =>
    markerPadding.left + ((day - minDay) / Math.max(maxDay - minDay, 1)) * innerWidth;
  const yFor = (price: number) =>
    markerPadding.top + ((maxPrice - price) / Math.max(maxPrice - minPrice, 1)) * innerHeight;
  const markerPath = (trade: TradeLog): string => {
    const x = xFor(trade.day);
    const y = yFor(trade.price);
    const size = 6;

    if (trade.side === "BUY") {
      return `M ${x.toFixed(2)} ${(y - size).toFixed(2)} L ${(x - size).toFixed(2)} ${(y + size).toFixed(2)} L ${(x + size).toFixed(2)} ${(y + size).toFixed(2)} Z`;
    }

    return `M ${x.toFixed(2)} ${(y + size).toFixed(2)} L ${(x - size).toFixed(2)} ${(y - size).toFixed(2)} L ${(x + size).toFixed(2)} ${(y - size).toFixed(2)} Z`;
  };
  const recentTrades = trades.slice(-8).reverse();
  const recentCount = recentTrades.length;

  return (
    <section className="trade-marker-panel" aria-label="Trade price markers">
      <div className="chart-panel-header">
        <div>
          <h2>Trade Prices</h2>
          {trades.length > 0 ? (
            <p className="chart-subtitle">
              Latest {recentCount} of {formatNumber(trades.length)} scored trades
            </p>
          ) : null}
        </div>
        <div className="chart-legend-row" aria-label="Buy and sell legend">
          <span>
            <i className="legend-triangle legend-buy" />
            Buy
          </span>
          <span>
            <i className="legend-triangle legend-sell" />
            Sell
          </span>
        </div>
      </div>
      {trades.length === 0 ? (
        <p className="empty-state">No trade markers for this instrument.</p>
      ) : (
        <div className="trade-marker-grid">
          <svg className="chart-svg trade-price-svg" viewBox={`0 0 ${markerChartWidth} ${markerChartHeight}`}>
            <line
              className="chart-grid-line"
              x1={markerPadding.left}
              x2={markerChartWidth - markerPadding.right}
              y1={markerPadding.top}
              y2={markerPadding.top}
            />
            <line
              className="chart-grid-line"
              x1={markerPadding.left}
              x2={markerChartWidth - markerPadding.right}
              y1={(markerChartHeight - markerPadding.bottom + markerPadding.top) / 2}
              y2={(markerChartHeight - markerPadding.bottom + markerPadding.top) / 2}
            />
            <line
              className="chart-axis"
              x1={markerPadding.left}
              x2={markerPadding.left}
              y1={markerPadding.top}
              y2={markerChartHeight - markerPadding.bottom}
            />
            <line
              className="chart-axis"
              x1={markerPadding.left}
              x2={markerChartWidth - markerPadding.right}
              y1={markerChartHeight - markerPadding.bottom}
              y2={markerChartHeight - markerPadding.bottom}
            />
            {trades.map((trade, index) => (
              <g key={`${trade.day}-${trade.side}-${index}`}>
                <line
                  className="trade-marker-stem"
                  x1={xFor(trade.day)}
                  x2={xFor(trade.day)}
                  y1={yFor(trade.price)}
                  y2={markerChartHeight - markerPadding.bottom}
                />
                <path
                  className="trade-marker"
                  d={markerPath(trade)}
                  fill={trade.side === "BUY" ? "#059669" : "#dc2626"}
                />
              </g>
            ))}
            <text className="chart-axis-label" x={markerPadding.left - 10} y={markerPadding.top + 8}>
              {formatCurrency(maxPrice)}
            </text>
            <text className="chart-axis-label" x={markerPadding.left - 10} y={markerChartHeight - markerPadding.bottom}>
              {formatCurrency(minPrice)}
            </text>
            <text className="chart-x-label" x={markerPadding.left} y={markerChartHeight - 8}>
              Day {minDay}
            </text>
            <text className="chart-x-label chart-x-label-end" x={markerChartWidth - markerPadding.right} y={markerChartHeight - 8}>
              Day {maxDay}
            </text>
          </svg>
          <div className="marker-trade-list" aria-label="Latest scored trades">
            {recentTrades.map((trade, index) => (
              <article key={`${trade.day}-${trade.side}-${trade.instrument}-${index}`}>
                <span>Day {trade.day}</span>
                <strong className={`side-pill side-${trade.side.toLowerCase()}`}>{trade.side}</strong>
                <span>{formatCurrency(trade.price)}</span>
                <span>{formatNumber(trade.trade_quantity)}</span>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

export function InstrumentInspector({
  results,
  selectedInstrument,
  onSelectedInstrumentChange,
}: InstrumentInspectorProps) {
  const positions = results.positions.map((dayPositions, index) => ({
    day: results.series.days[index] ?? index,
    value: dayPositions[selectedInstrument] ?? 0,
  }));
  const summary = results.instrument_summary.find(
    (item) => item.instrument === selectedInstrument,
  );
  const markerTrades = results.trade_logs.filter(
    (trade) =>
      trade.instrument === selectedInstrument &&
      trade.day >= results.metadata.start_day &&
      trade.day <= results.metadata.end_day,
  );

  return (
    <section className="inspector-panel">
      <div className="inspector-header">
        <div>
          <p className="section-kicker">Instrument Inspector</p>
          <h2>Instrument {selectedInstrument}</h2>
        </div>
        <label className="instrument-select">
          <span>Instrument</span>
          <select
            value={selectedInstrument}
            onChange={(event) => onSelectedInstrumentChange(Number(event.target.value))}
          >
            {Array.from({ length: results.metadata.n_instruments }, (_, index) => (
              <option value={index} key={index}>
                {index}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="inspector-grid">
        <LineChart
          data={positions}
          title="Position Over Time"
          tone="amber"
          formatValue={(value) => formatNumber(value)}
        />
        <div className="instrument-stats">
          <article>
            <span>Total P&L</span>
            <strong>{formatCurrency(summary?.total_pnl ?? 0)}</strong>
          </article>
          <article>
            <span>Total Trades</span>
            <strong>{formatNumber(summary?.total_trades ?? 0)}</strong>
          </article>
          <article>
            <span>Turnover</span>
            <strong>{formatCompactCurrency(summary?.total_turnover ?? 0)}</strong>
          </article>
          <article>
            <span>Max Abs Position</span>
            <strong>{formatNumber(summary?.max_abs_position ?? 0)}</strong>
          </article>
        </div>
      </div>

      <TradeMarkerChart trades={markerTrades} />
    </section>
  );
}
