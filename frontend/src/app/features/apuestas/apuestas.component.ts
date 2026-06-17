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
  available: SafeBet[] = [];
  champions: OutrightPick[] = [];
  byMatchGroups: MatchDayGroup[] = [];
  loadingByMatch = true;
  note = '';
  loading = true;
  loadingOutrights = true;
  valueOnly = false;
  expanded: string | null = null;
  summary: SlipSummary;

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
    this.loadSafeBets();
    this.loadByMatch();
    // Tournament outrights — champion probabilities from full-bracket sims.
    this.api.getOutrights(3000, 8).subscribe({
      next: (r) => {
        this.champions = r.markets['champion'] ?? [];
        this.loadingOutrights = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loadingOutrights = false; this.cdr.detectChanges(); },
    });
  }

  // Simulation-backed safest bets (Monte Carlo per match + value edge).
  loadSafeBets(): void {
    this.loading = true;
    this.cdr.detectChanges();
    this.api.getSafeBets(40, 8000, 2, this.valueOnly).subscribe({
      next: (r) => {
        this.available = r.picks;
        this.note = r.note;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
  }

  // Best pick for every fixture, chronological, grouped by match day.
  loadByMatch(): void {
    this.loadingByMatch = true;
    this.cdr.detectChanges();
    this.api.getBestBetPerMatch(8000).subscribe({
      next: (r) => {
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

  toggleValueOnly(): void {
    this.valueOnly = !this.valueOnly;
    this.loadSafeBets();
  }

  toggleExpand(p: SafeBet): void {
    const k = pickKey(p);
    this.expanded = this.expanded === k ? null : k;
  }

  isExpanded(p: SafeBet): boolean { return this.expanded === pickKey(p); }

  flag = flagEmoji;
  readonly mxTz = MX_TZ;

  key = pickKey;
  inSlip(p: BetPick): boolean { return this.slip.has(p); }
  toggle(p: BetPick): void { this.slip.toggle(p); }
  remove(p: BetPick): void { this.slip.remove(p); }
  clear(): void { this.slip.clear(); }

  /** Fill the slip with the N safest picks from distinct matches. */
  autoFill(legs = 3): void {
    this.slip.clear();
    const seen = new Set<number>();
    for (const p of this.available) {
      if (seen.has(p.match_id)) continue;
      seen.add(p.match_id);
      this.slip.add(p);
      if (seen.size >= legs) break;
    }
  }

  onStake(value: string): void {
    this.slip.setStake(Number(value));
  }
}
