type SeriesPoint = {
  day: number;
  value: number;
};

type DualSeriesPoint = {
  day: number;
  primary: number;
  secondary: number;
};

type LineChartProps = {
  data: SeriesPoint[];
  title: string;
  tone?: "blue" | "green" | "red" | "amber";
  domain?: ChartDomainOptions;
  showZeroLine?: boolean;
  formatValue?: (value: number) => string;
};

type BarChartProps = {
  data: SeriesPoint[];
  title: string;
  domain?: ChartDomainOptions;
  showZeroLine?: boolean;
  formatValue?: (value: number) => string;
};

type DualLineChartProps = {
  data: DualSeriesPoint[];
  title: string;
  primaryLabel: string;
  secondaryLabel: string;
  domain?: ChartDomainOptions;
  showZeroLine?: boolean;
  formatValue?: (value: number) => string;
};

type ChartDomainOptions = {
  includeZero?: boolean;
  fixedMin?: number;
  fixedMax?: number;
};

const chartWidth = 720;
const chartHeight = 260;
const padding = {
  top: 18,
  right: 24,
  bottom: 32,
  left: 58,
};

const tones = {
  blue: "#2563eb",
  green: "#059669",
  red: "#dc2626",
  amber: "#d97706",
};

function getRange(
  values: number[],
  options: ChartDomainOptions = {},
): { min: number; max: number } {
  if (values.length === 0) {
    return {
      min: options.fixedMin ?? 0,
      max: options.fixedMax ?? 1,
    };
  }

  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  let min = rawMin;
  let max = rawMax;

  if (options.includeZero) {
    min = Math.min(min, 0);
    max = Math.max(max, 0);
  }

  if (options.fixedMin !== undefined) {
    min = options.fixedMin;
  }

  if (options.fixedMax !== undefined) {
    max = options.fixedMax;
  }

  if (min === max) {
    if (options.includeZero && min === 0) {
      return { min: 0, max: 1 };
    }

    if (options.fixedMin !== undefined && options.fixedMax === undefined) {
      return { min, max: min + 1 };
    }

    if (options.fixedMax !== undefined && options.fixedMin === undefined) {
      return { min: max - 1, max };
    }

    return { min: min - 1, max: max + 1 };
  }

  const paddingValue = (max - min) * 0.08;
  const zeroIsLowerBound =
    options.includeZero && rawMin >= 0 && options.fixedMin === undefined;
  const zeroIsUpperBound =
    options.includeZero && rawMax <= 0 && options.fixedMax === undefined;

  return {
    min:
      options.fixedMin === undefined && !zeroIsLowerBound
        ? min - paddingValue
        : min,
    max:
      options.fixedMax === undefined && !zeroIsUpperBound
        ? max + paddingValue
        : max,
  };
}

function xFor(index: number, length: number): number {
  const innerWidth = chartWidth - padding.left - padding.right;
  return padding.left + (innerWidth * index) / Math.max(length - 1, 1);
}

function yFor(value: number, min: number, max: number): number {
  const innerHeight = chartHeight - padding.top - padding.bottom;
  return padding.top + ((max - value) / (max - min)) * innerHeight;
}

function linePath(data: SeriesPoint[], min: number, max: number): string {
  return data
    .map((point, index) => {
      const command = index === 0 ? "M" : "L";
      return `${command} ${xFor(index, data.length).toFixed(2)} ${yFor(point.value, min, max).toFixed(2)}`;
    })
    .join(" ");
}

function AxisLabels({
  min,
  max,
  showZero,
  formatValue,
}: {
  min: number;
  max: number;
  showZero?: boolean;
  formatValue: (value: number) => string;
}) {
  return (
    <>
      <text className="chart-axis-label" x={padding.left - 10} y={padding.top + 8}>
        {formatValue(max)}
      </text>
      <text className="chart-axis-label" x={padding.left - 10} y={chartHeight - padding.bottom}>
        {formatValue(min)}
      </text>
      {showZero && min < 0 && max > 0 ? (
        <text className="chart-axis-label chart-zero-label" x={padding.left - 10} y={yFor(0, min, max) + 4}>
          {formatValue(0)}
        </text>
      ) : null}
    </>
  );
}

function ZeroLine({ min, max }: { min: number; max: number }) {
  if (min > 0 || max < 0) {
    return null;
  }

  const zeroY = yFor(0, min, max);

  return (
    <line
      className="chart-zero-line"
      x1={padding.left}
      x2={chartWidth - padding.right}
      y1={zeroY}
      y2={zeroY}
    />
  );
}

