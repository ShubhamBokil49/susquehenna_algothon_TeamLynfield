import type { DailyRecord } from "../data/resultTypes";
import { formatCurrency, formatCompactCurrency, formatNumber } from "../lib/formatters";

type DailyRecordsTableProps = {
  records: DailyRecord[];
};

export function DailyRecordsTable({ records }: DailyRecordsTableProps) {
  return (
    <section className="data-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Replay</p>
          <h2>Daily Records</h2>
        </div>
        <span className="panel-count">{records.length} rows</span>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Day</th>
              <th>Net P&L</th>
              <th>Gross P&L</th>
              <th>Cumulative</th>
              <th>Turnover</th>
              <th>Commission</th>
              <th>Traded</th>
              <th>Clipped</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.day}>
                <td>{record.day}</td>
                <td className={record.net_pnl >= 0 ? "positive-value" : "negative-value"}>
                  {formatCurrency(record.net_pnl)}
                </td>
                <td>{formatCurrency(record.gross_pnl)}</td>
                <td>{formatCurrency(record.cumulative_pnl)}</td>
                <td>{formatCompactCurrency(record.turnover)}</td>
                <td>{formatCurrency(record.commission)}</td>
                <td>{formatNumber(record.num_traded_instruments)}</td>
                <td>{formatNumber(record.num_clipped_instruments)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
