import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { GamesService } from '../../../core/services/games.service';
import { GameDetail } from '../../../shared/models/game.model';
import { formatGameSides, playerDisplayName } from '../../../shared/utils/game-format';
import { FormatDatePipe } from '../../../shared/pipes/format-date.pipe';
import { LoadingComponent } from '../../../shared/components/loading/loading.component';
import { BreadcrumbComponent, BreadcrumbItem } from '../../../shared/components/breadcrumb/breadcrumb.component';

@Component({
  selector: 'app-game-detail',
  standalone: true,
  imports: [RouterLink, FormatDatePipe, LoadingComponent, BreadcrumbComponent],
  templateUrl: './game-detail.component.html',
  styleUrl: './game-detail.component.scss',
})
export class GameDetailComponent implements OnInit {
  game: GameDetail | null = null;
  loading = true;
  error: string | null = null;
  breadcrumbs: BreadcrumbItem[] = [
    { label: 'Accueil', link: '/' },
    { label: 'Résultats', link: '/games' },
  ];

  constructor(
    private route: ActivatedRoute,
    private gamesService: GamesService,
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;
    this.gamesService.getById(id).subscribe({
      next: (g) => {
        this.game = g;
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.message ?? 'Partie introuvable';
        this.loading = false;
      },
    });
  }

  gameSides(game: GameDetail): { side1: string; side2: string } {
    return formatGameSides(game);
  }

  playerName(p: { firstName: string; lastName: string; nickname?: string | null }): string {
    return playerDisplayName(p);
  }
}