function ChartFrame({
  children,
  title,
  legend,
  empty = false,
}: {
  children: React.ReactNode;
  title: string;
  legend?: React.ReactNode;
  empty?: boolean;
}) {
  return (
    <section
      className={`chart-panel ${empty ? "chart-panel-empty" : ""}`}
      aria-label={title}
    >
      <div className="chart-panel-header">
        <h2>{title}</h2>
        {legend}
      </div>
      <svg
        className="chart-svg"
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        role="img"
        aria-label={empty ? `${title}: no backtest data yet` : title}
      >
        <line
          className="chart-grid-line"
          x1={padding.left}
          x2={chartWidth - padding.right}
          y1={padding.top}
          y2={padding.top}
        />
        <line
          className="chart-grid-line"
          x1={padding.left}
          x2={chartWidth - padding.right}
          y1={(chartHeight - padding.bottom + padding.top) / 2}
          y2={(chartHeight - padding.bottom + padding.top) / 2}
        />
        <line
          className="chart-grid-line"
          x1={padding.left}
          x2={chartWidth - padding.right}
          y1={chartHeight - padding.bottom}
          y2={chartHeight - padding.bottom}
        />
        <line
          className="chart-axis"
          x1={padding.left}
          x2={padding.left}
          y1={padding.top}
          y2={chartHeight - padding.bottom}
        />
        <line
          className="chart-axis"
          x1={padding.left}
          x2={chartWidth - padding.right}
          y1={chartHeight - padding.bottom}
          y2={chartHeight - padding.bottom}
        />
        {children}
        {empty ? (
          <text
            className="chart-empty-label"
            x={chartWidth / 2}
            y={(chartHeight - padding.bottom + padding.top) / 2 + 4}
          >
            Waiting for backtest data
          </text>
        ) : null}
      </svg>
    </section>
  );
}

export function LineChart({
  data,
  title,
  tone = "blue",
  domain = {},
  showZeroLine = false,
  formatValue = String,
}: LineChartProps) {
  const { min, max } = getRange(data.map((point) => point.value), domain);
  const isEmpty = data.length === 0;

  return (
    <ChartFrame title={title} empty={isEmpty}>
      {!isEmpty ? (
        <AxisLabels
          min={min}
          max={max}
          showZero={showZeroLine}
          formatValue={formatValue}
        />
      ) : null}
      {showZeroLine && !isEmpty ? <ZeroLine min={min} max={max} /> : null}
      <path className="chart-line" d={linePath(data, min, max)} stroke={tones[tone]} />
      {!isEmpty ? (
        <>
          <text className="chart-x-label" x={padding.left} y={chartHeight - 10}>
            Day {data[0]?.day}
          </text>
          <text className="chart-x-label chart-x-label-end" x={chartWidth - padding.right} y={chartHeight - 10}>
            Day {data[data.length - 1]?.day}
          </text>
        </>
      ) : null}
    </ChartFrame>
  );
}

export function BarChart({
  data,
  title,
  domain = {},
  showZeroLine = false,
  formatValue = String,
}: BarChartProps) {
  const { min, max } = getRange(data.map((point) => point.value), domain);
  const isEmpty = data.length === 0;
  const baseline = yFor(0, min, max);
  const innerWidth = chartWidth - padding.left - padding.right;
  const slotWidth = innerWidth / Math.max(data.length, 1);
  const barWidth = Math.max(Math.min(slotWidth * 0.72, 18), 1);

  return (
    <ChartFrame title={title} empty={isEmpty}>
      {!isEmpty ? (
        <AxisLabels
          min={min}
          max={max}
          showZero={showZeroLine}
          formatValue={formatValue}
        />
      ) : null}
      {showZeroLine && !isEmpty ? <ZeroLine min={min} max={max} /> : null}
      {data.map((point, index) => {
        const x = padding.left + slotWidth * index + (slotWidth - barWidth) / 2;
        const y = yFor(point.value, min, max);
        const height = Math.max(Math.abs(baseline - y), 1);
        const isPositive = point.value >= 0;
        return (
          <rect
            className="chart-bar"
            key={point.day}
            x={x}
            y={isPositive ? y : baseline}
            width={barWidth}
            height={height}
            fill={isPositive ? "#059669" : "#dc2626"}
          />
        );
      })}
      {!isEmpty ? (
        <>
          <text className="chart-x-label" x={padding.left} y={chartHeight - 10}>
            Day {data[0]?.day}
          </text>
          <text className="chart-x-label chart-x-label-end" x={chartWidth - padding.right} y={chartHeight - 10}>
            Day {data[data.length - 1]?.day}
          </text>
        </>
      ) : null}
    </ChartFrame>
  );
}

export function DualLineChart({
  data,
  title,
  primaryLabel,
  secondaryLabel,
  domain = {},
  showZeroLine = false,
  formatValue = String,
}: DualLineChartProps) {
  const isEmpty = data.length === 0;
  const primaryData = data.map((point) => ({
    day: point.day,
    value: point.primary,
  }));
  const secondaryData = data.map((point) => ({
    day: point.day,
    value: point.secondary,
  }));
  const { min, max } = getRange(
    data.flatMap((point) => [point.primary, point.secondary]),
    domain,
  );

  return (
    <ChartFrame
      title={title}
      empty={isEmpty}
      legend={
        <div className="chart-legend-row" aria-label={`${primaryLabel} and ${secondaryLabel} legend`}>
          <span>
            <i style={{ backgroundColor: "#7c3aed" }} />
            {primaryLabel}
          </span>
          <span>
            <i style={{ backgroundColor: "#ea580c" }} />
            {secondaryLabel}
          </span>
        </div>
      }
    >
      {!isEmpty ? (
        <AxisLabels
          min={min}
          max={max}
          showZero={showZeroLine}
          formatValue={formatValue}
        />
      ) : null}
      {showZeroLine && !isEmpty ? <ZeroLine min={min} max={max} /> : null}
      <path className="chart-line" d={linePath(primaryData, min, max)} stroke="#7c3aed" />
      <path className="chart-line chart-line-soft" d={linePath(secondaryData, min, max)} stroke="#ea580c" />
    </ChartFrame>
  );
}
