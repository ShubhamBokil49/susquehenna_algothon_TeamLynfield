import { randomBytes } from "node:crypto";
import {
  createReadStream,
  existsSync,
} from "node:fs";
import {
  mkdir,
  readFile,
  readdir,
  stat,
  writeFile,
} from "node:fs/promises";
import { createServer as createHttpServer } from "node:http";
import { basename, join, resolve, win32 } from "node:path";
import { spawn } from "node:child_process";

const TEST_ID_PATTERN = /^TEST_[A-F0-9]{8}$/;
const DEFAULT_MAX_UPLOAD_BYTES = 1_000_000;
const DEFAULT_EXECUTION_TIMEOUT_MS = 90_000;
const DEFAULT_MAX_CONCURRENT_RUNS = 2;

export const DEFAULT_BACKTEST_PARAMETERS = Object.freeze({
  commission_rate: 0.0001,
  position_limit_dollars: 10_000,
  instrument_0_commission_rate: 0.00002,
  instrument_0_position_limit_dollars: 100_000,
  num_test_days: 250,
  start_day: null,
  end_day: null,
  function_name: "getMyPosition",
});

class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

class RunQueue {
  constructor(limit) {
    this.limit = limit;
    this.active = 0;
    this.waiters = [];
  }

  async run(callback) {
    if (this.active >= this.limit) {
      await new Promise((resolveWaiter) => this.waiters.push(resolveWaiter));
    }

    this.active += 1;
    try {
      return await callback();
    } finally {
      this.active -= 1;
      this.waiters.shift()?.();
    }
  }
}

function utcNow() {
  return new Date().toISOString();
}

function cleanOriginalFilename(filename) {
  if (typeof filename !== "string" || filename.trim().length === 0) {
    throw new ApiError(400, "INVALID_FILENAME", "The strategy needs a filename.");
  }

  const cleaned = basename(win32.basename(filename.trim()));
  if (
    cleaned.length > 255 ||
    /[\u0000-\u001f\u007f]/.test(cleaned) ||
    !cleaned.toLowerCase().endsWith(".py")
  ) {
    throw new ApiError(
      400,
      "INVALID_FILE_TYPE",
      "Choose a Python file ending in .py.",
    );
  }

  return cleaned;
}

function validateNumber(
  parameters,
  key,
  { minimum, maximum, integer = false },
) {
  const value = parameters[key];
  if (
    typeof value !== "number" ||
    !Number.isFinite(value) ||
    value < minimum ||
    value > maximum ||
    (integer && !Number.isInteger(value))
  ) {
    const range = `${minimum} to ${maximum}`;
    throw new ApiError(
      422,
      "INVALID_PARAMETERS",
      `${key} must be ${integer ? "a whole number" : "a number"} from ${range}.`,
    );
  }
  return value;
}

function validateOptionalDay(parameters, key) {
  const value = parameters[key];
  if (value === null || value === undefined) {
    return null;
  }

  if (!Number.isInteger(value) || value < 1 || value > 100_000) {
    throw new ApiError(
      422,
      "INVALID_PARAMETERS",
      `${key} must be blank or a whole number from 1 to 100000.`,
    );
  }
  return value;
}

