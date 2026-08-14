from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ManuscriptCreate(BaseModel):
    title: str
    description: str | None = None
    language: str | None = None
    script: str | None = None
    author: str | None = None
    approximate_date: str | None = None
    source: str | None = None


class ManuscriptUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    language: str | None = None
    script: str | None = None
    author: str | None = None
    approximate_date: str | None = None
    source: str | None = None


class ManuscriptResponse(BaseModel):
    id: int
    collection_id: int
    title: str
    description: str | None
    language: str | None
    script: str | None
    author: str | None
    approximate_date: str | None
    source: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)