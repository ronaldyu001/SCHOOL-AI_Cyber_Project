# Frontend

React + TypeScript + Vite console for the dataset API in `src/backend`.

## Layout

```
src/
  api/        Typed client for the dataset endpoints (mirrors the backend schemas)
  app/        Root navigator (persistent header) and route table
  components/ Shared primitives: button, badge, status note, step card, record table
  pages/      Task selection (landing) and the per-task dataset workspace
  styles/     Design tokens and global styles
  tasks/      Task catalog and record-to-table mapping
```

Routes:

| Path | Page |
| --- | --- |
| `/` | Task selection (landing) |
| `/tasks/:slug` | Dataset pipeline for that task |

## Running it

The backend has no CORS middleware, so the app calls a relative `/api` path and
the Vite dev server proxies it. Start both:

```Shell
cd src/backend
.venv/bin/uvicorn main:app --port 8000
```

```Shell
cd src/frontend
npm ci
npm run dev
```

Open `http://localhost:5173`.

Override the proxy upstream with `BACKEND_URL`, or bypass the proxy entirely by
setting `VITE_API_BASE_URL` to an absolute API URL.

## Theming

Colours are declared once in `src/styles/tokens.css` with `light-dark()`, so the
active theme follows `color-scheme`. The app tracks the operating system until
the header toggle is used; the choice is then pinned as `data-theme` on `<html>`
and remembered in `localStorage`. A small inline script in `index.html` applies
it before first paint so a pinned dark theme does not flash light.

Because the theme is driven by `color-scheme` rather than classes, native
controls (the rows select, the split number inputs) switch with it.

## Pipeline

Each task page walks the dataset endpoints in order. A step unlocks only once
the one before it has run:

1. `POST /datasets/{task}/load`
2. `POST /datasets/{task}/{id}/clean`
3. `POST /datasets/{task}/{id}/splits`
4. `POST /datasets/{task}/{id}/prepare`
5. `POST /datasets/{task}/{id}/preprocess`

The records panel reads `GET .../prepared/{prepared_id}/{partition}` and
`GET .../preprocessed/{preprocessed_id}`, and `Unload dataset` sends
`DELETE /datasets/{task}/{id}`.

Notes:

- Datasets are static: every task loads only its bundled source file. The
  malware router also exposes `POST /upload`, but the console deliberately does
  not offer it.
- Network intrusion and malware detection preprocessing return 409 until a
  preprocessor is passed to `create_app()`. The UI shows that as a warning, not
  a failure.
- Malware preprocessed records are padded byte sequences, so the records panel
  adds a byte window (`token_offset` / `token_limit`) on top of the row pager
  and renders the tokens as hex, with padding shown as `··`.
- Pipeline state lives in component state, so reloading the page starts over.
  The backend session stays in memory until it is unloaded or the API restarts.

## Docker

`src/deployment/compose.yml` runs both services:

```Shell
cd src/deployment
docker compose up --build -d
```

Open `http://localhost:5173`. Stop with `docker compose down`.

The frontend image serves the bundle through nginx using `nginx.conf`, which
does two things the stock config does not:

- `try_files $uri $uri/ /index.html` so client-side routes such as
  `/tasks/phishing_detection` survive a direct load or a refresh. Paths under
  `/assets/` are excluded, so a missing bundle 404s instead of returning HTML.
- `proxy_pass http://backend:8000/` for `/api/`, with the trailing slash
  stripping the prefix. Read timeouts are raised to 300s because loading and
  preparing a dataset reads the whole CSV in one request.

The backend is only reachable inside the compose network; nginx is the single
published entry point. The frontend waits on the backend's healthcheck, so
nginx never starts before its upstream resolves.

To reach the API directly while debugging, add a port mapping to the backend
service:

```yaml
    ports:
      - "8000:8000"
```
