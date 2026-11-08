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

Default storage is `.artifacts/<cybertask>/<artifact-id>/manifest.json`, with a `tokenizer/`
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
bundle. Transformations use the task-specific token budgets described below to bound retained
in-memory output; reduce maximum length or dataset size if exceeded.

Artifact files persist after dataset deletion and app restart. Dataset sessions
remain process-local; recreate the prepared data and artifact binding after a
restart. Repeated identical creation loads the persisted bundle. The Docker
Compose volume preserves `.artifacts` across container recreation.

`create_app(artifact_root=...)` selects storage. The optional injected network and
malware preprocessors remain available for existing trusted integrations. Default
operation uses the backend-generated artifacts and requires no model checkpoint.
Model uploads and inference are supported through `/models`; saved evaluation and explanations are available through `/results`.

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
| `preprocessed` | Preprocessed results and session artifact bindings |

Loaded records, source identity, and malware upload files remain available. The
existing dataset DELETE endpoint still unloads the entire session. Every reset or
unload also deletes the dataset's saved prediction/analysis results and removes its
artifact bindings. Artifact files are deleted when no other active dataset uses
them. Uploaded models remain reusable until explicitly deleted or the API stops.

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

## Model uploads and inference

Model code and output meaning belong to the backend. Upload a data-only ZIP with
`manifest.json` and safetensors weights. Pickle, Python modules, custom Hugging
Face code (`auto_map`), and remote downloads during model loading are unsupported.
The dependency files now include PyTorch, safetensors, TabM 0.0.3 and numerical
embeddings; install them or rebuild the backend image before using model routes.
Loading is CPU-only. Trained model/tokenizer alignment and prediction quality are
the user's responsibility; the backend checks structural configuration, loadable
weights, and service output shape/meaning, not how a model was trained.

### Endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/models/capabilities` | Supported architectures, transformer families, output contracts |
| POST | `/models/upload` | Raw ZIP body with `Content-Type: application/zip`; returns 201 and `model_id` after validation |
| GET | `/models` | List validated uploaded models |
| GET | `/models/{model_id}` | Model metadata and configuration |
| GET | `/models/{model_id}/download` | Download the complete model bundle, including an optional tokenizer |
| DELETE | `/models/{model_id}` | Release the model's files and registry entry; returns 204 |
| POST | `/models/{model_id}/predict` | `{ "dataset_id": "...", "preprocessed_id": "..." }` |

Model files are temporary and scoped to the application process. They are deleted
on explicit model DELETE or application shutdown, and are not persisted in
`.artifacts`. Dataset resets/unloads do not delete models, allowing model reuse
across dataset sessions. The runtime loads weights per request and releases them
afterward instead of retaining a second in-memory model cache. Use one worker
for the current in-memory registries. ZIP requests/extracted contents are limited
to 16 GiB, 1,024 files and 64 MiB per JSON file. Invalid model content returns 422,
missing model/result IDs return 404, wrong upload content type returns 415, and
missing runtime dependencies or unavailable default tokenizers return 503.

### Transformer bundles and optional tokenizers

```text
manifest.json
config.json
model.safetensors                 # Or standard Hugging Face safetensors shards + index
tokenizer/                       # Optional
  tokenizer.json
  tokenizer_config.json
  special_tokens_map.json
```

The optional tokenizer directory accepts the same fast-tokenizer saved files
as downloadable preprocessing bundles. `tokenizer.json` is required; special-token
metadata, vocab/merge files, and SentencePiece data may also be included. The
loader reconstructs the fast tokenizer from its data graph without executing
uploaded code. It preserves pair token-type IDs for families such as BERT.

Transformer `manifest.json`:

```json
{
  "schema_version": 1,
  "task": "phishing_detection",
  "architecture": "transformer",
  "config": {}
}
```

Use the model's standard Hugging Face `config.json` at the ZIP root. Supported
families: BART, BERT, RoBERTa, DistilBERT, ALBERT, ELECTRA, DeBERTa, DeBERTa-v2,
and XLM-RoBERTa, using built-in sequence-classification implementations.
Service-owned transformer outputs are **three NLI logits**, ordered contradiction,
neutral, entailment. Binary two-logit classifiers and generative models are not
part of this inference contract. Candidate texts remain `phishing email` then
`legitimate email`, using `This example is {}.`. Inference normalizes the two
entailment logits across candidates to obtain the phishing probability. Dataset
labels remain 0=legitimate, 1=phishing. Uploaded id-to-label mappings do not override
this service contract.

