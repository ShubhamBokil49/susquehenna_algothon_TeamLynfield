import type { BacktestResults } from "../data/resultTypes";
import {
  formatCompactCurrency,
  formatCurrency,
  formatNumber,
} from "../lib/formatters";

type SummaryCardsProps = {
  results: BacktestResults;
};

export function SummaryCards({ results }: SummaryCardsProps) {
  const { summary } = results;
  const cards = [
    {
      label: "Score",
      value: formatNumber(summary.score),
      accent: "blue",
    },
    {
      label: "Total P&L",
      value: formatCurrency(summary.total_pnl),
      accent: summary.total_pnl >= 0 ? "green" : "red",
    },
    {
      label: "Max Drawdown",
      value: formatCurrency(summary.max_drawdown),
      accent: "red",
    },
    {
      label: "Turnover",
      value: formatCompactCurrency(summary.total_turnover),
      accent: "purple",
    },
    {
      label: "Commission",
      value: formatCurrency(summary.total_commission),
      accent: "orange",
    },
    {
      label: "Total Trades",
      value: formatNumber(summary.total_trades),
      accent: "blue",
    },
    {
      label: "Clipping Days",
      value: formatNumber(summary.clipping_event_count),
      accent: "slate",
    },
  ];

  return (
    <section className="summary-grid" aria-label="Backtest summary">
      {cards.map((card) => (
        <article className={`summary-card summary-card-${card.accent}`} key={card.label}>
          <span>{card.label}</span>
          <strong>{card.value}</strong>
        </article>
      ))}
    </section>
  );
}
