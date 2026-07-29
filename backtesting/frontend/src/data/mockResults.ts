import type {
  BacktestResults,
  BacktestWarning,
  ClippingEvent,
  DailyRecord,
  InstrumentSummary,
  TradeLog,
} from "./resultTypes";

const nInstruments = 50;
const nDays = 180;
const startDay = 1;
const endDay = nDays - 1;
const commissionRate = 0.001;
const positionLimitDollars = 10000;

function rounded(value: number, digits = 2): number {
  return Number(value.toFixed(digits));
}

function mockPrice(instrument: number, day: number): number {
  return rounded(72 + instrument * 1.4 + Math.sin(day / 11 + instrument * 0.31) * 5 + day * 0.04);
}

function makeMockResults(): BacktestResults {
  const dailyRecords: DailyRecord[] = [];
  const days: number[] = [];
  const dailyPnl: number[] = [];
  const grossDailyPnl: number[] = [];
  const cumulativePnl: number[] = [];
  const drawdown: number[] = [];
  const dailyTurnover: number[] = [];
  const dailyCommission: number[] = [];
  const positions: number[][] = [];
  const trades: number[][] = [];
  const tradeLogs: TradeLog[] = [];
  const instrumentPnlHistory: number[][] = [];
  const instrumentTurnoverHistory: number[][] = [];
  const instrumentCommissionHistory: number[][] = [];
  const clippingEvents: ClippingEvent[] = [];

  let runningPnl = 0;
  let runningGrossPnl = 0;
  let peakPnl = 0;

  for (let day = startDay; day <= endDay; day += 1) {
    const previousPositions = positions[positions.length - 1] ?? Array(nInstruments).fill(0);
    const dayPositions: number[] = [];
    const dayTrades: number[] = [];
    const instrumentPnl: number[] = [];
    const instrumentTurnover: number[] = [];
    const instrumentCommission: number[] = [];
    const dayTradeLogs: TradeLog[] = [];

    for (let instrument = 0; instrument < nInstruments; instrument += 1) {
      const currentPrice = mockPrice(instrument, day);
      const previousPrice = mockPrice(instrument, day - 1);
      const desiredPosition = Math.round(Math.sin(day / 9 + instrument * 0.37) * 44);
      const previousPosition = previousPositions[instrument] ?? 0;
      const signedQuantity = desiredPosition - previousPosition;
      const turnover = Math.abs(signedQuantity) * currentPrice;
      const commission = turnover * commissionRate;
      const grossPnl = previousPosition * (currentPrice - previousPrice);
      const netPnl = grossPnl - commission;

      dayPositions.push(desiredPosition);
      dayTrades.push(signedQuantity);
      instrumentTurnover.push(rounded(turnover));
      instrumentCommission.push(rounded(commission));
      instrumentPnl.push(rounded(netPnl));

      if (signedQuantity !== 0) {
        dayTradeLogs.push({
          day,
          instrument,
          side: signedQuantity > 0 ? "BUY" : "SELL",
          previous_position: previousPosition,
          new_position: desiredPosition,
          trade_quantity: Math.abs(signedQuantity),
          signed_quantity: signedQuantity,
          price: currentPrice,
          trade_value: rounded(turnover),
          commission: rounded(commission),
        });
      }
    }

    const grossPnl = rounded(
      instrumentPnl.reduce(
        (total, value, instrument) => total + value + instrumentCommission[instrument],
        0,
      ),
    );
    const netPnl = rounded(instrumentPnl.reduce((total, value) => total + value, 0));
    const turnover = rounded(instrumentTurnover.reduce((total, value) => total + value, 0));
    const commission = rounded(instrumentCommission.reduce((total, value) => total + value, 0));

    runningGrossPnl = rounded(runningGrossPnl + grossPnl);
    runningPnl = rounded(runningPnl + netPnl);
    peakPnl = Math.max(peakPnl, runningPnl);

    days.push(day);
    dailyPnl.push(netPnl);
    grossDailyPnl.push(grossPnl);
    cumulativePnl.push(runningPnl);
    drawdown.push(rounded(runningPnl - peakPnl));
    dailyTurnover.push(turnover);
    dailyCommission.push(commission);
    positions.push(dayPositions);
    trades.push(dayTrades);
    tradeLogs.push(...dayTradeLogs);
    instrumentPnlHistory.push(instrumentPnl);
    instrumentTurnoverHistory.push(instrumentTurnover);
    instrumentCommissionHistory.push(instrumentCommission);
    dailyRecords.push({
      day,
      gross_pnl: grossPnl,
      net_pnl: netPnl,
      cumulative_pnl: runningPnl,
      turnover,
      commission,
      num_traded_instruments: dayTradeLogs.length,
      num_clipped_instruments: 0,
    });
  }

  const meanDailyPnl =
    dailyPnl.reduce((total, value) => total + value, 0) / Math.max(dailyPnl.length, 1);
  const variance =
    dailyPnl.reduce((total, value) => total + (value - meanDailyPnl) ** 2, 0) /
    Math.max(dailyPnl.length, 1);
  const stdDailyPnl = Math.sqrt(variance);
  const instrumentSummary = buildInstrumentSummary(
    instrumentPnlHistory,
    instrumentTurnoverHistory,
    instrumentCommissionHistory,
    positions,
    trades,
  );
  const warnings: BacktestWarning[] = [
    {
      code: "MOCK_DATA",
      severity: "warning",
      message: "The dashboard is displaying generated mock data, not a backend run.",
      metric: "results_source",
      value: 1,
      threshold: 0,
    },
  ];

  return {
    metadata: {
      n_instruments: nInstruments,
      n_days: nDays,
      start_day: startDay,
      end_day: endDay,
      run_days: endDay - startDay + 1,
      commission_rate: commissionRate,
      position_limit_dollars: positionLimitDollars,
      strategy_function_name: "getMyPosition",
      deterministic: true,
      uses_simulated_price_data: false,
    },
    summary: {
      score: rounded(meanDailyPnl - 0.1 * stdDailyPnl),
      total_pnl: rounded(runningPnl),
      total_gross_pnl: rounded(runningGrossPnl),
      mean_daily_pnl: rounded(meanDailyPnl),
      std_daily_pnl: rounded(stdDailyPnl),
      max_drawdown: rounded(Math.min(...drawdown)),
      total_commission: rounded(dailyCommission.reduce((total, value) => total + value, 0)),
      total_turnover: rounded(dailyTurnover.reduce((total, value) => total + value, 0)),
      total_trades: tradeLogs.length,
      clipping_event_count: clippingEvents.length,
    },
    daily_records: dailyRecords,
    series: {
      days,
      daily_pnl: dailyPnl,
      gross_daily_pnl: grossDailyPnl,
      cumulative_pnl: cumulativePnl,
      drawdown,
      daily_turnover: dailyTurnover,
      daily_commission: dailyCommission,
    },
    positions,
    trades,
    trade_logs: tradeLogs,
    instrument_summary: instrumentSummary,
    warnings,
    clipping_events: clippingEvents,
  };
}

