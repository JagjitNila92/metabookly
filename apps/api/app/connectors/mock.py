"""
Mock distributor connector for MVP development and testing.
Returns deterministic fake price & availability data based on the ISBN.
This means the same ISBN always returns the same mock data — useful for demos.
"""
from app.connectors.base import AbstractDistributorConnector
from app.schemas.pricing import DistributorPrice


class MockDistributorConnector(AbstractDistributorConnector):
    """
    Returns realistic-looking mock prices for demos.
    Replace with a real connector once the distributor provides API credentials.
    """

    @property
    def distributor_code(self) -> str:
        return "MOCK"

    @property
    def distributor_name(self) -> str:
        return "Demo Distributor (Mock)"

    async def get_price_availability(
        self,
        isbn13: str,
        credentials: dict,
    ) -> DistributorPrice:
        # Use ISBN digits to generate deterministic but realistic-looking data
        isbn_sum = sum(int(d) for d in isbn13 if d.isdigit())

        # ~80% of books are in stock
        available = (isbn_sum % 10) < 8

        # Generate a realistic trade discount price (30-50% off RRP)
        base_price = 8.99 + (isbn_sum % 15)
        trade_discount = 35 + (isbn_sum % 15)  # 35-50% discount
        net_price = round(base_price * (1 - trade_discount / 100), 2)

        return DistributorPrice(
            distributor_code=self.distributor_code,
            distributor_name=self.distributor_name,
            available=available,
            stock_quantity=(isbn_sum % 50 + 1) if available else 0,
            price_gbp=net_price,
            price_currency="GBP",
            discount_percent=float(trade_discount),
            lead_time_days=1 if available else None,
        )
