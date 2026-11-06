"""CPU-only, data-only model loaders; no pickle, remote code, or implicit downloads."""
import json
from pathlib import Path
from domain.entities.models import FAMILIES

class ModelRuntimeUnavailable(RuntimeError):
    pass

class ModelRuntime:
    def _torch(self):
        try:
            import torch
            return torch
        except ImportError as error:
            raise ModelRuntimeUnavailable("Install the backend model runtime dependencies") from error

    def tokenizer(self, directory):
        # tokenizer.json is the full fast-tokenizer graph; metadata supplies special tokens.
        from transformers import PreTrainedTokenizerFast
        folder = Path(directory) / 'tokenizer'
        settings = {}
        for filename in ('tokenizer_config.json', 'special_tokens_map.json'):
            if (folder / filename).exists():
                settings.update(json.loads((folder / filename).read_text()))
        selected = {}
        for key in ('pad_token', 'bos_token', 'eos_token', 'unk_token', 'sep_token', 'cls_token', 'mask_token', 'additional_special_tokens'):
            if key in settings:
                value = settings[key]
                def token(v):
                    return v['content'] if isinstance(v, dict) else v
                selected[key] = [token(v) for v in value] if isinstance(value, list) else token(value)
        for side in ('padding_side', 'truncation_side'):
            if settings.get(side) in ('left', 'right'):
                selected[side] = settings[side]
        try:
            return PreTrainedTokenizerFast(tokenizer_file=str(folder / 'tokenizer.json'), **selected)
        except Exception as error:
            raise ValueError('Invalid fast tokenizer data') from error

    def load(self, model, directory):
        torch = self._torch()
        config = model.bundle.config
        if model.bundle.architecture == 'transformer':
            from transformers import AutoConfig, AutoModelForSequenceClassification
            raw = json.loads((directory / 'config.json').read_text())
            if raw.get('model_type') not in FAMILIES:
                raise ValueError("Unsupported transformer family")
            hf_config = AutoConfig.from_pretrained(directory, local_files_only=True, trust_remote_code=False)
            if hf_config.num_labels != 3:
                raise ValueError("Transformer output must be 3 NLI logits: contradiction, neutral, entailment")
            network, info = AutoModelForSequenceClassification.from_pretrained(
                directory, config=hf_config, local_files_only=True, trust_remote_code=False,
                use_safetensors=True, output_loading_info=True)
            if any(info.get(key) for key in ('missing_keys', 'unexpected_keys', 'mismatched_keys', 'error_msgs')):
                raise ValueError("Transformer weights do not fully match config.json")
        else:
            if model.bundle.architecture == 'malconv':
                from .malconv import MalConv
                network = MalConv(**config)
            else:
                import tabm
                import rtdl_num_embeddings
                config = dict(config)
                embedding = config.pop('num_embeddings')
                if embedding is not None:
                    embedding = dict(embedding)
                    embedding['bins'] = [torch.tensor(edges, dtype=torch.float32) for edges in embedding['bins']]
                    config['num_embeddings'] = rtdl_num_embeddings.PiecewiseLinearEmbeddings(**embedding)
                network = tabm.TabM.make(**config, d_out=2)
            from safetensors.torch import load_file
            from safetensors import SafetensorError
            try:
                network.load_state_dict(load_file(str(directory / 'model.safetensors'), device='cpu'), strict=True)
            except SafetensorError as error:
                raise ValueError('Invalid safetensors weights') from error
        return network.cpu().eval()

    def validate(self, model, directory):
        # Do not judge training/tokenizer alignment; require loadable weights and a data-only tokenizer.
        network = self.load(model, directory)
        del network
        if model.has_tokenizer:
            self.tokenizer(directory)

    def predict(self, model, directory, dataset):
        torch = self._torch()
        network = self.load(model, directory)
        scores = []
        with torch.inference_mode():
            # Process one sample at a time to avoid constructing a second whole-partition tensor.
            for i in range(len(dataset.row_ids)):
                if model.bundle.architecture == 'malconv':
                    if dataset.padding_token != model.bundle.config['padding_idx']:
                        raise ValueError("Model padding_idx must match the selected byte preprocessing")
                    if dataset.max_length < model.bundle.config['kernel_size']:
                        raise ValueError("Input length must accommodate the convolution kernel")
                    logits = network(torch.tensor([dataset.byte_tokens[i]], dtype=torch.long))
                    probability = logits.sigmoid().item()
                elif model.bundle.architecture == 'tabm':
                    if tuple(model.bundle.config['cat_cardinalities']) != dataset.category_cardinalities:
                        raise ValueError("Model cardinalities must match preprocessed categories")
                    logits = network(torch.tensor([dataset.numeric[i]], dtype=torch.float32),
                                     torch.tensor([dataset.categorical[i]], dtype=torch.long))
                    probability = logits.softmax(-1).mean(1)[0, 1].item()
                else:
                    if dataset.candidate_labels != ("phishing email", "legitimate email"):
                        raise ValueError("Candidate order must follow the service phishing output contract")
                    if not dataset.input_ids:
                        raise ValueError("Tokenized candidate pairs are required")
                    kwargs = dict(input_ids=torch.tensor(dataset.input_ids[i], dtype=torch.long),
                                  attention_mask=torch.tensor(dataset.attention_mask[i], dtype=torch.long))
                    # DistilBERT/BART do not take token_type_ids; BERT-like families do.
                    import inspect
                    if dataset.token_type_ids and 'token_type_ids' in inspect.signature(network.forward).parameters:
                        kwargs['token_type_ids'] = torch.tensor(dataset.token_type_ids[i], dtype=torch.long)
                    logits = network(**kwargs).logits
                    probability = logits[:, 2].softmax(dim=0)[0].item()
                scores.append(float(probability))
        return scores
