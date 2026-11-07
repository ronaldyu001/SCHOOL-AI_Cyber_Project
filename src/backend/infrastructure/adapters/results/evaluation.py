"""Notebook classification metrics and graph-ready curve arrays."""
import numpy as np
from sklearn import metrics

class ClassificationEvaluation:
    def evaluate(self, rows, output_contract):
        y = np.asarray(rows['true_labels'], dtype=int)
        p = np.asarray(rows['positive_probabilities'], dtype=float)
        if not len(y):
            raise ValueError("Cannot evaluate an empty result")
        predicted = np.asarray(rows['predictions'], dtype=int)
        labels = [output_contract['prediction_labels'][str(i)] for i in (0, 1)]
        summary = dict(log_loss=float(metrics.log_loss(y, np.column_stack([1-p, p]), labels=[0, 1])),
            accuracy=float(metrics.accuracy_score(y, predicted)),
            precision=float(metrics.precision_score(y, predicted, zero_division=0)),
            recall=float(metrics.recall_score(y, predicted, zero_division=0)),
            f1=float(metrics.f1_score(y, predicted, zero_division=0)), roc_auc=None, average_precision=None)
        warnings = []
        roc = None
        pr = None
        if len(np.unique(y)) == 2:
            summary['roc_auc'] = float(metrics.roc_auc_score(y, p))
            summary['average_precision'] = float(metrics.average_precision_score(y, p))
            fpr, tpr, thresholds = metrics.roc_curve(y, p)
            roc = dict(false_positive_rate=fpr.tolist(), true_positive_rate=tpr.tolist(),
                       thresholds=[float(v) if np.isfinite(v) else None for v in thresholds])
            precision, recall, thresholds = metrics.precision_recall_curve(y, p)
            pr = dict(precision=precision.tolist(), recall=recall.tolist(), thresholds=thresholds.tolist())
        else:
            warnings.append("ROC-AUC and PR curves require both true classes; unavailable fields are null.")
        return dict(sample_count=len(y), threshold=0.5, metrics=summary,
            classification_report=metrics.classification_report(y, predicted, labels=[0, 1], target_names=labels,
                                                               output_dict=True, zero_division=0),
            confusion_matrix=dict(labels=labels, true_axis='rows', predicted_axis='columns',
                                  values=metrics.confusion_matrix(y, predicted, labels=[0, 1]).tolist()),
            roc_curve=roc, precision_recall_curve=pr, warnings=warnings)
