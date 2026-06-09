import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ModeloComponent } from './modelo.component';
import { ApiService } from '../../core/services/api.service';
import { of } from 'rxjs';
import { vi } from 'vitest';
import { ModelMeta } from '../../core/models/match.model';

const mockMeta: ModelMeta = {
  last_updated: '2026-06-08T20:00:00',
  predictions_count: 72,
  model_version: 1,
  ensemble_weights: { dixon_coles: 0.4, xgboost: 0.35, elo: 0.25 },
  methodology: 'Dixon-Coles (1997) + ELO + XGBoost ensemble',
};

describe('ModeloComponent', () => {
  let fixture: ComponentFixture<ModeloComponent>;
  let apiMock: { getModelMeta: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    apiMock = { getModelMeta: vi.fn().mockReturnValue(of(mockMeta)) };

    await TestBed.configureTestingModule({
      imports: [ModeloComponent],
      providers: [{ provide: ApiService, useValue: apiMock }],
    }).compileComponents();

    fixture = TestBed.createComponent(ModeloComponent);
    fixture.detectChanges();
  });

  it('displays ensemble weights', () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('40%');
    expect(text).toContain('35%');
    expect(text).toContain('25%');
  });

  it('displays predictions count', () => {
    expect(fixture.nativeElement.textContent).toContain('72');
  });

  it('displays methodology text', () => {
    expect(fixture.nativeElement.textContent).toContain('Dixon-Coles');
  });
});
