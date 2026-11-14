-- NZ TransitPulse - one-time MySQL bootstrap.
-- Run this script in DataGrip (or the mysql client) before Phase 1 migrations.
-- It is the ONLY SQL that must be executed by hand; all tables are created by
-- Alembic via `python -m app.cli.gtfs migrate`.
--
-- Compatible with MySQL 8.x. If you already have a MySQL user you prefer,
-- skip the CREATE USER / GRANT statements and just put that user's credentials
-- into TP_DATABASE_URL in .env.

CREATE DATABASE IF NOT EXISTS transitpulse
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'transitpulse'@'localhost'
  IDENTIFIED BY 'transitpulse';

GRANT ALL PRIVILEGES ON transitpulse.* TO 'transitpulse'@'localhost';
FLUSH PRIVILEGES;

-- Verify the result.
SELECT SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME = 'transitpulse';
