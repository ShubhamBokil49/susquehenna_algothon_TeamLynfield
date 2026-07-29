import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";
import { EmptyDashboard } from "./components/EmptyDashboard";
import { ResultsDashboard } from "./components/ResultsDashboard";
import { RunSetup, type QueuedStrategy } from "./components/RunSetup";
import { TestRail } from "./components/TestRail";
import {
  BacktestApiError,
  createTest,
  listTests,
  loadBacktestConfig,
  loadTestResults,
  type BacktestConfig,
  type TestManifest,
} from "./data/backtestApi";
import type { BacktestResults } from "./data/resultTypes";

function uniqueClientId(): string {
  return globalThis.crypto?.randomUUID?.() ??
    `upload-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function errorMessage(error: unknown): string {
  if (error instanceof BacktestApiError || error instanceof Error) {
    return error.message;
  }
  return "The local backtest could not be completed.";
}

function App() {
  const [config, setConfig] = useState<BacktestConfig | null>(null);
  const [history, setHistory] = useState<TestManifest[]>([]);
  const [queue, setQueue] = useState<QueuedStrategy[]>([]);
  const [selectedQueueId, setSelectedQueueId] = useState<string | null>(null);
  const [selectedTestId, setSelectedTestId] = useState<string | null>(null);
  const [resultsById, setResultsById] = useState<Record<string, BacktestResults>>(
    {},
  );
  const [loadingTestIds, setLoadingTestIds] = useState<Set<string>>(new Set());
  const [resultErrors, setResultErrors] = useState<Record<string, string>>({});
  const [startupError, setStartupError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([loadBacktestConfig(), listTests()])
      .then(([loadedConfig, loadedHistory]) => {
        if (!active) {
          return;
        }
        setConfig(loadedConfig);
        setHistory(loadedHistory);
      })
      .catch((error: unknown) => {
        if (active) {
          setStartupError(errorMessage(error));
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const manifestsById = useMemo(
    () => new Map(history.map((test) => [test.id, test])),
    [history],
  );
  const selectedQueue =
    queue.find((item) => item.clientId === selectedQueueId) ?? null;
  const selectedManifest = selectedTestId
    ? manifestsById.get(selectedTestId) ?? null
    : null;
  const readyCount = queue.filter((item) => item.status === "ready").length;

  const upsertHistory = useCallback((manifest: TestManifest) => {
    setHistory((current) => [
      manifest,
      ...current.filter((test) => test.id !== manifest.id),
    ]);
  }, []);

  const openTest = useCallback(
    async (manifest: TestManifest) => {
      setSelectedQueueId(null);
      setSelectedTestId(manifest.id);
      setResultErrors((current) => {
        const next = { ...current };
        delete next[manifest.id];
        return next;
      });

      if (manifest.status !== "completed" || resultsById[manifest.id]) {
        return;
      }

      setLoadingTestIds((current) => new Set(current).add(manifest.id));
      try {
        const results = await loadTestResults(manifest.id);
        setResultsById((current) => ({ ...current, [manifest.id]: results }));
      } catch (error) {
        setResultErrors((current) => ({
          ...current,
          [manifest.id]: errorMessage(error),
        }));
      } finally {
        setLoadingTestIds((current) => {
          const next = new Set(current);
          next.delete(manifest.id);
          return next;
        });
      }
    },
    [resultsById],
  );

  const handleFiles = (files: FileList | File[]) => {
    if (!config) {
      return;
    }

    const accepted: QueuedStrategy[] = [];
    const rejected: string[] = [];
    Array.from(files).forEach((file) => {
      if (!file.name.toLowerCase().endsWith(".py")) {
        rejected.push(`${file.name} is not a .py file`);
      } else if (file.size === 0) {
        rejected.push(`${file.name} is empty`);
      } else if (file.size > config.max_upload_bytes) {
        rejected.push(`${file.name} is larger than the local upload limit`);
      } else {
        accepted.push({
          clientId: uniqueClientId(),
          file,
          customise: false,
          parameters: { ...config.defaults },
          status: "ready",
          error: null,
        });
      }
    });

    setUploadError(rejected.length > 0 ? `${rejected.join(". ")}.` : null);
    if (accepted.length > 0) {
      setQueue((current) => [...current, ...accepted]);
      setSelectedQueueId(accepted[0]?.clientId ?? null);
    }
  };

  const updateQueueItem = (updated: QueuedStrategy) => {
    setQueue((current) =>
      current.map((item) =>
        item.clientId === updated.clientId ? updated : item,
      ),
    );
  };

  const runQueueItem = useCallback(
    async (item: QueuedStrategy) => {
      setQueue((current) =>
        current.map((queued) =>
          queued.clientId === item.clientId
            ? { ...queued, status: "running", error: null }
            : queued,
        ),
      );

      try {
        const manifest = await createTest(item.file, item.parameters);
        upsertHistory(manifest);
        setQueue((current) =>
          current.filter((queued) => queued.clientId !== item.clientId),
        );
        if (selectedQueueId === item.clientId) {
          setSelectedQueueId(null);
        }
        await openTest(manifest);
      } catch (error) {
        setQueue((current) =>
          current.map((queued) =>
            queued.clientId === item.clientId
              ? {
                  ...queued,
                  status: "error",
                  error: errorMessage(error),
                }
              : queued,
          ),
        );
      }
    },
    [openTest, selectedQueueId, upsertHistory],
  );

  const runAllReady = async () => {
    const readyItems = queue.filter((item) => item.status === "ready");
    await Promise.all(readyItems.map((item) => runQueueItem(item)));
  };

  if (startupError) {
    return (
      <main className="startup-screen">
        <div className="startup-mark" aria-hidden="true">
          A
        </div>
        <p className="section-kicker">Local runner unavailable</p>
        <h1>Start from the frontend.</h1>
        <p>{startupError}</p>
        <code>cd frontend · npm run dev</code>
      </main>
    );
  }

  return (
    <div className="workspace-shell">
      <a className="skip-link" href="#workspace-main">
        Skip to backtest workspace
      </a>
      <TestRail
        configReady={Boolean(config)}
        maxUploadBytes={config?.max_upload_bytes ?? 1_000_000}
        queue={queue}
        history={history}
        selectedQueueId={selectedQueueId}
        selectedTestId={selectedTestId}
        uploadError={uploadError}
        onFiles={handleFiles}
        onSelectQueue={(clientId) => setSelectedQueueId(clientId)}
        onRemoveQueue={(clientId) => {
          setQueue((current) =>
            current.filter((item) => item.clientId !== clientId),
          );
          if (selectedQueueId === clientId) {
            setSelectedQueueId(null);
          }
        }}
        onSelectTest={(test) => void openTest(test)}
      />

      <main className="workspace-main" id="workspace-main">
        {!config ? (
          <section className="workspace-loading" aria-live="polite">
            <span className="loading-line" />
            <span className="loading-line loading-line-short" />
            <p>Preparing the local strategy lab…</p>
          </section>
        ) : selectedQueue ? (
          <RunSetup
            item={selectedQueue}
            config={config}
            readyCount={readyCount}
            onChange={updateQueueItem}
            onRun={(item) => void runQueueItem(item)}
            onRunAll={() => void runAllReady()}
          />
        ) : selectedManifest ? (
          selectedManifest.status === "failed" ? (
            <section
              className="failed-run"
              id={`panel-${selectedManifest.id}`}
              role="tabpanel"
            >
              <p className="section-kicker">Saved attempt · {selectedManifest.id}</p>
              <h1>This strategy did not finish.</h1>
              <p>
                The source and parameters were kept, so you can inspect the
                attempt before uploading a corrected version.
              </p>
              <pre>{selectedManifest.error ?? "The backtest failed."}</pre>
              <a
                href={`/api/tests/${encodeURIComponent(selectedManifest.id)}/strategy`}
                download
              >
                View stored Python file
              </a>
            </section>
          ) : loadingTestIds.has(selectedManifest.id) ? (
            <section className="workspace-loading" aria-live="polite">
              <span className="loading-line" />
              <span className="loading-line loading-line-short" />
              <p>Opening {selectedManifest.id}…</p>
            </section>
          ) : resultErrors[selectedManifest.id] ? (
            <section className="failed-run" role="alert">
              <p className="section-kicker">{selectedManifest.id}</p>
              <h1>The saved result could not be opened.</h1>
              <p>{resultErrors[selectedManifest.id]}</p>
              <button
                type="button"
                className="secondary-action"
                onClick={() => void openTest(selectedManifest)}
              >
                Try opening it again
              </button>
            </section>
          ) : resultsById[selectedManifest.id] ? (
            <ResultsDashboard
              manifest={selectedManifest}
              results={resultsById[selectedManifest.id]}
            />
          ) : null
        ) : (
          <EmptyDashboard />
        )}
      </main>
    </div>
  );
}

export default App;
