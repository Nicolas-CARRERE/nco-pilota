"""
Database ingestion service for scraped CTPB data.

Parses discipline_context from scraped games and saves to PostgreSQL via asyncpg.
Uses championship_parser to extract granular competition fields.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import asyncpg

from app.config import get_settings
from app.services.championship_parser import parse_championship_name

logger = logging.getLogger("pelota.ingestion")


class IngestionService:
    """Service for ingesting scraped games into the database."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize ingestion service.

        Args:
            database_url: PostgreSQL connection URL. Defaults to PELOTA_POSTGRES_DATABASE_URL env var.
        """
        self.database_url = database_url or get_settings().database_url
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Create connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.database_url)
            logger.info("Database connection pool created")

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Database connection pool closed")

    async def ingest_all_with_players(
        self,
        competitions: List[Dict[str, Any]],
        scrape_players: bool = True,
    ) -> Dict[str, int]:
        """
        Full pipeline: scrape players from engagements.php, then ingest games.

        Args:
            competitions: List of competition data from scraper (with games)
            scrape_players: Whether to scrape player rosters (default True)

        Returns:
            Dict with counts: players_created, competitions_created,
            games_created, games_updated
        """
        if not self._pool:
            await self.connect()

        players_created = 0
        competitions_created = 0
        games_created = 0
        games_updated = 0

        # Extract all games from competitions
        all_games = []
        for comp in competitions:
            games = comp.get("games", [])
            if isinstance(games, list):
                all_games.extend(games)

        # Extract unique clubs from games
        unique_clubs = set()
        for game in all_games:
            club1 = game.get("club1_name", "") or game.get("club1", "")
            club2 = game.get("club2_name", "") or game.get("club2", "")
            if club1:
                unique_clubs.add(club1)
            if club2:
                unique_clubs.add(club2)

        async with self._pool.acquire() as conn:
            # Step 1: Scrape and ingest players for each club
            if scrape_players and unique_clubs:
                logger.info("Scraping player rosters for %d clubs", len(unique_clubs))
                
                from app.services.engagements_scraper import scrape_club_engagements
                
                for club_name in unique_clubs:
                    # Get club ID from database
                    club_record = await conn.fetchrow(
                        "SELECT id FROM club WHERE name = $1", club_name
                    )
                    
                    if not club_record:
                        # Club doesn't exist yet, will be created during game ingestion
                        continue
                    
                    club_id = club_record["id"]
                    
                    # Scrape engagements for this club
                    players = await scrape_club_engagements(club_id)
                    
                    if players:
                        logger.debug(
                            "Club %s: found %d players",
                            club_name, len(players)
                        )
                        for player_data in players:
                            await self._get_or_create_player(
                                conn,
                                player_data['first_name'],
                                player_data['last_name'],
                                None,  # external_id
                                player_data['license']
                            )
                            players_created += 1

            # Step 2: Ingest games (with real player links)
            for game_data in all_games:
                # Check if game has pre-parsed fields from HTML parser
                pre_parsed = None
                discipline_val = game_data.get("discipline", "")
                series_val = game_data.get("series", "")
                group_val = game_data.get("group", "")
                pool_val = game_data.get("pool", "")
                
                has_granular_data = (
                    (discipline_val and isinstance(discipline_val, str) and discipline_val.strip()) or
                    (series_val and isinstance(series_val, str) and series_val.strip()) or
                    (group_val and isinstance(group_val, str) and group_val.strip()) or
                    (pool_val and isinstance(pool_val, str) and pool_val.strip())
                )
                
                if has_granular_data:
                    pre_parsed = {
                        "discipline": (discipline_val or "").strip() or None,
                        "group": (group_val or "").strip() or None,
                        "series": (series_val or "").strip() or None,
                        "pool": (pool_val or "").strip() or None,
                        "season": game_data.get("season", "").strip() if game_data.get("season") else None,
                        "year": game_data.get("year"),
                        "organization": (game_data.get("organization") or "CTPB").strip(),
                    }
                
                # Parse and create/find competition
                competition_id = await self.parse_and_create_competition(
                    conn, game_data.get("discipline_context", ""), pre_parsed
                )
                if competition_id:
                    competitions_created += 1

                # Create/update game
                result = await self.create_game(conn, game_data, competition_id)
                if result == "created":
                    games_created += 1
                elif result == "updated":
                    games_updated += 1

        logger.info(
            "Ingestion complete: %d players, %d competitions, %d games created, %d games updated",
            players_created,
            competitions_created,
            games_created,
            games_updated,
        )

        return {
            "players_created": players_created,
            "competitions_created": competitions_created,
            "games_created": games_created,
            "games_updated": games_updated,
        }

    async def ingest_scraped_games(self, games: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Main ingestion function - process all scraped games.

        Args:
            games: List of game dicts from scraper (with discipline_context field)

        Returns:
            Dict with counts: competitions_created, games_created, games_updated
        """
        if not self._pool:
            await self.connect()

        competitions_created = 0
        games_created = 0
        games_updated = 0

        async with self._pool.acquire() as conn:
            for game_data in games:
                # Check if game has pre-parsed fields from HTML parser
                # Use pre-parsed if ANY granular field is present (discipline, series, group, or pool)
                pre_parsed = None
                discipline_val = game_data.get("discipline", "")
                series_val = game_data.get("series", "")
                group_val = game_data.get("group", "")
                pool_val = game_data.get("pool", "")
                
                has_granular_data = (
                    (discipline_val and isinstance(discipline_val, str) and discipline_val.strip()) or
                    (series_val and isinstance(series_val, str) and series_val.strip()) or
                    (group_val and isinstance(group_val, str) and group_val.strip()) or
                    (pool_val and isinstance(pool_val, str) and pool_val.strip())
                )
                
                if has_granular_data:
                    # HTML parser already extracted granular fields
                    pre_parsed = {
                        "discipline": (discipline_val or "").strip() or None,
                        "group": (group_val or "").strip() or None,
                        "series": (series_val or "").strip() or None,
                        "pool": (pool_val or "").strip() or None,
                        "season": game_data.get("season", "").strip() if game_data.get("season") else None,
                        "year": game_data.get("year"),
                        "organization": (game_data.get("organization") or "CTPB").strip(),
                    }
                
                # Parse and create/find competition
                competition_id = await self.parse_and_create_competition(
                    conn, game_data.get("discipline_context", ""), pre_parsed
                )
                if competition_id:
                    competitions_created += 1

                # Create/update game
                result = await self.create_game(conn, game_data, competition_id)
                if result == "created":
                    games_created += 1
                elif result == "updated":
                    games_updated += 1

        logger.info(
            "Ingestion complete: %d competitions, %d games created, %d games updated",
            competitions_created,
            games_created,
            games_updated,
        )

        return {
            "competitions_created": competitions_created,
            "games_created": games_created,
            "games_updated": games_updated,
        }

    async def parse_and_create_competition(
        self,
        conn: asyncpg.Connection,
        discipline_context: str = "",
        pre_parsed: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Parse discipline_context or use pre-parsed fields and create Competition record.

        Args:
            conn: Database connection
            discipline_context: Championship name string from scraper (fallback)
            pre_parsed: Dict with already-parsed fields from HTML parser (preferred)

        Returns:
            Competition ID (existing or newly created)
        """
        # Use pre-parsed fields if available (from HTML parser), otherwise parse from string
        if pre_parsed:
            discipline_name = pre_parsed.get("discipline") or "Mur à gauche"
            season = pre_parsed.get("season")
            year = int(pre_parsed["year"]) if pre_parsed.get("year") else datetime.now().year
            series = pre_parsed.get("series")
            group = pre_parsed.get("group")
            pool = pre_parsed.get("pool")
            organization_name = pre_parsed.get("organization", "CTPB")
        else:
            if not discipline_context:
                return await self._get_or_create_default_competition(conn)
            
            # Parse championship name to get granular fields
            parsed = parse_championship_name(discipline_context)
            discipline_name = parsed.get("discipline", "Mur à gauche")
            season = parsed.get("season")
            year = int(parsed["year"]) if parsed.get("year") else datetime.now().year
            series = parsed.get("series")
            group = parsed.get("group")
            pool = parsed.get("pool")
            organization_name = parsed.get("organization", "CTPB")

        async with conn.transaction():
            # Get or create organizer
            organizer_id = await self._get_or_create_organizer(conn, organization_name)

            # Get or create modality
            modality_id = await self._get_or_create_modality(conn, "Pelote basque")

            # Get or create discipline
            discipline_id = await self._get_or_create_discipline(
                conn, modality_id, discipline_name
            )

            # Get or create competition year
            year_id = await self._get_or_create_competition_year(conn, year)

            # Get or create competition series (for series_id FK)
            series_id = None
            if series:
                series_id = await self._get_or_create_competition_series(conn, series)

            # Try to find existing competition with same key fields
            # Handle NULL/empty values properly - NULL != NULL in SQL
            # Must match on ALL granular fields including season and year
            existing = await conn.fetchrow(
                """
                SELECT id FROM competition
                WHERE organizer_id = $1
                  AND discipline_id = $2
                  AND year_id = $3
                  AND (series_id = $4 OR (series_id IS NULL AND $4 IS NULL))
                  AND (series = $5 OR (series IS NULL AND $5 IS NULL))
                  AND ("group" = $6 OR ("group" IS NULL AND $6 IS NULL))
                  AND (pool = $7 OR (pool IS NULL AND $7 IS NULL))
                  AND (season = $8 OR (season IS NULL AND $8 IS NULL))
                  AND year = $9
                """,
                organizer_id,
                discipline_id,
                year_id,
                series_id,
                series if series else None,
                group if group else None,
                pool if pool else None,
                season if season else None,
                year,
            )

            if existing:
                logger.debug("Found existing competition: %s", existing["id"])
                return existing["id"]

            # Create new competition
            start_date = datetime(year, 1, 1)
            competition = await conn.fetchrow(
                """
                INSERT INTO competition (
                    id, organizer_id, discipline_id, year_id, series_id,
                    start_date, end_date, status,
                    discipline, season, year, series, "group", pool, organization
                )
                VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING id
                """,
                organizer_id,
                discipline_id,
                year_id,
                series_id,
                start_date,
                start_date,
                "ongoing",
                discipline_name,
                season if season else None,
                year,
                series if series else None,
                group if group else None,
                pool if pool else None,
                organization_name,
            )

            logger.info(
                "Created competition: %s (discipline=%s, season=%s, series=%s, group=%s, pool=%s)",
                competition["id"],
                discipline_name,
                season,
                series,
                group,
                pool,
            )

            return competition["id"]

    async def create_game(
        self,
        conn: asyncpg.Connection,
        game_data: Dict[str, Any],
        competition_id: Optional[str],
    ) -> str:
        """
        Create or update Game record.

        Args:
            conn: Database connection
            game_data: Game data from scraper
            competition_id: Competition ID to link to

        Returns:
            "created" or "updated"
        """
        # Check for duplicate using external_id (no_renc)
        external_id = game_data.get("no_renc")
        source_id = game_data.get("source_id")

        if external_id and source_id:
            existing = await conn.fetchrow(
                """
                SELECT id FROM game
                WHERE external_id = $1 AND source_id = $2
                """,
                external_id,
                source_id,
            )

            if existing:
                # Update existing game
                await self._update_game(conn, existing["id"], game_data, competition_id)
                return "updated"

        # Create new game
        game_id = await self._create_game(conn, game_data, competition_id)
        return "created"

    async def _get_or_create_default_competition(
        self, conn: asyncpg.Connection
    ) -> str:
        """Get or create a default competition when no discipline_context is provided."""
        year = datetime.now().year
        organizer_id = await self._get_or_create_organizer(conn, "CTPB")
        modality_id = await self._get_or_create_modality(conn, "Pelote basque")
        discipline_id = await self._get_or_create_discipline(
            conn, modality_id, "Mur à gauche"
        )
        year_id = await self._get_or_create_competition_year(conn, year)

        existing = await conn.fetchrow(
            """
            SELECT id FROM competition
            WHERE organizer_id = $1 AND discipline_id = $2 AND year_id = $3
            """,
            organizer_id,
            discipline_id,
            year_id,
        )

        if existing:
            return existing["id"]

        start_date = datetime(year, 1, 1)
        competition = await conn.fetchrow(
            """
            INSERT INTO competition (
                id, organizer_id, discipline_id, year_id,
                start_date, end_date, status, year
            )
            VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            organizer_id,
            discipline_id,
            year_id,
            start_date,
            start_date,
            "ongoing",
            year,
        )

        return competition["id"]

    async def _get_or_create_organizer(
        self, conn: asyncpg.Connection, name: str
    ) -> str:
        """Get or create organizer record."""
        existing = await conn.fetchrow(
            "SELECT id FROM organizer WHERE name = $1", name
        )
        if existing:
            return existing["id"]

        organizer = await conn.fetchrow(
            """
            INSERT INTO organizer (id, name, type, is_active)
            VALUES (gen_random_uuid(), $1, $2, $3)
            RETURNING id
            """,
            name,
            "committee",
            True,
        )
        return organizer["id"]

    async def _get_or_create_modality(
        self, conn: asyncpg.Connection, name: str
    ) -> str:
        """Get or create modality record."""
        existing = await conn.fetchrow(
            "SELECT id FROM modality WHERE name = $1", name
        )
        if existing:
            return existing["id"]

        modality = await conn.fetchrow(
            """
            INSERT INTO modality (id, name) VALUES (gen_random_uuid(), $1)
            RETURNING id
            """,
            name,
        )
        return modality["id"]

    async def _get_or_create_discipline(
        self, conn: asyncpg.Connection, modality_id: str, name: str
    ) -> str:
        """Get or create discipline record."""
        existing = await conn.fetchrow(
            "SELECT id FROM discipline WHERE modality_id = $1 AND name = $2",
            modality_id,
            name,
        )
        if existing:
            return existing["id"]

        discipline = await conn.fetchrow(
            """
            INSERT INTO discipline (id, modality_id, name) VALUES (gen_random_uuid(), $1, $2)
            RETURNING id
            """,
            modality_id,
            name,
        )
        return discipline["id"]

    async def _get_or_create_competition_year(
        self, conn: asyncpg.Connection, year: int
    ) -> str:
        """Get or create competition year record."""
        existing = await conn.fetchrow(
            "SELECT id FROM competition_year WHERE year = $1", year
        )
        if existing:
            return existing["id"]

        current_year = datetime.now().year
        year_record = await conn.fetchrow(
            """
            INSERT INTO competition_year (id, year, is_current) VALUES (gen_random_uuid(), $1, $2)
            RETURNING id
            """,
            year,
            year == current_year,
        )
        return year_record["id"]

    async def _create_game(
        self,
        conn: asyncpg.Connection,
        game_data: Dict[str, Any],
        competition_id: Optional[str],
    ) -> str:
        """Create a new game record."""
        # Parse date
        start_date = self._parse_date(game_data.get("date", ""))

        # Determine status
        status = self._map_status(game_data.get("status", ""))

        # Check if score is complete
        score_complete = self._is_score_complete(
            game_data.get("status", ""), game_data.get("raw_score", "")
        )

        # Get winner - we can't determine winner UUID yet without proper player matching
        # For now, leave winner_id as NULL until player resolution is implemented
        winner_id = None

        # Get club names
        club1_name = game_data.get("club1_name", "")
        club2_name = game_data.get("club2_name", "")

        # Get or create players and link to clubs
        player1_id = await self._get_or_create_player_from_data(
            conn, game_data.get("club1_players", []), club1_name
        )
        player2_id = await self._get_or_create_player_from_data(
            conn, game_data.get("club2_players", []), club2_name
        )

        # Get or create source
        source_id = game_data.get("source_id")
        if not source_id:
            source_id = await self._get_or_create_ctpb_source(conn)

        game = await conn.fetchrow(
            """
            INSERT INTO game (id, 
                competition_id, player1_id, player2_id,
                start_date, status, source_id, external_id,
                scraped_from_url, score_complete, winner_id,
                notes, phase
            )
            VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id
            """,
            competition_id,
            player1_id,
            player2_id,
            start_date,
            status,
            source_id,
            game_data.get("no_renc"),
            game_data.get("scraped_from_url"),
            score_complete,
            winner_id,
            game_data.get("comment"),
            game_data.get("phase"),
        )

        # Create game score record - support both raw_score and score_home/score_away formats
        raw_score = game_data.get("raw_score")
        if not raw_score:
            # Build raw_score from score_home/score_away if available
            score_home = game_data.get("score_home")
            score_away = game_data.get("score_away")
            if score_home is not None and score_away is not None:
                raw_score = f"{score_home}/{score_away}"
            else:
                raw_score = ""
        
        await conn.execute(
            """
            INSERT INTO game_score (id, game_id, raw_score) VALUES (gen_random_uuid(), $1, $2)
            RETURNING id
            """,
            game["id"],
            str(raw_score)[:50] if raw_score else "",
        )

        logger.debug("Created game: %s", game["id"])
        return game["id"]

    async def _update_game(
        self,
        conn: asyncpg.Connection,
        game_id: str,
        game_data: Dict[str, Any],
        competition_id: Optional[str],
    ) -> None:
        """Update an existing game record."""
        status = self._map_status(game_data.get("status", ""))
        score_complete = self._is_score_complete(
            game_data.get("status", ""), game_data.get("raw_score", "")
        )
        winner_id = None
        if score_complete:
            winner_id = self._get_winner_from_score(game_data.get("raw_score", ""))

        update_fields = []
        update_values = []
        param_index = 1

        if competition_id:
            update_fields.append(f"competition_id = ${param_index}")
            update_values.append(competition_id)
            param_index += 1

        update_fields.append(f"status = ${param_index}")
        update_values.append(status)
        param_index += 1

        update_fields.append(f"score_complete = ${param_index}")
        update_values.append(score_complete)
        param_index += 1

        if winner_id:
            update_fields.append(f"winner_id = ${param_index}")
            update_values.append(winner_id)
            param_index += 1

        if game_data.get("scraped_from_url"):
            update_fields.append(f"scraped_from_url = ${param_index}")
            update_values.append(game_data["scraped_from_url"])
            param_index += 1

        if game_data.get("comment"):
            update_fields.append(f"notes = ${param_index}")
            update_values.append(game_data["comment"])
            param_index += 1

        if game_data.get("phase"):
            update_fields.append(f"phase = ${param_index}")
            update_values.append(game_data["phase"])
            param_index += 1

        update_values.append(game_id)

        query = f"""
        UPDATE game
        SET {", ".join(update_fields)}
        WHERE id = ${param_index}
        """

        await conn.execute(query, *update_values)

        # Update game score
        raw_score = str(game_data.get("raw_score", ""))[:50]
        await conn.execute(
            """
            UPDATE game_score
            SET raw_score = $1
            WHERE game_id = $2
            """,
            raw_score,
            game_id,
        )

        logger.debug("Updated game: %s", game_id)

    async def _get_or_create_player_from_data(
        self,
        conn: asyncpg.Connection,
        players: List[Dict[str, Any]],
        club_name: Optional[str] = None,
    ) -> str:
        """Get or create player from player data list (use first player) and link to club."""
        if not players:
            player_id = await self._get_or_create_player(conn, "Inconnu", "", None, None)
            if club_name:
                await self._link_player_to_club(conn, player_id, club_name)
            return player_id

        first_player = players[0]
        player_id = first_player.get("id")
        player_name = first_player.get("name", "")
        license_num = first_player.get("license")
        
        # Check if we already have first_name/last_name from parser (InSpec=0 format)
        first_name = first_player.get("first_name")
        last_name = first_player.get("last_name")
        
        # If not, parse from name field (old format: "NOM Prénom")
        if not first_name or not last_name:
            first_name, last_name = self._parse_player_name(player_name, player_id)

        player_id = await self._get_or_create_player(
            conn, first_name, last_name, player_id, license_num
        )
        
        # Link player to club
        if club_name:
            await self._link_player_to_club(conn, player_id, club_name)
        
        return player_id

    async def _get_or_create_player(
        self,
        conn: asyncpg.Connection,
        first_name: str,
        last_name: str,
        external_id: Optional[str],
        license: Optional[str],
    ) -> str:
        """Get or create player record."""
        # Try by license first
        if license:
            existing = await conn.fetchrow(
                "SELECT id FROM player WHERE license = $1", license[:32]
            )
            if existing:
                return existing["id"]

        # Try by external_id (nickname)
        if external_id:
            existing = await conn.fetchrow(
                "SELECT id FROM player WHERE nickname = $1", external_id
            )
            if existing:
                return existing["id"]

        # Try by name
        existing = await conn.fetchrow(
            "SELECT id FROM player WHERE first_name = $1 AND last_name = $2",
            first_name,
            last_name,
        )
        if existing:
            return existing["id"]

        # Create new player
        player = await conn.fetchrow(
            """
            INSERT INTO player (id, first_name, last_name, nickname, license, is_active)
            VALUES (gen_random_uuid(), $1, $2, $3, $4, $5)
            RETURNING id
            """,
            first_name or "Inconnu",
            last_name or "",
            external_id,
            license[:32] if license else None,
            True,
        )
        return player["id"]

    async def _get_or_create_club(
        self, conn: asyncpg.Connection, name: str
    ) -> str:
        """Get or create club record."""
        if not name or not name.strip():
            # Return a default "unknown" club
            name = "Inconnu"
        
        name = name.strip()
        existing = await conn.fetchrow(
            "SELECT id FROM club WHERE name = $1", name
        )
        if existing:
            return existing["id"]

        club = await conn.fetchrow(
            """
            INSERT INTO club (id, name, short_name, is_active)
            VALUES (gen_random_uuid(), $1, $2, true)
            RETURNING id
            """,
            name,
            name.upper()[:10],
        )
        return club["id"]

    async def _link_player_to_club(
        self,
        conn: asyncpg.Connection,
        player_id: str,
        club_name: str,
        joined_date: Optional[datetime] = None,
    ) -> None:
        """Link a player to a club via player_club_history."""
        if not club_name or not club_name.strip():
            return
        
        club_id = await self._get_or_create_club(conn, club_name)
        
        # Check if link already exists
        existing = await conn.fetchrow(
            """
            SELECT id FROM player_club_history
            WHERE player_id = $1 AND club_id = $2
            """,
            player_id,
            club_id,
        )
        
        if existing:
            return
        
        # Create the link
        await conn.execute(
            """
            INSERT INTO player_club_history (id, player_id, club_id, joined_date)
            VALUES (gen_random_uuid(), $1, $2, $3)
            """,
            player_id,
            club_id,
            joined_date or datetime.now(),
        )

    async def _get_or_create_competition_series(
        self, conn: asyncpg.Connection, name: str, competition_type: str = "tournament"
    ) -> str:
        """Get or create competition series record."""
        if not name or not name.strip():
            return None
        
        name = name.strip()
        existing = await conn.fetchrow(
            "SELECT id FROM competition_series WHERE name = $1", name
        )
        if existing:
            return existing["id"]

        # Generate a code from the name
        code = name.upper()[:10].replace(" ", "").replace("È", "E").replace("É", "E")
        
        series = await conn.fetchrow(
            """
            INSERT INTO competition_series (id, code, name, competition_type)
            VALUES (gen_random_uuid(), $1, $2, $3)
            RETURNING id
            """,
            code,
            name,
            competition_type,
        )
        return series["id"]

    async def _get_or_create_ctpb_source(
        self, conn: asyncpg.Connection
    ) -> str:
        """Get or create CTPB source record."""
        existing = await conn.fetchrow(
            "SELECT id FROM source WHERE url LIKE $1", "%ctpb.euskalpilota.fr%"
        )
        if existing:
            return existing["id"]

        source = await conn.fetchrow(
            """
            INSERT INTO source (id, name, url, is_active)
            VALUES (gen_random_uuid(), $1, $2, $3)
            RETURNING id
            """,
            "CTPB",
            "https://ctpb.euskalpilota.fr",
            True,
        )
        return source["id"]

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string (format: DD/MM/YYYY)."""
        if not date_str:
            return datetime.now()

        try:
            parts = date_str.split("/")
            if len(parts) == 3:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                return datetime(year, month, day)
        except (ValueError, IndexError):
            pass

        return datetime.now()

    def _map_status(self, status: str) -> str:
        """Map scraper status to database status."""
        status_lower = (status or "").lower().strip()
        if status_lower == "completed":
            return "completed"
        elif status_lower == "forfait":
            return "completed"
        elif status_lower == "in_progress":
            return "in_progress"
        else:
            return "scheduled"

    def _is_score_complete(self, status: str, raw_score: str) -> bool:
        """Check if score is complete (not needing rescan)."""
        s = (raw_score or "").strip()
        
        # X/P or P/X patterns are final
        if self._matches_pattern(s, r"^\s*\d+\s*/\s*P\s*$") or self._matches_pattern(
            s, r"^\s*P\s*/\s*\d+\s*$"
        ):
            return True

        if status != "completed":
            return False

        # Complete numeric score
        return self._matches_pattern(s, r"^\d+/\d+$")

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches regex pattern."""
        import re

        return bool(re.match(pattern, text, re.IGNORECASE))

    def _get_winner_from_score(self, raw_score: str) -> Optional[int]:
        """
        Determine winner from raw score.

        Returns:
            1 if player1 wins, 2 if player2 wins, None if tie/invalid
        """
        s = (raw_score or "").strip()

        # X/P pattern - player1 wins
        if self._matches_pattern(s, r"^\s*\d+\s*/\s*P\s*$"):
            return 1

        # P/X pattern - player2 wins
        if self._matches_pattern(s, r"^\s*P\s*/\s*\d+\s*$"):
            return 2

        # Numeric comparison
        match = self._extract_score_parts(s)
        if match:
            p1, p2 = int(match[0]), int(match[1])
            if p1 > p2:
                return 1
            elif p2 > p1:
                return 2

        return None

    def _extract_score_parts(self, raw_score: str) -> Optional[Tuple[str, str]]:
        """Extract score parts from raw score string."""
        import re

        match = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*$", raw_score)
        if match:
            return match.group(1), match.group(2)
        return None

    def _parse_player_name(
        self, full_name: str, player_id: Optional[str]
    ) -> Tuple[str, str]:
        """
        Parse player name from full name string.

        Format is "NOM Prénom" (family name first).
        Returns (first_name, last_name).
        """
        raw = (full_name or "").strip()

        if not raw:
            return "Inconnu", ""

        # License-only (digits only)
        if raw.isdigit():
            return "Joueur", raw

        parts = raw.split()
        if len(parts) == 1:
            return parts[0], ""

        # "NOM Prénom" format → first_name=prénom, last_name=nom
        return " ".join(parts[1:]), parts[0]


# Convenience functions for direct use
async def ingest_scraped_games(
    games: List[Dict[str, Any]], database_url: Optional[str] = None
) -> Dict[str, int]:
    """
    Convenience function to ingest scraped games.

    Args:
        games: List of game dicts from scraper
        database_url: Optional database URL override

    Returns:
        Dict with ingestion counts
    """
    service = IngestionService(database_url)
    try:
        await service.connect()
        return await service.ingest_scraped_games(games)
    finally:
        await service.disconnect()


async def parse_and_create_competition(
    discipline_context: str, database_url: Optional[str] = None
) -> Optional[str]:
    """
    Convenience function to parse and create competition.

    Args:
        discipline_context: Championship name string
        database_url: Optional database URL override

    Returns:
        Competition ID
    """
    service = IngestionService(database_url)
    try:
        await service.connect()
        async with service._pool.acquire() as conn:
            return await service.parse_and_create_competition(conn, discipline_context)
    finally:
        await service.disconnect()
