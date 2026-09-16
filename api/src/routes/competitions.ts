/**
 * Competition (championship) routes for the frontend.
 */

import { Router, Request, Response } from "express";
import { PrismaClient } from "@prisma/client";

const router = Router();
const prisma = new PrismaClient();

/**
 * GET /competitions
 * List competitions with pagination and optional filters.
 * 
 * New granular filters: discipline, season, year, series, group, pool, organization
 */
router.get("/", async (request: Request, response: Response) => {
  try {
    const {
      disciplineId,
      organizerId,
      status,
      year,
      // Enhanced championship filters
      discipline,
      season,
      series,
      group: groupFilter,
      pool,
      organization,
      limit = "50",
      offset = "0",
    } = request.query as Record<string, string | undefined>;

    const where: Record<string, unknown> = {};
    if (disciplineId) where.disciplineId = disciplineId;
    if (organizerId) where.organizerId = organizerId;
    if (status) where.status = status;
    if (year) {
      const yearNum = parseInt(year, 10);
      if (!Number.isNaN(yearNum)) {
        const yearRow = await prisma.competitionYear.findFirst({
          where: { year: yearNum },
          select: { id: true },
        });
        if (yearRow) where.yearId = yearRow.id;
      }
    }
    // Enhanced filters
    if (discipline) where.discipline = discipline;
    if (season) where.season = season;
    if (year && !where.yearId) {
      const yearNum = parseInt(year, 10);
      if (!Number.isNaN(yearNum)) {
        where.year = yearNum;
      }
    }
    if (series) where.series = series;
    if (groupFilter) where.group = groupFilter;
    if (pool) where.pool = pool;
    if (organization) where.organization = organization;

    const take = Math.min(100, Math.max(1, parseInt(limit, 10) || 50));
    const skip = Math.max(0, parseInt(offset, 10) || 0);

    const [competitions, total] = await Promise.all([
      prisma.competition.findMany({
        where,
        include: {
          organizerRelation: { select: { id: true, name: true, shortName: true } },
          disciplineRelation: { select: { id: true, name: true } },
          yearRelation: { select: { id: true, year: true, isCurrent: true } },
          seriesRelation: { select: { id: true, code: true, name: true } },
          _count: { select: { games: true } },
        },
        orderBy: [{ startDate: "desc" }],
        take,
        skip,
      }),
      prisma.competition.count({ where }),
    ]);

    response.json({
      competitions,
      total,
      limit: take,
      offset: skip,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to list competitions", message });
  }
});

/**
 * GET /competitions/:id
 * Single competition with recent games.
 */
router.get("/:id", async (request: Request, response: Response) => {
  const { id } = request.params;
  try {
    const competition = await prisma.competition.findUnique({
      where: { id },
      include: {
        organizerRelation: true,
        disciplineRelation: true,
        yearRelation: true,
        seriesRelation: true,
        ageCategory: { select: { id: true, name: true } },
        gender: { select: { id: true, name: true, code: true } },
        _count: { select: { games: true } },
      },
    });
    if (!competition) {
      response.status(404).json({ error: "Competition not found" });
      return;
    }

    const recentGames = await prisma.game.findMany({
      where: { competitionId: id },
      include: {
        player1: { select: { id: true, firstName: true, lastName: true, nickname: true } },
        player2: { select: { id: true, firstName: true, lastName: true, nickname: true } },
        winner: { select: { id: true } },
        gameScores: { select: { id: true, rawScore: true } },
        sidePlayers: {
          select: {
            side: true,
            displayOrder: true,
            player: { select: { id: true, firstName: true, lastName: true, nickname: true } },
          },
          orderBy: [{ side: "asc" }, { displayOrder: "asc" }],
        },
      },
      orderBy: { startDate: "desc" },
      take: 20,
    });

    // Map relation names for backward compatibility
    const competitionResponse = {
      ...competition,
      organizer: competition.organizerRelation,
      discipline: competition.disciplineRelation,
      year: competition.yearRelation,
      series: competition.seriesRelation,
      recentGames,
    };
    
    response.json(competitionResponse);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to get competition", message });
  }
});

/**
 * GET /competitions/filters
 * Get distinct filter options for dropdown population.
 * Returns available values for: discipline, season, year, series, group, pool, organization
 */
router.get("/filters", async (_request: Request, response: Response) => {
  try {
    const [
      disciplines,
      seasons,
      years,
      series,
      groups,
      pools,
      organizations,
    ] = await Promise.all([
      prisma.competition.findMany({
        where: { discipline: { not: null } },
        select: { discipline: true },
        distinct: ["discipline"],
      }),
      prisma.competition.findMany({
        where: { season: { not: null } },
        select: { season: true },
        distinct: ["season"],
      }),
      prisma.competition.findMany({
        where: { year: { not: null } },
        select: { year: true },
        distinct: ["year"],
        orderBy: [{ year: "desc" }],
      }),
      prisma.competition.findMany({
        where: { series: { not: null } },
        select: { series: true },
        distinct: ["series"],
      }),
      prisma.competition.findMany({
        where: { group: { not: null } },
        select: { group: true },
        distinct: ["group"],
      }),
      prisma.competition.findMany({
        where: { pool: { not: null } },
        select: { pool: true },
        distinct: ["pool"],
      }),
      prisma.competition.findMany({
        where: { organization: { not: null } },
        select: { organization: true },
        distinct: ["organization"],
      }),
    ]);

    response.json({
      filters: {
        discipline: disciplines
          .map((c) => c.discipline)
          .filter(Boolean)
          .map((d) => ({ value: d, label: d })),
        season: seasons
          .map((c) => c.season)
          .filter(Boolean)
          .map((s) => ({ value: s, label: s })),
        year: years
          .map((c) => c.year)
          .filter(Boolean)
          .map((y) => ({ value: String(y), label: String(y) })),
        series: series
          .map((c) => c.series)
          .filter(Boolean)
          .map((s) => ({ value: s, label: s })),
        group: groups
          .map((c) => c.group)
          .filter(Boolean)
          .map((g) => ({ value: g, label: g })),
        pool: pools
          .map((c) => c.pool)
          .filter(Boolean)
          .map((p) => ({ value: p, label: p })),
        organization: organizations
          .map((c) => c.organization)
          .filter(Boolean)
          .map((o) => ({ value: o, label: o })),
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to get filter options", message });
  }
});

export const competitionsRouter = router;
