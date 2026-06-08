# Mundial 2026 Predictor — Design Spec

**Date:** 2026-06-08  
**Status:** Approved

---

## 1. Overview

Predictive analytics platform for FIFA World Cup 2026 betting markets. Combines professional mathematical models (Dixon-Coles, Poisson, ELO, XGBoost ensemble) with a real-time FastAPI backend and Angular dashboard for a small group of users.

**Goals:**
- Maximize prediction accuracy across all betting markets (1X2, exact score, over/under, BTTS, first scorer, handicap)
- Provide transparent model confidence with full statistical backing
- Deliver a modern, data-dense dark dashboard accessible to non-technical users

---

## 2. Architecture

```
DATA LAYER
  football-data.org API (free tier)
  OpenLigaDB API
  ESPN unofficial API
  BeautifulSoup scraping (WhoScored, SofaScore player ratings)
  OpenWeatherMap API (conditions per venue)
  Kaggle FIFA/WC historical datasets (bootstrap)
       ↓
ML PIPELINE (Python)
  Data ingestion & normalization
  Feature engineering
  Model ensemble (Dixon-Coles + ELO + XGBoost + Poisson bivariate)
  Output: probabilities per market stored in SQLite/PostgreSQL
       ↓
FASTAPI BACKEND
  /api/matches        → upcoming matches + predictions
  /api/match/:id      → full multi-market prediction detail
  /api/teams/:id      → historical stats + current form
  /api/players/:id    → player momentum, ratings, injury status
  /api/standings      → group tables + bracket
  /api/model/meta     → model confidence, last update timestamp
       ↓
ANGULAR FRONTEND (static build)
  Served via nginx on VPS (18.217.119.162)
  Consumes FastAPI REST endpoints
```

**Deploy:** VPS ubuntu@18.217.119.162, FastAPI via PM2/uvicorn, Angular via nginx.

---

## 3. Mathematical Models

### 3.1 Dixon-Coles (primary goals model)
- Models λ_home and λ_away (Poisson goal rates per team)
- Low-score correction parameter ρ for 0-0, 1-0, 0-1, 1-1
- Time-decay weighting (recent matches weight more)
- Outputs: expected goals per team

### 3.2 ELO Rating System
- Dynamic rating updated after every match
- Competition weight multiplier (World Cup > Qualifiers > Friendlies)
- Temporal decay for inactivity
- Outputs: relative team strength differential

### 3.3 Bivariate Poisson
- Joint distribution of (goals_home, goals_away)
- Generates probability matrix for every scoreline 0-0 through 5-5+
- Drives: exact score market, over/under, BTTS, Asian handicap

### 3.4 XGBoost Classifier/Regressor
- Input features:
  - ELO differential
  - Form: points/goals last 5 and 10 matches
  - Rest days between matches
  - Travel distance and timezone delta
  - Venue altitude and weather (temp, humidity, rain probability)
  - Key player injury/suspension flags
  - WhoScored player form ratings (top 11)
  - Head-to-head record last 10 years
  - Tournament phase (group pressure vs knockout pressure)
  - Referee historical stats
- Output: 1X2 probabilities + expected goals adjustment

### 3.5 Ensemble (final output)
```
P_final = 0.40 × Dixon-Coles + 0.35 × XGBoost + 0.25 × ELO
```
Weights tuned via backtesting on 2010–2022 World Cup data.

### 3.6 Markets Covered
| Market | Model |
|--------|-------|
| 1X2 (Win/Draw/Loss) | Ensemble |
| Exact score | Bivariate Poisson matrix |
| Over/Under 0.5–4.5 | Poisson CDF |
| BTTS (Both Teams Score) | Poisson joint |
| Asian Handicap | Poisson + ELO |
| First scorer | Player form × team xG share |
| Anytime scorer | Same as above, cumulative |
| Half-time result | Dixon-Coles (45min λ) |

---

## 4. Data Pipeline

### Sources
| Source | Data | Update Frequency |
|--------|------|-----------------|
| football-data.org | Fixtures, results, standings | Daily |
| WhoScored (scrape) | Player ratings, form | Match day |
| SofaScore (scrape) | Injuries, lineups | Match day |
| OpenWeatherMap | Venue weather forecast | 6h before kickoff |
| Kaggle FIFA datasets | Historical 1930–2022 | One-time bootstrap |
| ESPN unofficial | Live scores (if needed) | Real-time |

### Feature Store
- SQLite for development, PostgreSQL for production
- Tables: `teams`, `players`, `matches`, `predictions`, `features_snapshot`
- Prediction snapshot saved per model run with timestamp and version

---

## 5. Backend (FastAPI)

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy ORM
- APScheduler for automated pipeline runs (daily + pre-match)
- Pydantic response schemas
- CORS configured for Angular frontend origin
- No auth for MVP (small trusted group; restrict by IP or simple API key header)

---

## 6. Frontend (Angular)

### Stack
- Angular 17+ (standalone components)
- Chart.js (via ng2-charts) for all visualizations
- TailwindCSS for styling
- Lucide icons (SVG, no emoji)
- Static build served by nginx

### Design System
- **Style:** Dark Mode OLED
- **Background:** `#050A14` | **Surface:** `#0D1829`
- **Primary:** `#1E40AF` | **Secondary:** `#3B82F6`
- **Accent/CTA:** `#D97706` (amber — high probability highlights)
- **Win:** `#22C55E` | **Loss:** `#EF4444`
- **Text:** `#F8FAFC`
- **Fonts:** Fira Code (numbers/stats) + Fira Sans (body)

### Routes & Views
| Route | Content |
|-------|---------|
| `/` | Dashboard: upcoming matches, top predictions, ELO leaderboard |
| `/partido/:id` | Full match prediction: all markets, radar chart, confidence % |
| `/equipos/:id` | Team profile: historical stats, form, squad momentum |
| `/torneo` | Bracket + group stage simulator |
| `/modelo` | Model transparency: methodology, confidence intervals, last update |

### Charts Per View
| View | Chart Type |
|------|-----------|
| Match probability | Radar Chart (attack/defense/form/H2H/conditions) |
| Expected goals trend | Line + Confidence Band (Dixon-Coles output) |
| Score probability matrix | Heatmap (Bivariate Poisson) |
| Team comparison | Grouped Horizontal Bar |
| Venue map | Choropleth (environmental conditions by host city) |
| ELO history | Area Chart with temporal axis |

---

## 7. Non-Functional Requirements

- API response time < 500ms (predictions pre-computed, not on-the-fly)
- Frontend initial load < 2s on 4G
- Model re-runs: daily at 02:00 UTC + triggered 6h before each match
- Responsive: 375px → 1440px
- Accessibility: WCAG AA minimum

---

## 8. Out of Scope (MVP)

- User authentication / personalization
- Push notifications
- Bankroll management / bet tracking
- Live in-play predictions
- Mobile native app
