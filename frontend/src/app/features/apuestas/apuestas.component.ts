import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { BetSlipService, SlipSummary, pickKey } from '../../core/services/bet-slip.service';
import { BetPick, SafeBet, OutrightPick, MatchBestBet } from '../../core/models/match.model';
import { flagEmoji, MX_TZ } from '../../core/utils/flag.util';

interface MatchDayGroup {
  date: string;             // ISO date (yyyy-MM-dd) for the DatePipe
  matches: MatchBestBet[];
}

@Component({
  selector: 'app-apuestas',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './apuestas.component.html',
})
export class ApuestasComponent implements OnInit {
  champions: OutrightPick[] = [];
  byMatchGroups: MatchDayGroup[] = [];
  loadingByMatch = true;
  loadingOutrights = true;
  note = '';
  autoFillNote: string | null = null;
  summary: SlipSummary;

  flag = flagEmoji;
  readonly mxTz = MX_TZ;

  constructor(
    private api: ApiService,
    public slip: BetSlipService,
    private cdr: ChangeDetectorRef,
  ) {
    this.summary = this.slip.summary();
  }

  ngOnInit(): void {
    this.slip.slip.subscribe(() => {
      this.summary = this.slip.summary();
      this.cdr.detectChanges();
    });
    this.loadByMatch();
    this.api.getOutrights(3000, 8).subscribe({
      next: (r) => {
        this.champions = r.markets['champion'] ?? [];
        this.loadingOutrights = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loadingOutrights = false; this.cdr.detectChanges(); },
    });
  }

  // Top picks for every fixture, chronological, grouped by match day.
  loadByMatch(): void {
    this.loadingByMatch = true;
    this.cdr.detectChanges();
    this.api.getBestBetPerMatch(8000).subscribe({
      next: (r) => {
        this.note = r.note;
        this.byMatchGroups = this.groupByDay(r.matches);
        this.loadingByMatch = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loadingByMatch = false; this.cdr.detectChanges(); },
    });
  }

  private groupByDay(matches: MatchBestBet[]): MatchDayGroup[] {
    const groups = new Map<string, MatchBestBet[]>();
    for (const m of matches) {
      const day = m.kickoff_utc.slice(0, 10); // yyyy-MM-dd
      (groups.get(day) ?? groups.set(day, []).get(day)!).push(m);
    }
    return [...groups.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, ms]) => ({ date, matches: ms }));
  }

  /** Every pick across every fixture, flattened. */
  private allPicks(): SafeBet[] {
    return this.byMatchGroups.flatMap(g => g.matches.flatMap(m => m.picks));
  }

  /**
   * Build a parlay of the safest legs: keep only likely picks (prob ≥ 0.55),
   * one per match, then rank by probability first and decimal odds second so
   * the slip favours hits while still grabbing the better-priced of equals.
   * Falls back to lower probabilities if there aren't enough strong legs.
   */
  autoFill(minLegs = 5): void {
    const ranked = (threshold: number) =>
      this.allPicks()
        .filter(p => p.model_prob >= threshold)
        .sort((a, b) => (b.model_prob - a.model_prob) || (b.decimal_odds - a.decimal_odds));

    let pool = ranked(0.55);
    if (pool.length < minLegs) pool = ranked(0.0);

    this.slip.clear();
    const seen = new Set<number>();
    for (const p of pool) {
      if (seen.has(p.match_id)) continue;
      seen.add(p.match_id);
      this.slip.add(p);
      if (seen.size >= minLegs) break;
    }
    this.autoFillNote = seen.size
      ? `Combinada de ${seen.size} apuestas: las más probables con mejor momio.`
      : 'No hay apuestas disponibles para combinar.';
  }

  key = pickKey;
  inSlip(p: BetPick): boolean { return this.slip.has(p); }
  toggle(p: BetPick): void { this.slip.toggle(p); }
  remove(p: BetPick): void { this.slip.remove(p); }
  clear(): void { this.slip.clear(); this.autoFillNote = null; }

  onStake(value: string): void {
    this.slip.setStake(Number(value));
  }
}
