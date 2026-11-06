"""Coordinate backend artifact generation and reject inconsistent providers."""
from domain.entities.preprocessing.artifacts import provenance

class CreatePreprocessingArtifacts:
    def __init__(self, artifacts, models=None, runtime=None):
        self.artifacts, self.models, self.runtime = artifacts, models, runtime

    def execute(self, prepared, settings=None, model_id=None):
        if model_id is None:
            artifact = self.artifacts.create(prepared, settings)
        else:
            if prepared.source.task.value != "phishing_detection":
                raise ValueError("Only phishing artifacts accept model_id")
            if self.models is None or self.runtime is None:
                raise ValueError("Model service is not configured")
            with self.models.borrow(model_id) as (model, directory):
                if model.bundle.task != prepared.source.task:
                    raise ValueError("Selected model must be a phishing transformer")
                if model.has_tokenizer:
                    artifact = self.artifacts.create_with_tokenizer(
                        prepared, settings, self.runtime.tokenizer(directory), model_id)
                else:
                    artifact = self.artifacts.create(prepared, settings)
        if artifact.task != prepared.source.task or artifact.manifest["provenance"] != provenance(prepared):
            raise ValueError("Artifacts must preserve task, dataset version, and training membership")
        return artifact

class ExportPreprocessingArtifacts:
    def __init__(self, artifacts):
        self.artifacts = artifacts

    def execute(self, artifact_id):
        return self.artifacts.export(artifact_id)
