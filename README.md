# TraceLab

Local-first AI-powered cybersecurity lab documentation tool. Organize findings, analyze evidence and generate GitHub-ready Markdown reports.

## Status

TraceLab provides a FastAPI backend with persistent management of platforms, categories, labs, evidence and Markdown reports, plus an optional local Ollama integration and a responsive React interface.

## Requirements

- Ubuntu Linux (or a compatible environment)
- Python 3.11+
- [Poetry 1.8+](https://python-poetry.org/docs/#installation)
- Node.js 20.19+
- npm 10+

No cloud service, paid API, API key, or AI model is required for the core application. Ollama is optional and the rest of TraceLab remains usable when it is absent or disabled.

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

## Local AI with Ollama

The optional AI integration uses only the local Ollama API at `http://127.0.0.1:11434` by default. It does not initiate model downloads. Open **Configurações de IA** in the web interface to inspect the server, select an installed model, test the connection, test text generation, or disable AI.

The default model name is `qwen3-vl:2b`, but it is configurable. Image requests are enabled only when Ollama explicitly reports the selected model's `vision` capability. See [docs/ollama.md](docs/ollama.md) for Ubuntu installation, model setup, configuration, API endpoints and troubleshooting.

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
- local AI settings with Ollama status, installed models and connection/generation tests.

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

The backend and frontend remain independently executable and communicate through the local HTTP API. The AI infrastructure is independent from evidence and report services; Smart Evidence and intelligent report generation are intentionally outside this milestone.

## License

A project license has not been selected yet.
