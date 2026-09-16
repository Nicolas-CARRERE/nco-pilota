/**
 * Scrape proxy routes - call FastAPI scraper and persist results.
 */

import { Router, Request, Response } from "express";
import axios from "axios";
import { PrismaClient } from "@prisma/client";

import { ingestFromPipelineResult } from "../services/ingest-scraped-games.js";
import { ingestScrapedData, ingestBatchScrapedData } from "../controllers/scrape.controller.js";

const router = Router();
const prisma = new PrismaClient();

const FASTAPI_SCRAPER_SERVICE_URL =
  process.env.PELOTA_FASTAPI_SCRAPER_SERVICE_URL ?? "http://localhost:8001";

/** Shared timeout (10 min) for all scraper requests to FastAPI. */
const SCRAPER_REQUEST_TIMEOUT_MS = 600_000;

/**
 * POST /scrape/trigger
 * Async trigger only: returns 202 Accepted and runs the scrape in the background.
 * Body: { url: string, sourceId?: string }
 */
router.post("/trigger", (request: Request, response: Response) => {
  const { url, sourceId } = request.body as { url?: string; sourceId?: string };

  if (!url || typeof url !== "string") {
    response.status(400).json({ error: "url is required" });
    return;
  }

  response.status(202).json({
    status: "accepted",
    message: "Scrape trigger started in background",
  });

  runTriggerScrape(url, sourceId).catch((err) => {
    console.error(
      "Scrape trigger failed:",
      err instanceof Error ? err.message : err,
    );
  });
});

async function runTriggerScrape(url: string, sourceId?: string): Promise<void> {
  try {
    const scraperResponse = await axios.post(
      `${FASTAPI_SCRAPER_SERVICE_URL}/scrape/run`,
      { url, source_id: sourceId },
      {
        timeout: SCRAPER_REQUEST_TIMEOUT_MS,
        headers: { "Content-Type": "application/json" },
        validateStatus: () => true,
      },
    );

    if (scraperResponse.status !== 200) {
      console.error(
        "Scrape trigger: FastAPI returned",
        scraperResponse.status,
        scraperResponse.data,
      );
      return;
    }

    const scrapeResult = scraperResponse.data as {
      status: string;
      raw_content?: Record<string, unknown>;
      total_items?: number;
      errors?: Array<{ url: string; code: string; message: string }>;
    };

    if (sourceId && scrapeResult.raw_content) {
      const sourceRecord = await prisma.source.findUnique({
        where: { id: sourceId },
      });
      if (sourceRecord) {
        await prisma.scrapingJobRun.create({
          data: {
            sourceId,
            url,
            startTime: new Date(),
            endTime: new Date(),
            status: scrapeResult.status,
            rawContent: JSON.stringify(scrapeResult.raw_content),
            errorsCount: scrapeResult.errors?.length ?? 0,
          },
        });
      }
    }

    console.log("Scrape trigger completed", {
      url: url.slice(0, 60),
      status: scrapeResult.status,
    });
  } catch (error) {
    console.error("Scrape trigger error:", error);
    throw error;
  }
}

/**
 * GET /scrape/ctpb/filters
 * Fetches CTPB resultats.php form and returns available filter options.
 * Query: competition (optional) = InCompet value to get specialties for that competition only.
 * Use these values in POST /ctpb/resultats.
 */
router.get("/ctpb/filters", async (request: Request, response: Response) => {
  try {
    const competition =
      typeof request.query?.competition === "string"
        ? request.query.competition
        : undefined;
    const url = new URL(`${FASTAPI_SCRAPER_SERVICE_URL}/scrape/ctpb/filters`);
    if (competition) url.searchParams.set("competition", competition);
    const scraperResponse = await axios.get(url.toString(), {
      timeout: SCRAPER_REQUEST_TIMEOUT_MS,
      validateStatus: () => true,
    });

    if (scraperResponse.status !== 200) {
      response.status(502).json({
        error: "CTPB filters proxy failed",
        status: scraperResponse.status,
        data: scraperResponse.data,
      });
      return;
    }

    response.json(scraperResponse.data);
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";
    response.status(502).json({
      error: "Failed to call CTPB filters",
      message: errorMessage,
    });
  }
});