function buildInstrumentSummary(
  instrumentPnlHistory: number[][],
  instrumentTurnoverHistory: number[][],
  instrumentCommissionHistory: number[][],
  positions: number[][],
  trades: number[][],
): InstrumentSummary[] {
  return Array.from({ length: nInstruments }, (_, instrument) => {
    const pnl = instrumentPnlHistory.map((row) => row[instrument] ?? 0);
    const positionValues = positions.map((row) => row[instrument] ?? 0);
    const tradeValues = trades.map((row) => row[instrument] ?? 0);
    const turnover = instrumentTurnoverHistory.map((row) => row[instrument] ?? 0);
    const commission = instrumentCommissionHistory.map((row) => row[instrument] ?? 0);

    return {
      instrument,
      total_pnl: rounded(pnl.reduce((total, value) => total + value, 0)),
      total_trades: tradeValues.filter((value) => value !== 0).length,
      total_turnover: rounded(turnover.reduce((total, value) => total + value, 0)),
      total_commission: rounded(commission.reduce((total, value) => total + value, 0)),
      average_position: rounded(
        positionValues.reduce((total, value) => total + value, 0) /
          Math.max(positionValues.length, 1),
      ),
      max_abs_position: Math.max(...positionValues.map((value) => Math.abs(value))),
      best_day_pnl: Math.max(...pnl),
      worst_day_pnl: Math.min(...pnl),
    };
  });
}

export const mockResults = makeMockResults();
