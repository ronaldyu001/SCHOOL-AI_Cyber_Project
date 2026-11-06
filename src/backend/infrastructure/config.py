"""Backend configuration, including model import capabilities.

An extension selects a candidate loader; the loader must validate the contents
and dataset compatibility. Enable a format only once its adapter is implemented.
Domain entities and application ports must not import this infrastructure module.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelImportFormat:
    format_id: str
    extensions: tuple[str, ...]
    adapter_key: str
    required_contents: tuple[str, ...]
    enabled: bool = False
    requires_trusted_upload: bool = False


MODEL_IMPORT_FORMATS = tuple(
    ModelImportFormat(
        format_id=architecture + "_bundle", extensions=(".zip",), adapter_key=architecture,
        required_contents=("manifest.json", "safetensors weights", "architecture configuration"),
        enabled=True,
    )
    for architecture in ("transformer", "tabm", "malconv")
)


@dataclass(frozen=True)
class BackendConfig:
    model_import_formats: tuple[ModelImportFormat, ...] = MODEL_IMPORT_FORMATS

    @property
    def supported_model_formats(self) -> tuple[ModelImportFormat, ...]:
        """Only formats backed by implemented and enabled import adapters."""
        return tuple(item for item in self.model_import_formats if item.enabled)


config = BackendConfig()