/** Map API filter keys to ScrapedFilterOption kind (CTPB). */
const FILTER_KEY_TO_KIND: Record<string, string> = {
  competitions: "competition",
  specialties: "specialty",
  cities: "city",
  clubs: "club",
  categories: "category",
  phases: "phase",
};

/** Map FFPB filter keys to ScrapedFilterOption kind. */
const FFPB_FILTER_KEY_TO_KIND: Record<string, string> = {
  years: "year",
  competition_types: "competition_type",
  categories: "category",
  disciplines: "discipline",
  locations: "location",
  phases: "phase",
};

/**
 * POST /scrape/ctpb/filters/sync
 * Async trigger only: returns 202 Accepted immediately and runs the sync in the background.
 * Fetches CTPB filters from FastAPI, resolves or creates the CTPB Source, then UPSERTs
 * all filter options (competitions, specialties, cities, clubs, categories, phases)
 * into ScrapedFilterOption. Body is optional (e.g. { url } for logging); not used for sync.
 */
router.post("/ctpb/filters/sync", (request: Request, response: Response) => {
  response.status(202).json({
    status: "accepted",
    message: "CTPB filters sync started in background",
  });

  runCtpbFiltersSync().catch((err: unknown) => {
    const isTimeout =
      err &&
      typeof err === "object" &&
      "code" in err &&
      (err as { code?: string }).code === "ECONNABORTED";
    console.error(
      "CTPB filters sync failed:",
      isTimeout
        ? "timeout calling FastAPI (backend needs more time for many competitions; timeout is 10 min)"
        : err instanceof Error
          ? err.message
          : String(err),
    );
    if (!isTimeout && err) console.error(err);
  });
});

async function runCtpbFiltersSync(): Promise<void> {
  console.log(
    "CTPB filters sync: background job started, calling FastAPI (timeout %d min)",
    SCRAPER_REQUEST_TIMEOUT_MS / 60000,
  );
  try {
    const scraperResponse = await axios.get(
      `${FASTAPI_SCRAPER_SERVICE_URL}/scrape/ctpb/filters`,
      {
        timeout: SCRAPER_REQUEST_TIMEOUT_MS,
        validateStatus: () => true,
      },
    );

    if (scraperResponse.status !== 200) {
      console.error(
        "CTPB filters fetch failed",
        scraperResponse.status,
        scraperResponse.data,
      );
      return;
    }

    const data = scraperResponse.data as {
      competitions?: Array<{ value: string; label: string }>;
      specialties?: Array<{ value: string; label: string }>;
      specialties_by_competition?: Record<
        string,
        Array<{ value: string; label: string }>
      >;
      cities?: Array<{ value: string; label: string }>;
      clubs?: Array<{ value: string; label: string }>;
      categories?: Array<{ value: string; label: string }>;
      phases?: Array<{ value: string; label: string }>;
      error?: string | null;
    };

    if (data.error) {
      console.error("CTPB filters returned error:", data.error);
      return;
    }

    let source = await prisma.source.findFirst({
      where: { url: { contains: "ctpb.euskalpilota.fr" } },
      select: { id: true },
    });
    if (!source) {
      source = await prisma.source.create({
        data: {
          name: "CTPB",
          url: "https://ctpb.euskalpilota.fr",
        },
        select: { id: true },
      });
    }

    const sourceId = source.id;
    const now = new Date();
    const counts: Record<string, number> = {};

    await prisma.$transaction(async (tx) => {
      // Upsert flat options (competition, city, club, category, phase) into ScrapedFilterOption
      for (const [key, kind] of Object.entries(FILTER_KEY_TO_KIND)) {
        if (kind === "specialty") continue;
        const options = data[key as keyof typeof data];
        if (!Array.isArray(options)) continue;
        let count = 0;
        for (const item of options) {
          const value = String(item?.value ?? "");
          const label = String(item?.label ?? "");
          await tx.scrapedFilterOption.upsert({
            where: {
              sourceId_kind_value: { sourceId, kind, value },
            },
            create: { sourceId, kind, value, label },
            update: { label },
          });
          count += 1;
        }
        counts[kind] = count;
      }

      // Upsert specialties into ScrapedSpecialty (one-to-many with competition)
      if (data.specialties_by_competition) {
        let specialtyCount = 0;
        for (const [compValue, options] of Object.entries(
          data.specialties_by_competition,
        )) {
          if (!Array.isArray(options)) continue;
          const competitionOption = await tx.scrapedFilterOption.findFirst({
            where: {
              sourceId,
              kind: "competition",
              value: compValue,
            },
            select: { id: true },
          });
          if (!competitionOption) continue;
          const competitionOptionId = competitionOption.id;
          for (const item of options) {
            const value = String(item?.value ?? "");
            const label = String(item?.label ?? "");
            await tx.scrapedSpecialty.upsert({
              where: {
                sourceId_competitionOptionId_value: {
                  sourceId,
                  competitionOptionId,
                  value,
                },
              },
              create: { sourceId, competitionOptionId, value, label },
              update: { label },
            });
            specialtyCount += 1;
          }
        }
        counts.specialty = specialtyCount;
      }

      await tx.source.update({
        where: { id: sourceId },
        data: {
          lastScraped: now,
          lastSuccessfulScrape: now,
        },
      });
    });

    console.log("CTPB filters sync completed", {
      sourceId,
      counts,
      synced_at: now.toISOString(),
    });
  } catch (error) {
    console.error("CTPB filters sync error:", error);
    throw error;
  }
}

