"""Portable dataset bundles, spooled to disk above 8 MiB."""
from dataclasses import fields, is_dataclass
from enum import Enum
import json
from io import BufferedWriter
from tempfile import SpooledTemporaryFile
from zipfile import ZipFile, ZIP_DEFLATED
from application.ports.datasets.export import ExportedDataset

class DatasetJSONEncoder(json.JSONEncoder):
    def default(self, value):
        if is_dataclass(value):
            return {field.name: getattr(value, field.name) for field in fields(value)}
        if isinstance(value, Enum):
            return value.value
        return super().default(value)


def write_json(archive, name, value):
    encoder = DatasetJSONEncoder(ensure_ascii=False, allow_nan=False)
    with archive.open(name, "w", force_zip64=True) as member, BufferedWriter(member) as output:
        for chunk in encoder.iterencode(value):
            output.write(chunk.encode("utf-8"))


class DatasetZIPExporter:
    task: str
    record_schema: dict | None = None

    def _export(self, dataset, stage, partition=None):
        stream = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
        try:
            with ZipFile(stream, "w", ZIP_DEFLATED, allowZip64=True) as archive:
                metadata = {"schema_version": 1, "task": self.task, "stage": stage,
                            "partition": partition}
                if self.record_schema is not None:
                    metadata["record_schema"] = self.record_schema
                if hasattr(dataset, "source"):
                    metadata["source"] = dataset.source
                if stage == "prepared":
                    metadata["split"] = dataset.split
                    selected = ("train", "test", "eval") if partition == "all" else (partition,)
                    for name in selected:
                        self._records(archive, f"{name}/", getattr(dataset, name).records)
                elif stage in ("loaded", "cleaned"):
                    if hasattr(dataset, "columns"):
                        metadata["columns"] = dataset.columns
                    if hasattr(dataset, "schema_version"):
                        metadata["dataset_schema_version"] = dataset.schema_version
                    self._records(archive, "", dataset.records)
                else:
                    # Includes all preprocessing arrays and encoding metadata without preview truncation.
                    write_json(archive, "data.json", dataset)
                write_json(archive, "manifest.json", metadata)
            stream.seek(0)
            suffix = f"-{partition}" if partition else ""
            return ExportedDataset(stream, f"{self.task}-{stage}{suffix}.zip")
        except BaseException:
            stream.close()
            raise

    def _records(self, archive, prefix, records):
        if self.task != "malware_detection":
            write_json(archive, prefix + "data.json", records)
            return
        # Preserve executable bytes separately; JSON holds their labels, hashes and archive paths.
        manifest = []
        for row in records:
            archive.writestr(prefix + row.relative_path, row.content)
            manifest.append({"row_id": row.row_id, "sha256": row.sha256,
                             "relative_path": row.relative_path, "label": int(row.label)})
        write_json(archive, prefix + "data.json", manifest)
