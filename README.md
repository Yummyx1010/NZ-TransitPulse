# NZ TransitPulse

A production-oriented public transport monitoring and analytics platform for
**Auckland, New Zealand**.

NZ TransitPulse answers two sets of questions:

- **For passengers:** Where is my bus, train or ferry now? When will it arrive? Is this
  route delayed?
- **For people who care about transit data:** Which routes are least reliable? At what
  time of day are delays worst? Is reliability improving?

The project is developed in small, documented phases. See
[`docs/ROADMAP.md`](docs/ROADMAP.md) for the phase plan and
[`docs/WORKFLOW.md`](docs/WORKFLOW.md) for the contribution and commit convention.

> **Current status: Phase 0 - Foundation.** The local development environment,
> configuration, API skeleton, CI and documentation conventions are in place. GTFS
> import, realtime data, the dashboard and analytics arrive in later phases.

## Technology

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic Settings, SQLAlchemy 2, Alembic, PyMySQL |
| Database | MySQL 8 (Docker Compose locally, Amazon RDS later) |
| Frontend | React, TypeScript, Vite, TanStack Query, Leaflet, Recharts (Phase 1+) |
| Quality | pytest, pytest-cov, Ruff, GitHub Actions |
| Deployment | Local first; AWS (ECS Fargate, RDS, S3/CloudFront) post-MVP |

## Quickstart (Phase 0)

Prerequisites: Python 3.12+, Git, and either Docker or a local MySQL 8 server.

1. Clone the repository and create the environment file:

   ```bash
   copy .env.example .env      # Windows (use `cp` on macOS/Linux)
   ```

   Fill in `TP_AT_API_KEY` and the `TP_AT_*_URL` values only after registering at the
   [AT developer portal](https://dev-portal.at.govt.nz). Phase 0 does not need a key.

2. Start MySQL (optional for Phase 0, required from Phase 1):

   ```bash
   docker compose up -d mysql
   ```

3. Set up the backend:

   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate        # Windows (source .venv/bin/activate on macOS/Linux)
   pip install -e ".[dev]"
   pytest -q
   uvicorn app.main:app --reload --port 8000
   ```

4. Check it works:

   ```text
   http://localhost:8000/health          liveness and configuration status
   http://localhost:8000/api/v1/meta     service metadata and data attribution
   http://localhost:8000/docs            interactive OpenAPI documentation
   ```

No database connection is required to boot the API in Phase 0.

## Documentation

| Document | Contents |
| --- | --- |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Phases, deliverables, MVP boundary |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Components, data flow, design decisions |
| [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) | AT feeds, licences, compliance decisions |
| [`docs/WORKFLOW.md`](docs/WORKFLOW.md) | Language, commit policy, phase definition of done |
| [`docs/phases/`](docs/phases/) | One implementation document per phase |
| [`docs/test-reports/`](docs/test-reports/) | One test report per phase |

## Data attribution

Public transport data is sourced from **Auckland Transport** and is licensed under
[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
See [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) for the compliance decisions that
govern historical observation collection.

This is an independent project. It is not affiliated with or endorsed by Auckland
Transport.

## Licence

Code: MIT (to be added when the repository is initialised). Data: CC BY 4.0,
attributed to Auckland Transport.
