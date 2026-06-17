import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { MatchCardComponent } from '../../shared/components/match-card/match-card.component';
import { Match, ModelMeta, BetPick } from '../../core/models/match.model';
import { flagEmoji, MX_TZ } from '../../core/utils/flag.util';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, DatePipe, MatchCardComponent, RouterLink],
  templateUrl: './dashboard.component.html',
})
export class DashboardComponent implements OnInit, OnDestroy {
  matches: Match[] = [];
  meta: ModelMeta | null = null;
  bestBets: BetPick[] = [];
  loading = true;
  error: string | null = null;
  refreshing = false;
  refreshError: string | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.loadAll();
  }

  private loadAll(): void {
    this.api.getMatches().subscribe({
      next: (m) => {
        this.matches = m.filter(x => !x.played).slice(0, 6);
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (e) => {
        console.error('[Dashboard] getMatches error:', e);
        this.error = 'No se pudo cargar los partidos.';
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
    this.api.getModelMeta().subscribe({
      next: (m) => {
        this.meta = m;
        this.cdr.detectChanges();
      },
      error: (e) => console.error('[Dashboard] getModelMeta error:', e),
    });
    this.api.getBestBets(12).subscribe({
      next: (r) => {
        this.bestBets = r.picks;
        this.cdr.detectChanges();
      },
      error: (e) => console.error('[Dashboard] getBestBets error:', e),
    });
  }

  /** Manually re-run the pipeline (pull latest results/odds), then reload. */
  refresh(): void {
    if (this.refreshing) return;
    this.refreshing = true;
    this.refreshError = null;
    this.cdr.detectChanges();
    this.api.triggerRefresh().subscribe({
      next: () => this.pollUntilDone(),
      error: () => { this.refreshing = false; this.refreshError = 'No se pudo iniciar la actualización.'; this.cdr.detectChanges(); },
    });
  }

  private pollUntilDone(): void {
    this.clearPoll();
    this.pollTimer = setInterval(() => {
      this.api.getRefreshStatus().subscribe({
        next: (s) => {
          if (!s.running) {
            this.clearPoll();
            this.refreshing = false;
            this.refreshError = s.last_error ? `Falló: ${s.last_error}` : null;
            this.loadAll();
            this.cdr.detectChanges();
          }
        },
        error: () => { this.clearPoll(); this.refreshing = false; this.cdr.detectChanges(); },
      });
    }, 2000);
  }

  private clearPoll(): void {
    if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
  }

  ngOnDestroy(): void { this.clearPoll(); }

  flag = flagEmoji;
  readonly mxTz = MX_TZ;

  get topTeams(): { name: string; elo: number; code: string | null }[] {
    const map = new Map<number, { name: string; elo: number; code: string | null }>();
    this.matches.forEach(m => {
      map.set(m.home_team.id, { name: m.home_team.name, elo: m.home_team.elo_rating, code: m.home_team.country_code });
      map.set(m.away_team.id, { name: m.away_team.name, elo: m.away_team.elo_rating, code: m.away_team.country_code });
    });
    return [...map.values()].sort((a, b) => b.elo - a.elo).slice(0, 8);
  }

  get maxElo(): number { return this.topTeams[0]?.elo ?? 2100; }
}