After upload, create artifacts with the optional `model_id`:

```json
{
  "prepared_id": "...",
  "model_id": "...",
  "settings": { "max_length": 512 }
}
```

Send this to `POST /datasets/phishing_detection/{dataset_id}/artifacts`. If the
model includes a tokenizer, the generated artifact packages it and no default
tokenizer download is needed. Otherwise the usual default tokenizer is used.

Then call `POST /datasets/phishing_detection/{dataset_id}/preprocess`:

```json
{
  "prepared_id": "...",
  "artifact_id": "...",
  "model_id": "...",
  "partition": "eval"
}
```

A supplied model tokenizer overrides the artifact tokenizer. Without an uploaded
tokenizer the artifact tokenizer is used. Without `model_id` the existing artifact
preprocessing behavior remains unchanged. Results record `model_id`; transformer
prediction requires a result preprocessed for that selected model. All fixed
cleaning, split, candidate-label, padding/truncation, and dataset label rules remain
service-owned. The existing 16–1,024 token-length validation still applies.

### Configurable MalConv

A MalConv bundle contains `manifest.json` and `model.safetensors`:

```json
{
  "schema_version": 1,
  "task": "malware_detection",
  "architecture": "malconv",
  "config": {
    "embedding_dim": 8,
    "channels": 128,
    "kernel_size": 512,
    "stride": 512,
    "hidden_size": 128,
    "activation": "ReLU",
    "padding_idx": 256
  }
}
```

The backend implements gated convolutions, global max pooling, a configurable
hidden layer and one output logit. Default weight names/shapes match the notebook's
MalTorch MalConv; `embedding_dim` corresponds to MalTorch's `embedding_size`.
Channel/hidden-width changes require training a matching configurable model.
The sigmoid output is the malware probability: 0=benign, 1=malware. Input length
comes from preprocessing, must accommodate the kernel, and padding must match
`padding_idx` (0 or 256). Tokenizers are not accepted for this architecture.

### Configurable TabM

TabM bundles contain `manifest.json` and `model.safetensors`:

```json
{
  "schema_version": 1,
  "task": "network_intrusion",
  "architecture": "tabm",
  "config": {
    "n_num_features": 16,
    "cat_cardinalities": [2, 2, 2, 2, 2],
    "n_blocks": 3,
    "d_block": 512,
    "k": 32,
    "dropout": 0.1,
    "activation": "ReLU",
    "arch_type": "tabm",
    "num_embeddings": null
  }
}
```

Use actual cardinalities from the selected network preprocessing artifact, not
necessarily the example values. `n_blocks` controls depth; `d_block` is the shared
hidden width (TabM does not expose independent widths for individual blocks).
Supported variants are `tabm`, `tabm-mini`, and `tabm-packed`. Supported activations
for TabM and MalConv are ReLU, GELU, SiLU, Tanh, LeakyReLU, and ELU.

For the notebook's piecewise-linear numerical embeddings, replace `null` with:

```json
{
  "bins": [[0.0, 1.0], [0.0, 1.0]],
  "d_embedding": 16,
  "activation": false,
  "version": "B"
}
```

The abbreviated bins example must be replaced with **16** strictly increasing,
finite edge lists, one per numeric feature, exported from the training run.
Embedding versions A and B are supported. Use explicit `n_blocks` matching the
trained model (the notebook embedding model typically uses 2). Numerical and
categorical feature order remain fixed. TabM has two logits per ensemble member;
inference averages member probabilities, with 0=normal and 1=attack.

### Notebook export helper

Add this backend directory to the notebook's Python path and use
`tools.export_model_bundle.export_model_bundle`:

```python
from tools.export_model_bundle import export_model_bundle

export_model_bundle(
    model,
    task="phishing_detection",
    architecture="transformer",
    tokenizer=tokenizer,  # Optional: omit to use the service default
    output="transformer-upload.zip",
)
```

For TabM/MalConv, supply `config` matching the examples above, omit `tokenizer`,
and use the corresponding task/architecture. The helper exports tensor weights
and JSON only; it does not serialize a Python model object. TabM embedding bins
must be converted with `[edges.cpu().tolist() for edges in bins]` in the config.

