/**
 * Scrape controller - handles scraping and ingestion logic.
 */

import { Request, Response } from "express";
import axios from "axios";

const FASTAPI_SCRAPER_SERVICE_URL =
  process.env.PELOTA_FASTAPI_SCRAPER_SERVICE_URL ?? "http://localhost:8001";

const SCRAPER_REQUEST_TIMEOUT_MS = 600_000; // 10 minutes

/**
 * Trigger scrape and ingest results into database.
 * POST /api/scrape/ingest
 */
export async function ingestScrapedData(
  request: Request,
  response: Response,
): Promise<void> {
  const { url, sourceId } = request.body as {
    url?: string;
    sourceId?: string;
  };

  if (!url || typeof url !== "string") {
    response.status(400).json({ error: "url is required" });
    return;
  }

  try {
    // Step 1: Call Python scraper service
    const scrapeResponse = await axios.post(
      `${FASTAPI_SCRAPER_SERVICE_URL}/scrape/run`,
      { url, source_id: sourceId },
      {
        timeout: SCRAPER_REQUEST_TIMEOUT_MS,
        headers: { "Content-Type": "application/json" },
        validateStatus: () => true,
      },
    );

    if (scrapeResponse.status !== 200) {
      response.status(502).json({
        error: "Scraping failed",
        status: scrapeResponse.status,
        data: scrapeResponse.data,
      });
      return;
    }

    const scrapeResult = scrapeResponse.data as {
      status: string;
      raw_content?: Record<string, unknown>;
      total_items?: number;
      errors?: Array<{ url: string; code: string; message: string }>;
    };

    if (scrapeResult.status !== "success" || !scrapeResult.raw_content) {
      response.status(500).json({
        error: "Scraping returned no data",
        status: scrapeResult.status,
        errors: scrapeResult.errors,
      });
      return;
    }

    // Step 2: Extract games from raw_content
    const games = scrapeResult.raw_content.games as Array<Record<string, unknown>>;
    if (!Array.isArray(games) || games.length === 0) {
      response.status(200).json({
        status: "success",
        message: "No games to ingest",
        competitions: 0,
        games: 0,
      });
      return;
    }

    // Step 3: Call ingestion service (Python backend with DB access)
    // For now, we use the Node.js ingestion service directly
    // In a future iteration, this could call a Python ingestion endpoint
    const { ingestFromPipelineResult } = await import(
      "../services/ingest-scraped-games.js"
    );

    const resolvedSourceId =
      sourceId || (await getOrCreateCtpbSource());

    const ingestResult = await ingestFromPipelineResult(
      resolvedSourceId,
      url,
      scrapeResult.raw_content,
    );

    response.status(200).json({
      status: "success",
      message: "Data ingested successfully",
      competitions: ingestResult.created, // Approximation - actual competition count would need separate tracking
      games: ingestResult.created + ingestResult.updated,
      details: {
        gamesCreated: ingestResult.created,
        gamesUpdated: ingestResult.updated,
      },
    });
  } catch (error) {
    console.error("Ingest scrape error:", error);
    response.status(500).json({
      error: "Failed to ingest scraped data",
      message: error instanceof Error ? error.message : "Unknown error",
    });
  }
}

/**
 * Get or create CTPB source record.
 */
async function getOrCreateCtpbSource(): Promise<string> {
  const { PrismaClient } = await import("@prisma/client");
  const prisma = new PrismaClient();

  try {
    let source = await prisma.source.findFirst({
      where: { url: { contains: "ctpb.euskalpilota.fr" } },
      select: { id: true },
    });

    if (!source) {
      source = await prisma.source.create({
        data: {
          name: "CTPB",
          url: "https://ctpb.euskalpilota.fr",
          isActive: true,
        },
        select: { id: true },
      });
    }

    return source.id;
  } finally {
    await prisma.$disconnect();
  }
}

/**
 * Batch ingest from pipeline results.
 * POST /api/scrape/ingest/batch
 */
export async function ingestBatchScrapedData(
  request: Request,
  response: Response,
): Promise<void> {
  const { results, sourceId } = request.body as {
    results?: Array<{
      url: string;
      raw_content?: Record<string, unknown>;
      status?: string;
    }>;
    sourceId?: string;
  };

  if (!Array.isArray(results) || results.length === 0) {
    response.status(400).json({ error: "results array is required" });
    return;
  }

  try {
    const { ingestFromPipelineResult } = await import(
      "../services/ingest-scraped-games.js"
    );

    const resolvedSourceId =
      sourceId || (await getOrCreateCtpbSource());

    let totalCreated = 0;
    let totalUpdated = 0;
    const ingestionResults = [];

    for (const result of results) {
      if (result.status !== "success" || !result.raw_content) {
        ingestionResults.push({
          url: result.url,
          status: "skipped",
          reason: result.status || "no_raw_content",
        });
        continue;
      }

      const ingestResult = await ingestFromPipelineResult(
        resolvedSourceId,
        result.url,
        result.raw_content,
      );

      totalCreated += ingestResult.created;
      totalUpdated += ingestResult.updated;

      ingestionResults.push({
        url: result.url,
        status: "ingested",
        gamesCreated: ingestResult.created,
        gamesUpdated: ingestResult.updated,
      });
    }

    response.status(200).json({
      status: "success",
      message: "Batch ingestion complete",
      summary: {
        totalResults: results.length,
        totalGamesCreated: totalCreated,
        totalGamesUpdated: totalUpdated,
        totalGames: totalCreated + totalUpdated,
      },
      details: ingestionResults,
    });
  } catch (error) {
    console.error("Batch ingest error:", error);
    response.status(500).json({
      error: "Failed to batch ingest scraped data",
      message: error instanceof Error ? error.message : "Unknown error",
    });
  }
}
