-- Rename all tables to lowercase (matching @@map in schema)

-- Core entities
ALTER TABLE "Modality" RENAME TO modality;
ALTER TABLE "Discipline" RENAME TO discipline;
ALTER TABLE "Organizer" RENAME TO organizer;
ALTER TABLE "CompetitionYear" RENAME TO competition_year;
ALTER TABLE "Club" RENAME TO club;
ALTER TABLE "Player" RENAME TO player;
ALTER TABLE "Team" RENAME TO team;
ALTER TABLE "Competition" RENAME TO competition;

-- Junction tables
ALTER TABLE "PlayerClubHistory" RENAME TO player_club_history;
ALTER TABLE "TeamPlayer" RENAME TO team_player;

-- Game entities
ALTER TABLE "Court" RENAME TO court;
ALTER TABLE "Game" RENAME TO game;
ALTER TABLE "GameSidePlayer" RENAME TO game_side_player;
ALTER TABLE "GameScore" RENAME TO game_score;

-- Lookup tables
ALTER TABLE "AgeCategory" RENAME TO age_category;
ALTER TABLE "CompetitionGender" RENAME TO competition_gender;
ALTER TABLE "CompetitionSeries" RENAME TO competition_series;
ALTER TABLE "PlayerStat" RENAME TO player_stat;

-- Scraping tables
ALTER TABLE "Source" RENAME TO source;
ALTER TABLE "ScrapedFilterOption" RENAME TO scraped_filter_option;
ALTER TABLE "ScrapedSpecialty" RENAME TO scraped_specialty;
ALTER TABLE "ScrapingJobRun" RENAME TO scraping_job_run;
