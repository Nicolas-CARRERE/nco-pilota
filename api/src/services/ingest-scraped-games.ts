/**
 * Ingest scraped games from pipeline raw_content into Prisma (Game, GameScore, Player, Club, etc.).
 * Sets scoreComplete and scrapedFromUrl for rescan tracing.
 */

import { PrismaClient } from "@prisma/client";
import { parseChampionshipName } from "../utils/championship-parser.js";

const prisma = new PrismaClient();

/** CTPB game row shape from backend (raw_content.games[]) */
export type CtpbGameRow = {
  no_renc: string;
  date: string;
  club1_name: string;
  club2_name: string;
  club1_players: Array<{ id: string; name: string }>;
  club2_players: Array<{ id: string; name: string }>;
  raw_score: string;
  comment?: string;
  status: string;
  discipline_context?: string;
  phase?: string;
};

const GAME_SCORE_RAW_MAX_LENGTH = 50; // Prisma GameScore.rawScore is VarChar(50)

/** X/P or P/X (X = number, P = perdant) are final scores and must not be rescanned. */
const SCORE_X_P = /^\s*\d+\s*\/\s*P\s*$/i;
const SCORE_P_X = /^\s*P\s*\/\s*\d+\s*$/i;

function isScoreComplete(status: string, rawScore: string): boolean {
  const s = (rawScore || "").trim();
  if (SCORE_X_P.test(s) || SCORE_P_X.test(s)) return true;
  if (status !== "completed") return false;
  return /^\d+\/\d+$/.test(s);
}

/**
 * Derive winner from CTPB-style raw score "P1/P2" (e.g. "40/20", "40/P", "P/30").
 * X/P or P/X: P = perdant, number = gagnant (X can be 30 or 40 depending on discipline).
 * Returns 1 if player1 wins, 2 if player2 wins, null if tie or invalid format.
 */
export function getWinnerFromRawScore(rawScore: string): 1 | 2 | null {
  const s = (rawScore || "").trim();
  if (SCORE_X_P.test(s)) return 1;
  if (SCORE_P_X.test(s)) return 2;
  const match = s.match(/^\s*(\d+)\s*\/\s*(\d+)\s*$/);
  if (!match) return null;
  const p1 = parseInt(match[1], 10);
  const p2 = parseInt(match[2], 10);
  if (p1 > p2) return 1;
  if (p2 > p1) return 2;
  return null;
}

/** Normalize raw_score for DB: string, max 50 chars. */
function normalizeRawScore(raw: unknown): string {
  const s = typeof raw === "string" ? raw : String(raw ?? "").trim();
  return s.length > GAME_SCORE_RAW_MAX_LENGTH ? s.slice(0, GAME_SCORE_RAW_MAX_LENGTH) : s;
}

function parseDate(dateStr: string): Date {
  const s = (dateStr || "").trim();
  const match = s.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (match) {
    const [, d, m, y] = match;
    return new Date(Number(y), Number(m) - 1, Number(d));
  }
  return new Date();
}

async function ensureOrganizer(name: string): Promise<string> {
  const existing = await prisma.organizer.findFirst({
    where: { name },
    select: { id: true },
  });
  if (existing) return existing.id;
  const created = await prisma.organizer.create({
    data: { name, type: "committee" },
    select: { id: true },
  });
  return created.id;
}

async function ensureModality(name: string): Promise<string> {
  const existing = await prisma.modality.findFirst({
    where: { name },
    select: { id: true },
  });
  if (existing) return existing.id;
  const created = await prisma.modality.create({
    data: { name },
    select: { id: true },
  });
  return created.id;
}

async function ensureDiscipline(modalityId: string, name: string): Promise<string> {
  const existing = await prisma.discipline.findFirst({
    where: { name, modalityId },
    select: { id: true },
  });
  if (existing) return existing.id;
  const created = await prisma.discipline.create({
    data: { name, modalityId },
    select: { id: true },
  });
  return created.id;
}

async function ensureCompetitionYear(year: number): Promise<string> {
  const existing = await prisma.competitionYear.findFirst({
    where: { year },
    select: { id: true },
  });
  if (existing) return existing.id;
  const created = await prisma.competitionYear.create({
    data: { year, isCurrent: year === new Date().getFullYear() },
    select: { id: true },
  });
  return created.id;
}

