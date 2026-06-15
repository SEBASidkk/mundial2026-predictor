import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { BetSlipService, SlipSummary, pickKey } from '../../core/services/bet-slip.service';
import { BetPick, SafeBet, OutrightPick } from '../../core/models/match.model';

@Component({
  selector: 'app-apuestas',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './apuestas.component.html',
})
export class ApuestasComponent implements OnInit {
  available: SafeBet[] = [];
  champions: OutrightPick[] = [];
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

  toggleValueOnly(): void {
    this.valueOnly = !this.valueOnly;
    this.loadSafeBets();
  }

  toggleExpand(p: SafeBet): void {
    const k = pickKey(p);
    this.expanded = this.expanded === k ? null : k;
  }

  isExpanded(p: SafeBet): boolean { return this.expanded === pickKey(p); }

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
