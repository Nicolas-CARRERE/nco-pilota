import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { PlayersService } from '../../../core/services/players.service';
import { PlayerStatsListItem } from '../../../shared/models/player.model';
import { LoadingComponent } from '../../../shared/components/loading/loading.component';
import { FilterComponent, FilterConfig } from '../../../shared/components/filter/filter.component';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-player-list',
  standalone: true,
  imports: [RouterLink, LoadingComponent, FilterComponent],
  templateUrl: './player-list.component.html',
  styleUrl: './player-list.component.scss',
})
export class PlayerListComponent implements OnInit {
  players: PlayerStatsListItem[] = [];
  total = 0;
  loading = true;
  error: string | null = null;
  filters: Record<string, any> = {};
  filterConfig: FilterConfig = { showSeason: true, compact: true };
  searchQuery = '';
  offset = 0;
  limit = 20;
  sortBy: string = 'name';
  sortDir: string = 'asc';

  constructor(
    private playersService: PlayersService,
    private toastService: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadPlayers();
  }

  applyFilters(newFilters: Record<string, any>): void {
    this.filters = { ...this.filters, ...newFilters };
    this.offset = 0;
    this.loadPlayers();
  }

  onResetFilters(): void {
    this.filters = {};
    this.searchQuery = '';
    this.toastService.info('Filtres réinitialisés');
    this.offset = 0;
    this.loadPlayers();
  }

  onSearchChange(query: string): void {
    this.searchQuery = query;
    this.offset = 0;
    this.loadPlayers();
  }

  onSortChange(sortBy: string): void {
    if (this.sortBy === sortBy) {
      this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortBy = sortBy;
      this.sortDir = 'asc';
    }
    this.loadPlayers();
  }

  pagePrev(): void {
    if (this.offset > 0) {
      this.offset -= this.limit;
      this.loadPlayers();
    }
  }

  pageNext(): void {
    this.offset += this.limit;
    this.loadPlayers();
  }

  loadPlayers(): void {
    this.loading = true;
    const params: any = { 
      limit: this.limit,
      offset: this.offset,
      sortBy: this.sortBy,
      sortDir: this.sortDir,
    };
    if (this.searchQuery.trim()) {
      params.search = this.searchQuery.trim();
    }
    this.playersService.getList(params).subscribe({
      next: (res) => {
        this.players = res.players ?? [];
        this.total = (res as any).total ?? this.players.length;
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.message ?? 'Erreur lors du chargement';
        this.loading = false;
      },
    });
  }

  displayName(p: PlayerStatsListItem): string {
    return p.nickname?.trim() ? p.nickname : `${p.firstName} ${p.lastName}`;
  }
}
