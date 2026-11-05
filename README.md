# TraceLab

Local-first cybersecurity lab documentation tool. Organize findings, manage evidence and generate GitHub-ready Markdown reports.

## Status

TraceLab provides a FastAPI backend with persistent management of platforms, categories, labs, multiple vulnerability findings, evidence, optional CVSS records and Markdown reports, plus a responsive React interface.

## Requirements

- Ubuntu Linux (or a compatible environment)
- Python 3.11+
- [Poetry 1.8+](https://python-poetry.org/docs/#installation)
- Node.js 20.19+
- npm 10+

No cloud service, paid API, or API key is required.

## Project structure

```text
tracelab/
├── backend/      # FastAPI, settings, SQLAlchemy, and backend tests
├── frontend/     # React, TypeScript, Vite, Tailwind CSS, and frontend tests
├── docs/         # Architecture and project documentation
├── scripts/      # Future local automation scripts
├── .env.example
├── .gitignore
└── README.md
```

See [docs/architecture.md](docs/architecture.md) for the initial architecture decisions.

## Configuration

Create a local environment file from the example:

```bash
cp .env.example .env
```

The defaults are suitable for local development. Relative data paths are resolved from stable project directories rather than the shell's current directory, so the SQLite database remains at `backend/data/tracelab.db`. Local `.env` files, database files, and evidence files are ignored by Git.

## Backend

Install dependencies and start the API:

```bash
cd backend
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check the health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`. Findings are exposed under `/api/labs/{lab_id}/findings`; evidence remains owned by the lab and may optionally reference one finding.

Before upgrading an existing database, follow [the backup procedure](docs/database-backup.md), then run `poetry run alembic upgrade head` from `backend/`.

Run backend tests:

```bash
cd backend
poetry run pytest
```

## Frontend

Install dependencies and start the development server:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend expects the backend at `http://127.0.0.1:8000` by default. Set `VITE_API_URL` to use a different API address.

The web interface includes:

- progress metrics and recent laboratories on the dashboard;
- searchable, filterable, paginated laboratory management;
- laboratory creation and editing, with inline platform and category creation;
- detailed information, notes, vulnerabilities, evidence, and report tabs;
- zero, one or many findings per lab, with optional manually supplied CVSS data;
- general evidence or evidence associated with a specific finding;
- explicit note saving with unsaved-change feedback.

Run frontend tests:

```bash
cd frontend
npm test
```

Create a production build:

```bash
cd frontend
npm run build
```

## Development scope

The backend and frontend remain independently executable and communicate through the local HTTP API.

## License

A project license has not been selected yet.
