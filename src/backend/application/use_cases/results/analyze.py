"""Analyze saved predictions without requiring a live model or dataset session."""
from datetime import datetime, timezone
import random
from application.ports.results import ResultRepositoryPort, EvaluationPort, ExplanationPort
from domain.entities.results import PredictionRows

class AnalyzeResult:
    def __init__(self, repository: ResultRepositoryPort, evaluation: EvaluationPort, explanations: ExplanationPort):
        self.repository, self.evaluation, self.explanations = repository, evaluation, explanations

    def execute(self, task, result_id, options):
        with self.repository.borrow(task, result_id) as (directory, metadata):
            rows = self.repository.rows(directory)
            PredictionRows(tuple(rows['row_ids']), tuple(rows['true_labels']), tuple(rows['positive_probabilities']))
            evaluation = self.evaluation.evaluate(rows, metadata['output_contract'])
            explanations = None
            if options['explain']:
                requested = options.get('row_ids')
                if requested is None:
                    count = min(options.get('sample_count', 4), len(rows['row_ids']))
                    rng = random.Random(options['seed'])
                    pools = [[row_id for row_id, label in zip(rows['row_ids'], rows['true_labels']) if label == c] for c in (0, 1)]
                    for pool in pools: rng.shuffle(pool)
                    requested = []
                    while len(requested) < count:
                        for pool in pools:
                            if pool and len(requested) < count: requested.append(pool.pop())
                if not requested or len(set(requested)) != len(requested):
                    raise ValueError("Select distinct result row IDs to explain")
                by_id = {row_id: i for i, row_id in enumerate(rows['row_ids'])}
                if any(row_id not in by_id for row_id in requested):
                    raise ValueError("Explanation row IDs must belong to this result")
                samples = [(row_id, by_id[row_id], self.repository.sample(directory, by_id[row_id])) for row_id in requested]
                explanations = self.explanations.explain(directory, metadata, rows, samples, options)
            return self.repository.save_analysis(directory, dict(schema_version=1, task=task, result_id=result_id,
                created_at=datetime.now(timezone.utc).isoformat(), parameters=options, evaluation=evaluation,
                explainability=explanations))