## Local notebook baselines

Baseline model files are packaged under `.models/<cybertask>/` in this backend:

| Directory | Notebook baseline |
| --- | --- |
| `.models/phishing_detection/` | Cached `facebook/bart-large-mnli`, revision `d7645e127eaf1aefc7862fd59a17a5aa8558b8ce`, without fine-tuning |
| `.models/network_intrusion/` | TabM checkpoint `20261015_095219_939710/epoch_026.pt`, selected by the notebook |
| `.models/malware_detection/` | MalConv checkpoint `20261104_131637_676400/best.pt`, epoch 1 |

Each directory contains safetensors weights, the model manifest, `preprocessing.json`,
`baseline.json` with source/checkpoint details and file checksums, and an upload-ready
`baseline.zip`. The transformer also includes its Hugging Face config and tokenizer.
TabM preprocessing preserves the checkpoint's actual fitted imputation, scaling,
and category mappings; numerical embedding bins are included in its manifest.
`preprocessing.json` is a companion reference, not an extra model-upload member.

The files are local and Git-ignored. To reproduce them from the existing trusted
notebook checkpoints and local Hugging Face cache, run from the repository root:

```sh
PYTHONPATH=src/backend src/backend/.venv/bin/python src/backend/tools/prepare_baseline_models.py
```

The script refuses to replace an existing task directory. No training or network
download is performed. Baselines are not loaded at server startup; submit the
chosen `baseline.zip` to `/models/upload` when needed.

## Saved prediction results and analysis

Every successful `POST /models/{model_id}/predict` now saves a result and returns
`result_id` and `task` in addition to the existing prediction payload. Files live
under `.results/<cybertask>/<result_id>/`:

```text
metadata.json           # Dataset/model/artifact references, partition, timestamp, output contract
predictions.json        # Row IDs, true labels, probabilities, predicted labels
inputs.zip              # Per-sample compressed NumPy inputs; no pickle
model/                  # Immutable model and optional tokenizer snapshot
preprocessing/          # Selected artifact and tokenizer snapshot, when present
analyses/<analysis_id>.json
```

Snapshots allow analysis after the original uploaded model is deleted or the API
restarts. They preserve exact preprocessed inputs, including attention/type IDs
and premise masks, rather than retokenizing or preprocessing differently for XAI.
Model files use hard links when available, with copies as a filesystem fallback;
no extra model is retained in process memory. Result writes and analysis writes
are atomic. The Compose `analysis-results` volume persists `.results`; both
`.results` and `.artifacts` are excluded from image build context and Git.

