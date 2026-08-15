from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AIJobCreate(BaseModel):
    job_type: str
    model_name: str | None = None
    model_version: str | None = None
    input_artifact_id: int | None = None
    parameters: dict[str, Any] | None = None


class AIJobResponse(BaseModel):
    id: int
    page_id: int
    job_type: str
    status: str

    model_name: str | None
    model_version: str | None

    input_artifact_id: int | None
    output_artifact_id: int | None

    parameters: dict[str, Any] | None
    result_metadata: dict[str, Any] | None

    error_message: str | None

    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(
        from_attributes=True
    )