export function validateBacktestRequest(payload, maxUploadBytes) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new ApiError(400, "INVALID_REQUEST", "The upload request is invalid.");
  }

  const originalFilename = cleanOriginalFilename(payload.filename);
  if (typeof payload.source !== "string" || payload.source.length === 0) {
    throw new ApiError(400, "EMPTY_FILE", "The selected Python file is empty.");
  }
  if (payload.source.includes("\0")) {
    throw new ApiError(
      400,
      "INVALID_SOURCE",
      "The Python file contains invalid null bytes.",
    );
  }

  const sourceBytes = Buffer.byteLength(payload.source, "utf8");
  if (sourceBytes > maxUploadBytes) {
    throw new ApiError(
      413,
      "UPLOAD_TOO_LARGE",
      `Python files must be ${maxUploadBytes.toLocaleString()} bytes or smaller.`,
    );
  }

  const submitted =
    payload.parameters &&
    typeof payload.parameters === "object" &&
    !Array.isArray(payload.parameters)
      ? payload.parameters
      : {};
  const values = { ...DEFAULT_BACKTEST_PARAMETERS, ...submitted };
  const parameters = {
    commission_rate: validateNumber(values, "commission_rate", {
      minimum: 0,
      maximum: 0.1,
    }),
    position_limit_dollars: validateNumber(values, "position_limit_dollars", {
      minimum: Number.EPSILON,
      maximum: 1_000_000_000,
    }),
    instrument_0_commission_rate: validateNumber(
      values,
      "instrument_0_commission_rate",
      {
        minimum: 0,
        maximum: 0.1,
      },
    ),
    instrument_0_position_limit_dollars: validateNumber(
      values,
      "instrument_0_position_limit_dollars",
      {
        minimum: Number.EPSILON,
        maximum: 1_000_000_000,
      },
    ),
    num_test_days: validateNumber(values, "num_test_days", {
      minimum: 1,
      maximum: 100_000,
      integer: true,
    }),
    start_day: validateOptionalDay(values, "start_day"),
    end_day: validateOptionalDay(values, "end_day"),
    function_name: values.function_name,
  };

  if (
    typeof parameters.function_name !== "string" ||
    !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(parameters.function_name)
  ) {
    throw new ApiError(
      422,
      "INVALID_PARAMETERS",
      "function_name must be a valid Python function name.",
    );
  }

  if (
    parameters.start_day !== null &&
    parameters.end_day !== null &&
    parameters.end_day < parameters.start_day
  ) {
    throw new ApiError(
      422,
      "INVALID_PARAMETERS",
      "end_day must be greater than or equal to start_day.",
    );
  }

  return {
    originalFilename,
    source: payload.source,
    parameters,
  };
}

function choosePythonExecutable(projectRoot) {
  if (process.env.PYTHON_EXECUTABLE) {
    return process.env.PYTHON_EXECUTABLE;
  }

  const candidates =
    process.platform === "win32"
      ? [
          join(projectRoot, ".venv", "Scripts", "python.exe"),
          join(projectRoot, "venv", "Scripts", "python.exe"),
        ]
      : [
          join(projectRoot, ".venv", "bin", "python"),
          join(projectRoot, "venv", "bin", "python"),
        ];

  return candidates.find((candidate) => existsSync(candidate)) ??
    (process.platform === "win32" ? "python" : "python3");
}

function choosePriceFile(projectRoot) {
  if (process.env.BACKTEST_PRICE_FILE) {
    return resolve(process.env.BACKTEST_PRICE_FILE);
  }

  const localPriceFile = join(projectRoot, "data", "prices.txt");
  if (existsSync(localPriceFile)) {
    return localPriceFile;
  }

  return join(projectRoot, "frontend", "testing", "prices_test.txt");
}

function collectProcessOutput(child, timeoutMs, input) {
  return new Promise((resolveProcess, rejectProcess) => {
    const stdout = [];
    const stderr = [];
    let outputBytes = 0;
    let settled = false;

    const finish = (callback, value) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      callback(value);
    };

    const capture = (target) => (chunk) => {
      outputBytes += chunk.length;
      if (outputBytes > 2_000_000) {
        child.kill();
        finish(
          rejectProcess,
          new ApiError(
            422,
            "EXCESSIVE_OUTPUT",
            "The strategy produced too much console output.",
          ),
        );
        return;
      }
      target.push(chunk);
    };

    child.stdout.on("data", capture(stdout));
    child.stderr.on("data", capture(stderr));
    child.on("error", (error) => finish(rejectProcess, error));
    child.on("close", (code) =>
      finish(resolveProcess, {
        code: code ?? -1,
        stdout: Buffer.concat(stdout).toString("utf8"),
        stderr: Buffer.concat(stderr).toString("utf8"),
      }),
    );

    const timeout = setTimeout(() => {
      child.kill();
      finish(
        rejectProcess,
        new ApiError(
          422,
          "RUN_TIMEOUT",
          `The strategy exceeded the ${Math.round(timeoutMs / 1000)}-second run limit.`,
        ),
      );
    }, timeoutMs);

    if (input === undefined) {
      child.stdin.end();
    } else {
      child.stdin.end(input, "utf8");
    }
  });
}

async function runPython(
  executable,
  args,
  { cwd, timeoutMs, input },
) {
  const child = spawn(executable, args, {
    cwd,
    windowsHide: true,
    shell: false,
    stdio: ["pipe", "pipe", "pipe"],
  });
  return collectProcessOutput(child, timeoutMs, input);
}

function lastProcessError(result, projectRoot) {
  const output = result.stderr.trim() || result.stdout.trim();
  const lastLine = output
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .at(-1);
  if (!lastLine) {
    return `The backtest process exited with code ${result.code}.`;
  }
  return lastLine.replaceAll(projectRoot, "<project>").slice(0, 1_000);
}

