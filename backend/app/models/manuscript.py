from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Manuscript(Base):
    __tablename__ = "manuscripts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    script: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    author: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    approximate_date: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )