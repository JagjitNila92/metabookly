from datetime import datetime
from pydantic import BaseModel


class OnixIngestResponse(BaseModel):
    feed_id: str
    status: str             # "completed" | "completed_with_errors" | "failed"
    records_found: int
    records_upserted: int
    records_failed: int
    errors: list[str]       # up to 20 error samples; full list in feed record


class OnixFeedSummary(BaseModel):
    id: str
    s3_bucket: str | None
    s3_key: str | None
    status: str
    records_found: int | None
    records_upserted: int | None
    records_failed: int | None
    triggered_by: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OnixFeedListResponse(BaseModel):
    feeds: list[OnixFeedSummary]
    total: int
