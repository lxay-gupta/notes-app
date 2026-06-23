# Notes App

A full-stack notes management application with file import functionality.

**Backend:** FastAPI, PostgreSQL, Redis, SQLAlchemy, Alembic, Docker

**Frontend:** React, Vite, Tailwind CSS, React Router, Axios

## Features

- JWT authentication (register, login, logout)
- Create, read, update, delete notes
- Search notes by title and content
- Tag notes and filter by tags
- Archive and unarchive notes
- Import files as notes (txt, md, csv, json)
- Redis caching for improved performance

## Prerequisites

Install these before running the project:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — runs the backend, database and Redis
- [Node.js](https://nodejs.org/) — runs the frontend (download the LTS version)

## Running locally

**Step 1 — Clone the repository:**
```bash
git clone https://github.com/lxay-gupta/notes-app.git
cd notes-app
```

**Step 2 — Set up the backend environment:**
```bash
cd backend
cp .env.example .env
```

**Step 3 — Start the backend (in Terminal 1):**
```bash
cd backend
docker compose up
```
Wait for `Application startup complete`

**Step 4 — Start the frontend (in Terminal 2):**
```bash
cd frontend
npm install
npm run dev
```
Wait for `Local: http://localhost:3000`

**Step 5 — Open your browser:**
http://localhost:3000

**Step 6 — Register an account and start using the app**

## Stopping the app

Press `Ctrl+C` in both terminals.

## Project structure
notes-app/

├── backend/         # FastAPI REST API

│   ├── app/         # Application code

│   ├── alembic/     # Database migrations

│   ├── tests/       # Test suite

│   └── docker-compose.yml

└── frontend/        # React frontend

├── src/

│   ├── api/     # API client and functions

│   ├── components/  # Reusable components

│   ├── pages/   # Page components

│   └── context/ # Auth context

└── vite.config.js

## API Documentation

Once the backend is running, visit:
http://localhost:8000/api/v1/docs
This shows all available API endpoints with interactive testing.

## Running tests

```bash
cd backend
docker compose exec api pytest
```
