from pydantic import BaseModel


class DistributorPrice(BaseModel):
    distributor_code: str
    distributor_name: str
    available: bool
    stock_quantity: int | None = None
    price_gbp: float | None = None
    price_currency: str = "GBP"
    discount_percent: float | None = None
    lead_time_days: int | None = None
    error: str | None = None  # Set if this distributor call failed


class AvailabilityResponse(BaseModel):
    isbn13: str
    distributors: list[DistributorPrice]


class BatchAvailabilityRequest(BaseModel):
    isbns: list[str]

    model_config = {"json_schema_extra": {"example": {"isbns": ["9780008123895", "9780099549482"]}}}


class BatchAvailabilityResponse(BaseModel):
    results: dict[str, list[DistributorPrice]]  # isbn13 -> list of distributor prices
