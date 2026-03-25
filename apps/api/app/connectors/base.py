from abc import ABC, abstractmethod
from app.schemas.pricing import DistributorPrice


class AbstractDistributorConnector(ABC):
    """
    Base class for all distributor price & availability connectors.
    Each distributor (Gardners, Bertrams, Ingram, etc.) implements this interface.
    """

    @property
    def requires_credentials(self) -> bool:
        """
        Return False for connectors that don't need Secrets Manager credentials
        (e.g. mock/demo connectors). Defaults to True for real distributors.
        """
        return True

    @property
    @abstractmethod
    def distributor_code(self) -> str:
        """Unique identifier for this distributor e.g. 'GARDNERS'"""

    @property
    @abstractmethod
    def distributor_name(self) -> str:
        """Human-readable name e.g. 'Gardners Books'"""

    @abstractmethod
    async def get_price_availability(
        self,
        isbn13: str,
        credentials: dict,
    ) -> DistributorPrice:
        """
        Fetch live price and availability for a single ISBN using the retailer's credentials.

        Args:
            isbn13: The 13-digit ISBN to query
            credentials: Retailer's credentials for this distributor
                         (fetched from Secrets Manager)

        Returns:
            DistributorPrice with price and availability data.
            On error, returns a DistributorPrice with available=False and error message set.
        """
