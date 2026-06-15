import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Match, MatchDetail, ModelMeta, StandingsResponse, BestBetsResponse, SimResult } from '../models/match.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getMatches(): Observable<Match[]> {
    return this.http.get<Match[]>(`${this.base}/api/matches`);
  }

  getMatch(id: number): Observable<MatchDetail> {
    return this.http.get<MatchDetail>(`${this.base}/api/match/${id}`);
  }

  getStandings(): Observable<StandingsResponse> {
    return this.http.get<StandingsResponse>(`${this.base}/api/standings`);
  }

  getModelMeta(): Observable<ModelMeta> {
    return this.http.get<ModelMeta>(`${this.base}/api/model/meta`);
  }

  getBestBets(limit = 12): Observable<BestBetsResponse> {
    return this.http.get<BestBetsResponse>(`${this.base}/api/bets/best?limit=${limit}`);
  }

  simulateMatch(id: number, n = 10000): Observable<SimResult> {
    return this.http.get<SimResult>(`${this.base}/api/match/${id}/simulate?n=${n}`);
  }
}
