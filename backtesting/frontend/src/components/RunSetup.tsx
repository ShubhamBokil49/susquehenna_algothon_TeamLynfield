import type {
  BacktestConfig,
  BacktestParameters,
} from "../data/backtestApi";

export type QueuedStrategy = {
  clientId: string;
  file: File;
  customise: boolean;
  parameters: BacktestParameters;
  status: "ready" | "running" | "error";
  error: string | null;
};

type RunSetupProps = {
  item: QueuedStrategy;
  config: BacktestConfig;
  readyCount: number;
  onChange: (item: QueuedStrategy) => void;
  onRun: (item: QueuedStrategy) => void;
  onRunAll: () => void;
};

type NumberParameter = Exclude<
  keyof BacktestParameters,
  "function_name"
>;

const parameterFields: Array<{
  key: NumberParameter;
  label: string;
  help: string;
  step: string;
  min?: string;
}> = [
  {
    key: "commission_rate",
    label: "Standard commission",
    help: "Decimal rate charged on traded notional.",
    step: "0.00001",
    min: "0",
  },
  {
    key: "position_limit_dollars",
    label: "Standard position limit",
    help: "Maximum dollar exposure per instrument.",
    step: "100",
    min: "1",
  },
  {
    key: "instrument_0_commission_rate",
    label: "Instrument 0 commission",
    help: "Special decimal commission rate for instrument 0.",
    step: "0.00001",
    min: "0",
  },
  {
    key: "instrument_0_position_limit_dollars",
    label: "Instrument 0 limit",
    help: "Special dollar exposure limit for instrument 0.",
    step: "100",
    min: "1",
  },
  {
    key: "num_test_days",
    label: "Scored days",
    help: "Used when the start day is left blank.",
    step: "1",
    min: "1",
  },
  {
    key: "start_day",
    label: "Start day",
    help: "Optional zero-based scored start, from day 1.",
    step: "1",
    min: "1",
  },
  {
    key: "end_day",
    label: "End day",
    help: "Optional inclusive end day.",
    step: "1",
    min: "1",
  },
];

function fileSizeLabel(bytes: number): string {
  if (bytes < 1_024) {
    return `${bytes} B`;
  }
  return `${(bytes / 1_024).toFixed(1)} KB`;
}

export function RunSetup({
  item,
  config,
  readyCount,
  onChange,
  onRun,
  onRunAll,
}: RunSetupProps) {
  const isRunning = item.status === "running";

  const updateParameter = (
    key: keyof BacktestParameters,
    value: number | string | null,
  ) => {
    onChange({
      ...item,
      parameters: {
        ...item.parameters,
        [key]: value,
      },
      error: null,
      status: "ready",
    });
  };

  return (
    <section className="run-setup" aria-labelledby="run-setup-title">
      <div className="setup-lead">
        <div>
          <p className="section-kicker">Fresh upload</p>
          <h1 id="run-setup-title">Ready for its first lap.</h1>
          <p className="setup-intro">
            Check the strategy, keep the competition defaults, or tune this run
            before it joins your test history.
          </p>
        </div>
        <div className="file-ticket" aria-label="Selected strategy file">
          <span>Python strategy</span>
          <strong>{item.file.name}</strong>
          <small>{fileSizeLabel(item.file.size)}</small>
        </div>
      </div>

      <div className="setup-question">
        <div>
          <h2>Would you like to customise the backtest?</h2>
          <p>
            Defaults are already loaded for {config.price_data_name}. You can
            inspect them without changing anything.
          </p>
        </div>
        <label className="customise-switch">
          <input
            type="checkbox"
            checked={item.customise}
            disabled={isRunning}
            onChange={(event) =>
              onChange({
                ...item,
                customise: event.target.checked,
                parameters: event.target.checked
                  ? item.parameters
                  : { ...config.defaults },
                error: null,
                status: "ready",
              })
            }
          />
          <span aria-hidden="true" />
          Customise this run
        </label>
      </div>

      <fieldset
        className="parameter-fieldset"
        disabled={!item.customise || isRunning}
      >
        <legend>Backtest parameters</legend>
        <div className="parameter-grid">
          {parameterFields.map((field) => {
            const value = item.parameters[field.key];
            const inputId = `${item.clientId}-${field.key}`;
            return (
              <label className="parameter-field" htmlFor={inputId} key={field.key}>
                <span>{field.label}</span>
                <input
                  id={inputId}
                  type="number"
                  inputMode="decimal"
                  min={field.min}
                  step={field.step}
                  value={value ?? ""}
                  placeholder="Auto"
                  onChange={(event) =>
                    updateParameter(
                      field.key,
                      event.target.value === ""
                        ? null
                        : Number(event.target.value),
                    )
                  }
                />
                <small>{field.help}</small>
              </label>
            );
          })}
          <label
            className="parameter-field parameter-function"
            htmlFor={`${item.clientId}-function-name`}
          >
            <span>Strategy function</span>
            <input
              id={`${item.clientId}-function-name`}
              type="text"
              value={item.parameters.function_name}
              autoComplete="off"
              spellCheck={false}
              onChange={(event) =>
                updateParameter("function_name", event.target.value)
              }
            />
            <small>The callable exported by the uploaded Python file.</small>
          </label>
        </div>
      </fieldset>

      {item.error ? (
        <p className="form-error" role="alert">
          <strong>This run did not start.</strong> {item.error}
        </p>
      ) : null}

      <div className="setup-actions">
        <button
          className="primary-action"
          type="button"
          disabled={isRunning}
          onClick={() => onRun(item)}
        >
          {isRunning ? "Running backtest…" : "Run this backtest"}
        </button>
        {readyCount > 1 ? (
          <button
            className="secondary-action"
            type="button"
            disabled={isRunning}
            onClick={onRunAll}
          >
            Run all {readyCount} ready files
          </button>
        ) : null}
        <p>
          <strong>Trusted files only.</strong> Python code runs on this computer.
          Backtests usually finish within {config.execution_timeout_seconds}{" "}
          seconds.
        </p>
      </div>
    </section>
  );
}
