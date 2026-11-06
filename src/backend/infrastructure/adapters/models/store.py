"""Temporary, model-scoped ZIP storage. Only data files are extracted."""
from contextlib import contextmanager
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import shutil
from stat import S_ISLNK
from tempfile import TemporaryDirectory
from threading import RLock
from uuid import uuid4
from zipfile import ZipFile, BadZipFile
from domain.entities.models import ModelBundle, UploadedModel

class ModelNotFound(LookupError):
    pass

@dataclass
class Entry:
    model: UploadedModel
    directory: Path
    lock: RLock = field(default_factory=RLock)
    ready: bool = False

class ModelBundleStore:
    def __init__(self):
        self.temporary = TemporaryDirectory(prefix="cyber-models-")
        self.root = Path(self.temporary.name)
        self.entries = {}
        self.lock = RLock()

    def upload(self, stream):
        model_id = str(uuid4())
        directory = self.root / model_id
        directory.mkdir()
        try:
            with ZipFile(stream) as archive:
                names = set()
                size = 0
                for member in archive.infolist():
                    name = member.filename
                    parts = name.rstrip('/').split('/')
                    if name.startswith('/') or '\\' in name or any(p in ('', '.', '..') for p in parts) or S_ISLNK(member.external_attr >> 16):
                        raise ValueError("Unsafe model bundle member")
                    if member.is_dir():
                        if name != 'tokenizer/':
                            raise ValueError("Unexpected model bundle directory")
                        continue
                    if name in names:
                        raise ValueError("Duplicate bundle member")
                    names.add(name)
                    allowed = name in ('manifest.json', 'config.json', 'model.safetensors', 'model.safetensors.index.json')
                    allowed |= bool(re.fullmatch(r'model-\d+-of-\d+\.safetensors', name))
                    allowed |= len(parts) == 2 and parts[0] == 'tokenizer' and parts[1] in {
                        'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json', 'added_tokens.json',
                        'vocab.json', 'vocab.txt', 'merges.txt', 'spiece.model', 'sentencepiece.bpe.model', 'config.json'}
                    if not allowed:
                        raise ValueError("Only model configuration, safetensors and tokenizer data files are accepted")
                    size += member.file_size
                    if size > 16 * 1024**3 or len(names) > 1024:
                        raise ValueError("Model bundle exceeds 16 GiB or 1024 files")
                    if name.endswith('.json') and member.file_size > 64 * 1024**2:
                        raise ValueError("JSON member exceeds 64 MiB")
                    target = directory / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, target.open('wb') as destination:
                        shutil.copyfileobj(source, destination, length=1024 * 1024)
            if not (directory / 'manifest.json').is_file():
                raise ValueError("manifest.json is required")
            bundle = ModelBundle((directory / 'manifest.json').read_text())
            has_tokenizer = any(n.startswith('tokenizer/') for n in names)
            if has_tokenizer and bundle.architecture != 'transformer':
                raise ValueError("Only transformers accept tokenizer files")
            if has_tokenizer and 'tokenizer/tokenizer.json' not in names:
                raise ValueError("Upload a fast tokenizer with tokenizer/tokenizer.json")
            if bundle.architecture == 'transformer':
                if 'config.json' not in names:
                    raise ValueError("Transformer config.json is required")
                if not ({'model.safetensors', 'model.safetensors.index.json'} & names):
                    raise ValueError("Transformer safetensors weights are required")
            elif 'model.safetensors' not in names or 'config.json' in names or any('of-' in n for n in names):
                raise ValueError("TabM and MalConv require one model.safetensors and manifest config")
            # Forbid remote/custom-code declarations even though runtime loading disables them.
            for name in names:
                if name.endswith('.json'):
                    value = json.loads((directory / name).read_text())
                    self._check_json(value)
            index = directory / 'model.safetensors.index.json'
            if index.exists():
                mapping = json.loads(index.read_text()).get('weight_map')
                if not isinstance(mapping, dict) or not mapping or any(not isinstance(v, str) or not re.fullmatch(r'model-\d+-of-\d+\.safetensors', v) or v not in names for v in mapping.values()):
                    raise ValueError("Weight index must reference included safetensors shards")
            model = UploadedModel(model_id, bundle, has_tokenizer)
            with self.lock:
                self.entries[model_id] = Entry(model, directory)
            return model
        except BaseException as error:
            shutil.rmtree(directory, ignore_errors=True)
            if isinstance(error, (BadZipFile, UnicodeError, json.JSONDecodeError, KeyError, TypeError)):
                raise ValueError("Invalid model ZIP or JSON metadata") from error
            raise

    def _check_json(self, value):
        if isinstance(value, dict):
            if {'auto_map', 'custom_pipelines'} & value.keys():
                raise ValueError("Custom model/tokenizer code is unsupported")
            for child in value.values(): self._check_json(child)
        elif isinstance(value, list):
            for child in value: self._check_json(child)

    @contextmanager
    def borrow(self, model_id, *, pending=False):
        with self.lock:
            entry = self.entries.get(model_id)
            if entry is None or (not pending and not entry.ready):
                raise ModelNotFound("Model not found")
        with entry.lock:
            with self.lock:
                if self.entries.get(model_id) is not entry:
                    raise ModelNotFound("Model not found")
            yield entry.model, entry.directory

    def publish(self, model_id):
        with self.borrow(model_id, pending=True):
            self.entries[model_id].ready = True

    def list(self):
        with self.lock:
            return [entry.model for entry in self.entries.values() if entry.ready]

    def delete(self, model_id):
        with self.borrow(model_id, pending=True) as (_, directory):
            with self.lock:
                del self.entries[model_id]
            shutil.rmtree(directory)

    def close(self):
        # Never hold the registry lock while waiting for an individual model lock.
        with self.lock:
            model_ids = list(self.entries)
        for model_id in model_ids:
            try:
                self.delete(model_id)
            except ModelNotFound:
                pass
        self.temporary.cleanup()
