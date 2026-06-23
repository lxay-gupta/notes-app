# Notes Frontend

React + Vite frontend for the Notes Management App.

## Tech Stack

- **React 18** + **React Router 6** — page routing with protected routes
- **Axios** — API client with automatic JWT refresh on 401
- **Tailwind CSS** — utility-first styling with custom design tokens
- **react-hot-toast** — toast notifications
- **date-fns** — date formatting

## Pages

- Login and Register
- Dashboard — notes list with search, filter, and pagination
- Create Note — title and monospace content editor
- Edit Note — partial update with unsaved changes indicator
- View Note — read view with tag management
- Import — drag and drop file import with history

## Running locally

Make sure the backend is running first (`docker compose up` in the backend folder), then:

```bash
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | Yes | Base URL of the FastAPI backend (no trailing slash) |

For local development:
VITE_API_URL=http://localhost:8000

## Build

```bash
npm run build      # outputs to dist/
npm run preview    # preview the production build locally
```

## Project structure
frontend/

└── src/

├── api/              # Axios client + per-resource API functions

│   ├── client.js     # Axios instance, token storage, refresh interceptor

│   ├── auth.js

│   ├── notes.js

│   ├── tags.js

│   └── imports.js

├── context/

│   └── AuthContext.jsx  # User state + login/logout/register actions

├── components/

│   ├── ui/           # Spinner, Empty, Modal, SearchBar, Pagination, ConfirmDialog

│   ├── layout/       # AppShell (sidebar), ProtectedRoute

│   ├── notes/        # NoteRow (list item with hover actions)

│   └── tags/         # TagManager (attach/detach/create tags inline)

├── pages/            # One file per route

│   ├── LoginPage.jsx

│   ├── RegisterPage.jsx

│   ├── DashboardPage.jsx

│   ├── CreateNotePage.jsx

│   ├── EditNotePage.jsx

│   ├── ViewNotePage.jsx

│   └── ImportPage.jsx

└── utils/

└── helpers.js    # Date formatting, error extraction, truncation

## Auth flow

Tokens are stored in `localStorage`. On every request the Axios interceptor attaches the access token as `Authorization: Bearer <token>`. On a 401 response, the interceptor silently calls `/auth/refresh`, updates storage, and retries the original request — transparent to the UI. If refresh fails, tokens are cleared and the user is redirected to `/login`.
