import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CompetitionsService } from '../../../core/services/competitions.service';
import { CompetitionListItem } from '../../../shared/models/competition.model';

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterConfig {
  showCompetition?: boolean;
  showDiscipline?: boolean;
  showSeason?: boolean;
  showPhase?: boolean;
  showDateRange?: boolean;
  showStatus?: boolean;
  showGranularFilters?: boolean; // NEW: discipline, season, year, series, group, pool, organization
  compact?: boolean;
}

export interface FieldErrors {
  [key: string]: string;
}

@Component({
  selector: 'app-filter',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './filter.component.html',
  styleUrl: './filter.component.scss',
})
export class FilterComponent implements OnInit {
  @Input() config: FilterConfig = {};
  @Input() filters: Record<string, any> = {};
  @Input() fieldErrors: FieldErrors = {};
  @Output() filtersChange = new EventEmitter<Record<string, any>>();
  @Output() resetFilters = new EventEmitter<void>();

  competitions: CompetitionListItem[] = [];
  loading = false;

  @Input() disciplineOptions: FilterOption[] = [
    { value: '', label: 'Toutes' },
    { value: 'main-nue', label: 'Main Nue' },
    { value: 'chistera', label: 'Chistera' },
    { value: 'paleta', label: 'Paleta' },
    { value: 'gros-paleta', label: 'Gros Paleta' },
    { value: 'pala-corta', label: 'Pala Corta' },
  ];

  @Input() phaseOptions: FilterOption[] = [
    { value: '', label: 'Toutes' },
    { value: 'poules', label: 'Poules' },
    { value: 'barrage', label: 'Barrage' },
    { value: 'quart', label: '1/4 finale' },
    { value: 'demi', label: '1/2 finale' },
    { value: 'finale', label: 'Finale' },
  ];

  @Input() statusOptions: FilterOption[] = [
    { value: '', label: 'Tous' },
    { value: 'cancelled', label: 'Annulé' },
    { value: 'in_progress', label: 'En cours' },
    { value: 'scheduled', label: 'Programmé' },
    { value: 'postponed', label: 'Reporté' },
    { value: 'completed', label: 'Terminé' },
  ];

  // NEW: Granular championship filter options
  @Input() granularDisciplineOptions: FilterOption[] = [{ value: '', label: 'Toutes' }];
  @Input() granularSeasonOptions: FilterOption[] = [{ value: '', label: 'Toutes' }];
  @Input() granularYearOptions: FilterOption[] = [{ value: '', label: 'Toutes' }];
  @Input() granularSeriesOptions: FilterOption[] = [{ value: '', label: 'Toutes' }];
  @Input() granularGroupOptions: FilterOption[] = [{ value: '', label: 'Tous' }];
  @Input() granularPoolOptions: FilterOption[] = [{ value: '', label: 'Toutes' }];
  @Input() granularOrganizationOptions: FilterOption[] = [{ value: '', label: 'Toutes' }];

  constructor(private competitionsService: CompetitionsService) {}

  ngOnInit(): void {
    if (this.config.showCompetition) {
      this.loading = true;
      this.competitionsService.getList({ limit: 200 }).subscribe({
        next: (res) => {
          this.competitions = res.competitions;
          this.loading = false;
        },
        error: () => {
          this.loading = false;
        },
      });
    }

    // NEW: Load granular filter options if enabled
    if (this.config.showGranularFilters) {
      this.loadGranularFilterOptions();
    }
  }

  loadGranularFilterOptions(): void {
    this.competitionsService.getFilters().subscribe({
      next: (res) => {
        const filters = res.filters || {};
        if (filters.discipline) {
          this.granularDisciplineOptions = [
            { value: '', label: 'Toutes' },
            ...filters.discipline,
          ];
        }
        if (filters.season) {
          this.granularSeasonOptions = [
            { value: '', label: 'Toutes' },
            ...filters.season,
          ];
        }
        if (filters.year) {
          this.granularYearOptions = [
            { value: '', label: 'Toutes' },
            ...filters.year,
          ];
        }
        if (filters.series) {
          this.granularSeriesOptions = [
            { value: '', label: 'Toutes' },
            ...filters.series,
          ];
        }
        if (filters.group) {
          this.granularGroupOptions = [
            { value: '', label: 'Tous' },
            ...filters.group,
          ];
        }
        if (filters.pool) {
          this.granularPoolOptions = [
            { value: '', label: 'Toutes' },
            ...filters.pool,
          ];
        }
        if (filters.organization) {
          this.granularOrganizationOptions = [
            { value: '', label: 'Toutes' },
            ...filters.organization,
          ];
        }
      },
      error: (err) => {
        console.error('Failed to load granular filter options', err);
      },
    });
  }

  onFilterChange(key: string, value: any): void {
    const updated = { ...this.filters, [key]: value };
    // Clear error for this field when user changes it
    if (this.fieldErrors[key]) {
      delete this.fieldErrors[key];
    }
    this.filtersChange.emit(updated);
  }

  doResetFilters(): void {
    const reset: Record<string, any> = {};
    this.filters = reset;
    this.fieldErrors = {};
    this.filtersChange.emit(reset);
    this.resetFilters.emit();
  }

  onResetFilters(): void {
    this.doResetFilters();
  }

  hasError(fieldName: string): boolean {
    return !!this.fieldErrors[fieldName];
  }

  getError(fieldName: string): string {
    return this.fieldErrors[fieldName] || '';
  }
}
