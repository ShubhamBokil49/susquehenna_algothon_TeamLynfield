import type { BacktestResults } from "./resultTypes";

export type BacktestParameters = {
  commission_rate: number;
  position_limit_dollars: number;
  instrument_0_commission_rate: number;
  instrument_0_position_limit_dollars: number;
  num_test_days: number;
  start_day: number | null;
  end_day: number | null;
  function_name: string;
};

export type BacktestConfig = {
  defaults: BacktestParameters;
  price_data_name: string;
  max_upload_bytes: number;
  execution_timeout_seconds: number;
  max_concurrent_runs: number;
};

export type TestSummary = {
  score: number;
  total_pnl: number;
  mean_daily_pnl: number;
  std_daily_pnl: number;
  max_drawdown: number;
  total_trades: number;
};

export type TestStatus = "queued" | "running" | "completed" | "failed";

export type TestManifest = {
  id: string;
  status: TestStatus;
  original_filename: string;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  parameters: BacktestParameters;
  summary: TestSummary | null;
  error: string | null;
};

type ApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
  };
};

export class BacktestApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = "BacktestApiError";
    this.code = code;
    this.status = status;
  }
}

async function requestJson<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      cache: "no-store",
      ...options,
    });
  } catch {
    throw new BacktestApiError(
      "The local runner is unavailable. Start this app with npm run dev.",
      "LOCAL_RUNNER_UNAVAILABLE",
      0,
    );
  }

  if (!response.ok) {
    let body: ApiErrorBody = {};
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      // The stable fallback below covers non-JSON development-server errors.
    }
    throw new BacktestApiError(
      body.error?.message ?? `The request failed with status ${response.status}.`,
      body.error?.code ?? "REQUEST_FAILED",
      response.status,
    );
  }

  return (await response.json()) as T;
}

export function loadBacktestConfig(): Promise<BacktestConfig> {
  return requestJson<BacktestConfig>("/api/config");
}

export function listTests(): Promise<TestManifest[]> {
  return requestJson<TestManifest[]>("/api/tests");
}

export async function createTest(
  file: File,
  parameters: BacktestParameters,
): Promise<TestManifest> {
  const source = await file.text();
  return requestJson<TestManifest>("/api/tests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: file.name,
      source,
      parameters,
    }),
  });
}

export function loadTestResults(testId: string): Promise<BacktestResults> {
  return requestJson<BacktestResults>(
    `/api/tests/${encodeURIComponent(testId)}/results`,
  );
}

export function storedStrategyUrl(testId: string): string {
  return `/api/tests/${encodeURIComponent(testId)}/strategy`;
}

export function resultsCsvUrl(testId: string): string {
  return `/api/tests/${encodeURIComponent(testId)}/results.csv`;
}
