/**
 * Stats routes for dashboard analytics.
 * Provides aggregated statistics with filtering support.
 */

import { Router, Request, Response } from "express";
import { PrismaClient } from "@prisma/client";

const router = Router();
const prisma = new PrismaClient();

/**
 * Build Prisma where clause from filter params.
 */
function buildGameWhereClause(params: {
  competition?: string;
  discipline?: string;
  season?: number;
  club?: string;
  player?: string;
  date_from?: string;
  date_to?: string;
  phase?: string;
}) {
  const where: any = {};

  if (params.competition) {
    where.competitionId = params.competition;
  }

  if (params.discipline) {
    where.competition = { disciplineId: params.discipline };
  }

  if (params.season) {
    where.competition = { ...where.competition, year: { year: params.season } };
  }

  if (params.phase) {
    where.phase = params.phase;
  }

  if (params.date_from || params.date_to) {
    where.startDate = {};
    if (params.date_from) where.startDate.gte = new Date(params.date_from);
    if (params.date_to) where.startDate.lte = new Date(params.date_to);
  }

  // Player and club filters need special handling (join through sidePlayers/PlayerClubHistory)
  return where;
}

/**
 * GET /stats/summary
 * Overall stats: total games, players, clubs, competitions, disciplines.
 */
router.get("/summary", async (request: Request, response: Response) => {
  try {
    const {
      competition,
      discipline,
      season,
      club,
      player,
      date_from,
      date_to,
      phase,
    } = request.query as Record<string, string | undefined>;

    const where = buildGameWhereClause({
      competition,
      discipline,
      season: season ? parseInt(season, 10) : undefined,
      phase,
      date_from,
      date_to,
    });

    // Total games
    const totalGames = await prisma.game.count({ where });

    // Get all games matching filters to extract player/club/competition/discipline counts
    const games = await prisma.game.findMany({
      where,
      select: {
        player1Id: true,
        player2Id: true,
        competitionId: true,
        sidePlayers: { select: { playerId: true } },
      },
    });

    const playerIds = new Set<string>();
    const competitionIds = new Set<string>();

    for (const game of games) {
      playerIds.add(game.player1Id);
      playerIds.add(game.player2Id);
      game.sidePlayers.forEach((sp) => playerIds.add(sp.playerId));
      competitionIds.add(game.competitionId);
    }

    // Get clubs from player club history
    let clubIds = new Set<string>();
    if (club) {
      clubIds = new Set([club]);
    } else if (playerIds.size > 0) {
      const playerClubs = await prisma.playerClubHistory.findMany({
        where: { playerId: { in: Array.from(playerIds) } },
        select: { clubId: true },
      });
      playerClubs.forEach((pc) => clubIds.add(pc.clubId));
    }

    // Get disciplines from competitions
    let disciplineIds = new Set<string>();
    if (discipline) {
      disciplineIds = new Set([discipline]);
    } else if (competitionIds.size > 0) {
      const comps = await prisma.competition.findMany({
        where: { id: { in: Array.from(competitionIds) } },
        select: { disciplineId: true },
      });
      comps.forEach((c) => disciplineIds.add(c.disciplineId));
    }

    response.json({
      total_games: totalGames,
      total_players: playerIds.size,
      total_clubs: clubIds.size,
      total_competitions: competitionIds.size,
      total_disciplines: disciplineIds.size,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to get summary stats", message });
  }
});

/**
 * Build player stats from games.
 */
function buildPlayerStatsFromGames(games: Array<{
  player1Id: string;
  player2Id: string;
  winnerId: string | null;
  sidePlayers: Array<{ playerId: string; side: number }>;
}>) {
  const map: Record<string, { games: number; wins: number }> = {};

  for (const game of games) {
    const side1 = new Set<string>([game.player1Id]);
    const side2 = new Set<string>([game.player2Id]);

    for (const sp of game.sidePlayers) {
      if (sp.side === 1) side1.add(sp.playerId);
      else if (sp.side === 2) side2.add(sp.playerId);
    }

    const participants = new Set<string>([...side1, ...side2]);
    const winningSide =
      game.winnerId === game.player1Id
        ? 1
        : game.winnerId === game.player2Id
          ? 2
          : null;

    const winners = winningSide === 1
      ? side1
      : winningSide === 2
        ? side2
        : new Set<string>();

    for (const pid of participants) {
      if (!map[pid]) map[pid] = { games: 0, wins: 0 };
      map[pid].games += 1;
      if (winners.has(pid)) map[pid].wins += 1;
    }
  }

  return map;
}

/**
 * GET /stats/players
 * Top players by wins and games count.
 */
router.get("/players", async (request: Request, response: Response) => {
  try {
    const {
      limit = "20",
      competition,
      discipline,
      season,
      club,
      player,
      date_from,
      date_to,
      phase,
    } = request.query as Record<string, string>;

    const take = Math.min(100, Math.max(1, parseInt(limit, 10) || 20));

    const where = buildGameWhereClause({
      competition,
      discipline,
      season: season ? parseInt(season, 10) : undefined,
      phase,
      date_from,
      date_to,
    });

    // If filtering by player, add to where clause
    if (player) {
      where.OR = [
        { player1Id: player },
        { player2Id: player },
        { sidePlayers: { some: { playerId: player } } },
      ];
    }

    // If filtering by club, need to filter games through player club history
    let gameIds: string[] | undefined;
    if (club) {
      const playerClubs = await prisma.playerClubHistory.findMany({
        where: { clubId: club },
        select: { playerId: true },
      });
      const playerIds = playerClubs.map((pc) => pc.playerId);

      const clubGames = await prisma.game.findMany({
        where: {
          OR: [
            { player1Id: { in: playerIds } },
            { player2Id: { in: playerIds } },
            { sidePlayers: { some: { playerId: { in: playerIds } } } },
          ],
        },
        select: { id: true },
      });
      gameIds = clubGames.map((g) => g.id);
    }

    const games = await prisma.game.findMany({
      where: gameIds ? { id: { in: gameIds }, ...where } : where,
      select: {
        player1Id: true,
        player2Id: true,
        winnerId: true,
        sidePlayers: { select: { playerId: true, side: true } },
      },
    });

    const statsMap = buildPlayerStatsFromGames(games);
    const playerIds = Object.keys(statsMap);

    const players = await prisma.player.findMany({
      where: { id: { in: playerIds } },
      select: {
        id: true,
        firstName: true,
        lastName: true,
        nickname: true,
      },
      orderBy: [{ lastName: "asc" }, { firstName: "asc" }],
    });

    const list = players.map((p) => {
      const s = statsMap[p.id] ?? { games: 0, wins: 0 };
      return {
        id: p.id,
        firstName: p.firstName,
        lastName: p.lastName,
        nickname: p.nickname,
        games_played: s.games,
        wins: s.wins,
        losses: s.games - s.wins,
      };
    });

    list.sort((a, b) => b.wins - a.wins || b.games_played - a.games_played);

    response.json({ players: list.slice(0, take) });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to get player stats", message });
  }
});

/**
 * GET /stats/clubs
 * Top clubs by games count and wins.
 */
router.get("/clubs", async (request: Request, response: Response) => {
  try {
    const {
      limit = "20",
      competition,
      discipline,
      season,
      club,
      player,
      date_from,
      date_to,
      phase,
    } = request.query as Record<string, string>;

    const take = Math.min(100, Math.max(1, parseInt(limit, 10) || 20));

    const where = buildGameWhereClause({
      competition,
      discipline,
      season: season ? parseInt(season, 10) : undefined,
      phase,
      date_from,
      date_to,
    });

    if (player) {
      where.OR = [
        { player1Id: player },
        { player2Id: player },
        { sidePlayers: { some: { playerId: player } } },
      ];
    }

    const games = await prisma.game.findMany({
      where,
      select: {
        id: true,
        player1Id: true,
        player2Id: true,
        winnerId: true,
        sidePlayers: { select: { playerId: true } },
      },
    });

    // Map club -> stats
    const clubStats: Record<string, { games: number; wins: number }> = {};

    for (const game of games) {
      const playerIds = [game.player1Id, game.player2Id, ...game.sidePlayers.map((sp) => sp.playerId)];

      const playerClubs = await prisma.playerClubHistory.findMany({
        where: { playerId: { in: playerIds } },
        select: { playerId: true, clubId: true },
      });

      const clubPlayers: Record<string, string[]> = {};
      for (const pc of playerClubs) {
        if (pc.clubId) {
          if (!clubPlayers[pc.clubId]) clubPlayers[pc.clubId] = [];
          clubPlayers[pc.clubId].push(pc.playerId);
        }
      }

      const winnerIds = game.winnerId ? [game.winnerId] : [];

      for (const [cid, pids] of Object.entries(clubPlayers)) {
        if (!clubStats[cid]) clubStats[cid] = { games: 0, wins: 0 };
        clubStats[cid].games += 1;

        if (winnerIds.some((wid) => pids.includes(wid))) {
          clubStats[cid].wins += 1;
        }
      }
    }

    const clubIds = Object.keys(clubStats);
    const clubs = await prisma.club.findMany({
      where: { id: { in: clubIds } },
      select: {
        id: true,
        name: true,
        shortName: true,
      },
    });

    const list = clubs.map((c) => {
      const s = clubStats[c.id] ?? { games: 0, wins: 0 };
      return {
        id: c.id,
        name: c.name,
        short_name: c.shortName,
        games_played: s.games,
        wins: s.wins,
      };
    });

    list.sort((a, b) => b.games_played - a.games_played || b.wins - a.wins);

    response.json({ clubs: list.slice(0, take) });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to get club stats", message });
  }
});

/**
 * GET /stats/competitions
 * Stats per competition.
 */
router.get("/competitions", async (request: Request, response: Response) => {
  try {
    const {
      competition,
      discipline,
      season,
      club,
      player,
      date_from,
      date_to,
      phase,
    } = request.query as Record<string, string>;

    const where = buildGameWhereClause({
      competition,
      discipline,
      season: season ? parseInt(season, 10) : undefined,
      phase,
      date_from,
      date_to,
    });

    if (player) {
      where.OR = [
        { player1Id: player },
        { player2Id: player },
        { sidePlayers: { some: { playerId: player } } },
      ];
    }

    const games = await prisma.game.groupBy({
      by: ["competitionId"],
      where,
      _count: { id: true },
    });

    const compIds = games.map((g) => g.competitionId);
    const competitions = await prisma.competition.findMany({
      where: { id: { in: compIds } },
      select: {
        id: true,
        seriesRelation: { select: { name: true } },
        disciplineRelation: { select: { name: true } },
        yearRelation: { select: { year: true } },
      },
    });

    const list = games.map((g) => {
      const comp = competitions.find((c) => c.id === g.competitionId);
      return {
        competition_id: g.competitionId,
        competition_name: comp
          ? `${comp.seriesRelation?.name || ""} ${comp.disciplineRelation?.name || ""} ${comp.yearRelation?.year || ""}`.trim()
          : g.competitionId,
        games_count: g._count.id,
      };
    });

    response.json({ competitions: list });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to get competition stats", message });
  }
});

/**
 * GET /stats/disciplines
 * Stats per discipline.
 */
router.get("/disciplines", async (request: Request, response: Response) => {
  try {
    const {
      competition,
      discipline,
      season,
      club,
      player,
      date_from,
      date_to,
      phase,
    } = request.query as Record<string, string>;

    const where = buildGameWhereClause({
      competition,
      discipline,
      season: season ? parseInt(season, 10) : undefined,
      phase,
      date_from,
      date_to,
    });

    if (player) {
      where.OR = [
        { player1Id: player },
        { player2Id: player },
        { sidePlayers: { some: { playerId: player } } },
      ];
    }

    const games = await prisma.game.findMany({
      where,
      select: {
        competition: {
          select: {
            disciplineId: true,
            disciplineRelation: { select: { name: true } },
          },
        },
      },
    });

    const discStats: Record<string, { name: string; count: number }> = {};

    for (const game of games) {
      const did = game.competition.disciplineId;
      const dname = game.competition.disciplineRelation?.name || "Unknown";
      if (!discStats[did]) discStats[did] = { name: dname, count: 0 };
      discStats[did].count += 1;
    }

    const list = Object.entries(discStats).map(([did, data]) => ({
      discipline_id: did,
      discipline_name: data.name,
      games_count: data.count,
    }));

    list.sort((a, b) => b.games_count - a.games_count);

    response.json({ disciplines: list });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to get discipline stats", message });
  }
});

/**
 * GET /stats/timeline
 * Games over time (monthly).
 */
router.get("/timeline", async (request: Request, response: Response) => {
  try {
    const {
      competition,
      discipline,
      season,
      club,
      player,
      date_from,
      date_to,
      phase,
    } = request.query as Record<string, string>;

    const where = buildGameWhereClause({
      competition,
      discipline,
      season: season ? parseInt(season, 10) : undefined,
      phase,
      date_from,
      date_to,
    });

    if (player) {
      where.OR = [
        { player1Id: player },
        { player2Id: player },
        { sidePlayers: { some: { playerId: player } } },
      ];
    }

    const games = await prisma.game.findMany({
      where,
      select: {
        startDate: true,
      },
    });

    const monthly: Record<string, number> = {};

    for (const game of games) {
      const monthKey = game.startDate.toISOString().slice(0, 7); // YYYY-MM
      monthly[monthKey] = (monthly[monthKey] || 0) + 1;
    }

    const list = Object.entries(monthly)
      .map(([month, count]) => ({ month, games_count: count }))
      .sort((a, b) => a.month.localeCompare(b.month));

    response.json({ timeline: list });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to get timeline stats", message });
  }
});

export const statsRouter = router;
