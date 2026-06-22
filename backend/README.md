# Notes Management API — Infrastructure Scaffolding

Production-ready FastAPI backend scaffolding for a Notes Management API.
**This repo contains infrastructure only — no business logic.** Endpoints
exist as empty routers with a `/health` stub each, ready for real
implementation.

## Stack

- **FastAPI** — async web framework
- **PostgreSQL** + **SQLAlchemy 2.0 (async, asyncpg)** — database layer
- **Redis** (async client) — connection wired at startup/shutdown, no caching logic yet
- **Alembic** — migrations, async-engine compatible `env.py`
- **Docker / docker-compose** — API + Postgres + Redis, with healthchecks

## Project structure

```
app/
├── core/                 # settings (.env loader) + logging config
├── db/                   # SQLAlchemy session/engine, declarative Base, Redis client
├── models/                # (empty) SQLAlchemy ORM models go here
├── schemas/                # (empty) Pydantic request/response schemas go here
├── services/                # (empty) business logic / service layer goes here
├── api/
│   ├── deps.py            # shared FastAPI dependencies (get_db, get_redis)
│   └── v1/
│       ├── router.py       # aggregates all endpoint routers
│       └── endpoints/        # auth, notes, users, tags, imports (empty routers)
├── middleware/             # request logging + global exception handling
└── main.py                # app factory, lifespan, middleware/router wiring
tests/                     # smoke tests for app boot / health endpoints
alembic/                   # migration environment (async-aware env.py)
logs/                      # rotating file logs written here at runtime
```

## Running locally with Docker (recommended)

```bash
cp .env.example .env   # adjust values if needed
docker-compose up --build
```

This starts three services:
- `db` — Postgres 16, with a healthcheck (`pg_isready`)
- `redis` — Redis 7, with a healthcheck (`redis-cli ping`)
- `api` — FastAPI app, waits for `db`/`redis` to be healthy before starting

Once up:
- App root: http://localhost:8000/
- Health check: http://localhost:8000/health
- Swagger docs: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

Each router also exposes its own health stub, e.g. `GET /api/v1/notes/health`.

## Running without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then point POSTGRES_HOST/REDIS_HOST at localhost
uvicorn app.main:app --reload
```

You'll need a local Postgres and Redis instance reachable at the hosts/ports
configured in `.env` (or update `POSTGRES_HOST`/`REDIS_HOST` to `localhost`).

## Database migrations (Alembic)

Alembic is initialized and wired to the app's async engine and the shared
`Base.metadata` (see `app/db/base.py`). The initial migration
(`alembic/versions/f59c26ad786c_*.py`) creates the `users` and
`refresh_tokens` tables.

```bash
# Inside the api container, or locally with deps installed:
alembic upgrade head

# After adding/changing a model:
alembic revision --autogenerate -m "add note model"
alembic upgrade head
```

## Tests

```bash
pytest
```

Currently includes smoke tests only (`tests/test_main.py`) verifying the app
boots and the root/health endpoints respond.

## Environment variables

See `.env.example` for the full list. Key groups: general/app, security
placeholders, CORS, PostgreSQL (`POSTGRES_*` or a full `DATABASE_URL`
override), Redis (`REDIS_*` or a full `REDIS_URL` override), and logging.

## What's implemented

- **Authentication** — registration, login, JWT access + refresh tokens
  (with DB-backed refresh-token storage/rotation/revocation), logout, and a
  `get_current_user` dependency. See [`docs/AUTH.md`](docs/AUTH.md) for the
  full design and endpoint reference.

## What's intentionally NOT implemented yet

- No note/tag/user CRUD logic (beyond auth's own user registration)
- No Redis caching logic (connection plumbing only)
- No rate limiting, email verification, or password reset flow

This is scaffolding meant to be built on top of.
