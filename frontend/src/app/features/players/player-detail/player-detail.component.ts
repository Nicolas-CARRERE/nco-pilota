import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { PlayersService } from '../../../core/services/players.service';
import { PlayerDetail, PlayerDetailGame } from '../../../shared/models/player.model';
import { FormatDatePipe } from '../../../shared/pipes/format-date.pipe';
import { LoadingComponent } from '../../../shared/components/loading/loading.component';
import { BreadcrumbComponent, BreadcrumbItem } from '../../../shared/components/breadcrumb/breadcrumb.component';

@Component({
  selector: 'app-player-detail',
  standalone: true,
  imports: [RouterLink, FormatDatePipe, LoadingComponent, BreadcrumbComponent],
  templateUrl: './player-detail.component.html',
  styleUrl: './player-detail.component.scss',
})
export class PlayerDetailComponent implements OnInit {
  player: PlayerDetail | null = null;
  loading = true;
  error: string | null = null;
  breadcrumbs: BreadcrumbItem[] = [
    { label: 'Accueil', link: '/' },
    { label: 'Joueurs', link: '/players' },
  ];

  constructor(
    private route: ActivatedRoute,
    private playersService: PlayersService,
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;
    this.playersService.getById(id).subscribe({
      next: (p) => {
        this.player = p;
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.message ?? 'Joueur introuvable';
        this.loading = false;
      },
    });
  }

  displayName(firstName: string, lastName: string, nickname?: string | null): string {
    return nickname?.trim() ? nickname : `${firstName} ${lastName}`;
  }

  recentGames(): PlayerDetailGame[] {
    if (!this.player?.recentGames) return [];
    return this.player.recentGames;
  }

  opponentsDisplay(g: PlayerDetailGame): string {
    if (g.opponentsLabel != null && g.opponentsLabel !== '') return g.opponentsLabel;
    const p1 = g.player1;
    const p2 = g.player2;
    if (p1 && p2) return `${p1.firstName} ${p1.lastName} – ${p2.firstName} ${p2.lastName}`;
    return '–';
  }

  scoreDisplay(scores: Array<{ rawScore: string }>): string {
    if (!scores?.length) return '–';
    return scores.map((s) => s.rawScore).join(', ');
  }
}
