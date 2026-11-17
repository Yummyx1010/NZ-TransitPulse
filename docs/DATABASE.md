# Database Setup and Schema

## 1. One-time setup in DataGrip

NZ TransitPulse uses a **local MySQL 8 server**. Docker is not required.

1. In DataGrip, open your local MySQL connection (usually `localhost:3306` with your
   own admin user).
2. Open `sql/001_create_database.sql` from this repository.
3. Make sure the editor's target schema/console is the server connection, **not** a
   specific database (the script creates the database itself).
4. Run the whole script (`Ctrl+Enter` / `Execute`). Expected result: a row for
   `transitpulse` with `utf8mb4` / `utf8mb4_unicode_ci`.
5. Find out which account DataGrip is using (see below), then edit `.env` so
   `TP_DATABASE_URL` matches it:

   ```text
   mysql+pymysql://<your-user>:<your-password>@127.0.0.1:3306/transitpulse
   ```

   The simplest option is to reuse the account you already have (often `root`). In
   that case the `CREATE USER` / `GRANT` statements in the script are unnecessary.
   `127.0.0.1` is used rather than `localhost` so PyMySQL always connects over TCP.

**This is the only SQL you ever need to run by hand.** Everything else is managed by
Alembic.

### Which account am I using?

`localhost` is a **host**, not a username. A MySQL account is a `user@host` pair such as
`root@localhost` or `transitpulse@localhost`. To see yours, open a query console on the
DataGrip connection and run:

```sql
SELECT CURRENT_USER() AS mysql_account, USER() AS connection_identity;
SELECT user, host FROM mysql.user ORDER BY user, host;
```

The first result is the account DataGrip is connected with. Its username and password
are exactly what goes into `TP_DATABASE_URL`; the password is stored in your DataGrip
connection settings (right-click the connection, then Properties), never in this
repository.

The URL shape is `mysql+pymysql://USER:PASSWORD@HOST:PORT/DATABASE`. URL-encode special
characters (`@`, `:`, `/`, `#`, `?`) in a password.

One trap: `CREATE USER IF NOT EXISTS` does **not** reset the password of an account
that already exists. If `transitpulse` was created earlier with another password, keep
`TP_DATABASE_URL` consistent with it, or run:

```sql
ALTER USER 'transitpulse'@'localhost' IDENTIFIED BY '<the password used in .env>';
FLUSH PRIVILEGES;
```

## 2. Verify and migrate

**First activate the Python environment that has the dependencies.** A `venv` or a
conda environment both work; the base system/Anaconda `python` will fail with
`ModuleNotFoundError`:

```bat
cd backend
.venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m app.cli.gtfs check-db
python -m app.cli.gtfs migrate
```

With conda, replace the activation line with `conda activate transitpulse` (after
`conda create -n transitpulse python=3.12`); the prompt then shows `(transitpulse)`.
Alternatively skip activation and call an interpreter directly:
`.venv\Scripts\python.exe -m app.cli.gtfs check-db`.

Optional integration test against this MySQL server (the quotes matter on Windows cmd,
otherwise `set VAR=1 && ...` leaves a trailing space in the value):

```bat
set "TP_RUN_MYSQL_INTEGRATION=1"
.venv\Scripts\python.exe -m pytest tests/integration -m integration
```

`check-db` prints the MySQL version and the list of tables. `migrate` applies all Alembic
revisions: `0001_initial_gtfs_schema.py` (six core tables) and
`0002_route_shape_points.py` (the `shape_points` table plus
`gtfs_feeds.shape_point_count`) and `0003_service_calendars.py` (the
`service_calendars` / `service_calendar_dates` tables and their feed counts), as well as
Alembic's own `alembic_version` table.

After applying `0002` or `0003` to a database that already contains a feed, re-import once
so the existing data gains its geometry and service calendars. The checksum is unchanged,
so `--force` is required:

```bat
python -m app.cli.gtfs load --file data\gtfs\gtfs-<hash>.zip --force
```

DataGrip will not show new tables automatically — right-click the `transitpulse` schema
and choose **Refresh** (or press `Ctrl+F5` in the Database tool window).

