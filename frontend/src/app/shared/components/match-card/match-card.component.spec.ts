import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatchCardComponent } from './match-card.component';
import { RouterTestingModule } from '@angular/router/testing';
import { Match } from '../../../core/models/match.model';

const mockMatch: Match = {
  id: 1,
  home_team: { id: 1, name: 'México', short_name: 'MEX', country_code: 'MX', elo_rating: 1987 },
  away_team: { id: 2, name: 'Sudáfrica', short_name: 'RSA', country_code: 'ZA', elo_rating: 1612 },
  kickoff_utc: '2026-06-11T19:00:00',
  stage: 'GROUP_STAGE', group: 'A', venue_city: 'New York',
  played: false, home_goals: null, away_goals: null,
  prediction: {
    prob_home_win: 0.42, prob_draw: 0.29, prob_away_win: 0.29,
    lambda_home: 1.42, lambda_away: 1.12,
    markets: {
      result_1x2: { home: 0.42, draw: 0.29, away: 0.29 },
      over_05: 0.94, over_15: 0.72, over_25: 0.42,
      over_35: 0.18, over_45: 0.07, under_25: 0.58,
      btts: 0.47, top_scores: [{ score: '1-1', probability: 0.142 }],
      model_confidence: 0.81,
    },
    model_confidence: 0.81, generated_at: '2026-06-08T00:00:00',
  },
};

describe('MatchCardComponent', () => {
  let fixture: ComponentFixture<MatchCardComponent>;
  let component: MatchCardComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MatchCardComponent, RouterTestingModule],
    }).compileComponents();
    fixture = TestBed.createComponent(MatchCardComponent);
    component = fixture.componentInstance;
    component.match = mockMatch;
    fixture.detectChanges();
  });

  it('renders both team names', () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('México');
    expect(text).toContain('Sudáfrica');
  });

  it('homeProb returns prob_home_win', () => {
    expect(component.homeProb).toBe(0.42);
  });

  it('drawProb returns prob_draw', () => {
    expect(component.drawProb).toBe(0.29);
  });

  it('over25 returns markets.over_25', () => {
    expect(component.over25).toBe(0.42);
  });

  it('topScore formats first score entry as "X-Y (N%)"', () => {
    expect(component.topScore).toBe('1-1 (14%)');
  });

  it('topScore returns "-" when no prediction', () => {
    component.match = { ...mockMatch, prediction: undefined };
    expect(component.topScore).toBe('-');
  });

  it('renders link to /partido/1', () => {
    const link = fixture.nativeElement.querySelector('a');
    expect(link.getAttribute('href')).toContain('/partido/1');
  });
});
