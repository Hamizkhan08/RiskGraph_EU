export type DatasetKey = "LI" | "HI";
export type Decision = "suspicious" | "false_positive" | "requires_review";
export type Status = "open" | Decision;
export type Priority = "P1" | "P2" | "P3";
export type PolicyKind = "none" | "static" | "rolling" | "conformal";

export interface Agg {
  mean: number;
  sd: number;
  values: number[];
}
export interface Alert {
  id: string;
  dataset: DatasetKey;
  account: string;
  date: string;
  decision_timestamp: string;
  score: number;
  p_cal: number;
  priority: Priority;
  status: Status;
  key_reason: string;
  key_reason_code: string;
  network: {
    degree_7d: number;
    reach2_7d: number;
    hub_neighbour_share: number;
    cycles: { c2: number; c3: number; c4: number };
    fanin_burst_3d: number;
    fanout_burst_3d: number;
  };
  amounts: { out_1d: number; in_1d: number; out_7d: number; in_7d: number; n_tx_1d: number; note: string };
}
export interface Contribution {
  feature: string;
  value: number;
  contribution: number;
  group: string;
  definition: string;
  reason_code: string;
}
export interface Reason {
  code: string;
  label: string;
  contribution: number;
}
export interface EvTx {
  timestamp: string;
  src: string;
  dst: string;
  amount: number;
  currency: string;
  type: string;
  direction: "in" | "out";
}
export interface GNode {
  id: string;
  focal: boolean;
  n: number;
  amount: number;
}
export interface GEdge {
  source: string;
  target: string;
  n: number;
  amount: number;
  first: string;
  last: string;
}
export interface Evidence {
  focal: string;
  decision_timestamp: string;
  lookback_days: number;
  transactions: EvTx[];
  n_transactions_window: number;
  counterparties_total: number;
  nodes: GNode[];
  edges: GEdge[];
}
export interface DecisionRecord {
  decision: Decision;
  note: string;
  analyst: string;
  simulated: boolean;
  created_at: string;
}
export interface CaseDetail extends Alert {
  explanation: { base_value: number; margin: number; top_features: Contribution[]; reasons: Reason[] };
  evidence: Evidence;
  features: Record<string, number>;
  research: { ground_truth_positive: number; family: string | null; scheme_id: string | null; note: string };
  decision_history?: DecisionRecord[];
}
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
export interface DatasetInfo {
  key: DatasetKey;
  label: string;
}
export interface Primary {
  policy: { kind: PolicyKind; alpha: number };
  capacity_multiplier: number;
  avg_review_per_day: number;
  n_review_total: number;
  n_cases: number;
  n_positives: number;
  review_recall: number;
  auto_closed_cases: number;
  realised_miss_rate: number;
  expired_positive_rate: number;
  open_backlog_positive_rate: number;
  mean_backlog: number;
  max_backlog: number;
  mean_backlog_age: number;
  violation_rate: number | null;
  miss_ci95: [number, number] | null;
  n_clusters: number | null;
}
export interface Summary {
  dataset: DatasetKey;
  label: string;
  disclosure: string;
  run_id: string;
  generated_at: string;
  split: Record<string, { days: number[]; dates: string[] }>;
  counts: Record<string, number>;
  primary: Primary;
  series: {
    day: number[];
    date: string[];
    n_new: number[];
    review: number[];
    auto_close: number[];
    backlog: number[];
    backlog_age: number[];
    expired: number[];
  };
  queue_sample: { n: number; of_total_review: number; rule: string };
}
export interface DashboardData {
  summary: Summary;
  decisions: { by_decision: Record<string, number>; decided_in_sample: number; open_in_sample: number; sample_size: number; simulated: boolean };
  latest_alerts: Alert[];
}
export interface TopK {
  recall: Agg;
  precision: Agg;
  lift: Agg;
  n_pos: number;
  avg_k_per_day: number;
}
export interface ModelResult {
  label: string;
  n_features: number;
  test: Record<"strict" | "all", { n_cases: number; n_pos: number; pr_auc: Agg; topk: Record<string, TopK> }>;
}
export interface Contrast {
  a: string;
  b: string;
  m: number;
  primary: boolean;
  recall: number;
  recall_b: number;
  diff: number;
  diff_ci95: [number, number];
  n_clusters: number;
  n_pos: number;
}
export interface CalBin {
  mean_pred: number;
  obs_rate: number;
  n: number;
  n_pos: number;
}
export interface H2Family {
  family: string;
  n_pos_cases: number;
  n_schemes: number;
  n_train_cases_removed: number;
  by_m: Record<
    string,
    Record<string, { recall_seen: Agg; recall_heldout: Agg; rel_loss: Agg }> & {
      diff_loss_M4_minus_M3: { ci95: [number, number]; point: number };
    }
  >;
}
export interface SimCell {
  policy: PolicyKind;
  alpha: number;
  m: number;
  n_pos: number;
  realised_miss_rate: number;
  miss_ci95: [number, number] | null;
  review_recall: number;
  unreviewed_rate: number;
  expired_positive_rate: number;
  workload_removed: number;
  auto_closed_cases: number;
  mean_backlog: number;
  max_backlog: number;
  violation_rate: number | null;
  n_weekly_windows: number;
}
export interface HeldoutCell {
  heldout_family_name: string;
  policy: { kind: PolicyKind; alpha: number };
  realised_miss_rate: number;
  miss_ci95: [number, number] | null;
  workload_removed: number;
  violation_rate: number | null;
  heldout_family_stats: { n_pos: number; miss: number; review_recall: number } | null;
}
export interface Metrics {
  dataset: DatasetKey;
  label: string;
  run_id: string;
  h1: {
    models: Record<string, ModelResult>;
    contrasts: Contrast[];
    calibration: Record<string, { brier: number; ece: number; bins: CalBin[]; n_val_pos: number; prevalence_test: number; brier_baseline_prevalence: number }>;
    pr_curve_main: { recall: number; precision: number }[];
    counts: Record<string, number>;
  };
  h2: { families: Record<string, H2Family>; window_start_day: number };
  h3: {
    stream: { n_cases: number; n_pos: number };
    same_regime: SimCell[];
    baseline_no_autoclose: Record<string, { review_recall: number; expired_positive_rate: number; mean_backlog: number; max_backlog: number }>;
    heldout: HeldoutCell[];
    review_only_labels: { policy: { kind: PolicyKind }; realised_miss_rate: number; miss_ci95: [number, number] | null; workload_removed: number }[];
  };
  feature_importance_gain: { feature: string; gain: number; group: string; definition: string }[];
  families: string[];
}
export interface Monitoring {
  mode: string;
  weekly: {
    week_start: string;
    block: string;
    n_cases: number;
    n_pos: number;
    n_review_at_m1: number;
    recall_at_m1: number | null;
    mean_p_cal: number;
    p50: number;
    p90: number;
    p99: number;
    pr_auc: number | null;
  }[];
  feature_drift: { window_start: string; psi: Record<string, number> }[];
  calibration_windows: { window_start: string; n_pos: number; brier: number; ece: number; mean_pred: number; obs_rate: number }[];
  top_features: string[];
  psi_note: string;
  score_definition: string;
}
export interface DataQuality {
  rows: number;
  in_period_rows: number;
  positive_transactions: number;
  positive_prevalence_tx: number;
  post_period_rows: number;
  post_period_positive_rows: number;
  duplicate_rows: number;
  self_loops: number;
  n_accounts: number;
  schemes_total: number;
  schemes_by_family: Record<string, number>;
  positive_by_tx_type: Record<string, number>;
  scheme_duration_days: Record<string, number>;
  warnings: string[];
  [k: string]: unknown;
}
export interface SimResult extends SimCell {
  note?: string;
}
export interface Health {
  status: "ok" | "degraded";
  version: string;
  demo_mode: boolean;
  datasets: string[];
  model_loaded: boolean;
}
export interface AlertQuery {
  dataset: DatasetKey;
  q: string;
  priority: "" | Priority;
  status: "" | Status;
  sort: "date" | "score" | "priority" | "amount";
  order: "asc" | "desc";
  page: number;
  pageSize: number;
}