### Result APIs

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/results/{task}` | List result metadata; optional `dataset_id` filter |
| GET | `/results/{task}/{result_id}` | Metadata and prediction rows; `offset=0`, `limit=100` (maximum 1,000) |
| DELETE | `/results/{task}/{result_id}` | Delete predictions, inputs, snapshots and all associated analyses |
| DELETE | `/results/{task}` | Delete all saved results for that task |
| GET | `/results/{task}/{result_id}/download` | ZIP of metadata, prediction rows and analysis JSON; excludes model/input snapshots |
| POST | `/results/{task}/{result_id}/analysis` | Calculate and save evaluation, optionally with explanations; returns 201 |
| GET | `/results/{task}/{result_id}/analysis` | List analysis IDs and parameters |
| GET | `/results/{task}/{result_id}/analysis/{analysis_id}` | Read a saved analysis payload |
| DELETE | `/results/{task}/{result_id}/analysis/{analysis_id}` | Delete one analysis |

`task` is `network_intrusion`, `malware_detection`, or `phishing_detection`.
Example analysis request:

```json
{
  "explain": true,
  "row_ids": [17, 42],
  "n_steps": 24,
  "internal_batch_size": 2,
  "n_repeats": 5,
  "seed": 123,
  "include_byte_attributions": false
}
```

Send `{}` for evaluation only. If `explain=true` and `row_ids` is omitted, a
seeded class-balanced sample is selected (up to `sample_count`, default 4).
Explicit row IDs refer to original dataset IDs, not positional indices. All
rows selected must belong to the saved result. Maximum selected sample count is
2,000; IG steps range 2–512, internal batch size 1–64, and permutation repeats
1–100. Analyses run synchronously on CPU; use a small sample for token/byte XAI.
Failed analyses do not publish a partial analysis file.

### Graph payload contract

Each analysis response contains `schema_version`, `task`, `result_id`,
`analysis_id`, `created_at`, `parameters`, `evaluation`, and `explainability`.
Evaluation always covers the **whole saved partition**, even when XAI uses a subset.

| Payload field | Frontend use |
| --- | --- |
| `evaluation.metrics` | Log loss, accuracy, precision, recall, F1, ROC-AUC, average-precision cards |
| `evaluation.classification_report` | Per-class and macro/weighted precision, recall, F1 and support tables |
| `evaluation.confusion_matrix` | `labels` and 2×2 `values`; rows are true classes, columns predicted classes |
| `evaluation.roc_curve` | Aligned `false_positive_rate`, `true_positive_rate`, `thresholds` arrays |
| `evaluation.precision_recall_curve` | `precision`, `recall`, `thresholds`; thresholds has one fewer element, as in sklearn |
| `explainability.samples` | Per-row attributions, target/baseline values and convergence deltas |

All payloads are JSON with finite numbers or explicit nulls, never NumPy objects,
NaN, Infinity, images or HTML. ROC's initial infinite threshold is encoded as null.
If the true labels contain only one class, ROC-AUC/AP/curves are null and a warning
explains why. Empty results cannot be evaluated. Predictions use the service's
fixed 0.5 threshold and output-label contract.

XAI follows the notebook methods:

- **Network:** Integrated Gradients for attack probability with zero standardized
  numeric inputs and fixed categories. Per-row signed numeric attributions and
  numeric feature values support waterfall/beeswarm plots. `global_importance`
  gives numeric `features` and `mean_absolute_attribution` bar heights.
  `feature_permutation` covers numeric and categorical features, with `features`,
  `feature_types`, mean `importance`, and `std` across repeats. Its target is the
  drop in true-class probability. Permutation requires at least two selected rows.
- **Malware:** Layer Integrated Gradients through the byte embedding, targeting
  the malware logit against an all-padding baseline. Each row includes `windows`
  with start/end offsets and signed attribution, `regions` with PE-region totals,
  `region_spans`, `top_bytes`, hash, logit/probability, and convergence delta.
  `include_byte_attributions=true` additionally returns the full per-byte array;
  otherwise the window/region arrays keep plotting payloads manageable. Final
  partial windows are included. PE data is parsed as bytes and never executed.
- **Phishing:** Integrated Gradients for the phishing-minus-legitimate entailment
  margin. Only email-token embeddings change; hypotheses, special tokens, masks
  and positions remain fixed. Per-row `tokens`, `token_ids`, and signed
  `attributions` support token heatmaps; `global_token_importance` supports bars.
  Margin, baseline margin, probability, retained-token count and convergence
  delta are included. The embedding-forward calculation is checked against the
  model's ordinary forward calculation before returning an explanation.

Positive network/phishing attributions push toward attack/phishing; positive byte
attributions push the malware logit upward. Attribution units differ by target,
so do not compare raw magnitudes across tasks. `convergence_delta` is signed and
can be displayed as an absolute error measure. The implementation supports the
same built-in transformer families as model upload, without custom uploaded code.

### Artifact and result cleanup

Persisted artifacts can now be managed independently of session bindings:

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/artifacts/{task}` | List stored artifacts for a task |
| GET | `/artifacts/{task}/{artifact_id}` | Inspect manifest |
| GET | `/artifacts/{task}/{artifact_id}/download` | Download artifact ZIP |
| DELETE | `/artifacts/{task}/{artifact_id}` | Delete artifact and its saved results; invalidate bound preprocessed inputs |
| DELETE | `/artifacts/{task}` | Delete all task artifacts and their dependent results |

The existing dataset-owned route also supports
`DELETE /datasets/{task}/{dataset_id}/artifacts/{artifact_id}` with the same
dependency cleanup, after verifying that the dataset owns the artifact.

New artifacts use task subfolders; legacy `.artifacts/<artifact_id>` bundles remain
readable, listable and deletable under their original task. Reusable default
tokenizer download caches are distinct from published artifact bundles.