Troubleshooting:

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'pydantic_settings'` | The base system/Anaconda `python` was used instead of the environment holding the requirements | Activate `.venv` or the conda env, then `python -m pip install -e ".[dev]"`; or use `.venv\Scripts\python.exe` |
| `1045 Access denied for user 'transitpulse'@'localhost'` | The account exists but its password does not match `TP_DATABASE_URL` (`CREATE USER IF NOT EXISTS` never resets an existing password) | Easiest: point `TP_DATABASE_URL` at your own account (e.g. `root`). Or `ALTER USER` to reset the dedicated account's password |
| `Unknown database 'transitpulse'` | Step 1 was not executed | Run `sql/001_create_database.sql` |
| `Can't connect to MySQL server` | MySQL service is stopped or a different port is used | Start the service, check `TP_DATABASE_URL` |
| `Table 'gtfs_feeds' doesn't exist` | `migrate` has not been run | `python -m app.cli.gtfs migrate` |
| `Table ... already exists` | The database was previously created by hand | Run `alembic stamp head` only if the schema already matches, otherwise drop the tables and re-run `migrate` |

## 3. Schema (Phase 1 + 1B + Phase 3 calendars)

All GTFS tables include `feed_id` as part of their primary key. `gtfs_feeds` records
every import and marks exactly one row as active.

| Table | Primary key | Purpose |
| --- | --- | --- |
| `gtfs_feeds` | `id` | Import history, SHA-256 checksum, counts, `is_active` |
| `agencies` | `feed_id`, `agency_id` | Operators |
| `routes` | `feed_id`, `route_id` | Bus / rail / ferry routes, colours, `route_type` |
| `stops` | `feed_id`, `stop_id` | Stop names, codes, coordinates |
| `trips` | `feed_id`, `trip_id` | Trips linked to routes, services and `shape_id` |
| `stop_times` | `feed_id`, `trip_id`, `stop_sequence` | Scheduled arrival/departure, raw GTFS time and seconds since service-day midnight |
| `shape_points` | `feed_id`, `shape_id`, `shape_pt_sequence` | Ordered points of the real drawn route geometry from `shapes.txt` |
| `service_calendars` | `feed_id`, `service_id` | Weekly operating pattern and valid date range from `calendar.txt` |
| `service_calendar_dates` | `feed_id`, `service_id`, `date` | Added (1) / removed (2) service exceptions from `calendar_dates.txt` |

Indexes: `ix_gtfs_feeds_checksum`, `ix_routes_feed_type`,
`ix_stops_feed_position`, `ix_trips_feed_route`, `ix_stop_times_feed_stop`.
`shape_points` uses its composite primary key as the lookup path, already ordered by
`shape_pt_sequence`.

Design notes:

- **Feed-version staging:** a new bundle is inserted under a fresh `feed_id` in one
  transaction, then `is_active` is flipped and the previous version's child rows are
  removed. Readers never observe a partially imported network. Feed metadata rows are
  retained as an import history.
- **Idempotence:** re-importing a bundle with the same SHA-256 checksum is a no-op
  unless `--force` is passed.
- **Times after midnight:** GTFS allows `25:10:00`. Both the raw string and the
  normalised second count are stored.
- **Time zone:** all timestamps are stored in UTC; the UI will render
  `Pacific/Auckland`.
- **No foreign keys between child tables:** bulk loading hundreds of thousands of rows
  is faster without them, and integrity is guaranteed by the loader transaction.

Deferred to later phases: `transfers`, fare tables, realtime snapshots and delay
observations. `shapes.txt` was added in Phase 1B for real route geometry; `calendar.txt`
and `calendar_dates.txt` were added in Phase 3 to filter arrivals to today's service.

## 4. Loading data

```bat
python -m app.cli.gtfs load --download
python -m app.cli.gtfs status
```

The loader downloads `https://gtfs.at.govt.nz/gtfs.zip`, validates the five required
files (`agency.txt`, `routes.txt`, `stops.txt`, `trips.txt`, `stop_times.txt`), reads the
optional `shapes.txt`, `calendar.txt` and `calendar_dates.txt`, skips invalid or duplicate
rows, and inserts in batches of 5,000 rows. The download is stored under a content-addressed
filename in `data/gtfs/` (gitignored). If `shapes.txt` is absent the map falls back to
ordered `stop_times` and labels the result as an approximate route; if calendars are
absent the ETA endpoint keeps the legacy unfiltered behaviour and says so in its note.

To import a file you downloaded manually:

```bat
python -m app.cli.gtfs load --file C:\path\to\gtfs.zip
```

## 5. Schema changes

Never edit tables by hand. Add an Alembic revision under
`backend/migrations/versions/` and run `python -m app.cli.gtfs migrate`. The test
`test_initial_migration_creates_every_model_table` protects against drift between the
ORM models and the migration.
