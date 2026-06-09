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
