import {
  formatCompactCurrency,
  formatCurrency,
} from "../lib/formatters";
import { BarChart, DualLineChart, LineChart } from "./Charts";

const emptySummaryCards = [
  { label: "Score", accent: "blue" },
  { label: "Total P&L", accent: "green" },
  { label: "Max Drawdown", accent: "red" },
  { label: "Turnover", accent: "purple" },
  { label: "Commission", accent: "orange" },
  { label: "Total Trades", accent: "blue" },
  { label: "Clipping Days", accent: "slate" },
];

export function EmptyDashboard() {
  return (
    <article
      className="results-dashboard empty-dashboard"
      aria-label="Backtest results waiting for a strategy"
    >
      <header className="results-header">
        <div>
          <p className="section-kicker">Backtest workspace</p>
          <h1>Backtest results</h1>
          <p className="results-caption">
            Upload a Python strategy to populate this dashboard.
          </p>
        </div>
        <div className="empty-dashboard-status" aria-label="Waiting for strategy">
          <span className="status-dot" aria-hidden="true" />
          Waiting for strategy
        </div>
      </header>

      <section className="summary-grid" aria-label="Empty backtest summary">
        {emptySummaryCards.map((card) => (
          <article
            className={`summary-card summary-card-${card.accent}`}
            key={card.label}
          >
            <span>{card.label}</span>
            <strong aria-label="No result yet">—</strong>
          </article>
        ))}
      </section>

      <section className="chart-grid" aria-label="Empty backtest charts">
        <LineChart
          data={[]}
          title="Cumulative P&L"
          tone="blue"
          domain={{ includeZero: true }}
          showZeroLine
          formatValue={formatCurrency}
        />
        <BarChart
          data={[]}
          title="Daily P&L"
          domain={{ includeZero: true }}
          showZeroLine
          formatValue={formatCurrency}
        />
        <LineChart
          data={[]}
          title="Drawdown"
          tone="red"
          domain={{ fixedMax: 0 }}
          showZeroLine
          formatValue={formatCurrency}
        />
        <DualLineChart
          data={[]}
          title="Turnover and Commission"
          primaryLabel="Turnover"
          secondaryLabel="Commission"
          domain={{ fixedMin: 0 }}
          showZeroLine
          formatValue={formatCompactCurrency}
        />
      </section>
    </article>
  );
}
