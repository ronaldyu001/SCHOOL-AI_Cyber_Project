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

Open `http://localhost:8000/docs` to exercise the APIs. The application starts without reading any dataset. Network intrusion, phishing detection, and malware detection are all implemented.

Bundled source files belong here:

```text
.data/network_intrusion/train_test_network.csv
.data/phishing_detection/phishing_email.csv
.data/malware_detection/MalwareDetectionDataset.zip
```

The available notebook CSVs have been copied to these locations locally. `.data` is Git-ignored: a fresh checkout must supply them before loading datasets or building an image. The Dockerfile includes `.data` without loading it at startup:

```sh
docker build -t ai-cyber-backend .
docker run --rm -p 8000:8000 ai-cyber-backend
```

## Dataset APIs

Use `/datasets/network_intrusion`, `/datasets/phishing_detection`, or `/datasets/malware_detection` as the prefix.

| Method | Suffix | Input / behavior |
| --- | --- | --- |
| POST | `/load` | No body. Loads only that task's bundled source file; returns `dataset_id`, schema columns, sample count, and SHA-256 source version. |
| POST | `/upload` | Malware detection only. Raw `application/zip` body, up to 4 GiB, streamed to a temporary directory. Same response as `/load`. |
| POST | `/{dataset_id}/clean` | Selects/normalizes records and deduplicates. Idempotent for the loaded dataset. |
| POST | `/{dataset_id}/splits` | `{}` uses defaults: stratified 70/15/15, seed 123. Optional `seed`, `train_fraction`, `test_fraction`, `eval_fraction`; returns `split_id` and partition counts. |
| POST | `/{dataset_id}/prepare` | `{"split_id":"..."}` materializes actual train/test/eval records. Returns `prepared_id`. |
| GET | `/{dataset_id}/prepared/{prepared_id}/{partition}` | `partition` is train/test/eval. Returns records with original source row IDs. |
| POST | `/{dataset_id}/preprocess` | `{"prepared_id":"...", "artifact_id":"...", "partition":"eval"}` transforms train/test/eval (default eval). Returns artifact and result IDs. |
| GET | `/{dataset_id}/preprocessed/{preprocessed_id}` | Returns transformed rows and labels. |
| GET | `/{dataset_id}/download` | ZIP attachment; requires `stage`, with `result_id` and `partition` as described below. |
| DELETE | `/{dataset_id}/stages/{stage}` | Resets cleaned, splits, prepared, or preprocessed and all downstream results; keeps the loaded dataset. |
| DELETE | `/{dataset_id}` | Releases that dataset and all associated state. |

The prepared and preprocessed record GET routes support `offset` (default 0) and `limit` (default 100, maximum 1000). The malware preprocessed route also takes `token_offset` (default 0) and `token_limit` (default 256, maximum 4096) to window each padded byte sequence. IDs are scoped to their dataset and task. Missing IDs/files return 404, missing prerequisite stages return 409, and invalid data/requests return 422. Failed stages do not save partial output.

State is held in memory per application process, like the MSCS reference project. A restart discards it; use one worker for this implementation. Datasets and their prepared/preprocessed entities are available under `app.state.network_intrusion_datasets`, `app.state.phishing_detection_datasets`, and `app.state.malware_detection_datasets` for subsequent integration. A malware session also owns an extracted-archive temporary directory, released by `DELETE` and at application shutdown.

## Task behavior

Network intrusion retains the fixed 16 numeric and five categorical features plus binary label, dropping the notebook's excluded features. Duplicate detection uses retained source columns. Original source row IDs and source order are preserved before sklearn performs the two stratified splits. Prepared partitions contain typed records.

Network artifacts fit median imputation, standard scaling, and category mappings
on the prepared training partition only. The bundle contains feature order,
fill values, means/scales, category IDs, and cardinalities as JSON. Evaluation
never fits or changes these values. An all-missing training column fills with 0;
unseen and missing categories use IDs 0 and 1.

Malware detection reads a ZIP holding `files/{benign,malware}/` executables named by their SHA-256 and matching `labels/{benign,malware}/` manifests. The ZIP adapter rejects links and unsafe members, enforces extraction limits, and parses only the hash column; the binary adapter then verifies each file's bytes against its name. Samples are read as bytes and never executed. Prepared records report the hash, archive path, label, and size rather than the content itself.

Malware artifacts default to 1 MiB prefixes, byte values 0–255 and padding 256.
Creation accepts `max_length`, `byte_offset`, `padding_token`, and `truncation`.
Use settings matching the model trained against the downloaded artifact.

Phishing artifacts package the `facebook/bart-large-mnli` tokenizer, resolved
revision, special token IDs, and encoding settings. First creation downloads only
tokenizer/config files; no model weights. Later transformations use the verified
local files. Tokenization produces one premise/hypothesis pair per candidate
(`phishing email`, `legitimate email`), preserving the original sample and binary
label. Creation accepts `max_length`, `padding`, and `truncation`; fixed padding
and `only_first` truncation preserve the hypothesis. GET previews show the first
64 tokens per candidate; full sequences stay in the entity.

## Preprocessing artifacts

Artifacts are generated by the backend, independently of training notebooks.
Create them after preparation, then select one to preprocess any partition:

| Method | Suffix | Behavior |
| --- | --- | --- |
| POST | `/{dataset_id}/artifacts` | `{"prepared_id":"...", "settings":{}}` creates a frozen version. |
| GET | `/{dataset_id}/artifacts/{artifact_id}` | Inspect manifest, settings, fitted statistics, file fingerprints, and provenance. |
| GET | `/{dataset_id}/artifacts/{artifact_id}/download` | Download the complete portable ZIP. |

