"""
Gardners Books connector — stub for post-MVP implementation.
Gardners uses BIC Realtime API (XML over HTTPS).
"""
from app.connectors.base import AbstractDistributorConnector
from app.schemas.pricing import DistributorPrice


class GardnersConnector(AbstractDistributorConnector):
    """
    TODO (post-MVP): Implement BIC Realtime price & availability requests to Gardners.

    Protocol: BIC Realtime API — HTTPS POST with XML payload
    Docs: https://bic.org.uk/resources/bic-realtime-for-libraries/
    Credentials needed: username, password, SAN (Standard Address Number)
    """

    @property
    def distributor_code(self) -> str:
        return "GARDNERS"

    @property
    def distributor_name(self) -> str:
        return "Gardners Books"

    async def get_price_availability(
        self,
        isbn13: str,
        credentials: dict,
    ) -> DistributorPrice:
        raise NotImplementedError(
            "Gardners connector not yet implemented. "
            "Requires BIC Realtime API credentials from Gardners."
        )
