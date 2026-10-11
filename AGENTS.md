# Finora — WEB VERSION (canonical, frozen)

This repository is the **web** frontend of Finora. Treat it as the web version.

- **Live web app:** https://finora-gamma-two.vercel.app/
- **Pinned snapshot:** git tag `web-version` (commit `a540f3e`) — the exact
  editorial web UI that matches the deployed site.
- **Backend:** Flask API in `backend/` (may be changed when needed).

## ⚠️ Do not touch the web frontend without asking

The web frontend is frozen to the `web-version` snapshot. This includes:

- `src/` (all components and pages)
- `public/`
- `index.html`
- `vite.config.ts`
- `package.json`, `package-lock.json`
- `tsconfig.json`

**Before modifying ANY of these files, STOP and ask the user for permission
first.** Do not redesign, restyle, replace, or "improve" the web UI on your own.
The mobile app that briefly replaced this UI is NOT wanted here.

## If the mobile app is ever needed

It is preserved in git history (commit `3f3f020`):

```sh
git worktree add ../Finora-mobile 3f3f020
```

## Deploy

- Vercel builds with `npm run build` → single-file `dist/index.html`.
- Requires `VITE_API_URL` set in the Vercel project env, pointing at the Flask
  backend (e.g. `https://finora-api-dio1.onrender.com`).
- Pushing to `main` triggers a Vercel production redeploy.

## Verify the frontend is intact

```sh
git diff --stat web-version -- src public index.html vite.config.ts package.json tsconfig.json
```

An empty diff means the web UI is untouched.
