export interface PlayerStatsListItem {
  id: string;
  firstName: string;
  lastName: string;
  nickname?: string | null;
  gamesPlayed: number;
  wins: number;
  losses: number;
}

export interface PlayersListResponse {
  players: PlayerStatsListItem[];
  total?: number;
}

export interface PlayerDetailGame {
  id: string;
  startDate: string;
  phase?: string | null;
  competition?: { id: string; phase?: string | null } | null;
  player1?: { firstName: string; lastName: string };
  player2?: { firstName: string; lastName: string };
  gameScores: Array<{ rawScore: string }>;
  /** True if the current player's side won (from API). */
  won?: boolean;
  /** Opponents display label, e.g. "A – B" for the other side (from API). */
  opponentsLabel?: string;
}

export interface PlayerDetail extends PlayerStatsListItem {
  /** Recent games for this player (includes participation via sidePlayers). From API. */
  recentGames?: PlayerDetailGame[];
}
