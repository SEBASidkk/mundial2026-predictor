import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TorneoComponent } from './torneo.component';
import { ApiService } from '../../core/services/api.service';
import { of } from 'rxjs';
import { vi } from 'vitest';
import { Standing } from '../../core/models/match.model';

const mockStandings: Standing[] = [
  { name: 'México', P: 1, W: 1, D: 0, L: 0, GF: 2, GA: 0, Pts: 3 },
  { name: 'Sudáfrica', P: 1, W: 0, D: 0, L: 1, GF: 0, GA: 2, Pts: 0 },
];

describe('TorneoComponent', () => {
  let fixture: ComponentFixture<TorneoComponent>;
  let component: TorneoComponent;
  let apiMock: { getStandings: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    apiMock = { getStandings: vi.fn().mockReturnValue(of({ standings: mockStandings })) };

    await TestBed.configureTestingModule({
      imports: [TorneoComponent],
      providers: [{ provide: ApiService, useValue: apiMock }],
    }).compileComponents();

    fixture = TestBed.createComponent(TorneoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads and displays team standings', () => {
    expect(fixture.nativeElement.textContent).toContain('México');
    expect(fixture.nativeElement.textContent).toContain('Sudáfrica');
  });

  it('standings are sorted by Pts descending', () => {
    expect(component.sortedStandings[0].name).toBe('México');
    expect(component.sortedStandings[0].Pts).toBe(3);
  });
});
