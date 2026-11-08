"""Analyze saved predictions without requiring a live model or dataset session."""
from datetime import datetime, timezone
from application.ports.progress import checkpoint, report_progress
import random
from application.ports.results import ResultRepositoryPort, EvaluationPort, ExplanationPort
from domain.entities.results import PredictionRows, PredictionOutcome

class AnalyzeResult:
    def __init__(self, repository: ResultRepositoryPort, evaluation: EvaluationPort, explanations: ExplanationPort):
        self.repository, self.evaluation, self.explanations = repository, evaluation, explanations

    def execute(self, task, result_id, options):
        options = dict(options)
        outcome = PredictionOutcome(options['outcome']) if options.get('outcome') is not None else None
        options['outcome'] = outcome.value if outcome is not None else None
        if outcome is not None and not options['explain']:
            raise ValueError("outcome filters explanations; set explain=true to use it")
        with self.repository.borrow(task, result_id) as (directory, metadata):
            report_progress("evaluation", 0, 1)
            rows = self.repository.rows(directory)
            PredictionRows(tuple(rows['row_ids']), tuple(rows['true_labels']), tuple(rows['positive_probabilities']))
            if len(rows['predictions']) != len(rows['row_ids']) or any(v not in (0, 1) for v in rows['predictions']):
                raise ValueError("Saved predictions must be binary and aligned with result rows")
            outcomes = [PredictionOutcome.from_labels(actual, predicted)
                        for actual, predicted in zip(rows['true_labels'], rows['predictions'])]
            counts = {item.value: outcomes.count(item) for item in PredictionOutcome}
            evaluation = self.evaluation.evaluate(rows, metadata['output_contract'])
            report_progress("evaluation", 1, 1)
            evaluation['outcome_counts'] = counts
            explanations = None
            selection = None
            if options['explain']:
                by_id = {row_id: i for i, row_id in enumerate(rows['row_ids'])}
                eligible = [row_id for row_id, group in zip(rows['row_ids'], outcomes)
                            if outcome is None or group == outcome]
                requested = options.get('row_ids')
                if requested is None:
                    if not eligible:
                        name = outcome.value if outcome is not None else 'all'
                        raise ValueError(f"No samples match outcome '{name}'")
                    count = min(options.get('sample_count', 4), len(eligible))
                    rng = random.Random(options['seed'])
                    if outcome is not None:
                        requested = rng.sample(eligible, count)
                    else:
                        pools = [[row_id for row_id, label in zip(rows['row_ids'], rows['true_labels']) if label == c] for c in (0, 1)]
                        for pool in pools: rng.shuffle(pool)
                        requested = []
                        while len(requested) < count:
                            for pool in pools:
                                if pool and len(requested) < count: requested.append(pool.pop())
                if not requested or len(set(requested)) != len(requested):
                    raise ValueError("Select distinct result row IDs to explain")
                if any(row_id not in by_id for row_id in requested):
                    raise ValueError("Explanation row IDs must belong to this result")
                if outcome is not None and any(outcomes[by_id[row_id]] != outcome for row_id in requested):
                    raise ValueError(f"All selected row IDs must match outcome '{outcome.value}'")
                selection = dict(outcome=outcome.value if outcome is not None else None,
                    eligible_count=len(eligible), selected_count=len(requested), row_ids=list(requested), outcome_counts=counts)
                samples = [(row_id, by_id[row_id], self.repository.sample(directory, by_id[row_id])) for row_id in requested]
                explanations = self.explanations.explain(directory, metadata, rows, samples, options)
                for sample in explanations.get('samples', []):
                    index = by_id[sample['row_id']]
                    sample.update(true_label=rows['true_labels'][index], predicted_label=rows['predictions'][index],
                                  positive_probability=rows['positive_probabilities'][index], outcome=outcomes[index].value)
            checkpoint()
            report_progress("saving_analysis", 0, 1)
            return self.repository.save_analysis(directory, dict(schema_version=1, task=task, result_id=result_id,
                created_at=datetime.now(timezone.utc).isoformat(), parameters=options, evaluation=evaluation,
                explainability=explanations, explanation_selection=selection))
