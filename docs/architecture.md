# Initial architecture

## Goals

The initial architecture favors local execution, explicit boundaries, and a small dependency footprint. The backend and frontend are independent projects so each can be installed, tested, and run separately.

## Backend

- `app/api/routes`: HTTP endpoints grouped by responsibility.
- `app/core`: environment-backed application configuration.
- `app/db`: SQLAlchemy base, engine, and session factory for SQLite.
- `app/models`: persistent platform, category, and lab entities.
- `app/schemas`: Pydantic request, response, and pagination contracts.
- `app/services`: CRUD rules, relation validation, filtering, and collision-safe slugs.
- `alembic`: versioned database schema migrations.
- `tests`: API tests using pytest and FastAPI's test client.

FastAPI exposes `GET /health` and CRUD collections under `/api/platforms`, `/api/categories`, and `/api/labs`. Lab IDs are database-generated and remain stable when a title changes. Human-readable slugs are normalized and receive numeric suffixes on collisions.

## Frontend

- `src`: React components and application entry point.
- `src/test`: shared Vitest setup.
- Vite provides the development and build tooling.
- Tailwind CSS provides local styling without a component framework.

No router or state-management library is included because the current single-screen setup does not require either.

## Local data

SQLite is the persistence mechanism, with the database kept under `backend/data` and excluded from version control. Alembic owns schema creation and upgrades. Tests override the application session with a separate temporary SQLite database.

Evidence is stored under `backend/data/evidences` with generated filenames and outside the frontend's public tree. Relative database and evidence paths are normalized against stable project directories, independently of the process working directory.

## Security baseline

- The API and frontend bind to loopback addresses by default.
- CORS allows only the configured local frontend origin and does not enable credentials.
- Mutating browser requests from unconfigured origins and cross-site fetch contexts are rejected, and trusted Host values protect the loopback service from DNS rebinding.
- Evidence uploads enforce extension, content signature, UTF-8/control-character, count, size, duplicate, and traversal checks.
- Markdown preview is rendered as React text nodes; exports reject unsafe evidence paths, external images, active HTML, cross-lab files, and oversized archives.
- Secrets and local data are excluded from version control.
- No external authentication, telemetry, paid API, or hosted dependency is configured.
