# Notes API

Production-ready FastAPI backend for the Notes Management App.

## Tech Stack

- **FastAPI** — async web framework
- **PostgreSQL** + **SQLAlchemy 2.0** (async, asyncpg) — database layer
- **Redis** — caching and rate limiting
- **Alembic** — database migrations
- **Docker / docker-compose** — API + Postgres + Redis with healthchecks
- **JWT** — authentication via python-jose
- **bcrypt** — password hashing via passlib

## Features

- JWT authentication (register, login, refresh tokens, logout)
- Full notes CRUD with soft delete and archive
- Tags with many-to-many relationship to notes
- Full-text search across title and content
- File import (txt, md, csv, json) with import history tracking
- Redis caching for notes list, search results, and user profiles
- Cache invalidation on all write operations
- Rate limiting on login and register endpoints
- Paginated responses
- Request logging and global error handling middleware
- Full test suite (pytest + pytest-asyncio)

## Project structure
backend/

├── app/

│   ├── api/

│   │   ├── deps.py          # shared dependencies (get_db, get_redis, get_current_user)

│   │   └── v1/endpoints/    # auth, notes, tags, imports, users, health

│   ├── core/                # config, security (JWT/bcrypt), cache, logging

│   ├── db/                  # SQLAlchemy session/engine, Redis client

│   ├── middleware/           # request logging, rate limiting, error handling

│   ├── models/              # SQLAlchemy ORM models

│   ├── schemas/             # Pydantic request/response schemas

│   ├── services/            # business logic layer

│   └── main.py              # app factory, lifespan, middleware/router wiring

├── alembic/                 # database migrations

├── tests/                   # test suite

├── docs/                    # additional documentation

└── docker-compose.yml

## Running locally

```bash
cp .env.example .env
docker compose up
```

This starts three services:
- `db` — Postgres 16 with healthcheck
- `redis` — Redis 7 with healthcheck
- `api` — FastAPI app, waits for db and redis to be healthy

Once running:
- App root: http://localhost:8000/
- Health check: http://localhost:8000/health
- Swagger docs: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Running tests

```bash
docker compose exec api pytest
```

## Database migrations

```bash
# Run all migrations
docker compose exec api alembic upgrade head

# Create a new migration after model changes
docker compose exec api alembic revision --autogenerate -m "description"
```

## Environment variables

See `.env.example` for the full list. Key variables:
- `SECRET_KEY` — JWT signing key
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `BACKEND_CORS_ORIGINS` — allowed frontend origins
