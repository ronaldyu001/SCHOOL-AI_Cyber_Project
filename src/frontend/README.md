# Frontend

React + TypeScript + Vite console for the dataset API in `src/backend`.

## Layout

```
src/
  api/        Typed client for the dataset endpoints (mirrors the backend schemas)
  app/        Root navigator (persistent header) and route table
  components/ Shared primitives: button, badge, status note, step card, record table
  models/     The registered-model list, read by the model step
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
5. `POST /models/baselines/{task}/load`, or `POST /models/upload` for your own
6. `POST /datasets/{task}/{id}/artifacts`, then
   `POST /datasets/{task}/{id}/preprocess` carrying that `artifact_id`
7. `POST /models/{model_id}/predict`, which saves a result
8. `POST /results/{task}/{result_id}/analysis` on that result

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

**The automatic rows stop once a prediction has been saved.** Unloading a
dataset deletes the results saved from it, so from the first saved prediction
the workspace holds the session and only `Unload dataset` or a stage reset
releases it — both of which say what they delete. Freeing that memory is then
the user's decision, not something the console does on its way out of a page.

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

## Models and results in the pipeline

There is no separate models or results page: everything a task needs is one
flow, so nothing has to be done in another tab and come back.

**Step 5, Model.** The packaged notebook baseline is the default. `GET
/models/baselines` says which tasks have one installed and names it, and `Use
baseline` registers it through `POST /models/baselines/{task}/load`. The first
call reads and validates the bundle; a later one reuses the registration and
says so. Uploading your own bundle is folded away under the step, because it is
the exception. The chosen model is held by the workspace and used by both later
steps, which is why phishing tokenization follows the selection automatically.

A baseline is treated as borrowed rather than owned: the backend packages the
bundle and memoizes its registration, so releasing it on the way out would only
force the next session to read it again — 1.6 GB of it, for phishing. Uploads
are owned and released, as `use-model-release.ts` describes.

**Step 7, Predict** scores the partition and saves a result. **Step 8,
Evaluate** analyses that result: `POST …/analysis` for metrics over the whole
partition and, when asked, attributions for a seeded class-balanced sample. The
saved analyses are listed so an earlier one can be reopened or deleted, and the
result downloads as a ZIP.

Class names in the summary, the tables and the charts come from the result's own
output contract rather than the task catalog, so a contract change needs no
frontend change.

Charts are inline SVG rather than a charting dependency: a ROC or PR curve has
two rate axes, so the domain is fixed at 0–1 and nothing needs scaling. A curve
over a large partition carries a point per threshold, so it is strided down to
400 points, keeping both endpoints. Attribution bars keep their sign, with the
axis in the middle whenever any value is negative.

Explanations are rendered per task, because each explains something different:
standardized features for network intrusion, PE byte regions and windows for
malware, and email tokens for phishing. Units are not comparable across tasks,
so each section states its own target and baseline.

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

### Models in the task pipeline

The Load model step sits between Prepare and Preprocess. Users can load a local
notebook baseline, upload their own ZIP, or choose an already registered model
without leaving the task. The selected model is shared by preprocessing and
prediction; transformer tokenization automatically uses that model selection.
Changing selection clears the current preprocessing/prediction view so it can be
rebuilt for the new model. Saved results remain until the dataset is reset or
unloaded.

Models newly registered by the workspace are released when replaced/cleared,
when the dataset is reloaded or explicitly unloaded, and on task/page exit.
Previously registered library models are borrowed and remain registered. A model
load/upload that finishes after leaving the page is also cleaned up if it created
a registration. Baselines are borrowed, so they survive. The saved-result hold
behaviour for datasets is unchanged: after scoring, the dataset stays loaded for
the evaluate step until it is explicitly unloaded or a stage is reset.

Nginx now accepts up to 16 GiB on `/api/`, matching the backend model ZIP limit,
and streams request bodies instead of buffering whole uploads at the proxy.

Preprocessing, prediction, and analysis use background job submission and one-second
status polling for every cyber task. The pipeline displays phase/count progress,
retries temporary polling disconnects, and provides cancellation. Leaving the step
cancels active work; dataset reset/unload invalidates dependent jobs. An API restart
ends in-memory jobs, so the UI asks the user to rerun an expired job.
