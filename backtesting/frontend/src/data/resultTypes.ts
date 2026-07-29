export type BacktestMetadata = {
  test_id?: string;
  original_strategy_filename?: string;
  created_at?: string;
  n_instruments: number;
  n_days: number;
  start_day: number;
  end_day: number;
  run_days: number;
  commission_rate: number;
  position_limit_dollars: number;
  strategy_function_name: string;
  deterministic: boolean;
  uses_simulated_price_data: boolean;
};

export type BacktestSummary = {
  score: number;
  total_pnl: number;
  total_gross_pnl: number;
  mean_daily_pnl: number;
  std_daily_pnl: number;
  max_drawdown: number;
  total_commission: number;
  total_turnover: number;
  total_trades: number;
  clipping_event_count: number;
};

export type DailyRecord = {
  day: number;
  gross_pnl: number;
  net_pnl: number;
  cumulative_pnl: number;
  turnover: number;
  commission: number;
  num_traded_instruments: number;
  num_clipped_instruments: number;
};

export type BacktestSeries = {
  days: number[];
  daily_pnl: number[];
  gross_daily_pnl: number[];
  cumulative_pnl: number[];
  drawdown: number[];
  daily_turnover: number[];
  daily_commission: number[];
};

export type TradeLog = {
  day: number;
  instrument: number;
  side: "BUY" | "SELL";
  previous_position: number;
  new_position: number;
  trade_quantity: number;
  signed_quantity: number;
  price: number;
  trade_value: number;
  commission: number;
};

export type InstrumentSummary = {
  instrument: number;
  total_pnl: number;
  total_trades: number;
  total_turnover: number;
  total_commission: number;
  average_position: number;
  max_abs_position: number;
  best_day_pnl: number;
  worst_day_pnl: number;
};

export type BacktestWarning = {
  code: string;
  severity: string;
  message: string;
  metric: string;
  value: number;
  threshold: number;
};

export type ClippingEvent = {
  day: number;
  num_clipped_instruments: number;
  instruments: number[];
};

export type BacktestResults = {
  metadata: BacktestMetadata;
  summary: BacktestSummary;
  daily_records: DailyRecord[];
  series: BacktestSeries;
  positions: number[][];
  trades: number[][];
  trade_logs: TradeLog[];
  instrument_summary: InstrumentSummary[];
  warnings: BacktestWarning[];
  clipping_events: ClippingEvent[];
};
