import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { BetPick } from '../models/match.model';

export interface SlipSummary {
  count: number;
  combinedOdds: number;     // product of decimal odds (parlay)
  combinedProb: number;     // product of model probs (assumes independence)
  impliedProb: number;      // 1 / combinedOdds
  payout: number;           // stake * combinedOdds
  profit: number;           // payout - stake
  expectedValue: number;    // stake * (combinedProb * combinedOdds - 1)
}

export function pickKey(p: BetPick): string {
  return `${p.match_id}:${p.market}:${p.selection}`;
}

@Injectable({ providedIn: 'root' })
export class BetSlipService {
  private picks: BetPick[] = [];
  private stakeValue = 100;

  private picks$ = new BehaviorSubject<BetPick[]>([]);
  readonly slip = this.picks$.asObservable();

  getPicks(): BetPick[] {
    return this.picks;
  }

  has(p: BetPick): boolean {
    const k = pickKey(p);
    return this.picks.some(x => pickKey(x) === k);
  }

  toggle(p: BetPick): void {
    this.has(p) ? this.remove(p) : this.add(p);
  }

  add(p: BetPick): void {
    if (this.has(p)) return;
    // Only one selection per match makes sense in a parlay (can't bet both sides).
    this.picks = this.picks.filter(x => x.match_id !== p.match_id);
    this.picks.push(p);
    this.emit();
  }

  remove(p: BetPick): void {
    const k = pickKey(p);
    this.picks = this.picks.filter(x => pickKey(x) !== k);
    this.emit();
  }

  clear(): void {
    this.picks = [];
    this.emit();
  }

  get stake(): number {
    return this.stakeValue;
  }

  setStake(v: number): void {
    this.stakeValue = isFinite(v) && v > 0 ? v : 0;
    this.emit();
  }

  summary(): SlipSummary {
    const combinedOdds = this.picks.reduce((acc, p) => acc * p.decimal_odds, 1);
    const combinedProb = this.picks.reduce((acc, p) => acc * p.model_prob, 1);
    const stake = this.stakeValue;
    const count = this.picks.length;
    const payout = count ? stake * combinedOdds : 0;
    return {
      count,
      combinedOdds: count ? combinedOdds : 0,
      combinedProb: count ? combinedProb : 0,
      impliedProb: count ? 1 / combinedOdds : 0,
      payout,
      profit: count ? payout - stake : 0,
      expectedValue: count ? stake * (combinedProb * combinedOdds - 1) : 0,
    };
  }

  private emit(): void {
    this.picks$.next([...this.picks]);
  }
}