Default storage is `.artifacts/<artifact-id>/manifest.json`, with a `tokenizer/`
subdirectory for phishing. Each ID hashes the canonical manifest, which includes
checksums for packaged files and a fingerprint of training membership/data.
Repeated identical creation reuses the bundle; changed settings or training data
produce a different ID. Loads verify fingerprints. JSON statistics replace
pickle-based preprocessing exports. ZIPs contain everything needed to reproduce
the transformation; numeric arrays use the saved feature order and float32.

The frontend exposes creation, selection, settings inspection, download, and
partition choice. API artifact references are scoped to the owning dataset and
prepared partition set. Missing prerequisites return 409, unavailable tokenizer
sources return 503, and invalid settings return 422. Failed creation publishes no
bundle. Transformations are limited to 32 million total tokens to bound retained
in-memory output; reduce maximum length or dataset size if exceeded.

Artifact files persist after dataset deletion and app restart. Dataset sessions
remain process-local; recreate the prepared data and artifact binding after a
restart. Repeated identical creation loads the persisted bundle. The Docker
Compose volume preserves `.artifacts` across container recreation.

`create_app(artifact_root=...)` selects storage. The optional injected network and
malware preprocessors remain available for existing trusted integrations. Default
operation uses the backend-generated artifacts and requires no model checkpoint.
User model uploads, inference, and explanations are separate integration work.

## Verify

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Ports are typed protocols; concrete adapters explicitly implement them. Use cases additionally check split coverage/policy and preservation of eval source, order, and labels. Domain invariants validate schema dimensions, unique membership, and alignment of actual data.

## Dataset downloads

Each task has an export use case, a typed export port, and a ZIP adapter. Downloads
use existing session entities and do not rerun preprocessing or modify state.

Use `GET /datasets/{task}/{dataset_id}/download` with these query parameters:

| `stage` | `result_id` | `partition` |
| --- | --- | --- |
| `loaded` | Omit | Omit; downloads all original loaded records |
| `cleaned` | Omit | Omit; downloads all cleaned records |
| `splits` | A `split_id` | Omit; downloads membership IDs and split policy |
| `prepared` | A `prepared_id` | `train`, `test`, `eval`, or `all` (default) |
| `preprocessed` | A `preprocessed_id` | Omit, or match the result's existing partition |

Examples, using the phishing task prefix:

```text
/{dataset_id}/download?stage=cleaned
/{dataset_id}/download?stage=prepared&result_id={prepared_id}&partition=train
/{dataset_id}/download?stage=preprocessed&result_id={preprocessed_id}
```

ZIPs contain `manifest.json` with export schema version, task, stage, partition,
and source identity where present. `data.json` contains full data, including
original row IDs. Loaded CSV records retain their original positional values;
column names appear in the manifest. Network bundles also describe numeric and
categorical feature order. Prepared exports put records under `train/`, `test/`,
and/or `eval/` and include the split policy and membership in the manifest.
Preprocessed exports contain the complete entity, including all token arrays,
encoding settings, and artifact reference, without preview truncation. A split
membership export contains IDs and policy only, rather than sample records.

Malware loaded, cleaned, and prepared exports include original executable bytes
at their relative `files/...` paths, alongside JSON row/hash/label metadata.
These are dataset export bundles, not copies of the original uploaded ZIP.

Missing datasets/results return 404, cleaned data before cleaning returns 409,
and incompatible stage/ID/partition selections return 422. Downloads are built
in temporary streams, spill to disk above 8 MiB, and are sent in 64 KiB chunks.
Temporary export streams close after delivery; the session data remains available.

## Resetting stages

`DELETE /datasets/{task}/{dataset_id}/stages/{stage}` returns an empty 204 response.
It resets all versions of the chosen stage within that session, under the session
lock, and is idempotent. Missing datasets return 404; unsupported stages return 422.

| Stage | Cleared state |
| --- | --- |
| `cleaned` | Cleaned data, splits, prepared datasets, artifact bindings, preprocessed results |
| `splits` | Splits, prepared datasets, artifact bindings, preprocessed results |
| `prepared` | Prepared datasets, artifact bindings, preprocessed results |
| `preprocessed` | Preprocessed results only |

Loaded records, source identity, and malware upload files remain available. The
existing dataset DELETE endpoint still unloads the entire session. Persisted
preprocessing artifacts are retained; resetting prepare or an earlier stage removes
the session bindings, while resetting preprocess preserves those bindings.

## Preprocessing token budgets

The backend permits 16,000,000,000 malware tokens or 256,000,000 phishing tokens
per preprocessing request. These cover the complete bundled datasets before
cleaning/splitting at default input lengths: 11,923 malware files at 1,048,576 bytes
and 82,486 emails at 1,024 tokens for each of two candidate pairs. Network
intrusion has no token-count budget. Counts use ZIP file entries and CSV records,
not newline counts, since email text can span multiple lines.

The frontend maximum-input-length field has no upper cap. Backend model validation
still restricts BART tokenizer lengths to 16–1,024; malware accepts positive
integer lengths. Larger custom inputs may exceed the per-request token budget.
These budgets count tokens, not RAM; the tuple-based implementation still
materializes the full partition, so passing the guard does not ensure it fits
in the process or Docker memory allocation.
