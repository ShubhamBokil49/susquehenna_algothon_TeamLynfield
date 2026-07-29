import type { TradeLog } from "../data/resultTypes";
import { formatCurrency, formatNumber } from "../lib/formatters";

type TradeLogTableProps = {
  tradeLogs: TradeLog[];
};

export function TradeLogTable({ tradeLogs }: TradeLogTableProps) {
  return (
    <section className="data-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Execution</p>
          <h2>Trade Log</h2>
        </div>
        <span className="panel-count">{tradeLogs.length} trades</span>
      </div>

      {tradeLogs.length === 0 ? (
        <p className="empty-state">No non-zero trades were logged.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Day</th>
                <th>Instrument</th>
                <th>Side</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>Trade Value</th>
                <th>Commission</th>
                <th>New Position</th>
              </tr>
            </thead>
            <tbody>
              {tradeLogs.map((trade, index) => (
                <tr key={`${trade.day}-${trade.instrument}-${index}`}>
                  <td>{trade.day}</td>
                  <td>{trade.instrument}</td>
                  <td>
                    <span className={`side-pill side-${trade.side.toLowerCase()}`}>
                      {trade.side}
                    </span>
                  </td>
                  <td>{formatNumber(trade.trade_quantity)}</td>
                  <td>{formatCurrency(trade.price)}</td>
                  <td>{formatCurrency(trade.trade_value)}</td>
                  <td>{formatCurrency(trade.commission)}</td>
                  <td>{formatNumber(trade.new_position)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
