"""Notebook Captum analyses, returned as numeric plotting data rather than figures."""
import inspect
from application.ports.progress import checkpoint, report_progress
import numpy as np
from domain.entities.models import ModelBundle, UploadedModel

class CaptumExplanations:
    def __init__(self, runtime):
        self.runtime = runtime

    def explain(self, directory, metadata, rows, samples, options):
        import torch
        bundle = ModelBundle((directory / 'model/manifest.json').read_text())
        model = UploadedModel(metadata['model_id'], bundle, metadata['has_tokenizer'])
        report_progress("loading_explainer", 0, len(samples))
        network = self.runtime.load(model, directory / 'model')
        checkpoint()
        network.eval()
        # No torch.inference_mode here: attribution requires gradients through the model.
        with torch.enable_grad():
            if bundle.architecture == 'tabm':
                return self._tabm(network, metadata, rows, samples, options)
            if bundle.architecture == 'malconv':
                return self._malconv(network, samples, options, bundle.config)
            tokenizer_folder = directory / ('model' if metadata['has_tokenizer'] else 'preprocessing')
            if not (tokenizer_folder / 'tokenizer/tokenizer.json').is_file():
                raise ValueError('This result has no tokenizer snapshot; rerun prediction with artifacts selected')
            tokenizer = self.runtime.tokenizer(tokenizer_folder)
            return self._transformer(network, tokenizer, samples, options)

    def _tabm(self, network, metadata, rows, samples, options):
        import torch
        from captum.attr import IntegratedGradients, FeaturePermutation
        n_steps, batch = options['n_steps'], options['internal_batch_size']
        numeric_names = metadata['numeric_features']
        categorical_names = metadata['categorical_features']
        def probability(x, cat):
            checkpoint()
            return network(x, cat).softmax(-1).mean(1)[:, 1]
        explanations = []
        all_attrs = []
        for ordinal, (row_id, index, sample) in enumerate(samples):
            report_progress("explaining_samples", ordinal, len(samples))
            x = torch.tensor(sample['numeric'][None], dtype=torch.float32)
            cat = torch.tensor(sample['categorical'][None], dtype=torch.long)
            attr, delta = IntegratedGradients(probability).attribute(x, baselines=torch.zeros_like(x),
                additional_forward_args=(cat,), n_steps=n_steps, internal_batch_size=batch, return_convergence_delta=True)
            scores = attr.detach()[0].tolist()
            all_attrs.append(scores)
            with torch.no_grad():
                value = probability(x, cat).item()
                baseline = probability(torch.zeros_like(x), cat).item()
            explanations.append(dict(row_id=row_id, numeric_values=x[0].tolist(), categorical_ids=cat[0].tolist(),
                attributions=scores, prediction_value=value, baseline_value=baseline,
                convergence_delta=float(delta.item())))
        x_num = torch.tensor(np.stack([s['numeric'] for _, _, s in samples]), dtype=torch.float32)
        x_cat = torch.tensor(np.stack([s['categorical'] for _, _, s in samples]), dtype=torch.long)
        permutation = dict(available=False, reason='Select at least two rows for feature permutation')
        if len(samples) >= 2:
            targets = torch.tensor([rows['true_labels'][i] for _, i, _ in samples], dtype=torch.long)
            n_num = len(numeric_names)
            def true_probability(x, labels):
                checkpoint()
                predictions = network(x[:, :n_num], x[:, n_num:].round().long()).softmax(-1).mean(1)
                return predictions.gather(1, labels[:, None]).squeeze(1)
            x_all = torch.cat([x_num, x_cat.float()], dim=1)
            runs = []
            # Preserve process RNG state, and make repeated analyses reproducible.
            with torch.random.fork_rng(devices=[]):
                for repeat in range(options['n_repeats']):
                    report_progress('feature_permutation', repeat, options['n_repeats'])
                    torch.manual_seed(options['seed'] + repeat)
                    attr = FeaturePermutation(true_probability).attribute(x_all, additional_forward_args=(targets,))
                    runs.append(attr.detach().mean(0).numpy())
            runs = np.stack(runs)
            permutation = dict(available=True, features=numeric_names + categorical_names,
                feature_types=['numeric'] * len(numeric_names) + ['categorical'] * len(categorical_names),
                importance=runs.mean(0).tolist(), std=runs.std(0).tolist(), repeats=options['n_repeats'],
                target='true_class_probability_drop')
        report_progress('explaining_samples', len(samples), len(samples))
        return dict(method='integrated_gradients', target='attack_probability', baseline='zero standardized numeric features; categorical IDs held fixed',
            feature_names=numeric_names, samples=explanations,
            global_importance=dict(features=numeric_names, mean_absolute_attribution=np.abs(all_attrs).mean(0).tolist()),
            feature_permutation=permutation)

    def _malconv(self, network, samples, options, config):
        import torch
        from captum.attr import LayerIntegratedGradients
        def logit(tokens):
            checkpoint()
            return network(tokens).reshape(-1)
        method = LayerIntegratedGradients(logit, network.embedding_1)
        explanations = []
        for ordinal, (row_id, _, sample) in enumerate(samples):
            report_progress("explaining_samples", ordinal, len(samples))
            ids = torch.tensor(sample['byte_tokens'].astype(np.int64)[None], dtype=torch.long)
            padding = int(sample['padding_token'])
            baseline_ids = torch.full_like(ids, padding)
            attr, delta = method.attribute(ids, baselines=baseline_ids, n_steps=options['n_steps'],
                internal_batch_size=options['internal_batch_size'], return_convergence_delta=True)
            scores = attr.sum(-1)[0].detach().numpy()
            length = int(sample['length'])
            raw = (sample['byte_tokens'][:length].astype(np.int64) - int(sample['byte_offset'])).astype(np.uint8).tobytes()
            with torch.no_grad():
                value, baseline = logit(ids).item(), logit(baseline_ids).item()
            stride = config['stride']
            windows = [dict(start=start, end=min(start+stride, len(scores)), attribution=float(scores[start:start+stride].sum()))
                       for start in range(0, len(scores), stride)]
            region_ids, names, spans = self._pe_regions(raw, len(scores))
            totals = np.bincount(region_ids, weights=scores, minlength=len(names))
            top = np.argsort(-np.abs(scores))[:min(256, len(scores))]
            result = dict(row_id=row_id, sha256=str(sample['sha256']), input_length=len(scores), retained_byte_length=length,
                logit=value, malware_probability=float(torch.sigmoid(torch.tensor(value)).item()), baseline_logit=baseline,
                attribution_sum=float(scores.sum()), convergence_delta=float(delta.item()), windows=windows,
                regions=[dict(name=name, attribution=float(totals[i])) for i, name in enumerate(names)], region_spans=spans,
                top_bytes=[dict(offset=int(i), attribution=float(scores[i])) for i in top])
            if options['include_byte_attributions']: result['byte_attributions'] = scores.tolist()
            explanations.append(result)
        report_progress('explaining_samples', len(samples), len(samples))
        return dict(method='layer_integrated_gradients', target='malware_logit', baseline='all padding tokens', samples=explanations)

    def _pe_regions(self, raw, size):
        names = ['padding']
        ids = np.zeros(size, dtype=np.int32)
        spans = []
        def paint(name, start, end):
            start, end = max(0, start), min(end, len(raw))
            if end <= start: return
            names.append(name)
            ids[start:end] = len(names)-1
            spans.append(dict(name=name, start=start, end=end))
        paint('other', 0, len(raw))
        if len(raw) < 64 or raw[:2] != b'MZ': return ids, names, spans
        pe = int.from_bytes(raw[60:64], 'little')
        if pe+24 > len(raw) or raw[pe:pe+4] != b'PE\x00\x00': return ids, names, spans
        count = min(int.from_bytes(raw[pe+6:pe+8], 'little'), 96)
        table = pe+24+int.from_bytes(raw[pe+20:pe+22], 'little')
        sections = []
        for i in range(count):
            entry = raw[table+40*i:table+40*(i+1)]
            if len(entry) < 40: break
            name = entry[:8].rstrip(b'\x00').decode('ascii', errors='replace') or 'unnamed'
            start = int.from_bytes(entry[20:24], 'little')
            end = start + int.from_bytes(entry[16:20], 'little')
            if end > start: sections.append((name, start, end))
        paint('headers', 0, min((s[1] for s in sections), default=table+40*count))
        for section in sections: paint(*section)
        if sections: paint('overlay', max(s[2] for s in sections), len(raw))
        return ids, names, spans

    def _transformer(self, network, tokenizer, samples, options):
        import torch
        from captum.attr import IntegratedGradients
        embedding = network.get_input_embeddings()
        explanations, token_totals = [], {}
        for ordinal, (row_id, _, sample) in enumerate(samples):
            report_progress("explaining_samples", ordinal, len(samples))
            ids = [torch.tensor(pair[None], dtype=torch.long) for pair in sample['input_ids']]
            masks = [torch.tensor(pair[None], dtype=torch.long) for pair in sample['attention_mask']]
            premise = sample.get('premise_masks')
            if premise is None:
                encoded = tokenizer([str(sample['text'])]*2, ['This example is phishing email.', 'This example is legitimate email.'],
                    max_length=len(ids[0][0]), padding='max_length', truncation='only_first')
                if encoded['input_ids'] != sample['input_ids'].tolist():
                    raise ValueError('Cannot align saved token inputs with the tokenizer snapshot')
                premise = np.asarray([[sid == 0 for sid in encoded.sequence_ids(i)] for i in range(2)])
            token_types = sample.get('token_type_ids')
            constants = tuple(embedding(pair).detach() for pair in ids)
            if tokenizer.pad_token_id is None: raise ValueError('Explanation requires a tokenizer padding token')
            baselines = []
            for i, value in enumerate(constants):
                base = value.clone()
                padding = embedding(torch.full_like(ids[i], tokenizer.pad_token_id)).detach()
                select = torch.tensor(premise[i], dtype=torch.bool)
                base[:, select] = padding[:, select]
                baselines.append(base)
            def forward(*values):
                checkpoint()
                logits = []
                for i, full in enumerate(values):
                    batch = len(full)
                    mask = masks[i].expand(batch, -1)
                    if network.config.model_type == 'bart':
                        start = embedding(torch.tensor([[network.config.decoder_start_token_id]], dtype=torch.long)).detach()
                        decoder = torch.cat([start.expand(batch, -1, -1), full[:, :-1]], dim=1)
                        hidden = network.model(inputs_embeds=full, attention_mask=mask, decoder_inputs_embeds=decoder, use_cache=False)[0]
                        eos = ids[i][0].eq(network.config.eos_token_id)
                        if not eos.any(): raise ValueError('BART classification requires an EOS token')
                        output = network.classification_head(hidden[:, eos, :][:, -1, :])
                    else:
                        kwargs = dict(inputs_embeds=full, attention_mask=mask)
                        if token_types is not None and 'token_type_ids' in inspect.signature(network.forward).parameters:
                            kwargs['token_type_ids'] = torch.tensor(token_types[i][None], dtype=torch.long).expand(batch, -1)
                        if network.config.model_type in ('roberta', 'xlm-roberta'):
                            nonpad = ids[i].ne(network.config.pad_token_id).long()
                            positions = nonpad.cumsum(1) * nonpad + network.config.pad_token_id
                            kwargs['position_ids'] = positions.expand(batch, -1)
                        output = network(**kwargs).logits
                    logits.append(output[:, 2])
                return logits[0]-logits[1]
            # Verify the embedding-based explanation targets the exact saved input computation.
            with torch.no_grad():
                actual_kwargs = dict(input_ids=torch.cat(ids), attention_mask=torch.cat(masks))
                if token_types is not None and 'token_type_ids' in inspect.signature(network.forward).parameters:
                    actual_kwargs['token_type_ids'] = torch.tensor(token_types, dtype=torch.long)
                actual_logits = network(**actual_kwargs).logits[:, 2]
                actual_margin = actual_logits[0] - actual_logits[1]
                if not torch.allclose(forward(*constants)[0], actual_margin, rtol=1e-4, atol=1e-5):
                    raise ValueError('The explanation forward path does not reproduce this transformer configuration')
            attrs, delta = IntegratedGradients(forward).attribute(constants, baselines=tuple(baselines),
                n_steps=options['n_steps'], internal_batch_size=options['internal_batch_size'], return_convergence_delta=True)
            combined = []
            pair_ids = []
            for i in range(2):
                selected = np.flatnonzero(premise[i])
                pair_ids.append(sample['input_ids'][i][selected].tolist())
                values = attrs[i].sum(-1)[0].detach().numpy()[selected]
                while len(combined) < len(values): combined.append(0.0)
                for j, value in enumerate(values): combined[j] += float(value)
            longest = max(pair_ids, key=len)
            tokens = tokenizer.convert_ids_to_tokens(longest)
            for token, score in zip(tokens, combined):
                key = token.lstrip('Ġ▁').lower()
                stats = token_totals.setdefault(key, [0.0, 0.0, 0])
                stats[0] += score; stats[1] += abs(score); stats[2] += 1
            with torch.no_grad():
                margin = forward(*constants).item()
                baseline_margin = forward(*baselines).item()
            explanations.append(dict(row_id=row_id, tokens=tokens, token_ids=longest, attributions=combined,
                margin=margin, baseline_margin=baseline_margin, phishing_probability=float(torch.sigmoid(torch.tensor(margin)).item()),
                convergence_delta=float(delta.item()), retained_premise_tokens=len(longest)))
        importance = [dict(token=token, mean_attribution=v[0]/v[2], mean_absolute_attribution=v[1]/v[2], count=v[2])
                      for token, v in token_totals.items()]
        importance.sort(key=lambda item: item['mean_absolute_attribution'], reverse=True)
        report_progress('explaining_samples', len(samples), len(samples))
        return dict(method='integrated_gradients', target='phishing_entailment_margin',
            baseline='padding embeddings for email tokens; special tokens and hypotheses held fixed',
            samples=explanations, global_token_importance=importance)
