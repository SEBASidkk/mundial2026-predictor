export interface Team {
  id: number;
  name: string;
  short_name: string | null;
  country_code: string | null;
  elo_rating: number;
}

export interface ScoreEntry {
  score: string;
  probability: number;
}

export interface Markets {
  result_1x2: { home: number; draw: number; away: number };
  over_05: number;
  over_15: number;
  over_25: number;
  over_35: number;
  over_45: number;
  under_25: number;
  btts: number;
  top_scores: ScoreEntry[];
  model_confidence: number;
}

export interface Prediction {
  prob_home_win: number;
  prob_draw: number;
  prob_away_win: number;
  lambda_home: number;
  lambda_away: number;
  markets: Markets;
  model_confidence: number;
  generated_at: string;
}

export interface Match {
  id: number;
  home_team: Team;
  away_team: Team;
  kickoff_utc: string;
  stage: string | null;
  group: string | null;
  venue_city: string | null;
  played: boolean;
  home_goals: number | null;
  away_goals: number | null;
  prediction?: Prediction | null;
}

export interface BetPick {
  match_id: number;
  home_team: string;
  away_team: string;
  home_code?: string | null;
  away_code?: string | null;
  kickoff_utc: string;
  market: string;
  selection: string;
  label: string;
  model_prob: number;
  decimal_odds: number;
  implied_prob: number;
  edge: number;
  source: 'market' | 'fair';
  bookmaker: string | null;
}

export interface BestBetsResponse {
  picks: BetPick[];
}

export interface SafeBet extends BetPick {
  model_confidence: number;
  safety_score: number;
  prob_ci_low: number;
  prob_ci_high: number;
  kelly_fraction: number;
  exp_goals_home: number;
  exp_goals_away: number;
  exp_goals_total: number;
  rationale: string;
}

export interface SafeBetsResponse {
  n: number;
  note: string;
  picks: SafeBet[];
}

export interface MatchBestBet {
  match_id: number;
  home_team: string;
  away_team: string;
  home_code: string | null;
  away_code: string | null;
  kickoff_utc: string;
  stage: string | null;
  group: string | null;
  picks: SafeBet[];
}

export interface MatchBestBetsResponse {
  n: number;
  note: string;
  matches: MatchBestBet[];
}

export interface OutrightPick {
  team: string;
  elo: number;
  prob: number;
  fair_odds: number;
}

export interface OutrightsResponse {
  n: number;
  markets: Record<string, OutrightPick[]>;
}

export interface MatchDetail extends Match {
  prediction: Prediction | null;
  bets: BetPick[];
}

export interface SimResult {
  n: number;
  available: boolean;
  home_team: string;
  away_team: string;
  lambda_home: number;
  lambda_away: number;
  result: { home: number; draw: number; away: number };
  avg_goals_home: number;
  avg_goals_away: number;
  over_25: number;
  btts: number;
  top_scores: ScoreEntry[];
  goal_distribution: { goals: string; probability: number }[];
}

export interface ModelMeta {
  last_updated: string | null;
  predictions_count: number;
  model_version: number;
  ensemble_weights: { dixon_coles: number; xgboost: number; elo: number };
  weights_source?: string;
  methodology: string;
}

export interface RefreshStatus {
  status?: string;            // "started" | "already_running" (POST only)
  running: boolean;
  last_run: string | null;
  last_error: string | null;
  started_at: string | null;
}

export interface ReliabilityBin {
  bin: string;
  avg_predicted: number;
  observed_freq: number;
  count: number;
}

export interface HoldoutMetrics {
  n: number;
  brier: number;
  baseline_brier: number;
  log_loss: number;
  accuracy: number;
}

export interface ModelMetrics {
  n: number;
  brier: number | null;
  log_loss: number | null;
  accuracy: number | null;
  baseline_brier: number | null;
  roi: number | null;
  value_bets: number;
  reliability: ReliabilityBin[];
  calibration: {
    goal_offset_home: number;
    goal_offset_away: number;
    calibrated_from: number;
  };
  holdout?: HoldoutMetrics | null;
}

export interface StandingsResponse {
  standings: Standing[];
}

export interface Standing {
  name: string;
  P: number;
  W: number;
  D: number;
  L: number;
  GF: number;
  GA: number;
  Pts: number;
}