async function ensureCompetition(
  organizerId: string,
  disciplineId: string,
  yearId: string,
  startDate: Date,
  championshipName?: string,
): Promise<string> {
  const existing = await prisma.competition.findFirst({
    where: { organizerId, yearId, disciplineId },
    select: { id: true },
  });
  if (existing) return existing.id;
  
  // Parse championship name to extract granular fields
  const parsed = championshipName ? parseChampionshipName(championshipName) : {};
  
  const created = await prisma.competition.create({
    data: {
      organizerId,
      disciplineId,
      yearId,
      startDate,
      endDate: startDate,
      status: "ongoing",
      discipline: parsed.discipline || undefined,
      season: parsed.season || undefined,
      year: parsed.year || undefined,
      series: parsed.series || undefined,
      group: parsed.group || undefined,
      pool: parsed.pool || undefined,
      organization: parsed.organization || undefined,
    },
    select: { id: true },
  });
  return created.id;
}

async function ensureClub(name: string): Promise<string> {
  const n = (name || "").trim();
  if (!n) {
    const placeholder = await prisma.club.findFirst({
      where: { name: "Inconnu" },
      select: { id: true },
    });
    if (placeholder) return placeholder.id;
    const created = await prisma.club.create({
      data: { name: "Inconnu" },
      select: { id: true },
    });
    return created.id;
  }
  const existing = await prisma.club.findFirst({
    where: { name: n },
    select: { id: true },
  });
  if (existing) return existing.id;
  const created = await prisma.club.create({
    data: { name: n },
    select: { id: true },
  });
  return created.id;
}

async function ensureTeam(clubId: string, disciplineId: string, name: string): Promise<string> {
  const existing = await prisma.team.findFirst({
    where: { clubId, disciplineId },
    select: { id: true },
  });
  if (existing) return existing.id;
  const teamName = (name || "").trim() || "Équipe";
  const created = await prisma.team.create({
    data: { clubId, disciplineId, name: teamName },
    select: { id: true },
  });
  return created.id;
}

async function ensurePlayerClubHistory(
  playerId: string,
  clubId: string,
  joinedDate: Date,
): Promise<void> {
  const existing = await prisma.playerClubHistory.findFirst({
    where: { playerId, clubId },
    select: { id: true, joinedDate: true },
  });
  if (existing) {
    const existingDate = new Date(existing.joinedDate);
    if (joinedDate < existingDate) {
      await prisma.playerClubHistory.update({
        where: { id: existing.id },
        data: { joinedDate },
      });
    }
    return;
  }
  await prisma.playerClubHistory.create({
    data: { playerId, clubId, joinedDate },
  });
}

async function ensureTeamPlayer(teamId: string, playerId: string): Promise<void> {
  await prisma.teamPlayer.upsert({
    where: {
      teamId_playerId: { teamId, playerId },
    },
    create: { teamId, playerId },
    update: {},
  });
}

/** When true, treat as license number only (store in nickname), not as display name. */
function isLicenseOnly(name: string): boolean {
  return /^\d+$/.test((name || "").trim());
}

/** Display name for parsing: use "Joueur <license>" when name is empty or only digits. */
function playerDisplayName(name: string, id: string): string {
  const n = (name || "").trim();
  if (!n || isLicenseOnly(n)) return id ? `Joueur ${id}` : "Joueur";
  return n;
}

/**
 * Parse full name from scrapers. CTPB (and similar) use "NOM Prénom" (family name first).
 * We store firstName = given name, lastName = family name for consistent display and sorting.
 */
function parsePlayerName(fullName: string): { firstName: string; lastName: string } {
  const raw = (fullName || "").trim();
  if (!raw) return { firstName: "Inconnu", lastName: "" };
  if (isLicenseOnly(raw)) return { firstName: "Joueur", lastName: raw };
  const parts = raw.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return { firstName: parts[0], lastName: "" };
  // Source format is "NOM Prénom" → store as firstName=prénom, lastName=nom
  return {
    firstName: parts.slice(1).join(" "),
    lastName: parts[0],
  };
}

const PLAYER_LICENSE_MAX_LENGTH = 32;

