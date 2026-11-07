"""Atomic task-scoped result snapshots. NumPy arrays never deserialize pickle."""
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from threading import RLock
from uuid import uuid4
from zipfile import ZipFile, ZIP_STORED
import numpy as np
from domain.entities.datasets.common import CyberTask
from domain.entities.results import PredictionRows

class ResultNotFound(LookupError):
    pass


def write_json(path, value):
    path.write_text(json.dumps(value, allow_nan=False, ensure_ascii=False))


def copy_snapshot(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.rglob('*'):
        if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
            raise ValueError("Snapshot members must be ordinary local files")
        target = destination / path.relative_to(source)
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(path, target)  # Immutable uploads: unlinking either copy preserves the other.
            except OSError:
                shutil.copyfile(path, target)


class ResultStore:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = RLock()

    def path(self, task, result_id=None):
        task = CyberTask(task).value
        if result_id is not None and not re.fullmatch(r'[0-9a-f]{32}', result_id):
            raise ValueError("Invalid result ID")
        folder = self.root / task
        return folder if result_id is None else folder / result_id

    def save(self, prediction, dataset, model, directory, context):
        rows = PredictionRows(tuple(dataset.row_ids), tuple(dataset.labels), tuple(prediction['positive_probabilities']))
        task = dataset.source.task.value
        result_id = uuid4().hex
        root = self.path(task)
        with self.lock:
            root.mkdir(parents=True, exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix='.pending-', dir=root))
            try:
                metadata = dict(schema_version=1, result_id=result_id, task=task,
                    dataset_id=context['dataset_id'], preprocessed_id=context['preprocessed_id'],
                    model_id=model.model_id, architecture=model.bundle.architecture,
                    has_tokenizer=model.has_tokenizer, source=asdict(dataset.source),
                    artifact_id=dataset.artifact_id, partition=dataset.partition,
                    sample_count=len(rows.row_ids), created_at=datetime.now(timezone.utc).isoformat(),
                    output_contract=prediction['output_contract'])
                if hasattr(dataset, 'numeric_features'):
                    metadata.update(numeric_features=list(dataset.numeric_features), categorical_features=list(dataset.categorical_features))
                if hasattr(dataset, 'candidate_labels'):
                    metadata['candidate_labels'] = list(dataset.candidate_labels)
                write_json(temporary / 'metadata.json', metadata)
                write_json(temporary / 'predictions.json', dict(row_ids=list(rows.row_ids), true_labels=list(rows.labels),
                    positive_probabilities=list(rows.probabilities), predictions=prediction['predictions']))
                copy_snapshot(directory, temporary / 'model')
                artifact = context.get('artifact_directory')
                if artifact is not None:
                    copy_snapshot(Path(artifact), temporary / 'preprocessing')
                with ZipFile(temporary / 'inputs.zip', 'w', ZIP_STORED, allowZip64=True) as archive:
                    for i in range(len(rows.row_ids)):
                        if model.bundle.architecture == 'tabm':
                            arrays = dict(numeric=np.asarray(dataset.numeric[i], dtype=np.float32),
                                          categorical=np.asarray(dataset.categorical[i], dtype=np.int64))
                        elif model.bundle.architecture == 'malconv':
                            arrays = dict(byte_tokens=np.asarray(dataset.byte_tokens[i], dtype=np.uint16),
                                length=np.asarray(dataset.lengths[i]), padding_token=np.asarray(dataset.padding_token),
                                byte_offset=np.asarray(dataset.byte_offset), sha256=np.asarray(dataset.hashes[i]))
                        else:
                            arrays = dict(input_ids=np.asarray(dataset.input_ids[i], dtype=np.int64),
                                          attention_mask=np.asarray(dataset.attention_mask[i], dtype=np.uint8),
                                          text=np.asarray(dataset.texts[i]))
                            if dataset.token_type_ids:
                                arrays['token_type_ids'] = np.asarray(dataset.token_type_ids[i], dtype=np.int64)
                            if dataset.premise_masks:
                                arrays['premise_masks'] = np.asarray(dataset.premise_masks[i], dtype=np.uint8)
                        output = io.BytesIO()
                        np.savez_compressed(output, **arrays)
                        archive.writestr(f'{i:08d}.npz', output.getvalue())
                os.rename(temporary, root / result_id)
            finally:
                if temporary.exists(): shutil.rmtree(temporary)
        return result_id

    @contextmanager
    def borrow(self, task, result_id):
        with self.lock:
            directory = self.path(task, result_id)
            if not (directory / 'metadata.json').is_file():
                raise ResultNotFound("Result not found for this task")
            yield directory, json.loads((directory / 'metadata.json').read_text())

    def rows(self, directory):
        return json.loads((directory / 'predictions.json').read_text())

    def sample(self, directory, index):
        with ZipFile(directory / 'inputs.zip') as archive:
            with np.load(io.BytesIO(archive.read(f'{index:08d}.npz')), allow_pickle=False) as arrays:
                return {key: arrays[key] for key in arrays.files}

    def list(self, task):
        with self.lock:
            root = self.path(task)
            return [json.loads(p.read_text()) for p in sorted(root.glob('*/metadata.json')) if not p.parent.name.startswith('.')]

    def delete(self, task, result_id):
        with self.borrow(task, result_id) as (directory, _):
            shutil.rmtree(directory)

    def clear(self, task, *, dataset_id=None, artifact_id=None):
        with self.lock:
            for metadata in self.list(task):
                if dataset_id is not None and metadata['dataset_id'] != dataset_id: continue
                if artifact_id is not None and metadata['artifact_id'] != artifact_id: continue
                self.delete(task, metadata['result_id'])

    def save_analysis(self, directory, payload):
        analysis_id = uuid4().hex
        payload = dict(payload, analysis_id=analysis_id)
        target = directory / 'analyses'
        target.mkdir(exist_ok=True)
        temporary = target / ('.' + analysis_id)
        try:
            write_json(temporary, payload)
            os.replace(temporary, target / (analysis_id + '.json'))
        finally:
            temporary.unlink(missing_ok=True)
        return payload

    def analysis_path(self, directory, analysis_id):
        if not re.fullmatch('[0-9a-f]{32}', analysis_id):
            raise ValueError("Invalid analysis ID")
        path = directory / 'analyses' / (analysis_id + '.json')
        if not path.is_file(): raise ResultNotFound("Analysis not found")
        return path