/**
 * POST /scrape/ctpb/resultats
 * Async trigger only: returns 202 Accepted and runs the scrape in the background.
 * Body: { competition?, specialty?, ville?, club?, date_from?, date_to?, category?, phase? }
 */
router.post("/ctpb/resultats", (request: Request, response: Response) => {
  const body = request.body as Record<string, unknown>;

  response.status(202).json({
    status: "accepted",
    message: "CTPB resultats scrape started in background",
  });

  runCtpbResultatsScrape(body).catch((err) => {
    console.error(
      "CTPB resultats scrape failed:",
      err instanceof Error ? err.message : err,
    );
  });
});

async function runCtpbResultatsScrape(
  body: Record<string, unknown>,
): Promise<void> {
  try {
    const scraperResponse = await axios.post(
      `${FASTAPI_SCRAPER_SERVICE_URL}/scrape/ctpb/resultats`,
      body ?? {},
      {
        timeout: SCRAPER_REQUEST_TIMEOUT_MS,
        headers: { "Content-Type": "application/json" },
        validateStatus: () => true,
      },
    );

    if (scraperResponse.status !== 200) {
      console.error(
        "CTPB resultats: FastAPI returned",
        scraperResponse.status,
        scraperResponse.data,
      );
      return;
    }

    const data = scraperResponse.data as { games?: unknown[] };
    const gamesCount = Array.isArray(data?.games) ? data.games.length : 0;
    console.log("CTPB resultats scrape completed", { games_count: gamesCount });
  } catch (error) {
    console.error("CTPB resultats scrape error:", error);
    throw error;
  }
}

/**
 * POST /scrape/batch
 * Async trigger only: returns 202 Accepted and runs the batch scrape in the background.
 * Body: { urls: Array<{ url: string, source_id?: string }> }
 */
router.post("/batch", (request: Request, response: Response) => {
  const { urls } = request.body as {
    urls?: Array<{ url: string; source_id?: string }>;
  };

  if (!Array.isArray(urls) || urls.length === 0) {
    response.status(400).json({ error: "urls array is required" });
    return;
  }

  response.status(202).json({
    status: "accepted",
    message: "Batch scrape started in background",
  });

  runBatchScrape(urls).catch((err) => {
    console.error(
      "Batch scrape failed:",
      err instanceof Error ? err.message : err,
    );
  });
});

async function runBatchScrape(
  urls: Array<{ url: string; source_id?: string }>,
): Promise<void> {
  try {
    const batchPayload = urls.map((urlItem) => ({
      url: urlItem.url,
      source_id: urlItem.source_id,
    }));
    const scraperResponse = await axios.post(
      `${FASTAPI_SCRAPER_SERVICE_URL}/scrape/batch`,
      { urls: batchPayload },
      {
        timeout: SCRAPER_REQUEST_TIMEOUT_MS,
        headers: { "Content-Type": "application/json" },
        validateStatus: () => true,
      },
    );

    if (scraperResponse.status !== 200) {
      console.error("Batch scrape: FastAPI returned", scraperResponse.status);
      return;
    }

    const results = scraperResponse.data as unknown[];
    console.log("Batch scrape completed", {
      urls_count: urls.length,
      results_count: results?.length ?? 0,
    });
  } catch (error) {
    console.error("Batch scrape error:", error);
    throw error;
  }
}

