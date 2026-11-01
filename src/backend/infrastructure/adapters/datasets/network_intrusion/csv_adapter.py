"""Lazy CSV reader implementing NetworkIntrusionDatasetPort."""
import csv
from application.ports.datasets.network_intrusion import NetworkIntrusionDatasetPort
from pathlib import Path
from domain.entities.datasets.network_intrusion import NetworkIntrusionRawRecord
from domain.entities.datasets.network_intrusion.schema import MISSING_TOKEN

class NetworkIntrusionCSVAdapter(NetworkIntrusionDatasetPort):
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._columns: tuple[str, ...] | None = None
        self._records: tuple[NetworkIntrusionRawRecord, ...] | None = None

    def _load(self) -> None:
        if self._records is not None:
            return
        try:
            with self.path.open(newline="", encoding="utf-8-sig") as source:
                reader = csv.reader(source, strict=True)
                columns = tuple(next(reader, ()))
                if not columns:
                    raise ValueError("Dataset CSV is empty or has no header")
                records = []
                for row_id, values in enumerate(reader):
                    if len(values) != len(columns):
                        raise ValueError(f"Malformed CSV row {row_id}")
                    records.append(NetworkIntrusionRawRecord(row_id, tuple(
                        None if value in ("", MISSING_TOKEN) else value for value in values
                    )))
        except csv.Error as error:
            raise ValueError(f"Malformed dataset CSV: {error}") from error
        self._columns = columns
        self._records = tuple(records)

    def load_columns(self) -> tuple[str, ...]:
        self._load()
        assert self._columns is not None
        return self._columns

    def load_records(self) -> tuple[NetworkIntrusionRawRecord, ...]:
        self._load()
        assert self._records is not None
        return self._records
