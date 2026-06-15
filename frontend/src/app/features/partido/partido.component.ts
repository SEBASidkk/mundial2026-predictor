import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked, ChangeDetectorRef } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { MatchDetail, Markets, ScoreEntry, BetPick, SimResult } from '../../core/models/match.model';
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
  sim: SimResult | null = null;
  simulating = false;
  private chart: Chart | null = null;
  private chartDrawn = false;

  constructor(private api: ApiService, private route: ActivatedRoute, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.api.getMatch(id).subscribe({
      next: (m) => {
        this.match = m;
        this.loading = false;
        this.chartDrawn = false;
        this.cdr.detectChanges();   // renders the canvas into the DOM
        // Zoneless: ngAfterViewChecked is unreliable for async data. Defer one frame
        // so the browser computes the container width before Chart.js sizes the canvas.
        requestAnimationFrame(() => {
          if (this.match?.prediction && this.radarCanvas && !this.chartDrawn) {
            this.drawRadar();
            this.chartDrawn = true;
          }
        });
      },
      error: () => {
        this.error = 'Partido no encontrado.';
        this.loading = false;
        this.cdr.detectChanges();
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

  get bets(): BetPick[] { return this.match?.bets ?? []; }

  runSimulation(): void {
    if (!this.match || this.simulating) return;
    this.simulating = true;
    this.cdr.detectChanges();
    this.api.simulateMatch(this.match.id, 10000).subscribe({
      next: (r) => { this.sim = r; this.simulating = false; this.cdr.detectChanges(); },
      error: () => { this.simulating = false; this.cdr.detectChanges(); },
    });
  }

  get maxGoalProb(): number {
    return this.sim ? Math.max(...this.sim.goal_distribution.map(g => g.probability), 0.01) : 1;
  }

  get markets(): Markets | undefined { return this.match?.prediction?.markets; }
  get topScores(): ScoreEntry[] { return this.markets?.top_scores?.slice(0, 8) ?? []; }
  get maxTopScore(): number { return this.topScores[0]?.probability ?? 1; }

  marketColor(val: number, threshold: number): string {
    return val >= threshold ? '#22C55E' : val >= threshold * 0.7 ? '#F59E0B' : '#94A3B8';
  }
}