async function ensurePlayer(
  firstName: string,
  lastName: string,
  externalId?: string,
  license?: string,
): Promise<string> {
  const licenseNorm =
    license != null && license.length > PLAYER_LICENSE_MAX_LENGTH
      ? license.slice(0, PLAYER_LICENSE_MAX_LENGTH)
      : license ?? undefined;

  if (licenseNorm) {
    const byLicense = await prisma.player.findFirst({
      where: { license: licenseNorm },
      select: { id: true },
    });
    if (byLicense) return byLicense.id;
  }
  if (externalId) {
    const byNickname = await prisma.player.findFirst({
      where: { nickname: externalId },
      select: { id: true },
    });
    if (byNickname) return byNickname.id;
  }
  const byName = await prisma.player.findFirst({
    where: { firstName, lastName },
    select: { id: true },
  });
  if (byName) return byName.id;
  const created = await prisma.player.create({
    data: {
      firstName: firstName || "Inconnu",
      lastName: lastName || "",
      nickname: externalId ?? undefined,
      license: licenseNorm,
    },
    select: { id: true },
  });
  return created.id;
}

/**
 * Ensure default competition for a source (organizer + discipline + year + competition).
 * Returns competitionId and disciplineId for use when ensuring teams.
 * @param disciplineName - Optional discipline name (e.g. "Trinquet", "Mur à gauche"). Defaults to "Mur à gauche".
 * @param championshipName - Optional full championship name for granular field parsing.
 */
export async function ensureDefaultCompetition(
  sourceId: string,
  disciplineName?: string,
  championshipName?: string,
): Promise<{ competitionId: string; disciplineId: string }> {
  const source = await prisma.source.findUnique({
    where: { id: sourceId },
    select: { name: true },
  });
  if (!source) throw new Error(`Source not found: ${sourceId}`);
  const organizerId = await ensureOrganizer(source.name);
  const modalityId = await ensureModality("Pelote basque");
  const resolvedDiscipline = (disciplineName ?? "Mur à gauche").trim() || "Mur à gauche";
  const disciplineId = await ensureDiscipline(modalityId, resolvedDiscipline);
  const year = new Date().getFullYear();
  const yearId = await ensureCompetitionYear(year);
  const startDate = new Date(year, 0, 1);
  const competitionId = await ensureCompetition(organizerId, disciplineId, yearId, startDate, championshipName);
  return { competitionId, disciplineId };
}

/**
 * Ingest CTPB games from raw_content into Game, GameScore, Club, Player.
 * Uses sourceId and scrapedFromUrl for tracing; sets scoreComplete from status + raw_score.
 */
