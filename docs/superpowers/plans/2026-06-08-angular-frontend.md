# Angular Frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Angular 17+ standalone frontend that consumes the FastAPI backend and displays World Cup 2026 match predictions across 4 views: Dashboard, Partido detail, Torneo standings, and Modelo transparency.

**Architecture:** Angular standalone components with lazy-loaded routes. TailwindCSS + CSS custom properties for OLED dark theme. Chart.js for radar chart. HttpClient proxied to FastAPI on `/api`. Static build served by nginx on VPS.

**Tech Stack:** Angular 17+, TailwindCSS v3, Chart.js v4, Lucide Angular, Fira Code + Fira Sans (Google Fonts), Jasmine/Karma tests

---

## File Map

```
frontend/
├── package.json
├── angular.json
├── tailwind.config.js
├── tsconfig.json
├── proxy.conf.json                          # Dev: /api → localhost:8000
├── nginx.conf                               # Prod deploy config
├── src/
│   ├── index.html
│   ├── main.ts
│   ├── styles.css                           # Tailwind + global CSS vars + utility classes
│   ├── environments/
│   │   ├── environment.ts                   # apiUrl: '' (proxy)
│   │   └── environment.prod.ts             # apiUrl: 'http://18.217.119.162:8000'
│   └── app/
│       ├── app.config.ts                    # provideRouter + provideHttpClient
│       ├── app.routes.ts                    # Lazy-loaded routes
│       ├── app.component.ts                 # Root layout: navbar + sidebar + router-outlet
│       ├── core/
│       │   ├── models/
│       │   │   └── match.model.ts           # All TS interfaces: Team, Match, Prediction, Markets, etc.
│       │   └── services/
│       │       ├── api.service.ts           # HttpClient wrapper for all 4 endpoints
│       │       └── api.service.spec.ts
│       ├── shared/
│       │   └── components/
│       │       ├── navbar/
│       │       │   ├── navbar.component.ts  # Top nav with active links + live badge
│       │       │   └── navbar.component.spec.ts
│       │       ├── sidebar/
│       │       │   ├── sidebar.component.ts # Left nav sidebar
│       │       │   └── sidebar.component.spec.ts
│       │       └── match-card/
│       │           ├── match-card.component.ts   # Clickable match preview card
│       │           ├── match-card.component.html
│       │           └── match-card.component.spec.ts
│       └── features/
│           ├── dashboard/
│           │   ├── dashboard.component.ts   # Stat cards + match list + ELO table
│           │   ├── dashboard.component.html
│           │   └── dashboard.component.spec.ts
│           ├── partido/
│           │   ├── partido.component.ts     # Full prediction: markets + score table + radar chart
│           │   ├── partido.component.html
│           │   └── partido.component.spec.ts
│           ├── torneo/
│           │   ├── torneo.component.ts      # Group standings from /api/standings
│           │   ├── torneo.component.html
│           │   └── torneo.component.spec.ts
│           └── modelo/
│               ├── modelo.component.ts      # Ensemble methodology + model meta
│               ├── modelo.component.html
│               └── modelo.component.spec.ts
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `frontend/` (ng new)
- Create: `frontend/tailwind.config.js`
- Create: `frontend/proxy.conf.json`
- Modify: `frontend/angular.json` (add proxyConfig)

- [ ] **Step 1: Scaffold Angular project**

```bash
cd /home/sebas/mundial2026-predictor
ng new frontend --standalone --routing --style=css --skip-git --package-manager=npm
cd frontend
```

Expected: project created with `src/app/app.component.ts`, `src/app/app.routes.ts`, `src/app/app.config.ts`.

- [ ] **Step 2: Install dependencies**

```bash
npm install chart.js lucide-angular
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Expected: `tailwind.config.js` created, `node_modules/chart.js` and `node_modules/lucide-angular` present.

- [ ] **Step 3: Configure Tailwind**

Replace `tailwind.config.js`:

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        'app-bg':      '#050A14',
        'app-surface': '#0D1829',
        'app-border':  '#1E3A5F',
        'app-primary': '#1E40AF',
        'app-blue':    '#3B82F6',
        'app-accent':  '#D97706',
        'app-amber':   '#F59E0B',
        'app-win':     '#22C55E',
        'app-draw':    '#94A3B8',
        'app-loss':    '#EF4444',
        'app-text':    '#F8FAFC',
        'app-muted':   '#94A3B8',
      },
      fontFamily: {
        mono: ['"Fira Code"', 'monospace'],
        sans: ['"Fira Sans"', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 4: Create proxy config**

Create `frontend/proxy.conf.json`:

```json
{
  "/api": {
    "target": "http://localhost:8000",
    "secure": false,
    "changeOrigin": true
  }
}
```

- [ ] **Step 5: Add proxy to angular.json**

In `angular.json`, under `projects.frontend.architect.serve.options`, add:

```json
"proxyConfig": "proxy.conf.json"
```

- [ ] **Step 6: Create environment files**

Create `src/environments/environment.ts`:

```typescript
export const environment = {
  production: false,
  apiUrl: '',
};
```

Create `src/environments/environment.prod.ts`:

```typescript
export const environment = {
  production: true,
  apiUrl: 'http://18.217.119.162:8000',
};
```

- [ ] **Step 7: Verify scaffold runs**

```bash
ng serve --port 4200
```

Expected: browser opens `http://localhost:4200`, default Angular page loads (no errors in console).

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Angular 17 frontend with Tailwind and Chart.js"
```

---

## Task 2: Global Styles

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/index.html`

- [ ] **Step 1: Replace styles.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');

:root {
  --bg:      #050A14;
  --surface: #0D1829;
  --border:  #1E3A5F;
  --primary: #1E40AF;
  --blue:    #3B82F6;
  --accent:  #D97706;
  --amber:   #F59E0B;
  --win:     #22C55E;
  --draw:    #94A3B8;
  --loss:    #EF4444;
  --text:    #F8FAFC;
  --muted:   #94A3B8;
}

* { box-sizing: border-box; }

body {
  background-color: var(--bg);
  color: var(--text);
  font-family: 'Fira Sans', sans-serif;
  margin: 0;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* Utility classes */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
}

.card-label {
  font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--muted); margin-bottom: 8px;
  display: block;
}

.section-title {
  font-size: 13px; font-weight: 600; color: var(--text);
  margin-bottom: 12px; display: flex; align-items: center; gap: 8px;
}
.section-title::after {
  content: ''; flex: 1; height: 1px; background: var(--border);
}

.badge {
  display: inline-flex; align-items: center; padding: 2px 8px;
  border-radius: 12px; font-size: 11px; font-weight: 600;
}
.badge-win { background: rgba(34,197,94,0.15); color: var(--win); border: 1px solid rgba(34,197,94,0.3); }
.badge-amber { background: rgba(217,119,6,0.15); color: var(--amber); border: 1px solid rgba(217,119,6,0.3); }

.prob-pill {
  font-family: 'Fira Code', monospace; font-size: 11px; font-weight: 600;
  padding: 2px 7px; border-radius: 4px;
}
.prob-home { background: rgba(59,130,246,0.2); color: var(--blue); }
.prob-draw { background: rgba(148,163,184,0.15); color: var(--draw); }
.prob-away { background: rgba(239,68,68,0.15); color: var(--loss); }

.chip {
  font-family: 'Fira Code', monospace; font-size: 10px; padding: 2px 8px;
  border-radius: 4px; background: rgba(255,255,255,0.05);
  border: 1px solid var(--border); color: var(--muted);
}
.chip-accent {
  background: rgba(217,119,6,0.15); border-color: rgba(217,119,6,0.4);
  color: var(--amber);
}

.market-item {
  background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px;
}
```

- [ ] **Step 2: Update index.html title**

In `src/index.html` change `<title>` to:

```html
<title>Mundial 2026 Predictor</title>
```

- [ ] **Step 3: Verify Tailwind compiles**

```bash
ng build --configuration=development 2>&1 | grep -i error | head -10
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/styles.css src/index.html tailwind.config.js
git commit -m "feat: OLED dark theme with CSS tokens and utility classes"
```

---

## Task 3: TypeScript Models

**Files:**
- Create: `frontend/src/app/core/models/match.model.ts`

- [ ] **Step 1: Create models directory and file**

```bash
mkdir -p src/app/core/models src/app/core/services
```

Create `src/app/core/models/match.model.ts`:

```typescript
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
```

- [ ] **Step 2: Verify compiles**

```bash
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add src/app/core/models/match.model.ts
git commit -m "feat: TypeScript interfaces for API models"
```

---

## Task 4: API Service + Tests

**Files:**
- Create: `frontend/src/app/core/services/api.service.ts`
- Create: `frontend/src/app/core/services/api.service.spec.ts`

- [ ] **Step 1: Write failing tests first**

Create `src/app/core/services/api.service.spec.ts`:

```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ApiService } from './api.service';