async function readJsonBody(request, maximumBytes) {
  const chunks = [];
  let totalBytes = 0;

  for await (const chunk of request) {
    totalBytes += chunk.length;
    if (totalBytes > maximumBytes) {
      throw new ApiError(
        413,
        "UPLOAD_TOO_LARGE",
        "The upload request is too large.",
      );
    }
    chunks.push(chunk);
  }

  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new ApiError(400, "INVALID_JSON", "The upload request is not valid JSON.");
  }
}

async function writeManifest(manifestPath, manifest) {
  manifest.updated_at = utcNow();
  await writeFile(
    manifestPath,
    `${JSON.stringify(manifest, null, 2)}\n`,
    "utf8",
  );
}

async function readManifest(storageRoot, testId) {
  if (!TEST_ID_PATTERN.test(testId)) {
    throw new ApiError(404, "TEST_NOT_FOUND", `Test ${testId} was not found.`);
  }

  try {
    return JSON.parse(
      await readFile(join(storageRoot, testId, "manifest.json"), "utf8"),
    );
  } catch {
    throw new ApiError(404, "TEST_NOT_FOUND", `Test ${testId} was not found.`);
  }
}

async function listManifests(storageRoot) {
  const entries = await readdir(storageRoot, { withFileTypes: true });
  const manifests = await Promise.all(
    entries
      .filter((entry) => entry.isDirectory() && TEST_ID_PATTERN.test(entry.name))
      .map(async (entry) => {
        try {
          return JSON.parse(
            await readFile(
              join(storageRoot, entry.name, "manifest.json"),
              "utf8",
            ),
          );
        } catch {
          return null;
        }
      }),
  );

  return manifests
    .filter(Boolean)
    .sort((first, second) => second.created_at.localeCompare(first.created_at));
}

function summaryFromResults(results) {
  const summary = results.summary;
  return {
    score: summary.score,
    total_pnl: summary.total_pnl,
    mean_daily_pnl: summary.mean_daily_pnl,
    std_daily_pnl: summary.std_daily_pnl,
    max_drawdown: summary.max_drawdown,
    total_trades: summary.total_trades,
  };
}

function sendJson(response, status, value) {
  const body = JSON.stringify(value);
  response.writeHead(status, {
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
    "X-Content-Type-Options": "nosniff",
  });
  response.end(body);
}

function sendError(response, error) {
  if (error instanceof ApiError) {
    sendJson(response, error.status, {
      error: { code: error.code, message: error.message },
    });
    return;
  }

  console.error("[backtest] Unexpected local API error", error);
  sendJson(response, 500, {
    error: {
      code: "INTERNAL_ERROR",
      message: "The local backtest service encountered an unexpected error.",
    },
  });
}

function isLoopbackAddress(address) {
  return (
    !address ||
    address === "127.0.0.1" ||
    address === "::1" ||
    address === "::ffff:127.0.0.1"
  );
}

function ensureSameOrigin(request) {
  const origin = request.headers.origin;
  const host = request.headers.host;
  if (!origin || !host) {
    return;
  }

  try {
    if (new URL(origin).host !== host) {
      throw new ApiError(
        403,
        "CROSS_ORIGIN_REQUEST",
        "Uploads are only accepted from the local backtester page.",
      );
    }
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(403, "CROSS_ORIGIN_REQUEST", "The request origin is invalid.");
  }
}

function safeRunFile(storageRoot, testId, filename) {
  if (!TEST_ID_PATTERN.test(testId)) {
    throw new ApiError(404, "TEST_NOT_FOUND", `Test ${testId} was not found.`);
  }
  return join(storageRoot, testId, filename);
}

async function sendFile(response, filePath, contentType, downloadName) {
  let fileStats;
  try {
    fileStats = await stat(filePath);
  } catch {
    throw new ApiError(
      409,
      "RESULTS_UNAVAILABLE",
      "This test does not have that artifact yet.",
    );
  }

  response.writeHead(200, {
    "Cache-Control": "no-store",
    "Content-Disposition": `attachment; filename="${downloadName}"`,
    "Content-Length": fileStats.size,
    "Content-Type": contentType,
    "X-Content-Type-Options": "nosniff",
  });
  createReadStream(filePath).pipe(response);
}