type PipelineCombinationResult = {
  url: string;
  competition: string;
  specialty: string;
  status: string;
  games_count: number;
  raw_content?: Record<string, unknown> | null;
  errors: Array<{ url: string; code: string; message: string }>;
};

type PipelineData = {
  filters_fetched: boolean;
  combinations_total: number;
  combinations_pending: number;
  combinations_scraped: number;
  results: PipelineCombinationResult[];
};

/**
 * POST /scrape/ctpb/pipeline
 * Async trigger only: returns 202 Accepted and runs the full pipeline in the background.
 *
 * Body (optional): sourceId?, maxCombinations?, maxAgeHours?, requestDelaySeconds?,
 * competition?, category?, specialty?, phase?, ville?, club?, dateFrom?, dateTo?
 */
router.post("/ctpb/pipeline", (request: Request, response: Response) => {
  const body = request.body as {
    sourceId?: string;
    maxCombinations?: number;
    maxAgeHours?: number;
    requestDelaySeconds?: number;
    competition?: string;
    category?: string;
    specialty?: string;
    phase?: string;
    ville?: string;
    club?: string;
    dateFrom?: string;
    dateTo?: string;
  };

  const {
    sourceId,
    maxCombinations,
    maxAgeHours = 0,
    requestDelaySeconds = 1.5,
    competition,
    category,
    specialty,
    phase,
    ville,
    club,
    dateFrom,
    dateTo,
  } = body;

  response.status(202).json({
    status: "accepted",
    message: "CTPB pipeline started in background",
  });

  runCtpbPipeline({
    sourceId,
    maxCombinations,
    maxAgeHours,
    requestDelaySeconds,
    competition,
    category,
    specialty,
    phase,
    ville,
    club,
    dateFrom,
    dateTo,
  }).catch((err) => {
    console.error(
      "CTPB pipeline failed:",
      err instanceof Error ? err.message : err,
    );
  });
});

