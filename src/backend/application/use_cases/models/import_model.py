"""Publish only bundles whose weights load into service-owned model code."""
from typing import BinaryIO
from application.ports.models import ModelRepositoryPort, ModelRuntimePort
from domain.entities.models import UploadedModel

class ImportModel:
    def __init__(self, repository: ModelRepositoryPort, runtime: ModelRuntimePort):
        self.repository, self.runtime = repository, runtime

    def execute(self, stream: BinaryIO) -> UploadedModel:
        model = self.repository.upload(stream)
        try:
            with self.repository.borrow(model.model_id, pending=True) as (model, directory):
                self.runtime.validate(model, directory)
            self.repository.publish(model.model_id)
        except BaseException:
            self.repository.delete(model.model_id)
            raise
        return model
