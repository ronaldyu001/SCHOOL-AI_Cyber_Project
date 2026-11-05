"""Coordinate backend artifact generation and reject inconsistent providers."""
from domain.entities.preprocessing.artifacts import provenance

class CreatePreprocessingArtifacts:
    def __init__(self, artifacts):
        self.artifacts = artifacts

    def execute(self, prepared, settings=None):
        artifact = self.artifacts.create(prepared, settings)
        if artifact.task != prepared.source.task or artifact.manifest["provenance"] != provenance(prepared):
            raise ValueError("Artifacts must preserve task, dataset version, and training membership")
        return artifact

class ExportPreprocessingArtifacts:
    def __init__(self, artifacts):
        self.artifacts = artifacts

    def execute(self, artifact_id):
        return self.artifacts.export(artifact_id)
