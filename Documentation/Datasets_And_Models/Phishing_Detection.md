# Dataset

[Phishing Email Dataset — Kaggle](https://www.kaggle.com/datasets/naserabdullahalam/phishing-email-dataset)

Place the selected CSV under `src/backend/.data/phishing_detection/`. Verify filename, text column, and label mapping in the notebook; the source schema has not yet been verified locally.

# Model

[AI-Phishing-Detector](https://github.com/salhabheba-cyber/AI-Phishing-Detector) describes zero-shot classification with `facebook/bart-large-mnli`. The notebook follows that approach, with explicit experimental labels and binary argmax classification. It does not claim to reproduce unavailable implementation details or the reference's reported accuracy.

# Validation

Notebook code has been syntax-checked. Dataset loading and model evaluation require the local CSV, dependencies, and model weights; no measured results are available yet.
