from math import isfinite
from application.ports.models import ModelRepositoryPort, ModelRuntimePort

class PredictModel:
    def __init__(self, repository: ModelRepositoryPort, runtime: ModelRuntimePort, results=None):
        self.repository, self.runtime, self.results = repository, runtime, results

    def execute(self, model_id, dataset, context=None):
        with self.repository.borrow(model_id) as (model, directory):
            if model.bundle.task != dataset.source.task:
                raise ValueError("Model and dataset tasks differ")
            if model.bundle.architecture == "transformer" and dataset.model_id != model_id:
                raise ValueError("Preprocess this partition with the selected model_id first")
            scores = self.runtime.predict(model, directory, dataset)
            if len(scores) != len(dataset.row_ids) or any(not isfinite(x) or not 0 <= x <= 1 for x in scores):
                raise ValueError("Model predictions must be finite probabilities aligned with rows")
            prediction = {"model_id": model_id, "row_ids": list(dataset.row_ids),
                "positive_probabilities": scores, "predictions": [int(p >= 0.5) for p in scores],
                "output_contract": model.bundle.output_contract}
            if self.results is not None:
                if context is None: raise ValueError("Prediction persistence requires dataset context")
                prediction['result_id'] = self.results.save(prediction, dataset, model, directory, context)
                prediction['task'] = model.bundle.task.value
            return prediction
