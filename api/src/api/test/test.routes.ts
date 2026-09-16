/**
 * Test mode routes - DEV/TEST only endpoints.
 * 
 * ⚠️ WARNING: These routes are for test/development environments ONLY.
 * They must NEVER be enabled in production.
 */

import { Router, Request, Response } from "express";
import { purgeDatabase, isTestModeEnabled } from "./test.controller.js";

const router = Router();

/**
 * Simple in-memory rate limiting for purge endpoint.
 * Tracks last purge time per IP.
 */
const rateLimitStore = new Map<string, number>();
const RATE_LIMIT_MS = 60000; // 1 minute between purges

/**
 * POST /api/test/purge-database
 * 
 * ⚠️ DESTRUCTIVE: Drops all tables and re-runs migrations.
 * 
 * Requirements:
 * - TEST_MODE=true or DEV_MODE=true in environment
 * - Rate limited: 1 request per minute per IP
 * 
 * Response:
 * - 200: Success with details
 * - 403: Test mode not enabled
 * - 429: Rate limit exceeded
 * - 500: Purge operation failed
 */
router.post("/purge-database", async (request: Request, response: Response) => {
  // Check test mode
  if (!isTestModeEnabled()) {
    response.status(403).json({
      error: "Forbidden",
      message: "This endpoint is only available in TEST_MODE or DEV_MODE",
      hint: "Set TEST_MODE=true or DEV_MODE=true in your environment",
    });
    return;
  }

  // Rate limiting
  const clientIp = request.ip || request.socket.remoteAddress || "unknown";
  const now = Date.now();
  const lastPurge = rateLimitStore.get(clientIp) || 0;

  if (now - lastPurge < RATE_LIMIT_MS) {
    const remainingMs = RATE_LIMIT_MS - (now - lastPurge);
    response.status(429).json({
      error: "Too Many Requests",
      message: `Rate limit exceeded. Try again in ${Math.ceil(remainingMs / 1000)} seconds`,
    });
    return;
  }

  rateLimitStore.set(clientIp, now);

  console.log(`[TEST MODE] Purge request from ${clientIp}`);

  const result = await purgeDatabase();

  if (result.success) {
    response.status(200).json({
      success: true,
      message: result.message,
      details: result.details,
      warning: "⚠️ This endpoint is for test mode only and will be removed",
    });
  } else {
    response.status(500).json({
      success: false,
      error: "Internal Server Error",
      message: result.message,
    });
  }
});

/**
 * GET /api/test/status
 * Returns current test mode status.
 */
router.get("/status", (_request: Request, response: Response) => {
  response.json({
    testModeEnabled: isTestModeEnabled(),
    environment: {
      TEST_MODE: process.env.TEST_MODE,
      DEV_MODE: process.env.DEV_MODE,
    },
    warning: "Test mode endpoints - do not use in production",
  });
});

export { router as testRouter };
