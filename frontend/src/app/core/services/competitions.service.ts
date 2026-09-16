import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CompetitionListItem, CompetitionDetail, CompetitionsListResponse } from '../../shared/models/competition.model';

export interface CompetitionFiltersResponse {
  filters: {
    discipline?: Array<{ value: string; label: string }>;
    season?: Array<{ value: string; label: string }>;
    year?: Array<{ value: string; label: string }>;
    series?: Array<{ value: string; label: string }>;
    group?: Array<{ value: string; label: string }>;
    pool?: Array<{ value: string; label: string }>;
    organization?: Array<{ value: string; label: string }>;
  };
}

@Injectable({ providedIn: 'root' })
export class CompetitionsService {
  private readonly base = '/competitions';

  constructor(private readonly http: HttpClient) {}

  getList(params?: { limit?: number; offset?: number }): Observable<CompetitionsListResponse> {
    let httpParams = new HttpParams();
    if (params?.limit) httpParams = httpParams.set('limit', params.limit.toString());
    if (params?.offset) httpParams = httpParams.set('offset', params.offset.toString());
    return this.http.get<CompetitionsListResponse>(this.base, { params: httpParams });
  }

  getById(id: string): Observable<CompetitionDetail> {
    return this.http.get<CompetitionDetail>(`${this.base}/${id}`);
  }

  /**
   * Get distinct filter options for granular championship filters.
   * Returns: discipline, season, year, series, group, pool, organization
   */
  getFilters(): Observable<CompetitionFiltersResponse> {
    return this.http.get<CompetitionFiltersResponse>(`${this.base}/filters`);
  }
}
