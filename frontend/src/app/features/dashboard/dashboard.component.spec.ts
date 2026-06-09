import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DashboardComponent } from './dashboard.component';
import { RouterTestingModule } from '@angular/router/testing';
import { ApiService } from '../../core/services/api.service';
import { of, throwError } from 'rxjs';
import { vi } from 'vitest';
import { Match, ModelMeta } from '../../core/models/match.model';

const mockMatch: Match = {
  id: 1,
  home_team: { id: 1, name: 'México', short_name: null, country_code: 'MX', elo_rating: 1987 },
  away_team: { id: 2, name: 'Sudáfrica', short_name: null, country_code: 'ZA', elo_rating: 1612 },
  kickoff_utc: '2026-06-11T19:00:00', stage: 'GROUP_STAGE', group: 'A',
  venue_city: 'New York', played: false, home_goals: null, away_goals: null, prediction: null,
};

const mockMeta: ModelMeta = {
  last_updated: '2026-06-08T20:00:00', predictions_count: 72, model_version: 1,
  ensemble_weights: { dixon_coles: 0.4, xgboost: 0.35, elo: 0.25 },
  methodology: 'Dixon-Coles + ELO + XGBoost',
};

describe('DashboardComponent', () => {
  let fixture: ComponentFixture<DashboardComponent>;
  let component: DashboardComponent;
  let apiMock: { getMatches: ReturnType<typeof vi.fn>; getModelMeta: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    apiMock = {
      getMatches: vi.fn().mockReturnValue(of([mockMatch])),
      getModelMeta: vi.fn().mockReturnValue(of(mockMeta)),
    };

    await TestBed.configureTestingModule({
      imports: [DashboardComponent, RouterTestingModule],
      providers: [{ provide: ApiService, useValue: apiMock }],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('displays team names from loaded matches', () => {
    expect(fixture.nativeElement.textContent).toContain('México');
  });

  it('topTeams returns teams sorted descending by ELO', () => {
    expect(component.topTeams[0].elo).toBe(1987);
    expect(component.topTeams[0].name).toBe('México');
  });

  it('shows model version from meta', () => {
    expect(fixture.nativeElement.textContent).toContain('v1');
  });

  it('shows error message when API fails', async () => {
    apiMock.getMatches.mockReturnValue(throwError(() => new Error('Network error')));
    fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('No se pudo cargar');
  });
});
