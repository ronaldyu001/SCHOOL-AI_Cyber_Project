"""Discover and register local baselines through the ordinary model import flow."""
from threading import RLock
from application.ports.models.repository import BaselineCatalogPort, ModelRepositoryPort, ModelRuntimePort
from domain.entities.datasets.common import CyberTask
from application.use_cases.models.import_model import ImportModel

class ListBaselineModels:
    def __init__(self, catalog: BaselineCatalogPort):
        self.catalog = catalog

    def execute(self):
        return self.catalog.list()


class LoadBaselineModel:
    def __init__(self, catalog: BaselineCatalogPort, repository: ModelRepositoryPort, runtime: ModelRuntimePort):
        self.catalog, self.repository = catalog, repository
        self.importer = ImportModel(repository, runtime)
        self.loaded = {}
        self.lock = RLock()

    def execute(self, task):
        task = CyberTask(task).value
        # Serialize first load and reuse registrations; no duplicated large bundles.
        with self.lock:
            previous = self.loaded.get(task)
            if previous is not None:
                try:
                    with self.repository.borrow(previous) as (model, _):
                        return model, True
                except LookupError:
                    del self.loaded[task]
            path = self.catalog.path(task)
            with path.open('rb') as stream:
                model = self.importer.execute(stream)
            if model.bundle.task.value != task:
                self.repository.delete(model.model_id)
                raise ValueError('Baseline task does not match requested task')
            self.loaded[task] = model.model_id
            return model, False
