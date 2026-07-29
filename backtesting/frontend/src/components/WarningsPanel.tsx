import type { BacktestWarning } from "../data/resultTypes";
import { formatNumber } from "../lib/formatters";

type WarningsPanelProps = {
  warnings: BacktestWarning[];
};

export function WarningsPanel({ warnings }: WarningsPanelProps) {
  return (
    <section className="data-panel warnings-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Diagnostics</p>
          <h2>Warnings</h2>
        </div>
        <span className="panel-count">{warnings.length}</span>
      </div>

      {warnings.length === 0 ? (
        <p className="empty-state">No rule-based warnings were emitted for this run.</p>
      ) : (
        <div className="warning-list">
          {warnings.map((warning) => (
            <article className="warning-item" key={warning.code}>
              <div>
                <strong>{warning.code}</strong>
                <p>{warning.message}</p>
              </div>
              <span>
                {formatNumber(warning.value)} / {formatNumber(warning.threshold)}
              </span>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
