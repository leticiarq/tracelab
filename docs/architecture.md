# Initial architecture

## Goals

The initial architecture favors local execution, explicit boundaries, and a small dependency footprint. The backend and frontend are independent projects so each can be installed, tested, and run separately.

## Backend

- `app/api/routes`: HTTP endpoints grouped by responsibility.
- `app/core`: environment-backed application configuration.
- `app/db`: SQLAlchemy base, engine, and session factory for SQLite.
- `tests`: API tests using pytest and FastAPI's test client.

FastAPI exposes only `GET /health` in this milestone. SQLAlchemy is configured but no domain models or migrations are introduced before they are needed.

## Frontend

- `src`: React components and application entry point.
- `src/test`: shared Vitest setup.
- Vite provides the development and build tooling.
- Tailwind CSS provides local styling without a component framework.

No router or state-management library is included because the current single-screen setup does not require either.

## Local data and AI

SQLite is the planned persistence mechanism, with the database kept under `backend/data` and excluded from version control. Ollama with `qwen3-vl:2b` is planned for a future milestone and is not integrated or downloaded in this setup.

## Security baseline

- The API and frontend bind to loopback addresses by default.
- CORS allows only the configured local frontend origin and does not enable credentials.
- Secrets and local data are excluded from version control.
- No external authentication, telemetry, paid API, or hosted dependency is configured.
