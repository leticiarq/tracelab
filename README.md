# TraceLab

Local-first AI-powered cybersecurity lab documentation tool. Organize findings, analyze evidence and generate GitHub-ready Markdown reports.

## Status

TraceLab currently provides a FastAPI backend with persistent management of platforms, categories, and labs, plus the initial React frontend shell. Evidence analysis, Markdown export, and Ollama integration are not implemented yet.

## Requirements

- Ubuntu Linux (or a compatible environment)
- Python 3.11+
- [Poetry 1.8+](https://python-poetry.org/docs/#installation)
- Node.js 20.19+
- npm 10+

No cloud service, paid API, API key, or AI model is required for this setup.

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

Open `http://localhost:5173`. The frontend expects the backend at `http://127.0.0.1:8000` by default.

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

The backend and frontend remain independent. The current milestone is backend-only and adds SQLite persistence and Alembic migrations without changing the frontend. Ollama and the planned `qwen3-vl:2b` model belong to a future milestone; this version neither downloads nor runs AI models.

## License

A project license has not been selected yet.
