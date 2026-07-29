import type { TestManifest } from "../data/backtestApi";
import { formatCurrency, formatNumber } from "../lib/formatters";
import type { QueuedStrategy } from "./RunSetup";

type TestRailProps = {
  configReady: boolean;
  maxUploadBytes: number;
  queue: QueuedStrategy[];
  history: TestManifest[];
  selectedQueueId: string | null;
  selectedTestId: string | null;
  uploadError: string | null;
  onFiles: (files: FileList | File[]) => void;
  onSelectQueue: (clientId: string) => void;
  onRemoveQueue: (clientId: string) => void;
  onSelectTest: (test: TestManifest) => void;
};

function shortFileName(filename: string): string {
  if (filename.length <= 30) {
    return filename;
  }
  return `${filename.slice(0, 18)}…${filename.slice(-9)}`;
}

function createdLabel(createdAt: string): string {
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) {
    return "Saved test";
  }
  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function TestRail({
  configReady,
  maxUploadBytes,
  queue,
  history,
  selectedQueueId,
  selectedTestId,
  uploadError,
  onFiles,
  onSelectQueue,
  onRemoveQueue,
  onSelectTest,
}: TestRailProps) {
  const maxSizeMb = Math.max(0.1, maxUploadBytes / 1_000_000);

  return (
    <aside className="test-rail" aria-label="Backtest files and history">
      <div className="brand-lockup">
        <div>
          <strong>Algothon Backtester</strong>
          <small>UNSW FinTechSoc x SIG</small>
        </div>
      </div>

      <label
        className={`upload-dropzone ${configReady ? "" : "is-disabled"}`}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          if (configReady) {
            onFiles(event.dataTransfer.files);
          }
        }}
      >
        <input
          type="file"
          accept=".py,text/x-python"
          multiple
          disabled={!configReady}
          onChange={(event) => {
            if (event.target.files) {
              onFiles(event.target.files);
            }
            event.target.value = "";
          }}
        />
        <span className="upload-plus" aria-hidden="true">
          +
        </span>
        <strong>Upload strategies</strong>
        <small>One or many .py files · up to {maxSizeMb} MB each</small>
      </label>

      {uploadError ? (
        <p className="rail-error" role="alert">
          {uploadError}
        </p>
      ) : null}

      {queue.length > 0 ? (
        <section className="rail-section" aria-labelledby="ready-heading">
          <div className="rail-heading">
            <h2 id="ready-heading">Ready to run</h2>
            <span>{queue.length}</span>
          </div>
          <div className="queue-list">
            {queue.map((item) => (
              <div
                className={`queue-item ${
                  selectedQueueId === item.clientId ? "is-selected" : ""
                }`}
                key={item.clientId}
              >
                <button
                  type="button"
                  onClick={() => onSelectQueue(item.clientId)}
                  aria-current={
                    selectedQueueId === item.clientId ? "page" : undefined
                  }
                >
                  <span
                    className={`status-dot status-${item.status}`}
                    aria-hidden="true"
                  />
                  <span>
                    <strong title={item.file.name}>
                      {shortFileName(item.file.name)}
                    </strong>
                    <small>
                      {item.status === "running"
                        ? "Backtest in progress"
                        : item.customise
                          ? "Custom parameters"
                          : "Competition defaults"}
                    </small>
                  </span>
                </button>
                {item.status !== "running" ? (
                  <button
                    className="remove-queue"
                    type="button"
                    aria-label={`Remove ${item.file.name} from the upload queue`}
                    onClick={() => onRemoveQueue(item.clientId)}
                  >
                    ×
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {history.length > 0 ? (
        <section
          className="rail-section history-section"
          aria-labelledby="history-heading"
        >
          <div className="rail-heading">
            <h2 id="history-heading">Test history</h2>
            <span>{history.length}</span>
          </div>
          <div className="history-list">
            {history.map((test) => (
              <button
                className={`history-item ${
                  selectedTestId === test.id ? "is-selected" : ""
                }`}
                type="button"
                key={test.id}
                onClick={() => onSelectTest(test)}
                aria-current={selectedTestId === test.id ? "page" : undefined}
              >
                <span className="history-title">
                  <strong>{test.id}</strong>
                  <small>{createdLabel(test.created_at)}</small>
                </span>
                <span className="history-file" title={test.original_filename}>
                  {shortFileName(test.original_filename)}
                </span>
                {test.summary ? (
                  <span className="history-points">
                    <span>
                      Score <strong>{formatNumber(test.summary.score)}</strong>
                    </span>
                    <span>
                      Mean <strong>{formatCurrency(test.summary.mean_daily_pnl)}</strong>
                    </span>
                    <span>
                      Std <strong>{formatCurrency(test.summary.std_daily_pnl)}</strong>
                    </span>
                  </span>
                ) : (
                  <span className={`history-status history-${test.status}`}>
                    {test.status === "failed" ? "Run failed" : test.status}
                  </span>
                )}
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </aside>
  );
}
