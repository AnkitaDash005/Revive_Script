from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    manuscript_id: Mapped[int] = mapped_column(
        ForeignKey("manuscripts.id"),
        nullable=False,
    )

    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    original_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    processed_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
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