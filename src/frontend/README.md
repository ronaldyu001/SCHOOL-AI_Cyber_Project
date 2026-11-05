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
5. `POST /datasets/{task}/{id}/artifacts`, then
   `POST /datasets/{task}/{id}/preprocess` carrying that `artifact_id`

The records panel reads `GET .../prepared/{prepared_id}/{partition}` and
`GET .../preprocessed/{preprocessed_id}`, and `Unload dataset` sends
`DELETE /datasets/{task}/{id}`. The preprocess step re-reads a manifest with
`GET .../artifacts/{artifact_id}` and links the bundle ZIP at
`GET .../artifacts/{artifact_id}/download`.

### Session lifetime

A session lives in the API process under the `dataset_id` the load step
returned, and nothing evicts it on a timer. The console therefore deletes one
everywhere it stops using it:

| Leaving by | Sent from |
| --- | --- |
| `Unload dataset` | the button, with any failure shown |
| `Reload dataset` | the load step, before the replacement is opened |
| Changing task, or returning to the task list | the workspace unmounting |
| Closing or refreshing the tab | a `pagehide` listener |

Only the button has anyone left to report a failure to, so the other three go
through `releaseDataset`, which swallows the outcome: a session that is already
gone answers 404, which is what those paths wanted anyway. `pagehide` fires on a
document that is going away, so that request carries `keepalive` to outlive it.

Reload releases first and loads second, so two sessions are never resident at
once — the malware source is large enough for that peak to be the point. The
cost is that a reload which then fails leaves nothing loaded.

### Stage exports

Every completed step offers its own ZIP from `GET .../download`, selected by
`stage` and, past the first two, the id that step returned:

| Step | Query | Archive holds |
| --- | --- | --- |
| Load | `stage=loaded` | `data.json` of every source row, `manifest.json` with the columns and digest |
| Clean | `stage=cleaned` | the surviving rows under the pinned schema version |
| Split | `stage=splits&result_id={split_id}` | the row ids per partition, with the seed and fractions |
| Prepare | `stage=prepared&result_id={prepared_id}&partition=…` | one folder per partition, records in split order |
| Preprocess | `stage=preprocessed&result_id={preprocessed_id}` | the full transformed arrays and encoding metadata |

`prepared` is the only stage holding all three partitions at once, so it is the
only one the console gives a partition select; `all` is its default. The other
stages reject a `partition`, and `loaded` and `cleaned` reject a `result_id`.

Notes:

- Datasets are static: every task loads only its bundled source file. The
  malware router also exposes `POST /upload`, but the console deliberately does
  not offer it.
- Preprocessing runs off a preprocessing artifact, so the step creates one
  first. Passing a preprocessor to `create_app()` replaces that task's artifact
  adapter, and the artifact endpoints then return 409.
- `ArtifactPanel` groups a manifest by the shape of its values rather than by
  task: scalar settings are the ones you retype in your own training code,
  while fitted series and maps are summarised and travel in the bundle. Files
  listed under `files` are what the bundle carries beyond `manifest.json`.
- Exports are plain anchors, not `fetch` calls, so the browser streams each
  archive straight to disk. A malware record stage carries the executables
  themselves, which no in-memory blob would hold. Because a `fieldset` cannot
  disable an anchor, `StageDownload` drops its own `href` while the workspace
  is busy.
- Malware preprocessed records are padded byte sequences, so the records panel
  adds a byte window (`token_offset` / `token_limit`) on top of the row pager
  and renders the tokens as hex, with padding shown as `··`.
- Pipeline state lives in component state, so reloading the page starts over,
  and the session behind it is released rather than left behind. Deleting it is
  the console's job alone: the API has no expiry of its own.

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

### Stage resets

Each completed Clean, Split, and Prepare step has a reset button; Preprocess can
also be reset once prepared data exists, including after a failed transform.
Reset clears that stage and later results through the backend while retaining the
loaded dataset and upstream results. Affected step forms and artifact selections
reset, and the record browser returns to train. Pipeline actions, resets, and
unload are mutually exclusive while a request is active. “Reset fractions” only
restores the split form defaults; it does not clear server results.
