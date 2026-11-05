# TraceLab

Local-first cybersecurity lab documentation tool. Organize lab notes, manage evidence and generate GitHub-ready Markdown reports.

## Overview

Security students and practitioners often document labs across scattered notes, screenshots, request files, and manually assembled reports. TraceLab centralizes that workflow in a local web application: catalog a lab, record findings and notes, arrange supporting evidence, review the generated Markdown, and export a repository-ready ZIP.

TraceLab runs locally and does not require a hosted service, API key, or external account.

## Features

- Create, edit, filter, and delete labs organized by platform, category, status, and difficulty.
- Keep free-form resolution notes and save them explicitly.
- Record zero, one, or multiple findings, with optional manually entered CVSS data.
- Upload, preview, download, label, associate, reorder, and delete PNG, JPEG, WebP, TXT, and HTTP evidence.
- Generate and edit one Markdown report per lab, with a safe in-app preview.
- Review warnings and export a ZIP containing `README.md` and selected evidence.
- Persist structured data in local SQLite and evidence in the local filesystem.

## Tech stack

- Backend: Python 3.11+, FastAPI, SQLAlchemy, Alembic, Pydantic Settings, Uvicorn
- Frontend: React 18, TypeScript, Vite, Tailwind CSS
- Storage: SQLite and local evidence files
- Tests: pytest, HTTPX, Vitest, Testing Library, jsdom

## Architecture

The React frontend communicates with the FastAPI backend over a local HTTP API. The backend applies validation and workflow rules, stores structured records in SQLite, and writes uploaded evidence outside the frontend's public directory. Alembic owns schema migrations. Reports are generated and saved in the database; ZIP files are produced on demand and downloaded by the browser.

See [Architecture](docs/architecture.md) for component and data-flow details.

## Requirements

- Ubuntu Linux or a compatible Linux environment
- Python 3.11+
- [Poetry 1.8+](https://python-poetry.org/docs/#installation)
- Node.js 20.19+
- npm 10+

## Installation

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

The defaults store the database at `backend/data/tracelab.db` and evidence under `backend/data/evidences/`. See [Installation](docs/installation.md) for a fuller Ubuntu walkthrough.

## Running locally

Start the backend from the repository root:

```bash
cd backend
poetry run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, start the frontend:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`. The API health endpoint is `http://127.0.0.1:8000/health`, and interactive API documentation is at `http://127.0.0.1:8000/docs`.

## Usage

1. Create or select a platform and category, then create a lab.
2. Add the source URL, difficulty, status, and other lab information.
3. Write resolution notes and save them.
4. Add findings when the lab contains vulnerabilities to document.
5. Upload synthetic or reviewed evidence, add captions, and arrange it in report order.
6. Generate the lab Markdown report.
7. Review and, if needed, edit the Markdown and inspect its preview.
8. Save changes, confirm the sensitive-data review, select the required evidence, and export the ZIP.

See [Usage](docs/usage.md). A fictional output and synthetic evidence are under [`examples/demo-lab`](examples/demo-lab/README.md).

## Generated output

```text
lab-name/
├── README.md
└── evidence/
    ├── image-01.png
    └── evidence-02.http
```

## Testing

```bash
cd backend
poetry run pytest
```

```bash
cd frontend
npm test
npm run build
```

## Security and privacy

TraceLab is local-first: the default services bind to loopback, structured data stays in SQLite, and evidence stays in a local data directory ignored by Git. The backend restricts trusted hosts and browser origins, validates evidence content and size, stores files under generated names, prevents duplicate evidence per lab, and validates export paths and archive size. The preview renders supported Markdown as React text rather than injecting HTML.

Local-first does not mean access-controlled. TraceLab currently has no user authentication or encryption at rest. Before sharing an export, review the report and every evidence file for tokens, cookies, passwords, personal data, private targets, and other secrets. See [Security](docs/security.md).

## Limitations

- Intended for a single trusted user on a local machine; there are no accounts or permissions.
- No encryption at rest, synchronization, cloud backup, or built-in repository publishing.
- Markdown preview supports headings, paragraphs, bullets, fenced code, and local report images; it is not a full GitHub Markdown renderer.
- Evidence is limited to PNG, JPEG, WebP, UTF-8 TXT, and HTTP files and is capped by configured count and size limits.
- Report generation creates one `README.md` per lab and does not automatically save after manual editing.
- Sensitive-content warnings use a small pattern set and cannot replace manual review.

## Roadmap

Potential future work includes richer GitHub-flavored Markdown preview, backup and restore tooling, configurable report templates, accessibility improvements, broader automated tests, and optional export layouts. These items are proposals, not current features; see [Roadmap](docs/roadmap.md).

## License

No license has been selected. Until a license is added, the repository does not grant general permission to copy, modify, or redistribute the project.
