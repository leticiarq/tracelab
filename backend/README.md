# TraceLab backend

FastAPI service for TraceLab. Installation, execution, and test commands are documented in the repository root `README.md`.

Apply database migrations before starting the API:

```bash
poetry run alembic upgrade head
```

The API exposes CRUD resources for platforms, categories, and labs under `/api`, with search, filters, and pagination on the lab collection. SQLite data is kept in `data/tracelab.db` by default.
