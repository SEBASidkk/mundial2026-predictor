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