**Any dataset stage reset or dataset unload deletes that dataset's saved results
and analyses.** All artifact bindings for that session are removed at the same
time, including on a preprocess reset; files remain only if another active dataset
still binds them. Earlier loaded/cleaned/split/prepared state follows the ordinary
stage reset rules. Explicit deletion of a result does not delete its live dataset
or uploaded model. Result snapshots survive API restarts until explicitly removed;
after restart, use task-scoped result/artifact delete routes to remove unbound data.
Storage operations use a consistent lock order so deletion waits for an in-flight
analysis or prediction rather than removing files while they are in use.

## Loading local baselines

- `GET /models/baselines` calls `ListBaselineModels` through `BaselineCatalogPort`
  and `FileBaselineCatalog`. It lists each task, architecture, name, availability
  and an optional unavailable reason without loading model weights.
- `POST /models/baselines/{task}/load` calls `LoadBaselineModel`, then the existing
  `ImportModel` validation/loading flow on `.models/{task}/baseline.zip`. Returns
  ordinary model metadata plus `baseline_task` and `reused`. The first request
  registers the model; repeated or simultaneous requests reuse that registration.
  Deleting the registration permits a fresh load; the baseline source ZIP is never
  deleted. There is no browser upload or implicit network download for this route.

`create_app(baseline_root=...)` can override the baseline catalog directory. Missing
bundles return 404, unsupported task names return 422, and invalid/cross-task
bundles return 422. No task-specific duplicate loader or inference implementation
is required.

### Explain prediction outcomes

The analysis request accepts an optional `outcome` filter for explanations:

```json
{
  "explain": true,
  "outcome": "false_positive",
  "sample_count": 5,
  "seed": 123
}
```

Supported values are `true_positive`, `false_positive`, `false_negative`, and
`true_negative`. Case-insensitive aliases `TP`, `FP`, `FN`, and `TN` also work;
saved parameters normalize them to their full names. Group membership uses the
saved service predictions: TP=(true 1, predicted 1), FP=(0,1), FN=(1,0), TN=(0,0).

Filtered automatic sampling uses the requested seed and selects up to
`sample_count` matching rows without replacement. Without an outcome filter,
existing class-balanced sampling remains unchanged. If `row_ids` is also supplied,
every selected ID must belong to the result and match the requested outcome;
IDs are not silently dropped. Empty outcome groups, inconsistent row selections,
invalid outcomes, or an outcome supplied without `explain=true` return 422 and do
not save a partial analysis.

Evaluation continues to cover the full saved partition. Its new `outcome_counts`
field gives all four group sizes. `explanation_selection` records the canonical
outcome, eligible/selected counts, selected row IDs, and group counts for frontend
filter controls and graph captions. Each explained sample additionally includes
`true_label`, `predicted_label`, `positive_probability`, and `outcome`.

### Background progress and cancellation

The frontend uses background jobs for all three cyber tasks. These requests return
`202` immediately with a `job_id` instead of holding an HTTP connection throughout
preprocessing, inference, or evaluation/explainability:

- `POST /datasets/{task}/{dataset_id}/preprocess/jobs` — same body as `/preprocess`.
- `POST /models/{model_id}/predict/jobs` — same body as `/predict`.
- `POST /results/{task}/{result_id}/analysis/jobs` — same body as `/analysis`.
- `GET /jobs/{job_id}` — status, phase, completed/total counts, percentage, error,
  and a compact result reference after success.
- `GET /jobs/{job_id}/result` — original operation response after success; `409`
  while incomplete or unsuccessful.
- `POST /jobs/{job_id}/cancel` — request cancellation (`202`).

Poll status about once a second until `succeeded`, `failed`, or `cancelled`.
`queued`, `running`, and `cancelling` are nonterminal. Progress is phase based,
not a remaining-time estimate; model loading and individual explanation batches
can take time between updates. Cancellation is checked between batches/records
and explanation forward passes. A commit that finishes before cancellation may
still succeed. Dataset reset/unload invalidates its jobs and prevents stale
prediction commits; artifact/result deletion also cancels dependent jobs.

One heavy job runs at a time, with at most 16 active/queued jobs. Identical active
requests reuse their job. Finished payloads live in temporary files, with a bounded
history of approximately 100 jobs. Jobs are local to one API process and are not
resumed after restart (`404`); saved results/analyses still follow their existing
storage lifecycle. Run a single API worker with this in-memory session architecture.
The original synchronous endpoints remain available for existing API clients.
