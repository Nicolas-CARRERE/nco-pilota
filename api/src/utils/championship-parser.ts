/**
 * Championship name parser - extracts structured fields from championship names.
 * 
 * Parses championship names like:
 * - "Championnat de France 2026 - Main Nue - 1ère Série - GROUPE A - Poule phase 1"
 * - "CTPB 2025 - Trinquet - Cadets - Finale"
 * - "FFPB Place Libre 2026 - M19 - 1.Maila"
 */

export interface ParsedChampionship {
  discipline?: string;      // Place Libre, Trinquet, Main Nue, Chistera, etc.
  season?: string;          // 2026
  year?: number;            // 2026
  series?: string;          // 1ère Série - 1.Maila
  group?: string;           // GROUPE A, M19, Cadets, Gazteak
  pool?: string;            // Poule phase 1, Finale
  organization?: string;    // CTPB, FFPB
}

/** Known discipline keywords (case-insensitive matching) */
const DISCIPLINE_KEYWORDS = [
  "Place Libre",
  "Trinquet",
  "Main Nue",
  "Chistera",
  "Joko Garbi",
  "Paleta",
  "Gros Paleta",
  "Pala Corta",
  "Xare",
  "Frontenis",
];

/** Known organization keywords */
const ORGANIZATION_KEYWORDS = ["CTPB", "FFPB", "Comité", "Fédération"];

/** Known group/age category keywords */
const GROUP_KEYWORDS = [
  "GROUPE A",
  "GROUPE B",
  "GROUPE C",
  "M19",
  "M17",
  "M15",
  "Cadets",
  "Juniors",
  "Seniors",
  "Gazteak",
  "Txikiak",
];

/** Known pool/phase keywords */
const POOL_KEYWORDS = [
  "Poule",
  "Finale",
  "Demi-finale",
  "1/2 finale",
  "1/4 finale",
  "Barrage",
  "Phase",
];

/**
 * Parse championship name into structured fields.
 * 
 * @param name - Championship name string
 * @returns ParsedChampionship object with extracted fields
 */
export function parseChampionshipName(name: string): ParsedChampionship {
  if (!name || typeof name !== "string") {
    return {};
  }

  const result: ParsedChampionship = {};
  const normalized = name.trim();

  // Extract organization (usually at the beginning)
  for (const org of ORGANIZATION_KEYWORDS) {
    if (normalized.toUpperCase().includes(org.toUpperCase())) {
      result.organization = org;
      break;
    }
  }

  // Extract year/season - detect season spans like "2025-2026" or "25-26"
  // Priority: full span (2025-2026) > short span (25-26) > single year (2026)
  const fullSeasonMatch = normalized.match(/\b(20\d{2})-(20\d{2})\b/);
  const shortSeasonMatch = normalized.match(/\b(\d{2})-(\d{2})\b/);
  const singleYearMatch = normalized.match(/\b(20\d{2})\b/);

  if (fullSeasonMatch) {
    // Full season span: "2025-2026"
    const startYear = parseInt(fullSeasonMatch[1], 10);
    const endYear = parseInt(fullSeasonMatch[2], 10);
    result.season = `${startYear}-${endYear}`;
    result.year = endYear;
  } else if (shortSeasonMatch) {
    // Short season span: "25-26" → "2025-2026"
    let startYear = parseInt(shortSeasonMatch[1], 10);
    let endYear = parseInt(shortSeasonMatch[2], 10);
    // Handle century rollover (e.g., 99-00 → 1999-2000)
    if (startYear > endYear) {
      startYear = 1900 + startYear;
      endYear = 2000 + endYear;
    } else {
      startYear = 2000 + startYear;
      endYear = 2000 + endYear;
    }
    result.season = `${startYear}-${endYear}`;
    result.year = endYear;
  } else if (singleYearMatch) {
    // Single year: "2026" → season: "2026", year: 2026
    const year = parseInt(singleYearMatch[1], 10);
    result.year = year;
    result.season = String(year);
  }

  // Extract discipline
  for (const discipline of DISCIPLINE_KEYWORDS) {
    if (normalized.toUpperCase().includes(discipline.toUpperCase())) {
      result.discipline = discipline;
      break;
    }
  }

  // Extract series (e.g., "1ère Série", "1.Maila")
  const seriesMatch = normalized.match(/(\d+(?:ère|ème|º|\.Maila)?\s*(?:Série|Maila)?)/i);
  if (seriesMatch) {
    result.series = seriesMatch[1].trim();
  }

  // Extract group/age category
  for (const group of GROUP_KEYWORDS) {
    if (normalized.toUpperCase().includes(group.toUpperCase())) {
      result.group = group;
      break;
    }
  }

  // Extract pool/phase
  for (const pool of POOL_KEYWORDS) {
    if (normalized.toUpperCase().includes(pool.toUpperCase())) {
      // Try to get more context (e.g., "Poule phase 1" instead of just "Poule")
      const poolRegex = new RegExp(
        `(${pool}(?:\\s+(?:phase\\s*\\d+|\\d+))?`,
        "i"
      );
      const poolMatch = normalized.match(poolRegex);
      if (poolMatch) {
        result.pool = poolMatch[1].trim();
      } else {
        result.pool = pool;
      }
      break;
    }
  }

  return result;
}

/**
 * Parse multiple championship names and return distinct filter options.
 * 
 * @param names - Array of championship names
 * @returns Object with arrays of distinct values for each field
 */
export function extractFilterOptions(names: string[]): {
  disciplines: string[];
  seasons: string[];
  years: number[];
  series: string[];
  groups: string[];
  pools: string[];
  organizations: string[];
} {
  const disciplines = new Set<string>();
  const seasons = new Set<string>();
  const years = new Set<number>();
  const series = new Set<string>();
  const groups = new Set<string>();
  const pools = new Set<string>();
  const organizations = new Set<string>();

  for (const name of names) {
    const parsed = parseChampionshipName(name);
    if (parsed.discipline) disciplines.add(parsed.discipline);
    if (parsed.season) seasons.add(parsed.season);
    if (parsed.year) years.add(parsed.year);
    if (parsed.series) series.add(parsed.series);
    if (parsed.group) groups.add(parsed.group);
    if (parsed.pool) pools.add(parsed.pool);
    if (parsed.organization) organizations.add(parsed.organization);
  }

  return {
    disciplines: Array.from(disciplines).sort(),
    seasons: Array.from(seasons).sort(),
    years: Array.from(years).sort((a, b) => b - a),
    series: Array.from(series).sort(),
    groups: Array.from(groups).sort(),
    pools: Array.from(pools).sort(),
    organizations: Array.from(organizations).sort(),
  };
}