async function runCtpbPipeline(params: {
  sourceId?: string;
  maxCombinations?: number;
  maxAgeHours?: number;
  requestDelaySeconds?: number;
  competition?: string;
  category?: string;
  specialty?: string;
  phase?: string;
  ville?: string;
  club?: string;
  dateFrom?: string;
  dateTo?: string;
}): Promise<void> {
  const {
    sourceId,
    maxCombinations,
    maxAgeHours = 0,
    requestDelaySeconds = 1.5,
    competition,
    category,
    specialty,
    phase,
    ville,
    club,
    dateFrom,
    dateTo,
  } = params;

  let resolvedSourceId: string | null = sourceId ?? null;
  if (!resolvedSourceId) {
    let ctpbSource = await prisma.source.findFirst({
      where: { url: { contains: "ctpb.euskalpilota.fr" } },
      select: { id: true },
    });
    if (!ctpbSource) {
      ctpbSource = await prisma.source.create({
        data: { name: "CTPB", url: "https://ctpb.euskalpilota.fr" },
        select: { id: true },
      });
    }
    resolvedSourceId = ctpbSource.id;
  }

  let alreadyScrapedUrls: string[] = [];
  if (maxAgeHours > 0) {
    const cutoff = new Date(Date.now() - maxAgeHours * 60 * 60 * 1000);
    const recentRuns = await prisma.scrapingJobRun.findMany({
      where: {
        url: { contains: "ctpb.euskalpilota.fr/resultats.php" },
        status: "success",
        startTime: { gte: cutoff },
      },
      select: { url: true },
    });
    const urlsFromRuns = [...new Set(recentRuns.map((run) => run.url))];
    const urlsToRescan = await prisma.game.findMany({
      where: {
        scrapedFromUrl: {
          not: null,
          contains: "ctpb.euskalpilota.fr/resultats.php",
        },
        scoreComplete: false,
      },
      select: { scrapedFromUrl: true },
      distinct: ["scrapedFromUrl"],
    });
    const rescanSet = new Set(
      urlsToRescan.map((g) => g.scrapedFromUrl).filter(Boolean) as string[],
    );
    alreadyScrapedUrls = urlsFromRuns.filter((url) => !rescanSet.has(url));
  }

  const pipelinePayload: Record<string, unknown> = {
    already_scraped_urls: alreadyScrapedUrls,
    max_combinations: maxCombinations ?? null,
    request_delay_seconds: requestDelaySeconds,
  };
  if (competition != null) pipelinePayload.competition = competition;
  if (category != null) pipelinePayload.category = category;
  if (specialty != null) pipelinePayload.specialty = specialty;
  if (phase != null) pipelinePayload.phase = phase;
  if (ville != null) pipelinePayload.ville = ville;
  if (club != null) pipelinePayload.club = club;
  if (dateFrom != null) pipelinePayload.date_from = dateFrom;
  if (dateTo != null) pipelinePayload.date_to = dateTo;

  const pipelineResponse = await axios.post(
    `${FASTAPI_SCRAPER_SERVICE_URL}/scrape/ctpb/pipeline`,
    pipelinePayload,
    {
      timeout: SCRAPER_REQUEST_TIMEOUT_MS,
      headers: { "Content-Type": "application/json" },
      validateStatus: () => true,
    },
  );

  if (pipelineResponse.status !== 200) {
    console.error(
      "CTPB pipeline: FastAPI returned",
      pipelineResponse.status,
      pipelineResponse.data,
    );
    return;
  }

  const pipelineData = pipelineResponse.data as PipelineData;

  let persistedCount = 0;
  let ingestCreated = 0;
  let ingestUpdated = 0;
  if (resolvedSourceId) {
    const now = new Date();
    const persistOps = pipelineData.results
      .filter((result) => result.status === "success")
      .map((result) =>
        prisma.scrapingJobRun.create({
          data: {
            sourceId: resolvedSourceId as string,
            url: result.url,
            startTime: now,
            endTime: now,
            status: "success",
            rawContent: result.raw_content
              ? JSON.stringify(result.raw_content)
              : null,
            errorsCount: result.errors?.length ?? 0,
          },
        }),
      );
    await Promise.all(persistOps);
    persistedCount = persistOps.length;

    for (const result of pipelineData.results) {
      if (result.status === "success" && result.raw_content) {
        const ing = await ingestFromPipelineResult(
          resolvedSourceId as string,
          result.url,
          result.raw_content as Record<string, unknown>,
        );
        ingestCreated += ing.created;
        ingestUpdated += ing.updated;
      }
    }
  }

  console.log("CTPB pipeline completed", {
    combinations_scraped: pipelineData.combinations_scraped,
    persisted_count: persistedCount,
    ingest_created: ingestCreated,
    ingest_updated: ingestUpdated,
  });
}

/**
 * GET /scrape/ctpb/urls-to-rescan
 * Returns URLs that have at least one game with incomplete score (scoreComplete = false).
 * These URLs should be rescraped to fetch final results.
 */
router.get(
  "/ctpb/urls-to-rescan",
  async (_request: Request, response: Response) => {
    try {
      const games = await prisma.game.findMany({
        where: {
          scrapedFromUrl: {
            not: null,
            contains: "ctpb.euskalpilota.fr/resultats.php",
          },
          scoreComplete: false,
        },
        select: { scrapedFromUrl: true },
        distinct: ["scrapedFromUrl"],
      });
      const urls = games
        .map((g) => g.scrapedFromUrl)
        .filter((u): u is string => u != null);
      response.json({ urls });
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      response.status(500).json({
        error: "Failed to get URLs to rescan",
        message: errorMessage,
      });
    }
  },
);

/**
 * GET /scrape/ffpb/filters
 * Fetches FFPB filter options from FastAPI (year, category, discipline, location, phase).
 */
router.get("/ffpb/filters", async (_request: Request, response: Response) => {
  try {
    const scraperResponse = await axios.get(
      `${FASTAPI_SCRAPER_SERVICE_URL}/scrape/ffpb/filters`,
      { timeout: SCRAPER_REQUEST_TIMEOUT_MS, validateStatus: () => true },
    );
    if (scraperResponse.status !== 200) {
      response.status(502).json({
        error: "FFPB filters proxy failed",
        status: scraperResponse.status,
        data: scraperResponse.data,
      });
      return;
    }
    response.json(scraperResponse.data);
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";
    response.status(502).json({
      error: "Failed to call FFPB filters",
      message: errorMessage,
    });
  }
});

/**
 * POST /scrape/ffpb/filters/sync
 * Async trigger only: returns 202 Accepted and runs FFPB filters sync in the background.
 */
