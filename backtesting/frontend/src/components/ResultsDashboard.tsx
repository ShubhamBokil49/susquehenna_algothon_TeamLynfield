import { useEffect, useMemo, useState } from "react";
import type { TestManifest } from "../data/backtestApi";
import {
  resultsCsvUrl,
  storedStrategyUrl,
} from "../data/backtestApi";
import type { BacktestResults } from "../data/resultTypes";
import {
  formatCompactCurrency,
  formatCurrency,
} from "../lib/formatters";
import { BarChart, DualLineChart, LineChart } from "./Charts";
import { DailyRecordsTable } from "./DailyRecordsTable";
import { InstrumentInspector } from "./InstrumentInspector";
import { MatrixHeatmap } from "./MatrixHeatmap";
import { SummaryCards } from "./SummaryCards";
import { TradeLogTable } from "./TradeLogTable";
import { WarningsPanel } from "./WarningsPanel";

type ResultsDashboardProps = {
  manifest: TestManifest;
  results: BacktestResults;
};

export function ResultsDashboard({
  manifest,
  results,
}: ResultsDashboardProps) {
  const [selectedInstrument, setSelectedInstrument] = useState(0);

  useEffect(() => {
    setSelectedInstrument(0);
  }, [manifest.id]);

  const dailyPnl = useMemo(
    () =>
      results.series.daily_pnl.map((value, index) => ({
        day: results.series.days[index] ?? index,
        value,
      })),
    [results],
  );

  const cumulativePnl = useMemo(
    () =>
      results.series.cumulative_pnl.map((value, index) => ({
        day: results.series.days[index] ?? index,
        value,
      })),
    [results],
  );

  const drawdown = useMemo(
    () =>
      results.series.drawdown.map((value, index) => ({
        day: results.series.days[index] ?? index,
        value,
      })),
    [results],
  );

  const turnoverCommission = useMemo(
    () =>
      results.series.daily_turnover.map((turnover, index) => ({
        day: results.series.days[index] ?? index,
        primary: turnover,
        secondary: results.series.daily_commission[index] ?? 0,
      })),
    [results],
  );

  return (
    <article
      className="results-dashboard"
      id={`panel-${manifest.id}`}
      role="tabpanel"
      aria-label={`${manifest.id} backtest results`}
    >
      <header className="results-header">
        <div>
          <p className="section-kicker">Saved backtest · {manifest.id}</p>
          <h1>{manifest.original_filename}</h1>
          <p className="results-caption">
            Strategy source, settings, and complete results are stored together
            under this test ID.
          </p>
        </div>
        <div className="artifact-actions">
          <a href={storedStrategyUrl(manifest.id)} download>
            View stored .py
          </a>
          <a className="artifact-primary" href={resultsCsvUrl(manifest.id)} download>
            Download all data · CSV
          </a>
        </div>
      </header>

      <div className="run-meta" aria-label="Run details">
        <span>{results.metadata.n_instruments} instruments</span>
        <span>
          Days {results.metadata.start_day}–{results.metadata.end_day}
        </span>
        <span>{results.summary.total_trades} trade events</span>
        <span>{manifest.parameters.num_test_days} scored-day setting</span>
      </div>

      <SummaryCards results={results} />

      <section className="chart-grid" aria-label="Backtest charts">
        <LineChart
          data={cumulativePnl}
          title="Cumulative P&L"
          tone="blue"
          domain={{ includeZero: true }}
          showZeroLine
          formatValue={formatCurrency}
        />
        <BarChart
          data={dailyPnl}
          title="Daily P&L"
          domain={{ includeZero: true }}
          showZeroLine
          formatValue={formatCurrency}
        />
        <LineChart
          data={drawdown}
          title="Drawdown"
          tone="red"
          domain={{ fixedMax: 0 }}
          showZeroLine
          formatValue={formatCurrency}
        />
        <DualLineChart
          data={turnoverCommission}
          title="Turnover and Commission"
          primaryLabel="Turnover"
          secondaryLabel="Commission"
          domain={{ fixedMin: 0 }}
          showZeroLine
          formatValue={formatCompactCurrency}
        />
      </section>

      <WarningsPanel warnings={results.warnings} />

      <InstrumentInspector
        results={results}
        selectedInstrument={selectedInstrument}
        onSelectedInstrumentChange={setSelectedInstrument}
      />

      <section className="matrix-grid-panels">
        <MatrixHeatmap
          kicker="Exposure"
          title="Position Exposure"
          matrix={results.positions}
          days={results.series.days}
          negativeLabel="Short"
          positiveLabel="Long"
        />
        <MatrixHeatmap
          kicker="Execution"
          title="Trade Activity"
          matrix={results.trades}
          days={results.series.days}
          negativeLabel="Sell"
          positiveLabel="Buy"
        />
      </section>

      <DailyRecordsTable records={results.daily_records} />
      <TradeLogTable tradeLogs={results.trade_logs} />
    </article>
  );
}