export async function ingestCtpbGames(
  sourceId: string,
  scrapedFromUrl: string,
  games: CtpbGameRow[],
): Promise<{ created: number; updated: number }> {
  const disciplineName =
    (games[0]?.discipline_context ?? "").trim() || "Mur à gauche";
  const { competitionId, disciplineId } = await ensureDefaultCompetition(
    sourceId,
    disciplineName,
  );
  let created = 0;
  let updated = 0;

  for (const row of games) {
    const externalId = row.no_renc;
    const existing = await prisma.game.findFirst({
      where: { sourceId, externalId },
      select: { id: true },
    });

    const club1Id = await ensureClub(row.club1_name);
    const club2Id = await ensureClub(row.club2_name);
    const MAX_PLAYERS_PER_SIDE = 5;
    const p1ListRaw = row.club1_players?.length ? row.club1_players : [{ id: "", name: row.club1_name }];
    const p2ListRaw = row.club2_players?.length ? row.club2_players : [{ id: "", name: row.club2_name }];
    const p1List = p1ListRaw.slice(0, MAX_PLAYERS_PER_SIDE);
    const p2List = p2ListRaw.slice(0, MAX_PLAYERS_PER_SIDE);
    const { firstName: f1, lastName: l1 } = parsePlayerName(playerDisplayName(p1List[0].name, p1List[0].id));
    const { firstName: f2, lastName: l2 } = parsePlayerName(playerDisplayName(p2List[0].name, p2List[0].id));
    const player1Id = await ensurePlayer(f1, l1, p1List[0].id || undefined, p1List[0].id || undefined);
    const player2Id = await ensurePlayer(f2, l2, p2List[0].id || undefined, p2List[0].id || undefined);
    const side1PlayerIds: string[] = [];
    for (let i = 0; i < p1List.length; i++) {
      const { firstName, lastName } = parsePlayerName(playerDisplayName(p1List[i].name, p1List[i].id));
      side1PlayerIds.push(
        await ensurePlayer(firstName, lastName, p1List[i].id || undefined, p1List[i].id || undefined),
      );
    }
    const side2PlayerIds: string[] = [];
    for (let i = 0; i < p2List.length; i++) {
      const { firstName, lastName } = parsePlayerName(playerDisplayName(p2List[i].name, p2List[i].id));
      side2PlayerIds.push(
        await ensurePlayer(firstName, lastName, p2List[i].id || undefined, p2List[i].id || undefined),
      );
    }
    const startDate = parseDate(row.date);
    const scoreComplete = isScoreComplete(row.status, row.raw_score);
    const winnerSide = scoreComplete ? getWinnerFromRawScore(row.raw_score) : null;
    const winnerId =
      winnerSide === 1 ? player1Id : winnerSide === 2 ? player2Id : undefined;
    const gameStatus =
      row.status === "completed"
        ? "completed"
        : row.status === "forfait"
          ? "completed"
          : "scheduled";

    const team1Id = await ensureTeam(club1Id, disciplineId, row.club1_name);
    const team2Id = await ensureTeam(club2Id, disciplineId, row.club2_name);
    for (const pid of side1PlayerIds) {
      await ensurePlayerClubHistory(pid, club1Id, startDate);
      await ensureTeamPlayer(team1Id, pid);
    }
    for (const pid of side2PlayerIds) {
      await ensurePlayerClubHistory(pid, club2Id, startDate);
      await ensureTeamPlayer(team2Id, pid);
    }

    const upsertSidePlayers = async (gameId: string) => {
      await prisma.gameSidePlayer.deleteMany({ where: { gameId } });
      const sidePlayerRows: Array<{ gameId: string; playerId: string; side: number; displayOrder: number }> = [];
      side1PlayerIds.forEach((pid, i) => {
        sidePlayerRows.push({ gameId, playerId: pid, side: 1, displayOrder: i + 1 });
      });
      side2PlayerIds.forEach((pid, i) => {
        sidePlayerRows.push({ gameId, playerId: pid, side: 2, displayOrder: i + 1 });
      });
      if (sidePlayerRows.length > 0) {
        await prisma.gameSidePlayer.createMany({ data: sidePlayerRows });
      }
    };

    const phaseValue = (row.phase ?? "").trim() || undefined;

    if (existing) {
      await prisma.game.update({
        where: { id: existing.id },
        data: {
          status: gameStatus,
          scrapedFromUrl,
          scoreComplete,
          winnerId,
          notes: row.comment ?? undefined,
          ...(phaseValue !== undefined ? { phase: phaseValue } : {}),
        },
      });
      const scoreRecord = await prisma.gameScore.findFirst({
        where: { gameId: existing.id },
        select: { id: true },
      });
      if (scoreRecord) {
        await prisma.gameScore.update({
          where: { id: scoreRecord.id },
          data: { rawScore: normalizeRawScore(row.raw_score) },
        });
      } else {
        await prisma.gameScore.create({
          data: { gameId: existing.id, rawScore: normalizeRawScore(row.raw_score) },
        });
      }
      await upsertSidePlayers(existing.id);
      updated += 1;
    } else {
      const game = await prisma.game.create({
        data: {
          competitionId,
          player1Id,
          player2Id,
          startDate,
          status: gameStatus,
          sourceId,
          externalId,
          scrapedFromUrl,
          scoreComplete,
          winnerId,
          notes: row.comment ?? undefined,
          phase: phaseValue,
        },
        select: { id: true },
      });
      await prisma.gameScore.create({
        data: { gameId: game.id, rawScore: normalizeRawScore(row.raw_score) },
      });
      await upsertSidePlayers(game.id);
      created += 1;
    }
  }

  return { created, updated };
}

/**
 * Ingest from pipeline result: parse raw_content and call ingestCtpbGames if source is CTPB.
 */
export async function ingestFromPipelineResult(
  sourceId: string,
  url: string,
  rawContent: Record<string, unknown>,
): Promise<{ created: number; updated: number }> {
  const games = rawContent.games as CtpbGameRow[] | undefined;
  if (!Array.isArray(games) || games.length === 0) {
    return { created: 0, updated: 0 };
  }
  if (url.includes("ctpb.euskalpilota.fr/resultats.php")) {
    return ingestCtpbGames(sourceId, url, games);
  }
  return { created: 0, updated: 0 };
}
