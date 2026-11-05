# TraceLab

Local-first cybersecurity lab documentation tool. Organize findings, manage evidence and generate GitHub-ready Markdown reports.

## Status

TraceLab provides a FastAPI backend with persistent management of platforms, categories, labs, evidence and Markdown reports, plus a responsive React interface.

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

The defaults are suitable for local development. The SQLite database is stored in `backend/data/tracelab.db`. Local `.env` files and database files are ignored by Git.

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

Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`. The lab management resources are exposed under `/api/platforms`, `/api/categories`, and `/api/labs`.

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
- detailed information, notes, evidence, and report tabs;
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
