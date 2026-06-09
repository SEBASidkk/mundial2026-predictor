import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Match, MatchDetail, ModelMeta, StandingsResponse } from '../models/match.model';

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
}
