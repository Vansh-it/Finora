# Finora — AI Financial Research & Intelligence (Web)

The **web** version of Finora: an editorial-style front end that turns public
filings into financial statements, institutional-grade metrics, valuation
analysis, and explainable research — with every number traced to its source.

## Live Web Deployment

- **Web app (Vercel):** https://finora-gamma-two.vercel.app/
- **Backend API (Flask):** set via `VITE_API_URL` (e.g. a Render service)

> This repository hosts the **web** frontend. The mobile app that briefly
> replaced it lives on in git history — see `3f3f020` if you need to recover it.

## Stack

- Vite 7 + React 19 + TypeScript
- Tailwind CSS 4 (`@tailwindcss/vite`)
- React Router 7, Recharts, react-markdown, exceljs
- `vite-plugin-singlefile` — the production build inlines everything into a
  single `dist/index.html`
- Flask backend served from `backend/` (Python)

## Project Structure

```text
/
├── backend/          # Flask API (research, chat, reviews, exports)
├── public/           # static assets (favicons, web manifest)
├── src/
│   ├── components/   # editorial UI components
│   ├── pages/        # routes (home, research, dashboard, chat, ...)
│   ├── lib/          # API client, auth, data, exports
│   └── main.tsx
├── index.html
└── vite.config.ts
```

## Commands

Run from the repo root:

| Command                 | Action                                                      |
| :---------------------- | :---------------------------------------------------------- |
| `npm install`           | Install dependencies                                         |
| `npm run dev`           | Dev server at `http://localhost:4321` (proxies `/api`)       |
| `npm run dev:backend`   | Run the Flask backend on `http://localhost:8000`             |
| `npm run dev:all`       | Run frontend + backend together                              |
| `npm run build`         | Production build to `./dist/` (single-file `index.html`)     |
| `npm run preview`       | Preview the production build locally                         |

## Environment

Copy `.env.example` to `.env` and fill in what you need. Frontend-relevant keys:

- `VITE_API_URL` — public base URL of the Flask backend. Leave unset in dev to
  use the Vite proxy (`/api` → `http://localhost:8000`); set it for production
  builds (Vercel) so the deployed UI reaches the API.
- `BACKEND_URL` — backend origin used for hosted deployments.
- `CORS_ORIGINS` — comma-separated allowed frontend origins.

API keys (`NVIDIA_API_KEY`, `TAVILY_API_KEY`, `FMP_API_KEY`, etc.) belong to the
backend and must never be exposed to the frontend.

## Deploying the Web Version

Vercel builds this repo with `npm run build` and serves `dist/`. Set
`VITE_API_URL` (and any backend secrets on the API host) in the Vercel project
environment before deploying.
