from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PageResponse(BaseModel):
    id: int
    manuscript_id: int
    page_number: int
    original_filename: str
    original_path: str
    processed_path: str | None
    mime_type: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)