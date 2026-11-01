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


MODEL_IMPORT_FORMATS = (
    ModelImportFormat(
        format_id="pickle_estimator",
        extensions=(".pkl", ".pickle"),
        adapter_key="pickle_estimator",
        required_contents=(
            "Fitted estimator implementing the supported prediction interface",
            "Input feature schema and fitted preprocessing, bundled or supplied separately",
        ),
        requires_trusted_upload=True,
    ),
    ModelImportFormat(
        format_id="tabm_checkpoint",
        extensions=(".pt", ".pth"),
        adapter_key="tabm_checkpoint",
        required_contents=(
            "Model weights and architecture configuration, including embedding bins",
            "Ordered numeric and categorical feature names",
            "Fitted numeric preprocessing and category mappings",
        ),
        requires_trusted_upload=True,
    ),
    ModelImportFormat(
        format_id="onnx_model",
        extensions=(".onnx",),
        adapter_key="onnx",
        required_contents=(
            "ONNX computation graph and weights",
            "Input/output schema and preprocessing requirements",
        ),
    ),
)


@dataclass(frozen=True)
class BackendConfig:
    model_import_formats: tuple[ModelImportFormat, ...] = MODEL_IMPORT_FORMATS

    @property
    def supported_model_formats(self) -> tuple[ModelImportFormat, ...]:
        """Only formats backed by implemented and enabled import adapters."""
        return tuple(item for item in self.model_import_formats if item.enabled)


config = BackendConfig()