describe('ApiService', () => {
  let service: ApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ApiService],
    });
    service = TestBed.inject(ApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('getMatches() GETs /api/matches', () => {
    service.getMatches().subscribe(matches => expect(matches.length).toBe(2));
    const req = httpMock.expectOne('/api/matches');
    expect(req.request.method).toBe('GET');
    req.flush([{ id: 1 }, { id: 2 }]);
  });

  it('getMatch() GETs /api/match/:id', () => {
    service.getMatch(42).subscribe(m => expect((m as any).id).toBe(42));
    const req = httpMock.expectOne('/api/match/42');
    expect(req.request.method).toBe('GET');
    req.flush({ id: 42 });
  });

  it('getStandings() GETs /api/standings', () => {
    service.getStandings().subscribe(r => expect(r.standings).toBeDefined());
    const req = httpMock.expectOne('/api/standings');
    expect(req.request.method).toBe('GET');
    req.flush({ standings: [] });
  });

  it('getModelMeta() GETs /api/model/meta', () => {
    service.getModelMeta().subscribe(m => expect((m as any).model_version).toBe(1));
    const req = httpMock.expectOne('/api/model/meta');
    expect(req.request.method).toBe('GET');
    req.flush({ model_version: 1 });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
ng test --include='**/api.service.spec.ts' --watch=false
```

Expected: FAIL — `ApiService` not found.

- [ ] **Step 3: Implement ApiService**

Create `src/app/core/services/api.service.ts`:

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Match, MatchDetail, ModelMeta, StandingsResponse } from '../models/match.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getMatches(): Observable<Match[]> {
    return this.http.get<Match[]>(`${this.base}/api/matches`);
  }

  getMatch(id: number): Observable<MatchDetail> {
    return this.http.get<MatchDetail>(`${this.base}/api/match/${id}`);
  }

  getStandings(): Observable<StandingsResponse> {
    return this.http.get<StandingsResponse>(`${this.base}/api/standings`);
  }

  getModelMeta(): Observable<ModelMeta> {
    return this.http.get<ModelMeta>(`${this.base}/api/model/meta`);
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
ng test --include='**/api.service.spec.ts' --watch=false
```

Expected: PASS — 4 tests green.

- [ ] **Step 5: Commit**

```bash
git add src/app/core/services/
git commit -m "feat: ApiService with HttpClient wrapper for all 4 endpoints"
```

---

## Task 5: App Shell (Routing + Layout)

**Files:**
- Modify: `frontend/src/app/app.config.ts`
- Modify: `frontend/src/app/app.routes.ts`
- Modify: `frontend/src/app/app.component.ts`
- Create: `frontend/src/main.ts` (verify bootstrap)

- [ ] **Step 1: Configure app.config.ts**

Replace `src/app/app.config.ts`:

```typescript
import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(),
  ],
};
```

- [ ] **Step 2: Define lazy routes**

Replace `src/app/app.routes.ts`:

```typescript
import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
  },
  {
    path: 'partido/:id',
    loadComponent: () =>
      import('./features/partido/partido.component').then(m => m.PartidoComponent),
  },
  {
    path: 'torneo',
    loadComponent: () =>
      import('./features/torneo/torneo.component').then(m => m.TorneoComponent),
  },
  {
    path: 'modelo',
    loadComponent: () =>
      import('./features/modelo/modelo.component').then(m => m.ModeloComponent),
  },
  { path: '**', redirectTo: '' },
];
```

- [ ] **Step 3: Scaffold empty feature stubs so router doesn't error**

```bash
mkdir -p src/app/features/dashboard src/app/features/partido src/app/features/torneo src/app/features/modelo
```

Create `src/app/features/dashboard/dashboard.component.ts`:

```typescript
import { Component } from '@angular/core';
@Component({ selector: 'app-dashboard', standalone: true, template: '<p>Dashboard</p>' })
export class DashboardComponent {}
```

Create `src/app/features/partido/partido.component.ts`:

```typescript
import { Component } from '@angular/core';
@Component({ selector: 'app-partido', standalone: true, template: '<p>Partido</p>' })
export class PartidoComponent {}
```

Create `src/app/features/torneo/torneo.component.ts`:

```typescript
import { Component } from '@angular/core';
@Component({ selector: 'app-torneo', standalone: true, template: '<p>Torneo</p>' })
export class TorneoComponent {}
```

Create `src/app/features/modelo/modelo.component.ts`:

```typescript
import { Component } from '@angular/core';
@Component({ selector: 'app-modelo', standalone: true, template: '<p>Modelo</p>' })
export class ModeloComponent {}
```

- [ ] **Step 4: Write app.component.ts**

Replace `src/app/app.component.ts`:

```typescript
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavbarComponent } from './shared/components/navbar/navbar.component';
import { SidebarComponent } from './shared/components/sidebar/sidebar.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, NavbarComponent, SidebarComponent],
  template: `
    <div class="flex flex-col" style="min-height:100dvh; background:#050A14">
      <app-navbar />
      <div class="flex flex-1 overflow-hidden">
        <app-sidebar />
        <main class="flex-1 p-6 overflow-y-auto">
          <router-outlet />
        </main>
      </div>
    </div>
  `,
})
export class AppComponent {}
```

Note: NavbarComponent and SidebarComponent will be created in Task 6. The app won't compile until Task 6 is done.

- [ ] **Step 5: Commit**

```bash
git add src/app/app.config.ts src/app/app.routes.ts src/app/app.component.ts src/app/features/
git commit -m "feat: lazy routing and app shell layout"
```

---

## Task 6: Navbar + Sidebar

**Files:**
- Create: `frontend/src/app/shared/components/navbar/navbar.component.ts`
- Create: `frontend/src/app/shared/components/navbar/navbar.component.spec.ts`
- Create: `frontend/src/app/shared/components/sidebar/sidebar.component.ts`
- Create: `frontend/src/app/shared/components/sidebar/sidebar.component.spec.ts`

- [ ] **Step 1: Write navbar test**

```bash
mkdir -p src/app/shared/components/navbar src/app/shared/components/sidebar
```

Create `src/app/shared/components/navbar/navbar.component.spec.ts`:

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NavbarComponent } from './navbar.component';
import { RouterTestingModule } from '@angular/router/testing';

describe('NavbarComponent', () => {
  let fixture: ComponentFixture<NavbarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NavbarComponent, RouterTestingModule],
    }).compileComponents();
    fixture = TestBed.createComponent(NavbarComponent);
    fixture.detectChanges();
  });

  it('renders brand name', () => {
    expect(fixture.nativeElement.textContent).toContain('MUNDIAL');
  });

  it('renders Dashboard nav link', () => {
    const links = fixture.nativeElement.querySelectorAll('a');
    const texts = Array.from(links).map((l: any) => l.textContent.trim());
    expect(texts).toContain('Dashboard');
  });
});
```

- [ ] **Step 2: Run navbar test to verify it fails**

```bash
ng test --include='**/navbar.component.spec.ts' --watch=false
```

Expected: FAIL — `NavbarComponent` not found.

- [ ] **Step 3: Implement NavbarComponent**

Create `src/app/shared/components/navbar/navbar.component.ts`:

```typescript
import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <nav class="flex items-center justify-between px-6 h-14 border-b"
         style="background:#0D1829; border-color:#1E3A5F; position:sticky; top:0; z-index:100;">
      <span class="font-mono font-bold text-base tracking-wide" style="color:#3B82F6">
        MUNDIAL<span style="color:#D97706">2026</span>
      </span>
      <div class="flex gap-1">
        <a routerLink="/" routerLinkActive="nav-active" [routerLinkActiveOptions]="{exact:true}"
           class="nav-link">Dashboard</a>
        <a routerLink="/torneo" routerLinkActive="nav-active" class="nav-link">Torneo</a>
        <a routerLink="/modelo" routerLinkActive="nav-active" class="nav-link">Modelo</a>
      </div>
      <div class="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono"
           style="background:rgba(34,197,94,0.1); border:1px solid rgba(34,197,94,0.25); color:#22C55E;">
        <span class="w-1.5 h-1.5 rounded-full animate-pulse" style="background:#22C55E;"></span>
        72 predicciones activas
      </div>
    </nav>
  `,
  styles: [`
    .nav-link {
      padding: 6px 14px; border-radius: 6px; font-size: 13px;
      font-weight: 500; color: #94A3B8; text-decoration: none; transition: all 150ms;
    }
    .nav-link:hover { color: #F8FAFC; background: rgba(255,255,255,0.05); }
    :host ::ng-deep .nav-active { color: #3B82F6 !important; background: rgba(59,130,246,0.12) !important; }
  `],
})
export class NavbarComponent {}
```

- [ ] **Step 4: Run navbar tests to verify they pass**

```bash
ng test --include='**/navbar.component.spec.ts' --watch=false
```

Expected: PASS — 2 tests green.

- [ ] **Step 5: Write sidebar test**

Create `src/app/shared/components/sidebar/sidebar.component.spec.ts`:

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SidebarComponent } from './sidebar.component';
import { RouterTestingModule } from '@angular/router/testing';

describe('SidebarComponent', () => {
  let fixture: ComponentFixture<SidebarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SidebarComponent, RouterTestingModule],
    }).compileComponents();
    fixture = TestBed.createComponent(SidebarComponent);
    fixture.detectChanges();
  });

  it('renders sidebar navigation links', () => {
    const links = fixture.nativeElement.querySelectorAll('a');
    expect(links.length).toBeGreaterThanOrEqual(2);
  });
});
```

- [ ] **Step 6: Implement SidebarComponent**

Create `src/app/shared/components/sidebar/sidebar.component.ts`:

```typescript
import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <aside class="w-52 flex-shrink-0 border-r p-3 flex flex-col gap-1"
           style="background:#0D1829; border-color:#1E3A5F; min-height:calc(100dvh - 56px);">
      <p class="sbl">Navegación</p>
      <a routerLink="/" routerLinkActive="sa" [routerLinkActiveOptions]="{exact:true}" class="si">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0
               01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
        </svg>
        Dashboard
      </a>
      <a routerLink="/torneo" routerLinkActive="sa" class="si">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0
               002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0
               002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
        Torneo
      </a>
      <p class="sbl mt-3">Sistema</p>
      <a routerLink="/modelo" routerLinkActive="sa" class="si">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3
               m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374
               3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
        </svg>
        Modelo
      </a>
    </aside>
  `,
  styles: [`
    .sbl { font-size:10px; font-weight:600; letter-spacing:0.1em; color:#94A3B8; padding:6px 8px; text-transform:uppercase; }
    .si { display:flex; align-items:center; gap:10px; padding:8px 12px; border-radius:8px; font-size:13px; font-weight:500; color:#94A3B8; text-decoration:none; transition:all 150ms; }
    .si:hover { color:#F8FAFC; background:rgba(255,255,255,0.05); }
    :host ::ng-deep .sa { color:#3B82F6 !important; background:rgba(59,130,246,0.12) !important; }
  `],
})
export class SidebarComponent {}
```

- [ ] **Step 7: Run sidebar tests**

```bash
ng test --include='**/sidebar.component.spec.ts' --watch=false
```

Expected: PASS — 1 test green.

- [ ] **Step 8: Verify app compiles and loads**

```bash
ng serve --port 4200
```

Open `http://localhost:4200`. Expected: navbar + sidebar visible, "Dashboard" text in main area.

- [ ] **Step 9: Commit**

```bash
git add src/app/shared/
git commit -m "feat: navbar and sidebar with active route highlighting"
```

---

## Task 7: MatchCard Shared Component

**Files:**
- Create: `frontend/src/app/shared/components/match-card/match-card.component.ts`
- Create: `frontend/src/app/shared/components/match-card/match-card.component.html`
- Create: `frontend/src/app/shared/components/match-card/match-card.component.spec.ts`

- [ ] **Step 1: Write failing tests**

Create `src/app/shared/components/match-card/match-card.component.spec.ts`:

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatchCardComponent } from './match-card.component';
import { RouterTestingModule } from '@angular/router/testing';
import { Match } from '../../../core/models/match.model';

const mockMatch: Match = {
  id: 1,
  home_team: { id: 1, name: 'México', short_name: 'MEX', country_code: 'MX', elo_rating: 1987 },
  away_team: { id: 2, name: 'Sudáfrica', short_name: 'RSA', country_code: 'ZA', elo_rating: 1612 },
  kickoff_utc: '2026-06-11T19:00:00',
  stage: 'GROUP_STAGE', group: 'A', venue_city: 'New York',
  played: false, home_goals: null, away_goals: null,
  prediction: {
    prob_home_win: 0.42, prob_draw: 0.29, prob_away_win: 0.29,
    lambda_home: 1.42, lambda_away: 1.12,
    markets: {
      result_1x2: { home: 0.42, draw: 0.29, away: 0.29 },
      over_05: 0.94, over_15: 0.72, over_25: 0.42,
      over_35: 0.18, over_45: 0.07, under_25: 0.58,
      btts: 0.47, top_scores: [{ score: '1-1', probability: 0.142 }],
      model_confidence: 0.81,
    },
    model_confidence: 0.81, generated_at: '2026-06-08T00:00:00',
  },
};

describe('MatchCardComponent', () => {
  let fixture: ComponentFixture<MatchCardComponent>;
  let component: MatchCardComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MatchCardComponent, RouterTestingModule],
    }).compileComponents();
    fixture = TestBed.createComponent(MatchCardComponent);
    component = fixture.componentInstance;
    component.match = mockMatch;
    fixture.detectChanges();
  });

  it('renders both team names', () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('México');
    expect(text).toContain('Sudáfrica');
  });

  it('homeProb returns prob_home_win', () => {
    expect(component.homeProb).toBe(0.42);
  });

  it('drawProb returns prob_draw', () => {
    expect(component.drawProb).toBe(0.29);
  });

  it('over25 returns markets.over_25', () => {
    expect(component.over25).toBe(0.42);
  });

  it('topScore formats first score entry as "X-Y (N%)"', () => {
    expect(component.topScore).toBe('1-1 (14%)');
  });

  it('topScore returns "-" when no prediction', () => {
    component.match = { ...mockMatch, prediction: undefined };
    expect(component.topScore).toBe('-');
  });

  it('renders link to /partido/1', () => {
    const link = fixture.nativeElement.querySelector('a');
    expect(link.getAttribute('href')).toContain('/partido/1');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
ng test --include='**/match-card.component.spec.ts' --watch=false
```

Expected: FAIL — `MatchCardComponent` not found.

- [ ] **Step 3: Implement MatchCardComponent**

```bash
mkdir -p src/app/shared/components/match-card
```

Create `src/app/shared/components/match-card/match-card.component.ts`:

```typescript
import { Component, Input } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Match } from '../../../core/models/match.model';

@Component({
  selector: 'app-match-card',
  standalone: true,
  imports: [CommonModule, RouterLink, DatePipe],
  templateUrl: './match-card.component.html',
})
export class MatchCardComponent {
  @Input({ required: true }) match!: Match;

  get homeProb(): number { return this.match.prediction?.prob_home_win ?? 0; }
  get drawProb(): number { return this.match.prediction?.prob_draw ?? 0; }
  get awayProb(): number { return this.match.prediction?.prob_away_win ?? 0; }
  get over25(): number { return this.match.prediction?.markets?.over_25 ?? 0; }
  get btts(): number { return this.match.prediction?.markets?.btts ?? 0; }
  get confidence(): number { return this.match.prediction?.model_confidence ?? 0; }

  get topScore(): string {
    const s = this.match.prediction?.markets?.top_scores?.[0];
    if (!s) return '-';
    return `${s.score} (${(s.probability * 100).toFixed(0)}%)`;
  }

  get stageLabel(): string {
    return (this.match.stage ?? '').replace(/_/g, ' ');
  }
}
```

Create `src/app/shared/components/match-card/match-card.component.html`:

```html
<a [routerLink]="['/partido', match.id]"
   class="block rounded-xl border p-4 cursor-pointer transition-colors duration-150"
   style="background:#0D1829; border-color:#1E3A5F; text-decoration:none; color:inherit;"
   [style.border-color]="'#1E3A5F'"
   (mouseenter)="el.style.borderColor='#3B82F6'"
   (mouseleave)="el.style.borderColor='#1E3A5F'"
   #el>

  <!-- Header -->
  <div class="flex justify-between items-center mb-3">
    <span class="text-xs font-semibold tracking-wider uppercase" style="color:#D97706;">
      {{ stageLabel }}{{ match.group ? ' · Grupo ' + match.group : '' }}
    </span>
    <span class="font-mono text-xs" style="color:#94A3B8;">
      {{ match.kickoff_utc | date:'dd MMM · HH:mm' }} UTC
    </span>
  </div>

  <!-- Teams + probabilities -->
  <div class="flex items-center justify-between gap-3">
    <span class="font-semibold text-sm flex-1">{{ match.home_team.name }}</span>
    <div class="text-center min-w-[96px]">
      <div class="flex gap-1 justify-center mb-1">
        <span class="prob-pill prob-home">{{ (homeProb * 100).toFixed(0) }}%</span>
        <span class="prob-pill prob-draw">{{ (drawProb * 100).toFixed(0) }}%</span>
        <span class="prob-pill prob-away">{{ (awayProb * 100).toFixed(0) }}%</span>
      </div>
      <span class="text-xs font-mono" style="color:#94A3B8;">LOC · EMP · VIS</span>
    </div>
    <span class="font-semibold text-sm flex-1 text-right">{{ match.away_team.name }}</span>
  </div>

  <!-- Probability bar -->
  <div class="flex h-1 rounded overflow-hidden mt-3 gap-px">
    <div class="rounded-l" style="background:#3B82F6" [style.width.%]="homeProb * 100"></div>
    <div style="background:#94A3B8" [style.width.%]="drawProb * 100"></div>
    <div class="rounded-r flex-1" style="background:#EF4444"></div>
  </div>

  <!-- Market chips -->
  @if (match.prediction) {
    <div class="flex flex-wrap gap-2 mt-3">
      <span class="chip chip-accent">Over 2.5: {{ (over25 * 100).toFixed(0) }}%</span>
      <span class="chip chip-accent">BTTS: {{ (btts * 100).toFixed(0) }}%</span>
      <span class="chip">{{ topScore }}</span>
      <span class="chip">Conf: {{ (confidence * 100).toFixed(0) }}%</span>
    </div>
  }
</a>
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
ng test --include='**/match-card.component.spec.ts' --watch=false
```

Expected: PASS — 7 tests green.

- [ ] **Step 5: Commit**

```bash
git add src/app/shared/components/match-card/
git commit -m "feat: MatchCard shared component with probabilities and market chips"
```

---

## Task 8: Dashboard View

**Files:**
- Modify: `frontend/src/app/features/dashboard/dashboard.component.ts` (replace stub)
- Create: `frontend/src/app/features/dashboard/dashboard.component.html`
- Create: `frontend/src/app/features/dashboard/dashboard.component.spec.ts`

- [ ] **Step 1: Write failing tests**

Create `src/app/features/dashboard/dashboard.component.spec.ts`:

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DashboardComponent } from './dashboard.component';
import { RouterTestingModule } from '@angular/router/testing';
import { ApiService } from '../../core/services/api.service';
import { of, throwError } from 'rxjs';
import { Match, ModelMeta } from '../../core/models/match.model';

const mockMatch: Match = {
  id: 1,
  home_team: { id: 1, name: 'México', short_name: null, country_code: 'MX', elo_rating: 1987 },
  away_team: { id: 2, name: 'Sudáfrica', short_name: null, country_code: 'ZA', elo_rating: 1612 },
  kickoff_utc: '2026-06-11T19:00:00', stage: 'GROUP_STAGE', group: 'A',
  venue_city: 'New York', played: false, home_goals: null, away_goals: null, prediction: null,
};

const mockMeta: ModelMeta = {
  last_updated: '2026-06-08T20:00:00', predictions_count: 72, model_version: 1,
  ensemble_weights: { dixon_coles: 0.4, xgboost: 0.35, elo: 0.25 },
  methodology: 'Dixon-Coles + ELO + XGBoost',
};

describe('DashboardComponent', () => {
  let fixture: ComponentFixture<DashboardComponent>;
  let component: DashboardComponent;
  let apiSpy: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    apiSpy = jasmine.createSpyObj('ApiService', ['getMatches', 'getModelMeta']);
    apiSpy.getMatches.and.returnValue(of([mockMatch]));
    apiSpy.getModelMeta.and.returnValue(of(mockMeta));

    await TestBed.configureTestingModule({
      imports: [DashboardComponent, RouterTestingModule],
      providers: [{ provide: ApiService, useValue: apiSpy }],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('displays team names from loaded matches', () => {
    expect(fixture.nativeElement.textContent).toContain('México');
  });

  it('topTeams returns teams sorted descending by ELO', () => {
    expect(component.topTeams[0].elo).toBe(1987);
    expect(component.topTeams[0].name).toBe('México');
  });

  it('shows model version from meta', () => {
    expect(fixture.nativeElement.textContent).toContain('v1');
  });

  it('shows error message when API fails', async () => {
    apiSpy.getMatches.and.returnValue(throwError(() => new Error('Network error')));
    fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('No se pudo cargar');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
ng test --include='**/dashboard.component.spec.ts' --watch=false
```

Expected: FAIL — stub component doesn't have required properties.

- [ ] **Step 3: Implement DashboardComponent**

Replace `src/app/features/dashboard/dashboard.component.ts`:

```typescript
import { Component, OnInit } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { MatchCardComponent } from '../../shared/components/match-card/match-card.component';
import { Match, ModelMeta } from '../../core/models/match.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, DatePipe, MatchCardComponent],
  templateUrl: './dashboard.component.html',
})
export class DashboardComponent implements OnInit {
  matches: Match[] = [];
  meta: ModelMeta | null = null;
  loading = true;
  error: string | null = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getMatches().subscribe({
      next: (m) => {
        this.matches = m.filter(x => !x.played).slice(0, 6);
        this.loading = false;
      },
      error: () => {
        this.error = 'No se pudo cargar los partidos.';
        this.loading = false;
      },
    });
    this.api.getModelMeta().subscribe({
      next: (m) => (this.meta = m),
    });
  }

  get topTeams(): { name: string; elo: number }[] {
    const map = new Map<number, { name: string; elo: number }>();
    this.matches.forEach(m => {
      map.set(m.home_team.id, { name: m.home_team.name, elo: m.home_team.elo_rating });
      map.set(m.away_team.id, { name: m.away_team.name, elo: m.away_team.elo_rating });
    });
    return [...map.values()].sort((a, b) => b.elo - a.elo).slice(0, 8);
  }

  get maxElo(): number { return this.topTeams[0]?.elo ?? 2100; }
}
```

Create `src/app/features/dashboard/dashboard.component.html`:

```html
<!-- Stat cards row -->
<div class="grid grid-cols-4 gap-4 mb-5">
  <div class="card">
    <span class="card-label">Partidos totales</span>
    <p class="font-mono text-3xl font-bold">104</p>
    <p class="text-xs mt-2" style="color:#94A3B8">Mundial 2026 · 48 equipos</p>
  </div>
  <div class="card">
    <span class="card-label">Predicciones activas</span>
    <p class="font-mono text-3xl font-bold" style="color:#3B82F6">{{ matches.length }}</p>
    <p class="text-xs mt-2" style="color:#22C55E">↑ Fase de grupos</p>
  </div>
  <div class="card">
    <span class="card-label">Confianza promedio</span>
    <p class="font-mono text-3xl font-bold" style="color:#22C55E">81%</p>
    <p class="text-xs mt-2" style="color:#22C55E">↑ Modelo estable</p>
  </div>
  @if (meta) {
    <div class="card">
      <span class="card-label">Última actualización</span>
      <p class="font-mono text-xl font-bold" style="color:#F59E0B">
        {{ meta.last_updated | date:'dd MMM · HH:mm' }}
      </p>
      <p class="text-xs mt-2" style="color:#94A3B8">v{{ meta.model_version }}</p>
    </div>
  }
</div>

<!-- Two-column layout -->
<div class="grid grid-cols-2 gap-5">

  <!-- Upcoming matches -->
  <div>
    <h2 class="section-title">Próximos partidos</h2>
    @if (loading) {
      <p class="text-center py-10" style="color:#94A3B8">Cargando…</p>
    }
    @if (error) {
      <p class="text-center py-10" style="color:#EF4444">{{ error }}</p>
    }
    <div class="flex flex-col gap-3">
      @for (m of matches; track m.id) {
        <app-match-card [match]="m" />
      }
    </div>
  </div>

  <!-- Right column -->
  <div>
    <!-- ELO ranking -->
    <h2 class="section-title">Ranking ELO</h2>
    <div class="card p-3 mb-4">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-xs uppercase tracking-wider border-b" style="color:#94A3B8; border-color:#1E3A5F;">
            <th class="text-left p-2 font-semibold">#</th>
            <th class="text-left p-2 font-semibold">Equipo</th>
            <th class="p-2 font-semibold text-right">ELO</th>
            <th class="p-2 w-24"></th>
          </tr>
        </thead>
        <tbody>
          @for (t of topTeams; track t.name; let i = $index) {
            <tr class="border-b" style="border-color:rgba(30,58,95,0.5);">
              <td class="p-2 font-mono text-xs" style="color:#94A3B8;">{{ i + 1 }}</td>
              <td class="p-2">{{ t.name }}</td>
              <td class="p-2 font-mono font-semibold text-right" style="color:#3B82F6;">
                {{ t.elo.toFixed(0) }}
              </td>
              <td class="p-2">
                <div class="h-1 rounded overflow-hidden" style="background:rgba(255,255,255,0.08);">
                  <div class="h-full rounded" style="background:#3B82F6;"
                       [style.width.%]="(t.elo / maxElo) * 100"></div>
                </div>
              </td>
            </tr>
          }
        </tbody>
      </table>
    </div>

    <!-- Model status -->
    @if (meta) {
      <div class="card p-4">
        <span class="card-label">Estado del modelo</span>
        <div class="flex flex-col gap-2 text-sm">
          <div class="flex justify-between items-center">
            <span style="color:#94A3B8;">Versión</span>
            <span class="badge badge-win">v{{ meta.model_version }} · ACTIVO</span>
          </div>
          <div class="flex justify-between">
            <span style="color:#94A3B8;">Dixon-Coles</span>
            <span class="font-mono" style="color:#3B82F6;">
              {{ (meta.ensemble_weights.dixon_coles * 100).toFixed(0) }}%
            </span>
          </div>
          <div class="flex justify-between">
            <span style="color:#94A3B8;">XGBoost</span>
            <span class="font-mono" style="color:#3B82F6;">
              {{ (meta.ensemble_weights.xgboost * 100).toFixed(0) }}%
            </span>
          </div>
          <div class="flex justify-between">
            <span style="color:#94A3B8;">ELO</span>
            <span class="font-mono" style="color:#3B82F6;">
              {{ (meta.ensemble_weights.elo * 100).toFixed(0) }}%
            </span>
          </div>
        </div>
      </div>
    }
  </div>
</div>
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
ng test --include='**/dashboard.component.spec.ts' --watch=false
```

Expected: PASS — 4 tests green.

- [ ] **Step 5: Verify in browser**

```bash
ng serve --port 4200
```

Open `http://localhost:4200`. Expected: stat cards, match list with real data from API, ELO table.

- [ ] **Step 6: Commit**

```bash
git add src/app/features/dashboard/
git commit -m "feat: dashboard with match list, ELO table, and model status"
```

---

## Task 9: Partido Detail View

**Files:**
- Modify: `frontend/src/app/features/partido/partido.component.ts`
- Create: `frontend/src/app/features/partido/partido.component.html`
- Create: `frontend/src/app/features/partido/partido.component.spec.ts`

- [ ] **Step 1: Write failing tests**

Create `src/app/features/partido/partido.component.spec.ts`:

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PartidoComponent } from './partido.component';
import { RouterTestingModule } from '@angular/router/testing';
import { ActivatedRoute } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { of, throwError } from 'rxjs';
import { MatchDetail } from '../../core/models/match.model';

