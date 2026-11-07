"""Package the exact notebook baselines from trusted LOCAL checkpoints and HF cache.

Run from the repository root:
  PYTHONPATH=src/backend src/backend/.venv/bin/python src/backend/tools/prepare_baseline_models.py

Network checkpoint deserialization is deliberately restricted to the known local
notebook file: it contains fitted sklearn objects. User uploads never use pickle.
"""
import gc
from hashlib import sha256
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_STORED

from domain.entities.models import ModelBundle, UploadedModel
from infrastructure.adapters.models.runtime import ModelRuntime

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / 'src/backend/.models'
NETWORK_CHECKPOINT = ROOT / 'Training/Network_Intrusion/.models/20261015_095219_939710/epoch_026.pt'
MALWARE_CHECKPOINT = ROOT / 'Training/Malware_Detection/.models/20261104_131637_676400/best.pt'
BART_REVISION = 'd7645e127eaf1aefc7862fd59a17a5aa8558b8ce'


def digest(path):
    checksum = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def json_file(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def network(folder):
    import torch
    from safetensors.torch import save_file
    # This is the existing notebook checkpoint, not an uploaded file.
    checkpoint = torch.load(NETWORK_CHECKPOINT, map_location='cpu', weights_only=False)
    config = checkpoint['model_config']
    state = checkpoint['model']
    blocks = {name.split('.')[2] for name in state if name.startswith('backbone.blocks.')}
    architecture = dict(n_num_features=config['n_num_features'], cat_cardinalities=config['cat_cardinalities'],
                        n_blocks=len(blocks), d_block=state['backbone.blocks.0.0.weight'].shape[0],
                        k=state['output.weight'].shape[0], dropout=0.1, activation='ReLU', arch_type='tabm',
                        num_embeddings=dict(bins=[edges.cpu().tolist() for edges in config['bins']],
                                            d_embedding=config['d_embedding'], activation=config['activation'], version=config['version']))
    save_file({name: value.detach().cpu().contiguous().clone() for name, value in state.items()}, folder / 'model.safetensors')
    pipeline = checkpoint['numeric_preprocessing']
    imputer, scaler = pipeline.named_steps['simpleimputer'], pipeline.named_steps['standardscaler']
    json_file(folder / 'preprocessing.json', dict(numeric_features=checkpoint['num_cols'], categorical_features=checkpoint['cat_cols'],
              imputer='median', all_missing_fill=0, scaler='standard', numeric_dtype='float32',
              fill_values=imputer.statistics_.tolist(), means=scaler.mean_.tolist(), scales=scaler.scale_.tolist(),
              variances=scaler.var_.tolist(), category_maps=checkpoint['category_maps'],
              category_cardinalities=config['cat_cardinalities'], unknown_category_id=0, missing_category_id=1))
    return 'tabm', architecture, dict(notebook='Training/Network_Intrusion/network_intrusion.ipynb',
        checkpoint=str(NETWORK_CHECKPOINT.relative_to(ROOT)), checkpoint_sha256=digest(NETWORK_CHECKPOINT),
        epoch=checkpoint['epoch'], metrics=checkpoint['metrics'], training_config=checkpoint['training_config'],
        architecture_notes='Depth, width, and ensemble size verified from checkpoint tensor shapes; ReLU/dropout=0.1 follow notebook TabM defaults.')


def malware(folder):
    import torch
    from safetensors.torch import save_file
    checkpoint = torch.load(MALWARE_CHECKPOINT, map_location='cpu', weights_only=True)
    config = checkpoint['model_config']
    state = checkpoint['model']
    architecture = dict(embedding_dim=config['embedding_size'], channels=state['conv1d_1.weight'].shape[0],
                        kernel_size=config['kernel_size'], stride=config['stride'], hidden_size=state['dense_1.weight'].shape[0],
                        activation='ReLU', padding_idx=config['padding_idx'])
    save_file({name: value.detach().cpu().contiguous().clone() for name, value in state.items()}, folder / 'model.safetensors')
    json_file(folder / 'preprocessing.json', checkpoint['preprocessing'])
    return 'malconv', architecture, dict(notebook='Training/Malware_Detection/Malware_Detection.ipynb',
        checkpoint=str(MALWARE_CHECKPOINT.relative_to(ROOT)), checkpoint_sha256=digest(MALWARE_CHECKPOINT),
        epoch=checkpoint['epoch'], metrics=checkpoint['metrics'], training_config=checkpoint['training_config'],
        dataset_version=checkpoint['dataset_version'], split_row_ids=checkpoint['split_row_ids'],
        split_hashes=checkpoint['split_hashes'], model_library=checkpoint['model_library'])


def phishing(folder):
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    source = Path(snapshot_download('facebook/bart-large-mnli', revision=BART_REVISION, local_files_only=True))
    # Copy actual local bytes; exported baselines must not depend on cache symlinks.
    for name in ('config.json', 'model.safetensors'):
        shutil.copyfile(source / name, folder / name)
    tokenizer = AutoTokenizer.from_pretrained(source, local_files_only=True, trust_remote_code=False)
    tokenizer.save_pretrained(folder / 'tokenizer')
    json_file(folder / 'preprocessing.json', dict(tokenizer_id='facebook/bart-large-mnli', tokenizer_revision=BART_REVISION,
              candidate_labels=['phishing email', 'legitimate email'], hypothesis_template='This example is {}.',
              padding='max_length', truncation='only_first', max_length=1024))
    return 'transformer', {}, dict(notebook='Training/Phishing_Detection/Phishing_Detection.ipynb',
        model_id='facebook/bart-large-mnli', revision=BART_REVISION, fine_tuned=False,
        notes='The notebook baseline is pretrained zero-shot BART-MNLI; no dataset fine-tuning checkpoint exists.')


def prepare(task, builder):
    destination = OUTPUT / task
    if destination.exists():
        raise FileExistsError(f'{destination} already exists; move it before regenerating baselines')
    with TemporaryDirectory(prefix=f'.{task}-', dir=OUTPUT) as temporary:
        folder = Path(temporary)
        print(f'Preparing {task}...', flush=True)
        architecture, config, provenance = builder(folder)
        manifest = dict(schema_version=1, task=task, architecture=architecture, config=config)
        json_file(folder / 'manifest.json', manifest)
        bundle = ModelBundle(json.dumps(manifest))
        model = UploadedModel('baseline-' + task, bundle, (folder / 'tokenizer').is_dir())
        ModelRuntime().validate(model, folder)
        gc.collect()
        files = [p for p in folder.rglob('*') if p.is_file() and p.name != 'preprocessing.json']
        # Upload bundle uses exactly the data-only /models/upload contract.
        with ZipFile(folder / 'baseline.zip', 'w', ZIP_STORED, allowZip64=True) as archive:
            for path in sorted(files):
                archive.write(path, path.relative_to(folder).as_posix())
        provenance['output_contract'] = bundle.output_contract
        provenance['files_sha256'] = {p.relative_to(folder).as_posix(): digest(p) for p in folder.rglob('*') if p.is_file()}
        json_file(folder / 'baseline.json', provenance)
        shutil.move(str(folder), str(destination))
        print(f'Validated {destination}', flush=True)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for task, builder in [('network_intrusion', network), ('malware_detection', malware), ('phishing_detection', phishing)]:
        prepare(task, builder)


if __name__ == '__main__':
    main()
