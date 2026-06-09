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

export interface MatchDetail extends Match {
  prediction: Prediction | null;
}

export interface ModelMeta {
  last_updated: string | null;
  predictions_count: number;
  model_version: number;
  ensemble_weights: { dixon_coles: number; xgboost: number; elo: number };
  methodology: string;
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
