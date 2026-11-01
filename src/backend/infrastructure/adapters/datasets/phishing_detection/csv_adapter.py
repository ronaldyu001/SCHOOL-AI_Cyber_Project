"""Lazy CSV reader implementing PhishingDetectionDatasetPort."""
import csv
from application.ports.datasets.phishing_detection import PhishingDetectionDatasetPort
import sys
from pathlib import Path
from domain.entities.datasets.phishing_detection import PhishingDetectionRawRecord

class PhishingDetectionCSVAdapter(PhishingDetectionDatasetPort):
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._columns: tuple[str, ...] | None = None
        self._records: tuple[PhishingDetectionRawRecord, ...] | None = None

    def _load(self) -> None:
        if self._records is not None:
            return
        # Some corpus emails exceed csv's default 128 KiB field limit.
        csv.field_size_limit(sys.maxsize)
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
                    records.append(PhishingDetectionRawRecord(row_id, tuple(
                        None if value == "" else value for value in values
                    )))
        except csv.Error as error:
            raise ValueError(f"Malformed dataset CSV: {error}") from error
        self._columns = columns
        self._records = tuple(records)

    def load_columns(self) -> tuple[str, ...]:
        self._load()
        assert self._columns is not None
        return self._columns

    def load_records(self) -> tuple[PhishingDetectionRawRecord, ...]:
        self._load()
        assert self._records is not None
        return self._records
