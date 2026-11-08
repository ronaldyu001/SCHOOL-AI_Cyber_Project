import { useBackgroundJob } from '../../../jobs/use-background-job';
import { JobProgress } from '../../../jobs/JobProgress';
/**
 * Scores a preprocessed partition with the model selected in the task pipeline.
 *
 * What the numbers mean belongs to the model's output contract, not to the
 * task catalog, so the class names shown here come back with the predictions.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { startPrediction } from '../../../api/models';
import type { PredictionResponse, PreprocessResponse, UploadedModel } from '../../../api/types';
import { StepCard } from '../../../components/StepCard';
import { Button, StatusNote, Summary } from '../../../components/ui';
import type { TaskDescriptor } from '../../../tasks/catalog';
import { useAction } from '../use-action';

/** Scores arrive for the whole partition at once; the table shows a page of it. */
const PAGE_SIZE = 20;

interface PredictStepProps {
  task: TaskDescriptor;
  model: UploadedModel | null;
  datasetId: string | null;
  preprocessed: PreprocessResponse | null;
  /** A prediction was saved, which the dataset must now outlive. */
  onSaved: (resultId: string) => void;
}

export function PredictStep({ model, datasetId, preprocessed, onSaved }: PredictStepProps) {
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [page, setPage] = useState(0);

  // A transformer reads the token IDs its own tokenizer produced, so the
  // partition has to have been preprocessed for this exact model.
  const needsOwnTokens =
    model !== null &&
    model.architecture === 'transformer' &&
    preprocessed?.model_id !== model.model_id;

  const operation = useBackgroundJob<PredictionResponse>((scored) => {
    setResult(scored);
    setPage(0);
    onSaved(scored.result_id);
  });
  const action = useAction(async (dataset: string, preprocessedId: string, id: string) => {
    setResult(null);
    operation.track(await startPrediction(id, dataset, preprocessedId));
  });

  const labels = result?.output_contract.prediction_labels ?? {};
  const scored = result?.row_ids.length ?? 0;
  const positives = result?.predictions.reduce((sum, value) => sum + value, 0) ?? 0;
  const meanScore =
    result === null || scored === 0
      ? 0
      : result.positive_probabilities.reduce((sum, value) => sum + value, 0) / scored;
  const lastPage = scored === 0 ? 0 : Math.ceil(scored / PAGE_SIZE) - 1;
  const start = page * PAGE_SIZE;

  return (
    <StepCard
      step={7}
      title="Predict"
      description="Scores the preprocessed partition with the selected model."
      state={result !== null ? 'done' : preprocessed === null || model === null ? 'locked' : 'ready'}
      lockedHint="Select a model and preprocess a partition first."
    >
      {datasetId === null || preprocessed === null ? null : (
        <>
          {model === null ? null : (
            <>
              <p className="work__hint">{`Selected model: ${model.architecture} · ${model.model_id.slice(0, 16)}`}</p>
              {needsOwnTokens ? (
                <StatusNote tone="warn">
                  This partition was tokenized{preprocessed.model_id === null
                    ? ' with the service default'
                    : ' for another model'}. Preprocess it again with this model selected before
                  scoring.
                </StatusNote>
              ) : null}

              <div className="work__row">
                <Button
                  variant="primary"
                  pending={action.pending}
                  disabled={needsOwnTokens || operation.active}
                  onClick={() => void action.run(datasetId, preprocessed.preprocessed_id, model.model_id)}
                >
                  Score {preprocessed.partition} partition
                </Button>

              </div>
            </>
          )}

          <JobProgress job={operation.job} error={operation.error} onCancel={operation.cancel} />
          {action.error === null ? null : <StatusNote tone="danger">{action.error}</StatusNote>}

          {result === null ? null : (
            <>
              <Summary
                items={[
                  { label: 'Rows scored', value: scored.toLocaleString() },
                  { label: `Predicted ${labels['1'] ?? 'positive'}`, value: positives.toLocaleString() },
                  {
                    label: `Predicted ${labels['0'] ?? 'negative'}`,
                    value: (scored - positives).toLocaleString(),
                  },
                  { label: 'Mean probability', value: meanScore.toFixed(4), mono: true },
                ]}
              />
              <p className="work__hint">
                {`Each probability is the model's confidence in ${labels['1'] ?? 'the positive class'}; at or above 0.5 it predicts that class. Rows follow the preprocessed partition's order.`}
              </p>
              <p className="work__hint">
                Saved as result <code className="mono">{result.result_id.slice(0, 12)}…</code>, with a
                snapshot of the model and these inputs. Evaluate or explain it on the{' '}
                <Link to="/results">Results</Link> page. This dataset now stays loaded, because
                unloading it or resetting a stage deletes the results saved from it.
              </p>

              <div className="work__scores-wrap">
                <table className="work__scores">
                  <caption className="sr-only">Model predictions for this partition</caption>
                  <thead>
                    <tr>
                      <th scope="col">Row</th>
                      <th scope="col">Probability</th>
                      <th scope="col">Prediction</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.row_ids.slice(start, start + PAGE_SIZE).map((rowId, index) => {
                      const at = start + index;
                      const predicted = result.predictions[at];
                      return (
                        <tr key={`${rowId}:${at}`}>
                          <th scope="row" className="mono">{String(rowId)}</th>
                          <td className="mono work__numeric">
                            {result.positive_probabilities[at].toFixed(4)}
                          </td>
                          <td>{labels[String(predicted)] ?? String(predicted)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="work__row">
                <Button onClick={() => setPage(page - 1)} disabled={page === 0}>
                  Previous
                </Button>
                <span className="work__hint">
                  {`Showing ${start + 1}–${Math.min(start + PAGE_SIZE, scored)} of ${scored.toLocaleString()}`}
                </span>
                <Button onClick={() => setPage(page + 1)} disabled={page >= lastPage}>
                  Next
                </Button>
              </div>
            </>
          )}
        </>
      )}
    </StepCard>
  );
}