router.post("/ffpb/filters/sync", (_request: Request, response: Response) => {
  response.status(202).json({
    status: "accepted",
    message: "FFPB filters sync started in background",
  });

  runFfpbFiltersSync().catch((err) => {
    console.error(
      "FFPB filters sync failed:",
      err instanceof Error ? err.message : err,
    );
  });
});

async function runFfpbFiltersSync(): Promise<void> {
  try {
    const scraperResponse = await axios.get(
      `${FASTAPI_SCRAPER_SERVICE_URL}/scrape/ffpb/filters`,
      { timeout: SCRAPER_REQUEST_TIMEOUT_MS, validateStatus: () => true },
    );
    if (scraperResponse.status !== 200) {
      console.error("FFPB filters sync: fetch failed", scraperResponse.status);
      return;
    }
    const data = scraperResponse.data as Record<string, unknown> & {
      error?: string | null;
    };
    if (data.error) {
      console.error("FFPB filters sync: API error", data.error);
      return;
    }
    let source = await prisma.source.findFirst({
      where: { url: { contains: "competition.ffpb.net" } },
      select: { id: true },
    });
    if (!source) {
      source = await prisma.source.create({
        data: {
          name: "FFPB",
          url: "https://competition.ffpb.net/FFPB_COMPETITION",
        },
        select: { id: true },
      });
    }
    const sourceId = source.id;
    const now = new Date();
    const counts: Record<string, number> = {};
    await prisma.$transaction(async (tx) => {
      for (const [key, kind] of Object.entries(FFPB_FILTER_KEY_TO_KIND)) {
        const options = data[key];
        if (!Array.isArray(options)) continue;
        let count = 0;
        for (const item of options) {
          const value = String((item as { value?: string })?.value ?? "");
          const label = String((item as { label?: string })?.label ?? "");
          await tx.scrapedFilterOption.upsert({
            where: {
              sourceId_kind_value: { sourceId, kind, value },
            },
            create: { sourceId, kind, value, label },
            update: { label },
          });
          count += 1;
        }
        counts[kind] = count;
      }
      await tx.source.update({
        where: { id: sourceId },
        data: { lastScraped: now, lastSuccessfulScrape: now },
      });
    });
    console.log("FFPB filters sync completed", { sourceId, counts });
  } catch (error) {
    console.error("FFPB filters sync error:", error);
    throw error;
  }
}

/**
 * POST /scrape/ffpb/resultats
 * Async trigger only: returns 202 Accepted and runs FFPB resultats scrape in the background.
 */
router.post("/ffpb/resultats", (request: Request, response: Response) => {
  const body = request.body as Record<string, unknown>;

  response.status(202).json({
    status: "accepted",
    message: "FFPB resultats scrape started in background",
  });

  runFfpbResultatsScrape(body).catch((err) => {
    console.error(
      "FFPB resultats scrape failed:",
      err instanceof Error ? err.message : err,
    );
  });
});

async function runFfpbResultatsScrape(
  body: Record<string, unknown>,
): Promise<void> {
  try {
    const scraperResponse = await axios.post(
      `${FASTAPI_SCRAPER_SERVICE_URL}/scrape/ffpb/resultats`,
      body ?? {},
      {
        timeout: SCRAPER_REQUEST_TIMEOUT_MS,
        headers: { "Content-Type": "application/json" },
        validateStatus: () => true,
      },
    );
    if (scraperResponse.status !== 200) {
      console.error("FFPB resultats: FastAPI returned", scraperResponse.status);
      return;
    }
    const data = scraperResponse.data as { games?: unknown[] };
    const gamesCount = Array.isArray(data?.games) ? data.games.length : 0;
    console.log("FFPB resultats scrape completed", { games_count: gamesCount });
  } catch (error) {
    console.error("FFPB resultats scrape error:", error);
    throw error;
  }
}

/**
 * POST /scrape/ingest
 * Scrape a URL and immediately ingest the results into the database.
 * Returns summary of competitions and games created/updated.
 */
router.post("/ingest", async (request: Request, response: Response) => {
  await ingestScrapedData(request, response);
});

/**
 * POST /scrape/ingest/batch
 * Batch ingest multiple scrape results into the database.
 */
router.post("/ingest/batch", async (request: Request, response: Response) => {
  await ingestBatchScrapedData(request, response);
});

export { router as scrapeRouter };
