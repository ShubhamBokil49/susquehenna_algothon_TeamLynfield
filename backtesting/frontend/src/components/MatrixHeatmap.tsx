type MatrixHeatmapProps = {
  title: string;
  kicker: string;
  matrix: number[][];
  days: number[];
  positiveLabel: string;
  negativeLabel: string;
};

function getMaxAbs(matrix: number[][]): number {
  return Math.max(
    1,
    ...matrix.flat().map((value) => Math.abs(value)),
  );
}

function colorFor(value: number, maxAbs: number): string {
  if (value === 0) {
    return "#e2e8f0";
  }

  const alpha = Math.min(0.92, 0.18 + (Math.abs(value) / maxAbs) * 0.74);
  return value > 0 ? `rgba(5, 150, 105, ${alpha})` : `rgba(220, 38, 38, ${alpha})`;
}

function getMatrixStats(matrix: number[][]) {
  const values = matrix.flat();
  const nonZeroCells = values.filter((value) => value !== 0).length;
  const activeRows = matrix.filter((row) => row.some((value) => value !== 0)).length;
  const activeColumns = matrix[0]?.reduce((count, _, columnIndex) => {
    return matrix.some((row) => row[columnIndex] !== 0) ? count + 1 : count;
  }, 0) ?? 0;

  return { nonZeroCells, activeRows, activeColumns };
}

export function MatrixHeatmap({
  title,
  kicker,
  matrix,
  days,
  positiveLabel,
  negativeLabel,
}: MatrixHeatmapProps) {
  const maxAbs = getMaxAbs(matrix);
  const nColumns = matrix[0]?.length ?? 0;
  const { nonZeroCells, activeRows, activeColumns } = getMatrixStats(matrix);

  return (
    <section className="data-panel matrix-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">{kicker}</p>
          <h2>{title}</h2>
        </div>
        <span className="panel-count">
          {matrix.length} x {nColumns}
        </span>
      </div>

      {matrix.length === 0 || nColumns === 0 ? (
        <p className="empty-state">No matrix data available.</p>
      ) : (
        <>
          <div className="matrix-meta">
            <span>{nonZeroCells} active cells</span>
            <span>{activeRows} active days</span>
            <span>{activeColumns} active instruments</span>
          </div>
          <div className="matrix-legend" aria-label={`${title} legend`}>
            <span>
              <i className="matrix-legend-negative" />
              {negativeLabel}
            </span>
            <span>
              <i className="matrix-legend-zero" />
              Zero
            </span>
            <span>
              <i className="matrix-legend-positive" />
              {positiveLabel}
            </span>
          </div>
          <div className="matrix-frame">
            <span className="matrix-axis-title matrix-axis-title-y">Days</span>
            <div className="matrix-body">
              <span className="matrix-axis-title matrix-axis-title-x">Instruments</span>
              <div className="matrix-scroll" aria-label={title}>
                <div
                  className="matrix-grid"
                  style={{ gridTemplateColumns: `repeat(${nColumns}, minmax(8px, 1fr))` }}
                >
                  {matrix.map((row, rowIndex) =>
                    row.map((value, columnIndex) => (
                      <span
                        className="matrix-cell"
                        key={`${rowIndex}-${columnIndex}`}
                        title={`Day ${days[rowIndex] ?? rowIndex}, instrument ${columnIndex}: ${value}`}
                        style={{ backgroundColor: colorFor(value, maxAbs) }}
                      />
                    )),
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
