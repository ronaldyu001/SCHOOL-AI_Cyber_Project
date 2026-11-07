"""One lock order for active dataset state, persistent artifacts and results."""
class StorageLifecycle:
    def __init__(self, results, artifacts, sessions):
        self.results, self.artifacts, self.sessions = results, artifacts, sessions
        self.lock = results.lock

    def cleanup(self, task, dataset_id, session, stage=None):
        # Called under the storage lock then the dataset lock.
        self.results.clear(task, dataset_id=dataset_id)
        candidates = set().union(*session.artifact_bindings.values()) if session.artifact_bindings else set()
        session.artifact_bindings.clear()
        referenced = {value for current in self.sessions[task].values()
                      for values in current.artifact_bindings.values() for value in values}
        for artifact_id in candidates - referenced:
            try:
                self.artifacts[task].delete(artifact_id)
            except FileNotFoundError:
                pass

    def delete_artifact(self, task, artifact_id):
        self.artifacts[task].delete(artifact_id)
        self.results.clear(task, artifact_id=artifact_id)
        for session in self.sessions[task].values():
            with session.lock:
                for bindings in session.artifact_bindings.values(): bindings.discard(artifact_id)
                for result_id, data in list(session.preprocessed.items()):
                    if data.artifact_id == artifact_id: del session.preprocessed[result_id]
