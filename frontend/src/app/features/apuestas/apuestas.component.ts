import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { BetSlipService, SlipSummary, pickKey } from '../../core/services/bet-slip.service';
import { BetPick } from '../../core/models/match.model';

@Component({
  selector: 'app-apuestas',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './apuestas.component.html',
})
export class ApuestasComponent implements OnInit {
  available: BetPick[] = [];
  loading = true;
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
    this.api.getBestBets(40).subscribe({
      next: (r) => {
        this.available = r.picks;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
  }

  key = pickKey;
  inSlip(p: BetPick): boolean { return this.slip.has(p); }
  toggle(p: BetPick): void { this.slip.toggle(p); }
  remove(p: BetPick): void { this.slip.remove(p); }
  clear(): void { this.slip.clear(); }

  onStake(value: string): void {
    this.slip.setStake(Number(value));
  }
}
