"""HTTP contracts shared by the task-specific dataset APIs."""
from typing import Any
from math import isclose
from pydantic import BaseModel, ConfigDict, Field, model_validator

class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class SplitRequest(RequestModel):
    seed: int = Field(default=123, ge=0, le=4294967295, strict=True)
    train_fraction: float = Field(default=0.7, gt=0, lt=1, allow_inf_nan=False)
    test_fraction: float = Field(default=0.15, gt=0, lt=1, allow_inf_nan=False)
    eval_fraction: float = Field(default=0.15, gt=0, lt=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_total(self) -> "SplitRequest":
        if not isclose(self.train_fraction + self.test_fraction + self.eval_fraction, 1.0,
                       rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("Train, test, and eval fractions must sum to one")
        return self

class PrepareRequest(RequestModel):
    split_id: str = Field(min_length=1)

class PreprocessRequest(RequestModel):
    prepared_id: str = Field(min_length=1)

class SourceResponse(BaseModel):
    dataset_id: str
    task: str
    filename: str
    version: str
    sample_count: int
    columns: list[str]

class CleanResponse(BaseModel):
    dataset_id: str
    sample_count: int
    removed_sample_count: int
    schema_version: str

class SplitResponse(BaseModel):
    dataset_id: str
    split_id: str
    seed: int
    train_count: int
    test_count: int
    eval_count: int

class PrepareResponse(BaseModel):
    dataset_id: str
    split_id: str
    prepared_id: str
    train_count: int
    test_count: int
    eval_count: int

class PreprocessResponse(BaseModel):
    dataset_id: str
    prepared_id: str
    preprocessed_id: str
    partition: str = "eval"
    sample_count: int

class RecordsResponse(BaseModel):
    total: int
    offset: int
    limit: int
    records: list[dict[str, Any]]
