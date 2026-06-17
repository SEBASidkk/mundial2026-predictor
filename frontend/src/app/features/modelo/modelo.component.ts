import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { ModelMeta, ModelMetrics } from '../../core/models/match.model';

@Component({
  selector: 'app-modelo',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './modelo.component.html',
})
export class ModeloComponent implements OnInit {
  meta: ModelMeta | null = null;
  metrics: ModelMetrics | null = null;

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

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.api.getModelMeta().subscribe(m => { this.meta = m; this.cdr.detectChanges(); });
    this.api.getModelMetrics().subscribe({
      next: m => { this.metrics = m; this.cdr.detectChanges(); },
      error: () => {},
    });
  }

  weight(key: 'dixon_coles' | 'xgboost' | 'elo'): string {
    if (!this.meta) return '—';
    return (this.meta.ensemble_weights[key] * 100).toFixed(0) + '%';
  }

  /** Dynamic ensemble formula reflecting the learned weights. */
  get formula(): string {
    if (!this.meta) return '—';
    const w = this.meta.ensemble_weights;
    return `P_final = ${w.dixon_coles.toFixed(2)} × Dixon-Coles + ` +
           `${w.xgboost.toFixed(2)} × XGBoost + ${w.elo.toFixed(2)} × ELO`;
  }

  /** How much better the model's Brier is vs an uninformed uniform guess. */
  get brierEdge(): string {
    if (!this.metrics?.brier || !this.metrics?.baseline_brier) return '—';
    const pct = (1 - this.metrics.brier / this.metrics.baseline_brier) * 100;
    return (pct >= 0 ? '+' : '') + pct.toFixed(0) + '%';
  }
}
