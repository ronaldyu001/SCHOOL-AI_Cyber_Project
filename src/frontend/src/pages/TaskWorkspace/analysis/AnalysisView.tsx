/**
 * One saved analysis: the evaluation of the whole partition, then whatever
 * attributions the request asked for.
 *
 * Evaluation and explanation cover different row sets by design — metrics are
 * always the full partition, while attributions are the selected sample — so
 * the two are kept visibly apart.
 */
import type { Analysis, ClassScore, Evaluation } from '../../../api/types';
import { StatusNote } from '../../../components/ui';
import { Curve } from './Charts';
import { Explanations } from './Explanations';
import './Analysis.css';

const format = (value: number | null, digits = 4) =>
  value === null || !Number.isFinite(value) ? '—' : value.toFixed(digits);

const isClassScore = (value: ClassScore | number): value is ClassScore => typeof value === 'object';

function Metrics({ evaluation }: { evaluation: Evaluation }) {
  const { metrics } = evaluation;
  const cards: [string, string][] = [
    ['Accuracy', format(metrics.accuracy)],
    ['Precision', format(metrics.precision)],
    ['Recall', format(metrics.recall)],
    ['F1', format(metrics.f1)],
    ['ROC-AUC', format(metrics.roc_auc)],
    ['Average precision', format(metrics.average_precision)],
    ['Log loss', format(metrics.log_loss)],
  ];
  return (
    <dl className="metrics">
      {cards.map(([label, value]) => (
        <div className="metrics__card" key={label}>
          <dt>{label}</dt>
          <dd className="mono">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function ConfusionMatrix({ evaluation }: { evaluation: Evaluation }) {
  const { labels, values } = evaluation.confusion_matrix;
  const total = values.flat().reduce((sum, value) => sum + value, 0);
  return (
    <figure className="chart">
      <figcaption className="chart__title">
        Confusion matrix
        <span className="chart__summary">rows are true classes, columns predicted</span>
      </figcaption>
      <table className="matrix">
        <thead>
          <tr>
            <th scope="col"><span className="sr-only">True class</span></th>
            {labels.map((label) => (
              <th scope="col" key={label}>Predicted {label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {values.map((row, index) => (
            <tr key={labels[index]}>
              <th scope="row">True {labels[index]}</th>
              {row.map((count, column) => (
                <td
                  key={labels[column]}
                  className={`matrix__cell${index === column ? ' matrix__cell--hit' : ''}`}
                  style={{ '--share': total === 0 ? 0 : count / total } as React.CSSProperties}
                >
                  <span className="mono">{count.toLocaleString()}</span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

function Report({ evaluation }: { evaluation: Evaluation }) {
  const rows = Object.entries(evaluation.classification_report).filter(([, value]) => isClassScore(value)) as [string, ClassScore][];
  return (
    <div className="analysis__table-wrap">
      <table className="analysis__table">
        <caption className="sr-only">Classification report</caption>
        <thead>
          <tr>
            <th scope="col">Class</th>
            <th scope="col">Precision</th>
            <th scope="col">Recall</th>
            <th scope="col">F1</th>
            <th scope="col">Support</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([name, score]) => (
            <tr key={name}>
              <th scope="row">{name}</th>
              <td className="mono">{format(score.precision)}</td>
              <td className="mono">{format(score.recall)}</td>
              <td className="mono">{format(score['f1-score'])}</td>
              <td className="mono">{score.support.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AnalysisView({ analysis }: { analysis: Analysis }) {
  const { evaluation } = analysis;
  const positives = evaluation.confusion_matrix.values[1]?.reduce((sum, value) => sum + value, 0) ?? 0;
  // The no-skill line for precision-recall is the share of positives, which a
  // ROC's diagonal has no equivalent of.
  const baseRate = evaluation.sample_count === 0 ? 0 : positives / evaluation.sample_count;

  return (
    <div className="analysis__analysis">
      <p className="analysis__note">
        {`Evaluated ${evaluation.sample_count.toLocaleString()} rows at the service's fixed ${evaluation.threshold} threshold.`}
      </p>

      {evaluation.warnings.map((warning) => (
        <StatusNote tone="warn" key={warning}>{warning}</StatusNote>
      ))}

      <Metrics evaluation={evaluation} />

      <div className="analysis__charts">
        <ConfusionMatrix evaluation={evaluation} />
        {evaluation.roc_curve === null ? null : (
          <Curve
            title="ROC curve"
            summary={`AUC ${format(evaluation.metrics.roc_auc, 3)}`}
            x={evaluation.roc_curve.false_positive_rate}
            y={evaluation.roc_curve.true_positive_rate}
            xLabel="False positive rate"
            yLabel="True positive rate"
            reference="diagonal"
          />
        )}
        {evaluation.precision_recall_curve === null ? null : (
          <Curve
            title="Precision–recall curve"
            summary={`AP ${format(evaluation.metrics.average_precision, 3)}`}
            x={evaluation.precision_recall_curve.recall}
            y={evaluation.precision_recall_curve.precision}
            xLabel="Recall"
            yLabel="Precision"
            reference={baseRate}
          />
        )}
      </div>

      <h3 className="analysis__heading">Classification report</h3>
      <Report evaluation={evaluation} />

      {analysis.explainability === null ? (
        <p className="analysis__note">
          This analysis was evaluation only. Run another with explanations to attribute individual rows.
        </p>
      ) : (
        <Explanations task={analysis.task} explainability={analysis.explainability} />
      )}
    </div>
  );
}
