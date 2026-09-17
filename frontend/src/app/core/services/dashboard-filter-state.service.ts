/**
 * The dashboard's filter state: which filters are set, kept in memory and in
 * localStorage.
 *
 * Not to be confused with FilterOptionsService, which fetches the values a filter
 * could take. This one holds what the user chose; that one asks the API what is
 * available.
 */
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { distinctUntilChanged } from 'rxjs/operators';

export interface DashboardFilters {
  competition?: string;
  discipline?: string;
  season?: number;
  club?: string;
  player?: string;
  date_from?: string;
  date_to?: string;
  phase?: string;
}

const STORAGE_KEY = 'dashboard_filters';

@Injectable({ providedIn: 'root' })
export class DashboardFilterStateService {
  private readonly defaultFilters: DashboardFilters = {};
  private filtersSubject = new BehaviorSubject<DashboardFilters>(this.defaultFilters);

  constructor() {
    this.loadFromStorage();
  }

  getFilters(): Observable<DashboardFilters> {
    return this.filtersSubject.asObservable().pipe(distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)));
  }

  getCurrentFilters(): DashboardFilters {
    return this.filtersSubject.getValue();
  }

  updateFilters(filters: Partial<DashboardFilters>): void {
    const current = this.getCurrentFilters();
    const updated = { ...current, ...filters };
    this.filtersSubject.next(updated);
    this.saveToStorage(updated);
  }

  resetFilters(): void {
    this.filtersSubject.next(this.defaultFilters);
    this.saveToStorage(this.defaultFilters);
  }

  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as DashboardFilters;
        this.filtersSubject.next(parsed);
      }
    } catch (e) {
      console.warn('Failed to load dashboard filters from storage', e);
    }
  }

  private saveToStorage(filters: DashboardFilters): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
    } catch (e) {
      console.warn('Failed to save dashboard filters to storage', e);
    }
  }
}
