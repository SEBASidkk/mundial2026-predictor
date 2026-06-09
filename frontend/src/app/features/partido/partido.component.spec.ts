import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PartidoComponent } from './partido.component';
import { RouterTestingModule } from '@angular/router/testing';
import { ActivatedRoute } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { of, throwError } from 'rxjs';
import { vi } from 'vitest';
import { MatchDetail } from '../../core/models/match.model';

const mockDetail: MatchDetail = {
  id: 1,
  home_team: { id: 1, name: 'México', short_name: null, country_code: 'MX', elo_rating: 1987 },
  away_team: { id: 2, name: 'Sudáfrica', short_name: null, country_code: 'ZA', elo_rating: 1612 },
  kickoff_utc: '2026-06-11T19:00:00', stage: 'GROUP_STAGE', group: 'A',
  venue_city: 'New York', played: false, home_goals: null, away_goals: null,
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

describe('PartidoComponent', () => {
  let fixture: ComponentFixture<PartidoComponent>;
  let component: PartidoComponent;
  let apiMock: { getMatch: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    apiMock = { getMatch: vi.fn().mockReturnValue(of(mockDetail)) };

    await TestBed.configureTestingModule({
      imports: [PartidoComponent, RouterTestingModule],
      providers: [
        { provide: ApiService, useValue: apiMock },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => '1' } } } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PartidoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads and displays team names', () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('México');
    expect(text).toContain('Sudáfrica');
  });

  it('topScores returns up to 8 entries', () => {
    expect(component.topScores.length).toBeLessThanOrEqual(8);
    expect(component.topScores[0].score).toBe('1-1');
  });

  it('maxTopScore returns highest probability', () => {
    expect(component.maxTopScore).toBe(0.142);
  });

  it('getRadarData returns array of 6 numbers', () => {
    const data = component.getRadarData('home');
    expect(data.length).toBe(6);
    data.forEach(v => expect(typeof v).toBe('number'));
  });

  it('shows error when match not found', async () => {
    apiMock.getMatch.mockReturnValue(throwError(() => new Error('Not found')));
    fixture = TestBed.createComponent(PartidoComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('no encontrado');
  });
});
