import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ApiService } from './api.service';

describe('ApiService', () => {
  let service: ApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ApiService],
    });
    service = TestBed.inject(ApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('getMatches() GETs /api/matches', () => {
    service.getMatches().subscribe(matches => expect(matches.length).toBe(2));
    const req = httpMock.expectOne('/api/matches');
    expect(req.request.method).toBe('GET');
    req.flush([{ id: 1 }, { id: 2 }]);
  });

  it('getMatch() GETs /api/match/:id', () => {
    service.getMatch(42).subscribe(m => expect((m as any).id).toBe(42));
    const req = httpMock.expectOne('/api/match/42');
    expect(req.request.method).toBe('GET');
    req.flush({ id: 42 });
  });

  it('getStandings() GETs /api/standings', () => {
    service.getStandings().subscribe(r => expect(r.standings).toBeDefined());
    const req = httpMock.expectOne('/api/standings');
    expect(req.request.method).toBe('GET');
    req.flush({ standings: [] });
  });

  it('getModelMeta() GETs /api/model/meta', () => {
    service.getModelMeta().subscribe(m => expect((m as any).model_version).toBe(1));
    const req = httpMock.expectOne('/api/model/meta');
    expect(req.request.method).toBe('GET');
    req.flush({ model_version: 1 });
  });
});
