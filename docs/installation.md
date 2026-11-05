# Installation on Ubuntu

## Prerequisites

```bash
sudo apt update
sudo apt install -y git python3 python3-venv pipx curl
pipx ensurepath
pipx install 'poetry>=1.8'
```

Install Node.js 20.19 or newer and npm 10 or newer using your preferred trusted Node.js distribution. Open a new shell if `pipx` changed the PATH, then verify:

```bash
python3 --version
poetry --version
node --version
npm --version
```

## Project setup

```bash
git clone <repository-url> tracelab
cd tracelab
cp .env.example .env
cd backend
poetry install
poetry run alembic upgrade head
cd ../frontend
npm install
cd ..
```

`poetry install` uses the backend lockfile, and `npm install` uses the frontend lockfile. Run Alembic from `backend/`, where its configuration is located.

## Configuration

Defaults in `.env.example` are ready for loopback-only development:

- `TRACELAB_DATABASE_URL`: SQLite URL; the default resolves to `backend/data/tracelab.db`.
- `TRACELAB_EVIDENCE_STORAGE_PATH`: local evidence directory.
- `TRACELAB_EVIDENCE_MAX_FILE_SIZE`: per-file limit in bytes.
- `TRACELAB_EVIDENCE_MAX_FILES_PER_UPLOAD` and `TRACELAB_EVIDENCE_MAX_FILES_PER_LAB`: count limits.
- `TRACELAB_REPORT_EXPORT_MAX_SIZE`: report plus selected-evidence limit.
- `TRACELAB_CORS_ORIGINS` and `TRACELAB_ALLOWED_HOSTS`: accepted browser origins and hosts.
- `VITE_API_URL`: backend URL used by the frontend.

Keep `.env` local; it is ignored by Git.

## Start and verify

Terminal 1:

```bash
cd tracelab/backend
poetry run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd tracelab/frontend
npm run dev
```

```bash
curl http://127.0.0.1:8000/health
```

The expected response is `{"status":"ok"}`. Then open `http://localhost:5173`.

## Updating and troubleshooting

Before migrations, stop the application and follow [Database backup](database-backup.md). Then run `poetry install` and `poetry run alembic upgrade head` from `backend/`, and `npm install` from `frontend/`.

- If the frontend cannot connect, confirm the backend is running and `VITE_API_URL` matches it.
- If the browser receives a host or origin rejection, use the documented localhost addresses or deliberately update both settings.
- For schema errors, run `poetry run alembic current` and `poetry run alembic upgrade head` from `backend/`.
