/**
 * Test mode controller - DEV/TEST only endpoints.
 * 
 * ⚠️ WARNING: These endpoints are for test/development environments ONLY.
 * They must NEVER be enabled in production.
 * 
 * Required environment variable: TEST_MODE=true or DEV_MODE=true
 */

import { PrismaClient } from "@prisma/client";
import { exec } from "child_process";
import { promisify } from "util";

const prisma = new PrismaClient();
const execAsync = promisify(exec);

/**
 * Check if test mode is enabled.
 * Returns true only if TEST_MODE or DEV_MODE is explicitly set to "true".
 */
function isTestModeEnabled(): boolean {
  const testMode = process.env.TEST_MODE?.toLowerCase();
  const devMode = process.env.DEV_MODE?.toLowerCase();
  return testMode === "true" || devMode === "true";
}

/**
 * Purge database - drop all tables and re-migrate.
 * 
 * ⚠️ DESTRUCTIVE OPERATION - only allowed in test mode.
 */
export async function purgeDatabase(): Promise<{
  success: boolean;
  message: string;
  details?: string;
}> {
  if (!isTestModeEnabled()) {
    return {
      success: false,
      message: "Purge operation denied: TEST_MODE or DEV_MODE must be set to 'true'",
    };
  }

  try {
    console.log("[TEST MODE] Starting database purge...");

    // Drop all tables using Prisma's $executeRaw
    // Note: This approach works for PostgreSQL
    await prisma.$executeRawUnsafe(`
      DO $$ DECLARE
          r RECORD;
      BEGIN
          FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema())
          LOOP
              EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
          END LOOP;
      END $$;
    `);

    console.log("[TEST MODE] All tables dropped");

    // Run migrations
    console.log("[TEST MODE] Running migrations...");
    const { stdout, stderr } = await execAsync("npx prisma migrate dev", {
      cwd: process.cwd(),
      env: process.env,
    });

    if (stderr && !stderr.includes("warn")) {
      console.error("[TEST MODE] Migration stderr:", stderr);
    }

    console.log("[TEST MODE] Migrations completed");

    return {
      success: true,
      message: "Database purged and migrations re-run successfully",
      details: stdout?.slice(0, 500),
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error("[TEST MODE] Purge failed:", errorMessage);
    return {
      success: false,
      message: `Purge operation failed: ${errorMessage}`,
    };
  }
}

export { isTestModeEnabled };
