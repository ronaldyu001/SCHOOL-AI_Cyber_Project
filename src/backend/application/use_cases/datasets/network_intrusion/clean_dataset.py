"""Fixed feature selection and deduplication in original source order."""
from domain.entities.datasets.network_intrusion import (
    NetworkIntrusionLoadedDataset, NetworkIntrusionCleanedDataset,
    NetworkIntrusionRecord, NetworkIntrusionLabel,
)
from domain.entities.datasets.network_intrusion.schema import NUMERIC_FEATURES, CATEGORICAL_FEATURES, TARGET_COLUMN

class CleanNetworkIntrusionDataset:
    def execute(self, dataset: NetworkIntrusionLoadedDataset) -> NetworkIntrusionCleanedDataset:
        indexes = {name: index for index, name in enumerate(dataset.columns)}
        selected = tuple(indexes[name] for name in (*NUMERIC_FEATURES, *CATEGORICAL_FEATURES, TARGET_COLUMN))
        seen = set()
        records = []
        for row in dataset.records:
            # Deduplicate selected source values just as the notebook does before encoding.
            key = tuple(row.values[index] for index in selected)
            if key in seen:
                continue
            label = row.values[indexes[TARGET_COLUMN]]
            if label is None:
                raise ValueError(f"Missing label at source row {row.row_id}")
            numeric_values = tuple(row.values[indexes[name]] for name in NUMERIC_FEATURES)
            try:
                record = NetworkIntrusionRecord(
                    row.row_id,
                    tuple(None if value is None else float(value) for value in numeric_values),
                    tuple(row.values[indexes[name]] for name in CATEGORICAL_FEATURES),
                    NetworkIntrusionLabel(int(label)),
                )
            except (ValueError, TypeError) as error:
                raise ValueError(f"Invalid network record at source row {row.row_id}: {error}") from error
            seen.add(key)
            records.append(record)
        return NetworkIntrusionCleanedDataset(dataset.source, tuple(records), dataset.sample_count)
