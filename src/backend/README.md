# Dataset backend

Python 3.12.15. Domain entities contain actual records and partition data. Application ports define loading, splitting, and preprocessing contracts; infrastructure adapters implement them. Use cases coordinate the stages. Task-specific FastAPI modules expose the dataset lifecycle.

## Run

From `src/backend`:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://localhost:8000/docs` to exercise the APIs. The application starts without reading either dataset. Network intrusion and phishing detection are implemented; malware remains a template.

Bundled source files belong here:

```text
.data/network_intrusion/train_test_network.csv
.data/phishing_detection/phishing_email.csv
```

The available notebook CSVs have been copied to these locations locally. `.data` is Git-ignored: a fresh checkout must supply them before loading datasets or building an image. The Dockerfile includes `.data` without loading it at startup:

```sh
docker build -t ai-cyber-backend .
docker run --rm -p 8000:8000 ai-cyber-backend
```

## Dataset APIs

Use either `/datasets/network_intrusion` or `/datasets/phishing_detection` as the prefix.

| Method | Suffix | Input / behavior |
| --- | --- | --- |
| POST | `/load` | No body. Loads only that task's bundled CSV; returns `dataset_id`, schema columns, sample count, and SHA-256 source version. |
| POST | `/{dataset_id}/clean` | Selects/normalizes records and deduplicates. Idempotent for the loaded dataset. |
| POST | `/{dataset_id}/splits` | `{}` uses notebook defaults: stratified 70/15/15, seed 123. Optional `seed`, `train_fraction`, `holdout_test_fraction`; returns `split_id` and partition counts. |
| POST | `/{dataset_id}/prepare` | `{"split_id":"..."}` materializes actual train/test/eval records. Returns `prepared_id`. |
| GET | `/{dataset_id}/prepared/{prepared_id}/{partition}` | `partition` is train/test/eval. Returns records with original source row IDs. |
| POST | `/{dataset_id}/preprocess` | `{"prepared_id":"..."}` transforms eval only. Returns `preprocessed_id`. |
| GET | `/{dataset_id}/preprocessed/{preprocessed_id}` | Returns transformed eval rows and labels. |
| DELETE | `/{dataset_id}` | Releases that dataset and all associated state. |

Both GET routes support `offset` (default 0) and `limit` (default 100, maximum 1000). IDs are scoped to their dataset and task. Missing IDs/files return 404, missing prerequisite stages return 409, and invalid data/requests return 422. Failed stages do not save partial output.

State is held in memory per application process, like the MSCS reference project. A restart discards it; use one worker for this implementation. Datasets and their prepared/preprocessed entities are available under `app.state.network_intrusion_datasets` and `app.state.phishing_detection_datasets` for subsequent integration.

## Task behavior

Network intrusion retains the fixed 16 numeric and five categorical features plus binary label, dropping the notebook's excluded features. Duplicate detection uses retained source columns. Original source row IDs and source order are preserved before sklearn performs the two stratified splits. Prepared partitions contain typed records.

Network preprocessing requires the imported model's fitted numeric pipeline, category maps, feature order, and cardinalities. The checkpoint adapter validates that contract and only calls `transform`. Configure it when assembling the app:

```python
from main import create_app
from infrastructure.adapters.preprocessing.network_intrusion import NetworkIntrusionCheckpointPreprocessor

# checkpoint is an already-loaded, trusted notebook checkpoint dictionary.
app = create_app(network_preprocessor=NetworkIntrusionCheckpointPreprocessor(checkpoint))
```

Until configured, the network preprocessing endpoint returns 409. Checkpoint import/deserialization and model inference belong to the model integration scope. Top-level dependencies are declared in `requirements.in`; `requirements.txt` is used for installation. Both currently list unpinned dependencies, with no separate dev requirements files.

Phishing uses one text feature (`text_combined`) and binary `label` (0 legitimate, 1 phishing/spam). Cleaning drops missing/blank inputs, normalizes whitespace, rejects conflicting labels for identical normalized text, and keeps the first duplicate. The text adapter extracts normalized eval strings and labels. The model pipeline owns BART tokenization and truncation; no vocabulary or scaler is fitted here.

## Verify

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Ports are typed protocols; concrete adapters explicitly implement them. Use cases additionally check split coverage/policy and preservation of eval source, order, and labels. Domain invariants validate schema dimensions, unique membership, and alignment of actual data.
