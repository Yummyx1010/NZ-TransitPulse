# Development Workflow

## Language

All repository content is written in **English**: source code, comments, docstrings,
identifiers, UI copy, documentation, commit messages, branch names, and test names.
This project targets Auckland, New Zealand, so user-facing text uses New Zealand English
conventions and the `Pacific/Auckland` time zone.

## Commit policy

The assistant **never runs `git commit`, `git push`, `git tag` or any other write
operation against the remote repository**. At the end of each phase the assistant
provides a block of exact commands; the repository owner reviews and runs them manually.

Suggested convention:

```text
branch:  phase/00-foundation
commit:  feat(foundation): bootstrap local development environment
tag:     phase-00
```

Commit messages follow Conventional Commits (`feat`, `fix`, `docs`, `test`, `chore`,
`refactor`, `ci`). One phase equals one focused commit plus, if needed, follow-up fix
commits before the phase tag.

## Definition of done for a phase

1. The feature runs locally with the documented commands.
2. Code is covered by automated tests; all tests pass.
3. `docs/phases/PHASE-XX-<slug>.md` is written (scope, design decisions, files changed,
   API or schema changes, how to verify, known limitations, next phase).
4. `docs/test-reports/PHASE-XX.md` is written (environment, exact commands, results,
   coverage, failures and resolutions).
5. `README.md` and `ROADMAP.md` reflect the new status, including a new row in the
   README phase index linking the implementation document and test report.
6. No secrets, API keys, database dumps or raw feed payloads are staged.
7. Manual commit commands are provided to the repository owner.

## Documentation layout

```text
README.md                              Project front page, quickstart, status
docs/ROADMAP.md                        Phase plan and MVP boundary
docs/ARCHITECTURE.md                   System design and key decisions
docs/DATA_SOURCES.md                   AT feeds, licences, compliance decisions
docs/WORKFLOW.md                       This file
docs/phases/_TEMPLATE.md               Template for a phase implementation document
docs/phases/PHASE-XX-<slug>.md         One implementation document per phase
docs/test-reports/PHASE-XX.md          One test report per phase
```

## Test report format

Every test report records: date, OS, runtime versions, exact commands, pass/fail counts,
coverage, and an explicit note about anything that could not be verified locally.
Results are copied from an actual run, never estimated.

## Reproducibility rules

- Configuration comes from environment variables (`.env` locally, `.env.example` as the
  documented template). `.env` is never committed.
- Dependencies are pinned by a version manifest in both `backend/` and `frontend/`.
- Database schema changes are made through migrations, never by hand.
- Every phase adds tests to the existing suite; the suite must stay green.
