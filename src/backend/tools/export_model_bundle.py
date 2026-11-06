"""Notebook helper: package a trained model as a data-only service upload.

Add src/backend to sys.path in a notebook, then import export_model_bundle.
Architecture configuration must describe the model actually trained in the notebook.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED
from domain.entities.models import ModelBundle


def export_model_bundle(model, *, task, architecture, output, config=None, tokenizer=None):
    manifest = dict(schema_version=1, task=task, architecture=architecture, config=config or {})
    ModelBundle(json.dumps(manifest))
    if tokenizer is not None and architecture != 'transformer':
        raise ValueError('Only transformers accept a tokenizer')
    output = Path(output)
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        if architecture == 'transformer':
            model.save_pretrained(root, safe_serialization=True)
        else:
            from safetensors.torch import save_file
            # Clone to support shared storage/views without pickling Python model objects.
            save_file({name: tensor.detach().cpu().contiguous().clone()
                       for name, tensor in model.state_dict().items()}, root / 'model.safetensors')
        if tokenizer is not None:
            tokenizer.save_pretrained(root / 'tokenizer')
            if not (root / 'tokenizer/tokenizer.json').is_file():
                raise ValueError('Export a fast tokenizer with tokenizer.json')
        with ZipFile(output, 'w', ZIP_DEFLATED, allowZip64=True) as archive:
            for path in sorted(root.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(root).as_posix())
    return output
