import { mockResults } from "./mockResults";
import type { BacktestResults } from "./resultTypes";

export type ResultsLoadSource = "generated" | "mock";

export type ResultsLoadResult = {
  results: BacktestResults;
  source: ResultsLoadSource;
  message: string;
};

export async function loadResults(): Promise<ResultsLoadResult> {
  try {
    const response = await fetch("/results.json", { cache: "no-store" });

    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    const results = (await response.json()) as BacktestResults;
    return {
      results,
      source: "generated",
      message: "Loaded /results.json from frontend/public.",
    };
  } catch (error) {
    const reason = error instanceof Error ? error.message : "unknown error";
    return {
      results: mockResults,
      source: "mock",
      message: `Using mock fallback because /results.json was unavailable (${reason}).`,
    };
  }
}