const mockDetail: MatchDetail = {
  id: 1,
  home_team: { id: 1, name: 'México', short_name: null, country_code: 'MX', elo_rating: 1987 },
  away_team: { id: 2, name: 'Sudáfrica', short_name: null, country_code: 'ZA', elo_rating: 1612 },
  kickoff_utc: '2026-06-11T19:00:00', stage: 'GROUP_STAGE', group: 'A',
  venue_city: 'New York', played: false, home_goals: null, away_goals: null,
  prediction: {
    prob_home_win: 0.42, prob_draw: 0.29, prob_away_win: 0.29,
    lambda_home: 1.42, lambda_away: 1.12,
    markets: {
      result_1x2: { home: 0.42, draw: 0.29, away: 0.29 },
      over_05: 0.94, over_15: 0.72, over_25: 0.42,
      over_35: 0.18, over_45: 0.07, under_25: 0.58,
      btts: 0.47, top_scores: [{ score: '1-1', probability: 0.142 }],
      model_confidence: 0.81,
    },
    model_confidence: 0.81, generated_at: '2026-06-08T00:00:00',
  },
};

describe('PartidoComponent', () => {
  let fixture: ComponentFixture<PartidoComponent>;
  let component: PartidoComponent;
  let apiSpy: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    apiSpy = jasmine.createSpyObj('ApiService', ['getMatch']);
    apiSpy.getMatch.and.returnValue(of(mockDetail));

    await TestBed.configureTestingModule({
      imports: [PartidoComponent, RouterTestingModule],
      providers: [
        { provide: ApiService, useValue: apiSpy },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => '1' } } } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PartidoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads and displays team names', () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('México');
    expect(text).toContain('Sudáfrica');
  });

  it('topScores returns up to 8 entries', () => {
    expect(component.topScores.length).toBeLessThanOrEqual(8);
    expect(component.topScores[0].score).toBe('1-1');
  });

  it('maxTopScore returns highest probability', () => {
    expect(component.maxTopScore).toBe(0.142);
  });

  it('getRadarData returns array of 6 numbers', () => {
    const data = component.getRadarData('home');
    expect(data.length).toBe(6);
    data.forEach(v => expect(typeof v).toBe('number'));
  });

  it('shows error when match not found', async () => {
    apiSpy.getMatch.and.returnValue(throwError(() => new Error('Not found')));
    fixture = TestBed.createComponent(PartidoComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('no encontrado');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
ng test --include='**/partido.component.spec.ts' --watch=false
```

Expected: FAIL.

- [ ] **Step 3: Implement PartidoComponent**

Replace `src/app/features/partido/partido.component.ts`:

```typescript
import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { MatchDetail, Markets, ScoreEntry } from '../../core/models/match.model';
import {
  Chart, RadarController, RadialLinearScale,
  PointElement, LineElement, Filler, Tooltip, Legend,
} from 'chart.js';

Chart.register(RadarController, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

@Component({
  selector: 'app-partido',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './partido.component.html',
})
export class PartidoComponent implements OnInit, AfterViewChecked {
  @ViewChild('radarCanvas') radarCanvas?: ElementRef<HTMLCanvasElement>;

  match: MatchDetail | null = null;
  loading = true;
  error: string | null = null;
  private chart: Chart | null = null;
  private chartDrawn = false;

  constructor(private api: ApiService, private route: ActivatedRoute) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.api.getMatch(id).subscribe({
      next: (m) => {
        this.match = m;
        this.loading = false;
        this.chartDrawn = false; // reset so AfterViewChecked draws it
      },
      error: () => {
        this.error = 'Partido no encontrado.';
        this.loading = false;
      },
    });
  }

  ngAfterViewChecked(): void {
    if (this.match && this.radarCanvas && !this.chartDrawn) {
      this.drawRadar();
      this.chartDrawn = true;
    }
  }

  getRadarData(side: 'home' | 'away'): number[] {
    const p = this.match?.prediction;
    if (!p) return [50, 50, 50, 50, 50, 50];
    const homeElo = this.match!.home_team.elo_rating;
    const awayElo = this.match!.away_team.elo_rating;
    const maxElo = 2200;
    if (side === 'home') {
      return [
        Math.min(100, (p.lambda_home / 2.5) * 100),
        Math.min(100, Math.max(0, (1 - p.lambda_away / 2.5) * 100)),
        Math.round(p.prob_home_win * 100),
        50,
        Math.round((homeElo / maxElo) * 100),
        50,
      ].map(v => Math.round(v));
    }
    return [
      Math.min(100, (p.lambda_away / 2.5) * 100),
      Math.min(100, Math.max(0, (1 - p.lambda_home / 2.5) * 100)),
      Math.round(p.prob_away_win * 100),
      50,
      Math.round((awayElo / maxElo) * 100),
      50,
    ].map(v => Math.round(v));
  }

  private drawRadar(): void {
    if (this.chart) { this.chart.destroy(); this.chart = null; }
    const ctx = this.radarCanvas!.nativeElement.getContext('2d');
    if (!ctx || !this.match) return;
    this.chart = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: ['Ataque', 'Defensa', 'Forma', 'H2H', 'ELO', 'Condiciones'],
        datasets: [
          {
            label: this.match.home_team.name,
            data: this.getRadarData('home'),
            borderColor: '#3B82F6',
            backgroundColor: 'rgba(59,130,246,0.15)',
            borderWidth: 1.5,
            pointRadius: 3,
          },
          {
            label: this.match.away_team.name,
            data: this.getRadarData('away'),
            borderColor: '#EF4444',
            backgroundColor: 'rgba(239,68,68,0.1)',
            borderWidth: 1.5,
            pointRadius: 3,
          },
        ],
      },
      options: {
        animation: false,
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            grid: { color: 'rgba(30,58,95,0.8)' },
            pointLabels: { color: '#94A3B8', font: { family: 'Fira Sans', size: 11 } },
            ticks: { display: false },
          },
        },
        plugins: {
          legend: { labels: { color: '#94A3B8', font: { family: 'Fira Sans', size: 11 } } },
        },
      },
    });
  }

  get markets(): Markets | undefined { return this.match?.prediction?.markets; }
  get topScores(): ScoreEntry[] { return this.markets?.top_scores?.slice(0, 8) ?? []; }
  get maxTopScore(): number { return this.topScores[0]?.probability ?? 1; }

  marketColor(val: number, threshold: number): string {
    return val >= threshold ? '#22C55E' : val >= threshold * 0.7 ? '#F59E0B' : '#94A3B8';
  }
}
```

Create `src/app/features/partido/partido.component.html`:

```html
@if (loading) {
  <p class="text-center py-16" style="color:#94A3B8;">Cargando…</p>
}
@if (error) {
  <p class="text-center py-16" style="color:#EF4444;">{{ error }}</p>
}

