# Test Report: Phase 00 - Foundation

- **Date:** 2026-11-14
- **Result:** **PASS** (12 tests, 100% statement coverage, HTTP smoke test passed)
- **Phase document:** `docs/phases/PHASE-00-foundation.md`

## 1. Environment

| Item | Value |
| --- | --- |
| OS | Windows (win32), `cmd` shell |
| Python | 3.12.7 |
| Virtual environment | `backend/.venv` (created for this phase) |
| pip | 26.3 |
| Node.js / npm | v24.14.0 / 11.9.0 (not used in Phase 0) |
| Docker | Not installed in this environment |
| MySQL server | Not running (not required in Phase 0) |
| Git | 2.55.0.windows.3 (repository not yet initialised) |

Installed backend versions (from `pip list --format=freeze`):

```text
fastapi==0.162.7          starlette==1.10.0
pydantic==2.14.3          pydantic-settings==2.16.3
SQLAlchemy==2.1.8         PyMySQL==1.2.4            alembic==1.20.1
httpx==0.28.1             uvicorn==0.54.0
pytest==8.4.2             pytest-cov==6.3.0         ruff==0.17.5
```

## 2. Commands and results

### 2.1 Dependency installation

```text
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Result: PASS. Editable install of `nz-transitpulse-backend==0.1.0` succeeded.

### 2.2 Lint

```text
.venv\Scripts\python.exe -m ruff check .
```

```text
All checks passed!
```

### 2.3 Unit and API tests

```text
.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

```text
............                                                             [100%]

Name                   Stmts   Miss  Cover   Missing
----------------------------------------------------
app\__init__.py            1      0   100%
app\api\__init__.py        0      0   100%
app\api\ops.py            28      0   100%
app\core\__init__.py       0      0   100%
app\core\config.py        34      0   100%
app\main.py               14      0   100%
----------------------------------------------------
TOTAL                     77      0   100%
12 passed, 1 warning in 0.18s
```

Warning (non-blocking): `StarletteDeprecationWarning: Using httpx with
starlette.testclient is deprecated; install httpx2 instead.` Originates from the
installed FastAPI/Starlette `TestClient`, not from project code.

### 2.4 Test cases

| # | Test | Result |
| --- | --- | --- |
| 1 | `test_health_returns_ok` | PASS |
| 2 | `test_health_never_exposes_the_api_key` | PASS |
| 3 | `test_meta_reports_region_timezone_and_attribution` | PASS |
| 4 | `test_cors_allows_only_the_configured_origin` | PASS |
| 5 | `test_openapi_documentation_is_available` | PASS |
| 6 | `test_unknown_route_returns_404` | PASS |
| 7 | `test_defaults_are_safe_for_local_development` | PASS |
| 8 | `test_cors_origins_are_split_and_trimmed` | PASS |
| 9 | `test_realtime_requires_key_and_all_three_feed_urls` | PASS |
| 10 | `test_poll_interval_below_feed_refresh_rate_is_rejected` | PASS |
| 11 | `test_environment_variables_use_tp_prefix` | PASS |
| 12 | `test_get_settings_is_cached` | PASS |

### 2.5 Live HTTP smoke test

Started a real `uvicorn app.main:app --port 8765` process and issued HTTP requests
against it:

```text
GET /health       200 {'status': 'ok', 'environment': 'local', 'version': '0.1.0',
                       'realtime_feed': 'not_configured'}
GET /api/v1/meta  200 Data source: Auckland Transport, licensed under CC BY 4.0
SMOKE TEST: PASS
```

The process was terminated after the check.

### 2.6 Configuration file validation

`docker-compose.yml` and `.github/workflows/ci.yml` were parsed with PyYAML to confirm
valid YAML syntax:

```text
docker-compose.yml        -> OK, top-level keys: ['services', 'volumes']
.github/workflows/ci.yml  -> OK, top-level keys: ['name', True, 'jobs']
```

PyYAML implements YAML 1.1 and reports the `on` key as `True`; GitHub Actions uses
YAML 1.2, where `on` is a normal key. This is a parser artefact, not a file error.

## 3. Issues found and resolved

| # | Issue | Resolution |
| --- | --- | --- |
| 1 | `pip install -e .` failed: `readme = "../README.md"` pointed outside the build root (`DistutilsOptionError`) | Removed the `readme` field from `backend/pyproject.toml`; the root `README.md` is referenced from docs instead |
| 2 | Ruff `E501` (101 > 100) in `app/api/ops.py` | Wrapped the `Field(description=...)` call over multiple lines |
| 3 | Starlette `httpx` deprecation warning | Recorded, not suppressed; no functional impact |

## 4. Not verified in this phase

| Item | Reason | Planned verification |
| --- | --- | --- |
| `docker compose up -d mysql` | Docker is not installed on this machine | Phase 1, when the schema and DB connection are added |
| GitHub Actions workflow | No remote push has been made | First push of Phase 0 |
| AT GTFS-Realtime endpoints, key and quota | No developer portal subscription key yet | Phase 2 |
| React / Vite frontend | Introduced in Phase 1 | Phase 1 test report |
| MySQL connectivity and migrations | Introduced in Phase 1 | Phase 1 test report |

## 5. Conclusion

Phase 0 meets its definition of done: the API boots locally, all 12 automated tests
pass with 100% statement coverage, the lint check is clean, the documentation set and
phase conventions are in place, and no secrets are present in the repository. Phase 1
can proceed.
