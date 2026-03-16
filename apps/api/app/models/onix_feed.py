import uuid
from datetime import datetime
from sqlalchemy import BigInteger, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class OnixFeed(Base):
    __tablename__ = "onix_feeds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    s3_bucket: Mapped[str] = mapped_column(Text, nullable=False)
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    records_found: Mapped[int | None] = mapped_column(Integer)
    records_upserted: Mapped[int | None] = mapped_column(Integer)
    records_failed: Mapped[int | None] = mapped_column(Integer)
    error_detail: Mapped[str | None] = mapped_column(Text)
    triggered_by: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())