@if (match) {
  <!-- Match header -->
  <div class="card flex items-center justify-between mb-5 p-6">
    <div class="text-center flex-1">
      <p class="font-bold text-xl">{{ match.home_team.name }}</p>
      <p class="font-mono text-xs mt-1" style="color:#3B82F6;">
        ELO {{ match.home_team.elo_rating.toFixed(0) }}
      </p>
    </div>

    @if (match.prediction) {
      <div class="text-center px-6">
        <div class="flex gap-6 mb-2">
          <div class="text-center">
            <p class="font-mono text-2xl font-bold" style="color:#3B82F6;">
              {{ (match.prediction.prob_home_win * 100).toFixed(0) }}%
            </p>
            <p class="text-xs mt-1" style="color:#94A3B8;">LOCAL</p>
          </div>
          <div class="text-center border-x px-4" style="border-color:#1E3A5F;">
            <p class="font-mono text-2xl font-bold" style="color:#94A3B8;">
              {{ (match.prediction.prob_draw * 100).toFixed(0) }}%
            </p>
            <p class="text-xs mt-1" style="color:#94A3B8;">EMPATE</p>
          </div>
          <div class="text-center">
            <p class="font-mono text-2xl font-bold" style="color:#EF4444;">
              {{ (match.prediction.prob_away_win * 100).toFixed(0) }}%
            </p>
            <p class="text-xs mt-1" style="color:#94A3B8;">VISITANTE</p>
          </div>
        </div>
        <div class="flex h-1.5 rounded overflow-hidden gap-px w-40 mx-auto mt-2">
          <div class="rounded-l" style="background:#3B82F6;"
               [style.width.%]="match.prediction.prob_home_win * 100"></div>
          <div style="background:#94A3B8;"
               [style.width.%]="match.prediction.prob_draw * 100"></div>
          <div class="rounded-r flex-1" style="background:#EF4444;"></div>
        </div>
        <p class="font-mono text-xs mt-2" style="color:#94A3B8;">
          {{ match.kickoff_utc | date:'dd MMM yyyy · HH:mm' }} UTC · {{ match.venue_city }}
        </p>
      </div>
    }

    <div class="text-center flex-1">
      <p class="font-bold text-xl">{{ match.away_team.name }}</p>
      <p class="font-mono text-xs mt-1" style="color:#EF4444;">
        ELO {{ match.away_team.elo_rating.toFixed(0) }}
      </p>
    </div>
  </div>

  @if (match.prediction && markets) {
    <div class="grid grid-cols-2 gap-5">

      <!-- Left: markets + expected goals -->
      <div>
        <h2 class="section-title">Mercados de apuestas</h2>
        <div class="grid grid-cols-3 gap-2 mb-4">
          @for (item of [
            {label:'Over 0.5', val: markets.over_05, t: 0.85},
            {label:'Over 1.5', val: markets.over_15, t: 0.65},
            {label:'Over 2.5', val: markets.over_25, t: 0.50},
            {label:'Over 3.5', val: markets.over_35, t: 0.30},
            {label:'BTTS',     val: markets.btts,    t: 0.50},
            {label:'Confianza',val: match.prediction.model_confidence, t: 0.75}
          ]; track item.label) {
            <div class="market-item">
              <span class="card-label">{{ item.label }}</span>
              <p class="font-mono text-xl font-bold" [style.color]="marketColor(item.val, item.t)">
                {{ (item.val * 100).toFixed(0) }}%
              </p>
            </div>
          }
        </div>

        <!-- Expected goals -->
        <div class="card p-4">
          <span class="card-label">Goles esperados (Dixon-Coles)</span>
          <div class="flex justify-around items-center">
            <div class="text-center">
              <p class="font-mono text-4xl font-bold" style="color:#3B82F6;">
                {{ match.prediction.lambda_home.toFixed(2) }}
              </p>
              <p class="text-xs mt-1" style="color:#94A3B8;">λ {{ match.home_team.name }}</p>
            </div>
            <div class="w-px h-12" style="background:#1E3A5F;"></div>
            <div class="text-center">
              <p class="font-mono text-4xl font-bold" style="color:#EF4444;">
                {{ match.prediction.lambda_away.toFixed(2) }}
              </p>
              <p class="text-xs mt-1" style="color:#94A3B8;">λ {{ match.away_team.name }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: score table + radar -->
      <div>
        <h2 class="section-title">Marcadores más probables</h2>
        <div class="card p-3 mb-4">
          <table class="w-full text-sm font-mono">
            @for (s of topScores; track s.score; let i = $index) {
              <tr class="border-b" style="border-color:rgba(30,58,95,0.4);">
                <td class="p-2 text-xs" style="color:#94A3B8;">{{ i + 1 }}</td>
                <td class="p-2 font-semibold">{{ s.score }}</td>
                <td class="p-2" style="color:#F59E0B;">
                  {{ (s.probability * 100).toFixed(1) }}%
                </td>
                <td class="p-2 w-24">
                  <div class="h-1 rounded overflow-hidden" style="background:rgba(255,255,255,0.08);">
                    <div class="h-full rounded"
                         style="background:linear-gradient(90deg,#D97706,#F59E0B);"
                         [style.width.%]="(s.probability / maxTopScore) * 100"></div>
                  </div>
                </td>
              </tr>
            }
          </table>
        </div>

        <h2 class="section-title">Análisis multidimensional</h2>
        <div class="card p-4">
          <canvas #radarCanvas></canvas>
        </div>
      </div>
    </div>
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
ng test --include='**/partido.component.spec.ts' --watch=false
```

Expected: PASS — 5 tests green.

- [ ] **Step 5: Verify radar chart in browser**

Navigate to `http://localhost:4200/partido/1` (after backend is running with `uvicorn app.main:app --port 8000`).

Expected: team header with probabilities, 6 market cards, score table, radar chart rendered.

- [ ] **Step 6: Commit**

```bash
git add src/app/features/partido/
git commit -m "feat: partido detail view with markets, score table, and Chart.js radar"
```

---

## Task 10: Torneo View

**Files:**
- Modify: `frontend/src/app/features/torneo/torneo.component.ts`
- Create: `frontend/src/app/features/torneo/torneo.component.html`
- Create: `frontend/src/app/features/torneo/torneo.component.spec.ts`

- [ ] **Step 1: Write failing tests**

Create `src/app/features/torneo/torneo.component.spec.ts`:

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TorneoComponent } from './torneo.component';
import { ApiService } from '../../core/services/api.service';
import { of } from 'rxjs';
import { Standing } from '../../core/models/match.model';

const mockStandings: Standing[] = [
  { name: 'México', P: 1, W: 1, D: 0, L: 0, GF: 2, GA: 0, Pts: 3 },
  { name: 'Sudáfrica', P: 1, W: 0, D: 0, L: 1, GF: 0, GA: 2, Pts: 0 },
];

describe('TorneoComponent', () => {
  let fixture: ComponentFixture<TorneoComponent>;
  let component: TorneoComponent;
  let apiSpy: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    apiSpy = jasmine.createSpyObj('ApiService', ['getStandings']);
    apiSpy.getStandings.and.returnValue(of({ standings: mockStandings }));

    await TestBed.configureTestingModule({
      imports: [TorneoComponent],
      providers: [{ provide: ApiService, useValue: apiSpy }],
    }).compileComponents();

    fixture = TestBed.createComponent(TorneoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads and displays team standings', () => {
    expect(fixture.nativeElement.textContent).toContain('México');
    expect(fixture.nativeElement.textContent).toContain('Sudáfrica');
  });

  it('standings are sorted by Pts descending', () => {
    expect(component.sortedStandings[0].name).toBe('México');
    expect(component.sortedStandings[0].Pts).toBe(3);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
ng test --include='**/torneo.component.spec.ts' --watch=false
```

Expected: FAIL.

- [ ] **Step 3: Implement TorneoComponent**

Replace `src/app/features/torneo/torneo.component.ts`:

```typescript
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { Standing } from '../../core/models/match.model';

@Component({
  selector: 'app-torneo',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './torneo.component.html',
})
export class TorneoComponent implements OnInit {
  standings: Standing[] = [];
  loading = true;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getStandings().subscribe({
      next: (r) => { this.standings = r.standings; this.loading = false; },
      error: () => { this.loading = false; },
    });
  }

  get sortedStandings(): Standing[] {
    return [...this.standings].sort((a, b) => {
      if (b.Pts !== a.Pts) return b.Pts - a.Pts;
      const gdA = a.GF - a.GA;
      const gdB = b.GF - b.GA;
      if (gdB !== gdA) return gdB - gdA;
      return b.GF - a.GF;
    });
  }
}
```

Create `src/app/features/torneo/torneo.component.html`:

```html
<h1 class="text-xl font-bold mb-5">Tabla de posiciones — Mundial 2026</h1>

@if (loading) {
  <p class="text-center py-10" style="color:#94A3B8;">Cargando tabla…</p>
}

@if (!loading) {
  <div class="card p-3">
    <table class="w-full text-sm">
      <thead>
        <tr class="text-xs uppercase tracking-wider border-b"
            style="color:#94A3B8; border-color:#1E3A5F;">
          <th class="text-left p-3 font-semibold">Equipo</th>
          <th class="p-3 font-semibold text-center">PJ</th>
          <th class="p-3 font-semibold text-center">G</th>
          <th class="p-3 font-semibold text-center">E</th>
          <th class="p-3 font-semibold text-center">P</th>
          <th class="p-3 font-semibold text-center">GF</th>
          <th class="p-3 font-semibold text-center">GC</th>
          <th class="p-3 font-semibold text-center">DG</th>
          <th class="p-3 font-semibold text-center" style="color:#3B82F6;">Pts</th>
        </tr>
      </thead>
      <tbody>
        @for (s of sortedStandings; track s.name; let i = $index) {
          <tr class="border-b" style="border-color:rgba(30,58,95,0.5);">
            <td class="p-3">
              <span class="font-mono text-xs mr-2" style="color:#94A3B8;">{{ i + 1 }}</span>
              {{ s.name }}
            </td>
            <td class="p-3 text-center font-mono">{{ s.P }}</td>
            <td class="p-3 text-center font-mono" style="color:#22C55E;">{{ s.W }}</td>
            <td class="p-3 text-center font-mono" style="color:#94A3B8;">{{ s.D }}</td>
            <td class="p-3 text-center font-mono" style="color:#EF4444;">{{ s.L }}</td>
            <td class="p-3 text-center font-mono">{{ s.GF }}</td>
            <td class="p-3 text-center font-mono">{{ s.GA }}</td>
            <td class="p-3 text-center font-mono">{{ s.GF - s.GA }}</td>
            <td class="p-3 text-center font-mono font-bold" style="color:#3B82F6;">{{ s.Pts }}</td>
          </tr>
        }
        @if (sortedStandings.length === 0) {
          <tr>
            <td colspan="9" class="p-6 text-center" style="color:#94A3B8;">
              No hay partidos jugados aún.
            </td>
          </tr>
        }
      </tbody>
    </table>
  </div>
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
ng test --include='**/torneo.component.spec.ts' --watch=false
```

Expected: PASS — 2 tests green.

- [ ] **Step 5: Commit**

```bash
git add src/app/features/torneo/
git commit -m "feat: torneo standings table sorted by points/GD/GF"
```

---

## Task 11: Modelo View

**Files:**
- Modify: `frontend/src/app/features/modelo/modelo.component.ts`
- Create: `frontend/src/app/features/modelo/modelo.component.html`
- Create: `frontend/src/app/features/modelo/modelo.component.spec.ts`

- [ ] **Step 1: Write failing tests**

Create `src/app/features/modelo/modelo.component.spec.ts`:

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ModeloComponent } from './modelo.component';
import { ApiService } from '../../core/services/api.service';
import { of } from 'rxjs';
import { ModelMeta } from '../../core/models/match.model';

const mockMeta: ModelMeta = {
  last_updated: '2026-06-08T20:00:00',
  predictions_count: 72,
  model_version: 1,
  ensemble_weights: { dixon_coles: 0.4, xgboost: 0.35, elo: 0.25 },
  methodology: 'Dixon-Coles (1997) + ELO + XGBoost ensemble',
};

describe('ModeloComponent', () => {
  let fixture: ComponentFixture<ModeloComponent>;
  let component: ModeloComponent;
  let apiSpy: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    apiSpy = jasmine.createSpyObj('ApiService', ['getModelMeta']);
    apiSpy.getModelMeta.and.returnValue(of(mockMeta));

    await TestBed.configureTestingModule({
      imports: [ModeloComponent],
      providers: [{ provide: ApiService, useValue: apiSpy }],
    }).compileComponents();

    fixture = TestBed.createComponent(ModeloComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('displays ensemble weights', () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('40%');
    expect(text).toContain('35%');
    expect(text).toContain('25%');
  });

  it('displays predictions count', () => {
    expect(fixture.nativeElement.textContent).toContain('72');
  });

  it('displays methodology text', () => {
    expect(fixture.nativeElement.textContent).toContain('Dixon-Coles');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
ng test --include='**/modelo.component.spec.ts' --watch=false
```

Expected: FAIL.

- [ ] **Step 3: Implement ModeloComponent**

Replace `src/app/features/modelo/modelo.component.ts`:

```typescript
import { Component, OnInit } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { ModelMeta } from '../../core/models/match.model';

@Component({
  selector: 'app-modelo',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './modelo.component.html',
})
export class ModeloComponent implements OnInit {
  meta: ModelMeta | null = null;

  readonly models = [
    {
      name: 'Dixon-Coles',
      weightKey: 'dixon_coles' as const,
      color: '#3B82F6',
      description: 'Modelo Poisson bivariado. Corrección ρ para marcadores bajos (0-0, 1-0, 0-1, 1-1). Ajuste MLE por equipo. Produce λ_home y λ_away.',
    },
    {
      name: 'XGBoost',
      weightKey: 'xgboost' as const,
      color: '#F59E0B',
      description: 'Gradient boosting sobre 20+ features: ELO diferencial, forma últimos 5/10 partidos, días de descanso, altitud de sede, clima, H2H, flags de lesión.',
    },
    {
      name: 'ELO',
      weightKey: 'elo' as const,
      color: '#22C55E',
      description: 'Rating dinámico actualizado tras cada partido. Peso por competición: WC 1.5×, clasificatorias 1.0×, amistosos 0.5×. Decaimiento por inactividad.',
    },
  ];

  readonly markets = [
    '1X2 (Resultado final)', 'Marcador exacto (Bivariate Poisson)',
    'Over/Under 0.5 – 4.5', 'BTTS (Ambos equipos marcan)',
    'Handicap asiático ±0.5', 'Resultado al descanso (HT)',
  ];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getModelMeta().subscribe(m => (this.meta = m));
  }

  weight(key: 'dixon_coles' | 'xgboost' | 'elo'): string {
    if (!this.meta) return '—';
    return (this.meta.ensemble_weights[key] * 100).toFixed(0) + '%';
  }
}
```

Create `src/app/features/modelo/modelo.component.html`:

```html
<h1 class="text-xl font-bold mb-5">Transparencia del modelo</h1>

<div class="grid grid-cols-2 gap-5">

  <!-- Ensemble architecture -->
  <div>
    <h2 class="section-title">Arquitectura del ensemble</h2>
    <div class="card p-4 mb-4">
      @for (m of models; track m.name) {
        <div class="flex gap-4 mb-4 last:mb-0">
          <div class="w-1 rounded flex-shrink-0" [style.background]="m.color"
               style="min-height:48px;"></div>
          <div>
            <p class="font-semibold text-sm mb-1">
              {{ m.name }}
              <span class="font-mono text-xs ml-2" [style.color]="m.color">
                {{ weight(m.weightKey) }}
              </span>
            </p>
            <p class="text-xs" style="color:#94A3B8; line-height:1.5;">{{ m.description }}</p>
          </div>
        </div>
      }
      <div class="mt-4 pt-4 border-t text-center font-mono text-xs" style="border-color:#1E3A5F; color:#94A3B8;">
        P_final = 0.40 × Dixon-Coles + 0.35 × XGBoost + 0.25 × ELO
      </div>
    </div>

    <!-- Formula explanation -->
    <div class="card p-4">
      <span class="card-label">Metodología</span>
      @if (meta) {
        <p class="text-xs leading-relaxed" style="color:#94A3B8;">{{ meta.methodology }}</p>
      }
    </div>
  </div>

  <!-- Right column -->
  <div>
    <h2 class="section-title">Mercados cubiertos</h2>
    <div class="card p-4 mb-4">
      <div class="grid grid-cols-2 gap-2">
        @for (m of markets; track m) {
          <div class="p-2 rounded text-xs border" style="background:rgba(255,255,255,0.03); border-color:#1E3A5F;">
            {{ m }}
          </div>
        }
      </div>
    </div>

    <!-- Live stats -->
    @if (meta) {
      <div class="card p-4">
        <span class="card-label">Estado en tiempo real</span>
        <div class="flex flex-col gap-3">
          <div class="flex justify-between">
            <span class="text-sm" style="color:#94A3B8;">Predicciones activas</span>
            <span class="font-mono font-bold text-sm" style="color:#3B82F6;">
              {{ meta.predictions_count }}
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm" style="color:#94A3B8;">Versión del modelo</span>
            <span class="badge badge-win">v{{ meta.model_version }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm" style="color:#94A3B8;">Última actualización</span>
            <span class="font-mono text-sm" style="color:#F59E0B;">
              {{ meta.last_updated | date:'dd MMM · HH:mm' }}
            </span>
          </div>
        </div>
      </div>
    }
  </div>
</div>
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
ng test --include='**/modelo.component.spec.ts' --watch=false
```

Expected: PASS — 3 tests green.

- [ ] **Step 5: Commit**

```bash
git add src/app/features/modelo/
git commit -m "feat: modelo view with ensemble architecture and methodology"
```

---

## Task 12: Build + nginx Deploy Config

**Files:**
- Modify: `frontend/angular.json` (file replacements for prod)
- Create: `frontend/nginx.conf`

- [ ] **Step 1: Add production file replacements to angular.json**

In `angular.json` under `projects.frontend.architect.build.configurations.production`, add:

```json
"fileReplacements": [
  {
    "replace": "src/environments/environment.ts",
    "with": "src/environments/environment.prod.ts"
  }
]
```

- [ ] **Step 2: Run full test suite**

```bash
ng test --watch=false
```

Expected: all tests PASS (green). Fix any failures before proceeding.

- [ ] **Step 3: Production build**

```bash
ng build --configuration=production
```

Expected: `dist/frontend/browser/` created, no errors.

- [ ] **Step 4: Create nginx.conf**

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /var/www/mundial2026;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1024;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

- [ ] **Step 5: Final commit**

```bash
git add frontend/nginx.conf angular.json
git commit -m "feat: production build config and nginx proxy setup"
```

---

## Self-Review

### Spec Coverage

| Spec Requirement | Task |
|-----------------|------|
| Angular 17+ standalone | Task 1 |
| TailwindCSS | Task 1–2 |
| Chart.js radar chart | Task 9 (PartidoComponent) |
| Dark OLED theme (#050A14 bg, #0D1829 surface) | Task 2 |
| Fira Code + Fira Sans | Task 2 |
| `/` Dashboard: matches + ELO + model status | Task 8 |
| `/partido/:id` markets + score matrix + radar | Task 9 |
| `/torneo` standings | Task 10 |
| `/modelo` methodology + weights | Task 11 |
| nginx config | Task 12 |
| Proxy config for dev | Task 1 |
| Lazy-loaded routes | Task 5 |

### Type Consistency

- `Match.prediction` typed `Prediction | null | undefined` — used consistently across MatchCard, Dashboard, Partido
- `ModelMeta.ensemble_weights` keys `dixon_coles`, `xgboost`, `elo` match backend JSON response
- `Standing` fields `P, W, D, L, GF, GA, Pts` match backend `/api/standings` response

### No Placeholders

All tasks contain complete code. No "TBD" or "implement later" entries.
