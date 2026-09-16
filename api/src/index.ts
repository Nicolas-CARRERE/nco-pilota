/**
 * Pelota Node.js API - main entry.
 * Owns DB, proxies scraping to FastAPI.
 */

import cors from "cors";
import express from "express";

import { logger } from "./logger.js";
import { requestLogger } from "./middleware/request-logger.js";
import { analyticsRouter } from "./routes/analytics.js";
import { competitionsRouter } from "./routes/competitions.js";
import { gamesRouter } from "./routes/games.js";
import { scrapeRouter } from "./routes/scrape.js";
import { statsRouter } from "./routes/stats.js";
import { teamsRouter } from "./routes/teams.js";
import { testRouter } from "./api/test/test.routes.js";

const app = express();

// Allow frontend dev server (and optional configured origin) to call the API.
const corsOrigin = process.env.PELOTA_CORS_ORIGIN ?? "http://localhost:4200";
app.use(
  cors({
    origin: corsOrigin.split(",").map((o) => o.trim()),
    credentials: true,
  })
);
app.use(express.json());
app.use(requestLogger);

app.get("/", (_request, response) => {
  response.json({ message: "Pelota API", version: "1.0.0" });
});

app.get("/health", (_request, response) => {
  response.json({ status: "ok" });
});

// Scrape routes are internal; do not include in public API docs (OpenAPI/Swagger).
// When adding a spec generator, register only public routers (games, analytics) in the served spec.
app.use("/scrape", scrapeRouter);
app.use("/games", gamesRouter);
app.use("/competitions", competitionsRouter);
app.use("/teams", teamsRouter);
app.use("/analytics", analyticsRouter);
app.use("/stats", statsRouter);
app.use("/api/test", testRouter);

const apiServerPort = process.env.PELOTA_API_SERVER_PORT ?? 3000;
app.listen(apiServerPort, () => {
  logger.info("Pelota API listening", {
    port: apiServerPort,
    corsOrigin,
  });
});
