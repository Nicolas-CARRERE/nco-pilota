/**
 * The filter options the API knows about, from /analytics/filters.
 *
 * The counterpart of DashboardFilterStateService, which holds the filters the user
 * has chosen. Nothing injects this one yet: the filter panel takes its options from
 * CompetitionsService and from lists written in the component. Recorded as a task
 * rather than removed — the endpoint exists and answers.
 */
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { FiltersResponse } from '../../shared/models/filter.model';

@Injectable({ providedIn: 'root' })
export class FilterOptionsService {
  private readonly base = '/analytics/filters';

  constructor(private readonly http: HttpClient) {}

  getFilters(sourceId?: string): Observable<FiltersResponse> {
    const params = sourceId
      ? new HttpParams().set('sourceId', sourceId)
      : undefined;
    return this.http.get<FiltersResponse>(this.base, { params });
  }
}
