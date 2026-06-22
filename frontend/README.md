# Notes Frontend

React + Vite frontend for the Notes Management API.

## Tech stack

- **React 18** + **React Router 6** — page routing with protected routes
- **Axios** — API client with automatic JWT refresh on 401
- **Tailwind CSS** — utility-first styling with custom design tokens
- **react-hot-toast** — toast notifications
- **date-fns** — date formatting

## Quick start

```bash
cp .env.example .env.local
# Edit .env.local — set VITE_API_URL to your backend URL

npm install
npm run dev        # http://localhost:3000
```

## Environment variables

| Variable        | Required | Description                                           |
|-----------------|----------|-------------------------------------------------------|
| `VITE_API_URL`  | Yes      | Base URL of the FastAPI backend (no trailing slash)   |

For local development with the Docker backend:
```
VITE_API_URL=http://localhost:8000
```

## Build

```bash
npm run build      # outputs to dist/
npm run preview    # preview the production build locally
```

## Deploy to Vercel

1. Push the `notes-frontend/` folder to a GitHub repository
2. In [Vercel](https://vercel.com), create a new project and import the repo
3. Set the **Root Directory** to `notes-frontend` (if in a monorepo)
4. Add environment variable: `VITE_API_URL` → your Render backend URL
5. Deploy — Vercel auto-detects Vite and uses `vercel.json` for SPA routing

> **CORS**: make sure your FastAPI backend has `BACKEND_CORS_ORIGINS` set to
> include your Vercel deployment URL (e.g. `https://notes-frontend.vercel.app`).

## Project structure

```
src/
├── api/               # Axios client + per-resource API functions
│   ├── client.js      # Axios instance, token storage, refresh interceptor
│   ├── auth.js
│   ├── notes.js
│   ├── tags.js
│   └── imports.js
├── context/
│   └── AuthContext.jsx  # User state + login/logout/register actions
├── components/
│   ├── ui/            # Shared: Spinner, Empty, Modal, SearchBar, etc.
│   ├── layout/        # AppShell (sidebar), ProtectedRoute
│   ├── notes/         # NoteRow (list item)
│   └── tags/          # TagManager (attach/detach/create tags inline)
├── pages/             # One file per route
│   ├── LoginPage.jsx
│   ├── RegisterPage.jsx
│   ├── DashboardPage.jsx
│   ├── CreateNotePage.jsx
│   ├── EditNotePage.jsx
│   ├── ViewNotePage.jsx
│   └── ImportPage.jsx
└── utils/
    └── helpers.js     # Date formatting, error extraction, truncation
```

## Auth flow

Tokens are stored in `localStorage` (keys: `notes_access_token`, `notes_refresh_token`).
On every request, the Axios interceptor attaches the access token as `Authorization: Bearer <token>`.
On a 401 response, the interceptor silently calls `/auth/refresh`, updates storage, and retries
the original request — transparent to the UI. If refresh fails, tokens are cleared and the user
is redirected to `/login`.
```
