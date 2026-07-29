import assert from "node:assert/strict";
import { once } from "node:events";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  startLocalBacktestTestServer,
  validateBacktestRequest,
} from "./local-backtest-api.mjs";

const frontendDirectory = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(frontendDirectory, "..");

const zeroStrategy = `import numpy as np

def getMyPosition(prices):
    return np.zeros(prices.shape[0], dtype=int)
`;

test("validates filenames and parameter ranges", () => {
  assert.throws(
    () =>
      validateBacktestRequest(
        {
          filename: "notes.txt",
          source: "hello",
          parameters: {},
        },
        1_000,
      ),
    /ending in \.py/,
  );

  assert.throws(
    () =>
      validateBacktestRequest(
        {
          filename: "strategy.py",
          source: zeroStrategy,
          parameters: { commission_rate: -1 },
        },
        10_000,
      ),
    /commission_rate/,
  );
});

test("stores a strategy, complete results, CSV, and history", async (context) => {
  const temporaryRoot = await mkdtemp(join(tmpdir(), "algothon-api-"));
  const storageRoot = join(temporaryRoot, "runs");
  const priceFile = join(temporaryRoot, "prices.txt");
  await writeFile(
    priceFile,
    "AAA BBB\n100 50\n101 49\n102 51\n103 52\n104 54\n",
    "utf8",
  );

  const { server } = await startLocalBacktestTestServer({
    projectRoot,
    storageRoot,
    priceFile,
    executionTimeoutMs: 15_000,
    maxConcurrentRuns: 1,
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");

  context.after(async () => {
    server.close();
    await once(server, "close");
    await rm(temporaryRoot, { recursive: true, force: true });
  });

  const address = server.address();
  assert(address && typeof address === "object");
  const baseUrl = `http://127.0.0.1:${address.port}`;
  const uploadResponse = await fetch(`${baseUrl}/api/tests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: "zero_strategy.py",
      source: zeroStrategy,
      parameters: { num_test_days: 3 },
    }),
  });

  if (uploadResponse.status !== 201) {
    assert.fail(await uploadResponse.text());
  }
  const manifest = await uploadResponse.json();
  assert.match(manifest.id, /^TEST_[A-F0-9]{8}$/);
  assert.equal(manifest.status, "completed");
  assert.equal(manifest.summary.score, 0);

  const runDirectory = join(storageRoot, manifest.id);
  assert.equal(
    await readFile(join(runDirectory, `${manifest.id}.py`), "utf8"),
    zeroStrategy,
  );
  assert.match(
    await readFile(join(runDirectory, "results.csv"), "utf8"),
    new RegExp(`metadata,\\$\\.test_id,string,\"\"\"${manifest.id}\"\"\"`),
  );

  const historyResponse = await fetch(`${baseUrl}/api/tests`);
  const history = await historyResponse.json();
  assert.equal(history[0].id, manifest.id);
  assert.equal(history[0].summary.mean_daily_pnl, 0);

  const resultsResponse = await fetch(
    `${baseUrl}/api/tests/${manifest.id}/results`,
  );
  const results = await resultsResponse.json();
  assert.equal(results.metadata.run_days, 3);
  assert.equal(results.metadata.test_id, manifest.id);

  const sourceResponse = await fetch(
    `${baseUrl}/api/tests/${manifest.id}/strategy`,
  );
  assert.equal(sourceResponse.status, 200);
  assert.equal(await sourceResponse.text(), zeroStrategy);

  const csvResponse = await fetch(
    `${baseUrl}/api/tests/${manifest.id}/results.csv`,
  );
  assert.equal(csvResponse.status, 200);
  assert.match(await csvResponse.text(), new RegExp(manifest.id));

  const failedResponse = await fetch(`${baseUrl}/api/tests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: "broken_strategy.py",
      source:
        "def getMyPosition(prices):\n    raise RuntimeError('test failure')\n",
      parameters: { num_test_days: 3 },
    }),
  });
  assert.equal(failedResponse.status, 201);
  const failedManifest = await failedResponse.json();
  assert.equal(failedManifest.status, "failed");
  assert.match(failedManifest.error, /test failure/);
  assert.equal(
    await readFile(
      join(storageRoot, failedManifest.id, `${failedManifest.id}.py`),
      "utf8",
    ),
    "def getMyPosition(prices):\n    raise RuntimeError('test failure')\n",
  );

  const updatedHistory = await (await fetch(`${baseUrl}/api/tests`)).json();
  assert.equal(updatedHistory.length, 2);
  assert.equal(updatedHistory[0].id, failedManifest.id);
});
