from datetime import datetime, timezone

from app.database.base import Base
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class Collections(Base):
    __tablename__="collections"

    id:Mapped[int]=mapped_column(
        primary_key=True,
        index=True,
    )
    name:Mapped[str]=mapped_column(
        String(200),
        nullable=False,
    )
    description:Mapped[str|None]=mapped_column(
        Text,
        nullable=True,
    )
    owner_id:Mapped[int]=mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )
    created_at:Mapped[datetime]=mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        nullable=False
    )
    updated_at:Mapped[datetime]=mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False
    )