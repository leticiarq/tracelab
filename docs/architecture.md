# Architecture

## System overview

TraceLab is a local web application split into independently installable frontend and backend projects.

```text
Browser (React/Vite)
        |
        | local JSON/multipart HTTP
        v
FastAPI routes -> service rules -> SQLAlchemy -> SQLite
                         |
                         +--------------------> local evidence files
                         |
                         +--------------------> in-memory ZIP response
```

The browser defaults to `http://localhost:5173`; the API defaults to `http://127.0.0.1:8000`. There is no server-side rendering or separate worker process.

## Backend

- `app/api/routes`: endpoints for health, platforms, categories, labs, findings, evidence, and reports.
- `app/services`: relation checks, slugs, file handling, report generation, and ZIP validation.
- `app/schemas`: Pydantic request and response contracts.
- `app/models`: SQLAlchemy persistence models.
- `app/core`: environment-backed settings and path resolution.
- `app/db`: engine, sessions, and SQLite foreign-key activation.
- `alembic`: ordered schema migrations.
- `tests`: API, configuration, migration, export, and security-focused tests.

Platforms contain categories and labs. A lab owns ordered findings, ordered evidence, and at most one saved report. Each finding may have one manually supplied CVSS assessment. Evidence always belongs to a lab and may optionally reference a finding in that same lab. Deleting a finding keeps its evidence and clears the association; deleting a lab removes its database children and stored evidence files.

## Frontend

The React application provides dashboard metrics, lab forms and filters, detail tabs, evidence management, finding management, and report editing. It uses a small internal navigation layer rather than a routing dependency. API access is centralized in `frontend/src/api.ts`.

Notes and report edits use explicit Save actions. Both surfaces warn about unsaved browser changes. Report preview is a deliberately limited renderer that creates React elements for supported Markdown constructs; it does not inject generated HTML.

## Persistence and files

SQLite is the default structured store at `backend/data/tracelab.db`. Alembic, not application startup, creates and upgrades the schema. Uploaded evidence is stored separately under `backend/data/evidences/` using generated filenames and restrictive file permissions. Metadata preserves the original filename, content type, size, SHA-256 digest, caption, step, and display order.

The database and evidence directory are ignored by Git. Back up both together; see [Database backup](database-backup.md).

## Report and export flow

Report generation reads the current lab, findings, CVSS records, and evidence ordering, then stores Markdown plus an evidence manifest. Regeneration is explicit because it replaces manual report edits. Export validates the saved report, selected evidence, manifest, references, active HTML, paths, duplicates, and total uncompressed input size before producing an in-memory ZIP.

The export contains one root directory, one `README.md`, and an `evidence/` directory when files are selected. It does not write an export archive to the server filesystem.

## Trust boundaries

TraceLab assumes a trusted local user and has no authentication or authorization model. Loopback binding, trusted-host checks, configured CORS origins, and cross-site mutation rejection reduce exposure to other sites and DNS rebinding. File and archive validation limits common upload and path attacks. These controls do not make it appropriate for an untrusted multi-user network without additional protections.
