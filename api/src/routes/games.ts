/**
 * Game and match routes for the frontend.
 */

import { Router, Request, Response } from "express";
import { PrismaClient } from "@prisma/client";

const router = Router();
const prisma = new PrismaClient();

/**
 * GET /games
 * List games with optional filters (sourceId, status, dateFrom, dateTo, competitionId, playerId, limit, offset).
 */
router.get("/", async (request: Request, response: Response) => {
  try {
    const {
      sourceId,
      status,
      dateFrom,
      dateTo,
      competitionId,
      playerId,
      phase,
      limit = "50",
      offset = "0",
    } = request.query as Record<string, string | undefined>;

    const where: Record<string, unknown> = {};
    if (sourceId) where.sourceId = sourceId;
    if (status) where.status = status;
    if (competitionId) where.competitionId = competitionId;
    if (phase) where.phase = phase;
    if (playerId) {
      where.OR = [
        { player1Id: playerId },
        { player2Id: playerId },
        { sidePlayers: { some: { playerId } } },
      ];
    }
    if (dateFrom || dateTo) {
      where.startDate = {};
      if (dateFrom) (where.startDate as Record<string, Date>).gte = new Date(dateFrom);
      if (dateTo) (where.startDate as Record<string, Date>).lte = new Date(dateTo);
    }

    const take = Math.min(100, Math.max(1, parseInt(limit, 10) || 50));
    const skip = Math.max(0, parseInt(offset, 10) || 0);

    const [games, total] = await Promise.all([
      prisma.game.findMany({
        where,
        include: {
          player1: { select: { id: true, firstName: true, lastName: true, nickname: true, license: true } },
          player2: { select: { id: true, firstName: true, lastName: true, nickname: true, license: true } },
          winner: { select: { id: true, firstName: true, lastName: true, license: true } },
          competition: { select: { id: true, status: true, phase: true } },
          gameScores: { select: { id: true, rawScore: true } },
          sidePlayers: {
            select: {
              side: true,
              displayOrder: true,
              playerId: true,
              player: { select: { id: true, firstName: true, lastName: true, nickname: true, license: true } },
            },
            orderBy: [{ side: "asc" }, { displayOrder: "asc" }],
          },
        },
        orderBy: { startDate: "desc" },
        take,
        skip,
      }),
      prisma.game.count({ where }),
    ]);

    response.json({
      games,
      total,
      limit: take,
      offset: skip,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to list games", message });
  }
});

/**
 * GET /games/next
 * Upcoming or in-progress matches (startDate >= today, status scheduled or in_progress).
 */
router.get("/next", async (_request: Request, response: Response) => {
  try {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const games = await prisma.game.findMany({
      where: {
        startDate: { gte: today },
        status: { in: ["scheduled", "in_progress"] },
      },
      include: {
        player1: { select: { id: true, firstName: true, lastName: true, license: true } },
        player2: { select: { id: true, firstName: true, lastName: true, license: true } },
        competition: { select: { id: true, phase: true } },
        court: { select: { id: true, name: true, city: true } },
        sidePlayers: {
          select: {
            side: true,
            displayOrder: true,
            player: { select: { id: true, firstName: true, lastName: true, license: true } },
          },
          orderBy: [{ side: "asc" }, { displayOrder: "asc" }],
        },
      },
      orderBy: { startDate: "asc" },
      take: 50,
    });

    response.json({ games });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to get next matches", message });
  }
});

/**
 * GET /games/filter-options
 * Returns filter options derived from data: distinct phases from Game.phase.
 * Used by the frontend to show only relevant filters (e.g. hide phase when 0–1 option).
 */
router.get("/filter-options", async (_request: Request, response: Response) => {
  try {
    const phases = await prisma.game.findMany({
      where: { phase: { not: null } },
      select: { phase: true },
      distinct: ["phase"],
      orderBy: { phase: "asc" },
    });
    const phaseOptions = phases
      .map((p) => p.phase as string)
      .filter(Boolean)
      .map((value) => ({ value, label: value }));
    response.json({ phases: phaseOptions });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to get filter options", message });
  }
});

/**
 * GET /games/:id
 * Single game by id.
 */
router.get("/:id", async (request: Request, response: Response) => {
  const { id } = request.params;
  try {
    const game = await prisma.game.findUnique({
      where: { id },
      include: {
        player1: true,
        player2: true,
        winner: true,
        competition: { include: { organizerRelation: true, disciplineRelation: true } },
        court: true,
        gameScores: true,
        sidePlayers: {
          include: { player: true },
          orderBy: [{ side: "asc" }, { displayOrder: "asc" }],
        },
      },
    });
    if (!game) {
      response.status(404).json({ error: "Game not found" });
      return;
    }
    response.json(game);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    response.status(500).json({ error: "Failed to get game", message });
  }
});

export const gamesRouter = router;