export function createLocalBacktestService(options = {}) {
  const projectRoot = resolve(options.projectRoot ?? "..");
  const storageRoot = resolve(
    options.storageRoot ??
      process.env.BACKTEST_STORAGE_DIR ??
      join(projectRoot, "backtest_runs"),
  );
  const priceFile = resolve(options.priceFile ?? choosePriceFile(projectRoot));
  const pythonExecutable =
    options.pythonExecutable ?? choosePythonExecutable(projectRoot);
  const maxUploadBytes =
    options.maxUploadBytes ?? DEFAULT_MAX_UPLOAD_BYTES;
  const executionTimeoutMs =
    options.executionTimeoutMs ?? DEFAULT_EXECUTION_TIMEOUT_MS;
  const maxConcurrentRuns =
    options.maxConcurrentRuns ?? DEFAULT_MAX_CONCURRENT_RUNS;
  const queue = new RunQueue(maxConcurrentRuns);

  async function initialise() {
    await mkdir(storageRoot, { recursive: true });
  }

  async function validatePythonSyntax(source, filename) {
    const validationCode =
      "import ast, sys; ast.parse(sys.stdin.read(), filename=sys.argv[1])";
    let result;
    try {
      result = await runPython(
        pythonExecutable,
        ["-I", "-B", "-c", validationCode, filename],
        {
          cwd: projectRoot,
          timeoutMs: 5_000,
          input: source,
        },
      );
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        503,
        "PYTHON_UNAVAILABLE",
        "Python could not be started from the local frontend setup.",
      );
    }

    if (result.code !== 0) {
      const message = lastProcessError(result, projectRoot)
        .replace(/^SyntaxError:\s*/i, "")
        .slice(0, 500);
      throw new ApiError(
        422,
        "INVALID_PYTHON",
        `The Python file has a syntax error: ${message}`,
      );
    }
  }

  async function createRun(payload) {
    const upload = validateBacktestRequest(payload, maxUploadBytes);
    if (!existsSync(priceFile)) {
      throw new ApiError(
        503,
        "PRICE_DATA_UNAVAILABLE",
        "The configured price data file is unavailable.",
      );
    }

    await validatePythonSyntax(upload.source, upload.originalFilename);

    let testId;
    let runDirectory;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      testId = `TEST_${randomBytes(4).toString("hex").toUpperCase()}`;
      runDirectory = join(storageRoot, testId);
      if (!existsSync(runDirectory)) {
        break;
      }
    }
    if (!testId || !runDirectory || existsSync(runDirectory)) {
      throw new ApiError(
        500,
        "ID_ALLOCATION_FAILED",
        "A unique test identifier could not be created.",
      );
    }

    await mkdir(runDirectory);
    const sourcePath = join(runDirectory, `${testId}.py`);
    const manifestPath = join(runDirectory, "manifest.json");
    const resultPath = join(runDirectory, "results.json");
    const csvPath = join(runDirectory, "results.csv");
    await writeFile(sourcePath, upload.source, "utf8");

    const createdAt = utcNow();
    const manifest = {
      id: testId,
      status: "queued",
      original_filename: upload.originalFilename,
      created_at: createdAt,
      updated_at: createdAt,
      completed_at: null,
      parameters: upload.parameters,
      summary: null,
      error: null,
    };
    await writeManifest(manifestPath, manifest);

    return queue.run(async () => {
      manifest.status = "running";
      await writeManifest(manifestPath, manifest);
      console.info(`[backtest] ${testId} started (${upload.originalFilename})`);

      const parameters = upload.parameters;
      const args = [
        "-I",
        "-B",
        join(projectRoot, "scripts", "run_backtest.py"),
        "--strategy",
        sourcePath,
        "--prices",
        priceFile,
        "--out",
        resultPath,
        "--csv-out",
        csvPath,
        "--test-id",
        testId,
        "--original-strategy-filename",
        upload.originalFilename,
        "--created-at",
        createdAt,
        "--commission",
        String(parameters.commission_rate),
        "--position-limit",
        String(parameters.position_limit_dollars),
        "--instrument-0-commission",
        String(parameters.instrument_0_commission_rate),
        "--instrument-0-position-limit",
        String(parameters.instrument_0_position_limit_dollars),
        "--num-test-days",
        String(parameters.num_test_days),
        "--function-name",
        parameters.function_name,
      ];
      if (parameters.start_day !== null) {
        args.push("--start-day", String(parameters.start_day));
      }
      if (parameters.end_day !== null) {
        args.push("--end-day", String(parameters.end_day));
      }

      try {
        const result = await runPython(pythonExecutable, args, {
          cwd: projectRoot,
          timeoutMs: executionTimeoutMs,
        });
        if (result.code !== 0) {
          throw new ApiError(
            422,
            "BACKTEST_FAILED",
            lastProcessError(result, projectRoot),
          );
        }

        const results = JSON.parse(await readFile(resultPath, "utf8"));
        manifest.status = "completed";
        manifest.summary = summaryFromResults(results);
        manifest.error = null;
        console.info(`[backtest] ${testId} completed`);
      } catch (error) {
        manifest.status = "failed";
        manifest.summary = null;
        manifest.error =
          error instanceof Error
            ? error.message.slice(0, 1_000)
            : "The backtest failed.";
        console.warn(`[backtest] ${testId} failed: ${manifest.error}`);
      }

      manifest.completed_at = utcNow();
      await writeManifest(manifestPath, manifest);
      return manifest;
    });
  }

  async function handle(request, response, next = () => {}) {
    if (!request.url?.startsWith("/api/")) {
      next();
      return;
    }

    try {
      if (!isLoopbackAddress(request.socket.remoteAddress)) {
        throw new ApiError(
          403,
          "LOCAL_ONLY",
          "The backtest runner only accepts requests from this computer.",
        );
      }

      const url = new URL(request.url, "http://localhost");
      const pathname = url.pathname;

      if (request.method === "GET" && pathname === "/api/config") {
        sendJson(response, 200, {
          defaults: DEFAULT_BACKTEST_PARAMETERS,
          price_data_name: basename(priceFile),
          max_upload_bytes: maxUploadBytes,
          execution_timeout_seconds: Math.round(executionTimeoutMs / 1000),
          max_concurrent_runs: maxConcurrentRuns,
        });
        return;
      }

      if (request.method === "GET" && pathname === "/api/tests") {
        sendJson(response, 200, await listManifests(storageRoot));
        return;
      }

      if (request.method === "POST" && pathname === "/api/tests") {
        ensureSameOrigin(request);
        const contentType = request.headers["content-type"] ?? "";
        if (!contentType.startsWith("application/json")) {
          throw new ApiError(
            415,
            "INVALID_CONTENT_TYPE",
            "Uploads must use JSON from the local frontend.",
          );
        }
        const payload = await readJsonBody(
          request,
          maxUploadBytes * 2 + 65_536,
        );
        sendJson(response, 201, await createRun(payload));
        return;
      }

      const match = pathname.match(
        /^\/api\/tests\/(TEST_[A-F0-9]{8})(?:\/(results|strategy|results\.csv))?$/,
      );
      if (request.method === "GET" && match) {
        const [, testId, artifact] = match;
        const manifest = await readManifest(storageRoot, testId);
        if (!artifact) {
          sendJson(response, 200, manifest);
          return;
        }
        if (artifact === "results") {
          const resultPath = safeRunFile(storageRoot, testId, "results.json");
          let results;
          try {
            results = JSON.parse(await readFile(resultPath, "utf8"));
          } catch {
            throw new ApiError(
              409,
              "RESULTS_UNAVAILABLE",
              `Completed results are not available for ${testId}.`,
            );
          }
          sendJson(response, 200, results);
          return;
        }
        if (artifact === "strategy") {
          await sendFile(
            response,
            safeRunFile(storageRoot, testId, `${testId}.py`),
            "text/x-python; charset=utf-8",
            `${testId}.py`,
          );
          return;
        }
        await sendFile(
          response,
          safeRunFile(storageRoot, testId, "results.csv"),
          "text/csv; charset=utf-8",
          `${testId}_results.csv`,
        );
        return;
      }

      throw new ApiError(404, "NOT_FOUND", "The local API route was not found.");
    } catch (error) {
      sendError(response, error);
    }
  }

  return {
    createRun,
    handle,
    initialise,
    paths: { priceFile, projectRoot, storageRoot },
  };
}

export function localBacktestApi(options = {}) {
  const service = createLocalBacktestService(options);
  return {
    name: "local-backtest-api",
    apply: "serve",
    async configureServer(server) {
      await service.initialise();
      server.middlewares.use((request, response, next) => {
        void service.handle(request, response, next);
      });
    },
  };
}

export async function startLocalBacktestTestServer(options = {}) {
  const service = createLocalBacktestService(options);
  await service.initialise();
  const server = createHttpServer((request, response) => {
    void service.handle(request, response, () => {
      response.writeHead(404);
      response.end();
    });
  });
  return { server, service };
}
